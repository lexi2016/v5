"""M03 end-to-end default chain against original offline producer bytes."""
import unittest
from m03_fixture import SourceCase, make_source
from v5_shadow import us_source_daily as m


class SourceChainTests(SourceCase):
    def test_default_entry_copies_validated_source_and_reuses_binding(self):
        make_source(self.source)
        self.assertTrue(callable(getattr(m, 'run_us_source', None)), 'complete run_us_source is missing')
        result = m.run_us_source(self.request())
        self.assertEqual(result['status'], 'VALIDATED_SOURCE_BINDING')
        self.assertEqual(result['source_status'], 'READY')
        self.assertEqual(len(result['market_snapshot']['rows']), 24)
        for key, path in m.source_paths(self.source, '20261009').items():
            self.assertEqual(path.read_bytes(), m.source_paths(self.snapshot, '20261009')[key].read_bytes())
        self.assertEqual(m.run_us_source(self.request()), result)
        self.assertEqual(len(list(self.bindings.glob('*.json'))), 1)

class FailureBoundaryTests(SourceCase):
    def test_missing_source_never_implicitly_collects(self):
        self.assertTrue(callable(getattr(m, 'run_us_source', None)))
        self.assertEqual(m.run_us_source(self.request())['status'], 'SOURCE_MISSING')
        self.assertFalse(self.source.exists())
        self.assertFalse(list(self.bindings.glob('*.json')))

    def test_tampered_source_three_parts_fail_closed(self):
        for key in ('payload', 'receipt', 'manifest'):
            with self.subTest(key=key):
                source = self.root / key
                make_source(source)
                path = m.source_paths(source, '20261009')[key]
                path.write_bytes(b'{}')
                with self.assertRaises((RuntimeError, ValueError)):
                    m.run_us_source(self.request(source_root=source, snapshot_root=self.root / ('snap-'+key)))
        self.assertFalse(list(self.bindings.glob('*.json')))

    def test_bad_marker_overlap_symlink_and_wrong_code_root_rejected(self):
        make_source(self.source)
        for req in (self.request(snapshot_root=self.source), self.request(binding_root=self.source / 'nested'), self.request(v5_src=self.root / 'missing')):
            with self.assertRaises((ValueError, RuntimeError)):
                m.run_us_source(req)
        (self.source / '.v5-cloud-us-capture-root').write_text('bad')
        with self.assertRaises((ValueError, RuntimeError)):
            m.run_us_source(self.request())
        alias = self.root / 'alias'
        alias.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises((ValueError, RuntimeError)):
            m.run_us_source(self.request(source_root=alias))

    def test_wrong_date_session_phase_and_cutoff_refused(self):
        make_source(self.source)
        for changes in ({'session':'20261008'}, {'capture_phase':'PRE_OPEN'}, {'cutoff':'2026-10-10T09:00:15Z'}, {'cutoff':'2026-10-10T10:00:00'}, {'trade_date':'../escape'}):
            with self.subTest(changes=changes), self.assertRaises((ValueError, RuntimeError)):
                m.run_us_source(self.request(**changes))
        self.assertFalse(list(self.bindings.glob('*.json')))

    def test_pre_open_before_original_window_is_not_due(self):
        self.assertEqual(m.run_us_source(self.request(capture_phase='PRE_OPEN',cutoff='2026-10-09T12:59:59Z'))['status'], 'NOT_DUE')

    def test_independent_readback_rejects_each_tampered_snapshot(self):
        make_source(self.source)
        for key in ('payload','receipt','manifest'):
            req = self.request(snapshot_root=self.root / ('snap-'+key), binding_root=self.root / ('bind-'+key))
            result = m.run_us_source(req)
            path = m.source_paths(req.snapshot_root, req.trade_date)[key]
            path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaisesRegex((ValueError, RuntimeError), 'M03_SNAPSHOT_SHA_MISMATCH'):
                m.run_us_source(req)
            self.assertEqual(len(list(req.binding_root.glob('*.json'))), 1)

    def test_failure_does_not_replace_success(self):
        make_source(self.source)
        req = self.request()
        m.run_us_source(req)
        before={p.name:p.read_bytes() for p in self.bindings.glob('*.json')}
        with self.assertRaises((ValueError,RuntimeError)):
            m.run_us_source(self.request(cutoff='2026-10-10T09:00:15Z'))
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.bindings.glob('*.json')})

    def test_two_processes_publish_one_identical_binding(self):
        import concurrent.futures
        make_source(self.source)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(lambda _:m.run_us_source(self.request()), range(2)))
        self.assertEqual(outcomes[0],outcomes[1])
        self.assertEqual(len(list(self.bindings.glob('*.json'))),1)
        self.assertFalse(list(self.root.rglob('*.tmp')))

class AdditionalBoundaryTests(SourceCase):
    def test_explicit_collector_nonzero_and_zero_without_source_are_distinct(self):
        import json
        from m03_fixture import inner_chain
        for rc,status in ((7,'COLLECTOR_FAILED'),(0,'SOURCE_MISSING')):
            req=self.request(allow_network_capture=True,capture_root=self.root / ('capture-'+str(rc)))
            proc=inner_chain(req, "m.run_cold_collector=lambda request: {'returncode':"+str(rc)+",'stdout':'original diagnostic','stderr':'original failure'}")
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            result=json.loads(proc.stdout)
            self.assertEqual(result['status'],status)
            self.assertEqual(result['stdout'],'original diagnostic')
            self.assertFalse(list(self.bindings.glob('*.json')))

    def test_explicit_capture_uses_independent_root_and_then_real_reader(self):
        import json
        from m03_fixture import inner_chain, offline_collector_script
        capture=self.root / 'capture'
        req=self.request(allow_network_capture=True,capture_root=capture,allow_late_post_close=True)
        setup="""original=m.run_cold_collector
fixture_script="""+repr(offline_collector_script())+"""
def offline_runner(args,**kwargs):
    args=list(args)
    assert args[:4]==[m.sys.executable,'-I','-B','-c']
    args[4]=fixture_script
    return m.subprocess.run(args,**kwargs)
m.run_cold_collector=lambda request:original(request,runner=offline_runner)
"""
        proc=inner_chain(req,setup)
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['status'],'VALIDATED_SOURCE_BINDING')
        self.assertFalse(self.source.exists())
        self.assertNotEqual(capture,self.snapshot)
        for key,path in m.source_paths(capture,'20261009').items():
            self.assertEqual(path.read_bytes(),m.source_paths(self.snapshot,'20261009')[key].read_bytes())

    def test_collector_gate_argv_and_timeout(self):
        import subprocess
        from dataclasses import replace
        with self.assertRaisesRegex(ValueError,'M03_CAPTURE_NOT_AUTHORIZED'):
            m.run_cold_collector(self.request(),runner=lambda *a,**k:self.fail('collector executed'))
        req=self.request(allow_network_capture=True,capture_root=self.root/'capture',allow_late_post_close=True)
        args=m.collector_argv(req)
        self.assertEqual(args[args.index('--data-root')+1],str(req.capture_root))
        self.assertIn('--allow-late-post-close',args)
        with self.assertRaisesRegex(ValueError,'SESSION_DATE_MISMATCH'):
            m.collector_argv(replace(req,session='20261008'))
        def timeout(*a,**k):raise subprocess.TimeoutExpired('collector',300,output='kept',stderr='why')
        with self.assertRaisesRegex(RuntimeError,'M03_COLLECTOR_TIMEOUT'):
            m.run_cold_collector(req,runner=timeout)

    def test_same_phase_multiple_original_valid_captures_rejected(self):
        from m03_fixture import variant_source
        insert="""saved['us_session_captures'].append(dict(saved['us_session_captures'][0],capture_id='other-capture',run_id='other-run'))
from infrastructure.research_peripheral_store import ResearchPeripheralStore
store=ResearchPeripheralStore(root)
store.replace(saved,expected_sha256=store._manifest()[store._relative('20261009','external_finance')],reason='offline ambiguity fixture')
"""
        variant_source(self.source,[("before={str(p.relative_to(root)):",insert+"before={str(p.relative_to(root)):")])
        with self.assertRaisesRegex(RuntimeError,'M03_CAPTURE_AMBIGUOUS'):
            m.run_us_source(self.request())

    def test_source_changes_during_copy_rejected(self):
        from m03_fixture import inner_chain
        make_source(self.source)
        proc=inner_chain(self.request(),'''original=m._triplet
calls=0
def changing(root,request):
    global calls
    result=original(root,request)
    if root==request.source_root:
        calls+=1
        if calls==2:
            p=m.source_paths(root,request.trade_date)['receipt']
            p.write_bytes(p.read_bytes()+b' ')
    return result
m._triplet=changing
''')
        self.assertNotEqual(proc.returncode,0)
        self.assertIn('M03_SOURCE_CHANGED_DURING_COPY',proc.stderr)
        self.assertFalse(list(self.bindings.glob('*.json')))

    def test_changed_source_cannot_overwrite_existing_snapshot(self):
        import json
        from dataclasses import replace
        make_source(self.source)
        m.run_us_source(self.request())
        before={p.name:p.read_bytes() for p in self.bindings.glob('*.json')}
        source2=self.root/'source2'
        make_source(source2)
        path=m.source_paths(source2,'20261009')['receipt']
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(RuntimeError,'M03_SNAPSHOT_CONFLICT'):
            m.run_us_source(self.request(source_root=source2))
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.bindings.glob('*.json')})

    def test_original_valid_empty_is_explicitly_distinguished(self):
        from m03_fixture import variant_source
        variant_source(self.source,[("<item><title>NVIDIA semiconductor earnings growth - Reuters</title><description>NVIDIA reports semiconductor revenue growth.</description><link>https://example.invalid/synthetic-nvidia</link><source url=\"https://example.invalid\">Reuters</source><pubDate>Fri, 09 Oct 2026 19:00:00 GMT</pubDate></item>","")])
        result=m.run_us_source(self.request())
        self.assertEqual(result['source_status'],'READY_EMPTY')
        self.assertEqual(result['market_snapshot']['status'],'READY')

    def test_closed_original_calendar_session_is_not_due(self):
        self.assertEqual(m.run_us_source(self.request(session='20261010'))['status'],'NOT_DUE')

class EligibilityRaceTests(SourceCase):
    def test_valid_but_rejected_update_between_gate_and_copy_cannot_bind(self):
        from m03_fixture import inner_chain, variant_source
        make_source(self.source)
        rejected=self.root/'rejected'
        data=variant_source(rejected,[("fields[30]='20261009160000'","fields[30]='20261008160000'")])
        self.assertEqual(data['status'],'CANNOT_CONFIRM')
        proc=inner_chain(self.request(),'''original=m._copy_snapshot
def change_before_copy(request,source):
    import shutil
    for key,path in m.source_paths(source,request.trade_date).items():
        shutil.copyfile(m.source_paths(source.parent/'rejected',request.trade_date)[key],path)
    return original(request,source)
m._copy_snapshot=change_before_copy
''')
        self.assertNotEqual(proc.returncode,0,'a rejected source was published as a validated binding: '+proc.stdout)
        self.assertFalse(list(self.bindings.glob('*.json')))
        self.assertFalse(self.snapshot.exists(), 'rejected data must not freeze the snapshot root')

class OriginalPhaseTests(SourceCase):
    def test_pre_open_original_news_source_preserves_not_due_quote_state(self):
        from m03_fixture import variant_source
        result=variant_source(self.source,[
            ('output=io.StringIO()', "original_phase=owner.materialize_us_market_phase\nowner.materialize_us_market_phase=lambda **kwargs: original_phase(**kwargs,fetched_at='2026-10-09T13:00:16Z')\noutput=io.StringIO()"),
            ('datetime(2026,10,10,9,0,16','datetime(2026,10,9,13,0,16'),
            ("'POST_CLOSE','--allow-late-post-close'","'PRE_OPEN'"),
            ('Fri, 09 Oct 2026 19:00:00 GMT','Fri, 09 Oct 2026 12:00:00 GMT')])
        self.assertEqual(result['status'],'READY')
        outcome=m.run_us_source(self.request(capture_phase='PRE_OPEN',cutoff='2026-10-09T13:02:00Z'))
        self.assertEqual(outcome['status'],'NOT_DUE')
        self.assertEqual(outcome['reason'],'PRE_OPEN_QUOTE_NOT_DUE')
        self.assertFalse(list(self.bindings.glob('*.json')))

    def test_historical_original_reader_keeps_separate_three_part_contract(self):
        from m03_fixture import variant_source
        setup="""(root.parent/'dates.json').write_text('["20261009"]')
original_historical=owner.materialize_us_historical_backfill
owner.materialize_us_historical_backfill=lambda **kwargs: original_historical(**kwargs,fetched_at='2026-10-10T09:00:16Z')
"""
        result=variant_source(self.source,[
            ("output=io.StringIO()",setup+"output=io.StringIO()"),
            ("'--capture-phase','POST_CLOSE','--allow-late-post-close'","'--historical','--development-dates-file',str(root.parent/'dates.json')"),
            ('research/peripherals/20261009/external_finance.json','research/peripherals/history_backfill/20261009/external_finance.json'),
            ("read_exact('20261009','external_finance')","read_historical_backfill('20261009','external_finance')")])
        self.assertEqual(result['status'],'READY')
        req=self.request(capture_phase='HISTORICAL_BACKFILL')
        outcome=m.run_us_source(req)
        self.assertEqual(outcome['status'],'VALIDATED_SOURCE_BINDING')
        self.assertEqual(outcome['identity']['capture_origin'],'HISTORICAL_BACKFILL')
        self.assertFalse(outcome['identity']['original_time_capture'])
        self.assertFalse(outcome['production_allowed'])
        for key,path in m.source_paths(self.source,req.trade_date,req.capture_phase).items():
            self.assertEqual(path.read_bytes(),m.source_paths(self.snapshot,req.trade_date,req.capture_phase)[key].read_bytes())

    def test_invalid_market_session_and_response_hash_do_not_pass_reader(self):
        import json
        make_source(self.source)
        path=m.source_paths(self.source,'20261009')['payload']
        original=path.read_bytes()
        for key,value in (('capture_session_date','20261008'),('source_response_sha256','bad')):
            payload=json.loads(original)
            payload['market_snapshot'][key]=value
            path.write_text(json.dumps(payload))
            with self.assertRaises(RuntimeError):
                m.run_us_source(self.request())
        self.assertFalse(list(self.bindings.glob('*.json')))

    def test_binding_disk_identity_and_version_are_revalidated(self):
        import json
        make_source(self.source)
        m.run_us_source(self.request())
        target=next(self.bindings.glob('*.json'))
        original=target.read_bytes()
        for key,value in (('owner_source_commit','bad'),('orchestrator_sha256','0'*64),('source_status','CANNOT_CONFIRM')):
            binding=json.loads(original)
            binding[key]=value
            target.write_text(json.dumps(binding))
            with self.assertRaisesRegex(RuntimeError,'M03_BINDING_CONFLICT'):
                m.run_us_source(self.request())
        target.write_bytes(original)
        self.assertEqual(m.run_us_source(self.request())['status'],'VALIDATED_SOURCE_BINDING')

    def test_original_parse_utc_offset_and_naive_contract_retained(self):
        self.assertEqual(m.parse_utc('2026-10-10T04:00:00+02:00').hour,2)
        with self.assertRaises(ValueError):m.parse_utc('2026-10-10T01:00:00')

class ExecutionVersionTests(SourceCase):
    def test_imported_orchestrator_cannot_claim_changed_disk_bytes(self):
        import json, shutil, subprocess, sys
        from dataclasses import replace
        from m03_fixture import BASE
        code=self.root/'code'
        shutil.copytree(BASE,code)
        make_source(self.source)
        req=self.request(v5_src=code/'src')
        script='''import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import v5_shadow.us_source_daily as m
request=m._request_from_dict(json.loads(sys.argv[2]))
with Path(m.__file__).open('a') as out:out.write('\\n# modified after import\\n')
print(json.dumps(m._run_owned(request)))
'''
        proc=subprocess.run([sys.executable,'-I','-B','-c',script,str(req.v5_src),json.dumps(m._request_dict(req))],capture_output=True,text=True,timeout=30)
        self.assertNotEqual(proc.returncode,0,'changed disk code identity was falsely accepted')
        self.assertIn('M03_ORCHESTRATOR_CHANGED',proc.stderr)


class HistoricalAbsenceTests(SourceCase):
    def test_orphan_historical_source_is_not_permission_to_collect(self):
        import json
        from m03_fixture import inner_chain
        from v5_shadow.cloud_us_collector import initialize_output
        allowlist=self.root/'dates.json'
        allowlist.write_text('["20261009"]')
        for key in ('payload','receipt','manifest'):
            with self.subTest(key=key):
                source=self.root/('orphan-'+key)
                initialize_output(source,self.request().owner_root)
                paths=m.source_paths(source,'20261009','HISTORICAL_BACKFILL')
                paths[key].parent.mkdir(parents=True,exist_ok=True)
                content={str(paths['payload'].relative_to(source)):'a'*64} if key=='manifest' else {}
                paths[key].write_text(json.dumps(content))
                req=self.request(source_root=source,capture_phase='HISTORICAL_BACKFILL',allow_network_capture=True,capture_root=self.root/('capture-'+key),development_dates_file=allowlist)
                proc=inner_chain(req,"m.run_cold_collector=lambda request: (_ for _ in ()).throw(AssertionError('COLLECTOR_WAS_CALLED'))")
                self.assertNotEqual(proc.returncode,0)
                self.assertIn('M03_SOURCE_INCOMPLETE',proc.stderr)
                self.assertNotIn('COLLECTOR_WAS_CALLED',proc.stderr)


if __name__ == '__main__':
    unittest.main()

"""M07 original-owner chain. All created input records are SYNTHETIC."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from v5_shadow import a_stage_daily as daily

class M07ChainTests(unittest.TestCase):
    def test_concrete_entrypoint_has_no_callback_contract(self):
        import inspect
        names=inspect.signature(daily.run_a_stage_daily).parameters
        self.assertIn('request',names)
        self.assertNotIn('selector',names)
        self.assertNotIn('publish_verified',names)

    def test_original_raw_interface_requires_compatible_strict_body(self):
        owner=Path(__file__).resolve().parents[2]/'owner'
        code="""from stage_center.raw_store import validate_rows,RawStoreError
print(validate_rows([],trade_date='20261008',stage_id='STAGE_0930_0935',market='A_SHARE'))
for flag in (True, 0, 1, None):
 try: validate_rows([],trade_date='20261008',stage_id='STAGE_0930_0935',market='A_SHARE',allow_temporal_false_observation=flag)
 except RawStoreError: pass
 else: raise AssertionError('override accepted')
"""
        import os
        proc=subprocess.run([sys.executable,'-B','-c',code],env={**os.environ,'PYTHONPATH':str(owner)},capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)

class _M07Fixture(object):
    def setUp(self):
            from m07_fixture import make_case
            self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
            self.root=Path(self.tmp.name);inputs=self.root/'inputs';inputs.mkdir()
            self.request=make_case(inputs)
            self.output=self.root/'private-output';self.output.mkdir()
            (self.output/'.v5-m07-output').write_bytes(b'v5.m07-private-output.v1\n')
            (self.output/'ledger').mkdir()
            (self.output/'ledger/.v5-daily-run-ledger').write_bytes(b'v5.daily-run-ledger.v1\n')

    def run_case(self):return daily.run_a_stage_daily(self.request,output_root=self.output)

    def assert_blocked(self):
            result=self.run_case();self.assertEqual(result['status'],'BLOCKED',result)
            self.assertFalse((self.output/'current.json').exists())
            return result

class M07ConcreteOwnerTests(_M07Fixture, unittest.TestCase):
    def test_real_owner_chain_publishes_and_independently_reads_same_run(self):
            from m07_fixture import binding
            before={k:binding(Path(v['root'])) for k,v in self.request['inputs'].items()}
            result=self.run_case();self.assertEqual(result['status'],'SUCCEEDED',result)
            record=daily.read_a_stage_daily(self.output,self.request['target_date'],self.request['stage_id'])
            self.assertEqual(record['generation'],result['generation'])
            self.assertEqual(record['artifact_sha256'],result['artifact_sha256'])
            self.assertEqual(record['selection']['run_id'],result['selection']['run_id'])
            self.assertEqual(len(record['selection']['rows']),10)
            self.assertEqual(record['selection']['selection_status'],'PARTIAL_WITH_ROWS')
            self.assertEqual(record['selection']['source_status'],'CANNOT_CONFIRM')
            self.assertIn('FORMAL_OVERLAY_CANNOT_CONFIRM',record['selection']['cannot_confirm'])
            self.assertTrue(all(r['formal_eligible'] is False for r in record['selection']['rows']))
            self.assertTrue(all(r['research_quality_score']==72.5 for r in record['selection']['rows']))
            self.assertEqual(before,{k:binding(Path(v['root'])) for k,v in self.request['inputs'].items()})
            self.assertIs(result['natural_verified'],False)

    def test_original_selector_parity(self):
            result=self.run_case();self.assertEqual(result['status'],'SUCCEEDED',result)
            from stage_center.selection import select_a_live_stage
            admitted=result['selector_input'];rows=copy.deepcopy(admitted['rows']);before=copy.deepcopy(rows)
            expected=select_a_live_stage(rows,self.request['target_date'],self.request['stage_id'],self.request['recording']['artifact_sha256'],**admitted['kwargs'])
            self.assertEqual(expected,result['selection'])
            self.assertEqual(rows,before)
            self.assertEqual(admitted['algorithm'],'select_a_live_stage')
            self.assertEqual(admitted['input_mutated'],False)

    def test_success_is_reused_without_recomputation(self):
            result=self.run_case();again=self.run_case()
            self.assertEqual(again['status'],'REUSED_SUCCESS',again)
            self.assertEqual(again['generation'],result['generation'])
            self.assertEqual(len(list((self.output/'generations').iterdir())),1)

    def test_current_reader_does_not_create_any_files(self):
            self.run_case()
            def inventory():return {str(p.relative_to(self.output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.output.rglob('*') if p.is_file()}
            before=inventory();daily.read_a_stage_daily(self.output,'20261012','STAGE_0930_0935');self.assertEqual(inventory(),before)

    def test_unknown_hk_stage_is_blocked(self):
            self.request['stage_id']='STAGE_1545_1555';self.assert_blocked()

    def test_input_digest_is_checked(self):
            self.request['inputs']['pool']['files'][next(iter(self.request['inputs']['pool']['files']))]='0'*64
            self.assert_blocked()

    def test_claimed_natural_mode_is_rejected(self):
            self.request['natural']=True;self.assert_blocked()

    def test_future_recording_is_rejected(self):
            self.request['recording']['captured_at']='2099-10-12T09:35:00+08:00';self.assert_blocked()

    def test_recording_outside_original_window_is_rejected(self):
            self.request['recording']['captured_at']='2026-10-12T10:00:00+08:00';self.assert_blocked()

    def test_pool_source_date_drift_is_rejected(self):
            self.request['pool_source_dates']['a_d1_premarket_pool']='20261008';self.assert_blocked()

    def test_claimed_receipt_identity_is_rejected(self):
            self.request['recording']['receipt_sha256']='0'*64;self.assert_blocked()

    def test_missing_recording_is_not_valid_empty(self):
            self.request['recording']['run_id']='absent';self.assert_blocked()

    def test_readback_corruption_is_not_reused_success(self):
            result=self.run_case();self.assertEqual(result['status'],'SUCCEEDED',result)
            artifact=next((self.output/'generations').rglob('artifact.csv'));artifact.write_bytes(b'bad')
            with self.assertRaises(ValueError):daily.read_a_stage_daily(self.output,'20261012','STAGE_0930_0935')
            again=self.run_case();self.assertNotEqual(again['status'],'REUSED_SUCCESS',again)

    def test_current_compare_and_swap_failure_preserves_prior(self):
            first=self.run_case();self.assertEqual(first['status'],'SUCCEEDED',first)
            self.request['trigger']='MANUAL_RECOVERY';self.request['expected_generation']='f'*64
            before=(self.output/'current.json').read_bytes()
            result=self.run_case();self.assertEqual(result['status'],'BLOCKED',result)
            self.assertEqual((self.output/'current.json').read_bytes(),before)

def _rewrite_raw(case, transform, *, source_status='READY', missing=(), requested=None):
    """A new fully valid synthetic raw trio, not a mocked verifier."""
    from m07_fixture import binding
    from stage_center.raw_store import RawStore,RAW_FIELDS
    import csv
    binding_now=case.request['inputs']['live'];root=Path(binding_now['root']);old=RawStore(root).verify_run(case.request['target_date'],case.request['stage_id'],'A_SHARE',case.request['recording']['run_id'])
    with (root/old['artifact_relative']).open(encoding='utf-8-sig',newline='') as stream:
        rows=[{k:(r[k]=='True' if k=='temporal_cutoff_safe' else r[k]) for k in RAW_FIELDS} for r in csv.DictReader(stream)]
    rows=transform(rows)
    newroot=root.parent/('live-'+str(len(list(root.parent.glob('live-*')))));newroot.mkdir();(newroot/'.v5-m07-input').write_bytes(b'v5.m07-input-copy.v1\n')
    result=RawStore(newroot).publish(trade_date=case.request['target_date'],stage_id=case.request['stage_id'],market='A_SHARE',source_id='SYNTHETIC_A_QUOTES',source_status=source_status,rows=rows,cannot_confirm=[],source_evidence=['SYNTHETIC_ONLY'],requested_rows=old['requested_rows'] if requested is None else requested,missing_symbols=missing,window=old['window'],cutoff_at=old['cutoff_at'])
    case.request['inputs']['live']=binding(newroot)
    for key in ('run_id','artifact_sha256','manifest_sha256','receipt_sha256'):case.request['recording'][key]=result[key]

def _replace_research(case, source):
    from m07_fixture import binding,write
    from infrastructure.data_store import _canonical_bytes
    from domains.research import build_research_archive
    from infrastructure.research_store import HourlyResearchStore
    root=case.root/('research-'+str(len(list(case.root.glob('research-*')))));root.mkdir()
    (root/'.v5-m07-input').write_bytes(b'v5.m07-input-copy.v1\n')
    raw=_canonical_bytes(source);digest=hashlib.sha256(raw).hexdigest();path=root/'research/hourly/source'/f'{digest}.json';path.parent.mkdir(parents=True);path.write_bytes(raw)
    archive=build_research_archive(source,source_input_sha256=digest)
    HourlyResearchStore(root).publish(archive,slot=source['source_manifest']['hourly_slot'],mode='LIVE')
    case.request['inputs']['research']=binding(root)

class M07ExtendedTests(_M07Fixture, unittest.TestCase):
    def test_auction_original_route(self):
        from m07_fixture import make_case
        from stage_center.selection import select_a_0925_auction
        inputs=self.root/'auction';inputs.mkdir();self.request=make_case(inputs,stage='STAGE_0925')
        result=self.run_case();self.assertEqual(result['status'],'SUCCEEDED',result)
        admitted=result['selector_input'];self.assertEqual(admitted['algorithm'],'select_a_0925_auction')
        expected=select_a_0925_auction(copy.deepcopy(admitted['rows']),self.request['target_date'],self.request['recording']['artifact_sha256'],**admitted['kwargs'])
        self.assertEqual(expected,result['selection']);self.assertNotEqual(expected['rows'][0]['score'],expected['rows'][0]['qmt_amount'])

    def test_tail_uses_original_a_window(self):
        from m07_fixture import make_case
        inputs=self.root/'tail';inputs.mkdir();self.request=make_case(inputs,stage='STAGE_1445_1500')
        result=self.run_case();self.assertEqual(result['status'],'SUCCEEDED',result)
        self.assertEqual(result['selector_input']['algorithm'],'select_a_live_stage')
        self.assertEqual(result['selection']['stage_id'],'STAGE_1445_1500')

    def test_quote_fields_rejected(self):
        original=copy.deepcopy(self.request)
        for field in ('open_price','last_price','prev_close_price','high_price','low_price','volume','turnover','bid_vol','ask_vol'):
            with self.subTest(field=field):
                self.request=copy.deepcopy(original)
                _rewrite_raw(self,lambda rows: [{**r,field:''} for r in rows])
                self.assertIn('M07_REQUIRED_NUMBER',str(self.assert_blocked()))

    def test_duplicate_raw_rejected(self):
        _rewrite_raw(self,lambda rows: [rows[0]]+rows);self.assert_blocked()

    def test_partial_coverage_is_not_promoted(self):
        _rewrite_raw(self,lambda rows: rows[:-1],source_status='PARTIAL_WITH_ROWS',missing=['A.000012'])
        result=self.run_case();self.assertEqual(result['status'],'SUCCEEDED',result)
        self.assertEqual(result['selection']['missing_symbols'],['A.000012'])
        self.assertEqual(result['selection']['selection_status'],'PARTIAL_WITH_ROWS')
        self.assertEqual(result['selection']['source_rows'],11)

    def test_ready_missing_contradiction_rejected(self):
        _rewrite_raw(self,lambda rows: rows[:-1],missing=['A.000012']);self.assert_blocked()

    def test_empty_unknown_are_not_ready_empty(self):
        _rewrite_raw(self,lambda rows: [],requested=12,missing=['A.'+f'{i+1:06}' for i in range(12)])
        self.assert_blocked()

    def test_research_unknown_is_not_numeric_zero(self):
        from m07_fixture import binding,write
        root=Path(self.request['inputs']['research']['root'])
        # A wholly absent exact-date archive is never substituted by current data.
        self.request['inputs']['research']['files']={'manifest.json':self.request['inputs']['research']['files']['manifest.json']}
        result=self.assert_blocked();self.assertIn('research',str(result).lower())

    def test_symlink_source_rejected(self):
        binding=self.request['inputs']['pool'];name=next(iter(binding['files']));path=Path(binding['root'])/name
        target=path.with_suffix('.saved');path.rename(target);path.symlink_to(target)
        self.assert_blocked()

    def test_sources_rehashed_after_claim_before_copy(self):
        name=next(iter(self.request['inputs']['morning']['files']));path=Path(self.request['inputs']['morning']['root'])/name
        path.write_bytes(path.read_bytes()+b' ');self.assert_blocked()

    def test_changed_input_new_generation_leaves_old_readable(self):
        first=self.run_case();self.assertEqual(first['status'],'SUCCEEDED',first)
        self.request['trigger']='MANUAL_RECOVERY';self.request['expected_generation']=first['generation']
        second=self.run_case();self.assertEqual(second['status'],'SUCCEEDED',second)
        self.assertNotEqual(first['generation'],second['generation'])
        self.assertEqual(len(list((self.output/'generations').iterdir())),2)
        self.assertEqual(daily.read_a_stage_daily(self.output,'20261012','STAGE_0930_0935')['generation'],second['generation'])

    def test_concurrent_same_identity(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.run_case(),range(2)))
        self.assertEqual(sum(r['status']=='SUCCEEDED' for r in results),1,results)
        self.assertTrue(all(r['status'] in ('SUCCEEDED','IN_PROGRESS_OR_OUTCOME_UNKNOWN','REUSED_SUCCESS') for r in results),results)

    def test_original_acquisition_rank_and_code_are_preserved(self):
        _rewrite_raw(self,lambda rows:[{**r,'batch_index':str(12-i),'turnover':'100000000'} for i,r in enumerate(rows)])
        result=self.run_case();self.assertEqual(result['status'],'SUCCEEDED',result)
        self.assertEqual(result['selection']['rows'][0]['code'],'A.000012')
        self.assertEqual(result['selector_input']['rows'][0]['acquisition_rank'],12)

    def test_rollback_is_verified_and_compare_and_swap_only(self):
        first=self.run_case();self.assertEqual(first['status'],'SUCCEEDED',first)
        self.request['trigger']='MANUAL_RECOVERY';self.request['expected_generation']=first['generation']
        second=self.run_case();self.assertEqual(second['status'],'SUCCEEDED',second)
        reference=first['state']['latest_success']['product_reference']
        restored=daily.activate_a_stage_generation(self.output,reference,expected_generation=second['generation'])
        self.assertEqual(restored['generation'],first['generation'])
        with self.assertRaisesRegex(ValueError,'EXPECTED_GENERATION'):
            daily.activate_a_stage_generation(self.output,reference,expected_generation=second['generation'])

    def test_verified_research_none_is_preserved_and_blocks(self):
        from m07_fixture import _source
        from stage_center.research_context import load_research_context
        _replace_research(self,_source('20261012',slot='0900',with_stage_evidence=False))
        context=load_research_context(self.request['inputs']['research']['root'],trade_date='20261012',stage_cutoff='09:35:05',morning_root=self.request['inputs']['morning']['root'])
        self.assertIsNone(context.by_code['A.000001'].research_quality_score)
        result=self.assert_blocked();self.assertIn('M07_RESEARCH_REQUIRED_FIELDS_MISSING',str(result))

    def test_future_research_archive_is_not_used(self):
        from m07_fixture import _source
        _replace_research(self,_source('20261012',slot='1000',with_stage_evidence=True))
        result=self.assert_blocked();self.assertIn('before cutoff',str(result))

    def test_raw_temporal_false_rejected_for_default_and_false(self):
        from stage_center.raw_store import RAW_FIELDS,validate_rows,RawStoreError
        row=dict.fromkeys(RAW_FIELDS,'1');row.update(code='A.000001',update_time='2026-10-12 09:35:00',window_start='2026-10-12 09:30:00',window_end='2026-10-12 09:35:00',temporal_cutoff_safe=False)
        for extra in ({},{'allow_temporal_false_observation':False}):
            accepted,issues=validate_rows([row],trade_date='20261012',stage_id='STAGE_0930_0935',market='A_SHARE',**extra)
            self.assertEqual(accepted,[]);self.assertTrue(any('temporal_cutoff_safe' in x for x in issues))
        with self.assertRaisesRegex(RawStoreError,'M07_TEMPORAL_FALSE_OVERRIDE'):
            validate_rows([row],trade_date='20261012',stage_id='STAGE_0930_0935',market='A_SHARE',allow_temporal_false_observation=True)

    def test_closed_and_unknown_calendar(self):
        for date in ('20261011','20270104'):
            with self.subTest(date=date):
                self.request['target_date']=date
                result=self.assert_blocked();self.assertIn('M07_MARKET_NOT_OPEN',str(result))

    def test_other_market_bytes_unchanged_during_publish_and_rollback(self):
        other=self.root/'hk-output';other.mkdir();(other/'current.json').write_bytes(b'UNCHANGED_HK_SENTINEL')
        before=(other/'current.json').read_bytes()
        self.test_rollback_is_verified_and_compare_and_swap_only()
        self.assertEqual((other/'current.json').read_bytes(),before)

    def test_generation_symlink_cannot_redirect_publication(self):
        outside=self.root/'unrelated';outside.mkdir()
        (self.output/'generations').symlink_to(outside,target_is_directory=True)
        result=self.run_case();self.assertEqual(result['status'],'BLOCKED',result)
        self.assertEqual(list(outside.iterdir()),[])

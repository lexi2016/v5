"""Synthetic protocol tests; no producer, collector or real request data."""
import copy
import json
import unittest
from contextlib import ExitStack, nullcontext
from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

from v5_shadow import us_mapping_scope as scope
from v5_shadow import us_mapping_daily as wrapper
from v5_shadow.digests import canonical_bytes, sha256_json


def fixture():
    session = '20261009'
    payload_path = f'research/peripherals/{session}/external_finance.json'
    receipt_path = f'receipts/{payload_path}'
    manifest_path = 'research/peripherals/manifest.json'
    files = {payload_path: 'a'*64, receipt_path: 'b'*64, manifest_path: 'c'*64}
    request = dict(target_date='20261012', now='2026-10-10T01:25:07.580831+00:00',
                   us_data_root='/synthetic/input', manager_output_root='/synthetic/output', us_files=files)
    flags = dict(RESEARCH_ONLY=True, production_allowed=False, buy_gate_updated=False, orders_sent=False)
    daily = dict(schema_version='v4.manager_research.us_mapping_daily_run.v1', status='COMPLETED',
        target_trade_date=request['target_date'], run_id='d'*32, generated_at='2026-10-11T17:35:19Z',
        us_session_date=session, research_cutoff=request['now'],
        coverage_scope='FOUR_REVIEWED_US_TICKER_RELATIONS_WITHIN_FIXED_33_CONFIGURED_SYMBOL_SAMPLE_NOT_FULL_MARKET',
        coverage=dict(reviewed_us_symbol_count=4, matched_us_symbol_count=1, matched_hk_relation_count=1,
                      configured_us_universe_count=33, available_us_universe_count=33, full_market_coverage=False),
        matches=[dict(us_symbol='AAA', hk_symbol='HK.00001', change_pct=2.0, session_date=session,
                      source_row=dict(symbol='AAA',session_date=session,change_pct=2.0),
                      reviewed_relation_artifact_sha256='f'*64,
                      target_date_eligibility='CANNOT_CONFIRM')],
        source_status='READY',source_identity=dict(owner='ResearchPeripheralStore',source='external_finance',
            session_date=session,status='VERIFIED',payload_path=payload_path,receipt_path=receipt_path,
            manifest_path=manifest_path,payload_sha256=files[payload_path],receipt_sha256=files[receipt_path],
            manifest_sha256=files[manifest_path]), source_gaps=[],input_identity='e'*64,
        relation_artifact_sha256='f'*64,target_date_eligibility='CANNOT_CONFIRM',
        producer_owner='ManagerResearchJobService / ResearchPeripheralStore read adapter',readback_required=True,gaps=[],**flags)
    daily['artifact_sha256'] = sha256_json(daily)
    result = dict(schema_version='v5.us_mapping_daily.v1',execution_kind='MANUAL_RECOVERY',
        requested_research_cutoff=request['now'],context_sha256='1'*64,
        actual_started_at='2026-10-11T17:35:19.430507+00:00',actual_finished_at='2026-10-11T17:35:19.770685+00:00',
        source_capsule_sha256=wrapper.PIN,implementation_identity={'us_mapping_scope.py':'2'*64},
        persisted_daily=daily,payload=dict(schema_version='v4.manager_research.us_mapping_research.v1',
            target_trade_date=request['target_date'],daily_run=copy.deepcopy(daily),reviewed_research=None,**flags),
        readback_status='MATCHED',coverage_diagnostics=dict(status='CANNOT_CONFIRM',formal_eligible=False,
            natural_verified=False,full_market_coverage=False,rows=None),input_sha_before=copy.deepcopy(files),
        input_sha_after=copy.deepcopy(files),source_origin_verified=False,natural_verified=False,
        isolation='PINNED_OWNER_PYTHON_WRITE_GUARDS_NOT_OS_SANDBOX')
    return result,request


def resign(result):
    daily=result['persisted_daily']
    daily['artifact_sha256']=sha256_json({k:v for k,v in daily.items() if k!='artifact_sha256'})
    result['payload']['daily_run']=copy.deepcopy(daily)


class RecoveryEvaluationTests(unittest.TestCase):
    def evaluate(self,result,request):
        fn=getattr(scope,'describe_recovery_evaluation',None)
        self.assertTrue(callable(fn),'Missing parallel recovery evaluation; historical scope must stay unchanged')
        return fn(result,request)

    def test_late_recovery_reports_current_product_without_promoting_historical_scope(self):
        result,request=fixture();out=self.evaluate(result,request);daily=result['persisted_daily']
        self.assertEqual(out['status'],daily['status'])
        for field in ('run_id','artifact_sha256','target_trade_date','us_session_date','coverage','matches','source_status'):
            self.assertEqual(out[field],daily[field])
        self.assertFalse(out['recorded_generated_at_lte_cutoff'])
        self.assertEqual(out['historical_availability'],'NOT_ESTABLISHED')
        self.assertEqual(result['coverage_diagnostics']['status'],'CANNOT_CONFIRM')
        self.assertIs(out['natural_verified'],False);self.assertIs(out['formal_eligible'],False)
        self.assertIs(out['source_origin_verified'],False)
        self.assertEqual(out['target_date_eligibility'],'CANNOT_CONFIRM')

    def test_same_second_nonlate_result_is_only_a_temporal_fact(self):
        result,request=fixture();request['now']='2026-10-11T17:35:19.400000Z'
        result['requested_research_cutoff']=request['now'];result['persisted_daily']['research_cutoff']=request['now'];resign(result)
        out=self.evaluate(result,request)
        self.assertTrue(out['recorded_generated_at_lte_cutoff'])
        self.assertEqual(out['historical_availability'],'NOT_ESTABLISHED')
        self.assertIs(out['formal_eligible'],False)

    def test_original_status_and_none_are_preserved(self):
        for status in ('VALID_EMPTY','PARTIAL','CANNOT_CONFIRM','FAILED','INPUT_MISSING'):
            result,request=fixture();daily=result['persisted_daily'];daily['status']=status
            daily['coverage']['matched_hk_relation_count']=None;daily['matches']=[];resign(result)
            out=self.evaluate(result,request)
            self.assertEqual(out['status'],status);self.assertIsNone(out['coverage']['matched_hk_relation_count'])

    def test_rejects_readback_identity_and_digest_changes(self):
        mutations=[lambda r,q:r.update(readback_status='FAILED'),
            lambda r,q:r['payload']['daily_run'].update(run_id='9'*32),
            lambda r,q:r['persisted_daily'].update(run_id='not-a-run'),
            lambda r,q:r['persisted_daily'].update(artifact_sha256='0'*64),
            lambda r,q:r['payload'].update(target_trade_date='20261013'),
            lambda r,q:q.update(target_date='20261013'),
            lambda r,q:r['persisted_daily']['source_identity'].update(session_date='20261008'),
            lambda r,q:r['persisted_daily']['source_identity'].update(payload_sha256='3'*64),
            lambda r,q:r['input_sha_before'].update(extra='a'*64),
            lambda r,q:r['input_sha_after'].pop('research/peripherals/manifest.json'),
            lambda r,q:q['us_files'].update(extra='a'*64)]
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)):
                r,q=fixture();mutate(r,q)
                with self.assertRaises(ValueError):self.evaluate(r,q)

    def test_rehashed_session_paths_and_source_identity_rejected(self):
        for field,value in [('session_date','20261008'),('payload_path','research/peripherals/20261008/external_finance.json'),
                            ('status','CANNOT_CONFIRM'),('owner','other'),('receipt_sha256','8'*64)]:
            with self.subTest(field=field):
                r,q=fixture();r['persisted_daily']['source_identity'][field]=value;resign(r)
                with self.assertRaises(ValueError):self.evaluate(r,q)

    def test_rejects_times_missing_fields_and_nonfinite_numbers(self):
        changes=[('actual_started_at','2026-10-11T17:35:20Z'),('actual_finished_at','2026-10-11T17:35:18Z'),
                 ('actual_started_at','2026-10-11T17:35:19'),('requested_research_cutoff','2026-10-10T01:25:08Z')]
        for field,value in changes:
            r,q=fixture();r[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.evaluate(r,q)
        for value in ('2026-10-11T17:35:19.123Z','2026-10-11T17:35:18Z','2026-10-11T17:35:19'):
            r,q=fixture();r['persisted_daily']['generated_at']=value;resign(r)
            with self.subTest(generated=value),self.assertRaises(ValueError):self.evaluate(r,q)
        for section,field in [('result','payload'),('daily','coverage'),('daily','readback_required'),('source','manifest_sha256'),('request','now')]:
            r,q=fixture();part={'result':r,'daily':r['persisted_daily'],'source':r['persisted_daily']['source_identity'],'request':q}[section];part.pop(field)
            with self.subTest(missing=field),self.assertRaises(ValueError):self.evaluate(r,q)
        for bad in (float('nan'),float('inf'),-float('inf')):
            r,q=fixture();r['persisted_daily']['matches'][0]['change_pct']=bad
            with self.subTest(nonfinite=str(bad)),self.assertRaises(ValueError):self.evaluate(r,q)

    def test_boolean_integer_confusion_rejected_even_after_resigning(self):
        for section,field,value in [('daily','RESEARCH_ONLY',1),('daily','orders_sent',0),('daily','readback_required',1),
            ('payload','production_allowed',0),('result','natural_verified',0),('result','source_origin_verified',0),
            ('scope','formal_eligible',0),('scope','natural_verified',0),('coverage','full_market_coverage',0),
            ('coverage','matched_us_symbol_count',True)]:
            r,q=fixture();part={'daily':r['persisted_daily'],'payload':r['payload'],'result':r,'scope':r['coverage_diagnostics'],'coverage':r['persisted_daily']['coverage']}[section]
            part[field]=value;resign(r)
            with self.subTest(section=section,field=field),self.assertRaises(ValueError):self.evaluate(r,q)

    def test_canonical_readback_rejects_python_bool_int_equality(self):
        r,q=fixture();r['payload']['daily_run']['orders_sent']=0
        self.assertEqual(r['persisted_daily'],r['payload']['daily_run'])
        with self.assertRaises(ValueError):self.evaluate(r,q)

    def test_every_declared_result_daily_source_and_request_field_is_required(self):
        initial,request=fixture()
        declarations={'result':initial,'daily':initial['persisted_daily'],
                      'source':initial['persisted_daily']['source_identity'],'request':request}
        for section,value in declarations.items():
            for field in value:
                r,q=fixture()
                target={'result':r,'daily':r['persisted_daily'],'source':r['persisted_daily']['source_identity'],'request':q}[section]
                target.pop(field)
                # A recomputed artifact must not turn an incomplete owner
                # declaration into an admissible evaluation.
                if section in ('daily','source') and field!='artifact_sha256':resign(r)
                with self.subTest(section=section,missing=field),self.assertRaises(ValueError):self.evaluate(r,q)

    def test_rehashed_match_relation_and_session_mismatch_rejected(self):
        for field,value in [('session_date','20261008'),('reviewed_relation_artifact_sha256','8'*64)]:
            r,q=fixture();r['persisted_daily']['matches'][0][field]=value;resign(r)
            with self.subTest(field=field),self.assertRaises(ValueError):self.evaluate(r,q)

    def test_complete_source_set_must_match_even_when_all_declarations_agree(self):
        r,q=fixture()
        for files in (q['us_files'],r['input_sha_before'],r['input_sha_after']):files['unbound.json']='a'*64
        with self.assertRaises(ValueError):self.evaluate(r,q)

    def test_no_io_no_mutation_and_no_output_alias(self):
        r,q=fixture();before=canonical_bytes([r,q])
        with patch('builtins.open',side_effect=AssertionError('I/O')),patch('os.open',side_effect=AssertionError('I/O')),patch('socket.socket',side_effect=AssertionError('network')):
            out=self.evaluate(r,q)
        self.assertEqual(canonical_bytes([r,q]),before)
        out['matches'].clear();out['coverage']['matched_hk_relation_count']=99
        self.assertEqual(canonical_bytes([r,q]),before)

    def test_historical_scope_late_recovery_remains_unknown(self):
        r,q=fixture();daily=r['persisted_daily']
        market=dict(research_cutoff=q['now'],source_identity=daily['source_identity'],status='READY',expected_us_session=daily['us_session_date'],raw_individual_up=[])
        old=scope.describe_scope(daily,market,dict(cards=[],artifact_sha256=daily['relation_artifact_sha256']))
        self.assertEqual(old['status'],'CANNOT_CONFIRM');self.assertIsNone(old['rows'])
        self.assertEqual(self.evaluate(r,q)['status'],'COMPLETED')

    def wrapper_call(self,fail_at=None):
        r,q=fixture();events=[];identity=r['implementation_identity'];snap_count=0;source_count=0
        def snapshot(*args):
            nonlocal snap_count
            snap_count+=1;events.append('snapshot'+str(snap_count))
            if fail_at=='snapshot' and snap_count==2:raise ValueError('INPUT_CHANGED')
            return {p:b'{}' for p in q['us_files']}
        def sources():
            nonlocal source_count
            source_count+=1;events.append('sources'+str(source_count))
            if fail_at=='sources' and source_count==2:raise ValueError('SOURCE_CHANGED')
        def ident():
            events.append('identity')
            return {} if fail_at=='identity' and events.count('identity')==2 else identity
        def child(*args,**kwargs):events.append('worker');return SimpleNamespace(returncode=0,stdout=canonical_bytes(r),stderr=b'')
        real=getattr(scope,'describe_recovery_evaluation',None)
        self.assertTrue(callable(real),'Missing recovery evaluation hook')
        def evaluate(result,request):events.append('evaluation');return real(result,request)
        with ExitStack() as stack:
            for name,value in [('_request',lambda _:None),('_snapshot',snapshot),('_sources',sources),('_identity',ident)]:stack.enter_context(patch.object(wrapper,name,side_effect=value))
            stack.enter_context(patch.object(wrapper.subprocess,'run',side_effect=child))
            stack.enter_context(patch.object(scope,'describe_recovery_evaluation',side_effect=evaluate))
            if fail_at:
                with self.assertRaises(ValueError):wrapper.run_us_mapping(q)
                self.assertNotIn('evaluation',events)
            else:
                result=wrapper.run_us_mapping(q)
                self.assertIn('recovery_evaluation',result)
                self.assertEqual(events,['sources1','identity','snapshot1','worker','snapshot2','sources2','identity','evaluation'])
                self.assertEqual(result['coverage_diagnostics'],r['coverage_diagnostics'])

    def test_wrapper_evaluates_only_after_all_final_checks(self):self.wrapper_call()

    def test_wrapper_never_evaluates_failed_input_source_or_implementation(self):
        for failure in ('snapshot','sources','identity'):
            with self.subTest(failure=failure):self.wrapper_call(failure)



    def original_failure(self, case):
        # Execute the frozen original builder and bridge. Only external reads,
        # context and relation-file reads are injected; no producer/persistence.
        vendor = str(Path(__file__).parents[1] / 'vendor' / 'us_mapping_baseline')
        sys.path.insert(0, vendor)
        try:
            from v4.manager_research import us_mapping_research as original
            from v4.manager_research import us_market_bridge as bridge
            from infrastructure import owned_io
        finally:
            sys.path.remove(vendor)
        r,q=fixture()
        if case == 'missing':
            reader=None
        elif case == 'read_failed':
            def read(_):raise OSError('synthetic unavailable source')
            reader=SimpleNamespace(read_exact_session=read)
        elif case == 'no_snapshot':
            reader=SimpleNamespace(read_exact_session=lambda _: ({}, {}))
        else:
            # Original reader produces its real unverified lineage shape.
            reader=bridge.ResearchPeripheralUsMarketReader.__new__(bridge.ResearchPeripheralUsMarketReader)
            reader.root=Path('/synthetic/input')
            reader.store=SimpleNamespace(_lock=nullcontext,
                read_exact=lambda *args: {'market_snapshot': {}})
        with ExitStack() as stack:
            stack.enter_context(patch.object(original,'plan_context',return_value={'research_cutoff':q['now']}))
            stack.enter_context(patch.object(original,'_read_reviewed',return_value={'cards':[],'artifact_sha256':'f'*64}))
            stack.enter_context(patch.object(original,'_relation_available_at',return_value=(None,'US_HK_RELATION_AVAILABILITY_UNVERIFIED')))
            if case == 'lineage':
                io=SimpleNamespace(read_bytes=lambda *args,**kwargs: (_ for _ in ()).throw(OSError('synthetic bytes unavailable')))
                stack.enter_context(patch.object(owned_io,'SafeRoot',return_value=io))
            daily=original.build_daily_run(SimpleNamespace(_workspace_us_market_reader=reader),
                q['target_date'],now=datetime.fromisoformat(r['actual_started_at']))
        r['persisted_daily']=daily
        resign(r)  # Same artifact signing as persist_daily_run, no disk write.
        return r,q

    def through_wrapper(self,r,q,identity=None):
        from v5_shadow import daily_us_owner
        with ExitStack() as stack:
            for name,value in [('_request',None),('_sources',None),
                ('_identity',r['implementation_identity'] if identity is None else identity),
                ('_snapshot',{p:b'{}' for p in q['us_files']})]:
                stack.enter_context(patch.object(wrapper,name,return_value=value))
            stack.enter_context(patch.object(wrapper.subprocess,'run',return_value=SimpleNamespace(
                returncode=0,stdout=canonical_bytes(r),stderr=b'')))
            stack.enter_context(patch.object(daily_us_owner,'run_us_mapping',side_effect=wrapper.run_us_mapping))
            return daily_us_owner.run_us_owner(q,'failure-regression')

    def test_original_failure_shapes_return_failed_receipt_through_wrapper(self):
        for case,status in [('missing','INPUT_MISSING'),('read_failed','FAILED'),
                            ('no_snapshot','CANNOT_CONFIRM'),('lineage','CANNOT_CONFIRM')]:
            with self.subTest(case=case):
                r,q=self.original_failure(case);daily=r['persisted_daily']
                self.assertEqual(daily['status'],status)
                if case == 'lineage':
                    self.assertEqual(daily['source_identity']['status'],'CANNOT_CONFIRM')
                    self.assertNotIn('payload_sha256',daily['source_identity'])
                else:self.assertIsNone(daily['source_identity'])
                try:out=self.evaluate(r,q);receipt=self.through_wrapper(r,q)
                except ValueError as error:self.fail('Legal original failure was rejected: '+str(error))
                for field in ('status','source_identity','coverage','matches','run_id','artifact_sha256'):
                    self.assertEqual(out[field],daily[field])
                self.assertEqual(receipt['status'],'FAILED')
                self.assertEqual(receipt['reason_codes'],['US_OWNER_'+status])
                self.assertTrue(receipt['readback_verified'])
                self.assertFalse(receipt['retry_safe_without_external_effect'])
                self.assertEqual(receipt['product_reference']['owner_status'],status)

    def test_failure_shape_does_not_relax_integrity_or_allow_success(self):
        for case in ('missing','lineage'):
            mutations=[lambda r:r['persisted_daily'].update(status='COMPLETED'),
                lambda r:r['persisted_daily'].update(source_status='READY'),
                lambda r:r['persisted_daily']['matches'].append({'session_date':'20261009'}),
                lambda r:r['persisted_daily']['coverage'].update(matched_us_symbol_count=0),
                lambda r:r['persisted_daily'].update(orders_sent=0),
                lambda r:r['persisted_daily'].update(run_id='invalid')]
            if case=='lineage':
                mutations += [lambda r:r['persisted_daily']['source_identity'].update(payload_path='wrong'),
                    lambda r:r['persisted_daily']['source_identity'].update(payload_sha256='a'*64),
                    lambda r:r['persisted_daily']['source_identity'].update(reason='invented')]
            for index,mutate in enumerate(mutations):
                with self.subTest(case=case,mutation=index):
                    r,q=self.original_failure(case);mutate(r);resign(r)
                    with self.assertRaises(ValueError):self.evaluate(r,q)
            r,q=self.original_failure(case);r['payload']['daily_run']['run_id']='9'*32
            with self.assertRaises(ValueError):self.evaluate(r,q)
            r,q=self.original_failure(case);r['persisted_daily']['artifact_sha256']='0'*64
            r['payload']['daily_run']=copy.deepcopy(r['persisted_daily'])
            with self.assertRaises(ValueError):self.evaluate(r,q)

    def test_wrapper_implementation_identity_comparison_is_canonical(self):
        r,q=fixture();r['implementation_identity']={'probe':0}
        # Isolate wrapper equality from the helper's independent SHA checks.
        with patch.object(scope,'describe_recovery_evaluation',return_value={}):
            with self.assertRaisesRegex(ValueError,'US_MAPPING_IMPLEMENTATION_CHANGED'):
                self.through_wrapper(r,q,identity={'probe':False})

    def test_wrapper_rejects_returned_capsule_pin_mismatch(self):
        r,q=fixture();r['source_capsule_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'US_MAPPING_SOURCE_CAPSULE_CHANGED'):
            self.through_wrapper(r,q)

    def test_recorded_second_comparison_does_not_claim_actual_start_before_cutoff(self):
        r,q=fixture();q['now']='2026-10-11T17:35:19.400000Z'
        r['requested_research_cutoff']=q['now'];r['persisted_daily']['research_cutoff']=q['now'];resign(r)
        out=self.evaluate(r,q)
        self.assertNotIn('generated_by_research_cutoff',out)
        self.assertIs(out['recorded_generated_at_lte_cutoff'],True)
        self.assertEqual(out['generated_at'],r['persisted_daily']['generated_at'])
        self.assertEqual(out['historical_availability'],'NOT_ESTABLISHED')
        self.assertIs(out['formal_eligible'],False)


if __name__=='__main__':unittest.main()

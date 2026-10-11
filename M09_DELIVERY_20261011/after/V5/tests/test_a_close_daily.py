"""M09 behavior tests; all constructed market rows are SYNTHETIC."""
import importlib.util
import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from v5_shadow.digests import canonical_bytes, sha256_json


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_bytes(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*') if p.is_file()}


def make_input(root, *, rows=None, data_kind='SYNTHETIC'):
    root.mkdir()
    if rows is None:
        rows = [dict(trade_date='20261009', ts_code=f'{i:06}.SZ', name=f'SYNTHETIC_{i}',
                     pct_chg=pct, amount=100000000.0, bar_close_pos=.8,
                     tdx_industry_code='I1' if i < 4 else 'I2',
                     tdx_industry_name='行业甲' if i < 4 else '行业乙')
                for i, pct in enumerate([10., 2., -10., -1., 0., 3.], 1)]
    (root/'panel.json').write_bytes(canonical_bytes(rows))
    (root/'panel.txt').write_text('panel.json\n')
    (root/'members.txt').write_text(''.join(row['ts_code']+'\n' for row in rows))
    provenance = dict(source_id='SYNTHETIC_PANEL', version='fixture-v1', status='READY',
                      authority_status='VERIFIED', coverage_rate=1.0,
                      captured_at='2026-10-09T15:40:00+08:00',
                      acquired_at='2026-10-09T15:40:00+08:00',
                      available_at='2026-10-09T15:41:00+08:00')
    (root/'receipt.json').write_bytes(canonical_bytes(dict(trade_date='20261009', **provenance)))
    manifest = dict(schema_version='v5.m09.input.v1', trade_date='20261009', data_kind=data_kind,
                    panel=dict(pointer_path='panel.txt', pointer_sha256=file_sha(root/'panel.txt'),
                               sha256=file_sha(root/'panel.json'), format='SYNTHETIC_JSON', row_count=len(rows)),
                    membership=dict(path='members.txt', sha256=file_sha(root/'members.txt'),
                                    scope='DECLARED_UNIVERSE', source_id='SYNTHETIC_MEMBERS', version='fixture-v1',
                                    captured_at='2026-10-09T15:40:00+08:00', available_at='2026-10-09T15:41:00+08:00'),
                    provenance=dict(provenance, receipt_path='receipt.json', receipt_sha256=file_sha(root/'receipt.json')),
                    evidence={})
    save_manifest(root, manifest)
    return manifest


def save_manifest(root, manifest):
    (root/'input.json').write_bytes(canonical_bytes(manifest))


class DailyBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.a_close_daily'), 'M09 daily is missing')
        from v5_shadow import a_close_daily
        self.daily = a_close_daily
        self.tmp = tempfile.TemporaryDirectory(prefix='m09-engineering-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base/'source'
        self.root = self.base/'m09'
        self.manifest = make_input(self.source)
        self.daily.initialize_a_close_root(self.root)

    def request(self, attempt='first', slot='16:05', **extra):
        return dict(schema_version='v5.m09.daily_request.v1', trade_date='20261009', slot=slot,
                    job_id='a_share_close_review_'+slot.replace(':',''), attempt_id=attempt,
                    execution_kind='ENGINEERING', triggered_at=datetime.now(timezone.utc).isoformat(),
                    source_root=str(self.source), input_manifest='input.json',
                    input_manifest_sha256=file_sha(self.source/'input.json'),
                    configuration_revision='m09-r1', **extra)

    def run_daily(self, attempt='first', slot='16:05', **extra):
        return self.daily.run_a_close_daily(self.root, self.request(attempt, slot, **extra))

    def diagnose(self):
        return self.daily.diagnose_a_close_input(self.source, 'input.json', file_sha(self.source/'input.json'), '20261009', '16:05')

    def edit_rows(self, mutate):
        rows=json.loads((self.source/'panel.json').read_bytes()); mutate(rows)
        (self.source/'panel.json').write_text(json.dumps(rows, ensure_ascii=False))
        self.manifest['panel']['sha256']=file_sha(self.source/'panel.json')
        save_manifest(self.source,self.manifest)

    def test_price_chain_writer_reader_preserves_native_fields(self):
        result=self.run_daily(); self.assertEqual(result['status'],'SUCCEEDED', result)
        out=self.daily.read_a_close_daily(self.root,'20261009'); review=out['review']; model=review['model_review']
        self.assertEqual(review['trade_date'],'20261009');self.assertEqual(model['review_date'],'20261009')
        self.assertEqual(model['run_id'],result['run_id'])
        self.assertEqual(sum(model['market_summary'][k] for k in ('up_count','down_count','flat_count')),6)
        self.assertEqual(sorted(x['probability'] for x in model['scenario_tree'].values()),[.12,.28,.60])
        self.assertEqual(model['semantic_model_call_count'],0);self.assertEqual(review['core_stocks'],[])
        self.assertIn('CANNOT_CONFIRM_TARGET_VIDEO_NOT_CONSUMED',review['cannot_confirm'])
        self.assertFalse(out['record']['strict_1500_pit_verified'])
        self.assertEqual(out['record']['business_status'],'PARTIAL')
        self.assertEqual(out['record']['evidence_status']['stage_evidence']['status'],'MISSING')
        self.assertEqual(out['identity']['record_sha256'],sha256_json(out['record']))
        self.assertEqual(out['identity']['canonical_review_sha256'],sha256_json(review))

    def test_two_slots_reuse_one_calculation_and_keep_two_receipts(self):
        first=self.run_daily();second=self.run_daily('later','17:10')
        self.assertEqual(first['status'],'SUCCEEDED',first);self.assertTrue(second['reused'],second)
        self.assertEqual(first['run_id'],second['run_id']);self.assertNotEqual(first['trigger_sha256'],second['trigger_sha256'])
        self.assertNotEqual(first['cutoff'],second['cutoff'])
        self.assertEqual(len(list((self.root/'attempts').glob('*/receipt.json'))),2)

    def test_exact_same_attempt_returns_receipt_without_producing(self):
        request=self.request(); first=self.daily.run_a_close_daily(self.root,request); before=tree_bytes(self.root)
        with patch.object(self.daily,'_build',side_effect=AssertionError('must not build')):
            second=self.daily.run_a_close_daily(self.root,request)
        self.assertEqual(first,second);self.assertEqual(before,tree_bytes(self.root))

    def test_two_concurrent_attempts_share_one_calculation(self):
        requests=[self.request('parallel-1'),self.request('parallel-2')]
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda r:self.daily.run_a_close_daily(self.root,r),requests))
        self.assertTrue(all(x['status']=='SUCCEEDED' for x in results),results)
        self.assertEqual(len({x['run_id'] for x in results}),1)
        self.assertEqual(sum(not x['reused'] for x in results),1)

    def test_configuration_change_creates_a_new_immutable_run(self):
        first=self.run_daily(); first_tree=tree_bytes(self.root/'runs'/first['run_id'])
        req=self.request('config','17:10');req['configuration_revision']='m09-r2'
        second=self.daily.run_a_close_daily(self.root,req)
        self.assertEqual(second['status'],'SUCCEEDED',second);self.assertNotEqual(first['run_id'],second['run_id'])
        self.assertEqual(first_tree,tree_bytes(self.root/'runs'/first['run_id']))

    def test_later_failure_keeps_previous_success(self):
        first=self.run_daily(); self.edit_rows(lambda rows:rows[0].update(amount=-1))
        failed=self.run_daily('bad','17:10');self.assertEqual(failed['status'],'FAILED',failed)
        current=self.daily.read_a_close_daily(self.root,'20261009')
        self.assertEqual(current['identity']['model_run_id'],first['run_id'])

    def test_source_changed_during_compute_never_publishes(self):
        original=self.daily._build
        def changed(*args,**kwargs):
            out=original(*args,**kwargs);(self.source/'panel.txt').write_text('changed.json\n');return out
        with patch.object(self.daily,'_build',side_effect=changed):result=self.run_daily()
        self.assertEqual(result['status'],'FAILED');self.assertIsNone(self.daily.read_a_close_daily(self.root,'20261009'))
        self.assertIn('CHANGED',result['reason'])

    def test_original_writer_failure_does_not_replace_old_run(self):
        first=self.run_daily();req=self.request('writerfail','17:10');req['configuration_revision']='break'
        with patch.object(self.daily,'_build',side_effect=OSError('injected payload write interruption')):
            fail=self.daily.run_a_close_daily(self.root,req)
        self.assertEqual(fail['status'],'FAILED');self.assertIn('payload write interruption',fail['reason'])
        self.assertEqual(self.daily.read_a_close_daily(self.root,'20261009')['identity']['model_run_id'],first['run_id'])

    def test_cas_conflict_keeps_served_generation(self):
        first=self.run_daily();result=self.run_daily('cas','17:10',expected_generation_sha256='0'*64)
        self.assertEqual(result['status'],'FAILED');self.assertIn('CAS',result['reason'])
        self.assertEqual(self.daily.read_a_close_daily(self.root,'20261009')['identity']['generation_sha256'],first['generation_sha256'])

    def test_rollback_preserves_both_runs_and_switches_only_this_date(self):
        first=self.run_daily();req=self.request('second','17:10');req['configuration_revision']='new'
        second=self.daily.run_a_close_daily(self.root,req)
        runs=tree_bytes(self.root/'runs')
        out=self.daily.rollback_a_close_daily(self.root,'20261009',first['generation_sha256'],second['generation_sha256'],'independent engineering rollback')
        self.assertEqual(out['status'],'ROLLED_BACK');self.assertEqual(runs,tree_bytes(self.root/'runs'))
        self.assertEqual(self.daily.read_a_close_daily(self.root,'20261009')['identity']['model_run_id'],first['run_id'])

    def test_read_is_exact_date_and_has_no_file_side_effects(self):
        self.run_daily();before=tree_bytes(self.root)
        for _ in range(3):
            self.daily.read_a_close_daily(self.root,'20261009')
            self.assertIsNone(self.daily.read_a_close_daily(self.root,'20261008'))
        self.assertEqual(before,tree_bytes(self.root))

    def test_tampered_payload_is_rejected_by_independent_reader(self):
        result=self.run_daily();p=self.root/'runs'/result['run_id']/'product/a_share_reviews/20261009.json'
        obj=json.loads(p.read_bytes());obj['market_regime']='tampered';p.write_bytes(canonical_bytes(obj))
        with self.assertRaises(ValueError):self.daily.read_a_close_daily(self.root,'20261009')

    def test_missing_field_rejected_before_algorithm(self):
        self.edit_rows(lambda rows:rows[0].pop('tdx_industry_name'))
        self.assertFalse(self.diagnose()['admitted'])

    def test_bad_numeric_types_and_quality_are_not_normalized(self):
        for field,value in [('amount',-1),('pct_chg','2.0'),('bar_close_pos',1.01),('bar_close_pos',None),('amount',True),('name',''),('tdx_industry_name','')]:
            with self.subTest(field=field,value=value):
                backup=(self.source/'panel.json').read_bytes()
                self.edit_rows(lambda rows:rows[0].__setitem__(field,value))
                self.assertFalse(self.diagnose()['admitted'])
                (self.source/'panel.json').write_bytes(backup)

    def test_nonfinite_numeric_rejected(self):
        for value in [float('nan'),float('inf'),float('-inf')]:
            with self.subTest(value=value):
                self.edit_rows(lambda rows:rows[0].update(pct_chg=value))
                self.assertFalse(self.diagnose()['admitted'])

    def test_wrong_date_type_or_day_rejected(self):
        for value in ['20261008',20261009]:
            with self.subTest(value=value):
                self.edit_rows(lambda rows:rows[0].update(trade_date=value))
                self.assertFalse(self.diagnose()['admitted'])

    def test_duplicate_and_invalid_suffix_rejected(self):
        self.edit_rows(lambda rows:rows[1].update(ts_code=rows[0]['ts_code']))
        self.assertFalse(self.diagnose()['admitted'])
        self.edit_rows(lambda rows:rows[1].update(ts_code='000002.HK'))
        self.assertFalse(self.diagnose()['admitted'])

    def test_missing_declared_members_rejected(self):
        (self.source/'members.txt').write_text('000001.SZ\n')
        self.manifest['membership']['sha256']=file_sha(self.source/'members.txt');save_manifest(self.source,self.manifest)
        self.assertFalse(self.diagnose()['admitted'])

    def test_top_subset_cannot_claim_full_market(self):
        self.manifest['membership']['scope']='FULL_MARKET';save_manifest(self.source,self.manifest)
        self.assertFalse(self.diagnose()['admitted'])

    def test_unverified_or_unknown_source_is_not_promoted(self):
        for key,value in [('available_at',None),('authority_status','REBUILD_REQUIRED'),('status','PARTIAL'),('coverage_rate',.8858620689655172)]:
            with self.subTest(key=key):
                self.manifest['provenance'][key]=value;save_manifest(self.source,self.manifest)
                self.assertFalse(self.diagnose()['admitted'])

    def test_source_receipt_time_disagreement_rejected(self):
        self.manifest['provenance']['available_at']='2026-10-09T15:42:00+08:00';save_manifest(self.source,self.manifest)
        self.assertFalse(self.diagnose()['admitted'])

    def test_late_or_naive_source_time_rejected(self):
        for value in ['2026-10-09T17:11:00+08:00','2026-10-09T15:41:00','2026-10-10T01:00:00+08:00']:
            with self.subTest(value=value):
                self.manifest['provenance']['available_at']=value;save_manifest(self.source,self.manifest)
                self.assertFalse(self.diagnose()['admitted'])

    def test_pointer_traversal_and_symlink_fail_closed(self):
        for value in ['../outside','/etc/passwd','missing.parquet']:
            with self.subTest(value=value):
                (self.source/'panel.txt').write_text(value)
                self.manifest['panel']['pointer_sha256']=file_sha(self.source/'panel.txt');save_manifest(self.source,self.manifest)
                self.assertFalse(self.diagnose()['admitted'])
        (self.source/'panel.txt').unlink();(self.source/'panel.txt').symlink_to(self.source/'panel.json')
        self.assertFalse(self.diagnose()['admitted'])

    def test_panel_digest_and_manifest_digest_checked(self):
        self.manifest['panel']['sha256']='0'*64;save_manifest(self.source,self.manifest)
        self.assertFalse(self.diagnose()['admitted'])
        req=self.request();req['input_manifest_sha256']='1'*64
        self.assertEqual(self.daily.run_a_close_daily(self.root,req)['status'],'FAILED')

    def test_nontrading_or_invalid_date_and_third_slot_rejected(self):
        for target,slot in [('bad','16:05'),('20261010','16:05'),('20261009','18:00')]:
            with self.subTest(target=target,slot=slot):
                req=self.request();req['trade_date']=target;req['slot']=slot
                with self.assertRaises(ValueError):self.daily.run_a_close_daily(self.root,req)

    def test_synthetic_json_cannot_be_presented_as_real(self):
        self.manifest['data_kind']='REAL';save_manifest(self.source,self.manifest)
        self.assertFalse(self.diagnose()['admitted'])

    def test_natural_trigger_cannot_claim_historical_day(self):
        req=self.request();req['execution_kind']='NATURAL'
        with self.assertRaises(ValueError):self.daily.run_a_close_daily(self.root,req)

    def test_unmarked_and_source_overlapping_roots_are_rejected(self):
        unmarked=self.base/'unmarked';unmarked.mkdir()
        with self.assertRaises(ValueError):self.daily.run_a_close_daily(unmarked,self.request())
        req=self.request();req['source_root']=str(self.root)
        with self.assertRaises(ValueError):self.daily.run_a_close_daily(self.root,req)

    def test_initialize_refuses_existing_nonempty_root(self):
        occupied=self.base/'occupied';occupied.mkdir();(occupied/'existing').write_text('keep')
        with self.assertRaises(ValueError):self.daily.initialize_a_close_root(occupied)
        self.assertEqual((occupied/'existing').read_text(),'keep')

    def add_evidence(self, role, available, payload=None):
        payload=payload or {'trade_date':'20261009','status':'READY','fixture':'SYNTHETIC'}
        p=self.source/(role+'.json');p.write_bytes(canonical_bytes(payload))
        self.manifest['evidence'][role]=dict(path=p.name,sha256=file_sha(p),trade_date='20261009',
                                            source_id='SYNTHETIC_'+role,version='v1',
                                            captured_at='2026-10-09T16:10:00+08:00',available_at=available)
        save_manifest(self.source,self.manifest)

    def test_late_stage_reference_only_enters_second_slot(self):
        self.add_evidence('stage_evidence','2026-10-09T16:11:00+08:00')
        first=self.run_daily();second=self.run_daily('late-stage','17:10')
        self.assertEqual(first['status'],'SUCCEEDED',first);self.assertEqual(second['status'],'SUCCEEDED',second)
        self.assertNotEqual(first['run_id'],second['run_id'])
        self.assertEqual(first['evidence_status']['stage_evidence']['status'],'TOO_LATE')
        self.assertEqual(second['evidence_status']['stage_evidence']['status'],'AVAILABLE')
        self.assertIn('CANNOT_CONFIRM_TARGET_VIDEO_NOT_CONSUMED',self.daily.read_a_close_daily(self.root,'20261009')['review']['cannot_confirm'])

    def test_post_1710_video_is_not_even_read_for_either_old_slot(self):
        self.add_evidence('video_capture','2026-10-09T17:11:00+08:00')
        (self.source/'video_capture.json').unlink()
        first=self.run_daily();second=self.run_daily('post1710','17:10')
        self.assertEqual(first['status'],'SUCCEEDED',first);self.assertEqual(second['status'],'SUCCEEDED',second)
        self.assertEqual(second['evidence_status']['video_capture']['status'],'TOO_LATE')

    def test_available_unknown_evidence_remains_partial(self):
        self.add_evidence('stockdict_pointer',None)
        self.assertEqual(self.run_daily()['evidence_status']['stockdict_pointer']['status'],'UNKNOWN')

    def test_real_worker_timeout_keeps_old_generation(self):
        first=self.run_daily();req=self.request('timeout','17:10');req['configuration_revision']='timeout'
        with patch.object(self.daily,'_WORKER_TIMEOUT',.001,create=True):
            result=self.daily.run_a_close_daily(self.root,req)
        self.assertEqual(result['status'],'FAILED',result);self.assertIn('TIMEOUT',result['reason'])
        self.assertEqual(self.daily.read_a_close_daily(self.root,'20261009')['identity']['generation_sha256'],first['generation_sha256'])

    def test_error_after_head_replace_restores_previous_generation(self):
        first=self.run_daily();req=self.request('publishfail','17:10');req['configuration_revision']='publishfail'
        original=self.daily._activate
        def fail_after(*args,**kwargs):
            original(*args,**kwargs);raise OSError('injected post-replace failure')
        with patch.object(self.daily,'_activate',side_effect=fail_after):
            result=self.daily.run_a_close_daily(self.root,req)
        self.assertEqual(result['status'],'FAILED',result)
        self.assertEqual(self.daily.read_a_close_daily(self.root,'20261009')['identity']['generation_sha256'],first['generation_sha256'])

    def test_final_receipt_write_failure_preserves_previous_success(self):
        first=self.run_daily();req=self.request('receiptfail','17:10');req['configuration_revision']='receiptfail'
        cls=type(self.daily.frozen.safe_root(self.root));original=cls.write_bytes
        def fail_receipt(obj,relative,raw,**kw):
            if relative.startswith('attempts/') and relative.endswith('/receipt.json') and b'"status":"SUCCEEDED"' in raw:
                raise OSError('injected trigger receipt failure')
            return original(obj,relative,raw,**kw)
        with patch.object(cls,'write_bytes',fail_receipt):
            result=self.daily.run_a_close_daily(self.root,req)
        self.assertEqual(result['status'],'FAILED',result)
        self.assertEqual(self.daily.read_a_close_daily(self.root,'20261009')['identity']['generation_sha256'],first['generation_sha256'])

    def test_actual_generation_connects_to_pure_existing_page_projection(self):
        result=self.run_daily();self.assertEqual(result['status'],'SUCCEEDED',result)
        from v5_shadow.a_close_daily_api import read_a_close_preview,merge_a_close_preview
        before=tree_bytes(self.root);preview=read_a_close_preview(self.root,'20261009')
        self.assertEqual(preview['m09_publication']['read_status'],'VERIFIED',preview)
        envelope={'trade_date':'20261009','market_reviews':{'A':{},'HK':{'stock':'HK_SENTINEL','bytes':'keep'}},'research_review':{'keep':True},'production_allowed':False}
        merged=merge_a_close_preview(envelope,preview)
        self.assertEqual(merged['market_reviews']['HK'],envelope['market_reviews']['HK'])
        self.assertEqual(merged['market_reviews']['A']['model_review']['run_id'],result['run_id'])
        self.assertEqual(tree_bytes(self.root),before)

    def test_latest_failed_attempt_is_separate_from_served_success(self):
        first=self.run_daily();self.edit_rows(lambda rows:rows[0].update(amount=-1))
        failed=self.run_daily('latest-failed','17:10')
        out=self.daily.read_a_close_daily(self.root,'20261009')
        self.assertEqual(out.get('latest_attempt',{}).get('status'),'FAILED')
        self.assertEqual(out['identity']['model_run_id'],first['run_id'])
        self.assertEqual(out['latest_attempt']['trigger_sha256'],failed['trigger_sha256'])

    def test_restarted_unfinished_attempt_is_unknown_and_new_attempt_can_recover(self):
        req=self.request();trigger={k:req[k] for k in ('trade_date','slot','job_id','attempt_id','execution_kind','triggered_at')}
        relative='attempts/'+sha256_json(trigger)+'/started.json'
        handle=self.daily.frozen.safe_root(self.root)
        handle.write_bytes(relative,canonical_bytes({'schema_version':'v5.m09.attempt_start.v1','trigger':trigger,'request_sha256':sha256_json(req),'started_at':datetime.now(timezone.utc).isoformat()}),require_absent=True)
        interrupted=self.daily.run_a_close_daily(self.root,req)
        self.assertEqual(interrupted['status'],'UNKNOWN')
        recovered=self.run_daily('new-recovery')
        self.assertEqual(recovered['status'],'SUCCEEDED',recovered)

    def test_worker_rejects_unbound_external_product_root(self):
        import subprocess,sys
        from v5_shadow import a_close_daily_worker as worker
        external=self.base/'external-product';external.mkdir()
        pointer=self.source/'external-pointer.txt';pointer.write_text(str(self.source/'panel.json')+'\n')
        request=dict(run_root=str(external),trade_date='20261009',panel_pointer=str(pointer),
                     rows=json.loads((self.source/'panel.json').read_bytes()),panel_sha256=file_sha(self.source/'panel.json'),
                     run_id='m09-'+'a'*32+'-'+'b'*12,context={})
        result=subprocess.run([sys.executable,'-I','-B',worker.__file__],input=canonical_bytes(request),capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(tree_bytes(external),{})
        self.assertIn(b'M09_WORKER_RUN_ROOT_NOT_BOUND',result.stderr)

    def test_hard_exit_after_head_never_serves_unreceipted_run(self):
        import subprocess,sys
        first=self.run_daily()
        request=self.request('hard-exit','17:10');request['configuration_revision']='crash'
        code="""import json,os,sys
from pathlib import Path
from v5_shadow import a_close_daily as d
request=json.load(sys.stdin)
original=d._activate
def stop_after(*args,**kwargs):
    original(*args,**kwargs)
    os._exit(77)
d._activate=stop_after
d.run_a_close_daily(Path(sys.argv[1]),request)
"""
        result=subprocess.run([sys.executable,'-B','-c',code,str(self.root)],input=canonical_bytes(request),capture_output=True)
        self.assertEqual(result.returncode,77,result.stderr)
        current=self.daily.read_a_close_daily(self.root,'20261009')
        self.assertEqual(current['identity']['generation_sha256'],first['generation_sha256'])
        self.assertEqual(current['publication_recovery']['status'],'UNCOMMITTED_HEAD_NOT_SERVED')
        self.assertEqual(self.daily.run_a_close_daily(self.root,request)['status'],'UNKNOWN')
        request['attempt_id']='after-hard-exit'
        self.assertEqual(self.daily.run_a_close_daily(self.root,request)['status'],'SUCCEEDED')

    def test_research_request_cannot_claim_a_future_slot(self):
        req=self.request();req['execution_kind']='MANUAL_RECOVERY'
        req['triggered_at']='2026-10-09T15:59:00+08:00'
        with patch.object(self.daily,'_now',return_value=datetime(2026,10,9,8,0,tzinfo=timezone.utc)):
            with self.assertRaisesRegex(ValueError,'FUTURE'):
                self.daily.run_a_close_daily(self.root,req)

    def test_missing_each_of_eight_required_columns_is_rejected(self):
        original=(self.source/'panel.json').read_bytes()
        for key in self.daily.COLUMNS:
            with self.subTest(column=key):
                (self.source/'panel.json').write_bytes(original)
                self.edit_rows(lambda rows:rows[0].pop(key))
                self.assertFalse(self.diagnose()['admitted'])

    def test_each_original_store_write_interruption_preserves_success(self):
        import pandas as pd
        first=self.run_daily()
        cls=type(self.daily.frozen.safe_root(self.root));write=cls.write_bytes
        for suffix in ('a_share_reviews/20261009.json','a_share_reviews/receipts/20261009.json','a_share_reviews/manifest.json'):
            with self.subTest(failed_file=suffix):
                def interrupted(obj,relative,raw,**kw):
                    result=write(obj,relative,raw,**kw)
                    if relative == suffix:
                        raise OSError('injected original store interruption:'+suffix)
                    return result
                def direct_build(run_root,target,pointer,rows,panel_sha,run_id,context):
                    return self.daily.frozen.build_from_admitted_panel(run_root,target,pointer,
                        pd.DataFrame(rows,columns=list(self.daily.COLUMNS)),panel_sha,run_id,context)
                req=self.request('write-'+str(len(suffix)),'17:10');req['configuration_revision']='write-'+suffix.replace('/','-')
                with patch.object(cls,'write_bytes',interrupted),patch.object(self.daily,'_build',side_effect=direct_build):
                    failed=self.daily.run_a_close_daily(self.root,req)
                self.assertEqual(failed['status'],'FAILED',failed)
                self.assertIn('injected original store interruption',failed['reason'])
                self.assertEqual(self.daily.read_a_close_daily(self.root,'20261009')['identity']['generation_sha256'],first['generation_sha256'])

    def test_independent_readback_mismatch_keeps_old_generation(self):
        first=self.run_daily();original=self.daily._build
        def mismatched(*args,**kwargs):
            result=original(*args,**kwargs);result['publication']['sha256']='0'*64;return result
        req=self.request('readback','17:10');req['configuration_revision']='readback'
        with patch.object(self.daily,'_build',side_effect=mismatched):
            failed=self.daily.run_a_close_daily(self.root,req)
        self.assertEqual(failed['status'],'FAILED');self.assertIn('READBACK_MISMATCH',failed['reason'])
        self.assertEqual(self.daily.read_a_close_daily(self.root,'20261009')['identity']['generation_sha256'],first['generation_sha256'])

    def test_rollback_activation_exception_restores_previous_head(self):
        first=self.run_daily();req=self.request('pre-rollback','17:10');req['configuration_revision']='pre-rollback'
        second=self.daily.run_a_close_daily(self.root,req);activate=self.daily._activate
        def fail_after(*args,**kwargs):
            activate(*args,**kwargs);raise OSError('injected rollback activation failure')
        with patch.object(self.daily,'_activate',side_effect=fail_after):
            with self.assertRaises(OSError):
                self.daily.rollback_a_close_daily(self.root,'20261009',first['generation_sha256'],second['generation_sha256'],'test rollback failure')
        self.assertEqual(self.daily.read_a_close_daily(self.root,'20261009')['identity']['generation_sha256'],second['generation_sha256'])

    def test_first_failed_attempt_remains_visible_without_fabricating_product(self):
        self.edit_rows(lambda rows:rows[0].update(amount=-1));self.run_daily()
        from v5_shadow.a_close_daily_api import read_a_close_preview
        preview=read_a_close_preview(self.root,'20261009')
        self.assertEqual(preview['m09_publication']['read_status'],'MISSING')
        self.assertEqual(preview['m09_publication']['latest_attempt_status'],'FAILED')
        self.assertIsNone(preview['m09_publication']['model_run_id'])


@unittest.skipUnless(importlib.util.find_spec('pyarrow') is not None,
                     'NOT_RUN: real pyarrow is not installed; no dependency/environment changes permitted')
class ParquetEngineeringTests(unittest.TestCase):
    """Real parquet decoder, explicitly SYNTHETIC data; never market acceptance."""
    def setUp(self):
        from v5_shadow import a_close_daily
        self.daily=a_close_daily
        self.tmp=tempfile.TemporaryDirectory(prefix='m09-parquet-engineering-');self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.source=self.base/'source';self.root=self.base/'m09'
        self.manifest=make_input(self.source)
        self.rows=json.loads((self.source/'panel.json').read_bytes())
        self.daily.initialize_a_close_root(self.root)

    def parquet(self,rows):
        import pyarrow as pa
        import pyarrow.parquet as pq
        panel=self.source/'panel.parquet'
        pq.write_table(pa.Table.from_pylist(rows),panel)
        (self.source/'panel.txt').write_text('panel.parquet\n')
        self.manifest['panel'].update(format='PARQUET',sha256=file_sha(panel),
            pointer_sha256=file_sha(self.source/'panel.txt'),row_count=len(rows))
        save_manifest(self.source,self.manifest)
        return panel

    def diagnose(self):
        return self.daily.diagnose_a_close_input(self.source,'input.json',file_sha(self.source/'input.json'),'20261009','16:05')

    def test_real_parquet_decoder_to_full_original_engineering_chain(self):
        panel=self.parquet(self.rows);original=panel.read_bytes()
        diagnostic=self.diagnose();self.assertTrue(diagnostic['admitted'],diagnostic)
        self.assertTrue(diagnostic['panel_decoded']);self.assertEqual(diagnostic['row_count'],6)
        request=dict(schema_version='v5.m09.daily_request.v1',trade_date='20261009',slot='16:05',
            job_id='synthetic_parquet_engineering',attempt_id='parquet',execution_kind='ENGINEERING',
            triggered_at=datetime.now(timezone.utc).isoformat(),source_root=str(self.source),input_manifest='input.json',
            input_manifest_sha256=file_sha(self.source/'input.json'),configuration_revision='parquet-engineering-v1')
        result=self.daily.run_a_close_daily(self.root,request);self.assertEqual(result['status'],'SUCCEEDED',result)
        committed=self.daily.read_a_close_daily(self.root,'20261009')
        self.assertEqual(committed['record']['data_kind'],'SYNTHETIC')
        self.assertEqual(committed['record']['execution_kind'],'ENGINEERING')
        self.assertEqual(sum(committed['review']['model_review']['market_summary'][k] for k in ('up_count','down_count','flat_count')),6)
        self.assertEqual(panel.read_bytes(),original)

    def test_parquet_missing_column_is_rejected_before_producer(self):
        for row in self.rows:row.pop('amount')
        self.parquet(self.rows);diagnostic=self.diagnose()
        self.assertFalse(diagnostic['admitted']);self.assertFalse(diagnostic['panel_decoded'])
        self.assertIsNone(diagnostic['row_count'])
        self.assertTrue(any('PANEL_FIELDS_MISSING' in x.get('detail','') for x in diagnostic['issues']))

    def test_parquet_numeric_string_schema_is_not_coerced(self):
        for row in self.rows:row['pct_chg']=str(row['pct_chg'])
        self.parquet(self.rows);diagnostic=self.diagnose()
        self.assertFalse(diagnostic['admitted'])
        self.assertTrue(any('PANEL_ARROW_TYPE:pct_chg' in x.get('detail','') for x in diagnostic['issues']))

    def test_parquet_missing_values_are_preserved_and_rejected(self):
        self.rows[0]['bar_close_pos']=None;self.rows[1]['name']='';self.rows[2]['tdx_industry_name']=''
        panel=self.parquet(self.rows);original=panel.read_bytes();diagnostic=self.diagnose()
        self.assertFalse(diagnostic['admitted']);self.assertTrue(diagnostic['panel_decoded'])
        codes={x['code'] for x in diagnostic['issues']}
        self.assertTrue({'PANEL_NUMBER_INVALID','PANEL_TEXT_MISSING'}<=codes)
        self.assertEqual(panel.read_bytes(),original)


class DailyEntryRedTests(unittest.TestCase):
    def test_complete_daily_entry_is_present(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.a_close_daily'),
                             'M09 daily producer/store/generation entry is missing')


if __name__ == '__main__':
    unittest.main()

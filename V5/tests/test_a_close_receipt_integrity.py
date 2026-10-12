"""Real original-owner fixtures: durable attempts, cold reads and PIT boundaries."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from test_a_close_daily import make_input, file_sha, tree_bytes
from v5_shadow import a_close_daily as daily
from v5_shadow.digests import canonical_bytes, sha256_json


class ReceiptIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='m09-receipts-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.root, self.source = self.base/'output', self.base/'source'
        make_input(self.source)
        daily.initialize_a_close_root(self.root)

    def request(self, attempt='first', slot='16:05'):
        return dict(schema_version='v5.m09.daily_request.v1', trade_date='20261009', slot=slot,
                    job_id='a_share_close_review_'+slot.replace(':',''), attempt_id=attempt,
                    execution_kind='ENGINEERING', triggered_at=datetime.now(timezone.utc).isoformat(),
                    source_root=str(self.source), input_manifest='input.json',
                    input_manifest_sha256=file_sha(self.source/'input.json'), configuration_revision='integrity-v1')

    def run_request(self, request):
        return daily.run_a_close_daily(self.root, request)

    def receipt_path(self, receipt):
        return self.root/'attempts'/receipt['trigger_sha256']/'receipt.json'

    def assert_rejected_unchanged(self, request):
        before = tree_bytes(self.root)
        with patch.object(daily, '_build', side_effect=AssertionError('must not produce')):
            with self.assertRaises((ValueError, OSError)):
                self.run_request(request)
        self.assertEqual(tree_bytes(self.root), before)

    def test_six_reported_failed_receipt_tampers_are_rejected(self):
        mutations = {
            'schema': lambda r:r.update(schema_version='forged'),
            'date': lambda r:r.update(trade_date='20261008'),
            'trigger': lambda r:r['trigger'].update(attempt_id='other'),
            'safety': lambda r:r['safety'].update(orders_sent=True),
            'success': lambda r:r.update(status='SUCCEEDED', run_id='m09-'+'a'*32+'-'+'b'*12,
                                          generation_sha256='0'*64),
            'missing': lambda r:r.pop('started_at'),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                request=self.request(name);request['input_manifest_sha256']='1'*64
                receipt=self.run_request(request);self.assertEqual(receipt['status'],'FAILED')
                mutate(receipt);self.receipt_path(receipt).write_bytes(canonical_bytes(receipt))
                self.assert_rejected_unchanged(request)

    def test_boolean_lookalikes_and_bad_attempt_times_are_rejected(self):
        mutations = {
            'bool': lambda r:r['safety'].update(orders_sent=0),
            'natural': lambda r:r.update(natural_verified=0),
            'slot': lambda r:r.update(slot='17:10'),
            'cutoff': lambda r:r.update(cutoff='2026-10-09T17:10:00+08:00'),
            'start': lambda r:r.update(started_at='2026-10-08T01:00:00+00:00'),
            'end': lambda r:r.update(finished_at='2026-10-08T01:00:00+00:00'),
            'status': lambda r:r.update(status='READY'),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                request=self.request(name);request['input_manifest_sha256']='1'*64
                receipt=self.run_request(request);mutate(receipt)
                self.receipt_path(receipt).write_bytes(canonical_bytes(receipt))
                self.assert_rejected_unchanged(request)

    def test_bad_started_record_is_rejected_before_attempt_head_write(self):
        request=self.request();request['input_manifest_sha256']='1'*64
        receipt=self.run_request(request);path=self.receipt_path(receipt).with_name('started.json')
        start=json.loads(path.read_bytes());start['started_at']='not-a-time';path.write_bytes(canonical_bytes(start))
        self.assert_rejected_unchanged(request)

    def test_historical_engineering_retry_keeps_actual_time_and_old_cutoff(self):
        request=self.request();first=self.run_request(request)
        self.assertEqual(first['status'],'SUCCEEDED',first)
        self.assertGreater(daily.aware(first['started_at']), daily.aware(first['cutoff']))
        self.assertEqual(self.run_request(request),first)
        source_times=json.loads((self.source/'input.json').read_bytes())['provenance']
        self.assertEqual(source_times['available_at'],'2026-10-09T15:41:00+08:00')

    def test_later_slot_reuse_can_reference_earlier_commit_trigger(self):
        first=self.run_request(self.request())
        request=self.request('later','17:10');later=self.run_request(request)
        self.assertEqual(later['status'],'SUCCEEDED',later)
        self.assertTrue(later['reused']);self.assertEqual(first['generation_sha256'],later['generation_sha256'])
        self.assertNotEqual(first['trigger_sha256'],later['trigger_sha256'])
        self.assertEqual(self.run_request(request),later)
        self.assertEqual(daily.read_a_close_latest_attempt(self.root,'20261009'),later)

    def test_missing_product_rejected_on_duplicate_and_cold_read(self):
        request=self.request();receipt=self.run_request(request)
        self.assertEqual(receipt['status'],'SUCCEEDED',receipt)
        (self.root/'runs'/receipt['run_id']/'product/a_share_reviews/20261009.json').rename(self.base/'retained-product.json')
        self.assert_rejected_unchanged(request)
        with self.assertRaises((ValueError,OSError)):daily.read_a_close_daily(self.root,'20261009')

    def test_forged_success_cannot_borrow_existing_committed_generation(self):
        first=self.run_request(self.request())
        request=self.request('failed','17:10');request['input_manifest_sha256']='1'*64
        failed=self.run_request(request);self.assertEqual(failed['status'],'FAILED')
        forged=copy.deepcopy(first)
        for key in ('trigger','trigger_sha256','request_sha256','started_at','finished_at','slot','cutoff'):
            forged[key]=failed[key]
        forged['reused']=True
        self.receipt_path(failed).write_bytes(canonical_bytes(forged))
        self.assert_rejected_unchanged(request)
        served=daily.read_a_close_daily(self.root,'20261009')
        self.assertEqual(served['identity']['generation_sha256'],first['generation_sha256'])
        self.assertEqual(served['latest_attempt']['status'],'UNKNOWN')

    def test_record_calculation_and_generation_mismatch_rejected(self):
        for field in ('run_id','record_sha256','calculation_sha256','generation_sha256'):
            with self.subTest(field=field):
                request=self.request(field);receipt=self.run_request(request)
                self.assertEqual(receipt['status'],'SUCCEEDED',receipt)
                original=self.receipt_path(receipt).read_bytes()
                receipt[field]='m09-'+'a'*32+'-'+'b'*12 if field=='run_id' else '0'*64
                self.receipt_path(receipt).write_bytes(canonical_bytes(receipt))
                self.assert_rejected_unchanged(request)
                self.receipt_path(receipt).write_bytes(original)

    def test_cold_reader_proves_real_original_store_and_preview_identity(self):
        request=self.request();receipt=self.run_request(request)
        self.assertEqual(receipt['status'],'SUCCEEDED',receipt)
        source=Path(daily.__file__).resolve().parents[1]
        code='''import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from v5_shadow.a_close_daily import read_a_close_daily
from v5_shadow.a_close_daily_api import read_a_close_preview
root=Path(sys.argv[2]);read=read_a_close_daily(root,'20261009');preview=read_a_close_preview(root,'20261009')
assert read['review']['model_review']['run_id']==preview['model_review']['run_id']
assert read['identity']['generation_sha256']==preview['m09_publication']['generation_sha256']
print(json.dumps(read['identity'],sort_keys=True))
'''
        before=tree_bytes(self.root)
        process=subprocess.run([sys.executable,'-I','-B','-c',code,str(source),str(self.root)],capture_output=True,text=True)
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertEqual(json.loads(process.stdout)['model_run_id'],receipt['run_id'])
        self.assertEqual(before,tree_bytes(self.root))

    def test_pre_upgrade_committing_receipt_keeps_verified_old_success(self):
        request=self.request();receipt=self.run_request(request)
        self.assertEqual(receipt['status'],'SUCCEEDED',receipt)
        archive=self.receipt_path(receipt).with_name('request.json')
        archive.rename(self.base/'retained-request.json')
        before=tree_bytes(self.root)
        served=daily.read_a_close_daily(self.root,'20261009')
        self.assertEqual(served['identity']['generation_sha256'],receipt['generation_sha256'])
        self.assertEqual(self.run_request(request),receipt)
        self.assertEqual(tree_bytes(self.root),before)

    def test_valid_failed_and_interrupted_unknown_are_idempotent(self):
        failed_request=self.request('failed');failed_request['input_manifest_sha256']='1'*64
        failed=self.run_request(failed_request);self.assertEqual(failed['status'],'FAILED')
        self.assertEqual(self.run_request(failed_request),failed)
        request=self.request('interrupted');trigger={k:request[k] for k in ('trade_date','slot','job_id','attempt_id','execution_kind','triggered_at')}
        handle=daily.frozen.safe_root(self.root);prefix='attempts/'+sha256_json(trigger)
        handle.write_bytes(prefix+'/started.json',canonical_bytes(dict(schema_version='v5.m09.attempt_start.v1',
            trigger=trigger,request_sha256=sha256_json(request),started_at=datetime.now(timezone.utc).isoformat())),require_absent=True)
        unknown=self.run_request(request);self.assertEqual(unknown['status'],'UNKNOWN')
        self.assertEqual(self.run_request(request),unknown)


if __name__=='__main__':unittest.main()

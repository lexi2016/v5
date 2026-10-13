"""Read-only delivery fixtures: original bytes, no collectors or model loading."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'src'))
from v5_shadow.digests import canonical_bytes, sha256_json


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class M06InputDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.adapter = importlib.import_module('v5_shadow.m06_input_delivery')
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        for name in ('store', 'assets', 'dispatch', 'lane', 'snapshots', 'deliveries'):
            (self.root / name).mkdir()
        self.config = dict(original_store_root=str(self.root/'store'),
            original_asset_root=str(self.root/'assets'),
            dispatch_receipt_root=str(self.root/'dispatch'),
            lane_receipt_root=str(self.root/'lane'),
            dispatch_receipt_relative='{scheduled_date}/1720.json',
            lane_receipt_relative='hk-{signal_date}.json', dispatch_slot='1720',
            snapshot_root=str(self.root/'snapshots'), delivery_root=str(self.root/'deliveries'))
        self.write('snapshots', '.v5-m06-input-snapshots', b'v5.m06-input-snapshots.v1\n')
        self.write('deliveries', '.v5-m06-input-deliveries', b'v5.m06-input-deliveries.v1\n')
        self.signal, self.target = '20261012', '20261013'
        self.now = datetime.fromisoformat('2026-10-12T17:35:00+08:00')
        self.safety = dict(production_allowed=False, buy_gate_updated=False, orders_sent=False)
        self.panel = dict(asset_schema_version='v3_shared_data.hk_0_2_panel_asset.v2',
            panel_relative='panels/panel/data.parquet', panel_sha256=digest(b'panel bytes'),
            panel_max_date=self.signal, research_only=True, **self.safety)
        self.write('assets', 'panel_latest.json', dict(manifest_relative='panels/panel/manifest.json'))
        self.write('assets', 'panels/panel/manifest.json', self.panel)
        self.write('assets', self.panel['panel_relative'], b'panel bytes')
        self.write('assets', 'model_latest.json', dict(manifest_relative='model/manifest.json'))
        self.write('assets', 'model/manifest.json', dict(bundle_relative='model/models.joblib',
            bundle_sha256=digest(b'never unpickle'), production_allowed=False))
        self.write('assets', 'model/models.joblib', b'never unpickle')
        self.write('assets', 'name_latest.json', dict(manifest_relative='names/manifest.json'))
        self.write('assets', 'names/manifest.json', dict(dictionary_relative='names/names.csv',
            dictionary_sha256=digest(b'code,name\nHK.00001,Example\n'), production_allowed=False))
        self.write('assets', 'names/names.csv', b'code,name\nHK.00001,Example\n')
        self.master_prefix = 'assets/hk_security_master/'
        self.master = dict(schema_version='v3_shared_data.hk_security_master_manifest.v1',
            trade_date=self.signal, run_id='master-run', captured_at='2026-10-12T17:30:00+08:00',
            artifact_relative='runs/master/artifact.csv', artifact_sha256=digest(b'master bytes'),
            later_snapshot_price_allowed=False, **self.safety)
        self.master_receipt = dict(schema_version='v3_shared_data.hk_security_master_receipt.v1',
            status='READY', trade_date=self.signal, run_id='master-run',
            manifest_sha256=sha256_json(self.master), artifact_sha256=self.master['artifact_sha256'],
            **self.safety)
        self.write('store', self.master_prefix+'latest.json', dict(
            schema_version='v3_shared_data.hk_security_master_latest.v1', entries={self.signal:dict(
                run_id='master-run', manifest_relative='runs/master/manifest.json',
                receipt_relative='runs/master/receipt.json')}))
        self.write('store', self.master_prefix+'runs/master/manifest.json', self.master)
        self.write('store', self.master_prefix+'runs/master/receipt.json', self.master_receipt)
        self.write('store', self.master_prefix+'runs/master/artifact.csv', b'master bytes')

    def write(self, family, relative, value):
        path = self.root/family/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else canonical_bytes(value))
        return path

    def capture(self):
        return self.adapter._capture_inputs(self.config, self.signal, self.target)

    def test_capture_requires_original_asset_payload_hashes(self):
        capture = self.capture()
        self.assertEqual(capture['files'][self.panel['panel_relative']], digest(b'panel bytes'))
        self.assertEqual(len(capture['source_files']), 4)
        self.write('assets', 'model/models.joblib', b'corrupt')
        with self.assertRaisesRegex(ValueError, 'HASH'):
            self.capture()

    def test_master_requires_exact_signal_date_and_ready_hash_chain(self):
        self.master_receipt['trade_date'] = self.target
        self.write('store', self.master_prefix+'runs/master/receipt.json', self.master_receipt)
        with self.assertRaisesRegex(ValueError, 'MASTER'):
            self.capture()

    def test_master_receipt_canonical_manifest_hash_is_verified(self):
        self.master_receipt['manifest_sha256'] = '0'*64
        self.write('store', self.master_prefix+'runs/master/receipt.json', self.master_receipt)
        with self.assertRaisesRegex(ValueError, 'HASH'):
            self.capture()

    def test_optional_receipts_and_names_are_included_without_execution(self):
        self.write('assets', 'model/receipt.json', dict(status='READY', **self.safety))
        capture = self.capture()
        self.assertIn('model/receipt.json', capture['files'])
        self.assertIn('names/names.csv', capture['files'])
        self.assertNotIn('unrelated-private-file', capture['files'])

    def test_absent_source_pool_keeps_existing_latest_original_bytes(self):
        raw = b'{"entries": {}}\n'
        self.write('store', 'latest.json', raw)
        capture = self.capture()
        self.assertEqual(capture['source_files']['latest.json'], digest(raw))

    def test_corrupt_existing_pool_never_becomes_missing(self):
        self.write('store', 'latest.json', dict(entries={self.target+'/HK_CONNECT_D1_TOP100_0_2':{}}))
        with self.assertRaises((ValueError, KeyError)):
            self.capture()

    def test_panel_max_date_and_panel_pointer_identity_are_required(self):
        self.panel['panel_max_date'] = '20261009'
        self.write('assets', 'panels/panel/manifest.json', self.panel)
        with self.assertRaisesRegex(ValueError, 'PANEL'):
            self.capture()

    def test_relative_escape_and_noncanonical_paths_are_rejected(self):
        for relative in ('../secret', '/tmp/secret', 'panels/../secret', 'panels//secret', './secret'):
            with self.subTest(relative=relative):
                self.write('assets', 'panel_latest.json', dict(manifest_relative=relative))
                with self.assertRaisesRegex(ValueError, 'PATH'):
                    self.capture()

    def test_symlink_payload_and_symlink_ancestor_are_rejected(self):
        path = self.root/'assets'/self.panel['panel_relative']
        path.unlink()
        path.symlink_to(self.root/'store'/self.master_prefix/'runs/master/artifact.csv')
        with self.assertRaises((ValueError, OSError)):
            self.capture()

    def test_fifo_is_rejected_without_blocking(self):
        path = self.root/'assets'/self.panel['panel_relative']
        path.unlink()
        os.mkfifo(path)
        with self.assertRaisesRegex(ValueError, 'TYPE'):
            self.capture()

    def test_source_mutation_after_capture_is_detected_even_same_bytes_replaced(self):
        capture = self.capture()
        path = self.root/'assets'/self.panel['panel_relative']
        replacement = path.with_name('replacement')
        replacement.write_bytes(path.read_bytes())
        replacement.replace(path)
        with self.assertRaisesRegex(ValueError, 'CHANGED'):
            self.adapter._recheck_capture(capture)

    def test_missing_optional_pointer_creation_during_capture_is_detected(self):
        path = self.root/'assets'/'name_latest.json'
        raw = path.read_bytes()
        path.unlink()
        capture = self.capture()
        path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'CHANGED'):
            self.adapter._recheck_capture(capture)


    def upstream(self):
        self.lane = dict(schema_version='v3.macos.research_panel_receipt.v1',
            lane='HK', target_date=self.signal, status='READY', **self.safety,
            authority=dict(status='READY', through_date=self.signal, target_date=self.signal,
                           manifest_relative='panels/panel/manifest.json',
                           panel_sha256=self.panel['panel_sha256'], **self.safety))
        lane_raw = canonical_bytes(self.lane) + b'\n'
        self.write('lane', 'hk-'+self.signal+'.json', lane_raw)
        self.envelope = dict(schema_version='v3.macos.research_panel_authority_envelope.v1',
            lane='HK', target_date=self.signal, overall_status='READY', status='READY',
            lanes=dict(HK=dict(status='READY', receipt_bytes=len(lane_raw), receipt_sha256=digest(lane_raw))),
            **self.safety)
        self.dispatch = dict(schema_version='v3_5.dispatch.v1', mode='LIVE', status='SUCCEEDED',
            business_date=self.signal, scheduled_date=self.signal, slot='1720',
            finished_at='2026-10-12T17:25:00+08:00',
            succeeded_workload_ids=['research_panel_daily_hk'],
            invoked_workload_ids=['research_panel_daily_hk'],
            resolved_dates=dict(research_panel_daily_hk=dict(scheduled_date=self.signal,
                signal_date=self.signal, target_date=self.signal)),
            workload_results=[dict(workload_id='research_panel_daily_hk', status='SUCCEEDED',
                exit_code=0, _authoritative_payload=self.envelope, source_result=self.envelope)])
        self.write_dispatch()

    def write_dispatch(self):
        return self.write('dispatch', self.signal+'/1720.json', self.dispatch)

    def prepare(self, **kwargs):
        return self.adapter.prepare_input_delivery(self.config, self.signal, self.target, now=self.now, **kwargs)

    def test_new_delivery_copies_original_bytes_and_records_real_completion(self):
        self.upstream()
        completed = self.now.replace(minute=36)
        with patch.object(self.adapter, '_utc_now', return_value=completed):
            result = self.prepare()
        self.assertEqual(result['status'], 'READY')
        self.assertEqual(result['delivery']['completed_at'], completed.isoformat())
        self.assertEqual(result['delivery']['eligibility_source_date'], self.signal)
        self.assertEqual(set(result['delivery']), {'schema_version','status','target_date','signal_date',
            'eligibility_source_date','completed_at','files','source_files'})
        self.assertEqual(result['delivery_sha256'], digest((self.root/'deliveries'/(self.target+'.json')).read_bytes()))
        for family, field, root_key in [('assets','files','asset_root'),('store','source_files','store_root')]:
            for relative in result['delivery'][field]:
                self.assertEqual((Path(result[root_key])/relative).read_bytes(), (self.root/family/relative).read_bytes())
        seal = json.loads((Path(result['store_root']).parent/'seal.json').read_bytes())
        self.assertEqual(seal['upstream_evidence']['panel_finished_at'], self.dispatch['finished_at'])
        self.assertNotEqual(seal['upstream_evidence']['panel_finished_at'], result['delivery']['completed_at'])
        self.assertFalse(seal['natural_verified'])

    def test_sealed_delivery_reuses_without_refreshing_time_or_live_inventory(self):
        self.upstream()
        with patch.object(self.adapter, '_utc_now', return_value=self.now):
            first = self.prepare()
        self.write('assets', self.panel['panel_relative'], b'next live revision')
        with patch.object(self.adapter, '_utc_now', side_effect=AssertionError('reuse must not mint time')):
            second = self.prepare()
        self.assertEqual(second['status'], 'REUSED_M06_INPUT_DELIVERY')
        for key in ('delivery','delivery_sha256','store_root','asset_root','seal_sha256'):
            self.assertEqual(second[key], first[key])

    def test_sealed_snapshot_tampering_blocks_without_rebuilding(self):
        self.upstream()
        with patch.object(self.adapter, '_utc_now', return_value=self.now):
            first = self.prepare()
        (Path(first['asset_root'])/self.panel['panel_relative']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'SNAPSHOT'):
            self.prepare()
        self.assertEqual(json.loads((self.root/'deliveries'/(self.target+'.json')).read_bytes()), first['delivery'])

    def test_missing_upstream_is_waiting_and_does_not_publish(self):
        self.assertEqual(self.prepare()['status'], 'WAITING_M06_INPUT_DELIVERY')
        self.assertFalse((self.root/'deliveries'/(self.target+'.json')).exists())

    def test_lane_raw_bytes_mismatch_blocks_before_parsing(self):
        self.upstream()
        self.write('lane', 'hk-'+self.signal+'.json', canonical_bytes(self.lane))
        with self.assertRaisesRegex(ValueError, 'LANE.*HASH'):
            self.prepare()

    def test_contradictory_authoritative_payload_is_rejected(self):
        self.upstream()
        self.dispatch['workload_results'][0]['source_result'] = dict(self.envelope, target_date=self.target)
        self.write_dispatch()
        with self.assertRaisesRegex(ValueError, 'ENVELOPE'):
            self.prepare()

    def test_wrong_dispatch_dates_workload_status_and_duplicate_rows_rejected(self):
        for key, value in [('business_date',self.target),('mode','DRY_RUN'),('status','FAILED'),
                           ('succeeded_workload_ids',[]),('invoked_workload_ids',[])]:
            with self.subTest(key=key):
                self.upstream()
                self.dispatch[key] = value
                self.write_dispatch()
                with self.assertRaisesRegex(ValueError, 'DISPATCH'):
                    self.prepare()
        self.upstream()
        self.dispatch['workload_results'] *= 2
        self.write_dispatch()
        with self.assertRaisesRegex(ValueError, 'DISPATCH'):
            self.prepare()

    def test_roots_cannot_overlap_originals_or_each_other(self):
        self.upstream()
        for key, value in [('snapshot_root',str(self.root/'assets')),
                           ('delivery_root',str(self.root/'snapshots'))]:
            with self.subTest(key=key):
                changed = dict(self.config, **{key:value})
                with self.assertRaisesRegex(ValueError, 'OVERLAP'):
                    self.adapter.prepare_input_delivery(changed, self.signal, self.target, now=self.now)

    def test_symlink_output_parent_is_rejected(self):
        self.upstream()
        alias = self.root/'alias'
        alias.symlink_to(self.root/'snapshots', target_is_directory=True)
        self.config['snapshot_root'] = str(alias)
        with self.assertRaises((OSError, ValueError)):
            self.prepare()

    def test_clock_cannot_backdate_to_panel_or_before_completed_copy(self):
        self.upstream()
        with patch.object(self.adapter, '_utc_now', return_value=self.now.replace(minute=24)):
            with self.assertRaisesRegex(ValueError, 'CLOCK'):
                self.prepare()
        self.assertFalse((self.root/'deliveries'/(self.target+'.json')).exists())

    def test_live_mutation_during_copy_prevents_seal(self):
        self.upstream()
        original = self.adapter._copy_capture
        def mutate(*args):
            original(*args)
            self.write('assets', 'panel_latest.json', dict(manifest_relative='different.json'))
        with patch.object(self.adapter, '_copy_capture', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'CHANGED'):
                self.prepare()
        self.assertFalse((self.root/'deliveries'/(self.target+'.json')).exists())

    def test_missing_name_creation_during_copy_prevents_seal(self):
        self.upstream()
        path = self.root/'assets'/'name_latest.json'
        raw = path.read_bytes()
        path.unlink()
        original = self.adapter._copy_capture
        def mutate(*args):
            original(*args)
            path.write_bytes(raw)
        with patch.object(self.adapter, '_copy_capture', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'CHANGED'):
                self.prepare()



    def test_completion_clock_is_observed_only_after_copied_bytes_exist(self):
        self.upstream()
        def completion():
            payloads = list((self.root/'snapshots').glob('*/assets/model/models.joblib'))
            self.assertEqual(len(payloads), 1)
            self.assertEqual(payloads[0].read_bytes(), b'never unpickle')
            return self.now
        with patch.object(self.adapter, '_utc_now', side_effect=completion):
            self.assertEqual(self.prepare()['status'], 'READY')

    def test_concurrent_ticks_share_one_sealed_delivery(self):
        self.upstream()
        with patch.object(self.adapter, '_utc_now', return_value=self.now):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: self.prepare(), range(2)))
        self.assertEqual(sorted(row['status'] for row in results), ['READY','REUSED_M06_INPUT_DELIVERY'])
        self.assertEqual(results[0]['delivery_sha256'], results[1]['delivery_sha256'])
        self.assertEqual(results[0]['seal_sha256'], results[1]['seal_sha256'])

    def test_recover_delivery_write_after_seal_without_new_clock(self):
        self.upstream()
        original = self.adapter._write
        with patch.object(self.adapter, '_write', side_effect=OSError('synthetic interruption')):
            with patch.object(self.adapter, '_utc_now', return_value=self.now):
                with self.assertRaises(OSError):
                    self.prepare()
        with patch.object(self.adapter, '_utc_now', side_effect=AssertionError('no new completion')):
            recovered = self.prepare()
        self.assertEqual(recovered['status'], 'REUSED_M06_INPUT_DELIVERY')
        self.assertEqual(recovered['delivery']['completed_at'], self.now.isoformat())

    def test_observed_future_master_cannot_be_given_past_completion(self):
        self.upstream()
        self.master['captured_at'] = '2026-10-12T18:30:00+08:00'
        self.master_receipt['manifest_sha256'] = sha256_json(self.master)
        self.write('store', self.master_prefix+'runs/master/manifest.json', self.master)
        self.write('store', self.master_prefix+'runs/master/receipt.json', self.master_receipt)
        with patch.object(self.adapter, '_utc_now', return_value=self.now):
            with self.assertRaisesRegex(ValueError, 'CLOCK'):
                self.prepare()

    def test_root_markers_are_required_before_writes(self):
        self.upstream()
        self.write('snapshots', '.v5-m06-input-snapshots', b'wrong')
        with self.assertRaisesRegex(ValueError, 'MARKER'):
            self.prepare()
        self.assertFalse((self.root/'deliveries'/(self.target+'.json')).exists())

    def test_relative_template_cannot_access_attributes_or_parent_paths(self):
        self.upstream()
        for template in ('../{scheduled_date}.json', '{scheduled_date.__class__}.json', '{target_date!r}.json'):
            with self.subTest(template=template):
                self.config['dispatch_receipt_relative'] = template
                with self.assertRaisesRegex(ValueError, 'PATH'):
                    self.prepare()



    def test_duplicate_json_keys_are_not_accepted_as_original_metadata(self):
        self.write('assets', 'panel_latest.json', b'{"manifest_relative":"ignored", "manifest_relative":"panels/panel/manifest.json"}')
        with self.assertRaisesRegex(ValueError, 'DUPLICATE'):
            self.capture()

    def test_file_size_bound_applies_to_binary_payloads(self):
        with patch.object(self.adapter, 'MAX_FILE_BYTES', 4):
            with self.assertRaisesRegex(ValueError, 'SIZE'):
                self.capture()

    def test_same_byte_replacement_of_original_root_is_rejected(self):
        capture = self.capture()
        old = self.root/'old-assets'
        (self.root/'assets').rename(old)
        (self.root/'assets').mkdir()
        # Keep file inodes/bytes but replace the configured source root inode.
        for path in old.iterdir():
            path.rename(self.root/'assets'/path.name)
        with self.assertRaisesRegex(ValueError, 'CHANGED'):
            self.adapter._recheck_capture(capture)



    def test_changed_snapshot_input_identity_is_rejected(self):
        self.upstream()
        with patch.object(self.adapter, '_utc_now', return_value=self.now):
            first = self.prepare()
        seal_path = Path(first['store_root']).parent/'seal.json'
        seal = json.loads(seal_path.read_bytes())
        seal['input_sha256'] = '0'*64
        seal_path.write_bytes(canonical_bytes(seal))
        pointer_path = self.root/'snapshots'/(self.target+'.json')
        pointer = json.loads(pointer_path.read_bytes())
        pointer['seal_sha256'] = digest(seal_path.read_bytes())
        pointer_path.write_bytes(canonical_bytes(pointer))
        with self.assertRaisesRegex(ValueError, 'IDENTITY'):
            self.prepare()



    def test_asset_symlink_directory_cannot_escape_root(self):
        original = self.root/'assets'/'panels'
        original.rename(self.root/'moved-panels')
        original.symlink_to(self.root/'moved-panels', target_is_directory=True)
        with self.assertRaises((OSError, ValueError)):
            self.capture()

    def test_original_payload_bytes_are_unchanged_by_successful_delivery(self):
        self.upstream()
        before = {(family,str(p.relative_to(self.root/family))):p.read_bytes()
                  for family in ('store','assets','dispatch','lane')
                  for p in (self.root/family).rglob('*') if p.is_file()}
        with patch.object(self.adapter, '_utc_now', return_value=self.now):
            self.prepare()
        after = {(family,str(p.relative_to(self.root/family))):p.read_bytes()
                 for family in ('store','assets','dispatch','lane')
                 for p in (self.root/family).rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_lane_safety_flag_cannot_be_true(self):
        self.upstream()
        self.lane['orders_sent'] = True
        lane_raw = canonical_bytes(self.lane)
        self.write('lane', 'hk-'+self.signal+'.json', lane_raw)
        self.envelope['lanes']['HK'].update(receipt_bytes=len(lane_raw), receipt_sha256=digest(lane_raw))
        self.write_dispatch()
        with self.assertRaisesRegex(ValueError, 'SAFETY'):
            self.prepare()

    def test_envelope_cannot_bind_different_panel_manifest(self):
        self.upstream()
        self.lane['authority']['manifest_relative'] = 'panels/different/manifest.json'
        lane_raw = canonical_bytes(self.lane)
        self.write('lane', 'hk-'+self.signal+'.json', lane_raw)
        self.envelope['lanes']['HK'].update(receipt_bytes=len(lane_raw), receipt_sha256=digest(lane_raw))
        self.write_dispatch()
        with self.assertRaisesRegex(ValueError, 'PANEL'):
            self.prepare()



    def test_copy_rejects_symlink_destination_without_touching_original(self):
        capture = self.capture()
        target = self.root/'isolated'
        (target/'assets'/'model').mkdir(parents=True)
        original = self.root/'assets'/'model'/'models.joblib'
        (target/'assets'/'model'/'models.joblib').symlink_to(original)
        with self.assertRaises((OSError, ValueError)):
            self.adapter._copy_capture(capture, target)
        self.assertEqual(original.read_bytes(), b'never unpickle')

    def test_copy_rejects_changed_source_bytes(self):
        capture = self.capture()
        target = self.root/'isolated'
        target.mkdir()
        self.write('assets', 'model/models.joblib', b'changed source')
        with self.assertRaisesRegex(ValueError, 'CHANGED'):
            self.adapter._copy_capture(capture, target)
        self.assertFalse((target/'seal.json').exists())



    def test_locked_output_root_replacement_is_detected(self):
        with self.assertRaisesRegex(ValueError, 'ROOT_CHANGED'):
            with self.adapter._locked_roots(self.config):
                (self.root/'snapshots').rename(self.root/'old-snapshots')
                (self.root/'snapshots').mkdir()
                self.write('snapshots', '.v5-m06-input-snapshots', b'v5.m06-input-snapshots.v1\n')



    def test_dispatch_finish_requires_signal_day_and_not_before_slot(self):
        for stamp in ('2026-10-12T17:19:59+08:00', '2026-10-11T23:59:00+08:00',
                      '2026-10-13T00:01:00+08:00'):
            with self.subTest(stamp=stamp):
                self.upstream()
                self.dispatch['finished_at'] = stamp
                self.write_dispatch()
                with self.assertRaisesRegex(ValueError, 'DISPATCH'):
                    self.adapter._capture_upstream(self.capture(), self.config, self.signal, self.target)

    def test_master_capture_requires_exact_signal_day(self):
        self.master['captured_at'] = '2026-10-09T17:30:00+08:00'
        self.master_receipt['manifest_sha256'] = sha256_json(self.master)
        self.write('store', self.master_prefix+'runs/master/manifest.json', self.master)
        self.write('store', self.master_prefix+'runs/master/receipt.json', self.master_receipt)
        with self.assertRaisesRegex(ValueError, 'MASTER'):
            self.capture()



    def test_missing_signal_master_entry_waits_without_publishing(self):
        self.upstream()
        self.write('store', self.master_prefix+'latest.json', dict(
            schema_version='v3_shared_data.hk_security_master_latest.v1', entries={}))
        self.assertEqual(self.prepare()['status'], 'WAITING_M06_INPUT_DELIVERY')
        self.assertFalse((self.root/'deliveries'/(self.target+'.json')).exists())
        self.assertFalse((self.root/'snapshots'/(self.target+'.json')).exists())

    def test_corrupt_master_entries_and_existing_entry_do_not_wait(self):
        self.upstream()
        schema = 'v3_shared_data.hk_security_master_latest.v1'
        cases = [dict(schema_version=schema), dict(schema_version=schema, entries=None),
                 dict(schema_version=schema, entries=[]),
                 dict(schema_version=schema, entries={self.signal:{}})]
        for latest in cases:
            with self.subTest(latest=latest):
                self.write('store', self.master_prefix+'latest.json', latest)
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    self.prepare()
                self.assertFalse((self.root/'deliveries'/(self.target+'.json')).exists())


if __name__ == '__main__':
    unittest.main()

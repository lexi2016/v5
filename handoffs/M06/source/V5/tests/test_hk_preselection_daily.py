"""Daily orchestration uses real frozen source, never injected owner callbacks."""
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from fixtures.hk_preselection_verified_factory import create_verified_fixture

class DailyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        self.request=create_verified_fixture(self.root/'input')
        self.assets=self.root/'assets';self.assets.mkdir()
        self.output=self.root/'output';self.output.mkdir();(self.output/'.v5-shadow-root').write_text('v5.shadow-root.v1\n')
    def args(self):
        return dict(store_root=str(self.root/'input'),asset_root=str(self.assets),private_root=str(self.output),signal_date='20261007',target_date='20261008',eligibility_source_date='20260930',cutoff='2026-10-08T09:20:00+08:00',files={},execution_mode='RECORDED_INPUT_REPLAY')
    def run_daily(self,**updates):
        from v5_shadow.hk_preselection_daily import produce_hk02_daily
        args=self.args();args.update(updates);return produce_hk02_daily(**args)
    def test_module_implemented(self):
        self.assertTrue((Path(__file__).parents[1]/'src/v5_shadow/hk_preselection_daily.py').is_file(),'daily entrypoint must exist')
    def test_exact_existing_pool_committed_and_reused(self):
        first=self.run_daily();second=self.run_daily()
        self.assertEqual(first['status'],'SUCCEEDED');self.assertEqual(first['committed_reference'],second['committed_reference'])
        self.assertFalse(first['producer_receipt']['model_weights_reverified'])
        self.assertEqual(first['producer_receipt']['production_method'],'EXISTING_VERIFIED_POOL')
        self.assertFalse(first['natural_verified'])
        self.assertEqual(first['row_count'],100)
    def test_bad_existing_pool_no_generation_fallback_or_old_overwrite(self):
        good=self.run_daily();before={str(p.relative_to(self.output)):p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        p=Path(self.request['input_root'])/self.request['expected_source']['artifact_relative'];p.write_bytes(p.read_bytes()+b'bad')
        with self.assertRaises(ValueError):self.run_daily()
        after={str(p.relative_to(self.output)):p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
    def test_missing_pool_reports_actual_runtime_or_asset_blocker(self):
        (self.root/'input/latest.json').write_text('{"entries":{}}')
        with self.assertRaisesRegex(ValueError,'M06_PRODUCER_RUNTIME_MISMATCH|FileNotFoundError|HK 0.2'):
            self.run_daily()
        self.assertEqual([p.name for p in self.output.iterdir()],['.v5-shadow-root'])
    def test_marker_overlap_and_bad_kind_rejected(self):
        for changes in ({'private_root':str(self.root/'unbound')},{'private_root':str(self.root/'input')},{'execution_mode':'SYNTHETIC'}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):self.run_daily(**changes)
    def test_actual_after_cutoff_source_rejected(self):
        with self.assertRaises(ValueError):self.run_daily(cutoff='2026-10-08T07:00:00+08:00')
    def test_date_calendar_rejection_before_publication(self):
        with self.assertRaises(ValueError):self.run_daily(signal_date='20260930')
    def test_bad_calendar_precedes_missing_pool_runtime_gate(self):
        (self.root/'input/latest.json').write_text('{"entries":{}}')
        with self.assertRaisesRegex(ValueError,'HK_SIGNAL_NOT_PREVIOUS_SECURITIES_SESSION'):
            self.run_daily(signal_date='20260930')
        self.assertEqual([p.name for p in self.output.iterdir()],['.v5-shadow-root'])

    def test_only_explicit_recorded_replay_allows_missing_assets(self):
        for mode in ('NATURAL','MANUAL_RECOVERY'):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError,'M06_REQUIRED_ASSET_FILE_MISSING'):
                    self.run_daily(execution_mode=mode)
        result=self.run_daily()
        self.assertEqual(result['producer_receipt']['asset_binding_status'],'NOT_REVERIFIED_RECORDED_INPUT_ONLY')
        self.assertFalse(result['producer_receipt']['model_weights_reverified'])

    def test_daily_identity_binds_observed_runtime_dependencies(self):
        from v5_shadow import hk_preselection_daily as daily
        from v5_shadow import hk_preselection_verified as verified
        from v5_shadow.digests import sha256_json
        result=self.run_daily()
        actual=dict(source_descriptor=verified._production_sources(),runtime_dependencies=daily._runtime_dependencies())
        self.assertEqual(result['computation_identity']['dependency_sha256'],sha256_json(actual))
        self.assertEqual(result['producer_receipt']['dependency_manifest'],actual)
        self.assertEqual(result['producer_receipt']['runtime_dependencies'],actual['runtime_dependencies'])

    def test_reused_success_rechecks_live_inputs_after_exact_readback(self):
        from v5_shadow import hk_preselection_publication as publication
        self.run_daily()
        real=publication.read_verified_hk_preselection_reference
        source=Path(self.request['input_root'])/self.request['expected_source']['artifact_relative']
        def changed_after_readback(*args,**kwargs):
            result=real(*args,**kwargs)
            source.write_bytes(source.read_bytes()+b'changed-after-cold-readback')
            return result
        with patch.object(publication,'read_verified_hk_preselection_reference',side_effect=changed_after_readback):
            with self.assertRaisesRegex(ValueError,'M06_INPUT_CHANGED'):
                self.run_daily()

    def test_existing_receipt_preserves_actual_low_level_verification(self):
        from v5_shadow.hk_preselection_verified import run_verified_hk_preselection
        actual=run_verified_hk_preselection(self.request)
        self.assertIn('source_verification',actual)
        result=self.run_daily()
        self.assertEqual(result['producer_receipt']['original_result'],actual['source_verification'])

    def test_asset_file_sha_cannot_be_none(self):
        with self.assertRaises(ValueError):self.run_daily(files={'missing':None})

if __name__=='__main__':unittest.main()

"""Native receipt-authority schema and sealed branch choice, synthetic bytes only."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_m06_input_delivery as support
import test_m06_daily_cycle as cycle_support
from fixtures.hk_preselection_verified_factory import create_verified_fixture
from v5_shadow import p0_hk_preselection as p0
from v5_shadow.digests import canonical_bytes, sha256_json

POLICY = 'REUSE_VERIFIED_OR_GENERATE_IF_ABSENT'


class M06NativePoolAdmissionTests(unittest.TestCase):
    setUp = support.M06InputDeliveryTests.setUp
    write = support.M06InputDeliveryTests.write
    upstream = support.M06InputDeliveryTests.upstream
    write_dispatch = support.M06InputDeliveryTests.write_dispatch
    prepare = support.M06InputDeliveryTests.prepare
    capture = support.M06InputDeliveryTests.capture

    def native_pool(self):
        self.upstream()
        store = self.root/'store'
        create_verified_fixture(store, target=self.target, signal=self.signal,
                                eligibility=self.signal, master_capture_time='17:30:00')
        self.entry = json.loads((store/'latest.json').read_bytes())['entries'][self.target+'/'+self.adapter.ROLE]
        self.manifest = json.loads((store/self.entry['manifest_relative']).read_bytes())
        for key in self.adapter.SAFETY:
            self.manifest.pop(key)
        self.manifest['captured_at'] = '2026-10-12T17:31:00+08:00'
        self.manifest['provenance']['panel_sha256'] = self.panel['panel_sha256']
        self.receipt = json.loads((store/self.entry['receipt_relative']).read_bytes())
        self.receipt['finished_at'] = '2026-10-12T17:32:00+08:00'
        self.save_pool()

    def save_pool(self):
        self.receipt['manifest_sha256'] = sha256_json(self.manifest)
        self.write('store', self.entry['manifest_relative'], self.manifest)
        self.write('store', self.entry['receipt_relative'], self.receipt)

    def test_native_manifest_without_flags_is_admitted_by_bound_safe_receipt(self):
        self.native_pool()
        before = (self.root/'store'/self.entry['manifest_relative']).read_bytes()
        try:
            result = self.prepare()
        except ValueError as error:
            self.fail('Original receipt-authority schema must be admitted: '+str(error))
        self.assertEqual(result['status'], 'READY')
        self.assertEqual(result['production_method'], 'EXISTING_VERIFIED_POOL')
        self.assertEqual((self.root/'store'/self.entry['manifest_relative']).read_bytes(), before)
        self.assertEqual((Path(result['store_root'])/self.entry['manifest_relative']).read_bytes(), before)
        self.assertTrue(all(k not in json.loads(before) for k in self.adapter.SAFETY))

    def test_missing_or_true_receipt_safety_cannot_become_generation(self):
        self.native_pool()
        good = deepcopy(self.receipt)
        for key in self.adapter.SAFETY:
            for missing in (True, False):
                self.receipt = deepcopy(good)
                if missing:self.receipt.pop(key)
                else:self.receipt[key] = True
                self.save_pool()
                with self.subTest(key=key, missing=missing), self.assertRaisesRegex(ValueError, 'SAFETY'):
                    self.prepare()
        self.assertFalse((self.root/'snapshots'/(self.target+'.json')).exists())

    def test_explicit_manifest_safety_conflict_is_rejected_even_with_safe_receipt(self):
        self.native_pool()
        for key in self.adapter.SAFETY:
            self.manifest[key] = True; self.save_pool()
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'SAFETY'):
                self.prepare()
            self.manifest.pop(key)

    def test_native_schema_pair_and_owner_binding_are_required(self):
        self.native_pool(); good = deepcopy(self.receipt)
        for key, value in [('schema_version','other.receipt.v1'), ('owner','WRONG_OWNER'), ('run_id','WRONG_RUN')]:
            self.receipt = dict(good, **{key:value}); self.save_pool()
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'POOL'):
                self.prepare()

    def test_wrong_target_and_manifest_or_artifact_hash_are_rejected(self):
        self.native_pool(); self.manifest['trade_date'] = self.signal; self.save_pool()
        with self.assertRaisesRegex(ValueError, 'POOL'):self.prepare()
        self.manifest['trade_date'] = self.target; self.save_pool()
        self.receipt['manifest_sha256'] = '0'*64
        self.write('store', self.entry['receipt_relative'], self.receipt)
        with self.assertRaisesRegex(ValueError, 'HASH'):self.prepare()
        self.save_pool(); self.write('store', self.entry['artifact_relative'], b'wrong bytes')
        with self.assertRaisesRegex(ValueError, 'HASH'):self.prepare()

    def test_absent_pool_selects_generation_without_removing_other_date_entries(self):
        self.upstream()
        original = canonical_bytes(dict(schema_version='v3_shared_data.latest.v1',entries={'20261009/OTHER':{'untouched':True}}))
        self.write('store','latest.json',original)
        result = self.prepare()
        self.assertEqual(result['production_method'],'GENERATE_IF_ABSENT')
        self.assertEqual((Path(result['store_root'])/'latest.json').read_bytes(),original)
        self.assertEqual((self.root/'store/latest.json').read_bytes(),original)

    def test_present_null_entry_is_invalid_not_absent(self):
        self.upstream(); self.write('store','latest.json',dict(entries={self.target+'/'+self.adapter.ROLE:None}))
        with self.assertRaisesRegex(ValueError, 'POOL'):
            self.prepare()
        self.assertFalse((self.root/'snapshots'/(self.target+'.json')).exists())

    def test_sealed_existing_choice_is_retained_when_live_latest_moves(self):
        self.native_pool(); first = self.prepare()
        self.write('store','latest.json',dict(entries={}))
        with patch.object(self.adapter,'_utc_now',side_effect=AssertionError('no new seal clock')):
            second = self.prepare()
        self.assertEqual(second['production_method'],'EXISTING_VERIFIED_POOL')
        self.assertEqual(second['seal_sha256'],first['seal_sha256'])

    def test_sealed_absent_choice_does_not_follow_later_original_pool(self):
        self.upstream(); first = self.prepare()
        self.native_pool(); second = self.prepare()
        self.assertEqual(second['production_method'],'GENERATE_IF_ABSENT')
        self.assertEqual(second['seal_sha256'],first['seal_sha256'])


class M06PoolSelectionPolicyTests(unittest.TestCase):
    setUp = cycle_support.M06DailyCycleTests.setUp
    write_delivery = cycle_support.M06DailyCycleTests.write_delivery

    def test_opt_in_is_accepted_only_with_evening_sealed_input_adapter(self):
        self.policy.update(production_method=POLICY, execution_mode='NATURAL',
            date_contract=p0.EVENING_CONTRACT, owner_contract_cutoff_time='09:00',
            half_day_window=dict(start='17:30',end='18:30'))
        self.policy['input_delivery'] = dict(snapshot_root=str(self.root/'snapshots'),
            original_store_root=self.registration['store_root'], original_asset_root=self.registration['asset_root'])
        (self.root/'snapshots').mkdir()
        try:
            self.assertEqual(p0._candidate_policy(self.config)['production_method'], POLICY)
        except ValueError as error:
            self.fail('Explicit sealed selection policy not implemented: '+str(error))
        self.policy.pop('input_delivery')
        with self.assertRaisesRegex(ValueError, 'SELECTION'):
            p0._candidate_policy(self.config)


class M06SelectedRequestBoundaryTests(unittest.TestCase):
    """Real sealed inputs reach the fixed inspector; fake assets cannot pass it."""
    setUp = cycle_support.M06DailyCycleTests.setUp
    write_delivery = cycle_support.M06DailyCycleTests.write_delivery

    def selected_inspection(self, existing):
        fixture = M06NativePoolAdmissionTests()
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        if existing:fixture.native_pool()
        else:
            fixture.native_pool()
            # Explicit absent-target fixture. Keep the verified master and all
            # unrelated source bytes; never mutate any real store.
            fixture.write('store', 'latest.json', dict(entries={}))
        self.registration.update(store_root=str(fixture.root/'store'), asset_root=str(fixture.root/'assets'))
        self.policy.update(production_method=POLICY, execution_mode='NATURAL',
            date_contract=p0.EVENING_CONTRACT, owner_contract_cutoff_time='09:00',
            full_day_window=dict(start='17:30',end='18:30'),half_day_window=dict(start='17:30',end='18:30'),
            input_delivery={k:v for k,v in fixture.config.items() if k!='delivery_root'})
        now = fixture.now
        with patch.object(fixture.adapter,'_utc_now',return_value=now), patch.object(p0,'_utc_now',return_value=now), \
                patch('v5_shadow.m06_deadline_process._utc_now',return_value=now), \
                patch.object(p0,'_process',wraps=p0._process) as inspect, \
                patch.object(p0,'run_owner',side_effect=AssertionError('No owner may run for invalid assets')):
            with self.assertRaises(ValueError):p0.prepare_daily_candidate(self.config,now)
        self.assertEqual(inspect.call_count,1)
        action, request, registration = inspect.call_args.args[:3]
        self.assertEqual(action,'inspect')
        self.assertEqual(request['production_method'],'EXISTING_VERIFIED_POOL' if existing else 'GENERATE_IF_ABSENT')
        self.assertTrue(registration['store_root'].startswith(str(fixture.root/'snapshots')+'/'))
        self.assertEqual(request['signal_date'],'20261012');self.assertEqual(request['target_date'],'20261013')
        self.assertEqual(len(list((self.root/'ledger').iterdir())),1)
        self.assertFalse((self.root/'output/.m06-ledger').exists())
        self.assertFalse((self.root/'output/.m06-current-success.json').exists())
        self.assertEqual(list((self.root/'bundles').glob('.m06-????????.json')),[])

    def test_existing_selection_reaches_original_inspector_without_generation_fallback(self):
        self.selected_inspection(True)

    def test_absent_selection_reaches_original_generation_inspector_without_invocation(self):
        self.selected_inspection(False)

    def test_separate_opt_in_template_is_disabled_and_default_is_unchanged(self):
        examples=Path(__file__).resolve().parents[1]/'examples'
        original=json.loads((examples/'m06_daily_runtime.template.json').read_bytes())
        optional=json.loads((examples/'m06_daily_reuse_or_generate.disabled.template.json').read_bytes())
        self.assertEqual(original['daily']['hk_preselection_daily']['production_method'],'GENERATE_IF_ABSENT')
        self.assertEqual(optional['daily']['hk_preselection_daily']['production_method'],POLICY)
        optional['daily']['hk_preselection_daily']['production_method']='GENERATE_IF_ABSENT'
        self.assertEqual(original,optional)
        for key in ('enabled',):self.assertIs(optional['daily'][key],False)
        for key in ('hk_preselection','hk_preselection_daily'):self.assertIs(optional['daily'][key]['enabled'],False)


if __name__ == '__main__':unittest.main()

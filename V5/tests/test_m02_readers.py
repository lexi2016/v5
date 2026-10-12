"""Unmodified membership/native owners and default pinned panel loader tests.

The two-reader persistence test mocks only the panel transport, explicitly. The
optional all-real round trip uses a supplied complete fixture request; no model
PIN, owner function, or source manifest is patched to fabricate that success.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from v5_shadow import hk_source_daily as daily
from v5_shadow.digests import canonical_bytes
import test_hk_membership_recovery as membership_fixture
from synthetic_worker_clock import synthetic_worker_clock, clock_at

NATIVE_SCRIPT = r'''
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from v5_shadow.hk_preselection import _source_bytes,_HKLoader
sys.meta_path.insert(0,_HKLoader(_source_bytes()))
from upstreams.v3_shared_data.shared_data.hk_security_master import publish_hk_security_master
publish_hk_security_master(Path(sys.argv[2]),trade_date='20261008',
 rows=[{'code':'HK.00001','name':'SYNTHETIC ISSUER NOT REAL EVIDENCE'}],
 universe_codes_sha256='a'*64,captured_at=sys.argv[3])
'''

class OriginalReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        with patch.object(membership_fixture,'datetime',clock_at('2026-10-09T06:59:00+00:00')):
            fixture=membership_fixture.MembershipRecoveryTests();fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with synthetic_worker_clock({'hk_membership_recovery':'2026-10-09T07:00:00+00:00'}):
            self.membership=fixture.run_value()
        self.fixture=fixture
        native=self.root/'native';native.mkdir()
        child=subprocess.run([sys.executable,'-I','-B','-c',NATIVE_SCRIPT,
            str(Path(__file__).resolve().parents[1]/'src'),str(native),'2026-10-08T08:00:00+00:00'],capture_output=True,text=True,timeout=60)
        self.assertEqual(child.returncode,0,child.stderr)
        panel=self.root/'panel';panel.mkdir()
        # Deliberately invalid frozen bundle. The default owner must reject it.
        self.panel=panel
        self.write_panel({})
        out=self.root/'binding';out.mkdir(mode=0o700);(out/'.v5-hk-source-root').write_bytes(daily.MARKER)
        self.kw=dict(private_root=str(out),asset_binding=self.binding(panel),
            membership_root=str(fixture.output),membership_files=self.membership['files'],native_binding=self.binding(native),
            target_date='20261009',signal_date='20261008',eligibility_source_date='20261008',cutoff='2026-10-09T08:00:00+00:00')
        self.request=dict(private_root=str(out),inputs=dict(panel=self.kw['asset_binding'],
            membership=dict(root=str(fixture.output),files=self.membership['files']),native=self.kw['native_binding']),
            **{k:self.kw[k] for k in ('target_date','signal_date','eligibility_source_date','cutoff')},require_pit=False)

    def binding(self,root):
        return dict(root=str(root),files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()})

    def write_panel(self,model):
        files={'panel_latest.json':{'manifest_relative':'panel.json'},'model_latest.json':{'manifest_relative':'model.json'},
            'panel.json':{'panel_relative':'panel.parquet','panel_sha256':hashlib.sha256(b'fixture').hexdigest(),'panel_max_date':'20261008'},
            'model.json':dict(model,bundle_relative='models.joblib')}
        for name,value in files.items():(self.panel/name).write_bytes(canonical_bytes(value))
        (self.panel/'panel.parquet').write_bytes(b'fixture');(self.panel/'models.joblib').write_bytes(b'not the frozen model')

    def test_original_membership_and_native_success_no_source_mutation(self):
        before={n:daily.snapshot(b) for n,b in self.request['inputs'].items()}
        member=daily._membership(self.request);native=daily._native(self.request)
        self.assertEqual(len(member['identity']['codes']),698)
        self.assertEqual(native['identity']['master']['HK.00001']['name'],'SYNTHETIC ISSUER NOT REAL EVIDENCE')
        self.assertEqual(native['identity']['manifest']['trade_date'],'20261008')
        self.assertEqual(before,{n:daily.snapshot(b) for n,b in self.request['inputs'].items()})
        self.assertFalse(native['pit_verified'])

    def test_original_historical_asof_is_not_inferred_from_source_timestamps(self):
        # The original v2 owner also requires read witness <= as_of. A current
        # read of an older publication is identity evidence, not a PIT proof.
        result=daily._membership(self.request)
        self.assertFalse(result['pit_verified'])

    def test_default_chain_uses_all_owners_and_rejects_fake_model(self):
        with self.assertRaises(daily.SourceRejected) as caught:daily.build_binding(**self.kw)
        states=caught.exception.sources
        self.assertEqual(states['membership']['status'],'VERIFIED')
        self.assertEqual(states['native']['status'],'VERIFIED')
        self.assertEqual(states['panel']['status'],'REJECTED')
        self.assertIn('frozen model manifest mismatch',states['panel']['reason'])
        self.assertFalse((Path(self.kw['private_root'])/'slots').exists())

    def test_two_original_readers_persist_and_independently_read_with_panel_transport_mock(self):
        panel=dict(status='VERIFIED',identity={'explicit_test_double':'panel transport only'},times={},pit_verified=False)
        with patch.object(daily,'_panel',return_value=panel):
            saved=daily.build_binding(**self.kw)
            restored=daily.read_binding(self.kw['private_root'],self.kw['target_date'],receipt_hash=saved['receiptHash'])
        self.assertEqual(saved,restored)
        self.assertFalse(saved['binding']['formal_eligibility_verified'])
        self.assertEqual(saved['binding']['sources']['membership']['identity']['target_date'],'20261009')

    def test_owner_cutoff_date_and_seven_file_failures(self):
        for change in ({'cutoff':'2026-10-09T06:58:00+00:00'},{'target_date':'20261008'}):
            with self.subTest(change=change),self.assertRaises(ValueError):daily._membership(dict(self.request,**change))
        with self.assertRaises(ValueError):daily._native(dict(self.request,eligibility_source_date='20261007'))
        bad=copy.deepcopy(self.request);bad['inputs']['membership']['files'].pop(next(iter(bad['inputs']['membership']['files'])))
        with self.assertRaises(ValueError):daily._membership(bad)

    def test_default_panel_calendar_and_input_identity_boundaries(self):
        for change,reason in (({'target_date':'20261010'},'NOT_SESSION'),
                              ({'signal_date':'20261007'},'NOT_PREVIOUS_SESSION'),
                              ({'eligibility_source_date':'20261010'},'NOT_SESSION')):
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,reason):daily._panel(dict(self.request,**change))
        (self.panel/'panel.parquet').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'ASSET_SHA'):daily._panel(self.request)

    def test_incomplete_and_fake_reader_success_is_rejected(self):
        for name,reader in (('read_membership',daily._membership),('read_native_identity',daily._native)):
            for value in ({},{'formal_eligibility_verified':True},{'error':'BAD_SHA'}):
                with self.subTest(name=name,value=value),patch.object(daily,name,return_value=value),self.assertRaises(ValueError):reader(self.request)

    def test_original_frozen_model_checksum_is_hard_gate(self):
        model=dict(schema_version='hkconnect_d1_model_bundle.v1',trained_through='20260716',feature_count=155,
            model_names=['extra_trees','hgb_depth6','logit','random_forest'],bundle_file='models.joblib',
            bundle_sha256='3b0d5d5239342439cabf25b30012365a64d78839bc3cd4d90bad7be6ff4aaa07',
            python_version='3.13.12',sklearn_version='1.9.0',joblib_version='1.5.3',primary_strategy='prob_active',
            research_only=True,production_allowed=False,feature_columns=['f'+str(i) for i in range(155)])
        self.write_panel(model);request=copy.deepcopy(self.request);request['inputs']['panel']=self.binding(self.panel)
        with self.assertRaisesRegex(ValueError,'frozen model bundle checksum mismatch'):daily._panel(request)

    def test_undeclared_pointer_alias_cannot_resolve_to_declared_asset(self):
        (self.panel/'alias.parquet').symlink_to(self.panel/'panel.parquet')
        manifest=json.loads((self.panel/'panel.json').read_bytes());manifest['panel_relative']='alias.parquet'
        (self.panel/'panel.json').write_bytes(canonical_bytes(manifest))
        request=copy.deepcopy(self.request)
        request['inputs']['panel']['files']['panel.json']=hashlib.sha256((self.panel/'panel.json').read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'REFERENCE_NOT_BOUND'):daily._panel(request)

    def test_extra_declared_asset_is_not_part_of_fixed_owner_reference_set(self):
        (self.panel/'extra').write_bytes(b'extra')
        request=copy.deepcopy(self.request);request['inputs']['panel']=self.binding(self.panel)
        with self.assertRaisesRegex(ValueError,'REFERENCE_SET'):daily._panel(request)

    @unittest.skipUnless(os.environ.get('M02_REAL_ASSET_ROOT'), 'NOT_RUN: unchanged frozen assets not available in this environment')
    def test_all_three_original_readers_with_real_frozen_assets(self):
        import importlib.util
        tool=Path(__file__).resolve().parents[1]/'tools/prepare_m02_request.py'
        spec=importlib.util.spec_from_file_location('prepare_m02_request',tool)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        # Real unchanged panel/model/name assets, synthetic original owner data.
        # Current panel may be newer than the fixture cutoff: identity only.
        self.kw['asset_binding']=module.asset_binding(os.environ['M02_REAL_ASSET_ROOT'])
        first=daily.build_binding(**self.kw)
        second=daily.read_binding(self.kw['private_root'],self.kw['target_date'],receipt_hash=first['receiptHash'])
        self.assertEqual(first,second)
        self.assertFalse(first['binding']['historical_eligible'])
        self.assertFalse(first['binding']['formal_eligibility_verified'])


class ProvidedRealFixtureTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('M02_REAL_FIXTURE_REQUEST'), 'NOT_RUN: complete frozen-model fixture request not supplied')
    def test_all_three_unmodified_readers_roundtrip(self):
        # This path is test input only; production code has no bypass/fixture flag.
        request=json.loads(Path(os.environ['M02_REAL_FIXTURE_REQUEST']).read_text())
        first=daily.build_binding(**request)
        second=daily.read_binding(request['private_root'],request['target_date'],receipt_hash=first['receiptHash'])
        self.assertEqual(first,second);self.assertFalse(first['binding']['formal_eligibility_verified'])

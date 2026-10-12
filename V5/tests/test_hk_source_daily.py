"""Persistence/temporal contract tests; reader mocks are explicitly unit-only."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from v5_shadow import hk_source_daily as daily

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve(); self.out=self.root/'output'; self.out.mkdir(mode=0o700)
        (self.out/'.v5-hk-source-root').write_bytes(b'v5.hk-source-root.v1\n')
        self.inputs={}
        for name in ('panel','membership','native'):
            root=self.root/name;root.mkdir();(root/'fixture').write_bytes(name.encode())
            self.inputs[name]={'root':str(root),'files':{'fixture':hashlib.sha256(name.encode()).hexdigest()}}
        self.kw=dict(private_root=str(self.out),asset_binding=self.inputs['panel'],
            membership_root=self.inputs['membership']['root'],membership_files=self.inputs['membership']['files'],
            native_binding=self.inputs['native'],target_date='20261009',signal_date='20261008',
            eligibility_source_date='20261008',cutoff='2026-10-09T08:00:00+00:00')
        self.sources={n:{'status':'VERIFIED','identity':{'fixture':n},'times':{},'pit_verified':False} for n in self.inputs}

    def seam(self):
        self.assertTrue(hasattr(daily,'_collect'), 'complete three-reader collection seam missing')
        return patch.object(daily,'_collect',return_value=copy.deepcopy(self.sources))

    def build(self):
        with self.seam():return daily.build_binding(**self.kw)

    def read(self,saved):
        with self.seam():return daily.read_binding(str(self.out),'20261009',receipt_hash=saved['receiptHash'])

    def test_atomic_roundtrip_and_idempotent_bytes(self):
        first=self.build(); before=self.bytes()
        self.assertEqual(first,self.build()); self.assertEqual(before,self.bytes())
        restored=self.read(first)
        self.assertEqual(restored,first)
        self.assertFalse(restored['binding']['formal_eligibility_verified'])
        self.assertFalse(restored['binding']['historical_eligible'])
        self.assertEqual(restored['binding']['sources'],self.sources)

    def bytes(self):return {str(p.relative_to(self.out)):p.read_bytes() for p in self.out.rglob('*') if p.is_file()}

    def test_failure_keeps_prior_success(self):
        first=self.build(); before=self.bytes()
        with patch.object(daily,'_collect',side_effect=ValueError('reader failed')):
            with self.assertRaisesRegex(ValueError,'reader failed'):daily.build_binding(**self.kw)
        self.assertEqual(self.bytes(),before); self.assertEqual(self.read(first),first)

    def test_changed_input_conflicts_and_preserves_old(self):
        self.build();before=self.bytes();self.kw['cutoff']='2026-10-09T09:00:00+00:00'
        with self.assertRaisesRegex(ValueError,'CONFLICT'):self.build()
        self.assertEqual(before,self.bytes())

    def test_hash_tamper_wrong_date_and_wrong_receipt_fail(self):
        result=self.build()
        with self.seam():
            with self.assertRaises((ValueError,FileNotFoundError)):
                daily.read_binding(str(self.out),'20261008',receipt_hash=result['receiptHash'])
            with self.assertRaisesRegex(ValueError,'RECEIPT'):
                daily.read_binding(str(self.out),'20261009',receipt_hash='0'*64)
        path=next((self.out/'objects').glob('*.json'));path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'HASH'):self.read(result)

    def test_readback_reverifies_all_source_results(self):
        result=self.build(); self.sources['panel']['identity']['fixture']='swapped'
        with self.assertRaisesRegex(ValueError,'READBACK'):self.read(result)

    def test_output_overlap_private_mode_and_symlink_rejected(self):
        for root in (self.inputs['panel']['root'],str(self.root)):
            kw=dict(self.kw,private_root=root)
            with self.seam(),self.assertRaises((ValueError,OSError)):daily.build_binding(**kw)
        os.chmod(self.out,0o755)
        with self.assertRaisesRegex(ValueError,'PRIVATE'):self.build()
        os.chmod(self.out,0o700); link=self.root/'link';link.symlink_to(self.out,target_is_directory=True)
        with self.seam(),self.assertRaises((ValueError,OSError)):
            daily.build_binding(**dict(self.kw,private_root=str(link)))

    def test_invalid_dates_naive_cutoff_and_pit_missing_reject(self):
        for fields in ({'target_date':'20260230'},{'signal_date':'20261009'},
                       {'eligibility_source_date':'20261012'},{'cutoff':'2026-10-09T08:00:00'},
                       {'cutoff':'2026-10-08T08:00:00+00:00'},{'require_pit':True}):
            with self.subTest(fields=fields),self.seam(),self.assertRaises(ValueError):
                daily.build_binding(**dict(self.kw,**fields))
        self.assertFalse((self.out/'slots').exists())

    def test_receipt_write_failure_has_no_success_pointer(self):
        self.assertTrue(hasattr(daily,'_safe_root'),'fixed SafeRoot missing')
        io=daily._safe_root(); original=io.write_bytes
        def fail(instance,path,raw,**kw):
            if path.startswith('receipts/'):raise OSError('disk full')
            return original(instance,path,raw,**kw)
        with patch.object(io,'write_bytes',fail),self.assertRaisesRegex(OSError,'disk full'):self.build()
        self.assertFalse((self.out/'slots/20261009.json').exists())

    def test_concurrent_identical_builders_publish_one_pair(self):
        from concurrent.futures import ThreadPoolExecutor
        self.build()
        before=self.bytes()
        with self.seam(),ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:daily.build_binding(**self.kw),range(8)))
        self.assertTrue(all(value==results[0] for value in results))
        self.assertEqual(before,self.bytes())

    def test_output_root_replacement_during_readers_is_rejected(self):
        original=self.out.with_name('previous-output')
        def replace_root(request):
            self.out.rename(original);self.out.mkdir(mode=0o700)
            (self.out/'.v5-hk-source-root').write_bytes(b'v5.hk-source-root.v1\n')
            return self.sources
        self.assertTrue(hasattr(daily,'_collect'))
        with patch.object(daily,'_collect',side_effect=replace_root),self.assertRaisesRegex(ValueError,'ROOT_REPLACED'):
            daily.build_binding(**self.kw)
        self.assertFalse((self.out/'slots').exists())

    def test_resealed_disk_binding_cannot_replace_external_receipt_hash(self):
        result=self.build();old_hash=result['receiptHash']
        pointer_path=self.out/'slots/20261009.json';pointer=json.loads(pointer_path.read_bytes())
        binding=copy.deepcopy(result['binding']);binding['formal_eligibility_verified']=True
        raw=daily.canonical_bytes(binding);pointer['binding_sha256']=hashlib.sha256(raw).hexdigest()
        (self.out/'objects'/str(pointer['binding_sha256']+'.json')).write_bytes(raw)
        receipt=copy.deepcopy(result['receipt']);receipt['binding_sha256']=pointer['binding_sha256']
        raw=daily.canonical_bytes(receipt);pointer['receiptHash']=hashlib.sha256(raw).hexdigest()
        (self.out/'receipts'/str(pointer['receiptHash']+'.json')).write_bytes(raw)
        pointer_path.write_bytes(daily.canonical_bytes(pointer))
        with self.seam(),self.assertRaisesRegex(ValueError,'RECEIPT_POINTER'):
            daily.read_binding(str(self.out),'20261009',receipt_hash=old_hash)

    def test_source_bytes_tampered_before_readback_are_rejected(self):
        result=self.build();Path(self.inputs['panel']['root'],'fixture').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'ASSET_SHA'):self.read(result)

    def test_trailing_slash_root_normalized_for_independent_roundtrip(self):
        self.kw['private_root']+='/'
        first=self.build()
        self.assertEqual(self.read(first),first)

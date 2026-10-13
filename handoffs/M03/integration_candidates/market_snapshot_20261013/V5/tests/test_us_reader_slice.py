"""Real fresh-child reader and diagnostics, replacing R13 existence-only checks."""
from dataclasses import replace
import json
import subprocess
from types import SimpleNamespace
import unittest
from m03_fixture import SourceCase, make_source
from v5_shadow import us_source_daily as m


class ColdReaderTests(SourceCase):
    def test_reader_is_real_fresh_process_and_read_only(self):
        make_source(self.source)
        self.assertTrue(callable(getattr(m, 'read_cold_snapshot', None)), 'reader missing from complete module')
        before={str(p.relative_to(self.source)):p.read_bytes() for p in self.source.rglob('*') if p.is_file()}
        payload=m.read_cold_snapshot(self.request(snapshot_root=self.source))
        self.assertEqual(payload['status'],'READY')
        self.assertEqual(len(payload['market_snapshot']['quotes']),33)
        self.assertEqual(before,{str(p.relative_to(self.source)):p.read_bytes() for p in self.source.rglob('*') if p.is_file()})

    def test_missing_valid_root_returns_none(self):
        from v5_shadow.cloud_us_collector import initialize_output
        initialize_output(self.snapshot, self.request().owner_root)
        self.assertIsNone(m.read_cold_snapshot(self.request()))

    def test_invalid_marker_and_each_contract_tamper_refused(self):
        make_source(self.source)
        with self.assertRaisesRegex(RuntimeError,'M03_READER_FAILED'):
            m.read_cold_snapshot(self.request())
        for key,path in m.source_paths(self.source,'20261009').items():
            with self.subTest(key=key):
                original=path.read_bytes()
                path.write_bytes(b'{}')
                try:
                    with self.assertRaisesRegex(RuntimeError,'M03_READER_FAILED'):
                        m.read_cold_snapshot(self.request(snapshot_root=self.source))
                finally:path.write_bytes(original)

    def test_nonzero_bad_json_contract_type_and_timeout_diagnostics(self):
        cases=[(3,'original diagnostic','M03_READER_FAILED'),(0,'bad','M03_READER_BAD_JSON'),(0,'[]','M03_READER_CONTRACT_ERROR'),(0,'{}','M03_READER_CONTRACT_ERROR'),(0,'{"payload":3}','M03_READER_PAYLOAD_TYPE_ERROR')]
        for rc,stdout,code in cases:
            with self.subTest(code=code),self.assertRaisesRegex((RuntimeError,ValueError),code):
                m.read_cold_snapshot(self.request(),runner=lambda *a,**k:SimpleNamespace(returncode=rc,stdout=stdout,stderr='diagnostic stderr'))
        def timeout(*args,**kwargs):
            raise subprocess.TimeoutExpired('reader',300,output='partial out',stderr='partial err')
        with self.assertRaisesRegex(RuntimeError,'M03_READER_TIMEOUT'):
            m.read_cold_snapshot(self.request(),runner=timeout)

class ReaderCodeIdentityTests(SourceCase):
    def test_reader_rejects_alternate_code_tree_before_import(self):
        fake=self.root/'fake-src'
        (fake/'v5_shadow').mkdir(parents=True)
        (fake/'infrastructure').mkdir()
        (fake/'v5_shadow/__init__.py').write_text('')
        (fake/'infrastructure/__init__.py').write_text('')
        (fake/'v5_shadow/cloud_us_collector.py').write_text('def load_owner(*a): pass\ndef verify(*a): pass\ndef audit_modules(*a): pass\ndef admit_output(*a): pass\n')
        (fake/'infrastructure/research_peripheral_store.py').write_text('class ResearchPeripheralStore:\n def __init__(self,*a): pass\n def read_exact(self,*a): return {"forged":True}\n')
        with self.assertRaisesRegex(ValueError,'M03_V5_SRC_IDENTITY_MISMATCH'):
            m.read_cold_snapshot(self.request(v5_src=fake))

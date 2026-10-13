import copy
import importlib
from pathlib import Path
import tempfile
import unittest
from test_rebound_pytdx_window import ROOT,BASE,RUNTIME_SRC,fixture,canonical,sha

class OwnerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=importlib.import_module('v5_shadow.rebound_pytdx_window')
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT);self.addCleanup(self.tmp.cleanup)
        prefix='assets/m14_pytdx_windows/runs/20261013/independent-001'
        self.paths=dict(panel_manifest=prefix+'/manifest.json',panel=prefix+'/window.parquet',
            master_manifest='assets/hk_security_master/runs/20261013/run1/manifest.json',
            master_artifact='assets/hk_security_master/runs/20261013/run1/artifact.csv',
            master_receipt='assets/hk_security_master/runs/20261013/run1/receipt.json',
            window_parent_manifest='assets/hk_0_2/panels/20261013-old/manifest.json',
            window_parent_panel='assets/hk_0_2/panels/20261013-old/hkconnect_vipdoc_daily_panel.parquet')
        self.request=dict(schema_version=self.m.REQUEST_SCHEMA,target_date='20261014',signal_date='20261013',
            research_cutoff='2026-10-13T10:00:00+00:00',data_kind='SYNTHETIC',input_root=self.tmp.name,
            paths=self.paths,files={p:'a'*64 for p in self.paths.values()})
        self.request['files'][prefix+'/records-000.json']='b'*64
    def validate(self):return self.m.validate_request(self.request,base=BASE)
    def test_new_schema_and_new_namespace_required(self):
        self.assertEqual(self.validate(),self.request)
        self.request['schema_version']='v5.rebound_owner_request.v1'
        with self.assertRaisesRegex(ValueError,'SCHEMA'):self.validate()
    def test_private_total_counts_two_generated_routes_without_lifting_32(self):
        prefix=str(Path(self.paths['panel']).parent)
        for i in range(1,24):self.request['files'][prefix+f'/records-{i:03d}.json']='b'*64
        self.assertEqual(len(self.request['files']),31)
        with self.assertRaisesRegex(ValueError,'FILES'):self.validate()
    def test_no_extra_supplement_no_path_alias_no_missing_role(self):
        self.request['files']['assets/hk_0_2/daily_supplements/pointers/20261013.json']='b'*64
        with self.assertRaisesRegex(ValueError,'PATH'):self.validate()
        self.request['files'].pop('assets/hk_0_2/daily_supplements/pointers/20261013.json')
        self.request['paths']['panel']=self.request['paths']['window_parent_panel']
        with self.assertRaisesRegex(ValueError,'ROLE|PATH'):self.validate()
    def test_raw_decoder_pin_is_enforced(self):
        self.assertTrue(callable(getattr(self.m,'verify_decoder_pin',None)))
        self.m.verify_decoder_pin()
    def test_new_witness_accepts_same_cutoff_in_hong_kong_timezone(self):
        import types
        original=types.SimpleNamespace()
        private=Path(self.tmp.name)
        witness=dict(previous5_required='20261012',owner='V5_INDEPENDENT_PYTDX_RESEARCH_WINDOW')
        self.m.install_research_witness(original,private=private,request=self.request,witness=witness)
        observed,gaps=original._read_hk02_panel_witness(private,'20261013',research_cutoff='2026-10-13T18:00:00+08:00',required_history_date='20261012')
        self.assertEqual(observed['owner'],'V5_INDEPENDENT_PYTDX_RESEARCH_WINDOW')
        self.assertEqual(gaps,[])
    def test_owner_after_candidate_contains_untouched_legacy_entry(self):
        p=RUNTIME_SRC/'v5_shadow/rebound_owner.py'
        self.assertTrue(p.exists(),'full optional owner candidate is missing')
        original=(BASE/'src/v5_shadow/rebound_owner.py').read_text();updated=p.read_text()
        self.assertIn("if value['schema_version'] != 'v5.rebound_owner_request.v1':",updated)
        for name in ['_file','_sources','read_rebound_owner','manager_projection']:
            import ast
            def node(s):return next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(ast.dump(node(original)),ast.dump(node(updated)),name)

if __name__=='__main__':unittest.main()

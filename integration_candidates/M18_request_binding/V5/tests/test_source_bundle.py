"""Targeted P0 source integration; accepted owner algorithms stay unchanged."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE=Path(__file__).resolve().parents[1]

class SourceBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='p0-source-bundle-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()

    def bundle(self,jobs=None):
        return dict(schema_version='v5.source_bundle.request.v1',data_kind='SYNTHETIC',jobs=jobs or {})

    def run_bundle(self,jobs=None):
        from v5_shadow.source_bundle import run_source_bundle
        return run_source_bundle(self.bundle(jobs))

    def test_source_entrypoint_exists(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.source_bundle'))

    def test_missing_requests_are_four_explicit_blocks(self):
        result=self.run_bundle()
        self.assertEqual([x['module_id'] for x in result['modules']],['M01_A_MARKET','M02_HK_MARKET','M03_US_MARKET','M05_A_PRESELECTION'])
        self.assertTrue(all(x['status']=='BLOCKED_REQUEST_MISSING' for x in result['modules']))
        self.assertFalse(result['natural_verified'])

    def test_registry_does_not_alias_m03_to_m15(self):
        from v5_shadow.main_registry import registry_by_id
        records=registry_by_id()
        self.assertEqual(records['M03_US_MARKET'].owner_entry,'m03_us_source')
        self.assertEqual(records['M15_US_MAPPING'].owner_entry,'us_mapping')
        self.assertEqual(records['M18_MANAGER'].dependencies,('M13_ANNOUNCEMENT','M14_REBOUND','M15_US_MAPPING'))

    def us_request(self):
        return dict(trade_date='20261009',capture_phase='POST_CLOSE',session='20261009',
            cutoff='2026-10-10T10:00:00Z',source_root=str(self.root/'source'),
            snapshot_root=str(self.root/'snapshot'),binding_root=str(self.root/'binding'))

    def test_m03_network_request_is_rejected_before_any_side_effect(self):
        req=self.us_request();req['allow_network_capture']=True
        result=self.run_bundle({'M03_US_MARKET':req})['modules'][2]
        self.assertEqual(result['status'],'BLOCKED_CAPTURE_DISABLED')
        self.assertEqual(list(self.root.iterdir()),[])

    def test_m03_missing_source_calls_original_entrypoint(self):
        result=self.run_bundle({'M03_US_MARKET':self.us_request()})['modules'][2]
        self.assertEqual(result['status'],'SOURCE_MISSING',result)
        self.assertEqual(result['owner_result']['reason'],'EXPLICIT_CAPTURE_REQUIRED')
        self.assertFalse((self.root/'source').exists())
        self.assertTrue((self.root/'binding/.v5-cloud-us-capture-root').is_file())

    def test_m03_real_original_fixture_roundtrip_and_reuse(self):
        from v5_shadow.source_bundle import owner_root
        code=ast.parse((BASE/'tests/test_cloud_us_collector.py').read_text())
        method=next(n for n in ast.walk(code) if isinstance(n,ast.FunctionDef) and n.name=='test_successful_synthetic_rss_and_quotes_publish_and_original_reader_roundtrip')
        fixture=next(n.value for n in ast.walk(method) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'class Proxy:' in n.value)
        private=owner_root('m03');src=private/'V5/src';owner=private/'collector_owner';source=self.root/'source'
        init="import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from v5_shadow.cloud_us_collector import initialize_output;initialize_output(Path(sys.argv[3]),Path(sys.argv[2]))"
        for script in (init,fixture):
            p=subprocess.run([sys.executable,'-I','-B','-c',script,str(src),str(owner),str(source)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
        before={str(p.relative_to(source)):p.read_bytes() for p in source.rglob('*') if p.is_file()}
        req=self.us_request();one=self.run_bundle({'M03_US_MARKET':req})['modules'][2]
        self.assertEqual(one['status'],'VALIDATED_SOURCE_BINDING',one)
        self.assertEqual(one['owner_result']['source_status'],'READY')
        two=self.run_bundle({'M03_US_MARKET':req})['modules'][2]
        self.assertEqual(one['owner_result'],two['owner_result'])
        self.assertEqual(before,{str(p.relative_to(source)):p.read_bytes() for p in source.rglob('*') if p.is_file()})
        self.assertFalse(one['natural_verified'])

    def test_m01_calls_original_missing_marker_boundary(self):
        source=self.root/'source';source.mkdir();out=self.root/'out';out.mkdir()
        req=dict(private_root=str(out),source_root=str(source),generation_pointer=str(source/'CURRENT_FORMULA_GENERATION.json'),target_date='20261009')
        result=self.run_bundle({'M01_A_MARKET':req})['modules'][0]
        self.assertEqual(result['status'],'SOURCE_REJECTED',result)
        self.assertIn('SHADOW_ROOT_NOT_INITIALIZED',result['error'])
        self.assertEqual(list(out.iterdir()),[])

    @unittest.skipUnless(importlib.util.find_spec('pyarrow'), 'existing Mac Parquet environment required')
    def test_m01_real_default_fixture_create_and_independent_read(self):
        from v5_shadow.source_bundle import owner_root
        source=self.root/'source';source.mkdir();out=self.root/'out';out.mkdir()
        (out/'.v5-shadow-root').write_bytes(b'v5.shadow-root.v1\n')
        p=subprocess.run([sys.executable,'-I','-B',str(BASE/'tests/source_bundle_m01_fixture.py'),str(owner_root('m01')),str(source)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        req=dict(private_root=str(out),source_root=str(source),generation_pointer=p.stdout.strip(),target_date='20261009')
        row=self.run_bundle({'M01_A_MARKET':req})['modules'][0]
        self.assertEqual(row['status'],'BOUND',row)
        self.assertTrue(row['owner_result']['readback_verified'])
        req=dict(action='read',private_root=str(out),source_root=str(source),relative=row['owner_result']['binding_relative'])
        self.assertEqual(self.run_bundle({'M01_A_MARKET':req})['modules'][0],row)

    def test_m02_calls_real_contract_without_promoting_identity(self):
        req=dict(private_root=str(self.root/'out'),asset_binding={'root':str(self.root/'panel'),'files':{}},membership_root=str(self.root/'membership'),membership_files={},native_binding={'root':str(self.root/'native'),'files':{}},target_date='20261012',signal_date='20261009',eligibility_source_date='20261009',cutoff='2026-10-12T08:00:00+08:00',require_pit=False)
        result=self.run_bundle({'M02_HK_MARKET':req})['modules'][1]
        self.assertEqual(result['status'],'SOURCE_REJECTED',result)
        self.assertIn('error_type',result)
        self.assertFalse(result['formal_eligibility_verified'])

    def test_m05_missing_v192_and_permit_never_publish(self):
        req=dict(request=dict(target_date='20261012',signal_date='20261009',data_kind='SYNTHETIC',lanes=[]))
        result=self.run_bundle({'M05_A_PRESELECTION':req})['modules'][3]
        self.assertEqual(result['status'],'BLOCKED_MISSING_V192_SOURCE')
        req['request']['lanes']=[dict(kind='v192',input_root=str(self.root/'v192'),paths={},files={'latest.json':None})]
        result=self.run_bundle({'M05_A_PRESELECTION':req})['modules'][3]
        self.assertEqual(result['status'],'BLOCKED_WRITE_GATE_REQUIRED')
        self.assertEqual(list(self.root.iterdir()),[])

    def test_main_runtime_source_command_is_opt_in_and_does_not_tick(self):
        from v5_shadow.main_runtime import source_bundle
        self.assertEqual(source_bundle({})['status'],'SOURCE_BUNDLE_DISABLED')
        path=self.root/'request.json';path.write_text(json.dumps(self.bundle()))
        cfg=self.root/'config.json';cfg.write_text(json.dumps({'source_bundle':{'enabled':True,'request_file':str(path)}}))
        p=subprocess.run([sys.executable,'-m','v5_shadow.main_runtime','source-bundle','--config',str(cfg)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue(all(r['status']=='BLOCKED_REQUEST_MISSING' for r in json.loads(p.stdout)['modules']))
        self.assertEqual({x.name for x in self.root.iterdir()},{'config.json','request.json'})

    def test_m03_code_root_override_is_rejected(self):
        req=self.us_request();req['owner_root']=str(self.root)
        result=self.run_bundle({'M03_US_MARKET':req})['modules'][2]
        self.assertEqual(result['status'],'SOURCE_REJECTED')
        self.assertEqual(result['error'],'M03_OWNER_OR_CAPTURE_OVERRIDE_DENIED')
        self.assertEqual(list(self.root.iterdir()),[])

    def test_source_publication_is_readonly_and_separate_from_manager(self):
        from v5_shadow.source_bundle import publish_source_result,STATUS_ROUTE
        from v5_shadow.module_api import _config,read_response
        import os
        root=self.root/'api';root.mkdir();(root/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
        cfg=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='test',data_root=str(root),routes=[STATUS_ROUTE])
        result=self.run_bundle()
        publication=publish_source_result(result,cfg,expected_generation=None)
        self.assertTrue(publication['generation_sha256'])
        checked,fd=_config(cfg)
        try:record,_=read_response(checked,fd,STATUS_ROUTE,{})
        finally:os.close(fd)
        self.assertEqual(record['payload'],result)
        # Actual unchanged module server: GET reads this saved result; POST never runs owners.
        import threading
        from urllib.request import urlopen,Request
        from urllib.error import HTTPError
        from v5_shadow.module_api import create_module_server
        server=create_module_server(cfg)
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        url='http://127.0.0.1:'+str(server.server_address[1])+STATUS_ROUTE
        with urlopen(url,timeout=3) as response:self.assertEqual(json.load(response),result)
        with self.assertRaises(HTTPError) as caught:urlopen(Request(url,method='POST'),timeout=3)
        self.assertEqual(caught.exception.code,405);caught.exception.close()
        with self.assertRaisesRegex(ValueError,'SOURCE_MODULE_ID_REQUIRED'):
            publish_source_result(result,dict(cfg,module_id='manager'),expected_generation=None)

if __name__=='__main__':unittest.main()

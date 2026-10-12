"""P0 read-only M06 integration: real original synthetic publication, no model."""
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

BASE=Path(__file__).resolve().parents[1]
ROUTE='/api/v5/source-bundle/hk-preselection'
FLAGS=dict(research_only=True,production_allowed=False,buy_gate_updated=False,orders_sent=False,natural_verified=False,formal_eligibility_verified=False)


class M06ReadOnlyAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='m06-readonly-api-');cls.root=Path(cls.temp.name).resolve()
        cls.output=cls.root/'output';cls.output.mkdir();(cls.output/'.v5-shadow-root').write_text('v5.shadow-root.v1\n')
        owner=BASE/'source_owners/m06';tests=BASE/'tests'
        script='''import sys,json\nfrom pathlib import Path\nsys.path[:0]=[sys.argv[1],sys.argv[2]]\nfrom fixtures.hk_preselection_verified_factory import create_verified_fixture\nfrom v5_shadow.hk_preselection_publication import publish_verified_hk_preselection\nr=create_verified_fixture(Path(sys.argv[3]))\np=dict(schema_version='v5.hk_preselection_producer_receipt.v1',status='READY',verified_source_reference=r['expected_source'],production_method='EXISTING_VERIFIED_POOL',original_result=dict(r['expected_source'],status='READY'),model_weights_reverified=False,fixture_only=True)\nprint(json.dumps(publish_verified_hk_preselection(r,bound_root=Path(sys.argv[4]),producer_receipt=p)))\n'''
        run=subprocess.run([sys.executable,'-I','-B','-c',script,str(owner/'V5/src'),str(tests),str(cls.root/'source'),str(cls.output)],capture_output=True,text=True)
        if run.returncode:raise AssertionError(run.stderr)
        cls.reference=json.loads(run.stdout)
        cls.expected=json.loads((cls.output/cls.reference['artifact_relative']).read_bytes())
        api=cls.root/'api';api.mkdir();(api/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
        cls.config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='m06-readonly-fixture',data_root=str(api),routes=['/api/v5/source-bundle/status',ROUTE],m06_hk_preselection_binding=dict(bound_root=str(cls.output),committed_reference=cls.reference,python_executable=sys.executable))

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def request(self,config=None,path=ROUTE,method='GET'):
        from v5_shadow.module_api import create_module_server
        server=create_module_server(config or self.config);thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            client=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=60)
            client.request(method,path);response=client.getresponse();value=json.loads(response.read());status=response.status;headers=dict(response.getheaders());client.close()
            return status,value,headers
        finally:server.shutdown();thread.join();server.server_close()

    def inventory(self):
        return {str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}

    def test_actual_original_cold_projection_all100_and_readonly(self):
        before=self.inventory();status,value,headers=self.request()
        self.assertEqual(status,200,value);self.assertEqual(value['artifact'],self.expected)
        self.assertEqual(value['committed_reference'],self.reference)
        self.assertEqual(len(value['artifact']['rows']),100)
        self.assertEqual(value['artifact']['rows'][0]['score_prob_active'],'0.999')
        self.assertTrue(value['fixture_only']);self.assertFalse(value['model_weights_reverified'])
        for k,v in FLAGS.items():self.assertIs(value[k],v)
        self.assertEqual(headers['Cache-Control'],'no-store');self.assertIn('X-V5-Record-SHA256',headers)
        self.assertEqual(self.inventory(),before)
        self.assertNotIn('v5_shadow.hk_preselection_publication',sys.modules)

    def test_missing_binding_explicit_not_configured(self):
        config=copy.deepcopy(self.config);config.pop('m06_hk_preselection_binding')
        status,value,_=self.request(config)
        self.assertEqual(status,200);self.assertEqual(value['status'],'NOT_CONFIGURED')
        self.assertEqual(value['module_id'],'M06_HK_PRESELECTION');self.assertNotIn('artifact',value)
        self.assertFalse(value['model_weights_reverified'])

    def test_reference_mismatch_fails_closed_without_old_payload(self):
        config=copy.deepcopy(self.config);config['m06_hk_preselection_binding']['committed_reference']['artifact_sha256']='0'*64
        status,value,_=self.request(config)
        self.assertEqual(status,409);self.assertEqual(value['status'],'CANNOT_CONFIRM');self.assertNotIn('artifact',value)

    def test_saved_artifact_tamper_rejected_and_no_republication(self):
        path=self.output/self.reference['artifact_relative'];raw=path.read_bytes()
        def replace(data):
            temporary=path.with_name('test-tamper.tmp');temporary.write_bytes(data);os.replace(temporary,path)
        try:
            replace(raw+b' ');before=self.inventory();status,value,_=self.request()
            self.assertEqual(status,409);self.assertNotIn('artifact',value);self.assertEqual(self.inventory(),before)
        finally:replace(raw)

    def test_get_query_cannot_choose_another_date_or_reference(self):
        before=self.inventory()
        for query in ('?target_date=20261009','?reference=latest'):
            status,value,_=self.request(path=ROUTE+query);self.assertEqual(status,409);self.assertNotIn('artifact',value)
        self.assertEqual(self.inventory(),before)

    def test_post_is_readonly_no_writes(self):
        before=self.inventory();status,value,_=self.request(method='POST')
        self.assertEqual(status,405);self.assertEqual(value['reason_codes'],['MODULE_READ_ONLY']);self.assertEqual(self.inventory(),before)

    def test_binding_cannot_attach_to_manager_or_add_runtime_arguments(self):
        from v5_shadow.module_api import _config
        for mutate in (lambda c:c.update(module_id='manager'),lambda c:c['m06_hk_preselection_binding'].update(command='publish'),lambda c:c['m06_hk_preselection_binding'].update(bound_root='relative')):
            value=copy.deepcopy(self.config);mutate(value)
            with self.assertRaises(ValueError):_config(value)

    def test_preserve_existing_source_route_and_generation(self):
        from v5_shadow.source_bundle import run_source_bundle,publish_source_result,STATUS_ROUTE
        from v5_shadow.module_api import read_response,_config
        config=copy.deepcopy(self.config)
        result=run_source_bundle(dict(schema_version='v5.source_bundle.request.v1',data_kind='SYNTHETIC',jobs={}))
        publication=publish_source_result(result,config,expected_generation=None)
        checked,fd=_config(self.config)
        try:record,_=read_response(checked,fd,STATUS_ROUTE,{})
        finally:os.close(fd)
        self.assertEqual(record['payload'],result);self.assertEqual(len(record['payload']['modules']),4)


if __name__=='__main__':unittest.main()

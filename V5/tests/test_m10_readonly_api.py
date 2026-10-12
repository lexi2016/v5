"""Targeted M10 read-only HTTP seam; synthetic immutable records only."""
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
ROUTE='/api/v5/source-bundle/hk-close-review'
BINDING='m10_hk_close_binding'


class M10ReadOnlyAPITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='m10-readonly-api-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        api=self.root/'api';api.mkdir()
        (api/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
        self.config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',
            release_id='m10-readonly-synthetic',data_root=str(api),
            routes=['/api/v5/source-bundle/status','/api/v5/source-bundle/hk-preselection',ROUTE])

    def request(self,config=None,path=ROUTE,method='GET'):
        from v5_shadow.module_api import create_module_server
        server=create_module_server(config or self.config)
        thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            client=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=60)
            client.request(method,path);response=client.getresponse()
            value=json.loads(response.read());status=response.status
            headers=dict(response.getheaders());client.close()
            return status,value,headers
        finally:server.shutdown();thread.join();server.server_close()

    def test_missing_binding_is_not_configured_not_empty_success(self):
        status,value,_=self.request()
        self.assertEqual(status,200,value)
        self.assertEqual(value['status'],'NOT_CONFIGURED')
        self.assertEqual(value['module_id'],'M10_HK_CLOSE_REVIEW')
        self.assertNotIn('review',value)
        for key in ('production_allowed','buy_gate_updated','orders_sent','natural_verified','formal_eligibility_verified'):
            self.assertIs(value[key],False)


    def configure(self,**kwargs):
        from fixtures.hk_close_readonly_factory import create_fixture
        self.binding,self.expected=create_fixture(self.root/'runs',**kwargs)
        self.config[BINDING]=self.binding

    def inventory(self):
        return {str(p.relative_to(self.root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns)
            for p in self.root.rglob('*') if p.is_file()}

    def test_exact_original_projection_preserves_all_rows_nulls_identity_no_writes(self):
        self.configure();before=self.inventory();status,value,headers=self.request()
        self.assertEqual(status,200,value)
        self.assertEqual(value['review'],self.expected['review'])
        self.assertEqual(value['run_id'],self.binding['run_id']);self.assertEqual(value['generation'],self.binding['generation'])
        self.assertEqual(value['native_review_sha256'],self.expected['native_review_sha256'])
        self.assertEqual(value['status'],'PARTIAL');self.assertEqual(value['review']['source_status'],'MODEL_REVIEW_READY')
        self.assertEqual([len(value['review'][key]) for key in ('close_top20','model_rows','stage_rows')],[20,100,70])
        for metric in value['review']['stages'].values():
            self.assertEqual(metric['source_status'],'PARTIAL_WITH_ROWS')
            for key in ('hit_count','coverage','precision','coverage_pct','precision_pct'):self.assertIsNone(metric[key])
        self.assertTrue(all(r['stage_union_hit'] is None and r['classification']=='CANNOT_CONFIRM' for r in value['review']['top20_attribution']))
        self.assertNotIn('input_evidence',value);self.assertNotIn('native_evidence',value)
        self.assertNotIn(str(self.root),json.dumps(value));self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertEqual(self.inventory(),before)
        self.assertNotIn('v5_shadow.hk_close_daily',sys.modules)

    def test_exact_run_does_not_follow_new_latest(self):
        self.configure();first=self.expected
        from fixtures.hk_close_readonly_factory import create_fixture
        newer,_=create_fixture(self.root/'runs',revision=2)
        self.assertNotEqual(newer['run_id'],first['run_id'])
        status,value,_=self.request();self.assertEqual(status,200,value)
        self.assertEqual(value['run_id'],first['run_id']);self.assertEqual(value['review'],first['review'])

    def test_wrong_generation_and_uncommitted_run_reject_without_rows(self):
        self.configure()
        config=copy.deepcopy(self.config);config[BINDING]['generation']='0'*64
        status,value,_=self.request(config);self.assertEqual(status,409);self.assertNotIn('review',value)
        pointer=self.root/'runs/latest_success.json';value=json.loads(pointer.read_bytes())
        value['committed_runs']={};pointer.write_text(json.dumps(value));before=self.inventory()
        status,value,_=self.request();self.assertEqual(status,409);self.assertNotIn('review',value);self.assertEqual(self.inventory(),before)

    def test_payload_receipt_and_manifest_tampering_rejected_without_republish(self):
        self.configure()
        for part in ('payload','publication','manifest','receipt'):
            path=self.root/'runs'/self.binding['run_id']/(part+'.json');raw=path.read_bytes()
            try:
                value=json.loads(raw);value['synthetic_tamper']=True;path.write_text(json.dumps(value));before=self.inventory()
                status,value,_=self.request();self.assertEqual(status,409,(part,value));self.assertNotIn('review',value);self.assertEqual(self.inventory(),before)
            finally:path.write_bytes(raw)

    def test_partial_missing_model_and_verified_empty_are_distinct(self):
        self.configure(stage_status='READY_EMPTY',model=False)
        status,value,_=self.request();self.assertEqual(status,200,value)
        self.assertEqual(len(value['review']['close_top20']),20);self.assertEqual(value['review']['model_rows'],[])
        self.assertTrue(all(metric['source_status']=='READY_EMPTY' for metric in value['review']['stages'].values()))
        self.assertTrue(all(r['model_0_2_hit'] is None for r in value['review']['top20_attribution']))

    def test_query_and_post_cannot_produce_or_switch_run(self):
        self.configure();before=self.inventory()
        for suffix in ('?run_id=latest','?generation='+self.binding['generation'],'?date=20261012'):
            status,value,_=self.request(path=ROUTE+suffix);self.assertEqual(status,409);self.assertNotIn('review',value)
        for method in ('POST','PUT','DELETE'):
            status,_,_=self.request(method=method);self.assertEqual(status,405)
        self.assertEqual(self.inventory(),before)

    def test_config_rejects_other_module_extra_fields_and_invalid_reference(self):
        self.configure()
        from v5_shadow.module_api import _config
        for mutate in (lambda c:c.update(module_id='manager'),lambda c:c[BINDING].update(action='build'),
            lambda c:c[BINDING].update(run_root='relative'),lambda c:c[BINDING].update(run_id='../escape'),
            lambda c:c[BINDING].update(generation='bad')):
            config=copy.deepcopy(self.config);mutate(config)
            with self.assertRaises(ValueError):_config(config)

    def test_source_publication_and_m06_not_configured_survive_third_route(self):
        from v5_shadow.source_bundle import run_source_bundle,publish_source_result,STATUS_ROUTE
        result=run_source_bundle(dict(schema_version='v5.source_bundle.request.v1',data_kind='SYNTHETIC',jobs={}))
        publish_source_result(result,self.config,expected_generation=None)
        status,value,_=self.request(path=STATUS_ROUTE);self.assertEqual(status,200);self.assertEqual(value,result)
        status,value,_=self.request(path='/api/v5/source-bundle/hk-preselection')
        self.assertEqual(status,200);self.assertEqual(value['status'],'NOT_CONFIGURED')


    def test_m10_and_m06_reads_have_independent_single_slots(self):
        self.configure()
        from concurrent.futures import ThreadPoolExecutor
        from unittest.mock import patch
        from v5_shadow.module_api import create_module_server
        import v5_shadow.m06_readonly as m06
        import v5_shadow.m10_readonly as m10
        entered=threading.Event();release=threading.Event()
        original=m06.read_record
        def hold_m06(*args):
            entered.set();release.wait(10);return original(*args)
        server=create_module_server(self.config);thread=threading.Thread(target=server.serve_forever);thread.start()
        def get(path):
            connection=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=20)
            connection.request('GET',path);response=connection.getresponse();value=json.loads(response.read());status=response.status;connection.close();return status,value
        try:
            with patch.object(m06,'read_record',hold_m06),ThreadPoolExecutor(max_workers=2) as pool:
                pending=pool.submit(get,'/api/v5/source-bundle/hk-preselection')
                self.assertTrue(entered.wait(5))
                try:
                    status,value=get(ROUTE);self.assertEqual(status,200,value);self.assertEqual(value['run_id'],self.binding['run_id'])
                finally:release.set()
                self.assertEqual(pending.result()[0],200)
            entered.clear();release.clear();original_m10=m10.read_record
            def hold_m10(*args):
                entered.set();release.wait(10);return original_m10(*args)
            with patch.object(m10,'read_record',hold_m10),ThreadPoolExecutor(max_workers=2) as pool:
                pending=pool.submit(get,ROUTE);self.assertTrue(entered.wait(5))
                try:
                    status,value=get(ROUTE);self.assertEqual(status,503);self.assertEqual(value['reason_codes'],['MODULE_BUSY'])
                finally:release.set()
                self.assertEqual(pending.result()[0],200)
        finally:release.set();server.shutdown();thread.join();server.server_close()


    def test_symlinked_run_root_and_missing_fixed_run_fail_closed(self):
        self.configure();alias=self.root/'alias';alias.symlink_to(self.root/'runs',target_is_directory=True)
        config=copy.deepcopy(self.config);config[BINDING]['run_root']=str(alias)
        status,value,_=self.request(config);self.assertEqual(status,409);self.assertNotIn('review',value)
        config=copy.deepcopy(self.config);config[BINDING]['run_id']='20261012-'+'0'*24
        status,value,_=self.request(config);self.assertEqual(status,409);self.assertNotIn('review',value)

    def test_owner_copy_tamper_rejected_without_changing_original_source(self):
        self.configure()
        import shutil
        from unittest.mock import patch
        import v5_shadow.m10_readonly as bridge
        temporary=self.root/'source-copy';temporary.mkdir()
        shutil.copytree(BASE/'source_owners/m10',temporary/'source_owners/m10')
        (temporary/'contracts').mkdir();shutil.copyfile(bridge.MANIFEST,temporary/'contracts/m10_readonly_runtime.json')
        owner=temporary/'source_owners/m10/V5/src/v5_shadow/hk_close_daily.py';owner.write_bytes(owner.read_bytes()+b'\n# synthetic tamper\n')
        with patch.object(bridge,'BASE',temporary),patch.object(bridge,'MANIFEST',temporary/'contracts/m10_readonly_runtime.json'):
            status,value,_=self.request();self.assertEqual(status,409);self.assertNotIn('review',value)
        status,_,_=self.request();self.assertEqual(status,200)

    def test_timeout_returns_no_paths_or_previous_rows(self):
        self.configure()
        from unittest.mock import patch
        with patch('v5_shadow.m10_readonly.subprocess.run',side_effect=subprocess.TimeoutExpired('PRIVATE_PATH_SENTINEL',30)):
            status,value,_=self.request();self.assertEqual(status,409);self.assertNotIn('review',value)
            self.assertNotIn('PRIVATE_PATH_SENTINEL',json.dumps(value))


    def test_owner_closure_rejects_extra_importable_files(self):
        self.configure()
        import shutil
        from unittest.mock import patch
        import v5_shadow.m10_readonly as bridge
        temporary=self.root/'extra-source-copy';temporary.mkdir()
        shutil.copytree(BASE/'source_owners/m10',temporary/'source_owners/m10')
        (temporary/'contracts').mkdir();shutil.copyfile(bridge.MANIFEST,temporary/'contracts/m10_readonly_runtime.json')
        package=temporary/'source_owners/m10/V5/src/v5_shadow'
        for relative in ('__init__.py','hk_close_daily.pyc','__pycache__/hk_close_daily.cpython-312.pyc'):
            extra=package/relative;extra.parent.mkdir(exist_ok=True);extra.write_bytes(b'# synthetic unlisted file')
            try:
                with patch.object(bridge,'BASE',temporary),patch.object(bridge,'MANIFEST',temporary/'contracts/m10_readonly_runtime.json'):
                    with self.assertRaisesRegex(ValueError,'CLOSURE'):bridge.owner_root()
            finally:extra.unlink()


if __name__=='__main__':unittest.main()

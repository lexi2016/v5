"""New M09 historical-only HTTP seam tests; original suites are not rerun."""
import copy
import hashlib
import http.client
import subprocess
import sys
import json
from pathlib import Path
import tempfile
import threading
import unittest

ROUTE='/api/v5/source-bundle/a-close-replay'
BINDING='m09_a_close_replay_binding'

class M09ReadOnlyAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='m09-p0-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();api=self.root/'api';api.mkdir()
        (api/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
        self.config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',
            release_id='m09-readonly-synthetic',data_root=str(api),routes=['/api/v5/source-bundle/status',
            '/api/v5/source-bundle/hk-preselection','/api/v5/source-bundle/hk-close-review',ROUTE])
    def request(self,config=None,path=ROUTE,method='GET'):
        from v5_shadow.module_api import create_module_server
        server=create_module_server(config or self.config);thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            c=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=60)
            c.request(method,path);r=c.getresponse();value=json.loads(r.read());status=r.status
            headers=dict(r.getheaders());c.close();return status,value,headers
        finally:server.shutdown();thread.join();server.server_close()
    def test_missing_binding_is_explicit_and_does_not_fabricate_review(self):
        status,value,_=self.request()
        self.assertEqual(status,200,value);self.assertEqual(value['status'],'NOT_CONFIGURED')
        self.assertEqual(value['module_id'],'M09_A_CLOSE_REPLAY');self.assertNotIn('review',value)
        self.assertIs(value['research_only'],True);self.assertIs(value['natural_verified'],False)

    def configure(self,**kw):
        from fixtures.a_close_replay_factory import create_fixture
        self.binding,self.expected=create_fixture(self.root/'fixture',**kw);self.config[BINDING]=self.binding
    def inventory(self):
        return {str(p.relative_to(self.root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns)
            for p in self.root.rglob('*') if p.is_file()}
    def test_original_review_identity_gaps_dates_and_no_read_writes(self):
        self.configure();before=self.inventory();status,value,headers=self.request()
        self.assertEqual(status,200,value);self.assertEqual(value['review'],self.expected['review'])
        self.assertEqual(value['identity'],self.expected['identity']);self.assertEqual(value['run_id'],self.binding['run_id'])
        self.assertEqual(value['generation'],self.binding['generation']);self.assertEqual(value['trade_date'],'20261009')
        self.assertEqual(value['status'],'PARTIAL');self.assertEqual(value['execution_kind'],'HISTORICAL_REPLAY')
        self.assertEqual(value['scope'],'OBSERVED_ROWS_ONLY');self.assertEqual(value['data_kind'],'RECORDED_INPUT_REPLAY')
        for key,item in value['publication'].items():self.assertEqual(item,self.expected['publication'][key],key)
        historical=value['publication']['historical_research']
        self.assertEqual(historical['missing_text'],dict(name=1,tdx_industry_code=1,tdx_industry_name=1))
        self.assertEqual(historical['snapshot_row_count'],6);self.assertEqual(historical['nonfinite_unused_close_position'],1)
        self.assertTrue(all(historical[k] is False for k in ('source_time_verified','membership_qualification_verified','natural_verified','strict_1500_pit_verified')))
        self.assertNotIn('latest_attempt',value['publication']);self.assertNotIn('provenance',value['publication'])
        self.assertNotIn(str(self.root),json.dumps(value));self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertEqual(self.inventory(),before);self.assertNotIn('v5_shadow.a_close_daily',sys.modules)
    def test_public_source_metadata_never_exposes_private_original_extra_paths(self):
        private='/Users/private-owner/private-source/history.parquet'
        self.configure(origin_extra=dict(private_path=private,nested_private=dict(root=private)))
        status,value,_=self.request();self.assertEqual(status,200,value)
        self.assertEqual(value['review'],self.expected['review'])
        self.assertNotIn(private,json.dumps(value));self.assertNotIn('private_path',value['publication']['historical_research']['original_source'])
        for key in ('sha256','bytes','format','hash_verified'):
            self.assertEqual(value['publication']['historical_research']['original_source'][key],self.expected['publication']['historical_research']['original_source'][key])
        self.configure(revision=2,origin_extra=dict(format=private))
        status,value,_=self.request();self.assertEqual(status,409);self.assertNotIn(private,json.dumps(value))

    def test_cold_worker_cannot_call_owner_producer_or_source_preparation(self):
        self.configure();before=self.inventory()
        from v5_shadow.m09_readonly import owner_root
        worker=Path(__file__).resolve().parents[1]/'src/v5_shadow/m09_readonly_worker.py'
        code='''import contextlib,io,json,runpy,sys
from pathlib import Path
owner,worker=sys.argv[1:3];sys.path.insert(0,str(Path(owner)/'V5/src'))
from v5_shadow import a_close_daily as d,a_close_historical as h,a_close_daily_sources as f
binding=json.load(sys.stdin)
def forbidden(*args,**kwargs):raise AssertionError('PRODUCER_MUST_NOT_RUN')
d._build=d.run_a_close_daily=forbidden
h.prepare_a_close_historical_snapshot=h.run_a_close_historical=h._write_snapshot=forbidden
f.build_from_admitted_panel=forbidden
load=f.load_frozen_module
def only_reader(name):
 if name.startswith('ops.') or name=='domains.a_share_close_model':raise AssertionError('PRODUCER_MUST_NOT_IMPORT')
 return load(name)
f.load_frozen_module=only_reader
module=runpy.run_path(worker);sys.argv=[worker,owner];sys.stdin=io.TextIOWrapper(io.BytesIO(json.dumps(binding).encode()))
output=io.StringIO()
with contextlib.redirect_stdout(output):module['main']()
assert 'pyarrow' not in sys.modules
print(output.getvalue())
'''
        proc=subprocess.run([sys.executable,'-I','-B','-c',code,str(owner_root()),str(worker)],input=json.dumps(self.binding),capture_output=True,text=True,timeout=50)
        self.assertEqual(proc.returncode,0,proc.stderr);self.assertEqual(json.loads(proc.stdout)['review'],self.expected['review'])
        self.assertEqual(self.inventory(),before)

    def test_reference_ignores_new_product_head_and_separate_attempt(self):
        self.configure();before=self.expected
        from fixtures.a_close_replay_factory import create_fixture
        next_binding,_=create_fixture(self.root/'fixture',revision=2)
        self.assertNotEqual(next_binding['generation'],self.binding['generation'])
        status,value,_=self.request();self.assertEqual(status,200,value)
        self.assertEqual(value['review'],before['review']);self.assertEqual(value['generation'],self.binding['generation'])
        # Even an invalid mutable head cannot change or hide an explicit generation.
        (Path(self.binding['run_root'])/'heads/20261009.json').write_text('invalid mutable head')
        status,value,_=self.request();self.assertEqual(status,200,value);self.assertEqual(value['generation'],self.binding['generation'])
    def test_wrong_run_date_generation_reject_without_fallback(self):
        self.configure()
        for key,new in (('run_id','m09-'+'0'*32+'-'+'0'*12),('generation','0'*64),('trade_date','20261012')):
            config=copy.deepcopy(self.config);config[BINDING][key]=new
            status,value,_=self.request(config);self.assertEqual(status,409,(key,value));self.assertNotIn('review',value)
    def test_product_input_record_generation_and_commit_receipt_tamper_rejected(self):
        self.configure();root=Path(self.binding['run_root']);run=root/'runs'/self.binding['run_id']
        generation=root/'generations'/(self.binding['generation']+'.json')
        gen=json.loads(generation.read_bytes());receipt=root/'attempts'/gen['commit_trigger_sha256']/'receipt.json'
        paths=[run/'record.json',run/'calculation.json',generation,receipt,run/'inputs/admitted_panel.json',
            run/'product/a_share_reviews/20261009.json',run/'product/a_share_reviews/receipts/20261009.json',run/'product/a_share_reviews/manifest.json']
        for path in paths:
            raw=path.read_bytes()
            try:
                changed=json.loads(raw);changed['synthetic_tamper']=True;path.write_text(json.dumps(changed));before=self.inventory();status,value,_=self.request()
                self.assertEqual(status,409,(str(path.relative_to(root)),value));self.assertNotIn('review',value);self.assertEqual(self.inventory(),before)
            finally:path.write_bytes(raw)
    def test_uncommitted_generation_and_wrong_historical_marker_reject(self):
        self.configure();root=Path(self.binding['run_root']);generation=json.loads((root/'generations'/(self.binding['generation']+'.json')).read_bytes())
        receipt=root/'attempts'/generation['commit_trigger_sha256']/'receipt.json';raw=receipt.read_bytes();receipt.unlink()
        status,value,_=self.request();self.assertEqual(status,409);self.assertNotIn('review',value);receipt.write_bytes(raw)
        marker=root/'.v5-m09-historical-root'
        self.assertTrue(marker.exists());marker.write_text('not historical')
        status,value,_=self.request();self.assertEqual(status,409);self.assertNotIn('review',value)
    def test_query_and_mutations_cannot_switch_reference_or_produce(self):
        self.configure();before=self.inventory()
        for suffix in ('?run_id=latest','?generation='+self.binding['generation'],'?date=20261012'):
            status,value,_=self.request(path=ROUTE+suffix);self.assertEqual(status,409);self.assertNotIn('review',value)
        for method in ('POST','PUT','DELETE','PATCH'):
            status,_,_=self.request(method=method);self.assertEqual(status,405)
        self.assertEqual(self.inventory(),before)
    def test_missing_and_symlinked_root_reject(self):
        self.configure();alias=self.root/'alias';alias.symlink_to(self.binding['run_root'],target_is_directory=True)
        for root in (alias,self.root/'missing'):
            config=copy.deepcopy(self.config);config[BINDING]['run_root']=str(root)
            status,value,_=self.request(config);self.assertEqual(status,409);self.assertNotIn('review',value)
    def test_binding_rejects_extra_fields_other_module_and_bad_reference(self):
        self.configure()
        from v5_shadow.module_api import _config
        for change in (lambda c:c.update(module_id='manager'),lambda c:c[BINDING].update(action='build'),
                       lambda c:c[BINDING].update(trade_date='20261033'),lambda c:c[BINDING].update(run_root='relative'),
                       lambda c:c[BINDING].update(run_id='../escape'),lambda c:c[BINDING].update(generation='bad')):
            config=copy.deepcopy(self.config);change(config)
            with self.assertRaises(ValueError):_config(config)
    def test_existing_source_m06_m10_routes_survive(self):
        from v5_shadow.source_bundle import run_source_bundle,publish_source_result,STATUS_ROUTE
        result=run_source_bundle(dict(schema_version='v5.source_bundle.request.v1',data_kind='SYNTHETIC',jobs={}))
        publish_source_result(result,self.config,expected_generation=None)
        status,value,_=self.request(path=STATUS_ROUTE);self.assertEqual(status,200);self.assertEqual(value,result)
        for route in ('hk-preselection','hk-close-review'):
            status,value,_=self.request(path='/api/v5/source-bundle/'+route)
            self.assertEqual(status,200);self.assertEqual(value['status'],'NOT_CONFIGURED')
    def test_distinct_readers_do_not_steal_slots_and_same_reader_is_bounded(self):
        from concurrent.futures import ThreadPoolExecutor
        from unittest.mock import patch
        from v5_shadow.module_api import create_module_server
        import v5_shadow.m09_readonly as m09
        import v5_shadow.m10_readonly as m10
        import v5_shadow.m06_readonly as m06
        entered=threading.Event();release=threading.Event()
        server=create_module_server(self.config);thread=threading.Thread(target=server.serve_forever);thread.start()
        def get(path):
            c=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=20);c.request('GET',path)
            r=c.getresponse();value=json.loads(r.read());status=r.status;c.close();return status,value
        try:
            for module,route in ((m09,ROUTE),(m10,'/api/v5/source-bundle/hk-close-review'),(m06,'/api/v5/source-bundle/hk-preselection')):
                entered.clear();release.clear();original=module.read_record
                def hold(*args):entered.set();release.wait(10);return original(*args)
                with patch.object(module,'read_record',hold),ThreadPoolExecutor(max_workers=2) as pool:
                    pending=pool.submit(get,route);self.assertTrue(entered.wait(5))
                    try:
                        other='/api/v5/source-bundle/hk-close-review' if route==ROUTE else ROUTE
                        self.assertEqual(get(other)[0],200);self.assertEqual(get(route)[0],503)
                    finally:release.set()
                    self.assertEqual(pending.result()[0],200)
        finally:release.set();server.shutdown();thread.join();server.server_close()
    def test_owner_copy_tamper_extra_file_and_timeout_fail_closed(self):
        self.configure()
        import shutil
        from unittest.mock import patch
        import v5_shadow.m09_readonly as bridge
        temporary=self.root/'copy';temporary.mkdir();shutil.copytree(bridge.BASE/'source_owners/m09',temporary/'source_owners/m09')
        (temporary/'contracts').mkdir();shutil.copyfile(bridge.MANIFEST,temporary/'contracts/m09_readonly_runtime.json')
        owner=temporary/'source_owners/m09/V5/src/v5_shadow/a_close_daily.py';raw=owner.read_bytes()
        with patch.object(bridge,'BASE',temporary),patch.object(bridge,'MANIFEST',temporary/'contracts/m09_readonly_runtime.json'):
            owner.write_bytes(raw+b'# tamper');status,value,_=self.request();self.assertEqual(status,409);self.assertNotIn('review',value)
            owner.write_bytes(raw);(owner.parent/'unexpected.py').write_text('raise RuntimeError()')
            status,value,_=self.request();self.assertEqual(status,409);self.assertNotIn('review',value)
        with patch.object(bridge.subprocess,'run',side_effect=subprocess.TimeoutExpired('PRIVATE_PATH_SENTINEL',45)):
            status,value,_=self.request();self.assertEqual(status,409);self.assertNotIn('PRIVATE_PATH_SENTINEL',json.dumps(value))

if __name__=='__main__':unittest.main()

"""P0 M17 GET seam. Only synthetic fixtures; no live collector or deployment.

The regression mutation is removing the M17 binding/route dispatch: success
must then fail rather than falling through to a saved module-response record.
"""
import copy
import hashlib
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE/'src'))
sys.path.insert(0, str(BASE/'tests'))
from test_daily_close_recapture_owner import fixture
from v5_shadow import daily_close_recapture_owner as original
from v5_shadow.digests import canonical_bytes, sha256_json
from v5_shadow.module_api import create_module_server, response_key

ROUTE = '/api/v5/manager/close-recapture'
BINDING = 'm17_close_recapture_binding'
OLD_ROUTES = ['/api/v5/source-bundle/status', '/api/v5/source-bundle/hk-preselection',
              '/api/v5/source-bundle/hk-stage-observed', '/api/v5/source-bundle/a-close-replay',
              '/api/v5/source-bundle/hk-close-review']


class M17ReadonlyAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        data = self.root/'api'; data.mkdir()
        (data/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
        self.config = dict(schema_version='v5.module_api.v1', module_id='source_bundle',
            release_id='p0-m17-synthetic', data_root=str(data), routes=[*OLD_ROUTES, ROUTE])

    def configure(self, partial=False):
        inputs = self.root/'inputs'; inputs.mkdir()
        request, ledger = fixture(inputs)
        if partial:
            request['simulation']['result']['rows'] = request['simulation']['result']['rows'][:2]
            request['simulation']['result']['completed_code_count'] = 2
        result = original.run_close_recapture_daily(request, str(ledger),
            original.bind_close_recapture_owner(request['config']))
        self.assertEqual(result['status'], 'SUCCEEDED', result)
        self.state = result['state']; self.reference = self.state['latest_success']['product_reference']
        self.binding = dict(schema_version='v5.m17.readonly-binding.v1',
            state_root=request['config']['state_root'], universe_root=request['config']['universe_root'],
            ledger_root=str(ledger), python_executable=sys.executable, identity=self.state['identity'],
            run_id=self.state['latest_success']['run_id'], execution_label='MANUAL_RECOVERY',
            operation='EXISTING_VERIFIED_PRODUCT_REUSE')
        self.config[BINDING] = self.binding
        self.query = dict(source_trade_date=request['source_trade_date'], run_id=self.binding['run_id'])
        self.path = ROUTE+'?'+urlencode(self.query)

    def start(self, config=None):
        try:
            server = create_module_server(config or self.config)
        except ValueError as error:
            self.fail('M17 binding/route must be accepted by P0: '+str(error))
        thread = threading.Thread(target=server.serve_forever); thread.start()
        self.addCleanup(server.server_close); self.addCleanup(thread.join); self.addCleanup(server.shutdown)
        return server

    def request(self, server, path=None, method='GET'):
        client = http.client.HTTPConnection('127.0.0.1', server.server_address[1], timeout=60)
        try:
            client.request(method, path or self.path); response = client.getresponse()
            return response.status, json.loads(response.read()), dict(response.getheaders())
        finally: client.close()

    def inventory(self):
        return {str(p.relative_to(self.root)):(hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                for p in self.root.rglob('*') if p.is_file()}

    def test_exact_get_cold_reads_original_rows_and_never_writes(self):
        self.configure(); before = self.inventory(); server = self.start()
        with patch.object(original, 'claim_run', side_effect=AssertionError('claim forbidden')), \
             patch.object(original, 'finish_run', side_effect=AssertionError('finish forbidden')), \
             patch.object(original, 'run_close_recapture_owner', side_effect=AssertionError('owner forbidden')):
            status, value, headers = self.request(server)
            again_status, again, _ = self.request(server)
        self.assertEqual(status, 200, value); self.assertEqual(again_status, 200, again)
        overlay = json.loads((Path(self.binding['state_root']) / self.reference['files']['candidate_overlay']['artifact_ref']).read_bytes())
        self.assertEqual(value['rows'], overlay['rows']); self.assertEqual(value['candidate_count'], 100)
        self.assertEqual(value['identity'], self.binding['identity']); self.assertEqual(value['run_id'], self.query['run_id'])
        self.assertNotEqual(value['reader_pid'], again['reader_pid'])
        for key in ('files','pool','captured_at','available_at','execution_kind'):
            self.assertEqual(value[key], self.reference[key])
        self.assertEqual(value['execution_label'], 'MANUAL_RECOVERY')
        self.assertEqual(value['operation'], 'EXISTING_VERIFIED_PRODUCT_REUSE')
        self.assertIs(value['received_not_historical_1530'], True)
        self.assertIs(value['RESEARCH_ONLY'], True)
        for key in ('production_allowed','buy_gate_updated','orders_sent','natural_verified','formal_eligibility_verified'):
            self.assertIs(value[key], False)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['Content-Type'], 'application/json; charset=utf-8')
        self.assertLessEqual(int(headers['Content-Length']), 256*1024)
        self.assertNotIn(str(self.root), json.dumps(value)); self.assertEqual(self.inventory(), before)

    def test_exact_query_required_no_date_run_or_1530_fallback(self):
        self.configure(); server=self.start(); before=self.inventory()
        invalid=[{}, {'source_trade_date':self.query['source_trade_date']},
            dict(self.query,source_trade_date='20260929'), dict(self.query,run_id='f'*32),
            dict(self.query,source_trade_date='20261399'), dict(self.query,source_trade_date=''),
            dict(self.query,slot='1530'), dict(self.query,limit='100')]
        for query in invalid:
            with self.subTest(query=query):
                status,value,_=self.request(server,ROUTE+'?'+urlencode(query))
                self.assertEqual(status,409,value); self.assertEqual(value['status'],'CANNOT_CONFIRM'); self.assertNotIn('rows',value)
        self.assertEqual(self.request(server,self.path+'&run_id='+self.query['run_id'])[0],400)
        self.assertEqual(self.inventory(),before)

    def test_missing_binding_cannot_fall_back_to_forged_saved_success(self):
        query=dict(source_trade_date='20260928',run_id='a'*32)
        payload={'status':'READY','rows':[]}
        record=dict(schema_version='v5.module_response.v1',module_id='source_bundle',release_id=self.config['release_id'],
            path=ROUTE,query=query,payload=payload,payload_sha256=sha256_json(payload),source_input_sha256='a'*64,
            data_kind='OWNER_RESULT',generated_at='2026-09-28T16:00:00+08:00',status_code=200)
        root=Path(self.config['data_root']); (root/'responses').mkdir()
        (root/'responses'/(response_key('source_bundle',ROUTE,query)+'.json')).write_bytes(canonical_bytes(record))
        status,value,_=self.request(self.start(),ROUTE+'?'+urlencode(query))
        self.assertEqual(status,503,value); self.assertEqual(value['status'],'CANNOT_CONFIRM');self.assertNotIn('rows',value)

    def test_partial_original_result_stays_partial_with_real_gap(self):
        self.configure(partial=True)
        status,value,_=self.request(self.start())
        self.assertEqual(status,200,value);self.assertEqual(value['status'],'PARTIAL')
        self.assertEqual(value['candidate_count'],2)
        self.assertIn('PYTDX_EXHQ_COVERAGE_INCOMPLETE',value['cannot_confirm'])

    def test_damage_after_success_fails_closed_without_stale_rows(self):
        self.configure();server=self.start();self.assertEqual(self.request(server)[0],200)
        product=Path(self.binding['state_root'])/self.reference['files']['receipt']['artifact_ref']
        product.write_bytes(b'{}');before=self.inventory()
        status,value,_=self.request(server)
        self.assertEqual(status,409,value);self.assertEqual(value['status'],'CANNOT_CONFIRM');self.assertNotIn('rows',value)
        self.assertEqual(self.inventory(),before)

    def test_oversize_response_rejected_at_http_boundary(self):
        self.configure();server=self.start()
        from v5_shadow import m17_readonly
        with patch.object(m17_readonly,'MAX_RESPONSE_BYTES',100):
            status,value,_=self.request(server)
        self.assertEqual(status,409,value);self.assertNotIn('rows',value)

    def test_methods_and_other_source_routes_preserved(self):
        self.configure();server=self.start();before=self.inventory()
        for method in ('POST','PUT','PATCH','DELETE','OPTIONS'):
            with self.subTest(method=method):self.assertEqual(self.request(server,method=method)[0],405)
        for route in OLD_ROUTES[1:]:
            status,value,_=self.request(server,route)
            self.assertEqual(status,200,value);self.assertEqual(value['status'],'NOT_CONFIGURED')
        self.assertEqual(self.request(server,'/__v5/module-health')[0],200)
        self.assertEqual(self.request(server,'/api/v5/manager/not-a-route')[0],404)
        self.assertEqual(self.inventory(),before)

    def test_binding_cannot_attach_to_manager_or_unregistered_route(self):
        self.configure()
        for change in (dict(module_id='manager'),dict(routes=OLD_ROUTES)):
            config=copy.deepcopy(self.config);config.update(change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError,'M17_READONLY_HOST_BINDING'):
                create_module_server(config)

    def test_m17_busy_is_bounded_and_does_not_starve_m06(self):
        self.configure();server=self.start()
        from v5_shadow import m17_readonly
        original_get=m17_readonly.get_response; entered=threading.Event();release=threading.Event();result=[]
        def blocked(*args):
            entered.set()
            if not release.wait(5):raise AssertionError('test reader release timeout')
            return original_get(*args)
        with patch.object(m17_readonly,'get_response',side_effect=blocked):
            worker=threading.Thread(target=lambda:result.append(self.request(server)));worker.start()
            try:
                self.assertTrue(entered.wait(5))
                status,value,_=self.request(server)
                self.assertEqual(status,503,value);self.assertEqual(value['reason_codes'],['MODULE_BUSY'])
                self.assertEqual(self.request(server,OLD_ROUTES[1])[0],200)
            finally:release.set();worker.join()
        self.assertEqual(result[0][0],200,result)


if __name__=='__main__':unittest.main(verbosity=2)

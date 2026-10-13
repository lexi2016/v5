"""Synthetic commits made by the original store; never real provider acceptance."""
import hashlib
import http.client
import importlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROUTE='/api/v5/source-bundle/manager-public-research'
DATE='20261012'

class M16SavedIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.m16_readonly'),'M16 saved-result adapter is missing')
        from v5_shadow import m16_readonly
        self.m=m16_readonly
        temp=tempfile.TemporaryDirectory(prefix='v5-m16-saved-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve();self.private=self.root/'m16';self.private.mkdir()
        (self.private/'.m16-private-root.json').write_text('{"module":"M16","private":true,"schema":"v5.private_root.v1"}')
        api=self.root/'api';api.mkdir();(api/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
        self.config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='m16-synthetic',data_root=str(api),routes=[ROUTE])

    def fixture(self):
        from v5_shadow.m16_readonly_worker import owner_components
        from v5_shadow.digests import sha256_json
        components=owner_components();self.store_class=components.store_class
        store=components.store_class(self.private)
        identity='a'*64;job_id='mr-'+DATE+'-'+identity[:32]
        flags=dict(RESEARCH_ONLY=True,production_allowed=False,buy_gate_updated=False,orders_sent=False)
        common=dict(target_trade_date=DATE,stage_id='STAGE_0935_0940',market='HK_CONNECT',cutoff_at='2026-10-12T09:40:00+08:00',input_identity=identity,input_source_sha256='b'*64,input_row_count=1,**flags)
        product=dict(schema_version='v4.manager_research.product.v1',kind='MANAGER_RESEARCH_PRODUCT',status='CANNOT_CONFIRM',rows=[dict(code='HK.00001',name='SYNTHETIC_ONLY',status='CANNOT_CONFIRM',facts=[],reason='SYNTHETIC_NO_PROVIDER',observation=dict(stage_rank=1,source_last_bar_time='2026-10-12 09:40:00'))],cannot_confirm=['SYNTHETIC_NO_PROVIDER'],**common)
        product['summary']={'text':'SYNTHETIC: persisted research only','API_Key':'dummy-secret','nested':{'cookie':'dummy-cookie','safe_note':'kept'}}
        product['source_path']='/private/synthetic-source'
        job=dict(schema_version='v4.manager_research.job.v1',kind='MANAGER_RESEARCH_JOB',job_id=job_id,generation='c'*32,attempt=1,status='QUEUED',owner_pid=123,owner_instance='synthetic',**common)
        store.admit_job(job);job=dict(job,status='CANNOT_CONFIRM')
        receipt=dict(schema_version='v4.manager_research.receipt.v1',job_id=job_id,target_trade_date=DATE,input_identity=identity,status='CANNOT_CONFIRM',provider_id='synthetic-not-called',source_receipt_count=0,**flags)
        store.commit_result(job,product,receipt)
        self.commit=self.private/'.commits'/DATE/(identity+'.json')
        self.binding=dict(private_root=str(self.private),trade_date=DATE,input_identity=identity,job_id=job_id,generation='c'*32,attempt=1,commit_sha256=json.loads(self.commit.read_bytes())['sha256'],commit_file_sha256=hashlib.sha256(self.commit.read_bytes()).hexdigest(),data_kind='SYNTHETIC',python_executable=sys.executable)
        self.config[self.m.BINDING]=self.binding
        return product,job,receipt

    def snapshot(self):
        return {str(p.relative_to(self.root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}

    def request(self,path=ROUTE,method='GET'):
        from v5_shadow.module_api import create_module_server
        server=create_module_server(self.config);thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            client=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=30)
            client.request(method,path);response=client.getresponse();value=json.loads(response.read());client.close()
            return response.status,value,dict(response.getheaders())
        finally:server.shutdown();thread.join();server.server_close()

    def repin(self,change,inner=True):
        from v5_shadow.digests import sha256_json
        value=json.loads(self.commit.read_bytes());change(value)
        if inner:value['sha256']=sha256_json({k:v for k,v in value.items() if k!='sha256'})
        self.commit.write_text(json.dumps(value));self.binding['commit_sha256']=value['sha256'];self.binding['commit_file_sha256']=hashlib.sha256(self.commit.read_bytes()).hexdigest()

    def test_missing_binding_waits_without_writes(self):
        before=self.snapshot();status,value,_=self.request()
        self.assertEqual(status,200,value);self.assertEqual(value['status'],'WAITING');self.assertFalse(value['can_execute'])
        self.assertNotIn('product',value);self.assertEqual(before,self.snapshot())

    def test_original_commit_is_read_and_business_status_is_preserved(self):
        product,job,receipt=self.fixture();before=self.snapshot();status,value,headers=self.request(ROUTE+'?trade_date='+DATE)
        self.assertEqual(status,200,value);self.assertEqual(value['status'],'SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED')
        self.assertEqual(value['business_status'],'CANNOT_CONFIRM');self.assertEqual(value['product']['rows'][0]['name'],'SYNTHETIC_ONLY')
        self.assertEqual(value['job']['attempt'],1);self.assertEqual(value['receipt']['source_receipt_count'],0)
        self.assertEqual(value['reference']['commit_sha256'],self.binding['commit_sha256'])
        from v5_shadow.digests import sha256_json
        self.assertEqual(value['reference']['product_sha256'],sha256_json(product))
        self.assertEqual(value['reference']['job_sha256'],sha256_json(job))
        self.assertEqual(value['reference']['receipt_sha256'],sha256_json(receipt))
        self.assertEqual(value['evidence_status'],'VERIFIED_PERSISTENCE_ONLY');self.assertFalse(value['natural_verified'])
        self.assertFalse(value['can_execute']);self.assertTrue(value['read_only']);self.assertEqual(value['data_kind'],'SYNTHETIC')
        rendered=json.dumps(value);self.assertNotIn('dummy-secret',rendered);self.assertNotIn('dummy-cookie',rendered);self.assertNotIn('/private',rendered);self.assertNotIn('owner_pid',rendered);self.assertEqual(value['receipt']['provider_id'],'synthetic-not-called')
        self.assertEqual(headers['Cache-Control'],'no-store');self.assertEqual(before,self.snapshot())

    def test_get_never_constructs_store_or_calls_provider_or_service(self):
        self.fixture()
        from v5_shadow.m16_readonly_worker import project,owner_components
        c=owner_components()
        constructors = {c.store_class.__init__.__code__, c.service_class.__init__.__code__, c.provider_class.__init__.__code__}
        calls = []
        def observe(frame, event, arg):
            if event == 'call' and frame.f_code in constructors:
                calls.append(frame.f_code.co_name)
        previous = sys.getprofile()
        try:
            sys.setprofile(observe)
            with patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden')):
                self.assertEqual(project(self.binding)['status'], 'SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED')
        finally:
            sys.setprofile(previous)
        self.assertEqual(calls, [])

    def test_original_verifier_consumes_the_exact_bounded_bytes(self):
        self.fixture()
        from v5_shadow.m16_readonly_worker import project
        actual=self.store_class._read_commit;seen=[]
        def observed(store,date,identity):
            seen.append(store._io.read_bytes(f'.commits/{date}/{identity}.json'))
            return actual(store,date,identity)
        with patch.object(self.store_class,'_read_commit',observed):result=project(self.binding)
        self.assertEqual(seen,[self.commit.read_bytes()]);self.assertEqual(result['status'],'SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED')

    def test_altered_original_verifier_output_is_rejected(self):
        self.fixture()
        from v5_shadow.m16_readonly_worker import project
        actual=self.store_class._read_commit
        def altered(store,date,identity):
            value=actual(store,date,identity);value['product']['status']='READY';return value
        with patch.object(self.store_class,'_read_commit',altered):
            with self.assertRaisesRegex(ValueError,'PINNED'):project(self.binding)

    def test_plain_legacy_products_and_receipts_are_not_commit_success(self):
        self.fixture();self.commit.rename(self.commit.with_name('legacy.json'))
        status,value,_=self.request();self.assertEqual(status,200);self.assertEqual(value['status'],'WAITING');self.assertNotIn('product',value)

    def test_other_date_waits_without_exposing_bound_date_content(self):
        self.fixture();status,value,_=self.request(ROUTE+'?trade_date=20261013')
        self.assertEqual(status,200);self.assertEqual(value['status'],'WAITING');self.assertNotIn('product',value)

    def test_raw_commit_pin_mismatch_is_cannot_confirm(self):
        self.fixture();self.binding['commit_file_sha256']='0'*64
        status,value,_=self.request();self.assertEqual(status,200);self.assertEqual(value['status'],'CANNOT_CONFIRM');self.assertNotIn('product',value)

    def test_inner_commit_integrity_is_checked_even_after_repin(self):
        self.fixture();self.repin(lambda v:v['product'].update(status='READY'),inner=False)
        self.assertEqual(self.request()[1]['status'],'CANNOT_CONFIRM')

    def test_job_attempt_generation_and_identity_are_exact(self):
        self.fixture()
        for field,value in [('attempt',2),('generation','d'*32),('job_id','mr-'+DATE+'-'+'e'*32),('input_identity','e'*64)]:
            prior=self.binding[field];self.binding[field]=value
            status,payload,_=self.request();self.assertEqual(status,200);self.assertIn(payload['status'],['CANNOT_CONFIRM','WAITING']);self.assertNotIn('product',payload)
            self.binding[field]=prior

    def test_cross_date_commit_members_rejected(self):
        self.fixture();self.repin(lambda v:v['receipts'][self.binding['job_id']].update(target_trade_date='20261013'))
        self.assertEqual(self.request()[1]['status'],'CANNOT_CONFIRM')

    def test_uncommitted_running_job_not_promoted(self):
        self.fixture();self.repin(lambda v:v['jobs'][self.binding['job_id']].update(status='RUNNING'))
        self.assertEqual(self.request()[1]['status'],'CANNOT_CONFIRM')

    def test_private_root_marker_required(self):
        self.fixture();(self.private/'.m16-private-root.json').write_text('{"module":"V4"}')
        self.assertEqual(self.request()[1]['status'],'CANNOT_CONFIRM')

    def test_symlink_and_oversized_commit_rejected(self):
        self.fixture();real=self.commit.with_suffix('.saved');self.commit.rename(real);self.commit.symlink_to(real)
        self.assertEqual(self.request()[1]['status'],'CANNOT_CONFIRM')
        self.commit.unlink();real.rename(self.commit)
        from v5_shadow.m16_readonly_worker import project
        with patch('v5_shadow.m16_readonly_worker.MAX_BYTES',32):
            with self.assertRaisesRegex(ValueError,'READ_LIMIT'):project(self.binding)

    def test_unsafe_claim_in_repinned_product_rejected(self):
        self.fixture();self.repin(lambda v:v['product'].update(orders_sent=True))
        self.assertEqual(self.request()[1]['status'],'CANNOT_CONFIRM')

    def test_parent_runtime_pin_and_timeout_fail_closed(self):
        self.fixture()
        with patch.object(self.m,'RUNTIME_SHA256','0'*64):self.assertEqual(self.request()[1]['status'],'CANNOT_CONFIRM')
        with patch.object(self.m.subprocess,'run',side_effect=subprocess.TimeoutExpired('reader',30)):
            self.assertEqual(self.request()[1]['status'],'CANNOT_CONFIRM')

    def test_unexpected_query_and_posts_remain_rejected(self):
        self.fixture();self.assertEqual(self.request(ROUTE+'?root=anything')[0],409)
        for method in ['POST','PUT','DELETE']:self.assertEqual(self.request(method=method)[0],405)

    def test_original_partial_rows_and_public_source_provenance_survive(self):
        self.fixture()
        def partial(value):
            product = value['product'];job = value['jobs'][self.binding['job_id']];receipt = value['receipts'][self.binding['job_id']]
            product.update(status='PARTIAL_WITH_ROWS', input_row_count=10)
            product['rows'] = [dict(product['rows'][0], code=f'HK.{index:05d}') for index in range(1,11)]
            product['source_receipts'] = [dict(provider_id='v4.hkex.official_titlesearch.v1', status='PARSED', sha256='d'*64, url='https://www.hkexnews.hk/synthetic-only.pdf') for _ in range(10)]
            job.update(status='PARTIAL_WITH_ROWS', input_row_count=10)
            receipt.update(status='PARTIAL_WITH_ROWS', source_receipt_count=10)
        self.repin(partial)
        result = self.request()[1]
        self.assertEqual(result['business_status'], 'PARTIAL_WITH_ROWS')
        self.assertEqual(len(result['product']['rows']), 10)
        self.assertEqual(result['product']['source_receipts'][0]['provider_id'], 'v4.hkex.official_titlesearch.v1')
        self.assertNotIn('attempt', result['receipt']);self.assertNotIn('generation', result['receipt'])

    def test_original_event_refresh_receipt_keeps_distinct_business_status(self):
        product, job, receipt = self.fixture()
        store = self.store_class(self.private)
        refresh = dict(job, job_id=job['job_id']+'-events', mode='EVENT_REFRESH', status='QUEUED')
        store.admit_job(refresh)
        refresh.update(status='READY')
        refresh_receipt = dict(receipt, schema_version='v4.manager_research.catalyst_receipt.v1', job_id=refresh['job_id'], status='READY')
        store.commit_result(refresh, product, refresh_receipt, merge=lambda latest: latest)
        self.binding.update(job_id=refresh['job_id'], commit_sha256=json.loads(self.commit.read_bytes())['sha256'], commit_file_sha256=hashlib.sha256(self.commit.read_bytes()).hexdigest())
        result = self.request()[1]
        self.assertEqual(result['status'], 'SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED')
        self.assertEqual(result['business_status'], 'CANNOT_CONFIRM')
        self.assertEqual(result['job']['status'], 'READY')
        self.assertEqual(result['receipt']['schema_version'], 'v4.manager_research.catalyst_receipt.v1')

    def test_explicit_receipt_attempt_and_generation_conflicts_are_rejected(self):
        self.fixture()
        self.repin(lambda value: value['receipts'][self.binding['job_id']].update(attempt=2))
        self.assertEqual(self.request()[1]['status'], 'CANNOT_CONFIRM')
        self.repin(lambda value: value['receipts'][self.binding['job_id']].update(attempt=1,generation='e'*32))
        self.assertEqual(self.request()[1]['status'], 'CANNOT_CONFIRM')

    def test_canonical_pin_is_not_interchangeable_with_raw_file_pin(self):
        self.fixture();self.binding['commit_sha256'] = self.binding['commit_file_sha256']
        self.assertEqual(self.request()[1]['status'], 'CANNOT_CONFIRM')

    def test_original_manager_safety_checks_nested_trading_claims(self):
        self.fixture()
        for nested in [{'ORDER_ALLOWED': True}, {'RESEARCH_ONLY': False}, {'action': 'BUY'}]:
            self.repin(lambda value: value['product'].update(untrusted_metadata=nested))
            self.assertEqual(self.request()[1]['status'], 'CANNOT_CONFIRM', nested)

    def test_public_projection_hides_url_credentials_and_local_paths(self):
        self.fixture()
        self.repin(lambda value: value['product'].update(source_url='https://demo:dummy-pass@example.test/a.pdf', source_receipts=[{'url':'https://example.test/a.pdf?access_token=dummy-access'}], note='/var/lib/owner/private.json'))
        result = self.request()[1];text = json.dumps(result)
        self.assertEqual(result['status'], 'SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED')
        for secret in ('dummy-pass', 'dummy-access', '/var/lib/owner'):
            self.assertNotIn(secret, text)

    def test_mixed_case_natural_verification_claim_is_rejected(self):
        self.fixture();self.repin(lambda value: value['product'].update(Natural_Verified=True))
        self.assertEqual(self.request()[1]['status'], 'CANNOT_CONFIRM')

    def test_child_response_contract_fails_closed_without_leaking_content(self):
        self.fixture()
        from v5_shadow.m16_readonly_worker import project, unavailable
        good = project(self.binding)
        cases = [dict(good, product=[]), dict(good, job=None), dict(good, reason_codes=[]), dict(good, reference=[]), dict(unavailable('MISSING'), data_kind='OWNER_RESULT')]
        for payload in cases:
            process = subprocess.CompletedProcess([], 0, json.dumps(payload).encode(), b'')
            with patch.object(self.m.subprocess, 'run', return_value=process):
                status, result, _ = self.request()
            self.assertEqual(status, 200);self.assertEqual(result['status'], 'CANNOT_CONFIRM');self.assertNotIn('product', result)

    def test_second_m16_reader_is_rejected_while_first_is_active(self):
        from v5_shadow.module_api import create_module_server
        entered=threading.Event();release=threading.Event();real=self.m.read_record
        def blocked(config, query):
            entered.set();release.wait(5);return real(config, query)
        server=create_module_server(self.config);thread=threading.Thread(target=server.serve_forever);thread.start()
        port=server.server_address[1];first=[]
        def call():
            client=http.client.HTTPConnection('127.0.0.1',port,timeout=10);client.request('GET',ROUTE);response=client.getresponse();first.append(response.status);response.read();client.close()
        try:
            with patch.object(self.m, 'read_record', blocked):
                running=threading.Thread(target=call);running.start();self.assertTrue(entered.wait(3))
                client=http.client.HTTPConnection('127.0.0.1',port,timeout=3);client.request('GET',ROUTE);response=client.getresponse();status=response.status;response.read();client.close()
                release.set();running.join(5)
            self.assertEqual(status,503);self.assertEqual(first,[200])
        finally:
            release.set();server.shutdown();thread.join();server.server_close()

    def test_registry_truthfully_declares_read_only_capability(self):
        from v5_shadow.main_registry import registry_by_id
        entry=registry_by_id()['M16_PUBLIC_RESEARCH']
        self.assertEqual(entry.owner_entry,'manager_factory.build_manager_jobs')
        self.assertEqual(entry.runtime,'m16_readonly');self.assertEqual(entry.status,'READ_ONLY_SAVED_REQUIRES_BINDING')
        from v5_shadow.manager_factory import build_manager_jobs
        self.assertTrue(callable(build_manager_jobs))

if __name__=='__main__':unittest.main()

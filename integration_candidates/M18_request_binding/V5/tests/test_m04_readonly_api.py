"""M04 exact historical archive seam. All fixture article content is synthetic."""
import ast
import copy
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from v5_shadow.digests import canonical_bytes, sha256_json

BASE=Path(__file__).resolve().parents[1]
ROUTE='/api/v5/source-bundle/research-intelligence'

class M04ReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.m04_readonly'), 'M04 read-only adapter is missing')
        from v5_shadow import m04_readonly as m
        self.m=m
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.archive=self.root/'archive';self.archive.mkdir()
        (self.archive/'.v5-m04-saved-root').write_text('v5.m04-saved-reference.v1\n')
        api=self.root/'api';api.mkdir();(api/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
        self.config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='m04-synthetic',data_root=str(api),routes=[ROUTE])
        self.config[m.BINDING]=dict(archive_root=str(self.archive),python_executable=sys.executable)
        tree=ast.parse((BASE/'vendor/archive_reader_baseline/contracts/research.py').read_text())
        fields={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('_ARTICLE_FIELDS','_POOL_FIELDS','DEDUPE_KEY_FIELDS')}
        articles=[]
        for i in range(18):
            a={k:'' for k in fields['_ARTICLE_FIELDS']}
            a.update(article_id=hashlib.sha256(str(i).encode()).hexdigest(),dedupe_key=hashlib.sha256(('dedupe'+str(i)).encode()).hexdigest(),source_path_sha256='c'*64,archive_date='20261012',stock_code='00001.HK',stock_name='SYNTHETIC',source_title='Synthetic saved research '+str(i),theme='Synthetic theme',published_at='2026-10-12T08:00:00+08:00',collected_at='2026-10-12T21:00:00+08:00',first_seen_at='2026-10-12T21:00:00+08:00',recommendation_status='RESEARCH_ONLY',duplicate_evidence_count=1,source_dedup_keys=['synthetic'])
            articles.append(a)
        pool={k:'' for k in fields['_POOL_FIELDS']};pool.update(stock_code='00001.HK',archive_date='20261012',first_seen_at=articles[0]['first_seen_at'],collected_at=articles[0]['collected_at'],recommendation_status='RESEARCH_ONLY',source_types=[],themes=[],top_catalysts=[])
        self.payload=dict(schema_version='v3_5.research_archive.v1',archive_date='20261012',status='READY',timezone='Asia/Shanghai',source_input_sha256='d'*64,source_schema_version='SYNTHETIC',source_generated_at=articles[0]['collected_at'],dedupe_key_fields=list(fields['DEDUPE_KEY_FIELDS']),article_count=18,stock_pool_count=1,source_counts={},articles=articles,stock_pool=[pool],cannot_confirm=['SYNTHETIC'],write_policy='read_only',recommendation_status='RESEARCH_ONLY',production_allowed=False,buy_gate_updated=False,orders_sent=False)
        rel='research/archives/20261012.json'
        receipt=dict(schema_version='v3_5.research_archive_receipt.v1',archive_date='20261012',payload_path=rel,payload_sha256=sha256_json(self.payload),source_input_sha256='d'*64,article_count=18,stock_pool_count=1,production_allowed=False,buy_gate_updated=False,orders_sent=False)
        self.files={}
        self.put(rel,self.payload);self.put('receipts/'+rel,receipt)
        self.put('manifest.json',{rel:sha256_json(self.payload),'research/archives/20261011.json':'e'*64})
        self.pins=patch.object(m,'FILES',self.files);self.pins.start();self.addCleanup(self.pins.stop)
        count=patch.object(m,'EXPECTED_OUT_OF_SAMPLE_ERRORS',1,create=True);count.start();self.addCleanup(count.stop)

    def put(self,name,value):
        path=self.archive/name;path.parent.mkdir(parents=True,exist_ok=True);raw=canonical_bytes(value);path.write_bytes(raw);self.files[name]=hashlib.sha256(raw).hexdigest()

    def snapshot(self):
        return {str(p.relative_to(self.root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}

    def request(self,path=ROUTE,method='GET'):
        from v5_shadow.module_api import create_module_server
        server=create_module_server(self.config);thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            client=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=30)
            client.request(method,path);r=client.getresponse();result=(r.status,json.loads(r.read()),dict(r.getheaders()));client.close();return result
        finally:server.shutdown();thread.join();server.server_close()

    def test_original_cold_reader_preserves_18_articles_and_missing_clocks_without_writes(self):
        before=self.snapshot();status,value,headers=self.request()
        self.assertEqual(status,200,value);self.assertEqual(value['archive'],self.payload)
        self.assertEqual(value['article_count'],18);self.assertEqual(value['missing_retrieved_at'],18);self.assertEqual(value['missing_available_at'],18)
        self.assertEqual(value['pit'],'UNKNOWN');self.assertEqual(value['out_of_sample_record_errors'],1)
        self.assertEqual(value['reference']['source_run_id'],'hip-49cb26f7f3a0661bde1d1440')
        self.assertEqual(headers['Cache-Control'],'no-store');self.assertNotIn(str(self.root),json.dumps(value))
        self.assertEqual(before,self.snapshot())
        for key in ('natural_verified','historical_pit_claimed','production_allowed','buy_gate_updated','orders_sent','formal_eligibility_verified'):self.assertIs(value[key],False)
        self.assertNotIn('v5_shadow.archive_reader',sys.modules)

    def test_missing_binding_reports_not_configured(self):
        del self.config[self.m.BINDING];status,value,_=self.request()
        self.assertEqual(status,200);self.assertEqual(value['status'],'NOT_CONFIGURED');self.assertNotIn('archive',value)

    def test_each_get_cold_reads_exact_reference_and_ignores_latest(self):
        first=self.request();(self.root/'latest.json').write_text('{"run_id":"other"}')
        second=self.request();self.assertEqual(first[1],second[1]);self.assertEqual(second[0],200)

    def test_undeclared_root_files_are_rejected_before_original_reader(self):
        (self.archive/'latest.json').write_text('{}')
        with patch.object(self.m.subprocess,'run',side_effect=AssertionError('reader must not start')):
            self.assertEqual(self.request()[0],409)

    def test_unexpected_sample_outcome_is_rejected(self):
        with patch.object(self.m,'EXPECTED_OUT_OF_SAMPLE_ERRORS',53):
            self.assertEqual(self.request()[0],409)

    def test_payload_tamper_rejected_before_original_reader(self):
        (self.archive/'research/archives/20261012.json').write_text('{}')
        with patch.object(self.m.subprocess,'run',side_effect=AssertionError('reader must not start')):
            status,value,_=self.request()
        self.assertEqual(status,409);self.assertEqual(value['status'],'CANNOT_CONFIRM')

    def test_receipt_semantic_tamper_is_rejected_by_original_reader(self):
        rel='receipts/research/archives/20261012.json';receipt=json.loads((self.archive/rel).read_bytes());receipt['article_count']=99;self.put(rel,receipt)
        status,value,_=self.request();self.assertEqual(status,409);self.assertEqual(value['status'],'CANNOT_CONFIRM')

    def test_query_selector_and_mutating_methods_rejected(self):
        self.assertEqual(self.request(ROUTE+'?run_id=latest')[0],409)
        for method in ('POST','PUT','PATCH','DELETE','HEAD'):
            if method=='HEAD':continue
            self.assertEqual(self.request(method=method)[0],405)

    def test_missing_file_never_becomes_empty_success(self):
        (self.archive/'receipts/research/archives/20261012.json').unlink();status,value,_=self.request()
        self.assertIn(status,(409,503));self.assertEqual(value['status'],'CANNOT_CONFIRM')

    def test_wrong_root_marker_and_symlink_rejected(self):
        (self.archive/'.v5-m04-saved-root').write_text('wrong')
        self.assertEqual(self.request()[0],409)
        (self.archive/'.v5-m04-saved-root').write_text('v5.m04-saved-reference.v1\n')
        link=self.root/'alias';link.symlink_to(self.archive,target_is_directory=True)
        self.config[self.m.BINDING]['archive_root']=str(link)
        self.assertEqual(self.request()[0],409)

    def test_runtime_closure_tamper_fails_before_execution(self):
        with patch.object(self.m,'RUNTIME_SHA256','0'*64),patch.object(self.m.subprocess,'run',side_effect=AssertionError('reader must not start')):
            self.assertEqual(self.request()[0],409)

    def test_reader_timeout_releases_slot_and_next_get_recovers(self):
        from v5_shadow.module_api import create_module_server
        server=create_module_server(self.config);thread=threading.Thread(target=server.serve_forever);thread.start()
        def get():
            client=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=30)
            client.request('GET',ROUTE);response=client.getresponse();value=json.loads(response.read());client.close();return response.status,value
        try:
            with patch.object(self.m.subprocess,'run',side_effect=self.m.subprocess.TimeoutExpired('original-reader',30)):
                self.assertEqual(get()[0],409)
            self.assertEqual(get()[0],200)
        finally:server.shutdown();thread.join();server.server_close()

    def test_fixed_identity_cannot_be_selected_from_http_or_config(self):
        self.config[self.m.BINDING]['files']={}
        with self.assertRaises(ValueError):self.request()

if __name__=='__main__':unittest.main()

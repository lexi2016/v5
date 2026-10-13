"""Single-row saved result admission with real owner/store and offline bytes."""
from copy import deepcopy
from hashlib import sha256
import importlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from support import observation,write_input,wait_terminal,offline_error,file_snapshot
import test_temporary_counter as counter_fixture
from test_receipt_recovery import p0_modules
from v5_shadow.manager_loader import load_owner
from v5_shadow.manager_jobs import ManagerJobs
from v5_shadow.m16_runtime import closure,PinnedObservationReader
from v5_shadow.m16_reparse_saved import import_saved_provider_result
DATE='20261012'
class SavedProviderImportTests(unittest.TestCase):
    transport=counter_fixture.TemporaryCounterTests.transport
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.c=load_owner(closure())['components'];self.contracts=importlib.import_module('m16_owner_manager_research.contracts')
        self.ports=importlib.import_module('m16_owner_manager_research.ports');self.calls=[];self.mapping=[]
        self.directory_code='02670';self.published='24/09/2026 06:30'
        for target in ('socket.create_connection','socket.socket.connect','urllib.request.urlopen','urllib.request.OpenerDirector.open'):
            guard=patch(target,side_effect=AssertionError('NO_NETWORK'));guard.start();self.addCleanup(guard.stop)
        value=observation();value['target_trade_date']=DATE
        row=value['rows'][0];row.update(code='HK.02915',name='YUNJI-OLD',source_last_bar_time='2026-10-12 09:40:00')
        for i in range(9):other=deepcopy(row);other.update(code=f'HK.{1000+i:05}',stage_rank=i+2);value['rows'].append(other)
        self.path,self.sha=write_input(self.root,value);self.runtime=self.root/'runtime'
        self.store=self.c.store_class(self.runtime);self.materials=self.c.material_store_class(self.runtime/'materials')
        provider=self.c.provider_class(transport=self.transport,material_store=self.materials,eastmoney_transport=offline_error)
        service=self.c.service_class(self.store,PinnedObservationReader(self.path,self.sha),provider,reader_fetcher=offline_error);self.addCleanup(service.close)
        job=service.ensure(DATE)['job'];wait_terminal(ManagerJobs(service=service),job['job_id'],DATE)
        self.data=service._read_input(DATE);self.before=self.store._read_commit(DATE,self.data['input_identity'])
        self.raw=self.store._io.read_bytes(f".commits/{DATE}/{self.data['input_identity']}.json")
        self.mapping=[{'c':'02670','i':'123','n':'YUNJI'}]
        # Separate original provider, existing saved material cache, offline transport.
        provider=self.c.provider_class(transport=self.transport,material_store=self.materials,eastmoney_transport=offline_error)
        # The empty mapping from the seed is cached: clear synthetic cache via a
        # new cache namespace is not needed; preload the original active mapping seam.
        with patch.object(provider,'_load_active_stocks',return_value=({'02670':{'mapping_code':'02670','stock_id':'123','issuer':'YUNJI'}},'a'*64,'2026-10-13T10:00:00+08:00')):
            self.result=provider.collect(target_trade_date=DATE,cutoff_at=self.data['cutoff_at'],observation=self.data['rows'][0])
        self.result_path=self.root/'provider-result.json';self.save_result()
        self.args=dict(runtime_root=self.runtime,input_path=self.path,input_sha256=self.sha,target_trade_date=DATE,
            expected_product_sha256=self.contracts.sha256_json(self.before['product']),expected_commit_sha256=self.before['sha256'],
            expected_commit_file_sha256=sha256(self.raw).hexdigest(),source_result_path=self.result_path,source_result_sha256=sha256(self.result_path.read_bytes()).hexdigest())
        (self.runtime/'.m16-private-root.json').write_text(json.dumps({'module':'M16','private':True,'schema':'v5.private_root.v1'}))
    def save_result(self):self.result_path.write_text(json.dumps(self.result,ensure_ascii=False))
    def invoke(self,**changes):return import_saved_provider_result(**{**self.args,**changes})
    def test_preview_and_original_p0_worker_apply(self):
        snapshot=file_snapshot(self.runtime);calls=len(self.calls)
        self.assertFalse(self.invoke()['applied']);self.assertEqual(file_snapshot(self.runtime),snapshot)
        applied=self.invoke(apply=True);commit=self.store._read_commit(DATE,self.data['input_identity']);product=commit['product']
        self.assertEqual(product['rows'][0]['status'],'READY');self.assertEqual(product['rows'][0]['issuer'],'YUNJI');self.assertEqual(product['rows'][1:],self.before['product']['rows'][1:])
        for key in ('input_identity','cutoff_at','generated_at','historical_system_available','catalyst_source_receipts'):
            self.assertEqual(product.get(key),self.before['product'].get(key))
        for key in ('jobs','receipts'):
            for name,value in self.before[key].items():self.assertEqual(commit[key][name],value)
        self.assertEqual(self.store._io.read_bytes('.provider-import/'+sha256(self.raw).hexdigest()+'.json'),self.raw)
        oldrow=self.before['product']['rows'][0];newrow=product['rows'][0]
        for key in ('observation','stage_observation','formal_eligible','source_receipts'):
            self.assertEqual(newrow.get(key),oldrow.get(key))
        for key,value in oldrow.get('catalyst_result',{}).items():
            if key not in {'financial_counterevidence','financial_counterevidence_refs','financial_re_evaluation'}:
                self.assertEqual(newrow['catalyst_result'].get(key),value)
        worker,readonly,digests=p0_modules();job=commit['jobs'][applied['job_id']]
        binding=dict(private_root=str(self.runtime),trade_date=DATE,input_identity=self.data['input_identity'],job_id=job['job_id'],generation=job['generation'],attempt=job['attempt'],commit_sha256=commit['sha256'],commit_file_sha256=sha256(self.store._io.read_bytes(f".commits/{DATE}/{self.data['input_identity']}.json")).hexdigest(),data_kind='SYNTHETIC',python_executable=sys.executable)
        with patch.object(worker,'owner_components',return_value=self.c),patch.dict(sys.modules,{'v5_shadow.m16_readonly':readonly,'v5_shadow.digests':digests}):projected=worker.project(binding)
        self.assertEqual(projected['receipt']['status'],projected['job']['status']);self.assertEqual(len(self.calls),calls)
        self.assertEqual(projected['receipt']['pdf_parse_calls'],0)
    def test_pin_negatives(self):
        for key in ('input_sha256','expected_product_sha256','expected_commit_sha256','expected_commit_file_sha256','source_result_sha256'):
            with self.subTest(key=key),self.assertRaises(ValueError):self.invoke(**{key:'0'*64},apply=True)
        self.assertEqual(self.store._read_commit(DATE,self.data['input_identity']),self.before)
    def test_source_relationship_time_and_facts_negatives(self):
        original=deepcopy(self.result)
        for key,value in [('issuer_code','HK.02670'),('issuer_document_code','HK.00928'),('published_at','2026-10-12T09:41:00+08:00'),('issuer_relationship',{}),('sha256','0'*64)]:
            self.result=deepcopy(original);self.result['source'][key]=value;self.save_result()
            with self.subTest(key=key),self.assertRaises(ValueError):self.invoke(source_result_sha256=sha256(self.result_path.read_bytes()).hexdigest(),apply=True)
        self.result=deepcopy(original);self.result['facts'][0]['value']='FORGED';self.save_result()
        with self.assertRaisesRegex(ValueError,'FACT_CACHE_BINDING'):self.invoke(source_result_sha256=sha256(self.result_path.read_bytes()).hexdigest())
    def test_missing_cache_never_parses(self):
        with patch.object(self.materials.__class__,'_parsed_relative',return_value='parsed/not-found.json'),self.assertRaisesRegex(ValueError,'CURRENT_PARSE_CACHE_REQUIRED'):self.invoke(apply=True)
        self.assertEqual(self.store._read_commit(DATE,self.data['input_identity']),self.before)
    def test_cancel_and_receipt_failure_preserve_commit(self):
        original=self.store.__class__.commit_result
        def cancel(store,job,product,receipt,**kwargs):store.cancel_job(job['job_id'],DATE);return original(store,job,product,receipt,**kwargs)
        with patch.object(self.store.__class__,'commit_result',cancel),self.assertRaises(Exception):self.invoke(apply=True)
        self.assertEqual(self.store._read_commit(DATE,self.data['input_identity']),self.before)
        with patch.object(self.store.__class__,'write_receipt',side_effect=OSError('FAIL')),self.assertRaises(OSError):self.invoke(apply=True)
        self.assertEqual(self.store._read_commit(DATE,self.data['input_identity']),self.before)

    def test_same_product_new_commit_race_fenced(self):
        original=self.store.__class__.commit_result
        def race(store,job,product,receipt,**kwargs):
            other=deepcopy(job);other.update(job_id=job['job_id']+'-race',generation='synthetic-race',attempt=1,status='QUEUED')
            store.admit_job(other);other['status']=self.before['product']['status']
            original(store,other,self.before['product'],dict(receipt,job_id=other['job_id'],status=other['status']))
            return original(store,job,product,receipt,**kwargs)
        with patch.object(self.store.__class__,'commit_result',race),self.assertRaisesRegex(ValueError,'COMMIT_CHANGED'):self.invoke(apply=True)
        self.assertEqual(self.store.read_product(DATE,self.data['input_identity']),self.before['product'])

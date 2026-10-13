"""Recovery integration against real owner/store and synthetic offline PDF bytes."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from v5_shadow.manager_loader import load_owner
from v5_shadow.manager_jobs import ManagerJobs
from v5_shadow.m16_runtime import closure, PinnedObservationReader
from v5_shadow.m16_reparse_saved import reparse_saved
from support import DATE, OfflineTransport, offline_error, observation, write_input, wait_terminal, file_snapshot

class SavedReparseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.c=load_owner(closure())['components']
        self.hkex=importlib.import_module('m16_owner_manager_research.hkex_provider')
        self.pdf=importlib.import_module('m16_owner_manager_research.pdf_parser')
        self.contracts=importlib.import_module('m16_owner_manager_research.contracts')
        for target in ['socket.create_connection','socket.socket.connect','urllib.request.urlopen','urllib.request.OpenerDirector.open']:
            guard=patch(target,side_effect=AssertionError('NO_NETWORK'));guard.start();self.addCleanup(guard.stop)
        value=observation();value['rows'][0]['code']='HK.02583'
        unmatched=deepcopy(value['rows'][0]);unmatched.update(code='HK.02915',stage_rank=2);value['rows'].append(unmatched)
        self.path,self.sha=write_input(self.root,value)
        self.runtime=self.root/'runtime';self.materials=self.c.material_store_class(self.runtime/'materials')
        self.store=self.c.store_class(self.runtime);self.transport=OfflineTransport();self.transport.code='02583'
        event=importlib.import_module('m16_owner_manager_research.event_source')
        self.provider=self.c.provider_class(transport=self.transport,material_store=self.materials,event_media_transport=event.BoundedMediaTransport(transport=offline_error),eastmoney_transport=offline_error)
        self.service=self.c.service_class(self.store,PinnedObservationReader(self.path,self.sha),self.provider,reader_fetcher=offline_error)
        self.addCleanup(self.service.close)
        # Seed an original zero-facts generation via the actual owner lifecycle.
        with patch.object(self.hkex,'PDF_FACTS_CACHE_VERSION',1),patch.object(self.hkex,'extract_pdf_facts',return_value=([],self.pdf.extract_pdf_pages(self.transport.document))):
            envelope=self.service.ensure(DATE);self.original_job_id=envelope['job']['job_id']
            wait_terminal(ManagerJobs(service=self.service),self.original_job_id)
        self.data=self.service._read_input(DATE);self.product=self.store.read_product(DATE,self.data['input_identity'])
        self.assertEqual(self.product['rows'][0]['status'],'CANNOT_CONFIRM')
        self.original_job=self.store.read_job(self.original_job_id)
        self.calls=len(self.transport.calls)
        self.args=dict(runtime_root=self.runtime,input_path=self.path,input_sha256=self.sha,target_trade_date=DATE,
            expected_product_sha256=self.contracts.sha256_json(self.product),codes=['HK.02583'])

    def test_preview_reads_only_and_apply_preserves_identity_audit(self):
        before=file_snapshot(self.runtime)
        preview=reparse_saved(**self.args)
        self.assertFalse(preview['applied']);self.assertGreater(preview['rows'][0]['new_fact_count'],0)
        self.assertEqual(file_snapshot(self.runtime),before)
        result=reparse_saved(**self.args,apply=True)
        self.assertTrue(result['applied']);self.assertEqual(len(self.transport.calls),self.calls)
        current=self.store.read_product(DATE,self.data['input_identity'])
        self.assertEqual(current['rows'][0]['status'],'READY')
        self.assertEqual(current['rows'][1],self.product['rows'][1])
        for key in ('input_identity','input_source_sha256','cutoff_at','generated_at','historical_system_available','catalyst_source_receipts'):
            self.assertEqual(current.get(key),self.product.get(key))
        self.assertEqual(self.store.read_job(self.original_job_id),self.original_job)
        receipt=self.store.read_receipt(DATE,result['job_id'])
        self.assertEqual(receipt['previous_product'],self.product)
        self.assertEqual(receipt['previous_job'],self.original_job)
        self.assertEqual(receipt['parser_cache_version'],3)
        self.assertNotEqual(result['generation'],self.original_job['generation'])
        old_catalyst=self.product['rows'][0].get('catalyst_result',{});new_catalyst=current['rows'][0].get('catalyst_result',{})
        for key in old_catalyst:
            if key not in {'financial_counterevidence','financial_counterevidence_refs','financial_re_evaluation'}:
                self.assertEqual(new_catalyst.get(key),old_catalyst[key])
        self.assertGreater(current['rows'][0]['current_research']['financial_advice']['fact_count'],0)
        self.assertEqual(current['rows'][0]['research_recommendation']['timing_status'],self.product['rows'][0]['research_recommendation']['timing_status'])

    def test_wrong_product_hash_no_commit(self):
        with self.assertRaisesRegex(ValueError,'SHA_MISMATCH'):
            reparse_saved(**{**self.args,'expected_product_sha256':'0'*64},apply=True)
        self.assertEqual(self.store.read_product(DATE,self.data['input_identity']),self.product)

    def test_unmatched_code_scope_refused(self):
        with self.assertRaisesRegex(ValueError,'CODE_SCOPE'):
            reparse_saved(**{**self.args,'codes':['HK.02915']},apply=True)

    def test_missing_material_cannot_fetch(self):
        with patch.object(self.materials.__class__,'stat_source',return_value=None):
            with self.assertRaisesRegex(ValueError,'INDEX_MISMATCH'): reparse_saved(**self.args,apply=True)
        self.assertEqual(len(self.transport.calls),self.calls)

    def test_tampered_pdf_rejected_before_commit(self):
        with patch.object(self.materials.__class__,'_blob_relative',return_value='blobs/not-present'):
            with self.assertRaises(FileNotFoundError): reparse_saved(**self.args,apply=True)
        self.assertEqual(self.store.read_product(DATE,self.data['input_identity']),self.product)

    def test_cancel_fence_keeps_previous_product(self):
        original=self.store.__class__.commit_result
        def cancel_first(store,job,product,receipt,**kwargs):
            store.cancel_job(job['job_id'],DATE)
            return original(store,job,product,receipt,**kwargs)
        with patch.object(self.store.__class__,'commit_result',cancel_first):
            with self.assertRaises(Exception): reparse_saved(**self.args,apply=True)
        self.assertEqual(self.store.read_product(DATE,self.data['input_identity']),self.product)

    def test_concurrent_product_change_fenced(self):
        original=self.store.__class__.commit_result
        changed=deepcopy(self.product);changed['diagnostic_test']='SYNTHETIC_CHANGED'
        def change_first(store,job,product,receipt,**kwargs):
            other=deepcopy(self.original_job);other.update(job_id=self.original_job_id+'-concurrent',generation='synthetic-concurrent',attempt=1,status='QUEUED')
            store.admit_job(other);other['status']=changed['status']
            original(store,other,changed,dict(job_id=other['job_id'],target_trade_date=DATE,input_identity=self.data['input_identity']))
            return original(store,job,product,receipt,**kwargs)
        with patch.object(self.store.__class__,'commit_result',change_first):
            with self.assertRaisesRegex(ValueError,'CHANGED_DURING'): reparse_saved(**self.args,apply=True)
        self.assertEqual(self.store.read_product(DATE,self.data['input_identity']),changed)

    def test_input_file_tamper_refused(self):
        self.path.write_text('{}')
        with self.assertRaisesRegex(Exception,'BYTES_CHANGED'): reparse_saved(**self.args,apply=True)

    def test_zero_facts_does_not_admit_recovery(self):
        with patch.object(self.pdf,'extract_pdf_facts',return_value=([],[])):
            with self.assertRaisesRegex(ValueError,'NO_STRUCTURED_FACTS'): reparse_saved(**self.args)
        self.assertEqual(self.store.read_product(DATE,self.data['input_identity']),self.product)

    def test_active_owner_blocks_recovery(self):
        other=deepcopy(self.original_job);other.update(job_id=self.original_job_id+'-active',generation='synthetic-active',attempt=1,status='QUEUED')
        self.store.admit_job(other)
        with self.assertRaisesRegex(ValueError,'OTHER_JOB_ACTIVE'): reparse_saved(**self.args,apply=True)
        self.assertEqual(self.store.read_product(DATE,self.data['input_identity']),self.product)

    def test_receipt_failure_keeps_old_commit(self):
        with patch.object(self.store.__class__,'write_receipt',side_effect=OSError('synthetic receipt failure')):
            with self.assertRaises(OSError): reparse_saved(**self.args,apply=True)
        self.assertEqual(self.store.read_product(DATE,self.data['input_identity']),self.product)

    def test_failed_retry_mirror_cannot_replace_committed_audit(self):
        retry=deepcopy(self.original_job)
        retry.update(attempt=retry['attempt']+1,generation='synthetic-failed-retry',status='QUEUED')
        self.store.admit_job(retry);retry['status']='FAILED';self.store.write_job(retry)
        result=reparse_saved(**self.args,apply=True)
        receipt=self.store.read_receipt(DATE,result['job_id'])
        self.assertEqual(receipt['previous_job'],self.original_job)
        self.assertEqual(self.store.read_job(self.original_job_id),retry)

    def test_envelope_digest_tamper_is_rejected(self):
        source=self.product['rows'][0]['source'];entry=self.materials.stat_source('hkex-official:'+source['url'])
        path=self.runtime/'materials'/'blobs'/entry['sha256'];path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'ENVELOPE_HASH'): reparse_saved(**self.args,apply=True)
        self.assertEqual(self.store.read_product(DATE,self.data['input_identity']),self.product)

    def test_source_job_mismatch_is_rejected(self):
        original=self.store.__class__._read_commit
        def mismatch(store,date,identity):
            value=original(store,date,identity)
            if value:
                value=deepcopy(value);value['jobs'][self.original_job_id]['results']['HK.02583']['source']['sha256']='0'*64
            return value
        with patch.object(self.store.__class__,'_read_commit',mismatch):
            with self.assertRaisesRegex(ValueError,'SOURCE_JOB_BINDING'): reparse_saved(**self.args,apply=True)

    def test_preview_does_not_initialize_an_empty_runtime(self):
        empty=self.root/'empty';empty.mkdir()
        with self.assertRaisesRegex(ValueError,'INITIALIZED_RUNTIME'):
            reparse_saved(**{**self.args,'runtime_root':empty})
        self.assertEqual(list(empty.iterdir()),[])

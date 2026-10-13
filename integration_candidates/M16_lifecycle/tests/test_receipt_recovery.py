"""Actual pinned P0 worker + original store; no weakened terminal validation."""
from copy import deepcopy
from hashlib import sha256,sha1
import importlib,json,sys,types
from pathlib import Path
import unittest
from unittest.mock import patch
import test_reparse_saved as saved_fixture
from support import DATE,file_snapshot
from v5_shadow.m16_reparse_saved import reparse_saved,repair_missing_receipt_status

P0_ROOT=Path(__file__).parent/'reference/p0_m16'

def p0_modules():
    manifest=json.loads((P0_ROOT/'SOURCE.json').read_text())
    for entry in manifest['files']:
        raw=(P0_ROOT/entry['path']).read_bytes()
        if sha256(raw).hexdigest()!=entry['sha256'] or sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=entry['git_blob_sha']:
            raise AssertionError('PINNED_P0_SOURCE_CHANGED')
    name='m16_test_pinned_p0'
    if name not in sys.modules:
        package=types.ModuleType(name);package.__path__=[str(P0_ROOT)];sys.modules[name]=package
    return [importlib.import_module(name+'.'+part) for part in ('m16_readonly_worker','m16_readonly','digests')]

class ReceiptRecoveryTests(unittest.TestCase):
    setUp=saved_fixture.SavedReparseTests.setUp

    def binding(self,job_id):
        commit=self.store._read_commit(DATE,self.data['input_identity']);job=commit['jobs'][job_id]
        raw=self.store._io.read_bytes(f".commits/{DATE}/{self.data['input_identity']}.json")
        return dict(private_root=str(self.runtime),trade_date=DATE,input_identity=self.data['input_identity'],job_id=job_id,
            generation=job['generation'],attempt=job['attempt'],commit_sha256=commit['sha256'],commit_file_sha256=sha256(raw).hexdigest(),
            data_kind='SYNTHETIC',python_executable=sys.executable)

    def project(self,binding):
        worker,readonly,digests=p0_modules()
        # Original P0 validation/project/raw/_members/public_tree remain unchanged.
        # Only its owner-closure loader seam points at this candidate's verified owner.
        with patch.object(worker,'owner_components',return_value=self.c),patch.dict(sys.modules,{'v5_shadow.m16_readonly':readonly,'v5_shadow.digests':digests}):
            return worker.project(binding)

    def seed_missing_status(self):
        (self.runtime/'.m16-private-root.json').write_text(json.dumps({'module':'M16','private':True,'schema':'v5.private_root.v1'}))
        original=self.store.__class__.commit_result
        def legacy(store,job,product,receipt,**kwargs):
            receipt=deepcopy(receipt);receipt.pop('status',None)
            return original(store,job,product,receipt,**kwargs)
        with patch.object(self.store.__class__,'commit_result',legacy):
            result=reparse_saved(**self.args,apply=True)
        self.bad_binding=self.binding(result['job_id'])
        self.before=self.store._read_commit(DATE,self.data['input_identity'])
        self.before_raw=self.store._io.read_bytes(f".commits/{DATE}/{self.data['input_identity']}.json")
        self.repair_args=dict(runtime_root=self.runtime,input_path=self.path,input_sha256=self.sha,target_trade_date=DATE,
            expected_product_sha256=self.contracts.sha256_json(self.before['product']),expected_commit_sha256=self.before['sha256'],
            expected_commit_file_sha256=sha256(self.before_raw).hexdigest(),job_id=result['job_id'],generation=result['generation'])

    def test_fixed_producer_passes_original_p0_worker(self):
        (self.runtime/'.m16-private-root.json').write_text(json.dumps({'module':'M16','private':True,'schema':'v5.private_root.v1'}))
        result=reparse_saved(**self.args,apply=True);binding=self.binding(result['job_id'])
        projected=self.project(binding)
        self.assertEqual(projected['status'],'SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED')
        self.assertEqual(projected['receipt']['status'],projected['job']['status'])
        self.assertEqual(projected['reference']['product_sha256'],result['product_sha256'])

    def test_legacy_rejected_then_formal_recovery_passes_without_product_change(self):
        self.seed_missing_status()
        with self.assertRaisesRegex(ValueError,'M16_TERMINAL_STATUS'): self.project(self.bad_binding)
        snapshot=file_snapshot(self.runtime)
        preview=repair_missing_receipt_status(**self.repair_args)
        self.assertFalse(preview['applied']);self.assertEqual(file_snapshot(self.runtime),snapshot)
        with patch.object(self.pdf,'extract_pdf_facts',side_effect=AssertionError('NO_REPARSE')):
            repaired=repair_missing_receipt_status(**self.repair_args,apply=True)
        after=self.store._read_commit(DATE,self.data['input_identity'])
        self.assertEqual(after['product'],self.before['product'])
        for key,value in self.before['jobs'].items():self.assertEqual(after['jobs'][key],value)
        for key,value in self.before['receipts'].items():self.assertEqual(after['receipts'][key],value)
        archived=self.store._io.read_bytes('.receipt-recovery/'+sha256(self.before_raw).hexdigest()+'.json')
        self.assertEqual(archived,self.before_raw)
        projected=self.project(self.binding(repaired['job_id']))
        self.assertEqual(projected['reference']['product_sha256'],self.repair_args['expected_product_sha256'])
        self.assertEqual(projected['receipt']['status'],self.before['product']['status'])
        self.assertEqual(projected['receipt']['pdf_parse_calls'],0)
        self.assertEqual(len(self.transport.calls),self.calls)
        self.assertNotEqual(repaired['generation'],self.bad_binding['generation'])

    def test_all_pins_and_generation_fail_closed(self):
        self.seed_missing_status()
        for key in ('expected_product_sha256','expected_commit_sha256','expected_commit_file_sha256','generation'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                repair_missing_receipt_status(**{**self.repair_args,key:'0'*64},apply=True)
        self.assertEqual(self.store._read_commit(DATE,self.data['input_identity']),self.before)

    def test_no_repair_for_correct_or_explicitly_wrong_status(self):
        self.seed_missing_status();original=self.store.__class__._read_commit
        # This is a validation negative, not a write to the original receipt.
        for status in (self.before['product']['status'],'FAILED'):
            changed=deepcopy(self.before);changed['receipts'][self.bad_binding['job_id']]['status']=status
            changed.pop('sha256');changed['sha256']=self.contracts.sha256_json(changed)
            raw=self.contracts.canonical_json(changed)
            io=self.store._io.__class__;read=io.read_bytes
            def substitute(instance,relative,**kwargs):
                if relative.startswith('.commits/'):return raw
                return read(instance,relative,**kwargs)
            with patch.object(io,'read_bytes',substitute),self.assertRaisesRegex(ValueError,'NOT_KNOWN_MISSING_STATUS'):
                repair_missing_receipt_status(**{**self.repair_args,'expected_commit_sha256':changed['sha256'],'expected_commit_file_sha256':sha256(raw).hexdigest()})

    def test_cancel_fence_preserves_bad_commit(self):
        self.seed_missing_status();original=self.store.__class__.commit_result
        def cancel(store,job,product,receipt,**kwargs):
            store.cancel_job(job['job_id'],DATE);return original(store,job,product,receipt,**kwargs)
        with patch.object(self.store.__class__,'commit_result',cancel),self.assertRaises(Exception):
            repair_missing_receipt_status(**self.repair_args,apply=True)
        self.assertEqual(self.store._read_commit(DATE,self.data['input_identity']),self.before)

    def test_receipt_write_failure_preserves_old_generation(self):
        self.seed_missing_status()
        with patch.object(self.store.__class__,'write_receipt',side_effect=OSError('SYNTHETIC_FAIL')),self.assertRaises(OSError):
            repair_missing_receipt_status(**self.repair_args,apply=True)
        self.assertEqual(self.store._read_commit(DATE,self.data['input_identity']),self.before)

    def test_race_rejects_even_same_product_new_commit(self):
        self.seed_missing_status();original=self.store.__class__.commit_result
        def race(store,job,product,receipt,**kwargs):
            other=deepcopy(job);other.update(job_id=job['job_id']+'-race',generation='synthetic-race',attempt=1,status='QUEUED')
            store.admit_job(other);other['status']=product['status']
            other_receipt=dict(receipt,job_id=other['job_id'],generation=other['generation'])
            original(store,other,product,other_receipt)
            return original(store,job,product,receipt,**kwargs)
        with patch.object(self.store.__class__,'commit_result',race),self.assertRaisesRegex(ValueError,'COMMIT_CHANGED'):
            repair_missing_receipt_status(**self.repair_args,apply=True)
        after=self.store._read_commit(DATE,self.data['input_identity'])
        self.assertEqual(after['product'],self.before['product'])
        self.assertEqual(after['receipts'][self.bad_binding['job_id']],self.before['receipts'][self.bad_binding['job_id']])

    def test_active_owner_and_conflicting_archive_are_refused(self):
        self.seed_missing_status()
        other=deepcopy(self.before['jobs'][self.bad_binding['job_id']]);other.update(job_id='synthetic-active-owner',generation='synthetic-active',attempt=1,status='QUEUED')
        self.store.admit_job(other)
        with self.assertRaisesRegex(ValueError,'OTHER_JOB_ACTIVE'):repair_missing_receipt_status(**self.repair_args,apply=True)
        self.store.cancel_job(other['job_id'],DATE)
        archive='.receipt-recovery/'+self.repair_args['expected_commit_file_sha256']+'.json'
        self.store._io.write_bytes(archive,b'SYNTHETIC_CONFLICT')
        with self.assertRaisesRegex(ValueError,'ARCHIVE_CONFLICT'):repair_missing_receipt_status(**self.repair_args,apply=True)
        self.assertEqual(self.store._read_commit(DATE,self.data['input_identity']),self.before)

    def test_explicit_contradictory_receipt_attempt_is_not_missing_status_only(self):
        self.seed_missing_status()
        for key,value in [('generation','SYNTHETIC_WRONG_GENERATION'),('attempt',999)]:
            changed=deepcopy(self.before);changed['receipts'][self.bad_binding['job_id']][key]=value
            changed.pop('sha256');changed['sha256']=self.contracts.sha256_json(changed)
            raw=self.contracts.canonical_json(changed)
            io=self.store._io.__class__;read=io.read_bytes
            def substitute(instance,relative,**kwargs):
                return raw if relative.startswith('.commits/') else read(instance,relative,**kwargs)
            with patch.object(io,'read_bytes',substitute),self.assertRaisesRegex(ValueError,'NOT_KNOWN_MISSING_STATUS'):
                repair_missing_receipt_status(**{**self.repair_args,'expected_commit_sha256':changed['sha256'],'expected_commit_file_sha256':sha256(raw).hexdigest()})

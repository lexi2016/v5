"""Actual original M08 cold reader; no selector, publisher or M16 job is run."""
from hashlib import sha256
import importlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from v5_shadow.m16_prepare_stage import prepare, canonical, verified_reader, ROOT, read_json
from v5_shadow.m16_runtime import PinnedObservationReader, closure
from v5_shadow.manager_loader import load_owner
from stage_fixture import make_saved_stage
from support import file_snapshot

class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.recorded,self.reference,self.artifact,self.trio=make_saved_stage(self.root)
        self.output=self.root/'new-input'
        self.before=file_snapshot(self.recorded)
        owner=load_owner(closure())['components']
        p=patch('m16_owner_manager_research.service.ThreadPoolExecutor',side_effect=AssertionError('M16_OWNER_MUST_NOT_START'))
        p.start();self.addCleanup(p.stop)
        p=patch('socket.socket.connect',side_effect=AssertionError('NETWORK_MUST_NOT_RUN'))
        p.start();self.addCleanup(p.stop)

    def tearDown(self):
        # Tests that intentionally tamper source take their own post-tamper snapshot.
        self.assertEqual(file_snapshot(self.recorded),self.before)

    def test_complete_original_rows_and_source_hash_are_preserved(self):
        r=prepare(self.recorded,self.reference,self.output)
        raw=(self.output/'observation.json').read_bytes();value=json.loads(raw)
        self.assertEqual(value['rows'],self.artifact['rows'])
        for k,v in self.artifact.items():self.assertEqual(value[k],v)
        self.assertEqual(value['status'],self.artifact['selection_status'])
        self.assertEqual(value['target_trade_date'],'20261005')
        self.assertEqual(r['source_raw_artifact_sha256'],'2'*64)
        self.assertEqual(r['source_artifact_file_sha256'],sha256((self.trio/'artifact.csv').read_bytes()).hexdigest())
        self.assertEqual(r['input_file_sha256'],sha256(raw).hexdigest())
        self.assertNotEqual(r['input_file_sha256'],r['source_raw_artifact_sha256'])
        self.assertFalse(r['manager_job_started']);self.assertFalse(r['prior_product_identity_claimed'])
        self.assertEqual(r['status'],'PREPARED_NOT_RUN');self.assertFalse(r['pit_verified'])
        self.assertEqual(PinnedObservationReader(self.output/'observation.json',r['input_file_sha256']).read('20261005'),value)
        contract=importlib.import_module('m16_owner_manager_research.contracts')
        self.assertEqual(contract.normalise_observation_input(value)['input_identity'],r['input_identity'])

    def test_preparation_does_not_modify_input_or_package_bytes(self):
        before=file_snapshot(ROOT/'source/m08_readonly');reference=self.reference.read_bytes()
        prepare(self.recorded,self.reference,self.output)
        self.assertEqual(before,file_snapshot(ROOT/'source/m08_readonly'))
        self.assertEqual(reference,self.reference.read_bytes())

    def test_no_existing_output_overwrite(self):
        self.output.mkdir();(self.output/'keep').write_text('unchanged')
        with self.assertRaisesRegex(ValueError,'OUTPUT_EXISTS'):prepare(self.recorded,self.reference,self.output)
        self.assertEqual((self.output/'keep').read_text(),'unchanged')

    def test_output_cannot_write_into_m08_store(self):
        with self.assertRaisesRegex(ValueError,'MUST_BE_SEPARATE'):prepare(self.recorded,self.reference,self.recorded/'bad')

    def test_trio_tamper_is_rejected_by_original_reader(self):
        p=self.trio/'artifact.csv';p.write_bytes(p.read_bytes()+b'changed');self.before=file_snapshot(self.recorded)
        with self.assertRaisesRegex(ValueError,'COMMITTED_READ_REJECTED'):prepare(self.recorded,self.reference,self.output)
        self.assertFalse(self.output.exists())

    def test_reference_wrong_stage_is_rejected_without_rewriting(self):
        v=json.loads(self.reference.read_bytes());v['stage_id']='STAGE_0940_0945';self.reference.write_bytes(canonical(v))
        with self.assertRaisesRegex(ValueError,'0935_REFERENCE'):prepare(self.recorded,self.reference,self.output)
        self.assertFalse(self.output.exists())

    def test_receipt_wrong_date_is_rejected(self):
        v=json.loads(self.reference.read_bytes());v['target_date']='20261006';self.reference.write_bytes(canonical(v))
        with self.assertRaisesRegex(ValueError,'COMMITTED_READ_REJECTED'):prepare(self.recorded,self.reference,self.output)
        self.assertFalse(self.output.exists())

    def test_reference_symlink_is_rejected(self):
        link=self.root/'link.json';link.symlink_to(self.reference)
        with self.assertRaisesRegex(ValueError,'PATH_REFUSED'):prepare(self.recorded,link,self.output)

    def test_dependency_pin_tamper_fails_before_reader(self):
        with patch('v5_shadow.m16_prepare_stage.DEPENDENCY_SHA256','0'*64):
            with self.assertRaisesRegex(ValueError,'DEPENDENCY_MANIFEST_HASH'):prepare(self.recorded,self.reference,self.output)
        self.assertFalse(self.output.exists())

    def test_m08_verified_but_missing_or_late_timestamp_is_not_filled(self):
        for kind in ('late','missing_time','empty'):
            directory=self.root/kind;directory.mkdir()
            store,ref,_,_=make_saved_stage(directory,**{kind:True})
            before=file_snapshot(store)
            with self.assertRaises(ValueError):prepare(store,ref,directory/'prepared')
            self.assertEqual(file_snapshot(store),before)
            self.assertFalse((directory/'prepared').exists())

    def test_cli_prepares_only_and_prints_new_file_sha(self):
        run=subprocess.run([sys.executable,'-B','-m','v5_shadow.m16_prepare_stage',
             '--recorded-root',str(self.recorded),'--reference',str(self.reference),
             '--output-directory',str(self.output)],capture_output=True,text=True,timeout=30)
        self.assertEqual(run.returncode,0,run.stderr+run.stdout)
        r=json.loads(run.stdout)
        self.assertEqual(r['status'],'PREPARED_NOT_RUN');self.assertFalse(r['manager_job_started'])
        self.assertEqual(r['input_file_sha256'],sha256((self.output/'observation.json').read_bytes()).hexdigest())
        self.assertNotIn(str(self.root),run.stdout)

    def test_duplicate_json_is_refused(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_KEY'):read_json(b'{"a":1,"a":2}')

if __name__=='__main__':unittest.main()

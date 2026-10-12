"""Offline M04 orchestration: real frozen owners; synthetic provider boundary only."""
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import test_archive_article_v2 as chain
from v5_shadow.digests import canonical_bytes

class ResearchIngestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        chain.ArticleV2ChainTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):
        chain.ArticleV2ChainTests.tearDownClass.__func__(cls)
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.research_ingest_daily'),
                             'M04 default owner orchestration entrypoint is missing')
        from v5_shadow import research_ingest_daily
        self.module = research_ingest_daily
        self.fixture = chain.ArticleV2ChainTests('test_real_producer_original_store_independent_reader_workspace_and_same_run_plan')
        self.fixture.owner = self.owner
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        # New private capture; original fixture's successful source is untouched.
        root = f.root/'second-capture'; root.mkdir()
        (root/'.v5-archive-acquisition').write_bytes(b'v5.archive-acquisition.v2\n')
        completed = subprocess.CompletedProcess([], 0, json.dumps({'topics':[f.raw_topic], 'has_more':False}), '')
        with patch.object(self.owner, '_acquisition_clock', side_effect=f.times):
            status = self.owner.materialize_zsxq_hourly_delta(data_root=root, trade_date=f.day,
                slot='0900', now=f.base, groups=[('123','synthetic')],
                process_runner=lambda *a,**k: completed,
                analyzer=lambda *a: {'effective_topic_count':1,'effective_topics':[f.summary_topic]})
        ref = {k:status['acquisition_evidence_v2'][k] for k in ('path','sha256','bytes')}
        files = {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (root/'external_sources').rglob('*') if p.is_file()}
        raw = (root/status['status_path']).read_bytes()
        status_ref = dict(path=status['status_path'],sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
        files[status_ref['path']] = status_ref['sha256']
        self.state = f.root/'ingest'; self.state.mkdir()
        (self.state/'.v5-research-ingest').write_bytes(b'v5.research-ingest.v1\n')
        self.request = dict(capture_root=str(root),capture_files=files,receipt=ref,status=status_ref,state_root=str(self.state))
    def snapshot(self):
        return {str(p.relative_to(self.state)):p.read_bytes() for p in self.state.rglob('*') if p.is_file()}
    def test_default_chain_and_cold_cli_exact_reference(self):
        result = self.module.run(self.request)
        self.assertEqual(result['status'], 'SUCCEEDED')
        self.assertFalse(result['natural_verified'])
        self.assertEqual(result['article_count'], 1)
        before = self.snapshot()
        process = subprocess.run([sys.executable,'-B','-m','v5_shadow.research_ingest_daily','read'],
            input=canonical_bytes(result['archive_binding']),capture_output=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)['records'][self.fixture.day+'/']['payload']['articles'][0]['article_id'],
                         result['article_ids'][0])
        self.assertEqual(self.snapshot(),before)
    def test_same_request_reuses_success_without_writes(self):
        first = self.module.run(self.request); before = self.snapshot()
        second = self.module.run(self.request)
        self.assertEqual(first,second); self.assertEqual(before,self.snapshot())
    def test_import_failure_retains_builder_then_retry_uses_new_root(self):
        original = self.module.run_import
        def interrupted(request):
            (Path(request['output_root'])/'partial').write_text('interrupted synthetic import')
            raise RuntimeError('synthetic interruption')
        with patch.object(self.module,'run_import',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'synthetic interruption'): self.module.run(self.request)
        built = next(self.state.glob('runs/*/builder.json')).read_bytes()
        result = self.module.run(self.request)
        self.assertEqual(result['status'],'SUCCEEDED')
        self.assertEqual(next(self.state.glob('runs/*/builder.json')).read_bytes(),built)
        self.assertTrue(list(self.state.glob('runs/*/imports/*/partial')))
        self.assertEqual(len(list(self.state.glob('runs/*/imports/*'))),2)
    def test_capture_tamper_rejected_before_reusing_success(self):
        self.module.run(self.request)
        path = Path(self.request['capture_root'])/self.request['status']['path']
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'CAPTURE_CHANGED'): self.module.run(self.request)
    def test_archive_tamper_rejected_by_cold_reader(self):
        result = self.module.run(self.request)
        path = Path(result['archive_binding']['root'])/'manifest.json'; path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'ARCHIVE_PRIVATE_SHA'): self.module.run(self.request)
    def test_overlap_rejected_before_owner(self):
        self.request['state_root'] = self.request['capture_root']
        with self.assertRaisesRegex(ValueError,'ROOT_OVERLAP'): self.module.run(self.request)
    def test_unmarked_state_rejected(self):
        (self.state/'.v5-research-ingest').unlink()
        with self.assertRaisesRegex(ValueError,'STATE_MARKER'): self.module.run(self.request)
    def test_locked_run_is_rejected(self):
        import fcntl
        with (self.state/'writer.lock').open('a+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError,'WRITER_BUSY'): self.module.run(self.request)
    def test_changed_input_failure_preserves_previous_success(self):
        self.module.run(self.request)
        before=(self.state/'latest_success.json').read_bytes()
        self.request['receipt'] = dict(self.request['receipt'],sha256='0'*64)
        with self.assertRaises(ValueError): self.module.run(self.request)
        self.assertEqual((self.state/'latest_success.json').read_bytes(),before)
        self.assertEqual(json.loads((self.state/'latest_attempt.json').read_bytes())['status'],'FAILED')
    def test_explicit_run_cli_executes_same_original_chain(self):
        process = subprocess.run([sys.executable,'-B','-m','v5_shadow.research_ingest_daily','run'],
            input=canonical_bytes(self.request),capture_output=True)
        self.assertEqual(process.returncode,0,process.stdout.decode())
        result=json.loads(process.stdout)
        self.assertEqual(result['status'],'SUCCEEDED')
        self.assertEqual(result['article_count'],1)
        self.assertFalse(result['orders_sent'])
    def test_partial_builder_is_not_reexecuted_or_overwritten(self):
        capture=Path(self.request['capture_root'])
        guard=capture/'research/incoming'/self.fixture.day/'0900.builder-v1'
        guard.mkdir(parents=True)
        witness=guard/'interruption'; witness.write_text('synthetic interrupted owner')
        with self.assertRaisesRegex(ValueError,'OWNER_FAILED'): self.module.run(self.request)
        self.assertEqual(witness.read_text(),'synthetic interrupted owner')
        self.assertFalse(list(self.state.glob('runs/*/imports')))
        self.assertFalse((self.state/'latest_success.json').exists())
    def test_symlink_state_is_rejected(self):
        alias=self.fixture.root/'state-link'; alias.symlink_to(self.state,target_is_directory=True)
        self.request['state_root']=str(alias)
        with self.assertRaisesRegex(ValueError,'PRIVATE_ROOT'): self.module.run(self.request)
    def test_unknown_fields_cannot_enable_acquisition(self):
        self.request['fetch']=True
        with self.assertRaisesRegex(ValueError,'REQUEST_FIELDS'): self.module.run(self.request)
    def test_success_checkpoint_cannot_escalate_safety_claims(self):
        self.module.run(self.request)
        path=next(self.state.glob('runs/*/success.json'))
        value=json.loads(path.read_bytes()); value['production_allowed']=True
        path.write_bytes(canonical_bytes(value))
        with self.assertRaisesRegex(ValueError,'SUCCESS_SAFETY'): self.module.run(self.request)

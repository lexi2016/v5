import json,unittest
from unittest.mock import patch
import test_capture as fixture

class BuilderReuseTests(unittest.TestCase):
 def setUp(self):
  self.c=fixture.CaptureTests();self.c.setUp();self.addCleanup(self.c.doCleanups)
 def saved_prior_adapter(self):
  c=self.c
  with patch.object(c.m.ingest,'article_v2_identity',return_value='prior-adapter-identity'),patch.object(c.m.ingest,'run_import',side_effect=ValueError('synthetic old adapter rejection')):
   with self.assertRaisesRegex(ValueError,'old adapter'):c.run_capture()
  paths=list((c.runtime/'ingest/runs').glob('*/builder.json'));self.assertEqual(len(paths),1)
  source=c.runtime/'captures/case1/source';guards=list(source.rglob('*.builder-v1'));self.assertEqual(len(guards),1);self.assertTrue(guards[0].is_dir())
  c.cli.write_text('no reacquisition permitted')
  return paths[0],source,guards[0]
 def test_cross_adapter_reuses_bound_builder_with_real_guard(self):
  c=self.c;checkpoint,source,guard=self.saved_prior_adapter();old=checkpoint.read_bytes()
  before={str(p.relative_to(source)):c.sha(p) for p in source.rglob('*') if p.is_file()}
  with patch.object(c.m.ingest,'run_build',side_effect=AssertionError('must not rerun original writer')):
   result=c.m.resume(c.config,'case1')
  self.assertEqual(result['status'],'SUCCEEDED');self.assertTrue(guard.is_dir());self.assertEqual(checkpoint.read_bytes(),old)
  self.assertEqual(before,{str(p.relative_to(source)):c.sha(p) for p in source.rglob('*') if p.is_file()})
  self.assertEqual(c.m.materials(result['archive_binding'])['articles'][0]['body_text'],c.body)
  self.assertEqual(len(list((c.runtime/'ingest/runs').glob('*/builder.json'))),2)
 def test_tampered_old_archive_rejected_without_writer(self):
  c=self.c;checkpoint,source,guard=self.saved_prior_adapter();value=json.loads(checkpoint.read_bytes());value['archive_v1']['articles'][0]['evidence_sentence']='invented';checkpoint.write_text(json.dumps(value))
  with patch.object(c.m.ingest,'run_build',side_effect=AssertionError('must not rerun writer')):
   with self.assertRaisesRegex(ValueError,'INGEST_BUILDER_REUSE'):c.m.resume(c.config,'case1')
  self.assertTrue(guard.is_dir());self.assertFalse((c.runtime/'captures/case1/result.json').exists())
 def test_changed_owner_pin_rejected(self):
  c=self.c;checkpoint,source,guard=self.saved_prior_adapter();value=json.loads(checkpoint.read_bytes());value['builder_identity']['adapter_sha256']='0'*64;checkpoint.write_text(json.dumps(value))
  with patch.object(c.m.ingest,'run_build',side_effect=AssertionError('must not rerun writer')):
   with self.assertRaisesRegex(ValueError,'INGEST_BUILDER_REUSE'):c.m.resume(c.config,'case1')
 def test_changed_source_bytes_rejected(self):
  c=self.c;checkpoint,source,guard=self.saved_prior_adapter();value=json.loads(checkpoint.read_bytes());p=source/value['builder_source']['path'];p.write_bytes(p.read_bytes()+b' ')
  with patch.object(c.m.ingest,'run_build',side_effect=AssertionError('must not rerun writer')):
   with self.assertRaisesRegex(ValueError,'INGEST_BUILDER_REUSE'):c.m.resume(c.config,'case1')
 def test_conflicting_completed_checkpoints_rejected(self):
  c=self.c;checkpoint,source,guard=self.saved_prior_adapter();other=c.runtime/'ingest/runs'/('0'*64);other.mkdir()
  value=json.loads(checkpoint.read_bytes());value['archive_v1']['articles'][0]['evidence_sentence']='conflict';(other/'builder.json').write_text(json.dumps(value))
  with self.assertRaisesRegex(ValueError,'INGEST_BUILDER_REUSE_CONFLICT'):c.m.resume(c.config,'case1')
  self.assertTrue(guard.is_dir())
 def test_partial_builder_guard_still_blocks_without_complete_checkpoint(self):
  c=self.c;checkpoint,source,guard=self.saved_prior_adapter();checkpoint.rename(checkpoint.with_name('incomplete.saved-for-test'))
  with self.assertRaisesRegex(ValueError,'BUILDER_V1_OWNER_FAILED:FileExistsError'):c.m.resume(c.config,'case1')
  self.assertTrue(guard.is_dir())

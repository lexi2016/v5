"""Synthetic, read-only dependency audit; never executes writer or real formula."""
import unittest, copy, importlib.util
import stages
import test_checkpoint as fixtures
digest=fixtures.digest
spec=importlib.util.spec_from_file_location('adapter_audit','/workspace/shared/latest109_rebuild_v2_20261108/latest109_rebuild.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)

class Audit(unittest.TestCase):
 setUp=fixtures.CheckpointTests.setUp
 runtime=fixtures.CheckpointTests.runtime
 def run_bound(self,adapter_validation=True):
  rt=self.runtime()
  def compute(rows,ctx,prior_state,*,checkpoint_prefix_sha256):
   if adapter_validation:adapter.validate_checkpoint(rows,ctx,prior_state,checkpoint_prefix_sha256)
   return 'CALLED'
  rt.compute=compute
  return stages.compute_with_checkpoint(self.prepared,self.prior,rt)
 def test_context_symbol_rejected_by_v2(self):
  self.prepared['context']['symbol']='000002.SZ'
  with self.assertRaisesRegex(ValueError,'PRIOR_IDENTITY'):self.run_bound()
 def test_context_date_rejected_by_v2(self):
  self.prepared['context']['asof']='20261109'
  with self.assertRaisesRegex(ValueError,'TARGET_IDENTITY'):self.run_bound()
 def test_target_symbol_rejected_by_v2(self):
  self.rows[-1]['symbol']='000002.SZ'
  with self.assertRaisesRegex(ValueError,'CHECKPOINT_ROW_SYMBOL'):self.run_bound()
 def test_saved_state_date_rejected_by_v2(self):
  self.state['last_date']='20261104'
  with self.assertRaisesRegex(ValueError,'PRIOR_IDENTITY'):self.run_bound()
 def test_context_guard_now_blocks_before_compute(self):
  self.prepared['context']['symbol']='000002.SZ'
  with self.assertRaisesRegex(ValueError,'PRIOR_IDENTITY'):self.run_bound(False)
 def test_forged_owner_binder_is_not_authenticated_by_stage(self):
  # Entire supplied snapshot and saved digest are attacker-consistent: this is
  # not an external attack API, but documents why binder must be owner-private.
  self.rows[0]['close']=999999
  self.cp['prefix_sha256']=digest(self.rows[:-1])
  self.assertEqual(self.run_bound(),'CALLED')
 def test_nonhex_prior_sha_should_block(self):
  self.prior['continuation_ref']['sha256']='z'*64
  self.cp['prior_continuation_sha256']='z'*64
  with self.assertRaises(ValueError):self.run_bound()
 def test_cross_symbol_historical_prefix_should_block(self):
  self.rows[0]['symbol']='000002.SZ'
  self.cp['prefix_sha256']=digest(self.rows[:-1])
  with self.assertRaises(ValueError):self.run_bound()
 def test_target_before_prior_should_block(self):
  self.rows[-1]['event_date']='20261104'
  self.prepared['context']['asof']='20261104'
  with self.assertRaises(ValueError):self.run_bound()
 def test_missing_prior_sha_blocks(self):
  self.prior['continuation_ref'].pop('sha256')
  with self.assertRaisesRegex(ValueError,'CHECKPOINT_PRIOR'):self.run_bound()

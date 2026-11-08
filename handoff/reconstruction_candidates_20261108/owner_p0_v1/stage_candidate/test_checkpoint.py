import unittest, json, hashlib, types, copy
import stages

def digest(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
class CheckpointTests(unittest.TestCase):
 def setUp(self):
  self.state={'symbol':'000001.SZ','count':1,'last_date':'20261105'}
  self.rows=[{'symbol':'000001.SZ','event_date':'20261105'},{'symbol':'000001.SZ','event_date':'20261106'}]
  self.prepared={'rows':self.rows,'context':{'symbol':'000001.SZ','asof':'20261106'},'prior_component_state':self.state}
  self.prior={'continuation_ref':{'sha256':'a'*64}}
  self.cp={'schema':'OWNER_CHECKPOINT_PREFIX_V1','prior_continuation_sha256':'a'*64,'state':self.state,'prefix_sha256':digest(self.rows[:-1])}
 def runtime(self,cp=None):
  raw=json.dumps(cp or self.cp).encode();ref={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'path':'FIXTURE_ONLY'}
  return types.SimpleNamespace(bound_checkpoint_ref=lambda prior:ref,checked=lambda r:raw)
 def test_checkpoint_forwarded_to_required_keyword(self):
  self.assertTrue(hasattr(stages,'compute_with_checkpoint'),'stage requires persisted checkpoint binder')
  rt=self.runtime();rt.compute=lambda rows,ctx,prior_state,*,checkpoint_prefix_sha256:(prior_state,checkpoint_prefix_sha256)
  state,prefix=stages.compute_with_checkpoint(self.prepared,self.prior,rt)
  self.assertEqual(state,self.state);self.assertEqual(prefix,self.cp['prefix_sha256'])
 def test_missing_checkpoint_blocks_before_compute(self):
  self.assertTrue(hasattr(stages,'compute_with_checkpoint'))
  with self.assertRaisesRegex(ValueError,'CHECKPOINT_BINDING_REQUIRED'):stages.compute_with_checkpoint(self.prepared,self.prior,types.SimpleNamespace())
 def test_changed_prefix_not_recomputed(self):
  self.assertTrue(hasattr(stages,'compute_with_checkpoint'))
  self.prepared['rows'][0]['event_date']='20261104'
  with self.assertRaisesRegex(ValueError,'CHECKPOINT_PREFIX'):stages.compute_with_checkpoint(self.prepared,self.prior,self.runtime())
 def test_changed_state_rejected(self):
  self.assertTrue(hasattr(stages,'compute_with_checkpoint'))
  cp=copy.deepcopy(self.cp);cp['state']['count']=2
  with self.assertRaisesRegex(ValueError,'CHECKPOINT_STATE'):stages.compute_with_checkpoint(self.prepared,self.prior,self.runtime(cp))
 def test_wrong_prior_ref_rejected(self):
  self.assertTrue(hasattr(stages,'compute_with_checkpoint'))
  cp=copy.deepcopy(self.cp);cp['prior_continuation_sha256']='b'*64
  with self.assertRaisesRegex(ValueError,'CHECKPOINT_PRIOR'):stages.compute_with_checkpoint(self.prepared,self.prior,self.runtime(cp))
 def test_tampered_bytes_rejected(self):
  self.assertTrue(hasattr(stages,'compute_with_checkpoint'))
  rt=self.runtime();rt.checked=lambda ref:b'{}'
  with self.assertRaisesRegex(ValueError,'CHECKPOINT_BYTES'):stages.compute_with_checkpoint(self.prepared,self.prior,rt)
if __name__=='__main__':unittest.main()

class StageRouteTests(unittest.TestCase):
 setUp=CheckpointTests.setUp
 runtime=CheckpointTests.runtime
 def test_stage_routes_bound_checkpoint_and_retains_failure(self):
  prepared=dict(self.prepared,status='PREPARED_ONE_SESSION',symbol='000001.SZ')
  runtime=self.runtime()
  runtime.completed=lambda *args:None
  runtime.verify_inputs=lambda *args:None
  runtime.gate=lambda:None
  runtime.started=lambda *args:{'fixture':True}
  runtime.provider=types.SimpleNamespace(prepare=lambda *args:prepared)
  captured={}
  def compute(rows, context, prior_state, *, checkpoint_prefix_sha256):
   captured.update(prefix=checkpoint_prefix_sha256,rows=rows,state=prior_state)
   raise RuntimeError('FIXTURE_STOP_BEFORE_WRITER')
  runtime.compute=compute
  attempt=stages.Attempt('000001.SZ',20261106)
  with self.assertRaisesRegex(RuntimeError,'FIXTURE_STOP_BEFORE_WRITER'):
   stages.advance_stock(attempt,runtime,self.prior,{'sha256':'input'},'input')
  self.assertEqual(captured['prefix'],self.cp['prefix_sha256'])
  self.assertIs(captured['rows'],prepared['rows'])
  self.assertIs(captured['state'],prepared['prior_component_state'])
  self.assertEqual(attempt.phase,'UNKNOWN_NO_BLIND_RETRY')

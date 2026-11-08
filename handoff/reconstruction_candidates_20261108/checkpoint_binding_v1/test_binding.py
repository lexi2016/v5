import unittest,json,gzip,hashlib,copy
from binding import Binding
class Tests(unittest.TestCase):
 def setUp(self):
  self.state={'symbol':'SYNTH','last_date':'20261105','count':2}
  self.bundle={'schema':'SAME_BASIS_CONTINUATION_BUNDLE_V1','symbol':'SYNTH','asof':'20261105','component109':self.state,'state51':{'count':2}}
 def make(self,change=None):
  def pin(raw,path):return {'path':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
  br=gzip.compress(json.dumps(self.bundle).encode());pr=pin(br,'FIXTURE/continuation.gz')
  cp={'schema':'OWNER_CHECKPOINT_PREFIX_V1','prior_continuation_sha256':pr['sha256'],'state':copy.deepcopy(self.state),'prefix_sha256':'a'*64}
  if change:change(cp)
  cr=json.dumps(cp).encode();cpr=pin(cr,'FIXTURE/checkpoint.json');data={pr['path']:br,cpr['path']:cr}
  reg={'schema':'OWNER_CHECKPOINT_REGISTRY_V1','entries':[{'continuation_ref':pr,'checkpoint_ref':cpr}]};rr=json.dumps(reg).encode()
  return rr,pin(rr,'FIXTURE/registry'),data,pr,cpr
 def binder(self,m):return Binding(m[0],m[1],lambda ref:m[2][ref['path']],lambda:None)
 def test_captured_same_saved_state(self):
  m=self.make();b=self.binder(m);ref=b.bound_checkpoint_ref({'continuation_ref':m[3]});self.assertEqual(b.checked(ref),m[2][m[4]['path']])
 def test_unregistered_reject_not_generate(self):
  b=self.binder(self.make())
  with self.assertRaisesRegex(ValueError,'UNREGISTERED_PRIOR'):b.bound_checkpoint_ref({'continuation_ref':{'sha256':'b'*64}})
 def test_cross_state_reject(self):
  with self.assertRaisesRegex(ValueError,'STATE_NOT_SAME'):self.binder(self.make(lambda cp:cp['state'].update(count=3)))
 def test_cross_prior_reject(self):
  with self.assertRaisesRegex(ValueError,'CHECKPOINT_PRIOR'):self.binder(self.make(lambda cp:cp.update(prior_continuation_sha256='b'*64)))
 def test_missing_prefix_reject(self):
  with self.assertRaisesRegex(ValueError,'PERSISTED_PREFIX'):self.binder(self.make(lambda cp:cp.pop('prefix_sha256')))
 def test_snapshot_mutation_cannot_change_bound_bytes(self):
  m=self.make();b=self.binder(m);before=b.checked(m[4]);m[2][m[4]['path']]=b'changed';self.assertEqual(b.checked(m[4]),before)
 def test_source_tamper_rejected(self):
  m=self.make();m[2][m[4]['path']]=b'changed'
  with self.assertRaisesRegex(ValueError,'SNAPSHOT_BYTES'):self.binder(m)
 def test_registry_pin_tamper_rejected(self):
  m=list(self.make());m[0]+=b' '
  with self.assertRaisesRegex(ValueError,'SNAPSHOT_BYTES'):self.binder(m)
 def test_selection_path_swap_rejected(self):
  m=self.make();b=self.binder(m);pr=dict(m[3],path='OTHER')
  with self.assertRaisesRegex(ValueError,'PRIOR_REF'):b.bound_checkpoint_ref({'continuation_ref':pr})
 def test_no_arbitrary_checkpoint_read(self):
  b=self.binder(self.make())
  with self.assertRaisesRegex(ValueError,'UNREGISTERED_CHECKPOINT'):b.checked({'path':'OTHER'})
 def test_bundle_identity_rejected(self):
  self.bundle['symbol']='OTHER'
  with self.assertRaisesRegex(ValueError,'CONTINUATION_STATE_IDENTITY'):self.binder(self.make())
 def test_absent_identity_rejected(self):
  self.bundle.pop('symbol');self.bundle.pop('asof');self.state.pop('symbol');self.state.pop('last_date')
  with self.assertRaisesRegex(ValueError,'CONTINUATION_IDENTITY_REQUIRED'):self.binder(self.make())
 def test_invalid_date_rejected(self):
  self.bundle['asof']='20260230';self.state['last_date']='20260230'
  with self.assertRaisesRegex(ValueError,'CONTINUATION_DATE'):self.binder(self.make())
 def test_bool_count_rejected(self):
  self.state['count']=1;self.bundle['state51']['count']=True
  with self.assertRaisesRegex(ValueError,'CONTINUATION_STATE_IDENTITY'):self.binder(self.make())
if __name__=='__main__':unittest.main()

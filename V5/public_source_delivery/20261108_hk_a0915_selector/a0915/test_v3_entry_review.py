import unittest,json,hashlib
import test_v3_dispatch as f
class Review(unittest.TestCase):
 setUp=f.Dispatch.setUp
 pin_policy=f.Dispatch.pin_policy
 runone=f.Dispatch.runone
 def test_unrecognized_mode_not_fallback(self):
  self.r['reader_mode']='UNREVIEWED'
  with self.assertRaisesRegex(ValueError,'READER_MODE'):self.runone()
  self.assertEqual(self.events,[])
 def test_input_mutation_before_save(self):
  count=0
  def gate():
   nonlocal count
   count+=1
   if count==2:(self.root/'input.json').write_bytes(b'{}')
  self.r['gate']=gate
  with self.assertRaisesRegex(ValueError,'CHANGED_BEFORE_SAVE'):self.runone()
  self.assertFalse(self.r['output'].exists());self.assertEqual(self.events,['enter','exit'])
 def test_duplicate_contract_keys_rejected(self):
  raw=(self.root/'contract.json').read_bytes();raw=raw[:-1]+b',"schema":"A0915_TEXT_READER_CONTRACT_V3"}';(self.root/'contract.json').write_bytes(raw);self.r['text_contract'].update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
  with self.assertRaisesRegex(ValueError,'DUPLICATE_KEY'):self.runone()
 def test_synthetic_trigger_cannot_accept_unverified_kind(self):
  self.data['data_kind']='RECORDED_UNVERIFIED';raw=json.dumps(self.data).encode();(self.root/'input.json').write_bytes(raw);self.r['input_sha256']=hashlib.sha256(raw).hexdigest();self.policy['input_sha256']=self.r['input_sha256'];self.pin_policy()
  with self.assertRaisesRegex(ValueError,'DATA_KIND_BINDING'):self.runone()
 def test_manual_replay_preserves_synthetic_label(self):
  self.r['trigger']='MANUAL_RECORDED_REPLAY';x=self.runone();self.assertEqual(x['report']['result']['recorded_input']['data_kind'],'SYNTHETIC_TEST');self.assertFalse(x['report']['production_allowed'])
if __name__=='__main__':unittest.main()

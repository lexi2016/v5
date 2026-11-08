import unittest,tempfile,contextlib,hashlib,json
from pathlib import Path
import bridge
outbox=bridge.outbox

def raw_inputs():
 return {k:json.dumps({'business_date':'20261109','available_at':'2026-11-09T08:00:00+08:00','status':'UNKNOWN','text':'SYNTHETIC ONLY '+k}).encode() for k in ('freeze','morning-materials','jk-verify')}
class Integration(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=raw_inputs();self.p={k:hashlib.sha256(v).hexdigest() for k,v in self.r.items()}
  self.config={'authorized':True,'node':'0810','task_id':'SYNTHETIC','environment_id':'ISOLATED','binding_version':'TEST_V1','authorization_ref':'SYNTHETIC_NOT_LIVE','channel':'chatgpt','destination':'SYNTHETIC_NO_REAL_RECIPIENT','input_sha256':outbox.sha(outbox.canonical(self.p)),'code_version':'TEST','data_date':'20261109','run_id':'MANUAL_SYNTHETIC','output_root':self.tmp.name,'owner_context':contextlib.nullcontext,'gate':lambda:True,'sender':lambda **kw:self.fail('must not send'),'reconciler':lambda **kw:self.fail('must not reconcile')}
  outbox.REGISTRY={'fixture':self.config}
  bridge.REGISTRY={'fixture':{'domain':'synthetic','review':'SYNTHETIC_REVIEW_ONLY','outbox_registration':'fixture','business_date':'20261109','cutoff':'2026-11-09T08:10:00+08:00','pins':self.p,'outbox_identity':{k:self.config[k] for k in bridge.IDENTITY_KEYS}}}
 def tearDown(self):
  outbox.REGISTRY={};bridge.REGISTRY={};self.tmp.cleanup()
 def test_prepare_only_and_reuse(self):
  first=bridge.prepare('fixture',self.r);second=bridge.prepare('fixture',self.r)
  self.assertEqual(first['outbox']['state'],'PREPARED');self.assertFalse(first['outbox']['sent']);self.assertTrue(second['outbox']['reused']);self.assertFalse(first['business_accepted'])
 def test_unregistered(self):
  self.assertRaises(ValueError,bridge.prepare,'missing',self.r)
 def test_changed_input(self):
  self.r['freeze']+=b' ';self.assertRaises(ValueError,bridge.prepare,'fixture',self.r)
 def test_recipient_change(self):
  self.config['destination']='OTHER';self.assertRaises(ValueError,bridge.prepare,'fixture',self.r)
 def test_output_root_change(self):
  self.config['output_root']='/tmp';self.assertRaises(ValueError,bridge.prepare,'fixture',self.r)
 def test_module_origin(self):
  original=bridge.outbox.__file__
  try:
   bridge.outbox.__file__='/tmp/other.py';self.assertRaises(ValueError,bridge.prepare,'fixture',self.r)
  finally:bridge.outbox.__file__=original
 def test_gate(self):
  self.config['gate']=lambda:False;self.assertRaises(ValueError,bridge.prepare,'fixture',self.r)
 def test_missing_section_preserved(self):
  del self.r['freeze'];del self.p['freeze'];self.config['input_sha256']=outbox.sha(outbox.canonical(self.p));bridge.REGISTRY['fixture']['outbox_identity']['input_sha256']=self.config['input_sha256']
  result=bridge.prepare('fixture',self.r);self.assertIn('freeze',result['bundle']['missing']);self.assertEqual(result['outbox']['state'],'PREPARED')
 def test_unknown_attempt_not_reset(self):
  first=bridge.prepare('fixture',self.r);db=outbox._connection(self.config)
  try:outbox._transition(db,first['outbox']['key'],'ATTEMPT_UNKNOWN',{'synthetic':True})
  finally:db.close()
  again=bridge.prepare('fixture',self.r);self.assertEqual(again['outbox']['state'],'ATTEMPT_UNKNOWN');self.assertTrue(again['outbox']['reused']);self.assertFalse(again['outbox']['sent'])
 def test_production_blocked(self):
  bridge.REGISTRY['fixture']['domain']='production';self.assertRaises(ValueError,bridge.prepare,'fixture',self.r)
if __name__=='__main__':unittest.main()

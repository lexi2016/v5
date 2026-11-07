import contextlib,tempfile,unittest,sqlite3
from pathlib import Path
import outbox as o
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.calls=[]
  self.c=dict(run_id='synthetic-run',authorized=True,node='0810',task_id='synthetic-task',environment_id='synthetic-env',binding_version='1',authorization_ref='synthetic-authorized-user-channel',channel='chatgpt',destination='synthetic-room',input_sha256='a'*64,code_version='fixture',data_date='20261106',output_root=self.tmp.name,owner_context=contextlib.nullcontext,gate=lambda:True,sender=self.send,reconciler=lambda **k:{})
  o.REGISTRY['fixture']=self.c
 def tearDown(self):o.REGISTRY.clear();self.tmp.cleanup()
 def send(self,**kw):
  self.calls.append(kw);return {'channel':'chatgpt','destination':'synthetic-room','status':'accepted','message_id':'SYNTHETIC-ID'}
 def prepare(self):return o.prepare('fixture','SYNTHETIC ONLY')['key']
 def test_missing_binding(self):
  with self.assertRaisesRegex(ValueError,'NO_REVIEWED'):o.prepare('none','test')
 def test_gate(self):
  self.c['gate']=lambda:False
  with self.assertRaisesRegex(ValueError,'GATE'):self.prepare()
  self.assertEqual(self.calls,[])
 def test_duplicate_and_accepted_not_delivered(self):
  key=self.prepare();self.assertTrue(o.prepare('fixture','SYNTHETIC ONLY')['reused'])
  a=o.attempt('fixture',key);self.assertEqual(a['state'],'ACCEPTED');self.assertFalse(a['delivery_verified'])
  self.assertFalse(o.attempt('fixture',key)['attempted']);self.assertFalse(o.reconcile('fixture',key)['delivery_verified']);self.assertEqual(len(self.calls),1)
 def test_unknown_never_retry(self):
  def fail(**kw):self.calls.append(kw);raise TimeoutError()
  self.c['sender']=fail;key=self.prepare();self.assertEqual(o.attempt('fixture',key)['state'],'ATTEMPT_UNKNOWN')
  self.assertFalse(o.attempt('fixture',key)['attempted']);self.assertEqual(len(self.calls),1)
 def test_changed_binding(self):
  key=self.prepare();self.c['input_sha256']='b'*64
  with self.assertRaisesRegex(ValueError,'CHANGED'):o.attempt('fixture',key)
  self.assertEqual(self.calls,[])
 def test_reconcile_explicit_fixture(self):
  key=self.prepare();o.attempt('fixture',key)
  self.c['reconciler']=lambda **kw:dict(delivery_confirmed=True,channel='chatgpt',destination='synthetic-room',message_id='SYNTHETIC-ID',payload_sha256=o.sha(b'SYNTHETIC ONLY'),evidence_ref='SYNTHETIC-DELIVERY-PROOF')
  self.assertTrue(o.reconcile('fixture',key)['delivery_verified'])
  self.assertFalse(o.attempt('fixture',key)['attempted'])
 def test_code_change_cannot_resend(self):
  key=self.prepare();o.attempt('fixture',key);self.c['code_version']='new'
  with self.assertRaisesRegex(ValueError,'CHANGED'):self.prepare()
  self.assertEqual(len(self.calls),1)
 def test_tampered_state_rejected(self):
  key=self.prepare();o.attempt('fixture',key)
  db=sqlite3.connect(Path(self.tmp.name)/'outbox.sqlite3');db.execute("UPDATE items SET state='DELIVERED_VERIFIED',receipt=NULL");db.commit();db.close()
  with self.assertRaisesRegex(ValueError,'JOURNAL'):o.reconcile('fixture',key)
  with self.assertRaisesRegex(ValueError,'JOURNAL'):o.attempt('fixture',key)
 def test_wrong_recipient_receipt_unknown(self):
  self.c['sender']=lambda **kw:dict(channel='chatgpt',destination='wrong',status='accepted',message_id='synthetic')
  self.assertEqual(o.attempt('fixture',self.prepare())['state'],'ATTEMPT_UNKNOWN')
 def test_wrong_message_proof_rejected(self):
  key=self.prepare();o.attempt('fixture',key)
  self.c['reconciler']=lambda **kw:dict(delivery_confirmed=True,channel='chatgpt',destination='synthetic-room',message_id='WRONG',payload_sha256=o.sha(b'SYNTHETIC ONLY'),evidence_ref='SYNTHETIC')
  with self.assertRaisesRegex(ValueError,'MESSAGE_ID'):o.reconcile('fixture',key)
if __name__=='__main__':unittest.main()

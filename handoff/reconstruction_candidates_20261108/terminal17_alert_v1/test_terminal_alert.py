import contextlib,copy,json,tempfile,unittest
import terminal_alert as a
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.doc={'schema':'RETRY_TERMINAL_NODE_V1','node':'terminal-1700','target_date':'20261108','identity':'fixture-identity','checked_at':'2026-11-08T17:00:00+08:00','status':'NOT_RUN'}
  self.raw=a.canonical(self.doc)
 def assembly(self,**updates):
  d=self.doc|updates;raw=a.canonical(d)
  return a.assemble(raw,a.sha(raw),'20261108','fixture-identity')
 def bind(self):
  c=dict(task_id='fixture-task',node='1700',environment_id='fixture-env',binding_version='fixture-v1',authorization_ref='SYNTHETIC_ONLY',channel='chatgpt',destination='SYNTHETIC_NO_RECIPIENT',input_sha256=a.sha(self.raw),code_version='fixture',data_date='20261108',run_id='fixture-run',output_root=self.tmp.name,authorized=True,owner_context=contextlib.nullcontext,gate=lambda:True,sender=lambda **kw:self.fail('sender called'),reconciler=lambda **kw:self.fail('reconciler called'))
  a.REGISTRY={'fixture':dict(domain='synthetic',outbox_config=c,identity={k:c[k] for k in a.KEYS},report_sha256=a.sha(self.raw),report_identity='fixture-identity')}
  return c
 def test_unknown(self): self.assertEqual(self.assembly(status='future-status')['reported_generation_status'],'UNKNOWN')
 def test_running(self): self.assertTrue(self.assembly(status='UNKNOWN_RECONCILIATION_REQUIRED')['alert_required'])
 def test_completed_not_business_accepted(self):
  r=self.assembly(status='COMPLETED_REVIEW_VERIFIED');self.assertFalse(r['business_accepted']);self.assertFalse(r['generation_independently_verified'])
 def test_dates(self):
  for t in ['2026-11-08T16:59:59+08:00','2026-11-09T17:00:00+08:00','2026-11-08T17:00:00']:
   with self.subTest(t=t),self.assertRaises(ValueError):self.assembly(checked_at=t)
 def test_wrong_identity(self):
  with self.assertRaises(ValueError):self.assembly(identity='different')
 def test_wrong_node(self):
  with self.assertRaises(ValueError):self.assembly(node='retry-1640')
 def test_digest(self):
  with self.assertRaises(ValueError):a.assemble(self.raw,'0'*64,'20261108','fixture-identity')
 def test_prepare_reuse_no_send(self):
  self.bind();r=a.prepare('fixture',self.raw);self.assertEqual(r['outbox']['state'],'PREPARED');self.assertFalse(r['delivery_verified']);self.assertTrue(a.prepare('fixture',self.raw)['outbox']['reused'])
 def test_reused_delivery_states_not_unsent(self):
  self.bind();r=a.prepare('fixture',self.raw);key=r['outbox']['key']
  ob=a._outbox();c=a.REGISTRY['fixture']['outbox_config'];db=ob._connection(c)
  try:
   body=db.execute('SELECT payload FROM items WHERE key=?',(key,)).fetchone()[0]
   receipt=dict(channel=c['channel'],destination=c['destination'],message_id='synthetic-message',payload_sha256=a.sha(body))
   for state in ('ATTEMPT_UNKNOWN','ACCEPTED','DELIVERED_VERIFIED'):
    ob._transition(db,key,state,receipt)
    result=a.prepare('fixture',self.raw)
    self.assertEqual(result['delivery_state'],state)
    self.assertEqual(result['alert']['delivery_status'],'UNKNOWN')
    self.assertFalse(result['sent_in_this_call']);self.assertFalse(result['delivery_verified'])
  finally:db.close()
 def test_gate(self):
  c=self.bind();c['gate']=lambda:False
  with self.assertRaisesRegex(ValueError,'GATE'):a.prepare('fixture',self.raw)
 def test_recipient(self):
  c=self.bind();c['destination']='real-recipient'
  with self.assertRaises(ValueError):a.prepare('fixture',self.raw)
 def test_production(self):
  self.bind();a.REGISTRY['fixture']['domain']='production'
  with self.assertRaises(ValueError):a.prepare('fixture',self.raw)
 def test_absent_binding(self):
  a.REGISTRY={}
  with self.assertRaises(ValueError):a.prepare('fixture',self.raw)
if __name__=='__main__':unittest.main()

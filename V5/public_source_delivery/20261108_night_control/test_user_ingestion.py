import unittest,copy,json,pathlib,tempfile,contextlib,hashlib,os,shutil
import night_handoff as n

def fixture():
 mapping={'announcements':'announcements','essential_news':'news','preopen_memo':'notes','preopen_analysis':'notes'}
 policy={'schema':'USER_RESULT_INGESTION_POLICY_V1','version':'v1','cutoff':'2026-11-09T08:00:00+08:00','column_map':mapping,'expected_parent_identity':None}
 row={'symbol':'000001.SZ','category':'announcements','status':'AVAILABLE','event_at':'2026-11-09T07:00:00+08:00','observed_at':'2026-11-09T07:01:00+08:00','available_at':'2026-11-09T07:02:00+08:00','details':{'source_url':'https://example.invalid/fixture','title':'SYNTHETIC','body_reference':'fixture paragraph 1','facts':'fixture text','inferences':'UNKNOWN','counterevidence':'UNKNOWN'}}
 doc={'schema':'USER_RESEARCH_RETURN_V1','target_date':'20261109','list_sha256':'a'*64,'version':'v1','records':[row]}
 return policy,doc
class Pure(unittest.TestCase):
 def call(self,p,d,parent=None):return n.ingest_user_results('20261109','a'*64,['000001.SZ'],p,d,parent)
 def test_full_scope_and_unknown(self):
  p,d=fixture();x=self.call(p,d);self.assertEqual(x['scope_count'],1);self.assertEqual(x['missing_count'],3);self.assertEqual(x['records'][0]['columns']['announcements'][0]['status'],'AVAILABLE');self.assertFalse(x['research_complete']);self.assertEqual(x['delivery_status'],'NOT_SENT')
 def test_late_then_append(self):
  p,d=fixture();d['records'][0]['available_at']='2026-11-09T08:01:00+08:00';old=self.call(p,d);self.assertEqual(len(old['late_records']),1);self.assertIsNone(old['records'][0]['columns']['announcements'][0]['details']);saved=copy.deepcopy(old)
  p.update(version='v2',cutoff='2026-11-09T08:02:00+08:00',expected_parent_identity=old['identity']);d['version']='v2';new=self.call(p,d,old);self.assertEqual(new['parent_identity'],old['identity']);self.assertEqual(new['late_records'],[]);self.assertEqual(old,saved)
 def test_wrong_parent(self):
  p,d=fixture();old=self.call(p,d);p.update(version='v2',expected_parent_identity=old['identity']);d['version']='v2';old['missing_count']=0
  with self.assertRaises(ValueError):self.call(p,d,old)
 def test_scope_duplicate(self):
  for symbol in ('999999.SH','000001.SZ'):
   p,d=fixture();d['records'].append(copy.deepcopy(d['records'][0]));d['records'][-1]['symbol']=symbol
   with self.assertRaises(ValueError):self.call(p,d)
 def test_statuses_not_absence_assertion(self):
  for status in ('NOT_PUBLISHED','NOT_OBSERVED','BODY_UNAVAILABLE','UNKNOWN'):
   p,d=fixture();d['records'][0].update(status=status,event_at=None,details={});x=self.call(p,d);self.assertEqual(x['records'][0]['columns']['announcements'][0]['status'],status)
 def test_order_and_missing_evidence(self):
  p,d=fixture();d['records'][0]['observed_at']='2026-11-09T06:00:00+08:00'
  with self.assertRaises(ValueError):self.call(p,d)
  p,d=fixture();d['records'][0]['details'].pop('body_reference')
  with self.assertRaises(ValueError):self.call(p,d)
 def test_map_no_guessed_default(self):
  p,d=fixture();p['column_map']['preopen_analysis']='fourth'
  with self.assertRaises(ValueError):self.call(p,d)
class ExistingEntry(unittest.TestCase):
 def test_real_guard_pin_freeze_reuse(self):
  source=os.environ.get('SAFEIO_SOURCE')
  if not source:self.skipTest('existing exact safeio path required')
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);safe=root/n.SAFE_PATH;safe.parent.mkdir(parents=True);shutil.copyfile(source,safe)
   data={'schema':'DATED_FIXED_REFERENCE_TOP200_V1','rows':[{'symbol':f'{i:06d}.SZ','rank':i,'actual_date':'20261106'} for i in range(1,201)]};raw=json.dumps(data).encode();(root/'list.json').write_bytes(raw);digest=n.sha(raw)
   p,d=fixture();d['list_sha256']=digest
   def pin(name,obj):
    raw=json.dumps(obj).encode();(root/name).write_bytes(raw);return {'path':name,'sha256':n.sha(raw),'bytes':len(raw)}
   events=[]
   @contextlib.contextmanager
   def guard():
    events.append('enter')
    try:yield
    finally:events.append('exit')
   r={'target_date':'20261109','gate':lambda:events.append('gate'),'owner_guard':guard,'root':root,'list_path':'list.json','list_sha256':digest,'output':root/'out','result_binding':{'policy':pin('policy.json',p),'results':pin('results.json',d),'parent':None}}
   x=n._execute('morning-materials','SYNTHETIC','TEMP',r);self.assertEqual(x['report']['status'],'USER_RESULTS_INGESTED_UNVERIFIED');self.assertEqual(x['report']['user_results']['missing_count'],799);self.assertEqual(x['save']['byte_readback'],'PASS');y=n._execute('morning-materials','SYNTHETIC','TEMP',r);self.assertTrue(y['save']['reused']);self.assertEqual(events.count('enter'),2);self.assertEqual(events.count('exit'),2)
   (root/'results.json').write_bytes(b'{}')
   with self.assertRaises(ValueError):n._execute('morning-materials','SYNTHETIC','TEMP',r)
 def test_registry_closed(self):self.assertEqual(n.dispatch('morning-materials','x','x')['reason'],'NO_REVIEWED_ORIGINAL_BINDING')
if __name__=='__main__':unittest.main()

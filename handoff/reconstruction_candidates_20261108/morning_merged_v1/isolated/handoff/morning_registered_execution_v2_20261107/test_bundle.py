import unittest, hashlib,json,copy
import bundle_candidate as b

def fixture():
 docs={k:{'business_date':'20261109','available_at':'2026-11-09T08:00:00+08:00','status':'UNKNOWN','text':'SYNTHETIC '+k} for k in ('freeze','morning-materials','jk-verify')}
 raws={k:json.dumps(v).encode() for k,v in docs.items()}
 return raws,{k:hashlib.sha256(v).hexdigest() for k,v in raws.items()}
class Test(unittest.TestCase):
 def test_bundle(self):
  r,p=fixture();x=b.assemble(r,p,'20261109','2026-11-09T08:10:00+08:00');self.assertEqual(x['delivery_status'],'NOT_SENT');self.assertEqual(len(x['sections']),3);self.assertEqual(x['sections'][0]['status'],'UNKNOWN')
 def test_missing(self):
  r,p=fixture();del r['freeze'];x=b.assemble(r,p,'20261109','2026-11-09T08:10:00+08:00');self.assertEqual(x['status'],'PARTIAL_LOCAL_ASSEMBLY');self.assertIn('freeze',x['missing'])
 def test_mutation(self):
  r,p=fixture();r['freeze']+=b' ';self.assertRaises(ValueError,b.assemble,r,p,'20261109','2026-11-09T08:10:00+08:00')
 def test_future(self):
  r,p=fixture();r['freeze']=r['freeze'].replace(b'08:00:00',b'08:11:00');p['freeze']=hashlib.sha256(r['freeze']).hexdigest();self.assertRaises(ValueError,b.assemble,r,p,'20261109','2026-11-09T08:10:00+08:00')
 def test_wrong_day(self):
  r,p=fixture();self.assertRaises(ValueError,b.assemble,r,p,'20261110','2026-11-10T08:10:00+08:00')
 def test_naive(self):
  r,p=fixture();self.assertRaises(ValueError,b.assemble,r,p,'20261109','2026-11-09T08:10:00')
 def test_cutoff_contract(self):
  r,p=fixture()
  for cutoff in ('2026-11-10T08:10:00+08:00','2026-11-09T09:10:00+08:00'):
   self.assertRaises(ValueError,b.assemble,r,p,'20261109',cutoff)
 def test_extra(self):
  r,p=fixture();r['extra']=b'{}';self.assertRaises(ValueError,b.assemble,r,p,'20261109','2026-11-09T08:10:00+08:00')
 def test_deterministic(self):
  r,p=fixture();self.assertEqual(b.assemble(r,p,'20261109','2026-11-09T08:10:00+08:00'),b.assemble(r,p,'20261109','2026-11-09T08:10:00+08:00'))
if __name__=='__main__':unittest.main()

import unittest, copy
import registered as r

def fixture():
 reg={'node':'morning-delivery','domain':'synthetic','business_date':'20261109','source_date':'20261106','cutoff':'2026-11-09T08:10:00+08:00'}
 policy={'assembly_schema':'MORNING_0810_PREVIEW_V1','section_max_age_seconds':{k:600 for k in ('freeze','morning-materials','jk-verify')}}
 docs={'assembly_sections':{k:{'business_date':'20261109','source_date':'20261106','observed_at':'2026-11-09T08:00:00+08:00','available_at':'2026-11-09T08:01:00+08:00','status':'UNKNOWN','content':{'note':'SYNTHETIC TEST'},'source_reference':'fixture:'+k} for k in policy['section_max_age_seconds']}}
 return reg,policy,docs
class Test(unittest.TestCase):
 def calc(self,reg,policy,docs):return r.calculate(reg,policy,docs,None)
 def test_branch_assembles(self):
  args=fixture();x=self.calc(*args);self.assertEqual(x['status'],'PREVIEW_ASSEMBLED_NOT_ADMITTED');self.assertEqual(len(x['sections']),3);self.assertEqual(x['delivery_status'],'NOT_SENT');self.assertFalse(x['business_accepted']);self.assertFalse(x['formal_freeze']);self.assertEqual(x['sections'][0]['status'],'UNKNOWN')
 def test_missing(self):
  a,b,c=fixture();del c['assembly_sections']['freeze'];x=self.calc(a,b,c);self.assertEqual(x['missing'],['freeze']);self.assertEqual(x['status'],'PARTIAL_PREVIEW_NOT_ADMITTED')
 def test_production_and_old_default_still_block(self):
  a,b,c=fixture();a['domain']='production';self.assertEqual(self.calc(a,b,c)['status'],'BLOCKED_DELIVERY_ASSEMBLY_NOT_BOUND');self.assertEqual(self.calc({'node':'morning-delivery'},{},{})['status'],'BLOCKED_DELIVERY_ASSEMBLY_NOT_BOUND')
 def test_cutoff(self):
  for value in ('2026-11-10T08:10:00+08:00','2026-11-09T08:11:00+08:00','2026-11-09T08:10:00'):
   a,b,c=fixture();a['cutoff']=value
   with self.assertRaises(ValueError):self.calc(a,b,c)
 def test_record_timing(self):
  for key,value in [('available_at','2026-11-09T08:11:00+08:00'),('available_at','2026-11-09T07:59:00+08:00'),('observed_at','2026-11-09T07:59:59+08:00')]:
   a,b,c=fixture();c['assembly_sections']['freeze'][key]=value
   with self.assertRaises(ValueError):self.calc(a,b,c)
 def test_scope_date_and_age(self):
  for change in ('extra','date','future_source','age'):
   a,b,c=fixture()
   if change=='extra':c['assembly_sections']['other']={}
   if change=='date':c['assembly_sections']['freeze']['business_date']='20261108'
   if change=='future_source':c['assembly_sections']['freeze']['source_date']='20261110'
   if change=='age':b['section_max_age_seconds']['freeze']=True
   with self.assertRaises(ValueError):self.calc(a,b,c)
 def test_detached_and_deterministic(self):
  a,b,c=fixture();x=self.calc(a,b,c);self.assertEqual(x,self.calc(a,b,c));c['assembly_sections']['freeze']['content']['note']='changed';self.assertEqual(x['sections'][0]['content']['note'],'SYNTHETIC TEST')
 def test_no_registry_enabled(self):self.assertEqual(r.TRUSTED_RUNS,());self.assertEqual(r.dispatch('morning-delivery','x','x',None)['status'],'BLOCKED_NO_TRUSTED_REGISTRATION')
if __name__=='__main__':unittest.main()

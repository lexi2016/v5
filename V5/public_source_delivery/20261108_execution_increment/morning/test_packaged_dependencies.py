import datetime as dt,unittest
from unittest.mock import patch
import registered as m
class PackagedTests(unittest.TestCase):
 def test_all_pinned_modules_load_without_path_override(self):
  safe=m.module('safeio')
  for key in ('crosscheck','jk','prep'):self.assertIsNotNone(m.module(key,safe))
 def test_wrong_bindings_digest_refused(self):
  with patch.object(m,'CODE_BINDINGS_SHA','0'*64):
   with self.assertRaisesRegex(ValueError,'CODE_BINDINGS_CHANGED'):m.codes()
 def test_jk_actual_module_agreement(self):
  safe=m.module('safeio');cut='2026-11-09T08:00:00+08:00'
  reg={'node':'jk-verify','source_date':'20261109','business_date':'20261109','cutoff':cut}
  policy={'source_ids':['S1','S2'],'required_comparisons':[{'symbol':'X','field':'open','source_ids':['S1','S2']}],'max_observation_age_seconds':600}
  rows=[{'id':s,'source_id':s,'source_date':'2026-11-09','symbol':'X','field':'open','value':'1','url':'https://example.org/'+s,'observed_at':'2026-11-09T07:59:00+08:00','available_at':'2026-11-09T07:59:30+08:00'} for s in ['S1','S2']]
  policy['provider_catalog']={s:{'independence_group':s,'allowed_urls':['https://example.org/'+s]} for s in ('S1','S2')}
  policy['required_comparisons'][0]['semantic_contract']={'unit':'index_points','basis':'unadjusted','currency':'JPY','raw_fields':{s:['open'] for s in ('S1','S2')}}
  for row in rows:row.update(unit='index_points',basis='unadjusted',currency='JPY')
  result=m.calculate(reg,policy,{'observations':{'source_day':'2026-11-09','records':rows}},safe)
  self.assertEqual(result['status'],'RECONCILED');self.assertFalse(result['source_admission']);self.assertEqual(result['collector_calls'],0)
 def test_delivery_stays_unbound(self):
  r=m.calculate({'node':'morning-delivery'},{},{},m.module('safeio'))
  self.assertEqual(r['delivery_status'],'NOT_SENT');self.assertFalse(r['business_accepted'])
if __name__=='__main__':unittest.main()

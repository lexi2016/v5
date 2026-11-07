import unittest,tempfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
import node_results_api as api
class Tests(unittest.TestCase):
 def call(self,node,records,gate=lambda:None,overrides=None):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);pins={}
   for role,data in records.items():
    raw=json.dumps(data).encode();f=root/(role+'.json');f.write_bytes(raw);pins[role]={'path':f.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
   bindings=dict(ROOT=root,RECORD_DATE='20000102',SOURCE_DATE='20000101',ISO_SOURCE_DATE='2000-01-01',HK_FINAL_KEY='synthetic_final',PRIVATE_BINDINGS={node:pins});bindings.update(overrides or {})
   with patch.multiple(api,**bindings):return api.NodeResultsService(gate).get(node,'20000102')
 def hk(self):return {'hk_observations':{'data_date':'2000-01-01','mode':'MANUAL_HISTORICAL_LOOKUP_NOT_NATURAL_CAPTURE','source_admission':False,'natural_verified':False,'business_accepted':False,'production_allowed':False,'official_schedule':{'synthetic_final':None}}}
 def test_unbound_all(self):
  for n in ['morning-materials','opening-prep','a-top200','hk-continuous-close','hk-auction-final']:
   with self.assertRaisesRegex(ValueError,'NO_APPROVED_PRIVATE'):api.NodeResultsService(lambda:None).get(n,'20000102')
 def test_hk_unknown_final_retained(self):
  r=self.call('hk-auction-final',self.hk());self.assertEqual(r['delivery_status'],'NOT_SENT');self.assertFalse(r['natural_verified'])
 def test_hk_final_cannot_invent(self):
  d=self.hk();d['hk_observations']['official_schedule']['synthetic_final']='2000-01-01T16:10:00+08:00'
  with self.assertRaisesRegex(ValueError,'HK_FINAL'):self.call('hk-auction-final',d)
 def test_resource_gate_preserved(self):
  def gate():raise ValueError('RESOURCE_HEADROOM')
  with self.assertRaisesRegex(ValueError,'RESOURCE_HEADROOM'):self.call('hk-auction-final',self.hk(),gate)
 def test_opening_no_buy_and_pit(self):
  d={'group_review':{'source_date':'20000101','top_rows':200,'buy_qualification':False,'natural_verified':False,'rows':[{'no_buy':True} for _ in range(200)]},'ranking_provenance_source':{'ranking_provenance':{'source':'G4','historical_PIT':False,'source_admission':False}}}
  self.assertEqual(self.call('opening-prep',d)['business_acceptance'],'NOT_GRANTED');d['ranking_provenance_source']['ranking_provenance']['historical_PIT']=0
  with self.assertRaisesRegex(ValueError,'RANKING_PROVENANCE'):self.call('opening-prep',d)
 def test_postclose_not_1500_capture(self):
  d={'consolidated_review':{'data_date':'2000-01-01','scope':'POST_CLOSE_RETROSPECTIVE_ONLY_NOT_1500_CAPTURE','natural_verified':False,'business_accepted':False,'rows':[{'historical_PIT':False,'source_admission':False,'buy_eligibility':'NOT_EVALUATED'} for _ in range(200)]}}
  self.assertEqual(self.call('a-top200',d)['trigger_type'],'POST_CLOSE_RETROSPECTIVE_ONLY');d['consolidated_review']['rows'][0]['source_admission']=True
  with self.assertRaisesRegex(ValueError,'QUALIFICATION'):self.call('a-top200',d)
 def test_partial_date_bindings_refused(self):
  for field in ['RECORD_DATE','SOURCE_DATE','ISO_SOURCE_DATE']:
   for value in [None,'',False,'invalid']:
    with self.subTest(field=field,value=value),self.assertRaisesRegex(ValueError,'PRIVATE_BINDING'):self.call('hk-auction-final',self.hk(),overrides={field:value})
 def test_partial_hk_binding_refused(self):
  for value in [None,'',False]:
   with self.assertRaisesRegex(ValueError,'INCOMPLETE_HK_BINDING'):self.call('hk-auction-final',self.hk(),overrides={'HK_FINAL_KEY':value})
 def test_missing_hk_field_not_unknown(self):
  d=self.hk();d['hk_observations']['official_schedule']={}
  with self.assertRaisesRegex(ValueError,'HK_FINAL_FIELD_MISSING'):self.call('hk-auction-final',d)
 def test_annotation_partial_binding_refused_before_loading_code(self):
  records={'source_cards':{},'announcement_event':{},'announcement_code':{}}
  for values in [{'ANNOTATION_SYMBOL':None,'ANNOTATION_DATES':['2000-01-01']},{'ANNOTATION_SYMBOL':'SYNTHETIC','ANNOTATION_DATES':[]},{'ANNOTATION_SYMBOL':'SYNTHETIC','ANNOTATION_DATES':[None]}]:
   with self.assertRaisesRegex(ValueError,'INCOMPLETE_ANNOTATION_BINDING'):self.call('morning-materials',records,overrides=values)
 def test_missing_role_or_pin_refused(self):
  with self.assertRaisesRegex(ValueError,'INCOMPLETE_NODE_BINDING'):self.call('opening-prep',{})
  with self.assertRaisesRegex(ValueError,'INCOMPLETE_PIN_BINDING'):self.call('hk-auction-final',self.hk(),overrides={'PRIVATE_BINDINGS':{'hk-auction-final':{'hk_observations':{}}}})
if __name__=='__main__':unittest.main()

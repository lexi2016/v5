import unittest,tempfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
import node_results_api as api
class Tests(unittest.TestCase):
 def call(self,provenance):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);data={'source_date':'2000-01-01','mode':'HISTORICAL_TEXT_ASSOCIATION_ONLY','natural_verified':False,'business_accepted':False}
   if provenance is not None:data['ranking_provenance']=provenance
   raw=json.dumps(data).encode();(root/'synthetic.json').write_bytes(raw);pins={'morning-materials':{'source_cards':{'path':'synthetic.json','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}}}
   with patch.multiple(api,ROOT=root,RECORD_DATE='20000102',SOURCE_DATE='20000101',CARD_SOURCE_DATE='2000-01-01',PRIVATE_BINDINGS=pins):return api.NodeResultsService(lambda:None).get('morning-materials','20000102')
 def test_unbound(self):
  with self.assertRaisesRegex(ValueError,'NO_APPROVED_PRIVATE'):api.NodeResultsService(lambda:None).get('morning-materials','20000102')
 def test_missing(self):
  with self.assertRaisesRegex(ValueError,'PIT_PROVENANCE'):self.call(None)
 def test_strict_flags(self):
  good={'source':'G4','historical_PIT':False,'source_admission':False}
  for field,values in [('source',['other',None]),('historical_PIT',[True,0,None]),('source_admission',[True,0,None])]:
   for value in values:
    with self.subTest(field=field,value=value):
     with self.assertRaisesRegex(ValueError,'PIT_PROVENANCE'):self.call(dict(good,**{field:value}))
 def test_valid_flags_still_no_admission(self):
  r=self.call({'source':'G4','historical_PIT':False,'source_admission':False});self.assertFalse(r['natural_verified']);self.assertEqual(r['business_acceptance'],'NOT_GRANTED');self.assertEqual(r['delivery_status'],'NOT_SENT')
if __name__=='__main__':unittest.main()

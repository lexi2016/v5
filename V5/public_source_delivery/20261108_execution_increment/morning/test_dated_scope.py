import unittest, types,sys,copy
sys.modules.setdefault('safeio',types.ModuleType('safeio'))
import importlib.util,pathlib
PREP_PATH=pathlib.Path(__file__).with_name('prepare.py')
if not PREP_PATH.exists():PREP_PATH=pathlib.Path(__file__).resolve().parents[2]/'handoff/preopen_top200_group_review_20261107/prepare.py'
spec=importlib.util.spec_from_file_location('dated_prepare_test',PREP_PATH);p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

def fixture():
 symbols=[f'{i:06d}.SZ' for i in range(1,202)]
 scope={'schema':'DATED_RESEARCH_POOL_V1','source_date':'20261109','pool_version':'fixture-pool','symbols':symbols}
 top={'schema':'DATED_FIXED_REFERENCE_TOP200_V1','source_date':'20261109','pool_version':'fixture-pool','scope_count':201,'rows':[{'symbol':s,'rank':i+1,'actual_date':'20261109','change_pct_display':0} for i,s in enumerate(symbols[:200])]}
 panel={'schema':'PAR_SCREEN_DISPLAY_V1','source_date':'20261109','pool_version':'fixture-pool','scope_count':201,'rows':[{'symbol':s,'name':'test','actual_date':'20261109','owner_outcome':'COMPUTED_CURRENT','source_family':'SYNTHETIC','layers':{g:{'after_risk':'UNKNOWN'} for g in p.GROUPS}} for s in symbols]}
 return top,panel,scope
class DatedScopeTests(unittest.TestCase):
 def test_dynamic_scope(self):
  t,s,c=fixture();x=p.annotate_dated(t,s,c);self.assertEqual(len(x),200);self.assertTrue(all(r['has_unknown'] and r['no_buy'] for r in x));self.assertEqual(x[0]['symbol'],t['rows'][0]['symbol'])
 def test_old_entry_still_rejects_dated(self):self.assertRaises(ValueError,p.annotate,*fixture()[:2])
 def test_wrong_members(self):
  t,s,c=fixture();c['symbols'][-1]='999999.SH';self.assertRaises(ValueError,p.annotate_dated,t,s,c)
 def test_duplicate_scope(self):
  t,s,c=fixture();c['symbols'][-1]=c['symbols'][0];self.assertRaises(ValueError,p.annotate_dated,t,s,c)
 def test_binding(self):
  for kind in ('version','date','denominator','rank','top_symbol'):
   t,s,c=fixture()
   if kind=='version':t['pool_version']='other'
   if kind=='date':c['source_date']='20261108'
   if kind=='denominator':t['scope_count']=5575
   if kind=='rank':t['rows'][0]['rank']=True
   if kind=='top_symbol':t['rows'][0]['symbol']='999999.SH'
   with self.assertRaises(ValueError):p.annotate_dated(t,s,c)
 def test_original_values_and_detachment(self):
  t,s,c=fixture();s['rows'][0]['layers']['original']['after_risk']='TRUE';x=p.annotate_dated(t,s,c);self.assertTrue(x[0]['existing_selected']);s['rows'][0]['layers']['original']['after_risk']='FALSE';self.assertEqual(x[0]['groups']['original'],'TRUE')
 def test_no_future_actual(self):
  t,s,c=fixture();t['rows'][0]['actual_date']='20261110';self.assertRaises(ValueError,p.annotate_dated,t,s,c)
if __name__=='__main__':unittest.main()

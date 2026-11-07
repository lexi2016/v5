import contextlib,copy,json,types,unittest
import exporter as e
class Tests(unittest.TestCase):
 def fixture(self):
  self.calls=[];self.docs={};self.asset={'path':'synthetic/daily51.json','sha256':'synthetic','bytes':1};self.success={'path':'synthetic/SUCCESS.json'};self.input={'path':'synthetic/input.json'}
  self.bundle={'symbol':'000001.SZ','asof':'20261106','state51':{'symbol':'000001.SZ','last_date':20261106,'formula_sha256':'F','original_engine_sha256':'E'},'daily51':{'trade_date':20261106,'values':{'一级买点':True,'二级买点':False}}}
  self.meta={'symbol':'000001.SZ','name':'SYNTHETIC','selection_date':20261106,'observation_date':20261109,'formula_asset':self.asset,'formula_status':'SYNTHETIC','qualification':'UNKNOWN','visual_status':'UNKNOWN'}
  self.docs['synthetic/daily51.json']=copy.deepcopy(self.bundle['daily51'])
  def checked(p):self.calls.append('checked');return json.dumps(self.docs.get(p['path'],{})).encode()
  @contextlib.contextmanager
  def owner():
   self.calls.append('lock_enter')
   try:yield
   finally:self.calls.append('lock_exit')
  def physical(*args):self.calls.append('physical');return copy.deepcopy(self.bundle),{}, {'synthetic':True}
  self.rt=types.SimpleNamespace(gate=lambda:self.calls.append('gate'),physical=physical,rt=types.SimpleNamespace(step=types.SimpleNamespace(FORMULA_SHA='F',ENGINE_SHA='E')))
  self.args=[self.rt,{'doc':{'symbol':'000001.SZ'},'ref':self.success},self.input,self.meta,20261106,20261109,checked,owner]
 def test_success_only_fields(self):
  self.fixture();r=e.extract(*self.args);self.assertTrue(r['original_hit']);self.assertFalse(r['approved_for_capture']);self.assertLess(self.calls.index('lock_enter'),self.calls.index('physical'))
 def test_unknown_not_false(self):
  self.fixture();self.bundle['daily51']['values']['一级买点']='UNKNOWN';self.docs['synthetic/daily51.json']=self.bundle['daily51'];r=e.extract(*self.args);self.assertIsNone(r['primary']);self.assertIsNone(r['original_hit'])
 def test_original_or_true_unknown(self):
  self.fixture();self.bundle['daily51']['values']['二级买点']='UNKNOWN';self.docs['synthetic/daily51.json']=self.bundle['daily51'];r=e.extract(*self.args);self.assertTrue(r['original_hit']);self.assertIsNone(r['secondary'])
 def test_wrong_asset(self):
  self.fixture();self.docs['synthetic/daily51.json']={}
  with self.assertRaisesRegex(ValueError,'ASSET'):e.extract(*self.args)
 def test_asset_type_mismatch(self):
  self.fixture();self.docs['synthetic/daily51.json']['values']['一级买点']=1
  with self.assertRaisesRegex(ValueError,'ASSET'):e.extract(*self.args)
 def test_old_day(self):
  self.fixture();self.bundle['asof']='20261105'
  with self.assertRaisesRegex(ValueError,'DATE'):e.extract(*self.args)
 def test_gate(self):
  self.fixture();self.rt.gate=lambda:(_ for _ in ()).throw(ValueError('RESOURCE'))
  with self.assertRaisesRegex(ValueError,'RESOURCE'):e.extract(*self.args)
  self.assertNotIn('physical',self.calls)
 def test_dispatch_closed(self):
  with self.assertRaisesRegex(ValueError,'BLOCKED'):e.dispatch('x','y')
if __name__=='__main__':unittest.main()

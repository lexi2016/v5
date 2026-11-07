import unittest,tempfile,pathlib,json,io
from unittest.mock import patch
from urllib.parse import parse_qs,urlsplit
from transport import https_get,run_live,_isolated_engine,_url,NoRedirect
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.scope={'source_date':'2030-01-02','complete_structural_check':True,'rows':[{'code':'00001','security_type':'股票'},{'code':'00002','security_type':'股票'}]};self.codes=['00001','00002'];self.now=[0];self.calls=[]
 def tearDown(self):self.tmp.cleanup()
 def fixture(self,u):
  c=parse_qs(urlsplit(u).query)['secid'][0][4:];self.calls.append(c);return json.dumps({'rc':0,'data':{'code':c,'market':116,'klines':['2030-01-02,10,11,12,9,100,1000,0,0,0,0']}}).encode()
 def engine(self,**kw):return _isolated_engine(self.root,self.scope,'2030-01-02',self.codes,mock_transport=kw.get('transport',self.fixture),check_gates=kw.get('gates',lambda:None),clock=lambda:self.now[0],sleep=lambda t:self.now.__setitem__(0,self.now[0]+t))
 def test_complete_resume(self):
  x=self.engine();self.assertEqual(len(x['completed']),2);self.assertEqual(self.now[0],1);self.engine();self.assertEqual(len(self.calls),2)
 def test_failure_resume_persisted_throttle(self):
  def fail(u):raise TimeoutError('mock')
  x=self.engine(transport=fail);self.assertEqual(x['status'],'STOPPED_UNKNOWN');x=self.engine();self.assertEqual(len(x['completed']),2);self.assertEqual(self.now[0],2);self.assertEqual(len(x['attempts']),3)
 def test_gate_no_request(self):
  def fail():raise ValueError('RESOURCE_UNKNOWN')
  with self.assertRaises(ValueError):self.engine(gates=fail)
  self.assertFalse(self.calls)
 def test_active_lock(self):
  (self.root/'test.lock').write_text('other')
  with self.assertRaises(FileExistsError):self.engine()
  self.assertEqual((self.root/'test.lock').read_text(),'other')
 def test_changed_identity(self):
  self.engine();self.codes.reverse()
  with self.assertRaises(ValueError):self.engine()
 def test_corrupt_checkpoint(self):
  self.engine();p=self.root/'checkpoint.json';x=json.loads(p.read_text());x['completed']['00001']['raw_hex']='00';p.write_text(json.dumps(x))
  with self.assertRaises(ValueError):self.engine()
 def test_atomic_failure_retains_old(self):
  self.engine();before=(self.root/'checkpoint.json').read_bytes()
  with patch('transport.os.replace',side_effect=OSError('mock')):
   with self.assertRaises(OSError):self.engine()
  self.assertEqual((self.root/'checkpoint.json').read_bytes(),before)
 def test_public_blocked(self):self.assertEqual(run_live('forged',approved=True)['network_requests'],0)
 def test_response_size(self):
  self.assertEqual(self.engine(transport=lambda u:b'x'*131073)['status'],'STOPPED_UNKNOWN')
 def test_https_mock(self):
  class Response(io.BytesIO):status=200
  class Opener:
   def open(self,req,timeout):self.timeout=timeout;return Response(b'{}')
  o=Opener()
  with patch('transport.urllib.request.build_opener',return_value=o):self.assertEqual(https_get(_url('00001','2030-01-02')),b'{}');self.assertEqual(o.timeout,15)
 def test_https_size(self):
  class Response(io.BytesIO):status=200
  class Opener:
   def open(self,*a,**k):return Response(b'x'*11)
  with patch('transport.urllib.request.build_opener',return_value=Opener()):
   with self.assertRaises(ValueError):https_get(_url('00001','2030-01-02'),max_bytes=10)
 def test_destination_redirect(self):
  with self.assertRaises(ValueError):https_get('http://push2his.eastmoney.com/api/qt/stock/kline/get')
  with self.assertRaises(ValueError):NoRedirect().redirect_request(None)
 def test_five_large_valid_responses_resume(self):
  self.codes=['00001','00002','00003','00004','00005'];self.scope['rows']=[{'code':c,'security_type':'股票'} for c in self.codes]
  def large(u):
   j=json.loads(self.fixture(u));j['padding']='x'*110000;return json.dumps(j).encode()
  first=self.engine(transport=large);self.assertEqual(len(first['completed']),5)
  self.assertGreater((self.root/'checkpoint.json').stat().st_size,1048576)
  resumed=self.engine(transport=large);self.assertEqual(len(resumed['completed']),5);self.assertEqual(len(self.calls),5)
 def test_oversize_write_preserves_old_checkpoint(self):
  from transport import _write,CHECKPOINT_MAX_BYTES
  self.engine();old=(self.root/'checkpoint.json').read_bytes()
  with self.assertRaisesRegex(ValueError,'BEFORE_WRITE'):_write(self.root,{'oversize':'x'*CHECKPOINT_MAX_BYTES})
  self.assertEqual((self.root/'checkpoint.json').read_bytes(),old)
 def test_failed_checkpoint_flags_cannot_admit(self):
  def fail(u):raise TimeoutError('mock')
  x=self.engine(transport=fail);self.assertIs(x['production_allowed'],False);self.assertIs(x['natural_verified'],False)
  p=self.root/'checkpoint.json';x=json.loads(p.read_text());x.update(production_allowed=True,natural_verified=True);p.write_text(json.dumps(x))
  with self.assertRaisesRegex(ValueError,'BOUNDARY_CORRUPT'):self.engine(transport=fail)
if __name__=='__main__':unittest.main()

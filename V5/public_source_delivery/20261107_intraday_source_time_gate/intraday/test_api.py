import json,threading,unittest,urllib.request,urllib.error
from observation_api import create_server
import observation_api
from unittest.mock import patch
from synthetic_fixture import install
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.bindings=install();cls.bindings.__enter__();cls.addClassCleanup(cls.bindings.__exit__,None,None,None)
  cls.server=create_server();cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.url='http://127.0.0.1:'+str(cls.server.server_port)
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.thread.join();cls.server.server_close()
 def request(self,path,method='GET',headers=None):
  try:r=urllib.request.urlopen(urllib.request.Request(self.url+path,method=method,headers=headers or {}));return r.status,r.read()
  except urllib.error.HTTPError as e:return e.code,e.read()
 def test_history(self):
  status,raw=self.request('/observations/history/2000-01-02');d=json.loads(raw);self.assertEqual(status,200);self.assertEqual(len(d['latest']['rows']),2);self.assertEqual(d['latest']['analysis_admission'],'NOT_GRANTED')
 def test_current_blocked(self):
  status,raw=self.request('/observations/current');self.assertEqual(status,409);self.assertEqual(json.loads(raw)['status'],'BLOCKED_CURRENT_BINDING_UNKNOWN')
 def test_no_other_date(self):self.assertEqual(self.request('/observations/history/2026-11-06')[0],404)
 def test_no_post(self):self.assertEqual(self.request('/observations/current','POST')[0],405)
 def test_no_query(self):self.assertEqual(self.request('/observations/history/2000-01-02?current=true')[0],404)
 def test_host_rebinding(self):self.assertEqual(self.request('/status',headers={'Host':'evil.example'})[0],403)
 def test_cross_origin(self):self.assertEqual(self.request('/status',headers={'Origin':'https://evil.example'})[0],403)
 def test_status_not_running_collector(self):
  status,raw=self.request('/status');self.assertEqual(status,200);self.assertFalse(json.loads(raw)['collector_running'])
if __name__=='__main__':unittest.main()

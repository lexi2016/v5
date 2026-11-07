import json,socket,subprocess,sys,time,unittest
from pathlib import Path
class LifetimeTests(unittest.TestCase):
 def test_slow_header_cannot_outlive_total_lifetime(self):
  p=subprocess.Popen([sys.executable,str(Path(__file__).parent/'synthetic_cli.py'),'--serve-seconds','1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  self.addCleanup(lambda:p.kill() if p.poll() is None else None)
  info=json.loads(p.stdout.readline());port=int(info['url'].rsplit(':',1)[1]);start=time.monotonic();s=socket.create_connection(('127.0.0.1',port));self.addCleanup(s.close);s.sendall(b'GET /status HTTP/1.1\r\nHost: 127.0.0.1:')
  p.wait(timeout=1.7);self.assertEqual(p.returncode,0);self.assertLess(time.monotonic()-start,1.7)
 def test_idle_connection_cannot_outlive_total_lifetime(self):
  p=subprocess.Popen([sys.executable,str(Path(__file__).parent/'synthetic_cli.py'),'--serve-seconds','1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  self.addCleanup(lambda:p.kill() if p.poll() is None else None)
  info=json.loads(p.stdout.readline());port=int(info['url'].rsplit(':',1)[1]);s=socket.create_connection(('127.0.0.1',port));self.addCleanup(s.close)
  p.wait(timeout=1.7);self.assertEqual(p.returncode,0)
 def test_trickled_header_cannot_reset_absolute_deadline(self):
  import threading
  p=subprocess.Popen([sys.executable,str(Path(__file__).parent/'synthetic_cli.py'),'--serve-seconds','1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  self.addCleanup(lambda:p.kill() if p.poll() is None else None)
  info=json.loads(p.stdout.readline());port=int(info['url'].rsplit(':',1)[1]);s=socket.create_connection(('127.0.0.1',port));self.addCleanup(s.close);s.sendall(b'GET /status HTTP/1.1\r\nX-Slow: ');stop=threading.Event()
  def drip():
   while not stop.wait(0.08):
    try:s.sendall(b'x')
    except OSError:return
  t=threading.Thread(target=drip);t.start()
  try:p.wait(timeout=1.7);self.assertEqual(p.returncode,0)
  finally:stop.set();t.join()
if __name__=='__main__':unittest.main()

"""Real bounded receipt faults. No production budget/clock changes."""
import concurrent.futures,json,multiprocessing,os,struct,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from test_m18_offline_pages import fixture
from v5_shadow import m18_offline_v2 as m
from v5_shadow import m18_offline_v2_process as p

def partial_worker(request,connection):
 kind=Path(request['output_root']).name
 raw={'header':b'\0','body':struct.pack('!I',100)+b'{}','footer':struct.pack('!I',2)+b'{}'}[kind]
 os.write(connection.fileno(),raw);time.sleep(95)
def empty_worker(request,connection):connection.close()

class ReceiptTests(unittest.TestCase):
 def setUp(self):self.assertTrue(hasattr(p,'receive_receipt'),'M18_BOUNDED_RECEIPT_MISSING')
 def receive(self,raw,close=True):
  rd,wr=os.pipe()
  try:
   os.write(wr,raw)
   if close:os.close(wr);wr=None
   return p.receive_receipt(rd,time.monotonic()+.05)
  finally:
   os.close(rd)
   if wr is not None:os.close(wr)
 def test_partial_eof_and_deadlines(self):
  for raw in [b'',b'\0',struct.pack('!I',20)+b'{}',struct.pack('!I',2)+b'{}']:
   with self.subTest(raw=raw),self.assertRaisesRegex(m.ContractError,'RECEIPT_(EOF|TRUNCATED)'):self.receive(raw)
   start=time.monotonic()
   with self.subTest(timeout=raw),self.assertRaisesRegex(m.ContractError,'WALL_SECONDS'):self.receive(raw,False)
   self.assertLess(time.monotonic()-start,.5)
 def test_length_and_io_errors(self):
  for n in [0,16385,2**32-1]:
   with self.subTest(n=n),self.assertRaisesRegex(m.ContractError,'RECEIPT_LENGTH'):self.receive(struct.pack('!I',n),False)
  with self.assertRaisesRegex(m.ContractError,'RECEIPT_IO'):p.receive_receipt(-1,time.monotonic()+1)
 def test_schema_trailing_and_nonfinite_footer(self):
  for body,tail in [(b'{"x":1,"x":2}',b''),(b'[]',b''),(b'{}',b'x')]:
   with self.subTest(body=body),self.assertRaises(m.ContractError):self.receive(struct.pack('!I',len(body))+body+p.FOOTER.pack(1,0.,0.)+tail)
  body=p.encode_receipt(p.compact_receipt(dict(pid=os.getpid(),status='REJECTED',error='M18_V2_WORKER_FAILED')))
  for cpu in [float('nan'),float('inf'),-1.]:
   with self.subTest(cpu=cpu),self.assertRaises(m.ContractError):self.receive(struct.pack('!I',len(body))+body+p.FOOTER.pack(1,cpu,0.))
 def test_short_summary_and_send_resource_boundary(self):
  value=dict(pid=os.getpid(),status='REJECTED',error='M18_V2_WORKER_FAILED',usage=dict(scan_nodes=1,scan_bytes=1),stages=[None]*10000)
  compact=p.compact_receipt(value);self.assertEqual(compact['stage_count'],10000);self.assertNotIn('stages',compact)
  for key,val in [('private_body','x'),('error','x'*100000),('pid',True)]:
   with self.subTest(key=key),self.assertRaises(m.ContractError):p.compact_receipt(dict(value,**{key:val}))
  rd,wr=multiprocessing.get_context('spawn').Pipe(False);writer=p.ReceiptSender(wr);original=p.encode_receipt
  def slow(v):
   start=time.process_time()
   while time.process_time()-start<.08:sum(i*i for i in range(1000))
   return original(v)
  start=time.process_time()
  with patch.object(p,'encode_receipt',slow):writer.send(value)
  writer.close();result=p.receive_receipt(rd.fileno(),time.monotonic()+1);rd.close()
  self.assertGreaterEqual(result['usage']['cpu_seconds'],start+.075)
 def test_late_resource_rejection_keeps_error_not_success_fields(self):
  value=dict(pid=os.getpid(),status='REJECTED',error='M18_V2_RESOURCE_CPU_SECONDS',manifest_sha256='a'*64,objects=4,generation_bytes=10)
  try:compact=p.compact_receipt(value)
  except m.ContractError as error:self.fail('Late rejection must preserve its error: '+str(error))
  self.assertEqual(compact['error'],value['error']);self.assertNotIn('manifest_sha256',compact)
 def test_eof_worker_reaped_no_accepted(self):
  _,_,identity=fixture()
  with tempfile.TemporaryDirectory() as td,patch.object(p,'_worker',empty_worker):
   root=Path(td);result=p.run(dict(action='build',response_path=str(root/'r'),saved_path=str(root/'s'),output_root=str(root/'out'),identity=identity,profile_sha256=m.PROFILE_SHA256))
   self.assertEqual(result['error'],'M18_V2_RECEIPT_EOF');self.assertTrue(result['worker_reaped']);self.assertFalse((root/'out/ACCEPTED.json').exists())

class ReceiptDeadlineTests(unittest.TestCase):
 def test_actual_90s_partial_frames_terminate_and_reap(self):
  _,_,identity=fixture()
  with tempfile.TemporaryDirectory() as td,patch.object(p,'_worker',partial_worker):
   root=Path(td)
   def run(kind):return p.run(dict(action='build',response_path=str(root/'r'),saved_path=str(root/'s'),output_root=str(root/kind),identity=identity,profile_sha256=m.PROFILE_SHA256))
   with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=dict(zip(['header','body','footer'],pool.map(run,['header','body','footer'])))
   for kind,result in results.items():
    with self.subTest(kind=kind):
     self.assertEqual(result['error'],'M18_V2_RESOURCE_WALL_SECONDS');self.assertTrue(result['worker_reaped']);self.assertGreaterEqual(result['supervisor_wall_seconds'],90);self.assertLess(result['supervisor_wall_seconds'],94);self.assertFalse((root/kind/'ACCEPTED.json').exists())
   if os.environ.get('M18_RECEIPT_DEADLINE_EVIDENCE'):Path(os.environ['M18_RECEIPT_DEADLINE_EVIDENCE']).write_text(json.dumps(results,indent=2)+'\n')

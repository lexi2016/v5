"""New isolated native lifetime probe. NOT existing E1 no-native admission.
Parent original E1 lock/resource primitives are reused unchanged; child obligations
and completion checks below are separately reviewed. No production/data interface.
"""
import hashlib,json,subprocess,sys,time,types,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent

def load(path,sha,name):
 raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('FIXED_SOURCE_PIN')
 m=types.ModuleType(name);m.__file__=str(path);sys.modules[name]=m;exec(compile(raw,str(path),'exec'),m.__dict__);return m

def run():
 pins=json.loads((HERE/'PINS.json').read_bytes())
 w=load(HERE/'worker.py',pins['worker_sha256'],'_native_probe_guard')
 # Before creating E1 session, opening locks or starting any native/DB/process.
 resources=w.gate()
 e=load(ROOT/'handoff/owner_e1_dependency_correction_20261107/caller_lock.py','c360c96ce652f705343347833688a88a46c79d5ccea0fcb83fc780fbc8919cc0','_native_probe_e1')
 base=e.create_test_session();r=e._anchor.slot
 rec=types.SimpleNamespace(phase='REGISTERED',process=None,pid=None,spawn_started=False,wait_returned=False,pipes_closed=False,error=None,cleanup_errors=[],output=None)
 r.native_subprocess_probe=rec;operation=None
 try:
  base.enter();operation=e._begin(r,('VERIFIED_ACTIVE',));e._observe(r);w.gate()
  out=r.root/'native_probe';out.mkdir()
  if hashlib.sha256((HERE/'worker.py').read_bytes()).hexdigest()!=pins['worker_sha256']:raise ValueError('WORKER_CHANGED_BEFORE_SPAWN')
  rec.phase='SPAWN_STARTED';rec.spawn_started=True
  rec.process=subprocess.Popen([sys.executable,'-I','-B',str(HERE/'worker.py'),str(out)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  rec.pid=rec.process.pid;rec.phase='CHILD_OWNED';deadline=time.monotonic()+30
  while True:
   e._observe(r);w.gate()
   if time.monotonic()>deadline:raise TimeoutError('NATIVE_PROBE_30_SECONDS')
   try:
    stdout,stderr=rec.process.communicate(timeout=.05);rec.wait_returned=True;break
   except subprocess.TimeoutExpired:continue
  if len(stdout)>8192 or len(stderr)>8192:raise ValueError('CHILD_OUTPUT_CAP')
  if rec.process.returncode!=0:raise RuntimeError('CHILD_FAILED:'+stderr.decode(errors='replace')[:2048])
  if hashlib.sha256((HERE/'worker.py').read_bytes()).hexdigest()!=pins['worker_sha256']:raise ValueError('WORKER_CHANGED_AFTER_RUN')
  doc=json.loads(stdout);rec.output=doc
  if doc.get('status')!='REAL_NATIVE_SYNTHETIC16_ROUNDTRIP' or doc.get('row_count')!=16 or doc.get('sum')!=120 or doc.get('connection_close_returned')is not True:raise ValueError('CHILD_RESULT_CONTRACT')
  for stream in (rec.process.stdout,rec.process.stderr):
   if not stream.closed:stream.close()
  rec.pipes_closed=True;e._observe(r);w.gate();rec.phase='CHILD_COMPLETED_VERIFIED'
 except BaseException as error:
  rec.error=error;rec.phase='UNKNOWN';e._retain(r,error,'RETAINED_UNKNOWN')
  if rec.process is not None:
   try:
    if rec.process.poll()is None:rec.process.kill()
    rec.process.wait(timeout=5);rec.wait_returned=True
    for stream in (rec.process.stdout,rec.process.stderr):
     if stream is not None and not stream.closed:stream.close()
    rec.pipes_closed=True
   except BaseException as cleanup:rec.cleanup_errors.append(cleanup)
  # Even known child termination does not turn an aborted operation into success.
  # Original pair and parent objects remain rooted; never finish/release here.
  raise
 finally:
  if operation is not None:e._end(r,operation)
 # Release is allowed only after actual child wait, closed pipes, valid output.
 if rec.phase!='CHILD_COMPLETED_VERIFIED' or not rec.wait_returned or not rec.pipes_closed:raise ValueError('NO_RELEASE_EVIDENCE')
 result=base.finish_test_only();rec.phase='TEST_COMPLETE_ORIGINAL_LOCKS_CLOSED'
 return dict(status=rec.phase,e1_finish=result.kind,resources=resources,child_pid=rec.pid,child_wait_returned=rec.wait_returned,pipes_closed=rec.pipes_closed,output=rec.output,root=str(r.root),business_admission=False,stock_computation=False)
if __name__=='__main__':
 try:result=run()
 except BaseException as e:result=dict(status='BLOCKED_OR_FAILED_NOT_COMPLETED',error_type=type(e).__name__,reason=str(e));print(json.dumps(result));raise SystemExit(2)
 print(json.dumps(result))

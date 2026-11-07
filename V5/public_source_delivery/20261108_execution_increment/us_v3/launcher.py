"""Fixed Nov9 launcher integration, offline-only until external admission.

Public execution cannot write state, lock live files or request HTTP while the
activation/trigger registry is empty. Private seams are isolated test targets.
"""
import argparse,contextlib,hashlib,json,math,os,re,signal,stat,sys,time,types
from datetime import datetime,timezone
from pathlib import Path
import urllib.request
HERE=Path(__file__).absolute().parent
ROOT=HERE.parents[1]
STATE=HERE/'runtime'
TARGET=None  # Bound only from the reviewed capture-run registry.
PINSET_SHA='c2c0a6aaf4965429a3117e8d103d0a5af81b3b132f32a6ebabc94368f5b5296d'
ACTIVATIONS=()
TRIGGER_BINDINGS=()
CODE_PIN=globals().get('__verified_source_pin__')
MODULE_PATHS={
 'session_plan':'handoff/us_schedule_preflight_v3_20261107/session_plan.py',
 'resource_gate':'handoff/us_schedule_preflight_v3_20261107/resource_gate.py',
 'capture_core':'handoff/us_raw_capture_candidate_v4r1_20261107/capture_core.py',
 'shared_locks':'handoff/us_raw_capture_candidate_v4r1_20261107/shared_locks.py'}
FLAGS=dict.fromkeys(('execution_admitted','source_admission','formal_reader_admission','research_consumption_allowed','training_allowed','natural_trigger_verified','orders_sent'),False)

def need(ok,why):
 if not ok:raise ValueError(why)
def now():return datetime.now(timezone.utc)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canon(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def unique(pairs):
 result={}
 for k,v in pairs:need(k not in result,'DUPLICATE_JSON_KEY');result[k]=v
 return result
def strict(raw):return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
def aware(value):
 d=datetime.fromisoformat(value);need(d.tzinfo is not None and d.utcoffset() is not None,'AWARE_TIME');return d.astimezone(timezone.utc)

def read(relative,limit=1048576):
 p=Path(relative);need(not p.is_absolute() and '..' not in p.parts and p.parts,'PATH_SCOPE');fds=[]
 try:
  fd=os.open(ROOT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(fd)
  for part in p.parts[:-1]:fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(fd)
  f=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);fds.append(f);s=os.fstat(f)
  need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and 0<s.st_size<=limit,'READ_TYPE_SIZE')
  raw=b''
  while len(raw)<=s.st_size:
   b=os.read(f,min(65536,s.st_size+1-len(raw)))
   if not b:break
   raw+=b
  ident=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,x.st_ctime_ns)
  need(len(raw)==s.st_size and ident(s)==ident(os.fstat(f))==ident(os.stat(p.name,dir_fd=fd,follow_symlinks=False)),'READ_CHANGED')
  return raw
 finally:
  for fd in reversed(fds):os.close(fd)

def checked(pin):
 need(type(pin) is dict and set(pin)=={'path','bytes','sha256'} and type(pin['bytes']) is int,'PIN_SHAPE')
 raw=read(pin['path']);need(len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],'PIN_CHANGED');return raw

def verify_dependencies():
 raw=read(str((HERE/'PINSET.json').relative_to(ROOT)));need(sha(raw)==PINSET_SHA,'PINSET_CHANGED')
 pins=strict(raw);need(pins['schema']=='US_LAUNCHER_V5_DEPENDENCY_PINS','PINSET_SCHEMA')
 blobs={}
 for pin in pins['refs']:
  need(pin['path'] not in blobs,'DUPLICATE_DEPENDENCY');blobs[pin['path']]=checked(pin)
 return pins,blobs

def load_bundle():
 pins,blobs=verify_dependencies();bundle={'pins':pins};previous={};created=[]
 try:
  for name,path in MODULE_PATHS.items():
   previous[name]=sys.modules.get(name);m=types.ModuleType(name);m.__file__=str(ROOT/path)
   # Execute the exact held-and-hashed bytes, never import/reopen a source path.
   sys.modules[name]=m;created.append(name);exec(compile(blobs[path],m.__file__,'exec'),m.__dict__);bundle[name]=m
 finally:
  for name in reversed(created):
   if previous[name] is None:sys.modules.pop(name,None)
   else:sys.modules[name]=previous[name]
 return bundle

def verify_launcher():
 need(CODE_PIN is not None,'NO_PINNED_LAUNCHER_BOOTSTRAP');checked(CODE_PIN);return CODE_PIN

def check_resources(bundle,start=False):
 g=bundle['resource_gate'];memory,disk=g.values()
 need(type(memory) is int and type(disk) is int and memory>=0 and disk>=0,'RESOURCE_VALUE_TYPE')
 need(memory>=(g.START_MEMORY if start else g.RUNTIME_MEMORY),'RESOURCE_MEMORY_FLOOR')
 need(disk>=(g.START_DISK if start else g.RUNTIME_DISK),'RESOURCE_DISK_FLOOR')
 return {'effective_memory_bytes':memory,'disk_free_bytes':disk}

def trigger_readback(payload,binding):
 """Strict readback join; binding must come from an external admitted registry."""
 need(type(binding) is dict and set(binding)=={'automation_id','run_id','scheduled_for','snapshot_ref'},'TRIGGER_BINDING_SHAPE')
 raw=checked(binding['snapshot_ref']);evidence=strict(raw)
 for _ in range(3):
  if type(evidence) is dict and 'automations' in evidence:break
  need(type(evidence) is dict and type(evidence.get('structuredContent')) is dict,'TRIGGER_READBACK_SHAPE');evidence=evidence['structuredContent']
 records=evidence.get('automations');need(type(records) is list,'TRIGGER_AUTOMATIONS')
 matches=[a for a in records if a.get('id')==binding['automation_id']];need(len(matches)==1,'TRIGGER_AUTOMATION_ID')
 task=matches[0];need(task.get('is_enabled') is True,'TRIGGER_DISABLED')
 run=(task.get('run_details') or {}).get('last_run');need(type(run) is dict,'TRIGGER_ACTUAL_RUN_MISSING')
 need(type(run.get('id')) is str and run['id']==binding['run_id'] and bool(run['id']),'TRIGGER_RUN_ID')
 plan=load_bundle()['session_plan'].plan(TARGET)
 scheduled=aware(run['scheduled_for']);started=aware(run['started_at'])
 need(scheduled==aware(binding['scheduled_for'])==aware(plan['start_ny']),'TRIGGER_SCHEDULE')
 need(scheduled<=started<aware(plan['end_ny']),'TRIGGER_START_WINDOW')
 need(run.get('recorded_status') in ('in_progress','completed'),'TRIGGER_RUN_STATE')
 expected={'automation_id':binding['automation_id'],'run_id':binding['run_id'],'scheduled_for':binding['scheduled_for'],'target_session_date':TARGET}
 need(type(payload) is dict and payload==expected,'TRIGGER_PAYLOAD_BINDING')
 return {**expected,'actual_started_at':run['started_at'],'snapshot_ref':binding['snapshot_ref'],'readback_bound':True,'natural_trigger_verified':False}

def trigger_clock(trigger):
 """A capture clock read may never predate the externally bound trigger."""
 instant=now();need(instant.tzinfo is not None and instant.utcoffset() is not None,'RUNTIME_CLOCK_AWARE')
 need(aware(trigger['actual_started_at'])<=instant,'TRIGGER_AFTER_OBSERVATION')
 return instant

def trigger_timing(trigger,claim,samples,plan,terminal):
 """Join the pinned capture claim and observed resource trace, not replay time."""
 started=aware(trigger['actual_started_at'])
 need(started<=aware(claim['started_at_utc']),'TRIGGER_AFTER_CLAIM')
 need(started<=aware(samples[0]['at_utc']),'TRIGGER_AFTER_FIRST_RESOURCE')
 start,end=aware(plan['start_ny']),aware(plan['end_ny']);finished=aware(terminal['finished_at_utc'])
 need(aware(samples[0]['at_utc'])<=aware(claim['started_at_utc']),'RESOURCE_FIRST_AFTER_CLAIM')
 for sample in samples:
  instant=aware(sample['at_utc'])
  need(started<=instant,'TRIGGER_AFTER_RESOURCE')
  if sample['phase']=='capture':
   need(start<=instant<end,'RESOURCE_CAPTURE_WINDOW')
   need(instant<=finished,'RESOURCE_CAPTURE_AFTER_TERMINAL')
  else:need(finished<=instant,'RESOURCE_FINAL_BEFORE_TERMINAL')

def verify_locks(bundle,receipts):
 core=bundle['capture_core'];paths=bundle['shared_locks'].LOCK_PATHS
 need([r['path'] for r in receipts]==list(paths),'LOCK_RECEIPT_SCOPE')
 for r in receipts:
  p=ROOT/r['path']
  with core.directory(p.parent) as fd:
   f=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
   try:
    s=os.fstat(f);need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and (s.st_dev,s.st_ino)==(r['device'],r['inode']),'HELD_LOCK_IDENTITY_CHANGED');core.anchor(fd,p.parent)
   finally:os.close(f)

class RuntimeGuard:
 def __init__(self,bundle,plan,locks,trigger=None):self.trigger=trigger;self.bundle,self.plan,self.locks=bundle,plan,locks;self.failure=None;self.samples=[];self.started_monotonic=time.monotonic()
 def check(self,window=True):
  if self.failure is not None:raise RuntimeError('LATCHED_RUNTIME_FAILURE: '+self.failure)
  try:
   need(not self.samples or self.samples[-1]['phase']=='capture','RESOURCE_CHECK_AFTER_FINAL')
   need(window or bool(self.samples),'RESOURCE_FINAL_WITHOUT_CAPTURE')
   verify_launcher();verify_dependencies();verify_locks(self.bundle,self.locks);x=check_resources(self.bundle)
   instant=trigger_clock(self.trigger) if self.trigger is not None else now();need(instant.tzinfo is not None and instant.utcoffset() is not None,'RUNTIME_CLOCK_AWARE')
   if window:need(aware(self.plan['start_ny'])<=instant<aware(self.plan['end_ny']),'RUNTIME_WINDOW_EXPIRED')
   need(not self.samples or aware(self.samples[-1]['at_utc'])<=instant,'RESOURCE_WALL_CLOCK_REVERSED')
   need(len(self.samples)<2048,'RESOURCE_SAMPLE_CAP')
   self.samples.append({'phase':'capture' if window else 'post_capture','at_utc':instant.isoformat(),'elapsed_monotonic_seconds':time.monotonic()-self.started_monotonic,**x});return x
  except BaseException as e:self.failure=type(e).__name__+': '+str(e);raise

def resource_trace(samples):
 need(type(samples) is list and 2<=len(samples)<=2048,'RESOURCE_TRACE_COUNT')
 last=0.0;gaps=[];last_wall=None
 for i,x in enumerate(samples):
  need(type(x) is dict and set(x)=={'phase','at_utc','elapsed_monotonic_seconds','effective_memory_bytes','disk_free_bytes'},'RESOURCE_TRACE_SHAPE')
  need(x['phase']==('post_capture' if i==len(samples)-1 else 'capture'),'RESOURCE_TRACE_PHASE')
  wall=aware(x['at_utc']);need(last_wall is None or last_wall<=wall,'RESOURCE_WALL_CLOCK_REVERSED');last_wall=wall
  value=x['elapsed_monotonic_seconds'];need(type(value) in (int,float) and math.isfinite(value) and value>=last,'RESOURCE_TRACE_TIME')
  need(type(x['effective_memory_bytes']) is int and type(x['disk_free_bytes']) is int,'RESOURCE_TRACE_VALUE_TYPE')
  need(x['effective_memory_bytes']>=2952790016 and x['disk_free_bytes']>=2147483648,'RESOURCE_TRACE_FLOOR')
  gaps.append(value-last);last=value
 return {'samples':samples,'sample_count':len(samples),'min_effective_memory_bytes':min(x['effective_memory_bytes'] for x in samples),'min_disk_free_bytes':min(x['disk_free_bytes'] for x in samples),'max_observed_sample_gap_seconds':max(gaps),'nominal_request_sampling_interval_seconds':.25,'absolute_peak_or_continuous_bound_proven':False}

def guarded_http(bundle,request,timeout,guard):
 """Single timer owns both request deadline and bounded runtime checks."""
 core=bundle['capture_core'];need(type(timeout) in (int,float) and not isinstance(timeout,bool) and 0<timeout<=20,'TRANSPORT_TIMEOUT')
 key=request.get('provider_key');need(type(key) is str and re.fullmatch(r'us[A-Z][A-Z0-9.-]{0,9}\.(?:N|OQ|AM)',key),'TRANSPORT_IDENTITY')
 need(request['url']==f'https://web.ifzq.gtimg.cn/appstock/app/usfqkline/get?param={key},day,,,5,qfq','TRANSPORT_URL')
 need(signal.getitimer(signal.ITIMER_REAL)==(0.0,0.0),'EXISTING_TIMER')
 guard.check();end=aware(request['deadline_utc']);start=aware(request['window_start_utc']);instant=now();need(start<=instant<end,'TRANSPORT_WINDOW')
 duration=min(timeout,(end-instant).total_seconds());deadline=time.monotonic()+duration;old=signal.getsignal(signal.SIGALRM);samples=[]
 def tick(*args):
  remaining=deadline-time.monotonic()
  if remaining<=0:raise core.DeadlineExceeded('REQUEST_DEADLINE')
  guard.check();samples.append(time.monotonic());remaining=deadline-time.monotonic()
  if remaining<=0:raise core.DeadlineExceeded('REQUEST_DEADLINE')
  signal.setitimer(signal.ITIMER_REAL,min(.25,remaining))
 signal.signal(signal.SIGALRM,tick);signal.setitimer(signal.ITIMER_REAL,min(.25,duration))
 try:
  opener=urllib.request.build_opener(core.NoRedirect());req=urllib.request.Request(request['url'],headers={'User-Agent':'PrivateResearchCapture/1.0'})
  guard.check();need(start<=now()<end,'TRANSPORT_WINDOW_BEFORE_OPEN')
  with opener.open(req,timeout=duration) as response:
   body=response.read(core.RESPONSE_CAP+1);need(len(body)<=core.RESPONSE_CAP,'RESPONSE_CAP');guard.check()
   return {'http_status':response.status,'http_date':response.headers.get('Date'),'body':body}
 finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)

def _runtime_dirs(bundle):
 core=bundle['capture_core']
 with core.directory(HERE) as fd:
  try:os.mkdir('runtime',0o700,dir_fd=fd);os.fsync(fd)
  except FileExistsError:pass
 with core.directory(STATE) as fd:
  for name in ('captures','receipts'):
   try:os.mkdir(name,0o700,dir_fd=fd);os.fsync(fd)
   except FileExistsError:pass
 return STATE/'captures',STATE/'receipts'

def replay(bundle,plan):
 """Read-only reconciliation; no natural-window check, locks, writes or HTTP."""
 core=bundle['capture_core'];run=STATE/'captures'/plan['dedup_identity'];outer=STATE/'receipts'
 try:
  with core.directory(run) as fd:
   raw=core.read_at(fd,'TERMINAL.json');terminal=strict(raw);core.terminal_replay(fd,terminal,plan,33);claim=strict(core.verify_at(fd,terminal['artifact_refs'][0]))
 except FileNotFoundError:
  try:
   with core.directory(run):status='UNKNOWN_EXISTING_ATTEMPT_MISSING_TERMINAL'
  except FileNotFoundError:status='NOT_RUN_NO_ATTEMPT_DIRECTORY'
  return {'status':status,'network_requests':0,**FLAGS}
 pin={'name':'TERMINAL.json','bytes':len(raw),'sha256':sha(raw)}
 try:
  with core.directory(outer) as fd:receipt=strict(core.read_at(fd,plan['dedup_identity']+'.json'))
 except FileNotFoundError:return {'status':'UNKNOWN_TERMINAL_WITHOUT_OUTER_RECEIPT','terminal_pin':pin,'network_requests':0,**FLAGS}
 need(set(receipt)=={'schema','plan_sha256','terminal_pin','trigger','pinset_sha256','launcher_ref','start_resource','runtime_resource_trace','locks_released','outcome','flags'},'OUTER_RECEIPT_SHAPE')
 need(receipt['schema']=='US_FIXED_LAUNCH_RECEIPT_V5R2' and receipt['plan_sha256']==sha(canon(plan)) and receipt['terminal_pin']==pin and receipt['pinset_sha256']==PINSET_SHA,'OUTER_RECEIPT_BINDING')
 need(receipt['flags']==FLAGS and all(v is False for v in receipt['flags'].values()) and receipt['locks_released'] is True,'OUTER_RECEIPT_FLAGS')
 need(receipt['launcher_ref']==verify_launcher(),'OUTER_LAUNCHER_IDENTITY')
 start_resource=receipt['start_resource'];need(type(start_resource) is dict and set(start_resource)=={'effective_memory_bytes','disk_free_bytes'} and all(type(v) is int for v in start_resource.values()),'OUTER_START_RESOURCE')
 need(start_resource['effective_memory_bytes']>=3070230528 and start_resource['disk_free_bytes']>=2189426688,'OUTER_START_RESOURCE_FLOOR')
 need(resource_trace(receipt['runtime_resource_trace']['samples'])==receipt['runtime_resource_trace'],'OUTER_RESOURCE_TRACE')
 trigger=receipt['trigger'];need(type(trigger) is dict and set(trigger)=={'automation_id','run_id','scheduled_for','target_session_date','actual_started_at','snapshot_ref','readback_bound','natural_trigger_verified'},'OUTER_TRIGGER_SHAPE')
 bound={k:trigger[k] for k in ('automation_id','run_id','scheduled_for','snapshot_ref')};payload={k:trigger[k] for k in ('automation_id','run_id','scheduled_for','target_session_date')}
 need(trigger_readback(payload,bound)==trigger and trigger['readback_bound'] is True and trigger['natural_trigger_verified'] is False,'OUTER_TRIGGER_BINDING')
 trigger_timing(trigger,claim,receipt['runtime_resource_trace']['samples'],plan,terminal)
 need(receipt['outcome']=='CAPTURE_CANDIDATE_SEALED_NOT_INDEPENDENTLY_ADMITTED','OUTER_RECEIPT_OUTCOME')
 return {'status':'LOCAL_CLOSED_RECEIPTS_NOT_INDEPENDENTLY_ADMITTED','receipt':receipt,'network_requests':0,**FLAGS}

def _pipeline(bundle,plan,trigger_payload,binding):
 """Fixed-path integration. Called only by isolated tests in this release."""
 core=bundle['capture_core'];verify_launcher();verify_dependencies();need(plan==bundle['session_plan'].plan(TARGET),'FIXED_PLAN_BINDING');trigger=trigger_readback(trigger_payload,binding);trigger_clock(trigger);start_resource=check_resources(bundle,start=True)
 # Any prior state is reconciled, never retried or overwritten by the launcher.
 try:
  with core.directory(STATE/'captures'/plan['dedup_identity']):return replay(bundle,plan)
 except FileNotFoundError:pass
 captures,receipts=_runtime_dirs(bundle);guard=None;terminal=None
 try:
  with bundle['shared_locks'].acquire_existing(ROOT) as held:
   guard=RuntimeGuard(bundle,plan,held,trigger);guard.check()
   terminal=core.collect(captures,plan,fetch=lambda req,timeout:guarded_http(bundle,req,timeout,guard),clock=lambda:trigger_clock(trigger),resource_check=guard.check,expected_count=33)
   guard.check(window=False);verify_locks(bundle,held)
   with core.directory(captures/plan['dedup_identity']) as fd:
    raw=core.read_at(fd,'TERMINAL.json');sealed=strict(raw);core.terminal_replay(fd,sealed,plan,33);claim=strict(core.verify_at(fd,sealed['artifact_refs'][0]));resource_trace(guard.samples);trigger_timing(trigger,claim,guard.samples,plan,sealed);pin={'name':'TERMINAL.json','bytes':len(raw),'sha256':sha(raw)}
  # No positive outer receipt is committed until the shared-lock context exits.
  verify_launcher();verify_dependencies()
  receipt={'schema':'US_FIXED_LAUNCH_RECEIPT_V5R2','plan_sha256':sha(canon(plan)),'terminal_pin':pin,'trigger':trigger,'pinset_sha256':PINSET_SHA,'launcher_ref':CODE_PIN,'start_resource':start_resource,'runtime_resource_trace':resource_trace(guard.samples),'locks_released':True,'outcome':'CAPTURE_CANDIDATE_SEALED_NOT_INDEPENDENTLY_ADMITTED','flags':FLAGS}
  with core.directory(receipts) as fd:core.save_at(fd,plan['dedup_identity']+'.json',canon(receipt))
  return {'status':'LOCAL_CLOSED_RECEIPTS_NOT_INDEPENDENTLY_ADMITTED','receipt':receipt,'resource_samples':len(guard.samples),'source_admission':False,'natural_trigger_verified':False}
 except BaseException as e:
  return {'status':'UNKNOWN_OR_BLOCKED_NO_POSITIVE_OUTER_RECEIPT','error':type(e).__name__+': '+str(e),'guard_failure':guard.failure if guard else None,'terminal_may_exist':terminal is not None,'network_count':'UNKNOWN_UNLESS_RECONCILED','flags':FLAGS}

def preflight():
 bundle=load_bundle();plan=bundle['session_plan'].plan(TARGET);resource=bundle['resource_gate'].preflight()
 blockers=[]
 if not ACTIVATIONS:blockers.append('NO_EXTERNAL_EXECUTION_ADMISSION')
 if not TRIGGER_BINDINGS:blockers.append('NO_ACTUAL_AUTOMATION_TRIGGER_BINDING')
 if CODE_PIN is None:blockers.append('NO_PINNED_LAUNCHER_BOOTSTRAP')
 if resource.get('eligible') is not True:blockers.append('RESOURCE_EVIDENCE_UNAVAILABLE_OR_BELOW_FLOOR')
 return {'schema':'US_FIXED_LAUNCHER_PREFLIGHT_V5','observed_at_utc':now().isoformat(),'target_session_date':TARGET,'prior_session_date':plan['prior_session_date'],'request_count':len(plan['requests']),'start_ny':plan['start_ny'],'end_ny':plan['end_ny'],'dependency_pinset_sha256':PINSET_SHA,'resource':resource,'blockers':blockers,'network_requests':0,'actual_locks_acquired':0,'state_written':False,**FLAGS}

def execute():
 # Even a caller mutating a Python registry cannot turn this reviewed offline
 # release into a live one. Activation requires a separately reviewed entry.
 if TARGET is None:return {'status':'BLOCKED_NO_EXECUTION_ADMISSION','reason':'NO_REVIEWED_SESSION_BINDING','network_requests':0,**FLAGS}
 result=preflight();return {'status':'BLOCKED_NO_EXECUTION_ADMISSION',**result}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('operation',choices=('preflight','execute','reconcile'));args=parser.parse_args()
 if args.operation=='reconcile':
  b=load_bundle();result=replay(b,b['session_plan'].plan(TARGET))
 else:result=execute() if args.operation=='execute' else preflight()
 print(json.dumps(result,ensure_ascii=False,indent=2))

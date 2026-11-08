"""New isolated HK observation owner. No formula, ranking, order or M10 KPI changes.
Provider/lock/calendar/source approval supplied by reviewed code registry, never HTTP.
"""
import datetime as dt
import hashlib,json,os,re,tempfile
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Hong_Kong')
NODES={'hk-open','hk-continuous-close','hk-auction-final'}
def encode(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def stamp(s):
 t=dt.datetime.fromisoformat(s)
 if t.tzinfo is None:raise ValueError('TIMEZONE_REQUIRED')
 return t.astimezone(TZ)
@dataclass(frozen=True)
class Binding:
 node:str
 day:str
 scope:tuple
 source_reference:str
 source_review_sha256:str
 calendar_sha256:str
 scope_sha256:str
 code_version:str
 environment_id:str
 job_id:str
 output:Path
 calendar:object
 gate:object
 lock:object
 collect:object
 clock:object
 synthetic:bool=False
 # New reviewed event contract. A timestamp alone is never actual CAS evidence.
 cas_event_ref:object=None
 read_cas_event:object=None

def cas_event(b,x,now):
 pin=b.cas_event_ref
 if not isinstance(pin,dict) or not callable(b.read_cas_event):raise ValueError('ACTUAL_CAS_EVENT_BINDING_REQUIRED')
 if set(pin)!={'path','bytes','sha256'} or not isinstance(pin['path'],str) or not pin['path'] or type(pin['bytes'])is not int or not 0<pin['bytes']<=16384 or not isinstance(pin['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',pin['sha256']):raise ValueError('CAS_EVENT_REFERENCE')
 raw=b.read_cas_event(dict(pin)) # reviewed local reader, never a network collector
 if not isinstance(raw,bytes) or len(raw)!=pin['bytes'] or sha(raw)!=pin['sha256']:raise ValueError('CAS_EVENT_PIN_CHANGED')
 event=json.loads(raw)
 if event.get('schema')!='HK_CAS_TERMINATION_EVENT_V1' or not isinstance(event.get('event_id'),str) or not event['event_id'].strip():raise ValueError('CAS_EVENT_SCHEMA')
 expected={'day':b.day,'source_reference':b.source_reference,'scope_sha256':b.scope_sha256,
           'data_kind':'SYNTHETIC_TEST' if b.synthetic else 'RECORDED_INPUT'}
 if x is not None:expected['actual_cas_end']=x['actual_cas_end']
 if any(event.get(k)!=v for k,v in expected.items()):raise ValueError('CAS_EVENT_IDENTITY')
 close=stamp(event['continuous_close_at']);end=stamp(event['actual_cas_end']);available=stamp(event['available_at'])
 # This node's current contract is the regular 16:00 continuous close. An early
 # close requires a separately reviewed calendar contract, never a guessed event.
 if close.strftime('%Y%m%d')!=b.day or close.time().replace(tzinfo=None)!=dt.time(16):raise ValueError('CAS_CONTINUOUS_CLOSE_BINDING')
 observed=stamp(x['observed_at']) if x is not None else now
 if end.strftime('%Y%m%d')!=b.day or not close<end<=observed or not end<=available<=now:raise ValueError('CAS_EVENT_TIME_ORDER')
 return event

def hk09_times(day,started,observed,received,checked):
 import importlib.util
 path=None # original reviewed helper intentionally unbound
 if path is None:raise ValueError('HK09_WINDOW_DEPENDENCY_UNBOUND')
 if hashlib.sha256(path.read_bytes()).hexdigest()!='ec052a4105998a8611d7bb7b55d14768ac33b0a261c27065fd1e978a168c04a4':raise ValueError('HK09_WINDOW_CODE_CHANGED')
 spec=importlib.util.spec_from_file_location('hk09_window_verified',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module.inspect_window(day,started_at=started,observed_at=observed,received_at=received,checked_at=checked)

def validate(b,x,now,started=None):
 if set(x)!={'schema','node','day','scope','source_reference','observed_at','available_at','rows','actual_cas_end','data_kind'}:raise ValueError('SOURCE_FIELDS')
 if (x['schema'],x['node'],x['day'],x['scope'],x['source_reference'])!=('HK_OBSERVATION_V1',b.node,b.day,list(b.scope),b.source_reference):raise ValueError('SOURCE_IDENTITY')
 if x['data_kind']!=('SYNTHETIC_TEST' if b.synthetic else 'RECORDED_INPUT'):raise ValueError('SOURCE_KIND')
 observed=stamp(x['observed_at']);available=stamp(x['available_at']);day=dt.datetime.strptime(b.day,'%Y%m%d').date()
 if observed.date()!=day or not observed<=available<=now:raise ValueError('SOURCE_TIME')
 if b.node=='hk-open':hk09_times(b.day,started or x['observed_at'],x['observed_at'],x['available_at'],now.isoformat())
 if b.node=='hk-continuous-close' and observed.time().replace(tzinfo=None)!=dt.time(16):raise ValueError('CONTINUOUS_CLOSE_NOT_CAS')
 if b.node=='hk-auction-final':
  if x['actual_cas_end'] is None:raise ValueError('ACTUAL_CAS_EVIDENCE_REQUIRED')
  end=stamp(x['actual_cas_end'])
  if b.cas_event_ref is not None or not b.synthetic:
   cas_event(b,x,now) # event receipt supplies the actual end, not a 16:10 timer
  elif end.date()!=day or not dt.time(16,8)<=end.time().replace(tzinfo=None)<=dt.time(16,10) or not end<=observed:raise ValueError('CAS_EVENT_INVALID')
 elif x['actual_cas_end'] is not None:raise ValueError('CAS_EVIDENCE_WRONG_NODE')
 if not isinstance(x['rows'],list) or len(x['rows'])>len(b.scope):raise ValueError('ROWS_INVALID')
 seen=set()
 for r in x['rows']:
  if not isinstance(r,dict) or set(r)!={'symbol','observation'} or r['symbol'] not in b.scope or r['symbol'] in seen or not isinstance(r['observation'],str) or len(r['observation'])>4000:raise ValueError('ROW_INVALID')
  seen.add(r['symbol'])
 return sorted(set(b.scope)-seen)

def owner_gate(b):
 result=b.gate()
 # This repair covers the two afternoon nodes; keep the morning contract as-is.
 if b.node in ('hk-continuous-close','hk-auction-final') and result is not None and result is not True:raise ValueError('ORIGINAL_RESOURCE_GATE_DENIED')

def execute(b):
 if b.node=='hk-open' and not b.synthetic:raise ValueError('HK09_REAL_SCOPE_OWNER_RESOURCE_LOCK_UNBOUND')
 if b.node not in NODES:raise ValueError('NODE_INVALID')
 if b.node=='hk-auction-final' and not b.synthetic and (not isinstance(b.cas_event_ref,dict) or not callable(b.read_cas_event)):raise ValueError('ACTUAL_CAS_EVENT_BINDING_REQUIRED')
 if b.node!='hk-auction-final' and b.cas_event_ref is not None:raise ValueError('CAS_EVIDENCE_WRONG_NODE')
 if not b.scope or len(b.scope)>10000 or len(set(b.scope))!=len(b.scope) or any(not re.fullmatch(r'HK\.\d{5}',s) for s in b.scope):raise ValueError('SCOPE_INVALID')
 if any(not re.fullmatch('[0-9a-f]{64}',s) for s in [b.source_review_sha256,b.calendar_sha256,b.scope_sha256,b.code_version]):raise ValueError('REVIEWED_BINDINGS_REQUIRED')
 if b.scope_sha256!=sha(encode(list(b.scope))) or not b.environment_id or not b.job_id or not b.source_reference:raise ValueError('SCOPE_JOB_BINDING')
 if not all(callable(x) for x in [b.calendar,b.gate,b.lock,b.collect,b.clock]):raise ValueError('ORIGINAL_GATES_REQUIRED')
 identity={k:getattr(b,k) for k in ['node','day','source_reference','source_review_sha256','calendar_sha256','scope_sha256','code_version','environment_id','job_id','synthetic']}
 if b.cas_event_ref is not None:identity['cas_event_ref']=json.loads(encode(b.cas_event_ref))
 run=sha(encode(identity));out=Path(b.output)
 if out.is_symlink() or any(p.is_symlink() for p in out.parents):raise ValueError('OUTPUT_SYMLINK')
 owner_gate(b)
 with b.lock():
  owner_gate(b)
  now=stamp(b.clock().isoformat())
  if now.strftime('%Y%m%d')!=b.day:raise ValueError('NO_HISTORICAL_BACKFILL')
  if b.calendar(b.day) is not True:raise ValueError('CALENDAR_NOT_TRADING_DAY')
  if now.time().replace(tzinfo=None)<(dt.time(9) if b.node=='hk-open' else dt.time(16)):raise ValueError('NOT_DUE')
  if b.node=='hk-auction-final' and (b.cas_event_ref is not None or not b.synthetic):
   cas_event(b,None,now) # validate actual event evidence BEFORE any source call
  path=out/(run+'.json')
  if path.exists():
   if path.is_symlink() or path.stat().st_size>2*1024*1024:raise ValueError('SAVED_OUTPUT_INVALID')
   result=json.loads(path.read_bytes())
   if result['identity']!=identity or result['source_sha256']!=sha(encode(result['source'])):raise ValueError('SAVED_OUTPUT_CHANGED')
   missing=validate(b,result['source'],now,result.get('started_at'))
   expected_fields={'schema','identity','run_id','status','missing_symbols','source','source_sha256','raw_source_sha256','started_at','finished_at','business_verified','natural_verified','production_allowed','orders_sent','reused'}
   if b.cas_event_ref is not None:
    expected_fields.update(('cas_event_available_at','effective_final_available_at'))
    event=cas_event(b,result['source'],now)
    effective=max(stamp(result['source']['available_at']),stamp(event['available_at'])).isoformat()
    if result.get('cas_event_available_at')!=event['available_at'] or result.get('effective_final_available_at')!=effective:raise ValueError('SAVED_CAS_AVAILABILITY_CHANGED')
   if b.node=='hk-open':
    expected_fields.add('timing_status')
    timing=hk09_times(b.day,result['started_at'],result['source']['observed_at'],result['source']['available_at'],now.isoformat())['timing_status']
    if result.get('timing_status')!=timing:raise ValueError('HK09_TIMING_CHANGED')
   if set(result)!=expected_fields or result['schema']!='HK_OBSERVATION_RESULT_V1' or result['run_id']!=run:raise ValueError('SAVED_RESULT_IDENTITY')
   if any(result[k] is not False for k in ['business_verified','natural_verified','production_allowed','orders_sent','reused']):raise ValueError('SAVED_ADMISSION_CHANGED')
   if result['missing_symbols']!=missing or result['status']!=('OBSERVATION_PARTIAL' if missing else 'OBSERVATION_SAVED'):raise ValueError('SAVED_STATUS_CHANGED')
   if not isinstance(result['raw_source_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',result['raw_source_sha256']):raise ValueError('SAVED_RAW_PIN_INVALID')
   start=stamp(result['started_at']);finish=stamp(result['finished_at'])
   if start.strftime('%Y%m%d')!=b.day or finish.strftime('%Y%m%d')!=b.day or not start<=finish<=now:raise ValueError('SAVED_EXECUTION_TIME')
   validate(b,result['source'],finish,result['started_at'])
   if b.cas_event_ref!=identity.get('cas_event_ref'):raise ValueError('CAS_EVENT_BINDING_CHANGED')
   return dict(result,reused=True)
  if b.node=='hk-open':hk09_times(b.day,now.isoformat(),now.isoformat(),now.isoformat(),now.isoformat())
  raw=b.collect() # registered adapter alone owns provider; no guessed network source
  owner_gate(b)
  if not isinstance(raw,bytes) or len(raw)>1024*1024:raise ValueError('SOURCE_BYTE_LIMIT')
  finished=stamp(b.clock().isoformat())
  if finished.strftime('%Y%m%d')!=b.day:raise ValueError('COLLECTION_CROSSED_BUSINESS_DAY')
  if finished<now:raise ValueError('CLOCK_MOVED_BACKWARD')
  if b.calendar(b.day) is not True:raise ValueError('CALENDAR_NOT_TRADING_DAY')
  x=json.loads(raw);missing=validate(b,x,finished,now.isoformat())
  if b.cas_event_ref!=identity.get('cas_event_ref'):raise ValueError('CAS_EVENT_BINDING_CHANGED')
  result={'schema':'HK_OBSERVATION_RESULT_V1','identity':identity,'run_id':run,'status':'OBSERVATION_PARTIAL' if missing else 'OBSERVATION_SAVED','missing_symbols':missing,'source':x,'source_sha256':sha(encode(x)),'raw_source_sha256':sha(raw),'started_at':now.isoformat(),'finished_at':finished.isoformat(),'business_verified':False,'natural_verified':False,'production_allowed':False,'orders_sent':False,'reused':False}
  if b.cas_event_ref is not None:
   event=cas_event(b,x,finished)
   result['cas_event_available_at']=event['available_at']
   result['effective_final_available_at']=max(stamp(x['available_at']),stamp(event['available_at'])).isoformat()
  if b.node=='hk-open':result['timing_status']=hk09_times(b.day,now.isoformat(),x['observed_at'],x['available_at'],finished.isoformat())['timing_status']
  owner_gate(b);out.mkdir(parents=True,exist_ok=True)
  # Original task lock spans provider, identity and commit. No new replacement lock.
  with tempfile.NamedTemporaryFile(dir=out,prefix='.pending-',delete=False) as f:
   temp=Path(f.name);f.write(encode(result));f.flush();os.fsync(f.fileno())
  try:
   os.link(temp,path) # immutable: never overwrites another result
  finally:temp.unlink()
  return result

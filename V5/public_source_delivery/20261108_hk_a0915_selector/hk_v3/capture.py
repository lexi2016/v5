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
 # fromisoformat silently truncates finer fractions, including UTC offsets.
 # Reject evidence that cannot retain its stated instant before any time gate.
 if type(s) is not str or re.search(r'[.,][0-9]{7,}',s):raise ValueError('TIME_PRECISION_UNSUPPORTED')
 t=dt.datetime.fromisoformat(s)
 if t.tzinfo is None:raise ValueError('TIMEZONE_REQUIRED')
 if not s.endswith('Z'):
  offset=re.search(r'([+-])([0-9]{2})(?::?([0-9]{2}))?(?::?([0-9]{2}))?(?:[.,]([0-9]{1,6}))?$',s)
  if offset is None:raise ValueError('TIME_OFFSET_FORMAT_UNSUPPORTED')
  sign,hours,minutes,seconds,fraction=offset.groups()
  declared=dt.timedelta(hours=int(hours),minutes=int(minutes or 0),seconds=int(seconds or 0),microseconds=int((fraction or '').ljust(6,'0') or 0))
  if sign=='-':declared=-declared
  if t.utcoffset()!=declared:raise ValueError('TIME_OFFSET_NOT_REPRESENTABLE')
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

def validate(b,x,now):
 if set(x)!={'schema','node','day','scope','source_reference','observed_at','available_at','rows','actual_cas_end','data_kind'}:raise ValueError('SOURCE_FIELDS')
 if (x['schema'],x['node'],x['day'],x['scope'],x['source_reference'])!=('HK_OBSERVATION_V1',b.node,b.day,list(b.scope),b.source_reference):raise ValueError('SOURCE_IDENTITY')
 if x['data_kind']!=('SYNTHETIC_TEST' if b.synthetic else 'RECORDED_INPUT'):raise ValueError('SOURCE_KIND')
 observed=stamp(x['observed_at']);available=stamp(x['available_at']);day=dt.datetime.strptime(b.day,'%Y%m%d').date()
 if observed.date()!=day or not observed<=available<=now:raise ValueError('SOURCE_TIME')
 if b.node=='hk-open' and observed.time().replace(tzinfo=None)!=dt.time(9):raise ValueError('HK0900_OBSERVATION_REQUIRED')
 if b.node=='hk-open' and available.time().replace(tzinfo=None)>dt.time(9):raise ValueError('HK0900_LATE_NOT_BACKFILLED')
 if b.node=='hk-continuous-close' and observed.time().replace(tzinfo=None)!=dt.time(16):raise ValueError('CONTINUOUS_CLOSE_NOT_CAS')
 if b.node=='hk-auction-final':
  if x['actual_cas_end'] is None:raise ValueError('ACTUAL_CAS_EVIDENCE_REQUIRED')
  end=stamp(x['actual_cas_end'])
  if end.date()!=day or not dt.time(16,8)<=end.time().replace(tzinfo=None)<=dt.time(16,10) or not end<=observed:raise ValueError('CAS_EVENT_INVALID')
 elif x['actual_cas_end'] is not None:raise ValueError('CAS_EVIDENCE_WRONG_NODE')
 if not isinstance(x['rows'],list) or len(x['rows'])>len(b.scope):raise ValueError('ROWS_INVALID')
 seen=set()
 for r in x['rows']:
  if not isinstance(r,dict) or set(r)!={'symbol','observation'} or r['symbol'] not in b.scope or r['symbol'] in seen or not isinstance(r['observation'],str) or len(r['observation'])>4000:raise ValueError('ROW_INVALID')
  seen.add(r['symbol'])
 return sorted(set(b.scope)-seen)

def execute(b):
 if b.node not in NODES:raise ValueError('NODE_INVALID')
 if not b.scope or len(b.scope)>10000 or len(set(b.scope))!=len(b.scope) or any(not re.fullmatch(r'HK\.\d{5}',s) for s in b.scope):raise ValueError('SCOPE_INVALID')
 if any(not re.fullmatch('[0-9a-f]{64}',s) for s in [b.source_review_sha256,b.calendar_sha256,b.scope_sha256,b.code_version]):raise ValueError('REVIEWED_BINDINGS_REQUIRED')
 if b.scope_sha256!=sha(encode(list(b.scope))) or not b.environment_id or not b.job_id or not b.source_reference:raise ValueError('SCOPE_JOB_BINDING')
 if not all(callable(x) for x in [b.calendar,b.gate,b.lock,b.collect,b.clock]):raise ValueError('ORIGINAL_GATES_REQUIRED')
 identity={k:getattr(b,k) for k in ['node','day','source_reference','source_review_sha256','calendar_sha256','scope_sha256','code_version','environment_id','job_id','synthetic']}
 run=sha(encode(identity));out=Path(b.output)
 if out.is_symlink() or any(p.is_symlink() for p in out.parents):raise ValueError('OUTPUT_SYMLINK')
 b.gate()
 with b.lock():
  b.gate()
  now=stamp(b.clock().isoformat())
  if now.strftime('%Y%m%d')!=b.day:raise ValueError('NO_HISTORICAL_BACKFILL')
  if b.calendar(b.day) is not True:raise ValueError('CALENDAR_NOT_TRADING_DAY')
  if now.time().replace(tzinfo=None)<(dt.time(9) if b.node=='hk-open' else dt.time(16)):raise ValueError('NOT_DUE')
  path=out/(run+'.json')
  if path.exists():
   if path.is_symlink() or path.stat().st_size>2*1024*1024:raise ValueError('SAVED_OUTPUT_INVALID')
   result=json.loads(path.read_bytes())
   if result['identity']!=identity or result['source_sha256']!=sha(encode(result['source'])):raise ValueError('SAVED_OUTPUT_CHANGED')
   missing=validate(b,result['source'],now)
   expected_fields={'schema','identity','run_id','status','missing_symbols','source','source_sha256','raw_source_sha256','started_at','finished_at','business_verified','natural_verified','production_allowed','orders_sent','reused'}
   if set(result)!=expected_fields or result['schema']!='HK_OBSERVATION_RESULT_V1' or result['run_id']!=run:raise ValueError('SAVED_RESULT_IDENTITY')
   if any(result[k] is not False for k in ['business_verified','natural_verified','production_allowed','orders_sent','reused']):raise ValueError('SAVED_ADMISSION_CHANGED')
   if result['missing_symbols']!=missing or result['status']!=('OBSERVATION_PARTIAL' if missing else 'OBSERVATION_SAVED'):raise ValueError('SAVED_STATUS_CHANGED')
   if not isinstance(result['raw_source_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',result['raw_source_sha256']):raise ValueError('SAVED_RAW_PIN_INVALID')
   start=stamp(result['started_at']);finish=stamp(result['finished_at'])
   if start.strftime('%Y%m%d')!=b.day or finish.strftime('%Y%m%d')!=b.day or not start<=finish<=now:raise ValueError('SAVED_EXECUTION_TIME')
   validate(b,result['source'],finish)
   return dict(result,reused=True)
  raw=b.collect() # registered adapter alone owns provider; no guessed network source
  b.gate()
  if not isinstance(raw,bytes) or len(raw)>1024*1024:raise ValueError('SOURCE_BYTE_LIMIT')
  finished=stamp(b.clock().isoformat())
  if finished.strftime('%Y%m%d')!=b.day:raise ValueError('COLLECTION_CROSSED_BUSINESS_DAY')
  if finished<now:raise ValueError('CLOCK_MOVED_BACKWARD')
  if b.calendar(b.day) is not True:raise ValueError('CALENDAR_NOT_TRADING_DAY')
  x=json.loads(raw);missing=validate(b,x,finished)
  result={'schema':'HK_OBSERVATION_RESULT_V1','identity':identity,'run_id':run,'status':'OBSERVATION_PARTIAL' if missing else 'OBSERVATION_SAVED','missing_symbols':missing,'source':x,'source_sha256':sha(encode(x)),'raw_source_sha256':sha(raw),'started_at':now.isoformat(),'finished_at':finished.isoformat(),'business_verified':False,'natural_verified':False,'production_allowed':False,'orders_sent':False,'reused':False}
  b.gate();out.mkdir(parents=True,exist_ok=True)
  # Original task lock spans provider, identity and commit. No new replacement lock.
  with tempfile.NamedTemporaryFile(dir=out,prefix='.pending-',delete=False) as f:
   temp=Path(f.name);f.write(encode(result));f.flush();os.fsync(f.fileno())
  try:
   os.link(temp,path) # immutable: never overwrites another result
  finally:temp.unlink()
  return result

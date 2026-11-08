"""Date-general full-scope research projection. Not a source collector or buy selector.
The empty registry intentionally blocks production. Only the existing owner may bind
reviewed dates, original resource/lock policy and exact source inputs at integration.
"""
import datetime as dt
import hashlib
import json
import pathlib
import types
from zoneinfo import ZoneInfo
HERE=pathlib.Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
ROOT=PROJECT
TRUSTED_RUNS=()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def timestamp(v):
 t=dt.datetime.fromisoformat(v)
 if t.tzinfo is None:raise ValueError('TIMEZONE_REQUIRED')
 return t

def owner_gate(reg):
 result=reg['gate']()
 if result is not None and result is not True:raise ValueError('ORIGINAL_RESOURCE_GATE_DENIED')

def bindings():
 raw=(HERE/'code_bindings.json').read_bytes()
 if sha(raw)!=BINDINGS_SHA:raise ValueError('CODE_BINDINGS_CHANGED')
 return json.loads(raw)
def module(key):
 pin=bindings()[key];raw=(PROJECT/pin['path']).read_bytes()
 if len(raw)!=pin['bytes'] or sha(raw)!=pin['sha256']:raise ValueError('CODE_CHANGED:'+key)
 m=types.ModuleType('top200_'+key);m.__file__=str(PROJECT/pin['path']);exec(compile(raw,m.__file__,'exec'),m.__dict__)
 return m

def read(pin,safe):
 raw=safe.local_bytes(ROOT,pin['path'])
 if len(raw)!=pin['bytes'] or sha(raw)!=pin['sha256']:raise ValueError('INPUT_PIN_CHANGED:'+pin['path'])
 return json.loads(raw)

def contract_identity(reg):
 return sha(canonical({k:reg[k] for k in ('run_id','environment_id','domain','source_date','scheduled_at','trigger_source','inputs','owner_identity','output_relative','adapter_sha256')}))

def validate_authorized_scope(reg,docs,symbols):
 """New scope contract; a reviewed registry must pin it, never a request body.

 Matching a document does not itself grant source, market-wide or PIT admission.
 The original fixed-5575 guard remains in calculate; this is an additional gate.
 """
 scope=docs.get('authorized_scope')
 if scope is None:
  if reg['domain']=='production':raise ValueError('AUTHORIZED_SCOPE_CONTRACT_REQUIRED')
  return {'status':'UNKNOWN','scope_count':len(symbols),'reference':None,'source_admission':False}
 pin=reg['inputs'].get('authorized_scope')
 if not isinstance(pin,dict) or docs['source_review'].get('authorized_scope_ref')!=pin:raise ValueError('AUTHORIZED_SCOPE_REVIEW_BINDING')
 if scope.get('schema')!='TOP200_AUTHORIZED_SCOPE_V1' or scope.get('scope_kind')!='AUTHORIZED_COMPLETE_RESEARCH_UNIVERSE':raise ValueError('AUTHORIZED_SCOPE_SCHEMA')
 if type(scope.get('source_date'))is not int or scope['source_date']!=reg['source_date']:raise ValueError('AUTHORIZED_SCOPE_DATE')
 if any(not isinstance(scope.get(k),str) or not scope[k].strip() or scope[k].strip().upper() in ('UNKNOWN','NONE','UNBOUND','NOT_SET') for k in ('authority_identity','universe_version')):raise ValueError('AUTHORIZED_SCOPE_AUTHORITY')
 declared=scope.get('symbols')
 if not isinstance(declared,list) or any(not isinstance(s,str) for s in declared) or len(declared)!=len(set(declared)):raise ValueError('AUTHORIZED_SCOPE_UNIQUE')
 if type(scope.get('scope_count'))is not int or scope['scope_count']!=len(declared) or declared!=symbols:raise ValueError('AUTHORIZED_SCOPE_EXACT_ORDER')
 if scope.get('symbols_sha256')!=sha(canonical(declared)):raise ValueError('AUTHORIZED_SCOPE_DIGEST')
 return {'status':'MATCHED_REVIEWED_SCOPE_CONTRACT','scope_count':len(symbols),
         'reference':pin,'universe_version':scope['universe_version'],
         'authority_identity':scope['authority_identity'],'source_admission':False}

def source_availability(times,scheduled,day,checked_at):
 """Preserve when data became available separately from its market date."""
 started=timestamp(times['capture_started']);ended=timestamp(times['capture_ended'])
 if started>ended or ended.astimezone(ZoneInfo('Asia/Shanghai')).date()!=day or ended>checked_at:raise ValueError('SOURCE_CAPTURE_TIME_ORDER')
 available=timestamp(times['available_at']) if times.get('available_at') is not None else None
 if available is not None and not ended<=available<=checked_at:raise ValueError('SOURCE_AVAILABILITY_TIME_ORDER')
 published=timestamp(times['provider_published_at']) if times.get('provider_published_at') is not None else None
 if published is not None and (available is None or published>available):raise ValueError('SOURCE_PUBLICATION_TIME_ORDER')
 late=True if ended>scheduled else (available>scheduled if available is not None else None)
 return {'capture_started':times['capture_started'],'capture_ended':times['capture_ended'],
         'available_at':times.get('available_at'),'provider_published_at':times.get('provider_published_at'),
         'availability_status':'RECORDED_IN_PINNED_SOURCE_REVIEW' if available is not None else 'UNKNOWN',
         'late_source':late}

def calculate(reg,docs):
 date=reg['source_date']
 if type(date)is not int:raise ValueError('INTEGER_SOURCE_DATE_REQUIRED')
 day=dt.datetime.strptime(str(date),'%Y%m%d').date()
 scheduled=timestamp(reg['scheduled_at']);local=scheduled.astimezone(ZoneInfo('Asia/Shanghai'))
 if local.date()!=day or (local.hour,local.minute,local.second,local.microsecond)!=(15,0,0,0):raise ValueError('NODE_DATE_1500_REQUIRED')
 ledger=docs['ledger'];catalog=docs['catalog'];review=docs['source_review']
 if review.get('status')!='PASS_SCOPED_ACTUAL_RAW_LEDGER_AND_GBBQ_INTEGRITY_REVIEW' or review.get('source_date')!=date:raise ValueError('ORIGINAL_SOURCE_REVIEW_REQUIRED')
 if review['ledger_ref']!=reg['inputs']['ledger'] or review['catalog_ref']!=reg['inputs']['catalog']:raise ValueError('SOURCE_REVIEW_BINDING')
 symbols=[r['symbol'] for r in catalog['latest_selections']]
 authorized=validate_authorized_scope(reg,docs,symbols)
 if ledger['fixed_scope_count']!=5575 or len(symbols)!=5575 or ledger['source_date']!=date or ledger['scope_order']!=symbols:raise ValueError('FULL_5575_SCOPE_DATE')
 times=review['source_timestamps']['g4']
 availability=source_availability(times,scheduled,day,dt.datetime.now(dt.timezone.utc))
 result=module('ranking').project_rows(ledger['rows'],symbols,date)
 result['source_timestamps']=times;result['input_refs']=reg['inputs']
 # Never imply after-close material was available at 15:00. Provider publication
 # or final-market coverage not proved by capture timestamp; PIT stays unaccepted.
 result['authorized_scope']=authorized;result['availability']=availability
 result['late_source']=availability['late_source']
 result['status']=('LATE_SOURCE_RESEARCH_ONLY' if availability['late_source'] is True else
                   'RESEARCH_PROJECTION_READY_PENDING_AVAILABILITY_REVIEW' if availability['late_source'] is None else
                   'RESEARCH_PROJECTION_READY_PENDING_PIT_REVIEW')
 result['formal_1500_pit_verified']=False
 return result

def dispatch(run_id,environment_id):
 matches=[r for r in TRUSTED_RUNS if (r['run_id'],r['environment_id'])==(run_id,environment_id)]
 if len(matches)!=1:return {'status':'BLOCKED_NO_TRUSTED_REGISTRATION','node':'a-close-top200','jobs_started':0,'natural_verified':False}
 reg=matches[0]
 if reg['domain'] not in ('synthetic','production'):raise ValueError('DOMAIN')
 if reg['trigger_source'] not in ('MANUAL_TEST','SCHEDULED'):raise ValueError('TRIGGER_SOURCE')
 if reg['domain']=='synthetic' and reg['trigger_source']!='MANUAL_TEST':raise ValueError('SYNTHETIC_IS_NOT_NATURAL')
 if reg['adapter_sha256']!=sha(pathlib.Path(__file__).read_bytes()):raise ValueError('ADAPTER_CHANGED')
 if not callable(reg.get('guard_factory')) or not callable(reg.get('gate')) or not reg.get('owner_identity'):raise ValueError('ORIGINAL_OWNER_GUARD_AND_GATE_REQUIRED')
 safe=module('safeio');original=module('original_rank')
 # Same original resource floor and bounded output cap, plus owner-specific gate.
 original.resources();owner_gate(reg)
 review=read(reg['review'],safe)
 if review.get('verdict')!='APPROVED_RESEARCH_PROJECTION_ONLY' or review.get('contract_sha256')!=contract_identity(reg) or review.get('domain')!=reg['domain'] or not review.get('independent_reviewer_identity'):raise ValueError('INDEPENDENT_EXECUTION_REVIEW_REQUIRED')
 relative=pathlib.Path(reg['output_relative'])
 if relative.is_absolute() or '..' in relative.parts or not relative.parts:raise ValueError('OUTPUT_SCOPE')
 with reg['guard_factory'](reg['owner_identity']):
  original.resources();owner_gate(reg)
  docs={k:read(v,safe) for k,v in reg['inputs'].items()}
  result=calculate(reg,docs)
  report={'schema':'DATED_TOP200_EXECUTION_V1','node':'a-close-top200','run_id':run_id,'environment_id':environment_id,'domain':reg['domain'],'scheduled_at':reg['scheduled_at'],'trigger_source':reg['trigger_source'],'source_date':reg['source_date'],'contract_sha256':contract_identity(reg),'code_bindings':bindings(),'adapter_sha256':reg['adapter_sha256'],'execution_review':reg['review'],'result':result,'natural_verified':False,'business_accepted':False,'delivery_status':'NOT_SENT','no_buy':True}
  report['identity']=sha(canonical(report));report['observed_at']=dt.datetime.now(dt.timezone.utc).isoformat()
  for pin in reg['inputs'].values():read(pin,safe)
  read(reg['review'],safe);original.resources();owner_gate(reg)
  saved=safe.freeze(ROOT/relative,report)
 return {'status':result['status'],'output':saved['path'],'saved':saved,'reused':saved['reused'],'natural_verified':False,'business_accepted':False,'delivery_status':'NOT_SENT'}

BINDINGS_SHA='a757dbf5fc31e8c9b12e85f0df94c6b7cc9b1f3ae78f05c9ecb21079cab94eb9'

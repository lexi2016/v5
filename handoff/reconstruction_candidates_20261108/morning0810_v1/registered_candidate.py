"""Reviewed process registry selects dated inputs. No HTTP/request-supplied authority.
Original functions reused; source protocol is NEW, not claimed as recovered original.
"""
import builtins,contextlib,datetime as dt,hashlib,json,pathlib,types
from decimal import Decimal
from zoneinfo import ZoneInfo
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TRUSTED_RUNS=()  # Only reviewed deployment code may register original owner contexts.
NODES=('freeze','jk-verify','morning-delivery','opening-prep')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def time(v):
 t=dt.datetime.fromisoformat(v)
 if t.tzinfo is None:raise ValueError('TIMEZONE_REQUIRED')
 return t

def codes():
 b=(HERE/'code_bindings.json').read_bytes()
 if sha(b)!=CODE_BINDINGS_SHA:raise ValueError('CODE_BINDINGS_CHANGED')
 return json.loads(b)
def module(key,safe=None):
 p=codes()[key];raw=safe.local_bytes(ROOT,p['path']) if safe else (ROOT/p['path']).read_bytes()
 if sha(raw)!=p['sha256']:raise ValueError('CODE_CHANGED:'+key)
 m=types.ModuleType('morning_v2_'+key);m.__file__=str(ROOT/p['path'])
 imp=dict(vars(builtins));original=builtins.__import__
 imp['__import__']=lambda name,*a,**kw:safe if name=='safeio' else original(name,*a,**kw)
 m.__dict__['__builtins__']=imp;exec(compile(raw,m.__file__,'exec'),m.__dict__)
 return m

def read(ref,safe):
 raw=safe.local_bytes(ROOT,ref['path'])
 if len(raw)!=ref['bytes'] or sha(raw)!=ref['sha256']:raise ValueError('INPUT_PIN_CHANGED:'+ref['path'])
 return json.loads(raw)

def contract_identity(reg):
 # All semantic inputs and authority versions, not mutable callables or current clock.
 return sha(canonical({k:reg[k] for k in ('node','run_id','environment_id','domain','business_date','source_date','cutoff','inputs','policy','owner_identity','output_relative','adapter_sha256')}))

def verify(reg,safe):
 if reg['adapter_sha256']!=sha(safe.local_bytes(HERE,'registered.py')):raise ValueError('ADAPTER_CHANGED')
 day=dt.datetime.strptime(reg['business_date'],'%Y%m%d').date()
 source=dt.datetime.strptime(reg['source_date'],'%Y%m%d').date()
 cutoff=time(reg['cutoff'])
 if cutoff.astimezone(ZoneInfo('Asia/Shanghai')).date()!=day or source>day:raise ValueError('DATE_BINDING')
 if reg['domain'] not in ('synthetic','production'):raise ValueError('DOMAIN')
 if not callable(reg.get('owner_guard_factory')):raise ValueError('ORIGINAL_OWNER_GUARD_MISSING')
 if not reg.get('owner_identity'):raise ValueError('ORIGINAL_OWNER_IDENTITY_MISSING')
 policy=read(reg['policy'],safe);review=read(reg['review'],safe)
 if review.get('verdict')!='APPROVED' or review.get('contract_sha256')!=contract_identity(reg) or review.get('domain')!=reg['domain'] or not review.get('independent_reviewer_identity') or review.get('policy_sha256')!=reg['policy']['sha256']:raise ValueError('INDEPENDENT_REVIEW_REQUIRED')
 # Trusted review must describe the exact scope, including previously authorized output.
 if policy.get('node')!=reg['node'] or policy.get('domain')!=reg['domain']:raise ValueError('POLICY_SCOPE')
 if policy.get('version') is None or policy.get('original_policy_reference') is None:raise ValueError('ORIGINAL_POLICY_REQUIRED')
 docs={k:read(v,safe) for k,v in reg['inputs'].items()}
 evidence=docs['pit']
 if evidence.get('business_date')!=reg['business_date'] or evidence.get('source_date')!=reg['source_date']:raise ValueError('PIT_DATE')
 expected={k:v['sha256'] for k,v in reg['inputs'].items() if k!='pit'}
 if evidence.get('input_sha256')!=expected:raise ValueError('PIT_INPUT_BINDING')
 if evidence.get('known_by_cutoff') is not True or time(evidence['latest_available_at'])>cutoff:raise ValueError('POST_CUTOFF_INPUT')
 if evidence.get('source_admission') is not True:raise ValueError('SOURCE_ADMISSION_REQUIRED')
 return policy,docs

def semantic_compare(doc,policy,cutoff):
 """Exact normalized fields from independently approved policy; no scoring/estimation."""
 expected=policy['semantic_keys'];sources=policy['source_ids']
 if len(sources)<2 or len(set(sources))!=len(sources) or not expected or len(set(expected))!=len(expected):raise ValueError('MULTISOURCE_POLICY')
 if set(doc['sources'])!=set(sources):raise ValueError('SOURCE_SET_MISMATCH')
 maps={};unknown=[];conflicts=[]
 for source in sources:
  d=doc['sources'][source]
  if time(d['available_at'])>cutoff:raise ValueError('SOURCE_AFTER_CUTOFF')
  rows=d['facts']
  if len({r['key'] for r in rows})!=len(rows) or {r['key'] for r in rows}!=set(expected):raise ValueError('SEMANTIC_KEY_SCOPE')
  values={}
  for row in rows:
   # Key contract includes symbol/field/unit/basis/currency/asof. Raw units cannot be guessed.
   definition=policy['key_definitions'][row['key']]
   if set(definition)!={'symbol','field','unit','basis','currency','asof'} or any(not definition[k] for k in ('symbol','field','unit','basis','asof')):raise ValueError('SEMANTIC_DEFINITION_REQUIRED')
   if row['definition']!=definition:raise ValueError('SEMANTIC_DEFINITION_MISMATCH')
   value=row['value']
   if value is None:unknown.append([source,row['key']]);values[row['key']]=None;continue
   number=Decimal(str(value))
   if not number.is_finite():raise ValueError('NONFINITE_SOURCE')
   values[row['key']]=number
  maps[source]=values
 for key in expected:
  observed={maps[s][key] for s in sources}
  if len(observed)>1:conflicts.append(key)
 return {'compared_keys':len(expected),'sources':sources,'unknown':unknown,'conflicts':conflicts,'passed':not unknown and not conflicts}

def calculate(reg,policy,docs,safe):
 node=reg['node']
 if node=='freeze':
  panel=docs['panel']
  if panel['source_date']!=reg['source_date'] or panel['scope_count']!=policy['panel_denominator']:raise ValueError('PANEL_DATE_SCOPE')
  audit=module('crosscheck',safe).audit(panel,reg['business_date'])
  semantic=semantic_compare(docs['multi_source'],policy,time(reg['cutoff']))
  if audit['errors'] or not semantic['passed']:return {'status':'BLOCKED_SOURCE_REVIEW','row_audit':audit,'semantic_review':semantic,'formal_freeze':False}
  return {'status':'REVIEWED_FREEZE_MANIFEST_READY','row_audit':audit,'semantic_review':semantic,'formal_freeze':reg['domain']=='production','freeze_manifest':{'contract_sha256':contract_identity(reg),'business_date':reg['business_date'],'source_date':reg['source_date'],'scope_count':panel['scope_count'],'source_inputs':reg['inputs'],'review':reg['review'],'policy':reg['policy'],'missing_and_unknown_preserved':True}}
 if node=='jk-verify':
  if reg['source_date']!=reg['business_date']:raise ValueError('JK_CURRENT_DAY_REQUIRED')
  day=dt.datetime.strptime(reg['source_date'],'%Y%m%d').date().isoformat()
  result=module('jk',safe).reconcile(docs['observations'],day)
  expected={(x['symbol'],x['field']) for x in policy['required_comparisons']}
  actual={(x['symbol'],x['field']) for x in result['comparisons']}
  ok=actual==expected and all(x['status']=='OBSERVED_VALUES_AGREE' for x in result['comparisons'])
  return {'status':'RECONCILED' if ok else 'BLOCKED_MISSING_OR_CONFLICTING_SOURCE','observations':result,'source_admission':False,'collector_calls':0}
 if node=='morning-delivery':
  return {'status':'BLOCKED_DELIVERY_ASSEMBLY_NOT_BOUND','delivery_status':'NOT_SENT','source_calls':0,'business_accepted':False}
 # opening-prep ONLY creates names+prompt. 08:10 cannot fall through here.
 panel=docs['panel'];top=docs['top']
 if str(top['source_date'])!=reg['source_date'] or panel['source_date']!=reg['source_date']:raise ValueError('TOP_PANEL_DATE')
 if top['schema']!=policy['top_schema']:raise ValueError('TOP_SCHEMA_POLICY')
 if top['schema']=='DATED_FIXED_REFERENCE_TOP200_V1':
  # Original join only recognizes its historical schema label. No values/dates are changed.
  top=dict(top,schema='NOV6_FIXED_REFERENCE_TOP200_V1')
 elif top['schema']!='NOV6_FIXED_REFERENCE_TOP200_V1':raise ValueError('TOP_SCHEMA_UNSUPPORTED')
 rows=module('prep',safe).annotate(top,panel)
 prompt='请按名单核查目标交易日 '+reg['business_date']+' 的用户提供资料；分别列原始URL、披露时刻及时区、事件日期、事实/观点、风险与UNKNOWN。不得改四组公式或把事后数据倒填盘前；不表示买入或监测激活。名单行情日 '+reg['source_date']+'；截止 '+reg['cutoff']+'。\n'+'\n'.join(f"{x['rank']}. {x['symbol']} {x['name']}" for x in rows)
 return {'status':'LIST_AND_PROMPT_READY','rows':rows,'prompt':prompt,'target_date':reg['business_date'],'source_date':reg['source_date'],'monitor_list_frozen':False,'source_calls':0,'delivery_status':'NOT_SENT'}

def dispatch(node,run_id,environment_id,gate):
 if node not in NODES:raise ValueError('NODE')
 matches=[r for r in TRUSTED_RUNS if (r['node'],r['run_id'],r['environment_id'])==(node,run_id,environment_id)]
 if len(matches)!=1:return {'status':'BLOCKED_NO_TRUSTED_REGISTRATION','node':node,'jobs_started':0,'natural_verified':False}
 if not callable(gate):raise ValueError('ORIGINAL_RESOURCE_GATE_REQUIRED')
 reg=matches[0];safe=module('safeio')
 if hasattr(gate,'start'):gate.start()
 gate();policy,docs=verify(reg,safe)
 # Original owner guard checks actual lock identity/reconciliation; not a replacement lock.
 with reg['owner_guard_factory'](reg['owner_identity']):
  gate();result=calculate(reg,policy,docs,safe);gate()
  report={'schema':'DATED_MORNING_NODE_RESULT_V2','node':node,'run_id':run_id,'environment_id':environment_id,'domain':reg['domain'],'business_date':reg['business_date'],'source_date':reg['source_date'],'contract_sha256':contract_identity(reg),'result':result,'code_bindings':codes(),'adapter_sha256':reg['adapter_sha256'],'review':reg['review'],'natural_verified':False,'business_accepted':False,'delivery_status':'NOT_SENT'}
  report['identity']=sha(canonical(report));report['observed_at']=dt.datetime.now(dt.timezone.utc).isoformat()
  relative=pathlib.Path(reg['output_relative'])
  if relative.is_absolute() or '..' in relative.parts or not relative.parts:raise ValueError('OUTPUT_SCOPE')
  gate();saved=safe.freeze(ROOT/relative,report)
 return {'status':result['status'],'saved':saved,'node':node,'domain':reg['domain'],'natural_verified':False,'business_accepted':False,'delivery_status':'NOT_SENT'}
CODE_BINDINGS_SHA='32cf66923cc2c3de8c300f82f7bd6df2d74155f8e2c7ed8f6823d030672a3f6d'

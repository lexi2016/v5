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
 # Per-fact temporal contract is mandatory; an early envelope cannot admit late facts.
 ages=policy.get('semantic_max_age_seconds')
 if type(ages) is not dict or set(ages)!=set(expected) or any(type(v) is not int or v<=0 for v in ages.values()):raise ValueError('SEMANTIC_FRESHNESS_POLICY_REQUIRED')
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
   try:
    observed=time(row['observed_at']);available=time(row['available_at']);envelope=time(d['available_at'])
    if not observed<=available<=envelope<=cutoff:raise ValueError('SEMANTIC_FACT_TIME_ORDER_OR_CUTOFF')
    if (cutoff-observed).total_seconds()>ages[row['key']]:raise ValueError('SEMANTIC_FACT_STALE')
   except (KeyError,TypeError,OverflowError) as exc:
    raise ValueError('SEMANTIC_FACT_TIMING_REQUIRED') from exc
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

def validate_jk_observations(doc,policy,cutoff):
 """New fail-closed candidate contract, NOT recovered production source authority.
 source_ids are reviewed provider identities, not arbitrary observation IDs.
 Freshness limit must be supplied by reviewed policy; no guessed default.
 """
 try:
  required=policy['required_comparisons'];age=policy['max_observation_age_seconds']
  if type(required) is not list or not required:raise ValueError('JK_NONEMPTY_SCOPE_REQUIRED')
  if type(age) is not int or age<=0:raise ValueError('JK_FRESHNESS_POLICY_REQUIRED')
  expected={}
  for c in required:
   key=(c['symbol'],c['field']);sources=c['source_ids']
   if any(type(v) is not str or not v for v in key) or key in expected:raise ValueError('JK_UNIQUE_SCOPE_REQUIRED')
   if type(sources) is not list or len(sources)<2 or any(type(v) is not str or not v for v in sources) or len(set(sources))!=len(sources):raise ValueError('JK_INDEPENDENT_SOURCE_POLICY_REQUIRED')
   expected[key]=set(sources)
  rows=doc['records']
  if type(rows) is not list or not rows:raise ValueError('JK_OBSERVATIONS_REQUIRED')
  seen={key:set() for key in expected}
  for row in rows:
   key=(row['symbol'],row.get('comparison_group',row['field']));source=row['source_id']
   if key not in expected or source not in expected[key]:raise ValueError('JK_SOURCE_SCOPE_MISMATCH')
   if source in seen[key]:raise ValueError('JK_DUPLICATE_SOURCE')
   observed=time(row['observed_at']);available=time(row['available_at'])
   if available<observed:raise ValueError('JK_TIME_ORDER')
   if observed>cutoff or available>cutoff:raise ValueError('JK_AFTER_CUTOFF')
   if (cutoff-observed).total_seconds()>age:raise ValueError('JK_STALE_OBSERVATION')
   seen[key].add(source)
  if seen!=expected:raise ValueError('JK_SOURCE_COVERAGE_INCOMPLETE')
 except (KeyError,TypeError,OverflowError) as exc:
  raise ValueError('JK_INPUT_OR_POLICY_SCHEMA') from exc
 return {'per_record_cutoff_checked':True,'max_observation_age_seconds':age,
         'source_identity_independence':'REQUIRES_TRUSTED_POLICY_REVIEW',
         'source_admission':False,'production_bound':False}

def assemble_morning_preview(reg,policy,docs):
 """NEW synthetic-only 08:10 assembly contract; not original delivery authority.
 Structured sections preserve their reported status/content. No sends or collection.
 The existing dispatch still requires its unchanged owner/review/source gates.
 """
 names=('freeze','morning-materials','jk-verify')
 cutoff=time(reg['cutoff']);local=cutoff.astimezone(ZoneInfo('Asia/Shanghai'))
 day=dt.datetime.strptime(reg['business_date'],'%Y%m%d').date()
 if local.date()!=day or local.time()!=dt.time(8,10):raise ValueError('ASSEMBLY_0810_CUTOFF')
 if reg.get('domain')!='synthetic' or policy.get('assembly_schema')!='MORNING_0810_PREVIEW_V1':raise ValueError('ASSEMBLY_PREVIEW_ONLY')
 ages=policy['section_max_age_seconds'];inputs=docs['assembly_sections']
 if type(ages) is not dict or set(ages)!=set(names) or any(type(v) is not int or v<=0 for v in ages.values()):raise ValueError('ASSEMBLY_AGE_POLICY')
 if type(inputs) is not dict or set(inputs)-set(names):raise ValueError('ASSEMBLY_SECTIONS')
 sections=[];missing=[]
 for name in names:
  if name not in inputs:
   missing.append(name);sections.append({'name':name,'status':'UNKNOWN','content':None,'input_identity':None});continue
  doc=inputs[name]
  if type(doc) is not dict or set(doc)!={'business_date','source_date','observed_at','available_at','status','content','source_reference'}:raise ValueError('ASSEMBLY_SECTION_SCHEMA')
  if doc['business_date']!=reg['business_date']:raise ValueError('ASSEMBLY_TARGET_DAY')
  source=dt.datetime.strptime(doc['source_date'],'%Y%m%d').date()
  if source>day:raise ValueError('ASSEMBLY_SOURCE_AFTER_TARGET')
  observed=time(doc['observed_at']);available=time(doc['available_at'])
  if not observed<=available<=cutoff or (cutoff-observed).total_seconds()>ages[name]:raise ValueError('ASSEMBLY_SECTION_TIMING')
  if any(type(doc[k]) is not str or not doc[k].strip() for k in ('status','source_reference')):raise ValueError('ASSEMBLY_STATUS_SOURCE')
  if type(doc['content']) is not dict:raise ValueError('ASSEMBLY_STRUCTURED_CONTENT')
  raw=canonical(doc)
  if len(raw)>2*1024*1024:raise ValueError('ASSEMBLY_SECTION_SIZE')
  sections.append(dict(json.loads(raw),name=name,input_identity=sha(raw)))
 result={'schema':'MORNING_0810_PREVIEW_RESULT_V1','contract_kind':'NEW_SYNTHETIC_ONLY_NOT_ORIGINAL_DELIVERY',
         'status':'PARTIAL_PREVIEW_NOT_ADMITTED' if missing else 'PREVIEW_ASSEMBLED_NOT_ADMITTED',
         'business_date':reg['business_date'],'cutoff':reg['cutoff'],'sections':sections,'missing':missing,
         'delivery_status':'NOT_SENT','source_admission':'UNKNOWN','source_calls':0,'formal_freeze':False,
         'business_accepted':False,'production_allowed':False,'natural_verified':False}
 result['identity']=sha(canonical(result))
 return result

def normalize_jk_semantics(doc,policy):
 """Reviewed provider/field mapping only. No inferred aliases or independence.
 Source authority still requires existing policy review and source gates.
 """
 from urllib.parse import urlsplit
 import copy
 from decimal import InvalidOperation
 catalog=policy.get('provider_catalog');required=policy['required_comparisons']
 if type(catalog) is not dict or not catalog:raise ValueError('JK_PROVIDER_CATALOG_REQUIRED')
 expected={};used=set()
 for comparison in required:
  key=(comparison['symbol'],comparison['field']);providers=comparison['source_ids'];semantic=comparison.get('semantic_contract')
  if type(semantic) is not dict or set(semantic)!={'unit','basis','currency','raw_fields'}:raise ValueError('JK_SEMANTIC_CONTRACT_REQUIRED')
  if any(type(semantic[k]) is not str or not semantic[k].strip() for k in ('unit','basis','currency')):raise ValueError('JK_SEMANTIC_DEFINITION')
  mapping=semantic['raw_fields']
  if type(mapping) is not dict or set(mapping)!=set(providers):raise ValueError('JK_FIELD_MAPPING_PROVIDER_SCOPE')
  groups=[]
  for provider in providers:
   entry=catalog.get(provider)
   if type(entry) is not dict or set(entry)!={'independence_group','allowed_urls'} or type(entry['independence_group']) is not str or not entry['independence_group'].strip():raise ValueError('JK_PROVIDER_DEFINITION')
   urls=entry['allowed_urls']
   if type(urls) is not list or not urls or len(set(urls))!=len(urls):raise ValueError('JK_PROVIDER_URL_POLICY')
   for url in urls:
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:raise ValueError('JK_PROVIDER_URL_POLICY')
   fields=mapping[provider]
   if type(fields) is not list or not fields or any(type(x) is not str or not x.strip() or x=='UNKNOWN' for x in fields) or len(set(fields))!=len(fields):raise ValueError('JK_RAW_FIELD_POLICY')
   groups.append(entry['independence_group']);used.add(provider)
  if len(groups)!=len(set(groups)):raise ValueError('JK_SHARED_UPSTREAM_NOT_INDEPENDENT')
  expected[key]=semantic
 if set(catalog)!=used:raise ValueError('JK_PROVIDER_CATALOG_SCOPE')
 normalized=copy.deepcopy(doc);evidence={};gaps=[];urls_seen={};ids=set()
 for row in normalized['records']:
  key=(row['symbol'],row.get('comparison_group',row['field']));provider=row['source_id'];semantic=expected[key]
  raw_field=row['field']
  if type(raw_field) is not str or raw_field not in semantic['raw_fields'][provider]:raise ValueError('JK_RAW_FIELD_SEMANTICS')
  if any(row.get(k)!=semantic[k] for k in ('unit','basis','currency')):raise ValueError('JK_UNIT_BASIS_CURRENCY')
  url=row.get('url');entry=catalog[provider]
  if url not in entry['allowed_urls']:raise ValueError('JK_PROVIDER_URL_BINDING')
  if (key,url) in urls_seen and urls_seen[(key,url)]!=provider:raise ValueError('JK_SHARED_URL_NOT_INDEPENDENT')
  urls_seen[(key,url)]=provider
  observation=row.get('id')
  if type(observation) is not str or not observation.strip() or observation in ids:raise ValueError('JK_OBSERVATION_ID')
  ids.add(observation)
  evidence.setdefault(key,[]).append({'provider_id':provider,'observation_id':observation,'raw_field':raw_field,'normalized_field':key[1],'unit':row['unit'],'basis':row['basis'],'currency':row['currency'],'url':url,'independence_group':entry['independence_group']})
  value=row.get('value')
  try:
   if value is None or type(value) is bool:raise ValueError('UNKNOWN_VALUE')
   number=Decimal(str(value))
   if not number.is_finite() or number<=0:raise ValueError('INVALID_VALUE')
   row['value']=str(number) # numeric representation only; no unit/scaling conversion
  except (ValueError,InvalidOperation):
   gaps.append({'provider_id':provider,'observation_id':observation,'symbol':key[0],'field':key[1],'reason':'UNKNOWN_OR_INVALID_VALUE'})
  row['field']=key[1];row['comparison_group']=key[1]
 return normalized,evidence,gaps

def build_freeze_lineage(reg,policy,docs):
 """New explicit ancestry/delta contract. Consistency never establishes source authority.
 Existing dispatch must pin parent+change documents and independently review policy.
 """
 import re
 contract=policy.get('freeze_chain')
 if type(contract) is not dict or set(contract)!={'schema','version','mode','expected_parent_identity'} or contract['schema']!='FREEZE_CHAIN_POLICY_V1':raise ValueError('FREEZE_CHAIN_POLICY_REQUIRED')
 version=contract['version']
 if type(version) is not str or not version.strip():raise ValueError('FREEZE_VERSION')
 def date(value):
  if type(value) is not str or not re.fullmatch('[0-9]{8}',value):raise ValueError('FREEZE_DATE')
  return dt.datetime.strptime(value,'%Y%m%d').date()
 day=date(reg['business_date']);source=date(reg['source_date']);cutoff=time(reg['cutoff'])
 if source>day or cutoff.astimezone(ZoneInfo('Asia/Shanghai')).date()!=day:raise ValueError('FREEZE_DATE_ORDER')
 rows=docs['panel']['rows'];current={}
 for row in rows:
  symbol=row['symbol']
  if type(symbol) is not str or not re.fullmatch(r'[0-9]{6}\.(SZ|SH|BJ)',symbol) or symbol in current:raise ValueError('FREEZE_ROW_IDENTITY')
  current[symbol]=sha(canonical(row))
 parent=docs.get('freeze_parent');old={};parent_identity=None
 if contract['mode']=='GENESIS':
  if parent is not None or contract['expected_parent_identity'] is not None:raise ValueError('FREEZE_GENESIS_PARENT')
 elif contract['mode']=='DELTA':
  keys={'schema','version','business_date','source_date','cutoff','parent_identity','row_sha256','changes','identity'}
  if type(parent) is not dict or set(parent)!=keys or parent['schema']!='DATED_FREEZE_LINEAGE_V1':raise ValueError('FREEZE_PARENT_REQUIRED')
  parent_identity=sha(canonical({k:v for k,v in parent.items() if k!='identity'}))
  if parent_identity!=parent['identity'] or parent_identity!=contract['expected_parent_identity']:raise ValueError('FREEZE_PARENT_IDENTITY')
  if type(parent['version']) is not str or not parent['version'].strip() or parent['version']==version:raise ValueError('FREEZE_PARENT_VERSION')
  parent_day=date(parent['business_date']);parent_source=date(parent['source_date']);parent_cutoff=time(parent['cutoff'])
  if not parent_source<=parent_day<=day or parent_source>source or parent_cutoff>cutoff or parent_cutoff.astimezone(ZoneInfo('Asia/Shanghai')).date()!=parent_day:raise ValueError('FREEZE_PARENT_DATE_ORDER')
  old=parent['row_sha256']
  if type(old) is not dict or any(type(k) is not str or not re.fullmatch(r'[0-9]{6}\.(SZ|SH|BJ)',k) or type(v) is not str or not re.fullmatch('[0-9a-f]{64}',v) for k,v in old.items()):raise ValueError('FREEZE_PARENT_ROWS')
 else:raise ValueError('FREEZE_CHAIN_MODE')
 added=sorted(set(current)-set(old));removed=sorted(set(old)-set(current));changed=sorted(k for k in set(old)&set(current) if old[k]!=current[k])
 reasons=docs.get('freeze_changes')
 if type(reasons) is not dict or set(reasons)!=set(added+removed+changed) or any(type(v) is not str or not v.strip() for v in reasons.values()):raise ValueError('FREEZE_EXACT_CHANGE_REASONS')
 changes=[{'symbol':k,'kind':kind,'before':old.get(k),'after':current.get(k),'reason':reasons[k]} for kind,items in [('ADDED',added),('REMOVED',removed),('CHANGED',changed)] for k in items]
 result={'schema':'DATED_FREEZE_LINEAGE_V1','version':version,'business_date':reg['business_date'],'source_date':reg['source_date'],'cutoff':reg['cutoff'],'parent_identity':parent_identity,'row_sha256':current,'changes':changes}
 result['identity']=sha(canonical(result))
 return result

def calculate(reg,policy,docs,safe):
 node=reg['node']
 if node=='freeze':
  panel=docs['panel']
  if panel['source_date']!=reg['source_date'] or panel['scope_count']!=policy['panel_denominator']:raise ValueError('PANEL_DATE_SCOPE')
  audit=module('crosscheck',safe).audit(panel,reg['business_date'])
  semantic=semantic_compare(docs['multi_source'],policy,time(reg['cutoff']))
  if audit['errors'] or not semantic['passed']:return {'status':'BLOCKED_SOURCE_REVIEW','row_audit':audit,'semantic_review':semantic,'formal_freeze':False}
  lineage=build_freeze_lineage(reg,policy,docs)
  return {'lineage':lineage,'status':'REVIEWED_FREEZE_MANIFEST_READY','row_audit':audit,'semantic_review':semantic,'formal_freeze':reg['domain']=='production','freeze_manifest':{'contract_sha256':contract_identity(reg),'business_date':reg['business_date'],'source_date':reg['source_date'],'scope_count':panel['scope_count'],'source_inputs':reg['inputs'],'review':reg['review'],'policy':reg['policy'],'missing_and_unknown_preserved':True}}
 if node=='jk-verify':
  if reg['source_date']!=reg['business_date']:raise ValueError('JK_CURRENT_DAY_REQUIRED')
  day=dt.datetime.strptime(reg['source_date'],'%Y%m%d').date().isoformat()
  timing=validate_jk_observations(docs['observations'],policy,time(reg['cutoff']))
  normalized,provenance,gaps=normalize_jk_semantics(docs['observations'],policy)
  if gaps:return {'status':'BLOCKED_MISSING_OR_CONFLICTING_SOURCE','value_gaps':gaps,'timing_review':timing,'source_admission':False,'collector_calls':0}
  result=module('jk',safe).reconcile(normalized,day)
  for comparison in result['comparisons']:
   evidence=provenance[(comparison['symbol'],comparison['field'])]
   comparison.pop('source_ids',None) # legacy field contained observation IDs, not providers
   comparison['provider_ids']=[x['provider_id'] for x in evidence]
   comparison['observation_ids']=[x['observation_id'] for x in evidence]
   comparison['raw_source_fields']=sorted({x['raw_field'] for x in evidence})
   comparison['semantic_provenance']=evidence
  result['identity_schema']='JK_PROVIDER_OBSERVATION_IDENTITIES_V1'
  result['source_independence']='DECLARED_BY_REVIEWED_POLICY_NOT_PROVED_BY_ID_STRINGS'
  expected={(x['symbol'],x['field']) for x in policy['required_comparisons']}
  actual={(x['symbol'],x['field']) for x in result['comparisons']}
  ok=actual==expected and all(x['status']=='OBSERVED_VALUES_AGREE' for x in result['comparisons'])
  return {'status':'RECONCILED' if ok else 'BLOCKED_MISSING_OR_CONFLICTING_SOURCE','observations':result,'timing_review':timing,'source_admission':False,'collector_calls':0}
 if node=='morning-delivery':
  if reg.get('domain')=='synthetic' and policy.get('assembly_schema')=='MORNING_0810_PREVIEW_V1':
   return assemble_morning_preview(reg,policy,docs)
  return {'status':'BLOCKED_DELIVERY_ASSEMBLY_NOT_BOUND','delivery_status':'NOT_SENT','source_calls':0,'business_accepted':False}
 # opening-prep ONLY creates names+prompt. 08:10 cannot fall through here.
 panel=docs['panel'];top=docs['top']
 if str(top['source_date'])!=reg['source_date'] or panel['source_date']!=reg['source_date']:raise ValueError('TOP_PANEL_DATE')
 if top['schema']!=policy['top_schema']:raise ValueError('TOP_SCHEMA_POLICY')
 if top['schema']=='DATED_FIXED_REFERENCE_TOP200_V1':
  # Explicit pinned daily scope input; never relabel a new pool as the Nov6 5575 pool.
  rows=module('prep',safe).annotate_dated(top,panel,docs['pool_scope'])
 elif top['schema']=='NOV6_FIXED_REFERENCE_TOP200_V1':
  rows=module('prep',safe).annotate(top,panel)
 else:raise ValueError('TOP_SCHEMA_UNSUPPORTED')
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
CODE_BINDINGS_SHA='f291a8c87611625e05c37c6b11c0f996488b83a004f18f742835311922f7383e'

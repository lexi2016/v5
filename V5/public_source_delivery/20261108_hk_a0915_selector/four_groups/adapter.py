"""Explicit reviewed-date adapter for recovered physical-Par four-group consumer.
Original formulas/admission/physical reader/history functions remain AST-identical.
No trusted registration or current-date input is created by this module.
"""
import ast,copy,datetime,hashlib,json,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
SOURCE='handoff/portable_nov6_selector_v3_20261106/portable_nov6_selector.py'
SOURCE_SHA='0c5101c9ce12435b700564aa12ec461469eccffa5a37138744c0d2d2dfca13c4'

def need(v,msg):
 if not v:raise ValueError(msg)
def checked(pin):
 p=ROOT/pin['path'];need(not Path(pin['path']).is_absolute()and p.resolve()==p and p.is_relative_to(ROOT),'REF_SCOPE')
 before=p.stat();need(0<before.st_size==pin['bytes']<=16*1024**2,'REF_SIZE');raw=p.read_bytes();after=p.stat()
 need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'REF_CHANGED')
 need(hashlib.sha256(raw).hexdigest()==pin['sha256'],'REF_SHA');return raw
def ref(p):
 p=Path(p);need(p.resolve()==p and p.is_relative_to(ROOT) and 0<p.stat().st_size<=16*1024**2,'REF_SCOPE_SIZE');raw=p.read_bytes();pin={'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()};checked(pin);return pin
def day(n):
 need(type(n)is int,'DATE_TYPE');datetime.datetime.strptime(str(n),'%Y%m%d');return n

def validate_calendar(calendar,target,observation):
 need(calendar.get('status')=='VERIFIED_CURRENT_SESSION_CALENDAR' and calendar.get('reviewer_role')=='independent_reviewer','INDEPENDENT_CALENDAR')
 need((calendar['target_date'],calendar['observation_date'])==(day(target),day(observation))and calendar['prior_date']<target<observation,'EXACT_SESSION_BINDING')
 need(calendar.get('evidence_refs'),'CALENDAR_EVIDENCE_REQUIRED')

def _clone(target,observation,provenance):
 """Private compilation; callers cannot use it as admission. No Runtime starts."""
 day(target);day(observation);need(target<observation,'DATE_ORDER')
 raw=(ROOT/SOURCE).read_bytes();need(hashlib.sha256(raw).hexdigest()==SOURCE_SHA,'ORIGINAL_SELECTOR_PIN')
 tree=ast.parse(raw);original=copy.deepcopy(tree);counts={'dates':0,'home':0,'manifest':0,'main_removed':0}
 body=[]
 for n in tree.body:
  if isinstance(n,ast.If)and ast.unparse(n.test)=="__name__ == '__main__'":counts['main_removed']+=1;continue
  if isinstance(n,ast.Assign)and len(n.targets)==1:
   if isinstance(n.targets[0],ast.Tuple)and [x.id for x in n.targets[0].elts]==['TARGET','OBSERVATION']:
    n.value=ast.Tuple(elts=[ast.Constant(target),ast.Constant(observation)],ctx=ast.Load());counts['dates']+=1
   elif isinstance(n.targets[0],ast.Name)and n.targets[0].id=='HERE':
    n.value=ast.Call(func=ast.Name(id='Path',ctx=ast.Load()),args=[ast.Constant(str(HERE))],keywords=[]);counts['home']+=1
  body.append(n)
 tree.body=body
 # Only final output's identifying metadata changes; calculation calls unchanged.
 for n in ast.walk(tree):
  if isinstance(n,ast.Dict):
   keys=[k.value if isinstance(k,ast.Constant)else None for k in n.keys]
   if 'schema' in keys:
    i=keys.index('schema')
    if isinstance(n.values[i],ast.Constant)and n.values[i].value=='NOV6_PHYSICAL_PAR_ORIGINAL_FOUR_GROUP_SELECTION_V1':
     n.keys.append(ast.Constant('dated_adapter_provenance'));n.values.append(ast.parse(repr(provenance),mode='eval').body);counts['manifest']+=1
 need(counts==dict(dates=1,home=1,manifest=1,main_removed=1),'EXPECTED_AST_SITES')
 # Every function/class other than run is verbatim AST. run differs only by the
 # added provenance field; retain original schema/status for reader compatibility,
 # with explicit dated_adapter_provenance rather than claim those labels are new.
 old={n.name:ast.dump(n,include_attributes=False)for n in original.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name!='run'}
 new={n.name:ast.dump(n,include_attributes=False)for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name!='run'}
 need(old==new,'BUSINESS_AST_CHANGED')
 ast.fix_missing_locations(tree);m=types.ModuleType('private_dated_four_group');m.__file__=str(ROOT/SOURCE)
 exec(compile(tree,str(ROOT/SOURCE)+'::dated_binding','exec'),m.__dict__)
 return m,counts

def bind(binding_ref,review_ref):
 binding=json.loads(checked(binding_ref));review=json.loads(checked(review_ref))
 need(binding.get('schema')=='DATED_FOUR_GROUP_BINDING_V1','BINDING_SCHEMA')
 calendar=json.loads(checked(binding['calendar_review_ref']));validate_calendar(calendar,binding['target_date'],binding['observation_date'])
 for pin in calendar['evidence_refs']:checked(pin)
 need(review.get('status')=='PASS_DATED_FOUR_GROUP_ADAPTER_AND_BINDING'and review.get('reviewer_role')=='independent_reviewer'and review.get('binding_ref')==binding_ref,'ADAPTER_INDEPENDENT_REVIEW')
 need(review.get('adapter_ref')==ref(Path(__file__))and review.get('original_selector_ref')==ref(ROOT/SOURCE),'EXACT_ADAPTER_CODE_REVIEW')
 manifest=json.loads(checked(binding['owner_manifest_ref']));started=json.loads(checked(binding['owner_started_ref']));contract=json.loads(checked(started['contract_ref']))
 need(started['target_date']==manifest['target_date']==contract['target_date']==binding['target_date'] and contract['observation_date']==binding['observation_date'],'OWNER_DATE_BINDING')
 # Original admission still verifies exact owner namespace, frozen codes, reviews,
 # source, history closure, physical schema, full5575 and actual calendar_for.
 output_review=json.loads(checked(binding['output_review_ref']))
 need(output_review['owner_manifest_ref']==binding['owner_manifest_ref'],'OUTPUT_REVIEW_BINDING')
 provenance=dict(binding_ref=binding_ref,adapter_review_ref=review_ref,adapter_ref=ref(Path(__file__)),original_selector_ref=ref(ROOT/SOURCE),calendar_review_ref=binding['calendar_review_ref'],target_date=binding['target_date'],observation_date=binding['observation_date'],schema_labels='ORIGINAL_NOV6_SCHEMA_RETAINED_FOR_COMPATIBILITY_NOT_FIXED_DATE_AUTHORITY')
 m,delta=_clone(binding['target_date'],binding['observation_date'],provenance)
 m.validate_output_review(output_review,binding['owner_manifest_ref'],started['review_ref'])
 for pin in output_review['sample_evidence_refs']+output_review['code_refs']:checked(pin)
 # Revalidate additional dated pins before every original checked() read.
 original_checked=m.checked
 extra=(binding_ref,review_ref,binding['calendar_review_ref'],*calendar['evidence_refs'])
 def guarded_checked(pin,limit=16*1024**2):
  for extra_pin in extra:checked(extra_pin)
  return original_checked(pin,limit)
 m.checked=guarded_checked
 return m,binding,delta

def verify_existing_terminal(doc,binding):
 need(doc.get('schema')=='NOV6_PHYSICAL_PAR_ORIGINAL_FOUR_GROUP_SELECTION_V1' and doc.get('status')=='NOV6_RESEARCH_SELECTION_COMPLETE_WITH_EXPLICIT_COVERAGE' and doc.get('test_only') is False,'EXISTING_REAL_TERMINAL')
 need(doc.get('scope_count')==5575 and doc.get('calculation_date')==binding['target_date'] and doc.get('observation_date')==binding['observation_date'],'EXISTING_DATES_SCOPE')
 for key in ('owner_manifest_ref','owner_started_ref','output_review_ref'):need(doc.get(key)==binding[key],'EXISTING_BINDING_'+key)
 started=json.loads(checked(binding['owner_started_ref']))
 need(doc.get('source_review_ref')==started['review_ref'] and doc.get('contract_ref')==started['contract_ref'],'EXISTING_SOURCE_BINDING')
 contract=json.loads(checked(started['contract_ref']));catalog=json.loads(checked(contract['prior_catalog_ref']))
 authoritative=[row['symbol']for row in catalog['latest_selections']]
 need(len(authoritative)==len(set(authoritative))==5575,'EXISTING_AUTHORITATIVE_SCOPE');authoritative=set(authoritative)
 counts=json.loads(checked(doc['counts_ref']))
 for key in ('scope_count','counts','dedup_selected','dedup_pending'):need(counts.get(key)==doc.get(key),'EXISTING_COUNTS_'+key)
 pin=doc['output_ref'];path=ROOT/pin['path'];need(not Path(pin['path']).is_absolute() and path.resolve()==path and path.is_relative_to(ROOT),'EXISTING_OUTPUT_SCOPE')
 before=path.stat();need(0<before.st_size==pin['bytes']<=64*1024**2,'EXISTING_OUTPUT_SIZE')
 sha=hashlib.sha256();size=0;symbols=set()
 with path.open('rb')as stream:
  for line in stream:
   need(len(line)<=65536,'EXISTING_ROW_LIMIT');sha.update(line);size+=len(line);row=json.loads(line)
   need(row.get('test_only') is False and row['symbol'] in authoritative and row['symbol'] not in symbols and row.get('calculation_date')==binding['target_date'] and row.get('observation_date')==binding['observation_date'],'EXISTING_ROW_IDENTITY')
   symbols.add(row['symbol']);need(len(symbols)<=5575,'EXISTING_OUTPUT_DENOMINATOR')
 after=path.stat();need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'EXISTING_OUTPUT_CHANGED')
 need(symbols==set(authoritative) and size==pin['bytes'] and sha.hexdigest()==pin['sha256'],'EXISTING_OUTPUT_PIN_DENOMINATOR')
 # This is byte/metadata reuse verification, not a new physical Parquet read or
 # invocation of native-dependent Runtime/admission. Never labels it new business.
 return True

def run(binding_ref,review_ref):
 m,binding,delta=bind(binding_ref,review_ref)
 # Historical successes are reused, not evaluated under a new output name.
 for folder in (ROOT/Path(SOURCE).parent/'runs',HERE/'runs'):
  if folder.exists():
   entries=list(folder.iterdir());need(len(entries)<=4096,'ATTEMPT_SCAN_CAP')
   for attempt in entries:
    terminal=attempt/'MANIFEST.json'
    if terminal.is_file():
     terminal_pin=ref(terminal);doc=json.loads(checked(terminal_pin))
     if doc.get('owner_manifest_ref')==binding['owner_manifest_ref']:
      need(doc.get('calculation_date')==binding['target_date'],'EXISTING_RESULT_DATE_CONFLICT')
      need(doc.get('status')=='NOV6_RESEARCH_SELECTION_COMPLETE_WITH_EXPLICIT_COVERAGE' and doc.get('scope_count')==5575 and doc.get('test_only') is False,'EXISTING_RESULT_NOT_REAL_TERMINAL')
      need(doc.get('output_review_ref')==binding['output_review_ref'] and doc.get('output_ref') and doc.get('counts_ref'),'EXISTING_RESULT_EVIDENCE_BINDING')
      verify_existing_terminal(doc,binding)
      return dict(status='REUSE_EXISTING_SELECTION_NO_RECOMPUTE',existing_manifest_ref=ref(terminal),business_acceptance='HISTORICAL_NOT_CURRENT_NATURAL')
 # Fixed identity means reawakening cannot invent another candidate output path.
 name='run_'+str(binding['target_date'])+'_'+binding['owner_manifest_ref']['sha256'][:16]
 need(not(HERE/'runs'/name).exists(),'EXISTING_ATTEMPT_INSPECT_NO_RETRY')
 return m.run(binding['owner_manifest_ref'],binding['output_review_ref'],name,False)

"""Controlled dated G4/GBBQ capture-convert and reviewed source-prepare stages.
No unknown legacy lock substitution. No automatic actual-source review bypass.
"""
import argparse,ast,contextlib,datetime,hashlib,json,os,pathlib,re,sys,types
ROOT=None;BASE=None;LEGACY=None;CHAIN_FILE=None;CHAIN_SHA=None
PREPARE_FILE=None;PREPARE_SHA=None;RUNTIME_NAMESPACE=None

def need(ok,reason):
 if not ok:raise ValueError(reason)

def load_source_chain():
 need(all(isinstance(p,pathlib.Path) and p.is_absolute() for p in (ROOT,BASE,LEGACY,CHAIN_FILE,PREPARE_FILE)) and all(isinstance(x,str) and len(x)==64 for x in (CHAIN_SHA,PREPARE_SHA)) and isinstance(RUNTIME_NAMESPACE,str) and bool(RUNTIME_NAMESPACE),'NO_APPROVED_PRIVATE_BINDING')
 need(not pathlib.Path(RUNTIME_NAMESPACE).is_absolute() and '..' not in pathlib.Path(RUNTIME_NAMESPACE).parts,'RUNTIME_NAMESPACE')
 for p in (BASE,CHAIN_FILE,PREPARE_FILE):need(p.resolve().is_relative_to(ROOT.resolve()) and p.resolve()==p,'BOUND_SOURCE_PATH')
 need(ROOT.resolve()==ROOT and LEGACY.resolve()==LEGACY,'ROOT_OR_LEGACY_IDENTITY')
 raw=CHAIN_FILE.read_bytes();need(hashlib.sha256(raw).hexdigest()==CHAIN_SHA,'SOURCE_CHAIN_PIN')
 module=types.ModuleType('approved_source_chain');module.__file__=str(CHAIN_FILE)
 sys.path.insert(0,str(CHAIN_FILE.parent))
 try:exec(compile(raw,str(CHAIN_FILE),'exec'),module.__dict__)
 finally:sys.path.pop(0)
 return module

def file_ref(reader,path):
 p=pathlib.Path(path);p=p if p.is_absolute()else ROOT/p;b=p.read_bytes()
 pin={'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};reader.checked(pin);return pin

def bind(binding_ref):
 reader,dependencies,_=load_source_chain().bind();binding=json.loads(reader.checked(binding_ref))
 def checked_dependency(path):
  refs=[r for r in dependencies if r['path']==str(pathlib.Path(path).relative_to(ROOT))];need(len(refs)==1,'DEPENDENCY_PIN_IDENTITY');return reader.checked(refs[0])
 need(binding.get('schema')=='DATED_CAPTURE_CONVERT_BINDING_V1','BINDING_SCHEMA')
 calendar=json.loads(reader.checked(binding['calendar_review_ref']))
 need(calendar.get('status')=='VERIFIED_CURRENT_SESSION_CALENDAR' and calendar.get('reviewer_role')=='independent_reviewer','CALENDAR_REVIEW')
 p,d,n=[calendar[k]for k in ('prior_date','target_date','observation_date')]
 need(all(type(x)is int for x in (p,d,n)) and p<d<n,'DATE_ORDER')
 for x in (p,d,n):datetime.datetime.strptime(str(x),'%Y%m%d')
 need(calendar.get('evidence_refs'),'CALENDAR_EVIDENCE')
 for ref in calendar['evidence_refs']:reader.checked(ref)
 need(binding.get('target_date')==d,'TARGET_BINDING')
 # A clone namespace leaves all existing modules and archived code unchanged.
 cap=types.ModuleType('dated_private_capture');cap.__file__=str(BASE/'isolated_capture.py')
 exec(compile(checked_dependency(cap.__file__),cap.__file__,'exec'),cap.__dict__)
 cap.CATALOG_PIN=binding['prior_catalog_ref'];cap.NAMESPACE=RUNTIME_NAMESPACE+'/'+str(d)+'/'+binding_ref['sha256']
 original=cap.Capture;runner_pin=file_ref(reader,__file__)
 cap._migration_verifier=None;cap._initializing=False
 class Capture(original):
  def initialize(self):
   need(not cap._initializing,'NESTED_MIGRATION_INITIALIZATION')
   cap._initializing=True
   try:return super().initialize()
   finally:cap._initializing=False
  @contextlib.contextmanager
  def locks(self):
   need(cap._migration_verifier is None,'NESTED_MIGRATION_LOCK_CONTEXT')
   with super().locks()as(verify,init_pin):
    verify();cap._migration_verifier=verify
    try:yield verify,init_pin
    finally:cap._migration_verifier=None
  def catalog(self,target):
   need(target==d,'CAPTURE_TARGET_BINDING');doc=json.loads(self.reader.checked(cap.CATALOG_PIN))
   need(doc.get('target_date')==p and doc.get('issues')==[],'PRIOR_CATALOG')
   rows=doc['latest_selections'];symbols=[r['symbol']for r in rows]
   need(len(rows)==len(set(symbols))==5575 and all(re.fullmatch(r'\d{6}\.(SH|SZ|BJ)',s)for s in symbols),'FIXED5575')
   for row in rows:need(cap.portable.date_value(row['event_date'])<=p,'PRIOR_FUTURE_ROW')
   return dict(cap.CATALOG_PIN),doc
  def code_pins(self):return [*super().code_pins(),runner_pin,binding_ref,binding['calendar_review_ref']]
 cap.Capture=Capture
 converter=types.ModuleType('dated_private_conversion');converter.__file__=str(BASE/'isolated_g4_ledger.py');converter.cap=cap
 tree=ast.parse(checked_dependency(converter.__file__))
 imports=[x for x in tree.body if isinstance(x,ast.Import) and any(a.name=='isolated_capture'for a in x.names)]
 need(len(imports)==1,'EXACT_CAPTURE_IMPORT');tree.body.remove(imports[0]);ast.fix_missing_locations(tree)
 exec(compile(tree,converter.__file__+'::private_cap','exec'),converter.__dict__)
 return reader,binding,calendar,cap,converter

@contextlib.contextmanager
def original_locks(cap,binding,reader):
 # Existing original path/domain only; no mkdir, no empty replacement files.
 lock_reader=cap.portable.ReferenceReader(LEGACY)
 review=json.loads(reader.checked(binding['original_lock_binding_review_ref']))
 need(review.get('status')=='PASS_EXISTING_ORIGINAL_LOCK_DOMAIN_BINDING' and review.get('reviewer_role')=='independent_reviewer' and review.get('root')==str(LEGACY),'ORIGINAL_LOCK_DOMAIN_REVIEW')
 expected=review.get('locks');need(type(expected)is list and [x['path']for x in expected]==list(cap.portable.LOCKS),'ORIGINAL_LOCK_SET')
 with cap.portable.existing_locks(lock_reader)as verify:
  def checked():
   verify();reader.checked(binding['original_lock_binding_review_ref'])
   for row in expected:
    with lock_reader.open_existing(row['path'])as(fd,path,st):need([st.st_dev,st.st_ino]==row['identity'],'ORIGINAL_LOCK_BOUND_IDENTITY')
  checked();yield checked;checked()

def window(cal,now):
 d,n=cal['target_date'],cal['observation_date'];need(now.tzinfo is not None,'CLOCK_ZONE')
 local=now.astimezone(datetime.timezone(datetime.timedelta(hours=8)))
 close=datetime.datetime.strptime(str(d),'%Y%m%d').replace(hour=15,minute=30,tzinfo=local.tzinfo)
 need(d<=int(now.astimezone(datetime.timezone.utc).strftime('%Y%m%d'))<=n and local>=close,'TARGET_SESSION_NOT_CLOSED_OR_OUTSIDE_WINDOW')

def install_guarded_writes(cap,reader,verify_original,phase):
 original_measure=cap.measure_resources
 def measure(root):verify_original();return original_measure(root)
 cap.measure_resources=measure
 base_write=cap.new_json
 def guarded_json(fd,name,value):
  verify_original();mem,disk=measure(ROOT)
  need(cap.portable.resource_check(phase[0],mem,disk,source_kind=phase[1])['passed'],'RECEIPT_RESOURCE_GATE')
  path=pathlib.Path(os.readlink('/proc/self/fd/'+str(fd)))
  need(path.is_relative_to(ROOT),'RECEIPT_DIRECTORY_SCOPE')
  def verify_migration():
   callback=cap._migration_verifier
   if callback is not None:
    need(not cap._initializing,'LOCK_STATE_CONFLICT');callback();return
   # Only initialization files before flock are allowed, never a run receipt.
   need(cap._initializing and path==ROOT/cap.NAMESPACE,'MIGRATION_LOCK_NOT_HELD')
   expected_schema='NEW_MIGRATION_NAMESPACE_V1'if name=='INITIALIZED.json'else'NEW_MIGRATION_LOCK_V1'
   need(name in (*cap.LOCK_NAMES,'INITIALIZED.json') and value.get('schema')==expected_schema and value.get('scope')==cap.SCOPE,'INITIALIZATION_WRITE_ONLY')
  verify_migration()
  with cap.directory(reader,str(path.relative_to(ROOT)))as(reopened,verify_dir):
   need(cap.identity(os.fstat(fd))==cap.identity(os.fstat(reopened)),'RECEIPT_DIRECTORY_IDENTITY')
   verify_migration();verify_dir();base_write(fd,name,value);verify_dir();verify_migration()
  verify_original()
 cap.new_json=guarded_json

def run(binding_ref,stage,*,capture_review=None,conversion_review=None,prepare_config=None,prepare_review=None):
 reader,binding,calendar,cap,converter=bind(binding_ref)
 need(stage in ('capture_convert','prepare'),'STAGE')
 window(calendar,cap.now())
 # Fail before network/write if original legacy lock domain is unavailable.
 with original_locks(cap,binding,reader)as verify_original:
  phase=['prepare',None];install_guarded_writes(cap,reader,verify_original,phase)
  if stage=='capture_convert':
   capture=cap.Capture(ROOT);convert=converter.Converter(ROOT);results={}
   # Both code reviews bound to runner, explicit calendar/catalog and namespace.
   capture.reviewed_inputs(capture_review);convert.reviewed(conversion_review)
   for kind in ('g4','gbbq'):
    phase[:]=['capture',kind];verify_original();fetched=capture.capture(kind,calendar['target_date'],calendar['observation_date'],capture_review)
    need(fetched['receipt']['status']=='FETCHED_NOT_ADMITTED','CAPTURE_FAILED_STOP_NO_CONVERSION')
    phase[:]=['prepare',None]
    converted=convert.convert(kind,fetched['receipt_ref'],conversion_review);need(converted['receipt']['status']=='CONVERTED_PENDING_INDEPENDENT_REVIEW','CONVERSION_FAILED_STOP');results[kind]={'fetch':fetched,'conversion':converted}
   verify_original()
   return {'status':'CAPTURE_CONVERTED_PENDING_INDEPENDENT_ACTUAL_SOURCE_REVIEW','target_date':calendar['target_date'],'results':results,'prepare_called':False,'source_admission':False,'natural_run_verified':False}
  need(prepare_config and prepare_review,'PREPARE_SOURCE_AND_INDEPENDENT_REVIEW_REQUIRED')
  config=json.loads(reader.checked(prepare_config))
  need(config.get('calendar_review_ref')==binding['calendar_review_ref'] and config.get('prior_catalog_ref')==binding['prior_catalog_ref'],'PREPARE_BINDING')
  for key,kind in [('g4_conversion_ref','g4'),('gbbq_conversion_ref','gbbq')]:
   need(config[key]['path']==cap.NAMESPACE+'/conversions/'+str(calendar['target_date'])+'/'+kind+'/CONVERSION_RECEIPT.json','PREPARE_CONVERSION_CHAIN')
   reader.checked(config[key])
  path=PREPARE_FILE
  raw=reader.checked(file_ref(reader,path));need(hashlib.sha256(raw).hexdigest()==PREPARE_SHA,'PREPARE_V2_PIN')
  module=types.ModuleType('dated_reviewed_preparation');module.__file__=str(path);exec(compile(raw,str(path),'exec'),module.__dict__)
  _,v3,prepared_reader=module.runtime();module.runtime=lambda:(cap,v3,prepared_reader)
  verify_original();result=module.execute(prepare_config,prepare_review);verify_original();return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--binding',required=True);p.add_argument('--stage',required=True,choices=['capture_convert','prepare'])
 for key in ('capture-review','conversion-review','prepare-config','prepare-review'):p.add_argument('--'+key)
 a=p.parse_args()
 reader,_,_=load_source_chain().bind();kwargs={key:file_ref(reader,getattr(a,key))if getattr(a,key)else None for key in ('capture_review','conversion_review','prepare_config','prepare_review')};print(json.dumps(run(file_ref(reader,a.binding),a.stage,**kwargs),ensure_ascii=False,indent=2))

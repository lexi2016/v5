"""Reviewed adapter wiring; browser only inspects. Trusted runner selects frozen registration.
Empty registration is deliberate: strings/files supplied by browser cannot grant authority.
Original adapters retain their own resource, lock, source and reconciliation gates.
"""
import json,types,threading,pathlib,subprocess,sys,builtins
from workflow_node_api import checked
ROOT=None;ADAPTER_BINDINGS=None
# Only code-reviewed release binding may populate this. No request or JSON mutates it.
TRUSTED_RUNS=()
LOCK=threading.Lock()
def bindings():
 if not isinstance(ROOT,pathlib.Path) or not ROOT.is_absolute() or not isinstance(ADAPTER_BINDINGS,dict) or not ADAPTER_BINDINGS:raise ValueError('NO_APPROVED_EXECUTION_BINDING')
 return ADAPTER_BINDINGS
def inspect(node):
 entry=bindings()[node];checked(entry['code'])
 for dep in entry.get('dependencies',[]):checked(dep)
 for key in ('safeio','a0915'):
  if key in entry:checked(entry[key])
 return {'status':'BLOCKED_NO_TRUSTED_EXECUTOR_BINDING','node':node,'adapter_sha256':entry['code']['sha256'],'scope':entry['scope'],'adapter_code_verified':True,'browser_execution_enabled':False,'business_accepted':False,'natural_verified':False,'source_calls':0,'required':['trusted run/environment registration','actual source/config and independent admission','original resource/locks and owner reconciliation']+entry.get('required',[]),'qualification':'Adapter code connected; inspection does not execute it. Missing trusted binding is not a pending successful job.'}
def load(pin):
 raw=checked(pin);m=types.ModuleType('controlled_original_adapter');m.__file__=str(ROOT/pin['path']);exec(compile(raw,m.__file__,'exec'),m.__dict__);return m

def dispatch(node,run_id,environment_id,gate):
 """Trusted process-only interface. No caller-provided contract/config/argv/clock."""
 if not callable(gate):raise ValueError('ORIGINAL_RESOURCE_GATE_REQUIRED')
 if node not in bindings():raise ValueError('NODE_NOT_CONTROLLED')
 matches=[r for r in TRUSTED_RUNS if r['node']==node and r['run_id']==run_id and r['environment_id']==environment_id]
 if len(matches)!=1:return inspect(node)
 registration=matches[0];entry=bindings()[node]
 if registration['adapter_sha256']!=entry['code']['sha256']:raise ValueError('EXECUTOR_CODE_BINDING_CHANGED')
 if not LOCK.acquire(timeout=95):raise ValueError('RESOURCE_BUSY')
 try:
  if hasattr(gate,'start'):gate.start()
  gate()
  if node in {'a-auction-close','a-open'}:
   return dispatch_m07(node,registration,entry,gate)
  if node in {'night','morning-materials','a-top200','a-auction'}:
   return dispatch_remaining(node,registration,entry,gate)
  if node.startswith('evening-'):
   return dispatch_evening(node,registration,entry,gate)
  if node=='daily-update':
   return dispatch_daily_capture(registration,entry,gate)
  module=load(entry['code'])
  if node in {'freeze','jk-verify','morning-delivery','opening-prep'}:result=module.execute(node,gate,mode=registration['mode'])
  elif node in {'hk-open','hk-continuous-close','hk-auction-final'}:result=module.dispatch(node,registration['run_key'])
  elif node=='us-close':result=module.dispatch(registration['automation_id'],run_id,environment_id)
  else:result=module.invoke(node,registration['contract_ref'],execute=node!='terminal-1700')
  # Preserve original result; no invented completion or retry on failure.
  return {'node':node,'run_id':run_id,'environment_id':environment_id,'adapter_scope':entry['scope'],'result':result,'natural_verified':False,'business_accepted':False}
 finally:LOCK.release()

def dispatch_m07(node,registration,entry,gate):
 """Original CLI in isolated interpreter; exact stage and original natural refusal preserved."""
 checked(entry['code'])
 for dep in entry['dependencies']:checked(dep)
 request=registration['request']
 if request['stage_id']!=entry['stage']:raise ValueError('M07_NODE_STAGE_BINDING')
 message={'request':request,'output_root':registration['output_root']}
 raw=json.dumps(message).encode()
 if len(raw)>1024*1024:raise ValueError('M07_MESSAGE_BOUND')
 script=str(ROOT/entry['code']['path']);gate()
 try:
  process=subprocess.run([sys.executable,'-I','-B',script,'--run'],input=raw,capture_output=True,timeout=150)
  if len(process.stdout)>16*1024*1024:raise ValueError('M07_RESPONSE_BOUND')
  result=json.loads(process.stdout)
 except (subprocess.TimeoutExpired,ValueError,OSError) as error:
  return {'node':node,'status':'OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY','reason':type(error).__name__,'business_accepted':False,'natural_verified':False}
 # Never retry or convert SUCCEEDED replay into natural/business acceptance.
 return {'node':node,'run_id':registration['run_id'],'environment_id':registration['environment_id'],'adapter_scope':entry['scope'],'returncode':process.returncode,'result':result,'business_accepted':False,'natural_verified':False,'readback_scope':'ORIGINAL_RUN_ENTRY_INCLUDES_INDEPENDENT_COLD_READ'}

def dispatch_evening(node,registration,entry,gate):
 """Original fixed historical export only; no rollover, selection or actual sending."""
 if registration.get('source_date')!=entry['source_date']:raise ValueError('EVENING_HISTORICAL_SCOPE')
 safe=types.ModuleType('fixed_bundle_safeio');exec(compile(checked(entry['safeio']),entry['safeio']['path'],'exec'),safe.__dict__)
 module=types.ModuleType('fixed_evening_bundle');module.__file__=str(ROOT/entry['code']['path'])
 imports=dict(vars(builtins));original=builtins.__import__;imports['__import__']=lambda name,*a,**kw:safe if name=='safeio' else original(name,*a,**kw);module.__dict__['__builtins__']=imports
 exec(compile(checked(entry['code']),module.__file__,'exec'),module.__dict__);gate()
 result=module.prepare() if node=='evening-prepare' else module.check(registration['package_id'])
 return {'node':node,'run_id':registration['run_id'],'result':result,'source_date':entry['source_date'],'business_accepted':False,'natural_verified':False,'delivery_status':'NOT_SENT','qualification':entry['scope']}

def dispatch_remaining(node,registration,entry,gate):
 """Local imports pinned independently, date exclusively from trusted release registration."""
 modules={};original=builtins.__import__
 for key in ('safeio','a0915','code'):
  pin=entry[key];module=types.ModuleType('fixed_remaining_'+key);module.__file__=str(ROOT/pin['path'])
  imports=dict(vars(builtins));imports['__import__']=lambda name,*a,**kw:modules[name] if name in modules else original(name,*a,**kw)
  module.__dict__['__builtins__']=imports
  exec(compile(checked(pin),module.__file__,'exec'),module.__dict__);modules[key]=module
 result=modules['code'].execute(node,registration['target_date'],gate)
 return {'node':node,'run_id':registration['run_id'],'environment_id':registration['environment_id'],'result':result,'natural_verified':False,'business_accepted':False,'qualification':entry['scope']}

def dispatch_daily_capture(registration,entry,gate):
 """One explicitly registered stage per call; never self-generates source review."""
 stage=registration.get('stage')
 needed={'capture_convert':('capture_review','conversion_review'),'prepare':('prepare_config','prepare_review')}
 if stage not in needed or not registration.get('binding_ref') or any(not registration.get(k) for k in needed.get(stage,())):
  return {'node':'daily-update','status':'BLOCKED_DATED_BINDING_STAGE_OR_INDEPENDENT_REVIEW','source_admission':False,'natural_verified':False,'business_accepted':False,'pipeline_called':False}
 module=load(entry['code']);gate()
 kwargs={key:registration[key] for key in needed[stage]}
 result=module.run(registration['binding_ref'],stage,**kwargs)
 return {'node':'daily-update','run_id':registration['run_id'],'environment_id':registration['environment_id'],'stage':stage,'result':result,'automatic_next_stage':False,'source_admission':False,'natural_verified':False,'business_accepted':False,'qualification':entry['scope']}

"""Default original owner → private immutable capsule → independent cold reader.

All roots and config pins are operator bindings. HTTP consumers only see opaque
run identities. No implicit regeneration, replacement, provider or clock override.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from .intraday_capsule import IntradayCapsuleStore,M11Slot,_date,_root,_digest,_encoded
from .owner_sources import SOURCE_PIN,OWNER_ROOT,V5,safe_root_class,verify_sources,implementation_sha256,BUILD_MANIFEST_SHA


def _sha(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):raise ValueError('M11_SHA_INVALID')
    return value


def _time(value):
    if not isinstance(value,str):raise ValueError('M11_TIME_UNKNOWN')
    stamp=datetime.fromisoformat(value)
    if stamp.tzinfo is None:raise ValueError('M11_TIME_UNBOUND')
    return stamp


def validate_availability(sources,cutoff):
    limit=_time(cutoff)
    if not isinstance(sources,list) or not sources:raise ValueError('M11_SOURCE_AVAILABILITY_UNKNOWN')
    for source in sources:
        if not isinstance(source,dict):raise ValueError('M11_SOURCE_RECORD_INVALID')
        available=_time(source.get('available_at'))
        if available>limit:raise ValueError('M11_SOURCE_LATE')
        for key in ('event_time','published_at','observed_at'):
            if key not in source:raise ValueError('M11_SOURCE_TIME_UNKNOWN')
            if _time(source[key])>available:raise ValueError('M11_SOURCE_TIME_ORDER')
    return True


@dataclass(frozen=True)
class M11Binding:
    state_root: Path
    archive_root: Path
    config_path: Path
    config_sha256: str
    owner_manifest_sha256: str

    def validate(self):
        state=_root(self.state_root); archive=_root(self.archive_root); config=_root(self.config_path)
        if config==archive or archive in config.parents:
            raise ValueError('M11_CONFIG_OUTPUT_OVERLAP')
        for a,b in ((state,archive),(state,V5),(archive,V5)):
            if a==b or a in b.parents or b in a.parents:raise ValueError('M11_ROOT_OVERLAP')
        for root in (state,archive):
            marker=json.loads(safe_root_class()(root).read_bytes('.m11-private-root.json'))
            if marker!={'module':'M11','private':True,'schema':'v5.private_root.v1'}:raise ValueError('M11_PRIVATE_ROOT_REQUIRED')
        _sha(self.config_sha256);_sha(self.owner_manifest_sha256)
        if self.owner_manifest_sha256!=BUILD_MANIFEST_SHA:raise ValueError('M11_UNAPPROVED_BUILD_PIN')
        raw=safe_root_class()(config.parent).read_bytes(config.name)
        if hashlib.sha256(raw).hexdigest()!=self.config_sha256:raise ValueError('M11_CONFIG_SHA_MISMATCH')
        cfg=json.loads(raw)
        if cfg.get('state_root')!=str(state):raise ValueError('M11_STATE_BINDING_MISMATCH')
        for key in ('cache_root','cache_manifest_path','profile_path'):
            if key in cfg:
                p=_root(cfg[key])
                if p==archive or archive in p.parents or p in archive.parents:raise ValueError('M11_INPUT_OUTPUT_OVERLAP')
        verify_sources()
        return cfg

    def request(self,operation,day,slot=None):
        return {'operation':operation,'target_date':_date(day),'slot':slot,
                'state_root':str(self.state_root),'config_path':str(self.config_path),
                'config_sha256':self.config_sha256,'owner_manifest_sha256':self.owner_manifest_sha256}


def _worker(request,timeout=900):
    # -I ignores user site and PYTHONPATH. Only our explicit fixed source root is added.
    code='import sys;sys.path.insert(0,'+repr(str(V5/'src'))+');from v5_shadow.m11.owner_worker import main;main()'
    try:
        result=subprocess.run([sys.executable,'-I','-B','-c',code],input=json.dumps(request),text=True,
                              capture_output=True,timeout=timeout,check=False)
    except subprocess.TimeoutExpired:
        return {'status':'BLOCKED','error_code':'M11_OWNER_TIMEOUT','attempt_state':'ATTEMPT_UNKNOWN'}
    if result.returncode:
        return {'status':'BLOCKED','error_code':'M11_WORKER_EXIT','attempt_state':'ATTEMPT_UNKNOWN','exit_code':result.returncode}
    try:return json.loads(result.stdout)
    except (ValueError,TypeError):return {'status':'BLOCKED','error_code':'M11_WORKER_PROTOCOL','attempt_state':'ATTEMPT_UNKNOWN'}



def _execute_guarded(binding,request):
    """Durable process intent. Unknown crashes only reconcile; never reacquire."""
    io=safe_root_class()(binding.archive_root)
    key=_digest(request); path='executions/'+key+'.json'
    with io.kernel_lock('execution-locks/'+key+'.lock',timeout=930):
        try: previous=json.loads(io.read_bytes(path))
        except FileNotFoundError:previous=None
        except (ValueError,OSError):
            return {'status':'BLOCKED','error_code':'M11_EXECUTION_MARKER_INVALID','attempt_state':'ATTEMPT_UNKNOWN'}
        if previous is not None:
            if previous.get('phase')=='FINISHED':
                result=previous['result']
                if result.get('attempt_state')!='FAILED_NO_REQUEST':return result
            elif previous.get('phase')=='REQUEST_IN_FLIGHT':
                # Do not call capture/generate again. Only original cold read may reconcile.
                read=dict(request,operation='read_slot' if request['operation']=='capture' else 'read_daily')
                cold=_worker(read)
                if cold.get('status')!='BLOCKED':
                    if request['operation']=='capture':
                        result={'status':'OWNER_RETURNED','owner_result':{'status':'ALREADY_EXISTS',**cold['proof']}}
                    else:
                        result={'status':'OWNER_RETURNED','owner_result':{'status':'READY_FOR_REVIEW','artifact_sha256':cold['artifact_sha256']}}
                    io.write_bytes(path,_encoded({'phase':'FINISHED','result':result}))
                    return result
                return {'status':'BLOCKED','error_code':'M11_RECONCILIATION_REQUIRED','attempt_state':'ATTEMPT_UNKNOWN'}
            else:return {'status':'BLOCKED','error_code':'M11_EXECUTION_MARKER_INVALID','attempt_state':'ATTEMPT_UNKNOWN'}
        io.write_bytes(path,_encoded({'phase':'REQUEST_IN_FLIGHT'}))
        result=_worker(request)
        io.write_bytes(path,_encoded({'phase':'FINISHED','result':result}))
        return result


def read_owner_day(binding,day):
    binding.validate()
    return _worker(binding.request('read',day))


def _cold_capsule(root,identity):
    code='import sys,json;sys.path.insert(0,'+repr(str(V5/'src'))+');from v5_shadow.m11.intraday_capsule import IntradayCapsuleStore,M11Slot;d=json.load(sys.stdin);print(json.dumps(IntradayCapsuleStore(d["root"]).read_verified(M11Slot(**d["identity"]))))'
    p=subprocess.run([sys.executable,'-I','-B','-c',code],input=json.dumps({'root':str(root),'identity':identity.__dict__}),
                     text=True,capture_output=True,check=True,timeout=60)
    return json.loads(p.stdout)


def capture(binding,*,target_date,slot,cutoff,run_id,sources=None):
    binding.validate()
    stamp=_time(cutoff).astimezone(ZoneInfo('Asia/Shanghai'))
    if stamp.date().isoformat()!=target_date or slot not in ('09:25','09:35','10:00','11:30','14:00','15:00'):
        raise ValueError('M11_CUTOFF_IDENTITY')
    drift=stamp.hour*60+stamp.minute-int(slot[:2])*60-int(slot[3:])
    if not 0<=drift<=8:raise ValueError('M11_CUTOFF_WINDOW')
    initial=M11Slot(target_date,slot,cutoff,'capture',run_id,config_sha=binding.config_sha256,code_sha=implementation_sha256(),source_sha=binding.owner_manifest_sha256)
    initial.identity()
    validate_availability(sources,cutoff)
    request=binding.request('capture',target_date,slot)
    result=_execute_guarded(binding,request)
    store=IntradayCapsuleStore(binding.archive_root/'intraday')
    if result.get('status')=='BLOCKED':
        if result.get('attempt_state'):
            store.write_attempt(initial,result['attempt_state'],result['error_code'])
        return result
    original=result['owner_result']
    if original.get('status') not in ('SUCCEEDED','ALREADY_EXISTS'):
        return {'status':'CANNOT_CONFIRM','owner_result':original}
    cold=_worker(binding.request('read_slot',target_date,slot))
    if cold.get('status')=='BLOCKED':return cold
    for key in ('artifact_sha256','manifest_sha256','receipt_sha256'):
        if original.get(key)!=cold['proof'].get(key):raise ValueError('M11_OWNER_COLD_READ_MISMATCH')
    identity=M11Slot(target_date,slot,cutoff,'capture',run_id,input_sha=_digest({'owner_input':cold['owner_bundle']['input'],'source_times':sources}),
        config_sha=binding.config_sha256,code_sha=implementation_sha256(),source_sha=binding.owner_manifest_sha256)
    payload={'status':cold['intraday_research']['status'],'owner':cold,
        'availability':sources,'pit_status':'CANNOT_CONFIRM','source_times_validated':True,
        'natural_admission':'CANNOT_CONFIRM','production_allowed':False,'orders_sent':False,'buy_gate_updated':False}
    try:store.write_success(identity,payload,binding.owner_manifest_sha256)
    except FileExistsError:
        if store.read_verified(identity)!=payload:raise ValueError('M11_IDENTITY_COLLISION')
    if _cold_capsule(store.root,identity)!=payload:raise ValueError('M11_CAPSULE_COLD_READ_MISMATCH')
    return {'status':'COMMITTED','business_status':payload['status'],'identity':identity.__dict__,
            'pit_status':payload['pit_status'],'natural_admission':'CANNOT_CONFIRM','owner_result':original}


def generate(binding,*,target_date,cutoff,run_id,sources=None):
    binding.validate()
    if _time(cutoff).astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()!=target_date:raise ValueError('M11_CUTOFF_IDENTITY')
    validate_availability(sources,cutoff)
    result=_execute_guarded(binding,binding.request('generate',target_date))
    if result.get('status')=='BLOCKED':return result
    original=result['owner_result']
    cold=_worker(binding.request('read_daily',target_date))
    if cold.get('status')=='BLOCKED':return cold
    if cold['artifact_sha256']!=original.get('artifact_sha256'):raise ValueError('M11_DAILY_COLD_READ_MISMATCH')
    identity=M11Slot(target_date,'15:00',cutoff,'explicit-daily-generation',run_id,
        input_sha=_digest({'source':cold['owner_artifact'].get('source',{}),'source_times':sources}),config_sha=binding.config_sha256,
        code_sha=implementation_sha256(),source_sha=binding.owner_manifest_sha256)
    payload={'status':cold['research_review']['status'],'owner':cold,'availability':sources,
        'pit_status':'CANNOT_CONFIRM','source_times_validated':True,'natural_admission':'CANNOT_CONFIRM'}
    store=IntradayCapsuleStore(binding.archive_root/'daily')
    try:store.write_success(identity,payload,binding.owner_manifest_sha256)
    except FileExistsError:
        if store.read_verified(identity)!=payload:raise ValueError('M11_IDENTITY_COLLISION')
    if _cold_capsule(store.root,identity)!=payload:raise ValueError('M11_DAILY_CAPSULE_COLD_READ_MISMATCH')
    return {'status':'COMMITTED','identity':identity.__dict__,'business_status':payload['status'],'natural_admission':'CANNOT_CONFIRM'}

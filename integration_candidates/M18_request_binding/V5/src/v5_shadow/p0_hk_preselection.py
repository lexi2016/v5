"""Explicit P0 M06 registration; fixed original owner, separate exact ledgers."""
from datetime import datetime,timedelta,timezone
from functools import partial
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import stat
from pathlib import Path
import subprocess
import sys
import threading
import types
from .composition import no_symlinks,shadow_root
from .contracts import aware,exact_keys,sha,trade_date
from .digests import canonical_bytes,sha256_json,MAX_JSON_BYTES
from . import m06_readonly

LANE='hk_preselection'
TZ=timezone(timedelta(hours=8))
IDENTITIES=('code_sha256','config_sha256','dependency_sha256')
EVENING_CONTRACT='CLOSE_TO_NEXT_HK_SESSION_V1'
SEALED_POOL_SELECTION='REUSE_VERIFIED_OR_GENERATE_IF_ABSENT'
REQUEST_KEYS=('signal_date','target_date','eligibility_source_date','admission_cutoff','completion_cutoff',
    'files','source_files','execution_mode','production_method')


def _python_launch(registration):
    """Only a pinned venv's executable leaf is exempt from no_symlinks."""
    launch=Path(registration['python_executable']);environment=registration.get('python_venv')
    if environment is None:
        target=no_symlinks(launch);paths=[target]
    else:
        exact_keys(environment,('root','realpath','pyvenv_cfg_sha256','symlink_sha256'))
        root=no_symlinks(environment['root']);cfg=no_symlinks(root/'pyvenv.cfg')
        if (not launch.is_absolute() or '..' in launch.parts or launch.parent!=root/'bin'
                or not launch.is_symlink()):raise ValueError('M06_VENV_LAUNCH_PATH')
        no_symlinks(launch.parent)
        sha(environment['pyvenv_cfg_sha256']);sha(environment['symlink_sha256'])
        if not cfg.is_file() or hashlib.sha256(cfg.read_bytes()).hexdigest()!=environment['pyvenv_cfg_sha256']:
            raise ValueError('M06_VENV_CONFIG_PIN_MISMATCH')
        if hashlib.sha256(os.readlink(launch).encode()).hexdigest()!=environment['symlink_sha256']:
            raise ValueError('M06_VENV_LINK_PIN_MISMATCH')
        target=no_symlinks(environment['realpath'])
        if launch.resolve(strict=True)!=target:raise ValueError('M06_VENV_REALPATH_MISMATCH')
        paths=[root,cfg,launch,target]
    if not stat.S_ISREG(target.stat().st_mode) or not os.access(target,os.X_OK):
        raise ValueError('M06_PYTHON_EXECUTABLE_REQUIRED')
    sha(registration['python_sha256'])
    if hashlib.sha256(target.read_bytes()).hexdigest()!=registration['python_sha256']:
        raise ValueError('M06_PYTHON_PIN_MISMATCH')
    # Replacement (even same-byte replacement) cannot finish or reuse the old
    # P0 binding. These observations never change original M06 identities.
    def identity(path):
        value=path.lstat()
        return dict(path=str(path),device=value.st_dev,inode=value.st_ino,size=value.st_size,
            mtime_ns=value.st_mtime_ns,ctime_ns=value.st_ctime_ns)
    return dict(launch=str(launch),realpath=str(target),files=[identity(p) for p in paths])


def _check_python(registration,expected):
    if _python_launch(registration)!=expected:raise ValueError('M06_PYTHON_LAUNCH_CHANGED')


def _config(registration):
    keys=('enabled','python_executable','python_sha256','timeout_seconds','store_root','asset_root','private_root')
    exact_keys(registration,keys+(('python_venv',) if isinstance(registration,dict) and 'python_venv' in registration else ()))
    if registration['enabled'] is not True:raise ValueError('M06_EXECUTION_DISABLED')
    if type(registration['timeout_seconds']) is not int or not 30<=registration['timeout_seconds']<=1800:
        raise ValueError('M06_TIMEOUT_BOUND')
    _python_launch(registration)
    source=no_symlinks(registration['store_root']);assets=no_symlinks(registration['asset_root'])
    output=shadow_root(Path(registration['private_root']))
    for path in (source,assets):
        if not path.is_dir() or path==output or path.is_relative_to(output) or output.is_relative_to(path):raise ValueError('M06_ROOT_OVERLAP')
    m06_readonly.owner_root()
    return registration


def _process(action,request,registration,snapshot=None,**extra):
    _config(registration)
    python_identity=_python_launch(registration)
    root=m06_readonly.owner_root();worker=Path(__file__).with_name('m06_daily_worker.py')
    worker_sha=hashlib.sha256(no_symlinks(worker).read_bytes()).hexdigest()
    envelope=dict(action=action,request=request,registration=registration,**extra)
    if snapshot is not None:envelope['snapshot']=snapshot
    argv=[registration['python_executable'],'-I','-B',str(worker),str(root)]
    if request.get('date_contract')==EVENING_CONTRACT:
        from .m06_deadline_process import run_bounded
        process=run_bounded(argv,input_bytes=canonical_bytes(envelope),timeout_seconds=registration['timeout_seconds'],
            execution_deadline=aware(request['execution_deadline']))
    else:
        process=subprocess.run(argv,input=canonical_bytes(envelope),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=registration['timeout_seconds'])
    if len(process.stdout)>MAX_JSON_BYTES:raise ValueError('M06_DAILY_RESPONSE_LIMIT')
    try:result=json.loads(process.stdout)
    except (ValueError,UnicodeError) as error:raise ValueError('M06_DAILY_RESPONSE_INVALID') from error
    if process.returncode:
        reason=result.get('reason','M06_DAILY_FAILED')
        raise ValueError(reason if isinstance(reason,str) and reason.isidentifier() else 'M06_DAILY_FAILED')
    if result.get('request_sha256')!=sha256_json(envelope) or type(result.get('pid')) is not int:
        raise ValueError('M06_DAILY_RESPONSE_IDENTITY')
    if hashlib.sha256(no_symlinks(worker).read_bytes()).hexdigest()!=worker_sha:raise ValueError('M06_DAILY_CODE_CHANGED')
    _config(registration);_check_python(registration,python_identity)
    if 'python_venv' in registration:
        observed=result.get('python_launch',{})
        if (observed.get('executable')!=registration['python_executable']
                or observed.get('prefix')!=registration['python_venv']['root']
                or observed.get('prefix')==observed.get('base_prefix')
                or observed.get('realpath')!=registration['python_venv']['realpath']):
            raise ValueError('M06_VENV_PROCESS_IDENTITY_MISMATCH')
    return result


def validate_registration(registration=None):
    if registration is None or registration=={'enabled':False}:return dict(status='DISABLED',natural_verified=False)
    try:
        _config(registration)
        return dict(status='BOUND_NOT_NATURALLY_VERIFIED',natural_verified=False)
    except (ValueError,TypeError,KeyError,OSError):
        return dict(status='BLOCKED_M06_REGISTRATION',natural_verified=False)


def _owner_cutoff(request):
    return request['owner_contract_cutoff'] if request.get('date_contract')==EVENING_CONTRACT else request['completion_cutoff']


def _execution_deadline(request):
    return request['execution_deadline'] if request.get('date_contract')==EVENING_CONTRACT else request['completion_cutoff']


def _request(request):
    evening=isinstance(request,dict) and 'date_contract' in request
    exact_keys(request,tuple(k for k in REQUEST_KEYS if k!='completion_cutoff')+
        ('date_contract','scheduled_date','execution_deadline','owner_contract_cutoff') if evening else REQUEST_KEYS)
    for key in ('signal_date','target_date','eligibility_source_date'):trade_date(request[key])
    target=request['target_date'];admission=aware(request['admission_cutoff']);completion=aware(_owner_cutoff(request))
    if evening:
        if request['date_contract']!=EVENING_CONTRACT:raise ValueError('M06_DATE_CONTRACT')
        scheduled=trade_date(request['scheduled_date']);cycle=calendar_day(scheduled,evening=True)
        deadline=aware(request['execution_deadline'])
        if (cycle['target_date']!=target or cycle['state'] not in ('FULL_TRADING_DAY','HALF_TRADING_DAY_AM')
                or request['signal_date']!=scheduled or request['eligibility_source_date']!=scheduled):
            raise ValueError('M06_EVENING_DATE_MISMATCH')
        if (any(v.astimezone(TZ).strftime('%Y%m%d')!=scheduled for v in (admission,deadline))
                or completion.astimezone(TZ).strftime('%Y%m%d')!=target or not admission<deadline<completion):
            raise ValueError('M06_EVENING_CUTOFF_MISMATCH')
    elif any(v.astimezone(TZ).strftime('%Y%m%d')!=target for v in (admission,completion)):
        raise ValueError('M06_CUTOFF_DATE_MISMATCH')
    if request['execution_mode'] not in ('NATURAL','MANUAL_RECOVERY','RECORDED_INPUT_REPLAY'):raise ValueError('M06_EXECUTION_MODE')
    if request['production_method'] not in ('EXISTING_VERIFIED_POOL','GENERATE_IF_ABSENT'):raise ValueError('M06_PRODUCTION_METHOD')
    if request['production_method']=='GENERATE_IF_ABSENT' and (request['execution_mode']=='RECORDED_INPUT_REPLAY' or completion<=admission):
        raise ValueError('M06_GENERATION_WINDOW')
    for key in ('files','source_files'):
        if not isinstance(request[key],dict):raise ValueError('M06_INPUT_INVENTORY_REQUIRED')
        for name,digest in request[key].items():
            rel=Path(name)
            if not name or rel.is_absolute() or '..' in rel.parts:raise ValueError('M06_INPUT_PATH')
            sha(digest)
    if not request['source_files']:raise ValueError('M06_SOURCE_INVENTORY_REQUIRED')


def _code_manifest():
    return {name:hashlib.sha256(no_symlinks(Path(__file__).with_name(name)).read_bytes()).hexdigest() for name in
        ('p0_hk_preselection.py','m06_deadline_process.py','m06_input_delivery.py','m06_daily_worker.py','m06_readonly.py','daily_tick.py','daily_dispatch.py','run_ledger.py','main_registry.py','main_runtime.py','composition.py','contracts.py','digests.py','module_api.py','module_artifacts.py')}


def _check_code(expected):
    if _code_manifest()!=expected:raise ValueError('M06_P0_CODE_CHANGED')


def prepare_job(job,registration,today):
    _config(registration);request=job.get('owner_request');_request(request)
    if job.get('lane')!=LANE or type(job.get('max_attempts')) is not int or job['max_attempts']!=1:
        raise ValueError('M06_SINGLE_ATTEMPT_REQUIRED')
    if any(k not in job for k in ('scheduled_at','deadline','half_day_bound')) or type(job['half_day_bound']) is not bool:
        raise ValueError('M06_EXPLICIT_SLOT_REQUIRED')
    start,end=aware(job['scheduled_at']),aware(job['deadline'])
    scheduled=request.get('scheduled_date',request['target_date'])
    if (start>=end or scheduled!=today
            or any(stamp.astimezone(TZ).strftime('%Y%m%d')!=today for stamp in (start,end))):
        raise ValueError('M06_CURRENT_SLOT_REQUIRED')
    if request.get('date_contract')==EVENING_CONTRACT:
        if aware(request['execution_deadline'])!=end:raise ValueError('M06_EXECUTION_DEADLINE_MISMATCH')
    elif request['production_method']=='GENERATE_IF_ABSENT' and aware(request['completion_cutoff'])>end:
        raise ValueError('M06_GENERATION_WINDOW')
    snapshot=_process('inspect',request,registration)['payload']
    code=_code_manifest();python_identity=_python_launch(registration)
    binding=dict(code_sha256=sha256_json(dict(p0=code,original_manifest=m06_readonly.MANIFEST_SHA256)),
        config_sha256=sha256_json(registration),dependency_sha256=sha256_json(dict(owner=snapshot,python_launch=python_identity)),
        registration=registration,owner_snapshot=snapshot,p0_code_manifest=code,python_identity=python_identity)
    binding['invoke']=partial(run_owner,registration=registration,snapshot=snapshot,code_manifest=code,python_identity=python_identity)
    identity=dict(lane=LANE,target_date=request['target_date'],input_sha256=sha256_json(request),research_cutoff=request['admission_cutoff'],
        **{k:binding[k] for k in IDENTITIES})
    return dict(job,identity=identity),binding


def admission_reason(job,binding,now,ledger_root):
    request=job['owner_request']
    if no_symlinks(ledger_root)==no_symlinks(Path(binding['registration']['private_root'])/'.m06-ledger'):
        raise ValueError('M06_SEPARATE_LEDGER_REQUIRED')
    if request['production_method']=='GENERATE_IF_ABSENT' and now>=aware(_execution_deadline(request)):
        return 'M06_GENERATION_COMPLETION_WINDOW_EXPIRED'
    budget=binding.get('execution_budget_seconds')
    if budget is not None and now+timedelta(seconds=budget)>aware(_execution_deadline(request)):
        return 'M06_EXECUTION_BUDGET_INSUFFICIENT'
    prepared,current=prepare_job(job,binding['registration'],now.astimezone(TZ).strftime('%Y%m%d'))
    if prepared['identity']!=job['identity'] or any(current[k]!=binding[k] for k in IDENTITIES) or current['owner_snapshot']!=binding['owner_snapshot']:
        return 'OWNER_BINDING_IDENTITY_MISMATCH'
    if budget is not None:
        observed=_utc_now()
        if observed<now:return 'M06_CLOCK_REGRESSION'
        if observed+timedelta(seconds=budget)>aware(_execution_deadline(request)):
            return 'M06_EXECUTION_BUDGET_INSUFFICIENT'
    return None


def run_owner(request,p0_run_id,*,registration,snapshot,code_manifest,python_identity):
    _check_code(code_manifest);_check_python(registration,python_identity)
    produced=_process('invoke',request,registration,snapshot)
    _check_code(code_manifest);_check_python(registration,python_identity)
    first=produced['payload'];reference=first['committed_reference']
    read=_process('read',request,registration,snapshot,reference=reference,m06_ledger_run_id=first['m06_ledger_run_id'])
    _check_code(code_manifest);_check_python(registration,python_identity)
    if read['payload']!={k:v for k,v in first.items() if k!='owner_reused'} or read['pid']==produced['pid']:
        raise ValueError('M06_INDEPENDENT_READBACK_MISMATCH')
    product=dict(first,owner='M06',p0_ledger_run_id=p0_run_id,request_sha256=sha256_json(request),
        admission_cutoff=request['admission_cutoff'],
        **({k:request[k] for k in ('date_contract','scheduled_date','execution_deadline','owner_contract_cutoff')}
           if request.get('date_contract')==EVENING_CONTRACT else dict(completion_cutoff=request['completion_cutoff'])),
        producer_pid=produced['pid'],reader_pid=read['pid'],bound_root=registration['private_root'])
    return dict(status='SUCCEEDED',product_reference=product,readback_verified=True,retry_safe_without_external_effect=False,reason_codes=[])


def verify_receipt(receipt,request,binding,claim):
    if request.get('date_contract')==EVENING_CONTRACT and _utc_now()>=aware(request['execution_deadline']):
        raise TimeoutError('M06_EXECUTION_DEADLINE_EXPIRED')
    _check_code(binding['p0_code_manifest']);_check_python(binding['registration'],binding['python_identity'])
    if (claim['identity']['input_sha256']!=sha256_json(request)
            or claim['identity']['research_cutoff']!=request['admission_cutoff']):
        raise ValueError('M06_P0_REQUEST_CHANGED')
    product=receipt['product_reference']
    if (receipt['status']!='SUCCEEDED' or receipt['readback_verified'] is not True
            or product['p0_ledger_run_id']!=claim['run_id'] or product['request_sha256']!=sha256_json(request)
            or product['m06_computation_identity']!=binding['owner_snapshot']['computation_identity']
            or product['committed_reference']['producer_computation_identity']!=product['m06_computation_identity']):
        raise ValueError('M06_P0_RECEIPT_MAPPING_MISMATCH')


def verify_finished_state(job,state):
    request=job['owner_request']
    if request.get('date_contract')==EVENING_CONTRACT:
        deadline=aware(request['execution_deadline'])
        if _utc_now()>=deadline or aware(state['latest_success']['finished_at'])>=deadline:
            raise TimeoutError('M06_EXECUTION_DEADLINE_EXPIRED')


def read_saved(claim,request,binding):
    saved=claim['state']['latest_success'];product=saved['product_reference']
    try:
        verify_receipt(saved,request,binding,dict(run_id=saved['run_id'],identity=claim['state']['identity']))
        read=_process('read',request,binding['registration'],binding['owner_snapshot'],
            reference=product['committed_reference'],m06_ledger_run_id=product['m06_ledger_run_id'])['payload']
        _check_code(binding['p0_code_manifest']);_check_python(binding['registration'],binding['python_identity'])
        if any(product.get(key)!=value for key,value in read.items()):raise ValueError('M06_SAVED_PRODUCT_MISMATCH')
    except Exception:return dict(status='BLOCKED_SAVED_PRODUCT_INVALID',state=claim['state'],natural_verified=False)
    return dict(claim,readback_verified=True,natural_verified=False)


# Candidate automation is separate from the explicit manual job/registration.
# No upstream completion evidence, clock, calendar or window is synthesized.
DELIVERY_SCHEMA='v5.m06_daily_input_delivery.v1'
FROZEN_SCHEMA='v5.m06_daily_frozen_bundle.v1'
_CALENDAR_LOCK=threading.RLock()


def _utc_now():return datetime.now(timezone.utc)


def calendar_day(target, *, evening=False):
    """Fixed HK securities calendar; evening jobs target its next open session."""
    trade_date(target)
    root=m06_readonly.owner_root()/'V5/vendor/hk_preselection_baseline/contracts'
    name='_v5_m06_daily_candidate_calendar'
    with _CALENDAR_LOCK:
        previous=sys.modules.get(name);module=types.ModuleType(name)
        module.__file__=str(root/'trading_calendar.py');sys.modules[name]=module
        try:
            raw=no_symlinks(root/'trading_calendar.py').read_bytes()
            exec(compile(raw,module.__file__,'exec'),module.__dict__)
            calendar=module.load_market_calendar(no_symlinks(root/'market_calendar_2026.json'))
            state=module.resolve_market_states(calendar,target)['hk_securities'].value
            signal=None;following=None
            if state in ('FULL_TRADING_DAY','HALF_TRADING_DAY_AM'):
                if evening:
                    signal=target;cursor=datetime.strptime(target,'%Y%m%d').date()+timedelta(days=1)
                    while cursor.year==calendar.year:
                        date8=cursor.strftime('%Y%m%d')
                        if module.resolve_market_states(calendar,date8)['hk_securities'].value in ('FULL_TRADING_DAY','HALF_TRADING_DAY_AM'):
                            following=date8;break
                        cursor+=timedelta(days=1)
                    if following is None:state='UNKNOWN'
                else:
                    try:signal=module.previous_session(calendar,target,market='hk_securities')
                    except ValueError:state='UNKNOWN'
            m06_readonly.owner_root()
            if evening:return dict(state=state,scheduled_date=target,signal_date=signal,target_date=following)
            return dict(state=state,signal_date=signal)
        finally:
            if previous is None:sys.modules.pop(name,None)
            else:sys.modules[name]=previous


def _candidate_policy(config):
    value=config.get('hk_preselection_daily')
    if value is None or value=={'enabled':False}:return None
    if not isinstance(value,dict):raise ValueError('M06_DAILY_CONFIG')
    if value.get('enabled') is False:return None
    evening='date_contract' in value
    exact_keys(value,('enabled','delivery_root','full_day_window','half_day_window',
        'execution_budget_seconds','execution_mode','production_method')+
        (('date_contract','owner_contract_cutoff_time') if evening else ())+
        (('input_delivery',) if 'input_delivery' in value else ()))
    if evening and value['date_contract']!=EVENING_CONTRACT:raise ValueError('M06_DATE_CONTRACT')
    if not evening and value['execution_mode']!='RECORDED_INPUT_REPLAY':raise ValueError('M06_DAILY_DATE_CONTRACT_REQUIRED')
    if value['enabled'] is not True:raise ValueError('M06_DAILY_DISABLED_REQUIRED')
    for key in ('full_day_window','half_day_window'):
        window=value[key]
        if window is None and key=='half_day_window':continue
        exact_keys(window,('start','end'))
        for stamp in window.values():
            if (not isinstance(stamp,str) or len(stamp)!=5 or stamp[2]!=':'
                    or not (stamp[:2]+stamp[3:]).isascii() or not (stamp[:2]+stamp[3:]).isdigit()
                    or int(stamp[:2])>23 or int(stamp[3:])>59):raise ValueError('M06_EXPLICIT_WINDOW_REQUIRED')
        if window['start']>=window['end']:raise ValueError('M06_EXPLICIT_WINDOW_REQUIRED')
    if evening:
        stamp=value['owner_contract_cutoff_time']
        if (not isinstance(stamp,str) or len(stamp)!=5 or stamp[2]!=':' or not (stamp[:2]+stamp[3:]).isascii()
                or not (stamp[:2]+stamp[3:]).isdigit() or int(stamp[:2])>23 or int(stamp[3:])>59):
            raise ValueError('M06_OWNER_CONTRACT_CUTOFF_REQUIRED')
        if value['half_day_window'] is None:raise ValueError('M06_HALF_DAY_EVENING_WINDOW_REQUIRED')
    registration=config.get('hk_preselection');_config(registration)
    budget=value['execution_budget_seconds']
    # Owner process plus independent reader process, with an explicit caller
    # budget for inspection/publication overhead. Never infer it from a slot.
    if type(budget) is not int or not 2*registration['timeout_seconds']<=budget<=86400:
        raise ValueError('M06_EXECUTION_BUDGET_REQUIRED')
    if value['execution_mode'] not in ('NATURAL','MANUAL_RECOVERY','RECORDED_INPUT_REPLAY'):
        raise ValueError('M06_EXECUTION_MODE')
    if value['production_method'] not in ('EXISTING_VERIFIED_POOL','GENERATE_IF_ABSENT',SEALED_POOL_SELECTION):
        raise ValueError('M06_PRODUCTION_METHOD')
    if value['production_method']==SEALED_POOL_SELECTION and (not evening or 'input_delivery' not in value):
        raise ValueError('M06_SEALED_POOL_SELECTION_REQUIRED')
    if value['execution_mode']=='RECORDED_INPUT_REPLAY' and value['production_method']!='EXISTING_VERIFIED_POOL':
        raise ValueError('M06_GENERATION_WINDOW')
    delivery=no_symlinks(value['delivery_root']);output=no_symlinks(registration['private_root'])
    bundle=no_symlinks(config['bundle_root']);ledger=no_symlinks(config['ledger_root'])
    roots=(delivery,output,bundle,ledger)
    if any(a==b or a.is_relative_to(b) or b.is_relative_to(a) for i,a in enumerate(roots) for b in roots[i+1:]):
        raise ValueError('M06_DAILY_ROOT_OVERLAP')
    if 'input_delivery' in value:
        adapter=value['input_delivery'];snapshot=no_symlinks(adapter['snapshot_root'])
        if any(snapshot==root or snapshot.is_relative_to(root) or root.is_relative_to(snapshot) for root in roots):
            raise ValueError('M06_DAILY_ROOT_OVERLAP')
        if (registration['store_root']!=adapter['original_store_root']
                or registration['asset_root']!=adapter['original_asset_root']):
            raise ValueError('M06_DELIVERY_REGISTRATION_ROOTS')
    inputs=(no_symlinks(registration['store_root']),no_symlinks(registration['asset_root']))
    if any(a==b or a.is_relative_to(b) or b.is_relative_to(a) for a in (output,bundle,ledger) for b in inputs):
        raise ValueError('M06_DAILY_ROOT_OVERLAP')
    return value


def _window_status(now,start,end,budget):
    if now<start:return 'WAITING_M06_WINDOW'
    if now>=end:return 'MISSED_M06_WINDOW_NO_BACKFILL'
    if now+timedelta(seconds=budget)>end:return 'M06_EXECUTION_BUDGET_INSUFFICIENT'
    return None


def _delivery(policy,target,signal,now):
    from .module_api import _open_directory,_read_at
    fd=_open_directory(no_symlinks(policy['delivery_root']))
    try:
        if _read_at(fd,None,'.v5-m06-input-deliveries')!=b'v5.m06-input-deliveries.v1\n':
            raise ValueError('M06_DELIVERY_ROOT_MARKER')
        try:raw=_read_at(fd,None,target+'.json')
        except FileNotFoundError:return None
    finally:os.close(fd)
    value=json.loads(raw)
    exact_keys(value,('schema_version','status','target_date','signal_date','eligibility_source_date',
        'completed_at','files','source_files'))
    if value['schema_version']!=DELIVERY_SCHEMA:raise ValueError('M06_INPUT_DELIVERY_SCHEMA')
    if value['status']!='READY':raise ValueError('M06_INPUT_DELIVERY_NOT_READY')
    if value['target_date']!=target or value['signal_date']!=signal:raise ValueError('M06_INPUT_DELIVERY_DATE')
    trade_date(value['eligibility_source_date'])
    if value['eligibility_source_date']>target:raise ValueError('M06_INPUT_DELIVERY_DATE')
    if aware(value['completed_at'])>now:raise ValueError('M06_INPUT_DELIVERY_FUTURE')
    return value,hashlib.sha256(raw).hexdigest()


def _delivery_timing(request,registration,completed_at):
    """Cross-check the new handoff time against original dated input evidence."""
    from .module_api import _open_directory,_read_at
    completed=aware(completed_at)
    def metadata(root,relative,inventory):
        if relative not in inventory:raise ValueError('M06_DELIVERY_REQUIRED_INPUT')
        path=no_symlinks(Path(root)/relative);fd=_open_directory(path.parent)
        try:raw=_read_at(fd,None,path.name)
        finally:os.close(fd)
        if hashlib.sha256(raw).hexdigest()!=inventory[relative]:raise ValueError('M06_DELIVERY_INPUT_CHANGED')
        value=json.loads(raw)
        if not isinstance(value,dict):raise ValueError('M06_DELIVERY_METADATA')
        return value
    for field,root in (('source_files',registration['store_root']),('files',registration['asset_root'])):
        for relative in request[field]:
            path=no_symlinks(Path(root)/relative)
            if not path.exists():raise FileNotFoundError('M06_INPUT_NOT_DELIVERED')
            if not path.is_file():raise ValueError('M06_INPUT_FILE_TYPE')
    source=registration['store_root'];files=request['source_files'];prefix='assets/hk_security_master/'
    entry=metadata(source,prefix+'latest.json',files)['entries'][request['eligibility_source_date']]
    manifest=metadata(source,prefix+entry['manifest_relative'],files)
    receipt=metadata(source,prefix+entry['receipt_relative'],files)
    if receipt.get('status')!='READY' or receipt.get('trade_date')!=request['eligibility_source_date']:
        raise ValueError('M06_MASTER_COMPLETION_IDENTITY')
    observed=[manifest['captured_at']]
    if request['production_method']=='EXISTING_VERIFIED_POOL':
        entry=metadata(source,'latest.json',files)['entries'][request['target_date']+'/HK_CONNECT_D1_TOP100_0_2']
        observed.extend((metadata(source,entry['manifest_relative'],files)['captured_at'],
            metadata(source,entry['receipt_relative'],files)['finished_at']))
    if any(aware(stamp)>completed for stamp in observed):raise ValueError('M06_INPUT_AFTER_DELIVERY_COMPLETION')
    if request['files']:
        assets=registration['asset_root'];inventory=request['files']
        pointer=metadata(assets,'panel_latest.json',inventory)
        panel=metadata(assets,pointer['manifest_relative'],inventory)
        if panel.get('panel_max_date')!=request['signal_date']:raise ValueError('M06_PANEL_SIGNAL_DATE_MISMATCH')


@contextmanager
def _state_lock(root,marker,expected,lockname):
    """Stable no-follow lock plus existing fd-relative atomic JSON writer."""
    from .module_api import _open_directory,_read_at
    fd=_open_directory(no_symlinks(root));lock=None
    try:
        if _read_at(fd,None,marker)!=expected:raise ValueError('M06_STATE_ROOT_MARKER')
        flags=os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK
        try:lock=os.open(lockname,flags|os.O_CREAT|os.O_EXCL,0o600,dir_fd=fd)
        except FileExistsError:lock=os.open(lockname,flags,dir_fd=fd)
        if not stat.S_ISREG(os.fstat(lock).st_mode):raise ValueError('M06_STATE_LOCK')
        fcntl.flock(lock,fcntl.LOCK_EX)
        yield fd
    finally:
        if lock is not None:os.close(lock)
        os.close(fd)


def _current_binding(config):
    registration=config['hk_preselection']
    return dict(bound_root=registration['private_root'],python_executable=registration['python_executable'],
        python_sha256=registration['python_sha256'],current_success_ledger_root=config['ledger_root'],
        **({'python_venv':registration['python_venv']} if 'python_venv' in registration else {}))


def prepare_daily_candidate(config,now):
    """Admit real delivery evidence, then freeze one immutable M06 job per day."""
    policy=_candidate_policy(config)
    if policy is None:return dict(status='DISABLED')
    now=aware(now.isoformat()).astimezone(TZ);scheduled=now.strftime('%Y%m%d')
    evening=policy.get('date_contract')==EVENING_CONTRACT
    calendar=calendar_day(scheduled,evening=evening)
    target=calendar['target_date'] if evening else scheduled
    if calendar['state']=='UNKNOWN':return dict(status='M06_CALENDAR_UNKNOWN')
    if calendar['state']=='NON_TRADING_DAY':return dict(status='M06_NON_TRADING_DAY')
    half=calendar['state']=='HALF_TRADING_DAY_AM'
    window=policy['half_day_window'] if half else policy['full_day_window']
    if window is None:return dict(status='M06_HALF_DAY_NOT_ENABLED')
    date=now.date().isoformat()
    start,end=(aware(date+'T'+window[key]+':00+08:00') for key in ('start','end'))
    reason=_window_status(now,start,end,policy['execution_budget_seconds'])
    if reason:return dict(status=reason)
    registration=config['hk_preselection'];method=policy['production_method']
    if 'input_delivery' in policy:
        from .m06_input_delivery import prepare_input_delivery
        sealed=prepare_input_delivery(dict(policy['input_delivery'],delivery_root=policy['delivery_root']),scheduled,target,now=now)
        if sealed['status'] not in ('READY','REUSED_M06_INPUT_DELIVERY'):return dict(status=sealed['status'])
        if method==SEALED_POOL_SELECTION:
            method=sealed['production_method']
            if method not in ('EXISTING_VERIFIED_POOL','GENERATE_IF_ABSENT'):
                raise ValueError('M06_SEALED_POOL_SELECTION_INVALID')
        registration=dict(registration,store_root=sealed['store_root'],asset_root=sealed['asset_root'])
        now=_utc_now().astimezone(TZ)
        if now.strftime('%Y%m%d')!=scheduled:return dict(status='MISSED_M06_WINDOW_NO_BACKFILL')
        reason=_window_status(now,start,end,policy['execution_budget_seconds'])
        if reason:return dict(status=reason)
    delivered=_delivery(policy,target,calendar['signal_date'],now)
    if delivered is None:return dict(status='WAITING_M06_INPUT_DELIVERY')
    from .module_api import _read_at
    from .run_ledger import _write
    fingerprint=sha256_json(dict(policy=policy,registration=registration,
        bundle_root=config['bundle_root'],ledger_root=config['ledger_root']))
    with _state_lock(config['bundle_root'],'.v5-daily-bundles',b'v5.daily-bundles.v1\n','.m06-freeze.lock') as fd:
        # Reread under the single M06 lock: callers cannot freeze two revisions.
        repeated=_delivery(policy,target,calendar['signal_date'],now)
        if repeated!=delivered:raise ValueError('M06_INPUT_DELIVERY_CHANGED')
        delivery,delivery_sha=delivered;name='.m06-'+target+'.json'
        try:frozen=json.loads(_read_at(fd,None,name))
        except FileNotFoundError:frozen=None
        if frozen is not None:
            exact_keys(frozen,('schema_version','target_date','delivery_sha256','candidate_sha256','job','expected_current_sha256'))
            if frozen['schema_version']!=FROZEN_SCHEMA or frozen['target_date']!=target:raise ValueError('M06_FROZEN_BUNDLE_IDENTITY')
            if frozen['delivery_sha256']!=delivery_sha:raise ValueError('M06_FROZEN_INPUT_CHANGED')
            if frozen['candidate_sha256']!=fingerprint:raise ValueError('M06_FROZEN_CONFIG_CHANGED')
            admission=frozen['job']['owner_request']['admission_cutoff']
            if not start<=aware(admission)<=now:raise ValueError('M06_FROZEN_ADMISSION_TIME')
        else:admission=now.isoformat()
        request={key:delivery[key] for key in ('target_date','signal_date','eligibility_source_date','files','source_files')}
        request.update(admission_cutoff=admission,execution_mode=policy['execution_mode'],production_method=method)
        if evening:
            day=f'{target[:4]}-{target[4:6]}-{target[6:]}'
            request.update(date_contract=EVENING_CONTRACT,scheduled_date=scheduled,execution_deadline=end.isoformat(),
                owner_contract_cutoff=day+'T'+policy['owner_contract_cutoff_time']+':00+08:00')
        else:request['completion_cutoff']=end.isoformat()
        _request(request)
        if aware(delivery['completed_at'])>aware(admission):raise ValueError('M06_INPUT_DELIVERY_AFTER_ADMISSION')
        try:_delivery_timing(request,registration,delivery['completed_at'])
        except FileNotFoundError:return dict(status='WAITING_M06_INPUT_FILES')
        job=dict(lane=LANE,owner_request=request,scheduled_at=start.isoformat(),deadline=end.isoformat(),
            half_day_bound=half,max_attempts=1)
        prepared,binding=prepare_job(job,registration,scheduled)
        if frozen is not None and frozen['job']!=prepared:raise ValueError('M06_FROZEN_BINDING_CHANGED')
        observed=_utc_now()
        if observed<now:raise ValueError('M06_CLOCK_REGRESSION')
        reason=_window_status(observed,start,end,policy['execution_budget_seconds'])
        if reason:return dict(status=reason)
        if _delivery(policy,target,calendar['signal_date'],observed)!=delivered:raise ValueError('M06_INPUT_DELIVERY_CHANGED')
        if frozen is None:
            current=m06_readonly.read_current_success(_current_binding(config))
            if current is not None:m06_readonly.validate_current_success(_current_binding(config),current)
            frozen=dict(schema_version=FROZEN_SCHEMA,target_date=target,delivery_sha256=delivery_sha,
                candidate_sha256=fingerprint,job=prepared,expected_current_sha256=sha256_json(current) if current is not None else None)
            _write(fd,name,frozen)
            if json.loads(_read_at(fd,None,name))!=frozen:raise ValueError('M06_FROZEN_BUNDLE_READBACK')
        binding['execution_budget_seconds']=policy['execution_budget_seconds']
        return dict(status='PREPARED_M06_CANDIDATE',job=prepared,binding=binding,frozen=frozen)


def promote_current_success(config,candidate,row):
    """Only dual-ledger success plus another cold read can advance the private CAS."""
    if row.get('status') not in ('SUCCEEDED','REUSED_SUCCESS'):return dict(status='CURRENT_SUCCESS_UNCHANGED')
    from .run_ledger import read_run,_write
    from .module_api import _read_at
    job=candidate['job'];binding=candidate['binding'];state=read_run(config['ledger_root'],job['identity'])
    if state is None or state!=row.get('state'):raise ValueError('M06_PROMOTION_P0_STATE_MISMATCH')
    if _utc_now()>=aware(_execution_deadline(job['owner_request'])):return dict(status='CURRENT_SUCCESS_LATE_NOT_PROMOTED')
    fresh=read_saved(dict(status='REUSED_SUCCESS',state=state),job['owner_request'],binding)
    if fresh.get('readback_verified') is not True:raise ValueError('M06_PROMOTION_FRESH_READBACK_FAILED')
    saved=state['latest_success'];product=saved['product_reference']
    pointer=dict(schema_version='v5.m06_current_success.v1',p0_identity=job['identity'],p0_run_id=saved['run_id'],
        m06_identity=product['m06_computation_identity'],m06_run_id=product['m06_ledger_run_id'],
        committed_reference=product['committed_reference'],product_sha256=sha256_json(product))
    current_binding=_current_binding(config)
    with _state_lock(binding['registration']['private_root'],'.v5-shadow-root',b'v5.shadow-root.v1\n','.m06-current-success.lock') as fd:
        m06_readonly.validate_current_success(current_binding,pointer)
        if read_run(config['ledger_root'],job['identity'])!=state:raise ValueError('M06_PROMOTION_P0_STATE_CHANGED')
        current=m06_readonly.read_current_success(current_binding)
        if current==pointer:return dict(status='REUSED_CURRENT_SUCCESS',reference_sha256=sha256_json(pointer))
        if _utc_now()>=aware(_execution_deadline(job['owner_request'])):return dict(status='CURRENT_SUCCESS_LATE_NOT_PROMOTED')
        digest=sha256_json(current) if current is not None else None
        if digest!=candidate['frozen']['expected_current_sha256']:return dict(status='CURRENT_SUCCESS_CAS_MISMATCH')
        if current is not None:
            m06_readonly.validate_current_success(current_binding,current)
            if current['p0_identity']['target_date']>=job['identity']['target_date']:
                return dict(status='CURRENT_SUCCESS_NOT_NEWER')
        _write(fd,'.m06-current-success.json',pointer)
        if json.loads(_read_at(fd,None,'.m06-current-success.json'))!=pointer:raise ValueError('M06_CURRENT_SUCCESS_READBACK')
        return dict(status='CURRENT_SUCCESS_PROMOTED',reference_sha256=sha256_json(pointer))

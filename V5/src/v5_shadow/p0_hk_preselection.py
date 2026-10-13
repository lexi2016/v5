"""Explicit P0 M06 registration; fixed original owner, separate exact ledgers."""
from datetime import datetime,timedelta,timezone
from functools import partial
import hashlib
import json
import os
import stat
from pathlib import Path
import subprocess
from .composition import no_symlinks,shadow_root
from .contracts import aware,exact_keys,sha,trade_date
from .digests import canonical_bytes,sha256_json,MAX_JSON_BYTES
from . import m06_readonly

LANE='hk_preselection'
TZ=timezone(timedelta(hours=8))
IDENTITIES=('code_sha256','config_sha256','dependency_sha256')
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
    process=subprocess.run([registration['python_executable'],'-I','-B',str(worker),str(root)],
        input=canonical_bytes(envelope),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=registration['timeout_seconds'])
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


def _request(request):
    exact_keys(request,REQUEST_KEYS)
    for key in ('signal_date','target_date','eligibility_source_date'):trade_date(request[key])
    target=request['target_date'];admission=aware(request['admission_cutoff']);completion=aware(request['completion_cutoff'])
    if any(v.astimezone(TZ).strftime('%Y%m%d')!=target for v in (admission,completion)):
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
        ('p0_hk_preselection.py','m06_daily_worker.py','m06_readonly.py','daily_tick.py','daily_dispatch.py','run_ledger.py','main_registry.py','main_runtime.py','composition.py','contracts.py','digests.py')}


def _check_code(expected):
    if _code_manifest()!=expected:raise ValueError('M06_P0_CODE_CHANGED')


def prepare_job(job,registration,today):
    _config(registration);request=job.get('owner_request');_request(request)
    if job.get('lane')!=LANE or type(job.get('max_attempts')) is not int or job['max_attempts']!=1:
        raise ValueError('M06_SINGLE_ATTEMPT_REQUIRED')
    if any(k not in job for k in ('scheduled_at','deadline','half_day_bound')) or type(job['half_day_bound']) is not bool:
        raise ValueError('M06_EXPLICIT_SLOT_REQUIRED')
    start,end=aware(job['scheduled_at']),aware(job['deadline'])
    if (start>=end or request['target_date']!=today
            or any(stamp.astimezone(TZ).strftime('%Y%m%d')!=today for stamp in (start,end))):
        raise ValueError('M06_CURRENT_SLOT_REQUIRED')
    if request['production_method']=='GENERATE_IF_ABSENT' and aware(request['completion_cutoff'])>end:
        raise ValueError('M06_GENERATION_WINDOW')
    snapshot=_process('inspect',request,registration)['payload']
    code=_code_manifest();python_identity=_python_launch(registration)
    binding=dict(code_sha256=sha256_json(dict(p0=code,original_manifest=m06_readonly.MANIFEST_SHA256)),
        config_sha256=sha256_json(registration),dependency_sha256=sha256_json(dict(owner=snapshot,python_launch=python_identity)),
        registration=registration,owner_snapshot=snapshot,p0_code_manifest=code,python_identity=python_identity)
    binding['invoke']=partial(run_owner,registration=registration,snapshot=snapshot,code_manifest=code,python_identity=python_identity)
    identity=dict(lane=LANE,target_date=today,input_sha256=sha256_json(request),research_cutoff=request['admission_cutoff'],
        **{k:binding[k] for k in IDENTITIES})
    return dict(job,identity=identity),binding


def admission_reason(job,binding,now,ledger_root):
    request=job['owner_request']
    if no_symlinks(ledger_root)==no_symlinks(Path(binding['registration']['private_root'])/'.m06-ledger'):
        raise ValueError('M06_SEPARATE_LEDGER_REQUIRED')
    if request['production_method']=='GENERATE_IF_ABSENT' and now>=aware(request['completion_cutoff']):
        return 'M06_GENERATION_COMPLETION_WINDOW_EXPIRED'
    prepared,current=prepare_job(job,binding['registration'],now.astimezone(TZ).strftime('%Y%m%d'))
    if prepared['identity']!=job['identity'] or any(current[k]!=binding[k] for k in IDENTITIES) or current['owner_snapshot']!=binding['owner_snapshot']:
        return 'OWNER_BINDING_IDENTITY_MISMATCH'
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
        admission_cutoff=request['admission_cutoff'],completion_cutoff=request['completion_cutoff'],
        producer_pid=produced['pid'],reader_pid=read['pid'],bound_root=registration['private_root'])
    return dict(status='SUCCEEDED',product_reference=product,readback_verified=True,retry_safe_without_external_effect=False,reason_codes=[])


def verify_receipt(receipt,request,binding,claim):
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

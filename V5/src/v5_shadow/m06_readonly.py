"""P0 bridge to one exact M06 committed reference; never calls an owner writer."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import timedelta,timezone

from .composition import no_symlinks
from .contracts import aware,exact_keys,sha
from .digests import MAX_JSON_BYTES,canonical_bytes,sha256_json

ROUTE='/api/v5/source-bundle/hk-preselection'
BINDING='m06_hk_preselection_binding'
BASE=Path(__file__).resolve().parents[2]
MANIFEST=BASE/'contracts/m06_readonly_runtime.json'
MANIFEST_SHA256='6594ddff403e4ef268662021427ec74dcbc589b57bd2035bc0754dba8a02f303'
FLAGS=dict(research_only=True,production_allowed=False,buy_gate_updated=False,orders_sent=False,natural_verified=False,formal_eligibility_verified=False)
CURRENT_SUCCESS_NAME='.m06-current-success.json'
CURRENT_SUCCESS_SCHEMA='v5.m06_current_success.v1'
CURRENT_BINDING_KEYS=('bound_root','python_executable','python_sha256','current_success_ledger_root')
CURRENT_POINTER_KEYS=('schema_version','p0_identity','p0_run_id','m06_identity','m06_run_id','committed_reference','product_sha256')


def _current_binding(binding):
    from .p0_hk_preselection import _python_launch
    exact_keys(binding,CURRENT_BINDING_KEYS+(('python_venv',) if isinstance(binding,dict) and 'python_venv' in binding else ()))
    if 'python_venv' in binding:
        exact_keys(binding['python_venv'],('root','realpath','pyvenv_cfg_sha256','symlink_sha256'))
    for field in ('bound_root','python_executable','current_success_ledger_root'):
        value=binding[field]
        if not isinstance(value,str) or not value or not Path(value).is_absolute() or '..' in Path(value).parts:
            raise ValueError('M06_BINDING_PATH')
        if field!='python_executable':no_symlinks(value)
    if no_symlinks(binding['current_success_ledger_root'])==no_symlinks(Path(binding['bound_root'])/'.m06-ledger'):
        raise ValueError('M06_SEPARATE_LEDGER_REQUIRED')
    _python_launch(binding)
    canonical_bytes(binding)


def _current_root(binding):
    from .module_api import _open_directory,_read_at
    _current_binding(binding)
    fd=_open_directory(binding['bound_root'])
    try:
        if _read_at(fd,None,'.v5-shadow-root')!=b'v5.shadow-root.v1\n':
            raise ValueError('M06_CURRENT_ROOT_MARKER')
        return fd
    except Exception:
        os.close(fd);raise


def read_current_success(binding):
    """Read only the fixed current pointer; absence does not admit any work."""
    from .module_api import _read_at
    fd=_current_root(binding)
    try:
        try:raw=_read_at(fd,None,CURRENT_SUCCESS_NAME)
        except FileNotFoundError:return None
    finally:os.close(fd)
    try:pointer=json.loads(raw)
    except (ValueError,UnicodeError) as error:raise ValueError('M06_CURRENT_POINTER_JSON') from error
    exact_keys(pointer,CURRENT_POINTER_KEYS)
    if pointer['schema_version']!=CURRENT_SUCCESS_SCHEMA:raise ValueError('M06_CURRENT_POINTER_SCHEMA')
    canonical_bytes(pointer)
    return pointer


def _current_success_snapshot(binding,pointer):
    from . import run_ledger
    fd=_current_root(binding);os.close(fd)
    exact_keys(pointer,CURRENT_POINTER_KEYS)
    if pointer['schema_version']!=CURRENT_SUCCESS_SCHEMA:raise ValueError('M06_CURRENT_POINTER_SCHEMA')
    sha(pointer['product_sha256'])
    for key in ('p0_run_id','m06_run_id'):
        if not isinstance(pointer[key],str) or not pointer[key].strip():raise ValueError('M06_CURRENT_RUN_ID')
    p0_identity=pointer['p0_identity'];m06_identity=pointer['m06_identity']
    reference=pointer['committed_reference']
    if (not isinstance(reference,dict) or reference.get('schema_version')!='v5.hk_preselection_committed_reference.v1'
            or reference.get('owner')!='M06' or reference.get('market')!='HK' or reference.get('status')!='COMMITTED'):
        raise ValueError('M06_CURRENT_REFERENCE')
    for identity in (p0_identity,m06_identity):
        run_ledger.identity_key(identity)
        if (identity['lane']!='hk_preselection' or identity['target_date']!=reference.get('target_date')
                or aware(identity['research_cutoff']).astimezone(timezone(timedelta(hours=8))).strftime('%Y%m%d')!=identity['target_date']):
            raise ValueError('M06_CURRENT_IDENTITY')
    if (m06_identity!=reference.get('producer_computation_identity')
            or m06_identity['research_cutoff']!=reference.get('research_cutoff')):
        raise ValueError('M06_CURRENT_REFERENCE_IDENTITY')
    computation=sha(reference.get('computation_sha256'))
    relative='hk_preselection/'+m06_identity['target_date']+'/objects/'+computation+'/'
    for field,name in (('artifact_relative','artifact.json'),('manifest_relative','manifest.json'),
            ('receipt_relative','receipt.json'),('producer_reference','producer_receipt.json'),
            ('reader_reference','strict_reader_receipt.json')):
        value=reference.get(field)
        if field.endswith('_reference'):value=value.get('relative') if isinstance(value,dict) else None
        if value!=relative+name:raise ValueError('M06_CURRENT_REFERENCE_PATH')
        no_symlinks(Path(binding['bound_root'])/value)
    states=(run_ledger.read_run(binding['current_success_ledger_root'],p0_identity),
        run_ledger.read_run(str(Path(binding['bound_root'])/'.m06-ledger'),m06_identity))
    products=[]
    for state,key in zip(states,('p0_run_id','m06_run_id')):
        saved=state.get('latest_success') if isinstance(state,dict) else None
        product=saved.get('product_reference') if isinstance(saved,dict) else None
        if (not isinstance(saved,dict) or saved.get('status')!='SUCCEEDED' or saved.get('readback_verified') is not True
                or saved.get('run_id')!=pointer[key] or not isinstance(product,dict)
                or product.get('committed_reference')!=reference):
            raise ValueError('M06_CURRENT_LEDGER_SUCCESS')
        products.append(product)
    product,m06_product=products
    if (sha256_json(product)!=pointer['product_sha256'] or product.get('bound_root')!=binding['bound_root']
            or product.get('p0_ledger_run_id')!=pointer['p0_run_id'] or product.get('m06_ledger_run_id')!=pointer['m06_run_id']
            or product.get('m06_computation_identity')!=m06_identity or product.get('request_sha256')!=p0_identity['input_sha256']
            or product.get('admission_cutoff')!=p0_identity['research_cutoff']
            or product.get('completion_cutoff')!=reference['research_cutoff']):
        raise ValueError('M06_CURRENT_PRODUCT_IDENTITY')
    producer=m06_product.get('producer_receipt');producer_reference=reference.get('producer_reference')
    if (not isinstance(producer,dict) or not isinstance(producer_reference,dict)
            or sha256_json(producer)!=producer_reference.get('sha256')):
        raise ValueError('M06_CURRENT_PRODUCER_RECEIPT')
    fixed=dict(bound_root=binding['bound_root'],python_executable=binding['python_executable'],committed_reference=reference)
    canonical_bytes(pointer)
    return fixed,states


def validate_current_success(binding,pointer):
    """Bind one exact pointer to verified P0 and original-M06 ledger successes."""
    return _current_success_snapshot(binding,pointer)[0]


def validate_binding(config):
    binding=config.get(BINDING)
    if binding is None:return
    if config.get('module_id')!='source_bundle' or ROUTE not in config.get('routes',[]):
        raise ValueError('M06_ROUTE_CONFIG')
    if isinstance(binding,dict) and 'current_success_ledger_root' in binding:
        _current_binding(binding)
        return
    exact_keys(binding,('bound_root','committed_reference','python_executable'))
    for field in ('bound_root','python_executable'):
        value=binding[field]
        if not isinstance(value,str) or not value or not Path(value).is_absolute() or '..' in Path(value).parts:
            raise ValueError('M06_BINDING_PATH')
    if not isinstance(binding['committed_reference'],dict):raise ValueError('M06_BINDING_REFERENCE')
    canonical_bytes(binding)


def owner_root():
    raw=no_symlinks(MANIFEST).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA256:raise ValueError('M06_OWNER_MANIFEST_SHA')
    manifest=json.loads(raw)
    for entry in manifest['entries']:
        rel=Path(entry['path'])
        if rel.is_absolute() or '..' in rel.parts or not entry['path'].startswith('source_owners/m06/'):
            raise ValueError('M06_OWNER_PATH')
        data=no_symlinks(BASE/rel).read_bytes()
        if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
            raise ValueError('M06_OWNER_BYTES_MISMATCH')
    return no_symlinks(BASE/'source_owners/m06')


def not_configured():
    return dict(status='NOT_CONFIGURED',module_id='M06_HK_PRESELECTION',
        reason_codes=['M06_REFERENCE_NOT_CONFIGURED'],model_weights_reverified=False,**FLAGS)


def read_record(config,query):
    """Return the original module record after cold saved-reference verification."""
    if query:raise ValueError('M06_FIXED_REFERENCE_QUERY')
    validate_binding(config)
    binding=config.get(BINDING)
    if binding is None:return None
    if 'current_success_ledger_root' in binding:
        from .p0_hk_preselection import _python_launch,_check_python
        pointer=read_current_success(binding)
        if pointer is None:return None
        fixed,before=_current_success_snapshot(binding,pointer)
        launch=_python_launch(binding)
        result=read_record(dict(config,**{BINDING:fixed}),{})
        _check_python(binding,launch)
        if read_current_success(binding)!=pointer or _current_success_snapshot(binding,pointer)!=(fixed,before):
            raise ValueError('M06_CURRENT_SUCCESS_CHANGED')
        return result
    root=owner_root()
    request=dict(binding=binding,config={k:config[k] for k in ('module_id','release_id','routes')})
    worker=Path(__file__).with_name('m06_readonly_worker.py')
    try:
        proc=subprocess.run([binding['python_executable'],'-I','-B',str(worker),str(root)],
            input=canonical_bytes(request),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    except subprocess.TimeoutExpired as error:raise ValueError('M06_READ_TIMEOUT') from error
    if len(proc.stdout)>MAX_JSON_BYTES:raise ValueError('M06_READ_RESPONSE_LIMIT')
    if proc.returncode:raise ValueError('M06_COMMITTED_REFERENCE_REJECTED')
    try:record=json.loads(proc.stdout)
    except (ValueError,UnicodeError) as error:raise ValueError('M06_READ_RESPONSE_JSON') from error
    from .module_api import _validate_record
    record=_validate_record(config,record,ROUTE,{})
    if record['payload'].get('committed_reference')!=binding['committed_reference']:
        raise ValueError('M06_REFERENCE_RESPONSE_MISMATCH')
    owner_root()
    return record,sha256_json(record)

"""P0 bridge to one exact M06 committed reference; never calls an owner writer."""
import hashlib
import json
from pathlib import Path
import subprocess

from .composition import no_symlinks
from .contracts import exact_keys
from .digests import MAX_JSON_BYTES,canonical_bytes,sha256_json

ROUTE='/api/v5/source-bundle/hk-preselection'
BINDING='m06_hk_preselection_binding'
BASE=Path(__file__).resolve().parents[2]
MANIFEST=BASE/'contracts/m06_readonly_runtime.json'
MANIFEST_SHA256='6594ddff403e4ef268662021427ec74dcbc589b57bd2035bc0754dba8a02f303'
FLAGS=dict(research_only=True,production_allowed=False,buy_gate_updated=False,orders_sent=False,natural_verified=False,formal_eligibility_verified=False)


def validate_binding(config):
    binding=config.get(BINDING)
    if binding is None:return
    if config.get('module_id')!='source_bundle' or ROUTE not in config.get('routes',[]):
        raise ValueError('M06_ROUTE_CONFIG')
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

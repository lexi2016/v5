"""P0 exact M10 cold-reader bridge. No producer, latest selection or writes."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from .composition import no_symlinks
from .contracts import exact_keys
from .digests import MAX_JSON_BYTES,canonical_bytes,sha256_json

ROUTE='/api/v5/source-bundle/hk-close-review'
BINDING='m10_hk_close_binding'
BASE=Path(__file__).resolve().parents[2]
MANIFEST=BASE/'contracts/m10_readonly_runtime.json'
MANIFEST_SHA256='8c5580a078e71f97664b2739aa67b1b1528aeef8ae5ff72a2175e8f3c8451b53'
FLAGS=dict(research_only=True,production_allowed=False,buy_gate_updated=False,orders_sent=False,natural_verified=False,formal_eligibility_verified=False)


def validate_binding(config):
    binding=config.get(BINDING)
    if binding is None:return
    if config.get('module_id')!='source_bundle' or ROUTE not in config.get('routes',[]):
        raise ValueError('M10_ROUTE_CONFIG')
    exact_keys(binding,('run_root','run_id','generation','python_executable'))
    for field in ('run_root','python_executable'):
        value=binding[field]
        if not isinstance(value,str) or not value or not Path(value).is_absolute() or '..' in Path(value).parts:
            raise ValueError('M10_BINDING_PATH')
    if not isinstance(binding['run_id'],str) or not re.fullmatch(r'\d{8}-[0-9a-f]{24}',binding['run_id']):
        raise ValueError('M10_BINDING_RUN')
    if not isinstance(binding['generation'],str) or not re.fullmatch(r'[0-9a-f]{64}',binding['generation']):
        raise ValueError('M10_BINDING_GENERATION')
    canonical_bytes(binding)


def owner_root():
    raw=no_symlinks(MANIFEST).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA256:raise ValueError('M10_OWNER_MANIFEST_SHA')
    manifest=json.loads(raw)
    if not manifest.get('entries'):raise ValueError('M10_OWNER_CLOSURE_MISSING')
    for entry in manifest['entries']:
        rel=Path(entry['path'])
        if rel.is_absolute() or '..' in rel.parts or not entry['path'].startswith('source_owners/m10/'):
            raise ValueError('M10_OWNER_PATH')
        data=no_symlinks(BASE/rel).read_bytes()
        if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
            raise ValueError('M10_OWNER_BYTES_MISMATCH')
    root=no_symlinks(BASE/'source_owners/m10')
    expected={entry['path'] for entry in manifest['entries']}
    actual={str(path.relative_to(BASE)) for path in root.rglob('*') if path.is_file() or path.is_symlink()}
    if actual!=expected:raise ValueError('M10_OWNER_CLOSURE_EXTRA_FILES')
    return root


def not_configured():
    return dict(status='NOT_CONFIGURED',module_id='M10_HK_CLOSE_REVIEW',
        reason_codes=['M10_REFERENCE_NOT_CONFIGURED'],**FLAGS)


def read_record(config,query):
    if query:raise ValueError('M10_FIXED_REFERENCE_QUERY')
    validate_binding(config);binding=config.get(BINDING)
    if binding is None:return None
    root=owner_root();worker=Path(__file__).with_name('m10_readonly_worker.py')
    try:
        proc=subprocess.run([binding['python_executable'],'-I','-S','-B',str(worker),str(root)],
            input=canonical_bytes(binding),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    except subprocess.TimeoutExpired as error:raise ValueError('M10_READ_TIMEOUT') from error
    if len(proc.stdout)>MAX_JSON_BYTES:raise ValueError('M10_READ_RESPONSE_LIMIT')
    if proc.returncode:raise ValueError('M10_COMMITTED_REFERENCE_REJECTED')
    try:value=json.loads(proc.stdout)
    except (ValueError,UnicodeError) as error:raise ValueError('M10_READ_RESPONSE_JSON') from error
    if (not isinstance(value,dict) or value.get('schema')!='v5.hk_close_daily.envelope.v1'
        or value.get('run_id')!=binding['run_id'] or value.get('generation')!=binding['generation']
        or value.get('data_kind')!='RECORDED_INPUT_REPLAY' or value.get('natural_admission')!='UNVERIFIED'):
        raise ValueError('M10_REFERENCE_RESPONSE_MISMATCH')
    review=value['review']
    if any(review.get(k) is not False for k in ('production_allowed','buy_gate_updated','orders_sent')):
        raise ValueError('M10_RESEARCH_BOUNDARY')
    if review.get('trade_date')!=value['identity']['trade_date'] or review['trade_date']!=binding['run_id'][:8]:
        raise ValueError('M10_TRADE_DATE_MISMATCH')
    # Transport the original projected review and identities, not the private raw
    # input-evidence/model/stage payloads carried by the immutable envelope.
    payload=dict(schema_version='v5.hk_close_readonly.v1',module_id='M10_HK_CLOSE_REVIEW',
        status=review['status'],review=review,run_id=value['run_id'],generation=value['generation'],
        identity=value['identity'],native_review_sha256=value['native_review_sha256'],
        data_kind=value['data_kind'],natural_admission=value['natural_admission'],
        cannot_confirm=value['cannot_confirm'],**FLAGS)
    owner_root()
    record=dict(schema_version='v5.module_response.v1',module_id=config['module_id'],
        release_id=config['release_id'],path=ROUTE,query={},payload=payload,
        payload_sha256=sha256_json(payload),source_input_sha256=value['identity']['input_sha256'],
        data_kind=value['data_kind'],generated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),status_code=200)
    from .module_api import _validate_record
    return _validate_record(config,record,ROUTE,{}),sha256_json(record)

"""Exact frozen M09 historical cold-reader bridge. GET has no producer path."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from .composition import no_symlinks
from .contracts import exact_keys,trade_date
from .digests import MAX_JSON_BYTES,canonical_bytes,sha256_json

ROUTE='/api/v5/source-bundle/a-close-replay'
BINDING='m09_a_close_replay_binding'
BASE=Path(__file__).resolve().parents[2]
MANIFEST=BASE/'contracts/m09_readonly_runtime.json'
MANIFEST_SHA256='d07a7a671ab7bd42b4b1778918c75e15c647ed954d30358125dac15327c056a0'
OWNER_COMMIT='084df7c61e57e7615633828a0d6a5d9078dc9b1c'
FLAGS=dict(research_only=True,production_allowed=False,buy_gate_updated=False,orders_sent=False,
    natural_verified=False,formal_eligibility_verified=False,strict_1500_pit_verified=False,
    source_time_verified=False,membership_qualification_verified=False)


def validate_binding(config):
    binding=config.get(BINDING)
    if binding is None:return
    if config.get('module_id')!='source_bundle' or ROUTE not in config.get('routes',[]):
        raise ValueError('M09_ROUTE_CONFIG')
    exact_keys(binding,('run_root','trade_date','run_id','generation','python_executable'))
    for key in ('run_root','python_executable'):
        value=binding[key]
        if not isinstance(value,str) or not value or not Path(value).is_absolute() or '..' in Path(value).parts:
            raise ValueError('M09_BINDING_PATH')
    trade_date(binding['trade_date'])
    if not isinstance(binding['run_id'],str) or not re.fullmatch(r'm09-[0-9a-f]{32}-[0-9a-f]{12}',binding['run_id']):
        raise ValueError('M09_BINDING_RUN')
    if not isinstance(binding['generation'],str) or not re.fullmatch(r'[0-9a-f]{64}',binding['generation']):
        raise ValueError('M09_BINDING_GENERATION')
    canonical_bytes(binding)


def owner_root():
    raw=no_symlinks(MANIFEST).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA256:raise ValueError('M09_OWNER_MANIFEST_SHA')
    manifest=json.loads(raw)
    if manifest.get('source_commit')!=OWNER_COMMIT or not manifest.get('entries'):
        raise ValueError('M09_OWNER_CLOSURE_MISSING')
    for entry in manifest['entries']:
        rel=Path(entry['path'])
        if rel.is_absolute() or '..' in rel.parts or not entry['path'].startswith('source_owners/m09/'):
            raise ValueError('M09_OWNER_PATH')
        data=no_symlinks(BASE/rel).read_bytes()
        if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
            raise ValueError('M09_OWNER_BYTES_MISMATCH')
    root=no_symlinks(BASE/'source_owners/m09')
    expected={entry['path'] for entry in manifest['entries']}
    actual={str(path.relative_to(BASE)) for path in root.rglob('*') if path.is_file() or path.is_symlink()}
    if actual!=expected:raise ValueError('M09_OWNER_CLOSURE_EXTRA_FILES')
    return root


def not_configured():
    return dict(status='NOT_CONFIGURED',module_id='M09_A_CLOSE_REPLAY',
        reason_codes=['M09_REFERENCE_NOT_CONFIGURED'],**FLAGS)


def read_record(config,query):
    if query:raise ValueError('M09_FIXED_REFERENCE_QUERY')
    validate_binding(config);binding=config.get(BINDING)
    if binding is None:return None
    root=owner_root();worker=Path(__file__).with_name('m09_readonly_worker.py')
    try:
        proc=subprocess.run([binding['python_executable'],'-I','-B',str(worker),str(root)],
            input=canonical_bytes(binding),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
    except subprocess.TimeoutExpired as error:raise ValueError('M09_READ_TIMEOUT') from error
    if len(proc.stdout)>MAX_JSON_BYTES:raise ValueError('M09_READ_RESPONSE_LIMIT')
    if proc.returncode:raise ValueError('M09_COMMITTED_REFERENCE_REJECTED')
    try:value=json.loads(proc.stdout)
    except (ValueError,UnicodeError) as error:raise ValueError('M09_READ_RESPONSE_JSON') from error
    if (not isinstance(value,dict) or value.get('schema_version')!='v5.a_close_replay_readonly.v1'
            or value.get('module_id')!='M09_A_CLOSE_REPLAY' or value.get('run_id')!=binding['run_id']
            or value.get('generation')!=binding['generation'] or value.get('trade_date')!=binding['trade_date']
            or value.get('owner_commit')!=OWNER_COMMIT or value.get('data_kind')!='RECORDED_INPUT_REPLAY'
            or value.get('execution_kind')!='HISTORICAL_REPLAY' or value.get('scope')!='OBSERVED_ROWS_ONLY'
            or value.get('status')!='PARTIAL' or any(value.get(k) is not v for k,v in FLAGS.items())):
        raise ValueError('M09_REFERENCE_RESPONSE_MISMATCH')
    review=value['review'];identity=value['identity'];publication=value['publication']
    if (review.get('trade_date')!=binding['trade_date'] or identity.get('trade_date')!=binding['trade_date']
            or identity.get('model_run_id')!=binding['run_id'] or identity.get('generation_sha256')!=binding['generation']
            or review['model_review'].get('run_id')!=binding['run_id']
            or sha256_json(review)!=identity.get('canonical_review_sha256')
            or publication.get('read_status')!='VERIFIED'
            or any(review.get(k) is not False for k in ('production_allowed','buy_gate_updated','orders_sent'))):
        raise ValueError('M09_REVIEW_IDENTITY_OR_BOUNDARY')
    owner_root()
    record=dict(schema_version='v5.module_response.v1',module_id=config['module_id'],
        release_id=config['release_id'],path=ROUTE,query={},payload=value,
        payload_sha256=sha256_json(value),source_input_sha256=identity['source_sha256'],
        data_kind=value['data_kind'],generated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),status_code=200)
    from .module_api import _validate_record
    return _validate_record(config,record,ROUTE,{}),sha256_json(record)

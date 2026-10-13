"""P0 read-only binding for an exact original M16 committed result."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from .contracts import exact_keys, trade_date, sha
from .digests import canonical_bytes, sha256_json
from .m16_readonly_worker import raw, unavailable, OUTPUT_BYTES, FLAGS

BASE = Path(__file__).resolve().parents[2]
ROUTE = '/api/v5/source-bundle/manager-public-research'
BINDING = 'm16_saved_public_research_binding'
RUNTIME = BASE / 'contracts/m16_readonly_runtime.json'
RUNTIME_SHA256 = '54e2e08ab806873bf0d24f4af72014c3ff7f14cb67208c7c636efc2746b8131a'


def validate_reference(binding):
    exact_keys(binding, ('private_root', 'trade_date', 'input_identity', 'job_id',
                         'generation', 'attempt', 'commit_sha256', 'commit_file_sha256',
                         'data_kind', 'python_executable'))
    trade_date(binding['trade_date'])
    for key in ('input_identity', 'commit_sha256', 'commit_file_sha256'):
        sha(binding[key])
    for key in ('job_id', 'generation'):
        value = binding[key]
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,179}', value):
            raise ValueError('M16_IDENTITY')
    if type(binding['attempt']) is not int or binding['attempt'] < 1:
        raise ValueError('M16_ATTEMPT')
    if binding['data_kind'] not in {'SYNTHETIC', 'RECORDED_INPUT_REPLAY', 'OWNER_RESULT'}:
        raise ValueError('M16_DATA_KIND')
    for key in ('private_root', 'python_executable'):
        value = binding[key]
        if not isinstance(value, str) or not Path(value).is_absolute() or '..' in Path(value).parts:
            raise ValueError('M16_BINDING_PATH')


def validate_binding(config):
    if BINDING not in config:
        return
    if config['module_id'] != 'source_bundle' or ROUTE not in config['routes']:
        raise ValueError('M16_ROUTE_BINDING')
    validate_reference(config[BINDING])


def verify_runtime():
    content = raw(RUNTIME)
    if hashlib.sha256(content).hexdigest() != RUNTIME_SHA256:
        raise ValueError('M16_RUNTIME_PIN')
    manifest = json.loads(content)
    for entry in manifest['entries']:
        path = Path(entry['path'])
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('M16_RUNTIME_PATH')
        source = raw(BASE / path)
        if len(source) != entry['bytes'] or hashlib.sha256(source).hexdigest() != entry['sha256']:
            raise ValueError('M16_RUNTIME_BYTES')


def not_configured():
    return unavailable('M16_SAVED_REFERENCE_NOT_CONFIGURED')


def _check_child(payload, binding):
    if (not isinstance(payload, dict) or payload.get('schema_version') != 'v5.m16_saved_public_research.v1'
            or payload.get('module_id') != 'M16_PUBLIC_RESEARCH' or payload.get('mode') != 'READ_ONLY_SAVED_RESULT'
            or any(payload.get(key) is not value for key, value in FLAGS.items())):
        raise ValueError('M16_CHILD_BOUNDARY')
    reasons = payload.get('reason_codes')
    if not isinstance(reasons, list) or not reasons or any(not isinstance(reason, str) or not reason for reason in reasons):
        raise ValueError('M16_CHILD_REASONS')
    status = payload.get('status')
    if status in {'WAITING', 'CANNOT_CONFIRM'}:
        if any(key in payload for key in ('product', 'job', 'receipt', 'reference', 'data_kind', 'business_status', 'evidence_status', 'display_data')):
            raise ValueError('M16_UNAVAILABLE_HAS_CONTENT')
        return
    if status != 'SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED' or payload.get('evidence_status') != 'VERIFIED_PERSISTENCE_ONLY':
        raise ValueError('M16_CHILD_STATUS')
    if any(not isinstance(payload.get(key), dict) for key in ('product', 'job', 'receipt', 'reference')):
        raise ValueError('M16_CHILD_RECORDS')
    ref = payload['reference']
    for key in ('trade_date', 'input_identity', 'job_id', 'generation', 'attempt', 'commit_sha256', 'commit_file_sha256'):
        if ref.get(key) != binding[key]:
            raise ValueError('M16_CHILD_REFERENCE')
    for key in ('product_sha256', 'job_sha256', 'receipt_sha256'):
        sha(ref.get(key))
    if payload.get('data_kind') != binding['data_kind'] or payload.get('business_status') != payload.get('product', {}).get('status'):
        raise ValueError('M16_CHILD_BUSINESS')


def read_record(config, query):
    if set(query) - {'trade_date'}:
        raise ValueError('M16_QUERY')
    if 'trade_date' in query:
        trade_date(query['trade_date'])
    validate_binding(config)
    binding = config.get(BINDING)
    if binding is None:
        payload = not_configured()
    elif query.get('trade_date', binding['trade_date']) != binding['trade_date']:
        payload = unavailable('M16_NO_SAVED_RESULT_FOR_DATE', requested_trade_date=query['trade_date'])
    else:
        try:
            verify_runtime()
            proc = subprocess.run([binding['python_executable'], '-I', '-B', str(BASE / 'src/v5_shadow/m16_readonly_worker.py')],
                                  input=canonical_bytes(binding), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  timeout=30, cwd=str(BASE.parent), env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'})
            if proc.returncode or len(proc.stdout) > OUTPUT_BYTES:
                raise ValueError('M16_READER_REFUSED')
            payload = json.loads(proc.stdout)
            verify_runtime()
            _check_child(payload, binding)
        except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired):
            payload = unavailable('M16_SAVED_RESULT_REJECTED', status='CANNOT_CONFIRM')
    record = dict(schema_version='v5.module_response.v1', module_id=config['module_id'], release_id=config['release_id'],
                  path=ROUTE, query=query, payload=payload, payload_sha256=sha256_json(payload),
                  source_input_sha256=binding['commit_file_sha256'] if binding else sha256_json(payload),
                  data_kind=binding['data_kind'] if binding else 'OWNER_RESULT',
                  generated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), status_code=200)
    from .module_api import _validate_record
    return _validate_record(config, record, ROUTE, query), sha256_json(record)

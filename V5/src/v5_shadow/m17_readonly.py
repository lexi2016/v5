"""Exact-run M17 GET adapter. No owner, collector, claim or finish path.

The frozen original reader validates products in a new interpreter per GET.
Only synthetic tests create products. This module never publishes or schedules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v5_shadow.composition import no_symlinks
from v5_shadow.contracts import exact_keys, trade_date
from v5_shadow.digests import canonical_bytes
from v5_shadow.run_ledger import identity_key, read_run
from v5_shadow.daily_close_recapture_owner import _config, _read_file, _audit_guard

BASE = Path(__file__).resolve().parents[2]
ROUTE = '/api/v5/manager/close-recapture'
MAX_RESPONSE_BYTES = 256 * 1024
MAX_CONFIG_BYTES = 32 * 1024
FLAGS = dict(RESEARCH_ONLY=True, production_allowed=False, buy_gate_updated=False,
             orders_sent=False, natural_verified=False, formal_eligibility_verified=False)
KEYS = ('schema_version', 'state_root', 'universe_root', 'ledger_root', 'python_executable',
        'identity', 'run_id', 'execution_label', 'operation')


def _refs(date):
    prefix = f'workbench_research/{date}/'
    return dict(artifact=prefix+'close_recapture.json', receipt=prefix+'close_recapture.receipt.json',
                snapshot=prefix+'inputs/close_recapture_pytdx.json',
                candidate_overlay=prefix+'close_recapture.candidates.json')


def validate_binding(config):
    """Explicit isolated roots and all seven original ledger identity fields."""
    exact_keys(config, KEYS)
    if (config['schema_version'] != 'v5.m17.readonly-binding.v1'
            or config['execution_label'] != 'MANUAL_RECOVERY'
            or config['operation'] != 'EXISTING_VERIFIED_PRODUCT_REUSE'):
        raise ValueError('M17_READONLY_BINDING')
    if len(canonical_bytes(config)) > MAX_CONFIG_BYTES:
        raise ValueError('M17_READONLY_CONFIG_LIMIT')
    identity_key(config['identity'])
    if config['identity']['lane'] != 'manager_close_recapture':
        raise ValueError('M17_READONLY_LANE')
    if not isinstance(config['run_id'], str) or not re.fullmatch('[0-9a-f]{32}', config['run_id']):
        raise ValueError('M17_READONLY_RUN_ID')
    roots = [no_symlinks(Path(config[k])) for k in ('state_root','universe_root','ledger_root')]
    for i, root in enumerate(roots):
        for other in roots[i+1:]:
            if root.is_relative_to(other) or other.is_relative_to(root):
                raise ValueError('M17_READONLY_ROOT_OVERLAP')
    # Reuse the existing 24-file manifest, root marker, and interpreter checks.
    runtime = dict(capture_mode='PYTDX_LATE_OBSERVATION',
        owner_root=str(BASE/'vendor/close_discovery_baseline'),
        python=config['python_executable'], state_root=config['state_root'],
        universe_root=config['universe_root'],
        source_manifest=str(BASE/'contracts/close_recapture_source_manifest.json'), timeout_seconds=30)
    _config(runtime)
    return runtime


def _saved(config, state):
    saved = state.get('latest_success') if isinstance(state, dict) else None
    if (not isinstance(saved, dict) or saved.get('run_id') != config['run_id']
            or saved.get('status') != 'SUCCEEDED' or saved.get('readback_verified') is not True
            or not isinstance(state.get('attempts'), list)
            or not any(a == saved for a in state['attempts'])):
        raise ValueError('M17_READONLY_SAVED_SUCCESS_REQUIRED')
    ref = saved.get('product_reference')
    if (not isinstance(ref, dict) or ref.get('ledger_run_id') != config['run_id']
            or ref.get('source_trade_date') != config['identity']['target_date']
            or ref.get('request_sha256') != config['identity']['input_sha256']
            or ref.get('root') != config['state_root']
            or ref.get('owner_status') not in {'READY','PARTIAL'}
            or any(ref.get(k) is not v for k,v in FLAGS.items() if k != 'formal_eligibility_verified')):
        raise ValueError('M17_READONLY_PRODUCT_IDENTITY')
    files = ref.get('files')
    if not isinstance(files, dict) or set(files) != set(_refs(config['identity']['target_date'])):
        raise ValueError('M17_READONLY_FILES')
    for key, path in _refs(config['identity']['target_date']).items():
        item = files[key]
        if (not isinstance(item, dict) or item.get('artifact_ref') != path
                or not isinstance(item.get('sha256'), str)
                or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
            raise ValueError('M17_READONLY_FILE_REFERENCE')
    return ref


def _redact(value, roots):
    if isinstance(value, str):
        if value.startswith(('/', 'file://', '\\\\')) or re.match(r'^[A-Za-z]:[\\/]', value):
            return '<redacted>'
        for root in roots:
            value = value.replace(root, '<redacted>')
        # Free-form original fields can embed an unrelated private path.
        return re.sub(r"(?<![A-Za-z0-9_./-])(?:file://[^\s\"'<>]+|/(?!/)[^\s\"'<>]+|[A-Za-z]:[\\/][^\s\"'<>]+|\\\\[^\s\"'<>]+)",
                      '<redacted>', value)
    if isinstance(value, list):
        return [_redact(v, roots) for v in value]
    if isinstance(value, dict):
        return {_redact(k, roots): _redact(v, roots) for k,v in value.items()}
    return value


def _worker(packet):
    config, ref = packet['config'], packet['reference']
    runtime = validate_binding(config)
    state_root = Path(config['state_root']); date = config['identity']['target_date']
    # Existing reader guard is reused unchanged. It is not an OS sandbox claim.
    _audit_guard('reader', state_root)
    sys.path.insert(0, runtime['owner_root'])
    from apps.api.v35_api.manager_workbench_router import ManagerWorkbenchResearchReader
    from ops.materialize_manager_close_discovery import _read_close_recapture_pool
    expected = _refs(date)

    def read_hashes():
        return {key: dict(artifact_ref=path,
                    sha256=hashlib.sha256(_read_file(state_root/path)).hexdigest())
                for key,path in expected.items()}

    if read_hashes() != ref['files']:
        raise ValueError('M17_READONLY_FILES_CHANGED')
    value = ManagerWorkbenchResearchReader(state_root).read_close_recapture(date)
    if value['status'] not in {'READY','PARTIAL'}:
        raise ValueError('M17_READONLY_ORIGINAL_READER_REJECTED')
    pool, _ = _read_close_recapture_pool(Path(config['universe_root'])/'.runtime/data', date)
    if pool != value['pool'] or pool != ref['pool']:
        raise ValueError('M17_READONLY_EXTERNAL_POOL_CHANGED')
    rows = value['candidate_overlay']['rows']
    if (not 1 <= len(rows) <= 100 or len(rows) != ref['candidate_count']
            or value['plan_trade_date'] != ref['plan_trade_date']
            or value['status'] != ref['owner_status']
            or value['request']['captured_at'] != ref['captured_at']
            or value['request']['available_at'] != ref['available_at']
            or value['cannot_confirm'] != ref['cannot_confirm']
            or value['received_not_historical_1530'] is not True
            or read_hashes() != ref['files']):
        raise ValueError('M17_READONLY_PRODUCT_CHANGED')
    result = dict(schema_version='v5.m17.readonly-response.v1', status=value['status'],
        source_trade_date=date, plan_trade_date=value['plan_trade_date'], run_id=config['run_id'],
        identity=config['identity'], execution_kind=ref['execution_kind'],
        execution_label=config['execution_label'], operation=config['operation'],
        captured_at=value['request']['captured_at'], available_at=value['request']['available_at'],
        received_not_historical_1530=True, candidate_count=len(rows), rows=rows,
        files=ref['files'], pool=pool, cannot_confirm=value['cannot_confirm'],
        bar_window=value['bar_window'], coverage=value['coverage'],
        source=value['source'], reader_pid=os.getpid(), **FLAGS)
    result = _redact(result, [config[k] for k in ('state_root','universe_root','ledger_root','python_executable')]
                     + [str(BASE)])
    if len(canonical_bytes(result)) > MAX_RESPONSE_BYTES:
        raise ValueError('M17_READONLY_RESPONSE_LIMIT')
    return result


def read_m17(config, *, source_trade_date, run_id):
    """Read only this explicit source date and exact successful original run."""
    validate_binding(config)
    trade_date(source_trade_date)
    if source_trade_date != config['identity']['target_date'] or run_id != config['run_id']:
        raise ValueError('M17_READONLY_EXACT_REFERENCE_REQUIRED')
    before = read_run(config['ledger_root'], config['identity'])
    reference = _saved(config, before)
    try:
        child = subprocess.run([config['python_executable'], '-I', '-B', str(Path(__file__).resolve()), '--worker'],
            input=canonical_bytes(dict(config=config, reference=reference)), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=30, cwd=str(BASE),
            env={'PATH':os.defpath, 'PYTHONDONTWRITEBYTECODE':'1'})
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError('M17_READONLY_READER_UNAVAILABLE') from error
    if len(child.stdout) > MAX_RESPONSE_BYTES:
        raise ValueError('M17_READONLY_RESPONSE_LIMIT')
    if child.returncode:
        # The isolated worker emits only a bounded, allowlisted reason code;
        # preserve that cause instead of collapsing every rejection to one code.
        try:
            failure = json.loads(child.stdout)
            code = failure.get('reason_code') if isinstance(failure, dict) else None
        except (UnicodeError, json.JSONDecodeError):
            code = None
        if isinstance(code, str) and re.fullmatch(r'M17_READONLY_[A-Z0-9_]{1,80}', code):
            raise ValueError(code)
        raise ValueError('M17_READONLY_READER_REJECTED')
    try:
        result = json.loads(child.stdout)
        if (result['schema_version'] != 'v5.m17.readonly-response.v1'
                or result['source_trade_date'] != source_trade_date or result['run_id'] != run_id
                or result['identity'] != config['identity'] or result['files'] != reference['files']
                or result['status'] not in {'READY','PARTIAL'}
                or not 1 <= len(result['rows']) <= 100
                or result['candidate_count'] != len(result['rows'])
                or any(result.get(k) is not v for k,v in FLAGS.items())):
            raise ValueError('M17_READONLY_RESPONSE_MISMATCH')
    except (KeyError, TypeError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('M17_READONLY_RESPONSE_INVALID') from error
    if read_run(config['ledger_root'], config['identity']) != before:
        raise ValueError('M17_READONLY_LEDGER_CHANGED')
    if len(canonical_bytes(result)) > MAX_RESPONSE_BYTES:
        raise ValueError('M17_READONLY_RESPONSE_LIMIT')
    return result


def get_response(config, query):
    """Host GET contract; no shared route registry is modified by this candidate."""
    exact_keys(query, ('source_trade_date', 'run_id'))
    return read_m17(config, source_trade_date=query['source_trade_date'], run_id=query['run_id'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--source-trade-date')
    parser.add_argument('--run-id')
    args = parser.parse_args(argv)
    try:
        if args.worker:
            raw = sys.stdin.buffer.read(1024*1024+1)
            if len(raw) > 1024*1024: raise ValueError('M17_READONLY_PACKET_LIMIT')
            result = _worker(json.loads(raw))
        else:
            if args.config is None or args.source_trade_date is None or args.run_id is None:
                parser.error('--config, --source-trade-date and --run-id are required')
            raw = _read_file(args.config)
            if len(raw) > MAX_CONFIG_BYTES: raise ValueError('M17_READONLY_CONFIG_LIMIT')
            result = read_m17(json.loads(raw), source_trade_date=args.source_trade_date, run_id=args.run_id)
        print(canonical_bytes(result).decode())
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        # Return only a stable reason code; never expose paths or child tracebacks.
        code = str(error)
        if not re.fullmatch(r'M17_READONLY_[A-Z0-9_]{1,80}', code):
            code = 'M17_READONLY_REFERENCE_REJECTED'
        print(json.dumps({'status': 'REJECTED', 'reason_code': code}, separators=(',', ':')))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

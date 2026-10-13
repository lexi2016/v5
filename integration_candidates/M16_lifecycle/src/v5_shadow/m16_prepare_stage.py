"""Prepare private M16 observation bytes from an exact verified M08 saved run.

Read-only at the source. Never starts a selector, manager service, provider,
model, job, network request, import, or latest-pointer operation. New output
files are preparation only and must not be confused with a historical product.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from .manager_loader import load_owner
from .m16_runtime import ROOT, closure, MAX_INPUT_BYTES

DEPENDENCY_SHA256 = '9734257087ad36c94c809c5acd372c1c51201f49606b053ebc9db2879e130723'
STAGE = 'STAGE_0935_0940'
FLAGS = ('production_allowed', 'buy_gate_updated', 'orders_sent')
OBSERVED = dict(data_kind='OWNER_RESULT', evidence_mode='HISTORICAL', qualification='OBSERVED_ONLY',
                natural_verified=False, pit_verified=False, formal_admission=False,
                raw_input_verified=False, computation_replayed=False,
                market_data_authenticity_verified=False)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def checked_path(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('M16_PREPARE_PATH_REFUSED')
    return path


def read_bytes(path):
    path = checked_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError('M16_PREPARE_REGULAR_FILE_REQUIRED')
        raw = handle.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError('M16_PREPARE_FILE_TOO_LARGE')
    return raw


def read_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: raise ValueError('M16_PREPARE_DUPLICATE_KEY')
            out[key] = value
        return out
    def constant(_): raise ValueError('M16_PREPARE_NONFINITE')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    canonical(value)
    return value


def verified_reader():
    raw = read_bytes(ROOT / 'M08_READONLY_DEPENDENCY.json')
    if sha256(raw).hexdigest() != DEPENDENCY_SHA256:
        raise ValueError('M16_M08_DEPENDENCY_MANIFEST_HASH')
    manifest = read_json(raw)
    root = checked_path(ROOT / 'source/m08_readonly')
    expected = set()
    for item in manifest['entries']:
        rel = item['path']
        if not isinstance(rel, str) or Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise ValueError('M16_M08_DEPENDENCY_PATH')
        data = read_bytes(root / rel)
        if len(data) != item['bytes'] or sha256(data).hexdigest() != item['sha256']:
            raise ValueError('M16_M08_DEPENDENCY_BYTES')
        expected.add(rel)
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() or p.is_symlink()}
    if actual != expected:
        raise ValueError('M16_M08_DEPENDENCY_FILESET')
    return root / manifest['read_entry']


def read_saved_stage(recorded_root, reference_path):
    root = checked_path(recorded_root)
    reference_path = checked_path(reference_path)
    reference_raw = read_bytes(reference_path)
    reference = read_json(reference_raw)
    if (not isinstance(reference, dict) or reference.get('schema_version') != 'v5.hk_stage_observed_reference.v1'
            or reference.get('stage_id') != STAGE or reference.get('market') != 'HK_CONNECT'):
        raise ValueError('M16_EXACT_M08_0935_REFERENCE_REQUIRED')
    reader = verified_reader()
    # Invoke the already-existing M08 READ entry, never init/import/prepare/producer.
    proc = subprocess.run([sys.executable, '-I', '-B', str(reader), 'read', '--root', str(root),
                           '--reference', str(reference_path), '--include-artifact'],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=75)
    if proc.returncode or len(proc.stdout) > MAX_INPUT_BYTES:
        raise ValueError('M16_M08_COMMITTED_READ_REJECTED')
    value = read_json(proc.stdout)
    if (value.get('reference') != reference or value.get('read_status') != 'VERIFIED'
            or any(value.get(flag) is not False for flag in (*FLAGS, 'natural_verified'))
            or any(value.get('provenance', {}).get(k) != v for k, v in OBSERVED.items())
            or value['provenance'].get('captured_at') is not None):
        raise ValueError('M16_M08_READ_BOUNDARY')
    if read_bytes(reference_path) != reference_raw:
        raise ValueError('M16_M08_REFERENCE_CHANGED')
    verified_reader()
    return value, sha256(reference_raw).hexdigest()


def prepare(recorded_root, reference_path, output_directory):
    output = checked_path(output_directory)
    for protected in (checked_path(recorded_root), ROOT):
        if output == protected or protected in output.parents or output in protected.parents:
            raise ValueError('M16_PREPARE_OUTPUT_MUST_BE_SEPARATE')
    if output.exists(): raise ValueError('M16_PREPARE_OUTPUT_EXISTS')
    checked_path(output.parent)
    if not output.parent.is_dir(): raise ValueError('M16_PREPARE_OUTPUT_PARENT_MISSING')
    value, reference_file_sha = read_saved_stage(recorded_root, reference_path)
    artifact = value['artifact']; ref = value['reference']; provenance = value['provenance']
    if (artifact.get('trade_date') != ref['target_date'] or artifact.get('stage_id') != STAGE
            or artifact.get('market') != 'HK_CONNECT' or artifact.get('run_id') != ref['run_id']
            or any(artifact.get(k) is not False for k in FLAGS)
            or not re.fullmatch('[0-9a-f]{64}', str(artifact.get('raw_artifact_sha256', '')))):
        raise ValueError('M16_STAGE_ARTIFACT_IDENTITY')
    # Preserve every original field and every complete row. Only provide the two
    # existing M16 contract aliases, without reordering/filtering/capping rows.
    observation = json.loads(canonical(artifact))
    for name, expected in [('target_trade_date', artifact['trade_date']), ('status', artifact['selection_status'])]:
        if name in observation and observation[name] != expected:
            raise ValueError('M16_STAGE_ALIAS_CONFLICT')
        observation[name] = expected
    # Carry original observed-only limits outside rows, without promoting a row
    # or rewriting its saved historical eligibility/evidence/time.
    for key, expected in OBSERVED.items():
        if key in observation and observation[key] != expected:
            raise ValueError('M16_STAGE_OBSERVED_BOUNDARY_CONFLICT')
        observation[key] = expected
    load_owner(closure())  # Trusted contract import only; no service is constructed.
    contracts = importlib.import_module('m16_owner_manager_research.contracts')
    normalized = contracts.normalise_observation_input(observation)
    if (normalized['input_source_sha256'] != artifact['raw_artifact_sha256']
            or normalized['input_row_count'] != len(artifact['rows'])):
        raise ValueError('M16_STAGE_CONTRACT_BINDING')
    raw = canonical(observation)
    if len(raw) > MAX_INPUT_BYTES: raise ValueError('M16_PREPARE_INPUT_TOO_LARGE')
    receipt = dict(schema_version='v5.m16.stage_input_preparation.v1', status='PREPARED_NOT_RUN',
        prepared_at=datetime.now(timezone.utc).isoformat(), input_file='observation.json',
        input_file_sha256=sha256(raw).hexdigest(), input_bytes=len(raw), input_identity=normalized['input_identity'],
        input_identity_origin='ORIGINAL_M16_CONTRACT_FROM_NEW_EXPORTED_INPUT',
        target_trade_date=normalized['target_trade_date'], stage_id=STAGE, market='HK_CONNECT',
        source_raw_artifact_sha256=normalized['input_source_sha256'], source_artifact_id=normalized['source_artifact_id'],
        source_artifact_file_sha256=provenance['original_reference']['artifact_sha256'],
        source_reference_file_sha256=reference_file_sha, source_reference=ref,
        source_provenance=provenance, source_rows=len(artifact['rows']),
        prior_product_identity_claimed=False, manager_job_started=False,
        network_called=False, model_called=False, **OBSERVED, **{k: False for k in FLAGS})
    # Exclusive destination, source never written. Receipt is the final marker;
    # an interrupted preparation without it must not be treated as complete.
    output.mkdir(mode=0o700, exist_ok=False)
    for name, data in [('observation.json', raw), ('receipt.json', canonical(receipt))]:
        with (output / name).open('xb') as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
    if read_bytes(output / 'observation.json') != raw or read_json(read_bytes(output / 'receipt.json')) != receipt:
        raise ValueError('M16_PREPARE_OUTPUT_READBACK')
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recorded-root', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = prepare(args.recorded_root, args.reference, args.output_directory)
    # Keep original evidence/private paths in local files, not command output.
    print(canonical({k: receipt[k] for k in ('status', 'input_file', 'input_file_sha256',
          'input_identity', 'target_trade_date', 'stage_id', 'source_rows', 'manager_job_started')}).decode())
    return 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (ValueError, OSError, subprocess.TimeoutExpired):
        print('{"status":"BLOCKED","reason":"M16_STAGE_INPUT_PREPARATION_REJECTED"}')
        raise SystemExit(1)

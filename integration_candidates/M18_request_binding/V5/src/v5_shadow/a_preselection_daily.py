"""M05 daily bridge: frozen read-only assembly, then an independent strict writer.

Only synthetic or recorded replay requests supported by the original assembler
are accepted. The caller supplies all five gate identity fields; this module
never creates permits or opens gates. M07 binding remains WAIT_INTEGRATION.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Mapping

from .a_preselection import BASE, DESCRIPTOR_SHA256, SAFETY, _request
from .a_preselection import run_a_preselection as _default_run_a_preselection
from .composition import no_symlinks, shadow_root
from .digests import MAX_JSON_BYTES, canonical_bytes, sha256_json

LANE_POOLS = {
    'v192': 'a_d1_premarket_pool',
    'fupan': 'a_d1_fupan_watchlist_pool',
    'stage7': 'a_d1_stage7_fenshi_review_pool',
    'research': 'a_share_research_recommendation_pool',
    'baimao': 'a_share_baimao_research_map',
    'wechat': 'wechat_public_account_v3_preselect',
}
A_POOL_IDS = frozenset(LANE_POOLS.values())
CONTEXT_FIELDS = frozenset(('control_dir', 'expected_permit_sha256',
    'expected_owner_id', 'expected_release_sha256', 'expected_root'))


class M05WriterError(ValueError):
    """Preserve a precise writer exception across the process boundary."""
    def __init__(self, remote_type, message):
        super().__init__(remote_type + ':' + message)
        self.remote_type = remote_type
        self.remote_message = message


class M05PublicationError(ValueError):
    """An immutable conflict is a failed publication with all sibling results."""
    def __init__(self, result):
        super().__init__('conflicting preselection-pool materialization')
        self.result = result
        self.results = result['outcomes']


def _context_binding(value):
    if not isinstance(value, Mapping) or set(value) != CONTEXT_FIELDS:
        raise ValueError('M05_CONTEXT_FIELDS_REQUIRED')
    result = dict(value)
    for field in ('control_dir', 'expected_root'):
        path = result[field]
        if isinstance(path, Path):
            path = str(path)
        if not isinstance(path, str) or not path or not Path(path).is_absolute() or '..' in Path(path).parts:
            raise ValueError('M05_CONTEXT_PATH_REQUIRED:' + field)
        result[field] = path
    for field in CONTEXT_FIELDS - {'control_dir', 'expected_root'}:
        if not isinstance(result[field], str) or not result[field]:
            raise ValueError('M05_CONTEXT_VALUE_REQUIRED:' + field)
    canonical_bytes(result)
    return result


def _validate_required_root(private_root, source_root, lane_roots=(), code_root=None, v4_root=None):
    if private_root is None or source_root is None:
        raise ValueError('M05_ROOT_BINDING_REQUIRED')
    out = shadow_root(Path(private_root))
    roots = [source_root, code_root, v4_root, str(BASE), *lane_roots]
    for value in roots:
        if not isinstance(value, (str, Path)) or not str(value) or not Path(value).is_absolute():
            raise ValueError('M05_OWNER_ROOT_BINDING_REQUIRED')
        root = no_symlinks(Path(value))
        if root == out or root in out.parents or out in root.parents:
            raise ValueError('M05_ROOT_OVERLAP')
    return out


def _validate_assembly(request, result):
    if not isinstance(result, Mapping) or result.get('request_sha256') != sha256_json(request):
        raise ValueError('M05_REQUEST_IDENTITY_MISMATCH')
    if result.get('schema_version') != 'v5.a_preselection_assembly.v1':
        raise ValueError('M05_SCHEMA_MISMATCH')
    if (result.get('source_capsule_sha256') != DESCRIPTOR_SHA256
            or any(result.get(k) != v for k, v in SAFETY.items())
            or any(result.get(k) != request[k] for k in ('target_date', 'signal_date', 'data_kind'))):
        raise ValueError('M05_ASSEMBLY_IDENTITY_MISMATCH')
    lanes = result.get('lanes')
    if not isinstance(lanes, list) or [x.get('kind') for x in lanes] != [x['kind'] for x in request['lanes']]:
        raise ValueError('M05_ASSEMBLY_LANES_MISMATCH')
    for lane in lanes:
        if type(lane.get('accepted')) is not bool:
            raise ValueError('M05_LANE_ACCEPTANCE_INVALID')
        artifact = lane.get('artifact')
        if lane['accepted'] and not isinstance(artifact, Mapping):
            raise ValueError('M05_ACCEPTED_WITHOUT_ARTIFACT')
        if isinstance(artifact, Mapping):
            if artifact.get('trade_date') != request['target_date']:
                raise ValueError('M05_TRADE_DATE_MISMATCH')
            if artifact.get('pool_id') != LANE_POOLS[lane['kind']]:
                raise ValueError('M05_LANE_POOL_MISMATCH')
            if artifact.get('market') != 'A':
                raise ValueError('M05_MARKET_MISMATCH')
            if lane['accepted'] and artifact.get('source_role') == 'EXPECTED_MISSING':
                raise ValueError('M05_MISSING_CANNOT_BE_SUCCESS')
    canonical_bytes(result)


def _outcome(lane, status, **extra):
    result = {key: lane.get(key) for key in ('kind', 'accepted', 'reason')}
    result['status'] = status
    if not lane.get('accepted') and 'artifact' in lane:
        result['artifact'] = lane['artifact']
    for key in ('rejected_artifact', 'rejected_artifact_tagged', 'rejected_artifact_status'):
        if key in lane:
            result[key] = lane[key]
    result.update(extra)
    return result


def _run_writer(envelope):
    worker = Path(__file__).with_name('a_preselection_writer.py')
    worker_sha = hashlib.sha256(worker.read_bytes()).hexdigest()
    envelope = dict(envelope, writer_implementation_sha256=worker_sha)
    with tempfile.TemporaryDirectory(prefix='v5-m05-writer-cache-') as cache:
        process = subprocess.run([sys.executable, '-I', '-B', '-X',
            'pycache_prefix=' + str(Path(cache).resolve()), str(worker), '--worker'],
            input=canonical_bytes(envelope), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=120)
    if len(process.stdout) > MAX_JSON_BYTES:
        raise ValueError('M05_WRITER_OUTPUT_TOO_LARGE')
    try:
        response = json.loads(process.stdout)
    except (ValueError, UnicodeError) as error:
        raise ValueError('M05_WRITER_RESPONSE_INVALID:' + process.stderr.decode(errors='replace')[-2000:]) from error
    if process.returncode != 0:
        raise M05WriterError(response.get('error_type', 'WriterFailure'), response.get('error', 'M05_WRITER_FAILED'))
    if (response.get('request_sha256') != sha256_json(envelope['request'])
            or response.get('writer_implementation_sha256') != worker_sha
            or hashlib.sha256(worker.read_bytes()).hexdigest() != worker_sha):
        raise ValueError('M05_WRITER_IDENTITY_MISMATCH')
    return response


def build_m05_daily(request, *, source_root=None, private_root=None,
                    code_root=None, v4_root=None, write_gate_context=None,
                    run_a_preselection=None):
    """Publish M05 pools using the default frozen factory, without host imports.

    ``write_gate_context`` is a mapping with exactly the five StoreGateContext
    fields. The real context object is created only inside the writer process.
    ``run_a_preselection`` is a test seam; production uses the original worker.
    No store instance crosses this boundary.
    """
    request = json.loads(canonical_bytes(request))
    lane_roots = [lane.get('input_root') for lane in request.get('lanes', [])]
    out = _validate_required_root(private_root, source_root, lane_roots, code_root, v4_root)
    request = _request(request)
    context = _context_binding(write_gate_context)
    result = (run_a_preselection or _default_run_a_preselection)(request)
    _validate_assembly(request, result)
    response = _run_writer(dict(request=request, assembly=result,
        roots=dict(private_root=str(out), source_root=str(source_root),
                   code_root=str(code_root), v4_root=str(v4_root)),
        write_gate_context=context))
    if response['status'] == 'CONFLICT':
        raise M05PublicationError(response)
    return response

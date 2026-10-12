"""M09 same-day close research: admitted inputs, immutable runs and read-only heads.

This module never collects data, changes BUY, schedules itself or writes V4.
The original deterministic producer/store live in the separately pinned M09
capsule. A successful engineering calculation is not natural-run/PIT evidence.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import subprocess
import sys
import traceback
from types import CodeType
from uuid import uuid4

from .contracts import aware, sha, trade_date as checked_date
from .digests import canonical_bytes, sha256_json
from . import a_close_daily_sources as frozen

TZ = timezone(timedelta(hours=8))
SLOTS = ('16:05', '17:10')
SAFETY = dict(research_only=True, production_allowed=False, buy_gate_updated=False, orders_sent=False)
ROOT_MARKERS = {'.v5-shadow-root': b'v5.shadow-root.v1\n', '.v5-m09-root': b'v5.m09-root.v1\n'}
COLUMNS = ('trade_date', 'ts_code', 'name', 'pct_chg', 'amount', 'bar_close_pos', 'tdx_industry_code', 'tdx_industry_name')
EVIDENCE_ROLES = ('stage_evidence', 'video_acceptance', 'video_capture', 'stockdict_pointer', 'ocr_alignment_pointer', 'video_gap_pointer')
MAX_PANEL_BYTES = 128 * 1024 * 1024
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_ROWS = 20000
_WORKER_TIMEOUT = 120
_IMPLEMENTATION_PATHS = ('a_close_daily.py', 'a_close_daily_sources.py', 'a_close_daily_worker.py', 'a_close_historical.py', 'contracts.py', 'digests.py')
# A long-lived dispatcher must restart when any loaded implementation changes.
# Hashing only at run time would attest bytes which this process never loaded.
_IMPORTED_IMPLEMENTATION = {
    name: frozen._regular_snapshot(Path(__file__).absolute().parent / name, max_bytes=1024 * 1024)[1]['sha256']
    for name in _IMPLEMENTATION_PATHS
}
_SHARED_SOURCE_BASELINE = {
    'contracts.py': 'eee026873e0d765fcedf52077daea823edf6ee7013f37c106c82b66a4582d85a',
    'digests.py': '134b1a13b7ff677afef6f556e2a750d94cc54a396cbdcff111c5d67e645280e5',
}


def _now():
    return datetime.now(timezone.utc)


def _raw_sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    def reject(value):
        raise ValueError('NONFINITE_JSON:' + value)
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('DUPLICATE_JSON_KEY:' + key)
            value[key] = item
        return value
    return json.loads(raw, parse_constant=reject, object_pairs_hook=pairs)


def _absolute_root(root):
    value = str(root)
    path = Path(value)
    if (not path.is_absolute() or path == Path('/') or '\\' in value or '\x00' in value
            or '..' in value.split('/') or '~' in path.parts):
        raise ValueError('M09_ROOT_INVALID')
    # Do not resolve first: doing so would erase a symlink from the evidence.
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError('M09_SYMLINK_REJECTED')
    return path


def _relative(value):
    if (not isinstance(value, str) or not value or '\\' in value or '\x00' in value
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('M09_RELATIVE_PATH_INVALID')
    p, win = PurePosixPath(value), PureWindowsPath(value)
    if p.is_absolute() or win.drive or win.root:
        raise ValueError('M09_RELATIVE_PATH_INVALID')
    return value


def _source_io(root):
    path = _absolute_root(root)
    handle = frozen.safe_root(path)
    with handle.directory():
        pass
    return path, handle


def _private_io(root):
    path, handle = _source_io(root)
    try:
        for name, value in ROOT_MARKERS.items():
            if handle.read_bytes(name, max_bytes=100) != value:
                raise ValueError('M09_ROOT_MARKER_INVALID')
    except (OSError, ValueError) as exc:
        raise ValueError('M09_ROOT_NOT_INITIALIZED:' + str(exc)) from exc
    return path, handle


def initialize_a_close_root(root):
    """Explicitly initialize one new/empty private M09 directory, never a store."""
    path = _absolute_root(root)
    parent = frozen.safe_root(path.parent)
    with parent.directory() as fd:
        try:
            os.mkdir(path.name, mode=0o700, dir_fd=fd)
        except FileExistsError:
            pass
    handle = frozen.safe_root(path)
    with handle.directory() as fd:
        present = os.listdir(fd)
        if present:
            if set(ROOT_MARKERS) <= set(present):
                _private_io(path)
                return {'status': 'ALREADY_INITIALIZED', 'schema_version': 'v5.m09-root.v1'}
            raise ValueError('M09_ROOT_NOT_EMPTY')
        meta = os.fstat(fd)
        if meta.st_mode & 0o077:
            raise ValueError('M09_ROOT_MUST_BE_PRIVATE')
    for name, value in ROOT_MARKERS.items():
        handle.write_bytes(name, value, require_absent=True)
    return {'status': 'INITIALIZED', 'schema_version': 'v5.m09-root.v1'}


def _date_slot(target, slot):
    checked_date(target)
    if slot not in SLOTS:
        raise ValueError('M09_SLOT_INVALID')
    states = frozen.market_states(target)
    if states.get('a_share') != 'FULL_TRADING_DAY':
        raise ValueError('M09_MARKET_NOT_OPEN')
    return datetime.strptime(target + ' ' + slot, '%Y%m%d %H:%M').replace(tzinfo=TZ)


def _request(value):
    required = {'schema_version', 'trade_date', 'slot', 'job_id', 'attempt_id', 'execution_kind',
                'triggered_at', 'source_root', 'input_manifest', 'input_manifest_sha256', 'configuration_revision'}
    if not isinstance(value, dict) or not required <= set(value) or set(value) - required - {'expected_generation_sha256'}:
        raise ValueError('M09_REQUEST_FIELDS')
    value = _json(canonical_bytes(value))
    if value['schema_version'] != 'v5.m09.daily_request.v1':
        raise ValueError('M09_REQUEST_SCHEMA')
    cutoff = _date_slot(value['trade_date'], value['slot'])
    for key in ('job_id', 'attempt_id', 'configuration_revision'):
        if not isinstance(value[key], str) or re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', value[key]) is None:
            raise ValueError('M09_REQUEST_IDENTIFIER:' + key)
    if value['execution_kind'] not in ('ENGINEERING', 'RECORDED_INPUT_REPLAY', 'MANUAL_RECOVERY', 'NATURAL'):
        raise ValueError('M09_EXECUTION_KIND')
    triggered = aware(value['triggered_at'])
    now = _now()
    if triggered > now:
        raise ValueError('M09_TRIGGER_IN_FUTURE')
    if value['execution_kind'] != 'ENGINEERING' and cutoff > now:
        raise ValueError('M09_RESEARCH_SLOT_IN_FUTURE')
    if value['execution_kind'] == 'NATURAL':
        # A scheduler claim still needs independent Mac evidence. These checks
        # prevent a historical/manual call from claiming a current natural slot.
        if (triggered.astimezone(TZ).strftime('%Y%m%d') != value['trade_date']
                or now.astimezone(TZ).strftime('%Y%m%d') != value['trade_date']):
            raise ValueError('M09_NATURAL_DATE_MISMATCH')
        end = cutoff.replace(hour=17, minute=10) if value['slot'] == '16:05' else cutoff.replace(hour=23, minute=59, second=59)
        if not cutoff <= triggered <= now <= end:
            raise ValueError('M09_MISSED_OR_EARLY_SLOT')
    _absolute_root(value['source_root'])
    _relative(value['input_manifest'])
    sha(value['input_manifest_sha256'])
    if value.get('expected_generation_sha256') is not None:
        sha(value['expected_generation_sha256'])
    return value, cutoff


class _InputError(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__('M09_INPUT_NOT_ADMITTED:' + ','.join(dict.fromkeys(x['code'] for x in issues)))


def _time_pair(meta, target, cutoff, label, issues, *, post_close=False):
    try:
        captured = aware(meta.get('captured_at'))
        available = aware(meta.get('available_at'))
        if (captured.astimezone(TZ).strftime('%Y%m%d') != target
                or available.astimezone(TZ).strftime('%Y%m%d') != target or not captured <= available <= cutoff):
            raise ValueError('DATE_OR_ORDER_OR_CUTOFF')
        if post_close and captured.astimezone(TZ).strftime('%H:%M:%S') < '15:00:00':
            raise ValueError('BEFORE_CLOSE')
        if meta.get('acquired_at') is not None:
            acquired = aware(meta['acquired_at'])
            if acquired.astimezone(TZ).strftime('%Y%m%d') != target or acquired > available:
                raise ValueError('ACQUISITION_ORDER')
        return captured, available
    except (TypeError, ValueError) as exc:
        issues.append({'code': label + '_TIME_INVALID_OR_UNKNOWN', 'detail': str(exc)})
        return None


def _json_pointer(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/') or len(pointer) > 512:
        raise ValueError('SOURCE_RECEIPT_FIELD_POINTER')
    for key in pointer[1:].split('/'):
        key = key.replace('~1', '/').replace('~0', '~')
        if not isinstance(value, dict) or key not in value:
            raise ValueError('SOURCE_RECEIPT_FIELD_MISSING:' + pointer)
        value = value[key]
    return value


def _panel_rows(raw, panel_format, data_kind):
    if panel_format == 'SYNTHETIC_JSON':
        if data_kind != 'SYNTHETIC':
            raise ValueError('SYNTHETIC_JSON_NOT_REAL_INPUT')
        rows = _json(raw)
        if not isinstance(rows, list):
            raise ValueError('PANEL_ROWS_TYPE')
        return rows, 'SYNTHETIC_JSON_ENGINEERING_ONLY'
    if panel_format != 'PARQUET':
        raise ValueError('PANEL_FORMAT_INVALID')
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ValueError('PARQUET_ENGINE_UNAVAILABLE:' + str(exc)) from exc
    # Decode the immutable bytes already read through SafeRoot, never a second
    # path read. Check declared sizes/types before materializing the table.
    parquet = pq.ParquetFile(pa.BufferReader(raw))
    if not 1 <= parquet.metadata.num_rows <= MAX_ROWS:
        raise ValueError('PANEL_ROW_LIMIT')
    if sum(parquet.metadata.row_group(i).total_byte_size for i in range(parquet.num_row_groups)) > 256 * 1024 * 1024:
        raise ValueError('PANEL_UNCOMPRESSED_LIMIT')
    schema = parquet.schema_arrow
    if not set(COLUMNS) <= set(schema.names):
        raise ValueError('PANEL_FIELDS_MISSING')
    for name in COLUMNS:
        dtype = schema.field(name).type
        good = (pa.types.is_integer(dtype) or pa.types.is_floating(dtype)) if name in ('pct_chg', 'amount', 'bar_close_pos') else (pa.types.is_string(dtype) or pa.types.is_large_string(dtype))
        if not good:
            raise ValueError('PANEL_ARROW_TYPE:' + name + ':' + str(dtype))
    return parquet.read(columns=list(COLUMNS)).to_pylist(), str(schema)


def _admit(source_root, manifest_path, manifest_sha, target, slot, *, execution_kind=None):
    cutoff = _date_slot(target, slot)
    root, source = _source_io(source_root)
    files, issues = {}, []

    def read(relative, expected, limit=MAX_JSON_BYTES):
        _relative(relative); sha(expected)
        raw = source.read_bytes(relative, max_bytes=limit)
        if _raw_sha(raw) != expected:
            raise ValueError('SOURCE_SHA_MISMATCH:' + relative)
        if relative in files and files[relative]['sha256'] != expected:
            raise ValueError('SOURCE_ALIAS_CONFLICT:' + relative)
        files[relative] = {'raw': raw, 'sha256': expected, 'bytes': len(raw)}
        return raw

    manifest = _json(read(manifest_path, manifest_sha))
    if isinstance(manifest, dict) and manifest.get('schema_version') == 'v5.m09.historical_input.v1':
        from .a_close_historical import admit_historical
        return admit_historical(source_root, manifest_path, manifest_sha, target, slot, execution_kind)
    required = {'schema_version', 'trade_date', 'data_kind', 'panel', 'membership', 'provenance', 'evidence'}
    if not isinstance(manifest, dict) or set(manifest) != required or manifest['schema_version'] != 'v5.m09.input.v1':
        raise ValueError('INPUT_MANIFEST_FIELDS')
    if manifest['trade_date'] != target:
        raise ValueError('INPUT_MANIFEST_DATE')
    kind = manifest['data_kind']
    if kind not in ('REAL', 'RECORDED_INPUT_REPLAY', 'SYNTHETIC'):
        raise ValueError('INPUT_DATA_KIND')
    panel, membership, provenance = (manifest[name] for name in ('panel', 'membership', 'provenance'))
    if not all(isinstance(x, dict) for x in (panel, membership, provenance)):
        raise ValueError('INPUT_SECTION_TYPE')
    pointer = read(panel['pointer_path'], panel['pointer_sha256'], 8192)
    target_path = pointer.decode('utf-8-sig').strip()
    if Path(target_path).is_absolute():
        absolute = _absolute_root(target_path)
        try:
            target_path = absolute.relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError('PANEL_POINTER_OUTSIDE_SOURCE_ROOT') from exc
    _relative(target_path)
    panel_raw = read(target_path, panel['sha256'], MAX_PANEL_BYTES)
    members_raw = read(membership['path'], membership['sha256'], 2 * 1024 * 1024)
    members = members_raw.decode('utf-8-sig').splitlines()
    if (not 1 <= len(members) <= MAX_ROWS or len(set(members)) != len(members)
            or any(re.fullmatch(r'[0-9]{6}\.(SH|SZ|BJ)', x) is None for x in members)):
        issues.append({'code': 'MEMBERSHIP_INVALID'})
    if membership.get('scope') != 'DECLARED_UNIVERSE':
        issues.append({'code': 'FULL_MARKET_MEMBERSHIP_NOT_PROVEN'})
    for label, meta in (('SOURCE', provenance), ('MEMBERSHIP', membership)):
        if any(not isinstance(meta.get(k), str) or not meta[k].strip() for k in ('source_id', 'version')):
            issues.append({'code': label + '_IDENTITY_MISSING'})
        _time_pair(meta, target, cutoff, label, issues, post_close=(label == 'SOURCE'))
    if provenance.get('status') != 'READY' or provenance.get('authority_status') != 'VERIFIED':
        issues.append({'code': 'SOURCE_AUTHORITY_NOT_READY', 'status': provenance.get('status'), 'authority_status': provenance.get('authority_status')})
    coverage = provenance.get('coverage_rate')
    if type(coverage) not in (int, float) or not math.isfinite(coverage) or coverage != 1:
        issues.append({'code': 'SOURCE_COVERAGE_INCOMPLETE', 'coverage_rate': coverage})
    try:
        receipt = _json(read(provenance['receipt_path'], provenance['receipt_sha256']))
        mapping = provenance.get('receipt_fields', {})
        if not isinstance(mapping, dict):
            raise ValueError('SOURCE_RECEIPT_MAPPING_INVALID')
        fields = dict(trade_date=target, **{k: provenance.get(k) for k in ('source_id', 'version', 'status', 'authority_status', 'coverage_rate', 'captured_at', 'available_at', 'acquired_at')})
        for key, expected in fields.items():
            if _json_pointer(receipt, mapping.get(key, '/' + key)) != expected:
                raise ValueError('SOURCE_RECEIPT_FIELD_MISMATCH:' + key)
    except (KeyError, TypeError, OSError, ValueError) as exc:
        issues.append({'code': 'SOURCE_RECEIPT_NOT_BOUND', 'detail': str(exc)})
    rows, schema, decoded = [], None, False
    try:
        rows, schema = _panel_rows(panel_raw, panel['format'], kind)
        decoded = True
        if not 1 <= len(rows) <= MAX_ROWS or type(panel.get('row_count')) is not int or len(rows) != panel['row_count']:
            issues.append({'code': 'PANEL_ROW_COUNT_MISMATCH', 'actual': len(rows), 'declared': panel.get('row_count')})
        seen = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not set(COLUMNS) <= set(row):
                issues.append({'code': 'PANEL_FIELDS_MISSING', 'row': index}); continue
            if type(row['trade_date']) is not str or row['trade_date'] != target:
                issues.append({'code': 'PANEL_ROW_DATE', 'row': index})
            code = row['ts_code']
            if not isinstance(code, str) or re.fullmatch(r'[0-9]{6}\.(SH|SZ|BJ)', code) is None:
                issues.append({'code': 'PANEL_CODE_INVALID', 'row': index})
            seen.append(code)
            for key in ('pct_chg', 'amount', 'bar_close_pos'):
                value = row[key]
                if type(value) not in (int, float) or not math.isfinite(value) or (key == 'amount' and value < 0) or (key == 'bar_close_pos' and not 0 <= value <= 1):
                    issues.append({'code': 'PANEL_NUMBER_INVALID', 'field': key, 'row': index})
            for key in ('name', 'tdx_industry_code', 'tdx_industry_name'):
                if not isinstance(row[key], str) or not row[key].strip():
                    issues.append({'code': 'PANEL_TEXT_MISSING', 'field': key, 'row': index})
        if len(set(map(str, seen))) != len(seen) or set(map(str, seen)) != set(members) or len(rows) != len(members):
            issues.append({'code': 'PANEL_DECLARED_MEMBERSHIP_MISMATCH'})
    except (KeyError, TypeError, OSError, ValueError) as exc:
        issues.append({'code': 'PANEL_DECODE_OR_FORMAT_FAILED', 'detail': str(exc)})
    evidence_status, context = {}, {}
    evidence = manifest['evidence']
    if not isinstance(evidence, dict) or set(evidence) - set(EVIDENCE_ROLES):
        raise ValueError('EVIDENCE_ROLES_INVALID')
    for role in EVIDENCE_ROLES:
        ref = evidence.get(role)
        if ref is None:
            evidence_status[role] = {'status': 'MISSING', 'reason': 'NO_COMMITTED_REFERENCE'}
            continue
        try:
            if not isinstance(ref, dict) or ref.get('trade_date') != target:
                raise ValueError('EVIDENCE_DATE_OR_TYPE')
            if any(not isinstance(ref.get(k), str) or not ref[k] for k in ('source_id', 'version')):
                raise ValueError('EVIDENCE_SOURCE_IDENTITY')
            if ref.get('available_at') is None or ref.get('captured_at') is None:
                evidence_status[role] = {'status': 'UNKNOWN', 'reason': 'SOURCE_TIME_UNKNOWN'}
                continue
            capture, available = aware(ref['captured_at']), aware(ref['available_at'])
            if not capture <= available or capture.astimezone(TZ).strftime('%Y%m%d') != target or available.astimezone(TZ).strftime('%Y%m%d') != target:
                raise ValueError('EVIDENCE_TIME_ORDER_OR_DAY')
            if available > cutoff:
                evidence_status[role] = {'status': 'TOO_LATE', 'reason': 'AVAILABLE_AFTER_SLOT_CUTOFF', 'available_at': ref['available_at']}
                continue
            payload = _json(read(ref['path'], ref['sha256']))
            if not isinstance(payload, dict):
                raise ValueError('EVIDENCE_PAYLOAD_TYPE')
            for date_key in ('trade_date', 'target_date', 'review_date'):
                if date_key in payload and payload[date_key] != target:
                    raise ValueError('EVIDENCE_PAYLOAD_DATE')
            evidence_status[role] = {'status': 'AVAILABLE', 'source_id': ref['source_id'], 'version': ref['version'], 'sha256': ref['sha256'], 'captured_at': ref['captured_at'], 'available_at': ref['available_at'], 'semantic_consumption_verified': False}
            if role != 'stage_evidence':
                context[role] = payload
        except (KeyError, TypeError, OSError, ValueError) as exc:
            evidence_status[role] = {'status': 'INVALID', 'reason': str(exc)}
    diagnostic = {'schema_version': 'v5.m09.admission.v1', 'admitted': not issues, 'trade_date': target,
                  'slot': slot, 'cutoff': cutoff.isoformat(), 'data_kind': kind, 'issues': issues,
                  'row_count': len(rows) if decoded else None, 'panel_decoded': decoded,
                  'declared_panel_row_count': panel.get('row_count'), 'declared_member_count': len(members), 'panel_schema': schema,
                  'scope': 'DECLARED_UNIVERSE_ONLY', 'source_provenance_independently_verified': False,
                  'strict_1500_pit_verified': False, 'evidence_status': evidence_status}
    return {'diagnostic': diagnostic, 'rows': rows, 'panel_raw': panel_raw, 'manifest': manifest, 'panel_source_path': target_path,
            'source': source, 'files': files, 'context': context, 'source_root': root}


def diagnose_a_close_input(source_root, manifest_path, expected_manifest_sha256, trade_date, slot):
    """Read-only diagnosis; no normalization, product writes or data collection."""
    try:
        return _admit(source_root, manifest_path, expected_manifest_sha256, trade_date, slot)['diagnostic']
    except (KeyError, TypeError, OSError, ValueError) as exc:
        return {'schema_version': 'v5.m09.admission.v1', 'admitted': False, 'trade_date': trade_date,
                'slot': slot, 'issues': [{'code': 'INPUT_INTEGRITY_OR_CONTRACT_FAILED', 'detail': str(exc)}]}


def _verify_inputs(admitted):
    for path, item in admitted['files'].items():
        try:
            raw = admitted['source'].read_bytes(path, max_bytes=max(len(item['raw']), 1))
        except (OSError, ValueError) as exc:
            raise ValueError('SOURCE_CHANGED_DURING_COMPUTE:' + path) from exc
        if raw != item['raw']:
            raise ValueError('SOURCE_CHANGED_DURING_COMPUTE:' + path)


def _environment():
    versions = {}
    for name in ('pandas', 'pyarrow'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    def pair(v):
        try:
            return tuple(int(x) for x in v.split('.')[:2])
        except (AttributeError, ValueError):
            return (0, 0)
    compatible = sys.version_info >= (3, 14) and (2, 3) <= pair(versions['pandas']) < (3, 0) and (21, 0) <= pair(versions['pyarrow']) < (25, 0)
    return {'python': sys.version.split()[0], 'executable': sys.executable, **versions,
            'declared_environment_compatible': compatible, 'os_compatibility_independently_verified': False}


def _implementation_identity():
    directory = Path(__file__).parent
    current = {name: frozen._regular_snapshot(directory / name, max_bytes=1024 * 1024)[1]['sha256'] for name in _IMPLEMENTATION_PATHS}
    if current != _IMPORTED_IMPLEMENTATION:
        raise ValueError('M09_LOADED_IMPLEMENTATION_CHANGED_RESTART_REQUIRED')
    bindings = {'contracts.py': {'aware': aware, 'sha': sha, 'trade_date': checked_date},
                'digests.py': {'canonical_bytes': canonical_bytes, 'sha256_json': sha256_json}}
    # Other V5 code may have imported these shared helpers before daily. Do
    # not reload or mutate a shared module: compare the functions actually
    # bound here to code compiled from the fixed, independently hashed bytes.
    for name, functions in bindings.items():
        if current[name] != _SHARED_SOURCE_BASELINE[name]:
            raise ValueError('M09_SHARED_HELPER_BASELINE_CHANGED_REBASE_REQUIRED:' + name)
        raw, meta = frozen._regular_snapshot(directory / name, retain=True, max_bytes=1024 * 1024)
        if meta['sha256'] != current[name]:
            raise ValueError('M09_SHARED_HELPER_CHANGED_DURING_VERIFICATION:' + name)
        representative = next(iter(functions.values()))
        code = compile(raw, representative.__code__.co_filename, 'exec', dont_inherit=True)
        expected = {item.co_name: item for item in code.co_consts if isinstance(item, CodeType)}
        module = sys.modules[__package__ + '.' + name[:-3]]
        if any(getattr(module, key, None) is not function or function.__code__ != expected.get(key)
               for key, function in functions.items()):
            raise ValueError('M09_CACHED_SHARED_HELPER_MISMATCH_RESTART_REQUIRED:' + name)
    if sys.modules[__package__ + '.digests'].MAX_JSON_BYTES != MAX_JSON_BYTES:
        raise ValueError('M09_CACHED_SHARED_HELPER_CONSTANT_MISMATCH')
    return {'capsule': frozen.sources_identity(), 'modules': current, 'environment': _environment()}


def _build(run_root, target, pointer, rows, panel_sha, run_id, context, *, historical_replay=False):
    request = dict(run_root=str(run_root), trade_date=target, panel_pointer=str(pointer), rows=rows,
                   panel_sha256=panel_sha, run_id=run_id, context=context, expected_implementation_identity=_implementation_identity())
    if historical_replay:
        request['rows'] = frozen.encode_rows(rows)
        request['historical_replay'] = True
    try:
        process = subprocess.run([sys.executable, '-I', '-B', str(Path(__file__).with_name('a_close_daily_worker.py'))],
                                 input=canonical_bytes(request), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 timeout=_WORKER_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = exc.stdout or b'', exc.stderr or b''
        raise ValueError('M09_WORKER_TIMEOUT:stdout=' + stdout.decode(errors='replace')[-2000:] + ';stderr=' + stderr.decode(errors='replace')[-4000:]) from exc
    if len(process.stdout) > MAX_JSON_BYTES:
        raise ValueError('M09_WORKER_OUTPUT_TOO_LARGE')
    if process.returncode:
        raise ValueError('M09_WORKER_FAILED:exit=' + str(process.returncode) + ';stdout=' + process.stdout.decode(errors='replace')[-4000:] + ';stderr=' + process.stderr.decode(errors='replace')[-8000:])
    try:
        result = _json(process.stdout)
    except (ValueError, UnicodeError) as exc:
        raise ValueError('M09_WORKER_RESPONSE_INVALID:stderr=' + process.stderr.decode(errors='replace')[-4000:]) from exc
    if not isinstance(result, dict) or set(result) != {'review', 'publication'} or not all(isinstance(result[k], dict) for k in result):
        raise ValueError('M09_WORKER_RESPONSE_CONTRACT')
    return result


def _read_optional(handle, relative):
    try:
        return _json(handle.read_bytes(relative, max_bytes=MAX_JSON_BYTES))
    except FileNotFoundError:
        return None


def _head(handle, target):
    value = _read_optional(handle, 'heads/' + target + '.json')
    if value is None:
        return None
    if not isinstance(value, dict) or value.get('trade_date') != target or value.get('schema_version') != 'v5.m09.head.v1':
        raise ValueError('M09_HEAD_INVALID')
    return sha(value['generation_sha256'])


def _read_run(root, handle, run_id, record_sha):
    if not isinstance(run_id, str) or re.fullmatch(r'm09-[0-9a-f]{32}-[0-9a-f]{12}', run_id) is None:
        raise ValueError('M09_RUN_ID_INVALID')
    prefix = 'runs/' + run_id
    raw_record = handle.read_bytes(prefix + '/record.json', max_bytes=MAX_JSON_BYTES)
    record = _json(raw_record)
    if _raw_sha(raw_record) != record_sha or sha256_json(record) != record_sha or record.get('run_id') != run_id or record.get('schema_version') != 'v5.m09.record.v1':
        raise ValueError('M09_RECORD_DIGEST_OR_IDENTITY')
    target = checked_date(record['trade_date'])
    # A verified output also commits its calculation and the exact retained
    # evidence. Do not promote a payload whose immutable input history is lost.
    calculation_raw = handle.read_bytes(prefix + '/calculation.json', max_bytes=MAX_JSON_BYTES)
    calculation = _json(calculation_raw)
    if (_raw_sha(calculation_raw) != record['calculation_sha256']
            or sha256_json(calculation) != record['calculation_sha256']
            or calculation.get('schema_version') != 'v5.m09.calculation.v1'
            or not run_id.startswith('m09-' + record['calculation_sha256'][:32] + '-')
            or any(calculation.get(key) != record.get(key) for key in ('trade_date', 'data_kind', 'execution_kind', 'scope', 'evidence_status'))
            or calculation.get('implementation') != record['implementation_identity']):
        raise ValueError('M09_CALCULATION_DIGEST_OR_IDENTITY')
    source_files = calculation['source_files']
    manifest_path = _relative(calculation['input_manifest_path'])
    panel_source_path = _relative(calculation['panel_source_path'])
    retained = record['input_files']
    if not isinstance(source_files, dict) or not isinstance(retained, dict):
        raise ValueError('M09_INPUT_SNAPSHOT_MANIFEST')
    panel_relative = 'inputs/admitted_panel' + ('.parquet' if calculation['panel_format'] == 'PARQUET' else '.json')
    required_inputs = {'inputs/source/' + _relative(name): meta for name, meta in source_files.items()}
    if (set(retained) != set(required_inputs) | {panel_relative, 'inputs/producer_pointer.txt'}
            or any(retained[name] != meta for name, meta in required_inputs.items())):
        raise ValueError('M09_INPUT_SNAPSHOT_SET_OR_METADATA')
    saved = {}
    for name, expected in retained.items():
        _relative(name)
        if (not isinstance(expected, dict) or set(expected) != {'sha256', 'bytes'}
                or type(expected['bytes']) is not int or not 0 <= expected['bytes'] <= MAX_PANEL_BYTES):
            raise ValueError('M09_INPUT_SNAPSHOT_METADATA')
        sha(expected['sha256'])
        raw = handle.read_bytes(prefix + '/' + name, max_bytes=max(expected['bytes'], 1))
        if _raw_sha(raw) != expected['sha256'] or len(raw) != expected['bytes']:
            raise ValueError('M09_INPUT_SNAPSHOT_DIGEST:' + name)
        # Retain only the small manifest and two pointers after hashing.
        if name in ('inputs/source/' + manifest_path, 'inputs/producer_pointer.txt'):
            saved[name] = raw
    manifest_raw = saved['inputs/source/' + manifest_path]
    manifest = _json(manifest_raw)
    if (_raw_sha(manifest_raw) != calculation['input_manifest_sha256']
            or manifest.get('trade_date') != target or manifest.get('data_kind') != record['data_kind']
            or manifest['panel']['format'] != calculation['panel_format']
            or manifest['panel']['sha256'] != source_files[panel_source_path]['sha256']
            or retained[panel_relative] != source_files[panel_source_path]
            or manifest['membership'] != record['membership'] or manifest['provenance'] != record['provenance']):
        raise ValueError('M09_SAVED_INPUT_MANIFEST_RELATIONSHIP')
    for section, file_key, digest_key in (('panel', 'pointer_path', 'pointer_sha256'),
                                        ('membership', 'path', 'sha256'), ('provenance', 'receipt_path', 'receipt_sha256')):
        meta = manifest[section]
        if source_files[_relative(meta[file_key])]['sha256'] != meta[digest_key]:
            raise ValueError('M09_SAVED_SOURCE_RELATIONSHIP:' + section)
    pointer_raw = handle.read_bytes(prefix + '/inputs/source/' + manifest['panel']['pointer_path'], max_bytes=8192)
    source_target = pointer_raw.decode('utf-8-sig').strip()
    if Path(source_target).is_absolute():
        source_target = _absolute_root(source_target).relative_to(_absolute_root(calculation['source_root_at_admission'])).as_posix()
    if _relative(source_target) != panel_source_path:
        raise ValueError('M09_SAVED_SOURCE_POINTER_RELATIONSHIP')
    # Absolute legacy producer pointers are retained as historical bytes. Bind
    # the original run location recorded at write time, without dereferencing it
    # during read-back (an exported immutable archive can therefore be read).
    expected_pointer = (record['run_root_at_creation'] + '/' + panel_relative + '\n').encode()
    if saved['inputs/producer_pointer.txt'] != expected_pointer:
        raise ValueError('M09_SAVED_PRODUCER_POINTER_RELATIONSHIP')
    for path, expected in record['store_files'].items():
        _relative(path)
        raw = handle.read_bytes(prefix + '/product/' + path, max_bytes=MAX_JSON_BYTES)
        if _raw_sha(raw) != expected['sha256'] or len(raw) != expected['bytes']:
            raise ValueError('M09_STORE_RAW_DIGEST:' + path)
    if manifest.get('schema_version') == 'v5.m09.historical_input.v1':
        from .a_close_historical import admit_historical
        checked = admit_historical(root / prefix / 'inputs/source', manifest_path,
                                   calculation['input_manifest_sha256'], target, '16:05', 'RECORDED_INPUT_REPLAY')
        if (record.get('data_kind') != 'RECORDED_INPUT_REPLAY' or record.get('execution_kind') != 'HISTORICAL_REPLAY'
                or record.get('scope') != 'OBSERVED_ROWS_ONLY'
                or record.get('historical_research') != checked['diagnostic']['historical_research']
                or record.get('natural_verified') is not False or record.get('strict_1500_pit_verified') is not False):
            raise ValueError('M09_HISTORICAL_RECORD_IDENTITY')
    # A newly constructed original Store reads payload/receipt/manifest together.
    review = frozen.read_original_review(root / prefix / 'product', target)
    if (not isinstance(review, dict) or sha256_json(review) != record['review_sha256']
            or review.get('source_sha256') != record['source_sha256']
            or review.get('trade_date') != target or review['model_review'].get('run_id') != run_id
            or review['model_review'].get('review_date') != target or record['safety'] != SAFETY):
        raise ValueError('M09_REVIEW_IDENTITY_OR_SAFETY')
    return review, record


def _generation(handle, target, digest):
    raw = handle.read_bytes('generations/' + digest + '.json', max_bytes=MAX_JSON_BYTES)
    generation = _json(raw)
    if (_raw_sha(raw) != digest or sha256_json(generation) != digest or generation.get('trade_date') != target
            or generation.get('schema_version') != 'v5.m09.generation.v1'):
        raise ValueError('M09_GENERATION_IDENTITY')
    for key in ('record_sha256', 'commit_trigger_sha256', 'commit_request_sha256'):
        sha(generation[key])
    if generation['previous_generation_sha256'] is not None:
        sha(generation['previous_generation_sha256'])
    return generation


def _attempt_start(handle, target, trigger_sha):
    start = _read_optional(handle, 'attempts/' + trigger_sha + '/started.json')
    if (not isinstance(start, dict) or set(start) != {'schema_version', 'trigger', 'request_sha256', 'started_at'}
            or start['schema_version'] != 'v5.m09.attempt_start.v1'):
        raise ValueError('M09_ATTEMPT_START_IDENTITY')
    trigger = start['trigger']
    keys = {'trade_date', 'slot', 'job_id', 'attempt_id', 'execution_kind', 'triggered_at'}
    if (not isinstance(trigger, dict) or set(trigger) != keys or trigger['trade_date'] != target
            or sha256_json(trigger) != sha(trigger_sha)
            or trigger['execution_kind'] not in ('ENGINEERING', 'RECORDED_INPUT_REPLAY', 'MANUAL_RECOVERY', 'NATURAL')):
        raise ValueError('M09_ATTEMPT_START_IDENTITY')
    cutoff = _date_slot(target, trigger['slot'])
    for key in ('job_id', 'attempt_id'):
        if not isinstance(trigger[key], str) or re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', trigger[key]) is None:
            raise ValueError('M09_ATTEMPT_TRIGGER_IDENTIFIER')
    sha(start['request_sha256'])
    triggered, started = aware(trigger['triggered_at']), aware(start['started_at'])
    # Source availability belongs to the historical cutoff. Actual attempts may
    # run later: never compare an engineering/replay start with that cutoff.
    if not triggered <= started <= _now():
        raise ValueError('M09_ATTEMPT_TIME_ORDER')
    if trigger['execution_kind'] == 'NATURAL':
        end = cutoff.replace(hour=17, minute=10) if trigger['slot'] == '16:05' else cutoff.replace(hour=23, minute=59, second=59)
        if not cutoff <= triggered <= started <= end:
            raise ValueError('M09_NATURAL_ATTEMPT_TIME')
    request = _read_optional(handle, 'attempts/' + trigger_sha + '/request.json')
    if request is not None and (not isinstance(request, dict) or sha256_json(request) != start['request_sha256']
            or any(request.get(key) != value for key, value in trigger.items())):
        raise ValueError('M09_ATTEMPT_REQUEST_IDENTITY')
    return start, cutoff, request


def _verify_calculation_request(handle, receipt, request, record):
    calculation = _read_optional(handle, 'runs/' + receipt['run_id'] + '/calculation.json')
    for key in ('trade_date', 'input_manifest_sha256', 'input_manifest_path', 'configuration_revision', 'source_root_at_admission'):
        request_key = {'input_manifest_path': 'input_manifest', 'source_root_at_admission': 'source_root'}.get(key, key)
        if calculation.get(key) != request.get(request_key):
            raise ValueError('M09_ATTEMPT_CALCULATION_REQUEST:' + key)
    expected_class = ('ENGINEERING' if request['execution_kind'] == 'ENGINEERING' else
                      'HISTORICAL_REPLAY' if request['execution_kind'] == 'RECORDED_INPUT_REPLAY' else 'DAILY_RESEARCH')
    if record['execution_kind'] != expected_class:
        raise ValueError('M09_ATTEMPT_EXECUTION_CLASS')


def _verify_committed_success(handle, target, receipt):
    generation = _generation(handle, target, receipt['generation_sha256'])
    if any(generation.get(key) != receipt[key] for key in ('run_id', 'record_sha256')):
        raise ValueError('M09_ATTEMPT_GENERATION_IDENTITY')
    # SafeRoot carries the real private root. Never pass None to the cold store.
    _, record = _read_run(handle.root, handle, receipt['run_id'], receipt['record_sha256'])
    for key in ('calculation_sha256', 'business_status', 'data_kind', 'evidence_status'):
        if record.get(key) != receipt[key]:
            raise ValueError('M09_ATTEMPT_RECORD_IDENTITY:' + key)
    request = _read_optional(handle, 'attempts/' + receipt['trigger_sha256'] + '/request.json')
    if request is None:
        # Pre-upgrade committing receipts have no archived request. Their exact
        # generation still binds the trigger/request and verified original run.
        # Unbound legacy reuse stays UNKNOWN; it cannot borrow another commit.
        if (generation['commit_trigger_sha256'] != receipt['trigger_sha256']
                or generation['commit_request_sha256'] != receipt['request_sha256']):
            raise ValueError('M09_ATTEMPT_REQUEST_UNVERIFIED')
    else:
        _verify_calculation_request(handle, receipt, request, record)
    witness = _attempt_receipt(handle, target, generation['commit_trigger_sha256'], verify_success=False)
    if (witness['status'] != 'SUCCEEDED' or witness['request_sha256'] != generation['commit_request_sha256']
            or any(witness.get(key) != receipt[key] for key in ('run_id', 'record_sha256', 'generation_sha256', 'calculation_sha256'))):
        raise ValueError('M09_ATTEMPT_COMMIT_WITNESS')
    if (generation['commit_trigger_sha256'] != receipt['trigger_sha256'] and not receipt['reused']):
        raise ValueError('M09_ATTEMPT_REUSE_IDENTITY')
    if not aware(record['computed_at']) <= aware(generation['published_at']) <= aware(witness['finished_at']) <= aware(receipt['finished_at']):
        raise ValueError('M09_ATTEMPT_PUBLICATION_TIME_ORDER')


def _attempt_receipt(handle, target, trigger_sha, *, verify_success=True):
    sha(trigger_sha)
    start, cutoff, _ = _attempt_start(handle, target, trigger_sha)
    receipt = _read_optional(handle, 'attempts/' + trigger_sha + '/receipt.json')
    common = dict(schema_version='v5.m09.trigger_receipt.v1', trade_date=target,
                  slot=start['trigger']['slot'], cutoff=cutoff.isoformat(), trigger=start['trigger'],
                  trigger_sha256=trigger_sha, request_sha256=start['request_sha256'],
                  started_at=start['started_at'], natural_verified=False, safety=dict(SAFETY))
    if receipt is None:
        return dict(common, status='UNKNOWN', reason='ATTEMPT_STARTED_WITHOUT_TERMINAL_RECEIPT')
    if (not isinstance(receipt, dict) or any(receipt.get(key) != value for key, value in common.items())
            or receipt.get('natural_verified') is not False
            or not isinstance(receipt.get('safety'), dict) or set(receipt['safety']) != set(SAFETY)
            or any(receipt['safety'][key] is not value for key, value in SAFETY.items())):
        raise ValueError('M09_ATTEMPT_RECEIPT_IDENTITY')
    if not aware(start['started_at']) <= aware(receipt.get('finished_at')) <= _now():
        raise ValueError('M09_ATTEMPT_TIME_ORDER')
    status = receipt.get('status')
    terminal = set(common) | {'status', 'finished_at'}
    if status == 'SUCCEEDED':
        required = {'reused', 'run_id', 'calculation_sha256', 'record_sha256', 'generation_sha256',
                    'business_status', 'data_kind', 'evidence_status'}
        if set(receipt) != terminal | required or type(receipt['reused']) is not bool:
            raise ValueError('M09_ATTEMPT_SUCCESS_FIELDS')
        for key in ('calculation_sha256', 'record_sha256', 'generation_sha256'):
            sha(receipt[key])
        if verify_success:
            _verify_committed_success(handle, target, receipt)
    elif status == 'FAILED':
        required = {'reason', 'run_id', 'previous_success_generation_sha256', 'publication_recovery_status', 'issues'}
        if (set(receipt) != terminal | required or not isinstance(receipt['reason'], str) or not receipt['reason']
                or not isinstance(receipt['issues'], list) or any(not isinstance(x, dict) for x in receipt['issues'])
                or not isinstance(receipt['publication_recovery_status'], str)):
            raise ValueError('M09_ATTEMPT_FAILURE_FIELDS')
        if receipt['run_id'] is not None and (not isinstance(receipt['run_id'], str)
                or re.fullmatch(r'm09-[0-9a-f]{32}-[0-9a-f]{12}', receipt['run_id']) is None):
            raise ValueError('M09_ATTEMPT_RUN_ID')
        if receipt['previous_success_generation_sha256'] is not None:
            sha(receipt['previous_success_generation_sha256'])
    elif status == 'UNKNOWN':
        if set(receipt) != terminal | {'reason'} or receipt['reason'] != 'INTERRUPTED_ATTEMPT_REQUIRES_NEW_ATTEMPT_ID':
            raise ValueError('M09_ATTEMPT_UNKNOWN_FIELDS')
    else:
        raise ValueError('M09_ATTEMPT_STATUS')
    return receipt


def _is_committed(handle, target, digest, generation):
    receipt = _attempt_receipt(handle, target, generation['commit_trigger_sha256'])
    if receipt['request_sha256'] != generation['commit_request_sha256']:
        raise ValueError('M09_GENERATION_COMMIT_REQUEST')
    if receipt['status'] != 'SUCCEEDED':
        return False
    if (receipt.get('generation_sha256') != digest or receipt.get('run_id') != generation['run_id']
            or receipt.get('record_sha256') != generation['record_sha256']):
        raise ValueError('M09_GENERATION_COMMIT_RECEIPT')
    return True


def _read_generation_content(path, handle, target, digest, generation=None):
    generation = generation or _generation(handle, target, digest)
    review, record = _read_run(path, handle, generation['run_id'], sha(generation['record_sha256']))
    if record['trade_date'] != target:
        raise ValueError('M09_GENERATION_RECORD_DATE')
    identity = {'trade_date': target, 'model_run_id': record['run_id'], 'canonical_review_sha256': record['review_sha256'],
                'raw_review_sha256': record['store_files']['a_share_reviews/' + target + '.json']['sha256'],
                'source_sha256': record['source_sha256'], 'record_sha256': generation['record_sha256'], 'generation_sha256': digest}
    return {'review': review, 'record': record, 'generation': generation, 'identity': identity}


def _select_committed(path, handle, target, digest, *, explicit=False):
    cursor, skipped, seen = digest, [], set()
    while cursor is not None:
        if cursor in seen or len(seen) >= 1024:
            raise ValueError('M09_GENERATION_HISTORY_CYCLE_OR_LIMIT')
        seen.add(cursor)
        generation = _generation(handle, target, cursor)
        if _is_committed(handle, target, cursor, generation):
            return _read_generation_content(path, handle, target, cursor, generation), skipped
        if explicit:
            raise ValueError('M09_GENERATION_NOT_COMMITTED')
        skipped.append(cursor)
        cursor = generation['previous_generation_sha256']
    return None, skipped


def read_a_close_latest_attempt(root, trade_date):
    """Read attempt state separately; UNKNOWN never changes served success."""
    target = checked_date(trade_date)
    _, handle = _private_io(root)
    pointer = _read_optional(handle, 'attempt_heads/' + target + '.json')
    if pointer is None:
        return None
    if pointer.get('schema_version') != 'v5.m09.attempt_head.v1' or pointer.get('trade_date') != target:
        raise ValueError('M09_ATTEMPT_HEAD_IDENTITY')
    return _attempt_receipt(handle, target, pointer['trigger_sha256'])


def read_a_close_daily(root, trade_date, *, generation_sha256=None):
    """Read one exact-date committed generation; GET never repairs/writes state."""
    target = checked_date(trade_date)
    path, handle = _private_io(root)
    digest = _head(handle, target) if generation_sha256 is None else sha(generation_sha256)
    if digest is None:
        return None
    committed, skipped = _select_committed(path, handle, target, digest, explicit=generation_sha256 is not None)
    if committed is None:
        return None
    if skipped:
        committed['publication_recovery'] = dict(status='UNCOMMITTED_HEAD_NOT_SERVED', head_generation_sha256=digest,
                                                 skipped_generation_sha256=skipped,
                                                 served_generation_sha256=committed['identity']['generation_sha256'])
    try:
        committed['latest_attempt'] = read_a_close_latest_attempt(path, target)
    except (KeyError, TypeError, OSError, ValueError) as exc:
        committed['latest_attempt'] = dict(status='UNKNOWN', reason='LATEST_ATTEMPT_METADATA_INVALID:' + str(exc))
    return committed


def _restore_head(handle, target, expected, previous):
    if _head(handle, target) != expected:
        raise ValueError('M09_RECOVERY_CAS_CONFLICT')
    relative = 'heads/' + target + '.json'
    if previous is None:
        raw_head = canonical_bytes(dict(schema_version='v5.m09.head.v1', trade_date=target, generation_sha256=expected))
        if not handle.unlink_if_same(relative, raw_head):
            raise ValueError('M09_RECOVERY_CAS_CONFLICT')
    else:
        handle.write_bytes(relative, canonical_bytes(dict(schema_version='v5.m09.head.v1', trade_date=target, generation_sha256=previous)))


def _reconcile_interrupted_head(path, handle, target):
    head = _head(handle, target)
    if head is None:
        return
    current, skipped = _select_committed(path, handle, target, head)
    if not skipped:
        return
    previous = current['identity']['generation_sha256'] if current is not None else None
    recovery = dict(schema_version='v5.m09.recovery.v1', status='RECOVERY_PREPARED', trade_date=target,
                    interrupted_generation_sha256=head, served_generation_sha256=previous,
                    skipped_generation_sha256=skipped, started_at=_now().isoformat(), safety=dict(SAFETY))
    prefix = 'recoveries/' + sha256_json(recovery)
    handle.write_bytes(prefix + '/started.json', canonical_bytes(recovery), require_absent=True)
    _restore_head(handle, target, head, previous)
    recovery.update(status='INTERRUPTED_HEAD_RECONCILED', finished_at=_now().isoformat())
    handle.write_bytes(prefix + '/receipt.json', canonical_bytes(recovery), require_absent=True)


def _activate(handle, target, generation_sha, expected_head):
    if _head(handle, target) != expected_head:
        raise ValueError('M09_GENERATION_CAS_CONFLICT')
    handle.write_bytes('heads/' + target + '.json', canonical_bytes({'schema_version': 'v5.m09.head.v1', 'trade_date': target, 'generation_sha256': generation_sha}))


def run_a_close_daily(root, request):
    """Execute one explicit trigger. The caller owns scheduler/auth configuration."""
    request, cutoff = _request(request)
    path, handle = _private_io(root)
    from .a_close_historical import MARKER, MARKER_BYTES
    try:
        marker = handle.read_bytes(MARKER, max_bytes=100)
    except FileNotFoundError:
        marker = None
    if marker is not None and (marker != MARKER_BYTES or request['execution_kind'] != 'RECORDED_INPUT_REPLAY'):
        raise ValueError('M09_HISTORICAL_ROOT_REPLAY_ONLY')
    source_path = _absolute_root(request['source_root'])
    if source_path.is_relative_to(path) or path.is_relative_to(source_path):
        raise ValueError('M09_SOURCE_OUTPUT_OVERLAP')
    target = request['trade_date']
    trigger = {key: request[key] for key in ('trade_date', 'slot', 'job_id', 'attempt_id', 'execution_kind', 'triggered_at')}
    trigger_sha = sha256_json(trigger)
    attempt = 'attempts/' + trigger_sha
    request_sha = sha256_json(request)
    with handle.kernel_lock('locks/' + target + '.lock', timeout=30):
        existing = _read_optional(handle, attempt + '/receipt.json')
        if existing is not None:
            existing = _attempt_receipt(handle, target, trigger_sha)
            if existing['request_sha256'] != request_sha:
                raise ValueError('M09_ATTEMPT_IDENTITY_CONFLICT')
            if existing['status'] == 'SUCCEEDED':
                _, record = _read_run(path, handle, existing['run_id'], existing['record_sha256'])
                _verify_calculation_request(handle, existing, request, record)
            return existing
        previous_start = _read_optional(handle, attempt + '/started.json')
        if previous_start is not None:
            previous_start, _, _ = _attempt_start(handle, target, trigger_sha)
            if previous_start['request_sha256'] != request_sha:
                raise ValueError('M09_ATTEMPT_IDENTITY_CONFLICT')
        saved_request = _read_optional(handle, attempt + '/request.json')
        if saved_request is not None and saved_request != request:
            raise ValueError('M09_ATTEMPT_REQUEST_IDENTITY')
        _reconcile_interrupted_head(path, handle, target)
        if saved_request is None:
            handle.write_bytes(attempt + '/request.json', canonical_bytes(request), require_absent=True)
        start = {'schema_version': 'v5.m09.attempt_start.v1', 'trigger': trigger, 'request_sha256': request_sha, 'started_at': _now().isoformat()}
        if previous_start is None:
            handle.write_bytes(attempt + '/started.json', canonical_bytes(start), require_absent=True)
        elif previous_start.get('request_sha256') != request_sha:
            raise ValueError('M09_ATTEMPT_IDENTITY_CONFLICT')
        handle.write_bytes('attempt_heads/' + target + '.json', canonical_bytes(dict(
            schema_version='v5.m09.attempt_head.v1', trade_date=target, trigger_sha256=trigger_sha)))
        common = {'schema_version': 'v5.m09.trigger_receipt.v1', 'trade_date': target, 'slot': request['slot'], 'cutoff': cutoff.isoformat(),
                  'trigger': trigger, 'trigger_sha256': trigger_sha, 'request_sha256': request_sha,
                  'started_at': (previous_start or start)['started_at'], 'natural_verified': False, 'safety': dict(SAFETY)}
        if previous_start is not None:
            result = dict(common, status='UNKNOWN', reason='INTERRUPTED_ATTEMPT_REQUIRES_NEW_ATTEMPT_ID', finished_at=_now().isoformat())
            handle.write_bytes(attempt + '/receipt.json', canonical_bytes(result), require_absent=True)
            return result
        serving = _head(handle, target)
        run_id = None
        generation_sha = None
        try:
            if 'expected_generation_sha256' in request and request['expected_generation_sha256'] != serving:
                raise ValueError('M09_GENERATION_CAS_CONFLICT')
            admitted = _admit(source_path, request['input_manifest'], request['input_manifest_sha256'], target, request['slot'],
                              execution_kind=request['execution_kind'])
            historical_replay = admitted['manifest']['schema_version'] == 'v5.m09.historical_input.v1'
            if historical_replay and marker != MARKER_BYTES:
                raise ValueError('M09_HISTORICAL_ROOT_REQUIRED')
            handle.write_bytes(attempt + '/admission.json', canonical_bytes(admitted['diagnostic']), require_absent=True)
            if not admitted['diagnostic']['admitted']:
                raise _InputError(admitted['diagnostic']['issues'])
            kind = admitted['manifest']['data_kind']
            if (kind == 'SYNTHETIC') != (request['execution_kind'] == 'ENGINEERING'):
                raise ValueError('M09_DATA_EXECUTION_CLASS_MISMATCH')
            if kind == 'RECORDED_INPUT_REPLAY' and request['execution_kind'] != 'RECORDED_INPUT_REPLAY':
                raise ValueError('M09_RECORDED_INPUT_NOT_DAILY')
            classification = 'ENGINEERING' if kind == 'SYNTHETIC' else ('HISTORICAL_REPLAY' if request['execution_kind'] == 'RECORDED_INPUT_REPLAY' else 'DAILY_RESEARCH')
            implementation = _implementation_identity()
            computation = {'schema_version': 'v5.m09.calculation.v1', 'trade_date': target, 'data_kind': kind,
                           'execution_kind': classification, 'input_manifest_sha256': request['input_manifest_sha256'],
                           'input_manifest_path': request['input_manifest'], 'panel_source_path': admitted['panel_source_path'],
                           'panel_format': admitted['manifest']['panel']['format'], 'source_root_at_admission': str(source_path),
                           'source_files': {key: {k: v for k, v in value.items() if k != 'raw'} for key, value in admitted['files'].items()},
                           'evidence_status': admitted['diagnostic']['evidence_status'], 'implementation': implementation,
                           'configuration_revision': request['configuration_revision'], 'scope': admitted['diagnostic']['scope']}
            calculation_sha = sha256_json(computation)
            cached = _read_optional(handle, 'calculations/' + calculation_sha + '.json')
            reused = cached is not None
            if reused:
                if cached.get('calculation_sha256') != calculation_sha:
                    raise ValueError('M09_CALCULATION_INDEX_INVALID')
                run_id, record_sha = cached['run_id'], cached['record_sha256']
                _, record = _read_run(path, handle, run_id, record_sha)
                if record['calculation_sha256'] != calculation_sha:
                    raise ValueError('M09_CALCULATION_RECORD_MISMATCH')
            else:
                run_id = 'm09-' + calculation_sha[:32] + '-' + uuid4().hex[:12]
                prefix = 'runs/' + run_id
                handle.ensure_directory(prefix + '/product')
                input_files = {}
                for name, item in admitted['files'].items():
                    handle.write_bytes(prefix + '/inputs/source/' + name, item['raw'], require_absent=True)
                    input_files['inputs/source/' + name] = {'sha256': item['sha256'], 'bytes': item['bytes']}
                panel_extension = '.parquet' if admitted['manifest']['panel']['format'] == 'PARQUET' else '.json'
                panel_path = path / prefix / ('inputs/admitted_panel' + panel_extension)
                handle.write_bytes(prefix + '/inputs/admitted_panel' + panel_extension, admitted['panel_raw'], require_absent=True)
                input_files['inputs/admitted_panel' + panel_extension] = {'sha256': _raw_sha(admitted['panel_raw']), 'bytes': len(admitted['panel_raw'])}
                pointer_path = path / prefix / 'inputs/producer_pointer.txt'
                pointer_raw = (str(panel_path) + '\n').encode()
                handle.write_bytes(prefix + '/inputs/producer_pointer.txt', pointer_raw, require_absent=True)
                input_files['inputs/producer_pointer.txt'] = {'sha256': _raw_sha(pointer_raw), 'bytes': len(pointer_raw)}
                handle.write_bytes(prefix + '/calculation.json', canonical_bytes(computation), require_absent=True)
                build_options = {'historical_replay': True} if historical_replay else {}
                output = _build(path / prefix / 'product', target, pointer_path, admitted['rows'], admitted['manifest']['panel']['sha256'], run_id, admitted['context'], **build_options)
                review = frozen.read_original_review(path / prefix / 'product', target)
                if review != output['review'] or sha256_json(review) != output['publication']['sha256']:
                    raise ValueError('M09_INDEPENDENT_READBACK_MISMATCH')
                model = review['model_review']
                if (review['trade_date'] != target or model['review_date'] != target or model['run_id'] != run_id
                        or sum(model['market_summary'][k] for k in ('up_count', 'down_count', 'flat_count')) != len(admitted['rows'])
                        or model.get('semantic_model_call_count') != 0 or review['core_stocks'] != []):
                    raise ValueError('M09_ORIGINAL_OUTPUT_IDENTITY_OR_SAFETY')
                store_files = {}
                for name in ('a_share_reviews/' + target + '.json', 'a_share_reviews/receipts/' + target + '.json', 'a_share_reviews/manifest.json'):
                    raw = handle.read_bytes(prefix + '/product/' + name, max_bytes=MAX_JSON_BYTES)
                    store_files[name] = {'sha256': _raw_sha(raw), 'bytes': len(raw)}
                record = {'schema_version': 'v5.m09.record.v1', 'trade_date': target, 'run_id': run_id, 'calculation_sha256': calculation_sha,
                          'review_sha256': sha256_json(review), 'source_sha256': review['source_sha256'], 'store_files': store_files,
                          'input_files': input_files, 'run_root_at_creation': str(path / prefix),
                          'computed_at': _now().isoformat(), 'data_kind': kind, 'execution_kind': classification,
                          'business_status': 'PARTIAL', 'scope': admitted['diagnostic']['scope'], 'natural_verified': False,
                          'strict_1500_pit_verified': False, 'source_provenance_independently_verified': False,
                          'scenario_probabilities_status': 'FROZEN_LEGACY_CONSTANTS_NOT_CALIBRATED',
                          'legacy_as_of': model['as_of'], 'provenance': deepcopy(admitted['manifest']['provenance']),
                          'membership': deepcopy(admitted['manifest']['membership']), 'evidence_status': deepcopy(admitted['diagnostic']['evidence_status']),
                          'cannot_confirm': ['FULL_MARKET_MEMBERSHIP_NOT_VERIFIED', 'STRICT_1500_PIT_NOT_VERIFIED', 'NATURAL_TRIGGER_NOT_INDEPENDENTLY_VERIFIED'],
                          'implementation_identity': implementation, 'safety': dict(SAFETY)}
                if historical_replay:
                    record['historical_research'] = deepcopy(admitted['diagnostic']['historical_research'])
                    record['cannot_confirm'].extend(['HISTORICAL_RESEARCH_ONLY', 'SOURCE_TIME_UNKNOWN',
                        'SOURCE_AVAILABILITY_AT_SLOT_UNVERIFIED', 'OBSERVED_ROWS_ARE_NOT_QUALIFIED_MEMBERSHIP',
                        *record['historical_research']['affected_metrics']])
                record_sha = sha256_json(record)
                handle.write_bytes(prefix + '/record.json', canonical_bytes(record), require_absent=True)
                _read_run(path, handle, run_id, record_sha)
            _verify_inputs(admitted)
            if _implementation_identity() != implementation:
                raise ValueError('M09_IMPLEMENTATION_CHANGED_DURING_COMPUTE')
            if not reused:
                # This is an index of independently verified immutable objects,
                # not a claim that they are active. Save before the commit point.
                handle.write_bytes('calculations/' + calculation_sha + '.json', canonical_bytes({'calculation_sha256': calculation_sha, 'run_id': run_id, 'record_sha256': record_sha}), require_absent=True)
            current = read_a_close_daily(path, target) if serving is not None else None
            if current is not None and current['identity']['model_run_id'] == run_id:
                generation_sha = serving
            else:
                generation = {'schema_version': 'v5.m09.generation.v1', 'trade_date': target, 'run_id': run_id,
                              'record_sha256': record_sha, 'previous_generation_sha256': serving, 'published_at': _now().isoformat(),
                              'commit_trigger_sha256': trigger_sha, 'commit_request_sha256': request_sha}
                generation_sha = sha256_json(generation)
                handle.write_bytes('generations/' + generation_sha + '.json', canonical_bytes(generation), require_absent=True)
                _read_generation_content(path, handle, target, generation_sha)
                _activate(handle, target, generation_sha, serving)
            result = dict(common, status='SUCCEEDED', reused=reused, run_id=run_id, calculation_sha256=calculation_sha,
                          record_sha256=record_sha, generation_sha256=generation_sha, business_status=record['business_status'],
                          data_kind=kind, evidence_status=record['evidence_status'], finished_at=_now().isoformat())
            handle.write_bytes(attempt + '/receipt.json', canonical_bytes(result), require_absent=True)
            return result
        except Exception as exc:
            recovery = 'UNCHANGED'
            # A visible rename can precede an fsync/receipt exception. Under the
            # same date lock, restore only our own candidate head and retain all
            # objects. Never report a failed new attempt while serving it.
            try:
                if generation_sha is not None and generation_sha != serving and _head(handle, target) == generation_sha:
                    _restore_head(handle, target, generation_sha, serving)
                    recovery = 'PREVIOUS_SUCCESS_RESTORED'
            except (OSError, ValueError) as recovery_error:
                recovery = 'FAILED:' + str(recovery_error)
            result = dict(common, status='FAILED', reason=type(exc).__name__ + ':' + str(exc), run_id=run_id,
                          previous_success_generation_sha256=serving, publication_recovery_status=recovery,
                          issues=getattr(exc, 'issues', []), finished_at=_now().isoformat())
            handle.write_bytes(attempt + '/error.txt', traceback.format_exc().encode(), require_absent=True)
        handle.write_bytes(attempt + '/receipt.json', canonical_bytes(result), require_absent=True)
        return result


def rollback_a_close_daily(root, trade_date, target_generation_sha256, expected_generation_sha256, reason):
    target = checked_date(trade_date)
    sha(target_generation_sha256); sha(expected_generation_sha256)
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2048:
        raise ValueError('M09_ROLLBACK_REASON')
    path, handle = _private_io(root)
    with handle.kernel_lock('locks/' + target + '.lock', timeout=30):
        _reconcile_interrupted_head(path, handle, target)
        candidate = read_a_close_daily(path, target, generation_sha256=target_generation_sha256)
        current = read_a_close_daily(path, target)
        if current is None or current['identity']['generation_sha256'] != expected_generation_sha256:
            raise ValueError('M09_ROLLBACK_CAS_CONFLICT')
        # Only a verified predecessor of this date may be selected for rollback.
        cursor, seen = expected_generation_sha256, set()
        while cursor != target_generation_sha256:
            if cursor is None or cursor in seen:
                raise ValueError('M09_ROLLBACK_TARGET_NOT_PREDECESSOR')
            seen.add(cursor)
            cursor = read_a_close_daily(path, target, generation_sha256=cursor)['generation']['previous_generation_sha256']
        receipt = {'schema_version': 'v5.m09.rollback.v1', 'status': 'ROLLBACK_PREPARED', 'trade_date': target,
                   'previous_generation_sha256': expected_generation_sha256, 'generation_sha256': target_generation_sha256,
                   'model_run_id': candidate['identity']['model_run_id'], 'reason': reason, 'performed_at': _now().isoformat(), 'safety': dict(SAFETY)}
        prefix = 'rollbacks/' + sha256_json(receipt)
        handle.write_bytes(prefix + '/started.json', canonical_bytes(receipt), require_absent=True)
        try:
            _activate(handle, target, target_generation_sha256, expected_generation_sha256)
            after = read_a_close_daily(path, target)
            if after['identity']['generation_sha256'] != target_generation_sha256:
                raise ValueError('M09_ROLLBACK_READBACK_FAILED')
            receipt.update(status='ROLLED_BACK', finished_at=_now().isoformat())
            handle.write_bytes(prefix + '/receipt.json', canonical_bytes(receipt), require_absent=True)
        except Exception as exc:
            recovery = 'UNCHANGED'
            try:
                if _head(handle, target) == target_generation_sha256:
                    _restore_head(handle, target, target_generation_sha256, expected_generation_sha256)
                    recovery = 'PREVIOUS_HEAD_RESTORED'
            except (OSError, ValueError) as restore_error:
                recovery = 'FAILED:' + str(restore_error)
            failed = dict(receipt, status='FAILED', reason=type(exc).__name__ + ':' + str(exc),
                          recovery_status=recovery, finished_at=_now().isoformat())
            handle.write_bytes(prefix + '/failure.json', canonical_bytes(failed), require_absent=True)
            raise
        return receipt

"""M03 complete source-to-binding chain over the unchanged frozen US owner.

run_us_source is the public default. It isolates owner imports in a fresh
process; collector and snapshot reader each run in their own fresh child.
Data roots are private, marked, disjoint, and never used as code roots.
Network capture is off unless explicitly enabled on the request.
"""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


_ORCHESTRATOR_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

def _verify_orchestrator():
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != _ORCHESTRATOR_SHA256:
        raise ValueError('M03_ORCHESTRATOR_CHANGED')


@dataclass(frozen=True)
class USSourceRequest:
    trade_date: str
    capture_phase: str
    session: str
    cutoff: str
    source_root: Path
    snapshot_root: Path
    binding_root: Path
    owner_root: Path
    v5_src: Path
    allow_network_capture: bool = False
    capture_root: Path | None = None
    allow_late_post_close: bool = False
    development_dates_file: Path | None = None
    market_snapshot_only: bool = False


_PATH_FIELDS = ('source_root', 'snapshot_root', 'binding_root', 'owner_root',
                'v5_src', 'capture_root', 'development_dates_file')


def parse_utc(value):
    if not isinstance(value, str):
        raise ValueError('M03_TIME_REQUIRED')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('M03_TIMEZONE_REQUIRED')
    return parsed.astimezone(timezone.utc)


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{8}', value):
        raise ValueError('M03_DATE_INVALID')
    datetime.strptime(value, '%Y%m%d')
    return value


def source_paths(root, date, phase=None):
    _date(date)
    extra = 'history_backfill/' if phase == 'HISTORICAL_BACKFILL' else ''
    return {
        'payload': Path(root) / f'research/peripherals/{extra}{date}/external_finance.json',
        'receipt': Path(root) / f'receipts/research/peripherals/{extra}{date}/external_finance.json',
        'manifest': Path(root) / 'research/peripherals/manifest.json',
    }


def _request_dict(req):
    value = asdict(req)
    for name in _PATH_FIELDS:
        if value[name] is not None:
            value[name] = str(value[name])
    return value


def _request_from_dict(value):
    fields = dict(value)
    for name in _PATH_FIELDS:
        if fields.get(name) is not None:
            fields[name] = Path(fields[name])
    return USSourceRequest(**fields)


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _validate_request(req):
    _verify_orchestrator()
    from v5_shadow.composition import no_symlinks
    _date(req.trade_date)
    _date(req.session)
    parse_utc(req.cutoff)
    if req.capture_phase not in ('PRE_OPEN', 'POST_CLOSE', 'HISTORICAL_BACKFILL'):
        raise ValueError('M03_PHASE_INVALID')
    if type(req.allow_network_capture) is not bool or type(req.allow_late_post_close) is not bool:
        raise ValueError('M03_BOOLEAN_REQUIRED')
    if type(req.market_snapshot_only) is not bool:
        raise ValueError('M03_BOOLEAN_REQUIRED')
    if req.market_snapshot_only and req.capture_phase != 'POST_CLOSE':
        raise ValueError('M03_MARKET_CAPTURE_POST_CLOSE_ONLY')
    if req.allow_late_post_close and req.capture_phase != 'POST_CLOSE':
        raise ValueError('US_LATE_POST_CLOSE_ONLY')
    if no_symlinks(req.v5_src) != Path(__file__).resolve().parents[1]:
        raise ValueError('M03_V5_SRC_IDENTITY_MISMATCH')
    roots = [no_symlinks(getattr(req, name)) for name in
             ('source_root', 'snapshot_root', 'binding_root', 'owner_root')]
    if req.capture_root is not None:
        roots.append(no_symlinks(req.capture_root))
    code = no_symlinks(req.v5_src).parent
    for index, root in enumerate(roots):
        if root.is_relative_to(code) or code.is_relative_to(root):
            raise ValueError('M03_CODE_DATA_OVERLAP')
        for other in roots[index+1:]:
            if root.is_relative_to(other) or other.is_relative_to(root):
                raise ValueError('M03_ROOT_OVERLAP')
    if req.development_dates_file is not None:
        no_symlinks(req.development_dates_file)


def collector_argv(req):
    if not req.allow_network_capture:
        raise ValueError('M03_CAPTURE_NOT_AUTHORIZED')
    if req.capture_root is None:
        raise ValueError('M03_CAPTURE_ROOT_REQUIRED')
    # Original CLI binds session to trade_date: never silently collect a
    # different NY date on behalf of a target-date request.
    if req.trade_date != req.session:
        raise ValueError('M03_COLLECTOR_SESSION_DATE_MISMATCH')
    args = ['--owner-root', str(req.owner_root), '--allow-network-capture', '--',
            '--data-root', str(req.capture_root), '--trade-date', req.trade_date]
    if req.capture_phase == 'HISTORICAL_BACKFILL':
        if req.development_dates_file is None:
            raise ValueError('M03_HISTORICAL_ALLOWLIST_REQUIRED')
        args += ['--historical', '--development-dates-file', str(req.development_dates_file)]
    else:
        args += ['--capture-phase', req.capture_phase]
        if req.allow_late_post_close:
            args.append('--allow-late-post-close')
    return args


def _run_process(args, runner, label, timeout=300):
    try:
        return runner(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f'M03_{label}_TIMEOUT stdout={exc.stdout!r} stderr={exc.stderr!r}') from exc


def run_cold_collector(req, runner=subprocess.run):
    if req.market_snapshot_only:
        collector_argv(req)  # Preserve the original explicit authorization/date gate.
        bootstrap = '''import sys
sys.path.insert(0, sys.argv[1])
from v5_shadow.us_market_capture import main
raise SystemExit(main(sys.argv[2:]))
'''
        proc = _run_process([sys.executable, '-I', '-B', '-c', bootstrap,
                             str(req.v5_src), '--request-json', json.dumps(_request_dict(req))],
                            runner, 'COLLECTOR')
        return {'returncode': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr}
    bootstrap = '''import sys
sys.path.insert(0, sys.argv[1])
from v5_shadow.cloud_us_collector import main
raise SystemExit(main(sys.argv[2:]))
'''
    proc = _run_process([sys.executable, '-I', '-B', '-c', bootstrap,
                         str(req.v5_src), *collector_argv(req)], runner, 'COLLECTOR')
    return {'returncode': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr}


def _reader_child_code():
    # Preserve R13's multiline script and success-after-finally ordering.
    return r'''
import json
import sys
from pathlib import Path
try:
    sys.path.insert(0, sys.argv[1])
    from v5_shadow.cloud_us_collector import load_owner, verify, audit_modules, admit_output
    owner = Path(sys.argv[2])
    snapshot = Path(sys.argv[3])
    load_owner(owner)
    admit_output(snapshot, owner)
    from infrastructure.research_peripheral_store import ResearchPeripheralStore
    payload = None
    try:
        store = ResearchPeripheralStore(snapshot)
        if len(sys.argv) > 5 and sys.argv[5] == 'HISTORICAL_BACKFILL':
            payload = store.read_historical_backfill(sys.argv[4], 'external_finance')
        else:
            payload = store.read_exact(sys.argv[4], 'external_finance')
    finally:
        verify(owner)
        audit_modules()
    if payload is not None and not isinstance(payload, dict):
        raise TypeError('M03_READER_PAYLOAD_NOT_DICT')
    print(json.dumps({'payload': payload}, sort_keys=True))
except Exception as exc:
    print(json.dumps({'error': str(exc)}, sort_keys=True))
    raise
'''


def _decode_process(proc, label, key):
    if proc.returncode != 0:
        raise RuntimeError(f'M03_{label}_FAILED rc={proc.returncode} stdout={proc.stdout} stderr={proc.stderr}')
    try:
        value = json.loads(proc.stdout)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'M03_{label}_BAD_JSON stdout={proc.stdout} stderr={proc.stderr}') from exc
    if not isinstance(value, dict) or key not in value:
        raise ValueError(f'M03_{label}_CONTRACT_ERROR')
    return value[key]


def read_cold_snapshot(req, runner=subprocess.run):
    from v5_shadow.composition import no_symlinks
    if no_symlinks(req.v5_src) != Path(__file__).resolve().parents[1]:
        raise ValueError('M03_V5_SRC_IDENTITY_MISMATCH')
    _date(req.trade_date)
    no_symlinks(req.owner_root)
    no_symlinks(req.snapshot_root)
    proc = _run_process([sys.executable, '-I', '-B', '-c', _reader_child_code(),
                         str(req.v5_src), str(req.owner_root), str(req.snapshot_root),
                         req.trade_date, req.capture_phase], runner, 'READER')
    payload = _decode_process(proc, 'READER', 'payload')
    if payload is not None and not isinstance(payload, dict):
        raise ValueError('M03_READER_PAYLOAD_TYPE_ERROR')
    return payload


def _safe_root(root):
    from v5_shadow.cloud_us_collector import audit_modules
    audit_modules()
    from infrastructure.owned_io import SafeRoot
    return SafeRoot(root)


def _prepare_root(root, owner):
    from v5_shadow.cloud_us_collector import initialize_output, admit_output, MARKER
    from v5_shadow.composition import no_symlinks
    no_symlinks(root)
    if not root.exists():
        try:
            initialize_output(root, owner)
        except (FileExistsError, ValueError) as exc:
            if isinstance(exc, ValueError) and str(exc) != 'CLOUD_US_NEW_OUTPUT_REQUIRED':
                raise
    # A concurrent initializer can be between mkdir and the original marker
    # write. Wait only for visibility; never create a marker in an old root.
    for attempt in range(25):
        if (root / MARKER).exists():
            break
        time.sleep(.004)
    admit_output(root, owner)
    return _safe_root(root)


def _triplet(root, req):
    io = _safe_root(root)
    result = {}
    for key, path in source_paths(root, req.trade_date, req.capture_phase).items():
        relative = str(path.relative_to(root))
        with io.parent(relative) as (parent, name):
            before = os.stat(name, dir_fd=parent, follow_symlinks=False)
            raw = io.read_bytes(relative)
            after = os.stat(name, dir_fd=parent, follow_symlinks=False)
        identity = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
        if identity(before) != identity(after):
            raise ValueError('M03_SOURCE_CHANGED_DURING_COPY')
        result[key] = (raw, identity(after))
    return result


def _stable_triplet(root, req):
    first = _triplet(root, req)
    if first != _triplet(root, req):
        raise ValueError('M03_SOURCE_CHANGED_DURING_COPY')
    return {key: value[0] for key, value in first.items()}


def select_capture(payload, req):
    captures = payload.get('us_session_captures', [])
    if not isinstance(captures, list):
        raise ValueError('M03_CAPTURE_AMBIGUOUS')
    rows = [row for row in captures if isinstance(row, dict)
            and row.get('us_session_date') == req.session
            and row.get('capture_phase') == req.capture_phase]
    if len(rows) != 1:
        raise ValueError('M03_CAPTURE_AMBIGUOUS')
    return rows[0]


def _validate_payload(req, payload):
    if not isinstance(payload, dict) or not payload:
        raise ValueError('M03_PAYLOAD_NOT_VALIDATED')
    if payload.get('trade_date') != req.trade_date:
        raise ValueError('M03_DATE_MISMATCH')
    capture = select_capture(payload, req)
    cutoff = parse_utc(req.cutoff)
    if parse_utc(capture['captured_at']) > cutoff or parse_utc(payload['fetched_at']) > cutoff:
        raise ValueError('M03_CAPTURE_AFTER_CUTOFF')
    snapshot = payload.get('market_snapshot')
    if snapshot is not None:
        if not isinstance(snapshot, dict) or snapshot.get('capture_session_date') != req.session or snapshot.get('capture_phase') != req.capture_phase:
            raise ValueError('M03_SNAPSHOT_IDENTITY_MISMATCH')
        if parse_utc(snapshot['captured_at']) > cutoff:
            raise ValueError('M03_CAPTURE_AFTER_CUTOFF')
    # All original schema, window, DST, late/historical, response digest and
    # quote contracts are validated by the original fresh store reader.
    return capture


def _require_eligible(req, payload):
    if payload.get('status') not in ('READY', 'READY_EMPTY'):
        raise ValueError('M03_SOURCE_NOT_ELIGIBLE')
    if req.capture_phase != 'HISTORICAL_BACKFILL' and payload.get('market_snapshot', {}).get('status') != 'READY':
        raise ValueError('M03_MARKET_SNAPSHOT_NOT_ELIGIBLE')


def create_binding(req, payload):
    _verify_orchestrator()
    raw = _stable_triplet(req.snapshot_root, req)
    reread = read_cold_snapshot(req)
    if reread != payload or raw != _stable_triplet(req.snapshot_root, req):
        raise ValueError('M03_SNAPSHOT_CHANGED_DURING_READ')
    capture = _validate_payload(req, reread)
    _require_eligible(req, reread)
    from v5_shadow.cloud_us_collector import PIN, descriptor
    return {
        'schema_version': 'v5.m03.source_binding.v1',
        'status': 'VALIDATED_SOURCE_BINDING',
        'request': _request_dict(req),
        'owner_descriptor_sha256': PIN,
        'owner_source_commit': descriptor()['source_commit'],
        'orchestrator_sha256': _ORCHESTRATOR_SHA256,
        'source_status': reread['status'],
        'identity': capture,
        'market_snapshot': reread.get('market_snapshot', {}),
        'source_sha256': {key: _digest(value) for key, value in raw.items()},
        'production_allowed': False, 'orders_sent': False, 'buy_gate_updated': False,
    }


def _binding_name(req):
    return _digest(_json_bytes(_request_dict(req))) + '.json'


def _verify_binding(binding, req):
    if not isinstance(binding, dict) or binding.get('request') != _request_dict(req):
        raise ValueError('M03_BINDING_IDENTITY_MISMATCH')
    raw = _stable_triplet(req.snapshot_root, req)
    if binding.get('source_sha256') != {key: _digest(value) for key, value in raw.items()}:
        raise ValueError('M03_SNAPSHOT_SHA_MISMATCH')
    payload = read_cold_snapshot(req)
    expected = create_binding(req, payload)
    if binding != expected:
        raise ValueError('M03_BINDING_CONFLICT')
    return binding


def persist_binding(binding, root):
    if binding.get('status') != 'VALIDATED_SOURCE_BINDING':
        return binding
    req = _request_from_dict(binding['request'])
    if Path(root) != req.binding_root:
        raise ValueError('M03_BINDING_ROOT_MISMATCH')
    io = _prepare_root(req.binding_root, req.owner_root)
    name = _binding_name(req)
    with io.kernel_lock('.locks/publish.lock', timeout=30):
        _verify_binding(binding, req)
        try:
            io.write_bytes(name, _json_bytes(binding), require_absent=True)
        except FileExistsError:
            old = json.loads(io.read_bytes(name))
            if old != binding:
                raise ValueError('M03_BINDING_CONFLICT')
        # Independent disk read and original fresh reader, including reuse.
        return _verify_binding(json.loads(io.read_bytes(name)), req)


def _copy_snapshot(req, source):
    from v5_shadow.cloud_us_collector import admit_output
    admit_output(source, req.owner_root)
    raw = _stable_triplet(source, req)
    source_payload = read_cold_snapshot(replace(req, snapshot_root=source))
    if raw != _stable_triplet(source, req):
        raise ValueError('M03_SOURCE_CHANGED_DURING_COPY')
    _validate_payload(req, source_payload)
    _require_eligible(req, source_payload)
    io = _prepare_root(req.snapshot_root, req.owner_root)
    with io.kernel_lock('.locks/snapshot.lock', timeout=30):
        for key, path in source_paths(req.snapshot_root, req.trade_date, req.capture_phase).items():
            relative = str(path.relative_to(req.snapshot_root))
            try:
                io.write_bytes(relative, raw[key], require_absent=True)
            except FileExistsError:
                if io.read_bytes(relative) != raw[key]:
                    raise ValueError('M03_SNAPSHOT_CONFLICT')
        if raw != _stable_triplet(source, req):
            raise ValueError('M03_SOURCE_CHANGED_DURING_COPY')
        if raw != _stable_triplet(req.snapshot_root, req):
            raise ValueError('M03_SNAPSHOT_SHA_MISMATCH')
        payload = read_cold_snapshot(req)
        if payload != source_payload or raw != _stable_triplet(req.snapshot_root, req):
            raise ValueError('M03_SNAPSHOT_CHANGED_DURING_READ')
        return payload


def _run_owned(req):
    from v5_shadow.cloud_us_collector import load_owner, verify, audit_modules, admit_output
    _validate_request(req)
    owner, _ = load_owner(req.owner_root)
    try:
        return _run_chain(req, owner, admit_output)
    finally:
        verify(req.owner_root)
        audit_modules()
        _verify_orchestrator()


def _assert_source_absent(root, req):
    # The original historical reader returns None before checking manifest
    # when either payload or receipt is missing. Do not turn an orphan into
    # collection permission or a zero-exit missing-source success.
    io = _safe_root(root)
    paths = source_paths(root, req.trade_date, req.capture_phase)
    for key in ('payload', 'receipt'):
        try:
            io.read_bytes(str(paths[key].relative_to(root)))
        except FileNotFoundError:
            continue
        raise ValueError('M03_SOURCE_INCOMPLETE')
    try:
        raw = io.read_bytes(str(paths['manifest'].relative_to(root)))
    except FileNotFoundError:
        return
    manifest = json.loads(raw)
    if (not isinstance(manifest, dict)
            or any(not isinstance(k, str) or not isinstance(v, str) for k, v in manifest.items())
            or str(paths['payload'].relative_to(root)) in manifest):
        raise ValueError('M03_SOURCE_INCOMPLETE')


def _run_chain(req, owner, admit_output):
    from contracts.us_equity_calendar import session
    start, end = owner.us_capture_window(req.session, req.capture_phase)
    cutoff = parse_utc(req.cutoff)
    if req.capture_phase != 'HISTORICAL_BACKFILL':
        selected = session(req.session)
        if selected.close_at is None:
            return {'status': 'NOT_DUE', 'reason': selected.state}
        if cutoff < start:
            return {'status': 'NOT_DUE', 'reason': 'US_CAPTURE_NOT_YET_DUE'}
    io = _prepare_root(req.binding_root, req.owner_root)
    with io.kernel_lock('.locks/chain.lock', timeout=30):
        try:
            old = json.loads(io.read_bytes(_binding_name(req)))
        except FileNotFoundError:
            old = None
        if old is not None:
            admit_output(req.snapshot_root, req.owner_root)
            return _verify_binding(old, req)
        source = req.source_root
        payload = None
        if source.exists():
            admit_output(source, req.owner_root)
            payload = read_cold_snapshot(replace(req, snapshot_root=source))
            if payload is None:
                _assert_source_absent(source, req)
        if payload is None:
            if not req.allow_network_capture:
                return {'status': 'SOURCE_MISSING', 'reason': 'EXPLICIT_CAPTURE_REQUIRED'}
            collector_argv(req)  # Check authorization and original CLI identity first.
            _prepare_root(req.capture_root, req.owner_root)
            outcome = run_cold_collector(req)
            if outcome['returncode'] != 0:
                return {'status': 'COLLECTOR_FAILED', **outcome}
            source = req.capture_root
            payload = read_cold_snapshot(replace(req, snapshot_root=source))
            if payload is None:
                _assert_source_absent(source, req)
                return {'status': 'SOURCE_MISSING', 'reason': 'COLLECTOR_ZERO_WITHOUT_SOURCE', **outcome}
        _validate_payload(req, payload)
        if payload.get('status') not in ('READY', 'READY_EMPTY'):
            return {'status': 'SOURCE_REJECTED', 'source_status': payload.get('status'), 'cannot_confirm': payload.get('cannot_confirm', [])}
        snapshot = payload.get('market_snapshot', {})
        if req.capture_phase == 'PRE_OPEN' and snapshot.get('status') != 'READY':
            return {'status': 'NOT_DUE', 'reason': 'PRE_OPEN_QUOTE_NOT_DUE', 'source_status': payload['status']}
        if req.capture_phase == 'POST_CLOSE' and snapshot.get('status') != 'READY':
            return {'status': 'SOURCE_REJECTED', 'reason': 'POST_CLOSE_MARKET_SNAPSHOT_NOT_READY'}
        selected_payload = payload
        payload = _copy_snapshot(req, source)
        if payload != selected_payload:
            raise ValueError('M03_SOURCE_CHANGED_DURING_COPY')
        return persist_binding(create_binding(req, payload), req.binding_root)


def run_us_source(req, runner=subprocess.run):
    """Return an independently verified binding or an explicit non-success.

    Rejections and process/IO failures raise with their original diagnostics;
    absence, not-due, rejected source and collector nonzero have distinct statuses.
    Never pass a custom runner in production to grant capture permissions.
    """
    _validate_request(req)
    script = '''import json, sys
sys.path.insert(0, sys.argv[1])
from v5_shadow.us_source_daily import _request_from_dict, _run_owned
request = _request_from_dict(json.loads(sys.argv[2]))
result = _run_owned(request)
print(json.dumps({'result': result}, sort_keys=True))
'''
    proc = _run_process([sys.executable, '-I', '-B', '-c', script, str(req.v5_src),
                         json.dumps(_request_dict(req))], runner, 'CHAIN', timeout=900)
    result = _decode_process(proc, 'CHAIN', 'result')
    if not isinstance(result, dict) or not isinstance(result.get('status'), str):
        raise ValueError('M03_CHAIN_RESULT_TYPE_ERROR')
    return result

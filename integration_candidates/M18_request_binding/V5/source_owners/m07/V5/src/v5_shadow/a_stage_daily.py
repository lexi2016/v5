"""M07 concrete, replay-only A-stage owner chain.

Inputs are explicit SHA-pinned V5 private copies. Original owners run in fresh
processes. No provider, scheduling, formal-authority grant, or trading path.
"""
from __future__ import annotations
import sys
from pathlib import Path
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import csv
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import fcntl
import hashlib
import importlib
import importlib.abc
import importlib.util
import io
import json
import math
import os
import re
import stat
import subprocess
import tempfile
import traceback
from uuid import uuid4
from v5_shadow.contracts import aware, trade_date, exact_keys, sha
from v5_shadow.digests import canonical_bytes, sha256_json, MAX_JSON_BYTES
from v5_shadow.composition import no_symlinks
from v5_shadow.run_ledger import claim_run, finish_run

BASE = Path(__file__).resolve().parents[2]
HANDOFF = BASE.parent
OWNER = HANDOFF / 'owner'
MANIFEST = HANDOFF / 'OWNER_CLOSURE.json'
MANIFEST_SHA256 = 'dc63874f8d9e8307ee30a50d398d3c31d3fbac0d124702786b240d7059c6c301'
INPUT_MARKER = b'v5.m07-input-copy.v1\n'
OUTPUT_MARKER = b'v5.m07-private-output.v1\n'
FLAGS = dict(production_allowed=False, buy_gate_updated=False, orders_sent=False,
             natural_verified=False, formal_eligibility_verified=False)
TZ = timezone(timedelta(hours=8))
SOURCES = ('pool', 'live', 'research', 'morning')
SIDE_EFFECTS_STARTED = False


def _bytes(path):
    path = no_symlinks(Path(path))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('M07_REGULAR_FILE_REQUIRED')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(MAX_JSON_BYTES + 1)
        if len(data) > MAX_JSON_BYTES:
            raise ValueError('M07_FILE_TOO_LARGE')
        return data
    finally:
        os.close(fd)


def _path(root, relative):
    if (not isinstance(relative, str) or not relative or '\\' in relative
            or Path(relative).is_absolute() or Path(relative).as_posix() != relative
            or any(p in ('', '.', '..') for p in relative.split('/'))):
        raise ValueError('M07_RELATIVE_PATH')
    return no_symlinks(Path(root) / relative)


def _private(root, marker_name, marker):
    root = Path(root)
    if not root.is_absolute() or '..' in root.parts:
        raise ValueError('M07_ABSOLUTE_PRIVATE_ROOT_REQUIRED')
    root = no_symlinks(root)
    if any(p.casefold() in ('v4', 'v3', 'v3.5', 'v35', 'v3_system') for p in root.parts):
        raise ValueError('M07_LEGACY_RUNTIME_ROOT_FORBIDDEN')
    if not root.is_dir() or _bytes(root / marker_name) != marker:
        raise ValueError('M07_PRIVATE_ROOT_MARKER')
    return root


def _owner_sources():
    raw = _bytes(MANIFEST)
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError('M07_OWNER_MANIFEST_CHANGED')
    manifest = json.loads(raw)
    sources = {}
    for entry in manifest['entries']:
        raw = _bytes(_path(OWNER, entry['path']))
        if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('M07_OWNER_BYTES_CHANGED:' + entry['path'])
        sources[entry['path']] = raw
    return sources


class _OwnerLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, sources):
        self.sources = {p[:-3].replace('/', '.'): (p, data)
                        for p, data in sources.items() if p.endswith('.py')}
        self.packages = set()
        for name in self.sources:
            parts = name.split('.')
            self.packages.update('.'.join(parts[:i]) for i in range(1, len(parts)))
    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.sources or fullname in self.packages:
            return importlib.util.spec_from_loader(fullname, self, is_package=fullname in self.packages)
        if fullname.split('.')[0] in ('stage_center', 'infrastructure', 'domains', 'contracts', 'upstreams'):
            raise ImportError('M07_FROZEN_CLOSURE_MISSING:' + fullname)
        return None
    def create_module(self, spec):
        return None
    def exec_module(self, module):
        if module.__name__ in self.packages:
            module.__path__ = []
        if module.__name__ in self.sources:
            relative, raw = self.sources[module.__name__]
            module.__file__ = str(OWNER / relative)
            exec(compile(raw, module.__file__, 'exec'), module.__dict__)


def _load_owner():
    if any(n in sys.modules for n in ('stage_center', 'infrastructure', 'domains', 'contracts')):
        raise ValueError('M07_FRESH_OWNER_PROCESS_REQUIRED')
    sys.meta_path.insert(0, _OwnerLoader(_owner_sources()))
    return importlib.import_module('stage_center.selection')


def _guard(writable):
    """Defense in depth, not an OS-sandbox certification. Supports owned dir_fds."""
    writable = tuple(Path(p).resolve() for p in writable)
    descriptors = {}
    opening = False
    def resolved(path, directory=None):
        if isinstance(path, int):
            if path not in descriptors:
                raise PermissionError('M07_UNTRACKED_DESCRIPTOR')
            return descriptors[path]
        p = Path(os.fsdecode(path))
        if not p.is_absolute():
            if directory is not None:
                if directory not in descriptors:
                    raise PermissionError('M07_UNTRACKED_DIRECTORY_DESCRIPTOR')
                p = descriptors[directory] / p
            else:
                p = Path.cwd() / p
        if '..' in p.parts:
            raise PermissionError('M07_PARENT_TRAVERSAL')
        return p
    def check(path, directory=None):
        p = resolved(path, directory)
        if not any(p == root or root in p.parents for root in writable):
            raise PermissionError('M07_WRITE_OUTSIDE_PRIVATE_ROOT:' + str(p))
    original_open, original_close = os.open, os.close
    def opened(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal opening
        p = resolved(path, dir_fd)
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            check(p)
        opening = True
        try:
            fd = original_open(path, flags, mode, dir_fd=dir_fd)
        finally:
            opening = False
        descriptors[fd] = p
        return fd
    def closed(fd):
        descriptors.pop(fd, None)
        return original_close(fd)
    original_mkdir = os.mkdir
    def mkdir(path, mode=0o777, *, dir_fd=None):
        p = resolved(path, dir_fd)
        if any(p in root.parents for root in writable):
            # SafeRoot probes every existing ancestor with mkdir. No syscall or
            # permission expansion is needed for this guaranteed EEXIST case.
            if not p.is_symlink() and p.is_dir():
                raise FileExistsError(str(p))
            raise PermissionError('M07_ANCESTOR_NOT_EXISTING_DIRECTORY')
        check(p)
        return original_mkdir(path, mode, dir_fd=dir_fd)
    os.open, os.close, os.mkdir = opened, closed, mkdir
    def audit(event, args):
        if event.startswith(('socket.', 'subprocess.')) or event in ('os.system', 'os.exec', 'os.spawn'):
            raise PermissionError('M07_NETWORK_OR_PROCESS_FORBIDDEN')
        if event == 'open' and not opening:
            path, mode, flags = args
            write = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            if write:
                check(path)
        if event in ('os.remove', 'os.rmdir'):
            check(args[0], None if args[1] == -1 else args[1])
        if event == 'os.mkdir':
            check(args[0], None if args[2] == -1 else args[2])
        if event == 'os.rename':
            check(args[0], None if args[2] == -1 else args[2])
            check(args[1], None if args[3] == -1 else args[3])
        if event == 'os.link':
            check(args[0], None if args[2] == -1 else args[2])
            check(args[1], None if args[3] == -1 else args[3])
        if event == 'os.symlink':
            raise PermissionError('M07_SYMLINK_CREATION_FORBIDDEN')
    sys.addaudithook(audit)


def _request(value):
    exact_keys(value, ('schema_version', 'target_date', 'stage_id', 'cutoff', 'data_kind',
        'trigger', 'natural', 'pool_source_dates', 'inputs', 'recording', 'expected_generation'))
    if value['schema_version'] != 'v5.m07_daily_request.v1':
        raise ValueError('M07_REQUEST_SCHEMA')
    trade_date(value['target_date']); aware(value['cutoff'])
    if value['natural'] is not False or value['trigger'] not in ('RECORDED_INPUT_REPLAY', 'MANUAL_RECOVERY'):
        raise ValueError('M07_NATURAL_EXECUTION_NOT_BOUND')
    if value['data_kind'] not in ('SYNTHETIC', 'RECORDED_INPUT_REPLAY'):
        raise ValueError('M07_DATA_KIND')
    if value['expected_generation'] is not None:
        sha(value['expected_generation'])
    exact_keys(value['inputs'], SOURCES)
    for key, binding in value['inputs'].items():
        exact_keys(binding, ('root', 'files'))
        if not isinstance(binding['files'], dict) or not binding['files']:
            raise ValueError('M07_INPUT_FILES_REQUIRED:' + key)
        for relative, digest in binding['files'].items():
            _path(Path(binding['root']), relative); sha(digest)
    exact_keys(value['recording'], ('run_id', 'artifact_sha256', 'manifest_sha256',
                                   'receipt_sha256', 'captured_at', 'acquired_at'))
    for field in ('artifact_sha256', 'manifest_sha256', 'receipt_sha256'):
        sha(value['recording'][field])
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', value['recording']['run_id']):
        raise ValueError('M07_RAW_RUN_ID')
    canonical_bytes(value)
    return deepcopy(value)


def _snapshots(request, directory):
    result = {}
    originals = {}
    for key in SOURCES:
        binding = request['inputs'][key]
        root = _private(binding['root'], '.v5-m07-input', INPUT_MARKER)
        target = directory / key; target.mkdir()
        before = {}
        for relative, digest in binding['files'].items():
            source = _path(root, relative); raw = _bytes(source)
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError('M07_INPUT_BYTES_MISMATCH:' + key + ':' + relative)
            before[relative] = raw
            dest = _path(target, relative); dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        # Catch a source change during copy; readers only lock or recover copies.
        if any(_bytes(_path(root, name)) != raw for name, raw in before.items()):
            raise ValueError('M07_INPUT_CHANGED_DURING_COPY')
        originals[key] = before; result[key] = target
    return result, originals


def _number(value, *, positive=False):
    if isinstance(value, bool):
        raise ValueError('M07_REQUIRED_NUMBER')
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError('M07_REQUIRED_NUMBER') from None
    if not math.isfinite(result) or (result <= 0 if positive else result < 0):
        raise ValueError('M07_REQUIRED_NUMBER')
    return result


def _admit(request, roots):
    from stage_center.contracts import STAGE_BY_ID
    from stage_center.calendar import resolve_market_states
    from stage_center.raw_store import RawStore, RAW_FIELDS
    from infrastructure.stage_acquisition_universe_contracts import read_strict_a_preselection_snapshot
    from stage_center.input_contracts import KNOWN_A_STAGE_POOL_IDS
    spec = STAGE_BY_ID.get(request['stage_id'])
    date = request['target_date']; iso = f'{date[:4]}-{date[4:6]}-{date[6:]}'
    if spec is None or 'A_SHARE' not in spec.markets:
        raise ValueError('M07_A_STAGE_NOT_SUPPORTED')
    if resolve_market_states(date)['a_share'].value != 'FULL_TRADING_DAY':
        raise ValueError('M07_MARKET_NOT_OPEN')
    cutoff = aware(iso + 'T' + spec.cutoff + '+08:00')
    if aware(request['cutoff']) != cutoff:
        raise ValueError('M07_ORIGINAL_CUTOFF_MISMATCH')
    start = aware(iso + 'T' + spec.window.split('-')[0] + ':00+08:00')
    captured = aware(request['recording']['captured_at'])
    acquired = aware(request['recording']['acquired_at'])
    if not start <= captured <= acquired <= cutoff or acquired > datetime.now(timezone.utc):
        raise ValueError('M07_RECORDING_OUTSIDE_WINDOW_OR_FUTURE')
    exact_keys(request['pool_source_dates'], KNOWN_A_STAGE_POOL_IDS)
    for value in request['pool_source_dates'].values():
        trade_date(value)
    snapshot = read_strict_a_preselection_snapshot(roots['pool'], date)
    if not snapshot.ready:
        raise ValueError('M07_M05_NO_VALID_ROWS:' + ';'.join(snapshot.diagnostic_reasons))
    # Every physically present lane must verify, even when another valid lane exists.
    for reasons in snapshot.pool_diagnostics.values():
        if any('SOURCE_REJECTED:' in r or ('SOURCE_UNAVAILABLE:' in r and 'FileNotFoundError' not in r) for r in reasons):
            raise ValueError('M07_M05_REJECTED_PHYSICAL_LANE')
    for pool in snapshot.pools:
        payload = pool.artifact
        if (payload.get('target_date') != date or
                payload.get('signal_date') != request['pool_source_dates'][pool.pool_id]):
            raise ValueError('M07_M05_SOURCE_DATE_MISMATCH')
        for row in payload['rows']:
            for field in ('symbol', 'code', 'stock_code', 'normalized_code', 'ts_code'):
                if field in row and (not isinstance(row[field], str) or row[field] != row[field].strip()):
                    raise ValueError('M07_POOL_CODE_WHITESPACE')
            if row.get('formal_eligible') is True or row.get('formal_authority') is True:
                raise ValueError('M07_DECLARED_FORMAL_AUTHORITY')
    raw = RawStore(roots['live']).verify_run(date, request['stage_id'], 'A_SHARE', request['recording']['run_id'])
    for field in ('artifact_sha256', 'manifest_sha256', 'receipt_sha256'):
        if raw[field] != request['recording'][field]:
            raise ValueError('M07_RAW_RECEIPT_BINDING')
    if raw['cutoff_at'] != spec.cutoff or raw['window'] != spec.window:
        raise ValueError('M07_RAW_WINDOW_BINDING')
    with _path(roots['live'], raw['artifact_relative']).open(newline='', encoding='utf-8-sig') as stream:
        csv_rows = list(csv.DictReader(stream))
    rows = []; seen = set()
    for source in csv_rows:
        code = source['code']
        if not re.fullmatch(r'A\.\d{6}', code) or code in seen:
            raise ValueError('M07_RAW_CODE_INVALID_OR_DUPLICATE')
        seen.add(code)
        if code not in snapshot.codes:
            raise ValueError('M07_RAW_CODE_NOT_IN_M05')
        if source['temporal_cutoff_safe'] != 'True' or datetime.strptime(source['window_end'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=TZ) > captured:
            raise ValueError('M07_RAW_UNSAFE_OR_AFTER_CAPTURE')
        row = {k: source[k] for k in RAW_FIELDS}
        for field in ('last_price', 'open_price', 'high_price', 'low_price', 'prev_close_price'):
            row[field] = _number(source[field], positive=True)
        for field in ('turnover', 'volume', 'bid_price', 'ask_price', 'bid_vol', 'ask_vol'):
            row[field] = _number(source[field])
        if row['low_price'] > min(row['open_price'], row['last_price']) or row['high_price'] < max(row['open_price'], row['last_price']):
            raise ValueError('M07_QUOTE_INCONSISTENT')
        rows.append(row)
    missing = set(snapshot.codes) - seen
    declared = raw['missing_symbols']
    if (len(declared) != len(set(declared)) or any(not re.fullmatch(r'A\.\d{6}', c) for c in declared)
            or set(declared) != missing or raw['requested_rows'] != len(snapshot.codes)):
        raise ValueError('M07_RAW_COVERAGE_NOT_EXACT')
    if raw['status'] in ('READY', 'READY_EMPTY') and (missing or raw['cannot_confirm']):
        raise ValueError('M07_RAW_READY_CONTRADICTION')
    if raw['status'] == 'CANNOT_CONFIRM' or not rows:
        raise ValueError('M07_RAW_UNKNOWN_OR_WINDOW_MISSED')
    return spec, snapshot, raw, rows


def _select(request, roots, spec, pool, raw, observations, owner):
    gaps = list(raw['cannot_confirm'])
    gaps.append('FORMAL_OVERLAY_CANNOT_CONFIRM')
    evidence = list(raw['source_evidence']) + ['selection_contract=V3_TOP10_RECOMMENDATION',
        'formal_overlay=CANNOT_CONFIRM', 'm07_raw_status=' + raw['status'],
        'm07_input_sha256=' + sha256_json(request['inputs']),
        'm07_pool_codes_sha256=' + sha256_json(list(pool.codes)),
        'm07_trigger=' + request['trigger'], 'm07_natural=false']
    rows = []
    research = None
    if request['stage_id'] != 'STAGE_0925':
        from stage_center.research_context import load_research_context
        research = load_research_context(roots['research'], trade_date=request['target_date'],
            stage_cutoff=spec.cutoff, morning_root=roots['morning'])
        gaps.extend(research.cannot_confirm); evidence.extend(research.source_evidence)
    for index, obs in enumerate(observations, 1):
        code = obs['code']
        if request['stage_id'] == 'STAGE_0925':
            rows.append(dict(code=code, name=obs['name'], trade_date=request['target_date'],
                time=obs['update_time'], update_time=obs['update_time'], amount=obs['turnover'],
                price=obs['last_price'], prev_close_price=obs['prev_close_price'],
                open_price=obs['open_price'], last_price=obs['last_price'], high_price=obs['high_price'],
                low_price=obs['low_price'], bid_vol=obs['bid_vol'], ask_vol=obs['ask_vol'],
                pool_score=None, next_validation_time=raw['cutoff_at']))
            continue
        score = research.by_code.get(obs['code'])
        if score is None or score.news_quality_score is None or score.research_quality_score is None:
            # Do not invoke a selector whose numeric default turns absence into zero.
            raise ValueError('M07_RESEARCH_REQUIRED_FIELDS_MISSING:' + code)
        rows.append(dict(code=code, name=obs['name'], stock_name=obs['name'],
            trade_date=request['target_date'], stage_id=request['stage_id'],
            formal_eligible=False, formal_rank='', candidate={'score': None},
            qmt=dict(open=obs['open_price'], lastPrice=obs['last_price'], lastClose=obs['prev_close_price'],
                high=obs['high_price'], low=obs['low_price'], amount=obs['turnover'],
                bidVol=[obs['bid_vol']], askVol=[obs['ask_vol']]),
            open_price=obs['open_price'], last_price=obs['last_price'], high_price=obs['high_price'], low_price=obs['low_price'],
            update_time=obs['update_time'],
            next_validation_time=raw['cutoff_at'], acquisition_rank=int(_number(obs['batch_index'], positive=True)),
            lane_evidence=['STAGE_ACQUISITION_UNIVERSE','PYTDX_EXACT_STAGE_ADAPTER'],
            news_quality_score=score.news_quality_score, research_quality_score=score.research_quality_score,
            latest_research_slot=score.latest_research_slot, research_delta_hits=score.research_delta_hits,
            news_research_reason='；'.join(score.news_research_reason), source_health=score.source_health))
    before = canonical_bytes(rows)
    kwargs = dict(source_status='CANNOT_CONFIRM', requested_rows=raw['requested_rows'],
        missing_symbols=raw['missing_symbols'], cannot_confirm=list(dict.fromkeys(gaps)),
        source_evidence=list(dict.fromkeys(evidence)))
    if request['stage_id'] == 'STAGE_0925':
        artifact = owner.select_a_0925_auction(rows, request['target_date'], raw['artifact_sha256'], **kwargs)
        algorithm = 'select_a_0925_auction'
    else:
        artifact = owner.select_a_live_stage(rows, request['target_date'], request['stage_id'], raw['artifact_sha256'], **kwargs)
        algorithm = 'select_a_live_stage'
    if canonical_bytes(rows) != before:
        raise ValueError('M07_SELECTOR_MUTATED_INPUT')
    if (artifact['algorithm_sha256'] != owner.A_SHARE_LIVE_ALGORITHM_SHA256 or len(artifact['rows']) > 10
            or any(artifact.get(k) is not False for k in ('production_allowed','buy_gate_updated','orders_sent'))
            or any(r.get('formal_eligible') is not False for r in artifact['rows'])):
        raise ValueError('M07_SELECTION_OUTPUT_CONTRACT')
    return artifact, dict(algorithm=algorithm, rows=rows, kwargs=kwargs, input_mutated=False)


def _build(message, owner):
    global SIDE_EFFECTS_STARTED
    request = _request(message['request'])
    with tempfile.TemporaryDirectory(prefix='m07-input-copy-') as temporary:
        directory = Path(temporary).resolve()
        roots, originals = _snapshots(request, directory)
        output = no_symlinks(Path(message['generation_root']))
        output.parent.mkdir(exist_ok=True)
        _guard((directory, output))
        spec, pool, raw, observations = _admit(request, roots)
        artifact, selector_input = _select(request, roots, spec, pool, raw, observations, owner)
        for key in SOURCES:
            for relative, original in originals[key].items():
                if _bytes(_path(roots[key], relative)) != original:
                    raise ValueError('M07_OWNER_CHANGED_INPUT_BYTES')
        _owner_sources()
        SIDE_EFFECTS_STARTED = True
        output.mkdir(parents=True, exist_ok=False)
        published = owner.SelectionStore(output).publish(artifact, market='A_SHARE')
        verified = owner.SelectionStore(output)._verify_run(request['target_date'], request['stage_id'], 'A_SHARE', published['run_id'])
        if verified['envelope'] != artifact:
            raise ValueError('M07_PUBLISH_READBACK_MISMATCH')
        return dict(status='BUILT', selection=artifact, selector_input=selector_input,
            artifact_sha256=verified['artifact_sha256'], manifest_sha256=verified['manifest_sha256'],
            receipt_sha256=verified['receipt_sha256'], artifact_relative=verified['artifact_relative'],
            pool_codes_sha256=sha256_json(list(pool.codes)), pool_diagnostics={k:list(v) for k,v in pool.pool_diagnostics.items()},
            request_sha256=sha256_json(request), isolation_status='PYTHON_GUARDS_ONLY_OS_UNVERIFIED', **FLAGS)


def _worker(message):
    owner = _load_owner()
    if message['operation'] == 'build':
        return _build(message, owner)
    if message['operation'] == 'read':
        root = no_symlinks(Path(message['generation_root']))
        _guard(())
        store = owner.SelectionStore(root)
        envelope = store.read_verified(message['target_date'], message['stage_id'], 'A_SHARE')
        result = store._verify_run(message['target_date'], message['stage_id'], 'A_SHARE', envelope['run_id'])
        _owner_sources()
        return result
    raise ValueError('M07_WORKER_OPERATION')


def _invoke(message):
    proc = subprocess.run([sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--worker'],
        input=canonical_bytes(message), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
        env={k:v for k,v in os.environ.items() if not k.startswith(('V4_', 'V35_', 'PYTHONPATH'))})
    if len(proc.stdout) > MAX_JSON_BYTES:
        raise ValueError('M07_WORKER_OUTPUT_TOO_LARGE')
    try:
        value = json.loads(proc.stdout)
    except (ValueError, UnicodeError) as error:
        raise ValueError('M07_WORKER_RESPONSE:' + proc.stderr.decode(errors='replace')[-1000:]) from error
    return value


def _current(root):
    try:
        value = json.loads(_bytes(root / 'current.json'))
    except FileNotFoundError:
        return {'schema_version':'v5.m07_current.v1','entries':{}}
    exact_keys(value, ('schema_version','entries'))
    if value['schema_version'] != 'v5.m07_current.v1' or not isinstance(value['entries'], dict):
        raise ValueError('M07_CURRENT_SCHEMA')
    return value


def _atomic(path, payload):
    temporary = path.parent / ('.' + uuid4().hex + '.tmp')
    fd = os.open(temporary, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(canonical_bytes(payload)); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)


def _slot(date, stage):
    trade_date(date)
    if not re.fullmatch(r'STAGE_[0-9_]+', stage):
        raise ValueError('M07_STAGE_ID')
    return date + '/' + stage


def _read_reference(root, reference):
    sha(reference['generation'])
    verified = _invoke(dict(operation='read', generation_root=str(root/'generations'/reference['generation']),
                           target_date=reference['target_date'], stage_id=reference['stage_id']))
    if verified.get('status') == 'ERROR':
        raise ValueError('M07_ORIGINAL_READBACK_REJECTED:' + verified['reason'])
    for field in ('artifact_sha256','manifest_sha256','receipt_sha256','run_id'):
        if verified.get(field) != reference[field]:
            raise ValueError('M07_PRODUCT_REFERENCE_MISMATCH:' + field)
    return dict(generation=reference['generation'], selection=verified['envelope'],
                artifact_sha256=verified['artifact_sha256'], manifest_sha256=verified['manifest_sha256'],
                receipt_sha256=verified['receipt_sha256'], **FLAGS)


def read_a_stage_daily(output_root, target_date, stage_id):
    """Read committed data only; no claim, creation, capture, retry or repair."""
    root = _private(output_root, '.v5-m07-output', OUTPUT_MARKER)
    reference = _current(root)['entries'].get(_slot(target_date, stage_id))
    if reference is None:
        raise ValueError('M07_NO_COMMITTED_SELECTION')
    if reference['target_date'] != target_date or reference['stage_id'] != stage_id:
        raise ValueError('M07_CURRENT_IDENTITY')
    return _read_reference(root, reference)


def activate_a_stage_generation(output_root, reference, *, expected_generation):
    """Activate or roll back one verified private A slot with an exact CAS lease."""
    root = _private(output_root, '.v5-m07-output', OUTPUT_MARKER)
    exact_keys(reference, ('generation','target_date','stage_id','run_id',
                           'artifact_sha256','manifest_sha256','receipt_sha256'))
    if expected_generation is not None:
        sha(expected_generation)
    slot = _slot(reference['target_date'], reference['stage_id'])
    verified = _read_reference(root, reference)
    fd = os.open(root/'.publication.lock', os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('M07_PUBLICATION_LOCK')
        fcntl.flock(fd,fcntl.LOCK_EX)
        current = _current(root); existing = current['entries'].get(slot)
        if (existing['generation'] if existing else None) != expected_generation:
            raise ValueError('M07_EXPECTED_GENERATION_MISMATCH')
        current['entries'][slot] = deepcopy(reference)
        _atomic(root/'current.json',current)
    finally:
        os.close(fd)
    return verified


def run_a_stage_daily(request, *, output_root):
    """Replay pinned bytes using actual owners; SUCCEEDED means saved readback only."""
    try:
        request = _request(request)
        root = _private(output_root, '.v5-m07-output', OUTPUT_MARKER)
        _owner_sources()
        slot = _slot(request['target_date'], request['stage_id'])
        identity = dict(lane='a_stage', target_date=request['target_date'],
            input_sha256=sha256_json(request), research_cutoff=request['cutoff'],
            code_sha256=hashlib.sha256(_bytes(Path(__file__))).hexdigest(),
            config_sha256=sha256_json(dict(stage_id=request['stage_id'],pool_source_dates=request['pool_source_dates'],root=str(root))),
            dependency_sha256=MANIFEST_SHA256)
        claim = claim_run(root/'ledger', identity, max_attempts=1)
    except (ValueError, OSError, TypeError, KeyError) as error:
        return dict(status='BLOCKED',reason_codes=[type(error).__name__+':'+str(error)],**FLAGS)
    if claim['status'] == 'REUSED_SUCCESS':
        try:
            reference = claim['state']['latest_success']['product_reference']
            return dict(status='REUSED_SUCCESS', **_read_reference(root,reference))
        except (ValueError, OSError, KeyError) as error:
            return dict(status='READBACK_FAILED',reason_codes=[str(error)],**FLAGS)
    if claim['status'] != 'CLAIMED':
        return dict(status=claim['status'],state=claim['state'],**FLAGS)
    generation = claim['identity_sha256']
    def blocked(reason, safe=True, failure_trace=None):
        state = finish_run(root/'ledger',claim,dict(status='BLOCKED',product_reference=None,
            readback_verified=False,retry_safe_without_external_effect=safe,reason_codes=[reason]))
        return dict(status='BLOCKED',reason_codes=[reason],state=state,failure_trace=failure_trace,**FLAGS)
    try:
        prior = _current(root)['entries'].get(slot)
    except (ValueError, OSError) as error:
        return blocked(type(error).__name__+':'+str(error))
    if (prior['generation'] if prior else None) != request['expected_generation']:
        return blocked('M07_EXPECTED_GENERATION_MISMATCH')
    try:
        built = _invoke(dict(operation='build',request=request,generation_root=str(root/'generations'/generation)))
        if built.get('status') == 'ERROR':
            if built.get('side_effects_started') is False:
                return blocked(built['reason'],failure_trace=built.get('trace'))
            return dict(status='OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY',reason_codes=[built['reason']],run_id=claim['run_id'],**FLAGS)
        if built.get('status') != 'BUILT' or built.get('request_sha256') != sha256_json(request):
            raise ValueError('M07_BUILD_IDENTITY_MISMATCH')
        reference = dict(generation=generation,target_date=request['target_date'],stage_id=request['stage_id'],
            run_id=built['selection']['run_id'],artifact_sha256=built['artifact_sha256'],
            manifest_sha256=built['manifest_sha256'],receipt_sha256=built['receipt_sha256'])
        verified = _read_reference(root,reference)
        if verified['selection'] != built['selection']:
            raise ValueError('M07_INDEPENDENT_READBACK_MISMATCH')
        try:
            activate_a_stage_generation(root, reference, expected_generation=request['expected_generation'])
        except ValueError as error:
            if str(error) == 'M07_EXPECTED_GENERATION_MISMATCH':
                return blocked(str(error),False)
            raise
        state = finish_run(root/'ledger',claim,dict(status='SUCCEEDED',product_reference=reference,
            readback_verified=True,retry_safe_without_external_effect=False,reason_codes=['REPLAY_ONLY','FORMAL_AUTHORITY_NOT_CONNECTED']))
        return dict(status='SUCCEEDED',state=state,selector_input=built['selector_input'],
            pool_diagnostics=built['pool_diagnostics'],**verified)
    except Exception as error:
        # Publication may already exist. Never turn uncertainty into a retry.
        return dict(status='OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY',run_id=claim['run_id'],
                    reason_codes=[type(error).__name__+':'+str(error)],**FLAGS)


if __name__ == '__main__':
    try:
        raw=sys.stdin.buffer.read(MAX_JSON_BYTES+1)
        if len(raw)>MAX_JSON_BYTES:raise ValueError('M07_REQUEST_TOO_LARGE')
        message=json.loads(raw)
        if sys.argv[1:] == ['--worker']:
            answer=_worker(message)
        elif sys.argv[1:] == ['--run']:
            answer=run_a_stage_daily(message['request'],output_root=message['output_root'])
        elif sys.argv[1:] == ['--activate']:
            answer=activate_a_stage_generation(message['output_root'],message['reference'],expected_generation=message['expected_generation'])
        elif sys.argv[1:] == ['--read']:
            answer=read_a_stage_daily(message['output_root'],message['target_date'],message['stage_id'])
        else:
            raise ValueError('M07_USAGE: --run, --read, --activate or internal --worker')
        print(canonical_bytes(answer).decode())
    except Exception as error:
        print(canonical_bytes(dict(status='ERROR',reason=type(error).__name__+':'+str(error),
            side_effects_started=SIDE_EFFECTS_STARTED,trace=traceback.format_exc())).decode())
        raise SystemExit(1)

"""Read-only original M06 inputs -> isolated, sealed V5 delivery.

This adapter never imports a provider, collector or model. Hash checks establish
byte identity; the fixed original owner's cold inspection remains authoritative
for input/model validity. Upstream panel completion is retained separately from
this adapter's fresh immutable-delivery completion.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import stat
from string import Formatter
from uuid import uuid4

from .composition import no_symlinks
from .contracts import aware, exact_keys, sha, trade_date
from .digests import canonical_bytes, sha256_json, MAX_JSON_BYTES
from .module_api import _open_directory, _read_regular, _read_at
from .module_artifacts import _directory, _write_once
from .run_ledger import _write

DELIVERY_SCHEMA = 'v5.m06_daily_input_delivery.v1'
SEAL_SCHEMA = 'v5.m06_input_snapshot_seal.v1'
MAX_FILE_BYTES = 4 * 1024**3
MAX_FILES = 128
MAX_DISPATCH_RECEIPTS = 64
MAX_DISPATCH_BYTES = 64 * 1024**2
DISPATCH_DISCOVERY = 'DAY_SLOT_UUID_V1'
MAX_TOTAL_BYTES = 8 * 1024**3
SAFETY = ('production_allowed', 'buy_gate_updated', 'orders_sent')
HK_TIME = timezone(timedelta(hours=8))
MASTER = 'assets/hk_security_master/'
ROLE = 'HK_CONNECT_D1_TOP100_0_2'


def _utc_now():
    return datetime.now(timezone.utc)



def _json(raw):
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('M06_DELIVERY_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def invalid_constant(_):
        raise ValueError('M06_DELIVERY_JSON_CONSTANT')
    return json.loads(raw, object_pairs_hook=object_pairs, parse_constant=invalid_constant)


def _relative(value):
    if (not isinstance(value, str) or not value or len(value) > 1024
            or '\\' in value or '\x00' in value
            or any(part in ('', '.', '..') for part in value.split('/'))
            or Path(value).is_absolute()):
        raise ValueError('M06_DELIVERY_PATH')
    return value


def _identity(info):
    return tuple(getattr(info, name) for name in
                 ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


@contextmanager
def _file(root, relative):
    relative = _relative(relative)
    path = Path(root)/relative
    parent = _open_directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('M06_DELIVERY_FILE_TYPE')
        yield fd
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def _hash_fd(fd, *, output=None):
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
        raise ValueError('M06_DELIVERY_FILE_SIZE_OR_TYPE')
    size, digest = 0, hashlib.sha256()
    while chunk := os.read(fd, 1024**2):
        size += len(chunk)
        if size > MAX_FILE_BYTES:
            raise ValueError('M06_DELIVERY_FILE_SIZE')
        digest.update(chunk)
        if output is not None:
            output.write(chunk)
    if size != before.st_size or _identity(before) != _identity(os.fstat(fd)):
        raise ValueError('M06_DELIVERY_INPUT_CHANGED')
    return dict(sha256=digest.hexdigest(), bytes=size, identity=_identity(before))


def _observe(capture, family, relative, *, metadata=False, optional=False):
    relative = _relative(relative)
    key = (family, relative)
    root = capture['roots'][family]
    try:
        with _file(root, relative) as fd:
            before = os.fstat(fd)
            if metadata:
                raw = _read_regular(fd, MAX_JSON_BYTES)
                record = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), identity=_identity(before))
            else:
                record = _hash_fd(fd)
                raw = None
    except FileNotFoundError:
        if not optional:
            raise
        record, raw = None, None
    previous = capture['records'].get(key, record)
    if previous != record:
        raise ValueError('M06_DELIVERY_INPUT_CHANGED')
    capture['records'][key] = record
    if len(capture['records']) > MAX_FILES or sum(r['bytes'] for r in capture['records'].values() if r) > MAX_TOTAL_BYTES:
        raise ValueError('M06_DELIVERY_INVENTORY_LIMIT')
    if record is None:
        return None
    if metadata:
        value = _json(raw)
        if not isinstance(value, dict):
            raise ValueError('M06_DELIVERY_METADATA')
        return value
    return record['sha256']


def _safety(value, *, required=True):
    if any((required or key in value) and value.get(key) is not False for key in SAFETY):
        raise ValueError('M06_DELIVERY_SAFETY')


def _pool_safety(manifest, receipt, entry, signal):
    # The fixed native writer puts safety flags on the hash-binding receipt,
    # not on v3_shared_data.manifest.v1. Never manufacture source fields.
    native_manifest = manifest.get('schema_version') == 'v3_shared_data.manifest.v1'
    native_receipt = receipt.get('schema_version') == 'v3_shared_data.receipt.v1'
    if native_manifest or native_receipt:
        if not (native_manifest and native_receipt):
            raise ValueError('M06_DELIVERY_POOL_SCHEMA')
        if (not isinstance(entry.get('owner'), str) or not entry['owner']
                or receipt.get('owner') != entry['owner']
                or not isinstance(entry.get('run_id'), str) or not entry['run_id']
                or manifest.get('signal_date') != signal
                or manifest.get('temporal_cutoff_safe') is not True
                or type(manifest.get('row_count')) is not int or manifest['row_count'] != 100):
            raise ValueError('M06_DELIVERY_POOL_IDENTITY')
        _safety(manifest, required=False)  # Explicit contradictory flags still fail.
    else:
        _safety(manifest)  # No compatibility exception for another schema.
    _safety(receipt)


def _payload(capture, family, relative, expected):
    sha(expected)
    if _observe(capture, family, relative) != expected:
        raise ValueError('M06_DELIVERY_PAYLOAD_HASH')


def _capture_inputs(config, signal, target):
    capture = dict(roots=dict(store=str(no_symlinks(config['original_store_root'])),
        assets=str(no_symlinks(config['original_asset_root']))), records={}, observed_times=[])
    metadata = lambda family, relative, **kw: _observe(capture, family, relative, metadata=True, **kw)
    paths = set()
    for kind, relative_key, hash_key in (
            ('panel', 'panel_relative', 'panel_sha256'),
            ('model', 'bundle_relative', 'bundle_sha256'),
            ('name', 'dictionary_relative', 'dictionary_sha256')):
        pointer_name = kind+'_latest.json'
        pointer = metadata('assets', pointer_name, optional=kind == 'name')
        if pointer is None:
            continue
        relative = _relative(pointer['manifest_relative'])
        manifest = metadata('assets', relative)
        payload = _relative(manifest[relative_key])
        current = {pointer_name, relative, payload}
        if len(current) != 3 or paths.intersection(current):
            raise ValueError('M06_DELIVERY_ASSET_CLOSURE')
        paths.update(current)
        _safety(manifest, required=False)
        if manifest.get('production_allowed') is not False:
            raise ValueError('M06_DELIVERY_SAFETY')
        _payload(capture, 'assets', payload, manifest[hash_key])
        if kind == 'panel':
            if manifest.get('panel_max_date') != signal:
                raise ValueError('M06_DELIVERY_PANEL_DATE')
            capture['panel'] = dict(manifest_relative=relative, panel_sha256=manifest[hash_key])
        # The original worker also requires existing conventional/explicit receipts.
        receipts = {str(Path(relative).with_name('receipt.json'))}
        for value in (pointer, manifest):
            if value.get('receipt_relative'):
                receipts.add(_relative(value['receipt_relative']))
        for receipt_name in sorted(receipts):
            receipt = metadata('assets', receipt_name, optional=True)
            if receipt is not None:
                _safety(receipt, required=False)
    latest = metadata('store', MASTER+'latest.json')
    if latest.get('schema_version') != 'v3_shared_data.hk_security_master_latest.v1':
        raise ValueError('M06_DELIVERY_MASTER_SCHEMA')
    entries = latest.get('entries')
    if not isinstance(entries, dict):
        raise ValueError('M06_DELIVERY_MASTER_ENTRIES')
    if signal not in entries:
        raise FileNotFoundError('M06_DELIVERY_MASTER_NOT_DELIVERED')
    entry = entries[signal]
    manifest = metadata('store', MASTER+_relative(entry['manifest_relative']))
    receipt = metadata('store', MASTER+_relative(entry['receipt_relative']))
    if (manifest.get('schema_version') != 'v3_shared_data.hk_security_master_manifest.v1'
            or receipt.get('schema_version') != 'v3_shared_data.hk_security_master_receipt.v1'
            or receipt.get('status') != 'READY'
            or manifest.get('trade_date') != signal or receipt.get('trade_date') != signal
            or not entry.get('run_id') or manifest.get('run_id') != entry['run_id']
            or receipt.get('run_id') != entry['run_id']
            or manifest.get('later_snapshot_price_allowed') is not False):
        raise ValueError('M06_DELIVERY_MASTER_IDENTITY')
    _safety(manifest)
    _safety(receipt)
    if sha256_json(manifest) != receipt.get('manifest_sha256') or manifest.get('artifact_sha256') != receipt.get('artifact_sha256'):
        raise ValueError('M06_DELIVERY_MASTER_HASH')
    _payload(capture, 'store', MASTER+_relative(manifest['artifact_relative']), manifest['artifact_sha256'])
    if aware(manifest['captured_at']).astimezone(HK_TIME).strftime('%Y%m%d') != signal:
        raise ValueError('M06_DELIVERY_MASTER_CAPTURE_DATE')
    capture['observed_times'].append(manifest['captured_at'])
    latest = metadata('store', 'latest.json', optional=True)
    if latest is not None:
        if not isinstance(latest.get('entries'), dict):
            raise ValueError('M06_DELIVERY_SOURCE_LATEST')
        pool_key = target+'/'+ROLE
        entry = latest['entries'].get(pool_key)
        if pool_key in latest['entries']:
            if not isinstance(entry, dict):
                raise ValueError('M06_DELIVERY_POOL_IDENTITY')
            manifest = metadata('store', _relative(entry['manifest_relative']))
            receipt = metadata('store', _relative(entry['receipt_relative']))
            if (manifest.get('trade_date') != target or receipt.get('trade_date') != target
                    or receipt.get('status') != 'READY' or receipt.get('role') != ROLE
                    or receipt.get('run_id') != entry.get('run_id')):
                raise ValueError('M06_DELIVERY_POOL_IDENTITY')
            _pool_safety(manifest, receipt, entry, signal)
            if (sha256_json(manifest) != receipt.get('manifest_sha256')
                    or manifest.get('artifact_sha256') != receipt.get('artifact_sha256')
                    or manifest.get('artifact_relative') != entry['artifact_relative']):
                raise ValueError('M06_DELIVERY_POOL_HASH')
            _payload(capture, 'store', entry['artifact_relative'], manifest['artifact_sha256'])
            for stamp in (manifest['captured_at'], receipt['finished_at']):
                aware(stamp)
                capture['observed_times'].append(stamp)
    capture['files'] = {name: record['sha256'] for (family, name), record in capture['records'].items() if record and family == 'assets'}
    capture['source_files'] = {name: record['sha256'] for (family, name), record in capture['records'].items() if record and family == 'store'}
    return capture


def _recheck_capture(capture):
    for (family, relative), expected in capture['records'].items():
        try:
            with _file(capture['roots'][family], relative) as fd:
                actual = _hash_fd(fd)
        except FileNotFoundError:
            actual = None
        if actual != expected:
            raise ValueError('M06_DELIVERY_INPUT_CHANGED')
    if 'discovery_capture' in capture:
        _recheck_capture(capture['discovery_capture'])
        _check_dispatch_directory(capture['dispatch_directory'])


def _locator(template, scheduled, target):
    if not isinstance(template, str):
        raise ValueError('M06_DELIVERY_PATH_TEMPLATE')
    fields = {'scheduled_date': scheduled, 'signal_date': scheduled, 'target_date': target}
    for _, name, spec, conversion in Formatter().parse(template):
        if name is not None and (name not in fields or spec or conversion):
            raise ValueError('M06_DELIVERY_PATH_TEMPLATE')
    return _relative(template.format(**fields))


def _configuration(config):
    locators = [key for key in ('dispatch_receipt_relative', 'dispatch_receipt_discovery') if key in config]
    if len(locators) != 1:
        raise ValueError('M06_DELIVERY_DISPATCH_LOCATOR')
    if locators[0] == 'dispatch_receipt_discovery' and config[locators[0]] != DISPATCH_DISCOVERY:
        raise ValueError('M06_DELIVERY_DISPATCH_LOCATOR')
    exact_keys(config, ('original_store_root', 'original_asset_root', 'dispatch_receipt_root',
        'lane_receipt_root', 'lane_receipt_relative', 'dispatch_slot', 'snapshot_root',
        'delivery_root', locators[0]))
    originals = [no_symlinks(config[key]) for key in ('original_store_root', 'original_asset_root',
                  'dispatch_receipt_root', 'lane_receipt_root')]
    outputs = [no_symlinks(config[key]) for key in ('snapshot_root', 'delivery_root')]
    def overlap(a, b):
        return a == b or a.is_relative_to(b) or b.is_relative_to(a)
    if overlap(*outputs) or any(overlap(a, b) for a in originals for b in outputs):
        raise ValueError('M06_DELIVERY_ROOT_OVERLAP')
    if not isinstance(config['dispatch_slot'], str) or len(config['dispatch_slot']) != 4 or not config['dispatch_slot'].isascii() or not config['dispatch_slot'].isdigit():
        raise ValueError('M06_DELIVERY_DISPATCH_SLOT')
    return outputs



def _check_directory(path, expected_fd):
    observed = _open_directory(path)
    try:
        before, after = os.fstat(expected_fd), os.fstat(observed)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise ValueError('M06_DELIVERY_ROOT_CHANGED')
    finally:
        os.close(observed)


def _check_roots(config, snapshot_fd, delivery_fd):
    for key, fd, name, marker in (
            ('snapshot_root', snapshot_fd, '.v5-m06-input-snapshots', b'v5.m06-input-snapshots.v1\n'),
            ('delivery_root', delivery_fd, '.v5-m06-input-deliveries', b'v5.m06-input-deliveries.v1\n')):
        _check_directory(config[key], fd)
        if _read_at(fd, None, name) != marker:
            raise ValueError('M06_DELIVERY_ROOT_MARKER')


@contextmanager
def _locked_roots(config):
    snapshot, delivery = _configuration(config)
    fd = _open_directory(snapshot)
    delivery_fd = lock = None
    try:
        if _read_at(fd, None, '.v5-m06-input-snapshots') != b'v5.m06-input-snapshots.v1\n':
            raise ValueError('M06_DELIVERY_SNAPSHOT_ROOT_MARKER')
        delivery_fd = _open_directory(delivery)
        if _read_at(delivery_fd, None, '.v5-m06-input-deliveries') != b'v5.m06-input-deliveries.v1\n':
            raise ValueError('M06_DELIVERY_ROOT_MARKER')
        flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
        try:
            lock = os.open('.delivery.lock', flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=fd)
        except FileExistsError:
            lock = os.open('.delivery.lock', flags, dir_fd=fd)
        if not stat.S_ISREG(os.fstat(lock).st_mode):
            raise ValueError('M06_DELIVERY_LOCK')
        fcntl.flock(lock, fcntl.LOCK_EX)
        _check_roots(config, fd, delivery_fd)
        yield fd, delivery_fd
        _check_roots(config, fd, delivery_fd)
    finally:
        for item in (lock, delivery_fd, fd):
            if item is not None:
                os.close(item)


def _json_optional(fd, name):
    try:
        raw = _read_at(fd, None, name)
    except FileNotFoundError:
        return None
    value = _json(raw)
    if not isinstance(value, dict):
        raise ValueError('M06_DELIVERY_METADATA')
    return value


@contextmanager
def _destination(root, relative):
    components = _relative(relative).split('/')
    fd = _open_directory(root)
    try:
        for part in components[:-1]:
            child = _directory(fd, part)
            os.close(fd)
            fd = child
        yield fd, components[-1]
    finally:
        os.close(fd)


def _copy_capture(capture, snapshot):
    """Stream exact original bytes into no-follow, write-once snapshot files."""
    for (family, relative), expected in capture['records'].items():
        if expected is None:
            continue
        with _destination(snapshot, family+'/'+relative) as (parent, name):
            temporary = '.'+uuid4().hex+'.tmp'
            out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            try:
                with os.fdopen(out, 'wb') as stream, _file(capture['roots'][family], relative) as source:
                    actual = _hash_fd(source, output=stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                if actual != expected:
                    raise ValueError('M06_DELIVERY_INPUT_CHANGED')
                try:
                    os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                except FileExistsError:
                    with _file(snapshot, family+'/'+relative) as existing:
                        observed = _hash_fd(existing)
                    if (observed['sha256'], observed['bytes']) != (expected['sha256'], expected['bytes']):
                        raise ValueError('M06_DELIVERY_SNAPSHOT_COLLISION')
                os.fsync(parent)
            finally:
                os.unlink(temporary, dir_fd=parent)
                os.fsync(parent)


def _snapshot_records(capture):
    return {family+'/'+relative: None if value is None else dict(sha256=value['sha256'], bytes=value['bytes'])
            for (family, relative), value in capture['records'].items()}


def _verify_snapshot(snapshot, records):
    if not isinstance(records, dict) or len(records) > MAX_FILES:
        raise ValueError('M06_DELIVERY_SNAPSHOT_INVENTORY')
    for relative, expected in records.items():
        try:
            with _file(snapshot, relative) as fd:
                actual = _hash_fd(fd)
        except FileNotFoundError:
            actual = None
        if expected is None:
            if actual is not None:
                raise ValueError('M06_DELIVERY_SNAPSHOT_CHANGED')
        elif actual is None or (actual['sha256'], actual['bytes']) != (expected['sha256'], expected['bytes']):
            raise ValueError('M06_DELIVERY_SNAPSHOT_HASH')


def _sealed_pool_method(snapshot, records, target):
    # Decide only from the verified sealed latest bytes, never a live pointer.
    key = 'store/latest.json'
    if key not in records:
        raise ValueError('M06_DELIVERY_SNAPSHOT_INVENTORY')
    if records[key] is None:
        return 'GENERATE_IF_ABSENT'
    with _file(snapshot, key) as fd:
        raw = _read_regular(fd, MAX_JSON_BYTES)
    if hashlib.sha256(raw).hexdigest() != records[key]['sha256']:
        raise ValueError('M06_DELIVERY_SNAPSHOT_HASH')
    latest = _json(raw)
    if not isinstance(latest, dict) or not isinstance(latest.get('entries'), dict):
        raise ValueError('M06_DELIVERY_SOURCE_LATEST')
    pool_key = target+'/'+ROLE
    if pool_key not in latest['entries']:
        return 'GENERATE_IF_ABSENT'
    if not isinstance(latest['entries'][pool_key], dict):
        raise ValueError('M06_DELIVERY_POOL_IDENTITY')
    return 'EXISTING_VERIFIED_POOL'


def _sealed_result(config, scheduled, target, pointer, delivery_fd, *, reused):
    exact_keys(pointer, ('snapshot_relative', 'seal_sha256'))
    relative = _relative(pointer['snapshot_relative'])
    if '/' in relative:
        raise ValueError('M06_DELIVERY_SNAPSHOT_PATH')
    sha(pointer['seal_sha256'])
    snapshot = Path(config['snapshot_root'])/relative
    with _file(snapshot, 'seal.json') as fd:
        raw = _read_regular(fd, MAX_JSON_BYTES)
    if hashlib.sha256(raw).hexdigest() != pointer['seal_sha256']:
        raise ValueError('M06_DELIVERY_SNAPSHOT_SEAL_HASH')
    seal = _json(raw)
    exact_keys(seal, ('schema_version', 'scheduled_date', 'target_date', 'config_sha256',
        'input_sha256', 'records', 'delivery', 'upstream_evidence', 'natural_verified', *SAFETY))
    identity = {key: seal[key] for key in ('scheduled_date', 'target_date', 'config_sha256',
                                          'records', 'upstream_evidence')}
    if (sha256_json(identity) != seal['input_sha256']
            or relative != target+'-'+seal['input_sha256'] or seal['natural_verified'] is not False):
        raise ValueError('M06_DELIVERY_SNAPSHOT_IDENTITY')
    _safety(seal)
    if (seal['schema_version'] != SEAL_SCHEMA or seal['config_sha256'] != sha256_json(config)
            or seal['scheduled_date'] != scheduled or seal['target_date'] != target):
        raise ValueError('M06_DELIVERY_SNAPSHOT_IDENTITY')
    _verify_snapshot(snapshot, seal['records'])
    delivery = seal['delivery']
    if (delivery['target_date'] != target or delivery['signal_date'] != scheduled
            or delivery['eligibility_source_date'] != scheduled
            or delivery['schema_version'] != DELIVERY_SCHEMA or delivery['status'] != 'READY'):
        raise ValueError('M06_DELIVERY_SNAPSHOT_IDENTITY')
    for family, key in (('assets', 'files'), ('store', 'source_files')):
        expected = {name[len(family)+1:]: item['sha256'] for name, item in seal['records'].items()
                    if name.startswith(family+'/') and item is not None}
        if expected != delivery[key]:
            raise ValueError('M06_DELIVERY_SNAPSHOT_INVENTORY')
    observed = _json_optional(delivery_fd, target+'.json')
    if observed is not None and observed != delivery:
        raise ValueError('M06_DELIVERY_EXISTING_CONFLICT')
    _check_directory(config['delivery_root'], delivery_fd)
    if observed is None:
        _write(delivery_fd, target+'.json', delivery)
    raw_delivery = _read_at(delivery_fd, None, target+'.json')
    if raw_delivery != canonical_bytes(delivery):
        raise ValueError('M06_DELIVERY_READBACK')
    return dict(status='REUSED_M06_INPUT_DELIVERY' if reused else 'READY',
        delivery=delivery, delivery_sha256=hashlib.sha256(raw_delivery).hexdigest(),
        store_root=str(snapshot/'store'), asset_root=str(snapshot/'assets'),
        seal_sha256=pointer['seal_sha256'],
        production_method=_sealed_pool_method(snapshot, seal['records'], target))


def prepare_input_delivery(config, scheduled_date, target_date, *, now=None):
    """Seal one D -> next-HK-session delivery; calendar eligibility stays in P0.

    ``now`` is only an optional lower-bound observation. It never supplies the
    completion time. Reuse reads the sealed bytes and never refreshes live input
    pointers, completion time, or identity. Missing original files may wait;
    malformed, mutated, overlapping or contradictory evidence fails closed.
    """
    trade_date(scheduled_date)
    trade_date(target_date)
    if scheduled_date >= target_date:
        raise ValueError('M06_DELIVERY_DATES')
    if now is not None:
        now = aware(now.isoformat())
    with _locked_roots(config) as (root_fd, delivery_fd):
        pointer = _json_optional(root_fd, target_date+'.json')
        if pointer is not None:
            return _sealed_result(config, scheduled_date, target_date, pointer, delivery_fd, reused=True)
        if _json_optional(delivery_fd, target_date+'.json') is not None:
            raise ValueError('M06_DELIVERY_UNSEALED_EXISTING')
        try:
            # No receipt for this close day is ordinary waiting, even while the
            # previous day's panel remains current. Never relabel that old panel.
            candidates = (_dispatch_candidates(config, scheduled_date)
                if 'dispatch_receipt_discovery' in config else None)
            capture = _capture_inputs(config, scheduled_date, target_date)
            _capture_upstream(capture, config, scheduled_date, target_date, candidates=candidates)
            _recheck_capture(capture)
        except FileNotFoundError:
            return dict(status='WAITING_M06_INPUT_DELIVERY')
        identity = dict(scheduled_date=scheduled_date, target_date=target_date,
            config_sha256=sha256_json(config), records=_snapshot_records(capture),
            upstream_evidence=capture['upstream_evidence'])
        input_sha = sha256_json(identity)
        relative = target_date+'-'+input_sha
        snapshot_fd = _directory(root_fd, relative)
        snapshot = Path(config['snapshot_root'])/relative
        try:
            sealed = _json_optional(snapshot_fd, 'seal.json')
            if sealed is None:
                _check_roots(config, root_fd, delivery_fd)
                _check_directory(snapshot, snapshot_fd)
                _copy_capture(capture, snapshot)
                _check_roots(config, root_fd, delivery_fd)
                _check_directory(snapshot, snapshot_fd)
                records = _snapshot_records(capture)
                _verify_snapshot(snapshot, records)
                _recheck_capture(capture)
                completed = aware(_utc_now().isoformat())
                if ((now is not None and completed < now)
                        or any(completed < aware(stamp) for stamp in capture['observed_times'])):
                    raise ValueError('M06_DELIVERY_CLOCK_REGRESSION')
                delivery = dict(schema_version=DELIVERY_SCHEMA, status='READY',
                    target_date=target_date, signal_date=scheduled_date, eligibility_source_date=scheduled_date,
                    completed_at=completed.isoformat(), files=capture['files'], source_files=capture['source_files'])
                sealed = dict(schema_version=SEAL_SCHEMA, scheduled_date=scheduled_date,
                    target_date=target_date, config_sha256=sha256_json(config), input_sha256=input_sha,
                    records=records, delivery=delivery, upstream_evidence=capture['upstream_evidence'],
                    natural_verified=False, **dict.fromkeys(SAFETY, False))
                _write_once(snapshot_fd, 'seal.json', canonical_bytes(sealed))
            seal_raw = _read_at(snapshot_fd, None, 'seal.json')
        finally:
            os.close(snapshot_fd)
        pointer = dict(snapshot_relative=relative, seal_sha256=hashlib.sha256(seal_raw).hexdigest())
        _check_roots(config, root_fd, delivery_fd)
        _write_once(root_fd, target_date+'.json', canonical_bytes(pointer))
        return _sealed_result(config, scheduled_date, target_date, pointer, delivery_fd, reused=False)


def _row_envelope(row):
    # Installed original wrapper confirmed read-only on Mac, 2026-10-13.
    # Both fields directly contain the same authority envelope (no nesting).
    envelope = row.get('_authoritative_payload')
    if (not isinstance(envelope, dict) or row.get('source_result') != envelope
            or envelope.get('overall_status') != 'READY' or envelope.get('status') != 'READY'):
        raise ValueError('M06_DELIVERY_ENVELOPE_CONTRADICTION')
    return envelope


def _capture_exact_upstream(capture, config, scheduled, target):
    workload = 'research_panel_daily_hk'
    capture['roots'].update(dispatch=config['dispatch_receipt_root'], lane=config['lane_receipt_root'])
    dispatch_relative = _locator(config['dispatch_receipt_relative'], scheduled, target)
    lane_relative = _locator(config['lane_receipt_relative'], scheduled, target)
    dispatch = _observe(capture, 'dispatch', dispatch_relative, metadata=True)
    if (dispatch.get('schema_version') != 'v3_5.dispatch.v1'
            or dispatch.get('mode') != 'LIVE' or dispatch.get('status') != 'SUCCEEDED'
            or dispatch.get('business_date') != scheduled or dispatch.get('scheduled_date') != scheduled
            or dispatch.get('slot') != config['dispatch_slot']):
        raise ValueError('M06_DELIVERY_DISPATCH_IDENTITY')
    for key in ('succeeded_workload_ids', 'invoked_workload_ids'):
        values = dispatch.get(key)
        if (not isinstance(values, list) or any(not isinstance(value, str) for value in values)
                or len(values) != len(set(values)) or values.count(workload) != 1):
            raise ValueError('M06_DELIVERY_DISPATCH_WORKLOAD')
    dates = dispatch.get('resolved_dates', {}).get(workload)
    if not isinstance(dates, dict) or any(dates.get(key) != scheduled for key in ('scheduled_date', 'signal_date', 'target_date')):
        raise ValueError('M06_DELIVERY_DISPATCH_DATES')
    rows = dispatch.get('workload_results')
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('M06_DELIVERY_DISPATCH_WORKLOAD')
    rows = [row for row in rows if row.get('workload_id') == workload]
    if (len(rows) != 1 or rows[0].get('status') != 'SUCCEEDED'
            or type(rows[0].get('exit_code')) is not int or rows[0]['exit_code'] != 0):
        raise ValueError('M06_DELIVERY_DISPATCH_WORKLOAD')
    finished = aware(dispatch['finished_at'])
    slot = config['dispatch_slot']
    earliest = aware(f'{scheduled[:4]}-{scheduled[4:6]}-{scheduled[6:]}T{slot[:2]}:{slot[2:]}:00+08:00')
    if finished.astimezone(HK_TIME).strftime('%Y%m%d') != scheduled or finished < earliest:
        raise ValueError('M06_DELIVERY_DISPATCH_FINISHED_AT')
    envelope = _row_envelope(rows[0])
    if (envelope.get('schema_version') != 'v3.macos.research_panel_authority_envelope.v1'
            or envelope.get('lane') != 'HK' or envelope.get('target_date') != scheduled):
        raise ValueError('M06_DELIVERY_ENVELOPE_IDENTITY')
    _safety(envelope, required=False)
    lane_binding = envelope['lanes']['HK']
    if lane_binding.get('status') != 'READY' or type(lane_binding.get('receipt_bytes')) is not int:
        raise ValueError('M06_DELIVERY_LANE_IDENTITY')
    sha(lane_binding['receipt_sha256'])
    # Compare the original lane receipt's raw bytes/hash before JSON parsing.
    lane_sha = _observe(capture, 'lane', lane_relative)
    record = capture['records'][('lane', lane_relative)]
    if lane_sha != lane_binding['receipt_sha256'] or record['bytes'] != lane_binding['receipt_bytes']:
        raise ValueError('M06_DELIVERY_LANE_RAW_HASH')
    lane = _observe(capture, 'lane', lane_relative, metadata=True)
    if (lane.get('schema_version') != 'v3.macos.research_panel_receipt.v1'
            or lane.get('lane') != 'HK' or lane.get('target_date') != scheduled
            or lane.get('status') != 'READY'):
        raise ValueError('M06_DELIVERY_LANE_IDENTITY')
    _safety(lane)
    authority = lane['authority']
    _safety(authority)
    if (authority.get('status') != 'READY' or authority.get('through_date') != scheduled
            or authority.get('target_date') != scheduled
            or authority.get('manifest_relative') != capture['panel']['manifest_relative']
            or authority.get('panel_sha256') != capture['panel']['panel_sha256']):
        raise ValueError('M06_DELIVERY_PANEL_AUTHORITY')
    capture['observed_times'].append(finished.isoformat())
    capture['upstream_evidence'] = dict(dispatch_relative=dispatch_relative,
        dispatch_sha256=capture['records'][('dispatch', dispatch_relative)]['sha256'],
        dispatch_slot=config['dispatch_slot'], panel_finished_at=dispatch['finished_at'],
        envelope_sha256=sha256_json(envelope), lane_relative=lane_relative,
        lane_receipt_sha256=lane_sha, lane_receipt_bytes=record['bytes'],
        panel_manifest_relative=capture['panel']['manifest_relative'],
        panel_sha256=capture['panel']['panel_sha256'])



def _check_dispatch_directory(observed):
    fd = _open_directory(observed['path'])
    try:
        if _identity(os.fstat(fd)) != observed['identity']:
            raise ValueError('M06_DELIVERY_DISPATCH_DIRECTORY_CHANGED')
    finally:
        os.close(fd)


def _dispatch_candidates(config, scheduled):
    """Only the original scheduled-day/slot directory, never latest or mtime."""
    if config.get('dispatch_receipt_discovery') != DISPATCH_DISCOVERY:
        raise ValueError('M06_DELIVERY_DISPATCH_LOCATOR')
    trade_date(scheduled)
    relative = _relative(scheduled+'/'+config['dispatch_slot'])
    path = Path(config['dispatch_receipt_root'])/relative
    fd = _open_directory(path)
    try:
        observed = dict(path=str(path), identity=_identity(os.fstat(fd)), names=[])
        # Bound iteration even if the directory contains unrelated temp files.
        with os.scandir(fd) as entries:
            for index, entry in enumerate(entries):
                if index >= 256:
                    raise ValueError('M06_DELIVERY_DISPATCH_SCAN_LIMIT')
                if not re.fullmatch(r'[0-9a-f]{32}\.dispatch-receipt\.json', entry.name):
                    continue
                if not stat.S_ISREG(entry.stat(follow_symlinks=False).st_mode):
                    raise ValueError('M06_DELIVERY_DISPATCH_FILE_TYPE')
                observed['names'].append(relative+'/'+entry.name)
                if len(observed['names']) > MAX_DISPATCH_RECEIPTS:
                    raise ValueError('M06_DELIVERY_DISPATCH_SCAN_LIMIT')
        _check_dispatch_directory(observed)
    finally:
        os.close(fd)
    if not observed['names']:
        raise FileNotFoundError('M06_DELIVERY_DISPATCH_NOT_DELIVERED')
    observed['names'].sort()
    return observed


def _capture_upstream(capture, config, scheduled, target, *, candidates=None):
    if 'dispatch_receipt_discovery' not in config:
        return _capture_exact_upstream(capture, config, scheduled, target)
    if 'dispatch_receipt_relative' in config:
        raise ValueError('M06_DELIVERY_DISPATCH_LOCATOR')
    directory = candidates if candidates is not None else _dispatch_candidates(config, scheduled)
    observations = dict(roots=dict(dispatch=config['dispatch_receipt_root'],
                                   lane=config['lane_receipt_root']), records={})
    eligible = []
    rejected = {'M06_DELIVERY_DISPATCH_IDENTITY', 'M06_DELIVERY_DISPATCH_WORKLOAD',
        'M06_DELIVERY_DISPATCH_DATES', 'M06_DELIVERY_DISPATCH_FINISHED_AT',
        'M06_DELIVERY_ENVELOPE_CONTRADICTION', 'M06_DELIVERY_ENVELOPE_IDENTITY',
        'M06_DELIVERY_LANE_RAW_HASH', 'M06_DELIVERY_LANE_IDENTITY', 'M06_DELIVERY_PANEL_AUTHORITY'}
    for relative in directory['names']:
        trial = dict(capture, roots=dict(capture['roots']), records=dict(capture['records']),
                     observed_times=list(capture['observed_times']))
        exact = dict(config, dispatch_receipt_relative=relative)
        try:
            _capture_exact_upstream(trial, exact, scheduled, target)
            finished = aware(trial['upstream_evidence']['panel_finished_at'])
            if finished <= _utc_now():
                eligible.append((finished, trial['upstream_evidence']['dispatch_sha256'], relative, trial))
        except ValueError as error:
            if str(error) not in rejected:
                raise
        finally:
            for key, record in trial['records'].items():
                if key[0] not in ('dispatch', 'lane'):
                    continue
                previous = observations['records'].get(key, record)
                if record != previous:
                    raise ValueError('M06_DELIVERY_INPUT_CHANGED')
                observations['records'][key] = record
            if sum(item['bytes'] for (family, _), item in observations['records'].items()
                   if family == 'dispatch') > MAX_DISPATCH_BYTES:
                raise ValueError('M06_DELIVERY_DISPATCH_BYTES_LIMIT')
    _recheck_capture(observations)
    _check_dispatch_directory(directory)
    if not eligible:
        raise FileNotFoundError('M06_DELIVERY_DISPATCH_NO_MATCHING_SUCCESS')
    # Every eligible receipt binds the same captured lane raw hash and panel.
    # This is a new explicit V5 selection policy, not an upstream latest rule.
    selected = min(eligible, key=lambda item:item[:3])[3]
    capture.update(selected)
    capture['discovery_capture'] = observations
    capture['dispatch_directory'] = directory

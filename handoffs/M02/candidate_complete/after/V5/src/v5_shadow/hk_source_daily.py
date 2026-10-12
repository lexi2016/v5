"""M02 source identity binding, immutable publication and independent readback.

No acquisition, inference, scoring or eligibility approval. The three existing
owners remain authoritative; a successful binding is not historical availability.
"""
import sys
from pathlib import Path
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copy
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
import stat
import subprocess
from types import ModuleType
from zoneinfo import ZoneInfo
from v5_shadow.composition import no_symlinks
from v5_shadow.contracts import aware, sha, trade_date
from v5_shadow.digests import canonical_bytes, sha256_json, MAX_JSON_BYTES
from v5_shadow.hk_preselection import _source_bytes, _HKLoader, DESCRIPTOR_SHA256
from v5_shadow.hk_membership_recovery import PIN as MEMBERSHIP_PIN
from v5_shadow.membership_reader import read_private as read_membership
from v5_shadow.native_identity_reader import read_private as read_native_identity
from v5_shadow.m02_input_snapshot import snapshot
from v5_shadow.module_api import _read_regular

SCHEMA = 'v5.m02.hk_source_binding.v2'
RECEIPT_SCHEMA = 'v5.m02.hk_source_receipt.v1'
POINTER_SCHEMA = 'v5.m02.hk_source_pointer.v1'
MARKER = b'v5.hk-source-root.v1\n'
HK = ZoneInfo('Asia/Hong_Kong')
FLAGS = dict(formal_eligibility_verified=False, historical_eligible=False,
             production_allowed=False, buy_gate_updated=False, orders_sent=False)
# M02-local streaming budgets; never change the shared/native JSON limits.
ASSET_MAX_FILES = 9
ASSET_MAX_FILE_BYTES = 64 * 1024**2
ASSET_MAX_TOTAL_BYTES = 128 * 1024**2
_SAFE_ROOT = None


class SourceRejected(ValueError):
    def __init__(self, sources):
        self.sources = sources
        super().__init__('M02_SOURCES_REJECTED:' + ','.join(
            name + ':' + value.get('reason', '') for name, value in sources.items()
            if value['status'] != 'VERIFIED'))


def _safe_root():
    """Load exactly the pinned owner's FD/locking implementation, unmodified."""
    global _SAFE_ROOT
    raw = _source_bytes()['infrastructure/owned_io.py']
    if _SAFE_ROOT is None:
        module = ModuleType('_m02_pinned_owned_io')
        exec(compile(raw, 'pinned:infrastructure/owned_io.py', 'exec'), module.__dict__)
        _SAFE_ROOT = module.SafeRoot
    return _SAFE_ROOT


def _asset_snapshot(binding):
    """Streaming frozen-asset identities; separate from the native JSON limits.

    The fixed six required files and three optional name files; 64 MiB per
    asset, 128 MiB total. JSON metadata remains at the original 16 MiB limit. No arbitrary memory-sized
    reads, symlinks, special files, or unstable descriptor identities are accepted.
    This does not validate a model: the unchanged pinned loader still does that.
    """
    if (not isinstance(binding, dict) or set(binding) != {'root', 'files'}
            or not isinstance(binding['files'], dict) or not 1 <= len(binding['files']) <= ASSET_MAX_FILES):
        raise ValueError('M02_ASSET_BINDING')
    io = _safe_root()(no_symlinks(binding['root']))
    result = {}; total = 0
    for relative, expected in binding['files'].items():
        sha(expected)
        with io.parent(relative) as (parent, name):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode) or before.st_size > ASSET_MAX_FILE_BYTES:
                    raise ValueError('M02_ASSET_SIZE_OR_TYPE')
                total += before.st_size
                if total > ASSET_MAX_TOTAL_BYTES:
                    raise ValueError('M02_ASSET_TOTAL_LIMIT')
                digest = hashlib.sha256(); size = 0
                while block := os.read(fd, 1024 * 1024):
                    size += len(block)
                    if size > before.st_size:
                        raise ValueError('M02_ASSET_CHANGED')
                    digest.update(block)
                after = os.fstat(fd)
                keys = ('st_ino', 'st_dev', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
                if tuple(getattr(before, k) for k in keys) != tuple(getattr(after, k) for k in keys) or size != before.st_size:
                    raise ValueError('M02_ASSET_CHANGED')
            finally:
                os.close(fd)
        if digest.hexdigest() != expected:
            raise ValueError('M02_ASSET_SHA')
        result[relative] = dict(bytes=size, sha256=expected)
    return result


def _snapshot_source(name, binding):
    return _asset_snapshot(binding) if name == 'panel' else snapshot(binding)


def _read(io, relative):
    with io.parent(relative) as (parent, name):
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            return _read_regular(fd, MAX_JSON_BYTES)
        finally:
            os.close(fd)


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('M02_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def reject(value):
        raise ValueError('M02_NONFINITE_JSON:' + value)
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)
    if not isinstance(value, dict):
        raise ValueError('M02_JSON_OBJECT_REQUIRED')
    return value


def _private_root(root, inputs=()):
    root = no_symlinks(root)
    io = _safe_root()(root)
    with io.directory() as fd:
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError('M02_PRIVATE_ROOT_REQUIRED')
        for binding in inputs:
            source = no_symlinks(binding['root'])
            if source.is_relative_to(root) or root.is_relative_to(source):
                raise ValueError('M02_INPUT_OUTPUT_OVERLAP')
    if _read(io, '.v5-hk-source-root') != MARKER:
        raise ValueError('M02_PRIVATE_ROOT_MARKER')
    return io


def _validate_request(request):
    fields = {'private_root', 'inputs', 'target_date', 'signal_date',
              'eligibility_source_date', 'cutoff', 'require_pit'}
    if not isinstance(request, dict) or set(request) != fields:
        raise ValueError('M02_REQUEST_FIELDS')
    target = trade_date(request['target_date'])
    signal = trade_date(request['signal_date'])
    eligibility = trade_date(request['eligibility_source_date'])
    if not signal < target or not eligibility <= target:
        raise ValueError('M02_THREE_DATES')
    cutoff = aware(request['cutoff'])
    if cutoff.astimezone(HK).strftime('%Y%m%d') != target:
        raise ValueError('M02_CUTOFF_DATE')
    if type(request['require_pit']) is not bool:
        raise ValueError('M02_PIT_MODE')
    inputs = request['inputs']
    if not isinstance(inputs, dict) or set(inputs) != {'panel', 'membership', 'native'}:
        raise ValueError('M02_INPUTS')
    for name, binding in inputs.items():
        _snapshot_source(name, binding)
    _private_root(request['private_root'], inputs.values())
    canonical_bytes(request)
    return request


def _verified(value, required, name):
    if (not isinstance(value, dict) or value.get('error') or value.get('diagnostic')
            or not set(required) <= set(value)):
        raise ValueError('M02_' + name + '_CONTRACT')
    canonical_bytes(value)
    return copy.deepcopy(value)


def _time(value, cutoff, date=None):
    stamp = aware(value)
    if stamp > aware(cutoff):
        raise ValueError('M02_SOURCE_AFTER_CUTOFF')
    if date is not None and stamp.astimezone(HK).strftime('%Y%m%d') != date:
        raise ValueError('M02_SOURCE_TIME_DATE')
    return stamp


def _membership(request):
    binding = request['inputs']['membership']; target = request['target_date']
    value = _verified(read_membership(binding['root'], binding['files'], target),
        ('target_date', 'request_sha256', 'source_capsule_sha256', 'codes', 'source'), 'MEMBERSHIP')
    expected = dict(root=binding['root'], files=binding['files'], target_date=target)
    if (value['target_date'] != target or value['request_sha256'] != sha256_json(expected)
            or value['source_capsule_sha256'] != MEMBERSHIP_PIN
            or not isinstance(value['codes'], list) or not value['codes']
            or not isinstance(value['source'], dict)):
        raise ValueError('M02_MEMBERSHIP_IDENTITY')
    source = value['source']
    for key in ('run_id', 'capture_run_id', 'owner', 'producer_owner', 'contract_owner',
                'sha256', 'acquired_at', 'available_at', 'source_date'):
        if not source.get(key):
            raise ValueError('M02_MEMBERSHIP_SOURCE_' + key)
    if source['source_date'] != target:
        raise ValueError('M02_MEMBERSHIP_DATE')
    acquired = _time(source['acquired_at'], request['cutoff'], target)
    available = _time(source['available_at'], request['cutoff'], target)
    if acquired > available:
        raise ValueError('M02_MEMBERSHIP_TIME_ORDER')
    # Original read_at is the current read's clock, not immutable source identity.
    # The original as_of gate also constrains that witness. Calling read_private
    # without as_of cannot establish historical availability; never infer it.
    source.pop('read_at', None)
    return dict(status='VERIFIED', identity=value,
                times={k: source[k] for k in ('acquired_at', 'available_at')}, pit_verified=False)


def _native(request):
    binding = request['inputs']['native']; date = request['eligibility_source_date']
    value = _verified(read_native_identity(binding, date),
                      ('master', 'manifest', 'request_sha256', 'owner_source_sha256'), 'NATIVE')
    manifest = value['manifest']
    if (value['request_sha256'] != sha256_json(dict(binding=binding, date=date))
            or value['owner_source_sha256'] != DESCRIPTOR_SHA256
            or not isinstance(value['master'], dict) or not value['master']
            or not isinstance(manifest, dict) or manifest.get('trade_date') != date
            or not manifest.get('run_id')):
        raise ValueError('M02_NATIVE_IDENTITY')
    sha(manifest.get('artifact_sha256'))
    _time(manifest.get('captured_at'), request['cutoff'], date)
    times = {'captured_at': manifest['captured_at']}
    # The original master owner has no publication-time witness. Never invent one.
    return dict(status='VERIFIED', identity=value, times=times, pit_verified=False)


def project_frozen_assets(asset):
    """Project the real dataclass without stringifying its manifest dictionaries."""
    return dict(root=str(asset.root), panel_path=str(asset.panel_path),
                panel_manifest=asset.panel_manifest, model_path=str(asset.model_path),
                model_manifest=asset.model_manifest,
                name_dictionary_path=None if asset.name_dictionary_path is None else str(asset.name_dictionary_path))


def _panel_date(manifest, signal):
    # Original scoring selects rows <= signal. A newer frozen panel can supply
    # reference identity but never proves it was historically available then.
    maximum = trade_date(manifest.get('panel_max_date'))
    if maximum < signal:
        raise ValueError('M02_PANEL_SIGNAL_NOT_COVERED')
    return maximum


def _panel_references(binding):
    """Bind the lexical owner references before its resolver can follow aliases."""
    io = _safe_root()(no_symlinks(binding['root']))
    references = {}; selected = set()
    def bound_json(relative):
        raw = _read(io, relative)
        if hashlib.sha256(raw).hexdigest() != binding['files'][relative]:
            raise ValueError('M02_PANEL_METADATA_SHA')
        return _json(raw)
    for pointer, field in (('panel_latest.json', 'panel_relative'),
                           ('model_latest.json', 'bundle_relative'),
                           ('name_latest.json', 'dictionary_relative')):
        if pointer not in binding['files']:
            if pointer == 'name_latest.json':
                try:
                    _read(io, pointer)
                except FileNotFoundError:
                    continue
            raise ValueError('M02_PANEL_REFERENCE_NOT_BOUND:' + pointer)
        manifest = bound_json(pointer).get('manifest_relative')
        if not isinstance(manifest, str) or manifest not in binding['files']:
            raise ValueError('M02_PANEL_REFERENCE_NOT_BOUND:manifest')
        selected.update((pointer, manifest))
        metadata = bound_json(manifest)
        relative = metadata.get(field)
        if not isinstance(relative, str) or relative not in binding['files']:
            raise ValueError('M02_PANEL_REFERENCE_NOT_BOUND:' + field)
        # Opening via SafeRoot rejects symlinks in the reference and ancestors.
        with io.parent(relative) as (parent, name):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            os.close(fd)
        references[pointer] = (relative, metadata)
        selected.add(relative)
    if selected != set(binding['files']):
        raise ValueError('M02_PANEL_REFERENCE_SET')
    return references


def _bound_projection(asset, binding, references):
    projection = project_frozen_assets(asset)
    root = no_symlinks(binding['root'])
    expected = dict(root=str(root), name_dictionary_path=None)
    for pointer, path_key, manifest_key, hash_key in (
        ('panel_latest.json', 'panel_path', 'panel_manifest', 'panel_sha256'),
        ('model_latest.json', 'model_path', 'model_manifest', 'bundle_sha256'),
        ('name_latest.json', 'name_dictionary_path', None, 'dictionary_sha256'),
    ):
        if pointer not in references:
            continue
        relative, metadata = references[pointer]
        if metadata.get(hash_key) != binding['files'][relative]:
            raise ValueError('M02_PANEL_DECLARED_SHA:' + path_key)
        expected[path_key] = str(root / relative)
        if manifest_key is not None:
            expected[manifest_key] = metadata
    if canonical_bytes(projection) != canonical_bytes(expected):
        raise ValueError('M02_PANEL_PROJECTION_NOT_BOUND')
    return projection


def _panel_worker(request):
    binding = request['inputs']['panel']; before = _asset_snapshot(binding)
    references = _panel_references(binding)
    sources = _source_bytes()
    if any(name in sys.modules for name in ('upstreams', 'contracts', 'infrastructure')):
        raise ValueError('M02_PANEL_REQUIRES_FRESH_PROCESS')
    sys.meta_path.insert(0, _HKLoader(sources))
    calendars = importlib.import_module('contracts.trading_calendar')
    calendar = calendars.load_market_calendar()
    target = request['target_date']; signal = request['signal_date']
    for date in (target, request['eligibility_source_date']):
        state = calendars.resolve_market_states(calendar, date)['hk_securities'].value
        if state not in ('FULL_TRADING_DAY', 'HALF_TRADING_DAY_AM'):
            raise ValueError('M02_HK_NOT_SESSION')
    if calendars.previous_session(calendar, target, market='hk_securities') != signal:
        raise ValueError('M02_HK_SIGNAL_NOT_PREVIOUS_SESSION')
    owner = importlib.import_module('upstreams.v3_shared_data.shared_data.hk_0_2')
    root = Path(binding['root'])
    def audit(event, args):
        if event.startswith(('socket.', 'subprocess.', 'os.exec', 'os.spawn', 'os.posix_spawn')) or event in ('os.system', 'os.fork', 'os.forkpty'):
            raise PermissionError('M02_PANEL_NETWORK_PROCESS_DENIED')
        if event in ('os.mkdir', 'os.remove', 'os.rename', 'os.rmdir', 'os.chmod', 'os.link', 'os.symlink', 'os.truncate', 'os.utime', 'os.chown'):
            raise PermissionError('M02_PANEL_WRITE_DENIED')
        if event == 'open':
            name, _mode, flags = args
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                raise PermissionError('M02_PANEL_WRITE_DENIED')
            if isinstance(name, (str, bytes)):
                path = Path(os.fsdecode(name))
                if path.is_absolute() and path.is_relative_to(root):
                    if str(path.relative_to(root)) not in binding['files']:
                        raise PermissionError('M02_PANEL_UNDECLARED_INPUT')
    sys.addaudithook(audit)
    asset = owner.load_frozen_hk_0_2_assets(root)
    if type(asset) is not owner.FrozenHK02Assets:
        raise ValueError('M02_PANEL_ASSET_TYPE')
    projection = _bound_projection(asset, binding, references)
    _panel_date(projection['panel_manifest'], signal)
    for name in ('panel_path', 'model_path', 'name_dictionary_path'):
        if projection[name] is not None:
            relative = str(Path(projection[name]).relative_to(root))
            if relative not in binding['files']:
                raise ValueError('M02_PANEL_PATH_NOT_BOUND')
    if _asset_snapshot(binding) != before:
        raise ValueError('M02_PANEL_INPUT_CHANGED')
    _source_bytes()
    return dict(identity=projection, request_sha256=sha256_json(request),
                owner_source_sha256=DESCRIPTOR_SHA256)


def _panel(request):
    child = subprocess.run([sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--panel-worker'],
                           input=canonical_bytes(request), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    if child.returncode:
        raise ValueError('M02_PANEL_OWNER_READ_FAILED:' + child.stderr.decode(errors='replace')[-1000:])
    if len(child.stdout) > MAX_JSON_BYTES:
        raise ValueError('M02_PANEL_RESPONSE_LIMIT')
    value = _json(child.stdout)
    if value.get('request_sha256') != sha256_json(request) or value.get('owner_source_sha256') != DESCRIPTOR_SHA256:
        raise ValueError('M02_PANEL_RESPONSE_IDENTITY')
    manifest = value['identity']['panel_manifest']; times = {}
    for name in ('captured_at', 'available_at'):
        if manifest.get(name) is not None:
            _time(manifest[name], request['cutoff']); times[name] = manifest[name]
    if len(times) == 2 and aware(times['captured_at']) > aware(times['available_at']):
        raise ValueError('M02_PANEL_TIME_ORDER')
    # The original frozen panel owner does not verify publication availability.
    return dict(status='VERIFIED', identity=value, times=times, pit_verified=False)


def _collect(request):
    before = {name: _snapshot_source(name, binding) for name, binding in request['inputs'].items()}
    results = {}
    for name, reader in (('membership', _membership), ('native', _native), ('panel', _panel)):
        try:
            results[name] = reader(request)
        except Exception as error:
            results[name] = dict(status='REJECTED', reason=type(error).__name__ + ':' + str(error))
    for name, binding in request['inputs'].items():
        if _snapshot_source(name, binding) != before[name]:
            raise ValueError('M02_INPUT_CHANGED:' + name)
    if any(value['status'] != 'VERIFIED' for value in results.values()):
        raise SourceRejected(results)
    return results


def _binding(request, sources):
    if request['require_pit'] and not all(value['pit_verified'] for value in sources.values()):
        raise ValueError('M02_PIT_AVAILABILITY_UNPROVEN')
    return dict(schema=SCHEMA, request=request, request_sha256=sha256_json(request),
                run_id=sha256_json(dict(request=request, sources=sources)), sources=sources,
                purpose='SOURCE_IDENTITY_ONLY', temporal_status='CANNOT_CONFIRM', **FLAGS)


def _put_immutable(io, name, raw):
    try:
        existing = _read(io, name)
    except FileNotFoundError:
        io.write_bytes(name, raw, require_absent=True)
    else:
        if existing != raw:
            raise ValueError('M02_IMMUTABLE_CONFLICT')


def _saved(io, target, receipt_hash):
    sha(receipt_hash)
    pointer = _json(_read(io, 'slots/' + target + '.json'))
    if (set(pointer) != {'schema', 'target_date', 'run_id', 'binding_sha256', 'receiptHash'}
            or pointer['schema'] != POINTER_SCHEMA or pointer['target_date'] != target
            or pointer['receiptHash'] != receipt_hash):
        raise ValueError('M02_RECEIPT_POINTER_IDENTITY')
    sha(pointer['binding_sha256']); sha(pointer['run_id'])
    binding_raw = _read(io, 'objects/' + pointer['binding_sha256'] + '.json')
    receipt_raw = _read(io, 'receipts/' + receipt_hash + '.json')
    if hashlib.sha256(binding_raw).hexdigest() != pointer['binding_sha256'] or hashlib.sha256(receipt_raw).hexdigest() != receipt_hash:
        raise ValueError('M02_DISK_HASH_MISMATCH')
    binding = _json(binding_raw); receipt = _json(receipt_raw)
    if (binding.get('schema') != SCHEMA or receipt.get('schema') != RECEIPT_SCHEMA
            or receipt.get('binding_sha256') != pointer['binding_sha256']
            or receipt.get('run_id') != pointer['run_id'] or binding.get('run_id') != pointer['run_id']
            or receipt.get('target_date') != target or binding.get('request', {}).get('target_date') != target
            or receipt.get('request_sha256') != binding.get('request_sha256')
            or binding.get('request_sha256') != sha256_json(binding.get('request'))
            or any(binding.get(k) is not v for k, v in FLAGS.items())):
        raise ValueError('M02_DISK_IDENTITY')
    aware(receipt.get('created_at'))
    return dict(binding=binding, receipt=receipt, receiptHash=receipt_hash)


def build_binding(*, private_root, asset_binding, membership_root, membership_files,
                  native_binding, target_date, signal_date, eligibility_source_date,
                  cutoff, require_pit=False):
    request = _validate_request(copy.deepcopy(dict(private_root=str(no_symlinks(private_root)),
        inputs=dict(panel=asset_binding, membership=dict(root=str(membership_root), files=membership_files), native=native_binding),
        target_date=target_date, signal_date=signal_date, eligibility_source_date=eligibility_source_date,
        cutoff=cutoff, require_pit=require_pit)))
    io = _private_root(request['private_root'], request['inputs'].values())
    with io.kernel_lock('.publish.lock'):
        value = _binding(request, _collect(request))
        try:
            pointer = _json(_read(io, 'slots/' + target_date + '.json'))
        except FileNotFoundError:
            pointer = None
        if pointer is not None:
            existing = _saved(io, target_date, pointer.get('receiptHash'))
            if canonical_bytes(existing['binding']) != canonical_bytes(value):
                raise ValueError('M02_IMMUTABLE_CONFLICT')
            return existing
        raw = canonical_bytes(value); binding_sha = hashlib.sha256(raw).hexdigest()
        receipt = dict(schema=RECEIPT_SCHEMA, target_date=target_date, run_id=value['run_id'],
                       binding_sha256=binding_sha, request_sha256=value['request_sha256'],
                       created_at=datetime.now(timezone.utc).isoformat(), purpose='SOURCE_IDENTITY_ONLY')
        receipt_raw = canonical_bytes(receipt); receipt_hash = hashlib.sha256(receipt_raw).hexdigest()
        _put_immutable(io, 'objects/' + binding_sha + '.json', raw)
        _put_immutable(io, 'receipts/' + receipt_hash + '.json', receipt_raw)
        pointer = dict(schema=POINTER_SCHEMA, target_date=target_date, run_id=value['run_id'],
                       binding_sha256=binding_sha, receiptHash=receipt_hash)
        # The one immutable pointer is the atomic commit point for the pair.
        io.write_bytes('slots/' + target_date + '.json', canonical_bytes(pointer), require_absent=True)
        return _saved(io, target_date, receipt_hash)


def read_binding(private_root, target_date, *, receipt_hash):
    """Read-only: only disk-bound source roots/files are accepted, never replacements."""
    target_date = trade_date(target_date)
    io = _private_root(private_root)
    saved = _saved(io, target_date, receipt_hash)
    request = _validate_request(saved['binding']['request'])
    if request['private_root'] != str(no_symlinks(private_root)):
        raise ValueError('M02_READBACK_ROOT')
    actual = _binding(request, _collect(request))
    if canonical_bytes(actual) != canonical_bytes(saved['binding']):
        raise ValueError('M02_READBACK_IDENTITY_MISMATCH')
    return saved


build_source_binding = build_binding
read_source_binding = read_binding

if __name__ == '__main__':
    if sys.argv[1:] != ['--panel-worker']:
        raise SystemExit('M02 supports only its isolated panel reader worker')
    raw = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError('M02_PANEL_REQUEST_LIMIT')
    sys.stdout.buffer.write(canonical_bytes(_panel_worker(_json(raw))))

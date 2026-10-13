"""M06 private, immutable source publication and exact-reference cold readback.

A producer receipt records provenance; it never authorizes source admission.
All source bytes are re-admitted by the unchanged pinned reader through the
verified cold consumer.  The only publication operation is an exclusive hard
link of a complete reference under a same-root process lock.  An incomplete
object is an unknown outcome and is deliberately not overwritten or retried.
"""
from __future__ import annotations

import csv
import fcntl
import hashlib
import importlib
import json
import os
import platform
import stat
import sys
from contextlib import contextmanager
from pathlib import Path

from . import hk_preselection as legacy
from . import hk_preselection_verified as verified
from .composition import no_symlinks, shadow_root
from .contracts import exact_keys, sha, trade_date
from .digests import MAX_JSON_BYTES, canonical_bytes, sha256_json

REFERENCE_SCHEMA = 'v5.hk_preselection_committed_reference.v1'
PRODUCER_SCHEMA = 'v5.hk_preselection_producer_receipt.v1'
SOURCE_KEYS = ('role', 'run_id', 'artifact_sha256', 'manifest_sha256', 'receipt_sha256', 'artifact_relative')
MODES = ('NATURAL', 'MANUAL_RECOVERY', 'RECORDED_INPUT_REPLAY')
CODE_FILES = ('__init__.py', 'hk_preselection_publication.py', 'hk_preselection_verified.py',
              'hk_preselection.py', 'hk_preselection_daily.py', 'a_preselection.py', 'composition.py', 'contracts.py', 'digests.py', 'provider_evidence.py')
DOCUMENTS = ('request.json', 'input_manifest.json', 'code_manifest.json', 'config_manifest.json',
             'dependency_manifest.json', 'producer_receipt.json', 'strict_reader_receipt.json', 'artifact.json')
SOURCE_PROJECTION = {'run_id': 'source_run_id', 'artifact_sha256': 'source_sha256',
                     'manifest_sha256': 'source_manifest_sha256', 'receipt_sha256': 'source_receipt_sha256',
                     'artifact_relative': 'source_path'}


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _clone(value):
    return json.loads(canonical_bytes(value))


def _relative(root, relative):
    if (not isinstance(relative, str) or not relative or '\\' in relative
            or Path(relative).is_absolute() or '..' in Path(relative).parts
            or Path(relative).as_posix() != relative or relative == '.'):
        raise ValueError('M06_PATH_ESCAPE')
    path = no_symlinks(root / relative)
    if not path.is_relative_to(root):
        raise ValueError('M06_PATH_ESCAPE')
    return path


def _read(path, *, limit=None):
    path = no_symlinks(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError('M06_FILE_NOT_REGULAR')
            data = stream.read() if limit is None else stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        live = no_symlinks(path).stat()
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        if identity(before) != identity(after) or identity(after) != identity(live):
            raise ValueError('M06_INPUT_CHANGED')
        if limit is not None and len(data) > limit:
            raise ValueError('M06_METADATA_TOO_LARGE')
        return data
    except (OSError, TypeError) as error:
        raise ValueError('M06_REQUIRED_FILE_MISSING:' + str(path)) from error


def _json(path):
    try:
        value = json.loads(_read(path, limit=MAX_JSON_BYTES))
    except (ValueError, UnicodeError) as error:
        raise ValueError('M06_METADATA_INVALID:' + str(path)) from error
    if not isinstance(value, dict):
        raise ValueError('M06_METADATA_INVALID:' + str(path))
    canonical_bytes(value)
    return value


def _mkdir(path):
    path = no_symlinks(path)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        if not path.is_dir():
            raise ValueError('M06_COMMIT_CONFLICT:directory')
    return no_symlinks(path)


def _parents(path, root):
    relative = path.relative_to(root)
    current = root
    for component in relative.parts:
        current = _mkdir(current / component)


def _fsync_dir(path):
    fd = os.open(no_symlinks(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_new(path, data):
    path = no_symlinks(path)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    except FileExistsError as error:
        raise ValueError('M06_COMMIT_CONFLICT:existing-file') from error
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    _fsync_dir(path.parent)


def _write_json(path, value):
    _write_new(path, canonical_bytes(value))


@contextmanager
def _lock(root):
    lockpath = no_symlinks(root / '.m06-hk-publication.lock')
    fd = os.open(lockpath, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        value = os.fstat(fd)
        if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
            raise ValueError('M06_LOCK_INVALID')
        fcntl.flock(fd, fcntl.LOCK_EX)
        current = no_symlinks(lockpath).stat()
        if (value.st_dev, value.st_ino) != (current.st_dev, current.st_ino):
            raise ValueError('M06_LOCK_INVALID')
        shadow_root(root)
        yield
    finally:
        os.close(fd)


def _source_reference(value):
    if not isinstance(value, dict) or not set(SOURCE_KEYS) <= set(value):
        raise ValueError('M06_SOURCE_REF_INVALID')
    result = {key: value[key] for key in SOURCE_KEYS}
    if result['role'] != legacy.ROLE or not isinstance(result['run_id'], str) or not result['run_id']:
        raise ValueError('M06_SOURCE_REF_INVALID')
    for name in ('artifact_sha256', 'manifest_sha256', 'receipt_sha256'):
        sha(result[name])
    return result


def _producer(receipt, expected):
    if (not isinstance(receipt, dict) or receipt.get('schema_version') != PRODUCER_SCHEMA
            or receipt.get('status') != 'READY'):
        raise ValueError('M06_PRODUCER_RECEIPT_INVALID')
    if _source_reference(receipt.get('verified_source_reference')) != expected:
        raise ValueError('M06_IDENTITY_CHAIN_MISMATCH:producer-reference')
    original = receipt.get('original_result')
    if not isinstance(original, dict):
        raise ValueError('M06_PRODUCER_RECEIPT_INVALID:original-result')
    for key in SOURCE_PROJECTION:
        if original.get(key) != expected[key]:
            raise ValueError('M06_IDENTITY_CHAIN_MISMATCH:producer-original:' + key)
    if original.get('status', 'READY') != 'READY' or original.get('role', legacy.ROLE) != legacy.ROLE:
        raise ValueError('M06_IDENTITY_CHAIN_MISMATCH:producer-original-status')
    method = receipt.get('production_method')
    if method == 'EXISTING_VERIFIED_POOL':
        if receipt.get('model_weights_reverified') is not False:
            raise ValueError('M06_PRODUCER_RECEIPT_INVALID:existing-model-claim')
    elif method == 'FROZEN_MODEL_PRODUCER':
        if receipt.get('model_weights_reverified') is not True:
            raise ValueError('M06_PRODUCER_RECEIPT_INVALID:model-proof')
        from . import hk_preselection_daily as daily
        descriptor = verified._production_sources()
        code = daily._code_manifest()
        worker = receipt.get('worker_request')
        if (not isinstance(worker, dict) or receipt.get('runtime') != descriptor['producer_runtime']
                or receipt.get('code_manifest') != code or receipt.get('implementation_identity') != code
                or receipt.get('dependency_manifest') != daily._dependency_manifest()
                or receipt.get('request_sha256') != sha256_json(worker)):
            raise ValueError('M06_PRODUCER_PROOF_INVALID:worker-runtime-code')
        runtime_inventory = receipt.get('runtime_dependencies')
        packages = runtime_inventory.get('packages') if isinstance(runtime_inventory, dict) else None
        if (not isinstance(runtime_inventory, dict)
                or runtime_inventory != receipt['dependency_manifest']['runtime_dependencies']
                or set(runtime_inventory) != {'packages', 'python', 'executable_sha256'}
                or not isinstance(packages, dict)
                or set(packages) != {'numpy', 'pandas', 'scikit-learn', 'joblib', 'pyarrow', 'fastparquet'}
                or any(not isinstance(value, str) or not value.strip() for value in packages.values())
                or any(packages[name] == 'MISSING' for name in ('numpy', 'pandas'))
                or all(packages[name] == 'MISSING' for name in ('pyarrow', 'fastparquet'))
                or runtime_inventory['python'] != descriptor['producer_runtime']['python']
                or any(packages[name] != descriptor['producer_runtime'][name] for name in ('scikit-learn', 'joblib'))):
            raise ValueError('M06_PRODUCER_PROOF_INVALID:runtime-inventory')
        try:
            sha(runtime_inventory['executable_sha256'])
        except (TypeError, ValueError) as error:
            raise ValueError('M06_PRODUCER_PROOF_INVALID:runtime-inventory') from error
        if not isinstance(receipt.get('input_manifest'), dict) or not isinstance(receipt.get('asset_evidence'), dict):
            raise ValueError('M06_PRODUCER_PROOF_INVALID:inventories')
        if not isinstance(receipt.get('asset_snapshot'), dict):
            raise ValueError('M06_PRODUCER_PROOF_INVALID:asset-snapshot')
    else:
        raise ValueError('M06_PRODUCER_RECEIPT_INVALID:method')
    return receipt


def _validate_result(result, request, expected):
    if (not isinstance(result, dict) or result.get('status') != 'ASSEMBLED'
            or result.get('data_kind') != 'VERIFIED_SOURCE_SNAPSHOT'
            or result.get('model_weights_reverified') is not False
            or any(result.get(key) != value for key, value in legacy.SAFETY.items())):
        reason = result.get('reason', '') if isinstance(result, dict) else ''
        raise ValueError('M06_STRICT_READBACK_FAILED:' + reason)
    if any(result.get(key) != request[key] for key in
           ('target_date', 'signal_date', 'eligibility_source_date', 'research_cutoff')):
        raise ValueError('M06_IDENTITY_CHAIN_MISMATCH:reader-dates')
    if _source_reference(result.get('verified_source_reference')) != expected:
        raise ValueError('M06_IDENTITY_CHAIN_MISMATCH:reader-reference')
    artifact = result.get('artifact')
    if (not isinstance(artifact, dict) or artifact.get('market') != 'HK'
            or artifact.get('trade_date') != request['target_date']
            or artifact.get('status') != 'STRICT_0_2_READY'):
        raise ValueError('M06_STRICT_READBACK_FAILED:artifact')
    for key, output in SOURCE_PROJECTION.items():
        if artifact.get(output) != expected[key]:
            raise ValueError('M06_IDENTITY_CHAIN_MISMATCH:artifact:' + key)
    if not isinstance(artifact.get('rows'), list) or len(artifact['rows']) != 100:
        raise ValueError('M06_ROWS_DIVERGED')
    canonical_bytes(result)
    return result


def _inventory(root, files, *, minimum=8):
    if not isinstance(files, dict) or len(files) < minimum:
        raise ValueError('M06_REQUIRED_FILE_MISSING')
    inventory = {}
    for relative, expected in sorted(files.items()):
        sha(expected)
        data = _read(_relative(root, relative))
        if _digest(data) != expected:
            raise ValueError('M06_INPUT_CHANGED:' + relative)
        item = {'bytes': len(data), 'raw_sha256': expected}
        if relative.endswith('.json'):
            try:
                item['canonical_sha256'] = sha256_json(json.loads(data))
            except (ValueError, UnicodeError) as error:
                raise ValueError('M06_METADATA_INVALID:' + relative) from error
        inventory[relative] = item
    return inventory



def _producer_assets(receipt, request, mode, *, source_root=None, asset_root=None):
    """Recheck receipt claims against actual input bytes; never load a model."""
    snapshot = receipt.get('asset_snapshot')
    if snapshot is None:
        if (receipt['production_method'] == 'FROZEN_MODEL_PRODUCER'
                or receipt.get('asset_binding_status') == 'FROZEN_ASSET_BYTES_CHECKED'):
            raise ValueError('M06_PRODUCER_PROOF_INVALID:asset-snapshot')
        return {}
    if not isinstance(snapshot, dict) or set(snapshot) != {'input_root', 'files'}:
        raise ValueError('M06_PRODUCER_PROOF_INVALID:asset-snapshot')
    source_root = no_symlinks(Path(source_root if source_root is not None else request['input_root']))
    asset_root = no_symlinks(Path(asset_root if asset_root is not None else snapshot['input_root']))
    if source_root.is_relative_to(asset_root) or asset_root.is_relative_to(source_root):
        raise ValueError('SOURCE_OUTPUT_OVERLAP')
    files = snapshot['files']
    inputs = receipt.get('input_manifest')
    if not isinstance(inputs, dict) or inputs.get('asset_files') != files:
        raise ValueError('M06_PRODUCER_PROOF_INVALID:asset-inventory')
    inventory = _inventory(asset_root, files, minimum=0)
    model = receipt['production_method'] == 'FROZEN_MODEL_PRODUCER'
    checked_assets = receipt.get('asset_binding_status') == 'FROZEN_ASSET_BYTES_CHECKED'
    if not (model or checked_assets):
        if mode != 'RECORDED_INPUT_REPLAY' or receipt.get('asset_binding_status') != 'NOT_REVERIFIED_RECORDED_INPUT_ONLY':
            raise ValueError('M06_PRODUCER_PROOF_INVALID:asset-binding')
        return inventory
    from . import hk_preselection_daily as daily
    dates = {key: request[key] for key in ('target_date', 'signal_date', 'eligibility_source_date', 'research_cutoff')}
    if (inputs.get('dates') != dates or inputs.get('data_kind') != 'SOURCE_SNAPSHOT'
            or inputs.get('execution_mode') != mode or not isinstance(inputs.get('source_files'), dict)
            or any(request['files'].get(key) != digest for key, digest in inputs['source_files'].items())):
        raise ValueError('M06_PRODUCER_PROOF_INVALID:input-manifest')
    if model:
        worker = receipt['worker_request']
        if (set(worker) != {'store_root', 'asset_root', 'asset_files', 'source_files', *dates}
                or worker.get('store_root') != request['input_root']
                or worker.get('asset_root') != snapshot['input_root']
                or worker.get('asset_files') != files or worker.get('source_files') != inputs['source_files']
                or any(worker.get(key) != value for key, value in dates.items())
                or receipt['original_result'].get('ok') is not True
                or set(inputs['source_files']) != set(daily._master_paths(source_root, request['eligibility_source_date']))):
            raise ValueError('M06_PRODUCER_PROOF_INVALID:worker-request')
        identity = dict(lane='hk_preselection', target_date=request['target_date'],
                        input_sha256=sha256_json(inputs), research_cutoff=request['research_cutoff'],
                        code_sha256=sha256_json(receipt['code_manifest']),
                        config_sha256=sha256_json(dict(execution_mode=mode, reader=verified.SCHEMA)),
                        dependency_sha256=sha256_json(receipt['dependency_manifest']))
        if receipt.get('computation_identity') != identity:
            raise ValueError('M06_PRODUCER_PROOF_INVALID:computation-identity')
    latest = _json(source_root / 'latest.json')
    try:
        source_entry = latest['entries'][request['target_date'] + '/' + legacy.ROLE]
        manifest_relative = source_entry['manifest_relative']
    except (KeyError, TypeError) as error:
        raise ValueError('M06_PRODUCER_PROOF_INVALID:source-manifest') from error
    if manifest_relative not in request['files']:
        raise ValueError('M06_REQUIRED_FILE_MISSING:' + str(manifest_relative))
    source_manifest = _json(_relative(source_root, manifest_relative))
    provenance = source_manifest.get('provenance', {})
    panel_sha, model_sha = provenance.get('panel_sha256'), provenance.get('model_bundle_sha256')
    sha(panel_sha); sha(model_sha)
    if model and (receipt.get('panel_sha256') != panel_sha or receipt.get('model_bundle_sha256') != model_sha):
        raise ValueError('M06_PRODUCER_PROOF_INVALID:source-assets')
    proof_request = dict(asset_root=str(asset_root), asset_files=files,
                         panel_sha256=panel_sha, model_bundle_sha256=model_sha)
    # This fixed cold entry calls the original load_frozen_hk_0_2_assets only.
    # It hashes the bundle and validates manifests; it does not unpickle/score.
    proof = daily._cold(proof_request, '--assets')
    if (proof.get('status') != 'ASSET_BYTES_VERIFIED' or proof.get('model_weights_reverified') is not False
            or proof.get('asset_evidence') != receipt.get('asset_evidence')):
        raise ValueError('M06_PRODUCER_PROOF_INVALID:original-asset-reader')
    if _inventory(asset_root, files, minimum=0) != inventory:
        raise ValueError('M06_INPUT_CHANGED:producer-assets')
    return inventory

def _code_manifest():
    # The unchanged original descriptor is itself pinned by the original loader.
    sources = legacy._source_bytes()
    base = Path(__file__).resolve().parent
    files = {}
    for name in CODE_FILES:
        data = _read(base / name)
        files['src/v5_shadow/' + name] = {'bytes': len(data), 'raw_sha256': _digest(data)}
    descriptor = _read(legacy.DESCRIPTOR)
    files['contracts/hk_preselection_source_manifest.json'] = {
        'bytes': len(descriptor), 'raw_sha256': _digest(descriptor),
        'canonical_sha256': legacy.DESCRIPTOR_SHA256}
    for relative, data in sorted(sources.items()):
        files['vendor/hk_preselection_baseline/' + relative] = {'bytes': len(data), 'raw_sha256': _digest(data)}
    production = verified._production_sources()
    raw = _read(verified.PRODUCTION_DESCRIPTOR)
    files['contracts/hk_preselection_production_sources.json'] = {
        'bytes': len(raw), 'raw_sha256': _digest(raw),
        'canonical_sha256': verified.PRODUCTION_DESCRIPTOR_SHA256}
    for entry in production['entries']:
        relative = entry['relative_path']
        data = _read(_relative(legacy.BASE.parent, relative))
        files[relative.removeprefix('V5/')] = {'bytes': len(data), 'raw_sha256': _digest(data)}
    return dict(schema_version='v5.hk_preselection_code_manifest.v1', files=files)


def _dependencies():
    # No third-party package is loaded by this read/publication lane. Record
    # exact stdlib/executable bytes rather than inventing a model runtime pass.
    names = ('base64', 'binascii', 'contextlib', 'csv', 'dataclasses', 'datetime',
             'fcntl', 'hashlib', 'importlib', 'importlib.abc', 'importlib.util', 'importlib.metadata',
             'io', 'json', 'json.decoder', 'json.encoder', 'math', 'os', 'pathlib',
             'platform', 're', 'shutil', 'socket', 'stat', 'struct', 'subprocess',
             'sys', 'tempfile', 'threading', 'time', 'typing', 'uuid', 'zoneinfo')
    modules = {}
    for name in names:
        module = importlib.import_module(name)
        path = getattr(module, '__file__', None)
        origin = getattr(getattr(module, '__spec__', None), 'origin', None)
        if path and Path(path).is_file():
            actual = Path(path).resolve()
            data = _read(actual)
            modules[name] = {'origin': str(actual), 'bytes': len(data), 'raw_sha256': _digest(data)}
        else:
            modules[name] = {'origin': origin or 'built-in'}
    executable = Path(sys.executable).resolve()
    return dict(schema_version='v5.hk_preselection_dependency_manifest.v1',
                python_implementation=platform.python_implementation(), python_version=sys.version,
                executable={'path': str(executable), 'raw_sha256': _digest(_read(executable))},
                stdlib=modules, third_party_packages=[], model_runtime_checked=False)


def _config(mode):
    return dict(schema_version='v5.hk_preselection_publication_config.v1', execution_mode=mode,
                owner='M06', lane='hk_preselection', role=legacy.ROLE,
                source_capsule_sha256=legacy.DESCRIPTOR_SHA256, model_weights_reverified=False, **legacy.SAFETY)


def _identity(request, producer, inventory, code, config, dependencies, assets=None):
    inputs = dict(schema_version='v5.hk_preselection_input_manifest.v1',
                  request=request, files=inventory, producer_assets=assets or {}, producer_receipt_sha256=sha256_json(producer),
                  execution_mode=config['execution_mode'])
    identity = dict(lane='hk_preselection', target_date=request['target_date'],
                    input_sha256=sha256_json(inputs), research_cutoff=request['research_cutoff'],
                    code_sha256=sha256_json(code), config_sha256=sha256_json(config),
                    dependency_sha256=sha256_json(dependencies))
    return inputs, identity


def _semantic_result(result):
    return {key: value for key, value in result.items() if key != 'finished_at'}


def _full_row_match(request, artifact):
    # Compare the complete original CSV values as well as all projector fields.
    source = _relative(Path(request['input_root']), request['expected_source']['artifact_relative'])
    with source.open('r', encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    projected = artifact['rows']
    replaced = {'recommendation_status', 'production_allowed', 'buy_gate_updated', 'orders_sent',
                'symbol', 'market', 'pool_id', 'pool_rank', 'stock_name', 'pool_score'}
    if len(rows) != 100 or len(projected) != 100:
        raise ValueError('M06_ROWS_DIVERGED')
    for index, (raw, row) in enumerate(zip(rows, projected), 1):
        if any(row.get(key) != value for key, value in raw.items() if key not in replaced):
            raise ValueError('M06_ROWS_DIVERGED:original-fields')
        code = str(raw.get('code_norm') or raw.get('code') or '').strip().upper().removeprefix('HK.')
        expected = {'symbol': 'HK.' + code, 'market': 'HK', 'pool_id': 'hkconnect_d1_top100',
                    'pool_rank': index, 'stock_name': raw.get('name') or 'HK.' + code,
                    'pool_score': float(raw['score_prob_active']), 'recommendation_status': 'WATCH_ONLY',
                    'production_allowed': False, 'buy_gate_updated': False, 'orders_sent': False}
        if any(row.get(key) != value for key, value in expected.items()):
            raise ValueError('M06_ROWS_DIVERGED:projection')


def _read_candidate(root, obj, expected_manifest_sha):
    manifest_path = obj / 'manifest.json'
    raw = _read(manifest_path, limit=MAX_JSON_BYTES)
    if _digest(raw) != expected_manifest_sha:
        raise ValueError('M06_PUBLICATION_MANIFEST_MISMATCH')
    manifest = _json(manifest_path)
    if manifest.get('schema_version') != 'v5.hk_preselection_publication_manifest.v1':
        raise ValueError('M06_PUBLICATION_MANIFEST_MISMATCH')
    files = manifest.get('files')
    if not isinstance(files, dict):
        raise ValueError('M06_PUBLICATION_MANIFEST_MISMATCH')
    for relative, digest in files.items():
        if _digest(_read(_relative(obj, relative))) != sha(digest):
            raise ValueError('M06_INPUT_CHANGED:' + relative)
    request = _json(obj / 'request.json')
    if request.get('input_root') != str(obj / 'source'):
        raise ValueError('M06_SOURCE_REF_MISMATCH:root')
    expected = _source_reference(request['expected_source'])
    producer = _producer(_json(obj / 'producer_receipt.json'), expected)
    asset_files = (producer.get('asset_snapshot') or {}).get('files', {})
    if set(files) != set(DOCUMENTS) | {'source/' + key for key in request['files']} | {'producer_assets/' + key for key in asset_files}:
        raise ValueError('M06_PUBLICATION_MANIFEST_MISMATCH:closure')
    inputs = _json(obj / 'input_manifest.json')
    original = inputs.get('request')
    if not isinstance(original, dict) or {k:v for k,v in request.items() if k != 'input_root'} != {k:v for k,v in original.items() if k != 'input_root'}:
        raise ValueError('M06_SOURCE_REF_MISMATCH:request')
    inventory = _inventory(obj / 'source', request['files'])
    code = _json(obj / 'code_manifest.json')
    dependencies = _json(obj / 'dependency_manifest.json')
    config = _json(obj / 'config_manifest.json')
    if code != _code_manifest() or dependencies != _dependencies() or config != _config(config.get('execution_mode')):
        raise ValueError('M06_IMPLEMENTATION_CHANGED')
    if config['execution_mode'] not in MODES:
        raise ValueError('M06_EXECUTION_MODE_INVALID')
    assets = _producer_assets(producer, original, config['execution_mode'], source_root=obj / 'source', asset_root=obj / 'producer_assets')
    expected_inputs, identity = _identity(original, producer, inventory, code, config, dependencies, assets)
    if inputs != expected_inputs or manifest.get('computation_identity') != identity or obj.name != sha256_json(identity):
        raise ValueError('M06_PUBLICATION_IDENTITY_MISMATCH')
    result = _validate_result(verified.run_verified_hk_preselection(request), request, expected)
    stored = _json(obj / 'strict_reader_receipt.json')
    if stored.get('schema_version') != 'v5.hk_preselection_strict_reader_receipt.v1':
        raise ValueError('M06_STRICT_READBACK_FAILED:receipt')
    if _semantic_result(result) != _semantic_result(stored.get('result', {})):
        raise ValueError('M06_STRICT_READBACK_FAILED:receipt-result')
    if result['artifact'] != _json(obj / 'artifact.json'):
        raise ValueError('M06_ROWS_DIVERGED:saved-artifact')
    _full_row_match(request, result['artifact'])
    if _inventory(obj / 'source', request['files']) != inventory:
        raise ValueError('M06_INPUT_CHANGED')
    for relative, digest in files.items():
        if _digest(_read(_relative(obj, relative))) != digest:
            raise ValueError('M06_INPUT_CHANGED:' + relative)
    if _digest(_read(manifest_path)) != expected_manifest_sha:
        raise ValueError('M06_INPUT_CHANGED:manifest')
    if _code_manifest() != code or _dependencies() != dependencies:
        raise ValueError('M06_IMPLEMENTATION_CHANGED')
    return result, manifest, producer, original, config


def _reference(root, obj, result, manifest, producer, original, config, receipt):
    identity = manifest['computation_identity']
    relative = obj.relative_to(root).as_posix()
    return dict(schema_version=REFERENCE_SCHEMA, owner='M06', market='HK', status='COMMITTED',
                business_status=result['artifact']['status'], data_kind='VERIFIED_SOURCE_SNAPSHOT',
                target_date=original['target_date'], signal_date=original['signal_date'],
                eligibility_source_date=original['eligibility_source_date'], research_cutoff=original['research_cutoff'],
                execution_mode=config['execution_mode'], computation_identity=identity,
                producer_computation_identity=producer.get('computation_identity'),
                fixture_only=result.get('fixture_only') is True,
                computation_sha256=sha256_json(identity), request_sha256=sha256_json(original),
                artifact_relative=relative + '/artifact.json', artifact_sha256=manifest['files']['artifact.json'],
                manifest_relative=relative + '/manifest.json', manifest_sha256=_digest(_read(obj / 'manifest.json')),
                receipt_relative=relative + '/receipt.json', receipt_sha256=_digest(_read(obj / 'receipt.json')),
                producer_reference={'relative': relative + '/producer_receipt.json',
                                    'sha256': manifest['files']['producer_receipt.json'],
                                    'production_method': producer['production_method']},
                reader_reference={'relative': relative + '/strict_reader_receipt.json',
                                  'sha256': manifest['files']['strict_reader_receipt.json']},
                verified_source_reference=result['verified_source_reference'],
                model_weights_reverified=False, **legacy.SAFETY)


def read_verified_hk_preselection_reference(bound_root, reference):
    """Read exactly the committed object; no latest/date/source fallback exists."""
    root = shadow_root(Path(bound_root))
    reference = _clone(reference)
    if (not isinstance(reference, dict) or reference.get('schema_version') != REFERENCE_SCHEMA
            or reference.get('owner') != 'M06' or reference.get('market') != 'HK'):
        raise ValueError('M06_COMMITTED_REFERENCE_INVALID')
    target = trade_date(reference.get('target_date'))
    computation = sha(reference.get('computation_sha256'))
    obj = _relative(root, 'hk_preselection/' + target + '/objects/' + computation)
    slot = _relative(root, 'hk_preselection/' + target + '/committed.json')
    if _json(slot) != reference:
        raise ValueError('M06_COMMITTED_REFERENCE_MISMATCH')
    if _json(obj / 'reference.json') != reference:
        raise ValueError('M06_COMMITTED_REFERENCE_MISMATCH:object')
    result, manifest, producer, original, config = _read_candidate(root, obj, reference.get('manifest_sha256'))
    receipt = _json(obj / 'receipt.json')
    if (receipt.get('schema_version') != 'v5.hk_preselection_publication_receipt.v1'
            or receipt.get('status') != 'PREPARED_VERIFIED' or receipt.get('cold_readback_verified') is not True
            or receipt.get('computation_identity') != manifest['computation_identity']
            or receipt.get('manifest_sha256') != reference['manifest_sha256']
            or receipt.get('strict_result_sha256') != sha256_json(_semantic_result(result))):
        raise ValueError('M06_PUBLICATION_RECEIPT_MISMATCH')
    actual = _reference(root, obj, result, manifest, producer, original, config, receipt)
    if reference != actual:
        raise ValueError('M06_COMMITTED_REFERENCE_MISMATCH:readback')
    # Both files must still contain the exact expected commit after cold reading.
    if _json(slot) != reference or _json(obj / 'reference.json') != reference:
        raise ValueError('M06_COMMITTED_REFERENCE_MISMATCH:changed')
    return dict(result, committed_reference=reference)


def publish_verified_hk_preselection(request, *, bound_root, producer_receipt, execution_mode='MANUAL_RECOVERY'):
    """Snapshot and publish a verified existing pool, without executing a model.

    A pre-existing incomplete object, final file, or final directory is never
    replaced. A same-input success is re-read from disk before it is reused.
    """
    root = shadow_root(Path(bound_root))
    request = _clone(request)
    producer = _clone(producer_receipt)
    if execution_mode not in MODES:
        raise ValueError('M06_EXECUTION_MODE_INVALID')
    source = no_symlinks(Path(request['input_root']))
    if root.is_relative_to(source) or source.is_relative_to(root):
        raise ValueError('SOURCE_OUTPUT_OVERLAP')
    expected = _source_reference(request['expected_source'])
    _producer(producer, expected)
    original_result = _validate_result(verified.run_verified_hk_preselection(request), request, expected)
    _full_row_match(request, original_result['artifact'])
    inventory = _inventory(source, request['files'])
    code, dependencies, config = _code_manifest(), _dependencies(), _config(execution_mode)
    asset_snapshot = producer.get('asset_snapshot')
    asset_root = no_symlinks(Path(asset_snapshot['input_root'])) if asset_snapshot is not None else None
    if asset_root is not None and (root.is_relative_to(asset_root) or asset_root.is_relative_to(root)):
        raise ValueError('SOURCE_OUTPUT_OVERLAP')
    assets = _producer_assets(producer, request, execution_mode)
    inputs, identity = _identity(request, producer, inventory, code, config, dependencies, assets)
    computation = sha256_json(identity)
    with _lock(root):
        slot_dir = root / 'hk_preselection' / trade_date(request['target_date'])
        _parents(slot_dir / 'objects', root)
        slot = no_symlinks(slot_dir / 'committed.json')
        if slot.exists():
            try:
                existing = _json(slot)
            except ValueError as error:
                raise ValueError('M06_COMMIT_CONFLICT:invalid-existing-final') from error
            if existing.get('computation_identity') != identity:
                raise ValueError('M06_COMMIT_CONFLICT:different-input')
            read_verified_hk_preselection_reference(root, existing)
            if _inventory(source, request['files']) != inventory:
                raise ValueError('M06_INPUT_CHANGED')
            return existing
        obj = no_symlinks(slot_dir / 'objects' / computation)
        try:
            obj.mkdir(mode=0o700)
        except FileExistsError as error:
            raise ValueError('M06_COMMIT_CONFLICT:incomplete-object-outcome-unknown') from error
        _fsync_dir(obj.parent)
        _mkdir(obj / 'source')
        for relative, digest in request['files'].items():
            data = _read(_relative(source, relative))
            if _digest(data) != digest:
                raise ValueError('M06_INPUT_CHANGED:' + relative)
            destination = _relative(obj / 'source', relative)
            _parents(destination.parent, obj / 'source')
            _write_new(destination, data)
        if asset_snapshot is not None:
            _mkdir(obj / 'producer_assets')
            for relative, digest in asset_snapshot['files'].items():
                data = _read(_relative(asset_root, relative))
                if _digest(data) != digest:
                    raise ValueError('M06_INPUT_CHANGED:producer-assets:' + relative)
                destination = _relative(obj / 'producer_assets', relative)
                _parents(destination.parent, obj / 'producer_assets')
                _write_new(destination, data)
        snapshot_request = dict(request, input_root=str(obj / 'source'))
        result = _validate_result(verified.run_verified_hk_preselection(snapshot_request), snapshot_request, expected)
        if result['artifact'] != original_result['artifact'] or result['verified_source_reference'] != original_result['verified_source_reference']:
            raise ValueError('M06_ROWS_DIVERGED:source-copy')
        _full_row_match(snapshot_request, result['artifact'])
        values = {'request.json': snapshot_request, 'input_manifest.json': inputs,
                  'code_manifest.json': code, 'config_manifest.json': config,
                  'dependency_manifest.json': dependencies, 'producer_receipt.json': producer,
                  'strict_reader_receipt.json': {'schema_version': 'v5.hk_preselection_strict_reader_receipt.v1', 'result': result},
                  'artifact.json': result['artifact']}
        # Producer provenance and all inventories exist before cold readback.
        for name in ('producer_receipt.json', 'input_manifest.json', 'code_manifest.json', 'config_manifest.json',
                     'dependency_manifest.json', 'request.json', 'artifact.json', 'strict_reader_receipt.json'):
            _write_json(obj / name, values[name])
        files = {name: _digest(_read(obj / name)) for name in DOCUMENTS}
        files.update({'source/' + name: digest for name, digest in request['files'].items()})
        if asset_snapshot is not None:
            files.update({'producer_assets/' + name: digest for name, digest in asset_snapshot['files'].items()})
        manifest = dict(schema_version='v5.hk_preselection_publication_manifest.v1', computation_identity=identity, files=files)
        _write_json(obj / 'manifest.json', manifest)
        manifest_sha = sha256_json(manifest)
        cold, _, _, _, _ = _read_candidate(root, obj, manifest_sha)
        if (asset_root is not None and _inventory(asset_root, asset_snapshot['files'], minimum=0) != assets):
            raise ValueError('M06_INPUT_CHANGED:producer-assets-precommit')
        if _inventory(source, request['files']) != inventory or _code_manifest() != code or _dependencies() != dependencies:
            raise ValueError('M06_INPUT_CHANGED:precommit')
        receipt = dict(schema_version='v5.hk_preselection_publication_receipt.v1', status='PREPARED_VERIFIED',
                       cold_readback_verified=True, computation_identity=identity, manifest_sha256=manifest_sha,
                       strict_result_sha256=sha256_json(_semantic_result(cold)), model_weights_reverified=False, **legacy.SAFETY)
        _write_json(obj / 'receipt.json', receipt)
        reference = _reference(root, obj, cold, manifest, producer, request, config, receipt)
        _write_json(obj / 'reference.json', reference)
        shadow_root(root)
        no_symlinks(slot)
        # link() is kernel no-clobber. Unlike rename/replace, it cannot replace
        # any pre-existing final file or empty directory, even in a race.
        try:
            os.link(obj / 'reference.json', slot, follow_symlinks=False)
        except FileExistsError as error:
            raise ValueError('M06_COMMIT_CONFLICT:final-exists') from error
        _fsync_dir(slot_dir)
        read_verified_hk_preselection_reference(root, reference)
        return reference


def project_hk_preselection_record(bound_root, reference, *, config, path, query):
    """Project one exact committed reference for an already-configured API route.

    The caller supplies the existing module/release/route contract. This helper
    writes nothing and neither publishes nor activates any API generation.
    """
    from .module_api import _validate_record
    result = read_verified_hk_preselection_reference(bound_root, reference)
    config, query = _clone(config), _clone(query)
    payload = dict(artifact=result['artifact'], committed_reference=result['committed_reference'],
                   model_weights_reverified=False, fixture_only=result.get('fixture_only') is True,
                   **legacy.SAFETY)
    root = shadow_root(Path(bound_root))
    raw = _read(_relative(root, reference['reader_reference']['relative']), limit=MAX_JSON_BYTES)
    if _digest(raw) != reference['reader_reference']['sha256']:
        raise ValueError('M06_INPUT_CHANGED:projection-reader-receipt')
    reader_receipt = json.loads(raw)
    record = dict(schema_version='v5.module_response.v1', module_id=config['module_id'],
                  release_id=config['release_id'], path=path, query=query, payload=payload,
                  payload_sha256=sha256_json(payload), source_input_sha256=reference['computation_identity']['input_sha256'],
                  data_kind='SYNTHETIC' if result.get('fixture_only') is True else 'OWNER_RESULT',
                  generated_at=reader_receipt['result']['finished_at'], status_code=200)
    canonical_bytes(record)
    return _validate_record(config, record, path, query)

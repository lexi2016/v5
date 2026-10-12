"""SOURCE_SNAPSHOT cold consumer of the unchanged frozen HK Top100 chain."""
import sys
from pathlib import Path
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hashlib
import importlib
import io
import json
import os
import subprocess
import tempfile
from contextlib import redirect_stdout
from datetime import datetime, timezone, timedelta
from v5_shadow import hk_preselection as legacy
from v5_shadow import a_preselection as common
from v5_shadow.composition import no_symlinks
from v5_shadow.contracts import aware, sha, trade_date
from v5_shadow.digests import canonical_bytes, sha256_json, MAX_JSON_BYTES

SCHEMA = 'v5.hk_preselection_verified_request.v1'
RESULT_SCHEMA = 'v5.hk_preselection_verified_assembly.v1'
ROLE = legacy.ROLE
SAFETY = legacy.SAFETY
PRODUCTION_DESCRIPTOR = legacy.BASE / 'contracts/hk_preselection_production_sources.json'
PRODUCTION_DESCRIPTOR_SHA256 = 'a444e1f3a17c91033ab8838a3798f038a11bd5adca28a7628158c35077f0b264'
SOURCE_KEYS = ('role', 'run_id', 'artifact_sha256', 'manifest_sha256', 'receipt_sha256', 'artifact_relative')
ARTIFACT_KEYS = dict(run_id='source_run_id', artifact_sha256='source_sha256',
    manifest_sha256='source_manifest_sha256', receipt_sha256='source_receipt_sha256', artifact_relative='source_path')


def _identity():
    return dict(legacy._identity(), hk_preselection_verified=hashlib.sha256(
        no_symlinks(Path(__file__)).read_bytes()).hexdigest(), production_descriptor=PRODUCTION_DESCRIPTOR_SHA256)


def _production_sources():
    descriptor = legacy._json(PRODUCTION_DESCRIPTOR)
    if sha256_json(descriptor) != PRODUCTION_DESCRIPTOR_SHA256:
        raise ValueError('M06_PRODUCTION_DESCRIPTOR_MISMATCH')
    root = legacy.BASE.parent
    for entry in descriptor['entries']:
        data = common._relative(root, entry['relative_path']).read_bytes()
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('M06_PRODUCTION_SOURCE_BYTES_MISMATCH')
    legacy._source_bytes()
    return descriptor


def _validate_source_ref(value):
    if not isinstance(value, dict) or set(value) != set(SOURCE_KEYS):
        raise ValueError('M06_SOURCE_REF_FIELDS_INVALID')
    for key in SOURCE_KEYS:
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValueError('M06_SOURCE_REF_MISSING:' + key)
    if value['role'] != ROLE:
        raise ValueError('M06_SOURCE_ROLE_INVALID')
    for key in ('artifact_sha256', 'manifest_sha256', 'receipt_sha256'):
        sha(value[key])
    path = Path(value['artifact_relative'])
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('M06_PATH_ESCAPE')
    if '/' in value['run_id'] or '\\' in value['run_id'] or value['run_id'] in ('.', '..'):
        raise ValueError('M06_SOURCE_RUN_ID_INVALID')
    return value


def _lane(request):
    return dict(kind='v192', input_root=request['input_root'], paths={}, files=request['files'])


def _snapshot_layout(request):
    """Resolve original metadata paths only through the declared byte whitelist."""
    root = no_symlinks(request['input_root']); files = request['files']
    def metadata(relative):
        if relative not in files:raise ValueError('M06_REQUIRED_FILE_MISSING:' + relative)
        return legacy._json(common._relative(root, relative))
    latest = metadata('latest.json')
    try:
        entry = latest['entries'][request['target_date'] + '/' + ROLE]
        pool_paths = [entry[k] for k in ('artifact_relative', 'manifest_relative', 'receipt_relative')]
        master_prefix = 'assets/hk_security_master/'
        master_latest = metadata(master_prefix + 'latest.json')
        master_entry = master_latest['entries'][request['eligibility_source_date']]
        master_manifest = metadata(master_prefix + master_entry['manifest_relative'])
        paths = ['latest.json', *pool_paths, master_prefix + 'latest.json',
            master_prefix + master_manifest['artifact_relative'], master_prefix + master_entry['manifest_relative'],
            master_prefix + master_entry['receipt_relative']]
        if len(set(paths)) != 8:raise ValueError('M06_REQUIRED_FILE_SET_INVALID')
        for relative in paths:
            common._relative(root, relative)
            if relative not in files:raise ValueError('M06_REQUIRED_FILE_MISSING:' + relative)
        manifest = metadata(pool_paths[1]); receipt = metadata(pool_paths[2])
    except (KeyError, TypeError) as error:
        raise ValueError('M06_REQUIRED_FILE_LAYOUT_INVALID:' + str(error)) from error
    actual = dict(role=receipt.get('role'), run_id=entry.get('run_id'), artifact_relative=entry.get('artifact_relative'),
        artifact_sha256=common._file_sha(common._relative(root, pool_paths[0])),
        manifest_sha256=sha256_json(manifest), receipt_sha256=common._file_sha(common._relative(root, pool_paths[2])))
    _validate_source_ref(actual)
    if actual != request['expected_source']:
        raise ValueError('M06_SOURCE_REF_MISMATCH')
    return paths


def _validate_request(request):
    required = {'schema_version', 'target_date', 'signal_date', 'eligibility_source_date', 'research_cutoff',
        'data_kind', 'input_root', 'files', 'expected_source'}
    if isinstance(request, dict) and (request.get('eligibility_universe_root') is not None or request.get('research_name_supplement', False) is not False):
        raise ValueError('UNSUPPORTED_LEGACY_READER_ARGUMENT')
    if not isinstance(request, dict) or set(request) != required:
        raise ValueError('M06_REQUEST_FIELDS_INVALID')
    if request['schema_version'] != SCHEMA or request['data_kind'] != 'SOURCE_SNAPSHOT':
        raise ValueError('M06_SOURCE_KIND_INVALID')
    _validate_source_ref(request['expected_source'])
    target = trade_date(request['target_date']); signal = trade_date(request['signal_date'])
    eligibility = trade_date(request['eligibility_source_date']); cutoff = aware(request['research_cutoff'])
    if not signal < target or eligibility > target:raise ValueError('HK_THREE_DATES_INVALID')
    if cutoff.astimezone(timezone(timedelta(hours=8))).strftime('%Y%m%d') != target:
        raise ValueError('HK_CUTOFF_DATE_MISMATCH')
    root = no_symlinks(request['input_root'])
    for code_root in (legacy.BASE, Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(), Path(os.__file__).resolve().parent):
        if root.is_relative_to(code_root) or code_root.is_relative_to(root):raise ValueError('INPUT_CODE_ROOT_OVERLAP')
    files = request['files']
    if not isinstance(files, dict) or not 8 <= len(files) <= 2000:raise ValueError('M06_REQUIRED_FILE_MISSING')
    for relative, digest in files.items():
        common._relative(root, relative); sha(digest)
    common._verify_lane(_lane(request))
    _snapshot_layout(request)
    canonical_bytes(request)
    return request


def _verify_chain(pool, artifact, request):
    verification = pool.run.verification
    actual = dict(role=pool.run.receipt['role'], **{k:verification[k] for k in SOURCE_KEYS if k != 'role'})
    _validate_source_ref(actual)
    if actual != request['expected_source']:raise common.InputEvidenceError('M06_SOURCE_REF_MISMATCH')
    if verification.get('status') != 'READY' or verification.get('row_count') != 100:
        raise common.InputEvidenceError('M06_IDENTITY_CHAIN_MISMATCH')
    for source_key, artifact_key in ARTIFACT_KEYS.items():
        if artifact.get(artifact_key) != actual[source_key]:raise common.InputEvidenceError('M06_IDENTITY_CHAIN_MISMATCH')
    rows = artifact.get('rows')
    if not isinstance(rows, list) or len(rows) != 100:raise common.InputEvidenceError('M06_ROWS_DIVERGED')
    replaced = {'symbol','market','pool_id','pool_rank','stock_name','pool_score',
        'recommendation_status','production_allowed','buy_gate_updated','orders_sent'}
    for index, (raw, row) in enumerate(zip(pool.rows, rows), 1):
        if any(row.get(k) != v for k, v in raw.items() if k not in replaced):
            raise common.InputEvidenceError('M06_ROWS_DIVERGED')
        code = str(raw.get('code_norm') or raw.get('code') or '').strip().upper().removeprefix('HK.')
        projection = dict(symbol='HK.'+code,market='HK',pool_id='hkconnect_d1_top100',pool_rank=index,
            stock_name=str(raw.get('name') or 'HK.'+code),pool_score=float(raw['score_prob_active']),
            recommendation_status='WATCH_ONLY',production_allowed=False,buy_gate_updated=False,orders_sent=False)
        if any(row.get(k) != v for k,v in projection.items()):
            raise common.InputEvidenceError('M06_ROWS_DIVERGED')
    return actual


def _assemble_verified(request):
    request = _validate_request(request); _production_sources()
    sources = legacy._source_bytes(); finder = legacy._HKLoader(sources)
    if any(name in sys.modules for name in ('domains', 'infrastructure', 'contracts', 'upstreams')):
        raise ValueError('HK_WORKER_REQUIRES_FRESH_PROCESS')
    sys.meta_path.insert(0, finder)
    calendars = importlib.import_module('contracts.trading_calendar'); calendar = calendars.load_market_calendar()
    states = calendars.resolve_market_states(calendar, request['target_date'])
    if states['hk_securities'].value not in ('FULL_TRADING_DAY', 'HALF_TRADING_DAY_AM'):
        raise ValueError('HK_TARGET_NOT_SECURITIES_SESSION')
    if calendars.previous_session(calendar, request['target_date'], market='hk_securities') != request['signal_date']:
        raise ValueError('HK_SIGNAL_NOT_PREVIOUS_SECURITIES_SESSION')
    module = importlib.import_module('domains.preselection_materializer')
    reader_module = importlib.import_module('upstreams.v3_shared_data.shared_data.hk_0_2')
    master_module = importlib.import_module('upstreams.v3_shared_data.shared_data.hk_security_master')
    validator = importlib.import_module('infrastructure.preselection_pool_store').validate_pool_artifact
    lane = _lane(request); select = common._guard([lane]); select(lane); root = no_symlinks(request['input_root'])
    base = dict(schema_version=RESULT_SCHEMA, **{k:request[k] for k in ('target_date','signal_date','eligibility_source_date','research_cutoff','data_kind')},
        market_states={k:v.value for k,v in states.items()}, request_sha256=sha256_json(request),
        source_capsule_sha256=legacy.DESCRIPTOR_SHA256, production_descriptor_sha256=PRODUCTION_DESCRIPTOR_SHA256,
        implementation_identity=_identity(), model_weights_reverified=False, input_binding_status='DECLARED_BYTES_CHECKED',
        isolation_status='PYTHON_GUARDS_ONLY_OS_UNVERIFIED', **SAFETY)
    checked = []; master_fixture = []
    try:
        common._verify_lane(lane)
        def checked_reader(source_root, *, target_date, expected_signal_date, expected_eligibility_source_date=None):
            if (no_symlinks(source_root) != root or target_date != request['target_date']
                or expected_signal_date != request['signal_date']
                or (expected_eligibility_source_date or expected_signal_date) != request['eligibility_source_date']):
                raise common.InputEvidenceError('HK_READER_ARGUMENT_BINDING_MISMATCH')
            pool = reader_module.read_verified_hk_0_2_pool(source_root, target_date=target_date,
                expected_signal_date=expected_signal_date, expected_eligibility_source_date=request['eligibility_source_date'])
            master, master_manifest = master_module.load_verified_hk_security_master(source_root, request['eligibility_source_date'])
            legacy._verify_pool(pool, master, master_manifest, request, root)
            checked.append(pool)
            master_fixture.append(master_manifest.get("fixture_only") is True or any(
                row.get("source") == "SYNTHETIC_FIXTURE" for row in master.values()))
            return pool
        with redirect_stdout(io.StringIO()):
            artifact = module.build_shared_hk_0_2_pool(root, trade_date=request['target_date'], signal_date=request['signal_date'],
                eligibility_source_date=request['eligibility_source_date'], reader=checked_reader)
        validator(artifact); canonical_bytes(artifact)
        if artifact.get('market') != 'HK' or artifact.get('trade_date') != request['target_date'] or len(checked) != 1:
            raise common.InputEvidenceError('HK_OUTPUT_IDENTITY_MISMATCH')
        actual = _verify_chain(checked[0], artifact, request)
        common._verify_lane(lane); legacy._source_bytes(); _production_sources()
        base['data_kind'] = 'VERIFIED_SOURCE_SNAPSHOT'
        return dict(base, status='ASSEMBLED', artifact=artifact, verified_source_reference=actual,
            source_verification=dict(checked[0].run.verification),
            fixture_only=any(master_fixture) or checked[0].run.manifest.get('fixture_only') is True or checked[0].run.receipt.get('owner') == 'SYNTHETIC_FIXTURE',
            reason='', finished_at=datetime.now(timezone.utc).isoformat())
    except Exception as error:
        if not (common._expected(error) or type(error) is ValueError and str(error).startswith('shared HK 0.2 ')):raise
        return dict(base, status='CANNOT_CONFIRM', artifact=None, verified_source_reference=None, source_verification=None, fixture_only=False,
            reason=type(error).__name__ + ':' + str(error), finished_at=datetime.now(timezone.utc).isoformat())


def run_verified_hk_preselection(request):
    request = json.loads(canonical_bytes(request)); _validate_request(request); _production_sources(); identity = _identity()
    with tempfile.TemporaryDirectory(prefix='v5-hk-verified-cache-') as cache:
        process = subprocess.run([sys.executable, '-I', '-B', '-X', 'pycache_prefix=' + str(Path(cache).resolve()),
            str(Path(__file__).resolve()), '--worker'], input=canonical_bytes(request), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=120)
    if len(process.stdout) > MAX_JSON_BYTES:raise ValueError('HK_WORKER_OUTPUT_TOO_LARGE')
    try:result = json.loads(process.stdout)
    except (ValueError, UnicodeError) as error:
        raise ValueError('HK_WORKER_RESPONSE_INVALID:' + process.stderr.decode(errors='replace')[-2000:]) from error
    if process.returncode != 0:raise ValueError(result.get('reason', 'HK_WORKER_FAILED'))
    if (result.get('schema_version') != RESULT_SCHEMA or result.get('request_sha256') != sha256_json(request)
        or result.get('source_capsule_sha256') != legacy.DESCRIPTOR_SHA256
        or result.get('production_descriptor_sha256') != PRODUCTION_DESCRIPTOR_SHA256
        or result.get('implementation_identity') != identity or _identity() != identity
        or any(result.get(k) != request[k] for k in ('target_date','signal_date','eligibility_source_date','research_cutoff'))
        or result.get('status') not in ('ASSEMBLED','CANNOT_CONFIRM')
        or any(result.get(k) != v for k,v in SAFETY.items()) or result.get('model_weights_reverified') is not False):
        raise ValueError('HK_WORKER_CONTRACT_MISMATCH')
    if result['status'] == 'ASSEMBLED':
        if result.get('data_kind') != 'VERIFIED_SOURCE_SNAPSHOT' or result.get('verified_source_reference') != request['expected_source']:
            raise ValueError('M06_IDENTITY_CHAIN_MISMATCH')
        source_verification = result.get('source_verification')
        if (not isinstance(source_verification,dict) or source_verification.get('status')!='READY'
            or source_verification.get('row_count')!=100
            or any(source_verification.get(k)!=request['expected_source'][k] for k in SOURCE_KEYS if k!='role')):
            raise ValueError('M06_IDENTITY_CHAIN_MISMATCH')
        artifact = result.get('artifact')
        if not isinstance(artifact,dict) or len(artifact.get('rows',[])) != 100:
            raise ValueError('M06_ROWS_DIVERGED')
        for key, dest in ARTIFACT_KEYS.items():
            if artifact.get(dest) != request['expected_source'][key]:raise ValueError('M06_IDENTITY_CHAIN_MISMATCH')
    elif result.get('data_kind') != 'SOURCE_SNAPSHOT' or result.get('artifact') is not None or result.get('verified_source_reference') is not None or result.get('source_verification') is not None:
        raise ValueError('HK_WORKER_CONTRACT_MISMATCH')
    common._verify_lane(_lane(request)); _production_sources()
    return result


if __name__ == '__main__':
    try:
        if sys.argv[1:] != ['--worker']:raise ValueError('M06_WORKER_MODE_REQUIRED')
        raw = sys.stdin.buffer.read(MAX_JSON_BYTES+1)
        if len(raw) > MAX_JSON_BYTES:raise ValueError('REQUEST_TOO_LARGE')
        print(canonical_bytes(_assemble_verified(json.loads(raw))).decode())
    except Exception as error:
        print(canonical_bytes(dict(status='FAILED', reason=type(error).__name__ + ':' + str(error))).decode())
        raise SystemExit(1)

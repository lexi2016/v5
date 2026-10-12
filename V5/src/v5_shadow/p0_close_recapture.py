"""M17 contract bridge for the existing P0 tick/dispatch; no scheduler or ledger."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
from . import daily_close_recapture_owner as owner
from .contracts import aware, exact_keys, trade_date, sha
from .digests import sha256_json
from .daily_close_plan import _market_states

LANE = owner.LANE
TZ = timezone(timedelta(hours=8))
IDENTITIES = ('code_sha256', 'config_sha256', 'dependency_sha256')
POOL_KEYS = ('owner','role','trade_date','signal_date','source_id','run_id',
             'artifact_ref','artifact_sha256','manifest_ref','manifest_sha256',
             'receipt_ref','receipt_sha256','captured_at','row_count')


def verify_pool(config, pool):
    """Pin the explicit external D1 reference; original owner validates its schema."""
    exact_keys(pool, POOL_KEYS)
    trade_date(pool['trade_date']); trade_date(pool['signal_date']); aware(pool['captured_at'])
    if (pool['owner'] != 'v3_shared_data' or pool['role'] != 'HK_CONNECT_D1_TOP100_0_2'
            or pool['source_id'] != 'hkconnect_0_2_frozen_prob_active' or pool['row_count'] != 100):
        raise ValueError('M17_POOL_REFERENCE_CONTRACT')
    root = Path(config['universe_root']) / '.runtime/data'
    prefix = Path('runs') / pool['trade_date'] / pool['role'] / pool['run_id']
    if not pool['run_id'] or Path(pool['run_id']).name != pool['run_id'] or pool['run_id'] in ('.','..'):
        raise ValueError('M17_POOL_RUN_ID')
    contents={}
    for kind, filename in (('artifact','artifact.csv'), ('manifest','manifest.json'), ('receipt','receipt.json')):
        if pool[kind+'_ref'] != (prefix / filename).as_posix():
            raise ValueError('M17_POOL_REFERENCE_PATH')
        sha(pool[kind+'_sha256'])
        contents[kind]=owner._read_file(root / pool[kind+'_ref'])
        if owner._sha(contents[kind]) != pool[kind+'_sha256']:
            raise ValueError('M17_POOL_REFERENCE_CHANGED')

    manifest=json.loads(contents['manifest']);receipt=json.loads(contents['receipt'])
    if (any(manifest.get(k)!=pool[k] for k in ('trade_date','signal_date','source_id','captured_at','row_count','artifact_sha256'))
            or manifest.get('artifact_relative')!=pool['artifact_ref']
            or any(receipt.get(k)!=pool[k] for k in ('owner','role','trade_date','run_id','artifact_sha256','manifest_sha256'))):
        raise ValueError('M17_POOL_REFERENCE_METADATA_MISMATCH')

def _binding(registration):
    exact_keys(registration, ('enabled','execution_kind','config','pool_reference'))
    if registration['enabled'] is not True or registration['execution_kind'] not in {'SIMULATED','OWNER_VERIFIED'}:
        raise ValueError('M17_EXECUTION_REGISTRATION_REQUIRED')
    config = registration['config']; original = owner.bind_close_recapture_owner(config)
    marker = owner._read_file(Path(config['state_root']) / '.v5-m17-close-root')
    if registration['execution_kind'] == 'SIMULATED':
        if marker != owner.MARKER or 'real_binding' in config:
            raise ValueError('M17_SIMULATED_ROOT_MARKER_REQUIRED')
    else:
        reasons = owner.real_binding_reasons(dict(config=config,research_cutoff=datetime.now(timezone.utc).isoformat()))
        if reasons: raise ValueError(reasons[0])
        if not owner._real_runtime_ready(config['real_binding']):
            raise ValueError('M17_PYTDX_RUNTIME_NOT_BOUND')
    verify_pool(config, registration['pool_reference'])
    # P0 behavior/config and exact pool identity participate without altering the
    # original owner's request schema or its fixed five-field receipt.
    code = {name:owner._sha(owner._read_file(Path(__file__).with_name(name))) for name in
            ('p0_close_recapture.py','daily_dispatch.py','daily_tick.py','main_registry.py','main_runtime.py')}
    return dict(invoke=owner.run_close_recapture_owner,
        code_sha256=sha256_json(dict(owner=original['code_sha256'],p0=code)),
        config_sha256=sha256_json(registration),dependency_sha256=original['dependency_sha256'],
        registration=registration,pool_reference=registration['pool_reference'])


def validate_registration(registration=None):
    if registration is None or registration == {'enabled':False}:
        return dict(status='DISABLED',natural_verified=False)
    try:
        _binding(registration)
        return dict(status='BOUND_NOT_NATURALLY_VERIFIED',natural_verified=False)
    except (ValueError, TypeError, KeyError, OSError) as error:
        # No raw paths or runtime stderr in operational evidence.
        reason = str(error) if isinstance(error,ValueError) and str(error).isidentifier() else 'M17_BINDING_INVALID'
        return dict(status='BLOCKED_M17_REGISTRATION',reason_codes=[reason],natural_verified=False)


def prepare_job(job, registration, today):
    if validate_registration(registration)['status'] != 'BOUND_NOT_NATURALLY_VERIFIED':
        raise ValueError('BLOCKED_M17_REGISTRATION')
    if job['lane'] != LANE or type(job.get('max_attempts')) is not int or job['max_attempts'] != 1:
        raise ValueError('M17_SINGLE_ATTEMPT_REQUIRED')
    if 'scheduled_at' not in job or 'deadline' not in job:
        raise ValueError('M17_EXPLICIT_SLOT_REQUIRED')
    start, end = aware(job['scheduled_at']), aware(job['deadline'])
    if start >= end or start.astimezone(TZ).strftime('%Y%m%d') != today:
        raise ValueError('M17_EXPLICIT_CURRENT_SLOT_REQUIRED')
    request = job['owner_request']
    if request['config'] != registration['config'] or request['execution_kind'] != registration['execution_kind']:
        raise ValueError('M17_REQUEST_BINDING_MISMATCH')
    if request['source_trade_date'] != registration['pool_reference']['trade_date']:
        raise ValueError('M17_EXACT_POOL_SOURCE_DATE_REQUIRED')
    original = owner.bind_close_recapture_owner(request['config'])
    identity = owner.request_identity(request, original)
    binding = _binding(registration)
    identity.update({key:binding[key] for key in IDENTITIES})
    return dict(job, identity=identity), binding


def admission_reason(job, binding, now):
    """Original frozen HK Connect calendar and source date; never morning defaults."""
    request = job['owner_request']; source = request['source_trade_date']
    today = now.astimezone(TZ).strftime('%Y%m%d')
    config = request['config']
    owner._config(config)  # Verify frozen code before executing its calendar parser.
    sources = {name:owner._read_file(Path(config['owner_root'])/'contracts'/name)
               for name in ('trading_calendar.py','market_calendar_2026.json')}
    manifest_raw=owner._read_file(config['source_manifest'])
    if owner._sha(manifest_raw)!=owner.MANIFEST_SHA256:raise ValueError('M17_SOURCE_MANIFEST_MISMATCH')
    pins={entry['path']:entry['sha256'] for entry in json.loads(manifest_raw)['files']}
    if any(owner._sha(raw)!=pins['contracts/'+name] for name,raw in sources.items()):
        raise ValueError('M17_SOURCE_BYTES_MISMATCH')
    if source == today and now.astimezone(TZ).strftime('%H%M%S') < '155505':
        return 'M17_SOURCE_WINDOW_NOT_COMPLETE'
    if source != today:
        cursor = now.astimezone(TZ).date() - timedelta(days=1)
        previous = None
        while cursor.year == now.astimezone(TZ).year:
            token = cursor.strftime('%Y%m%d')
            state = _market_states(sources, token)['hk_connect']
            if state in {'FULL_TRADING_DAY','HALF_TRADING_DAY_AM'}:
                previous = token; break
            if state == 'UNKNOWN': break
            cursor -= timedelta(days=1)
        if source != previous: return 'M17_SOURCE_NOT_CURRENT_OR_PREVIOUS_SESSION'
    if _market_states(sources, source)['hk_connect'] != 'FULL_TRADING_DAY':
        return 'M17_HK_CONNECT_FULL_SESSION_REQUIRED'
    prepared, current = prepare_job(job, binding['registration'], today)
    if prepared['identity'] != job['identity'] or any(current[k] != binding[k] for k in IDENTITIES):
        return 'OWNER_BINDING_IDENTITY_MISMATCH'
    return None


def read_saved(claim, request, binding):
    saved = claim['state']['latest_success']
    try:
        reader = owner._process('reader',request,saved['run_id'])
        if reader['owner_status'] not in {'READY','PARTIAL'}: raise ValueError('M17_SAVED_READER_REJECTED')
        owner._same_product(saved['product_reference'],reader)
        if reader['pool'] != saved['product_reference']['pool'] or reader['pool'] != binding['pool_reference']:
            raise ValueError('M17_SAVED_POOL_CHANGED')
    except Exception:
        return dict(status='BLOCKED_SAVED_PRODUCT_INVALID',state=claim['state'],natural_verified=False)
    return dict(claim,readback_verified=True,natural_verified=False)


def verify_receipt(receipt, binding):
    if receipt['status'] == 'SUCCEEDED' and receipt['product_reference'].get('pool') != binding['pool_reference']:
        raise owner.OutcomeUnknown('M17_BOUND_POOL_READBACK_MISMATCH')

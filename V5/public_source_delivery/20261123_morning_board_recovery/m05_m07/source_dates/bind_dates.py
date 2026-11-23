"""Pure candidate date binding for already-verified M05 producer artifacts."""
from datetime import date
from hashlib import sha256
import json

LANES = {
    'fupan': ('a_d1_fupan_watchlist_pool','v3_fupan_watchlist_contract_v1','VERIFIED_D1_FUPAN_REVIEW','target_date'),
    'stage7': ('a_d1_stage7_fenshi_review_pool','v3_stage7_tail_replay_contract_v1','VERIFIED_D1_STAGE7_REPLAY','target_date'),
    'wechat': ('wechat_public_account_v3_preselect','v3_wechat_preselect_upstream_v1','VERIFIED_WECHAT_RESEARCH','effective_trade_date'),
}

def _day(value):
    if not isinstance(value, str) or len(value) != 8 or not value.isascii() or not value.isdecimal():
        raise ValueError('SOURCE_DATE_MISSING_OR_INVALID')
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:]))
    except ValueError as e:
        raise ValueError('SOURCE_DATE_MISSING_OR_INVALID') from e

def bind_dates(artifact, *, kind, manifest_bytes, rows_bytes, manifest_sha, rows_sha, target, signal):
    """Derive headers from exact inputs; never upgrade status, role or eligibility."""
    if kind not in LANES:
        raise ValueError('SOURCE_LANE_NOT_SUPPORTED')
    pool, producer, role, target_key = LANES[kind]
    if (artifact.get('pool_id'), artifact.get('producer_id'), artifact.get('source_role')) != (pool, producer, role):
        raise ValueError('SOURCE_LANE_IDENTITY_MISMATCH')
    if any(artifact.get(k) is not False for k in ('production_allowed','buy_gate_updated','orders_sent')):
        raise ValueError('SOURCE_SAFETY_MISMATCH')
    if (sha256(manifest_bytes).hexdigest(), sha256(rows_bytes).hexdigest()) != (manifest_sha, rows_sha):
        raise ValueError('SOURCE_BYTES_MISMATCH')
    if artifact.get('source_sha256') != sha256((manifest_sha+rows_sha).encode('ascii')).hexdigest():
        raise ValueError('SOURCE_ARTIFACT_BINDING_MISMATCH')
    manifest = json.loads(manifest_bytes.decode('utf-8-sig'))
    if not isinstance(manifest, dict):
        raise ValueError('SOURCE_MANIFEST_INVALID')
    mt, ms = manifest.get(target_key), manifest.get('signal_date')
    if _day(ms) >= _day(mt) or (mt, ms) != (target, signal) or artifact.get('trade_date') != mt:
        raise ValueError('SOURCE_DATE_MISMATCH')
    for key, value in (('target_date',mt),('signal_date',ms)):
        if key in artifact and artifact[key] != value:
            raise ValueError('SOURCE_ARTIFACT_DATE_CONFLICT')
    return dict(artifact, target_date=mt, signal_date=ms)

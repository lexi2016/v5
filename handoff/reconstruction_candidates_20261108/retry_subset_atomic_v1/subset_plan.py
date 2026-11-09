"""Pure candidate planner; never launches owners or mutates their state/locks.
All byte pins must come from an independently reviewed trusted registry, not
from the evidence document itself. Dispatch requires the new reviewed subset-owner
contract in entrypoint.py; its actual-run registry remains empty.
"""
import datetime as dt
import hashlib
import json
import re
from zoneinfo import ZoneInfo


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def pinned(raw, sha):
    need(type(raw) is bytes and len(raw) <= 16 * 1024**2, 'BOUNDED_BYTES_REQUIRED')
    need(isinstance(sha, str) and re.fullmatch('[0-9a-f]{64}', sha), 'INVALID_PIN')
    need(hashlib.sha256(raw).hexdigest() == sha, 'PIN_MISMATCH')
    return json.loads(raw, object_pairs_hook=no_duplicates,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))


def aware(value):
    # fromisoformat truncates excess fractional digits, including UTC offsets.
    # Reject rather than round evidence across the exact retry cooldown boundary.
    need(isinstance(value, str), 'AWARE_TIME_REQUIRED')
    need(re.search(r'[.,][0-9]{7,}', value) is None, 'UNSUPPORTED_TIME_PRECISION')
    # CPython loses a nonzero fractional offset when its integer part is zero.
    # Refuse this unfaithful form instead of rounding it across a time gate.
    offset = re.search(r'[+-](0{2}(?::?0{2}){0,2})[.,]([0-9]{1,6})$', value)
    need(offset is None or int(offset.group(2)) == 0,
         'UNSUPPORTED_ZERO_FRACTIONAL_OFFSET')
    result = dt.datetime.fromisoformat(value)
    need(result.tzinfo is not None and result.utcoffset() is not None, 'AWARE_TIME_REQUIRED')
    return result


def plan(binding, review_bytes, review_sha, output_bytes, node, now):
    """binding is the trusted registry identity, including full original contract.
    output_bytes maps successful content SHA to bytes read by the caller; this
    routine verifies them but never promotes planner output to live approval.
    """
    # Detach the report/intent from mutable caller-owned identity objects.
    binding = json.loads(canonical(binding), object_pairs_hook=no_duplicates)
    need(node in ('retry-1610', 'retry-1640'), 'RETRY_NODE_REQUIRED')
    need(isinstance(now, dt.datetime) and now.tzinfo is not None and now.utcoffset() is not None,
         'AWARE_TIME_REQUIRED')
    required = {'run_id', 'data_date', 'input_version', 'code_version', 'original_binding', 'symbols'}
    need(isinstance(binding, dict) and set(binding) == required, 'TRUSTED_BINDING_SCHEMA')
    need(all(isinstance(binding[k], str) and binding[k] for k in
             ('run_id', 'data_date', 'input_version', 'code_version')), 'IDENTITY_REQUIRED')
    date = dt.datetime.strptime(binding['data_date'], '%Y%m%d').date()
    need(date.strftime('%Y%m%d') == binding['data_date'], 'DATE_FORMAT')
    original = binding['original_binding']
    need(isinstance(original, dict) and set(original) ==
         {'contract_ref','identity','date','node','input_refs','code_refs','argv','resources','locks'},
         'ORIGINAL_BINDING_REQUIRED')
    need(original['date'] == binding['data_date'] and original['node'] == 'owner', 'ORIGINAL_IDENTITY')
    need(all(original[k] for k in original), 'ORIGINAL_BINDING_INCOMPLETE')
    symbols = binding['symbols']
    need(isinstance(symbols, list) and symbols and all(isinstance(s,str) and
         re.fullmatch(r'[0-9]{6}\.(SH|SZ|BJ)',s) for s in symbols), 'CANONICAL_SYMBOLS_REQUIRED')
    need(len(symbols) == len(set(symbols)), 'DUPLICATE_SCOPE')
    e = pinned(review_bytes, review_sha)
    need(isinstance(e,dict) and e.get('schema') == 'ISOLATED_SUBSET_RECONCILIATION_V1' and
         e.get('reviewer_role') == 'independent_reviewer' and e.get('binding') == binding,
         'REVIEW_IDENTITY_MISMATCH')
    need(e.get('activity') == 'CONFIRMED_ENDED' and e.get('unresolved_attempts') == [],
         'UNKNOWN_OR_ACTIVE_BLOCKS')
    attempts = e.get('attempt_ids')
    need(isinstance(attempts,list) and 1 <= len(attempts) <= 3 and
         all(isinstance(a,str) and a for a in attempts) and len(set(attempts)) == len(attempts),
         'ATTEMPT_COUNT_OR_ID')
    need(e.get('last_attempt_id') == attempts[-1], 'LATEST_ATTEMPT_MISMATCH')
    ended = aware(e['ended_at'])
    local = now.astimezone(ZoneInfo('Asia/Shanghai'))
    need(local.date() == date, 'WRONG_LOCAL_DATE')
    need(local.time().replace(tzinfo=None) >= dt.time.fromisoformat(
        {'retry-1610':'16:10','retry-1640':'16:40'}[node]), 'RETRY_TIME_GATE')
    need(ended.astimezone(ZoneInfo('Asia/Shanghai')).date() == date and ended <= now,
         'RECONCILIATION_END_TIME')
    rows = e.get('stocks')
    need(isinstance(rows,list) and len(rows) == len(symbols) and
         all(isinstance(r,dict) for r in rows), 'INCOMPLETE_STOCK_RECONCILIATION')
    indexed = {}
    for row in rows:
        s = row.get('symbol')
        need(isinstance(s,str) and s in symbols and s not in indexed, 'SCOPE_MISMATCH')
        need(row.get('attempt_id') in attempts, 'STOCK_ATTEMPT_MISMATCH')
        indexed[s] = row
    failed, reused = [], []
    for s in symbols:
        row = indexed[s]
        if row.get('status') == 'SUCCESS':
            sha = row.get('output_sha256')
            need(isinstance(sha,str) and re.fullmatch('[0-9a-f]{64}',sha), 'OUTPUT_PIN_REQUIRED')
            raw = output_bytes.get(sha)
            need(type(raw) is bytes and hashlib.sha256(raw).hexdigest() == sha, 'SUCCESS_OUTPUT_UNVERIFIED')
            reused.append({'symbol':s,'output_sha256':sha})
        elif row.get('status') == 'FAILED_CLEAN':
            need(row.get('attempt_id') == attempts[-1] and row.get('retryable') is True and
                 row.get('effects') == 'INDEPENDENTLY_CONFIRMED_NO_PERSISTED_EFFECTS', 'FAILED_EFFECTS_UNKNOWN')
            failed.append(s)
        else:
            raise ValueError('UNKNOWN_STOCK_BLOCKS')
    # Completion consumes no new attempt.  It remains reusable after attempt 3
    # and immediately after reconciliation; the retry limits apply only to work.
    if failed:
        need(len(attempts) < 3, 'SHARED_ATTEMPT_LIMIT')
        need(now-ended >= dt.timedelta(minutes=30), 'RETRY_COOLDOWN')
    ordinal = len(attempts)+1 if failed else None
    result = {'schema':'ISOLATED_RETRY_SUBSET_PLAN_V1', 'binding':binding,
              'reconciliation_sha256':review_sha, 'node':node, 'checked_at':now.isoformat(),
              'next_attempt_ordinal':ordinal, 'retry_symbols':failed,
              'reuse_success':reused, 'status':'CANDIDATE_SUBSET' if failed else 'NO_RETRY_NEEDED',
              'dispatchable':False, 'natural_verified':False, 'business_accepted':False,
              'integration_required':['new reviewed subset-owner interface approval',
                  'same owner count/state/locks under atomic claim',
                  'original start and runtime resource gates', 'per-stock terminal reconciliation']}
    # No new retry identity: a stable intent can be deduplicated by the original
    # coordinator, which alone owns actual claim and attempt accounting.
    result['intent_id'] = digest({'binding':binding,'review':review_sha,'attempt':ordinal})
    return result

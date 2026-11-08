"""Synthetic text-only contract experiment. NOT the missing original reader.
No filesystem, network, source admission, locks, dispatch or production registration.
"""
import datetime as dt
import hashlib
import json
from zoneinfo import ZoneInfo

class RejectedInput(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def inspect_synthetic(data, *, target_date, registered_scope):
    if not isinstance(data, dict) or data.get('data_kind') != 'SYNTHETIC_TEST':
        raise RejectedInput('SYNTHETIC_ONLY')
    allowed = {'schema','market','target_date','observed_at','available_at','scope','rows','source_reference','data_kind'}
    if set(data) - allowed:
        raise RejectedInput('UNEXPECTED_FIELDS')
    if not isinstance(target_date,str) or len(target_date)!=8 or not target_date.isascii() or not target_date.isdigit():
        raise RejectedInput('TARGET_DATE')
    if data.get('schema') != 'A0915_RECORDED_DISPLAY_INPUT_V1' or data.get('market') != 'A_SHARE':
        raise RejectedInput('SCHEMA_MARKET')
    if data.get('target_date') != target_date:
        raise RejectedInput('TARGET_DATE')
    try:
        day = dt.datetime.strptime(target_date, '%Y%m%d').date()
    except ValueError:
        raise RejectedInput('TARGET_DATE') from None
    if day.strftime('%Y%m%d') != target_date:
        raise RejectedInput('TARGET_DATE')
    scope = data.get('scope')
    if not isinstance(scope, list) or not scope or any(not isinstance(s,str) or not s for s in scope):
        raise RejectedInput('SCOPE')
    if not isinstance(registered_scope,(tuple,list)):
        raise RejectedInput('SCOPE')
    if len(set(scope)) != len(scope) or scope != list(registered_scope):
        raise RejectedInput('SCOPE')
    times = []
    for key in ('observed_at', 'available_at'):
        if not isinstance(data.get(key),str) or not data[key]:
            raise RejectedInput('TIMESTAMP_REQUIRED')
        try:
            t = dt.datetime.fromisoformat(data[key])
        except ValueError:
            raise RejectedInput('TIMESTAMP_INVALID') from None
        if t.tzinfo is None:
            raise RejectedInput('TIMEZONE_REQUIRED')
        t = t.astimezone(ZoneInfo('Asia/Shanghai'))
        if t.date() != day:
            raise RejectedInput('SOURCE_DATE')
        times.append(t)
    if times[1] < times[0]:
        raise RejectedInput('TIME_ORDER')
    # New conservative experiment cutoff, NOT recovered original semantics.
    cutoff = dt.datetime.combine(day,dt.time(9,15),ZoneInfo('Asia/Shanghai'))
    if any(t > cutoff for t in times):
        raise RejectedInput('NOT_AVAILABLE')
    if not isinstance(data.get('source_reference'),str) or not data['source_reference'].strip():
        raise RejectedInput('SOURCE_REFERENCE')
    rows = data.get('rows')
    if not isinstance(rows,list):
        raise RejectedInput('ROWS')
    seen = set()
    for row in rows:
        if not isinstance(row,dict) or set(row) != {'symbol','observation'}:
            raise RejectedInput('ROW_FIELDS')
        if row.get('symbol') not in scope:
            raise RejectedInput('ROW_SCOPE')
        if row['symbol'] in seen:
            raise RejectedInput('DUPLICATE_ROW')
        if not isinstance(row.get('observation'),str) or not row['observation'].strip():
            raise RejectedInput('OBSERVATION_TEXT')
        seen.add(row['symbol'])
    missing = [s for s in scope if s not in seen]
    raw = json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return {'schema':'A0915_SYNTHETIC_CONTRACT_EXPERIMENT_V2',
            'recorded_input':json.loads(raw),
            'input_canonical_sha256':hashlib.sha256(raw).hexdigest(),
            'freshness_admission':'UNKNOWN',
            'data_kind':'SYNTHETIC_TEST','missing_symbols':missing,
            'scope_count':len(scope),'observed_count':len(seen),
            'blocking_reasons':(['MISSING_SCOPE_ROWS'] if missing else [])+['SOURCE_ADMISSION_UNKNOWN','ORIGINAL_CONTRACT_NOT_RECOVERED','FRESHNESS_CONTRACT_UNKNOWN'],
            'source_admission':'UNKNOWN','production_allowed':False,
            'business_accepted':False,'natural_verified':False,'source_calls':0}

"""Isolated assembly experiment; not a registered delivery implementation."""
import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo

SECTIONS = ('freeze', 'morning-materials', 'jk-verify')

def _time(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('timezone required')
    return parsed

def assemble(raws, pins, business_date, cutoff):
    end = _time(cutoff)
    local_end = end.astimezone(ZoneInfo("Asia/Shanghai"))
    if local_end.strftime("%Y%m%d") != business_date or local_end.strftime("%H:%M:%S.%f") != "08:10:00.000000":
        raise ValueError("cutoff must be business-day 08:10 Asia/Shanghai")
    if set(raws) - set(SECTIONS) or set(pins) - set(SECTIONS):
        raise ValueError('unrecognized section')
    sections, missing = [], []
    for name in SECTIONS:
        if name not in raws:
            missing.append(name)
            sections.append({'name': name, 'status': 'UNKNOWN', 'text': None, 'sha256': None})
            continue
        raw = raws[name]
        digest = hashlib.sha256(raw).hexdigest()
        if pins.get(name) != digest:
            raise ValueError('input digest mismatch')
        doc = json.loads(raw)
        if doc.get('business_date') != business_date:
            raise ValueError('business date mismatch')
        if _time(doc['available_at']) > end:
            raise ValueError('input after cutoff')
        if not isinstance(doc.get('status'), str) or not isinstance(doc.get('text'), str):
            raise ValueError('status and text required')
        sections.append({'name': name, 'status': doc['status'], 'text': doc['text'], 'sha256': digest})
    return {'schema': 'UNREGISTERED_LOCAL_EXPERIMENT_V1', 'business_date': business_date,
            'cutoff': cutoff, 'status': 'PARTIAL_LOCAL_ASSEMBLY' if missing else 'LOCAL_ASSEMBLY_READY',
            'sections': sections, 'missing': missing, 'delivery_status': 'NOT_SENT',
            'business_accepted': False, 'natural_trigger_verified': False}

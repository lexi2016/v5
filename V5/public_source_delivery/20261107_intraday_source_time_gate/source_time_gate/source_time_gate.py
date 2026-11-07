"""Exact original M11 time predicates; isolated from owner execution.
No origin/semantic/production admission is granted.
"""
from datetime import datetime

def _time(value):
    if not isinstance(value,str):raise ValueError('M11_TIME_UNKNOWN')
    stamp=datetime.fromisoformat(value)
    if stamp.tzinfo is None:raise ValueError('M11_TIME_UNBOUND')
    return stamp

def validate_availability(sources,cutoff):
    limit=_time(cutoff)
    if not isinstance(sources,list) or not sources:raise ValueError('M11_SOURCE_AVAILABILITY_UNKNOWN')
    for source in sources:
        if not isinstance(source,dict):raise ValueError('M11_SOURCE_RECORD_INVALID')
        available=_time(source.get('available_at'))
        if available>limit:raise ValueError('M11_SOURCE_LATE')
        for key in ('event_time','published_at','observed_at'):
            if key not in source:raise ValueError('M11_SOURCE_TIME_UNKNOWN')
            if _time(source[key])>available:raise ValueError('M11_SOURCE_TIME_ORDER')
    return True

def partition_materials(records,cutoff):
    """Preserve source records, classify timing only; late is not deleted."""
    _time(cutoff)
    result={"on_time":[],"late":[],"unknown":[],"source_admission":False,"semantic_admission":False,"natural_verified":False}
    if not isinstance(records,list):raise ValueError("MATERIALS_LIST_REQUIRED")
    for record in records:
        try:
            validate_availability([record],cutoff)
            result["on_time"].append(record)
        except (ValueError,TypeError) as error:
            kind="late" if str(error)=="M11_SOURCE_LATE" else "unknown"
            result[kind].append({"record":record,"reason":str(error)})
    result["status"]="BLOCKED_NO_MATERIALS" if not records else "TIMING_PARTITIONED_NOT_CONTENT_ACCEPTED"
    return result

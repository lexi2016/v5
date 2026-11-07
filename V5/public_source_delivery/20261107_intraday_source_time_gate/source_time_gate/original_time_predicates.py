"""Reference excerpt only; never executes the original M11 owner."""
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

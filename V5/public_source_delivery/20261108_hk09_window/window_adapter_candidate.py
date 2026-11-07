"""HK09-only recorded-time adapter. No collector, source activation or registry.
Reuse original reviewed window_state; never round source/receipt timestamps.
"""
import datetime as dt
import hashlib
import importlib.util
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Hong_Kong')
ROOT=None # deployment dependencies intentionally unbound
RUNNER_SHA='2df55abdb06f58f4dc2a877d39537467bfbcd0cc223539587d507ffcf040144a'
TRUSTED_RUNS=() # no production dispatch API

def _stamp(value):
 t=dt.datetime.fromisoformat(value)
 if t.tzinfo is None:raise ValueError('TIMEZONE_REQUIRED')
 return t.astimezone(TZ)

def inspect_window(day, *, started_at, observed_at, received_at, checked_at):
 """Only validate recorded timing. This never grants scope/source admission."""
 target=dt.datetime.strptime(day,'%Y%m%d').date()
 start,observed,received,checked=map(_stamp,(started_at,observed_at,received_at,checked_at))
 if any(t.date()!=target for t in (start,observed,received,checked)):raise ValueError('EXACT_DATE_REQUIRED')
 if not start<=received<=checked or not observed<=received:raise ValueError('CLOCK_ORDER')
 if ROOT is None:raise ValueError('ORIGINAL_DEPENDENCIES_UNBOUND')
 path=ROOT/'runner.py';raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=RUNNER_SHA:raise ValueError('ORIGINAL_CODE_SHA')
 spec=importlib.util.spec_from_file_location('hk09_original_window',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.verify_review(ROOT/'INDEPENDENT_REVIEW.json',ROOT/'POLICY.json')
 timing=m.window_state(start,'0900')
 if timing not in ('ON_TIME','LATE'):raise ValueError('START_'+timing)
 if m.window_state(received,'0900') not in ('ON_TIME','LATE'):raise ValueError('RECEIVED_OUTSIDE_PHASE')
 if m.window_state(observed,'0900') not in ('ON_TIME','LATE'):raise ValueError('SOURCE_OUTSIDE_PHASE')
 if not 0<=(received-observed).total_seconds()<=120:raise ValueError('STALE_OR_FUTURE')
 return {'window_read_status':'RECORDED_TIMING_VALID','status':'BLOCKED_SOURCE_SCOPE_AND_RESOURCE_JOB_BINDING_UNKNOWN',
         'node':'hk-open','day':day,'timing_status':timing,'started_at':started_at,
         'observed_at':observed_at,'received_at':received_at,'checked_at':checked_at,
         'source_id':'tencent_ordinary_v1','purpose':'RAW_OBSERVATION_ONLY',
         'current_scope_authority':'UNKNOWN','current_connect_eligibility':'UNKNOWN',
         'provider_availability':'UNKNOWN','resource_and_job_lock_binding':'UNKNOWN',
         'production_allowed':False,'business_accepted':False,'natural_verified':False}

"""Invoke registered daily owner adapters only. No collector, cron or business rule."""
from datetime import datetime,timezone,timedelta
from v5_shadow.daily_close_plan import _sources,_market_states
from v5_shadow.contracts import aware
from v5_shadow.digests import sha256_json
from v5_shadow.run_ledger import claim_run,finish_run

LANES={'announcement','us_mapping','rebound','manager_close_recapture'}


def dispatch_due(schedule,bindings,ledger_root):
    """schedule is explicit approved slots; bindings are in-process trusted adapters.

    An adapter owns all source admission, original US session/calendar handling,
    bounded capture/idempotency and artifact readback. Missing adapters do not
    become successes. No dynamic import, shell command or automatic retry loop.
    """
    now=datetime.now(timezone.utc);today=now.astimezone(timezone(timedelta(hours=8))).strftime('%Y%m%d')
    states=_market_states(_sources(),today);results=[]
    def one(job):
        lane=job['lane']
        if lane not in LANES:raise ValueError('DAILY_LANE')
        reason=None
        if lane=='manager_close_recapture':
            if lane not in bindings:return dict(lane=lane,status='OWNER_ADAPTER_NOT_BOUND')
            from .p0_close_recapture import admission_reason
            try: reason=admission_reason(job,bindings[lane],now)
            except Exception:return dict(lane=lane,status='BLOCKED_M17_REGISTRATION')
            if reason:return dict(lane=lane,status=reason)
        if job['identity']['lane']!=lane or (lane!='manager_close_recapture' and job['identity']['target_date']!=today):reason='NOT_CURRENT_TARGET_DATE'
        elif lane!='manager_close_recapture' and states['hk_securities'] not in {'FULL_TRADING_DAY','HALF_TRADING_DAY_AM'}:reason='HK_SECURITIES_CALENDAR_NOT_OPEN'
        elif lane!='manager_close_recapture' and states['hk_securities']=='HALF_TRADING_DAY_AM' and job.get('half_day_bound') is not True:reason='HALF_DAY_SLOT_NOT_BOUND'
        elif aware(job['identity']['research_cutoff'])>now:reason='FUTURE_RESEARCH_CUTOFF'
        elif aware(job['scheduled_at'])>=aware(job['deadline']):reason='INVALID_SLOT_WINDOW'
        elif now<aware(job['scheduled_at']):reason='WAITING_TIME'
        elif now>=aware(job['deadline']):reason='MISSED_WINDOW_NO_BACKFILL'
        elif lane not in bindings:reason='OWNER_ADAPTER_NOT_BOUND'
        elif any(bindings[lane][key]!=job['identity'][key] for key in ('code_sha256','config_sha256','dependency_sha256')):reason='OWNER_BINDING_IDENTITY_MISMATCH'
        elif sha256_json(job['owner_request'])!=job['identity']['input_sha256']:reason='OWNER_REQUEST_IDENTITY_MISMATCH'
        elif lane=='us_mapping' and (job['owner_request'].get('target_date')!=today or aware(job['owner_request'].get('now'))!=aware(job['identity']['research_cutoff'])):reason='US_OWNER_DATE_CUTOFF_MISMATCH'
        if reason:
            return dict(lane=lane,status=reason)
        claim=claim_run(ledger_root,job['identity'],max_attempts=job['max_attempts'])
        if lane=='manager_close_recapture' and claim['status']=='REUSED_SUCCESS':
            from .p0_close_recapture import read_saved
            return dict(lane=lane,**read_saved(claim,job['owner_request'],bindings[lane]))
        if claim['status']!='CLAIMED':return dict(lane=lane,**claim)
        try:
            receipt=bindings[lane]['invoke'](job['owner_request'],claim['run_id'])
            if lane=='manager_close_recapture':
                from .p0_close_recapture import verify_receipt
                verify_receipt(receipt,bindings[lane])
            state=finish_run(ledger_root,claim,receipt)
            if lane=='manager_close_recapture':
                from .run_ledger import read_run
                if read_run(ledger_root,job['identity'])!=state:raise ValueError('M17_LEDGER_READBACK_MISMATCH')
            return dict(lane=lane,status=state['attempts'][-1]['status'],state=state)
        except Exception as error:
            # Unknown outcome is NOT proof that a capture was not sent. Retain
            # RUNNING until an owner-specific readback can reconcile it.
            return dict(lane=lane,status='OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY',run_id=claim['run_id'],reason=type(error).__name__)
    for job in schedule:
        try:results.append(one(job))
        except Exception as error:results.append(dict(lane=job.get('lane') if isinstance(job,dict) else None,status='LANE_ADMISSION_FAILED',reason=type(error).__name__))
    return dict(status='DISPATCH_ATTEMPT_ONLY',observed_at=now.isoformat(),lanes=results,natural_verified=False)

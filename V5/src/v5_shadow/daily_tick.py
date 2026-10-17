"""One existing-dispatcher tick over a prepared exact-date private request bundle."""
import sys
from pathlib import Path
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
from datetime import datetime,timezone,timedelta
import json
import plistlib
from v5_shadow.daily_dispatch import dispatch_due
from v5_shadow.daily_owner_adapters import adapter_identity,read_announcement_owner,run_manager_daily
from v5_shadow.daily_rebound_owner import run_rebound_owner,PIN as REBOUND_PIN
from v5_shadow.daily_us_owner import bind_us_owner
from v5_shadow.digests import sha256_json,canonical_bytes
from v5_shadow.module_api import _open_directory,_read_at
from v5_shadow.contracts import aware
import os

LABEL='com.lexi.v5.daily.candidate'


def default_slots(target):
    date=target[:4]+'-'+target[4:6]+'-'+target[6:]
    return dict(scheduled_at=date+'T08:00:00+08:00',deadline=date+'T08:45:00+08:00',
        research_cutoff=date+'T08:00:00+08:00',half_day_bound=True,max_attempts=1,
        plan_at=date+'T08:45:00+08:00',plan_deadline=date+'T09:00:00+08:00',
        schedule_basis='NEW_V5_DEFAULT_NOT_VERIFIED_V4_SCHEDULE')


def daily_config(config):
    """The CLI accepts either a daily object or the existing main runtime config."""
    if not isinstance(config,dict):raise ValueError('DAILY_CONFIG_INVALID')
    if 'daily' not in config:return config
    if any(key in config for key in ('enabled','bundle_root','ledger_root','hk_preselection','hk_preselection_daily','close_recapture')):
        raise ValueError('DAILY_CONFIG_AMBIGUOUS')
    if not isinstance(config['daily'],dict):raise ValueError('DAILY_CONFIG_INVALID')
    return config['daily']


def manager_plan_window_status(now, slots):
    """Apply the same bounded plan window to either prepared requests or templates.

    A prebuilt manager_request is not permission to bypass the scheduled window.
    Before the slot, wait; after it, never backfill. The caller may assemble a
    template or consume a prebuilt request only while the window is open.
    """
    start=aware(slots['plan_at'])
    deadline=aware(slots['plan_deadline'])
    if now < start:
        return 'WAITING_0845_PLAN_WINDOW'
    if now >= deadline:
        return 'MISSED_PLAN_WINDOW_NO_BACKFILL'
    return None


def tick(config):
    config=daily_config(config)
    if config.get('enabled') is not True:return dict(status='DISABLED',natural_verified=False)
    observed=datetime.now(timezone(timedelta(hours=8)));today=observed.strftime('%Y%m%d')
    candidate_enabled=config.get('hk_preselection_daily',{}).get('enabled') is True
    fd=_open_directory(config['bundle_root'])
    try:
        if _read_at(fd,None,'.v5-daily-bundles')!=b'v5.daily-bundles.v1\n':raise ValueError('DAILY_BUNDLE_MARKER')
        try:bundle=json.loads(_read_at(fd,None,today+'.json'))
        except FileNotFoundError:
            if not candidate_enabled:return dict(status='BLOCKED_CURRENT_BUNDLE_MISSING',natural_verified=False)
            bundle=dict(target_date=today,jobs=[])
    finally:os.close(fd)
    if bundle['target_date']!=today:raise ValueError('DAILY_BUNDLE_TARGET')
    from v5_shadow.announcement_offline_reader import PIN as ANNOUNCEMENT_PIN,REVISION_PIN
    from v5_shadow.manager_plan import PIN as MANAGER_PIN, _identity as manager_identity
    # M17's exact-date pool/runtime binding must not rekey unrelated owners.
    ordinary_config={k:v for k,v in config.items() if k not in {'close_recapture','hk_preselection','hk_preselection_daily'}}
    registration=adapter_identity(ordinary_config,dict(announcement=ANNOUNCEMENT_PIN,revision=REVISION_PIN,rebound=REBOUND_PIN,
        manager=MANAGER_PIN,manager_implementation=manager_identity()))
    bindings=dict(us_mapping=bind_us_owner(ordinary_config),
        announcement=dict(registration,invoke=read_announcement_owner),
        rebound=dict(registration,invoke=run_rebound_owner))
    jobs=[];rejected=[];candidate=None
    explicit_m06=any(job.get('lane')=='hk_preselection' for job in bundle['jobs'])
    if candidate_enabled:
        if explicit_m06:rejected.append(dict(lane='hk_preselection',status='BLOCKED_M06_DUPLICATE_SLOT'))
        else:
            from v5_shadow.p0_hk_preselection import prepare_daily_candidate
            try:
                candidate=prepare_daily_candidate(config,observed)
                if candidate['status']=='PREPARED_M06_CANDIDATE':
                    jobs.append(candidate['job']);bindings['hk_preselection']=candidate['binding']
                else:rejected.append(dict(lane='hk_preselection',status=candidate['status']))
            except Exception as error:
                token=str(error).split(':',1)[0]
                rejected.append(dict(lane='hk_preselection',status='BLOCKED_M06_DAILY_CANDIDATE',
                    reason=token if token.isidentifier() else type(error).__name__))
    defaults=default_slots(today)
    for job in bundle['jobs']:
        try:
            if job.get('lane')=='hk_preselection':
                if candidate_enabled:continue
                from v5_shadow.p0_hk_preselection import prepare_job
                prepared,binding=prepare_job(job,config.get('hk_preselection'),today)
                bindings[job['lane']]=binding;jobs.append(prepared);continue
            if job.get('lane')=='manager_close_recapture':
                from v5_shadow.p0_close_recapture import prepare_job,validate_registration
                registration_m17=config.get('close_recapture')
                gate=validate_registration(registration_m17)
                if gate['status']!='BOUND_NOT_NATURALLY_VERIFIED':
                    rejected.append(dict(lane=job['lane'],**gate));continue
                prepared,binding=prepare_job(job,registration_m17,today)
                bindings[job['lane']]=binding;jobs.append(prepared);continue
            job=dict({key:defaults[key] for key in ('scheduled_at','deadline','research_cutoff','half_day_bound','max_attempts')},**job)
            lane=job['lane'];request=job['owner_request']
            if lane=='announcement':
                if 'revision_create' in request:
                    if request['target_date']!=today:raise ValueError('ANNOUNCEMENT_REVISION_TARGET')
                    create=request['revision_create']
                    if not create or not request.get('review_identities') or any(not Path(create.get(key,'')).is_file() for key in ('semantic_catalog','reviewer_output','decisions')):
                        rejected.append(dict(lane=lane,status='BLOCKED_WAITING_REAL_ANALYSIS_REVIEW_DECISIONS'));continue
                elif request['binding']['target_date']!=today or request['cutoff']!=job['research_cutoff']:
                    raise ValueError('ANNOUNCEMENT_DATE_CUTOFF')
            elif lane=='rebound':
                if request['request']['target_date']!=today:raise ValueError('REBOUND_TARGET_DATE')
            if lane not in bindings:raise ValueError('DAILY_UNKNOWN_OWNER')
            identity={k:bindings[lane][k] for k in ('code_sha256','config_sha256','dependency_sha256')}
            jobs.append(dict(job,identity=dict(identity,lane=lane,target_date=today,
                research_cutoff=job['research_cutoff'],input_sha256=sha256_json(request))))
        except Exception as error:
            rejected.append(dict(lane=job.get('lane') if isinstance(job,dict) else None,
                                 status='BLOCKED_OWNER_CONTRACT',reason=type(error).__name__))
    result=dispatch_due(jobs,bindings,config['ledger_root'])
    if candidate is not None and candidate['status']=='PREPARED_M06_CANDIDATE':
        from v5_shadow.p0_hk_preselection import promote_current_success
        row=result['lanes'][0]
        try:row['current_success']=promote_current_success(config,candidate,row)
        except Exception as error:
            # Atomic replace may already have committed. Do not claim unchanged
            # or undo/reinvoke; only independent pointer/ledger reads can decide.
            row['current_success']=dict(status='CURRENT_SUCCESS_UPDATE_OUTCOME_UNKNOWN',
                reason=type(error).__name__,
                action_required='READ_ONLY_VERIFY_CURRENT_AND_BOTH_LEDGERS_NO_OWNER_RETRY')
    # At 08:45 the execution window closes, but already saved owner products
    # remain readable for the plan. Never re-execute to recover their references.
    from v5_shadow.run_ledger import read_run
    for job,row in zip(jobs,result['lanes']):
        # M06 success is attached only by its exact cold read path, never by
        # generic ledger fallback outside an admitted slot.
        if job['lane']=='hk_preselection':continue
        if 'state' not in row:
            state=read_run(config['ledger_root'],job['identity'])
            if state is not None:row['state']=state
    result['lanes'].extend(rejected)
    manager=bundle.get('manager_request')
    template=bundle.get('manager_template')
    if manager is None and template is None:result['manager']=dict(status='BLOCKED_POST_OWNER_REQUEST_MISSING')
    else:
        try:
            now=datetime.now(timezone.utc)
            window_status=manager_plan_window_status(now, defaults)
            if window_status is not None:
                result['manager']=dict(status=window_status);return result
            if template is not None:
                from v5_shadow.daily_manager_assembly import assemble_manager_request
                manager=assemble_manager_request(template,result['lanes'],config['ledger_root'],registration)
            publication_config = config.get('manager_publication')
            if publication_config is None:
                saved=run_manager_daily(manager,config['ledger_root'],registration)
            else:
                # Snapshot the transport CAS token before saving. It is runtime
                # concurrency state, not part of the stable config identity.
                from v5_shadow.module_api import _config, _generation_head
                checked, fd = _config(publication_config)
                try:
                    generation = _generation_head(fd, checked)
                finally:
                    os.close(fd)
                publication = dict(config=checked, expected_generation=generation)
                saved=run_manager_daily(manager,config['ledger_root'],registration,publication=publication)
            result['manager']=dict(status=saved.get('status','PLAN_SAVED_BUSINESS_BLOCKED'),
                publication=saved.get('publication'), state=saved.get('state'))
        except Exception as error:result['manager']=dict(status='BLOCKED_OR_OUTCOME_UNKNOWN',reason=type(error).__name__)
    return result


def launchd_contract(config_path, *, python, interval=300):
    """Render only. Installation/enablement belong to the existing Mac task."""
    config_path=Path(config_path);python=Path(python)
    if not config_path.is_absolute() or not python.is_absolute() or type(interval) is not int or interval<60:
        raise ValueError('DAILY_LAUNCHD_CONTRACT')
    return dict(Label=LABEL,ProgramArguments=[str(python),'-I','-B',str(Path(__file__).resolve()),
        '--config',str(config_path)],StartInterval=interval,RunAtLoad=False,Disabled=True,
        ProcessType='Background')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--render-launchd',action='store_true')
    parser.add_argument('--python',default=sys.executable)
    args=parser.parse_args()
    if args.render_launchd:sys.stdout.buffer.write(plistlib.dumps(launchd_contract(args.config,python=args.python)))
    else:
        result=tick(json.loads(args.config.read_bytes()))
        # Operational logs contain statuses only, not raw private artifacts.
        print(canonical_bytes(dict(status=result['status'],natural_verified=False,
            lanes=[dict(lane=row['lane'],status=row['status'],
                **({'current_success':row['current_success']['status']} if 'current_success' in row else {}),
                **({'current_success_action':row['current_success']['action_required']}
                   if 'action_required' in row.get('current_success',{}) else {})) for row in result.get('lanes',[])],
            manager=result.get('manager'))).decode())

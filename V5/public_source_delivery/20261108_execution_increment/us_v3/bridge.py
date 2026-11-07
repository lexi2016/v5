"""Reviewed-caller bridge, not a scheduler or an authority generator.

ADMISSIONS is a release-time reviewed registry, never read from CLI/untrusted
JSON. Empty until a real existing capture task and its run readback are bound.
Only raw capture is authorized here; no source/reader/training promotion.
"""
import hashlib,types,os,stat
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BOOTSTRAP='handoff/us_execution_bridge_candidate_v3_20261107/entrypoint.py'
BOOTSTRAP_SHA='2e55d7c8327100181225100004d1b571e85ab1b9f95e8c91f5c3958744a27f37'
LAUNCHER_SHA='cc19ae4822353999389c4791726ee3b14d7e3f6e38131d7bb33ff9db19eb8db0'
ADMISSIONS=()

def load():
    # Existing bootstrap pins the exact launcher before execution. This adapter
    # additionally pins bootstrap bytes and executes held bytes, not re-imports.
    p=ROOT/BOOTSTRAP
    fds=[]
    try:
        fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(fd)
        for part in p.parts[1:-1]:
            fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(fd)
        f=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);fds.append(f)
        before=os.fstat(f)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or not 0<before.st_size<65536:raise ValueError('BOOTSTRAP_FILE')
        raw=os.read(f,before.st_size+1)
        ident=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if len(raw)!=before.st_size or ident(before)!=ident(os.fstat(f)) or ident(before)!=ident(os.stat(p.name,dir_fd=fd,follow_symlinks=False)):raise ValueError('BOOTSTRAP_CHANGED')
    finally:
        for fd in reversed(fds):os.close(fd)
    if hashlib.sha256(raw).hexdigest()!=BOOTSTRAP_SHA:raise ValueError('BOOTSTRAP_PIN')
    m=types.ModuleType('_us_bridge_bootstrap');m.__file__=str(p)
    exec(compile(raw,str(p),'exec'),m.__dict__)
    return m.load()

def dispatch(automation_id,run_id,execution_environment_id):
    """Called by trusted task runner, never a user-supplied admission file.

    No registry entry means no load, resource probe, filesystem write, lock or
    network. The IDs select an already independently reviewed entry only.
    """
    matches=[a for a in ADMISSIONS if a.get('automation_id')==automation_id and a.get('run_id')==run_id]
    if len(matches)!=1:return {'status':'BLOCKED_NO_REVIEWED_CAPTURE_RUN','network_requests':0,'state_written':False}
    a=matches[0]
    required={'automation_id','run_id','execution_environment_id','target_session_date','launcher_sha256','purpose','binding','payload','review_ref'}
    if set(a)!=required or not all(type(a[k]) is str and a[k] for k in ('automation_id','run_id','execution_environment_id','review_ref')):raise ValueError('ADMISSION_SHAPE')
    if a['purpose']!='RAW_US_CAPTURE_ONLY' or a['launcher_sha256']!=LAUNCHER_SHA:raise ValueError('ADMISSION_SCOPE')
    if a['execution_environment_id']!=execution_environment_id:raise ValueError('ADMISSION_ENVIRONMENT')
    b=a['binding'];p=a['payload']
    if b.get('automation_id')!=automation_id or b.get('run_id')!=run_id or p.get('automation_id')!=automation_id or p.get('run_id')!=run_id:raise ValueError('ADMISSION_RUN_BINDING')
    l=load();l.verify_launcher();bundle=l.load_bundle();plan=bundle['session_plan'].plan(a['target_session_date']);l.TARGET=plan['target_session_date']
    if p.get('target_session_date')!=l.TARGET:raise ValueError('ADMISSION_SESSION_BINDING')
    # All refusal gates precede _pipeline's first state write. Existing code
    # retains 13 shared locks, resource rechecks, pins and attempt reconciliation.
    l.trigger_readback(p,b)
    try:l.check_resources(bundle,start=True)
    except (OSError,ValueError,StopIteration) as e:
        return {'status':'BLOCKED_RESOURCE_PREFLIGHT','error':type(e).__name__+': '+str(e),'network_requests':0,'state_written':False}
    result=l._pipeline(bundle,plan,p,b)
    return {'bridge_scope':'RAW_US_CAPTURE_ONLY','admission_review_ref':a['review_ref'],**result}

def main(argv=None):
    import argparse,json
    parser=argparse.ArgumentParser(description='Select an existing independently reviewed US capture run; arguments cannot grant admission.')
    parser.add_argument('--automation-id',required=True)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--environment-id',required=True)
    args=parser.parse_args(argv)
    result=dispatch(args.automation_id,args.run_id,args.environment_id)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 2 if result.get('status','').startswith('BLOCKED_') else 0

if __name__=='__main__':
    raise SystemExit(main())

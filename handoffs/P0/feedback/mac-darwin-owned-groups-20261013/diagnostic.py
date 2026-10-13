"""One finite three-case diagnostic; never signals a preexisting PID/group."""
from pathlib import Path
import os,sys,json,time,signal,subprocess,datetime,hashlib
ROOT=Path.cwd()/'evidence-darwin-owned-groups';ROOT.mkdir(exist_ok=False)
WORKER=ROOT/'finite_worker.py'
WORKER.write_text('''from pathlib import Path
import os,sys,json,time,subprocess
root=Path(sys.argv[1]);role=sys.argv[2];case=sys.argv[3]
started=time.monotonic()
(root/(role+'.json')).write_text(json.dumps(dict(pid=os.getpid(),ppid=os.getppid(),pgid=os.getpgrp(),sid=os.getsid(0))))
if case!='zombie_only' and role in ('leader','child'):
    nxt='child' if role=='leader' else 'grandchild'
    subprocess.Popen([sys.executable,'-I','-B',__file__,str(root),nxt,case],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
if case=='zombie_only':sys.exit(0)
if case=='exited_leader_live_children' and role=='leader':
    while not (root/'grandchild.json').exists() and time.monotonic()-started<2:time.sleep(.005)
    sys.exit(0)
while time.monotonic()-started<5:time.sleep(.01)
''')
def call(fn):
 try:return {'ok':True,'value':fn()}
 except OSError as e:return {'ok':False,'type':type(e).__name__,'errno':e.errno,'message':e.strerror}
def group_rows(group):
 raw=subprocess.check_output(['/bin/ps','-axo','pid=,ppid=,pgid=,stat=,command='],text=True)
 result=[]
 for line in raw.splitlines():
  f=line.strip().split(None,4)
  if len(f)==5 and int(f[2])==group:result.append(dict(pid=int(f[0]),ppid=int(f[1]),pgid=int(f[2]),state=f[3],command=f[4].replace(str(ROOT),'<DIAGNOSTIC_ROOT>').replace(sys.executable,'<EXISTING_HK02_PYTHON>')))
 return result
results=[]
for case in ('alive_leader','exited_leader_live_children','zombie_only'):
 root=ROOT/case;root.mkdir();start=time.monotonic()
 proc=subprocess.Popen([sys.executable,'-I','-B',str(WORKER),str(root),'leader',case],start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 expected_roles=['leader'] if case=='zombie_only' else ['leader','child','grandchild']
 while not all((root/(r+'.json')).is_file() for r in expected_roles) and time.monotonic()-start<2:time.sleep(.01)
 identities={r:json.loads((root/(r+'.json')).read_text()) for r in expected_roles if (root/(r+'.json')).exists()}
 def observe_wait():
  v=os.waitid(os.P_PID,proc.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG)
  return None if v is None else {k:getattr(v,k) for k in ('si_pid','si_uid','si_signo','si_status','si_code')}
 observed=observe_wait()
 if case!='alive_leader':
  while observed is None and time.monotonic()-start<2:time.sleep(.01);observed=observe_wait()
 pgid=call(lambda:os.getpgid(proc.pid));sid=call(lambda:os.getsid(proc.pid));members=group_rows(proc.pid)
 known={v['pid'] for v in identities.values()}
 own=(len(identities)==len(expected_roles) and identities['leader']['pid']==proc.pid and identities['leader']['ppid']==os.getpid() and proc.pid>1 and proc.pid!=os.getpgrp() and all(v['pgid']==proc.pid and v['sid']==proc.pid for v in identities.values()) and bool(members) and all(v['pid'] in known for v in members) and (observed is None or observed['si_pid']==proc.pid))
 row=dict(case=case,waitid_wnowait=observed,getpgid=pgid,getsid=sid,initial_owned_identities=identities,ps_group_before=members,ownership_confirmed=own,killpg_signal='SIGTERM',killpg=call(lambda:os.killpg(proc.pid,signal.SIGTERM)) if own else {'not_sent':'ownership not fully confirmed'},started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 # No poll()/wait() before the WNOWAIT observations and guarded signal above.
 try:row['final_wait_exit']=proc.wait(timeout=7)
 except subprocess.TimeoutExpired:row['final_wait_error']='finite leader exceeded 7 seconds; no extra signal'
 # All children have a hard-coded <=5-second lifetime; allow natural exits.
 until=start+6
 while time.monotonic()<until:
  remaining=group_rows(proc.pid)
  if not any(not x['state'].startswith('Z') for x in remaining):break
  time.sleep(.05)
 row['ps_group_after']=group_rows(proc.pid);row['duration_seconds']=round(time.monotonic()-start,3);results.append(row)
 (ROOT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))

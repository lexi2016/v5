from pathlib import Path
import subprocess,os,time,json,hashlib,signal
O=Path(__file__).resolve().parent;D=O/'unpacked/repository/M09_DELIVERY_20261011';W=O/'work';L=O/'verification';PY=str(O.parent/'m13-isolated/venv/bin/python');env=dict(os.environ);env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR=str(O/'fixture-tmp'));results=[]
def run(name,cmd,cwd,timeout=240):
 start=time.monotonic();meta={'argv':cmd,'cwd':str(cwd),'python':PY,'environment':{k:v for k,v in env.items() if k.startswith(('M09_','PYTHON')) or k=='TMPDIR'},'timeout_seconds':timeout};(L/(name+'.command.json')).write_text(json.dumps(meta,indent=2));timed=False
 with (L/(name+'.stdout.log')).open('w') as out,(L/(name+'.stderr.log')).open('w') as err:
  p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=out,stderr=err,start_new_session=True)
  try:code=p.wait(timeout=timeout)
  except subprocess.TimeoutExpired:timed=True;os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=5);code=124
 r={'name':name,'exit':code,'timed_out':timed,'elapsed_seconds':round(time.monotonic()-start,3)};(L/(name+'.exit')).write_text(str(code));results.append(r);(L/'results.json').write_text(json.dumps(results,indent=2));print(r,flush=True);return code
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();tree=lambda root:{str(p.relative_to(root)):h(p) for p in root.rglob('*') if p.is_file()}
m=json.loads((D/'DELIVERY_FILES.json').read_text());assert all(h(D/e['path'])==e['sha256'] for e in m['files'])
for phase,n in [('forward','forward.patch'),('reverse','reverse.patch')]:
 for check in [True,False]:assert run(phase+('-check' if check else '-apply'),['git','apply']+(['--check'] if check else [])+[str(D/n)],O/'patch-check')==0
 assert tree(O/'patch-check')==tree(D/('after' if phase=='forward' else 'before'))
run('environment',[PY,'-B','-c','import sys,platform,json,importlib.metadata as m,pandas,pyarrow; print(json.dumps({"python":sys.version,"executable":sys.executable,"platform":platform.platform(),"pandas":pandas.__version__,"pyarrow":pyarrow.__version__,"dependencies":{d.metadata["Name"]:d.version for d in m.distributions()}},indent=2))'],W)
env.update(PYTHONPATH=str(W/'V5/src')+os.pathsep+str(W/'V5/tests'),M09_ORIGINAL_SOURCE_ROOT=str(D/'before/handoff/v4-running-source-20261005/canonical'))
run('original-suite125',[PY,'-B','-m','unittest','-v','test_a_close_review','test_a_close_daily_sources','test_a_close_daily','test_a_close_daily_api','test_daily_close_plan'],W)
env.update(M09_REVIEW_SNAPSHOT=str(W),PYTHONPATH=str(D/'evidence/independent_review'))
run('independent-six',[PY,'-B','-m','unittest','-v','test_review_findings','test_api_raw_digest','test_preimported_helper_identity','test_restored_helper_identity'],W)
env['PYTHONPATH']=str(W/'V5/src')+os.pathsep+str(W/'V5/tests')
run('extract-real-inputs',[PY,'-B',str(D/'tools/extract_pinned_runtime.py'),'--archive',str(O/'unpacked/repository/handoff/m09-20261011/M09_ORIGINAL_INPUTS_RUNTIME_BINDINGS_20261011.zip'),'--out',str(O/'runtime-inputs')],W)
run('real-uncleaned-diagnostic',[PY,'-B',str(D/'tools/mac_real_input_check.py'),'--after',str(W),'--runtime-inputs',str(O/'runtime-inputs/M09_ORIGINAL_INPUTS_RUNTIME_BINDINGS_20261011'),'--out',str(O/'session/real_uncleaned_diagnostic')],W)
run('generation-walkthrough',[PY,'-B',str(D/'tools/mac_generation_walkthrough.py'),'--after',str(W),'--out',str(O/'session/engineering_walkthrough')],W)
(L/'final_tree_check.json').write_text(json.dumps({'work_matches_after':tree(W)==tree(D/'after'),'patch_copy_matches_before':tree(O/'patch-check')==tree(D/'before')},indent=2))

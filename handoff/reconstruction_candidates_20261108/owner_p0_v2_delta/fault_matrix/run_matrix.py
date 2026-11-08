import pathlib,subprocess,sys,json,gzip,time,hashlib,os,fcntl,atexit
H=pathlib.Path(__file__).resolve().parent
D=H/('evidence_'+str(time.time_ns()));D.mkdir()
(D/'input.gz').write_bytes(gzip.compress(json.dumps({'symbol':'SYNTHETIC','actual_last_date':'20261106'}).encode()))
rows=[]
def need(ok):
 if not ok:raise RuntimeError('MATRIX_ASSERTION_FAILED')
children=[]
def cleanup():
 for p in children:
  if p.poll() is None:p.kill()
  p.communicate()
atexit.register(cleanup)
def start(root,mode,out):
 p=subprocess.Popen([sys.executable,'-B',str(H/'worker.py'),str(root),mode,out],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 children.append(p);return p
def finish(p):
 text=p.communicate(timeout=10)[0];return {'exit':p.returncode,'log':text}
def hashes(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
root=D/'competition';a=start(root,'hold','a')
for _ in range(500):
 if (root/'runs/a/READY').exists():break
 time.sleep(.01)
else:raise RuntimeError('no ready')
b=finish(start(root,'normal','b'));(root/'RELEASE').write_text('release');ar=finish(a)
need(b['exit']==20 and 'BlockingIOError' in b['log'] and not (root/'runs/b').exists())
need(ar['exit']==0)
rows.append({'case':'actual_two_process_competition','first':ar,'second':b,'status':'PASS'})
for mode in ['crash_claim','partial_parquet','crash_pre_link','crash_post_link','fault_dir_fsync']:
 root=D/mode;r=finish(start(root,mode,'a'));before=hashes(root)
 fd=os.open(root/'OWNER.lock',os.O_RDWR)
 try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
 finally:os.close(fd)
 retry=finish(start(root,'normal','b'));after=hashes(root)
 need(retry['exit']==20 and 'EXISTING_TASK' in retry['log'] and before==after and not (root/'runs/b').exists())
 need(r['exit']=={'crash_claim':91,'partial_parquet':92,'crash_pre_link':93,'crash_post_link':94,'fault_dir_fsync':20}[mode])
 if mode=='fault_dir_fsync':need('INJECTED_DIR_FSYNC' in r['log'])
 if mode=='partial_parquet':need((root/'runs/a/stock/parquet/field_rows.parquet.partial').read_bytes()==b'PAR1_SYNTHETIC_INCOMPLETE_NOT_REAL_PARQUET')
 final=root/'runs/a/RESULT.json';pending=root/'runs/a/RESULT.json.pending'
 if mode in ['crash_claim','partial_parquet','crash_pre_link']:need(not final.exists())
 if mode=='crash_pre_link':need(pending.exists())
 if mode=='crash_post_link':need(final.exists() and pending.exists())
 if mode=='fault_dir_fsync':need(final.exists() and not pending.exists())
 if final.exists():need(json.loads(final.read_text())=={'status':'SYNTHETIC_PROTOCOL_ONLY','production_allowed':False})
 rows.append({'case':mode,'first':r,'retry':retry,'status':'PASS','terminal_exists':final.exists(),'pending_exists':pending.exists(),'retained_sha256':after,'interpretation':'No blind retry; terminal existence does not prove durable successful return'})
(D/'RESULTS.json').write_text(json.dumps(rows,indent=2));print(D);print(json.dumps(rows,indent=2))

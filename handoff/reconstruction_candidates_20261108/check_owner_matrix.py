import pathlib,json,sys,subprocess,hashlib,fcntl,os,datetime
H=pathlib.Path(__file__).resolve().parent;R=H/'owner_full_matrix';reports=[]
def hashes(out):return {str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
for label in ('none','second_object','receipt_before','receipt_after','none_opt','second_object_opt','receipt_before_opt','receipt_after_opt'):
 out=R/label;mode=label.removesuffix('_opt');r=json.loads((out/'RESULT.json').read_text());expected='PASS_ISOLATED_NATIVE109_ORIGINAL_WRITER_COLD_READ' if mode=='none' else 'WRITER_OUTCOME_UNKNOWN_INSPECT_NO_RETRY'
 if r['status']!=expected or r['lock_held_during_terminal'] is not True or r['monitor']['abort'] is not None:raise AssertionError(label)
 log=(R/(label+'.log')).read_text();last=json.loads(log.splitlines()[-1])
 if last.get('harness_pass') is not True:raise AssertionError(label)
 before=hashes(out)
 cmd=[sys.executable,'-B',str(H/'latest109_owner_v1/isolated_owner.py'),'--project','unused','--isolated','unused','--adapter-dir','unused','--input-wire','unused','--out',str(out)]
 completed=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
 if completed.returncode==0 or 'EXISTING_ATTEMPT_INSPECT_NO_RETRY' not in completed.stderr or before!=hashes(out):raise AssertionError('DUPLICATE:'+label)
 if mode!='none':
  objects=r['writer_reconciliation']['objects']
  for name,item in objects.items():
   if item['state']=='OBSERVED_NOT_ACCEPTED':
    path=out/'stock/parquet'/name
    if item['sha256']!=hashlib.sha256(path.read_bytes()).hexdigest() or item['bytes']!=path.stat().st_size:raise AssertionError('DIGEST:'+label)
  if mode=='second_object' and objects['row_metadata.parquet']['state']!='ABSENT':raise AssertionError(label)
  if mode=='receipt_before' and objects['RECEIPT.json']['state']!='ABSENT':raise AssertionError(label)
  if mode=='receipt_after' and objects['RECEIPT.json']['state']!='OBSERVED_NOT_ACCEPTED':raise AssertionError(label)
 reports.append({'case':label,'status':r['status'],'harness_pass':True,'duplicate_refused_unchanged':True,'terminal_lock_held':True,'native_calls':r.get('native_calls'),'input':r['input'],'output_hashes':before})
fd=os.open(R/'ISOLATED_OWNER.lock',os.O_RDWR|os.O_NOFOLLOW)
try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
finally:os.close(fd)
(R/'MATRIX.json').write_text(json.dumps({'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'production_allowed':False,'natural_acceptance':False,'lock_available_after_runs':True,'cases':reports,'limitations':['one historical stock only','checkpoint initialized from history, not production persisted prior','no repair/retry authorization inferred','no power loss/kill simulation','original output-parent lock domain unchanged']},indent=2));print('8 owner cases and no-overwrite duplicates verified')

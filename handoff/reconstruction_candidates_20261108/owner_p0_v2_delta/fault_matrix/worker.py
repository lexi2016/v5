"""Synthetic protocol worker; no original producer, live lock or genuine Parquet."""
import sys,pathlib,os,json,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import owner_candidate as o
root=pathlib.Path(sys.argv[1]);mode=sys.argv[2];out=root/'runs'/sys.argv[3]
o.COORDINATION_ROOT=root

def inner(project,isolated,adapter,wire,out,lock,fd,raw):
 out.mkdir();(out/'ENTERED').write_text('synthetic fault fixture')
 if mode=='hold':
  (out/'READY').write_text('ready')
  while not (root/'RELEASE').exists():time.sleep(.01)
 if mode=='crash_claim':os._exit(91)
 if mode=='partial_parquet':
  p=out/'stock'/'parquet';p.mkdir(parents=True)
  (p/'field_rows.parquet.partial').write_bytes(b'PAR1_SYNTHETIC_INCOMPLETE_NOT_REAL_PARQUET')
  os._exit(92)
 report={'status':'SYNTHETIC_PROTOCOL_ONLY','production_allowed':False}
 if mode=='crash_pre_link':
  def link(*a,**k):os._exit(93)
  o.os.link=link
 if mode=='crash_post_link':
  def unlink(*a,**k):os._exit(94)
  o.os.unlink=unlink
 if mode=='fault_dir_fsync':
  original=o.os.fsync
  def fsync(fd):
   import stat
   if stat.S_ISDIR(os.fstat(fd).st_mode):raise OSError('INJECTED_DIR_FSYNC')
   return original(fd)
  o.os.fsync=fsync
 o.seal_terminal(out/'RESULT.json',report,fd)
 return report
o._run_locked=inner
try:o.run(None,None,None,root.parent/'input.gz',out)
except Exception as e:
 print(type(e).__name__+':'+str(e),flush=True);sys.exit(20)

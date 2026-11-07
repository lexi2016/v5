"""Read-only 15:40 preflight bridge. Never dispatch/capture/compute/register commands."""
import argparse,ast,datetime,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=None;PINS_FILE=None;PINS_SHA=None;COORDINATOR=None;DATED_PREFLIGHT=None
def require(v,msg):
 if not v:raise ValueError(msg)
def verify():
 require(isinstance(ROOT,Path) and ROOT.is_absolute() and ROOT.is_dir() and not ROOT.is_symlink(),'NO_APPROVED_PRIVATE_BINDING')
 require(all(isinstance(x,str) and x for x in (PINS_FILE,PINS_SHA,COORDINATOR,DATED_PREFLIGHT)),'INCOMPLETE_PRIVATE_BINDING')
 def safe(name):
  relative=Path(name)
  require(not relative.is_absolute() and '..' not in relative.parts,'SOURCE_PATH')
  path=ROOT/relative
  require(path.resolve().is_relative_to(ROOT.resolve()) and not any((ROOT/Path(*relative.parts[:i])).is_symlink() for i in range(1,len(relative.parts)+1)),'SOURCE_PATH')
  return path
 raw=safe(PINS_FILE).read_bytes();require(hashlib.sha256(raw).hexdigest()==PINS_SHA,'STAGE_MANIFEST_DRIFT');refs=json.loads(raw)
 require(isinstance(refs,list) and refs,'EMPTY_STAGE_BINDING');seen=set()
 for pin in refs:
  require(isinstance(pin,dict),'STAGE_DESCRIPTOR')
  path,size,sha=(pin.get(k)for k in ('path','bytes','sha256'))
  require(isinstance(path,str) and path and path not in seen and type(size)is int and size>=0 and isinstance(sha,str),'STAGE_DESCRIPTOR');seen.add(path)
  data=safe(path).read_bytes();require(len(data)==size and hashlib.sha256(data).hexdigest()==sha,'STAGE_SOURCE_DRIFT')
 require(COORDINATOR in seen and DATED_PREFLIGHT in seen,'MISSING_EXECUTABLE_PIN')
 return refs
def inspect(date):
 require(type(date)is str and len(date)==8 and date.isascii()and date.isdigit(),'EXPLICIT_DATE_REQUIRED');datetime.datetime.strptime(date,'%Y%m%d');refs=verify()
 coordinator=ast.parse((ROOT/COORDINATOR).read_bytes());assigned=[n.value for n in coordinator.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='APPROVED'for t in n.targets)]
 require(len(assigned)==1 and ast.literal_eval(assigned[0])=={},'LIVE_DISPATCH_CHANGED_REVIEW_REQUIRED')
 argv=[sys.executable,'-B',str(ROOT/DATED_PREFLIGHT),'--target-date',date]
 p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,timeout=90)
 require(p.returncode==0,'DATED_PREFLIGHT_FAILED:'+p.stderr[-1000:]);result=json.loads(p.stdout);verify()
 return dict(schema='DAILY1540_PREFLIGHT_BRIDGE_V1',target_date=date,status='REUSE_COMPLETED_NO_DISPATCH'if result['result']['status']=='REUSE_COMPLETED_DATE_NO_COMPUTE'else 'BLOCKED_NO_DATED_EXECUTION_ADMISSION',schedule_slot=dict(zone='Asia/Shanghai',time='15:40',actually_registered_or_triggered=False),live_command_whitelist_entries=0,dated_preflight=result,reviewed_stage_refs=refs,source_capture_calls=0,owner_calls=0,formula_calls=0,native_calls=0,original_compute_locks_acquired=False,natural_run_verified=False,execution_permitted=False,remaining=['verified new-date calendar/source review and input manifest','original-lock same-attempt capture/prepare/owner execution binding','19-generation daily adoption and real prepare bridge','complete terminal/catalog/selector/projection receipts','natural 15:40 scheduler-to-business receipt'],note='Stage review linkage only, not new business admission; completed stocks reused; UNKNOWN never auto retried.')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target-date',required=True);a=p.parse_args();print(json.dumps(inspect(a.target_date),ensure_ascii=False,indent=2))

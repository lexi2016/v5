"""Date-strict read-only check. No current-day acceptance registry is authorized."""
import argparse,datetime as dt,hashlib,json,sys,threading,types
from pathlib import Path
from zoneinfo import ZoneInfo
HERE=Path(__file__).resolve().parent
V3=HERE.parent/'evening_nodes_candidate_v3_20261107'
LOCK=threading.RLock()
# New dated terminal adapters require a separately reviewed revision; no caller registration.
CURRENT_DAY_ADAPTERS={}
def check(target_date,now):
 day=dt.datetime.strptime(target_date,'%Y%m%d').date()
 if day.strftime('%Y%m%d')!=target_date or now.tzinfo is None:raise ValueError('TARGET_DATE_OR_TIMEZONE')
 if now.astimezone(ZoneInfo('Asia/Shanghai')).date()!=day:raise ValueError('TARGET_DATE_NOT_RUNTIME_DATE')
 pins=json.loads((HERE/'V3_PINS.json').read_bytes());raws={}
 for n,h in pins.items():
  p=V3/n
  if p.is_symlink() or p.parent.is_symlink():raise ValueError('PIN_SYMLINK')
  raw=p.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=h:raise ValueError('V3_CHANGED_REVIEW_REQUIRED')
  raws[n]=raw
 # Hold original module identities during reused code calls, restoring after read-only inspection.
 with LOCK:
  prior={name:sys.modules.get(name) for name in ('adapter','evening')}
  try:
   for name in ('adapter','evening'):
    m=types.ModuleType(name);m.__file__=str(V3/(name+'.py'));sys.modules[name]=m
    exec(compile(raws[name+'.py'],m.__file__,'exec'),m.__dict__)
   a=sys.modules['adapter'];e=sys.modules['evening']
   try:
    state=a.inspect();historical_date=state['merged']['data_date']
    observations=[{'stage':'registered_historical_display_merge','status':'COMPLETED','data_date':historical_date,'evidence_ref':state['pins']['merge_admission'],'facts':state}]
   except (OSError,ValueError,KeyError,TypeError) as error:
    historical_date='UNKNOWN'
    observations=[{'stage':'registered_historical_display_merge','status':'UNKNOWN','reason':type(error).__name__+':'+str(error)}]
   report=e.build('1700',target_date,now,observations)
   # A display-only receipt is never the new day's full terminal proof.
   return {'schema':'TARGET_DATE_TERMINAL_CHECK_V1','target_date':target_date,'target_day_status':'UNKNOWN','reason':'NO_APPROVED_TARGET_DAY_TERMINAL_ADAPTER','target_day_verified_refs':[],
    'historical_source_date':historical_date,'target_day_mapped_from_historical':False,'source_calls':0,'compute_calls':0,'report':report,'natural_verified':False,
    'guard_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'v3_pins':pins}
  finally:
   for name,old in prior.items():
    if old is None:sys.modules.pop(name,None)
    else:sys.modules[name]=old
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--target-date',required=True);args=p.parse_args()
 print(json.dumps(check(args.target_date,dt.datetime.now(dt.timezone.utc)),ensure_ascii=False,indent=2))

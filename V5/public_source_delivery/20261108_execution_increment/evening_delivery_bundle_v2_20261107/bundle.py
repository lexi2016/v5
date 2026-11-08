"""Prepare/check/export existing display results; never reselect or grant buy/freeze authority."""
import csv,datetime as dt,hashlib,io,json,os,re
from pathlib import Path
from zoneinfo import ZoneInfo
import safeio
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
GROUPS=('original','nav_smallk','nav_pullback','nav_breakout')
STATES=('TRUE','FALSE','UNKNOWN')
SAFEIO_SHA='facce7970f4919034d62e59dde8375e94d7a6a165de214f2e5178dbb5615fff5'
DATA={'path':'handoff/workbench_top200_auxiliary_service_v11_1_20261107/local/public/research-system/par-screen-data/9d1b65dc64e4b3ca3c08a114457a262f0743c7fc50affaffa82968ff990e710e.json','bytes':3183878,'sha256':'9d1b65dc64e4b3ca3c08a114457a262f0743c7fc50affaffa82968ff990e710e'}
ADMISSION={'path':'handoff/workbench_top200_auxiliary_service_v11_1_20261107/local/public/research-system/par-screen-data/merge407-admission.json','bytes':3376,'sha256':'e207d45d21d2f4cfae49b38a26a5640dfcbf36d11fe7a269fc1ca18af1106d1c'}
def canonical(x):return safeio.canonical(x)
def sha(x):return hashlib.sha256(x).hexdigest()
def cell(x):
 s=str(x)
 return "'"+s if s and s[0] in '=+-@\t\r\n' else s

def render(d):
 q=d['qualifications']
 if q.get('no_buy') is not True or q.get('production_allowed') is not False or q.get('research_display_allowed') is not True:raise ValueError('DISPLAY_ONLY_REQUIRED')
 for k in ('source_date','calculation_date','observation_date'):dt.datetime.strptime(d[k],'%Y%m%d')
 rows=d['rows'];symbols=[r['symbol'] for r in rows]
 if len(rows)!=d['scope_count'] or len(set(symbols))!=len(rows):raise ValueError('DENOMINATOR_DUPLICATE')
 if any(not re.fullmatch(r'\d{6}\.(SH|SZ|BJ)',s) for s in symbols):raise ValueError('SYMBOL')
 selected=[];pending=[];counts={g:{s:0 for s in STATES} for g in GROUPS}
 for r in rows:
  values=[r['layers'][g]['after_risk'] for g in GROUPS]
  if any(s not in STATES for s in values):raise ValueError('UNKNOWN_ENUM')
  for g,s in zip(GROUPS,values):counts[g][s]+=1
  if 'TRUE' in values:selected.append(r)
  if 'UNKNOWN' in values:pending.append(r)
 if len(selected)!=d['dedup_selected'] or len(pending)!=d['dedup_pending']:raise ValueError('DEDUP_COUNT')
 for g in GROUPS:
  if counts[g]!=d['counts'][g]['after_risk']:raise ValueError('GROUP_COUNT')
 def as_csv(items):
  out=io.StringIO(newline='');w=csv.writer(out,lineterminator='\n');w.writerow(['symbol','name','actual_date','source_family',*GROUPS,'source_date','calculation_date','inherited_observation_date','scope'])
  for r in items:w.writerow([cell(x) for x in [r['symbol'],r.get('name','UNKNOWN'),r.get('actual_date','UNKNOWN'),r.get('source_family','UNKNOWN'),*[r['layers'][g]['after_risk'] for g in GROUPS],d['source_date'],d['calculation_date'],d['observation_date'],'RESEARCH_DISPLAY_ONLY_NOT_BUY_NOT_FORMAL_FREEZE']])
  return out.getvalue().encode('utf-8-sig')
 summary={'schema':'EVENING_EXISTING_SELECTION_EXPORT_V1','source_date':d['source_date'],'calculation_date':d['calculation_date'],'inherited_observation_date':d['observation_date'],'denominator':len(rows),'selected':len(selected),'pending':len(pending),'group_counts':counts,'selected_pending_overlap':len({r['symbol'] for r in selected}&{r['symbol'] for r in pending}),'selection_executed':False,'formal_next_day_freeze':False,'buy_qualification':False,'production_allowed':False,'natural_verified':False,'delivery_status':'NOT_SENT','scope':'EXACT_EXISTING_AFTER_RISK_STATES_EXPORT_NO_NEW_RESEARCH_OR_SOURCE_ADMISSION'}
 text=('晚间待交付材料（既有结果导出，非新选股/正式次日冻结）\n'
       f"来源日期 {d['source_date']}；计算日期 {d['calculation_date']}；原件标注观察日期 {d['observation_date']}（仅沿用，未授予冻结资格）。\n"
       f"原分母 {len(rows)}；TRUE候选 {len(selected)}；含UNKNOWN {len(pending)}，可与候选重叠 {summary['selected_pending_overlap']}。\n"
       '人工图审/买入资格/当前日全链/自然触发/正式送达未由本程序验证；不执行交易。\n')
 return {'all_rows.csv':as_csv(rows),'selected.csv':as_csv(selected),'pending.csv':as_csv(pending),'summary.json':canonical(summary),'delivery.txt':text.encode()}

def load():
 if sha(safeio.local_bytes(HERE,'safeio.py'))!=SAFEIO_SHA:raise ValueError('SAFEIO_CHANGED')
 def checked(pin):
  raw=safeio.local_bytes(ROOT,pin['path'])
  if len(raw)!=pin['bytes'] or sha(raw)!=pin['sha256']:raise ValueError('INPUT_CHANGED')
  return json.loads(raw)
 ad=checked(ADMISSION);d=checked(DATA)
 if ad.get('status')!='PASS_RESEARCH_MERGE_DISPLAY_ONLY' or ad.get('production_allowed') is not False or ad.get('research_display_allowed') is not True:raise ValueError('ADMISSION_SCOPE')
 if [d['counts'][g]['after_risk']['TRUE'] for g in GROUPS]!=ad['group_true'] or d['dedup_selected']!=ad['dedup_selected'] or d['scope_count']!=ad['scope_count'] or d['dedup_pending']!=ad['dedup_pending']:raise ValueError('ADMISSION_COUNT')
 return render(d)

def expected_manifest(payloads):
 return {'schema':'EVENING_DELIVERY_BUNDLE_CANDIDATE_V1','input_refs':[DATA,ADMISSION],'code_sha256':sha(safeio.local_bytes(HERE,'bundle.py')),'safeio_sha256':SAFEIO_SHA,'files':{n:{'sha256':sha(v),'bytes':len(v)} for n,v in payloads.items()},'uploaded':False,'formal_freeze':False,'natural_verified':False,'sent':False}

def prepare():
 payloads=load()
 manifest=expected_manifest(payloads)
 raw=canonical(manifest);key=sha(raw);root=safeio.directory_fd(HERE/'frozen',create=True);child=None;reused=False
 try:
  try:os.mkdir(key,mode=0o700,dir_fd=root)
  except FileExistsError:reused=True
  child=os.open(key,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root)
  if not reused:
   for name,data in {**payloads,'manifest.json':raw}.items():safeio.write_at(child,name,data)
   os.fsync(child)
  # Re-read every byte, not only existence or source declarations.
  for name,data in {**payloads,'manifest.json':raw}.items():
   if safeio.read_at(child,name)!=data:raise ValueError('OUTPUT_CHANGED_OR_INCOMPLETE')
 finally:
  if child is not None:os.close(child)
  os.close(root)
 return check(key)|{'reused':reused}

def check(key):
 if not re.fullmatch('[a-f0-9]{64}',key):raise ValueError('PACKAGE_ID')
 root=HERE/'frozen'/key;raw=safeio.local_bytes(root,'manifest.json')
 if sha(raw)!=key:raise ValueError('MANIFEST_CHANGED')
 m=json.loads(raw);fresh=load()
 if raw!=canonical(expected_manifest(fresh)):raise ValueError('MANIFEST_SEMANTICS_OR_VERSION_CHANGED')
 if m['code_sha256']!=sha(safeio.local_bytes(HERE,'bundle.py')) or m['safeio_sha256']!=SAFEIO_SHA or m['input_refs']!=[DATA,ADMISSION]:raise ValueError('VERSION_CHANGED_REQUIRES_NEW_PACKAGE')
 if set(m['files'])!=set(fresh):raise ValueError('FILE_SET')
 for name,expected in fresh.items():
  actual=safeio.local_bytes(root,name)
  if actual!=expected or m['files'][name]!={'sha256':sha(actual),'bytes':len(actual)}:raise ValueError('PACKAGE_FILE_CHANGED')
 return {'package_id':key,'path':str(root),'byte_readback':'PASS','current_input_bytes':'PASS','source_date':json.loads(fresh['summary.json'])['source_date'],'business_acceptance':'NOT_GRANTED','delivery_status':'NOT_SENT','natural_verified':False,'job_execution':False,'upload_status':'NOT_UPLOADED_BY_THIS_TOOL'}

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=('1830','1850','1900'),required=True);p.add_argument('--package');a=p.parse_args()
 if a.stage=='1830':result=prepare()
 else:
  if not a.package:p.error('--package required for checking the same existing package')
  result=check(a.package)
 now=dt.datetime.now(dt.timezone.utc)
 result.update(stage=a.stage,observed_at=now.isoformat(),local_date=now.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat(),trigger_source='MANUAL_TEST',scope='1830_PREPARE_1850_RECHECK_1900_LOCAL_DELIVERY_TEXT_ONLY')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

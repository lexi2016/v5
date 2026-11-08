"""08:50 research preparation: annotate existing Top200, never select or activate."""
import csv,datetime as dt,hashlib,io,json,os
from pathlib import Path
import safeio
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PINS=[('handoff/nov6_top200_projection_v1_20261106/run_20261106_once/TOP200.json','4da0ec74e5af75f57151a6f7403d23d3b1f800b7320a49bbd6c6a6e5dd43645e'),('handoff/workbench_top200_auxiliary_service_v11_1_20261107/local/public/research-system/par-screen-data/9d1b65dc64e4b3ca3c08a114457a262f0743c7fc50affaffa82968ff990e710e.json','9d1b65dc64e4b3ca3c08a114457a262f0743c7fc50affaffa82968ff990e710e')]
GROUPS=('original','nav_smallk','nav_pullback','nav_breakout')
def sha(b):return hashlib.sha256(b).hexdigest()
def cell(v):
 s=str(v);return "'"+s if s[:1] in ('=','+','-','@','\t','\r','\n') else s

def annotate(top,selection):
 if top['schema']!='NOV6_FIXED_REFERENCE_TOP200_V1' or selection['schema']!='PAR_SCREEN_DISPLAY_V1':raise ValueError('SCHEMA')
 if str(top['source_date'])!=selection['source_date'] or top['scope_count']!=selection['scope_count'] or top['scope_count']!=5575:raise ValueError('DATE_SCOPE')
 rows=top['rows'];by={r['symbol']:r for r in selection['rows']}
 if len(by)!=len(selection['rows']) or len(by)!=5575 or len(rows)!=200 or len({r['symbol'] for r in rows})!=200 or [r['rank'] for r in rows]!=list(range(1,201)):raise ValueError('IDENTITY_OR_RANK')
 result=[]
 for r in rows:
  s=by[r['symbol']];states=[s['layers'][g]['after_risk'] for g in GROUPS]
  if any(x not in ('TRUE','FALSE','UNKNOWN') for x in states):raise ValueError('STATE')
  result.append({'rank':r['rank'],'symbol':r['symbol'],'name':s['name'],'name_date_semantics':'PRESERVED_OLD_DISPLAY_NAME_NOT_REFRESHED','change_pct':r['change_pct_display'],'rank_actual_date':r['actual_date'],'selection_actual_date':s['actual_date'],'owner_outcome':s['owner_outcome'],'source_family':s['source_family'],'groups':dict(zip(GROUPS,states)),'existing_selected':any(x=='TRUE' for x in states),'has_unknown':any(x=='UNKNOWN' for x in states),'manual_chart_review':'UNKNOWN','no_buy':True})
 return result

def main():
 if sha(safeio.local_bytes(HERE,'safeio.py'))!='facce7970f4919034d62e59dde8375e94d7a6a165de214f2e5178dbb5615fff5':raise ValueError('SAFEIO')
 data=[]
 for p,h in PINS:
  raw=safeio.local_bytes(ROOT,p)
  if sha(raw)!=h:raise ValueError('INPUT_CHANGED')
  data.append(json.loads(raw))
 rows=annotate(*data);stream=io.StringIO(newline='');w=csv.writer(stream,lineterminator='\n');w.writerow(['原Top200名次','代码','旧展示名称','原涨幅%','排名行情日','选股行日期','来源','消费状态',*GROUPS,'既有四组任一TRUE','含UNKNOWN','人工图审','研究用途非买入资格'])
 for r in rows:w.writerow([cell(v) for v in [r['rank'],r['symbol'],r['name'],r['change_pct'],r['rank_actual_date'],r['selection_actual_date'],r['source_family'],r['owner_outcome'],*[r['groups'][g] for g in GROUPS],r['existing_selected'],r['has_unknown'],'UNKNOWN','NO_BUY']])
 csv_bytes=stream.getvalue().encode('utf-8-sig')
 report={'schema':'PREOPEN_TOP200_ORIGINAL_GROUP_ANNOTATION_V1','source_date':data[1]['source_date'],'denominator':5575,'top_rows':len(rows),'selected_overlap':sum(r['existing_selected'] for r in rows),'unknown_overlap':sum(r['has_unknown'] for r in rows),'rows':rows,'input_refs':[list(pin) for pin in PINS],'code_sha256':sha(safeio.local_bytes(HERE,'prepare.py')),'csv_sha256':sha(csv_bytes),'csv_bytes':len(csv_bytes),'scope':'READ_ONLY_EXISTING_RESULTS_JOIN_NOT_SELECTION_OR_MONITOR_LIST','business_accepted':False,'monitor_list_frozen':False,'buy_qualification':False,'natural_verified':False,'new_source_calls':0,'formula_calls':0,'trigger_source':'MANUAL_TEST'}
 report['identity']=sha(safeio.canonical(report));report['observed_at']=dt.datetime.now(dt.timezone.utc).isoformat();receipt=safeio.freeze(HERE/'frozen',report);folder=Path(receipt['path']).parent;fd=safeio.directory_fd(folder)
 try:
  try:safeio.write_at(fd,'TOP200_GROUP_REVIEW.csv',csv_bytes)
  except FileExistsError:pass
  if safeio.read_at(fd,'TOP200_GROUP_REVIEW.csv')!=csv_bytes:raise ValueError('CSV_READBACK')
 finally:os.close(fd)
 print(json.dumps({'receipt':receipt,'csv_path':str(folder/'TOP200_GROUP_REVIEW.csv'),'csv_readback':'PASS','source_date':report['source_date'],'top_rows':200,'selected_overlap':report['selected_overlap'],'unknown_overlap':report['unknown_overlap'],'natural_verified':False},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

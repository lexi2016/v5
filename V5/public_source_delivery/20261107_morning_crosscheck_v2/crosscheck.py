"""06:30 crosscheck substep: actual per-row dates/source/owner consistency, not semantic approval."""
import collections,datetime as dt,hashlib,json,re,sys
from pathlib import Path
from zoneinfo import ZoneInfo
import safeio
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
GROUPS=('original','nav_smallk','nav_pullback','nav_breakout');STATES=('TRUE','FALSE','UNKNOWN')
SAFEIO_SHA='facce7970f4919034d62e59dde8375e94d7a6a165de214f2e5178dbb5615fff5'
DATA_PATH=None;DATA_SHA=None;DATA_BYTES=None

AD_PATH=None;AD_SHA=None;AD_BYTES=None
def sha(b):return hashlib.sha256(b).hexdigest()
def date(v):
 if not isinstance(v,str) or not re.fullmatch('[0-9]{8}',v):raise ValueError('DATE_SHAPE')
 return dt.datetime.strptime(v,'%Y%m%d').date()
def audit(data,target_date):
 if not isinstance(data,dict) or data.get('schema')!='PAR_SCREEN_DISPLAY_V1':raise ValueError('DISPLAY_SCHEMA_REQUIRED')
 target=date(target_date);source=date(data['source_date']);errors=[];rows=data['rows']
 if source>target:errors.append('SOURCE_AFTER_TARGET')
 counts={g:{s:0 for s in STATES} for g in GROUPS};owners=collections.Counter();families=collections.Counter();dates=collections.Counter();selected=set();pending=set();symbols=set()
 queues={k:[] for k in ('stale_or_missing_date','not_consumed','no_new_bar','unknown_source','unknown_groups')}
 for r in rows:
  symbol=r['symbol'];owner=r['owner_outcome'];family=r.get('source_family','UNKNOWN');actual=r.get('actual_date');owner_known=owner in ('COMPUTED_CURRENT','SOURCE_BLOCKED','RETAINED_NO_BAR')
  if not isinstance(symbol,str) or not re.fullmatch(r'\d{6}\.(SZ|SH|BJ)',symbol):errors.append('SYMBOL_INVALID')
  if symbol in symbols:errors.append('DUPLICATE:'+str(symbol))
  symbols.add(symbol);owners[owner]+=1;families[family]+=1;dates[str(actual)]+=1
  if not owner_known:errors.append('OWNER_UNKNOWN:'+symbol)
  try:actual_date=date(actual)
  except (ValueError,TypeError):actual_date=None
  if actual_date and actual_date>source:errors.append('ROW_AFTER_SOURCE:'+symbol)
  if owner=='COMPUTED_CURRENT' and actual_date!=source:errors.append('COMPUTED_CURRENT_DATE_MISMATCH:'+symbol)
  if owner=='COMPUTED_CURRENT' and family=='UNKNOWN':errors.append('COMPUTED_CURRENT_SOURCE_UNKNOWN:'+symbol)
  states={g:r['layers'][g]['after_risk'] for g in GROUPS};unknown=[]
  for g,s in states.items():
   if s not in STATES:errors.append('STATE_INVALID:'+symbol+':'+g);continue
   counts[g][s]+=1
   if s=='TRUE':selected.add(symbol)
   elif s=='UNKNOWN':pending.add(symbol);unknown.append(g)
  item={'symbol':symbol,'actual_date':actual,'source_family':family,'owner_outcome':owner,'unknown_groups':unknown,'original_reasons':r.get('reasons',[]),'next_action':'REVIEW_ORIGINAL_OWNER_AND_SOURCE_RECEIPTS_NO_AUTO_RETRY'}
  if actual_date!=source:queues['stale_or_missing_date'].append(item)
  if owner=='SOURCE_BLOCKED':queues['not_consumed'].append(item)
  if owner=='RETAINED_NO_BAR':queues['no_new_bar'].append(item)
  if family=='UNKNOWN':queues['unknown_source'].append(item)
  if unknown:queues['unknown_groups'].append(item)
 if len(rows)!=data['scope_count']:errors.append('DENOMINATOR_MISMATCH')
 if dict(owners)!={k:v for k,v in data['partitions'].items() if v}:errors.append('OWNER_PARTITION_MISMATCH')
 for g in GROUPS:
  if counts[g]!=data['counts'][g]['after_risk']:errors.append('GROUP_COUNT_MISMATCH:'+g)
 if len(selected)!=data['dedup_selected']:errors.append('SELECTED_COUNT_MISMATCH')
 if len(pending)!=data['dedup_pending']:errors.append('PENDING_COUNT_MISMATCH')
 return {'schema':'MORNING_SOURCE_CROSSCHECK_CANDIDATE_V1','target_date':target_date,'source_date':data['source_date'],'status':'FAILED_CONSISTENCY' if errors else 'CONSISTENT_WITH_DISCLOSED_GAPS','errors':errors,'denominator':len(rows),'source_date_census':dict(sorted(dates.items())),'source_family_census':dict(sorted(families.items())),'owner_partitions':dict(sorted(owners.items())),'group_counts':counts,'selected_count':len(selected),'pending_count':len(pending),'selected_pending_overlap':len(selected&pending),'queues':queues,'target_day_complete':False,'source_admission':False,'selection_admission':False,'semantic_crosscheck':'NOT_IMPLEMENTED_BY_THIS_CHECK','formal_freeze':False,'natural_verified':False,'business_accepted':False,'source_calls':0,'selector_calls':0,'jobs_started':0,'scope':'PINNED_SNAPSHOT_ROW_DATE_SOURCE_OWNER_STATE_CONSISTENCY_ONLY'}
def load():
 if sha(safeio.local_bytes(HERE,'safeio.py'))!=SAFEIO_SHA:raise ValueError('SAFEIO_CHANGED')
 if any(v is None for v in (DATA_PATH,DATA_SHA,DATA_BYTES,AD_PATH,AD_SHA,AD_BYTES)):raise ValueError('PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING')
 raw=safeio.local_bytes(ROOT,DATA_PATH);ad_raw=safeio.local_bytes(ROOT,AD_PATH)
 if sha(raw)!=DATA_SHA or len(raw)!=DATA_BYTES or sha(ad_raw)!=AD_SHA or len(ad_raw)!=AD_BYTES:raise ValueError('INPUT_PIN_CHANGED')
 ad=json.loads(ad_raw)
 if ad.get('status')!='PASS_RESEARCH_MERGE_DISPLAY_ONLY' or ad.get('production_allowed') is not False or ad.get('research_display_allowed') is not True:raise ValueError('DISPLAY_SCOPE')
 return json.loads(raw)
def main():
 # The production-style CLI has no alternate input path or bypass argument.
 # All data enters through load()'s exact source/admission/code pins.
 try:
  now=dt.datetime.now(dt.timezone.utc);target=now.astimezone(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d');r=audit(load(),target)
  if r['status']!='CONSISTENT_WITH_DISCLOSED_GAPS':
   print(json.dumps({'status':'FAILED_CONSISTENCY','errors':r['errors'],'target_date':target,'source_date':r['source_date'],'saved_success_receipt':False,'business_accepted':False,'natural_verified':False,'trigger_source':'MANUAL_TEST'},ensure_ascii=False,indent=2))
   return 2
  r.update(code_sha256=sha(safeio.local_bytes(HERE,'crosscheck.py')),safeio_sha256=SAFEIO_SHA,input_refs=[{'path':DATA_PATH,'sha256':DATA_SHA},{'path':AD_PATH,'sha256':AD_SHA}],trigger_source='MANUAL_TEST')
  r['identity']=sha(safeio.canonical(r));r['observed_at']=now.isoformat();saved=safeio.freeze(HERE/'frozen',r)
  if saved.get('byte_readback')!='PASS' or saved.get('business_accepted') is not False:raise ValueError('FREEZE_RECEIPT_INVALID')
  print(json.dumps({'saved':saved,'status':r['status'],'source_date':r['source_date'],'target_date':target,'queue_counts':{k:len(v) for k,v in r['queues'].items()},'natural_verified':False,'exit_zero_scope':'PINNED_SNAPSHOT_CONSISTENCY_AND_LOCAL_READBACK_ONLY_NOT_BUSINESS_ACCEPTANCE'},ensure_ascii=False,indent=2))
  return 0
 except (ValueError,TypeError,KeyError,OSError) as e:
  print(json.dumps({'status':'BLOCKED_OR_FAILED','error_type':type(e).__name__,'error':str(e),'saved_success_receipt':False,'business_accepted':False,'natural_verified':False,'trigger_source':'MANUAL_TEST'},ensure_ascii=False,indent=2))
  return 3
if __name__=='__main__':sys.exit(main())

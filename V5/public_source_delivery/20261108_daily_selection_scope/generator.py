"""New offline candidate identity, NOT the recovered historical generation algorithm.
No production verifier adapter exists. No contract, lock, activation or capture writes.
"""
import datetime
import hashlib
import json
import re
GROUPS=('original','nav_breakout','nav_pullback','nav_smallk')
ALGORITHM='DAILY_SELECTION_SCOPE_CANDIDATE_V1'
def need(x,reason):
    if not x:raise ValueError(reason)
def sha(x):return hashlib.sha256(x).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def pairs(ps):
    d={}
    for k,v in ps:
        need(k not in d,'DUPLICATE_JSON_KEY');d[k]=v
    return d
def date(x):
    need(type(x)is int and re.fullmatch('[0-9]{8}',str(x)) is not None,'DATE')
    return datetime.datetime.strptime(str(x),'%Y%m%d').date()
def production_verifier(*args):
    raise ValueError('BLOCKED_NO_REVIEWED_FREEZE_SOURCE_CALENDAR_ADAPTER')
def build(selection_bytes,calendar_bytes,source_date,observation_date,verify=production_verifier):
    # verify must independently inspect bound freeze/review/calendar artifacts;
    # testing injects a synthetic verifier, never a production registration.
    need(type(selection_bytes)is bytes and type(calendar_bytes)is bytes,'MISSING_INPUT_BYTES')
    need(date(source_date)<date(observation_date),'DATE_ORDER')
    refs=verify(sha(selection_bytes),sha(calendar_bytes),source_date,observation_date)
    need(type(refs)is dict,'MISSING_VERIFIED_CONTEXT')
    for role in ('freeze','source_review','calendar_review'):
        r=refs.get(role)
        need(type(r)is dict and type(r.get('path'))is str and bool(r['path'])
             and type(r.get('sha256'))is str and re.fullmatch('[a-f0-9]{64}',r['sha256']),'MISSING_'+role)
    cal=json.loads(calendar_bytes,object_pairs_hook=pairs)
    need(type(cal)is dict and type(cal.get('trading_days'))is list,'CALENDAR_SCHEMA')
    days=cal['trading_days'];[date(x) for x in days]
    need(days==sorted(set(days)),'CALENDAR_ORDER_DUPLICATE')
    need(observation_date in days and days.index(observation_date)>0,'CALENDAR_COVERAGE')
    need(days[days.index(observation_date)-1]==source_date,'PREVIOUS_TRADING_DAY')
    rows=[];seen=set();selected=[]
    for i,line in enumerate(selection_bytes.splitlines(),1):
        need(bool(line.strip()),'EMPTY_ROW')
        r=json.loads(line,object_pairs_hook=pairs);need(type(r)is dict,'ROW_SCHEMA')
        s=r.get('symbol');need(type(s)is str and re.fullmatch('[0-9]{6}\\.(SH|SZ|BJ)',s),'IDENTITY')
        need(s not in seen,'DUPLICATE_SYMBOL_ROW');seen.add(s)
        need(type(r.get('source_date'))is int and r['source_date']==source_date and
             type(r.get('observation_date'))is int and r['observation_date']==observation_date,'ROW_DATE')
        gs=r.get('selected_groups');need(type(gs)is list and all(type(g)is str and g in GROUPS for g in gs),'GROUP_SCHEMA')
        need(len(gs)==len(set(gs)),'DUPLICATE_GROUP')
        # Keep original membership and row-byte hash, never re-evaluate formulas.
        if gs:selected.append({'symbol':s,'selected_groups':gs,'source_line':i,'source_row_sha256':sha(line)})
        rows.append(r)
    need(bool(rows),'EMPTY_SOURCE')
    result={'algorithm':ALGORITHM,'status':'CANDIDATE_ONLY_SCOPE_MAPPING_UNKNOWN','source_date':source_date,
      'observation_date':observation_date,'source_sha256':sha(selection_bytes),'calendar_sha256':sha(calendar_bytes),
      'source_row_count':len(rows),'dedup_selected_count':len(selected),'group_counts':{g:sum(g in r['selected_groups'] for r in selected) for g in GROUPS},
      'selected':selected,'review_refs':refs,'scope_to_intraday_mapping':'UNKNOWN','approved_for_capture':False,
      'production_allowed':False,'original_generation_recovered':False,
      'blockers':['CURRENT_SCOPE_MAPPING_NOT_VERIFIED','ORIGINAL_CONTRACT_LOCK_SOURCE_GATES_NOT_BOUND']}
    result['candidate_sha256']=sha(canon(result))
    return result

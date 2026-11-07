"""Bounded ordinary-quote raw archive. Python stdlib; no strategy/production admission."""
import argparse, csv, datetime as dt, hashlib, io, json, os, pathlib, re, time
import urllib.request, urllib.error, signal, fcntl
from decimal import Decimal
from zoneinfo import ZoneInfo
P=pathlib.Path(__file__).resolve().parent
PROJECT=P.parents[1]
TZ={'A':ZoneInfo('Asia/Shanghai'),'HK':ZoneInfo('Asia/Hong_Kong')}
SLOTS={'0900':('09:00:00','09:02:00'),'0915':('09:15:00','09:17:00'),
       '0925':('09:25:05','09:30:00'),'0930':('09:30:00','09:32:00')}
ENDPOINT='https://qt.gtimg.cn/q='
SOURCE_ID='tencent_ordinary_v1'
MAX_BYTES=4*1024*1024

def sha(b):return hashlib.sha256(b).hexdigest()
def now():return dt.datetime.now(dt.timezone.utc)
def safe(root,relative):
 root=pathlib.Path(root).resolve();p=(root/relative).resolve()
 if not p.is_relative_to(root):raise ValueError('PATH_OUTSIDE_ROOT')
 return p

def atomic(path,data):
 """Durable replace, with no writes through a symlink target."""
 path=pathlib.Path(path)
 if path.is_symlink():raise ValueError('SYMLINK_WRITE')
 path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_name(path.name+'.tmp-'+str(os.getpid()))
 with open(tmp,'xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
 fd=os.open(path.parent,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def save(path,obj):atomic(path,(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode())
def read(path):return json.loads(pathlib.Path(path).read_text())
def canonical(root,c,slot):
 if c['market'] not in TZ or slot not in SLOTS:raise ValueError('MARKET_OR_SLOT')
 dt.date.fromisoformat(c['date'])
 if c.get('source_id',SOURCE_ID)!=SOURCE_ID:raise ValueError('SOURCE_ID_NOT_APPROVED')
 if not re.fullmatch('[0-9a-f]{64}',c['scope_sha256']):raise ValueError('SCOPE_HASH')
 return safe(root,f"{c['date']}/{c['market']}/{slot}/{SOURCE_ID}/{c['scope_sha256']}")
def deadline_seconds(t):
 local=t.astimezone(TZ['A'])
 return max(0,(dt.datetime.combine(local.date(),dt.time(9,35),TZ['A'])-local).total_seconds())

def window_state(t,slot):
 if t.tzinfo is None:raise ValueError('NAIVE_CLOCK')
 t=t.astimezone(TZ['A']);start,end=[dt.datetime.combine(t.date(),dt.time.fromisoformat(s),TZ['A']) for s in SLOTS[slot]]
 if t<start:return 'EARLY'
 if t>=end:return 'MISSED'
 return 'LATE' if (t-start).total_seconds()>30 else 'ON_TIME'
def calendar_state(date,cal):
 compact=dt.date.fromisoformat(date).strftime('%Y%m%d')
 if not cal['coverage_start']<=compact<=cal['coverage_end']:raise ValueError('CALENDAR_OUT_OF_RANGE')
 if compact in cal.get('closed_dates',[]) or compact in cal.get('extraordinary_closure_dates',[]):return 'CLOSED_NO_CAPTURE'
 if compact not in cal['open_dates']:raise ValueError('CALENDAR_DAY_UNKNOWN')
 return 'REGULAR_OPEN_EXTRAORDINARY_UNKNOWN'

def parse(raw,market,keys,slot,received):
 """Retain original fields. Never convert HK source quantity using an A lot multiplier."""
 decode_error=None
 try:text=raw.decode('gb18030')
 except UnicodeDecodeError as e:text=raw.decode('gb18030',errors='replace');decode_error=str(e)
 pairs=re.findall(r'v_(\w+)="([^"\r\n]*)";',text)
 found={};duplicates=set()
 for key,body in pairs:
  if key in found:duplicates.add(key)
  found[key]=body.split('~')
 extra=sorted(set(found)-set(keys));out=[]
 for key in keys:
  v=found.get(key,[])
  row={'key':key,'market':market,'status':'UNKNOWN','raw_fields':v,'source_time_raw':v[30] if len(v)>30 else None,
       'classification':'UNKNOWN','auction_execution_verified':False,'volume_screen_eligible':False,
       'current_connect_eligibility':'UNKNOWN','current_suspension_status':'UNKNOWN','currency':'CNY' if market=='A' else 'UNKNOWN',
       'volume_unit':'SOURCE_NATIVE_UNCERTIFIED_NO_MULTIPLIER','amount_unit':'CNY_PROVISIONAL_CROSSCHECK' if market=='A' else 'HKD_PROVISIONAL',
       'source_timestamp_kind':'VENDOR_UPDATE_NOT_LAST_TRADE','source_timezone_basis':'EXISTING_A_ADAPTER' if market=='A' else 'ASIA_HONG_KONG_ASSUMED_PROVISIONAL',
       'layout_basis':'EXISTING_A_SNAPSHOT' if market=='A' else 'D23_663_ROWS_AUDITED_78_FIELDS_PROVISIONAL',
       'received_at':received.isoformat(),'extra_identities':extra}
  try:
   if decode_error:raise ValueError('DECODE_ERROR '+decode_error)
   if duplicates:raise ValueError('DUPLICATE_IDENTITY_WHOLE_RESPONSE')
   if extra:raise ValueError('UNEXPECTED_IDENTITIES')
   if not v:raise ValueError('MISSING_IDENTITY')
   if (market=='HK' and len(v)!=78) or (market=='A' and len(v)<=57):raise ValueError('SCHEMA_LENGTH')
   if v[2]!=key[2:]:raise ValueError('WRONG_IDENTITY')
   if market=='HK' and v[75]!='HKD':raise ValueError('HK_CURRENCY_SCHEMA')
   row.update(price_source=v[3],open_source=v[5],volume_source=v[6],volume_crosscheck_source=v[36],
              amount_source=v[35].split('/')[2] if market=='A' else v[37],currency='CNY' if market=='A' else v[75])
   nums=[Decimal(row[k]) for k in ('price_source','open_source','volume_source','volume_crosscheck_source','amount_source')]
   if not all(x.is_finite() for x in nums):raise ValueError('NONFINITE')
   if min(nums)<=0:raise ValueError('ZERO_OR_NEGATIVE_UNCONFIRMED_EXECUTION')
   if nums[2]!=nums[3]:raise ValueError('VOLUME_FIELDS_DISAGREE')
   low,high=Decimal(v[34]),Decimal(v[33])
   if not low.is_finite() or not high.is_finite() or not 0<low<=min(nums[:2])<=max(nums[:2])<=high:raise ValueError('PRICE_RANGE_INVALID')
   if market=='A' and abs(nums[4]-Decimal(v[57])*10000)>1:raise ValueError('AMOUNT_FIELDS_DISAGREE')
   fmt='%Y%m%d%H%M%S' if market=='A' else '%Y/%m/%d %H:%M:%S'
   source=dt.datetime.strptime(v[30],fmt).replace(tzinfo=TZ[market]);local=received.astimezone(TZ[market]);delay=(local-source).total_seconds()
   row.update(source_time=source.isoformat(),delay_seconds=delay)
   if source.date()!=local.date() or not 0<=delay<=120:raise ValueError('STALE_OR_FUTURE')
   # Stage-specific timestamp guard; source updates do not prove an execution type.
   start=dt.time.fromisoformat(SLOTS[slot][0]);end=dt.time.fromisoformat(SLOTS[slot][1])
   if slot=='0925':start=dt.time(9,25) if market=='A' else dt.time(9,22)
   if not start<=source.time()<end:raise ValueError('SOURCE_OUTSIDE_PHASE')
   if window_state(received,slot)=='MISSED':raise ValueError('RECEIVED_AFTER_PHASE_END')
   row['status']='VALID_CURRENT_RAW'
   row['classification']=('AUCTION_POST_MATCH_CUMULATIVE_CANDIDATE' if market=='A' else 'POST_MATCH_SESSION_CUMULATIVE') if slot=='0925' else ('CONTINUOUS_SESSION_CUMULATIVE' if slot=='0930' else 'PREMATCH_SNAPSHOT_NOT_EXECUTED_AUCTION')
  except Exception as e:row['error']=str(e)
  out.append(row)
 return out

def lookup(root,c,slot):
 d=canonical(root,c,slot);receipt=d/'receipt.json';attempt=d/'attempt.json'
 if receipt.exists():
  rec=read(receipt)
  if rec.get('raw_sha256'):
   raw=d/'quotes.raw'
   if not raw.exists() or sha(raw.read_bytes())!=rec['raw_sha256']:return {'status':'RAW_HASH_MISMATCH','action':'DO_NOT_FETCH_ALERT','directory':str(d),'alert':True}
   return dict(rec,action='REUSE_RAW_NO_FETCH_ANALYSIS_PENDING')
  return dict(rec,action='DO_NOT_FETCH_PRIOR_ATTEMPT')
 if (d/'raw_receipt.json').exists():
  rec=read(d/'raw_receipt.json');raw=d/'quotes.raw'
  if raw.exists() and sha(raw.read_bytes())==rec.get('raw_sha256'):return dict(rec,status='RAW_SAVED_PARSE_PENDING',action='REUSE_RAW_NO_FETCH_ANALYSIS_PENDING',alert=True)
  return {'status':'RAW_HASH_MISMATCH','action':'DO_NOT_FETCH_ALERT','directory':str(d),'alert':True}
 if attempt.exists():return {'status':'INTERRUPTED_UNKNOWN_NO_RETRY','action':'DO_NOT_FETCH_ALERT','directory':str(d),'alert':True}
 return {'status':'ABSENT','action':'NO_CANONICAL_RECEIPT','directory':str(d)}

def monitor_bridge(root,c):
 result=lookup(root,c,'0930')
 return {'allow_fetch':False,'analysis_admission':'NOT_GRANTED','purpose':'09:30_CANONICAL_RAW_REUSE_ONLY','lookup':result,
         'message':'raw已保存，分析待准入' if result.get('action')=='REUSE_RAW_NO_FETCH_ANALYSIS_PENDING' else '开盘runner独占09:30，禁止旧fetch；等待或报告缺口'}

def http_fetch(keys):
 if not keys or len(keys)>666 or len(set(keys))!=len(keys) or any(not re.fullmatch(r'(?:sh|sz)\d{6}|hk\d{5}',x) for x in keys):raise ValueError('REQUEST_SCOPE')
 req=urllib.request.Request(ENDPOINT+','.join(keys),headers={'User-Agent':'Mozilla/5.0'})
 # Explicitly prohibit redirects; do not discover or switch alternate endpoints.
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args,**kwargs):raise ValueError('REDIRECT_NOT_ALLOWED')
 opener=urllib.request.build_opener(NoRedirect)
 with opener.open(req,timeout=15) as response:
  if response.status!=200:raise ValueError('HTTP_STATUS_'+str(response.status))
  raw=response.read(MAX_BYTES+1)
  if len(raw)>MAX_BYTES:raise ValueError('RESPONSE_LIMIT')
  return raw

def capture(root,c,slot,clock=now,fetch=http_fetch):
 d=canonical(root,c,slot);prior=lookup(root,c,slot)
 if prior['status']!='ABSENT':return prior
 start=clock();state=window_state(start,slot)
 rec={'date':c['date'],'market':c['market'],'slot':slot,'scope_sha256':c['scope_sha256'],
      'directory':str(d),'start_utc':start.isoformat(),'status':state,'timing_status':state,
      'source_id':SOURCE_ID,'purpose':'RAW_OBSERVATION_ONLY','analysis_admission':'NOT_GRANTED','alert':False,'request_count':0,
      'expected_count':len(c['keys']),'contract_sha256':sha(json.dumps(c,sort_keys=True).encode()),
      'runner_sha256':sha((P/'runner.py').read_bytes()),'policy_sha256':c.get('policy_sha256'),
      'calendar_sha256':c.get('calendar_sha256'),'scope_vintage':c.get('scope_vintage'),'carry_forward':c.get('carry_forward'),
      'extraordinary_closure_status':c.get('extraordinary_closure_status','UNKNOWN')}
 if start.astimezone(TZ[c['market']]).date().isoformat()!=c['date']:return dict(rec,status='DATE_MISMATCH',alert=True)
 if state=='EARLY':return rec
 d.mkdir(parents=True,exist_ok=True)
 try:
  with open(d/'attempt.json','x') as f:json.dump(rec,f);f.flush();os.fsync(f.fileno())
 except FileExistsError:return lookup(root,c,slot)
 # fsync directory after exclusive attempt: survives interruption before request.
 fd=os.open(d,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
 if state=='MISSED':rec.update(alert=True);save(d/'receipt.json',rec);return rec
 try:
  rec.update(request_count=1,url=ENDPOINT+','.join(c['keys']))
  raw=fetch(c['keys']);end=clock()
  atomic(d/'quotes.raw',raw)
  rec.update(end_utc=end.isoformat(),raw_sha256=sha(raw),raw_bytes=len(raw))
  # Durable raw receipt precedes parsing too, enabling read-only recovery.
  save(d/'raw_receipt.json',rec)
  rows=parse(raw,c['market'],c['keys'],slot,end)
  save(d/'rows.json',rows)
  valid=sum(x['status']=='VALID_CURRENT_RAW' for x in rows)
  rec.update(status='RAW_SAVED' if valid==len(rows) else 'RAW_SAVED_WITH_UNKNOWN',valid_current_count=valid,unknown_count=len(rows)-valid,alert=valid!=len(rows))
 except Exception as e:
  rec.update(status='PARSE_ERROR_RAW_RETAINED' if (d/'quotes.raw').exists() else 'FETCH_ERROR_NO_RETRY',error=repr(e),alert=True)
  if isinstance(e,PermissionError) or any(s in str(e).lower() for s in ('blocked by policy','permission denied','403','451','review_denied')):
   rec['security_stop']=True
 save(d/'receipt.json',rec)
 return rec


def pinned(root,binding):
 p=safe(root,binding['path']);b=p.read_bytes()
 if sha(b)!=binding['sha256']:raise ValueError('SOURCE_HASH_MISMATCH '+str(p))
 return b

def prepare(date,policy):
 contracts=[]
 for market in ('A','HK'):
  item=policy['markets'][market]
  if policy.get('source_id')!=SOURCE_ID:raise ValueError('POLICY_SOURCE_ID')
  if not policy['coverage_start']<=date<=policy['coverage_end']:raise ValueError('POLICY_DATE_OUT_OF_RANGE')
  raw=pinned(PROJECT,item['scope']);cal=json.loads(pinned(PROJECT,item['calendar']))
  for evidence in item.get('evidence_pins',[]):pinned(PROJECT,evidence)
  state=calendar_state(date,cal)
  if market=='A':keys=[x['symbol'].split('.')[1].lower()+x['symbol'].split('.')[0] for x in json.loads(raw)['stocks']]
  else:
   rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
   if any(x['security_type']!='股票' for x in rows):raise ValueError('NON_STOCK_HK_SCOPE')
   keys=['hk'+x['code'] for x in rows]
  if len(keys)!=item['count'] or len(set(keys))!=len(keys):raise ValueError('SCOPE_COUNT_OR_DUPLICATE')
  contracts.append({'source_id':SOURCE_ID,'policy_sha256':sha((P/'POLICY.json').read_bytes()),'policy_content_sha256':sha(json.dumps(policy,sort_keys=True).encode()),'date':date,'market':market,'scope_sha256':sha(raw),'keys':keys,'count':len(keys),
   'scope_vintage':item['vintage'],'carry_forward':date>item['vintage'],'new_day_selection':False,
   'calendar_status':state,'calendar_sha256':item['calendar']['sha256'],'extraordinary_closure_status':'UNKNOWN',
   'purpose':'RAW_OBSERVATION_ONLY','current_connect_eligibility':'UNKNOWN','current_suspensions':'UNKNOWN',
   'RESEARCH_ONLY':True,'production_allowed':False,'buy_gate_updated':False,'orders_sent':False})
 return contracts

def verify_review(review,policy_path):
 rv=read(review)
 if rv.get('verdict')!='PASS_RAW_CAPTURE_ONLY' or rv.get('runner_sha256')!=sha((P/'runner.py').read_bytes()) or rv.get('policy_sha256')!=sha(policy_path.read_bytes()):raise ValueError('INDEPENDENT_BINDING_MISSING_OR_CHANGED')
 return rv

def run(policy,review,clock=now,sleep=time.sleep,fetch=http_fetch):
 """Real CLI has no simulated clock. Dependency injection is only library test interface."""
 verify_review(review,P/'POLICY.json')
 if read(P/'POLICY.json')!=policy:raise ValueError('POLICY_ARGUMENT_DIFFERS_FROM_REVIEWED_FILE')
 start=clock();local=start.astimezone(TZ['A']);date=local.date().isoformat()
 if local.time()<dt.time(8,50):raise ValueError('START_BEFORE_0850')
 root=safe(P,'runtime');contracts=prepare(date,policy)
 contract_path=safe(root,date+'/run_contracts.json')
 if contract_path.exists():
  if read(contract_path)!=contracts:raise ValueError('EXISTING_DATE_CONTRACT_DIFFERS_NO_OVERWRITE')
 else:save(contract_path,contracts)
 stopfile=safe(root,date+'/SECURITY_STOP.json')
 results=[]
 if all(c['calendar_status']=='CLOSED_NO_CAPTURE' for c in contracts):
  save(safe(root,date+'/run_status.json'),{'status':'CLOSED_NO_CAPTURE','results':[],'finished_utc':clock().isoformat(),'alert':False})
  return []
 for slot,(begin,_) in SLOTS.items():
  target=dt.datetime.combine(local.date(),dt.time.fromisoformat(begin),TZ['A'])
  while clock()<target:
   sleep(min(15,max(0,(target-clock()).total_seconds())))
  for c in contracts:
   if c['market']=='A' and slot=='0900':continue
   if c['calendar_status']=='CLOSED_NO_CAPTURE':
    results.append({'market':c['market'],'slot':slot,'status':'CLOSED_NO_CAPTURE'});continue
   if stopfile.exists():
    results.append({'market':c['market'],'slot':slot,'status':'SECURITY_STOP_NO_REQUEST','alert':True});continue
   result=capture(root,c,slot,clock,fetch);results.append(result)
   if result.get('security_stop'):save(stopfile,result)
   save(safe(root,date+'/run_status.json'),{'status':'IN_PROGRESS','results':results,'natural_clock_cli':clock is now})
 save(safe(root,date+'/run_status.json'),{'status':'BOUNDED_RUN_FINISHED','results':results,'natural_clock_cli':clock is now,'finished_utc':clock().isoformat(),'alert':any(x.get('alert') for x in results)})
 return results

def record_deadline(t):
 date=t.astimezone(TZ['A']).date().isoformat();root=safe(P,'runtime/'+date)
 alert={'status':'DEADLINE_INTERRUPTED_UNKNOWN_NO_RETRY','at_utc':t.isoformat(),'alert':True,'action':'DO_NOT_FETCH_ALERT'}
 for marker in root.glob('*/*/'+SOURCE_ID+'/*/attempt.json'):
  d=marker.parent
  if not (d/'receipt.json').exists():
   base=read(d/'raw_receipt.json') if (d/'raw_receipt.json').exists() else read(marker)
   save(d/'receipt.json',dict(base,**alert))
 save(safe(root,'run_status.json'),dict(alert,deadline='09:35 Asia/Shanghai'))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('command',choices=['prepare','run','lookup','monitor-0930']);ap.add_argument('--date');ap.add_argument('--review');ap.add_argument('--market',choices=['A','HK'],default='A');ap.add_argument('--slot',choices=list(SLOTS),default='0930');a=ap.parse_args()
 policy=read(P/'POLICY.json')
 if a.command=='run':
  if not a.review:ap.error('--review required')
  # Lock is per fixed installation, never alternate output roots.
  lock=open(safe(P,'runner.lock'),'a')
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  budget=deadline_seconds(now())
  def deadline(signum,frame):
   record_deadline(now())
   raise SystemExit('09:35 HARD DEADLINE; inspect exclusive attempts, never retry blindly')
  signal.signal(signal.SIGALRM,deadline)
  if budget>0:signal.setitimer(signal.ITIMER_REAL,budget)
  try:result=run(policy,safe(P,a.review))
  finally:signal.setitimer(signal.ITIMER_REAL,0);lock.close()
 else:
  if not a.date:ap.error('--date required')
  contracts=prepare(a.date,policy)
  if a.command=='prepare':
   dest=safe(P,'contracts/'+a.date+'.json')
   if dest.exists() and read(dest)!=contracts:raise ValueError('EXISTING_CONTRACT_DIFFERS')
   if not dest.exists():save(dest,contracts)
   result={'path':str(dest),'contracts':contracts}
  else:
   c=next(x for x in contracts if x['market']==a.market)
   result=monitor_bridge(safe(P,'runtime'),c) if a.command=='monitor-0930' else lookup(safe(P,'runtime'),c,a.slot)
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
 try:main()
 except Exception as e:
  # Failures before a market attempt still leave a durable alert, not silent stdout only.
  failure={'status':'RUN_BLOCKED','error':repr(e),'at_utc':now().isoformat(),'alert':True}
  save(safe(P,'runtime/blocked_'+now().strftime('%Y%m%dT%H%M%S%f')+'.json'),failure)
  print(json.dumps(failure));raise SystemExit(2)

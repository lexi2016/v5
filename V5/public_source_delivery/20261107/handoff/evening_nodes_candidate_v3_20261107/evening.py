"""Read-only evening report preparation. Never dispatches, sends, or accepts a chain."""
from __future__ import annotations
import datetime as dt
import hashlib
import types
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NODES={'1700':'17:00','1830':'18:30','1850':'18:50','1900':'19:00'}
PINS={'trading_calendar.py':'584f28d18273a8824c5f68a701aa4404123b5c71900caada3e2772828991ee8f','market_calendar_2026.json':'9e2638b69e25495478cecb6ed551713178fcb989a63ebb4ecfd59689615f0acb'}
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def markets(date):
 # Exact original files, not caller-supplied executable calendar code.
 payloads={}
 for name,pin in PINS.items():
  p=HERE/'vendor'/name
  if p.is_symlink() or p.parent.is_symlink():raise ValueError('CALENDAR_SYMLINK')
  raw=p.read_bytes()
  if sha(raw)!=pin:raise ValueError('CALENDAR_PIN_CHANGED')
  payloads[name]=raw
 name='_evening_original_calendar'
 m=types.ModuleType(name);m.__file__=str(HERE/'vendor/trading_calendar.py');sys.modules[name]=m
 class FrozenCalendar:
  def read_text(self,encoding='utf-8'):return payloads['market_calendar_2026.json'].decode(encoding)
 try:
  exec(compile(payloads['trading_calendar.py'],m.__file__,'exec'),m.__dict__)
  m.CALENDAR_PATH=FrozenCalendar()
  return {k:str(v) for k,v in m.resolve_market_states(m.load_market_calendar(),date).items()}
 finally:sys.modules.pop(name,None)

def build(node,date,now,observations):
 if node not in NODES:raise ValueError('NODE')
 if now.tzinfo is None:raise ValueError('TIMEZONE_REQUIRED')
 local=now.astimezone(ZoneInfo('Asia/Shanghai'))
 if local.strftime('%Y%m%d')!=date:raise ValueError('WRONG_LOCAL_DATE_NO_CATCHUP')
 due=dt.datetime.combine(local.date(),dt.time.fromisoformat(NODES[node]),local.tzinfo)
 rows=[]
 for original in observations:
  row=dict(original)
  # Pin merely identifies a record; it does not establish business truth.
  row['claimed_status']=row.get('status','UNKNOWN')
  from adapter import checked
  try:
   evidence=checked(row.get('evidence_ref'));row['evidence_integrity']='VERIFIED_BYTES_ONLY'
   if row.get('status')=='COMPLETED':
    from adapter import HERE as AH,raw_read
    approved=json.loads(raw_read(AH/'INPUT_PINS.json'))['merge_admission']
    if row['evidence_ref']!=approved or evidence.get('schema')!='SINA69_RESEARCH_SELECTION_MERGE_ADMISSION_V1' or evidence.get('status')!='PASS_RESEARCH_MERGE_DISPLAY_ONLY' or evidence.get('production_allowed') is not False:raise ValueError('UNBOUND_COMPLETION')
    counts=checked(evidence['counts_ref'])
    if str(counts['source_date'])!=str(row.get('data_date')):raise ValueError('COMPLETION_DATE_MISMATCH')
    row['completion_scope']='REVIEWED_DISPLAY_MERGE_ONLY' 
  except (OSError,ValueError,KeyError,TypeError) as e:
   row['status']='UNKNOWN';row['evidence_integrity']='FAILED:'+type(e).__name__
  if row.get('status') not in ('COMPLETED','FAILED','NOT_RUN','RUNNING','BLOCKED','UNKNOWN'):row['status']='UNKNOWN'
  row['historical']=str(row.get('data_date'))!=date
  if row['status']=='RUNNING':row['status']='UNKNOWN';row['running_reason']='STALE_OR_UNBOUND_RUNTIME_NO_LIVENESS_PROOF'
  if row['historical'] and row.get('status')=='COMPLETED':row['status']='HISTORICAL_ONLY'
  row['business_acceptance']='NOT_GRANTED_BY_REPORTER'
  rows.append(row)
 identity=sha(canonical({'node':node,'date':date,'observations':rows,'code_sha256':sha(Path(__file__).read_bytes()),'calendar':PINS,'adapter_sha256':sha((HERE/'adapter.py').read_bytes()),'input_pins_sha256':sha((HERE/'INPUT_PINS.json').read_bytes())}))
 return {'schema':'EVENING_READ_ONLY_PREVIEW_V1','identity':identity,'node':node,'target_date':date,
  'scheduled_at':due.isoformat(),'observed_at':now.isoformat(),'time_status':'DUE' if local>=due else 'WAITING_TIME',
  'report_sections':{'done':[r for r in rows if r['status']=='COMPLETED'],
   'historical_completed':[r for r in rows if r['status']=='HISTORICAL_ONLY'],
   'unknown':[r for r in rows if r['status']=='UNKNOWN'],
   'not_run':[r for r in rows if r['status']=='NOT_RUN'],
   'errors':[r for r in rows if r['status'] in ('FAILED','BLOCKED')],
   'impact':'Current target-date complete chain is UNKNOWN; historical outputs are not relabelled.',
   'can_continue':'Read-only evidence reconciliation and authorized independent repairs; do not stop healthy jobs.',
   'needs_intervention':'UNKNOWN pending exact source/worker/scheduler/delivery receipts; no new permission presumed.'},
  'evening_1900':{'manifest_status':'PREVIEW_ONLY','board_status':'UNKNOWN_LIVE_NOT_QUERIED','next_observation_list':'UNKNOWN_NOT_MATERIALIZED','saved_formal':'NOT_SAVED_BY_REPORTER'},
  'markets':markets(date),'observations':rows,'business_status':'FAILED' if any(r['status']=='FAILED' for r in rows) else 'UNKNOWN',
  'trigger_source':'MANUAL_PREVIEW','scheduler_run_id':'UNKNOWN','actual_node_started_at':'UNKNOWN',
  'natural_verified':False,'live_service_verified':False,'delivery_status':'NOT_SENT','message_id':'UNKNOWN',
  'compute_calls':0,'source_calls':0,'selector_calls':0,'scope':'READ_ONLY_REPORT_PREPARATION_NOT_SCHEDULER_OR_ADMISSION'}
def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--node',choices=NODES,required=True);a=p.parse_args()
 now=dt.datetime.now(dt.timezone.utc)
 from adapter import inspect,freeze
 try:
  state=inspect()
  observations=[{'stage':'reviewed_display_merge_only','status':'COMPLETED','data_date':state['merged']['data_date'],'evidence_ref':state['pins']['merge_admission'],'facts':state}]
 except (OSError,ValueError,KeyError) as e:
  observations=[{'stage':'reviewed_display_merge_only','status':'UNKNOWN','reason':type(e).__name__+':'+str(e)}]
 report=build(a.node,now.astimezone(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d'),now,observations)
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

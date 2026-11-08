"""New V3 recorded TEXT contract, not recovered a0915.py or quote collection.
Explicit caller policy validates temporal fit only; never source admission.
No network, persistence, registry, locking, schedules or production execution.
"""
import datetime as dt
import hashlib
import json
import re
from zoneinfo import ZoneInfo
MAX_BYTES=2*1024*1024

def require(ok,reason):
 if not ok:raise ValueError(reason)
def strict(raw):
 def pairs(items):
  out={}
  for k,v in items:
   require(k not in out,'DUPLICATE_KEY');out[k]=v
  return out
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE')))
def timestamp(value):
 require(type(value)is str,'TIME_TYPE')
 value=dt.datetime.fromisoformat(value)
 require(value.tzinfo is not None and value.utcoffset() is not None,'TIMEZONE_REQUIRED')
 return value

def read_recorded_bytes(raw,contract):
 require(type(raw)is bytes and 0<len(raw)<=MAX_BYTES,'INPUT_SIZE')
 require(type(contract)is dict and set(contract)=={'schema','target_date','scope','source_reference','input_sha256','cutoff','max_age_seconds'},'CONTRACT_FIELDS')
 # Detach all input metadata. This contract is caller-supplied, not authority.
 contract=strict(json.dumps(contract,allow_nan=False).encode())
 require(contract['schema']=='A0915_TEXT_READER_CONTRACT_V3','CONTRACT_SCHEMA')
 pin=contract['input_sha256'];require(type(pin)is str and re.fullmatch('[0-9a-f]{64}',pin),'INPUT_PIN')
 require(hashlib.sha256(raw).hexdigest()==pin,'INPUT_CHANGED')
 day=contract['target_date'];require(type(day)is str and re.fullmatch('[0-9]{8}',day),'TARGET_DATE')
 date=dt.datetime.strptime(day,'%Y%m%d').date()
 scope=contract['scope'];require(type(scope)is list and 0<len(scope)<=10000 and all(type(s)is str and re.fullmatch(r'A\.[0-9]{6}',s) for s in scope) and len(set(scope))==len(scope),'SCOPE')
 source=contract['source_reference'];require(type(source)is str and 0<len(source.strip())<=4096,'SOURCE_REFERENCE')
 age=contract['max_age_seconds'];require(type(age)is int and 0<age<=86400,'FRESHNESS_POLICY')
 cutoff=timestamp(contract['cutoff']).astimezone(ZoneInfo('Asia/Shanghai'))
 require(cutoff.date()==date and cutoff.timetz().replace(tzinfo=None)==dt.time(9,15),'CUTOFF_MUST_BE_0915_SHANGHAI')
 data=strict(raw)
 require(type(data)is dict and set(data)=={'schema','market','target_date','observed_at','available_at','scope','rows','source_reference','data_kind'},'INPUT_FIELDS')
 require(data['schema']=='A0915_RECORDED_DISPLAY_INPUT_V1' and data['market']=='A_SHARE','INPUT_SCHEMA')
 require(data['data_kind'] in ('RECORDED_UNVERIFIED','SYNTHETIC_TEST'),'DATA_KIND')
 require(data['target_date']==day and data['scope']==scope and data['source_reference']==source,'INPUT_IDENTITY')
 observed=timestamp(data['observed_at']).astimezone(ZoneInfo('Asia/Shanghai'));available=timestamp(data['available_at']).astimezone(ZoneInfo('Asia/Shanghai'))
 require(observed.date()==available.date()==date,'SOURCE_DATE')
 require(observed<=available<=cutoff,'NOT_AVAILABLE_OR_TIME_ORDER')
 require((cutoff-observed).total_seconds()<=age,'STALE_FOR_EXPLICIT_POLICY')
 rows=data['rows'];require(type(rows)is list and len(rows)<=len(scope),'ROWS')
 seen=set()
 for row in rows:
  require(type(row)is dict and set(row)=={'symbol','observation'},'TEXT_ROW_FIELDS')
  symbol=row['symbol'];require(type(symbol)is str and symbol in scope and symbol not in seen,'ROW_SCOPE_OR_DUPLICATE')
  require(type(row['observation'])is str and 0<len(row['observation'].strip())<=16384,'OBSERVATION_TEXT')
  seen.add(symbol)
 missing=[s for s in scope if s not in seen]
 return {'schema':'A0915_TEXT_VALIDATION_RESULT_V3','status':'MISSING_SCOPE_ROWS' if missing else 'RECORDED_TEXT_VALIDATED_NOT_ADMITTED','contract_kind':'NEW_CALLER_POLICY_NOT_ORIGINAL_AUTHORITY','input_sha256':pin,'input_bytes':len(raw),'contract':contract,'recorded_input':data,'missing_symbols':missing,'observed_count':len(rows),'scope_count':len(scope),'temporal_policy_checked':True,'source_admission':'UNKNOWN','freshness_admission':'UNKNOWN','production_allowed':False,'business_accepted':False,'natural_verified':False,'source_calls':0,'sent':False,'quote_fields_validated':False}

if __name__=='__main__':
 import argparse,os,stat
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--contract',required=True);a=p.parse_args()
 def bounded(path):
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  with os.fdopen(fd,'rb') as f:
   require(stat.S_ISREG(os.fstat(f.fileno()).st_mode),'REGULAR_FILE_REQUIRED');raw=f.read(MAX_BYTES+1)
  require(0<len(raw)<=MAX_BYTES,'INPUT_SIZE');return raw
 print(json.dumps(read_recorded_bytes(bounded(a.input),strict(bounded(a.contract))),ensure_ascii=False,allow_nan=False))

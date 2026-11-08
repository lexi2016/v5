"""Registered reconstruction adapter; never a replacement for original latest109 pin.
No acquisition, persistence, locks, production registration or lowered resource gate.
"""
import hashlib, importlib.util, json
from pathlib import Path
from datetime import datetime
CANDIDATE_SHA='4acf301445ce3c63fc0a3116e76a24bc9f7410474aa50de990ddc8cc350a25cd'
ACTION_SHA='16457c1ebda6096652dc356d8f7044ce0e5a323fe5ebf16733423dabca0fb6ec'
FLAGS={'production_allowed':False,'source_admission':False,'selection_admission':False,'original_latest109_restored':False}

def digest(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def checked(path,sha):
 path=Path(path)
 if hashlib.sha256(path.read_bytes()).hexdigest()!=sha: raise ValueError('CODE_OR_RULE_PIN')
 return path

def load(candidate_path,action_path):
 path=Path(candidate_path);raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=CANDIDATE_SHA:raise ValueError('CODE_OR_RULE_PIN')
 checked(action_path,ACTION_SHA)
 spec=importlib.util.spec_from_file_location('registered_latest109_candidate',path)
 module=importlib.util.module_from_spec(spec)
 # Execute the exact verified snapshot, never reopen code via the loader.
 exec(compile(raw,str(path),'exec'),module.__dict__)
 return module

def validate_checkpoint(rows,context,state,checkpoint_prefix_sha256):
 if not isinstance(rows,list) or len(rows)<2 or not all(isinstance(row,dict) for row in rows):raise ValueError('CHECKPOINT_ROWS')
 if not isinstance(context,dict) or not isinstance(state,dict):raise ValueError('REVIEWED_PRIOR_COMPONENT_REQUIRED')
 symbol=context.get('symbol')
 if not isinstance(symbol,str) or not symbol or any(row.get('symbol')!=symbol for row in rows):raise ValueError('CHECKPOINT_ROW_SYMBOL')
 if type(state.get('count')) is not int:raise ValueError('PRIOR_COUNT_TYPE')
 previous=None
 for row in rows:
  date=row.get('event_date')
  if not isinstance(date,str) or len(date)!=8 or not date.isascii() or not date.isdigit():raise ValueError('CHECKPOINT_DATE_FORMAT')
  try:datetime.strptime(date,'%Y%m%d')
  except ValueError as exc:raise ValueError('CHECKPOINT_DATE_FORMAT') from exc
  if previous is not None and date<=previous:raise ValueError('CHECKPOINT_DATE_ORDER')
  previous=date
 if checkpoint_prefix_sha256 != digest(rows[:-1]):raise ValueError("PRIOR_PREFIX_COMMITMENT")
 if (state.get('symbol'),state.get('count'),state.get('last_date'))!=(context.get('symbol'),len(rows)-1,rows[-2].get('event_date')):raise ValueError('PRIOR_IDENTITY')
 if rows[-1].get('symbol')!=context.get('symbol') or rows[-1].get('event_date')!=context.get('asof'):raise ValueError('TARGET_IDENTITY')
 # Hashes bind the new result to exact caller input, without claiming source admission.
 return digest({'rows':rows,'context':context,'prior_state':state})

def build(candidate,producer,modules,*,original_monitor_gate):
 """Caller must retain the unchanged original owner monitor, including child monitor.
 This wrapper cannot attest the supplied callback; production admission stays false.
 """
 if not callable(original_monitor_gate):raise ValueError('ORIGINAL_MONITOR_REQUIRED')
 checked(candidate.__file__,CANDIDATE_SHA)
 actual_action=Path(candidate.__file__).resolve().parent.parent/'panel_field_algorithms_20261102/foundation_action_candidate/ACTION_RULES.json'
 checked(actual_action,ACTION_SHA)
 schema=json.loads((Path(producer.H)/'FIELD_SCHEMA_109.json').read_bytes())
 if len(schema)!=109:raise ValueError('FIELD_COUNT_109')
 original_monitor_gate()
 compute=candidate.build(producer,modules,gate=original_monitor_gate)
 def run(rows,context,prior_state=None,*,checkpoint_prefix_sha256):
  original_monitor_gate();input_sha=validate_checkpoint(rows,context,prior_state,checkpoint_prefix_sha256)
  row,facts=compute(rows,context,prior_state=prior_state)
  original_monitor_gate()
  if not isinstance(facts,dict) or not isinstance(facts.get('component_state'),dict):raise ValueError('RESULT_COMPONENT_STATE')
  if (row.get('symbol'),row.get('event_date'))!=(context['symbol'],context['asof']):raise ValueError('OUTPUT_IDENTITY')
  if set(row.get('fields',{}))!=set(schema):raise ValueError('OUTPUT_SCHEMA')
  for key,value in row['fields'].items():producer.core.check_field(value,schema[key])
  state=facts['component_state']
  if (state.get('symbol'),state.get('count'),state.get('last_date'))!=(context['symbol'],len(rows),context['asof']):raise ValueError('RESULT_IDENTITY')
  return row,{**facts,**FLAGS,'adapter_version':'LATEST109_REBUILD_V2','input_sha256':input_sha,'output_sha256':digest(row),'requires_original_owner_integration':True}
 return run

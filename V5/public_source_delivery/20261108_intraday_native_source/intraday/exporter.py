"""Isolated original-field extraction. Not a monitoring-list owner or activation.
Production registrations intentionally absent; Runtime.physical must remain original.
"""
import hashlib,json,re
from pathlib import Path
REGISTRY={}
FLAGS={'production_allowed':False,'approved_for_capture':False,'activation_created':False,'buy_gate_updated':False,'orders_sent':False}
def need(x,label):
 if not x:raise ValueError(label)
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def signal(x):
 # Original engine values are boolean; do not coerce strings/numbers/UNKNOWN.
 return x if type(x)is bool else None
def extract(runtime,terminal,input_ref,metadata,target,observation,checked,owner_context):
 """Called inside existing owner's reviewed resource/lock context, never takes locks.
 metadata and formula_asset must be independently bound by caller's owner contract.
 No standalone production caller exists in this candidate.
 """
 need(type(target)is int and type(observation)is int and target<observation,'DATES')
 s=terminal['doc']['symbol'];need(re.fullmatch(r'\d{6}\.(SH|SZ|BJ)',s),'IDENTITY')
 need(metadata['symbol']==s and metadata['selection_date']==target and metadata['observation_date']==observation,'METADATA_BINDING')
 for k in ('name','formula_status','qualification','visual_status'):need(type(metadata.get(k))is str and metadata[k],'MISSING_'+k)
 asset=metadata['formula_asset'];checked(asset)
 with owner_context():
  runtime.gate()
  bundle,facts,proof=runtime.physical(terminal['doc'],terminal['ref'],input_ref,False)
  need(bundle['symbol']==bundle['state51']['symbol']==s,'BUNDLE_IDENTITY')
  need(bundle['asof']==str(target) and bundle['daily51']['trade_date']==bundle['state51']['last_date']==target,'BUNDLE_DATE')
  # Asset is the original same-day 51 result document, not a substituted formula.
  original=json.loads(checked(asset));need(digest(original)==digest(bundle['daily51']),'FORMULA_ASSET_NOT_SAME_DAILY51')
  need(bundle['state51']['formula_sha256']==runtime.rt.step.FORMULA_SHA and bundle['state51']['original_engine_sha256']==runtime.rt.step.ENGINE_SHA,'FORMULA_IDENTITY')
  a=signal(bundle['daily51']['values'].get('一级买点'));b=signal(bundle['daily51']['values'].get('二级买点'))
  # Original tri-state OR: one True is sufficient; missing stays unknown otherwise.
  hit=True if a is True or b is True else False if a is False and b is False else None
  checked(terminal['ref']);checked(input_ref);checked(asset);runtime.gate()
 return {'symbol':s,'name':metadata['name'],'selection_date':target,'observation_date':observation,'primary':a,'secondary':b,'original_hit':hit,'formula_asset':asset,'formula_status':metadata['formula_status'],'qualification':metadata['qualification'],'visual_status':metadata['visual_status'],'owner_success_ref':terminal['ref'],'input_ref':input_ref,'physical_proof':proof,'status':'UNKNOWN_SIGNAL'if hit is None else 'EXTRACTED_ORIGINAL_FIELDS_NOT_MONITOR_SCOPE',**FLAGS}
def dispatch(run_id,environment_id):
 # Binding/independent export review and real owner factory deliberately not invented.
 if (run_id,environment_id) not in REGISTRY:raise ValueError('BLOCKED_NO_REVIEWED_ORIGINAL_FIELD_EXPORT_OWNER')
 raise ValueError('BLOCKED_PRODUCTION_EXPORT_BINDING_NOT_IMPLEMENTED')

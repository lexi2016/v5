"""Immutable latest-selection metadata overlay; never re-evaluates real stocks.

External owner/source review and a real independently bound sample are required.
No native/SQL/formula imports. Payloads receive stat checks only, not a false
all-population independent readback claim. Old assets and CURRENT stay unchanged.
"""
import argparse,copy,datetime,hashlib,json,os,pathlib,re,sys
HERE=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import continuation_provider as c
ROOT=c.ROOT;need=c.need

def day(value):
 text=str(value);need(type(value) in (str,int) and re.fullmatch('[0-9]{8}',text) is not None,'DATE_TYPE')
 datetime.date(int(text[:4]),int(text[4:6]),int(text[6:]));return text

def read(ref):return json.loads(c.checked(ref))
def closed(doc):need(all(doc.get(k) is False for k in c.FLAGS),'NONADMISSION_FLAGS')

def payload_stat(ref):
 need(type(ref) is dict and {'path','bytes','sha256'}<=set(ref),'PAYLOAD_REF')
 p=pathlib.Path(ref['path']);p=p if p.is_absolute() else ROOT/p
 need(p==p.resolve() and p.is_relative_to(ROOT) and not p.is_symlink(),'PAYLOAD_PATH')
 need(type(ref['bytes']) is int and ref['bytes']>0 and p.stat().st_size==ref['bytes'],'PAYLOAD_SIZE')
 need(type(ref['sha256']) is str and re.fullmatch('[0-9a-f]{64}',ref['sha256']) is not None,'PAYLOAD_SHA_FORMAT')
 return p

def build(prior_ref,manifest_ref,sample_ref):
 prior=read(prior_ref);m=read(manifest_ref);review=read(sample_ref)
 D=day(m['target_date']);need(day(prior['target_date'])<D,'NEW_TARGET_REQUIRED')
 need(m.get('status')=='ATTEMPT_COMPLETE_AWAIT_INDEPENDENT_SAMPLE','OWNER_NOT_TERMINAL');closed(m)
 contract=read(m['contract_ref']);need(day(contract['observation_date'])>D,'OBSERVATION_AFTER_TARGET');need(contract['schema']=='PAR_NEXT_SESSION_RUN_V1' and day(contract['target_date'])==D and contract['prior_catalog_ref']==prior_ref,'OWNER_CONTRACT_BINDING')
 need('raw_source_ref' in contract,'CURRENT_RAW_SOURCE_REQUIRED');payload_stat(contract['raw_source_ref'])
 source_review=read(m['source_review_ref']);need(source_review.get('status')=='PASS_SAME_SOURCE_NEXT_SESSION_INPUT_REVIEW' and source_review.get('contract_ref')==m['contract_ref'] and source_review.get('reviewer_role')=='independent_reviewer' and source_review.get('source_semantics_independently_verified') is True,'OWNER_SOURCE_REVIEW')
 base=prior['latest_selections'];symbols=[r['symbol'] for r in base]
 need(len(symbols)==len(set(symbols))==5575 and all(re.fullmatch('[0-9]{6}\\.(SZ|SH|BJ)',s) for s in symbols),'PRIOR_SCOPE')
 need(all(day(r['event_date'])<=day(prior['target_date']) for r in base),'PRIOR_FUTURE_DATE')
 lookup={r['symbol']:r for r in base};declared=[r['symbol'] for r in contract['inputs']]
 need(type(m['scope_count']) is int and declared and len(declared)==len(set(declared))==m['scope_count'] and set(declared)<=set(symbols),'OWNER_SCOPE')
 terminals={};successes={};retained={};failed={}
 for field,destination in (('successes',successes),('retained',retained),('failures',failed)):
  for pin in m[field]:
   value=read(pin);symbol=value['symbol'];need(symbol in declared and symbol not in terminals,'TERMINAL_PARTITION');closed(value)
   terminals[symbol]=(value,pin);destination[symbol]=(value,pin)
 need(set(terminals)==set(declared),'TERMINAL_PARTITION')
 need(review.get('schema')=='PAR_NEXT_SESSION_INDEPENDENT_SAMPLE_V1' and review.get('status')=='PASS_INDEPENDENT_SAMPLE' and review.get('reviewer_role')=='independent_reviewer' and review.get('all_sample_checks_passed') is True,'SAMPLE_STATUS')
 need(review['owner_manifest_ref']==manifest_ref and day(review['target_date'])==D,'SAMPLE_MANIFEST')
 sampled=review['sample_symbols'];need(type(review['sample_count']) is int and type(sampled) is list and len(sampled)==len(set(sampled))==review['sample_count'] and set(sampled)<=set(successes),'SAMPLE_SCOPE')
 if successes:need(sampled and review.get('sample_kind')=='REAL_PARQUET_AND_CONTINUATION_READBACK','REAL_SAMPLE_REQUIRED')
 else:need(not sampled and review.get('sample_kind')=='METADATA_ONLY_NO_NEW_SUCCESS','NO_SUCCESS_SAMPLE_KIND')
 out=[];unresolved=[]
 for old in base:
  symbol=old['symbol'];r=copy.deepcopy(old)
  if symbol in successes:
   success,pin=successes[symbol];need(success['status']=='COMPUTED_SAME_BASIS_NEXT_SESSION_WITH_CONTINUATION' and day(success['event_date'])==D,'SUCCESS_DATE')
   receipt=read(success['parquet_receipt_ref']);closed(receipt)
   need(receipt['status']=='SAME_BASIS_NEXT_SESSION_PARQUET_FULL_ROUNDTRIP_VERIFIED_NOT_ADMISSION' and receipt['symbol']==symbol and receipt['event_dates']==[D] and day(receipt['calculation_asof'])==D,'PARQUET_IDENTITY')
   need(type(receipt['field_rows']) is int and type(receipt['metadata_rows']) is int and receipt['field_rows']==109 and receipt['metadata_rows']==1 and receipt.get('full_objects_context_types_ieee_bits_key_orders_exact') is True,'PARQUET_SCHEMA_VERIFICATION')
   need(set(receipt['files'])=={'field_rows','row_metadata'},'PARQUET_PAIR')
   for file_ref in receipt['files'].values():payload_stat(file_ref)
   payload_stat(success['continuation_ref'])
   # Retain source provenance, but never inherit a stale previous-day status.
   r.update(event_date=D,selection_status='NEW_TARGET_DAY_SUCCESS',success_ref=pin,continuation_ref=success['continuation_ref'],parquet_receipt_ref=success['parquet_receipt_ref'],producer_ref=manifest_ref,source_origin='SAME_BASIS_NEXT_SESSION_CONTINUATION',field_rows=109,metadata_rows=1,stale=False,current_independent_sample=symbol in sampled,current_verification_ref=sample_ref if symbol in sampled else None,current_verification_coverage='INDEPENDENT_SAMPLE' if symbol in sampled else 'ORIGINAL_WRITER_BUILTIN_ONLY',prior_selection_ref={'catalog_ref':prior_ref,'symbol':symbol},current_attempt_ref=pin)
  elif symbol in retained:
   value,pin=retained[symbol];need(value['status']=='RETAINED_NO_VALID_BAR' and day(value['event_date'])==day(old['event_date']),'RETAINED_DATE')
   r.update(selection_status='RETAINED_NO_VALID_BAR',stale=True,current_attempt_ref=pin,current_reason='VERIFIED_NO_VALID_TARGET_DAY_BAR')
  elif symbol in failed:
   value,pin=failed[symbol];need(value['status']=='UNKNOWN_NO_BLIND_RETRY' and day(value['target_date'])==D and type(value['reason']) is str and value['reason'],'FAILED_IDENTITY')
   r.update(selection_status='FAILED_TARGET_DAY_KEPT_PRIOR',stale=True,current_attempt_ref=pin,current_reason=value['reason']);unresolved.append(symbol)
  else:
   r.update(selection_status='OUTSIDE_THIS_OWNER_SCOPE_KEPT_PRIOR',stale=True,current_reason='NOT_RUN_THIS_OWNER');unresolved.append(symbol)
  if symbol not in successes:
   r.update(current_independent_sample=False,current_verification_ref=None,current_verification_coverage='NO_NEW_TARGET_DAY_RESULT')
  out.append(r)
 dates={}
 for r in out:dates[r['event_date']]=dates.get(r['event_date'],0)+1
 # Recheck all small input metadata refs, detecting mid-finalization changes.
 for pin in (prior_ref,manifest_ref,sample_ref,m['contract_ref'],m['source_review_ref'],*(pin for _,pin in terminals.values())):c.checked(pin)
 return {'schema':'PAR_DYNAMIC_LATEST_SELECTION_CATALOG_V1','status':'METADATA_OVERLAY_COMPLETE_RESEARCH_CANDIDATE','target_date':D,'observation_date':day(contract['observation_date']),'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'prior_catalog_ref':prior_ref,'owner_manifest_ref':manifest_ref,'sample_ref':sample_ref,'source_review_ref':m['source_review_ref'],'raw_source_ref':contract['raw_source_ref'],'raw_source_date':D,'raw_source_binding_basis':'INDEPENDENTLY_REVIEWED_OWNER_CONTRACT_NOT_REPARSED_BY_FINALIZER','latest_selections':out,'logical_date_counts':dates,'sample_symbols':sampled,'counts':{'logical_symbols':5575,'owner_scope':len(declared),'new_successes':len(successes),'retained_no_bar':len(retained),'failed_kept_prior':len(failed),'outside_owner_scope':5575-len(declared),'independently_sampled_new_successes':len(sampled)},'issues':[],'additional_unresolved_symbols':unresolved,'boundaries':{'all_population_independent_readback':False,'payloads_opened':False,'payload_stat_checks_only':True,'metadata_refs_rehashed':True,'native_calls':0,'formula_calls':0,'current_pointer_changed':False,**c.FLAGS}}

def write_new(path,value):
 p=pathlib.Path(path).absolute();need(p==p.resolve() and p.is_relative_to(ROOT),'OUTPUT_PATH');data=c.canonical(value)
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 return {'path':str(p.relative_to(ROOT)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def cli_ref(path,expected):
 p=pathlib.Path(path).absolute();data=p.read_bytes();pin={'path':str(p),'bytes':len(data),'sha256':expected};c.checked(pin);return pin

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prior-catalog',required=True);p.add_argument('--prior-sha256',required=True);p.add_argument('--manifest',required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--sample',required=True);p.add_argument('--sample-sha256',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 result=build(cli_ref(a.prior_catalog,a.prior_sha256),cli_ref(a.manifest,a.manifest_sha256),cli_ref(a.sample,a.sample_sha256));print(json.dumps(write_new(a.output,result),ensure_ascii=False))

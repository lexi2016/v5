"""Dynamic-date serial owner using unchanged original locks/resources/native/writer.

Only an independently reviewed pinned source contract can execute. No fetching,
source qualification, deployment or blanket admission is performed here.
"""
import argparse, fcntl, gc, gzip, hashlib, json, os, pathlib, shutil, signal, sys, time, types
HERE=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import continuation_provider as c
ROOT=c.ROOT;RUNS=HERE/'runs';ORIGINAL=c.OLD/'run_batch.py'
ORIGINAL_SHA='cc4817949a1e1f892b5ca23ebdbb57bcea4c4a97089434243e2a93137bf130c9'
RUNNER_PATH=ROOT/'handoff/panel109_remaining577_direct_parquet_20261105/run577_v3.py'
RUNNER_SHA='ddbd0aa13d1892750e3626be82a5f0f46bfaea9ae0f142a6d4b9aefc700ef586'
WRITER_PATH=ROOT/'handoff/panel109_tdx841_rebuild_20261105/engine/selected_writer.py'
LATEST_SHA='b1183e88d9b07bc5f4cc9039193a0fccd84197e2cc3a6874ec8abc992699c9c2'
need=c.need

def ref(path):
 path=pathlib.Path(path).absolute();need(path==path.resolve() and path.is_relative_to(ROOT),'LOCAL_REF_SCOPE');raw=path.read_bytes();return {'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
LOADED_CODE_REFS=[ref(pathlib.Path(__file__)),ref(HERE/'continuation_provider.py'),ref(c.OLD/'latest109.py'),ref(ORIGINAL),ref(RUNNER_PATH),ref(WRITER_PATH)]

def verify_snapshots(doc,pin,review_pin):
 need(ref(ROOT/pin['path'])==pin,'RUN_CONTRACT_CHANGED')
 if review_pin is not None:need(ref(ROOT/review_pin['path'])==review_pin,'REVIEW_CHANGED')
 for code in LOADED_CODE_REFS:need(ref(ROOT/code['path'])==code,'LOADED_CODE_CHANGED')
 refs={doc['prior_catalog_ref']['path']:doc['prior_catalog_ref']}
 if review_pin is not None:
  review=json.loads(c.checked(review_pin))
  if review.get('source_preparation_receipt_ref'):
   receipt_pin=source_preparation(doc,pin,review);refs[receipt_pin['path']]=receipt_pin
 if doc.get('raw_source_ref'):refs[doc['raw_source_ref']['path']]=doc['raw_source_ref']
 for item in doc['inputs']:
  facts=json.loads(c.checked(item['input_ref']));refs[item['input_ref']['path']]=item['input_ref']
  for key in ('formula_bar_ref','no_bar_evidence_ref','prior_continuation_ref'):
   if facts.get(key):refs[facts[key]['path']]=facts[key]
  for r in facts.get('source_evidence_refs',[]):
   if r['path'] in refs:need(refs[r['path']]==r,'CONFLICTING_INPUT_PIN')
   refs[r['path']]=r
 for r in refs.values():c.checked(r)
 return list(refs.values())

def record_interruption(entry,out,created_output,error,results,failures):
 if created_output:entry.save(out/'INTERRUPTED.json',{'status':'STOPPED_SAFE_NO_BLIND_RETRY','reason':str(error),'type':type(error).__name__,'success_refs':results,'failure_refs':failures})

def load_original():
 raw=ORIGINAL.read_bytes();need(hashlib.sha256(raw).hexdigest()==ORIGINAL_SHA,'ORIGINAL_OWNER_PIN')
 m=types.ModuleType('generic_owner_original_helpers');m.__file__=str(ORIGINAL);sys.modules[m.__name__]=m
 exec(compile(raw,str(ORIGINAL),'exec'),m.__dict__);return m

def load_runner(entry,name):
 need(hashlib.sha256(entry.RUNNER.read_bytes()).hexdigest()==RUNNER_SHA,'RESOURCE_RUNNER_PIN')
 return entry.module(entry.RUNNER,name)

def source_preparation(doc,pin,review):
 """A produced contract alone is not a completed source-preparation attempt."""
 receipt_pin=review.get('source_preparation_receipt_ref');need(receipt_pin is not None,'SOURCE_PREPARATION_TERMINAL_REQUIRED')
 path=pathlib.Path(receipt_pin['path']);path=path if path.is_absolute()else ROOT/path
 contract_path=pathlib.Path(pin['path']);contract_path=contract_path if contract_path.is_absolute()else ROOT/contract_path
 need(path.parent==contract_path.parent and contract_path.name=='RUN_CONTRACT.json','SOURCE_PREPARATION_SAME_ATTEMPT')
 need(path.name=='SOURCE_PREPARATION_RECEIPT.json' and not (path.parent/'INTERRUPTED.json').exists(),'SOURCE_PREPARATION_INTERRUPTED_OR_NONTERMINAL')
 receipt=json.loads(c.checked(receipt_pin))
 need(receipt.get('status')=='SOURCE_CANDIDATE_PREPARED_PENDING_INDEPENDENT_REVIEW' and receipt.get('contract_ref')==pin and receipt.get('target_date')==doc['target_date'],'SOURCE_PREPARATION_BINDING')
 need(receipt.get('raw_source_ref')==doc.get('raw_source_ref') and receipt.get('event_delta_ref')==doc.get('event_delta_ref'),'SOURCE_PREPARATION_BINDING')
 ready=receipt.get('ready_inputs');blocked=receipt.get('blocked_count')
 need(type(ready)is int and type(blocked)is int and ready==len(doc['inputs']) and blocked>=0 and ready+blocked==receipt.get('scope_count')==5575,'SOURCE_PREPARATION_PARTITION')
 blocked_rows=doc.get('source_blocked');need(type(blocked_rows)is list and receipt.get('blocked')==blocked_rows and len(blocked_rows)==blocked,'SOURCE_PREPARATION_SYMBOL_PARTITION')
 blocked_symbols=[r['symbol']for r in blocked_rows];ready_symbols=[r['symbol']for r in doc['inputs']];catalog=json.loads(c.checked(doc['prior_catalog_ref']));known=[r['symbol']for r in catalog['latest_selections']]
 need(len(ready_symbols)==len(set(ready_symbols)) and len(blocked_symbols)==len(set(blocked_symbols)) and not set(ready_symbols)&set(blocked_symbols) and set(ready_symbols)|set(blocked_symbols)==set(known) and len(known)==len(set(known))==5575,'SOURCE_PREPARATION_SYMBOL_PARTITION')
 return receipt_pin

def contract(path,sha,review_path=None):
 p=pathlib.Path(path).absolute();pin=ref(p);need(pin['sha256']==sha,'CONTRACT_EXTERNAL_PIN')
 doc=json.loads(c.checked(pin));need(doc['schema']=='PAR_NEXT_SESSION_RUN_V1','CONTRACT_SCHEMA')
 target=doc['target_date'];observation=doc['observation_date'];step,_=c.modules();step.valid_date(target,'TARGET_DATE');step.valid_date(observation,'OBSERVATION_DATE');need(observation>target,'OBSERVATION_AFTER_TARGET')
 cat=json.loads(c.checked(doc['prior_catalog_ref']));need(int(cat['target_date'])<target,'NO_OLD_DATE_REPLAY')
 selections={r['symbol']:r for r in cat['latest_selections']};need(len(selections)==len(cat['latest_selections'])==5575,'FIXED_SCOPE')
 records=doc['inputs'];symbols=[r['symbol'] for r in records]
 need(symbols and len(symbols)==len(set(symbols)) and set(symbols)<=set(selections),'UNIQUE_KNOWN_INPUT_SCOPE')
 for r in records:
  facts=json.loads(c.checked(r['input_ref']));need(facts.get('schema')=='SAME_SOURCE_NEXT_SESSION_INPUT_V1','SOURCE_INPUT_SCHEMA')
  need(facts['symbol']==r['symbol'] and facts['target_date']==target and facts['observation_date']==observation,'INPUT_DATE_IDENTITY')
  if selections[r['symbol']].get('continuation_ref'):need(facts['prior_continuation_ref']==selections[r['symbol']]['continuation_ref'],'AUTHORITATIVE_PRIOR_REF')
  else:need(facts.get('prior_selection_sha256')==c.digest(selections[r['symbol']]),'RETAINED_PRIOR_SELECTION_BINDING')
 if review_path:
  review=json.loads(c.checked(ref(review_path)))
  need(review['status']=='PASS_SAME_SOURCE_NEXT_SESSION_INPUT_REVIEW' and review['contract_ref']==pin,'SOURCE_REVIEW_CONTRACT')
  need(review.get('source_semantics_independently_verified') is True,'SOURCE_SEMANTICS_REVIEW')
  code={r['path']:r for r in review['code_refs']}
  for path in (pathlib.Path(__file__),HERE/'continuation_provider.py',c.OLD/'latest109.py'):
   need(code.get(str(path.relative_to(ROOT)))==ref(path),'REVIEW_CODE_PIN')
  need(review.get('reviewer_role')=='independent_reviewer','INDEPENDENT_REVIEW_REQUIRED')
  source_preparation(doc,pin,review)
 return doc,pin,selections

def preflight(path,sha,review_path=None):
 result={'schema':'PAR_NEXT_SESSION_PREFLIGHT_V1','status':'BLOCKED','can_execute':False,'formula_calls':0,'native_calls':0,'source_fetches':0,**c.FLAGS}
 try:
  doc,pin,selection=contract(path,sha,review_path);result.update(target_date=doc['target_date'],observation_date=doc['observation_date'],scope=len(doc['inputs']),contract_ref=pin)
  entry=load_original();runner=load_runner(entry,'generic_preflight_original_runner');w=runner.module(ROOT/runner.WRITER_REF['path'],'generic_preflight_original_monitor',runner.WRITER_REF['sha256'])
  runner.MAX_OUTPUT=w.MAX_OUTPUT=entry.OUTPUT_BUDGET;runner.DISK_FLOOR=w.DISK_FLOOR=entry.DISK_RESERVE
  available=w.available();free=shutil.disk_usage(ROOT).free;result['resources']={'available_memory_bytes':available,'free_disk_bytes':free,'required_start_memory':runner.START,'required_start_disk':runner.DISK_FLOOR+runner.MAX_OUTPUT}
  runner.check_start(available,free)
  need(review_path is not None,'INDEPENDENT_SOURCE_REVIEW_REQUIRED')
  result.update(status='READY_FOR_ORIGINAL_OWNER_LOCK_CHECK',can_execute=True)
 except (ValueError,KeyError,TypeError,OSError) as error:result['reason']=str(error)
 return result

def compute_prepared(prepared,compute):
 """Small testable seam: original latest109 must receive persisted prior state."""
 result,facts=compute(prepared['rows'],prepared['context'],prior_state=prepared['prior_component_state'])
 need(result['event_date']==prepared['context']['asof'],'NEW_DATE_EXACT')
 need(facts['historical109_rows_evaluated']==0 and facts['prior_component_state_reused'] is True,'LATEST_ONLY_WITH_PRIOR_COMPONENTS')
 component=facts.pop('component_state');return result,facts,c.continuation(prepared,component)

def run(path,sha,review_path,name):
 need(name.startswith('run_') and name.replace('_','').isalnum(),'OUTPUT_NAME')
 check=preflight(path,sha,review_path);need(check['can_execute'],check.get('reason','PREFLIGHT_BLOCKED'))
 doc,pin,selections=contract(path,sha,review_path);review_pin=ref(review_path);verify_snapshots(doc,pin,review_pin);entry=load_original()
 runner=load_runner(entry,'generic_daily_original_runner');w=runner.module(ROOT/runner.WRITER_REF['path'],'generic_daily_original_monitor',runner.WRITER_REF['sha256'])
 runner.MAX_OUTPUT=w.MAX_OUTPUT=entry.OUTPUT_BUDGET;runner.DISK_FLOOR=w.DISK_FLOOR=entry.DISK_RESERVE
 runner.check_start(w.available(),shutil.disk_usage(ROOT).free)
 need(hashlib.sha256((c.OLD/'latest109.py').read_bytes()).hexdigest()==LATEST_SHA,'LATEST_CODE_PIN')
 latest=entry.module(c.OLD/'latest109.py','generic_daily_latest109')
 writer_raw=entry.WRITER.read_bytes();need(hashlib.sha256(writer_raw).hexdigest()=='2ce1518f6f56213fb90b4161e1a2445264568736689a767a06b5d39d6fefa168','ORIGINAL_WRITER_PIN')
 writer_source=writer_raw.decode();old_status='DIRECT_TDX_FULL_RECOMPUTE_SELECTED_PARQUET_FULL_ROUNDTRIP_VERIFIED_NOT_ADMISSION';need(writer_source.count(old_status)==1,'WRITER_STATUS_SINGLE_SITE');writer_source=writer_source.replace(old_status,'SAME_BASIS_NEXT_SESSION_PARQUET_FULL_ROUNDTRIP_VERIFIED_NOT_ADMISSION');writer=types.ModuleType('generic_daily_writer');writer.__file__=str(entry.WRITER);sys.modules[writer.__name__]=writer;exec(compile(writer_source,str(entry.WRITER),'exec'),writer.__dict__);writer.EVENT_DATES=(str(doc['target_date']),);writer.CALCULATION_ASOF=str(doc['target_date']);writer.VERSION='SAME_BASIS_NEXT_SESSION_LONG13_META6_V1'
 mods,schema=writer.load_dependencies();wpins=json.loads(w.PINS_PATH.read_bytes());mods['reader']=w.load(wpins['reader_ref'],'generic_daily_native_reader')
 fds=[];monitor=None;con=None;created_output=False;out=RUNS/name;results=[];failures=[];retained=[];oldterm=signal.getsignal(signal.SIGTERM)
 try:
  signal.signal(signal.SIGTERM,runner.stop_signal)
  for lock in w.LOCKS:
   fd=os.open(ROOT/lock,os.O_RDWR|os.O_NOFOLLOW);fds.append(fd);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  locked_doc,locked_pin,locked_selections=contract(path,sha,review_path);need(locked_doc==doc and locked_pin==pin and locked_selections==selections,'LOCKED_CONTRACT_CHANGED');input_refs=verify_snapshots(doc,pin,review_pin)
  need(not out.exists(),'NO_OVERWRITE')
  # One immutable attempt per day+symbol. Never erase failed/uncertain claims.
  for previous in RUNS.glob('run_*/STARTED.json'):
   old=json.loads(previous.read_bytes())
   if old['target_date']==doc['target_date']:
    need(not set(old['symbols']) & {r['symbol'] for r in doc['inputs']},'PRIOR_ATTEMPT_INSPECT_OUTCOME_FIRST')
  RUNS.mkdir(exist_ok=True);out.mkdir();created_output=True;(out/'stocks').mkdir();(out/'spill').mkdir()
  entry.save(out/'STARTED.json',{'status':'SERIAL_NEXT_SESSION_STARTED','target_date':doc['target_date'],'symbols':[r['symbol'] for r in doc['inputs']],'contract_ref':pin,'review_ref':review_pin,'loaded_code_refs':LOADED_CODE_REFS,'input_snapshot_refs':input_refs,'owner_ref':ref(__file__),**c.FLAGS})
  monitor=runner.make_monitor(w,out);monitor.locks=[(ROOT/n,fd,os.fstat(fd).st_dev,os.fstat(fd).st_ino) for n,fd in zip(w.LOCKS,fds)];monitor.refresh_root_budget();monitor.start()
  connections=runner.FreshConnections(mods['reader'],monitor.gate);native=runner.NativeRunner(monitor,[sys.executable,'-B',str(c.OLD/'latest109.py'),'--worker']);latest.subprocess=types.SimpleNamespace(run=native.run)
  sys.path.insert(0,str(ROOT/'handoff/unified_candidate_20261102'));import producer
  formulas,_=producer.module_candidates();compute=latest.build(producer,formulas);provider=c.Provider(monitor.gate)
  for item in doc['inputs']:
   monitor.gate();symbol=item['symbol'];stock=out/'stocks'/symbol;stock.mkdir();monitor.set_current(stock);started=time.monotonic()
   entry.save(stock/'STARTED.json',{'symbol':symbol,'target_date':doc['target_date'],'outcome':'UNKNOWN_UNTIL_TERMINAL'})
   try:
    prior=selections[symbol].get('continuation_ref')
    if prior is None:
     facts=json.loads(c.checked(item['input_ref']));need(facts['status']=='VERIFIED_NO_VALID_BAR','NO_CONTINUATION_REVIEWED_RECOVERY_REQUIRED');c.checked(facts['no_bar_evidence_ref'])
     prepared={'status':'RETAINED_NO_VALID_BAR','symbol':symbol,'event_date':selections[symbol]['event_date'],'prior_selection':selections[symbol],**c.FLAGS}
    else:prepared=provider.prepare(prior,item['input_ref'],item['input_ref']['sha256'])
    if prepared['status']=='RETAINED_NO_VALID_BAR':retained.append(entry.save(stock/'RETAINED.json',prepared))
    else:
     row,facts,bundle=compute_prepared(prepared,compute)
     state_ref=entry.save_bytes(stock/'continuation.json.gz',gzip.compress(json.dumps(bundle,ensure_ascii=False,sort_keys=False,separators=(',',':'),allow_nan=False).encode(),mtime=0))
     provenance={'symbol':symbol,'calculation_asof':str(doc['target_date']),'state_bundle_ref':state_ref,'input_provenance':prepared['provenance'],'compute_facts':facts,**c.FLAGS}
     con=connections.open();monitor.con=con
     try:
      con.execute("SET temp_directory='"+str(out/'spill').replace("'","''")+"'");con.execute("SET max_temp_directory_size='32MB'")
      receipt=writer.write_stock(con,[row],provenance,stock/'parquet',mods,schema,monitor)
     finally:monitor.con=None;con.close();con=None
     removed=entry.remove_committed_temporary_links(stock,receipt)
     results.append(entry.save(stock/'SUCCESS.json',{'status':'COMPUTED_SAME_BASIS_NEXT_SESSION_WITH_CONTINUATION','symbol':symbol,'event_date':str(doc['target_date']),'continuation_ref':state_ref,'parquet_receipt_ref':ref(stock/'parquet/RECEIPT.json'),'temporary_link_cleanup':removed,'compute_facts':facts,'seconds':time.monotonic()-started,**c.FLAGS}))
     del row,bundle
    del prepared;gc.collect()
   except Exception as error:
    if monitor.abort.is_set():raise
    failures.append(entry.save(stock/'FAILED.json',{'status':'UNKNOWN_NO_BLIND_RETRY','symbol':symbol,'target_date':doc['target_date'],'reason':str(error),'type':type(error).__name__,**c.FLAGS}));gc.collect()
   monitor.seal_chunk(stock);need(entry.allocated_bytes(out)<=entry.OUTPUT_BUDGET,'PHYSICAL_OUTPUT_CAP')
  monitor.gate();verify_snapshots(doc,pin,review_pin);contract(path,sha,review_path);entry.save(out/'MANIFEST.json',{'status':'ATTEMPT_COMPLETE_AWAIT_INDEPENDENT_SAMPLE','target_date':doc['target_date'],'scope_count':len(doc['inputs']),'successes':results,'retained':retained,'failures':failures,'resource_facts':monitor.facts(),'contract_ref':pin,'source_review_ref':review_pin,'loaded_code_refs':LOADED_CODE_REFS,**c.FLAGS})
 except BaseException as error:
  record_interruption(entry,out,created_output,error,results,failures)
  raise
 finally:
  if con is not None:con.close()
  if monitor is not None:monitor.stop()
  for fd in reversed(fds):os.close(fd)
  signal.signal(signal.SIGTERM,oldterm)
 return {'output':str(out),'success':len(results),'retained':len(retained),'failed':len(failures)}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--contract',required=True);p.add_argument('--expected-contract-sha256',required=True);p.add_argument('--review');p.add_argument('--output');p.add_argument('--preflight',action='store_true');a=p.parse_args()
 if a.preflight:
  result=preflight(a.contract,a.expected_contract_sha256,a.review);print(json.dumps(result,ensure_ascii=False));sys.exit(0 if result['can_execute'] else 2)
 need(a.review is not None and a.output is not None,'REVIEW_AND_OUTPUT_REQUIRED');print(json.dumps(run(a.contract,a.expected_contract_sha256,a.review,a.output),ensure_ascii=False))

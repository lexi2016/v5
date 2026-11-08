"""Isolated historical experiment owner, not original or production registration."""
import argparse,pathlib,sys,importlib.util,json,gzip,hashlib,fcntl,os,types,time,shutil

def load(path,name,sha=None):
 raw=path.read_bytes()
 if sha and hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('SOURCE_PIN:'+name)
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;# Execute the verified snapshot without reopening the path.
 exec(compile(raw,str(path),'exec'),m.__dict__);return m

def seal_terminal(path,report):
 # Publish complete immutable bytes; leave evidence on an uncertain commit.
 raw=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False).encode()
 temp=path.with_name(path.name+'.pending')
 fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as stream:
  stream.write(raw);stream.flush();os.fsync(stream.fileno())
 os.link(temp,path,follow_symlinks=False);os.unlink(temp)
 directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(directory)
 finally:os.close(directory)

def run(project,isolated,adapter_dir,input_wire,out):
 if out.exists():raise ValueError('EXISTING_ATTEMPT_INSPECT_NO_RETRY')
 out.mkdir();(out/'spill').mkdir();stock=out/'stock';stock.mkdir()
 report={'production_allowed':False,'source_admission':False,'selection_admission':False,'scope':'ISOLATED_ONE_HISTORICAL_STOCK','original_owner_restored':False}
 monitor=None;con=None;lockfd=None;lock_acquired=False
 try:
  adapter=load(adapter_dir/'latest109_rebuild.py','registered_rebuild','3a4a960fd2995d35298474f52b7cd3006ef35cc4de673c552e0290f75d8226e2')
  candidate=adapter.load(isolated/'handoff/latest109_rebuild_v1_20261106/latest109_candidate.py',isolated/'handoff/panel_field_algorithms_20261102/foundation_action_candidate/ACTION_RULES.json')
  source=load(project/'handoff/unified_candidate_20261102/source.py','source','5f5932db843a723e976dbea26bd79e05b1a2f494228ed2462fd5403c1d6ffe35')
  regression=load(isolated/'handoff/latest109_rebuild_v1_20261106/real_regression_301683.py','regression','01966d226fcbdf060b43b1e8d787a1b91e3147f4171583f07273edb0665633ea')
  bridge_module=load(project/'handoff/portable_par_reader_v1_20261106/portable_par_reader.py','bridge','1011b538bc888723cee4129a8b0161420064dc292d7a04a689578fdcb0077470')
  bridge=bridge_module.Bridge(project);bridge.load_code();bridge.load_runtime();bridge.gate()
  runner=load(project/'handoff/panel109_remaining577_direct_parquet_20261105/run577_v3.py','runner','ddbd0aa13d1892750e3626be82a5f0f46bfaea9ae0f142a6d4b9aefc700ef586')
  w=load(project/'handoff/panel109_isolated_chunks_20261105T1008/writer_1g.py','monitor','5b59d8ffefe98e357e11216d2299158a066fbca3a8c6c71a7b3a445068876f45')
  # Separate loaded instance only. Never lower original limits; raise to strict reader floor.
  w.ROOT=out;w.MEMORY_FLOOR=max(w.MEMORY_FLOOR,bridge_module.MIN_MEMORY);w.START=max(w.START,w.MEMORY_FLOOR+112*2**20)
  runner.check_start(w.available(),shutil.disk_usage(out).free);w.check_resources(w.available(),shutil.disk_usage(out).free)
  if w.available()<w.START:raise ValueError('STRICT_START_HEADROOM')
  lockpath=out.parent/'ISOLATED_OWNER.lock';lockfd=os.open(lockpath,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600);fcntl.flock(lockfd,fcntl.LOCK_EX|fcntl.LOCK_NB);lock_acquired=True
  fd2=os.open(lockpath,os.O_RDWR|os.O_NOFOLLOW)
  try:
   try:fcntl.flock(fd2,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:report['second_lock_claim_rejected']=True
   else:raise ValueError('DUPLICATE_LOCK_CLAIM')
  finally:os.close(fd2)
  monitor=runner.make_monitor(w,out);st=os.fstat(lockfd);monitor.locks=[(lockpath,lockfd,st.st_dev,st.st_ino)];monitor.set_current(stock);monitor.start()
  raw=input_wire.read_bytes();d=json.loads(gzip.decompress(raw));report['input']={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'symbol':d['symbol'],'date':d['actual_last_date']}
  rows=source.normalize([{'trade_date':b['date'],'ohlcv':{'trade_date':b['date'],**{k:b[k] for k in ('open','high','low','close','volume')}},'values':b['original_values']}for b in d['bars']],d['symbol'])
  context={'symbol':d['symbol'],'currency':'CNY','asof':rows[-1]['event_date'],'observation_date':'20261108','prefix_complete':True}
  mods,_=candidate.producer.module_candidates();prior=regression.original_state(mods,rows[:-1]);checkpoint={'test_only_original_history_initialization':True,'state':prior,'prefix_sha256':adapter.digest(rows[:-1])}
  cp=stock/'CHECKPOINT.json';w.save(cp,checkpoint);cpraw=cp.read_bytes();cppin=hashlib.sha256(cpraw).hexdigest();cold=json.loads(cpraw)
  native=runner.NativeRunner(monitor,[sys.executable,'-B',str(candidate.__file__),'--worker']);candidate.subprocess=types.SimpleNamespace(run=native.run)
  compute=adapter.build(candidate,candidate.producer,mods,original_monitor_gate=monitor.gate)
  current,facts=compute(rows,context,prior_state=cold['state'],checkpoint_prefix_sha256=cold['prefix_sha256']);monitor.gate()
  if hashlib.sha256(cp.read_bytes()).hexdigest()!=cppin:raise ValueError('CHECKPOINT_CHANGED')
  writer=bridge.writer;writer.ROOT=out;writer.EVENT_DATES=(context['asof'],);writer.CALCULATION_ASOF=context['asof'];writer.VERSION='ISOLATED_REBUILD_HISTORICAL_LONG13_META6_V1'
  con=bridge.db.connect(':memory:');con.execute('SET threads=1');con.execute("SET memory_limit='96MB'");con.execute("SET temp_directory='"+str(out/'spill')+"'");con.execute("SET max_temp_directory_size='32MB'");monitor.con=con
  provenance={'symbol':context['symbol'],'calculation_asof':context['asof'],'observation_date':context['observation_date'],'source_kind':'HISTORICAL_DISPLAY_RESEARCH_FIXTURE','input_ref':report['input'],'checkpoint_sha256':cppin,'production_allowed':False}
  receipt=writer.write_stock(con,[current],provenance,stock/'parquet',bridge.mods,bridge.schema,monitor);con.close();con=None;monitor.con=None
  # Fresh connection and original codec reconstruct both original output and context.
  monitor.gate();con=bridge.db.connect(':memory:');monitor.con=con;con.execute('SET threads=1');con.execute("SET memory_limit='96MB'");monitor.gate()
  fields=con.execute('SELECT * FROM read_parquet(?) ORDER BY symbol,event_date,field_name',[str(stock/'parquet/field_rows.parquet')]).fetchall();meta=con.execute('SELECT * FROM read_parquet(?)',[str(stock/'parquet/row_metadata.parquet')]).fetchone()
  monitor.gate();mapping=writer.DateMapping(bridge.mods['single_mapping'],bridge.mods['pool_mapping']);decoded=mapping.decode(meta,fields,bridge.schema,bridge.mods['core'],bridge.mods['transport'],bridge.mods['comparator'])
  if not bridge.mods['comparator'].exact(decoded['result'],current) or not bridge.mods['comparator'].exact(decoded['original_context_record'],provenance):raise ValueError('COLD_READ_PARITY')
  report.update(status='PASS_ISOLATED_NATIVE109_ORIGINAL_WRITER_COLD_READ',fields=len(fields),metadata_rows=1,native_calls=native.calls,native_completed=native.completed,original_writer_receipt=receipt,checkpoint_sha256=cppin,checkpoint_initialization='TEST_ONLY_HISTORY_CAPTURE_NOT_PRODUCTION_PERSISTED_PRIOR',facts=facts)
 except Exception as e:
  import traceback
  report.update(status='FAILED_OR_BLOCKED_PRESERVED',error=type(e).__name__+':'+str(e),traceback=traceback.format_exc())
 finally:
  cleanup=[]
  try:
   if con is not None:con.close()
  except Exception as e:cleanup.append('CONNECTION:'+repr(e))
  try:
   if monitor is not None:monitor.con=None;monitor.stop();report['monitor']=monitor.facts()
  except Exception as e:cleanup.append('MONITOR:'+repr(e))
  if cleanup:report.update(status='CLEANUP_UNCERTAIN_INSPECT_NO_RETRY',cleanup_errors=cleanup)
  report['lock_held_during_terminal']=lock_acquired
  try:
   # Keep the existing lock domain until terminal publication and directory sync.
   seal_terminal(out/'RESULT.json',report)
  finally:
   if lockfd is not None:os.close(lockfd)
  # Only the returned/printed result can attest to the subsequent release.
  report['isolated_lock_released']=lock_acquired
  print(json.dumps({k:v for k,v in report.items() if k not in ('traceback','facts','original_writer_receipt')},ensure_ascii=False))
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',type=pathlib.Path,required=True);p.add_argument('--isolated',type=pathlib.Path,required=True);p.add_argument('--adapter-dir',type=pathlib.Path,required=True);p.add_argument('--input-wire',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();r=run(a.project,a.isolated,a.adapter_dir,a.input_wire,a.out);sys.exit(0 if r["status"].startswith("PASS_") else 1)

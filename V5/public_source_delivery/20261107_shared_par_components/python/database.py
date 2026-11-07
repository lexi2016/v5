"""Immutable SQLite metadata/reference catalog. Never executes owners or changes Par."""
import contextlib,datetime,fcntl,hashlib,json,os,pathlib,sqlite3,stat,shutil
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PINS=None  # Private inputs deliberately excluded; not a production binding.
def checked(pin):
 p=ROOT/pin['path']
 if p.is_symlink() or not p.resolve().is_relative_to(ROOT):raise ValueError('PATH')
 if pin['bytes']>32*1024**2:raise ValueError('RESOURCE_SIZE')
 with p.open('rb') as f:
  before=os.fstat(f.fileno()); raw=f.read(pin['bytes']+1);after=os.fstat(f.fileno())
 if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns) or len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('INPUT_CHANGED_OR_SHA')
 return json.loads(raw)
def connect(path=None):
 if path is None and PINS is None:raise ValueError("PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING")
 p=pathlib.Path(path or HERE/'catalog.sqlite3').resolve()
 c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=2)
 c.execute('pragma query_only=on');c.execute('pragma trusted_schema=off');c.row_factory=sqlite3.Row
 return c
SCHEMA='''
PRAGMA foreign_keys=ON;
CREATE TABLE artifact(role TEXT PRIMARY KEY,path TEXT NOT NULL,bytes INTEGER NOT NULL,sha256 TEXT NOT NULL,verification TEXT NOT NULL);
CREATE TABLE panel(symbol TEXT PRIMARY KEY,name TEXT,actual_date TEXT,source_family TEXT,owner_outcome TEXT,status TEXT,history_bars INTEGER,selection_version TEXT,source_date TEXT,observation_date TEXT,artifact_sha TEXT,record_json TEXT NOT NULL);
CREATE TABLE layer(symbol TEXT REFERENCES panel(symbol),group_name TEXT,layer_name TEXT,state TEXT CHECK(state IN ('TRUE','FALSE','UNKNOWN')),PRIMARY KEY(symbol,group_name,layer_name));
CREATE TABLE par_reference(symbol TEXT PRIMARY KEY REFERENCES panel(symbol),baseline_date TEXT,continuation_path TEXT,continuation_sha TEXT,parquet_receipt_path TEXT,parquet_receipt_sha TEXT,verification TEXT,record_json TEXT);
CREATE TABLE top200(symbol TEXT PRIMARY KEY REFERENCES panel(symbol),rank INTEGER UNIQUE,actual_date TEXT,change_pct_decimal TEXT,artifact_sha TEXT,record_json TEXT);
CREATE TABLE node(id TEXT PRIMARY KEY,title TEXT,planned_label TEXT,timezone TEXT,execution_state TEXT,run_id TEXT,last_verified_utc TEXT,contract_sha TEXT,definition_json TEXT);
CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE VIEW selected AS SELECT p.* FROM panel p WHERE EXISTS(SELECT 1 FROM layer l WHERE l.symbol=p.symbol AND l.layer_name='after_risk' AND l.state='TRUE');
CREATE VIEW pending AS SELECT p.* FROM panel p WHERE EXISTS(SELECT 1 FROM layer l WHERE l.symbol=p.symbol AND l.layer_name='after_risk' AND l.state='UNKNOWN');
'''
def build(output=None):
 if PINS is None:raise ValueError("PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING")
 out=pathlib.Path(output or HERE/'catalog.sqlite3');out.parent.mkdir(parents=True,exist_ok=True)
 if shutil.disk_usage(out.parent).free<256*1024**2:raise ValueError('DISK_HEADROOM')
 available=next((int(x.split()[1])*1024 for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')),0)
 if available<1024**3:raise ValueError('MEMORY_HEADROOM')
 with (out.parent/(out.name+'.build.lock')).open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if out.exists():raise FileExistsError(out)
  docs={k:checked(v) for k,v in PINS.items()}
  proj,top,contract,cat=(docs[x] for x in ('projection','top200','timeline','baseline_catalog'))
  if len(proj['rows'])!=5575 or len({x['symbol'] for x in proj['rows']})!=5575 or len(top['rows'])!=200 or len(contract['nodes'])!=21:raise ValueError('SCOPE')
  tmp=out.parent/(out.name+'.partial')
  fd=os.open(tmp,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
  c=sqlite3.connect(tmp)
  try:
   c.executescript(SCHEMA)
   for role,pin in PINS.items():c.execute('insert into artifact values(?,?,?,?,?)',(role,pin['path'],pin['bytes'],pin['sha256'],'LOCAL_BYTES_SHA_VERIFIED'))
   for row in proj['rows']:
    c.execute('insert into panel values(?,?,?,?,?,?,?,?,?,?,?,?)',tuple(row.get(k) for k in ('symbol','name','actual_date','source_family','owner_outcome','status','history_bars'))+(proj['selection_version'],proj['source_date'],proj['observation_date'],PINS['projection']['sha256'],json.dumps(row,ensure_ascii=False)))
    for group,layers in row['layers'].items():
     for layer,state in layers.items():c.execute('insert into layer values(?,?,?,?)',(row['symbol'],group,layer,state))
   for row in cat['latest_selections']:
    cp,rp=row.get('continuation_ref') or {},row.get('parquet_receipt_ref') or {}
    c.execute('insert into par_reference values(?,?,?,?,?,?,?,?)',(row['symbol'],row['event_date'],cp.get('path'),cp.get('sha256'),rp.get('path'),rp.get('sha256'),'INHERITED_CATALOG_REFERENCE_NOT_PAYLOAD_REVERIFIED',json.dumps(row,ensure_ascii=False)))
   for row in top['rows']:c.execute('insert into top200 values(?,?,?,?,?,?)',(row['symbol'],row['rank'],str(row['actual_date']),row['change_pct_decimal'],PINS['top200']['sha256'],json.dumps(row,ensure_ascii=False)))
   for n in contract['nodes']:c.execute('insert into node values(?,?,?,?,?,?,?,?,?)',(n['id'],n['title'],n['planned_label'],n['timezone'],'UNKNOWN',None,None,PINS['timeline']['sha256'],json.dumps(n,ensure_ascii=False)))
   for key,val in {'schema':'PAR_UNIFIED_METADATA_SQLITE_V1','source_date':proj['source_date'],'scope':'5575_FIXED_REFERENCE','no_buy':True,'physical_par_history_copied':False,'node_states':'UNKNOWN_NO_RUNTIME_EVIDENCE_IMPORTED','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'projection_qualifications':proj['qualifications'],'input_pins':PINS}.items():c.execute('insert into metadata values(?,?)',(key,json.dumps(val,ensure_ascii=False)))
   c.commit()
   if c.execute('pragma integrity_check').fetchone()[0]!='ok' or c.execute('pragma foreign_key_check').fetchall():raise ValueError('INTEGRITY')
  finally:c.close()
  # No-overwrite publication; partial remains only on failed builds for diagnosis.
  os.link(tmp,out);tmp.unlink()
 return out
if __name__=='__main__':print(build())

def summary(date,selection_version,path=None):
 """Bounded metadata API. No market calls, owner execution or source admission."""
 if PINS is None:raise ValueError('PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING')
 if date!='20261106' or selection_version!='MAIN_PLUS_SINA69_407':raise ValueError('UNAVAILABLE_VERSION_NO_FALLBACK')
 with connect(path) as c:
  actual={r[0]:r[1] for r in c.execute('select actual_date,count(*) from panel group by actual_date')}
  return {'schema':'PAR_UNIFIED_METADATA_SUMMARY_V1','source_date':date,'selection_version':selection_version,'physical_database':'SQLite','scope_count':c.execute('select count(*) from panel').fetchone()[0],'selected_count':c.execute('select count(*) from selected').fetchone()[0],'any_unknown_count':c.execute('select count(*) from pending').fetchone()[0],'top_count':c.execute('select count(*) from top200').fetchone()[0],'actual_date_counts':actual,'nodes':[dict(r) for r in c.execute('select id,title,planned_label,timezone,execution_state,run_id,last_verified_utc from node')],'source_payloads_reverified':False,'no_buy':True,'production_allowed':False,'runtime_acceptance':'UNKNOWN','source_pin':PINS['projection']}

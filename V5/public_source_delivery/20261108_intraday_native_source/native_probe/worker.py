"""Exact pinned DuckDB child; synthetic 16-row Parquet only, no stock decoder."""
import hashlib,json,os,shutil,sys,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MEMORY=4563402752 # conservatively retain 4.25 GiB, including potential decoder ceiling
DISK=2415919104 # 2.25 GiB start reserve, stricter than Bridge runtime floor

def gate():
 available=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024
 cap=Path('/sys/fs/cgroup/memory.max');use=Path('/sys/fs/cgroup/memory.current')
 if cap.exists()and use.exists()and cap.read_text().strip()!='max':available=min(available,int(cap.read_text())-int(use.read_text()))
 disk=shutil.disk_usage(ROOT).free
 if available<MEMORY or disk<DISK:raise RuntimeError('NATIVE_FULL_RESOURCE_GATE:'+json.dumps(dict(available=available,disk=disk,required_memory=MEMORY,required_disk=DISK)))
 return dict(available_memory=available,free_disk=disk)

def main():
 gate();out=Path(sys.argv[1]);need=out.resolve()==out and out.parent.name.startswith('owner_cl1_candidate_') and out.name=='native_probe'
 if not need or not out.is_dir():raise ValueError('FIXED_E1_TMP_OUTPUT')
 p=ROOT/'handoff/portable_par_reader_v1_20261106/portable_par_reader.py';raw=p.read_bytes()
 if hashlib.sha256(raw).hexdigest()!='1011b538bc888723cee4129a8b0161420064dc292d7a04a689578fdcb0077470':raise ValueError('BRIDGE_SOURCE_PIN')
 m=types.ModuleType('native_probe_original_bridge');m.__file__=str(p);exec(compile(raw,str(p),'exec'),m.__dict__)
 bridge=m.Bridge(ROOT).load_code();gate();db=bridge.load_runtime();gate()
 con=None;closed=False
 try:
  con=db.connect(':memory:');gate()
  for q in ("SET threads=1","SET memory_limit='96MB'","SET max_temp_directory_size='32MB'","SET preserve_insertion_order=false"):con.execute(q);gate()
  sample=out/'synthetic16.parquet'
  if sample.exists():raise ValueError('NO_OVERWRITE')
  con.execute("COPY (SELECT i::BIGINT AS n FROM range(16) t(i)) TO '"+str(sample)+"' (FORMAT PARQUET)");gate()
  if sample.stat().st_size>1024**2:raise ValueError('OUTPUT_CAP')
  rows=con.execute("SELECT count(*),sum(n),min(n),max(n) FROM read_parquet('"+str(sample)+"')").fetchone();gate()
  if rows!=(16,120,0,15):raise ValueError('REAL_NATIVE_READBACK')
 finally:
  if con is not None:con.close();closed=True
 gate();print(json.dumps(dict(status='REAL_NATIVE_SYNTHETIC16_ROUNDTRIP',runtime_version=db.__version__,row_count=16,sum=120,connection_close_returned=closed,parquet_bytes=sample.stat().st_size,parquet_sha256=hashlib.sha256(sample.read_bytes()).hexdigest(),stock_data_used=False,original_formula_calls=0)))
if __name__=='__main__':main()

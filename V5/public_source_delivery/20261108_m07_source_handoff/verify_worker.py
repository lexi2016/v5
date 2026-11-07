"""Fresh subprocess invokes unchanged original M05/RawStore admission only."""
from pathlib import Path
import sys,json,hashlib,tempfile
ROOT=Path(__file__).resolve().parent.parent/'opening_owner_code_restore_20261107/m07'
ENTRY=ROOT/'V5/src/v5_shadow/a_stage_daily.py'
EXPECTED='01c791dee6547e5e1a54ef3c412ac3102dfcafdf7e78be34c702b053f6fb5791'
def main():
 if ENTRY.is_symlink() or any(p.is_symlink() for p in ENTRY.parents) or hashlib.sha256(ENTRY.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('ORIGINAL_ENTRY_CHANGED')
 manifest_path=ROOT.parent/'SOURCE_MANIFEST.json'
 if hashlib.sha256(manifest_path.read_bytes()).hexdigest()!='46b9d71a8cd1f43afe41f472d320d0245f3cf9ff0e5909dc2ea020a657ac8807':raise ValueError('SOURCE_MANIFEST_CHANGED')
 for item in json.loads(manifest_path.read_bytes())['files']:
  if not item['path'].startswith('m07/V5/src/'):continue
  file=ROOT.parent/item['path']
  if file.is_symlink() or any(p.is_symlink() for p in file.parents):raise ValueError('DEPENDENCY_SYMLINK')
  data=file.read_bytes()
  if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('DEPENDENCY_CHANGED')
 sys.path.insert(0,str(ROOT/'V5/src'))
 import v5_shadow.a_stage_daily as m
 request=json.loads(sys.stdin.buffer.read(1048577))
 m._load_owner() # verifies complete original 97-file closure before loading
 with tempfile.TemporaryDirectory(prefix='m07-source-admission-') as t:
  roots,originals=m._snapshots(request,Path(t))
  m._guard((Path(t),))
  spec,pool,raw,rows=m._admit(request,roots)
  for key,files in originals.items():
   for name,data in files.items():
    if m._bytes(m._path(roots[key],name))!=data:raise ValueError('ORIGINAL_READER_MUTATED_INPUT')
  m._owner_sources()
  known_synthetic=any('SYNTHETIC' in str(v).upper() for v in [raw['source_id'],*raw['source_evidence']])
  result=dict(status='VERIFIED',known_synthetic=known_synthetic,pool_codes=sorted(pool.codes),source_id=raw['source_id'],rows=len(rows),missing_symbols=raw['missing_symbols'],
   recording={k:raw[k] for k in ('run_id','artifact_sha256','manifest_sha256','receipt_sha256')})
 return result
if __name__=='__main__':
 try:print(json.dumps(main(),sort_keys=True))
 except Exception as e:print(json.dumps(dict(status='BLOCKED',reason=str(e))));raise SystemExit(2)

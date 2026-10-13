"""Exact two-file patch; use separate isolated copies of API and frontend releases."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--api-checkout',required=True);p.add_argument('--frontend-root',required=True);a=p.parse_args()
source=Path(__file__).resolve().parent;manifest=json.loads((source/'PREIMAGE.json').read_text());api=Path(a.api_checkout).resolve();web=Path(a.frontend_root).resolve()
targets={'V5/src/v5_shadow/m14_readonly.py':api/'V5/src/v5_shadow/m14_readonly.py','frontend/src/components/M14SavedRebound.vue':web/'src/components/M14SavedRebound.vue'}
def digest(path):
 if path.is_symlink() or not path.is_file():raise SystemExit('REGULAR_FILE_REQUIRED: '+str(path))
 return hashlib.sha256(path.read_bytes()).hexdigest()
if digest(web/'src/api/m14SavedRebound.ts')!=manifest['unchanged_api_sha256']:raise SystemExit('UNKNOWN_API_CONTRACT_PREIMAGE')
updates=[]
for name,target in targets.items():
 pins=manifest['files'][name]
 if digest(target)!=pins['before_sha256']:raise SystemExit('UNKNOWN_PREIMAGE: '+name)
 after=source/'files'/name
 if digest(after)!=pins['after_sha256']:raise SystemExit('CANDIDATE_SHA_MISMATCH: '+name)
 updates.append((target,after.read_bytes()))
for target,data in updates:target.write_bytes(data)
print(json.dumps(manifest['files'],indent=2))

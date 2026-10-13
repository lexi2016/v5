"""Apply to an isolated copy of the deployed d3 research checkout only."""
import hashlib,json,sys
from pathlib import Path
source=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve()
manifest=json.loads((source/'DATE_QUEUE_PATCH.json').read_text())['files']
updates=[]
for relative,pins in manifest.items():
 target=root/relative
 if target.is_symlink():raise SystemExit('SYMLINK_REFUSED: '+relative)
 before=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
 if before!=pins['before_sha256']:raise SystemExit('UNKNOWN_PREIMAGE: '+relative)
 data=(source/relative).read_bytes()
 if hashlib.sha256(data).hexdigest()!=pins['after_sha256']:raise SystemExit('CANDIDATE_HASH_MISMATCH: '+relative)
 updates.append((target,data))
for target,data in updates:
 target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
print(json.dumps(manifest,indent=2))

"""Verify delivered bytes without executing an owner or contacting a service."""
import hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parent
manifest=json.loads((BASE/'RELEASE.json').read_bytes())
for item in manifest['files']:
 path=BASE/item['path']
 if path.is_symlink() or not path.is_file():raise SystemExit('RELEASE_PATH:'+item['path'])
 raw=path.read_bytes()
 if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:raise SystemExit('RELEASE_BYTES:'+item['path'])
print('PASS',len(manifest['files']),'release files')

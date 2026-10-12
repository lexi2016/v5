"""Call the byte-identical bundled rebound owner in its original isolated process."""
import sys
from pathlib import Path
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import subprocess
from v5_shadow.digests import canonical_bytes, MAX_JSON_BYTES

PIN='2d8e38ec61792b3e75581f96318e9c284f72b7ba'


BASE=Path(__file__).resolve().parents[2]
BUNDLED_OWNER=BASE/'vendor/rebound_daily_owner'
DESCRIPTOR=BASE/'contracts/bundled_rebound_owner.json'
DESCRIPTOR_SHA='f3a90c608bc78a79df2eeea0df86bb84254fa1647f0133fb3c267ca4ef6ec539'


def verify_checkout(root=None):
    import hashlib
    from v5_shadow.composition import no_symlinks
    root=no_symlinks(BUNDLED_OWNER if root is None else root)
    if root!=BUNDLED_OWNER:raise ValueError('REBOUND_BUNDLED_OWNER_REQUIRED')
    raw=no_symlinks(DESCRIPTOR).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=DESCRIPTOR_SHA:raise ValueError('REBOUND_OWNER_DESCRIPTOR_SHA')
    descriptor=json.loads(raw)
    if descriptor['source_commit']!=PIN:raise ValueError('REBOUND_OWNER_PIN')
    entries={row['path']:row for row in descriptor['entries']}
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    if actual!=set(entries):raise ValueError('REBOUND_OWNER_FILE_SET')
    for name,row in entries.items():
        path=no_symlinks(root/name);raw=path.read_bytes()
        if not path.is_relative_to(root) or len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('REBOUND_OWNER_SOURCE_SHA:'+name)
    return root


def run_rebound_owner(request,ledger_run_id):
    root=verify_checkout(request.get('owner_checkout'))
    worker=Path(__file__).resolve()
    child=subprocess.run([sys.executable,'-I','-B',str(worker),'--worker'],
        input=canonical_bytes(request),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180,cwd=root)
    if child.returncode:raise ValueError('REBOUND_DAILY_OWNER_FAILED:'+child.stderr.decode(errors='replace')[-2000:])
    if len(child.stdout)>MAX_JSON_BYTES:raise ValueError('REBOUND_DAILY_RESPONSE_SIZE')
    value=json.loads(child.stdout)
    verify_checkout(root)
    from v5_shadow.daily_owner_adapters import rebound_receipt
    return rebound_receipt(request,ledger_run_id,value['result'],value['artifact'])


def worker(request):
    root=verify_checkout(request.get('owner_checkout'))
    # Current helper loaded v5_shadow for JSON contracts; switch the namespace
    # before importing the separate original owner and all its dependencies.
    for name in list(sys.modules):
        if name=='v5_shadow' or name.startswith('v5_shadow.'):del sys.modules[name]
    sys.path.insert(0,str(root/'V5/src'))
    from v5_shadow.rebound_daily import run_rebound_daily
    from v5_shadow.rebound_observation import read_rebound_observation
    result=run_rebound_daily(request['request'],request['output_root'])
    artifact=read_rebound_observation(request['output_root'],result['reference'])
    return dict(result=result,artifact=artifact)


if __name__=='__main__':
    if sys.argv[1:]!=['--worker']:raise SystemExit('worker invocation required')
    raw=sys.stdin.buffer.read(MAX_JSON_BYTES+1)
    if len(raw)>MAX_JSON_BYTES:raise ValueError('REBOUND_DAILY_REQUEST_SIZE')
    sys.stdout.buffer.write(canonical_bytes(worker(json.loads(raw))))

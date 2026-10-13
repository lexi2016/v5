"""Fresh-process original M15/manager saved readers; never rebuild or persist."""
from pathlib import Path
import sys
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import importlib
import json
import os
from v5_shadow.composition import no_symlinks
from v5_shadow.contracts import exact_keys,trade_date,sha
from v5_shadow.digests import canonical_bytes,MAX_JSON_BYTES

def worker(request):
    exact_keys(request,('kind','root','target_date','run_id','artifact_sha256'))
    trade_date(request['target_date']);sha(request['artifact_sha256'])
    root=no_symlinks(request['root'])
    if not root.is_absolute() or not root.is_dir():raise ValueError('M15_ORIGINAL_OWNER_ROOT')
    if request['kind']=='seed':
        from v5_shadow.us_mapping_daily import _Loader,_sources,PIN
        sys.meta_path.insert(0,_Loader(_sources()))
        owner=importlib.import_module('v4.manager_research.us_mapping_research')
        reader=owner._read_saved
        source_pin=PIN
    elif request['kind']=='material':
        from v5_shadow.manager_plan import load_owner,PIN
        owner=load_owner();reader=owner._read_plan;source_pin=PIN
    else:raise ValueError('M15_ORIGINAL_OWNER_KIND')
    store_module=importlib.import_module('v4.manager_research.store')
    io=importlib.import_module('infrastructure.owned_io')
    # Bypass only the constructor's unrelated directory creation. The original
    # Store._read, SafeRoot and original saved-product validators are unchanged.
    store=store_module.ManagerResearchStore.__new__(store_module.ManagerResearchStore)
    store.root=root;store._io=io.SafeRoot(root)
    def deny(event,args):
        if event.startswith(('socket.','subprocess.','os.exec','os.spawn','os.posix_spawn')) or event in ('os.system','os.fork','os.forkpty'):
            raise PermissionError('M15_COLD_NETWORK_PROCESS_FORBIDDEN')
        if event in ('os.mkdir','os.remove','os.rename','os.rmdir','os.chmod','os.chown','os.link','os.symlink','os.truncate','os.utime','os.setxattr','os.removexattr'):
            raise PermissionError('M15_COLD_WRITE_FORBIDDEN')
        if event=='open' and args[2] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            raise PermissionError('M15_COLD_WRITE_FORBIDDEN')
    sys.addaudithook(deny)
    saved=reader(store,request['target_date'])
    field='artifact_sha256' if request['kind']=='seed' else 'sha256'
    if not saved or saved.get('run_id')!=request['run_id'] or saved.get(field)!=request['artifact_sha256']:
        raise ValueError('M15_ORIGINAL_OWNER_IDENTITY')
    attempt=None
    if request['kind']=='material':
        attempt=owner.verified_plan_attempt(store,saved)
        if attempt is None or attempt.get('run_id')!=saved['run_id']:raise ValueError('M15_ORIGINAL_OWNER_ATTEMPT')
    return dict(status='MATCHED',kind=request['kind'],run_id=saved['run_id'],artifact_sha256=saved[field],
                target_date=request['target_date'],owner_source_pin=source_pin,process_id=os.getpid(),
                reader='us_mapping_research._read_saved' if request['kind']=='seed' else 'workspace._read_plan + verified_plan_attempt',
                read_only=True,production_allowed=False,buy_gate_updated=False,orders_sent=False)

if __name__=='__main__':
    raw=sys.stdin.buffer.read(MAX_JSON_BYTES+1)
    if len(raw)>MAX_JSON_BYTES:raise ValueError('M15_COLD_REQUEST_LIMIT')
    print(canonical_bytes(worker(json.loads(raw))).decode())

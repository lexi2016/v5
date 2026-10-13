"""Explicit original-owner execution boundary. No scheduler registration."""
from pathlib import Path
import hashlib
import json
import os
import sys
BASE=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(BASE.parent),str(BASE/'src')]

def guard_outputs(root):
    from v5_shadow.composition import no_symlinks
    # Reject pre-existing aliases before original producer makes its first write.
    for index,path in enumerate(root.rglob('*')):
        if index>100000:raise ValueError('M12_OUTPUT_INVENTORY_LIMIT')
        no_symlinks(path)
    def check(value):
        if isinstance(value,int):return
        path=no_symlinks(Path(os.fsdecode(value)).absolute())
        if not path.is_relative_to(root):raise ValueError('M12_OUTPUT_OUTSIDE_PRIVATE_ROOT')
    def audit(event,args):
        if event=='open':
            mode,flags=args[1],args[2]
            if (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):check(args[0])
        elif event in {'os.mkdir','os.remove','os.rmdir','os.chmod','os.utime'}:check(args[0])
        elif event=='os.rename':check(args[0]);check(args[1])
        elif event in {'os.symlink','os.link'}:raise ValueError('M12_OUTPUT_LINK_REJECTED')
    sys.addaudithook(audit)

def run(request,*,tools=None):
    from v5_shadow.m12_readonly_worker import private_root,project
    from V5.src.v5_shadow.video_fupan_daily import run_video_fupan
    from V5.vendor.video_fupan_baseline.review_core.producer import AcquisitionTools
    root=private_root(request['private_root']);guard_outputs(root)
    result=run_video_fupan(request['trade_date'],private_root=root,tools=tools if tools is not None else AcquisitionTools(),
        source_identity=request['source_identity'],tool_identity=request['tool_identity'],config_identity=request['config_identity'],allow_network=True)
    run_id=result['run_id'];date=request['trade_date']
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    binding=dict(private_root=str(root),trade_date=date,run_id=run_id,data_kind=request['data_kind'],
        manifest_sha256=digest(root/'video_fupan/runs'/date/run_id/'manifest.json'),
        owner_receipt_sha256=digest(root/'review'/date/'runs'/run_id/'receipt.json'))
    return project(binding)

if __name__=='__main__':print(json.dumps(run(json.load(sys.stdin)),ensure_ascii=False))

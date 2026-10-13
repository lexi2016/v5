"""Standalone offline M15 input preparation, original owners and immutable reads.

No source fetching, owner algorithm changes, scheduler activation or trading.
A prepared file hash is integrity evidence, never provenance or PIT evidence.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4
from v5_shadow.composition import no_symlinks
from v5_shadow.contracts import aware, trade_date, exact_keys
from v5_shadow.digests import canonical_bytes, MAX_JSON_BYTES
from v5_shadow.module_api import _open_directory, _read_regular

MARKER='.v5-m15-delivery-root'
MARKER_BYTES=b'v5.m15-delivery-root.v1\n'
FLAGS=dict(RESEARCH_ONLY=True,production_allowed=False,buy_gate_updated=False,orders_sent=False,
           formal_eligible=False,natural_verified=False,full_market_coverage=False)

def _bytes(path):
    path=no_symlinks(path)
    directory=_open_directory(path.parent)
    try: fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
    finally: os.close(directory)
    try:return _read_regular(fd,64*1024*1024)
    finally:os.close(fd)

def _json(path):
    value=json.loads(_bytes(path));canonical_bytes(value);return value

def _new(path,raw):
    path=Path(path);directory=_open_directory(path.parent)
    try: fd=os.open(path.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
    finally:os.close(directory)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())

def _root(value):
    root=no_symlinks(value)
    if not root.is_absolute() or _bytes(root/MARKER)!=MARKER_BYTES:raise ValueError('M15_OUTPUT_NOT_INITIALIZED')
    return root

def initialize(path):
    path=Path(path)
    if not path.is_absolute() or path.exists() or path.is_symlink():raise ValueError('M15_NEW_ABSOLUTE_ROOT_REQUIRED')
    no_symlinks(path.parent);path.mkdir();_new(path/MARKER,MARKER_BYTES)
    (path/'results').mkdir();(path/'attempts').mkdir()
    return {'root':str(path),'status':'INITIALIZED',**FLAGS}

def _binding(spec):
    exact_keys(spec,('root','files'))
    root=no_symlinks(spec['root'])
    if not root.is_absolute() or not root.is_dir():raise ValueError('M15_INPUT_ROOT_INVALID')
    if not isinstance(spec['files'],list) or len(set(spec['files']))!=len(spec['files']):raise ValueError('M15_EXPLICIT_FILE_LIST_REQUIRED')
    files={}
    for name in spec['files']:
        p=Path(name)
        if not name or p.is_absolute() or '..' in p.parts or str(p)!=name:raise ValueError('M15_INPUT_PATH_INVALID')
        files[name]=hashlib.sha256(_bytes(root/p)).hexdigest()
    return {'root':str(root),'files':files}

def prepare(spec):
    required=('mode','target_date','cutoff','us_root','session_date')
    optional=tuple(k for k in ('materials','native_master','archives') if k in spec)
    exact_keys(spec,required+optional)
    if spec['mode'] not in ('seed','both'):raise ValueError('M15_MODE_INVALID')
    trade_date(spec['target_date']);session=trade_date(spec['session_date']);cutoff=aware(spec['cutoff'])
    if cutoff>datetime.now(timezone.utc):raise ValueError('M15_FUTURE_CUTOFF')
    paths=['research/peripherals/manifest.json',f'research/peripherals/{session}/external_finance.json',f'receipts/research/peripherals/{session}/external_finance.json']
    us=_binding(dict(root=spec['us_root'],files=paths))
    inputs={k:(_binding(spec[k]) if spec[k] is not None else None) for k in optional}
    if spec['mode']=='both' and ('materials' not in inputs or inputs['materials'] is None):raise ValueError('M15_MATERIAL_STORE_BINDING_REQUIRED')
    return dict(schema_version='v5.m15.prepared.v1',mode=spec['mode'],target_date=spec['target_date'],cutoff=spec['cutoff'],
                us=us,inputs=inputs,source_origin_verified=False,**FLAGS)

def save_result(root,result,owner_files):
    root=_root(root);run=uuid4().hex;refs={}
    for path in owner_files:
        path=no_symlinks(path)
        if not path.is_relative_to(root):raise ValueError('M15_OWNER_ROOT_MISMATCH')
        refs[str(path.relative_to(root))]=hashlib.sha256(_bytes(path)).hexdigest()
    value=dict(schema_version='v5.m15.saved.v1',delivery_run_id=run,
               saved_at=datetime.now(timezone.utc).isoformat(),result=result,owner_files=refs,**FLAGS)
    raw=canonical_bytes(value);_new(root/'results'/f'{run}.json',raw)
    return dict(run_id=run,sha256=hashlib.sha256(raw).hexdigest(),target_date=result['target_date'])

def read_result(root,reference):
    root=_root(root);exact_keys(reference,('run_id','sha256','target_date'))
    if not re.fullmatch('[0-9a-f]{32}',reference['run_id']) or not re.fullmatch('[0-9a-f]{64}',reference['sha256']):raise ValueError('M15_REFERENCE_INVALID')
    trade_date(reference['target_date']);raw=_bytes(root/'results'/f"{reference['run_id']}.json")
    if hashlib.sha256(raw).hexdigest()!=reference['sha256']:raise ValueError('M15_RESULT_SHA_MISMATCH')
    value=json.loads(raw);canonical_bytes(value)
    if value['delivery_run_id']!=reference['run_id'] or value['result']['target_date']!=reference['target_date']:raise ValueError('M15_RESULT_IDENTITY')
    for k,v in FLAGS.items():
        if value.get(k) is not v:raise ValueError('M15_RESULT_SAFETY')
    for name,digest in value['owner_files'].items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts:raise ValueError('M15_OWNER_PATH_INVALID')
        if hashlib.sha256(_bytes(root/p)).hexdigest()!=digest:raise ValueError('M15_OWNER_BYTES_CHANGED')
    original_cold_readback(root,value)
    return value['result']

def original_cold_readback(root,envelope):
    """Invoke original saved validators on bound output bytes in new processes."""
    result=envelope['result'];seed=result.get('seed') or {}
    if seed.get('schema_version')!='v5.us_mapping_daily.v1':return []
    target=result['target_date'];daily=seed['persisted_daily'];owners=envelope['owner_files']
    requests=[]
    def bound(kind,suffix,run,digest):
        matches=[name for name in owners if name.startswith('attempts/') and name.endswith(suffix)]
        if len(matches)!=1:raise ValueError('M15_ORIGINAL_OWNER_BINDING')
        parent=Path(root)/matches[0][:-len(suffix)]
        requests.append(dict(kind=kind,root=str(parent),target_date=target,run_id=run,artifact_sha256=digest))
    bound('seed',f"us_mapping_research/{target}/runs/{daily['run_id']}.json",daily['run_id'],daily['artifact_sha256'])
    material=result.get('material')
    if material is not None:
        identity=material['readback']
        bound('material',f'workspace_plans/{target}/latest.json',identity['run_id'],identity['plan_sha256'])
    receipts=[]
    for request in requests:
        process=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).with_name('m15_owner_read.py'))],
            input=canonical_bytes(request),capture_output=True,timeout=60,
            env={k:v for k,v in os.environ.items() if not k.startswith(('V4_','V35_'))})
        if process.returncode:raise ValueError('M15_ORIGINAL_OWNER_READ_FAILED:'+process.stderr.decode(errors='replace')[-2000:])
        value=json.loads(process.stdout)
        if (value.get('status')!='MATCHED' or value.get('run_id')!=request['run_id']
                or value.get('artifact_sha256')!=request['artifact_sha256'] or value.get('read_only') is not True):
            raise ValueError('M15_ORIGINAL_OWNER_READ_IDENTITY')
        receipts.append(value)
    return receipts


def list_results(root):
    """Recover lost result receipts without calculating or promoting latest."""
    root=_root(root);refs=[]
    for path in sorted((root/'results').iterdir()):
        if not re.fullmatch(r'[0-9a-f]{32}\.json',path.name):raise ValueError('M15_UNEXPECTED_RESULT_ENTRY')
        raw=_bytes(path);value=json.loads(raw)
        ref=dict(run_id=path.stem,sha256=hashlib.sha256(raw).hexdigest(),target_date=value['result']['target_date'])
        read_result(root,ref);refs.append(ref)
    return refs


def execute(prepared,root):
    from v5_shadow.us_mapping_daily import run_us_mapping
    from v5_shadow.manager_plan import run_manager_plan, _snapshot
    from v5_shadow.current_us_research import coverage_paths
    root=_root(root)
    exact_keys(prepared,('schema_version','mode','target_date','cutoff','us','inputs','source_origin_verified',*FLAGS))
    if prepared['schema_version']!='v5.m15.prepared.v1' or prepared['mode'] not in ('seed','both'):raise ValueError('M15_PREPARED_INVALID')
    for k,v in {**FLAGS,'source_origin_verified':False}.items():
        if prepared[k] is not v:raise ValueError('M15_PREPARED_SAFETY')
    trade_date(prepared['target_date']);cutoff=aware(prepared['cutoff'])
    if cutoff>datetime.now(timezone.utc):raise ValueError('M15_FUTURE_CUTOFF')
    if set(prepared['inputs'])-{'materials','native_master','archives'}:raise ValueError('M15_INPUT_LANE_INVALID')
    if prepared['mode']=='both' and not prepared['inputs'].get('materials'):raise ValueError('M15_MATERIAL_STORE_BINDING_REQUIRED')
    bindings=[prepared['us'],*[b for b in prepared['inputs'].values() if b is not None]]
    for binding in bindings:
        source=no_symlinks(binding['root'])
        if source.is_relative_to(root) or root.is_relative_to(source):raise ValueError('M15_SOURCE_OUTPUT_OVERLAP')
        _snapshot(binding)
    attempt=root/'attempts'/uuid4().hex;attempt.mkdir()
    usout=attempt/'seed';usout.mkdir();_new(usout/'.v5-us-mapping-root',b'v5.us-mapping-root.v1\n')
    seed=run_us_mapping(dict(target_date=prepared['target_date'],now=prepared['cutoff'],
        us_data_root=prepared['us']['root'],us_files=prepared['us']['files'],manager_output_root=str(usout)))
    material=None
    if prepared['mode']=='both':
        # Reuse the original full workspace assembly. No copied parser, invented
        # identity adapter or alternate model is placed on the execution path.
        planout=attempt/'materials';planout.mkdir();_new(planout/'.v5-manager-plan-root',b'v5.manager-plan-root.v1\n')
        daily=seed['persisted_daily'];prefix=f"us_mapping_research/{prepared['target_date']}/"
        names=[prefix+'latest.json',prefix+'runs/'+daily['run_id']+'.json']
        manager=dict(root=str(usout),files={n:hashlib.sha256(_bytes(usout/n)).hexdigest() for n in names})
        inputs=dict(manager=manager,us=prepared['us'],**{k:v for k,v in prepared['inputs'].items() if v is not None})
        request=dict(target_date=prepared['target_date'],now=prepared['cutoff'],action='refresh',view='dynamic',
                     selection_date=None,announcement_date=None,inputs=inputs,rebound=None,manager_output_root=str(planout))
        saved=run_manager_plan(request)
        material=dict(workspace=saved['payload'],readback=saved['readback'],coverage_paths=coverage_paths(saved['payload']),
                      execution_kind='MANUAL_RECOVERY',source_origin_verified=False)
    for binding in bindings:_snapshot(binding)
    result=dict(target_date=prepared['target_date'],mode=prepared['mode'],seed=seed,material=material,
                prepared=prepared,execution_kind='MANUAL_RECOVERY',source_origin_verified=False,**FLAGS)
    owners=list(attempt.rglob('*.json'))
    reference=save_result(root,result,owners)
    # Separate read path verifies the immutable envelope and every saved owner byte.
    if read_result(root,reference)!=result:raise ValueError('M15_COLD_READ_MISMATCH')
    return dict(reference=reference,seed_status=seed['persisted_daily']['status'],
                material_assessment=(material or {}).get('coverage_paths',{}).get('combined_material_assessment_state'),
                owner_file_count=len(owners),**FLAGS)

ROUTE='/api/v5/source-bundle/us-mapping-saved'

def _public(value):
    if isinstance(value,dict):
        return {k:_public(v) for k,v in value.items() if not k.endswith(('_root','_path')) and k not in ('root','path','private_input')}
    if isinstance(value,list):return [_public(v) for v in value]
    if isinstance(value,str) and (value.startswith(('/','file:')) or re.match(r'^[A-Za-z]:[\\/]',value)):return '[local reference omitted]'
    return value

def publication_records(root,reference,config,*,data_kind):
    """Build ordinary immutable module records. P0 alone activates generations."""
    from v5_shadow.digests import sha256_json
    if data_kind not in ('SYNTHETIC','RECORDED_INPUT_REPLAY'):raise ValueError('M15_UNVERIFIED_SOURCE_DATA_KIND')
    result=read_result(root,reference);daily=result['seed']['persisted_daily']
    material=result.get('material');market=((material or {}).get('workspace') or {}).get('us_market_attention') or {}
    diagnostics=market.get('mapping_diagnostics') or {}
    lanes=dict(seed=daily.get('matches'),industry=diagnostics.get('industry'),individual=diagnostics.get('individual'))
    summary=dict(schema_version='v5.m15.public.v1',target_date=result['target_date'],reference=reference,
        mode=result['mode'],seed_status=daily.get('status'),seed_run_id=daily.get('run_id'),
        seed_artifact_sha256=daily.get('artifact_sha256'),seed_coverage=daily.get('coverage'),
        seed_source_status=daily.get('source_status'),seed_gaps=daily.get('gaps'),us_session_date=daily.get('us_session_date'),
        seed_coverage_diagnostics=result['seed'].get('coverage_diagnostics'),
        seed_coverage_scope=daily.get('coverage_scope'),
        seed_recovery_evaluation=result['seed'].get('recovery_evaluation'),
        seed_execution_kind=result['seed'].get('execution_kind'),
        target_date_eligibility=daily.get('target_date_eligibility'),
        material_status=diagnostics.get('assessment_state'),material_reasons=diagnostics.get('assessment_reasons'),
        material_readback=(material or {}).get('readback'),material_input=market.get('research_material_input'),
        material_coverage=(material or {}).get('coverage_paths'),
        lanes={k:len(v) if isinstance(v,list) else None for k,v in lanes.items()},page_size=50,data_kind=data_kind,**FLAGS)
    # Full per-mover diagnostic rows are paged, not truncated or replaced by counts.
    coverage=summary.get('material_coverage')
    if isinstance(coverage,dict):
        import copy
        coverage=copy.deepcopy(coverage)
        for lane in ('industry_material','individual_material'):
            if isinstance(coverage.get(lane),dict):coverage[lane].pop('original_diagnostics',None);coverage[lane].pop('raw_movers',None)
        summary['material_coverage']=coverage
    now=datetime.now(timezone.utc).isoformat();out=[]
    def record(query,payload):
        payload=_public(payload)
        out.append(dict(schema_version='v5.module_response.v1',module_id=config['module_id'],release_id=config['release_id'],
            path=ROUTE,query=query,payload=payload,payload_sha256=sha256_json(payload),source_input_sha256=reference['sha256'],
            data_kind=data_kind,generated_at=now,status_code=200))
    record(dict(date=result['target_date']),summary)
    record(dict(date=result['target_date'],run_id=reference['run_id']),summary)
    for lane,rows in lanes.items():
        if not isinstance(rows,list):continue
        for offset in range(0,max(1,len(rows)),50):
            query=dict(date=result['target_date'],run_id=reference['run_id'],lane=lane,offset=str(offset))
            record(query,dict(schema_version='v5.m15.page.v1',target_date=result['target_date'],reference=reference,lane=lane,
                offset=offset,total=len(rows),rows=rows[offset:offset+50],next_offset=(offset+50 if offset+50<len(rows) else None),**FLAGS))
    return out

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    init=sub.add_parser('init');init.add_argument('--root',required=True)
    listing=sub.add_parser('list');listing.add_argument('--root',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--spec',type=Path,required=True)
    run=sub.add_parser('run');run.add_argument('--request',type=Path,required=True);run.add_argument('--root',required=True)
    read=sub.add_parser('read');read.add_argument('--reference',type=Path,required=True);read.add_argument('--root',required=True)
    export=sub.add_parser('export');export.add_argument('--reference',type=Path,required=True);export.add_argument('--root',required=True);export.add_argument('--module-config',type=Path,required=True);export.add_argument('--data-kind',choices=('SYNTHETIC','RECORDED_INPUT_REPLAY'),required=True)
    args=parser.parse_args()
    try:
        if args.action=='init':value=initialize(args.root)
        elif args.action=='list':value=list_results(args.root)
        elif args.action=='prepare':value=prepare(_json(args.spec))
        elif args.action=='run':value=execute(_json(args.request),args.root)
        elif args.action=='export':value=publication_records(args.root,_json(args.reference),_json(args.module_config),data_kind=args.data_kind)
        else:value=read_result(args.root,_json(args.reference))
    except (ValueError,OSError,RuntimeError,KeyError,TypeError) as error:
        print(canonical_bytes(dict(status='REJECTED',reason=str(error),**FLAGS)).decode());raise SystemExit(2)
    print(canonical_bytes(value).decode())

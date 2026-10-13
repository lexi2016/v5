"""P0 one-shot source entrypoints and publication through the existing module API.

This does not invoke daily_tick or change any manager owner. Missing source is
visible, capture is disabled, and owner results remain semantically unchanged.
"""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from .composition import no_symlinks
from .digests import canonical_bytes,sha256_json,MAX_JSON_BYTES

BASE=Path(__file__).resolve().parents[2]
OWNER_MANIFEST=BASE/'contracts/source_owner_runtime.json'
OWNER_MANIFEST_SHA256='4742067f641a56df84d590c5036c4fd27e1cd7fa974519995589e8ecf7f54465'
STATUS_ROUTE='/api/v5/source-bundle/status'
MODULES=(('M01_A_MARKET','m01'),('M02_HK_MARKET','m02'),('M03_US_MARKET','m03'),('M05_A_PRESELECTION','m05'))
FLAGS=dict(natural_verified=False,formal_eligibility_verified=False,production_allowed=False,buy_gate_updated=False,orders_sent=False)


def owner_root(owner):
    if owner not in {'m01','m02','m03'}:raise ValueError('SOURCE_OWNER_ID')
    root=no_symlinks(BASE/'source_owners'/owner)
    raw=no_symlinks(OWNER_MANIFEST).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=OWNER_MANIFEST_SHA256:raise ValueError('SOURCE_OWNER_MANIFEST_SHA')
    manifest=json.loads(raw)
    entries=[e for e in manifest['entries'] if e['path'].startswith('source_owners/'+owner+'/')]
    if not entries:raise ValueError('SOURCE_OWNER_CLOSURE_MISSING')
    for entry in entries:
        relative=Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('SOURCE_OWNER_PATH')
        path=no_symlinks(BASE/relative);data=path.read_bytes()
        if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
            raise ValueError('SOURCE_OWNER_BYTES_MISMATCH:'+entry['path'])
    return root


class OwnerError(ValueError):
    def __init__(self,kind,message):
        super().__init__(message);self.remote_type=kind


def _call(operation,request):
    owner=operation.split('_')[0]
    root=BASE.parent if owner=='m05' else owner_root(owner)
    worker=Path(__file__).with_name('source_bundle_worker.py')
    proc=subprocess.run([sys.executable,'-I','-B',str(worker),operation,str(root)],
        input=canonical_bytes(request),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=960)
    if len(proc.stdout)>MAX_JSON_BYTES:raise ValueError('SOURCE_OWNER_RESPONSE_LIMIT')
    try:value=json.loads(proc.stdout)
    except ValueError as error:raise OwnerError('InvalidResponse',proc.stderr.decode(errors='replace')[-1000:]) from error
    if proc.returncode:
        raise OwnerError(value.get('error_type','OwnerFailure'),value.get('error','SOURCE_OWNER_FAILED'))
    result=value.get('result')
    if not isinstance(result,dict) or not isinstance(result.get('status'),str):raise ValueError('SOURCE_OWNER_RESULT_CONTRACT')
    # Files must remain the same after the accepted owner's complete execution.
    if owner!='m05':owner_root(owner)
    return result


def _m05(request):
    values=dict(request);assembly=values.get('request',{})
    lanes=assembly.get('lanes',[]) if isinstance(assembly,dict) else []
    if not isinstance(lanes,list) or not any(isinstance(x,dict) and x.get('kind')=='v192' for x in lanes):
        return dict(status='BLOCKED_MISSING_V192_SOURCE')
    gate=values.get('write_gate_context')
    if not isinstance(gate,dict) or set(gate)!={'control_dir','expected_permit_sha256','expected_owner_id','expected_release_sha256','expected_root'}:
        return dict(status='BLOCKED_WRITE_GATE_REQUIRED')
    # Verify the existing run first; missing current oracle provenance must stay
    # an original SOURCE_REJECTED, not be obscured by a historical M01 binding.
    provenance=_call('m05_probe',assembly)
    binding_request=values.pop('m01_binding',None)
    if not isinstance(binding_request,dict):return dict(status='BLOCKED_M01_BINDING_REQUIRED',v192=provenance)
    bound=_call('m01',dict(binding_request,action='read'))
    if bound['binding']['target_date']!=assembly.get('signal_date'):
        return dict(status='BLOCKED_M01_SIGNAL_DATE_MISMATCH',m01_target_date=bound['binding']['target_date'],signal_date=assembly.get('signal_date'))
    if bound['selector']['sha256']!=provenance['panel_sha256']:
        return dict(status='BLOCKED_M01_V192_SELECTOR_SHA_MISMATCH')
    result=_call('m05_publish',values)
    result['source_chain']=dict(m01_binding=bound['binding'],selector_sha256=bound['selector']['sha256'],v192=provenance)
    return result


def run_source_bundle(bundle):
    if (not isinstance(bundle,dict) or set(bundle)!={'schema_version','data_kind','jobs'}
        or bundle['schema_version']!='v5.source_bundle.request.v1'
        or bundle['data_kind'] not in {'SYNTHETIC','RECORDED_INPUT_REPLAY'}
        or not isinstance(bundle['jobs'],dict)
        or set(bundle['jobs'])-{m for m,_ in MODULES}):raise ValueError('SOURCE_BUNDLE_CONTRACT')
    bundle=json.loads(canonical_bytes(bundle));rows=[]
    for module,owner in MODULES:
        request=bundle['jobs'].get(module)
        row=dict(module_id=module,owner_entry=dict(m01='m01_a_source',m02='m02_hk_source',m03='m03_us_source',m05='m05_a_preselection')[owner],**FLAGS)
        if request is None:
            row['status']='BLOCKED_REQUEST_MISSING'
        elif not isinstance(request,dict):
            row['status']='BLOCKED_REQUEST_INVALID'
        elif owner=='m03' and request.get('allow_network_capture',False) is not False:
            row['status']='BLOCKED_CAPTURE_DISABLED'
        else:
            try:
                if owner=='m05' and request.get('request',{}).get('data_kind')!=bundle['data_kind']:
                    raise ValueError('SOURCE_DATA_KIND_MISMATCH')
                result=_m05(request) if owner=='m05' else _call(owner,request)
                row.update(status=result['status'],owner_result=result)
            except Exception as error:
                row.update(status='SOURCE_REJECTED',error_type=getattr(error,'remote_type',type(error).__name__),error=str(error))
        rows.append(row)
    return dict(schema_version='v5.source_bundle.result.v1',status='SOURCE_BUNDLE_ATTEMPTED',
        observed_at=datetime.now(timezone.utc).isoformat(),request_sha256=sha256_json(bundle),
        data_kind=bundle['data_kind'],modules=rows,**FLAGS)


def publish_source_result(result,config,*,expected_generation):
    from .module_api import M04_ROUTE,M07_ROUTE,M11_ROUTE,M12_ROUTE,M16_ROUTE,M17_ROUTE
    routes=config.get('routes')
    allowed={STATUS_ROUTE,M04_ROUTE,M07_ROUTE,M11_ROUTE,M12_ROUTE,M16_ROUTE,M17_ROUTE,
        '/api/v5/source-bundle/hk-preselection','/api/v5/source-bundle/hk-close-review',
        '/api/v5/source-bundle/a-close-replay','/api/v5/source-bundle/hk-stage-observed'}
    if (config.get('module_id')!='source_bundle' or not isinstance(routes,list)
        or STATUS_ROUTE not in routes or set(routes)-allowed):
        raise ValueError('SOURCE_MODULE_ID_REQUIRED')
    from .module_artifacts import publish_generation
    record=dict(schema_version='v5.module_response.v1',module_id='source_bundle',
        release_id=config['release_id'],path=STATUS_ROUTE,query={},payload=result,
        payload_sha256=sha256_json(result),source_input_sha256=result['request_sha256'],
        data_kind=result['data_kind'],generated_at=result['observed_at'],status_code=200)
    return publish_generation(config,[record],expected_generation=expected_generation)


def _m02_saved_public_view(result):
    """Project an original-reader result; never expose private roots/identities."""
    flags=('formal_eligibility_verified','historical_eligible','production_allowed','buy_gate_updated','orders_sent')
    saved=result['saved'];binding=saved['binding'];sources=binding['sources']
    if (result.get('status')!='SOURCE_IDENTITY_ONLY' or result.get('readback_verified') is not True
        or binding.get('purpose')!='SOURCE_IDENTITY_ONLY' or binding.get('temporal_status')!='CANNOT_CONFIRM'
        or any(binding.get(key) is not False for key in flags)
        or set(sources)!={'panel','membership','native'}
        or any(value.get('status')!='VERIFIED' or value.get('pit_verified') is not False for value in sources.values())):
        raise ValueError('M02_SAVED_RESULT_CONTRACT')
    projected={key:binding[key] for key in ('schema','run_id','request_sha256','purpose','temporal_status',*flags)}
    projected['request']={key:binding['request'][key] for key in
        ('target_date','signal_date','eligibility_source_date','cutoff','require_pit')}
    projected['sources']={name:dict(status=value['status'],pit_verified=value['pit_verified'],
        times={key:value['times'][key] for key in ('acquired_at','available_at','captured_at') if key in value['times']},
        identity_metadata_canonical_sha256=sha256_json(value['identity'])) for name,value in sources.items()}
    projected['sources']['membership']['member_count']=len(sources['membership']['identity']['codes'])
    receipt={key:saved['receipt'][key] for key in
        ('schema','target_date','run_id','binding_sha256','request_sha256','created_at')}
    return dict(status=result['status'],readback_verified=True,projection_schema='v5.m02.saved_public_view.v1',
        original_saved_result_sha256=sha256_json(saved),
        saved=dict(binding=projected,receipt=receipt,receiptHash=saved['receiptHash']))


def publish_m02_saved_binding(request,config,*,expected_generation,data_kind='RECORDED_INPUT_REPLAY'):
    """Read only M02, replace only its status row, and use the original route CAS."""
    from .contracts import exact_keys,sha,aware
    from .module_api import (_config,_generation_head,_load_generation,_read_object,
        _validate_record,response_key)
    import os
    request=json.loads(canonical_bytes(request))
    exact_keys(request,('action','private_root','target_date','receipt_hash'))
    if request['action']!='read':raise ValueError('M02_SAVED_READ_REQUIRED')
    if data_kind not in {'SYNTHETIC','RECORDED_INPUT_REPLAY'}:raise ValueError('M02_SAVED_DATA_KIND')
    sha(expected_generation)
    checked,root=_config(config)
    try:
        if _generation_head(root,checked)!=expected_generation:raise ValueError('GENERATION_CONFLICT')
        # Pin the object to this exact generation; read_response would select
        # the then-current head and could admit a different A->B->A predecessor.
        refs=_load_generation(root,checked,expected_generation)['records']
        digest=refs[response_key('source_bundle',STATUS_ROUTE,{})]
        record,_=_read_object(root,digest,checked)
        _validate_record(checked,record,STATUS_ROUTE,{})
    finally:os.close(root)
    previous=record['payload'];rows=previous.get('modules')
    owners=('m01_a_source','m02_hk_source','m03_us_source','m05_a_preselection')
    if (checked['module_id']!='source_bundle' or previous.get('schema_version')!='v5.source_bundle.result.v1'
        or previous.get('status')!='SOURCE_BUNDLE_ATTEMPTED'
        or any(previous.get(key) is not False for key in FLAGS)
        or not isinstance(rows,list) or len(rows)!=len(MODULES)
        or any(not isinstance(row,dict) or row.get('module_id')!=MODULES[i][0]
            or row.get('owner_entry')!=owners[i] or not isinstance(row.get('status'),str) or not row['status']
            or any(row.get(key) is not False for key in FLAGS) for i,row in enumerate(rows))):
        raise ValueError('M02_SAVED_PREDECESSOR_CONTRACT')
    if previous.get('data_kind')!=data_kind or record['data_kind']!=data_kind:
        raise ValueError('M02_SAVED_DATA_KIND_MISMATCH')
    sha(previous['request_sha256']);aware(previous['observed_at'])
    # The pinned original reader owns all receipt, source, and safety checks.
    # Failure propagates before publication; there is no fallback to a build.
    view=_m02_saved_public_view(_call('m02',request))
    result=json.loads(canonical_bytes(previous))
    result['modules'][1]=dict(module_id='M02_HK_MARKET',owner_entry='m02_hk_source',
        status=view['status'],owner_result=view,**FLAGS)
    result['observed_at']=datetime.now(timezone.utc).isoformat()
    result['request_sha256']=sha256_json(dict(operation='M02_ONLY_SAVED_READ',
        request=request,previous_generation=expected_generation,previous_record_sha256=digest))
    result['m02_saved_publication']=dict(operation='M02_ONLY_SAVED_READ',
        previous_generation=expected_generation,previous_record_sha256=digest,
        previous_payload_sha256=record['payload_sha256'],previous_observed_at=previous['observed_at'],
        previous_request_sha256=previous['request_sha256'],retained_modules=[MODULES[i][0] for i in (0,2,3)])
    publication=publish_source_result(result,checked,expected_generation=expected_generation)
    return dict(result=result,publication=publication)


def run_config(config):
    if config.get('enabled') is not True:return dict(status='SOURCE_BUNDLE_DISABLED',**FLAGS)
    from .module_api import _open_directory,_read_at
    import os
    path=no_symlinks(Path(config['request_file']))
    fd=_open_directory(path.parent)
    try:bundle=json.loads(_read_at(fd,None,path.name))
    finally:os.close(fd)
    result=run_source_bundle(bundle)
    if 'publication' in config:
        publication=config['publication']
        result_reference=publish_source_result(result,publication['config'],expected_generation=publication['expected_generation'])
        return dict(result=result,publication=result_reference)
    return result

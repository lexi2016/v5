"""Private process bridge to accepted source entrypoints, without shared imports.

This executable intentionally imports no v5_shadow package until the selected
owner's pinned code path has been installed. It accepts no custom callables.
"""
import dataclasses
import hashlib
import importlib
import json
from pathlib import Path
import sys
import types


def m01(request):
    from v5_shadow import a_source_daily as owner
    values=dict(request)
    action=values.pop('action','create')
    if action=='create':
        binding=owner.create_binding_from_roots(**values)
        relative=owner.binding_relative(binding)
    elif action=='read':
        relative=values['relative']
        binding=owner.read_binding_from_roots(**values)
    else:raise ValueError('M01_SOURCE_ACTION')
    reread=owner.read_binding_from_roots(private_root=values['private_root'],source_root=values['source_root'],relative=relative)
    if reread!=binding:raise ValueError('M01_INDEPENDENT_BINDING_MISMATCH')
    reader=owner.bounded_reader(Path(values['source_root']),owner.read_formula_generation,
                                owner.no_symlinks,owner.FORMULA_GENERATION_POINTER_NAME)
    generation=reader(binding.generation_path,expected_target_date=binding.target_date,require_source=True)
    if owner.project(generation)!=binding:raise ValueError('M01_GENERATION_BINDING_MISMATCH')
    evidence=generation['selector_evidence']
    return dict(status=binding.status,binding=dataclasses.asdict(binding),binding_relative=relative,
        selector=dict(path=str(evidence['path']),sha256=evidence['sha256']),readback_verified=True)


def m02(request):
    from v5_shadow.hk_source_daily import build_binding,read_binding
    values=dict(request);action=values.pop('action','build')
    if action=='read':
        verified=read_binding(**values)
    elif action=='build':
        result=build_binding(**values)
        verified=read_binding(values['private_root'],values['target_date'],receipt_hash=result['receiptHash'])
        if verified!=result:raise ValueError('M02_INDEPENDENT_BINDING_MISMATCH')
    else:raise ValueError('M02_SOURCE_ACTION')
    return dict(status=verified['binding']['purpose'],saved=verified,readback_verified=True)


def m03(request,root):
    from v5_shadow.us_source_daily import _request_from_dict,run_us_source
    values=dict(request)
    if values.get('allow_network_capture',False) is not False:
        raise ValueError('SOURCE_CAPTURE_DISABLED')
    if any(name in values for name in ('owner_root','v5_src','capture_root','development_dates_file','allow_late_post_close')):
        raise ValueError('M03_OWNER_OR_CAPTURE_OVERRIDE_DENIED')
    values.update(owner_root=str(root/'collector_owner'),v5_src=str(root/'V5/src'),allow_network_capture=False)
    return run_us_source(_request_from_dict(values))


def v192_probe(request):
    from v5_shadow.a_preselection import _FrozenLoader,_source_bytes,_guard,_verify_lane,_request
    _request(request)
    lane=next(x for x in request['lanes'] if x['kind']=='v192')
    sys.meta_path.insert(0,_FrozenLoader(_source_bytes()))
    owner=importlib.import_module('upstreams.v3_shared_data.shared_data.v192_selector')
    select=_guard([lane]);select(lane);_verify_lane(lane)
    pool=owner.read_verified_v192_pool(Path(lane['input_root']),target_date=request['target_date'],expected_signal_date=request['signal_date'])
    _verify_lane(lane)
    return dict(status='VERIFIED_EXISTING_V192',panel_sha256=pool.run.manifest['provenance']['panel_sha256'],
        verification=pool.run.verification)


def main():
    operation=sys.argv[1];root=Path(sys.argv[2]);request=json.loads(sys.stdin.buffer.read(16*1024*1024+1))
    sys.path.insert(0,str(root/'V5/src'))
    if operation=='m01':
        if 'infrastructure' in sys.modules:raise ValueError('M01_PRIVATE_NAMESPACE_OCCUPIED')
        package=types.ModuleType('infrastructure');package.__path__=[str(root/'infrastructure')]
        sys.modules['infrastructure']=package
        return m01(request)
    if operation=='m02':return m02(request)
    if operation=='m03':return m03(request,root)
    if operation=='m05_probe':return v192_probe(request)
    if operation=='m05_publish':
        from v5_shadow.a_preselection_daily import build_m05_daily,M05PublicationError
        try:return build_m05_daily(**request)
        except M05PublicationError as error:return error.result
    raise ValueError('SOURCE_OPERATION_UNKNOWN')


if __name__=='__main__':
    try:result=dict(result=main())
    except Exception as error:
        result=dict(error_type=type(error).__name__,error=str(error))
        print(json.dumps(result,sort_keys=True,allow_nan=False));raise SystemExit(1)
    print(json.dumps(result,sort_keys=True,allow_nan=False))

"""Isolated bridge to the fixed, unmodified M06 daily owner and exact reader.

Only 'invoke' writes. 'inspect' and 'read' never claim, publish, or generate.
The parent pins the complete original tree before and after every process.
"""
import json
import os
from pathlib import Path
import sys


def inspect_request(request, registration):
    from v5_shadow import hk_preselection_daily as daily, hk_preselection_verified as verified
    from v5_shadow import hk_preselection as legacy, a_preselection as common
    from v5_shadow.composition import no_symlinks, shadow_root
    from v5_shadow.contracts import aware
    from v5_shadow.digests import sha256_json
    from v5_shadow.hk_preselection_publication import _dependencies
    source=no_symlinks(registration['store_root']);assets=no_symlinks(registration['asset_root'])
    output=shadow_root(Path(registration['private_root']))
    daily._assert_separate(source,output);daily._assert_separate(assets,output)
    dates={k:request[k] for k in ('target_date','signal_date','eligibility_source_date')}
    dates['research_cutoff']=request['owner_contract_cutoff'] if request.get('date_contract')=='CLOSE_TO_NEXT_HK_SESSION_V1' else request['completion_cutoff']
    daily._calendar(dates)
    code=daily._code_manifest();dependencies=daily._dependency_manifest()
    if code['run_ledger.py']!=daily.LEDGER_SHA256:raise ValueError('M06_LEDGER_SOURCE_MISMATCH')
    daily._inventory(source,request['source_files']);daily._inventory(assets,request['files'])
    latest=common._relative(source,'latest.json');existing=False
    if latest.exists():
        value=legacy._json(latest)
        if not isinstance(value.get('entries'),dict):raise ValueError('M06_SOURCE_LATEST_INVALID')
        existing=request['target_date']+'/'+legacy.ROLE in value['entries']
    wanted=request['production_method']=='EXISTING_VERIFIED_POOL'
    if existing!=wanted:
        raise ValueError('M06_EXISTING_POOL_REQUIRED' if wanted else 'M06_GENERATION_REQUIRES_ABSENT_POOL')
    if existing:
        original=daily._source_request(source,dates);source_files=original['files']
        if source_files!=request['source_files']:raise ValueError('M06_SOURCE_INVENTORY_MISMATCH')
        checked=verified.run_verified_hk_preselection(original)
        if checked.get('status')!='ASSEMBLED':raise ValueError('M06_EXISTING_POOL_REJECTED')
        entry=value['entries'][request['target_date']+'/'+legacy.ROLE]
        manifest=legacy._json(common._relative(source,entry['manifest_relative']))
        receipt=legacy._json(common._relative(source,entry['receipt_relative']))
        observed=[manifest['captured_at'],receipt['finished_at']]
    else:
        source_files={p:common._file_sha(common._relative(source,p)) for p in daily._master_paths(source,request['eligibility_source_date'])}
        declared=dict(source_files)
        if latest.exists():declared['latest.json']=common._file_sha(latest)
        if declared!=request['source_files']:raise ValueError('M06_SOURCE_INVENTORY_MISMATCH')
        # Preserve the original generator runtime and asset gates; no model load.
        daily._require_runtime(verified._production_sources())
        packages=dependencies['runtime_dependencies']['packages']
        if all(packages[n]=='MISSING' for n in ('pyarrow','fastparquet')):raise ValueError('M06_PARQUET_RUNTIME_MISSING')
        observed=[]
    import importlib
    master=importlib.import_module('upstreams.v3_shared_data.shared_data.hk_security_master')
    _,master_manifest=master.load_verified_hk_security_master(source,request['eligibility_source_date'])
    observed.append(master_manifest['captured_at'])
    if any(aware(stamp)>aware(request['admission_cutoff']) for stamp in observed):
        raise ValueError('M06_SOURCE_AFTER_ADMISSION')
    if request['files'] or request['execution_mode']!='RECORDED_INPUT_REPLAY':
        layout=daily._asset_layout(assets,request['files'])
        # Existing optional receipts are part of the admitted original bytes,
        # even where the original asset loader only needs the payload.
        for kind in ('panel','model','name'):
            relative=layout.get(kind+'_manifest_relative')
            if relative is None:continue
            pointer=legacy._json(common._relative(assets,kind+'_latest.json'))
            receipts={str(Path(relative).with_name('receipt.json'))}
            for metadata in (pointer,layout[kind+'_manifest']):
                if metadata.get('receipt_relative'):receipts.add(metadata['receipt_relative'])
            for receipt in receipts:
                if common._relative(assets,receipt).exists() and receipt not in request['files']:
                    raise ValueError('M06_REQUIRED_ASSET_RECEIPT')
        asset_request=dict(asset_root=str(assets),asset_files=request['files'])
        if existing:
            asset_request.update({k:manifest['provenance'][k] for k in ('panel_sha256','model_bundle_sha256')})
        daily._cold(asset_request,'--assets')
    input_manifest=dict(dates=dates,execution_mode=request['execution_mode'],data_kind='SOURCE_SNAPSHOT',
        source_files=source_files,asset_files=request['files'])
    identity=dict(lane='hk_preselection',target_date=request['target_date'],input_sha256=sha256_json(input_manifest),
        research_cutoff=request['owner_contract_cutoff'] if request.get('date_contract')=='CLOSE_TO_NEXT_HK_SESSION_V1' else request['completion_cutoff'],code_sha256=sha256_json(code),
        config_sha256=sha256_json(dict(execution_mode=request['execution_mode'],reader=verified.SCHEMA)),
        dependency_sha256=sha256_json(dependencies))
    return dict(computation_identity=identity,input_manifest=input_manifest,
        publication_dependency_sha256=sha256_json(_dependencies()),
        owner_dependency_sha256=sha256_json(dependencies))


def read_product(request,registration,snapshot,reference,run_id):
    from v5_shadow.hk_preselection_publication import read_verified_hk_preselection_reference
    from v5_shadow import run_ledger
    from v5_shadow.digests import sha256_json
    result=read_verified_hk_preselection_reference(registration['private_root'],reference)
    state=run_ledger.read_run(str(Path(registration['private_root'])/'.m06-ledger'),snapshot['computation_identity'])
    saved=state['latest_success'] if state else None
    if (not saved or saved['run_id']!=run_id or saved['status']!='SUCCEEDED'
            or saved['readback_verified'] is not True
            or saved['product_reference']['committed_reference']!=reference
            or reference['producer_computation_identity']!=snapshot['computation_identity']):
        raise ValueError('M06_ORIGINAL_LEDGER_READBACK_MISMATCH')
    producer=saved['product_reference']['producer_receipt']
    if sha256_json(producer)!=reference['producer_reference']['sha256']:
        raise ValueError('M06_LEDGER_PUBLICATION_RECEIPT_MISMATCH')
    if (producer['computation_identity']!=snapshot['computation_identity']
            or producer['input_manifest']!=snapshot['input_manifest']
            or producer['verified_source_reference']!=result['verified_source_reference']):
        raise ValueError('M06_PRODUCER_IDENTITY_MISMATCH')
    method='EXISTING_VERIFIED_POOL' if request['production_method']=='EXISTING_VERIFIED_POOL' else 'FROZEN_MODEL_PRODUCER'
    if (producer['production_method']!=method or producer['model_weights_reverified']!=(method=='FROZEN_MODEL_PRODUCER')
            or result['model_weights_reverified'] is not False or len(result['artifact']['rows'])!=100):
        raise ValueError('M06_METHOD_READBACK_MISMATCH')
    return dict(m06_ledger_run_id=run_id,m06_computation_identity=snapshot['computation_identity'],
        committed_reference=reference,producer_receipt_sha256=sha256_json(producer),
        verified_source_reference=result['verified_source_reference'],artifact_sha256=sha256_json(result['artifact']),
        production_method=producer['production_method'],producer_model_weights_reverified=producer['model_weights_reverified'],
        reader_model_weights_reverified=False,row_count=100,fixture_only=result['fixture_only'],natural_verified=False)


def main():
    root=Path(sys.argv[1]);sys.path.insert(0,str(root/'V5/src'))
    from v5_shadow.digests import MAX_JSON_BYTES,canonical_bytes,sha256_json
    from v5_shadow import hk_preselection_daily as daily
    raw=sys.stdin.buffer.read(MAX_JSON_BYTES+1)
    if len(raw)>MAX_JSON_BYTES:raise ValueError('M06_DAILY_REQUEST_LIMIT')
    envelope=json.loads(raw);request=envelope['request'];registration=envelope['registration']
    action=envelope['action'];snapshot=inspect_request(request,registration)
    if action=='inspect':payload=snapshot
    else:
        if snapshot!=envelope['snapshot']:raise ValueError('M06_BINDING_CHANGED')
        if action=='invoke':
            result=daily.produce_hk02_daily(**{k:registration[k] for k in ('store_root','asset_root','private_root')},
                **{k:request[k] for k in ('signal_date','target_date','eligibility_source_date','files','execution_mode')},
                cutoff=(request['owner_contract_cutoff'] if request.get('date_contract')=='CLOSE_TO_NEXT_HK_SESSION_V1' else request['completion_cutoff']))
            if result['status']!='SUCCEEDED' or result['computation_identity']!=snapshot['computation_identity']:
                raise ValueError('M06_OWNER_IDENTITY_MISMATCH')
            payload=read_product(request,registration,snapshot,result['committed_reference'],result['ledger_run_id'])
            if payload['producer_receipt_sha256']!=sha256_json(result['producer_receipt']):raise ValueError('M06_OWNER_RECEIPT_MISMATCH')
            payload['owner_reused']=result['reused']
        elif action=='read':
            payload=read_product(request,registration,snapshot,envelope['reference'],envelope['m06_ledger_run_id'])
        else:raise ValueError('M06_DAILY_ACTION')
        if inspect_request(request,registration)!=snapshot:raise ValueError('M06_BINDING_CHANGED')
    sys.stdout.buffer.write(canonical_bytes(dict(payload=payload,pid=os.getpid(),request_sha256=sha256_json(envelope),
        python_launch=dict(executable=sys.executable,realpath=str(Path(sys.executable).resolve()),
            prefix=sys.prefix,base_prefix=sys.base_prefix))))


if __name__=='__main__':
    try:main()
    except Exception as error:
        # No private paths or raw exception text leaves this process.
        token=str(error).split(':',1)[0]
        reason=token if token.isidentifier() else 'M06_DAILY_'+type(error).__name__.upper()
        print(json.dumps(dict(status='FAILED',reason=reason)))
        raise SystemExit(1)

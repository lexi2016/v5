"""Frozen HK02 daily owner: exact source snapshot, cold producer, ledger, readback.

No acquisition. Existing qualified exact-day pools are reverified. Missing pools
alone may invoke the unmodified model owner under its exact runtime contract.
"""
import sys
from pathlib import Path
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
import tempfile
import subprocess
from datetime import datetime, timezone, timedelta
from v5_shadow import hk_preselection as legacy
from v5_shadow import hk_preselection_verified as verified
from v5_shadow import a_preselection as common
from v5_shadow.composition import no_symlinks, shadow_root
from v5_shadow.contracts import aware, sha, trade_date
from v5_shadow.digests import canonical_bytes, sha256_json, MAX_JSON_BYTES

LEDGER_SHA256 = 'd3ba8dc00de2525ccfc2756193be1338bb800c796c2302f6c97f525a76b5748e'
MODES = ('NATURAL', 'MANUAL_RECOVERY', 'RECORDED_INPUT_REPLAY')


def _code_manifest():
    names = ('__init__.py', 'hk_preselection_daily.py', 'hk_preselection_verified.py', 'hk_preselection_publication.py',
        'hk_preselection.py', 'a_preselection.py', 'composition.py', 'contracts.py', 'digests.py',
        'provider_evidence.py', 'run_ledger.py', 'module_api.py', 'module_artifacts.py', 'api_gateway.py')
    return {name:hashlib.sha256(no_symlinks(Path(__file__).parent / name).read_bytes()).hexdigest() for name in names}


def _runtime():
    def version(name):
        try:return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:return 'MISSING'
    return {'python':platform.python_version(), 'scikit-learn':version('scikit-learn'), 'joblib':version('joblib')}


def _runtime_dependencies():
    versions={}
    for name in ('numpy','pandas','scikit-learn','joblib','pyarrow','fastparquet'):
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]='MISSING'
    executable=Path(sys.executable).resolve()
    return dict(packages=versions,python=platform.python_version(),
        executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest())


def _dependency_manifest():
    return dict(source_descriptor=verified._production_sources(),runtime_dependencies=_runtime_dependencies())


def _require_runtime(descriptor):
    actual = _runtime()
    if actual != descriptor['producer_runtime']:
        raise ValueError('M06_PRODUCER_RUNTIME_MISMATCH:' + json.dumps(dict(expected=descriptor['producer_runtime'], actual=actual), sort_keys=True))
    return actual


def _inventory(root, files):
    root = no_symlinks(root)
    if not isinstance(files, dict):raise ValueError('M06_INPUT_FILES_INVALID')
    for name,digest in files.items():
        path=common._relative(root,name);sha(digest)
        if common._file_sha(path)!=digest:raise ValueError('M06_INPUT_CHANGED:' + name)
    return dict(files)


def _master_paths(root, eligibility):
    prefix='assets/hk_security_master/'
    latest=legacy._json(common._relative(root,prefix+'latest.json'))
    entry=latest['entries'][eligibility]
    manifest=legacy._json(common._relative(root,prefix+entry['manifest_relative']))
    return [prefix+'latest.json',prefix+manifest['artifact_relative'],prefix+entry['manifest_relative'],prefix+entry['receipt_relative']]


def _source_request(root, dates):
    latest=legacy._json(common._relative(root,'latest.json'))
    entry=latest['entries'][dates['target_date']+'/'+legacy.ROLE]
    paths=['latest.json',*[entry[key] for key in ('artifact_relative','manifest_relative','receipt_relative')],
        *_master_paths(root,dates['eligibility_source_date'])]
    files={name:common._file_sha(common._relative(root,name)) for name in paths}
    manifest=legacy._json(common._relative(root,entry['manifest_relative']))
    receipt=legacy._json(common._relative(root,entry['receipt_relative']))
    expected=dict(role=receipt['role'],run_id=entry['run_id'],artifact_relative=entry['artifact_relative'],
        artifact_sha256=files[entry['artifact_relative']],manifest_sha256=sha256_json(manifest),
        receipt_sha256=files[entry['receipt_relative']])
    return dict(schema_version=verified.SCHEMA,**dates,data_kind='SOURCE_SNAPSHOT',input_root=str(root),files=files,expected_source=expected)


def _copy_snapshot(source, target, files):
    _inventory(source,files)
    for relative,digest in files.items():
        before=common._relative(source,relative);data=before.read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('M06_INPUT_CHANGED:' + relative)
        destination=common._relative(target,relative);destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('xb') as f:f.write(data)
    _inventory(source,files);_inventory(target,files)


def _assert_separate(source, output):
    if source==output or source.is_relative_to(output) or output.is_relative_to(source):
        raise ValueError('HK_PRIVATE_ROOT_OVERLAP')


def _ledger_root(output):
    root=output/'.m06-ledger'
    try:
        root.mkdir()
        with (root/'.v5-daily-run-ledger').open('xb') as stream:stream.write(b'v5.daily-run-ledger.v1\n')
    except FileExistsError:
        pass
    no_symlinks(root)
    if (root/'.v5-daily-run-ledger').read_bytes()!=b'v5.daily-run-ledger.v1\n':raise ValueError('DAILY_LEDGER_MARKER')
    return root


def _calendar(request):
    target=trade_date(request['target_date']);signal=trade_date(request['signal_date'])
    eligibility=trade_date(request['eligibility_source_date']);cutoff=aware(request['research_cutoff'])
    if not signal<target or eligibility>target:raise ValueError('HK_THREE_DATES_INVALID')
    if cutoff.astimezone(timezone(timedelta(hours=8))).strftime('%Y%m%d')!=target:raise ValueError('HK_CUTOFF_DATE_MISMATCH')
    verified._production_sources();sys.meta_path.insert(0,legacy._HKLoader(legacy._source_bytes()))
    calendars=importlib.import_module('contracts.trading_calendar');calendar=calendars.load_market_calendar()
    states=calendars.resolve_market_states(calendar,target)
    if states['hk_securities'].value not in ('FULL_TRADING_DAY','HALF_TRADING_DAY_AM'):raise ValueError('HK_TARGET_NOT_SECURITIES_SESSION')
    if calendars.previous_session(calendar,target,market='hk_securities')!=signal:raise ValueError('HK_SIGNAL_NOT_PREVIOUS_SECURITIES_SESSION')
    return dict(status='CALENDAR_VERIFIED',market_states={k:v.value for k,v in states.items()},
        request_sha256=sha256_json(request),implementation_identity=_code_manifest())


def _asset_layout(root, files):
    """All original pointers, manifests and targets must be declared, including names."""
    paths=[];manifests={}
    for kind,field in (('panel','panel_relative'),('model','bundle_relative'),('name','dictionary_relative')):
        pointer=kind+'_latest.json'
        if kind=='name' and not common._relative(root,pointer).exists():continue
        if pointer not in files:raise ValueError('M06_REQUIRED_ASSET_FILE_MISSING:'+pointer)
        value=legacy._json(common._relative(root,pointer));relative=value['manifest_relative']
        if relative not in files:raise ValueError('M06_REQUIRED_ASSET_FILE_MISSING:'+relative)
        manifest=legacy._json(common._relative(root,relative));target=manifest[field]
        if target not in files:raise ValueError('M06_REQUIRED_ASSET_FILE_MISSING:'+target)
        common._relative(root,target);paths.extend((pointer,relative,target))
        manifests[kind+'_manifest']=manifest;manifests[kind+'_manifest_relative']=relative
    if len(set(paths))!=len(paths):raise ValueError('M06_ASSET_CLOSURE_INVALID')
    return manifests


def _assets_worker(request):
    verified._production_sources();root=no_symlinks(request['asset_root'])
    _inventory(root,request['asset_files']);evidence=_asset_layout(root,request['asset_files'])
    sys.meta_path.insert(0,legacy._HKLoader(legacy._source_bytes()))
    owner=importlib.import_module('upstreams.v3_shared_data.shared_data.hk_0_2')
    assets=owner.load_frozen_hk_0_2_assets(root)
    if request.get('panel_sha256') is not None and request['panel_sha256']!=assets.panel_manifest['panel_sha256']:
        raise ValueError('M06_EXISTING_POOL_PANEL_MISMATCH')
    if request.get('model_bundle_sha256') is not None and request['model_bundle_sha256']!=assets.model_manifest['bundle_sha256']:
        raise ValueError('M06_EXISTING_POOL_MODEL_MISMATCH')
    _inventory(root,request['asset_files']);verified._production_sources()
    return dict(status='ASSET_BYTES_VERIFIED',asset_evidence=evidence,model_weights_reverified=False,
        request_sha256=sha256_json(request),implementation_identity=_code_manifest())


def _producer_worker(request):
    _calendar(request)
    descriptor=verified._production_sources();runtime=_require_runtime(descriptor)
    if datetime.now(timezone.utc)>aware(request['research_cutoff']):raise ValueError('HK_SOURCE_AFTER_CUTOFF')
    store=no_symlinks(request['store_root']);assets=no_symlinks(request['asset_root'])
    _inventory(assets,request['asset_files']);_inventory(store,request['source_files'])
    asset_evidence=_asset_layout(assets,request['asset_files'])
    sources=legacy._source_bytes();sys.meta_path.insert(0,legacy._HKLoader(sources))
    owner=importlib.import_module('upstreams.v3_shared_data.shared_data.hk_0_2')
    master=importlib.import_module('upstreams.v3_shared_data.shared_data.hk_security_master')
    _,master_manifest=master.load_verified_hk_security_master(store,request['eligibility_source_date'])
    if aware(master_manifest['captured_at'])>aware(request['research_cutoff']):raise ValueError('HK_SOURCE_AFTER_CUTOFF')
    # The exact original loader/score/weights/publisher executes here, never a hook.
    outcome=owner.materialize_frozen_hk_0_2(store,assets,signal_date=request['signal_date'],target_date=request['target_date'],
        eligibility_source_date=request['eligibility_source_date'])
    if outcome.get('ok') is not True or outcome.get('status')!='READY':raise ValueError('HK_GENERATOR_NOT_READY')
    pool=owner.read_verified_hk_0_2_pool(store,target_date=request['target_date'],expected_signal_date=request['signal_date'],
        expected_eligibility_source_date=request['eligibility_source_date'])
    for key in ('run_id','artifact_sha256','manifest_sha256','receipt_sha256','artifact_relative'):
        if outcome.get(key)!=pool.run.verification[key]:raise ValueError('M06_IDENTITY_CHAIN_MISMATCH')
    loaded=owner.load_frozen_hk_0_2_assets(assets)
    _inventory(assets,request['asset_files']);_inventory(store,request['source_files']);verified._production_sources()
    return dict(status='READY',original_result=outcome,model_weights_reverified=True,runtime=runtime,runtime_dependencies=_runtime_dependencies(),asset_evidence=asset_evidence,
        panel_sha256=loaded.panel_manifest['panel_sha256'],model_bundle_sha256=loaded.model_manifest['bundle_sha256'],
        request_sha256=sha256_json(request),implementation_identity=_code_manifest())


def _cold(request, mode='--worker'):
    identity=_code_manifest()
    with tempfile.TemporaryDirectory(prefix='v5-hk-producer-cache-') as cache:
        process=subprocess.run([sys.executable,'-I','-B','-X','pycache_prefix='+str(Path(cache).resolve()),str(Path(__file__).resolve()),mode],
            input=canonical_bytes(request),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=600)
    if len(process.stdout)>MAX_JSON_BYTES:raise ValueError('M06_PRODUCER_RESPONSE_TOO_LARGE')
    try:result=json.loads(process.stdout)
    except (ValueError,UnicodeError) as error:raise ValueError('M06_PRODUCER_RESPONSE_INVALID:'+process.stderr.decode(errors='replace')[-2000:]) from error
    if process.returncode!=0:raise ValueError(result.get('reason','M06_PRODUCER_FAILED'))
    if result.get('request_sha256')!=sha256_json(request) or result.get('implementation_identity')!=identity or _code_manifest()!=identity:
        raise ValueError('M06_PRODUCER_IDENTITY_MISMATCH')
    return result


def produce_hk02_daily(*, store_root, asset_root, private_root, signal_date, target_date,
        eligibility_source_date, cutoff, files, execution_mode='MANUAL_RECOVERY'):
    from v5_shadow.hk_preselection_publication import publish_verified_hk_preselection, read_verified_hk_preselection_reference
    from v5_shadow import run_ledger
    if execution_mode not in MODES:raise ValueError('M06_EXECUTION_MODE_INVALID')
    descriptor=verified._production_sources();code=_code_manifest();dependencies=_dependency_manifest()
    if code['run_ledger.py']!=LEDGER_SHA256:raise ValueError('M06_LEDGER_SOURCE_MISMATCH')
    source=no_symlinks(store_root);assets=no_symlinks(asset_root);output=shadow_root(Path(private_root))
    _assert_separate(source,output);_assert_separate(assets,output)
    dates=dict(target_date=trade_date(target_date),signal_date=trade_date(signal_date),eligibility_source_date=trade_date(eligibility_source_date),research_cutoff=cutoff)
    aware(cutoff);_cold(dates,'--calendar');asset_files=_inventory(assets,files)
    latest_path=common._relative(source,'latest.json')
    existing=False
    if latest_path.exists():
        latest=legacy._json(latest_path)
        if not isinstance(latest.get('entries'),dict):raise ValueError('M06_SOURCE_LATEST_INVALID')
        existing=target_date+'/'+legacy.ROLE in latest['entries']
    if existing:
        source_request=_source_request(source,dates)
        checked=verified.run_verified_hk_preselection(source_request)
        if checked['status']!='ASSEMBLED':raise ValueError('M06_EXISTING_POOL_REJECTED:'+checked['reason'])
        source_files=source_request['files']
        if asset_files or execution_mode!='RECORDED_INPUT_REPLAY':
            _asset_layout(assets,asset_files)
            manifest=legacy._json(common._relative(source,latest['entries'][target_date+'/'+legacy.ROLE]['manifest_relative']))
            provenance=manifest['provenance']
            asset_result=_cold(dict(asset_root=str(assets),asset_files=asset_files,
                panel_sha256=provenance['panel_sha256'],model_bundle_sha256=provenance['model_bundle_sha256']),'--assets')
            asset_evidence=asset_result['asset_evidence'];asset_binding_status='FROZEN_ASSET_BYTES_CHECKED'
        else:
            asset_evidence=None;asset_binding_status='NOT_REVERIFIED_RECORDED_INPUT_ONLY'
    else:
        source_files={p:common._file_sha(common._relative(source,p)) for p in _master_paths(source,eligibility_source_date)}
        _require_runtime(descriptor);_asset_layout(assets,asset_files)
        checked=None;asset_evidence=None;asset_binding_status='FROZEN_ASSET_BYTES_CHECKED'
    input_manifest=dict(dates=dates,execution_mode=execution_mode,data_kind='SOURCE_SNAPSHOT',source_files=source_files,asset_files=asset_files)
    identity=dict(lane='hk_preselection',target_date=target_date,input_sha256=sha256_json(input_manifest),research_cutoff=cutoff,
        code_sha256=sha256_json(code),config_sha256=sha256_json(dict(execution_mode=execution_mode,reader=verified.SCHEMA)),
        dependency_sha256=sha256_json(dependencies))
    ledger=_ledger_root(output);claim=run_ledger.claim_run(str(ledger),identity,max_attempts=1)
    trigger=dict(execution_mode=execution_mode,triggered_at=datetime.now(timezone.utc).isoformat(),natural_verified=False)
    if claim['status']=='REUSED_SUCCESS':
        saved=claim['state']['latest_success']['product_reference'];ref=saved['committed_reference']
        readback=read_verified_hk_preselection_reference(str(output),ref)
        _inventory(source,source_files);_inventory(assets,asset_files)
        if _code_manifest()!=code or _dependency_manifest()!=dependencies:raise ValueError('M06_IMPLEMENTATION_CHANGED')
        return dict(status='SUCCEEDED',reused=True,computation_identity=identity,ledger_run_id=claim['state']['latest_success']['run_id'],
            committed_reference=ref,producer_receipt=saved['producer_receipt'],row_count=len(readback['artifact']['rows']),trigger_receipt=trigger,**legacy.SAFETY)
    if claim['status']!='CLAIMED':raise ValueError(claim['status'])
    try:
        with tempfile.TemporaryDirectory(prefix='v5-m06-snapshot-') as temp:
            staging=no_symlinks(Path(temp).resolve());store=staging/'store';store.mkdir();asset_copy=staging/'assets';asset_copy.mkdir()
            _copy_snapshot(source,store,source_files);_copy_snapshot(assets,asset_copy,asset_files)
            if existing:
                request=dict(source_request,input_root=str(store))
                original=dict(checked['source_verification'])
                producer=dict(status='READY',original_result=original,model_weights_reverified=False,production_method='EXISTING_VERIFIED_POOL',asset_evidence=asset_evidence,asset_binding_status=asset_binding_status)
            else:
                worker_request=dict(store_root=str(store),asset_root=str(asset_copy),asset_files=asset_files,source_files=source_files,**dates)
                producer=_cold(worker_request);producer['production_method']='FROZEN_MODEL_PRODUCER';producer['worker_request']=worker_request;producer['asset_binding_status']=asset_binding_status
                request=_source_request(store,dates)
            _inventory(source,source_files);_inventory(assets,asset_files)
            strict=verified.run_verified_hk_preselection(request)
            if strict['status']!='ASSEMBLED':raise ValueError('HK_STRICT_READER_NOT_ASSEMBLED:'+strict['reason'])
            if 'runtime_dependencies' not in producer:producer['runtime_dependencies']=dependencies['runtime_dependencies']
            if producer['runtime_dependencies']!=dependencies['runtime_dependencies']:raise ValueError('M06_RUNTIME_DEPENDENCIES_CHANGED')
            producer['asset_snapshot']=dict(input_root=str(asset_copy),files=asset_files) if asset_files else None
            receipt=dict(schema_version='v5.hk_preselection_producer_receipt.v1',**producer,
                verified_source_reference=request['expected_source'],input_manifest=input_manifest,code_manifest=code,
                dependency_manifest=dependencies,computation_identity=identity,fixture_only=strict['fixture_only'],**legacy.SAFETY)
            # Reader keeps model_weights_reverified=False even when producer proves actual loading.
            if _code_manifest()!=code or _dependency_manifest()!=dependencies:raise ValueError('M06_IMPLEMENTATION_CHANGED')
            ref=publish_verified_hk_preselection(request,bound_root=str(output),producer_receipt=receipt,execution_mode=execution_mode)
            readback=read_verified_hk_preselection_reference(str(output),ref)
            _inventory(source,source_files);_inventory(assets,asset_files)
            if canonical_bytes(readback['artifact'])!=canonical_bytes(strict['artifact']):raise ValueError('M06_ROWS_DIVERGED')
        if _code_manifest()!=code or _dependency_manifest()!=dependencies:raise ValueError('M06_IMPLEMENTATION_CHANGED')
        product=dict(committed_reference=ref,producer_receipt=receipt)
        run_ledger.finish_run(str(ledger),claim,dict(status='SUCCEEDED',product_reference=product,readback_verified=True,
            retry_safe_without_external_effect=False,reason_codes=[]))
        return dict(status='SUCCEEDED',reused=False,computation_identity=identity,ledger_run_id=claim['run_id'],
            committed_reference=ref,producer_receipt=receipt,row_count=100,trigger_receipt=trigger,**legacy.SAFETY)
    except Exception as error:
        run_ledger.finish_run(str(ledger),claim,dict(status='BLOCKED' if 'RUNTIME_MISMATCH' in str(error) else 'FAILED',
            product_reference=None,readback_verified=False,retry_safe_without_external_effect=False,reason_codes=[type(error).__name__+':'+str(error)]))
        raise


if __name__=='__main__':
    try:
        if sys.argv[1:] not in (['--worker'],['--calendar'],['--assets']):raise ValueError('M06_WORKER_MODE_REQUIRED')
        raw=sys.stdin.buffer.read(MAX_JSON_BYTES+1)
        if len(raw)>MAX_JSON_BYTES:raise ValueError('REQUEST_TOO_LARGE')
        operation={'--worker':_producer_worker,'--calendar':_calendar,'--assets':_assets_worker}[sys.argv[1]]
        print(canonical_bytes(operation(json.loads(raw))).decode())
    except Exception as error:
        print(canonical_bytes(dict(status='FAILED',reason=type(error).__name__+':'+str(error))).decode())
        raise SystemExit(1)

"""Explicit byte-preserving import of one already saved native M12 run.

No producer, downloader, ASR, latest selector, schedule or service configuration.
The destination is a new exclusive container; only a verified staging tree is
published as its data root. Failed attempts remain local and are never resumed
or overwritten automatically.
"""
from datetime import datetime,timezone
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import stat
import sys

if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v5_shadow.composition import no_symlinks
from v5_shadow.contracts import exact_keys,sha,trade_date
from v5_shadow.digests import sha256_json
from v5_shadow.m12_readonly import verify_runtime,read_record,ROUTE,BINDING
from v5_shadow.m12_readonly_worker import raw,MAX_META,MAX_ARTIFACT,MAX_TOTAL

VERSION='v5.m12_native_import.v1'
FLAGS=dict(producer_invoked=False,network_used=False,asr_executed=False,natural_verified=False,
           review_completed=False,production_allowed=False,buy_gate_updated=False,orders_sent=False)

def _path(value):
    if not isinstance(value,str) or not value:raise ValueError('M12_IMPORT_PATH')
    return no_symlinks(Path(value))

def _relative(value):
    if not isinstance(value,str) or not value or '\\' in value or '\x00' in value:raise ValueError('M12_IMPORT_REF_PATH')
    path=PurePosixPath(value)
    if not path.parts or path.is_absolute() or '..' in path.parts or str(path)!=value:raise ValueError('M12_IMPORT_REF_PATH')
    if path.parts[0].startswith('.') or path.parts[0]=='video_fupan' or path.name in {'current.json','latest_success.json','native_import.json'}:
        raise ValueError('M12_IMPORT_RESERVED_REF')
    return Path(*path.parts)

def _digest(path,limit=MAX_ARTIFACT):
    path=no_symlinks(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size>limit:raise ValueError('M12_IMPORT_FILE_LIMIT')
        digest=hashlib.sha256();size=0
        while True:
            block=os.read(fd,1024*1024)
            if not block:break
            size+=len(block)
            if size>limit:raise ValueError('M12_IMPORT_FILE_LIMIT')
            digest.update(block)
        if size!=info.st_size:raise ValueError('M12_IMPORT_SOURCE_CHANGED')
        return digest.hexdigest(),size
    finally:os.close(fd)

def _snapshot(request,source):
    # Pin original code before importing its evidence-validation entrypoint.
    verify_runtime()
    from v5_shadow.video_fupan_reader import _read_owner_evidence,VideoReadError
    date=request['trade_date'];run=request['run_id'];base=Path('review')/date/'runs'/run
    manifest_raw=raw(source/base/'manifest.json');receipt_raw=raw(source/base/'receipt.json')
    if hashlib.sha256(manifest_raw).hexdigest()!=request['owner_manifest_sha256']:raise ValueError('M12_IMPORT_MANIFEST_PIN')
    if hashlib.sha256(receipt_raw).hexdigest()!=request['owner_receipt_sha256']:raise ValueError('M12_IMPORT_RECEIPT_PIN')
    owner=json.loads(manifest_raw);receipt=json.loads(receipt_raw)
    if not isinstance(owner,dict) or not isinstance(receipt,dict):raise ValueError('M12_IMPORT_NATIVE_SCHEMA')
    try:checked,receipt_sha=_read_owner_evidence(source,date,run,owner)
    except VideoReadError as error:raise ValueError('M12_IMPORT_NATIVE_EVIDENCE') from error
    if checked!=receipt or receipt_sha!=request['owner_receipt_sha256']:raise ValueError('M12_IMPORT_RECEIPT_CHANGED')
    safety=receipt.get('safety_flags')
    if not isinstance(safety,dict):raise ValueError('M12_IMPORT_NATIVE_SAFETY')
    for key in ('production_allowed','buy_gate_updated','orders_sent'):
        if owner.get(key) is not False or safety.get(key) is not False:raise ValueError('M12_IMPORT_NATIVE_SAFETY')
    if not(receipt.get('status')=='ACQUIRED' and owner.get('discovery_status')=='TARGET_BV_LOCKED' and owner.get('capture_status') in {'CAPTURED','REUSED_CONTENT'} and owner.get('asr_status')=='ASR_REVIEW_REQUIRED'):
        raise ValueError('M12_IMPORT_NATIVE_NOT_QUALIFIED')
    refs=owner.get('artifact_refs')
    if not isinstance(refs,list) or not 1<=len(refs)<=256:raise ValueError('M12_IMPORT_REFS')
    for kind in ('transcript','segment'):
        if sum(isinstance(r,dict) and r.get('kind')==kind for r in refs)!=1:raise ValueError('M12_IMPORT_TEXT_REFS')
    expected={str(base/'manifest.json'):request['owner_manifest_sha256'],str(base/'receipt.json'):request['owner_receipt_sha256']};seen=set();sizes={}
    for ref in refs:
        if not isinstance(ref,dict):raise ValueError('M12_IMPORT_REF')
        relative=str(_relative(ref.get('path')));digest=sha(ref.get('sha256'))
        if relative in seen or (relative in expected and expected[relative]!=digest):raise ValueError('M12_IMPORT_REF_DUPLICATE')
        if 'size' in ref:
            if type(ref['size']) is not int or not 0<=ref['size']<=MAX_ARTIFACT:raise ValueError('M12_IMPORT_REF_SIZE')
            sizes[relative]=ref['size']
        seen.add(relative);expected[relative]=digest
    files=[];total=0
    for relative,digest in sorted(expected.items()):
        actual,size=_digest(source/_relative(relative),min(MAX_ARTIFACT,MAX_TOTAL-total))
        if actual!=digest:raise ValueError('M12_IMPORT_ARTIFACT_SHA')
        if relative in sizes and size!=sizes[relative]:raise ValueError('M12_IMPORT_REF_SIZE')
        files.append(dict(path=relative,sha256=digest,bytes=size));total+=size
    if total>MAX_TOTAL:raise ValueError('M12_IMPORT_TOTAL_LIMIT')
    if _digest(source/base/'manifest.json',MAX_META)[0]!=request['owner_manifest_sha256'] or _digest(source/base/'receipt.json',MAX_META)[0]!=request['owner_receipt_sha256']:
        raise ValueError('M12_IMPORT_NATIVE_CHANGED')
    return owner,files

def _copy_exact(source,target,expected):
    no_symlinks(source);no_symlinks(target)
    target.parent.mkdir(parents=True,exist_ok=True);no_symlinks(target.parent)
    source_fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    destination_fd=None
    try:
        info=os.fstat(source_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size!=expected['bytes']:raise ValueError('M12_IMPORT_SOURCE_CHANGED')
        destination_fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        digest=hashlib.sha256();size=0
        while True:
            block=os.read(source_fd,1024*1024)
            if not block:break
            size+=len(block)
            if size>expected['bytes']:raise ValueError('M12_IMPORT_SOURCE_CHANGED')
            digest.update(block);view=memoryview(block)
            while view:
                written=os.write(destination_fd,view)
                if written<=0:raise OSError('M12_IMPORT_SHORT_WRITE')
                view=view[written:]
        if size!=expected['bytes'] or digest.hexdigest()!=expected['sha256']:raise ValueError('M12_IMPORT_SOURCE_CHANGED')
        os.fsync(destination_fd)
    finally:
        os.close(source_fd)
        if destination_fd is not None:os.close(destination_fd)

def _cold_check(binding):
    config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='m12-native-saved-import',routes=[ROUTE])
    config[BINDING]=binding
    record,_=read_record(config,{'trade_date':binding['trade_date']});payload=record['payload']
    if payload.get('status')!='SAVED_ASR_REVIEW_REQUIRED' or payload.get('reference',{}).get('run_id')!=binding['run_id'] or payload.get('data_kind')!=binding['data_kind']:
        raise ValueError('M12_IMPORT_COLD_READ_REJECTED')

def _binding(request,root,manifest_sha):
    return dict(private_root=str(root),trade_date=request['trade_date'],run_id=request['run_id'],manifest_sha256=manifest_sha,
        owner_receipt_sha256=request['owner_receipt_sha256'],data_kind=request['data_kind'],python_executable=request['python_executable'])

def import_saved_native(request):
    """Read one exact native run; return local-only API binding after validation."""
    try:
        exact_keys(request,('source_root','destination_root','trade_date','run_id','owner_manifest_sha256','owner_receipt_sha256','data_kind','python_executable'))
        trade_date(request['trade_date']);sha(request['owner_manifest_sha256']);sha(request['owner_receipt_sha256'])
        if not isinstance(request['run_id'],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,255}',request['run_id']):raise ValueError('M12_IMPORT_RUN')
        if request['data_kind'] not in {'SYNTHETIC','RECORDED_INPUT_REPLAY'}:raise ValueError('M12_IMPORT_DATA_KIND')
        source=_path(request['source_root']);destination=_path(request['destination_root']);python=Path(request['python_executable'])
        if not python.is_absolute() or '..' in python.parts:raise ValueError('M12_IMPORT_PYTHON')
        if source==destination or source.is_relative_to(destination) or destination.is_relative_to(source):raise ValueError('M12_IMPORT_ROOT_OVERLAP')
        if not source.is_dir() or not destination.parent.is_dir():raise ValueError('M12_IMPORT_ROOT_REQUIRED')
        owner,files=_snapshot(request,source)
        from v5_shadow.video_fupan_store import safe_replace_json
        identity=dict(schema_version=VERSION,trade_date=request['trade_date'],run_id=request['run_id'],owner_manifest_sha256=request['owner_manifest_sha256'],
            owner_receipt_sha256=request['owner_receipt_sha256'],data_kind=request['data_kind'],files=files,
            importer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        import_id=sha256_json(identity);final=destination/'data'
        if destination.exists():
            commit=json.loads(raw(destination/'import.json'))
            receipt_raw=raw(final/'native_import.json');receipt=json.loads(receipt_raw)
            if not isinstance(commit,dict) or not isinstance(receipt,dict):raise ValueError('M12_IMPORT_EXISTING_ROOT')
            if commit.get('schema_version')!=VERSION+'.commit' or receipt.get('schema_version')!=VERSION+'.receipt' or receipt.get('import_id')!=import_id or commit.get('import_id')!=import_id or commit.get('receipt_sha256')!=hashlib.sha256(receipt_raw).hexdigest() or receipt.get('identity')!=identity:
                raise ValueError('M12_IMPORT_EXISTING_ROOT')
            if receipt.get('copy_policy')!='EXACT_ORIGINAL_BYTES' or any(receipt.get(k) is not v for k,v in FLAGS.items()):raise ValueError('M12_IMPORT_EXISTING_ROOT')
            imported_at=datetime.fromisoformat(receipt['imported_at'])
            if imported_at.tzinfo is None or imported_at.utcoffset().total_seconds()!=0:raise ValueError('M12_IMPORT_EXISTING_TIME')
            envelope_raw=raw(final/'video_fupan/runs'/request['trade_date']/request['run_id']/'manifest.json')
            if hashlib.sha256(envelope_raw).hexdigest()!=receipt['wrapper_manifest_sha256']:raise ValueError('M12_IMPORT_EXISTING_ROOT')
            envelope=json.loads(envelope_raw)
            if not isinstance(envelope,dict) or any(envelope.get(k)!=v for k,v in dict(schema_version=VERSION,import_kind='NATIVE_SAVED_IMPORT',import_id=import_id,imported_at=receipt['imported_at'],owner_manifest_sha256=request['owner_manifest_sha256'],owner_receipt_sha256=request['owner_receipt_sha256'],data_kind=request['data_kind']).items()) or any(envelope.get(k) is not v for k,v in FLAGS.items()):raise ValueError('M12_IMPORT_EXISTING_ROOT')
            binding=_binding(request,final,receipt['wrapper_manifest_sha256']);_cold_check(binding)
            return dict(status='REUSED_SAVED_NATIVE',import_id=import_id,imported_at=receipt['imported_at'],binding=binding,**FLAGS)
        # mkdir is an exclusive reservation; no existing destination is replaced.
        destination.mkdir(mode=0o700);stage=destination/'staging';stage.mkdir(mode=0o700)
        for entry in files:_copy_exact(source/_relative(entry['path']),stage/_relative(entry['path']),entry)
        imported_at=datetime.now(timezone.utc).isoformat()
        envelope=dict(import_kind='NATIVE_SAVED_IMPORT',schema_version=VERSION,import_id=import_id,imported_at=imported_at,
            owner_run_id=request['run_id'],owner_manifest=owner,owner_manifest_sha256=request['owner_manifest_sha256'],
            owner_receipt_sha256=request['owner_receipt_sha256'],data_kind=request['data_kind'],**FLAGS)
        wrapper=stage/'video_fupan/runs'/request['trade_date']/request['run_id']
        manifest_sha=safe_replace_json(wrapper/'manifest.json',envelope)
        safe_replace_json(wrapper/'receipt.json',dict(schema_version=VERSION+'.wrapper_receipt',import_kind='NATIVE_SAVED_IMPORT',import_id=import_id,
            imported_at=imported_at,owner_run_id=request['run_id'],manifest_sha256=manifest_sha,producer_invoked=False))
        marker=stage/'.v5-m12-root'
        with marker.open('xb') as stream:stream.write(b'v5.m12-private.v1\n');stream.flush();os.fsync(stream.fileno())
        # The saved reader launches a cold subprocess and calls the unchanged
        # original reader. Only a fully qualified staged result can be published.
        _cold_check(_binding(request,stage,manifest_sha))
        if _snapshot(request,source)!=(owner,files):raise ValueError('M12_IMPORT_SOURCE_CHANGED')
        receipt=dict(schema_version=VERSION+'.receipt',import_id=import_id,identity=identity,imported_at=imported_at,
            wrapper_manifest_sha256=manifest_sha,copy_policy='EXACT_ORIGINAL_BYTES',**FLAGS)
        receipt_sha=safe_replace_json(stage/'native_import.json',receipt)
        no_symlinks(destination);no_symlinks(final)
        if final.exists():raise ValueError('M12_IMPORT_FINAL_EXISTS')
        os.rename(stage,final)
        safe_replace_json(destination/'import.json',dict(schema_version=VERSION+'.commit',import_id=import_id,receipt_sha256=receipt_sha))
        binding=_binding(request,final,manifest_sha);_cold_check(binding)
        return dict(status='IMPORTED_SAVED_NATIVE',import_id=import_id,imported_at=imported_at,binding=binding,**FLAGS)
    except (OSError,KeyError,TypeError,UnicodeError,json.JSONDecodeError) as error:
        raise ValueError('M12_NATIVE_IMPORT_REJECTED') from error

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--request',type=Path,required=True);args=parser.parse_args()
    # Request and returned binding remain on the authorized local machine.
    try:result=import_saved_native(json.loads(raw(args.request.absolute())))
    except ValueError as error:
        token=str(error);print(json.dumps(dict(status='CANNOT_CONFIRM',reason=token if token.startswith('M12_') and token.isidentifier() else 'M12_NATIVE_IMPORT_REJECTED',**FLAGS)));return 1
    print(json.dumps(result,ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())

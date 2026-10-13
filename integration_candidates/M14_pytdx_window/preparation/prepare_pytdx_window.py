"""Offline pinned batch-journal -> independent SDK window bundle. Never runs owner.

Requires existing pandas/pyarrow. Installs no dependencies. Uses actual current
clocks. Expired capture tasks fail the original pinned audit; no backdating.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import stat
import sys
import types

BATCH_SHA='4d51d842839d38abd906e4294ff801a9e4d38824dd0b899e62c1f12f58e804dd'
SUPPLIER_SHA='29c47c3836f0b26a9106626a990f03cae47c2ac22f2b4ca10be68c916c75f897'


def _load_batch(path):
    path=Path(path)
    if (not path.is_absolute() or '..' in path.parts
            or any(p.is_symlink() for p in (path,*path.parents))):
        raise ValueError('WINDOW_PREP_HELPER_PATH')
    parent=os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
            os.close(parent);parent=child
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
    finally:os.close(parent)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>1024**2:raise ValueError('WINDOW_PREP_HELPER_SIZE')
        with os.fdopen(os.dup(fd),'rb') as handle:raw=handle.read(1024**2+1)
        after=os.fstat(fd)
        fields=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')
        if any(getattr(before,f)!=getattr(after,f) for f in fields):raise ValueError('WINDOW_PREP_HELPER_CHANGED')
    finally:os.close(fd)
    if hashlib.sha256(raw).hexdigest()!=BATCH_SHA:raise ValueError('WINDOW_PREP_BATCH_SOURCE_SHA')
    module=types.ModuleType('_m14_window_pinned_batch');module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module


def _offline_guard(event,args):
    if event.startswith(('socket.','subprocess.','os.exec','os.spawn','os.posix_spawn')) or event in ('os.system','os.fork','os.forkpty'):
        raise PermissionError('WINDOW_PREPARATION_NETWORK_AND_PROCESS_DENIED')


def prepare(args):
    """All source material is read-only; only one new output directory is created."""
    sys.dont_write_bytecode=True
    sys.addaudithook(_offline_guard)
    base=Path(args.baseline_root)
    if not base.is_absolute() or any(p.is_symlink() for p in (base,*base.parents)):
        raise ValueError('WINDOW_PREP_BASE_PATH')
    sys.path.insert(0,str(base/'src'))
    from v5_shadow import rebound_owner as owner,rebound_pytdx_window as window
    from v5_shadow.composition import no_symlinks
    from v5_shadow.source_capsule import checked_path
    if Path(owner.__file__).resolve()!=base/'src/v5_shadow/rebound_owner.py':raise ValueError('WINDOW_PREP_OWNER_IMPORT_ROOT')
    window.verify_decoder_pin()
    batch=_load_batch(args.batch_helper);h=batch._helper(args.capture_helper)
    plan_raw=h._read(args.plan)
    if h._sha(plan_raw)!=h._digest(args.plan_sha256):raise ValueError('WINDOW_PREP_PLAN_FILE_SHA')
    plan=h._json(plan_raw)
    # These pinned functions verify all original-reference/parent bytes,
    # canary plans/receipts, real clocks, request identity and current validity.
    h,_,validator,context,reused,_,clock=batch._validated(plan,baseline_root=base,
        capture_helper=args.capture_helper,context_file=args.context_file)
    journal=batch._Journal(h,args.capture_dir,plan,reused,create=False)
    try:
        audited=batch._state(h,journal,validator,clock)
        batch._check_context_unchanged(h,context,full=True)
        audited_at=datetime.now(timezone.utc).isoformat(timespec='microseconds')
        head=journal.head
        records=[];receipt_bindings=[]
        for ref in audited['receipts']:
            raw=h._read(Path(args.capture_dir)/ref['relative'],window.MAX_JSON_BYTES)
            if h._sha(raw)!=ref['sha256']:raise ValueError('WINDOW_PREP_RECEIPT_CHANGED')
            record=h._json(raw)
            # Capture writer emits canonical JSON. Preserve its complete record
            # and the exact original SHA when packing SDK records into shards.
            if h._canonical(record)!=raw:raise ValueError('WINDOW_PREP_NONCANONICAL_CAPTURE_RECEIPT')
            records.append(record)
            receipt_bindings.append(dict(code=record['code'],relative=ref['relative'],sha256=ref['sha256']))
        original_artifact=h._json(context['snapshots']['original_artifact']['raw'])
        original_request=original_artifact['request'];original_paths=original_request['paths']
        task=plan['task'];members=task['exact_member_codes']
        parent_path=Path(context['snapshots']['parent_panel']['path'])
        # Current explicit override only changes where original master bytes are
        # read; exact original relative paths and SHA values remain mandatory.
        master_root=no_symlinks(args.original_input_root or original_request['input_root'])
        if not master_root.is_dir():raise ValueError('WINDOW_PREP_ORIGINAL_INPUT_ROOT_MISSING_USE_EXPLICIT_OVERRIDE')
        import pandas as pd
        import pyarrow.parquet  # Missing dependency is a blocker, never installed here.
        frame=pd.read_parquet(parent_path,columns=['trade_date_compact','code_norm'])
        target=frame.loc[frame['trade_date_compact'].astype(str).str.zfill(8)==task['signal_date'],'code_norm'].astype(str).str.upper().tolist()
        if sorted(target)!=members or len(target)!=len(set(target)):
            raise ValueError('WINDOW_PREP_ORIGINAL_PANEL_MEMBER_SET')
        sources=owner._sources(stored_supplement=True)
        supplier=base/'vendor/rebound_supplement/workspace_plan.py'
        if h._sha(h._read(supplier))!=SUPPLIER_SHA:raise ValueError('WINDOW_PREP_SUPPLIER_SOURCE_SHA')
        if any(name.split('.')[0] in owner.NAMESPACES for name in sys.modules):
            raise ValueError('WINDOW_PREP_FRESH_PROCESS_REQUIRED')
        sys.meta_path.insert(0,owner._Loader(sources,stored_supplement=True))
        original=importlib.import_module('v4.manager_research.workspace_plan')
        prepared_at=datetime.now(timezone.utc).isoformat(timespec='microseconds')
        calendar_context=original.plan_context(task['target_date'],now=datetime.fromisoformat(prepared_at))
        if calendar_context['market_session']!=task['signal_date']:raise ValueError('WINDOW_PREP_CURRENT_SIGNAL_CALENDAR_MISMATCH')
        sessions=window._sessions(original.rebound_history_sessions(task['signal_date']),task['signal_date'])
        decoded=window.decode_window(records,members=members,signal_date=task['signal_date'],
            sessions=sessions,research_cutoff=prepared_at)
        output=no_symlinks(args.output_dir)
        protected=[base,master_root,Path(args.capture_dir),Path(args.context_file),Path(args.plan),
                   *[Path(item['path']) for item in context['snapshots'].values()]]
        if any(output.is_relative_to(p) or p.is_relative_to(output) for p in protected):
            raise ValueError('WINDOW_PREP_OUTPUT_SOURCE_OVERLAP')
        out_fd=h._new_output(output)
        try:
            input_root=output/'input';input_root.mkdir(mode=0o700)
            prefix='assets/m14_pytdx_windows/runs/'+task['signal_date']+'/'+journal.run_id
            paths=dict(panel_manifest=prefix+'/manifest.json',panel=prefix+'/window.parquet',
                window_parent_manifest='assets/hk_0_2/'+task['parent_binding']['parent_manifest_relative'],
                window_parent_panel='assets/hk_0_2/'+task['parent_binding']['parent_panel_relative'],
                **{role:original_paths[role] for role in ('master_manifest','master_artifact','master_receipt')})
            files={};total=0
            for role in ('window_parent_manifest','window_parent_panel','master_manifest','master_artifact','master_receipt'):
                if role.startswith('window_parent_'):
                    name='parent_manifest' if role.endswith('manifest') else 'parent_panel'
                    source=Path(context['snapshots'][name]['path']);expected=context['snapshots'][name]['sha256']
                else:
                    source=checked_path(master_root,paths[role]);expected=original_request['files'][paths[role]]
                identity=owner._file(source.parent,source.name,destination=checked_path(input_root,paths[role]))
                if identity['sha256']!=expected:raise ValueError('WINDOW_PREP_ORIGINAL_SOURCE_SHA:'+role)
                files[paths[role]]=expected;total+=identity['bytes']
            directory=checked_path(input_root,prefix);directory.mkdir(parents=True,exist_ok=False,mode=0o700)
            shard_refs=[]
            for index,raw in enumerate(window.pack_records(records)):
                relative=prefix+f'/records-{index:03d}.json'
                with checked_path(input_root,relative).open('xb') as handle:handle.write(raw)
                digest=h._sha(raw);files[relative]=digest;total+=len(raw)
                shard_refs.append(dict(relative=relative,sha256=digest,bytes=len(raw)))
            panel_path=checked_path(input_root,paths['panel'])
            with panel_path.open('xb') as handle:
                pd.DataFrame(decoded['rows'],columns=window.COLUMNS).to_parquet(handle,index=False)
            identity=owner._file(input_root,paths['panel']);files[paths['panel']]=identity['sha256'];total+=identity['bytes']
            prepared_at=datetime.now(timezone.utc).isoformat(timespec='microseconds')
            if original.plan_context(task['target_date'],now=datetime.fromisoformat(prepared_at))['market_session']!=task['signal_date']:
                raise ValueError('WINDOW_PREP_CURRENT_SIGNAL_CALENDAR_MISMATCH')
            capture_audit=dict(schema_version='v5.rebound_pytdx_batch_audit_binding.v1',
                status='PINNED_BATCH_READONLY_AUDIT_AT_PREPARATION',batch_helper_sha256=BATCH_SHA,
                plan_sha256=journal.plan_sha,context_file_sha256=context['sha256'],run_id=journal.run_id,
                checkpoint_sha256=head,original_reference=task['original_reference'],parent_binding=task['parent_binding'],
                audited_at=audited_at,receipts=sorted(receipt_bindings,key=lambda r:r['code']),
                pending_codes=audited['pending_codes'],uncertain_codes=audited['uncertain_codes'],failed_codes=audited['failed_codes'])
            manifest=dict(schema_version=window.MANIFEST_SCHEMA,asset_schema_version=window.ASSET_SCHEMA,
                source_contract=window.SOURCE_CONTRACT,target_date=task['target_date'],signal_date=task['signal_date'],
                research_cutoff=prepared_at,panel_relative=paths['panel'],panel_sha256=identity['sha256'],
                panel_rows=len(decoded['rows']),panel_code_count=len(members),members=members,
                members_sha256=decoded['members_sha256'],sessions=sessions,records=shard_refs,
                capture_started_at=decoded['capture_started_at'],capture_finished_at=decoded['capture_finished_at'],
                manifest_prepared_at=prepared_at,parent_panel_sha256=files[paths['window_parent_panel']],
                parent_manifest_sha256=files[paths['window_parent_manifest']],
                row_projection_sha256=h._sha(h._canonical(decoded['rows'])),pending_reasons=decoded['pending_reasons'],
                capture_audit=capture_audit,**window.SAFETY)
            manifest_raw=h._canonical(manifest)
            if len(manifest_raw)>window.MAX_JSON_BYTES:raise ValueError('WINDOW_PREP_MANIFEST_BYTES_BOUND')
            with checked_path(input_root,paths['panel_manifest']).open('xb') as handle:handle.write(manifest_raw)
            files[paths['panel_manifest']]=h._sha(manifest_raw);total+=len(manifest_raw)
            request=dict(schema_version=window.REQUEST_SCHEMA,target_date=task['target_date'],signal_date=task['signal_date'],
                research_cutoff=prepared_at,data_kind='RECORDED_INPUT_REPLAY',input_root=str(input_root),paths=paths,files=files)
            window.validate_request(request,base=base)
            window.metadata(input_root,request)
            # Verify real Parquet round-trip plus the exact pinned calendar and
            # raw-record reconstruction before handing the request to any owner.
            witness,native=window.bind_private_window(input_root,request,original)
            if total>1024**3:raise ValueError('WINDOW_PREP_TOTAL_INPUT_BOUND')
            journal._audit()
            if journal.head!=head:raise ValueError('WINDOW_PREP_JOURNAL_CHANGED')
            batch._check_context_unchanged(h,context,full=True)
            batch._task(h,task,datetime.now(timezone.utc))
            reference=h._write_once(out_fd,'owner-request.json',request)
            audit_ref=h._write_once(out_fd,'capture-audit.json',audited)
            result=dict(schema_version='v5.rebound_pytdx_window_preparation.v1',status='PREPARED_OFFLINE_RESEARCH_CANDIDATE',
                owner_request=reference,capture_audit=audit_ref,input_files=len(files),private_files_with_routing=len(files)+2,
                input_bytes=total,member_count=len(members),response_record_count=len(records),pending_member_count=len(decoded['pending_reasons']),
                research_cutoff=prepared_at,source_contract=window.SOURCE_CONTRACT,
                owner_execution='NOT_RUN',formal_status='CANNOT_CONFIRM',**window.SAFETY)
            h._write_once(out_fd,'preparation-result.json',result)
            return result
        finally:os.close(out_fd)
    finally:journal.close()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline-root','batch-helper','capture-helper','plan','plan-sha256','context-file','capture-dir','output-dir'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--original-input-root',help='Explicit existing root for only the three original SHA-bound master files')
    args=parser.parse_args(argv)
    result=prepare(args)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True));return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,KeyError,TypeError,ImportError) as error:
        print(f'{type(error).__name__}: {error}',file=sys.stderr);raise SystemExit(2)

"""Offline exact saved-owner/panel batch preparation, never collection or repair."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import stat
from pathlib import Path
import re
import sys
import types

HELPER_SHA = 'e1a5fc5dba23dd10c727f002848b38e6d688b98316c99480bbef95fd97c66312'
OWNER_SHA = 'dc1b68715ba38a97a1df029a1934dab58b84b7f7486cb60b2a75a4d71491aa15'
GROUPS = ('strict', 'near', 'pending', 'excluded', 'screen_unresolved')
REUSED_CODES = ('HK.00001', 'HK.02825', 'HK.03469')


def load_helper(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or any(p.is_symlink() for p in (path,*path.parents)):
        raise ValueError('BATCH_PREP_HELPER_PATH')
    fd=os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd);fd=child
        source=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
        try:
            if not stat.S_ISREG(os.fstat(source).st_mode) or os.fstat(source).st_size>1024**2:
                raise ValueError('BATCH_PREP_HELPER_BOUNDED_REGULAR')
            with os.fdopen(os.dup(source),'rb') as handle:raw=handle.read(1024**2+1)
        finally:os.close(source)
    finally:os.close(fd)
    if hashlib.sha256(raw).hexdigest() != HELPER_SHA:
        raise ValueError('BATCH_PREP_HELPER_SHA')
    module = types.ModuleType('_m14_pinned_capture_helper')
    module.__file__ = str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module


def members_from_saved(artifact):
    groups = artifact['research_observation']
    if not isinstance(groups,dict): raise ValueError('BATCH_PREP_OBSERVATION')
    members = []
    for group in GROUPS:
        rows = groups[group]
        if not isinstance(rows,list): raise ValueError('BATCH_PREP_GROUP')
        for row in rows:
            code = row.get('code') if isinstance(row,dict) else None
            if not isinstance(code,str) or not re.fullmatch(r'HK\.\d{5}',code):
                raise ValueError('BATCH_PREP_MEMBER_CODE')
            members.append(code)
    if not 1 <= len(members) <= 1000 or len(set(members)) != len(members):
        raise ValueError('BATCH_PREP_DUPLICATE_OR_BOUNDED_POOL')
    return sorted(members)


def derive_missing_keys(rows, members, signal, history):
    """Only absence of exact native-calendar rows; never fill invalid cells."""
    sessions = history['prior60']
    if (len(sessions)!=60 or len(set(sessions))!=60 or any(not re.fullmatch(r'\d{8}',d) or d>=signal for d in sessions)
            or len(history['previous5'])!=5 or not set(history['previous5']).issubset(sessions)):
        raise ValueError('BATCH_PREP_CALENDAR')
    member_set=set(members); session_set=set(sessions)
    target=Counter(); observed=Counter()
    for index, (code, day) in enumerate(rows):
        if index>=2_000_000:raise ValueError('BATCH_PREP_PANEL_ROW_BOUND')
        code,day=str(code),str(day)
        if day == signal: target[code]+=1
        if code in member_set and day in session_set: observed[(code,day)]+=1
    if set(target)!=member_set or any(n!=1 for n in target.values()):
        raise ValueError('BATCH_PREP_TARGET_POOL_MISMATCH')
    if any(n!=1 for n in observed.values()):
        raise ValueError('BATCH_PREP_DUPLICATE_HISTORY')
    return [dict(code=code,date=day) for code in sorted(members) for day in sorted(sessions)
            if (code,day) not in observed]


def task_and_context(*, artifact, reference, parent, members, keys, files, reuse, now):
    if now.tzinfo is None or now.utcoffset() is None:raise ValueError('BATCH_PREP_NAIVE_CLOCK')
    now=now.astimezone(timezone.utc)
    canonical=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    sha=lambda x:hashlib.sha256(canonical(x)).hexdigest()
    req=artifact['request']
    task=dict(schema_version='v5.m14_history_batch_task.v1',target_date=req['target_date'],signal_date=req['signal_date'],
        prepared_at=now.isoformat(timespec='microseconds'),valid_until=(now+timedelta(hours=2)).isoformat(timespec='microseconds'),
        exact_member_codes=members,exact_member_codes_sha256=sha(members),keys=keys,keys_sha256=sha(keys),
        expected_panel_sha256=parent['parent_panel_sha256'],original_reference=reference,parent_binding=parent,initial_reuse=reuse)
    context=dict(schema_version='v5.m14_history_batch_context.v1',target_date=req['target_date'],signal_date=req['signal_date'],
        original_reference=reference,parent_binding=parent,exact_member_codes=members,keys=keys,files=files)
    return task,context


def require_separate_output(output, protected):
    output=Path(output)
    if not output.is_absolute() or '..' in output.parts or any(p.is_symlink() for p in (output,*output.parents)):
        raise ValueError('BATCH_PREP_OUTPUT_PATH')
    for root in map(Path,protected):
        if output==root or root in output.parents or output in root.parents:
            raise ValueError('BATCH_PREP_OUTPUT_OVERLAP')
    return output


def prepare(args):
    h=load_helper(args.capture_helper)
    v5=Path(args.v5_root)
    os.close(h._open_directory(v5))  # Validate all ancestors before loading the fixed reader.
    if h._sha(h._read(v5/'src/v5_shadow/rebound_owner.py'))!=OWNER_SHA:
        raise ValueError('BATCH_PREP_ORIGINAL_OWNER_SOURCE_SHA')
    sys.path.insert(0,str(v5/'src'))
    from v5_shadow import rebound_owner as owner, rebound_panel_repair as repair
    config=owner._json(h._read(args.source_api_config))
    binding=config['m14_rebound_binding'];reference=binding['reference']
    artifact=owner.read_rebound_owner(binding['private_root'],reference)
    request=artifact['request']
    if (request['target_date'],request['signal_date'])!=(args.target_date,args.signal_date):
        raise ValueError('BATCH_PREP_TARGET_SIGNAL')
    members=members_from_saved(artifact)
    if len(members)!=args.expected_members:raise ValueError('BATCH_PREP_EXPECTED_POOL_COUNT')
    asset=owner.no_symlinks(args.hk02_asset_root)
    prefix='assets/hk_0_2/'
    pmanifest=request['paths']['panel_manifest'].removeprefix(prefix)
    ppanel=request['paths']['panel'].removeprefix(prefix)
    pointer_raw=repair._read(asset,'panel_latest.json')
    if owner._json(pointer_raw)['manifest_relative']!=pmanifest:raise ValueError('BATCH_PREP_PARENT_POINTER_CHANGED')
    manifest_sha=h._sha(repair._read(asset,pmanifest));panel_sha=owner._file(asset,ppanel)['sha256']
    if (manifest_sha!=request['files'][request['paths']['panel_manifest']]
            or panel_sha!=request['files'][request['paths']['panel']]):raise ValueError('BATCH_PREP_ORIGINAL_PANEL_SHA')
    parent=dict(parent_pointer_sha256=h._sha(pointer_raw),parent_manifest_relative=pmanifest,parent_manifest_sha256=manifest_sha,
        parent_panel_relative=ppanel,parent_panel_sha256=panel_sha)
    import pandas as pd
    frame=pd.read_parquet(owner.checked_path(asset,ppanel),columns=['code_norm','trade_date_compact'])
    history=repair._history_window(request['signal_date'])
    keys=derive_missing_keys(frame.itertuples(index=False,name=None),members,request['signal_date'],history)
    if len(keys)!=args.expected_missing_keys:raise ValueError('BATCH_PREP_EXPECTED_MISSING_KEY_COUNT')
    if owner._file(asset,ppanel)['sha256']!=panel_sha or h._sha(repair._read(asset,'panel_latest.json'))!=parent['parent_pointer_sha256']:
        raise ValueError('BATCH_PREP_PARENT_CHANGED')
    result_path=Path(args.canary_result)
    raw=h._read(result_path)
    if h._sha(raw)!=args.canary_result_sha256:raise ValueError('BATCH_PREP_CANARY_RESULT_SHA')
    result=h._json(raw);old_task=result['task']
    if (result.get('schema_version')!='v5.m14_history_capture_result.v1' or result.get('status')!='CAPTURED'
            or old_task['original_reference']!=reference or old_task['parent_binding']!=parent
            or old_task['target_date']!=request['target_date'] or old_task['signal_date']!=request['signal_date']):
        raise ValueError('BATCH_PREP_CANARY_CONTEXT')
    plan_path=result_path.parent/'plan.json';plan_raw=h._read(plan_path)
    if h._sha(plan_raw)!=result['plan_sha256']:raise ValueError('BATCH_PREP_CANARY_PLAN_SHA')
    plan=h._json(plan_raw)
    if plan!=h.prepare_plan(old_task,baseline_root=v5):raise ValueError('BATCH_PREP_CANARY_PLAN_IDENTITY')
    reuse=[]
    for source in result['sources']:
        if not re.fullmatch(r'[A-Za-z0-9._-]+\.json',source['relative']) or source['record_pointer']!='':
            raise ValueError('BATCH_PREP_CANARY_SOURCE_PATH')
        path=result_path.parent/source['relative'];record_raw=h._read(path,h.MAX_RESPONSE_BYTES+2*1024**2)
        if h._sha(record_raw)!=source['sha256']:raise ValueError('BATCH_PREP_CANARY_RECEIPT_SHA')
        record=h._json(record_raw)
        if (record['status']!='RESPONSE_CAPTURED' or record['error_code'] is not None or record['original_reference']!=reference
                or record['parent_binding']!=parent or record['plan_sha256']!=result['plan_sha256']):
            raise ValueError('BATCH_PREP_CANARY_RECORD_IDENTITY')
        reuse.append(dict(code=record['code'],receipt_path=str(path.absolute()),receipt_sha256=source['sha256'],
            plan_path=str(plan_path.absolute()),plan_sha256=result['plan_sha256']))
    reuse.sort(key=lambda item:item['code'])
    if tuple(item['code'] for item in reuse)!=REUSED_CODES:raise ValueError('BATCH_PREP_THREE_INITIAL_RECEIPTS_REQUIRED')
    saved=Path(binding['private_root'])/'runs'/reference['run_id']
    files=dict(original_artifact=str(saved/'artifact.json'),original_manifest=str(saved/'manifest.json'),
        original_receipt=str(saved/'receipt.json'),parent_pointer=str(asset/'panel_latest.json'),
        parent_manifest=str(asset/pmanifest),parent_panel=str(asset/ppanel))
    task,context=task_and_context(artifact=artifact,reference=reference,parent=parent,members=members,keys=keys,files=files,reuse=reuse,
        now=datetime.now(timezone.utc))
    output_path=require_separate_output(args.output_dir,(v5,asset,Path(binding['private_root']),result_path.parent,Path(args.source_api_config)))
    output=h._new_output(output_path)
    try:
        context_ref=h._write_once(output,'context.json',context)
        task_ref=h._write_once(output,'task.json',task)
        summary=dict(status='PREPARED_OFFLINE_NO_COLLECTION',member_count=len(members),missing_key_count=len(keys),
            missing_key_codes=len({k['code'] for k in keys}),initial_reuse_count=len(reuse),
            new_query_count=len({k['code'] for k in keys}-{item['code'] for item in reuse}),
            task=task_ref,context=context_ref,calendar_sha256=history['calendar_sha256'],
            repair_publish_allowed=False,unit_comparability='NOT_PROVEN_DO_NOT_MIX_WITH_PARENT',
            **h.SAFETY)
        h._write_once(output,'preparation.json',summary)
    finally:
        os.close(output)
    return summary


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture-helper','v5-root','source-api-config','hk02-asset-root','canary-result','canary-result-sha256','output-dir','target-date','signal-date'):
        p.add_argument('--'+name,required=True)
    p.add_argument('--expected-members',type=int,required=True)
    p.add_argument('--expected-missing-keys',type=int,required=True)
    args=p.parse_args(argv)
    print(json.dumps(prepare(args),ensure_ascii=False,sort_keys=True))
    return 0

if __name__=='__main__':raise SystemExit(main())

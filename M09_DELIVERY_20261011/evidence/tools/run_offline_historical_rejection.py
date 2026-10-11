"""Preserve actual R3 input bytes and execute honest rejection at both old slots.

The host may lack pyarrow. This script never calls a substitute decoder and
never turns source-reported row-quality statistics into observed decoded rows.
Its new pointer is a relocation aid; it is not source availability evidence.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for raw in iter(lambda:stream.read(1024*1024),b''):h.update(raw)
    return h.hexdigest()


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--after',required=True);p.add_argument('--runtime-inputs',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();after,original,out=map(Path,(a.after,a.runtime_inputs,a.out))
    for path in (after,original,out):
        assert path.is_absolute() and '..' not in path.parts and path != Path('/')
        assert not any(v.is_symlink() for v in (path,*path.parents))
    assert not out.exists() and not out.is_relative_to(after) and not out.is_relative_to(original)
    out.mkdir(mode=0o700);source=out/'relocated_source';source.mkdir(mode=0o700)
    expected={
        'panel_20261009_required8.parquet':(279209,'7dfa12fa03ad76d5e946088f88993748a3fffd8943281a12eb364c35712f8c47'),
        'membership_20261009.txt':(51260,'b1f561b1d18a5341784c4906b0e3bbbf21d7d092823e4a60c2787fdf004d91fb'),
        'panel_source_receipt.json':(80017050,'de652e8ddc540433bef8d0dd9f13da54eb973cf520156109d9e61794dace2a6e'),
        'CURRENT_SELECTOR_READY_PANEL.txt':(242,'91a52a4f28098a2525ca4c9af9dd96c082e1c028392a55787fc9bcfbcf2f946d'),
        'daily_pointer.txt':(242,'91a52a4f28098a2525ca4c9af9dd96c082e1c028392a55787fc9bcfbcf2f946d'),
        'dispatcher_pointer.txt':(242,'91a52a4f28098a2525ca4c9af9dd96c082e1c028392a55787fc9bcfbcf2f946d'),
    }
    for name,(size,sha) in expected.items():
        path=original/'originals'/name
        assert path.stat().st_size==size and digest(path)==sha,name
        shutil.copyfile(path,source/name)
        assert digest(source/name)==sha,name
    pointer=source/'candidate_projection_pointer.txt';pointer.write_text('panel_20261009_required8.parquet\n',encoding='utf-8')
    manifest={
        'schema_version':'v5.m09.input.v1','trade_date':'20261009','data_kind':'RECORDED_INPUT_REPLAY',
        'panel':{'pointer_path':pointer.name,'pointer_sha256':digest(pointer),'sha256':expected['panel_20261009_required8.parquet'][1],'format':'PARQUET','row_count':5126},
        'membership':{'path':'membership_20261009.txt','sha256':expected['membership_20261009.txt'][1],'scope':'DECLARED_UNIVERSE','source_id':None,'version':None,'captured_at':None,'available_at':None},
        'provenance':{'source_id':None,'version':None,'status':'PARTIAL','authority_status':'REBUILD_REQUIRED','coverage_rate':0.8858620689655172,'captured_at':None,'available_at':None,'acquired_at':None,
                      'receipt_path':'panel_source_receipt.json','receipt_sha256':expected['panel_source_receipt.json'][1],'receipt_fields':{'trade_date':'/target_date'}},
        'evidence':{},
    }
    save(source/'diagnostic_input.json',manifest)
    save(out/'relocation.json',{'original_root':str(original),'source_root':str(source),'originals':{k:{'bytes':v[0],'sha256':v[1]} for k,v in expected.items()},
        'new_pointer':{'path':pointer.name,'sha256':digest(pointer)},'manifest_sha256':digest(source/'diagnostic_input.json'),
        'invented_source_timestamps':False,'cleaning_applied':False,'source_copies_in_delivery':'Original bytes are already in the pinned R3/runtime archives; rerun this script to recreate these copied paths.'})
    sys.path.insert(0,str(after/'V5/src'))
    from v5_shadow.a_close_daily import diagnose_a_close_input,initialize_a_close_root,run_a_close_daily,read_a_close_daily
    from v5_shadow.a_close_daily_api import read_a_close_preview
    root=out/'rejected_attempts_root';initialize_a_close_root(root)
    statuses=[]
    for slot in ('16:05','17:10'):
        diagnostic=diagnose_a_close_input(source,'diagnostic_input.json',digest(source/'diagnostic_input.json'),'20261009',slot)
        assert not diagnostic['admitted'],diagnostic
        request=dict(schema_version='v5.m09.daily_request.v1',trade_date='20261009',slot=slot,job_id='m09_offline_historical_'+slot.replace(':',''),attempt_id='raw_unchanged_'+slot.replace(':',''),
            execution_kind='RECORDED_INPUT_REPLAY',triggered_at=datetime.now(timezone.utc).isoformat(),source_root=str(source),input_manifest='diagnostic_input.json',
            input_manifest_sha256=digest(source/'diagnostic_input.json'),configuration_revision='m09-r3-uncleaned-diagnostic')
        receipt=run_a_close_daily(root,request);preview=read_a_close_preview(root,'20261009')
        assert receipt['status']=='FAILED' and read_a_close_daily(root,'20261009') is None
        assert preview['m09_publication']['read_status']=='MISSING'
        assert preview['m09_publication']['latest_attempt_status']=='FAILED'
        for name,value in [('diagnostic',diagnostic),('request',request),('attempt',receipt),('api_preview',preview)]:save(out/(name+'_'+slot.replace(':','')+'.json'),value)
        statuses.append({'slot':slot,'attempt_status':receipt['status'],'admitted':False,'panel_decoded':diagnostic.get('panel_decoded'),
            'observed_decoded_row_count':diagnostic.get('row_count'),'declared_panel_row_count':5126,'read_status':preview['m09_publication']['read_status'],
            'issues':diagnostic['issues']})
    for name,(size,sha) in expected.items():
        assert (source/name).stat().st_size==size and digest(source/name)==sha
        assert (original/'originals'/name).stat().st_size==size and digest(original/'originals'/name)==sha
    result={'schema_version':'m09.offline_actual_input_rejection.v1','status':'EXPECTED_REJECTION_CONFIRMED','data_kind':'RECORDED_INPUT_REPLAY','market_success':False,
        'natural_execution':'NOT_RUN','Mac_execution':'NOT_RUN','real_original_producer':'NOT_RUN_INPUT_NOT_ADMITTED','real_pyarrow_decode':'EXERCISED' if all(x['panel_decoded'] for x in statuses) else 'NOT_RUN_ENGINE_UNAVAILABLE',
        'both_slots':statuses,'original_bytes_unchanged':True,'finished_at':datetime.now(timezone.utc).isoformat()}
    save(out/'result.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()

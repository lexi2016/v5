"""SYNTHETIC envelope recipe, published by frozen original Store, never builder."""
import importlib.util
from pathlib import Path
import sys

STAGES=('STAGE_0925','STAGE_0930_0935','STAGE_0935_0940','STAGE_0940_0945','STAGE_0945_1030','STAGE_1300_1315','STAGE_1445_1500')


def original():
    path=Path(__file__).resolve().parents[2]/'source_owners/m10/V5/src/v5_shadow/hk_close_daily.py'
    spec=importlib.util.spec_from_file_location('_m10_frozen_test_owner',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module


def create_fixture(root, *, revision=1, stage_status='PARTIAL_WITH_ROWS', model=True):
    daily=original();date='20261012';flags=dict(production_allowed=False,buy_gate_updated=False,orders_sent=False)
    rows=[dict(rank=i,code=f'HK.{101-i:05d}',name=f'SYNTHETIC_{i}',trade_date=date,pct_chg=i/10,close=100+i,pre_close=100,original_zero=0,original_empty='') for i in range(1,21)]
    model_rows=[dict(rank=i,code=f'HK.{i:05d}',name=f'SYNTHETIC_{i}',trade_date=date,strategy='prob_active',pool_version='0.2',hit_top20=i>80) for i in range(1,101)] if model else []
    stage_rows=[dict(stage_id=stage,stage_rank=i,code=f'HK.{i:05d}',name=f'SYNTHETIC_{i}',trade_date=date,hit_top20=False) for stage in STAGES for i in range(1,11)] if stage_status!='READY_EMPTY' else []
    metric=dict(evidence_status='READY',selected_count=10,selected_codes=[f'HK.{i:05d}' for i in range(1,11)],hit_count=0,hit_codes=[],coverage=0.0,precision=0.0,coverage_pct=0.0,precision_pct=0.0)
    if stage_status=='READY_EMPTY':metric.update(selected_count=0,selected_codes=[])
    stages={stage:dict(metric) for stage in STAGES}
    reason=[] if stage_status in ('READY','READY_EMPTY') else ['SYNTHETIC_PIT_UNVERIFIED']
    input_evidence=dict(model=dict(payload={'rows':model_rows}),stages={stage:dict(markets={'HK_CONNECT':{'status':stage_status,'cannot_confirm':reason}},cannot_confirm=reason) for stage in STAGES},synthetic_revision=revision)
    identity=dict(trade_date=date,input_sha256=daily._digest(input_evidence),calendar_sha256='a'*64,code_sha256='b'*64,config_sha256='c'*64,owner_capsule_sha256='d'*64)
    model_metric=dict(metric,evidence_status='READY' if model else 'MISSING',selected_count=100 if model else None)
    if not model:
        for key in ('hit_count','coverage','precision','coverage_pct','precision_pct'):model_metric[key]=None
    review=dict(schema_version='v3_5.close_review.v1',trade_date=date,status='MODEL_REVIEW_READY',primary_kpi='全港股通收盘涨幅Top20覆盖率',
        close_top20=rows,model_rows=model_rows,stage_rows=stage_rows,models={'0.2_prob_active':model_metric},stages=stages,stage_union=dict(metric),
        kpi={'model_0_2_close_top20_hits':0 if model else None,'stage_union_close_top20_hits':0},
        row_counts=dict(hkconnect_universe=698,close_top20=20,model_0_2=len(model_rows),stage_rows=len(stage_rows)),
        top20_attribution=[dict(row,model_0_2_hit=True,stage_union_hit=False,classification='model_only',first_stage=None,all_stages=[]) for row in rows],
        missing_stages=[],cannot_confirm=[],close_source_sha256='e'*64,evidence_mode='SYNTHETIC_OFFLINE',reference_snapshot=False,write_policy='review_only_read_only',**flags)
    run_id=date+'-'+daily._digest(identity)[:24]
    relative=f'close_reviews/{date}.json';receipt_relative=f'receipts/close_reviews/{date}.json'
    native_sha=daily._digest(review)
    publication=dict(payload_path=relative,receipt_path=receipt_relative,sha256=native_sha,previous_sha256='')
    envelope=dict(schema=daily.DAILY_SCHEMA,run_id=run_id,identity=identity,data_kind='RECORDED_INPUT_REPLAY',review=review,input_evidence=input_evidence,
        native_evidence={'manifest':{relative:native_sha},'receipt':{'schema_version':'v3_import_receipt.v1','payload_path':relative,'source_sha256':native_sha,'trade_date':date}},
        cannot_confirm=['M02_MEMBERSHIP_PIT_UNVERIFIED',*reason],natural_admission='UNVERIFIED',previous_native_sha256=None)
    reader=daily.HKCloseReviewReader(root);latest=reader.latest_identity()
    daily.HKCloseReviewStore(root).publish(run_id,envelope,publication,expected_generation=latest['generation'] if latest else None)
    projection=daily.read_hk_close_projection(root,run_id)
    return dict(run_root=str(root),run_id=run_id,generation=projection['generation'],python_executable=sys.executable),projection

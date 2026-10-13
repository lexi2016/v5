"""Hand-serialized synthetic saved trio; no selector, store writer or job runs."""
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
from v5_shadow.m16_prepare_stage import ROOT, canonical, OBSERVED

FIELDS = ('code','score','rank','status','formal_eligible','support','pressure','invalidation','source_mode','lane_evidence','action_level','trade_status')
FLAGS = dict(production_allowed=False,buy_gate_updated=False,orders_sent=False)


def make_saved_stage(root, *, stage='STAGE_0935_0940', late=False, missing_time=False, empty=False):
    date='20261005'
    rows=[] if empty else [dict(code=f'HK.{i:05d}',name=f'SYNTHETIC OFFLINE ISSUER {i}',score=70,
       rank=i,status='READY',formal_eligible=False,support=9,pressure=11,invalidation=8,
       source_mode='SYNTHETIC_TEST_ONLY',lane_evidence=['SYNTHETIC SAVED EVIDENCE'],
       action_level='NO_BUY',trade_status='RESEARCH_ONLY',last_price=10,
       source_last_bar_time='2026-10-05 09:41:00' if late else '2026-10-05 09:40:00',
       extra_original_evidence={'complete_row': True, 'nested': [1,2,3]}) for i in (1,2)]
    if missing_time:
        for row in rows:row.pop('source_last_bar_time')
    algorithm='fa010779606766f2bb94e2b5ef028a06df218ca6e68b48284a94c64bf0919657'
    raw_sha='2'*64
    identity=dict(identity=f'{date}/{stage}/HK_CONNECT',raw_artifact_sha256=raw_sha,algorithm_sha256=algorithm,rows=rows)
    digest=sha256(canonical(identity)).hexdigest(); run='run-'+digest[:24]
    role='HK_CONNECT_SELECTION_'+stage; prefix=f'selection_runs/{date}/{role}/{run}'
    artifact=dict(schema_version='stage_center.selection.v2',trade_date=date,stage_id=stage,market='HK_CONNECT',
        artifact_id='selection-'+digest[:24],run_id=run,algorithm_id='V3_STAGE_SELECTION_V1',algorithm_sha256=algorithm,
        raw_artifact_sha256=raw_sha,source_status='READY',selection_status='READY_EMPTY' if empty else 'READY',
        requested_rows=len(rows),source_rows=len(rows),selected_rows=len(rows),coverage_ratio=1.0,
        missing_symbols=[],rows=rows,source_evidence=['SYNTHETIC SAVED TRIO ONLY'],cannot_confirm=[],**FLAGS)
    stream=StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=FIELDS,lineterminator='\n');writer.writeheader()
    for row in rows:writer.writerow({f:json.dumps(row.get(f),ensure_ascii=False,sort_keys=True,separators=(',',':')) if f=='lane_evidence' else ('' if row.get(f) is None else row.get(f)) for f in FIELDS})
    csv_bytes=stream.getvalue().encode('utf-8-sig'); csv_sha=sha256(csv_bytes).hexdigest()
    shared=dict(owner='stage_center',trade_date=date,stage_id=stage,market='HK_CONNECT',role=role,run_id=run,
       artifact_relative=prefix+'/artifact.csv',artifact_sha256=csv_sha,row_count=len(rows),
       selection_status=artifact['selection_status'],raw_artifact_sha256=raw_sha,
       algorithm_id='V3_STAGE_SELECTION_V1',algorithm_sha256=algorithm,**FLAGS)
    manifest=dict(schema_version='stage_center.selection.manifest.v1',selection_envelope=artifact,**shared)
    manifest_raw=canonical(manifest); receipt=dict(schema_version='stage_center.selection.receipt.v1',
       manifest_sha256=sha256(manifest_raw).hexdigest(),idempotency_key='synthetic-idempotency',**shared)
    receipt_raw=canonical(receipt)
    raw={'artifact.csv':csv_bytes,'manifest.json':manifest_raw,'receipt.json':receipt_raw}
    source_ref=dict(schema_version='v5.hk_stage_observed_source.v1',target_date=date,stage_id=stage,market='HK_CONNECT',run_id=run,
       artifact_sha256=csv_sha,manifest_sha256=sha256(manifest_raw).hexdigest(),receipt_sha256=sha256(receipt_raw).hexdigest(),
       trio={name:dict(relative_path=prefix+'/'+name,sha256=sha256(b).hexdigest(),bytes=len(b)) for name,b in raw.items()})
    names=('hk_stage_observed.py','hk_stage_observed_api.py','hk_stage_api.py','hk_stage_sources.py',
           'contracts.py','digests.py','composition.py','module_api.py','module_artifacts.py','api_gateway.py')
    dependency=ROOT/'source/m08_readonly/V5/src/v5_shadow'
    implementation={name:sha256((dependency/name).read_bytes()).hexdigest() for name in names}
    imp=dict(schema_version='v5.hk_stage_observed_import.v1',original_reference=source_ref,
       source_closure_sha256='451f39aabcec3206ebda1252f7cdd426bac4a19e74889ed35881a9ae9b787d8d',
       reader_implementation_identity=implementation,**OBSERVED,**FLAGS)
    imp_bytes=canonical(imp); imp_sha=sha256(imp_bytes).hexdigest()
    imp_receipt=dict(schema_version='v5.hk_stage_observed_receipt.v1',status='COMMITTED',import_sha256=imp_sha,
       imported_at='2026-10-13T10:00:00+00:00',**OBSERVED,**FLAGS)
    imp_receipt_bytes=canonical(imp_receipt)
    ref=dict(schema_version='v5.hk_stage_observed_reference.v1',import_sha256=imp_sha,
       import_receipt_sha256=sha256(imp_receipt_bytes).hexdigest(),target_date=date,stage_id=stage,market='HK_CONNECT',run_id=run)
    recorded=Path(root)/'recorded';recorded.mkdir();(recorded/'.v5-hk-stage-observed-root').write_bytes(b'v5.hk-stage-observed-root.v1\n')
    location=recorded/'imports'/imp_sha;location.mkdir(parents=True)
    (location/'import.json').write_bytes(imp_bytes);(location/'receipt.json').write_bytes(imp_receipt_bytes)
    for name,b in raw.items():
        p=location/'owner'/prefix/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    reference=Path(root)/'reference.json';reference.write_bytes(canonical(ref))
    return recorded,reference,artifact,location/'owner'/prefix

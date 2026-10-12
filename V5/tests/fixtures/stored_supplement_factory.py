"""SYNTHETIC ONLY; writes local test fixtures, never contacts a provider."""
import hashlib,json
from pathlib import Path
from fixtures.rebound_factory import publish_fixture

def build(root, original, reader):
    import pandas as pd
    sha=lambda b:hashlib.sha256(b).hexdigest()
    canonical=lambda o:json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    def write(path, obj):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(obj))
    pm=Path(publish_fixture(root,original));panel=json.loads(pm.read_bytes())
    asset=root/'assets/hk_0_2';pp=asset/panel['panel_relative']
    frame=pd.read_parquet(pp);sessions,calendar=reader.requested_sessions('20261007')
    # Three missing prior sessions; preserve latest prior session for panel witness.
    frame=frame.loc[~frame.trade_date_compact.isin(sessions[:3])]
    frame.to_parquet(pp,index=False)
    digest=sha(pp.read_bytes())
    directory=asset/f'panels/20261007-{digest[:12]}'
    pp.parent.rename(directory);pp=directory/pp.name;pm=directory/'manifest.json'
    panel.update(panel_sha256=digest,panel_relative=str(pp.relative_to(asset)),panel_rows=len(frame));write(pm,panel)
    write(asset/'panel_latest.json',dict(manifest_relative=str(pm.relative_to(asset))))
    ma=root/'assets/hk_security_master';entry=json.loads((ma/'latest.json').read_bytes())['entries']['20261007']
    mp=ma/entry['manifest_relative'];master=json.loads(mp.read_bytes())
    paths=dict(panel_manifest=str(pm.relative_to(root)),panel=str(pp.relative_to(root)),
        master_manifest=str(mp.relative_to(root)),master_artifact=str((ma/master['artifact_relative']).relative_to(root)),
        master_receipt=str((ma/entry['receipt_relative']).relative_to(root)))
    panel_id=dict(panel_sha256=panel['panel_sha256'],panel_manifest_sha256=sha(pm.read_bytes()),manifest_prepared_at=panel['manifest_prepared_at'])
    master_id=dict(manifest_sha256=sha(mp.read_bytes()),artifact_sha256=master['artifact_sha256'],captured_at=master['captured_at'])
    codes=['HK.00001','HK.00002','HK.00003','HK.00004'];records=[]
    for code in codes:
        rows=[dict(datetime=f'{d[:4]}-{d[4:6]}-{d[6:]}',open=9.,high=10.,low=8.,close=9.,trade=100.) for d in sessions]
        rows[-1]['trade']=200. if code in ('HK.00001','HK.00003') else 100.
        request=dict(category=4,market=71,code=code.split('.')[1],start=0,count=6,requested_sessions=sessions)
        records.append(dict(code=code,request=request,request_sha256=sha(canonical(request)),source_rows=rows,
            response_sha256=sha(canonical(rows)),returned_count=len(rows),status='READY',missing_sessions=[],
            bars=[reader._decode_bar(r,'20261007',set(sessions)) for r in rows],
            request_started_at='2026-10-07T10:00:01+00:00',response_acquired_at='2026-10-07T10:00:02+00:00',request_finished_at='2026-10-07T10:00:03+00:00'))
    run='synthetic-stored';prefix='daily_supplements/runs/20261007/'+run
    capture=dict(schema_version=reader.CAPTURE_SCHEMA,target_date='20261007',requested_sessions=sessions,calendar_sha256=calendar,
        capture_scope='FULL_MASTER',canary_codes=None,capture_started_at='2026-10-07T10:00:00+00:00',capture_prepared_at='2026-10-07T10:01:00+00:00',
        source=dict(provider='PYTDX_EXHQ',host='119.97.142.130:7721',category=4,market=71,method='get_instrument_bars',start=0,count=6),records=records,**reader.SAFETY)
    rawrel=prefix+'/raw_capture.json';mrel=prefix+'/manifest.json';prel='daily_supplements/pointers/20261007.json'
    write(asset/rawrel,capture)
    manifest=dict(schema_version=reader.MANIFEST_SCHEMA,target_date='20261007',run_id=run,raw_capture_relative=rawrel,raw_capture_sha256=sha((asset/rawrel).read_bytes()),requested_sessions=sessions,calendar_sha256=calendar,
        capture_scope='FULL_MASTER',canary_codes=None,provider='PYTDX_EXHQ',method='get_instrument_bars',category=4,market=71,start=0,count=6,
        panel_identity=panel_id,security_master_identity=master_id,prepared_at=capture['capture_prepared_at'],capture_started_at=capture['capture_started_at'],
        code_count=4,master_code_count=4,selected_codes=codes,selected_codes_sha256=sha(canonical(codes)),universe_codes_sha256=sha(canonical(codes)),record_status_counts={'READY':4},status='READY',**reader.SAFETY)
    write(asset/mrel,manifest)
    pointer=dict(schema_version=reader.POINTER_SCHEMA,target_date='20261007',run_id=run,panel_identity=panel_id,security_master_identity=master_id,
        published_at='2026-10-07T10:01:01+00:00',manifest_relative=mrel,manifest_sha256=sha((asset/mrel).read_bytes()),raw_capture_relative=rawrel,raw_capture_sha256=sha((asset/rawrel).read_bytes()),**reader.SAFETY)
    write(asset/prel,pointer)
    paths.update(supplement_pointer='assets/hk_0_2/'+prel,supplement_manifest='assets/hk_0_2/'+mrel,supplement_capture='assets/hk_0_2/'+rawrel)
    return paths

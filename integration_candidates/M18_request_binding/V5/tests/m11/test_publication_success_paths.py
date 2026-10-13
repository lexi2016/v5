"""Publication units: explicit process-boundary fixtures, never live owner claims.

Daily fixture invokes the real donor writer, then real new-process daily reader.
Intraday unit uses the original pure aggregator and recorded process responses;
trusted-manifest acquisition remains blocked and is tested separately.
"""
import importlib.util
from datetime import datetime
import json
import sys
import pytest
from test_default_owner_chain import binding
from v5_shadow.m11 import daily
from v5_shadow.m11.owner_sources import OWNER_ROOT,V5
from v5_shadow.m11.intraday_capsule import IntradayCapsuleStore,M11Slot

SOURCES=[{'event_time':'2026-10-12T09:25:00+08:00','published_at':'2026-10-12T09:25:00+08:00','observed_at':'2026-10-12T09:25:00+08:00','available_at':'2026-10-12T09:25:00+08:00'}]


def test_real_fixture_daily_writer_then_independent_reader_and_publication(tmp_path,monkeypatch):
    sys.path.insert(0,str(OWNER_ROOT))
    from domains.research_review_generation.generation import run_generation
    path=V5.parent/'handoffs/M11/original_source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/tests/test_research_review_generation.py'
    spec=importlib.util.spec_from_file_location('_m11_daily_fixture',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    b=binding(tmp_path)
    original=run_generation('2026-10-12',review_root=b.state_root/'reviews',backend=module._payload)
    monkeypatch.setattr(daily,'_execute_guarded',lambda *_:{'status':'OWNER_RETURNED','owner_result':original})
    result=daily.generate(b,target_date='2026-10-12',cutoff='2026-10-12T15:05:00+08:00',run_id='fixture-daily',sources=SOURCES)
    assert result['status']=='COMMITTED' and result['natural_admission']=='CANNOT_CONFIRM'
    payload=IntradayCapsuleStore(b.archive_root/'daily').read_verified(M11Slot(**result['identity']))
    assert payload['owner']['owner_artifact']['v4_generation']['mode']=='mock_or_injected_backend'
    assert payload['owner']['research_review']['generation']['owner']=='CANNOT_CONFIRM'
    assert payload['pit_status']=='CANNOT_CONFIRM'


def test_intraday_original_aggregate_process_boundary_publication_and_hash_mismatch(tmp_path,monkeypatch):
    sys.path.insert(0,str(OWNER_ROOT))
    from domains.intraday_research import aggregate_snapshot
    b=binding(tmp_path)
    snapshot=aggregate_snapshot(date='2026-10-12',slot='09:25',now=datetime.fromisoformat('2026-10-12T09:25:00+08:00'),prev='2026-10-09',
        pp={'zt':[{'code':'1','name':'a','boards':1,'sector':'x'}]},live=None,pct={'1':2.})
    proof={'artifact_sha256':'a'*64,'manifest_sha256':'b'*64,'receipt_sha256':'c'*64}
    original={'status':'SUCCEEDED',**proof}
    cold={'snapshot':snapshot,'proof':proof,'owner_bundle':{'input':{'fixture':True}},
          'intraday_research':{'status':'READY','missing_slots':['09:35','10:00','11:30','14:00','15:00'],'slots':[snapshot],'cannot_confirm':['LIVE_POOL_UNAVAILABLE']}}
    monkeypatch.setattr(daily,'_execute_guarded',lambda *_:{'status':'OWNER_RETURNED','owner_result':original})
    monkeypatch.setattr(daily,'_worker',lambda *_:cold)
    kwargs={'target_date':'2026-10-12','slot':'09:25','cutoff':'2026-10-12T09:33:00+08:00','run_id':'fixture-capture','sources':SOURCES}
    result=daily.capture(b,**kwargs)
    payload=IntradayCapsuleStore(b.archive_root/'intraday').read_verified(M11Slot(**result['identity']))
    assert payload['owner']['snapshot']==snapshot and len(payload['owner']['intraday_research']['missing_slots'])==5
    assert payload['pit_status']=='CANNOT_CONFIRM'
    original['receipt_sha256']='d'*64
    with pytest.raises(ValueError,match='COLD_READ_MISMATCH'):daily.capture(b,**kwargs)

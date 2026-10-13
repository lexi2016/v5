"""Original arithmetic and actual fixture-labelled writer; no production claims."""
import importlib.util
import json
from datetime import datetime,timedelta
from pathlib import Path
import sys
import pytest
from v5_shadow.m11.owner_sources import OWNER_ROOT,V5,verify_sources

verify_sources();sys.path.insert(0,str(OWNER_ROOT))
from domains.intraday_research import aggregate_snapshot,_window,SLOTS
from domains.research_review_generation.generation import run_generation,GenerationRefused
from domains.daily_research_review import load_daily_research_review


@pytest.mark.parametrize('slot',SLOTS)
def test_original_six_slot_arithmetic_and_missing_coverage(slot):
    now=datetime.fromisoformat('2026-10-12T'+slot+':00+08:00')
    pp={'zt':[{'code':'1','name':'a','boards':1,'sector':'x'},{'code':'2','name':'b','boards':2,'sector':'y'},{'code':'3','name':'c','boards':3,'sector':'x'}]}
    snap=aggregate_snapshot(date='2026-10-12',slot=slot,now=now,prev='2026-10-09',pp=pp,live=None,pct={'1':2.,'2':-6.})
    assert snap['avg']==-2. and snap['median']==-2. and snap['deep_loss_5']==1
    assert snap['sample']==2 and snap['expected_sample']==3 and snap['live'] is None
    assert snap['prev_date']=='2026-10-09' and snap['slot']==slot


def test_original_eight_minute_and_cross_day_boundary():
    now=datetime.fromisoformat('2026-10-12T09:25:00+08:00')
    assert _window('2026-10-12','09:25',now+timedelta(minutes=8,seconds=59))==8
    for instant in (now-timedelta(seconds=1),now+timedelta(minutes=9),now+timedelta(days=1)):
        with pytest.raises(ValueError):_window('2026-10-12','09:25',instant)


def test_actual_generation_fixture_writer_preserves_old_success_and_unknown_provenance(tmp_path):
    path=V5.parent/'handoffs/M11/original_source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/tests/test_research_review_generation.py'
    spec=importlib.util.spec_from_file_location('_m11_original_test_fixture',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    root=tmp_path/'reviews'
    result=run_generation('2026-10-12',review_root=root,backend=module._payload)
    assert result['mode']=='mock_or_injected_backend' and result['natural_generation']=='CANNOT_CONFIRM'
    raw=(root/'2026-10-12.json').read_bytes()
    with pytest.raises(GenerationRefused):run_generation('2026-10-12',review_root=root,backend=module._payload)
    assert (root/'2026-10-12.json').read_bytes()==raw
    loaded=load_daily_research_review('2026-10-12',review_root=root)
    assert loaded['status']=='READY' and loaded['generation']['owner']=='CANNOT_CONFIRM'
    assert loaded['orders_sent'] is False

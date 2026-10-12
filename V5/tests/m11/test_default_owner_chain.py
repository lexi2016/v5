import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest
from v5_shadow.m11.owner_sources import BUILD_MANIFEST_SHA


def binding(tmp_path):
    from v5_shadow.m11.daily import M11Binding
    state=tmp_path/'owner'; archive=tmp_path/'archive'; state.mkdir(); archive.mkdir()
    for root in (state,archive):(root/'.m11-private-root.json').write_text('{"module":"M11","private":true,"schema":"v5.private_root.v1"}')
    cfg={'schema':'v4.intraday_bindings.v1','state_root':str(state),'cache_root':str(state/'cache'),
         'cache_manifest_path':str(state/'inventory.json'),'cache_manifest_sha256':'1'*64,
         'source_id':'V4_OWNED_ORIGINAL_VIBE_DATA','source_manifest_sha256':BUILD_MANIFEST_SHA,'input_bindings':{}}
    path=tmp_path/'capture.json';raw=json.dumps(cfg).encode();path.write_bytes(raw)
    return M11Binding(state,archive,path,hashlib.sha256(raw).hexdigest(),BUILD_MANIFEST_SHA)


def test_default_capture_invokes_original_and_keeps_config_source_refusal(tmp_path):
    from v5_shadow.m11.daily import capture
    b=binding(tmp_path)
    from v5_shadow.m11.daily import M11Binding
    cfg=json.loads(b.config_path.read_text());cfg['source_manifest_sha256']='0'*64
    raw=json.dumps(cfg).encode();b.config_path.write_bytes(raw)
    b=M11Binding(b.state_root,b.archive_root,b.config_path,hashlib.sha256(raw).hexdigest(),BUILD_MANIFEST_SHA)
    result=capture(b,target_date='2026-10-12',slot='09:25',cutoff='2026-10-12T09:33:00+08:00',run_id='r1',sources=[{'event_time':'2026-10-12T09:25:00+08:00','published_at':'2026-10-12T09:25:00+08:00','observed_at':'2026-10-12T09:25:00+08:00','available_at':'2026-10-12T09:25:00+08:00'}])
    assert result['status']=='BLOCKED'
    assert result['error_code']=='M11_OWNER_REFUSED'
    assert result['owner_entry']=='domains.intraday_research.capture_intraday'
    assert result['owner_called'] is True
    assert not list(b.archive_root.rglob('commit.json'))
    assert not (b.state_root/'intraday').exists()


def test_get_original_reader_is_zero_write(tmp_path):
    from v5_shadow.m11.daily import read_owner_day
    b=binding(tmp_path)
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result=read_owner_day(b,'2026-10-12')
    assert result['intraday_research']['status']=='CANNOT_CONFIRM'
    assert len(result['intraday_research']['missing_slots'])==6
    assert result['research_review']['status']=='CANNOT_CONFIRM'
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def test_default_config_digest_and_overlap_rejected(tmp_path):
    from v5_shadow.m11.daily import capture, M11Binding
    b=binding(tmp_path); b.config_path.write_text('{}')
    with pytest.raises(ValueError,match='CONFIG_SHA'):
        capture(b,target_date='2026-10-12',slot='09:25',cutoff='2026-10-12T09:33:00+08:00',run_id='r1',sources=[{'event_time':'2026-10-12T09:25:00+08:00','published_at':'2026-10-12T09:25:00+08:00','observed_at':'2026-10-12T09:25:00+08:00','available_at':'2026-10-12T09:25:00+08:00'}])
    with pytest.raises(ValueError,match='OVERLAP'):
        M11Binding(b.state_root,b.state_root/'archive',b.config_path,b.config_sha256,b.owner_manifest_sha256).validate()


def test_unknown_availability_never_admitted():
    from v5_shadow.m11.daily import validate_availability
    with pytest.raises(ValueError):validate_availability([{'available_at':None}],'2026-10-12T09:33:00+08:00')
    with pytest.raises(ValueError):validate_availability([{'available_at':'2026-10-12T15:00:00+08:00'}],'2026-10-12T09:33:00+08:00')
    assert validate_availability([{'event_time':'2026-10-11T15:00:00+08:00','published_at':'2026-10-12T09:00:00+08:00','observed_at':'2026-10-12T09:10:00+08:00','available_at':'2026-10-12T09:20:00+08:00'}],'2026-10-12T09:33:00+08:00')


def test_unknown_source_times_refuse_before_owner_request(tmp_path):
    from v5_shadow.m11.daily import capture
    b=binding(tmp_path)
    with pytest.raises(ValueError,match='AVAILABILITY_UNKNOWN'):
        capture(b,target_date='2026-10-12',slot='09:25',cutoff='2026-10-12T09:33:00+08:00',run_id='r1')
    assert not (b.state_root/'intraday').exists()


def test_default_daily_assembly_invoked_and_missing_profile_gate_preserved(tmp_path):
    from v5_shadow.m11.daily import generate,M11Binding
    b=binding(tmp_path)
    cfg={'schema':'v4.vibe_assembly.v1','state_root':str(b.state_root),'cache_root':str(b.state_root/'cache'),
         'cache_manifest_path':str(b.state_root/'inventory.json'),'cache_manifest_sha256':'1'*64,
         'profile_path':str(tmp_path/'profile.json'),'profile_sha256':'2'*64,
         'credential_db':str(tmp_path/'synthetic-never-opened.db'),'data_mode':'snapshot','data_as_of':'2026-10-12T15:00:00+08:00','snapshot_sha256':'3'*64}
    raw=json.dumps(cfg).encode();b.config_path.write_bytes(raw)
    b=M11Binding(b.state_root,b.archive_root,b.config_path,hashlib.sha256(raw).hexdigest(),BUILD_MANIFEST_SHA)
    result=generate(b,target_date='2026-10-12',cutoff='2026-10-12T15:05:00+08:00',run_id='generation1',sources=[{'event_time':'2026-10-12T15:00:00+08:00','published_at':'2026-10-12T15:00:00+08:00','observed_at':'2026-10-12T15:00:00+08:00','available_at':'2026-10-12T15:00:00+08:00'}])
    assert result['owner_called'] is True
    assert result['owner_entry']=='domains.research_review_generation.assembly.assemble_runtime'
    assert result['error_code']=='M11_OWNER_REFUSED'
    assert not list(b.archive_root.rglob('commit.json'))
    assert not (tmp_path/'synthetic-never-opened.db').exists()


def test_durable_unknown_worker_marker_never_retries(tmp_path):
    from v5_shadow.m11.daily import _execute_guarded
    b=binding(tmp_path)
    req=b.request('capture','2026-10-12','09:25')
    from v5_shadow.m11.intraday_capsule import _digest,_encoded
    from v5_shadow.m11.owner_sources import safe_root_class
    key=_digest(req)
    safe_root_class()(b.archive_root).write_bytes('executions/'+key+'.json',_encoded({'phase':'REQUEST_IN_FLIGHT'}))
    result=_execute_guarded(b,req)
    assert result['attempt_state']=='ATTEMPT_UNKNOWN'
    assert result['error_code']=='M11_RECONCILIATION_REQUIRED'
    assert not (b.state_root/'intraday').exists()


def test_capture_cutoff_cannot_borrow_next_day(tmp_path):
    from v5_shadow.m11.daily import capture
    b=binding(tmp_path)
    with pytest.raises(ValueError,match='CUTOFF'):
        capture(b,target_date='2026-10-12',slot='09:25',cutoff='2026-10-13T09:33:00+08:00',run_id='r1',sources=[{'event_time':'2026-10-12T09:25:00+08:00','published_at':'2026-10-12T09:25:00+08:00','observed_at':'2026-10-12T09:25:00+08:00','available_at':'2026-10-12T09:25:00+08:00'}])
    assert not (b.archive_root/'executions').exists()

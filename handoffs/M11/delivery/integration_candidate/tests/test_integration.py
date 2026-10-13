"""Candidate-only executable contracts. Fake owners never constitute real evidence."""
import importlib.util
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Event

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'after/V5/src/v5_shadow/m11/service.py'


def load_service():
    assert MODULE.is_file(), 'M11 private service candidate has not been implemented'
    spec = importlib.util.spec_from_file_location('m11_candidate_service', MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class Binding:
    state_root: Path
    archive_root: Path
    config_path: Path
    config_sha256: str = 'a' * 64
    owner_manifest_sha256: str = 'b' * 64
    def validate(self):
        return {}


def plan(m, tmp_path, slot=None):
    stamp = '2026-10-12T09:25:00+08:00' if slot else '2026-10-12T16:00:00+08:00'
    return m.BoundPlan(Binding(tmp_path/'state', tmp_path/'archive', tmp_path/'config.json'),
                       '2026-10-12', stamp,
                       [{'sha256': 'c'*64, 'event_time': stamp, 'published_at': stamp,
                         'observed_at': stamp, 'available_at': stamp}], slot)


def wait_job(service, job_id):
    for _ in range(200):
        job = service.get_job(job_id)
        if job['status'] not in {'QUEUED','RUNNING'}:
            return job
        time.sleep(.01)
    pytest.fail('job did not finish')


def test_get_absent_day_has_no_side_effects(tmp_path):
    m = load_service()
    s = m.Service([plan(m, tmp_path)], tmp_path/'jobs', owner=lambda *a, **k: pytest.fail('GET ran owner'))
    try:
        before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
        value = s.get_day('20261012')
        assert value['status'] == 'CANNOT_CONFIRM'
        assert value['pit_status'] == 'CANNOT_CONFIRM'
        assert value['jobs'] == []
        assert before == {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    finally: s.close()


def test_concurrent_identical_intent_is_one_opaque_job(tmp_path):
    m = load_service(); entered = Event(); release = Event(); calls=[]
    def owner(operation, binding, **kwargs):
        calls.append(kwargs); entered.set(); release.wait(2)
        return {'status':'BLOCKED', 'error_code':'MISSING_REAL_OWNER_MANIFEST', 'attempt_state':'FAILED_NO_REQUEST'}
    s = m.Service([plan(m,tmp_path)], tmp_path/'jobs', owner=owner)
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            result = list(pool.map(lambda _: s.submit('20261012','a'*32), range(8)))
        assert len({j['job_id'] for j in result}) == 1
        assert len(result[0]['job_id']) == 32 and result[0]['job_id'] != 'a'*32
        assert entered.wait(1); release.set()
        final=wait_job(s, result[0]['job_id'])
        assert final['status']=='BLOCKED' and len(calls)==1
        assert final['owner']['attempt_state']=='FAILED_NO_REQUEST'
        assert 'config_path' not in json.dumps(final)
        assert s.submit('20261012','a'*32)['job_id']==final['job_id']
    finally: release.set(); s.close()


def test_new_intent_retains_old_success_and_readbacks_same_run(tmp_path):
    m=load_service()
    def owner(operation,binding,**kwargs):
        return {'status':'COMMITTED','identity':{'run_id':kwargs['run_id'],'target_date':kwargs['target_date'],'slot':'15:00'},'business_status':'READY'}
    def readback(binding, operation, identity):
        return {'status':'READY','owner':{'research_review':{'status':'READY','focus':{'note':'same run '+identity['run_id']}}}}
    s=m.Service([plan(m,tmp_path)],tmp_path/'jobs',owner=owner,readback=readback)
    try:
        first=wait_job(s,s.submit('20261012','a'*32)['job_id'])
        second=wait_job(s,s.submit('20261012','b'*32)['job_id'])
        assert first['job_id'] != second['job_id']
        day=s.get_day('20261012')
        assert len(day['jobs'])==2 and len(day['committed'])==2
        assert day['committed'][0]['payload']['research_review']['focus']['note'].startswith('same run ')
        assert all(j['pit_status']=='CANNOT_CONFIRM' for j in day['committed'])
    finally:s.close()


def test_unknown_job_refuses_new_intent_after_restart(tmp_path):
    m=load_service()
    def owner(*a,**k):raise TimeoutError('provider may have charged')
    s=m.Service([plan(m,tmp_path)],tmp_path/'jobs',owner=owner)
    job=wait_job(s,s.submit('20261012','a'*32)['job_id']);s.close()
    assert job['status']=='ATTEMPT_UNKNOWN'
    s=m.Service([plan(m,tmp_path)],tmp_path/'jobs',owner=lambda *a,**k:pytest.fail('unknown retried'))
    try:
        with pytest.raises(m.Refused,match='ATTEMPT_REQUIRES_REVIEW'):s.submit('20261012','b'*32)
        assert s.submit('20261012','a'*32)['status']=='ATTEMPT_UNKNOWN'
    finally:s.close()


def test_interrupted_running_marker_is_unknown_without_get_writes(tmp_path):
    m=load_service();s=m.Service([plan(m,tmp_path)],tmp_path/'jobs',owner=lambda *a,**k:{'status':'BLOCKED'})
    job=wait_job(s,s.submit('20261012','a'*32)['job_id']);s.close()
    path=tmp_path/'jobs'/f"{job['job_id']}.json"
    value=json.loads(path.read_text());value['status']='RUNNING';path.write_text(json.dumps(value))
    s=m.Service([plan(m,tmp_path)],tmp_path/'jobs')
    try:
        before=path.read_bytes()
        assert s.get_job(job['job_id'])['status']=='ATTEMPT_UNKNOWN'
        assert path.read_bytes()==before
        with pytest.raises(m.Refused,match='ATTEMPT_REQUIRES_REVIEW'):s.submit('20261012','b'*32)
    finally:s.close()


@pytest.mark.parametrize('bad', ['../../etc/passwd','', '20260231', 'http://localhost', '2026-10-12/xx'])
def test_http_date_and_path_input_are_rejected(tmp_path,bad):
    m=load_service();s=m.Service([plan(m,tmp_path)],tmp_path/'jobs')
    try:
        with pytest.raises(m.Refused):s.get_day(bad)
    finally:s.close()


def test_corrupt_or_symlink_job_never_retried(tmp_path):
    m=load_service();s=m.Service([plan(m,tmp_path)],tmp_path/'jobs');s.close()
    (tmp_path/'jobs'/('f'*32+'.json')).write_text('{bad')
    with pytest.raises(m.Refused,match='JOB_STORE_UNTRUSTED'):m.Service([plan(m,tmp_path)],tmp_path/'jobs')


def test_duplicate_process_lease_refused(tmp_path):
    m=load_service();s=m.Service([plan(m,tmp_path)],tmp_path/'jobs')
    try:
        with pytest.raises(m.Refused,match='SERVICE_ALREADY_RUNNING'):m.Service([plan(m,tmp_path)],tmp_path/'jobs')
    finally:s.close()


def test_original_minute_window_and_only_six_slots(tmp_path):
    m=load_service()
    assert m.SLOTS==('09:25','09:35','10:00','11:30','14:00','15:00')
    assert m.slot_due('2026-10-12','09:25',datetime.fromisoformat('2026-10-12T09:33:59+08:00'))
    assert not m.slot_due('2026-10-12','09:25',datetime.fromisoformat('2026-10-12T09:34:00+08:00'))
    assert not m.slot_due('2026-10-12','09:25',datetime.fromisoformat('2026-10-12T09:24:59+08:00'))
    assert not m.slot_due('2026-10-12','09:25',datetime.fromisoformat('2026-10-13T09:25:00+08:00'))
    assert not m.slot_due('2026-10-12','11:00',datetime.fromisoformat('2026-10-12T11:00:00+08:00'))


def test_scheduler_calls_capture_only_with_pinned_trading_day(tmp_path):
    m=load_service();calls=[]
    def owner(operation,binding,**kwargs):calls.append(operation);return {'status':'BLOCKED','attempt_state':'FAILED_NO_REQUEST'}
    s=m.Service([plan(m,tmp_path),plan(m,tmp_path,'09:25')],tmp_path/'jobs',owner=owner)
    try:
        now=datetime.fromisoformat('2026-10-12T09:25:00+08:00')
        assert s.dispatch_due(now,trading_dates=[])==[]
        result=s.dispatch_due(now,trading_dates=['2026-10-12'])
        assert len(result)==1
        wait_job(s,result[0]['job_id'])
        assert calls==['capture']
        assert s.dispatch_due(now,trading_dates=['2026-10-12'])[0]['job_id']==result[0]['job_id']
    finally:s.close()


def test_unknown_availability_and_late_input_refused_at_startup(tmp_path):
    m=load_service();p=plan(m,tmp_path)
    for bad in (None,'2026-10-12T17:00:00+08:00'):
        source=dict(p.sources[0],available_at=bad)
        with pytest.raises(m.Refused):m.Service([m.BoundPlan(p.binding,p.target_date,p.cutoff,[source])],tmp_path/str(bad).replace(':',''))


def test_job_root_renaming_is_detected_without_writing_replacement(tmp_path):
    m=load_service();s=m.Service([plan(m,tmp_path)],tmp_path/'jobs')
    (tmp_path/'jobs').rename(tmp_path/'old-jobs');(tmp_path/'jobs').mkdir()
    try:
        with pytest.raises(m.Refused,match='ROOT_REPLACED'):s.get_day('20261012')
        assert list((tmp_path/'jobs').iterdir())==[]
    finally:s.close()


def test_source_identity_and_bound_snapshot_are_not_mutable_by_caller(tmp_path):
    m=load_service();p=plan(m,tmp_path);s=m.Service([p],tmp_path/'jobs')
    try:
        key=next(iter(s.plans.values())).key()
        p.sources[0]['sha256']='f'*64
        assert next(iter(s.plans.values())).key()==key
    finally:s.close()


def test_http_get_zero_writes_post_async_rejects_extra_paths(tmp_path):
    import http.client
    from threading import Thread
    m=load_service();release=Event();calls=[]
    def owner(*a,**k):calls.append(k);release.wait(2);return {'status':'BLOCKED','attempt_state':'FAILED_NO_REQUEST'}
    s=m.Service([plan(m,tmp_path)],tmp_path/'jobs',owner=owner)
    server=m.create_server(s);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    def request(method,path,body=None,extra=None):
        c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=1)
        headers={'Content-Type':'application/json',**(extra or {})}
        c.request(method,path,body=json.dumps(body) if body is not None else None,headers=headers)
        r=c.getresponse();result=(r.status,json.loads(r.read()));c.close();return result
    try:
        before={p.name:p.read_bytes() for p in (tmp_path/'jobs').iterdir() if p.is_file()}
        assert request('GET','/api/v5/m11/day?date=20261012')[0]==200
        assert not calls and before=={p.name:p.read_bytes() for p in (tmp_path/'jobs').iterdir() if p.is_file()}
        assert request('POST','/api/v5/m11/generate',{'date':'20261012','intent_id':'a'*32,'config_path':'/tmp/x'})[0]==400
        assert not calls
        code,body=request('POST','/api/v5/m11/generate',{'date':'20261012','intent_id':'a'*32})
        assert code==202 and body['status'] in {'QUEUED','RUNNING'}
        assert request('GET','/api/v5/m11/job?job_id='+body['job_id'])[0]==200
        assert request('GET','/api/v5/m11/day?date=20261012',extra={'Origin':'https://evil.invalid'})[0]==400
    finally:release.set();server.shutdown();server.server_close();s.close()

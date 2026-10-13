"""Synthetic offline bounded-capture contracts. No live connector is selected."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import fcntl
import time
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HELPER = Path(os.environ['M14_CAPTURE_HELPER'])
BASE = Path(os.environ['M14_BASELINE_ROOT'])
MODULE = ROOT / 'rebound_history_batch.py'

def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
def sha(x):
    return hashlib.sha256(x).hexdigest()
def write(path, value):
    path.write_bytes(canonical(value)); return sha(path.read_bytes())
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def row(day):
    return dict(datetime=datetime.strptime(day, '%Y%m%d').strftime('%Y-%m-%d 15:00'),open=10,high=12,low=9,close=11,trade=2345,volume=999,amount=None)

class API:
    def __init__(self, responses):
        self.responses = responses; self.calls=[]; self.disconnected=0
    def get_instrument_bars(self, *args):
        self.calls.append(args)
        response=self.responses[len(self.calls)-1]
        if isinstance(response, BaseException): raise response
        return response
    def disconnect(self): self.disconnected += 1

class BatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MODULE.exists(): raise AssertionError('bounded history batch implementation is missing')
        cls.m=load(MODULE, 'batch_candidate'); cls.h=load(HELPER,'canary_candidate')
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.output=self.root/'capture'
        self.now=datetime(2026,10,14,0,0,tzinfo=timezone.utc); self.tick=0.; self.sleeps=[]; self.connects=0
        codes=['HK.00001','HK.00002','HK.00003','HK.02825','HK.03469']
        members=sorted(codes+['HK.09999'])
        keys=[dict(code=c,date=d) for c in codes for d in ['20261009','20261012']]
        files={}; digests={}
        documents=dict(parent_panel={'fixture':'panel'},parent_pointer={'manifest_relative':'panels/original/manifest.json'})
        def evidence(name, value):
            p=self.root/(name+'.json'); digests[name]=write(p,value); files[name]=str(p)
        evidence('parent_panel',documents['parent_panel'])
        evidence('parent_manifest',dict(panel_relative='panels/original/hkconnect_vipdoc_daily_panel.parquet',panel_sha256=digests['parent_panel'],panel_max_date='20261013'))
        evidence('parent_pointer',documents['parent_pointer'])
        request=dict(target_date='20261014',signal_date='20261013',paths=dict(panel='assets/hk_0_2/panels/original/hkconnect_vipdoc_daily_panel.parquet',panel_manifest='assets/hk_0_2/panels/original/manifest.json'),files={'assets/hk_0_2/panels/original/hkconnect_vipdoc_daily_panel.parquet':digests['parent_panel'],'assets/hk_0_2/panels/original/manifest.json':digests['parent_manifest']})
        evidence('original_artifact',dict(schema_version='v5.rebound_owner.v1',run_id='0'*32,request=request,request_sha256=sha(canonical(request)),research_observation=dict(strict=[],near=[],pending=[dict(code=c) for c in members],excluded=[],screen_unresolved=[])))
        evidence('original_manifest',dict(schema_version='v5.rebound_owner_manifest.v1',run_id='0'*32,artifact_sha256=digests['original_artifact'],request_sha256=sha(canonical(request)),target_date='20261014'))
        evidence('original_receipt',dict(schema_version='v5.rebound_owner_receipt.v1',run_id='0'*32,status='COMMITTED',artifact_sha256=digests['original_artifact'],manifest_sha256=digests['original_manifest']))
        self.task=dict(schema_version='v5.m14_history_batch_task.v1',target_date='20261014',signal_date='20261013',
            prepared_at=self.now.isoformat(),valid_until=(self.now+timedelta(hours=2)).isoformat(),
            exact_member_codes=members,exact_member_codes_sha256=sha(canonical(members)),keys=keys,
            keys_sha256=sha(canonical(keys)),expected_panel_sha256=digests['parent_panel'],
            original_reference=dict(run_id='0'*32,artifact_sha256=digests['original_artifact'],manifest_sha256=digests['original_manifest'],receipt_sha256=digests['original_receipt']),
            parent_binding=dict(parent_pointer_sha256=digests['parent_pointer'],parent_manifest_relative='panels/original/manifest.json',parent_manifest_sha256=digests['parent_manifest'],parent_panel_relative='panels/original/hkconnect_vipdoc_daily_panel.parquet',parent_panel_sha256=digests['parent_panel']),initial_reuse=[])
        self.context=dict(schema_version='v5.m14_history_batch_context.v1',target_date='20261014',signal_date='20261013',
            original_reference=copy.deepcopy(self.task['original_reference']),parent_binding=copy.deepcopy(self.task['parent_binding']),exact_member_codes=members,keys=keys,files=files)
        self.context_path=self.root/'context.json'; write(self.context_path,self.context)
        for i,c in enumerate(['HK.00001','HK.02825','HK.03469']):
            canary={k:copy.deepcopy(self.task[k]) for k in ['target_date','signal_date','keys','expected_panel_sha256','original_reference','parent_binding']}
            canary.update(schema_version=self.h.TASK_SCHEMA,canary_codes=[c],keys=[k for k in keys if k['code']==c])
            plan=self.h.prepare_plan(canary,baseline_root=BASE)
            path=self.root/f'canary-{i}'; api=API([[row('20261009')] if c=='HK.03469' else [row('20261009'),row('20261012')]])
            old_now=self.now-timedelta(minutes=10)
            result=self.h.capture_plan(plan,baseline_root=BASE,output_dir=path,connector=lambda:(api,self.h.ENDPOINT),clock=lambda:old_now)
            source=result['sources'][0]
            self.task['initial_reuse'].append(dict(code=c,receipt_path=str(path/source['relative']),receipt_sha256=source['sha256'],plan_path=str(path/'plan.json'),plan_sha256=sha((path/'plan.json').read_bytes())))
    def clock(self): return self.now+timedelta(seconds=self.tick)
    def mono(self): return self.tick
    def sleep(self, seconds): self.sleeps.append(seconds); self.tick+=seconds
    def plan(self, task=None):
        return self.m.prepare_plan(task or self.task,baseline_root=BASE,capture_helper=HELPER,context_file=self.context_path,clock=self.clock)
    def capture(self,responses=None,plan=None,**kwargs):
        api=API(responses or [])
        def connect(): self.connects+=1; return api,self.h.ENDPOINT
        result=self.m.capture_plan(plan or self.plan(),baseline_root=BASE,capture_helper=HELPER,context_file=self.context_path,output_dir=self.output,connector=connect,clock=self.clock,monotonic=self.mono,sleep=self.sleep,**kwargs)
        return result,api
    def test_preparation_output_matches_batch_contract(self):
        prep=load(ROOT.parent/'preparation/prepare_history_batch.py','batch_preparation')
        artifact=json.loads(Path(self.context['files']['original_artifact']).read_bytes())
        task,context=prep.task_and_context(artifact=artifact,reference=self.task['original_reference'],
            parent=self.task['parent_binding'],members=self.task['exact_member_codes'],keys=self.task['keys'],
            files=self.context['files'],reuse=self.task['initial_reuse'],now=self.now)
        write(self.context_path,context)
        with patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK')):
            plan=self.plan(task)
        self.assertEqual(plan['query_codes'],['HK.00002','HK.00003'])
        self.assertEqual(plan['task']['initial_reuse'],self.task['initial_reuse'])
    def test_plan_offline_exact_members_keys_and_three_receipts(self):
        with patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK')):
            plan=self.plan()
        self.assertEqual(plan['query_codes'],['HK.00002','HK.00003'])
        self.assertEqual(plan['max_connections_per_invocation'],1)
        self.assertEqual(plan['request_template']['count'],120)
        self.assertEqual(len(plan['initial_reuse']),3)
    def test_capture_reuses_missing_canary_without_retry_and_whole_rows(self):
        rows=[row('20261009'),row('20261012'),row('20261014')]
        result,api=self.capture([rows,rows])
        self.assertEqual(self.connects,1); self.assertEqual(api.disconnected,1)
        self.assertEqual(api.calls,[(4,71,'00002',0,120),(4,71,'00003',0,120)])
        self.assertEqual(self.sleeps,[1.0]); self.assertEqual(result['reused_count'],3)
        self.assertEqual(result['attempted_count'],2); self.assertEqual(result['receipt_count'],5)
        self.assertIn(dict(code='HK.03469',date='20261012'),result['missing_keys'])
        self.assertFalse(result['repair_ready']); self.assertEqual(result['pending_codes'],[])
        for ref in result['sources']:
            self.assertEqual(set(ref),{'relative','sha256','record_pointer'}); self.assertEqual(ref['record_pointer'],'')
            raw=(self.output/ref['relative']).read_bytes(); self.assertEqual(sha(raw),ref['sha256'])
        new=[json.loads((self.output/r['relative']).read_bytes()) for r in result['sources'] if 'receipt-HK.00002' in r['relative']][0]
        self.assertEqual(new['source_rows'],rows); self.assertEqual(new['response_sha256'],sha(canonical(rows)))
    def test_maxcalls_then_resume_never_reissues_receipts(self):
        first,a=self.capture([[row('20261009')]],max_calls=1)
        self.assertEqual(first['pending_codes'],['HK.00003'])
        second,b=self.capture([[row('20261012')]],max_calls=1)
        self.assertEqual(b.calls,[(4,71,'00003',0,120)])
        self.assertEqual(second['reused_count'],3); self.assertEqual(second['attempted_count'],2)
        third,c=self.capture([])
        self.assertEqual(c.calls,[]); self.assertEqual(self.connects,2)
    def test_interrupted_started_attempt_is_unknown_not_retried(self):
        with self.assertRaises(KeyboardInterrupt): self.capture([KeyboardInterrupt()],max_calls=1)
        result,api=self.capture([[row('20261009')]])
        self.assertEqual(api.calls,[(4,71,'00003',0,120)])
        self.assertEqual(result['uncertain_codes'],['HK.00002']); self.assertEqual(result['attempted_count'],2)
    def test_failure_and_missing_are_final_no_auto_retry(self):
        one,api=self.capture([ConnectionError('offline')])
        self.assertEqual(len(api.calls),1)
        two,next_api=self.capture([[]])
        self.assertEqual(next_api.calls,[(4,71,'00003',0,120)])
        three,last=self.capture([])
        self.assertEqual(last.calls,[]); self.assertEqual(three['failed_codes'],['HK.00002'])
    def test_tampered_receipt_blocks_before_connect(self):
        result,_=self.capture([[row('20261009')]],max_calls=1)
        file=self.output/result['sources'][-1]['relative']; os.chmod(file,0o600); file.write_bytes(file.read_bytes()+b' ')
        with self.assertRaises(ValueError): self.capture([])
        self.assertEqual(self.connects,1)
    def test_stale_current_context_file_blocks_before_connect(self):
        self.capture([[row('20261009')]],max_calls=1)
        Path(self.context['files']['parent_pointer']).write_text('changed')
        with self.assertRaises(ValueError): self.capture([])
        self.assertEqual(self.connects,1)
    def test_stale_task_time_rejected(self):
        self.tick=7201
        with self.assertRaises(ValueError): self.plan()
    def test_duplicate_member_code_and_nonmember_key_rejected(self):
        for mutate in [lambda t:t['exact_member_codes'].append(t['exact_member_codes'][0]),lambda t:t['keys'].append(dict(code='HK.12345',date='20261009'))]:
            t=copy.deepcopy(self.task); mutate(t)
            with self.assertRaises(ValueError): self.plan(t)
    def test_cross_run_reuse_identity_and_response_hash_rejected(self):
        descriptor=self.task['initial_reuse'][0]; p=Path(descriptor['receipt_path']); raw=json.loads(p.read_bytes())
        for field,value in [('original_reference',dict(self.task['original_reference'],run_id='1'*32)),('response_sha256','1'*64)]:
            bad=copy.deepcopy(raw); bad[field]=value; os.chmod(p,0o600); descriptor['receipt_sha256']=write(p,bad)
            with self.assertRaises(ValueError): self.plan()
    def test_changed_task_cannot_resume_even_with_valid_context(self):
        self.capture([[row('20261009')]],max_calls=1)
        self.task['valid_until']=(self.now+timedelta(minutes=90)).isoformat()
        with self.assertRaises(ValueError): self.capture([])
        self.assertEqual(self.connects,1)
    def test_time_budget_stops_before_second_call(self):
        result,api=self.capture([[row('20261009')]],max_seconds=0.5)
        self.assertEqual(len(api.calls),1); self.assertEqual(result['pending_codes'],['HK.00003'])
    def test_symlink_helper_and_evidence_rejected(self):
        link=self.root/'helper.py'; link.symlink_to(HELPER)
        with self.assertRaises((ValueError,OSError)):
            self.m.prepare_plan(self.task,baseline_root=BASE,capture_helper=link,context_file=self.context_path,clock=self.clock)
    def test_resume_is_offline_and_validates_journal(self):
        self.capture([[row('20261009')]],max_calls=1)
        with patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK')):
            result=self.m.resume_plan(self.plan(),baseline_root=BASE,capture_helper=HELPER,context_file=self.context_path,output_dir=self.output,clock=self.clock)
        self.assertEqual(result['pending_codes'],['HK.00003'])

    def test_rate_limit_survives_immediate_resume(self):
        self.capture([[row('20261009')]],max_calls=1)
        self.capture([[row('20261009')]],max_calls=1)
        self.assertEqual(self.sleeps,[1.0])
    def test_context_semantic_pool_rejected_even_with_consistent_sha(self):
        p=Path(self.context['files']['original_artifact']); artifact=json.loads(p.read_bytes())
        artifact['research_observation']['pending'][0]['code']='HK.12345'
        digest=write(p,artifact)
        self.task['original_reference']['artifact_sha256']=digest
        self.context['original_reference']['artifact_sha256']=digest
        write(self.context_path,self.context)
        with self.assertRaises(ValueError): self.plan()
        self.assertEqual(self.connects,0)
    def test_receipt_file_hash_and_helper_source_pin_rejected(self):
        p=Path(self.task['initial_reuse'][0]['receipt_path']); os.chmod(p,0o600); p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaises(ValueError): self.plan()
        helper=self.root/'tampered.py'; helper.write_bytes(HELPER.read_bytes()+b'\n')
        with self.assertRaises(ValueError):
            self.m.prepare_plan(self.task,baseline_root=BASE,capture_helper=helper,context_file=self.context_path,clock=self.clock)
    def test_second_writer_cannot_connect(self):
        self.capture([[row('20261009')]],max_calls=1)
        fd=os.open(self.output,os.O_RDONLY|os.O_DIRECTORY)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.capture([])
        finally: os.close(fd)
        self.assertEqual(self.connects,1)
    def test_per_query_context_change_stops_without_second_query(self):
        api=API([[row('20261009')],[row('20261009')]])
        def sleep(seconds):
            self.sleep(seconds); Path(self.context['files']['parent_pointer']).write_text('changed')
        with self.assertRaises(ValueError):
            self.m.capture_plan(self.plan(),baseline_root=BASE,capture_helper=HELPER,context_file=self.context_path,output_dir=self.output,connector=lambda:(api,self.h.ENDPOINT),clock=self.clock,monotonic=self.mono,sleep=sleep)
        self.assertEqual(api.calls,[(4,71,'00002',0,120)]); self.assertEqual(api.disconnected,1)
    def test_orphan_file_fails_closed_without_retry(self):
        self.capture([[row('20261009')]],max_calls=1)
        write(self.output/'attempt-HK.00003.json',dict(status='STARTED'))
        with self.assertRaises(ValueError): self.capture([])
        self.assertEqual(self.connects,1)
    def test_connection_failure_makes_no_code_attempt(self):
        def connector(): raise ConnectionError('offline')
        result=self.m.capture_plan(self.plan(),baseline_root=BASE,capture_helper=HELPER,context_file=self.context_path,output_dir=self.output,connector=connector,clock=self.clock,monotonic=self.mono,sleep=self.sleep)
        self.assertEqual(result['attempted_count'],0); self.assertEqual(result['receipt_count'],3)
        self.assertEqual(result['stop_reason'],'CONNECT_FAILED')
    def test_wrong_endpoint_never_queries_or_switches_host(self):
        api=API([])
        result=self.m.capture_plan(self.plan(),baseline_root=BASE,capture_helper=HELPER,context_file=self.context_path,output_dir=self.output,connector=lambda:(api,'invalid:1234'),clock=self.clock,monotonic=self.mono,sleep=self.sleep)
        self.assertEqual(api.calls,[]); self.assertEqual(api.disconnected,1); self.assertEqual(result['stop_reason'],'CONNECT_FAILED')
    def test_invalid_response_preserved_and_not_retried(self):
        payload={'not':'a bar list'}
        result,api=self.capture([payload])
        ref=[r for r in result['receipts'] if r['relative']=='receipt-HK.00002.json'][0]
        record=json.loads((self.output/ref['relative']).read_bytes())
        self.assertEqual(record['source_rows'],payload); self.assertEqual(record['response_sha256'],sha(canonical(payload)))
        self.assertEqual(record['status'],'RESPONSE_INVALID')
        next_result,next_api=self.capture([[]])
        self.assertEqual(next_api.calls,[(4,71,'00003',0,120)])
    def test_limits_are_validated_before_connection(self):
        for kwargs in [dict(max_calls=0),dict(max_calls=1001),dict(max_calls=True),dict(max_seconds=0),dict(max_seconds=float('nan')),dict(max_seconds=3601)]:
            with self.assertRaises(ValueError): self.capture([],**kwargs)
        self.assertEqual(self.connects,0)
    def test_initial_three_canary_sources_cannot_be_omitted(self):
        self.task['initial_reuse'].pop()
        with self.assertRaises(ValueError): self.plan()
    def test_hard_deadline_interrupts_real_wait(self):
        with self.assertRaises(self.m._DeadlineExpired):
            with self.m._hard_deadline(.02): time.sleep(.5)
    def test_existing_receipt_count_is_distinct_from_new_attempts(self):
        first,_=self.capture([[row('20261009')]],max_calls=1)
        second,_=self.capture([[row('20261009')]],max_calls=1)
        self.assertEqual(first['existing_receipt_count'],3)
        self.assertEqual(second['existing_receipt_count'],4)
        self.assertEqual(second['invocation_attempted_count'],1)

if __name__=='__main__': unittest.main()

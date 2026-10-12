"""New real-path contract tests with an isolated synthetic TdxExHq network boundary.
No live network, PyTDX installation, real market evidence, or ef2d test rerun.
"""
from datetime import datetime,timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from zoneinfo import ZoneInfo

HERE=Path(__file__).resolve().parents[1]
REPO=next(p for p in (HERE,*HERE.parents) if (p/'V5/vendor/close_discovery_baseline').is_dir())
sys.path.insert(0,str(HERE/'src'));sys.path.insert(0,str(HERE/'tests'))
from test_daily_close_recapture_owner import fixture, encoded,digest
from v5_shadow import daily_close_recapture_owner as adapter


def real_fixture(root):
    request,ledger=fixture(root)
    sys.path.insert(0,request['config']['owner_root'])
    from contracts.trading_calendar import load_market_calendar,previous_session
    calendar=load_market_calendar();today=datetime.now(ZoneInfo('Asia/Hong_Kong')).strftime('%Y%m%d')
    source=previous_session(calendar,today,market='hk_connect');signal=previous_session(calendar,source,market='hk_connect')
    folder=next(Path(request['config']['universe_root']).rglob('manifest.json')).parent
    old=folder.parent.parent.name
    relative=f'runs/{source}/HK_CONNECT_D1_TOP100_0_2/{source}-hk-connect-d1-top100-0-2-fixture'
    new=Path(request['config']['universe_root'])/'.runtime/data'/relative;new.mkdir(parents=True)
    raw=(folder/'artifact.csv').read_bytes().replace(b'20260928',source.encode()).replace(b'20260924',signal.encode());(new/'artifact.csv').write_bytes(raw)
    manifest=json.loads((folder/'manifest.json').read_bytes());manifest.update(trade_date=source,signal_date=signal,captured_at=f'{signal[:4]}-{signal[4:6]}-{signal[6:]}T17:30:43+08:00',artifact_relative=relative+'/artifact.csv',artifact_sha256=digest(raw))
    raw=encoded(manifest);(new/'manifest.json').write_bytes(raw)
    receipt=json.loads((folder/'receipt.json').read_bytes());receipt.update(trade_date=source,run_id=new.name,artifact_sha256=manifest['artifact_sha256'],manifest_sha256=digest(raw));(new/'receipt.json').write_bytes(encoded(receipt))
    # Old fixture date is outside the current exact-date role; it is never selected.
    config=request['config'];config['timeout_seconds']=420
    (Path(config['state_root'])/'.v5-m17-close-root').write_bytes(b'v5.m17.close.v1\n')
    config['real_binding']=dict(active_capture_mode='PYTDX_LATE_OBSERVATION',pytdx_python=config['python'],pytdx_python_sha256=digest(Path(config['python']).resolve().read_bytes()),pytdx_exhq_sha256=digest(b'SYNTHETIC_TEST_BOUNDARY'),provider_root=str(Path(config['owner_root'])/'upstreams/v3_shared_data'),state_root=config['state_root'],universe_root=config['universe_root'])
    request.update(source_trade_date=source,research_cutoff=datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat(),execution_kind='OWNER_VERIFIED');request.pop('simulation')
    return request,ledger


def harness(path):
    """Only this test harness replaces the network/runtime boundary, never config."""
    packet=json.loads(Path(path).read_text());request=packet.get('request',packet);run_id=packet.get('ledger_run_id','real-contract-run');source=request['source_trade_date'];calls=[]
    def no_network(event,args):
        if event.startswith('socket.'):raise AssertionError('LIVE_NETWORK_FORBIDDEN_IN_TEST')
    sys.addaudithook(no_network)
    class FakeAPI:
        def __init__(self,**kw):calls.append(['construct',kw])
        def connect(self,host,port,**kw):calls.append(['connect',host,port]);return True
        def disconnect(self):calls.append(['disconnect'])
        def get_instrument_bars(self,category,market,code,start,count):
            calls.append(['bars',category,market,code,start,count]);day=datetime.strptime(source,'%Y%m%d');prior=day-timedelta(days=1)
            return [dict(datetime=prior.strftime('%Y-%m-%d')+' 16:00:00',open=10,high=10,low=10,close=10,vol=1,amount=10),dict(datetime=day.strftime('%Y-%m-%d')+' 15:46:00',open=10,high=11,low=9,last=10.5,close=10.5,vol=100,amount=1050)]
    package=types.ModuleType('pytdx');package.__path__=[];module=types.ModuleType('pytdx.exhq');module.TdxExHq_API=FakeAPI
    sys.modules['pytdx']=package;sys.modules['pytdx.exhq']=module
    original_run=subprocess.run
    def boundary(command,**kwargs):
        if command==adapter.real_runtime_command(request['config']['real_binding']):
            calls.append(['runtime-admission'])
            return types.SimpleNamespace(returncode=0,stdout=json.dumps(dict(available=True,module_sha256=request['config']['real_binding']['pytdx_exhq_sha256'])),stderr='')
        expected=[request['config']['real_binding']['pytdx_python'],'-m','scripts.live_acquisition.pytdx_exhq_probe']
        if command!=expected:raise AssertionError('UNEXPECTED_PROCESS:'+repr(command))
        if packet.get('boundary_timeout') is True:raise subprocess.TimeoutExpired('fixed-probe',180)
        assert kwargs['shell'] is False
        assert kwargs['env']['PYTHONPATH']==request['config']['real_binding']['provider_root']
        assert 'HOME' not in kwargs['env']
        from scripts.live_acquisition.pytdx_exhq_probe import collect_payload,MARKER
        payload=json.loads(kwargs['input']);calls.append(['probe',len(payload['codes']),payload['trade_date'],payload['stage_id']])
        result=collect_payload(payload)
        return types.SimpleNamespace(returncode=0,stdout=MARKER+json.dumps(result),stderr='')
    subprocess.run=boundary
    result=adapter._worker('producer',dict(request=request,ledger_run_id=run_id))
    print(json.dumps(dict(envelope=result,calls=calls,evidence_kind='SYNTHETIC_NETWORK_BOUNDARY')))


class RealBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
        self.assertTrue(hasattr(adapter,'real_runtime_command'),'Guarded real default path is missing')
        self.request,self.ledger=real_fixture(self.root)
    def tearDown(self):self.tmp.cleanup()
    def test_default_original_collector_probe_and_fresh_reader_contract(self):
        path=self.root/'request.json';path.write_text(json.dumps(self.request))
        child=subprocess.run([sys.executable,'-I','-B',__file__,'--harness',str(path)],capture_output=True,text=True)
        self.assertEqual(child.returncode,0,child.stderr);result=json.loads(child.stdout);produced=result['envelope'];self.assertEqual(produced['owner_status'],'MATERIALIZED',produced)
        probes=[x for x in result['calls'] if x[0]=='probe'];self.assertEqual([x[1] for x in probes],[64,36]);self.assertEqual(len([x for x in result['calls'] if x[0]=='bars']),100)
        self.assertEqual(produced['execution_kind'],'OWNER_VERIFIED');self.assertFalse(produced['natural_verified'])
        reader=adapter._process('reader',self.request,'real-contract-run');adapter._same_product(produced,reader);self.assertEqual(reader['owner_status'],'READY');self.assertEqual(reader['candidate_count'],100)
        self.assertFalse(list(Path(self.request['config']['state_root']).rglob('*1530*')))
    def test_bound_real_path_full_ledger_with_network_boundary_substitute(self):
        from unittest.mock import patch
        original_run=subprocess.run; observed=[]
        def worker_boundary(command,**kwargs):
            if command[-2:]==['--worker','producer']:
                packet=json.loads(kwargs['input']);path=self.root/'packet.json';path.write_text(json.dumps(packet))
                child=original_run([sys.executable,'-I','-B',__file__,'--harness',str(path)],capture_output=True,text=True)
                if child.returncode:return types.SimpleNamespace(returncode=child.returncode,stdout=child.stdout.encode(),stderr=child.stderr.encode())
                data=json.loads(child.stdout);observed.extend(data['calls'])
                return types.SimpleNamespace(returncode=0,stdout=json.dumps(data['envelope']).encode(),stderr=b'')
            return original_run(command,**kwargs)
        with patch.object(subprocess,'run',worker_boundary):
            result=adapter.run_close_recapture_daily(self.request,str(self.ledger),adapter.bind_close_recapture_owner(self.request['config']))
        self.assertEqual(result['status'],'SUCCEEDED',result)
        saved=result['state']['latest_success'];ref=saved['product_reference']
        self.assertEqual(saved['run_id'],ref['ledger_run_id']);self.assertEqual(ref['execution_kind'],'OWNER_VERIFIED');self.assertFalse(ref['natural_verified']);self.assertNotEqual(ref['producer_pid'],ref['reader_pid'])
        self.assertEqual([x[1] for x in observed if x[0]=='probe'],[64,36])
    def test_real_probe_timeout_preserves_running_ledger_without_retry(self):
        from unittest.mock import patch
        original_run=subprocess.run
        def worker_boundary(command,**kwargs):
            if command[-2:]==['--worker','producer']:
                packet=json.loads(kwargs['input']);packet['boundary_timeout']=True;path=self.root/'timeout-packet.json';path.write_text(json.dumps(packet))
                child=original_run([sys.executable,'-I','-B',__file__,'--harness',str(path)],capture_output=True,text=True)
                return types.SimpleNamespace(returncode=child.returncode,stdout=child.stdout.encode(),stderr=child.stderr.encode())
            return original_run(command,**kwargs)
        with patch.object(subprocess,'run',worker_boundary):
            result=adapter.run_close_recapture_daily(self.request,str(self.ledger),adapter.bind_close_recapture_owner(self.request['config']))
        self.assertEqual(result['status'],'IN_PROGRESS_OR_OUTCOME_UNKNOWN');self.assertEqual(result['state']['attempts'][0]['status'],'RUNNING');self.assertIsNone(result['state']['latest_success'])
        again=adapter.run_close_recapture_daily(self.request,str(self.ledger),adapter.bind_close_recapture_owner(self.request['config']))
        self.assertEqual(again['status'],'IN_PROGRESS_OR_OUTCOME_UNKNOWN');self.assertEqual(len(again['state']['attempts']),1)
    def test_probe_timeout_is_not_downgraded_to_confirmed_failure(self):
        from unittest.mock import patch
        sys.path.insert(0,self.request['config']['real_binding']['provider_root'])
        from scripts.live_acquisition.pytdx_exhq import collect_pytdx_exhq_minute
        runner=adapter._real_process_runner(self.request['config']['real_binding'],self.request['source_trade_date'])
        with patch.object(subprocess,'run',side_effect=subprocess.TimeoutExpired('fixed-probe',180)):
            with self.assertRaises(BaseException) as caught:
                collect_pytdx_exhq_minute(self.request['config']['python'],self.request['source_trade_date'],'STAGE_1545_1555',[f'HK.{i:05d}' for i in range(1,101)],market='HK_CONNECT',process_runner=runner,timeout_seconds=360)
        self.assertNotIsInstance(caught.exception,Exception)
        self.assertIn('M17_REAL_PROBE_OUTCOME_UNKNOWN',str(caught.exception))
    def test_missing_real_binding_is_blocked_before_worker(self):
        self.request['config'].pop('real_binding');result=adapter.run_close_recapture_daily(self.request,str(self.ledger),adapter.bind_close_recapture_owner(self.request['config']))
        self.assertEqual(result['status'],'BLOCKED');self.assertIn('REAL_COLLECTOR_NOT_BOUND',result['state']['attempts'][0]['reason_codes']);self.assertFalse((Path(self.request['config']['state_root'])/'workbench_research').exists())
    def test_wrong_interpreter_fingerprint_is_blocked(self):
        self.request['config']['real_binding']['pytdx_python_sha256']='0'*64
        receipt=adapter.run_close_recapture_owner(self.request,'bad-runtime');self.assertEqual(receipt['status'],'BLOCKED');self.assertIn('M17_REAL_INTERPRETER_SHA_MISMATCH',receipt['reason_codes'])
    def test_wrong_provider_binding_is_blocked(self):
        self.request['config']['real_binding']['provider_root']=str(self.root)
        receipt=adapter.run_close_recapture_owner(self.request,'bad-provider');self.assertEqual(receipt['status'],'BLOCKED');self.assertIn('M17_REAL_PROVIDER_BINDING',receipt['reason_codes'])
    def test_real_request_rejects_simulated_clock_data(self):
        self.request['simulation']={'clocks':['2000-01-01T00:00:00+00:00']}
        with self.assertRaises(ValueError):adapter.request_identity(self.request,adapter.bind_close_recapture_owner(self.request['config']))
    def test_mismatched_root_mode_is_blocked(self):
        (Path(self.request['config']['state_root'])/'.v5-m17-close-root').write_bytes(b'v5.m17.simulated-close.v1\n')
        receipt=adapter.run_close_recapture_owner(self.request,'wrong-marker');self.assertEqual(receipt['status'],'BLOCKED');self.assertIn('M17_REAL_ROOT_MARKER_REQUIRED',receipt['reason_codes'])
    def test_existing_runtime_without_pytdx_blocks_without_network(self):
        # This runner has no installed PyTDX. Never install it or try a live probe.
        import importlib.util
        if importlib.util.find_spec('pytdx') is not None:self.skipTest('Existing environment contains PyTDX; boundary test handles admission deterministically')
        result=adapter._process('producer',self.request,'missing-pytdx');self.assertEqual(result['owner_status'],'INPUT_MISSING');self.assertEqual(result['reason'],'M17_PYTDX_RUNTIME_NOT_BOUND');self.assertFalse((Path(self.request['config']['state_root'])/'workbench_research').exists())

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--harness':harness(sys.argv[2])
    else:unittest.main(verbosity=2)

"""All owner evidence in these tests is SYNTHETIC; sockets blocked in owner child."""
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

REPO=Path(__file__).resolve().parents[2]
ROUTE='/api/v5/source-bundle/video-fupan'
DATE='20261011'

class M12IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.m12_readonly'),'M12 saved adapter missing')
        from v5_shadow import m12_readonly as m
        self.m=m
        tmp=tempfile.TemporaryDirectory(prefix='v5-m12-integration-');self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name).resolve();self.saved=self.root/'v5-saved';self.saved.mkdir()
        (self.saved/'.v5-m12-root').write_text('v5.m12-private.v1\n')
        api=self.root/'api';api.mkdir();(api/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
        self.config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='m12-synthetic',data_root=str(api),routes=[ROUTE])

    def fixture(self,failed=False):
        script='''import sys,json,socket
from pathlib import Path
sys.path[:0]=[sys.argv[1],sys.argv[1]+'/tests/m12']
socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network forbidden'))
socket.create_connection=socket.socket.connect
from test_video_fupan_default_chain import SimulatedOwner
from V5.src.v5_shadow.video_fupan_daily import run_video_fupan
owner=SimulatedOwner(asr_status='ASR_FAILED' if sys.argv[3]=='failed' else 'ASR_REVIEW_REQUIRED')
r=run_video_fupan('20261011',private_root=Path(sys.argv[2]),tools=owner.tools(),source_identity='synthetic',tool_identity='synthetic',config_identity='synthetic',allow_network=True)
print(json.dumps({'run_id':r['run_id']}))
'''
        result=subprocess.run([sys.executable,'-B','-c',script,str(REPO),str(self.saved),'failed' if failed else 'ok'],cwd=REPO,capture_output=True,text=True,check=True)
        rid=json.loads(result.stdout)['run_id']
        digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        self.binding=dict(private_root=str(self.saved),trade_date=DATE,run_id=rid,data_kind='SYNTHETIC',python_executable=sys.executable,
            manifest_sha256=digest(self.saved/'video_fupan/runs'/DATE/rid/'manifest.json'),owner_receipt_sha256=digest(self.saved/'review'/DATE/'runs'/rid/'receipt.json'))
        self.config[self.m.BINDING]=self.binding
        return rid

    def request(self,path=ROUTE,method='GET'):
        from v5_shadow.module_api import create_module_server
        server=create_module_server(self.config);thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            client=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=30)
            client.request(method,path);r=client.getresponse();value=json.loads(r.read());client.close();return r.status,value,dict(r.getheaders())
        finally:server.shutdown();thread.join();server.server_close()

    def snapshot(self):
        return {str(p.relative_to(self.root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}

    def test_missing_binding_is_waiting_not_empty_success(self):
        before=self.snapshot();status,v,_=self.request()
        self.assertEqual(status,200);self.assertEqual(v['status'],'WAITING');self.assertIn('M12_SAVED_REFERENCE_NOT_CONFIGURED',v['reason_codes']);self.assertNotIn('transcript',v);self.assertEqual(before,self.snapshot())

    def test_original_saved_content_is_read_without_producer_import_or_writes(self):
        rid=self.fixture();before=self.snapshot();status,v,h=self.request(ROUTE+'?trade_date='+DATE)
        self.assertEqual(status,200,v);self.assertEqual(v['status'],'SAVED_ASR_REVIEW_REQUIRED');self.assertEqual(v['reference']['run_id'],rid)
        self.assertEqual(v['transcript']['text'],'SIMULATED');self.assertIn('0,1,SIMULATED',v['segments']['text']);self.assertEqual(v['data_kind'],'SYNTHETIC')
        self.assertEqual(v['video']['gap_status'],'VIDEO_GAP_AUDIT_EMPTY');self.assertEqual(v['video']['asr_status'],'ASR_REVIEW_REQUIRED')
        self.assertFalse(v['natural_verified']);self.assertFalse(v['production_allowed']);self.assertEqual(h['Cache-Control'],'no-store');self.assertEqual(before,self.snapshot())
        self.assertFalse(any(n.endswith('review_core.producer') for n in sys.modules));self.assertNotIn('v5_shadow.video_fupan_reader',sys.modules);self.assertNotIn(str(self.root),json.dumps(v))

    def test_wrong_selected_date_is_waiting_and_never_returns_another_days_transcript(self):
        self.fixture();status,v,_=self.request(ROUTE+'?trade_date=20261012')
        self.assertEqual(status,200);self.assertEqual(v['status'],'WAITING');self.assertNotIn('transcript',v)

    def test_failed_owner_evidence_is_not_a_qualified_result(self):
        self.fixture(True);status,v,_=self.request()
        self.assertEqual(status,200,v);self.assertEqual(v['status'],'WAITING');self.assertIn('M12_SAVED_RUN_NOT_QUALIFIED',v['reason_codes']);self.assertNotIn('transcript',v)

    def test_exact_digest_tampering_and_missing_artifact_fail_closed(self):
        self.fixture();self.binding['manifest_sha256']='0'*64
        self.assertEqual(self.request()[0],409)
        self.fixture();owner=json.loads((self.saved/'video_fupan/runs'/DATE/self.binding['run_id']/'manifest.json').read_text())['owner_manifest']
        path=self.saved/next(r['path'] for r in owner['artifact_refs'] if r['kind']=='transcript');path.write_text('CORRUPTED')
        status,v,_=self.request();self.assertEqual(status,409);self.assertNotIn('transcript',v)

    def test_symlink_and_unexpected_selectors_rejected(self):
        self.fixture();link=self.root/'alias';link.symlink_to(self.saved,target_is_directory=True);self.binding['private_root']=str(link)
        self.assertEqual(self.request()[0],409)
        self.binding['private_root']=str(self.saved)
        self.assertEqual(self.request(ROUTE+'?run_id=latest')[0],409);self.assertEqual(self.request(method='POST')[0],405)

    def test_runtime_pin_and_child_timeout_rejected(self):
        self.fixture()
        with patch.object(self.m,'RUNTIME_SHA256','0'*64):self.assertEqual(self.request()[0],409)
        with patch.object(self.m.subprocess,'run',side_effect=subprocess.TimeoutExpired('reader',30)):self.assertEqual(self.request()[0],409)
        self.assertEqual(self.request()[0],200)

    def test_daily_symlink_output_is_rejected_before_any_owner_writes(self):
        outside=self.root/'outside';outside.mkdir();(self.saved/'review').symlink_to(outside,target_is_directory=True)
        script="""import sys,json,socket
from pathlib import Path
sys.path[:0]=[sys.argv[1],sys.argv[1]+'/V5/src',sys.argv[1]+'/tests/m12']
socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network forbidden'))
socket.create_connection=socket.socket.connect
from test_video_fupan_default_chain import SimulatedOwner
from v5_shadow.m12_daily_worker import run
run(dict(private_root=sys.argv[2],trade_date='20261011',source_identity='synthetic',tool_identity='synthetic',config_identity='synthetic',data_kind='SYNTHETIC'),tools=SimulatedOwner().tools())
"""
        result=subprocess.run([sys.executable,'-B','-c',script,str(REPO),str(self.saved)],cwd=REPO,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(list(outside.rglob('*')),[],'original owner must not write through a symlink before rejection')

    def test_legacy_envelope_receipt_race_is_rejected(self):
        rid=self.fixture();manifest=self.saved/'video_fupan/runs'/DATE/rid/'manifest.json'
        envelope=json.loads(manifest.read_text());del envelope['owner_receipt_sha256'];manifest.write_text(json.dumps(envelope))
        self.binding['manifest_sha256']=hashlib.sha256(manifest.read_bytes()).hexdigest()
        path=manifest.with_name('receipt.json');receipt=json.loads(path.read_text());receipt['manifest_sha256']=self.binding['manifest_sha256'];path.write_text(json.dumps(receipt))
        script="""import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/V5/src')
from v5_shadow import m12_readonly_worker as worker
binding=json.load(sys.stdin);actual=worker.raw;changed=False
receipt=Path(binding['private_root'])/'review'/binding['trade_date']/'runs'/binding['run_id']/'receipt.json'
def race(path,*args):
 global changed
 value=actual(path,*args)
 if Path(path)==receipt and not changed:
  changed=True;obj=json.loads(value);obj['review_probe']='changed';receipt.write_text(json.dumps(obj))
 return value
worker.raw=race
try:worker.project(binding);print('INCORRECTLY_ACCEPTED')
except ValueError:print('REJECTED')
"""
        result=subprocess.run([sys.executable,'-I','-B','-c',script,str(REPO)],input=json.dumps(self.binding),capture_output=True,text=True,check=True)
        self.assertEqual(result.stdout.strip(),'REJECTED')

    def test_daily_default_never_runs_provider(self):
        from v5_shadow.m12_daily import run_daily
        with patch('subprocess.run',side_effect=AssertionError('must not launch provider')):
            v=run_daily({})
        self.assertEqual(v['status'],'WAITING');self.assertFalse(v['natural_verified'])

    def test_daily_child_calls_original_chain_from_unrelated_parent_cwd(self):
        from v5_shadow.m12_daily import run_daily
        fixture=self.root/'owner_fixture.py'
        fixture.write_text('''import sys,json,socket
from pathlib import Path
sys.path[:0]=[sys.argv[1],sys.argv[1]+'/V5/src',sys.argv[1]+'/tests/m12']
socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network forbidden'))
socket.create_connection=socket.socket.connect
from test_video_fupan_default_chain import SimulatedOwner
from v5_shadow.m12_daily_worker import run
print(json.dumps(run(json.load(sys.stdin),tools=SimulatedOwner().tools())))
''')
        actual=subprocess.run
        def runner(command,**kwargs):
            self.assertEqual(kwargs['cwd'],str(REPO));self.assertIn('-I',command);self.assertIn('-B',command)
            return actual([sys.executable,'-I','-B',str(fixture),str(REPO)],**kwargs)
        request=dict(execution_authorized=True,private_root=str(self.saved),trade_date=DATE,source_identity='synthetic',tool_identity='synthetic',config_identity='synthetic',data_kind='SYNTHETIC',python_executable=sys.executable)
        cwd=Path.cwd()
        try:
            os.chdir(self.root)
            with patch('v5_shadow.m12_daily.subprocess.run',side_effect=runner):
                first=run_daily(request);second=run_daily(request)
            self.assertEqual(Path.cwd(),self.root)
        finally:os.chdir(cwd)
        self.assertEqual(Path.cwd(),cwd);self.assertEqual(first['status'],'SAVED_ASR_REVIEW_REQUIRED');self.assertEqual(first['reference']['run_id'],second['reference']['run_id']);self.assertEqual(first['video']['asr_status'],'ASR_REVIEW_REQUIRED')

if __name__=='__main__':unittest.main()

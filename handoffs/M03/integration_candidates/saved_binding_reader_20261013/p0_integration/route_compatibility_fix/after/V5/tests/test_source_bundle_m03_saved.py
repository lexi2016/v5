"""Exact M03 saved-read dispatch and one-row publication; all market data synthetic."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from v5_shadow import source_bundle
from v5_shadow.module_api import _config, read_response
from v5_shadow.source_bundle import STATUS_ROUTE, publish_source_result
import test_source_bundle_publication_routes as route_fixture

MARKET_RUNTIME = Path(os.environ['M03_SAVED_TEST_RUNTIME'])
FIXTURE = r'''
import hashlib,json,sys
from pathlib import Path
base=Path(sys.argv[1]);root=Path(sys.argv[2])
sys.path[:0]=[str(base/'V5/src'),str(base/'V5/tests')]
from v5_shadow import us_source_daily as d
from test_us_market_capture import offline_chain_runner
req=d.USSourceRequest(trade_date='20261009',session='20261009',capture_phase='POST_CLOSE',
    cutoff='2026-10-09T20:20:00Z',source_root=root/'source',snapshot_root=root/'snapshot',
    binding_root=root/'binding',owner_root=base/'collector_owner',v5_src=base/'V5/src',
    capture_root=root/'capture',allow_network_capture=True,market_snapshot_only=True)
binding=d.run_us_source(req,runner=offline_chain_runner(root/'synthetic-provider-calls.jsonl'))
assert binding['status']=='VALIDATED_SOURCE_BINDING'
request=root/'original-request.json';request.write_bytes(d._json_bytes(d._request_dict(req)))
raw=(req.binding_root/d._binding_name(req)).read_bytes()
print(json.dumps(dict(action='read',request_file=str(request),
    expected_request_sha256=d._binding_name(req)[:-5],expected_binding_sha256=hashlib.sha256(raw).hexdigest(),
    expected_source_sha256=binding['source_sha256'])))
'''


class M03SavedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=route_fixture.SourceBundlePublicationRouteTests()
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root; self.config=self.fixture.config
        generation,self.siblings=self.fixture.seed_siblings()
        self.previous=copy.deepcopy(self.fixture.result)
        for i in (0,1,3):
            self.previous['modules'][i].update(status='RETAINED_SYNTHETIC_STATUS',owner_result={'sequence':i})
        self.generation=publish_source_result(self.previous,self.config,expected_generation=generation)['generation_sha256']
        tmp=tempfile.TemporaryDirectory(prefix='m03-saved-p0-synthetic-');self.addCleanup(tmp.cleanup)
        self.data=Path(tmp.name)
        run=subprocess.run([sys.executable,'-I','-B','-c',FIXTURE,str(MARKET_RUNTIME),str(self.data)],capture_output=True,text=True,timeout=120)
        self.assertEqual(run.returncode,0,run.stderr)
        self.request=json.loads(run.stdout)

    def publish(self,**kwargs):
        entry=getattr(source_bundle,'publish_m03_saved_binding',None)
        self.assertTrue(callable(entry),'M03_SAVED_PUBLICATION_ENTRY_MISSING')
        return entry(self.request,self.config,expected_generation=kwargs.get('expected_generation',self.generation),data_kind=kwargs.get('data_kind','SYNTHETIC'))

    def data_bytes(self):
        return {str(p.relative_to(self.data)):p.read_bytes() for p in self.data.rglob('*') if p.is_file()}

    def test_real_saved_reader_updates_only_m03_and_retains_all_other_cards_routes(self):
        before=self.data_bytes();old=self.fixture.tree();config_before=copy.deepcopy(self.config)
        self.assertEqual(len(self.config['routes']),15)
        out=self.publish();result=out['result']
        self.assertEqual(self.data_bytes(),before)
        for i in (0,1,3):self.assertEqual(result['modules'][i],self.previous['modules'][i])
        row=result['modules'][2];self.assertEqual(row['status'],'VALIDATED_SOURCE_BINDING')
        view=row['owner_result'];self.assertTrue(view['readback_verified'])
        self.assertEqual(view['market_snapshot']['quote_count'],33)
        self.assertEqual(view['market_snapshot']['theme_count'],24)
        self.assertEqual(view['request_sha256'],self.request['expected_request_sha256'])
        self.assertNotIn(str(self.data),json.dumps(result))
        self.assertNotIn(str(MARKET_RUNTIME),json.dumps(result))
        current=json.loads((self.root/'active.json').read_bytes())['generation_sha256']
        refs=json.loads((self.root/'generations'/(current+'.json')).read_bytes())['records']
        self.assertEqual(set(refs),set(self.siblings)|{route_fixture.response_key('source_bundle',STATUS_ROUTE,{})})
        self.assertEqual(self.config,config_before)
        for key,digest in self.siblings.items():self.assertEqual(refs[key],digest)
        for path,raw in old.items():
            if path!='active.json':self.assertEqual((self.root/path).read_bytes(),raw)
        checked,fd=_config(self.config)
        try:record,_=read_response(checked,fd,STATUS_ROUTE,{})
        finally:os.close(fd)
        self.assertEqual(record['payload'],result)

    def test_dispatch_read_preserves_original_true_capture_identity(self):
        before=self.data_bytes();result=source_bundle._call('m03',self.request)
        self.assertEqual(result['status'],'VALIDATED_SOURCE_BINDING')
        self.assertEqual(result['request_sha256'],self.request['expected_request_sha256'])
        self.assertEqual(self.data_bytes(),before)
        self.assertTrue(json.loads(Path(self.request['request_file']).read_bytes())['allow_network_capture'])

    def test_bad_binding_cas_and_data_kind_never_publish(self):
        before=self.fixture.tree(); self.request['expected_binding_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'M03_SAVED_BINDING_SHA_MISMATCH'):self.publish()
        self.assertEqual(self.fixture.tree(),before)
        with patch.object(source_bundle,'_call',side_effect=AssertionError('reader must not run')):
            with self.assertRaisesRegex(ValueError,'GENERATION_CONFLICT'):self.publish(expected_generation='0'*64)
            with self.assertRaisesRegex(ValueError,'M03_SAVED_DATA_KIND_MISMATCH'):self.publish(data_kind='RECORDED_INPUT_REPLAY')
        self.assertEqual(self.fixture.tree(),before)

    def test_unknown_action_and_extra_capture_fields_do_not_fall_back(self):
        for changes in ({'action':'read-or-capture'},{'allow_network_capture':True}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):source_bundle._call('m03',dict(self.request,**changes))
        before=self.fixture.tree();self.request['action']='create'
        with self.assertRaisesRegex(ValueError,'M03_SAVED_READ_REQUIRED'):self.publish()
        self.assertEqual(self.fixture.tree(),before)

    def test_racing_m02_update_is_preserved_by_cas_rejection(self):
        original=source_bundle._call;race={}
        def intervening(owner,request):
            changed=copy.deepcopy(self.previous);changed['modules'][1]['owner_result']['sequence']='newer'
            race['generation']=publish_source_result(changed,self.config,expected_generation=self.generation)['generation_sha256']
            race['tree']=self.fixture.tree()
            return original(owner,request)
        with patch.object(source_bundle,'_call',side_effect=intervening):
            with self.assertRaisesRegex(ValueError,'GENERATION_CONFLICT'):self.publish()
        self.assertEqual(self.fixture.tree(),race['tree'])

    def test_resealed_unknown_status_or_unsafe_flag_cannot_publish(self):
        before=self.fixture.tree();valid=source_bundle._call('m03',self.request)
        for change in ({'status':'READY'},{'production_allowed':True},{'readback_verified':False}):
            with self.subTest(change=change):
                with patch.object(source_bundle,'_call',return_value=dict(valid,**change)):
                    with self.assertRaisesRegex(ValueError,'M03_SAVED_RESULT_CONTRACT'):self.publish()
        self.assertEqual(self.fixture.tree(),before)

    def test_unknown_route_in_current_full_config_never_publishes(self):
        before=self.fixture.tree();data_before=self.data_bytes()
        self.config['routes'].append('/api/v5/source-bundle/not-registered')
        config_before=copy.deepcopy(self.config)
        with self.assertRaisesRegex(ValueError,'^SOURCE_MODULE_ID_REQUIRED$'):
            self.publish()
        self.assertEqual(self.fixture.tree(),before)
        self.assertEqual(self.data_bytes(),data_before)
        self.assertEqual(self.config,config_before)

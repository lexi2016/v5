"""SYNTHETIC persistence tests, never real research/PIT/owner qualification."""
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROUTE='/api/v5/source-bundle/intraday-research'
DATE='20261012'

class M11IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.m11_readonly'),'M11 saved adapter missing')
        from v5_shadow import m11_readonly
        self.m=m11_readonly
        temp=tempfile.TemporaryDirectory(prefix='v5-m11-integration-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve();self.archive=self.root/'archive';self.archive.mkdir()
        (self.archive/'.m11-private-root.json').write_text('{"module":"M11","private":true,"schema":"v5.private_root.v1"}')
        api=self.root/'api';api.mkdir();(api/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
        self.config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='m11-synthetic',data_root=str(api),routes=[ROUTE])

    def fixture(self,operation='capture',unsafe=False):
        from v5_shadow.m11.intraday_capsule import M11Slot,IntradayCapsuleStore
        from v5_shadow.m11.owner_sources import BUILD_MANIFEST_SHA,implementation_sha256
        slot=M11Slot('2026-10-12','09:25' if operation=='capture' else '15:00','2026-10-12T09:30:00+08:00' if operation=='capture' else '2026-10-12T15:05:00+08:00',
            'capture' if operation=='capture' else 'explicit-daily-generation','synthetic-run',input_sha='a'*64,config_sha='b'*64,code_sha=implementation_sha256(),source_sha=BUILD_MANIFEST_SHA)
        view=dict(status='READY',trade_date=DATE,target_date='2026-10-12',cannot_confirm=['GLOBAL_PIT_NOT_PROVEN'],source_path='/private/should-not-leak',
            generation=dict(status='V4_DECLARED_PROVENANCE',provenance_status='DECLARED_ONLY',independently_verified=False),
            market_facts=dict(breadth=dict(advancers=42)),production_allowed=unsafe,orders_sent=False,buy_gate_updated=False)
        payload=dict(status='READY',owner={('intraday_research' if operation=='capture' else 'research_review'):view},
            pit_status='CANNOT_CONFIRM',natural_admission='CANNOT_CONFIRM',source_times_validated=True)
        store=IntradayCapsuleStore(self.archive/('intraday' if operation=='capture' else 'daily'))
        store.write_success(slot,payload,slot.source_sha)
        self.commit=store._artifact_dir(slot)/'commit.json'
        self.binding=dict(archive_root=str(self.archive),identity=slot.__dict__,operation=operation,
            commit_sha256=hashlib.sha256(self.commit.read_bytes()).hexdigest(),data_kind='SYNTHETIC',python_executable=sys.executable)
        self.config[self.m.BINDING]=self.binding
        return slot

    def request(self,path=ROUTE,method='GET'):
        from v5_shadow.module_api import create_module_server
        server=create_module_server(self.config);thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            client=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=30)
            client.request(method,path);r=client.getresponse();value=json.loads(r.read());client.close();return r.status,value,dict(r.getheaders())
        finally:server.shutdown();thread.join();server.server_close()

    def snapshot(self):
        return {str(p.relative_to(self.root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}

    def test_unbound_route_is_waiting_without_writes(self):
        before=self.snapshot();status,value,_=self.request()
        self.assertEqual(status,200);self.assertEqual(value['status'],'WAITING')
        self.assertIn('M11_SAVED_REFERENCE_NOT_CONFIGURED',value['reason_codes']);self.assertNotIn('research',value)
        self.assertEqual(len(value['slots']),6);self.assertEqual(before,self.snapshot())

    def test_real_capsule_reader_preserves_business_and_declared_evidence(self):
        self.fixture();before=self.snapshot();status,value,headers=self.request(ROUTE+'?trade_date='+DATE)
        self.assertEqual(status,200,value);self.assertEqual(value['status'],'SAVED_RESEARCH_REVIEW_REQUIRED')
        self.assertEqual(value['research']['intraday_research']['market_facts']['breadth']['advancers'],42)
        self.assertEqual(value['research']['intraday_research']['generation']['provenance_status'],'DECLARED_ONLY')
        self.assertEqual(value['evidence_status'],'VERIFIED_PERSISTENCE_ONLY');self.assertFalse(value['natural_verified'])
        self.assertEqual(sum(s['status']=='SAVED' for s in value['slots']),1)
        self.assertNotIn('/private',json.dumps(value));self.assertNotIn('source_path',json.dumps(value))
        self.assertEqual(headers['Cache-Control'],'no-store');self.assertEqual(before,self.snapshot())
        self.assertNotIn('v5_shadow.m11.owner_worker',sys.modules)

    def test_daily_review_never_claims_six_intraday_slots(self):
        self.fixture('generate');status,value,_=self.request()
        self.assertEqual(status,200,value);self.assertIn('research_review',value['research'])
        self.assertEqual(sum(s['status']=='SAVED' for s in value['slots']),0)
        self.assertIn('DECLARED_PROVENANCE_NOT_INDEPENDENTLY_VERIFIED',value['reason_codes'])

    def test_plain_legacy_review_without_commit_is_waiting(self):
        self.fixture('generate');self.commit.rename(self.commit.with_name('legacy-review.json'))
        status,value,_=self.request();self.assertEqual(status,200,value);self.assertEqual(value['status'],'WAITING')
        self.assertIn('M11_COMMITTED_CAPSULE_MISSING',value['reason_codes']);self.assertNotIn('research',value)

    def test_wrong_selected_date_does_not_return_another_days_content(self):
        self.fixture();status,value,_=self.request(ROUTE+'?trade_date=20261013')
        self.assertEqual(status,200);self.assertEqual(value['status'],'WAITING');self.assertNotIn('research',value)

    def test_digest_tampering_refuses_even_valid_inner_envelope(self):
        self.fixture();self.binding['commit_sha256']='0'*64
        self.assertEqual(self.request()[0],409)

    def test_inner_envelope_tampering_refuses_even_repinned_file(self):
        self.fixture();obj=json.loads(self.commit.read_text());obj['payload']['status']='CORRUPTED';self.commit.write_text(json.dumps(obj))
        self.binding['commit_sha256']=hashlib.sha256(self.commit.read_bytes()).hexdigest()
        self.assertEqual(self.request()[0],409)

    def test_original_reader_output_must_match_the_exact_pinned_bytes(self):
        self.fixture()
        from v5_shadow.m11_readonly_worker import project
        from v5_shadow.m11.intraday_capsule import IntradayCapsuleStore
        actual=IntradayCapsuleStore.read_verified
        def different(store,slot):
            value=actual(store,slot);value['owner']['intraday_research']['market_facts']['breadth']['advancers']=999
            return value
        with patch.object(IntradayCapsuleStore,'read_verified',different):
            with self.assertRaisesRegex(ValueError,'PINNED_PAYLOAD'):project(self.binding)

    def test_original_verifier_receives_bounded_pinned_bytes_not_an_unbounded_reread(self):
        self.fixture()
        from v5_shadow.m11_readonly_worker import project
        from v5_shadow.m11.owner_sources import safe_root_class
        # raw() performs descriptor-safe bounded reads. The donor verifier must
        # consume that immutable buffer, rather than reopening a changed file.
        with patch.object(safe_root_class(),'read_bytes',side_effect=AssertionError('unbounded donor reread')):
            self.assertEqual(project(self.binding)['status'],'SAVED_RESEARCH_REVIEW_REQUIRED')

    def test_symlink_and_unexpected_query_or_post_rejected(self):
        self.fixture();link=self.root/'alias';link.symlink_to(self.archive,target_is_directory=True);self.binding['archive_root']=str(link)
        self.assertEqual(self.request()[0],409);self.binding['archive_root']=str(self.archive)
        self.assertEqual(self.request(ROUTE+'?run_id=latest')[0],409);self.assertEqual(self.request(method='POST')[0],405)

    def test_unsafe_claim_in_pinned_saved_payload_rejected(self):
        self.fixture(unsafe=True);self.assertEqual(self.request()[0],409)

    def test_projection_removes_nested_credential_key_variants(self):
        from v5_shadow.m11_readonly_worker import public_tree
        self.assertEqual(public_tree({'business':{'API_Key':'dummy','access-key':'dummy','Authorization':'dummy','cookie':'dummy','session_id':'dummy','score':1}}),{'business':{'score':1}})

    def test_runtime_pin_and_child_timeout_refused(self):
        self.fixture()
        with patch.object(self.m,'RUNTIME_SHA256','0'*64):self.assertEqual(self.request()[0],409)
        with patch.object(self.m.subprocess,'run',side_effect=subprocess.TimeoutExpired('reader',30)):self.assertEqual(self.request()[0],409)

    def test_original_service_is_reachable_and_not_a_placeholder(self):
        from v5_shadow.m11.service import default_owner,default_readback,Service
        from v5_shadow.research_review_daily import capture,generate,read_owner_day
        from v5_shadow.main_registry import registry_by_id
        self.assertTrue(all(callable(f) for f in [default_owner,default_readback,Service,capture,generate,read_owner_day]))
        entry=registry_by_id()['M11_INTRADAY_RESEARCH']
        self.assertEqual(entry.owner_entry,'research_review_daily.generate')
        self.assertEqual(entry.status,'CALLABLE_CANDIDATE_REQUIRES_INPUT')

if __name__=='__main__':unittest.main()

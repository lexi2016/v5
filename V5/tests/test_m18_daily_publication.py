"""Synthetic saved manager -> bounded bundle -> atomic descriptors -> HTTP.

No manager/owner execution, real market inputs, Mac changes or deployment.
"""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v5_shadow import m18_offline_v2 as m
from v5_shadow import m18_v2_publication_bridge as bridge
from v5_shadow import module_api as api
from v5_shadow.digests import canonical_bytes, sha256_json
import test_m18_v2_disk_pages as disk


class DailyPublicationTests(unittest.TestCase):
    setUp = disk.DiskPagesTests.setUp
    serve = disk.DiskPagesTests.serve
    get = disk.DiskPagesTests.get
    snapshot = disk.DiskPagesTests.snapshot

    def fixture(self, run='a' * 32):
        target='20261013'; source='c'*64
        payload=dict(target_trade_date=target,input_identity=source,RESEARCH_ONLY=True,
            production_allowed=False,buy_gate_updated=False,orders_sent=False,
            gaps=['SYNTHETIC_BUSINESS_BLOCKED'],stocks=[{'code':'SYNTHETIC','status':'PARTIAL'}])
        saved=dict(run_id=run,target_trade_date=target,input_identity=source,workspace=copy.deepcopy(payload))
        saved['sha256']=sha256_json(saved)
        saved_root=self.root/'manager'; folder=saved_root/'workspace_plans'/target
        folder.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(saved,indent=2).encode();(folder/(run+'.json')).write_bytes(raw)
        product=dict(consumed=True,run_id=run,sha256=saved['sha256'],status='PARTIAL')
        attempt=dict(run_id=run,state='PARTIAL')
        payload.update(plan_product=product,workspace_plan_attempt=attempt)
        request=dict(target_date=target,action='read',view='auto',selection_date=None,
            announcement_date=None,manager_output_root=str(saved_root),now='2026-10-13T00:50:00Z')
        result=dict(schema_version='v5.manager_plan.v1',payload=payload,
            readback=dict(run_id=run,plan_sha256=saved['sha256'],input_identity=source,
                attempt=attempt,store_relative='.'),request_sha256=sha256_json(request),
            local_result_transport={'not_part_of_saved_response':True})
        return request,result,raw

    def enable(self):
        self.config['m18_v2_daily_publication']=True
        self.config['routes'] = list(dict.fromkeys(self.config['routes'] + [bridge.ROUTE+'/overview',bridge.ROUTE+'/sections']))

    def publish(self, request, result, expected=None):
        return bridge.publish_daily_manager_result(request=request,result=result,config=self.config,
            expected_generation=self.generation if expected is None else expected,
            expected_run_id=result['payload']['plan_product']['run_id'],
            expected_plan_sha256=result['payload']['plan_product']['sha256'])

    def record(self, query):
        checked,root=api._config(self.config)
        try:return api.read_response(checked,root,bridge.ROUTE,query)[0]
        finally:os.close(root)

    def test_empty_query_without_opt_in_reads_exact_fixed_descriptor(self):
        record=self.record({})
        self.assertEqual(record['payload'],self.descriptor)
        self.assertEqual(record['payload']['target_date'],'20261012')

    def test_daily_publish_is_opt_in(self):
        request,result,_=self.fixture()
        with self.assertRaisesRegex(ValueError,'M18_DAILY_PUBLICATION_DISABLED'):
            self.publish(request,result)
        self.assertEqual(self.record({'run_id':disk.RUN})['payload'],self.descriptor)

    def test_two_descriptors_atomic_real_bundle_same_run_and_read_only_http(self):
        self.enable();request,result,saved_raw=self.fixture()
        published=self.publish(request,result)
        current=self.record({});explicit=self.record({'run_id':'a'*32})
        self.assertEqual(current['payload'],explicit['payload'])
        desc=current['payload'];ident=desc['identity']
        self.assertEqual(current['source_input_sha256'],sha256_json(request))
        self.assertEqual(set(ident),m.v1.IDENTITY_KEYS)
        self.assertEqual(ident['run_id'],'a'*32)
        self.assertEqual(ident['raw_sha256'],m.sha(saved_raw))
        self.assertEqual(ident['response_sha256'],m.v1.streamed_sha({k:v for k,v in result.items() if k!='local_result_transport'}))
        self.assertNotEqual(published['generation_sha256'],desc['generation_id'])
        self.assertEqual(self.record({'run_id':disk.RUN})['payload'],self.descriptor)
        base=self.serve();before=self.snapshot()
        with patch.object(bridge,'publish_daily_manager_result',side_effect=AssertionError('GET writes')):
            status,overview,_,_=self.get(base,bridge.ROUTE+'/overview?run_id='+ident['run_id']+'&generation_id='+desc['generation_id'])
            self.assertEqual(status,200);self.assertEqual(overview['identity'],ident)
            status,page,_,_=self.get(base,bridge.ROUTE+'/sections?run_id='+ident['run_id']+'&generation_id='+desc['generation_id']+'&section=stocks')
            self.assertEqual(status,200);self.assertEqual(page['entries'][0]['value']['status'],'PARTIAL')
            self.assertEqual(self.get(base,bridge.ROUTE+'/pages?run_id='+disk.RUN+'&page=0')[0],200)
        self.assertEqual(self.snapshot(),before)

    def test_cas_failure_keeps_both_old_descriptors(self):
        self.enable();request,result,_=self.fixture();self.publish(request,result)
        before=(self.publication/'active.json').read_bytes();current=self.record({})
        request2,result2,_=self.fixture('b'*32)
        with self.assertRaisesRegex(ValueError,'GENERATION_CONFLICT'):
            self.publish(request2,result2)
        self.assertEqual((self.publication/'active.json').read_bytes(),before)
        self.assertEqual(self.record({}),current)
        with self.assertRaises(FileNotFoundError):self.record({'run_id':'b'*32})
        # Retry only publication against a freshly observed token, no owner call.
        token=json.loads(before)['generation_sha256']
        retried=self.publish(request2,result2,expected=token)
        self.assertNotEqual(retried['generation_sha256'],token)
        self.assertEqual(self.record({})['payload']['run_id'],'b'*32)
        self.assertEqual(self.record({'run_id':'a'*32})['payload'],current['payload'])

    def test_wrong_saved_sha_attempt_or_source_cannot_publish(self):
        self.enable();request,result,_=self.fixture()
        before=(self.publication/'active.json').read_bytes()
        for change in ('sha','attempt','source'):
            bad=copy.deepcopy(result)
            if change=='sha':bad['payload']['plan_product']['sha256']='e'*64
            elif change=='attempt':bad['payload']['workspace_plan_attempt']['run_id']='b'*32
            else:bad['request_sha256']='e'*64
            with self.subTest(change=change),self.assertRaises(ValueError):self.publish(request,bad)
            self.assertEqual((self.publication/'active.json').read_bytes(),before)

    def test_dynamic_bundle_requires_opt_in_and_rejects_symlinks(self):
        self.enable();request,result,_=self.fixture();self.publish(request,result)
        desc=self.record({})['payload'];self.config.pop('m18_v2_daily_publication')
        checked,root=api._config(self.config)
        try:
            with self.assertRaises(ValueError):api._m18_page_response(checked,root,{'run_id':'a'*32,'page':'0'})
        finally:os.close(root)
        self.enable(); bundle=self.publication/'m18-v2-bundles'/desc['generation_id']
        outside=self.root/'moved-bundle';bundle.rename(outside);bundle.symlink_to(outside,target_is_directory=True)
        base=self.serve()
        self.assertEqual(self.get(base,bridge.ROUTE+'/pages?run_id='+'a'*32+'&page=0')[0],409)

    def test_bad_current_descriptor_never_falls_back_to_old_success(self):
        self.enable();request,result,_=self.fixture();self.publish(request,result)
        desc=self.record({})['payload'];bundle=self.publication/'m18-v2-bundles'/desc['generation_id']
        (bundle/'manifest.json').write_bytes(b'{}')
        base=self.serve()
        self.assertEqual(self.get(base,bridge.ROUTE+'/pages?run_id='+'a'*32+'&page=0')[0],409)
        self.assertEqual(self.get(base,bridge.ROUTE+'/pages?run_id='+disk.RUN+'&page=0')[0],200)

    def test_daily_adapter_uses_verified_page_without_another_owner_refresh(self):
        from datetime import datetime, timezone
        from daily_ledger_fixture import make_ledger_fixture
        from v5_shadow.daily_owner_adapters import run_manager_daily
        self.enable();request,page,_=self.fixture()
        request_refresh=dict(request,action='refresh')
        refreshed=copy.deepcopy(page)
        refreshed['readback']['status']='MATCHED'
        fixture=make_ledger_fixture(self.addCleanup)
        registration={key:fixture.identity[key] for key in ('code_sha256','config_sha256','dependency_sha256')}
        with patch('v5_shadow.daily_owner_adapters.datetime') as clock, \
                patch('v5_shadow.manager_plan.run_manager_plan',side_effect=[refreshed,page]) as owner:
            clock.now.return_value=datetime(2026,10,13,0,50,tzinfo=timezone.utc)
            saved=run_manager_daily(request_refresh,fixture.root,registration,
                publication=dict(config=self.config,expected_generation=self.generation))
        self.assertEqual(owner.call_count,2)
        self.assertEqual(saved['status'],'BLOCKED')
        self.assertEqual(saved['state']['attempts'][-1]['status'],'BLOCKED')
        self.assertEqual(self.record({})['payload']['run_id'],'a'*32)

    def test_directory_swap_cannot_write_outside_marked_root(self):
        from v5_shadow.module_artifacts import _directory
        self.enable();request,result,_=self.fixture()
        parent=self.publication/'m18-v2-bundles'; outside=self.root/'outside';outside.mkdir()
        swapped=[];before=(self.publication/'active.json').read_bytes()
        def swap(root,name):
            fd=_directory(root,name)
            if name=='m18-v2-bundles' and not swapped:
                parent.rename(self.root/'detached-bundles');parent.symlink_to(outside,target_is_directory=True)
                swapped.append(True)
            return fd
        escaped_writes=[];original_write=Path.write_bytes
        def observed_write(path,raw):
            if path.resolve().is_relative_to(outside):escaped_writes.append(str(path))
            return original_write(path,raw)
        with patch('v5_shadow.module_artifacts._directory',side_effect=swap), \
                patch.object(Path,'write_bytes',observed_write):
            with self.assertRaises((ValueError,OSError)):self.publish(request,result)
        self.assertEqual(escaped_writes,[])
        self.assertEqual(list(outside.iterdir()),[])
        self.assertEqual((self.publication/'active.json').read_bytes(),before)

    def test_published_run_identity_is_immutable(self):
        self.enable();request,result,_=self.fixture()
        first=self.publish(request,result);before=self.record({'run_id':'a'*32})
        changed=copy.deepcopy(result);changed['payload']['later_observation']='SYNTHETIC'
        with self.assertRaisesRegex(ValueError,'M18_DAILY_RUN_IMMUTABLE'):
            self.publish(request,changed,expected=first['generation_sha256'])
        self.assertEqual(self.record({'run_id':'a'*32}),before)
        self.assertEqual(self.record({})['payload'],before['payload'])

    def test_publication_failure_can_reuse_exact_verified_bundle(self):
        self.enable();request,result,_=self.fixture()
        with patch.object(bridge,'publish_generation',side_effect=ValueError('SYNTHETIC_CAS_FAILURE')):
            with self.assertRaisesRegex(ValueError,'SYNTHETIC_CAS_FAILURE'):
                self.publish(request,result)
        root=self.publication/'m18-v2-bundles'
        before={str(path.relative_to(root)):path.read_bytes() for path in root.rglob('*') if path.is_file()}
        self.publish(request,result)
        after={str(path.relative_to(root)):path.read_bytes() for path in root.rglob('*') if path.is_file()}
        self.assertEqual(before,after)
        self.assertEqual(self.record({})['payload']['run_id'],'a'*32)

    def test_dynamic_no_current_fails_closed_and_opt_in_is_strict_boolean(self):
        self.enable()
        with self.assertRaises(FileNotFoundError):self.record({})
        for value in ('true',1,None):
            bad=dict(self.config,m18_v2_daily_publication=value)
            with self.subTest(value=value),self.assertRaises(ValueError):api._config(bad)
        self.assertEqual(self.record({'run_id':disk.RUN})['payload']['target_date'],'20261012')

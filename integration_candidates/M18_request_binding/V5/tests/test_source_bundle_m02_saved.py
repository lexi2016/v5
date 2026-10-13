"""M02 saved-only dispatch and real persistence checks with synthetic sources.

The original owner's declared _collect unit seam supplies synthetic identities;
no test claims real three-source or Parquet validation. Disk/private-root/hash
validation and the original read_binding reconstruction run unchanged. The
build guard is armed only after the original builder creates the fixture.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from v5_shadow.module_api import _config, read_response
from v5_shadow import source_bundle
import test_source_bundle_publication_routes as route_fixture
from v5_shadow.source_bundle import STATUS_ROUTE, owner_root, publish_source_result

BASE = Path(__file__).resolve().parents[1]
WORKER = r'''
import copy, hashlib, importlib.util, json, sys, tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(sys.argv[1])/'V5/src'))
from v5_shadow import hk_source_daily as daily
spec = importlib.util.spec_from_file_location('p0_saved_worker', sys.argv[2])
bridge = importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)
case = sys.argv[3]
with tempfile.TemporaryDirectory(prefix='m02-saved-synthetic-') as temporary:
    root=Path(temporary).resolve(); out=root/'saved'; out.mkdir(mode=0o700)
    (out/'.v5-hk-source-root').write_bytes(daily.MARKER)
    inputs={}
    for name in ('panel','membership','native'):
        folder=root/name; folder.mkdir(); (folder/'fixture').write_bytes(name.encode())
        inputs[name]=dict(root=str(folder),files={'fixture':hashlib.sha256(name.encode()).hexdigest()})
    kw=dict(private_root=str(out),asset_binding=inputs['panel'],
        membership_root=inputs['membership']['root'],membership_files=inputs['membership']['files'],
        native_binding=inputs['native'],target_date='20261009',signal_date='20261008',
        eligibility_source_date='20261008',cutoff='2026-10-09T08:00:00+00:00')
    sources={name:dict(status='VERIFIED',identity={'fixture':name},times={},pit_verified=False)
             for name in inputs}
    sources['membership']['identity']['codes']=['00001','00002']
    for value in sources.values():
        value['identity']['private_path']=str(root/'PRIVATE_PATH_SENTINEL')
        value['identity']['files']={'PRIVATE_FILENAME_SENTINEL': 'synthetic-only'}
    with patch.object(daily,'_collect',return_value=copy.deepcopy(sources)):
        saved=daily.build_binding(**kw)
    request=dict(action='read',private_root=str(out),target_date='20261009',receipt_hash=saved['receiptHash'])
    if case=='wrong_receipt': request['receipt_hash']='0'*64
    if case=='wrong_date': request['target_date']='20261008'
    if case=='unknown_action': request['action']='read-or-build'
    if case=='extra_build_field': request['asset_binding']=inputs['panel']
    if case=='bad_disk_hash':
        next((out/'objects').glob('*.json')).write_bytes(b'{}')
    if case=='changed_source':
        (root/'panel/fixture').write_bytes(b'changed')
    if case in ('unsafe_flag','unknown_purpose','unknown_temporal','unknown_source_status','pit_upgrade'):
        binding=copy.deepcopy(saved['binding'])
        if case=='unsafe_flag': binding['production_allowed']=True
        if case=='unknown_purpose': binding['purpose']='UNRECOGNIZED_SUCCESS'
        if case=='unknown_temporal': binding['temporal_status']='READY'
        if case=='unknown_source_status': binding['sources']['panel']['status']='UNRECOGNIZED_SUCCESS'
        if case=='pit_upgrade': binding['sources']['panel']['pit_verified']=True
        binding_raw=daily.canonical_bytes(binding); binding_hash=hashlib.sha256(binding_raw).hexdigest()
        receipt=dict(saved['receipt'],binding_sha256=binding_hash)
        receipt_raw=daily.canonical_bytes(receipt); receipt_hash=hashlib.sha256(receipt_raw).hexdigest()
        (out/'objects'/(binding_hash+'.json')).write_bytes(binding_raw)
        (out/'receipts'/(receipt_hash+'.json')).write_bytes(receipt_raw)
        pointer_path=out/'slots/20261009.json'; pointer=json.loads(pointer_path.read_bytes())
        pointer.update(binding_sha256=binding_hash,receiptHash=receipt_hash)
        pointer_path.write_bytes(daily.canonical_bytes(pointer)); request['receipt_hash']=receipt_hash
    if case=='default_build': request=kw
    if case=='explicit_build': request=dict(kw,action='build')
    before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    calls={'build':0,'read':0}; original_build=daily.build_binding; original_read=daily.read_binding
    def build(**values):
        calls['build']+=1
        if case not in ('default_build','explicit_build'):
            raise AssertionError('BUILD_CALLED_IN_SAVED_READ')
        return original_build(**values)
    def read(*args,**values):
        calls['read']+=1
        return original_read(*args,**values)
    with patch.object(daily,'build_binding',side_effect=build), patch.object(daily,'read_binding',side_effect=read), patch.object(daily,'_collect',return_value=copy.deepcopy(sources)):
        try:
            result=bridge.m02(request); outcome=dict(ok=True,result=result)
        except Exception as error:
            outcome=dict(ok=False,error_type=type(error).__name__,error=str(error))
    after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert after==before, 'saved dispatch changed source or saved bytes'
    print(json.dumps(dict(outcome,calls=calls,expected=saved,unchanged=True),sort_keys=True))
'''


class M02SavedSourceTests(unittest.TestCase):
    def original_case(self, case='read'):
        completed = subprocess.run([sys.executable, '-I', '-B', '-c', WORKER,
            str(owner_root('m02')), str(BASE/'src/v5_shadow/source_bundle_worker.py'), case],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_saved_read_uses_original_reader_without_build(self):
        value=self.original_case()
        self.assertTrue(value['ok'], value)
        self.assertEqual(value['calls'], {'build':0,'read':1})
        self.assertEqual(value['result'], dict(status='SOURCE_IDENTITY_ONLY',
            saved=value['expected'],readback_verified=True))
        binding=value['result']['saved']['binding']
        self.assertEqual(binding['temporal_status'],'CANNOT_CONFIRM')
        self.assertTrue(all(source['pit_verified'] is False for source in binding['sources'].values()))
        for flag in ('formal_eligibility_verified','historical_eligible','production_allowed','buy_gate_updated','orders_sent'):
            self.assertIs(binding[flag],False)
        self.assertTrue(value['unchanged'])

    def test_original_disk_and_source_rejections_never_fall_back_to_build(self):
        for case, reason in [('wrong_receipt','M02_RECEIPT_POINTER_IDENTITY'),
                             ('wrong_date',''),('bad_disk_hash','M02_DISK_HASH_MISMATCH'),
                             ('changed_source','M02_ASSET_SHA')]:
            with self.subTest(case=case):
                value=self.original_case(case)
                self.assertFalse(value['ok'],value)
                self.assertEqual(value['calls'],{'build':0,'read':1})
                self.assertIn(reason,value['error'])

    def test_original_semantics_reject_resealed_status_or_authority_upgrade(self):
        for case in ('unsafe_flag','unknown_purpose','unknown_temporal','unknown_source_status','pit_upgrade'):
            with self.subTest(case=case):
                value=self.original_case(case)
                self.assertFalse(value['ok'],value)
                self.assertEqual(value['calls'],{'build':0,'read':1})
                expected='M02_DISK_IDENTITY' if case=='unsafe_flag' else 'M02_READBACK_IDENTITY_MISMATCH'
                self.assertEqual(value['error'],expected)

    def test_unknown_action_or_extra_build_fields_cannot_trigger_build(self):
        for case in ('unknown_action','extra_build_field'):
            with self.subTest(case=case):
                value=self.original_case(case)
                self.assertFalse(value['ok'],value)
                self.assertEqual(value['calls']['build'],0)
                if case=='unknown_action':
                    self.assertEqual(value['error'],'M02_SOURCE_ACTION')
                    self.assertEqual(value['calls']['read'],0)

    def test_default_and_explicit_build_retain_original_flow(self):
        for case in ('default_build','explicit_build'):
            with self.subTest(case=case):
                value=self.original_case(case)
                self.assertTrue(value['ok'],value)
                self.assertEqual(value['calls'],{'build':1,'read':1})
                self.assertEqual(value['result']['saved'],value['expected'])



class M02SavedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=route_fixture.SourceBundlePublicationRouteTests()
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root; self.config=self.fixture.config
        generation,self.siblings=self.fixture.seed_siblings()
        self.previous=copy.deepcopy(self.fixture.result)
        for i in (0,2,3):
            self.previous['modules'][i].update(status='RETAINED_SYNTHETIC_STATUS',
                owner_result={'fixture':'existing-product','sequence':i})
        self.generation=publish_source_result(self.previous,self.config,
            expected_generation=generation)['generation_sha256']
        self.read_request=dict(action='read',private_root='/SYNTHETIC/private/m02',
            target_date='20261009',receipt_hash='1'*64)
        value=M02SavedSourceTests().original_case()
        self.assertTrue(value['ok'],value)
        self.read_result=value['result']

    def publish(self, **kwargs):
        entry=getattr(source_bundle,'publish_m02_saved_binding',None)
        self.assertTrue(callable(entry),'M02_SAVED_PUBLICATION_ENTRY_MISSING')
        return entry(self.read_request,self.config,
            expected_generation=kwargs.get('expected_generation',self.generation),
            data_kind=kwargs.get('data_kind','SYNTHETIC'))

    def test_only_m02_row_changes_and_projection_hides_private_paths(self):
        before=self.fixture.tree(); config_before=copy.deepcopy(self.config)
        with patch.object(source_bundle,'_call',return_value=self.read_result) as transport:
            published=self.publish()
        transport.assert_called_once_with('m02',self.read_request)
        after=published['result']; self.assertEqual(self.config,config_before)
        for i in (0,2,3):self.assertEqual(after['modules'][i],self.previous['modules'][i])
        row=after['modules'][1]; self.assertEqual(row['status'],'SOURCE_IDENTITY_ONLY')
        projected=row['owner_result']; self.assertEqual(projected['projection_schema'],'v5.m02.saved_public_view.v1')
        binding=projected['saved']['binding']
        self.assertEqual(binding['temporal_status'],'CANNOT_CONFIRM')
        self.assertEqual(binding['sources']['membership']['member_count'],2)
        self.assertTrue(all(s['pit_verified'] is False for s in binding['sources'].values()))
        encoded=json.dumps(projected)
        private=self.read_result['saved']['binding']['request']
        forbidden_values=[private['private_root'],*[b['root'] for b in private['inputs'].values()]]
        for forbidden in (*forbidden_values,'PRIVATE_PATH_SENTINEL','PRIVATE_FILENAME_SENTINEL',
                          '/SYNTHETIC/','private_root','panel_path','model_path','"inputs"','"files"','"root"'):
            self.assertNotIn(forbidden,encoded)
        current=json.loads((self.root/'active.json').read_bytes())['generation_sha256']
        refs=json.loads((self.root/'generations'/(current+'.json')).read_bytes())['records']
        for key,digest in self.siblings.items():self.assertEqual(refs[key],digest)
        for path,raw in before.items():
            if path!='active.json':self.assertEqual((self.root/path).read_bytes(),raw)
        checked,fd=_config(self.config)
        try: record,_=read_response(checked,fd,STATUS_ROUTE,{})
        finally:os.close(fd)
        self.assertEqual(record['payload'],after)

    def test_read_failure_cas_conflict_and_data_kind_mismatch_do_not_publish(self):
        before=self.fixture.tree()
        with patch.object(source_bundle,'_call',side_effect=ValueError('M02_READ_REJECTED')):
            with self.assertRaisesRegex(ValueError,'M02_READ_REJECTED'):self.publish()
        self.assertEqual(self.fixture.tree(),before)
        with patch.object(source_bundle,'_call',side_effect=AssertionError('owner should not run')):
            with self.assertRaisesRegex(ValueError,'GENERATION_CONFLICT'):self.publish(expected_generation='0'*64)
            with self.assertRaisesRegex(ValueError,'M02_SAVED_DATA_KIND_MISMATCH'):self.publish(data_kind='RECORDED_INPUT_REPLAY')
        self.assertEqual(self.fixture.tree(),before)

    def test_racing_publication_rejects_stale_merge_without_clobbering(self):
        race={}
        def intervening(_owner,_request):
            changed=copy.deepcopy(self.previous);changed['modules'][0]['owner_result']['sequence']='newer'
            race['result']=changed
            race['generation']=publish_source_result(changed,self.config,
                expected_generation=self.generation)['generation_sha256']
            race['tree']=self.fixture.tree()
            return self.read_result
        with patch.object(source_bundle,'_call',side_effect=intervening):
            with self.assertRaisesRegex(ValueError,'GENERATION_CONFLICT'):self.publish()
        self.assertEqual(self.fixture.tree(),race['tree'])

    def test_projection_rejects_unknown_semantics_or_true_flags(self):
        before=self.fixture.tree()
        for field,value in [('status','UNRECOGNIZED_SUCCESS'),('readback_verified',False)]:
            with self.subTest(field=field):
                malformed=copy.deepcopy(self.read_result);malformed[field]=value
                with patch.object(source_bundle,'_call',return_value=malformed):
                    with self.assertRaisesRegex(ValueError,'M02_SAVED_RESULT_CONTRACT'):self.publish()
        malformed=copy.deepcopy(self.read_result);malformed['saved']['binding']['production_allowed']=True
        with patch.object(source_bundle,'_call',return_value=malformed):
            with self.assertRaisesRegex(ValueError,'M02_SAVED_RESULT_CONTRACT'):self.publish()
        self.assertEqual(self.fixture.tree(),before)

    def test_duplicate_predecessor_row_is_not_reconstructed_or_published(self):
        broken=copy.deepcopy(self.previous);broken['modules'][0]=copy.deepcopy(broken['modules'][1])
        self.generation=publish_source_result(broken,self.config,
            expected_generation=self.generation)['generation_sha256']
        before=self.fixture.tree()
        with patch.object(source_bundle,'_call',side_effect=AssertionError('owner should not run')):
            with self.assertRaisesRegex(ValueError,'M02_SAVED_PREDECESSOR_CONTRACT'):self.publish()
        self.assertEqual(self.fixture.tree(),before)

    def test_aba_head_transition_keeps_exact_expected_predecessor_object(self):
        from v5_shadow import module_api
        from v5_shadow.module_artifacts import activate_generation
        original=module_api._read_object; race={}
        def object_with_race(root,digest,config=None):
            if not race:
                changed=copy.deepcopy(self.previous)
                changed['modules'][0]['owner_result']['sequence']='intermediate-B'
                race['generation']=publish_source_result(changed,self.config,
                    expected_generation=self.generation)['generation_sha256']
            return original(root,digest,config)
        def restore_a(_owner,_request):
            activate_generation(self.config,self.generation,expected_generation=race['generation'])
            return self.read_result
        with patch.object(module_api,'_read_object',side_effect=object_with_race), \
             patch.object(source_bundle,'_call',side_effect=restore_a):
            result=self.publish()['result']
        for i in (0,2,3):self.assertEqual(result['modules'][i],self.previous['modules'][i])


if __name__=='__main__': unittest.main()

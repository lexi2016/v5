"""Real frozen reader contract tests; fixtures never imply production success."""
import copy
import csv
import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from fixtures.hk_preselection_verified_factory import create_verified_fixture
import test_hk_preselection as legacy_tests
from v5_shadow.digests import canonical_bytes, sha256_json
from v5_shadow.hk_preselection_verified import run_verified_hk_preselection


class VerifiedOriginalRegressions(legacy_tests.HKPreselectionTests):
    def request(self, **changes):
        return create_verified_fixture(self.root, **changes)

    def run_request(self, request):
        return run_verified_hk_preselection(request)

    def test_late_receipt_and_bad_input_hash_rejected(self):
        request=self.request();request['research_cutoff']='2026-10-08T07:00:00+08:00'
        self.assertEqual(self.run_request(request)['status'],'CANNOT_CONFIRM')
        request=self.request();request['files']['latest.json']='a'*64
        with self.assertRaises(ValueError):self.run_request(request)


class VerifiedContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()

    def request(self, **changes):return create_verified_fixture(self.root/'input', **changes)

    def test_real_cold_chain_exact_original_artifact_and_identity(self):
        from v5_shadow.hk_preselection import run_hk_preselection
        request=self.request()
        old={k:v for k,v in request.items() if k not in ('schema_version','expected_source')}
        old['data_kind']='SYNTHETIC'
        legacy=run_hk_preselection(old)
        result=run_verified_hk_preselection(request)
        self.assertEqual(result['status'],'ASSEMBLED')
        self.assertEqual(canonical_bytes(result['artifact']),canonical_bytes(legacy['artifact']))
        self.assertEqual(result['verified_source_reference'],request['expected_source'])
        self.assertEqual(result['data_kind'],'VERIFIED_SOURCE_SNAPSHOT')
        self.assertTrue(result['fixture_only'])
        for flag in ('production_allowed','buy_gate_updated','orders_sent','formal_eligibility_verified','natural_verified','model_weights_reverified'):
            self.assertIs(result[flag],False)
        self.assertEqual(list(inspect.signature(run_verified_hk_preselection).parameters),['request'])

    def test_actual_low_level_verification_is_preserved(self):
        req=self.request();result=run_verified_hk_preselection(req)
        self.assertIn('source_verification',result)
        actual=result['source_verification']
        entry=json.loads((Path(req['input_root'])/'latest.json').read_bytes())['entries'][req['target_date']+'/'+req['expected_source']['role']]
        manifest=json.loads((Path(req['input_root'])/entry['manifest_relative']).read_bytes())
        self.assertEqual(actual['manifest_relative'],entry['manifest_relative'])
        self.assertEqual(actual['receipt_relative'],entry['receipt_relative'])
        self.assertEqual(actual['input_sha256'],manifest['input_sha256'])
        self.assertEqual(actual['status'],'READY');self.assertEqual(actual['row_count'],100)
        for key,value in req['expected_source'].items():
            if key!='role':self.assertEqual(actual[key],value)

    def test_each_identity_absent_none_empty_and_wrong_sha_rejected(self):
        req=self.request()
        for key in req['expected_source']:
            for mode in ('missing',None,''):
                with self.subTest(key=key,mode=mode):
                    value=copy.deepcopy(req)
                    if mode=='missing':del value['expected_source'][key]
                    else:value['expected_source'][key]=mode
                    with self.assertRaises(ValueError):run_verified_hk_preselection(value)
        for key in ('artifact_sha256','manifest_sha256','receipt_sha256'):
            for bad in ('g'*64,'a'*63,'a'*64):
                with self.subTest(key=key,bad=bad):
                    value=copy.deepcopy(req);value['expected_source'][key]=bad
                    with self.assertRaises(ValueError):run_verified_hk_preselection(value)

    def test_each_of_eight_files_required(self):
        req=self.request();self.assertEqual(len(req['files']),8)
        for rel in req['files']:
            with self.subTest(rel=rel):
                value=copy.deepcopy(req);del value['files'][rel]
                with self.assertRaises(ValueError):run_verified_hk_preselection(value)

    def test_relative_path_and_ancestor_symlink_rejected(self):
        req=self.request()
        for rel in ('/tmp/nope','../nope',''):
            value=copy.deepcopy(req);value['files'][rel]='a'*64
            with self.assertRaises(ValueError):run_verified_hk_preselection(value)
        linked=self.root/'link';linked.symlink_to(self.root/'input',target_is_directory=True)
        value=copy.deepcopy(req);value['input_root']=str(linked)
        with self.assertRaisesRegex(ValueError,'SYMLINK'):run_verified_hk_preselection(value)
        link_parent=self.root/'parent-link';link_parent.symlink_to(self.root,target_is_directory=True)
        value=copy.deepcopy(req);value['input_root']=str(link_parent/'input')
        with self.assertRaisesRegex(ValueError,'SYMLINK'):run_verified_hk_preselection(value)

    def test_kind_extra_fields_and_bad_dates_rejected(self):
        req=self.request()
        for key,value in [('data_kind','VERIFIED_SOURCE_SNAPSHOT'),('data_kind','SYNTHETIC'),('signal_date','20261008'),('research_cutoff','2026-10-08T09:20:00'),('callback',True)]:
            copyreq=copy.deepcopy(req);copyreq[key]=value
            with self.assertRaises(ValueError):run_verified_hk_preselection(copyreq)

    def test_wrong_run_path_role_and_tamper_rejected(self):
        req=self.request()
        for key,value in [('run_id','wrong'),('artifact_relative','wrong.csv'),('role','A')]:
            bad=copy.deepcopy(req);bad['expected_source'][key]=value
            with self.assertRaises(ValueError):run_verified_hk_preselection(bad)
        path=Path(req['input_root'])/'latest.json';path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaises(ValueError):run_verified_hk_preselection(req)

    def test_101_nan_clock_and_unready_cannot_confirm(self):
        for changes in ({'count':101},{'score_override':'nan'},{'pool_capture_time':'08:10:00'},{'status':'CANNOT_CONFIRM'}):
            with self.subTest(changes=changes):
                r=run_verified_hk_preselection(self.request(**changes))
                self.assertEqual(r['status'],'CANNOT_CONFIRM');self.assertEqual(r['data_kind'],'SOURCE_SNAPSHOT')
                self.assertIsNone(r['artifact']);self.assertIsNone(r['verified_source_reference'])

    def test_original_projector_owned_fields_preserve_exact_legacy_semantics(self):
        from v5_shadow.hk_preselection import run_hk_preselection
        req=self.request();root=Path(req['input_root']);path=root/req['expected_source']['artifact_relative']
        with path.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        for row in rows:row.update(production_allowed='False',buy_gate_updated='False',orders_sent='False',market='HK_CONNECT')
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        mp=path.with_name('manifest.json');rp=path.with_name('receipt.json')
        manifest=json.loads(mp.read_bytes());receipt=json.loads(rp.read_bytes())
        digest=hashlib.sha256(path.read_bytes()).hexdigest();manifest['artifact_sha256']=digest;receipt['artifact_sha256']=digest
        mp.write_bytes(canonical_bytes(manifest));receipt['manifest_sha256']=sha256_json(manifest);rp.write_bytes(canonical_bytes(receipt))
        for p in (path,mp,rp):req['files'][str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
        req['expected_source'].update(artifact_sha256=digest,manifest_sha256=sha256_json(manifest),receipt_sha256=hashlib.sha256(rp.read_bytes()).hexdigest())
        old={k:v for k,v in req.items() if k not in ('schema_version','expected_source')};old['data_kind']='SYNTHETIC'
        expected=run_hk_preselection(old)
        actual=run_verified_hk_preselection(req)
        self.assertEqual(actual['status'],'ASSEMBLED')
        self.assertEqual(canonical_bytes(actual['artifact']),canonical_bytes(expected['artifact']))

    def test_duplicate_rows_rejected_with_self_consistent_hashes(self):
        req=self.request();root=Path(req['input_root']);relative=req['expected_source']['artifact_relative']
        path=root/relative
        with path.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f));fields=list(rows[0])
        rows[1]['code_norm']=rows[0]['code_norm']
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        mpath=path.with_name('manifest.json');rpath=path.with_name('receipt.json')
        m=json.loads(mpath.read_bytes());r=json.loads(rpath.read_bytes())
        digest=hashlib.sha256(path.read_bytes()).hexdigest();m['artifact_sha256']=digest;r['artifact_sha256']=digest
        mpath.write_bytes(canonical_bytes(m));r['manifest_sha256']=sha256_json(m);rpath.write_bytes(canonical_bytes(r))
        for p in (path,mpath,rpath):req['files'][str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
        req['expected_source'].update(artifact_sha256=digest,manifest_sha256=sha256_json(m),receipt_sha256=hashlib.sha256(rpath.read_bytes()).hexdigest())
        self.assertEqual(run_verified_hk_preselection(req)['status'],'CANNOT_CONFIRM')

if __name__=='__main__':unittest.main()

"""Offline M05 acceptance: real assembler, frozen strict store and physical bytes."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_a_preselection import (make_lane, make_baimao_lane, make_wechat_lane, make_research_lane,
    make_v192_lane, publish_frozen_hourly_fixture, research_hourly_item, make_research_lane_from_root)
from v5_shadow.a_preselection import run_a_preselection, BASE
from v5_shadow.digests import canonical_bytes, sha256_json

POOLS = {
    'v192': 'a_d1_premarket_pool',
    'fupan': 'a_d1_fupan_watchlist_pool',
    'stage7': 'a_d1_stage7_fenshi_review_pool',
    'research': 'a_share_research_recommendation_pool',
    'baimao': 'a_share_baimao_research_map',
    'wechat': 'wechat_public_account_v3_preselect',
}


class M05DailyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='m05-isolated-fixture-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = self.root / 'source'
        self.out = self.root / 'shadow'
        self.control = self.root / 'control'
        self.v4 = self.root / 'v4-sentinel'
        for p in (self.source, self.out, self.control, self.v4):
            p.mkdir()
        (self.out / '.v5-shadow-root').write_text('v5.shadow-root.v1\n')
        (self.v4 / 'untouched').write_text('V4 must remain unchanged')
        keys = [dict(business_key='SYNTHETIC:' + k, trade_date='20261008', pool_id=v)
                for k, v in POOLS.items()]
        keys.sort(key=lambda x: (x['business_key'], x['trade_date'], x['pool_id']))
        self.permit = dict(schema_version='v4.preselection.exact_scope.v1',
            decision_id='SYNTHETIC_FIXTURE_ONLY', owner_id='SYNTHETIC_M05_TEST',
            source_release_sha256='1'*64, target_release_sha256='2'*64,
            source_root=str(self.source), target_root=str(self.out), keys=keys,
            business_key_set_sha256=sha256_json(keys))
        (self.control/'permit.json').write_bytes(canonical_bytes(self.permit))
        self.context = dict(control_dir=str(self.control),
            expected_permit_sha256=hashlib.sha256((self.control/'permit.json').read_bytes()).hexdigest(),
            expected_owner_id='SYNTHETIC_M05_TEST', expected_release_sha256='2'*64,
            expected_root=str(self.out))
        self.gate = dict(schema_version='v4.preselection.gate.v1',
            permit_sha256=self.context['expected_permit_sha256'], revision=1, state='OPEN')
        (self.control/'gate.json').write_bytes(canonical_bytes(self.gate))
        self.kw = dict(source_root=str(self.source), private_root=str(self.out),
            code_root=str(BASE), v4_root=str(self.v4), write_gate_context=self.context)

    def request(self, lanes):
        return dict(target_date='20261008', signal_date='20260930', data_kind='SYNTHETIC', lanes=lanes)

    def daily(self, request, **changes):
        from v5_shadow.a_preselection_daily import build_m05_daily
        return build_m05_daily(request, **dict(self.kw, **changes))

    def tree(self, root):
        return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def test_daily_entrypoint_exists(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.a_preselection_daily'))

    def test_default_chain_keeps_scores_and_final_batch_raw_identity(self):
        req = self.request([make_lane(self.source/'fupan', count=250),
                            make_lane(self.source/'stage7', 'stage7'),
                            make_wechat_lane(self.source/'wechat', '20261008', '20260930'),
                            make_baimao_lane(self.source/'baimao', '20261008')])
        before = self.tree(self.source), self.tree(self.control), self.tree(self.v4)
        result = self.daily(req)
        self.assertEqual(result['status'], 'READY')
        self.assertEqual(result['integration_status'], 'WAIT_INTEGRATION')
        self.assertEqual(result['request_sha256'], sha256_json(req))
        self.assertEqual(result['row_count'], 253)
        self.assertEqual(result['receipts'][0]['pool_scores'][-1], 259)
        self.assertEqual(len(result['receipts'][0]['rows']), 250)
        digests = {r['manifest_raw_sha256'] for r in result['receipts']}
        self.assertEqual(len(digests), 1)
        self.assertEqual(result['batch_identity']['manifest_raw_sha256'], next(iter(digests)))
        self.assertEqual(result['batch_identity']['snapshot_count'], 4)
        for receipt in result['receipts']:
            for name in ('artifact', 'manifest', 'receipt'):
                b = (self.out/receipt[name+'_relative_path']).read_bytes()
                self.assertEqual(hashlib.sha256(b).hexdigest(), receipt[name+'_raw_sha256'])
            artifact = json.loads((self.out/receipt['artifact_relative_path']).read_bytes())
            self.assertEqual(sha256_json(artifact), receipt['artifact_sha256'])
            self.assertEqual(artifact['rows'], receipt['rows'])
            self.assertEqual(artifact, receipt['artifact'])
            self.assertEqual(artifact['status'], receipt['artifact_status'])
            self.assertEqual(artifact['cannot_confirm'], receipt['cannot_confirm'])
        self.assertFalse(result['orders_sent'])
        self.assertEqual(before, (self.tree(self.source), self.tree(self.control), self.tree(self.v4)))
        repeated = self.daily(req)
        self.assertEqual(repeated['batch_identity'], result['batch_identity'])
        self.assertEqual(repeated['receipts'], result['receipts'])

    def test_six_original_lanes_publish_one_batch_with_hourly_research(self):
        hourly = self.source/'research'; hourly.mkdir()
        publish_frozen_hourly_fixture(hourly,[research_hourly_item('20261007','0900',
            [('daily-row','2026-10-07T09:00:00+08:00')])])
        req=self.request([
            make_v192_lane(self.source/'v192','20261008','20260930'),
            make_lane(self.source/'fupan'), make_lane(self.source/'stage7','stage7'),
            make_wechat_lane(self.source/'wechat','20261008','20260930'),
            make_baimao_lane(self.source/'baimao','20261008'),
            make_research_lane_from_root(hourly)])
        result=self.daily(req)
        self.assertEqual(result['status'],'READY')
        self.assertEqual(result['row_count'],6)
        self.assertEqual({r['pool_id'] for r in result['receipts']},set(POOLS.values()))
        self.assertEqual(result['batch_identity']['snapshot_count'],6)
        self.assertEqual(len({r['manifest_raw_sha256'] for r in result['receipts']}),1)
        research=result['receipts'][-1]
        self.assertEqual(research['source_role'],'VERIFIED_HOURLY_RESEARCH')
        self.assertEqual(research['pool_scores'],[1])
        self.assertEqual(result['receipts'][0]['source_role'],'SHARED_VERIFIED_V192')

    def test_scope_excludes_unpermitted_success_key_without_writes(self):
        from v5_shadow.a_preselection_daily import M05WriterError
        req=self.request([make_lane(self.source/'fupan'),make_lane(self.source/'stage7','stage7')])
        self.permit['keys']=[k for k in self.permit['keys'] if k['pool_id']!=POOLS['stage7']]
        self.permit['business_key_set_sha256']=sha256_json(self.permit['keys'])
        (self.control/'permit.json').write_bytes(canonical_bytes(self.permit))
        self.context['expected_permit_sha256']=hashlib.sha256((self.control/'permit.json').read_bytes()).hexdigest()
        self.gate['permit_sha256']=self.context['expected_permit_sha256']
        (self.control/'gate.json').write_bytes(canonical_bytes(self.gate))
        before=self.tree(self.out),self.tree(self.control)
        with self.assertRaisesRegex(M05WriterError,'M05_POOL_OUTSIDE_EXACT_SCOPE'):
            self.daily(req)
        self.assertEqual(before,(self.tree(self.out),self.tree(self.control)))

    def test_all_five_context_fields_required_without_writes(self):
        from v5_shadow.a_preselection_daily import M05WriterError
        req = self.request([make_lane(self.source/'fupan')])
        for key in self.context:
            with self.subTest(field=key):
                context = dict(self.context); context.pop(key)
                before = self.tree(self.out), self.tree(self.control)
                with self.assertRaisesRegex(ValueError, 'M05_CONTEXT_FIELDS_REQUIRED'):
                    self.daily(req, write_gate_context=context)
                self.assertEqual(before, (self.tree(self.out), self.tree(self.control)))

    def test_each_bad_gate_binding_fails_before_any_write(self):
        from v5_shadow.a_preselection_daily import M05WriterError
        req = self.request([make_lane(self.source/'fupan')])
        cases = [('expected_permit_sha256','3'*64,'permit does not match independent trust anchor'),
                 ('expected_owner_id','OTHER','permit owner identity mismatch'),
                 ('expected_release_sha256','4'*64,'store root/release identity mismatch'),
                 ('expected_root',str(self.source),'configured root does not match store root'),
                 ('control_dir',str(self.root/'missing'),'unavailable control directory')]
        for key, value, reason in cases:
            with self.subTest(field=key):
                context = dict(self.context, **{key:value}); before = self.tree(self.out), self.tree(self.control)
                with self.assertRaisesRegex(M05WriterError, reason) as error:
                    self.daily(req, write_gate_context=context)
                self.assertEqual(error.exception.remote_type, 'GateConfigurationError')
                self.assertEqual(before, (self.tree(self.out), self.tree(self.control)))

    def test_fenced_gate_rejects_before_import_lock_or_pool_write(self):
        from v5_shadow.a_preselection_daily import M05WriterError
        req = self.request([make_lane(self.source/'fupan'), make_lane(self.source/'stage7','stage7')])
        self.gate['state']='FENCED'; (self.control/'gate.json').write_bytes(canonical_bytes(self.gate))
        before=self.tree(self.out),self.tree(self.control)
        with self.assertRaisesRegex(M05WriterError,'preselection pool fenced') as error:
            self.daily(req)
        self.assertEqual(error.exception.remote_type,'StoreWriteFenced')
        self.assertEqual(before,(self.tree(self.out),self.tree(self.control)))

    def test_missing_gate_and_bad_gate_identity_do_not_write(self):
        from v5_shadow.a_preselection_daily import M05WriterError
        req=self.request([make_lane(self.source/'fupan')])
        for value in (None, dict(self.gate,permit_sha256='5'*64)):
            p=self.control/'gate.json'
            if value is None:p.unlink()
            else:p.write_bytes(canonical_bytes(value))
            before=self.tree(self.out),self.tree(self.control)
            with self.assertRaises(M05WriterError):self.daily(req)
            self.assertEqual(before,(self.tree(self.out),self.tree(self.control)))

    def test_output_rejects_overlap_both_directions_and_symlink(self):
        req=self.request([make_lane(self.source/'fupan')])
        for key in ('source_root','code_root','v4_root'):
            for path in (self.out,self.root,self.out/'child'):
                with self.subTest(key=key,path=path):
                    with self.assertRaisesRegex(ValueError,'M05_ROOT_OVERLAP'):
                        self.daily(req,**{key:str(path)})
        link=self.root/'link';link.symlink_to(self.out,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'SYMLINK_REJECTED'):
            self.daily(req,private_root=str(link))
        self.assertFalse((self.out/'.import.lock.mutex').exists())

    def test_marker_is_required_before_gate_or_assembler(self):
        req=self.request([make_lane(self.source/'fupan')])
        (self.out/'.v5-shadow-root').unlink()
        with self.assertRaisesRegex(ValueError,'SHADOW_ROOT_NOT_INITIALIZED'):self.daily(req)
        self.assertEqual(self.tree(self.out),{})

    def test_expected_missing_never_occupies_pool_key(self):
        missing=make_research_lane(self.source/'research',preview=False,selector=False)
        result=self.daily(self.request([missing]))
        self.assertEqual(result['status'],'DEFERRED')
        self.assertEqual(result['outcomes'][0]['status'],'EXPECTED_MISSING')
        self.assertEqual(result['outcomes'][0]['artifact']['source_role'],'EXPECTED_MISSING')
        self.assertTrue(result['outcomes'][0]['artifact']['cannot_confirm'])
        self.assertIsNone(result['row_count'])
        self.assertEqual(result['receipts'],[])
        self.assertEqual(set(self.tree(self.out)),{'.v5-shadow-root'})

    def test_contract_valid_empty_retains_zero_rows_and_explicit_status(self):
        # This explicitly tests the wire contract seam, not a claim that the
        # current V192 builder supports its rejected verified-empty status.
        req=self.request([make_lane(self.source/'fupan')]);assembled=run_a_preselection(req)
        assembled['lanes'][0]['artifact'].update(rows=[],status='VALID_EMPTY')
        assembled['row_count']=0
        result=self.daily(req,run_a_preselection=lambda request:assembled)
        self.assertEqual(result['status'],'READY')
        self.assertEqual(result['row_count'],0)
        self.assertEqual(result['receipts'][0]['artifact_status'],'VALID_EMPTY')
        self.assertEqual(result['receipts'][0]['artifact']['rows'],[])

    def test_nonaccepted_artifact_and_assembly_evidence_are_preserved(self):
        req=self.request([make_lane(self.source/'fupan',count=0)])
        assembled=run_a_preselection(req)
        result=self.daily(req)
        self.assertEqual(result['status'],'REJECTED')
        self.assertEqual(result['outcomes'][0]['artifact'],assembled['lanes'][0]['artifact'])
        for name in ('input_binding_status','isolation_status','source_capsule_sha256','implementation_sha256'):
            self.assertEqual(result['assembly_evidence'][name],assembled[name])
        self.assertEqual(set(self.tree(self.out)),{'.v5-shadow-root'})

    def test_bad_optional_lane_retains_diagnostic_and_healthy_sibling(self):
        req=self.request([make_lane(self.source/'fupan'),make_lane(self.source/'stage7','stage7',corrupt=True)])
        result=self.daily(req)
        self.assertEqual(result['status'],'PARTIAL')
        self.assertEqual(len(result['receipts']),1)
        self.assertEqual(result['outcomes'][1]['status'],'REJECTED')
        self.assertIn('mismatch',result['outcomes'][1]['reason'])
        self.assertNotIn(POOLS['stage7'],json.loads((self.out/'preselection_pools/20261008/manifest.json').read_text()))

    def test_conflict_is_aggregated_after_healthy_sibling_and_not_success(self):
        from v5_shadow.a_preselection_daily import M05PublicationError
        lane=make_lane(self.source/'fupan')
        self.daily(self.request([lane]))
        pool=self.source/'fupan/pool.csv';pool.write_text(pool.read_text().replace(',10\n',',99\n'))
        lane['files']['pool.csv']=hashlib.sha256(pool.read_bytes()).hexdigest()
        with self.assertRaises(M05PublicationError) as error:
            self.daily(self.request([lane,make_lane(self.source/'stage7','stage7')]))
        result=error.exception.result
        self.assertEqual(result['status'],'CONFLICT')
        self.assertEqual([x['status'] for x in result['outcomes']],['CONFLICT','SUCCESS'])
        self.assertEqual([x['pool_id'] for x in result['receipts']],[POOLS['stage7']])
        self.assertEqual(result['receipts'][0]['rows'][0]['pool_score'],10)
        self.assertIn(POOLS['fupan'],result['batch_identity']['manifest'])

    def test_non_conflict_store_error_is_not_downgraded(self):
        from v5_shadow.a_preselection_daily import M05WriterError
        lane=make_lane(self.source/'fupan');folder=self.out/'preselection_pools/20261008'
        folder.mkdir(parents=True);(folder/(POOLS['fupan']+'.json')).write_text('{}')
        with self.assertRaisesRegex(M05WriterError,'partial preselection-pool materialization'):
            self.daily(self.request([lane]))

    def test_host_top_level_modules_cannot_supply_frozen_store(self):
        import types
        poison=types.ModuleType('infrastructure');poison.__path__=[]
        lane=make_lane(self.source/'fupan')
        with patch.dict(sys.modules,{'infrastructure':poison}):
            result=self.daily(self.request([lane]))
        self.assertEqual(result['status'],'READY')

    def test_request_identity_and_lane_mapping_checked_before_writer(self):
        req=self.request([make_lane(self.source/'fupan')]);result=run_a_preselection(req)
        for mutation,reason in ((lambda r:r.update(request_sha256='0'*64),'M05_REQUEST_IDENTITY_MISMATCH'),
            (lambda r:r['lanes'][0]['artifact'].update(pool_id=POOLS['stage7']),'M05_LANE_POOL_MISMATCH')):
            bad=copy.deepcopy(result);mutation(bad)
            with self.assertRaisesRegex(ValueError,reason):
                self.daily(req,run_a_preselection=lambda unused:bad)
            self.assertFalse((self.out/'.import.lock.mutex').exists())


if __name__=='__main__':unittest.main()

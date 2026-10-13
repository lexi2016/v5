"""Synthetic request/transport tests; no provider, real owner or Parquet run."""
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from datetime import timedelta, timezone
from unittest.mock import patch
from v5_shadow import rebound_owner as owner, rebound_panel_repair as repair
from v5_shadow.digests import canonical_bytes
from test_rebound_owner import request_for

class RepairedOwnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.request = request_for(self.root/'inputs')
        self.old = copy.deepcopy(self.request)
        paths = self.request['paths']
        paths['panel_receipt'] = str(Path(paths['panel']).with_name('receipt.json'))
        paths['repair_parent_manifest'] = 'assets/hk_0_2/panels/SYNTHETIC-parent/manifest.json'
        paths['repair_parent_panel'] = 'assets/hk_0_2/panels/SYNTHETIC-parent/hkconnect_vipdoc_daily_panel.parquet'
        for key in owner.REPAIR_ROLES:
            file = Path(self.request['input_root'])/paths[key]
            file.parent.mkdir(parents=True,exist_ok=True); file.write_bytes(b'{}')
            self.request['files'][paths[key]] = hashlib.sha256(file.read_bytes()).hexdigest()
        manifest_path = Path(self.request['input_root'])/paths['panel_manifest']
        manifest = owner._json(manifest_path.read_bytes())
        manifest['source_contract'] = repair.RAW_SOURCE_CONTRACT
        manifest['internal_gap_repair'] = {
            'parent_manifest_relative': paths['repair_parent_manifest'].removeprefix('assets/hk_0_2/'),
            'parent_panel_relative': paths['repair_parent_panel'].removeprefix('assets/hk_0_2/')}
        manifest_path.write_bytes(canonical_bytes(manifest))
        self.request['files'][paths['panel_manifest']] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    def test_accepts_explicit_repair_roles_and_old_request(self):
        self.assertEqual(owner._request(self.request),self.request)
        self.assertEqual(owner._request(self.old),self.old)

    def test_missing_or_extra_role_rejected(self):
        for role in owner.REPAIR_ROLES:
            req=copy.deepcopy(self.request); del req['paths'][role]
            with self.subTest(role=role),self.assertRaises(ValueError):owner._request(req)
        req=copy.deepcopy(self.request); req['files']['assets/hk_0_2/panels/unused/receipt.json']='a'*64
        with self.assertRaises(ValueError): owner._request(req)

    def test_repair_receipt_must_be_in_child_directory(self):
        req=copy.deepcopy(self.request); prior=req['paths']['panel_receipt']
        req['paths']['panel_receipt']='assets/hk_0_2/panels/elsewhere/receipt.json'
        req['files'][req['paths']['panel_receipt']]=req['files'].pop(prior)
        with self.assertRaisesRegex(ValueError,'REPAIR_ROLE_BINDING'):owner._request(req)

    def test_no_combining_repair_and_supplement(self):
        req=copy.deepcopy(self.request)
        for role in owner.SUPPLEMENT_ROLES: req['paths'][role]='unused/'+role
        with self.assertRaises(ValueError):owner._request(req)

    def test_original_witness_exact_binding_and_cutoff(self):
        with patch.object(repair,'read_repaired_panel_witness',return_value={'verified':'SYNTHETIC'}) as read:
            self.assertEqual(owner._repaired_witness(Path(self.request['input_root']),self.request),{'verified':'SYNTHETIC'})
        args,kw=read.call_args
        self.assertEqual(args[0],Path(self.request['input_root'])/'assets/hk_0_2')
        self.assertEqual(kw['cutoff'],self.request['research_cutoff'])
        self.assertEqual(len(kw['expected_files']),5)
        self.assertIn('panels/SYNTHETIC-parent/manifest.json',kw['expected_files'])

    def test_wrong_parent_contract_and_witness_failure_fail_closed(self):
        path=Path(self.request['input_root'])/self.request['paths']['panel_manifest']
        data=owner._json(path.read_bytes());data['internal_gap_repair']['parent_panel_relative']='panels/wrong/hkconnect_vipdoc_daily_panel.parquet'
        path.write_bytes(canonical_bytes(data))
        with self.assertRaisesRegex(ValueError,'REPAIR_ROLE_BINDING'):owner._repaired_witness(Path(self.request['input_root']),self.request)

    def test_unrepaired_read_does_not_enter_extension(self):
        with patch.object(repair,'read_repaired_panel_witness',side_effect=AssertionError):
            self.assertIsNone(owner._repaired_witness(Path(self.old['input_root']),self.old))

    def test_identity_preserves_old_key_set_and_binds_extension(self):
        old=owner._identity(); new=owner._identity(repaired=True)
        self.assertEqual(set(new)-set(old),{'rebound_panel_repair.py','rebound_raw_repair.py'})
        self.assertTrue(set(old).issubset(new))

    def test_worker_hook_accepts_same_instant_in_hk_zone_not_wrong_context(self):
        original=SimpleNamespace(_read_hk02_panel_witness='untouched')
        root=Path(self.request['input_root'])
        owner._install_repaired_witness(original,root,self.request)
        cutoff=owner.aware(self.request['research_cutoff']).astimezone(timezone(timedelta(hours=8))).isoformat()
        day=self.request['signal_date']; history=repair._history_window(day)['previous5'][-1]
        with patch.object(owner,'_repaired_witness',return_value={'verified':'SYNTHETIC'}) as read:
            result,gaps=original._read_hk02_panel_witness(root,day,research_cutoff=cutoff,required_history_date=history)
            self.assertEqual(result,{'verified':'SYNTHETIC'})
            self.assertIn('SCREEN_REPAIRED_HISTORY_RESEARCH_ONLY',gaps)
            read.assert_called_once()
            for wrong_root,wrong_day,wrong_cutoff,wrong_history in (
                (self.root,day,cutoff,history),(root,'20261006',cutoff,history),
                (root,day,'2020-01-01T00:00:00Z',history),(root,day,cutoff,'20200101')):
                with self.assertRaises(ValueError):
                    original._read_hk02_panel_witness(wrong_root,wrong_day,research_cutoff=wrong_cutoff,required_history_date=wrong_history)

    def test_old_worker_hook_unchanged(self):
        original=SimpleNamespace(_read_hk02_panel_witness='untouched')
        owner._install_repaired_witness(original,Path(self.old['input_root']),self.old)
        self.assertEqual(original._read_hk02_panel_witness,'untouched')

    def test_snapshot_runs_existing_witness_before_private_copy_commit(self):
        with patch.object(owner,'_repaired_witness',return_value={'verified':'SYNTHETIC'}) as witness:
            snapshot=owner.prepare_snapshot(self.request,self.root/'private')
        self.assertFalse(snapshot['owner_origin_verified'])
        self.assertFalse(snapshot['owner_read_lease_verified'])
        witness.assert_called_once()
        self.assertIn(self.request['paths']['panel_receipt'],snapshot['files'])

if __name__=='__main__':unittest.main()

"""Synthetic in-memory calculator tests. They do NOT exercise Parquet or owner."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import pandas as pd
from test_rebound_pytdx_window import ROOT,BASE,fixture,canonical,sha,rehash

class CalculatorWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from v5_shadow import rebound_pytdx_window as m, rebound_owner as owner
        cls.m=m;cls.owner=owner
        path=BASE/'vendor/rebound_supplement/workspace_plan.py'
        assert hashlib.sha256(path.read_bytes()).hexdigest()=='29c47c3836f0b26a9106626a990f03cae47c2ac22f2b4ca10be68c916c75f897'
        sys.path.insert(0,str(BASE/'vendor/rebound_baseline'))
        spec=importlib.util.spec_from_file_location('v4.manager_research.window_test_supplier',path)
        cls.original=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.original)
    def screen(self,records,members):
        signal,sessions,_=fixture()
        result=self.m.decode_window(records,members=members,signal_date=signal,sessions=sessions,research_cutoff='2026-10-13T10:00:00+00:00')
        frame=pd.DataFrame(result['rows'],columns=self.m.COLUMNS)
        master=dict(owner='EXACT_SIGNAL_MASTER',artifact_path='master.csv',artifact_sha256='c'*64,manifest_path='master.json',manifest_sha256='d'*64,names={c:dict(name=c) for c in members})
        witness=dict(owner='V5_INDEPENDENT_PYTDX_RESEARCH_WINDOW',panel_path='window.parquet',panel_sha256='a'*64,panel_manifest_path='manifest.json',panel_manifest_sha256='b'*64,source_contract=self.m.SOURCE_CONTRACT['name'],panel_rows=len(frame),panel_code_count=len(members))
        context=dict(market_session=signal,plan_trade_date='20261014',research_cutoff='2026-10-13T10:00:00+00:00')
        # Storage/calendar witnesses are synthetic seams; the actual pinned
        # screen function and all gate helpers run unmodified with pandas.
        with patch.object(self.original,'rebound_history_sessions',return_value=sessions),patch.object(self.original,'_read_hk02_panel_witness',return_value=(witness,[])),patch.object(self.original,'_screen_security_master_witness',return_value=(master,{})),patch.object(self.original,'_read_hk02_daily_supplement_witness',return_value=None),patch.object(pd,'read_parquet',return_value=frame):
            return self.original.read_rebound_screen(ROOT,context)
    def test_original_boundary_80percent_and_one_point_five_and_missing_pending(self):
        _,_,r=fixture();value=self.screen([r],['HK.00001','HK.00002'])
        self.assertTrue(value['main_screen_ready'],value)
        self.assertEqual([r['code'] for r in value['strict']],['HK.00001'])
        self.assertEqual(value['strict'][0]['volume_ratio_5d'],1.5)
        self.assertEqual(value['strict'][0]['oversold_cutoff_80pct_prior60_high'],8.0)
        self.assertEqual([r['code'] for r in value['pending']],['HK.00002'])
        self.assertEqual(value['coverage']['row_accounted_count'],2)
        self.assertIn('CURRENT_CLOSE_MISSING_OR_INVALID',value['pending'][0]['history_unknown_reasons'])
        self.assertIn('CURRENT_VOLUME_MISSING_OR_INVALID',value['pending'][0]['history_unknown_reasons'])
    def test_original_near_and_excluded_not_adapter_decisions(self):
        _,_,near=fixture();near['source_rows'][-1]['trade']=149;rehash(near)
        value=self.screen([near],['HK.00001']);self.assertEqual(len(value['near']),1)
        excluded=copy.deepcopy(near);excluded['source_rows'][-1]['close']=9;rehash(excluded)
        value=self.screen([excluded],['HK.00001']);self.assertEqual(len(value['excluded']),1)
        self.assertEqual(value['excluded'][0]['exclusion_reason_code'],'BOTH_REBOUND_GATES_FAILED')
        self.assertEqual(value['screen_unresolved'],[])
    def test_new_projection_does_not_retain_native_history_claims(self):
        _,_,r=fixture();legacy=self.screen([r],['HK.00001'])
        native=dict(source_contract=copy.deepcopy(self.m.SOURCE_CONTRACT))
        projected=self.owner.research_projection(legacy,native);row=projected['strict'][0]
        self.assertEqual(row['history_source'],'V5_INDEPENDENT_PYTDX_RESEARCH_WINDOW')
        self.assertEqual(row['history_adjustment'],'NOT_PROVEN')
        self.assertEqual(row['adjustment_consistency'],'NOT_PROVEN')
        self.assertEqual(row['connect_eligibility'],'UNVERIFIED')
        self.assertEqual(projected['authority']['price_basis'],'NOT_PROVEN')
        self.assertEqual(projected['status'],'CANNOT_CONFIRM')
        self.assertFalse(projected['main_screen_ready'])

if __name__=='__main__':unittest.main()

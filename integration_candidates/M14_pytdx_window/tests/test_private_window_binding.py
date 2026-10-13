"""Manifest/private reconstruction tests with synthetic in-memory Parquet seam."""
import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import pandas as pd
from test_rebound_pytdx_window import ROOT,BASE,fixture,canonical,sha

class PrivateWindowBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from v5_shadow import rebound_pytdx_window as m,rebound_owner as owner
        cls.m=m;cls.owner=owner
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT);self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.signal,self.sessions,self.record=fixture();prefix='assets/m14_pytdx_windows/runs/20261013/window1'
        self.paths=dict(panel_manifest=prefix+'/manifest.json',panel=prefix+'/window.parquet',
            master_manifest='assets/hk_security_master/runs/20261013/master1/manifest.json',
            master_artifact='assets/hk_security_master/runs/20261013/master1/artifact.csv',
            master_receipt='assets/hk_security_master/runs/20261013/master1/receipt.json',
            window_parent_manifest='assets/hk_0_2/panels/20261013-old/manifest.json',
            window_parent_panel='assets/hk_0_2/panels/20261013-old/hkconnect_vipdoc_daily_panel.parquet')
        self.files={}
        def write(relative,value):
            raw=value if isinstance(value,bytes) else canonical(value)
            p=self.root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);self.files[relative]=sha(raw)
            return raw
        self.write=write
        write(self.paths['window_parent_panel'],b'synthetic-original-parquet-seam')
        write(self.paths['panel'],b'synthetic-new-parquet-seam')
        write(self.paths['master_artifact'],b'synthetic-exact-day-master-seam')
        parent=dict(panel_max_date=self.signal,panel_relative=self.paths['window_parent_panel'].removeprefix('assets/hk_0_2/'),panel_sha256=self.files[self.paths['window_parent_panel']],manifest_prepared_at='2026-10-13T08:00:00+00:00')
        write(self.paths['window_parent_manifest'],parent)
        master=dict(trade_date=self.signal,artifact_relative=self.paths['master_artifact'].removeprefix('assets/hk_security_master/'),artifact_sha256=self.files[self.paths['master_artifact']],run_id='master1',captured_at='2026-10-13T08:00:00+00:00')
        write(self.paths['master_manifest'],master)
        write(self.paths['master_receipt'],dict(trade_date=self.signal,artifact_sha256=master['artifact_sha256'],manifest_sha256=sha(canonical(master)),run_id='master1',status='READY'))
        self.record.update(target_date='20261014',signal_date=self.signal,expected_panel_sha256=self.files[self.paths['window_parent_panel']],
            parent_binding=dict(parent_panel_relative=parent['panel_relative'],parent_panel_sha256=parent['panel_sha256'],
                parent_manifest_relative=self.paths['window_parent_manifest'].removeprefix('assets/hk_0_2/'),parent_manifest_sha256=self.files[self.paths['window_parent_manifest']]))
        self.record['original_reference']=dict(run_id='0'*32,artifact_sha256='c'*64,manifest_sha256='d'*64,receipt_sha256='e'*64)
        self.record['parent_binding']['parent_pointer_sha256']='f'*64
        records=[]
        for i,blob in enumerate(self.m.pack_records([self.record])):
            relative=prefix+f'/records-{i:03d}.json';write(relative,blob);records.append(dict(relative=relative,sha256=sha(blob),bytes=len(blob)))
        self.request=dict(schema_version=self.m.REQUEST_SCHEMA,target_date='20261014',signal_date=self.signal,
            research_cutoff='2026-10-13T10:00:00+00:00',input_root=str(self.root),data_kind='SYNTHETIC',paths=self.paths,files=self.files)
        self.decoded=self.m.decode_window([self.record],members=['HK.00001','HK.00002'],signal_date=self.signal,sessions=self.sessions,research_cutoff=self.request['research_cutoff'])
        self.frame=pd.DataFrame(self.decoded['rows'],columns=self.m.COLUMNS)
        self.parent_frame=pd.DataFrame([dict(trade_date_compact=self.signal,code_norm=c) for c in self.decoded['members']])
        self.manifest=dict(schema_version=self.m.MANIFEST_SCHEMA,asset_schema_version=self.m.ASSET_SCHEMA,
            source_contract=copy.deepcopy(self.m.SOURCE_CONTRACT),target_date='20261014',signal_date=self.signal,research_cutoff=self.request['research_cutoff'],
            panel_relative=self.paths['panel'],panel_sha256=self.files[self.paths['panel']],panel_rows=len(self.frame),panel_code_count=2,
            members=self.decoded['members'],members_sha256=self.decoded['members_sha256'],sessions=self.sessions,records=records,
            capture_started_at=self.decoded['capture_started_at'],capture_finished_at=self.decoded['capture_finished_at'],
            manifest_prepared_at='2026-10-13T09:59:00+00:00',parent_panel_sha256=parent['panel_sha256'],
            parent_manifest_sha256=self.files[self.paths['window_parent_manifest']],row_projection_sha256=sha(canonical(self.decoded['rows'])),pending_reasons=self.decoded['pending_reasons'],**self.m.SAFETY)
        self.manifest['capture_audit']=dict(schema_version='v5.rebound_pytdx_batch_audit_binding.v1',status='PINNED_BATCH_READONLY_AUDIT_AT_PREPARATION',batch_helper_sha256='4d51d842839d38abd906e4294ff801a9e4d38824dd0b899e62c1f12f58e804dd',plan_sha256='1'*64,context_file_sha256='2'*64,run_id='3'*32,checkpoint_sha256='4'*64,original_reference=self.record['original_reference'],parent_binding=self.record['parent_binding'],audited_at='2026-10-13T09:30:00+00:00',receipts=[dict(code=self.record['code'],relative='receipt-'+self.record['code']+'.json',sha256=sha(canonical(self.record)))],pending_codes=[],uncertain_codes=[],failed_codes=[])
        self.sync()
        self.original=types.SimpleNamespace(rebound_history_sessions=lambda _:self.sessions)
    def sync(self):self.write(self.paths['panel_manifest'],self.manifest)
    def bind(self):
        def read(path,columns):
            frame=self.parent_frame if Path(path).name=='hkconnect_vipdoc_daily_panel.parquet' else self.frame
            return frame[list(columns)].copy()
        with patch.object(pd,'read_parquet',side_effect=read):return self.m.bind_private_window(self.root,self.request,self.original)
    def test_exact_manifest_and_private_reconstruction(self):
        witness,native=self.bind();self.assertEqual(witness['owner'],'V5_INDEPENDENT_PYTDX_RESEARCH_WINDOW')
        self.assertEqual(native['original_member_count'],2);self.assertIsNone(witness['price_currency'])
    def test_reject_fake_old_contract_or_missing_shard_or_member_filter(self):
        self.manifest['source_contract']['name']='tdx_vipdoc_71_day+verified_zero_trade_repairs';self.sync()
        with self.assertRaisesRegex(ValueError,'MANIFEST_CONTRACT'):self.bind()
        self.manifest['source_contract']=copy.deepcopy(self.m.SOURCE_CONTRACT);self.sync()
        self.parent_frame=self.parent_frame.iloc[:1]
        with self.assertRaisesRegex(ValueError,'MEMBER_SET'):self.bind()
    def test_reject_value_scale_or_null_row_drop(self):
        self.frame.loc[self.frame['code_norm']=='HK.00001','trade']*=100
        with self.assertRaisesRegex(ValueError,'RECONSTRUCTION'):self.bind()
        self.frame=pd.DataFrame(self.decoded['rows'],columns=self.m.COLUMNS).iloc[:-1]
        with self.assertRaisesRegex(ValueError,'RECONSTRUCTION'):self.bind()
    def test_reject_calendar_substitution_even_when_manifest_self_consistent(self):
        self.original.rebound_history_sessions=lambda _:dict(self.sessions,calendar_sha256='c'*64)
        with self.assertRaisesRegex(ValueError,'CALENDAR'):self.bind()
    def test_reject_capture_parent_binding_change(self):
        self.record['expected_panel_sha256']='f'*64
        blob=self.m.pack_records([self.record])[0];ref=self.manifest['records'][0]
        self.write(ref['relative'],blob);ref.update(sha256=sha(blob),bytes=len(blob));self.manifest['capture_audit']['receipts'][0]['sha256']=sha(canonical(self.record));self.sync()
        with self.assertRaisesRegex(ValueError,'CAPTURE_PARENT_BINDING'):self.bind()
    def test_snapshot_new_routes_and_file_count(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as enclosing, patch.object(self.owner,'BASE',BASE):
            snapshot=self.owner.prepare_snapshot(self.request,Path(enclosing)/'private-destination')
        self.assertEqual(len(snapshot['files']),10)
        self.assertIn('assets/m14_pytdx_windows/latest.json',snapshot['files'])
        self.assertNotIn('assets/hk_0_2/panel_latest.json',snapshot['files'])

if __name__=='__main__':unittest.main()

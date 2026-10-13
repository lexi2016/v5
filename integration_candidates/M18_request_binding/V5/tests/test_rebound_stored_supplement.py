"""Actual frozen reader/consumer tests using synthetic fixtures only."""
import ast,copy,hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from v5_shadow import rebound_owner as owner
from v5_shadow.digests import canonical_bytes
BASE=Path(__file__).resolve().parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
FIXTURE='''
import importlib,json,sys
from pathlib import Path
from v5_shadow import rebound_owner as owner
from fixtures.stored_supplement_factory import build
sys.meta_path.insert(0,owner._Loader(owner._sources(stored_supplement=True),stored_supplement=True))
p=importlib.import_module('v4.manager_research.workspace_plan')
r=importlib.import_module('v3_shared_data.shared_data.hk_daily_supplement')
assert Path(p.__file__)==owner.BASE/'vendor/rebound_supplement/workspace_plan.py'
assert Path(r.__file__)==owner.BASE/'vendor/rebound_repair_baseline/hk_daily_supplement.py'
print(json.dumps(build(Path(sys.argv[1]),p,r)))
'''
class StoredSupplement(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.source=self.root/'input';self.source.mkdir()
        self.env=dict(os.environ,PYTHONPATH=os.pathsep.join((str(BASE/'src'),str(BASE/'tests'))),PYTHONDONTWRITEBYTECODE='1')
        r=subprocess.run([sys.executable,'-B','-c',FIXTURE,str(self.source)],env=self.env,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);paths=json.loads(r.stdout)
        self.request=dict(schema_version='v5.rebound_owner_request.v1',target_date='20261008',signal_date='20261007',research_cutoff='2026-10-07T11:00:00+00:00',data_kind='SYNTHETIC',input_root=str(self.source),paths=paths,files={})
        self.refresh();self.index=0
    def path(self,role):return self.source/self.request['paths'][role]
    def load(self,role):return json.loads(self.path(role).read_bytes())
    def write(self,role,obj):self.path(role).write_bytes(canonical_bytes(obj))
    def refresh(self):self.request['files']={p:sha((self.source/p).read_bytes()) for p in self.request['paths'].values()}
    def rehash(self):
        m=self.load('supplement_manifest');p=self.load('supplement_pointer')
        m['raw_capture_sha256']=sha(self.path('supplement_capture').read_bytes());self.write('supplement_manifest',m)
        p.update(raw_capture_sha256=m['raw_capture_sha256'],manifest_sha256=sha(self.path('supplement_manifest').read_bytes()));self.write('supplement_pointer',p);self.refresh()
    def run_owner(self):
        self.index+=1;output=self.root/f'output-{self.index}';output.mkdir();(output/'.v5-rebound-owner-root').write_bytes(owner.MARKER)
        before={p:sha((self.source/p).read_bytes()) for p in self.request['files']}
        result=owner.run_rebound_owner(self.request,output)
        script="import json,sys;from v5_shadow.rebound_owner import read_rebound_owner;print(json.dumps(read_rebound_owner(sys.argv[1],json.loads(sys.argv[2])),sort_keys=True))"
        cold=subprocess.run([sys.executable,'-B','-c',script,str(output),json.dumps(result['reference'])],env=self.env,capture_output=True,text=True)
        self.assertEqual(cold.returncode,0,cold.stderr);self.assertEqual(json.loads(cold.stdout),result['readback'])
        self.assertEqual(before,{p:sha((self.source/p).read_bytes()) for p in before})
        a=result['readback'];self.assertEqual(a['formal_status'],'CANNOT_CONFIRM');self.assertFalse(a['formal_eligibility_verified']);self.assertFalse(a['natural_verified'])
        manager=owner.manager_projection(a,target_date='20261008',market_session='20261007',research_cutoff=datetime.now(timezone.utc).isoformat())
        self.assertIsNone(manager['eligible_screen']);self.assertIsNone(manager['research_observation'])
        self.assertIn('REBOUND_MANAGER_SYNTHETIC_NOT_ADMITTED',manager['reason_codes'])
        return a
    def test_missing_history_is_filled_with_preserved_gates_and_cold_readback(self):
        a=self.run_owner();self.assertIn(a['computation_status'],('READY','READY_WITH_GAPS'),a['reason_codes'])
        p=a['research_observation'];self.assertEqual([p['coverage'][k] for k in ('strict_count','near_count','excluded_count','history_pending_count')],[1,2,1,0])
        self.assertFalse(p['main_screen_ready']);self.assertTrue(set(owner.BLOCKERS).issubset(p['gaps']))
        for role,key in [('supplement_pointer','pointer_sha256'),('supplement_manifest','manifest_sha256'),('supplement_capture','raw_capture_sha256')]:
            self.assertEqual(p['authority']['daily_supplement'][key],self.request['files'][self.request['paths'][role]])
        rows=p['strict']+p['near']+p['excluded'];self.assertEqual(len(rows),4)
        for row in rows:
            self.assertEqual(row['volume_source'],'PYTDX_EXHQ_CATEGORY_4_MARKET_71');self.assertEqual(row['volume_unit_status'],'NOT_PROVEN')
            self.assertTrue(row['history_source'].endswith('_PLUS_PYTDX_CATEGORY4_SUPPLEMENT'))
            self.assertEqual(row['source_refs'][-1]['artifact_sha256'],self.request['files'][self.request['paths']['supplement_capture']])
            self.assertIsNone(row['previous20_mean_volume_background']);self.assertEqual(row['previous5_mean_volume'],100.)
        self.assertEqual(p['strict'][0]['close'],7.) # supplement target close 9 cannot overwrite panel 7
    def test_without_supplement_preserves_missing_history_pending(self):
        for role in owner.SUPPLEMENT_ROLES:self.request['paths'].pop(role)
        self.refresh();a=self.run_owner();self.assertEqual(a['research_observation']['coverage']['history_pending_count'],4)
        self.assertNotIn('daily_supplement',a['research_observation']['authority'])
    def test_all_three_roles_and_only_three_files_are_required(self):
        original=copy.deepcopy(self.request)
        for role in owner.SUPPLEMENT_ROLES:
            with self.subTest(role=role):
                self.request=copy.deepcopy(original);self.request['paths'].pop(role)
                with self.assertRaises(ValueError):owner._request(self.request)
        self.request=copy.deepcopy(original)
        extra='assets/hk_0_2/daily_supplements/runs/20261007/extra/manifest.json';self.request['files'][extra]='0'*64
        with self.assertRaisesRegex(ValueError,'EXACT_FILE_SET'):owner._request(self.request)
    def test_cross_run_pointer_and_changed_bytes_reject_before_worker(self):
        p=self.load('supplement_pointer');p['manifest_relative']=p['manifest_relative'].replace('synthetic-stored','other')
        self.write('supplement_pointer',p);self.refresh()
        with self.assertRaisesRegex(ValueError,'POINTER_BINDING'):owner.prepare_snapshot(self.request,self.root/'private')
        self.path('supplement_capture').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'INPUT_SHA_MISMATCH'):owner.prepare_snapshot(self.request,self.root/'private2')
    def test_reader_pit_identity_universe_and_normalized_rows_fail_closed(self):
        original={role:self.path(role).read_bytes() for role in owner.SUPPLEMENT_ROLES}
        cases=[('supplement_pointer','published_at','2026-10-07T12:00:00+00:00','POINTER_AFTER_CUTOFF'),
            ('supplement_manifest','selected_codes',[], 'UNIVERSE_MISMATCH'),
            ('supplement_manifest','capture_started_at','2026-10-07T09:00:00+00:00','PREPARED_AFTER_CUTOFF')]
        for role,key,value,reason in cases:
            with self.subTest(reason=reason):
                for r,raw in original.items():self.path(r).write_bytes(raw)
                d=self.load(role);d[key]=value;self.write(role,d);self.rehash()
                a=self.run_owner();self.assertEqual(a['computation_status'],'CANNOT_CONFIRM');self.assertTrue(any('HK_DAILY_SUPPLEMENT_'+reason in g for g in a['reason_codes']),a['reason_codes'])
        for r,raw in original.items():self.path(r).write_bytes(raw)
        p=self.load('supplement_pointer');p['panel_identity']['manifest_prepared_at']='2026-10-07T09:00:00+00:00';self.write('supplement_pointer',p);self.refresh()
        a=self.run_owner();self.assertTrue(any('POINTER_IDENTITY_INVALID' in g for g in a['reason_codes']),a['reason_codes'])
        for r,raw in original.items():self.path(r).write_bytes(raw)
        c=self.load('supplement_capture');c['records'][0]['bars'][0]['trade']=999.;self.write('supplement_capture',c);self.rehash()
        a=self.run_owner();self.assertTrue(any('NORMALIZED_ROWS_MISMATCH' in g for g in a['reason_codes']),a['reason_codes'])
    def test_partial_six_bar_set_never_mixes_panel_and_supplement_volume(self):
        c=self.load('supplement_capture');r=c['records'][0]
        r['source_rows'].pop();r['bars'].pop();r.update(status='PENDING',missing_sessions=['20261007'],returned_count=5,response_sha256=sha(canonical_bytes(r['source_rows'])))
        self.write('supplement_capture',c)
        m=self.load('supplement_manifest');m.update(status='PARTIAL_WITH_PENDING',record_status_counts={'PENDING':1,'READY':3});self.write('supplement_manifest',m);self.rehash()
        a=self.run_owner();p=a['research_observation'];self.assertIsNotNone(p,a['reason_codes'])
        self.assertEqual([r['code'] for r in p['pending']],['HK.00001'])
        self.assertIsNone(p['pending'][0]['volume_ratio_5d']);self.assertEqual(p['pending'][0]['volume_source'],'V4_SHARED_HK_0_2_PANEL_AUTHORITY')
    def test_frozen_source_closure_and_original_observation_spans(self):
        from v5_shadow import rebound_observation as observation
        descriptor,sources=observation._capsule()
        self.assertEqual(sha(sources['v4/manager_research/workspace_plan.py']),'be0d5e69ff72efd07d2caca4e68948245db4900a8c41f467e9c30f6899c044b1')
        overlay=owner._sources(stored_supplement=True)
        self.assertEqual(len(overlay),19);self.assertNotEqual(overlay['v4/manager_research/workspace_plan.py'],sources['v4/manager_research/workspace_plan.py'])
        self.assertEqual(sha(overlay['v3_shared_data/shared_data/hk_daily_supplement.py']),'fa7dcbce4ee026b0a02c47220820d0407af183553d3304afcc5db425dce33cbd')
        def functions(raw):
            return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
        before=functions(sources['v4/manager_research/workspace_plan.py'])
        after=functions(overlay['v4/manager_research/workspace_plan.py'])
        self.assertEqual(set(after)-set(before),{'_read_hk02_daily_supplement_witness'})
        self.assertEqual([k for k in before if before[k]!=after[k]],['read_rebound_screen'])
        # The new consumer retains the exact F gate assignments and constants.
        def gates(raw):
            return {n.targets[0].id:ast.dump(n.value,include_attributes=False) for n in ast.walk(ast.parse(raw))
                if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)
                and n.targets[0].id in {'oversold','volume_flag','history_status','strict','near_eligible','_REBOUND_OVERSOLD_RATIO','_REBOUND_VOLUME_GATE'}}
        self.assertEqual(gates(sources['v4/manager_research/workspace_plan.py']),gates(overlay['v4/manager_research/workspace_plan.py']))
if __name__=='__main__':unittest.main()

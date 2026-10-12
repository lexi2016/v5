"""M08 engineering fixtures; dates/values are synthetic, never market evidence."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from v5_shadow.digests import sha256_json

DATE='20261008'
SIGNAL='20261007'
STAGE='STAGE_0930_0935'

def request(stage=STAGE, count=12):
    times={'STAGE_0925':'09:20:00','STAGE_0930_0935':'09:35:00','STAGE_0935_0940':'09:40:00','STAGE_0940_0945':'09:45:00','STAGE_0945_1030':'10:30:00','STAGE_1300_1315':'13:15:00','STAGE_1445_1500':'15:00:00','STAGE_1545_1555':'15:55:00'}
    captured='2026-10-08T'+times[stage]+'+08:00'
    pool=[dict(code=f'HK.{i:05}',rank=i,score_prob_active=1-i/1000,target_date=DATE,signal_date=SIGNAL,preselect_lane='D1_MODEL_TOP100') for i in range(1,101)]
    rows=[dict(code=f'HK.{i:05}',trade_date=DATE,target_date=DATE,signal_date=SIGNAL,stage_id=stage,captured_at=captured,update_time=captured,
        open_price=10,last_price=11,high_price=11,low_price=10,pct_chg=10,volume_ratio=2,turnover_hkd=100000000,circular_market_cap_hkd_yi=20,
        candidate_lanes=['D1_MODEL_TOP100'],rank=i,auction_score=100-i,reference_price_hkd=11,ask_price=11.1,bid_price=10.9,strict_failure_price_hkd=10.5,
        second_filter_status='WATCH_ONLY',preselect_lane='D1_MODEL_TOP100') for i in range(1,count+1)]
    payload=dict(rows=rows)
    source=dict(collector_id='SYNTHETIC_FIXTURE',source_date=DATE,captured_at=captured,available_at=captured,
        status='READY' if rows else 'READY_EMPTY',requested_rows=count,missing_symbols=[],cannot_confirm=[],source_evidence=['fixture_only=true'])
    out=dict(schema_version='v5.hk_stage_input.v1',market='HK_CONNECT',target_date=DATE,signal_date=SIGNAL,stage_id=stage,data_kind='SYNTHETIC',
        source=source,m06=dict(target_date=DATE,signal_date=SIGNAL,run_id='SYNTHETIC_M06',rows=pool,rows_sha256=sha256_json(pool)),
        m02=dict(membership_date=DATE,source_date=DATE,status='SYNTHETIC',codes=[r['code'] for r in pool],receipt_sha256='a'*64,
            units=dict(price='HKD',turnover='HKD',market_cap='HKD_100M',change='PERCENT',volume_ratio='RATIO')),
        route='SECOND_FILTER' if stage=='STAGE_0925' else ('STAGE8_RTDATA' if stage=='STAGE_1545_1555' else 'FOUR_LANE'),payload=payload,payload_sha256=sha256_json(payload))
    source['source_sha256']=out['payload_sha256']
    return out

def rehash(r):
    r['payload_sha256']=sha256_json(r['payload']);r['source']['source_sha256']=r['payload_sha256']
    r['m06']['rows_sha256']=sha256_json(r['m06']['rows'])
    return r

class HKDailyTests(unittest.TestCase):
    def test_00_default_chain_exists(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.hk_stage_daily'),'M08 default producer missing')
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.hk_stage_reader'),'M08 independent reader missing')


class HKChainTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'m08'
    def tearDown(self):self.temp.cleanup()
    def run_request(self,r):
        from v5_shadow.hk_stage_daily import init_hk_root,run_hk_stage
        if not self.root.exists():init_hk_root(self.root)
        return run_hk_stage(r,self.root)
    def test_four_lane_store_and_cold_reader(self):
        from v5_shadow.hk_stage_reader import read_hk_stage
        r=request();out=self.run_request(r);read=read_hk_stage(self.root,out['reference'])
        self.assertEqual(out['artifact'],read['artifact']);self.assertEqual(len(read['artifact']['rows']),10)
        self.assertEqual([v['score'] for v in read['artifact']['rows']],[89]*10)
        self.assertFalse(read['natural_verified']);self.assertFalse(read['provenance']['formal_admission'])
        self.assertEqual(read['artifact']['market'],'HK_CONNECT')
    def test_original_score_order_and_reasons(self):
        r=request();r['payload']['rows'][-1]['volume_ratio']=3
        out=self.run_request(rehash(r));a=out['artifact']
        self.assertEqual(a['rows'][0]['code'],'HK.00012');self.assertEqual(a['rows'][0]['score'],93)
        self.assertIn('D1_MODEL_TOP100',a['rows'][0]['lane_evidence'])
        detail=out['provenance']['owner_score_details']['HK.00012']
        self.assertEqual(detail['score'],93)
        self.assertIn('量比3.00',detail['reasons'])
    def test_auction_preserves_second_filter_order(self):
        r=request('STAGE_0925');r['payload']['rows'].reverse()
        a=self.run_request(rehash(r))['artifact']
        self.assertEqual(a['rows'][0]['code'],'HK.00012')
        self.assertEqual(a['rows'][0]['source_mode'],'HK_CONNECT_AUCTION_SECOND_FILTER_STAGE_0925')
    def test_auction_reference_never_promoted(self):
        r=request('STAGE_0925');r['route']='D1_REFERENCE';r['payload']['rows']=r['m06']['rows'][:12]
        a=self.run_request(rehash(r))['artifact']
        self.assertEqual(a['selection_status'],'CANNOT_CONFIRM')
        self.assertTrue(all(v['source_mode']=='HK_CONNECT_D1_PRESELECT_REFERENCE' for v in a['rows']))
    def test_empty_and_missing_are_distinct(self):
        r=request(count=0);a=self.run_request(r)['artifact'];self.assertEqual(a['selection_status'],'READY_EMPTY')
        r['source'].update(status='CANNOT_CONFIRM',cannot_confirm=['SOURCE_MISSING'])
        a=self.run_request(r)['artifact'];self.assertEqual(a['selection_status'],'CANNOT_CONFIRM')
    def test_partial_preserves_rows_and_diagnostics(self):
        r=request();r['source'].update(status='PARTIAL_WITH_ROWS',requested_rows=15,missing_symbols=['HK.00013'],cannot_confirm=['LANE_MISSING'])
        a=self.run_request(r)['artifact'];self.assertEqual(a['selection_status'],'PARTIAL_WITH_ROWS')
        self.assertEqual(a['selected_rows'],10);self.assertIn('LANE_MISSING',a['cannot_confirm'])
    def test_exact_retry_reuses_without_rewrite(self):
        r=request();a=self.run_request(r);before={str(p):p.stat().st_mtime_ns for p in self.root.rglob('*') if p.is_file()}
        b=self.run_request(r);self.assertTrue(b['reused']);self.assertEqual(a['reference'],b['reference'])
        self.assertEqual(before,{str(p):p.stat().st_mtime_ns for p in self.root.rglob('*') if p.is_file()})
    def test_changed_input_gets_new_run(self):
        r=request();a=self.run_request(r);r['payload']['rows'][0]['volume_ratio']=3
        b=self.run_request(rehash(r));self.assertNotEqual(a['reference']['run_id'],b['reference']['run_id'])
    def test_reader_ignores_latest_pointer(self):
        from v5_shadow.hk_stage_reader import read_hk_stage
        a=self.run_request(request());(self.root/'latest_success.json').write_text('{}')
        self.assertEqual(read_hk_stage(self.root,a['reference'])['artifact'],a['artifact'])
    def test_tamper_is_rejected(self):
        from v5_shadow.hk_stage_reader import read_hk_stage
        a=self.run_request(request());p=next(self.root.rglob('artifact.csv'));p.write_text('bad')
        with self.assertRaises(ValueError):read_hk_stage(self.root,a['reference'])
    def test_input_rejections(self):
        cases=[('digest',lambda r:r.update(payload_sha256='0'*64)),
          ('target',lambda r:r['m06'].update(target_date='20261009')),
          ('signal',lambda r:r['m06'].update(signal_date=DATE)),
          ('qualification_date',lambda r:r['m02'].update(membership_date='20261007')),
          ('mixed_market',lambda r:r['payload']['rows'][0].update(code='A.000001')),
          ('negative_cap',lambda r:r['payload']['rows'][0].update(platform_circular_market_cap_hkd_yi=-1)),
          ('raw_score',lambda r:r['payload']['rows'][0].update(stage_score=999)),
          ('missing_quote',lambda r:r['payload']['rows'][0].pop('volume_ratio')),
          ('future_capture',lambda r:r['payload']['rows'][0].update(captured_at='2026-10-08T09:36:00+08:00')),
          ('units',lambda r:r['m02']['units'].update(turnover='USD')),
          ('lanes',lambda r:r['payload']['rows'][0].update(candidate_lanes=[])),
          ('duplicate',lambda r:r['payload']['rows'].append(copy.deepcopy(r['payload']['rows'][0])))]
        for name,mutate in cases:
            with self.subTest(name=name):
                r=request();mutate(r)
                if name!='digest':rehash(r)
                with self.assertRaises(ValueError):self.run_request(r)
    def test_unknown_membership_is_observation_only(self):
        r=request();r['m02']['status']='UNKNOWN';a=self.run_request(r)['artifact']
        self.assertEqual(a['selection_status'],'PARTIAL_WITH_ROWS')
        self.assertIn('M02_MEMBERSHIP_NOT_VERIFIED',a['cannot_confirm'])
    def test_live_input_not_silently_admitted(self):
        r=request();r['data_kind']='LIVE'
        with self.assertRaisesRegex(ValueError,'NATURAL_ADMISSION_NOT_BOUND'):self.run_request(r)

def stage8_request():
    r=request('STAGE_1545_1555',3)
    rows=[dict(code=f'HK.{i:05}',prev_close_price=10,last_price=11 if i<=3 else 9,turnover=50000000,volume_ratio=2,update_time='2026-10-08T15:52:00+08:00') for i in range(1,101)]
    snap=dict(schema_version='stage_center.hk_active_snapshot.v1',trade_date=DATE,stage_id='STAGE_1545_1555',market='HK_CONNECT',source_role='FUTU_HKCONNECT_FULL_SCAN',
        codes=r['m02']['codes'],codes_sha256=sha256_json(r['m02']['codes']),requested_rows=100,returned_rows=100,full_coverage=True,rows=rows,snapshot_sha256=sha256_json(rows),
        captured_at='2026-10-08T15:52:00+08:00',cutoff_at='2026-10-08T15:55:00',temporal_cutoff_safe=True,production_allowed=False,buy_gate_updated=False,orders_sent=False)
    ticks=[dict(code=f'HK.{i:05}',time='2026-10-08T'+t+'+08:00',cur_price=p,high=p,low=p,turnover=50000000,volume=1000000) for i in range(1,4) for t,p in [('15:45:00',10),('15:55:00',11)]]
    r['payload']=dict(snapshot=snap,rtdata=dict(rows=ticks,errors=[],cleanup_warnings=[],missing_codes=[],batch_evidence=['fixture_only=true']),enrichment=[dict(code=f'HK.{i:05}',circular_market_cap_hkd_yi=20) for i in range(1,4)])
    return rehash(r)

class HKExtendedTests(unittest.TestCase):
    setUp=HKChainTests.setUp
    tearDown=HKChainTests.tearDown
    run_request=HKChainTests.run_request
    def test_stage8_original_snapshot_rtdata_store_reader(self):
        out=self.run_request(stage8_request());a=out['artifact']
        self.assertEqual(a['stage_id'],'STAGE_1545_1555');self.assertEqual(a['selected_rows'],3)
        self.assertTrue(any('route=hk_connect_stage8_natural_rtd_data'==v for v in a['source_evidence']))
        self.assertTrue(any('owner_execution=RETAINED_INPUT_ENGINEERING_REPLAY'==v for v in a['source_evidence']))
        self.assertEqual(a['rows'][0]['score'],100)
        self.assertFalse(out['natural_verified'])
    def test_stage8_tamper_and_missing_enrichment_fail(self):
        for mutate in (lambda r:r['payload']['snapshot'].update(snapshot_sha256='0'*64),lambda r:r['payload']['enrichment'].pop(),lambda r:r['payload']['rtdata']['rows'][0].update(time='2026-10-08T15:56:00+08:00')):
            with self.subTest(mutate=mutate):
                r=stage8_request();mutate(r)
                with self.assertRaises(ValueError):self.run_request(rehash(r))
    def test_failure_preserves_previous_success(self):
        good=self.run_request(stage8_request());latest=(self.root/'latest_success.json').read_bytes()
        r=stage8_request();r['payload']['snapshot']['snapshot_sha256']='0'*64
        with self.assertRaises(ValueError):self.run_request(rehash(r))
        self.assertEqual(latest,(self.root/'latest_success.json').read_bytes())
        from v5_shadow.hk_stage_reader import read_hk_stage
        self.assertEqual(good['artifact'],read_hk_stage(self.root,good['reference'])['artifact'])
    def test_cross_lane_merge_uses_original_precedence(self):
        r=request(count=1);extra=copy.deepcopy(r['payload']['rows'][0]);extra['candidate_lanes']=['OLD_DEMON_MEMORY'];extra['last_price']=10.5
        r['payload']['rows'].append(extra)
        a=self.run_request(rehash(r))['artifact'];self.assertEqual(a['selected_rows'],1)
        self.assertEqual(a['rows'][0]['last_price'],11)
        self.assertIn('OLD_DEMON_MEMORY',a['rows'][0]['candidate_lanes'])
    def test_half_day_blocked_before_normal_windows(self):
        r=request();r['target_date']='20261224'
        with self.assertRaisesRegex(ValueError,'HALF_DAY_WINDOW_CONTRACT_UNVERIFIED'):self.run_request(r)
    def test_m10_exactly_seven_excludes_stage8(self):
        from v5_shadow.hk_stage_daily import STAGES
        from v5_shadow.hk_stage_reader import read_m10_seven
        refs=[self.run_request(request(s,1))['reference'] for s in STAGES[:7]]
        out=read_m10_seven(self.root,refs,DATE);self.assertEqual(len(out['stages']),7);self.assertFalse(out['stage8_included'])
        with self.assertRaises(ValueError):read_m10_seven(self.root,refs[1:],DATE)
        with self.assertRaises(ValueError):read_m10_seven(self.root,refs+[self.run_request(stage8_request())['reference']],DATE)

    def test_auction_source_failure_without_reason_never_becomes_empty(self):
        r=request('STAGE_0925',0);r['source']['status']='CANNOT_CONFIRM'
        self.assertEqual(self.run_request(r)['artifact']['selection_status'],'CANNOT_CONFIRM')
    def test_auction_partial_source_without_reason_not_promoted(self):
        r=request('STAGE_0925',1);r['source']['status']='PARTIAL_WITH_ROWS'
        self.assertEqual(self.run_request(r)['artifact']['selection_status'],'PARTIAL_WITH_ROWS')


    def test_reader_rejects_rebound_metadata_even_with_new_self_hash(self):
        from v5_shadow.hk_stage_reader import read_hk_stage
        out=self.run_request(request());ref=copy.deepcopy(out['reference'])
        folder=self.root/'generations'/ref['generation_sha256']
        product=json.loads((folder/'product.json').read_text());attempt=json.loads((folder/'attempt.json').read_text())
        product['provenance']['source_identity']['captured_at']='2030-01-01T00:00:00+08:00'
        product['reference'].pop('product_sha256');ref['product_sha256']=sha256_json(product)
        product['reference']=ref;attempt['reference']=ref
        (folder/'product.json').write_text(json.dumps(product));(folder/'attempt.json').write_text(json.dumps(attempt))
        with self.assertRaisesRegex(ValueError,'PROVENANCE_REQUEST_BINDING'):read_hk_stage(self.root,ref)
    def test_final_source_failure_never_advances_success(self):
        import subprocess,sys
        self.run_request(request());before=(self.root/'latest_success.json').read_bytes()
        r=request();r['payload']['rows'][0]['volume_ratio']=3;rehash(r)
        script="import sys,json;sys.path.insert(0,sys.argv[1]);from v5_shadow import hk_stage_daily as d;v=json.load(sys.stdin);d.source_bytes=lambda:(_ for _ in ()).throw(ValueError('TEST_SOURCE_CHANGED'));d._worker(v['request'],v['root'])"
        result=subprocess.run([sys.executable,'-I','-B','-c',script,str(Path(__file__).resolve().parents[1]/'src')],input=json.dumps(dict(request=r,root=str(self.root))),text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('TEST_SOURCE_CHANGED',result.stderr)
        self.assertEqual(before,(self.root/'latest_success.json').read_bytes())
        self.assertTrue(any(json.loads(p.read_text())['status']=='FAILED' for p in self.root.rglob('attempt.json')))

if __name__=='__main__':unittest.main()

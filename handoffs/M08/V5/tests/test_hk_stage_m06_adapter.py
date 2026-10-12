"""Synthetic contract fixtures shaped like the original M06 cold-reader result.

These are not real pool data, qualification evidence, or a natural-stage run.
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from v5_shadow.digests import sha256_json
from test_hk_stage_daily import request, rehash


def mapped_result():
    reference=dict(role='HK_CONNECT_D1_TOP100_0_2',run_id='SYNTHETIC_M06_NATIVE',
        artifact_sha256='a'*64,manifest_sha256='b'*64,receipt_sha256='c'*64,
        artifact_relative='SYNTHETIC_ONLY/pool.csv')
    safety=dict(production_allowed=False,buy_gate_updated=False,orders_sent=False)
    rows=[dict(code=f'{i:05}',code_norm=f'{i:05}',symbol=f'HK.{i:05}',market='HK',
        pool_id='hkconnect_d1_top100',rank=str(i),pool_rank=i,
        score_prob_active=str(1-i/1000),pool_score=1-i/1000,
        target_date='20261008',signal_date='20261007',selected_strategy='prob_active',
        d1_freshness_status='PASS',recommendation_status='WATCH_ONLY',**safety)
        for i in range(1,101)]
    artifact=dict(schema_version='v3_5.preselection_pool.v1',market='HK',
        pool_id='hkconnect_d1_top100',trade_date='20261008',target_date='20261008',
        signal_date='20261007',status='STRICT_0_2_READY',source_role='SHARED_VERIFIED_HK_0_2',
        producer_id='v3_shared_hk_0_2_consumer_v1',stage_selection_eligible=True,
        source_run_id=reference['run_id'],source_sha256=reference['artifact_sha256'],
        source_manifest_sha256=reference['manifest_sha256'],source_receipt_sha256=reference['receipt_sha256'],
        source_path=reference['artifact_relative'],source_row_count=100,rows=rows,**safety)
    result=dict(status='ASSEMBLED',data_kind='VERIFIED_SOURCE_SNAPSHOT',
        model_weights_reverified=False,target_date='20261008',signal_date='20261007',
        eligibility_source_date='20261007',research_cutoff='2026-10-07T18:00:00+08:00',
        verified_source_reference=reference,artifact=artifact,fixture_only=True,
        source_verification=dict(status='READY',row_count=100,**{k:v for k,v in reference.items() if k!='role'}),**safety)
    return result,copy.deepcopy(reference)


def unbound_request(stage='STAGE_0930_0935'):
    r=request(stage);r.pop('m06');return r


class M06AdapterTests(unittest.TestCase):
    def bind(self,r=None,result=None,reference=None):
        from v5_shadow.hk_stage_m06 import bind_m06_verified_result
        default_result,default_reference=mapped_result()
        return bind_m06_verified_result(unbound_request() if r is None else r,
            default_result if result is None else result,
            default_reference if reference is None else reference)

    def run_request(self,r):
        from v5_shadow.hk_stage_daily import init_hk_root,run_hk_stage
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'m08';init_hk_root(root)
            return run_hk_stage(r,root)

    def test_original_rows_preserved_no_lane_or_numeric_raw_rewrite(self):
        r=unbound_request();result,ref=mapped_result();before=copy.deepcopy((r,result,ref))
        out=self.bind(r,result,ref)
        self.assertEqual((r,result,ref),before)
        self.assertEqual(out['m06']['rows'],result['artifact']['rows'])
        self.assertEqual(out['m06']['rows'][0]['rank'],'1')
        self.assertEqual(out['m06']['rows'][0]['code'],'00001')
        self.assertEqual(out['m06']['rows_sha256'],sha256_json(result['artifact']['rows']))
        self.assertTrue(all('preselect_lane' not in row and 'candidate_lanes' not in row for row in out['m06']['rows']))
        for key in ('payload','payload_sha256','m02','data_kind'):
            self.assertEqual(out[key],r[key])
        self.assertIn('m06_adapter=ORIGINAL_MAPPED_FIELDS_ONLY',out['source']['source_evidence'])

    def test_native_mapping_reaches_original_algorithm_store_and_cold_reader(self):
        out=self.run_request(self.bind())
        self.assertEqual(out['artifact']['selected_rows'],10)
        self.assertEqual([r['score'] for r in out['artifact']['rows']],[89]*10)
        self.assertFalse(out['natural_verified'])
        self.assertFalse(out['provenance']['formal_admission'])

    def test_d1_reference_projects_symbol_only_at_original_owner_boundary(self):
        r=unbound_request('STAGE_0925');result,ref=mapped_result()
        r['route']='D1_REFERENCE';r['payload']['rows']=copy.deepcopy(result['artifact']['rows'][:12])
        out=self.bind(r,result,ref);rehash(out)
        read=self.run_request(out)
        self.assertEqual(read['artifact']['selection_status'],'CANNOT_CONFIRM')
        self.assertTrue(all(row['code'].startswith('HK.') for row in read['artifact']['rows']))
        self.assertTrue(all(row['source_mode']=='HK_CONNECT_D1_PRESELECT_REFERENCE' for row in read['artifact']['rows']))

    def test_existing_pool_is_not_overwritten(self):
        with self.assertRaisesRegex(ValueError,'M06_ALREADY_BOUND'):self.bind(request())

    def test_target_13_cannot_bind_stage_12(self):
        r=unbound_request();r['target_date']='20261012';r['signal_date']='20261009'
        result,ref=mapped_result();result.update(target_date='20261013',signal_date='20261012')
        with self.assertRaisesRegex(ValueError,'M06_DATE'):self.bind(r,result,ref)

    def test_source_reference_and_projection_must_both_match(self):
        for field in ('run_id','artifact_sha256','manifest_sha256','receipt_sha256','artifact_relative','role'):
            with self.subTest(field=field):
                result,ref=mapped_result();result['verified_source_reference'][field]='different'
                with self.assertRaises(ValueError):self.bind(result=result,reference=ref)
        result,ref=mapped_result();result['artifact']['source_sha256']='d'*64
        with self.assertRaisesRegex(ValueError,'SOURCE_PROJECTION'):self.bind(result=result,reference=ref)

    def test_reader_verification_and_fixture_flag_required(self):
        for mutate in (lambda r:r.pop('source_verification'),
                lambda r:r['source_verification'].update(row_count=99),
                lambda r:r['source_verification'].update(artifact_sha256='d'*64),
                lambda r:r.pop('fixture_only'),lambda r:r.update(fixture_only='false')):
            with self.subTest(mutation=mutate):
                result,ref=mapped_result();mutate(result)
                with self.assertRaises(ValueError):self.bind(result=result,reference=ref)

    def test_local_cli_writes_once_and_rejects_wrong_source_without_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);result,ref=mapped_result()
            objects={'request':unbound_request(),'m06-result':result,'expected-source':ref}
            cmd=[sys.executable,'-B','-m','v5_shadow.hk_stage_m06']
            for key,value in objects.items():
                path=root/(key+'.json');path.write_text(json.dumps(value));cmd+=['--'+key,str(path)]
            output=root/'bound.json';cmd+=['--output',str(output)]
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
            proc=subprocess.run(cmd,capture_output=True,text=True,env=env)
            self.assertEqual(proc.returncode,0,proc.stderr)
            before=output.read_bytes();self.assertEqual(json.loads(before),self.bind())
            self.assertNotEqual(subprocess.run(cmd,capture_output=True,env=env).returncode,0)
            self.assertEqual(output.read_bytes(),before)
            ref['artifact_sha256']='d'*64;(root/'expected-source.json').write_text(json.dumps(ref))
            cmd[-1]=str(root/'invalid.json')
            self.assertNotEqual(subprocess.run(cmd,capture_output=True,env=env).returncode,0)
            self.assertFalse((root/'invalid.json').exists())

    def test_missing_mapped_fields_not_rebuilt_from_raw_strings(self):
        for field in ('symbol','pool_rank','pool_score'):
            with self.subTest(field=field):
                result,ref=mapped_result();result['artifact']['rows'][0].pop(field)
                with self.assertRaises(ValueError):self.bind(result=result,reference=ref)

    def test_mapped_pool_integrity_and_safety(self):
        mutations=[lambda x:x['artifact']['rows'][0].update(pool_rank=True),
            lambda x:x['artifact']['rows'][0].update(pool_score=float('nan')),
            lambda x:x['artifact']['rows'][1].update(pool_score=1),
            lambda x:x['artifact']['rows'][0].update(symbol='A.000001'),
            lambda x:x['artifact']['rows'][1].update(symbol='HK.00001'),
            lambda x:x['artifact']['rows'].pop(),
            lambda x:x['artifact'].update(stage_selection_eligible=False),
            lambda x:x.update(production_allowed=True),
            lambda x:x['artifact']['rows'][0].update(orders_sent=True)]
        for n,mutate in enumerate(mutations):
            with self.subTest(case=n):
                result,ref=mapped_result();mutate(result)
                with self.assertRaises(ValueError):self.bind(result=result,reference=ref)

    def test_no_quote_lane_membership_time_or_unit_completion(self):
        cases=[('M08_LANES',lambda r:r['payload']['rows'][0].pop('candidate_lanes')),
            ('M08_REQUIRED_NUMBER',lambda r:r['payload']['rows'][0].pop('volume_ratio')),
            ('M08_MEMBERSHIP_DATE',lambda r:r['m02'].update(membership_date='20261007')),
            ('M08_UNITS',lambda r:r['m02']['units'].update(turnover='UNKNOWN')),
            ('M08_SOURCE_TIME',lambda r:r['source'].update(available_at='2026-10-08T09:36:00+08:00'))]
        for reason,mutate in cases:
            with self.subTest(reason=reason):
                r=unbound_request();mutate(r);out=self.bind(r);rehash(out)
                with self.assertRaisesRegex(ValueError,reason):self.run_request(out)

    def test_adapter_does_not_change_replay_or_natural_admission(self):
        r=unbound_request();r['data_kind']='RECORDED_INPUT_REPLAY'
        with self.assertRaisesRegex(ValueError,'FIXTURE_NOT_REPLAY'):self.bind(r)
        result,ref=mapped_result();result['fixture_only']=False  # Simulated reader metadata, still test-only data.
        out=self.run_request(self.bind(r,result,ref))
        self.assertIn('REPLAY_POINT_IN_TIME_QUALIFICATION_NOT_ATTESTED',out['artifact']['cannot_confirm'])
        r['data_kind']='LIVE'
        with self.assertRaisesRegex(ValueError,'NATURAL_ADMISSION_NOT_BOUND'):self.run_request(self.bind(r,result,ref))

    def test_bound_fixture_cannot_be_reclassified_at_producer_reader_boundary(self):
        r=self.bind();r['data_kind']='RECORDED_INPUT_REPLAY'
        with self.assertRaisesRegex(ValueError,'FIXTURE_NOT_REPLAY'):self.run_request(r)


if __name__=='__main__':unittest.main()

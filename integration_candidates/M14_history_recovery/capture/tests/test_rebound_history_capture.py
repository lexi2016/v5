"""Synthetic offline contract tests; never call a real network connector."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(os.environ.get('V5_HISTORY_TEST_BASELINE_ROOT',
    '/workspace/shared/manager-daily-publication-20261013/V5'))
MODULE = ROOT / 'v5_shadow/rebound_history_capture.py'
sys.path.insert(0, str(BASE / 'src'))
from v5_shadow import rebound_raw_repair


def load_candidate():
    spec = importlib.util.spec_from_file_location('m14_capture_candidate', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def task(codes=('HK.00001',)):
    return dict(schema_version='v5.m14_history_capture_task.v1',
        target_date='20261014', signal_date='20261013', canary_codes=list(codes),
        keys=[dict(code=code, date=day) for code in codes for day in ('20261008', '20261009')],
        expected_panel_sha256='a'*64,
        original_reference=dict(run_id='0'*32, artifact_sha256='d'*64,
            manifest_sha256='e'*64, receipt_sha256='f'*64),
        parent_binding=dict(parent_pointer_sha256='b'*64,
            parent_manifest_relative='panels/original/manifest.json',
            parent_manifest_sha256='c'*64,
            parent_panel_relative='panels/original/hkconnect_vipdoc_daily_panel.parquet',
            parent_panel_sha256='a'*64))


def row(day, trade=45276):
    return dict(datetime=datetime.strptime(day, '%Y%m%d').strftime('%Y-%m-%d 15:00'),
        open=10.25, high=12.5, low=8.5, close=11.1234567890123,
        trade=trade, volume=999999999, amount=None)


class API:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.disconnections = 0

    def get_instrument_bars(self, *args):
        self.calls.append(args)
        response = self.responses[len(self.calls)-1]
        if isinstance(response, Exception):
            raise response
        return response

    def disconnect(self):
        self.disconnections += 1


class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MODULE.exists():
            raise AssertionError('capture implementation is missing')
        cls.m = load_candidate()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root / 'new_capture'
        self.connections = 0
        # An injected, explicit test clock. It cannot be supplied through CLI.
        self.instant = datetime.now(timezone.utc)-timedelta(hours=1)
        self.observed_times = []

    def clock(self):
        self.instant += timedelta(microseconds=1)
        self.observed_times.append(self.instant.isoformat(timespec='microseconds'))
        return self.instant

    def run_capture(self, responses, *, job=None, output=None):
        api = API(responses)
        def connector():
            self.connections += 1
            return api, '119.97.142.130:7721'
        plan = self.m.prepare_plan(task() if job is None else job, baseline_root=BASE)
        result = self.m.capture_plan(plan, baseline_root=BASE,
            output_dir=self.output if output is None else output,
            connector=connector, clock=self.clock)
        return result, api

    def read_source(self, result, index=0):
        source = result['sources'][index]
        raw = (self.output/source['relative']).read_bytes()
        self.assertEqual(source['sha256'], sha(raw))
        self.assertEqual(source['record_pointer'], '')
        return json.loads(raw)

    def test_plan_is_offline_pinned_strict_and_exact(self):
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('network')):
            plan = self.m.prepare_plan(task(), baseline_root=BASE)
        self.assertEqual(plan['task'], task())
        self.assertEqual(plan['request_template'], dict(category=4, market=71, start=0, count=120))
        self.assertEqual(plan['source']['sha256'], rebound_raw_repair.DECODER_SHA)
        self.assertEqual(plan['source']['extracted_functions'], ['_canonical', '_clock', '_connect'])
        self.assertFalse(plan['formal']); self.assertFalse(plan['natural'])

    def test_success_calls_exactly_once_per_explicit_code_preserves_rows_and_decodes(self):
        codes = ('HK.00001', 'HK.00002', 'HK.00003')
        responses = [[row('20261008'), row('20261009', 47348)] for _ in codes]
        original = copy.deepcopy(responses)
        result, api = self.run_capture(responses, job=task(codes))
        self.assertEqual(self.connections, 1)
        self.assertEqual(api.calls, [(4, 71, code[3:], 0, 120) for code in codes])
        self.assertEqual(api.disconnections, 1)
        self.assertEqual(responses, original)
        self.assertEqual(result['status'], 'CAPTURED')
        self.assertFalse(result['formal']); self.assertFalse(result['natural'])
        for i, code in enumerate(codes):
            record = self.read_source(result, i)
            self.assertEqual(record['code'], code)
            self.assertEqual(record['source_rows'], responses[i])
            self.assertEqual(record['request_sha256'], sha(canonical(record['request'])))
            self.assertEqual(record['response_sha256'], sha(canonical(responses[i])))
            self.assertEqual(record['returned_count'], 2)
            for field in ('request_started_at', 'response_acquired_at', 'request_finished_at'):
                self.assertIn(record[field], self.observed_times)
            rebound_raw_repair._record(record, datetime.now(timezone.utc))
        decoded = rebound_raw_repair.decode_raw_repair(self.output, sources=result['sources'],
            keys=task(codes)['keys'], through_date='20261013')
        self.assertEqual([r['trade'] for r in decoded['rows']], [45276,47348]*3)
        self.assertTrue(all(r['close']==11.1234567890123 for r in decoded['rows']))
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        for path in self.output.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o400)

    def test_future_rows_remain_in_original_response_and_block_decoder(self):
        original = [row('20261008'), row('20261009'), row('20261014', 99)]
        result, _ = self.run_capture([original])
        record = self.read_source(result)
        self.assertEqual(record['source_rows'], original)
        self.assertIn('FUTURE_ROWS_AFTER_SIGNAL_KEEP_RAW', result['repair_blockers'])
        self.assertEqual(record['diagnostics']['future_row_indexes'], [2])
        self.assertFalse(result['repair_ready'])
        with self.assertRaisesRegex(ValueError, 'FUTURE_ROW'):
            rebound_raw_repair.decode_raw_repair(self.output, sources=result['sources'],
                keys=task()['keys'], through_date='20261013')

    def test_missing_keys_remain_explicit_no_padding_or_fabrication(self):
        result, _ = self.run_capture([[row('20261008')]])
        self.assertEqual(result['missing_keys'], [dict(code='HK.00001',date='20261009')])
        self.assertFalse(result['repair_ready'])
        self.assertEqual(self.read_source(result)['returned_count'], 1)

    def test_query_failure_is_immutable_receipt_and_never_retried(self):
        result, api = self.run_capture([ConnectionError('synthetic query failure')])
        self.assertEqual(api.calls, [(4,71,'00001',0,120)])
        self.assertEqual(self.connections, 1); self.assertEqual(api.disconnections, 1)
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['sources'], [])
        receipt = json.loads((self.output/result['receipts'][0]['relative']).read_bytes())
        self.assertEqual(receipt['status'], 'QUERY_FAILED')
        self.assertIsNone(receipt['response_acquired_at'])
        self.assertIsNone(receipt['response_sha256'])
        self.assertEqual(receipt['error_type'], 'ConnectionError')
        self.assertEqual(receipt['request']['count'], 120)
        self.assertFalse(result['repair_ready'])

    def test_connect_failure_writes_receipt_without_queries(self):
        def connector():
            self.connections += 1
            raise TimeoutError('synthetic timeout')
        result = self.m.capture_plan(self.m.prepare_plan(task(), baseline_root=BASE),
            baseline_root=BASE, output_dir=self.output, connector=connector, clock=self.clock)
        self.assertEqual(self.connections, 1)
        self.assertEqual(result['status'], 'FAILED')
        receipt = json.loads((self.output/result['receipts'][0]['relative']).read_bytes())
        self.assertEqual(receipt['status'], 'CONNECT_FAILED')
        self.assertEqual(receipt['query_attempted'], False)

    def test_unknown_query_or_dates_keys_and_limits_are_rejected(self):
        invalid = []
        for field, value in (('target_date','20261013'),('signal_date','20261014'),
            ('target_date','20260230'),('query',dict(count=900)),('endpoint','elsewhere')):
            item=task(); item[field]=value; invalid.append(item)
        invalid += [task(('HK.00001','HK.00002','HK.00003','HK.00004')), task(())]
        for code in ('00001','HK.１２３４５','HK.0000A'):
            invalid.append(task((code,)))
        for key in (dict(code='HK.00001',date='20261013'),dict(code='HK.00002',date='20261008'),
                    dict(code='HK.00001',date='20260230')):
            item=task(); item['keys']=[key]; invalid.append(item)
        item=task(); item['keys']*=2; invalid.append(item)
        item=task(); item['expected_panel_sha256']='d'*64; invalid.append(item)
        item=task(); item['parent_binding']['parent_manifest_relative']='../manifest.json'; invalid.append(item)
        for item in invalid:
            with self.subTest(item=item):
                with self.assertRaises(ValueError): self.m.prepare_plan(item, baseline_root=BASE)

    def test_modified_plan_or_source_fails_before_connector(self):
        plan=self.m.prepare_plan(task(), baseline_root=BASE)
        plan['request_template']['count']=121
        with self.assertRaises(ValueError):
            self.m.capture_plan(plan, baseline_root=BASE, output_dir=self.output,
                connector=lambda: self.fail('connector called'))
        badbase=self.root/'base'; target=badbase/'vendor/rebound_repair_baseline'
        target.mkdir(parents=True)
        (target/'hk_daily_supplement.py').write_bytes(b'# fake')
        with self.assertRaises((ValueError,FileNotFoundError)):
            self.m.prepare_plan(task(),baseline_root=badbase)
        self.assertFalse(self.output.exists())

    def test_existing_output_or_symlinks_are_rejected_before_connect(self):
        plan=self.m.prepare_plan(task(),baseline_root=BASE)
        existing=self.root/'existing'; existing.mkdir()
        link=self.root/'alias'; link.symlink_to(self.root,target_is_directory=True)
        for output in (existing, link/'new', self.root/'missing'/'new'):
            with self.subTest(output=output):
                with self.assertRaises((ValueError,OSError)):
                    self.m.capture_plan(plan,baseline_root=BASE,output_dir=output,
                        connector=lambda:self.fail('connector called'))
        baseline_link=self.root/'base_alias'; baseline_link.symlink_to(BASE,target_is_directory=True)
        with self.assertRaises((ValueError,OSError)):
            self.m.prepare_plan(task(),baseline_root=baseline_link)

    def test_repeated_capture_cannot_overwrite_a_prior_receipt(self):
        result,_=self.run_capture([[row('20261008'),row('20261009')]])
        before={p.name:p.read_bytes() for p in self.output.iterdir()}
        with self.assertRaises(FileExistsError):
            self.run_capture([[row('20261008')]])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.output.iterdir()})

    def test_pinned_connector_uses_exact_sdk_options_and_one_fixed_connection(self):
        calls = []
        class SyntheticSDK:
            def __init__(self, **options):
                calls.append(('construct', options))
            def connect(self, *args, **kwargs):
                calls.append(('connect', args, kwargs))
                return True
            def disconnect(self):
                calls.append(('disconnect',))
        package = types.ModuleType('pytdx')
        module = types.ModuleType('pytdx.exhq')
        module.TdxExHq_API = SyntheticSDK
        functions, _ = self.m._baseline(BASE)
        with patch.dict(sys.modules, {'pytdx': package, 'pytdx.exhq': module}):
            _, endpoint = functions['_connect']()
        self.assertEqual(endpoint, '119.97.142.130:7721')
        self.assertEqual(calls, [
            ('construct', dict(heartbeat=False, auto_retry=False, raise_exception=True)),
            ('connect', ('119.97.142.130',7721), dict(time_out=2.0))])

    def test_connector_endpoint_mismatch_writes_failure_receipt_without_query(self):
        api=API([])
        result=self.m.capture_plan(self.m.prepare_plan(task(),baseline_root=BASE),
            baseline_root=BASE, output_dir=self.output, clock=self.clock,
            connector=lambda:(api,'unexpected:9999'))
        self.assertEqual(api.calls,[])
        self.assertEqual(api.disconnections,1)
        self.assertEqual(result['status'],'FAILED')

    def test_one_failed_code_does_not_retry_and_other_explicit_codes_each_run_once(self):
        job=task(('HK.00001','HK.00002','HK.00003'))
        result,api=self.run_capture([TimeoutError('synthetic'),
            [row('20261008'),row('20261009')],[row('20261008'),row('20261009')]],job=job)
        self.assertEqual(api.calls,[(4,71,c[3:],0,120) for c in job['canary_codes']])
        self.assertEqual(result['status'],'PARTIAL')
        self.assertEqual(len(result['receipts']),3)
        self.assertEqual(len(result['sources']),2)
        self.assertEqual({k['code'] for k in result['missing_keys']},{'HK.00001'})

    def test_response_shape_count_nonfinite_and_duplicate_dates_fail_closed(self):
        for index,response in enumerate((None, [row('20261008')]*121,
                [dict(row('20261008'),trade=float('nan'))],
                [row('20261008'),row('20261008')])):
            with self.subTest(index=index):
                result,api=self.run_capture([response],output=self.root/f'case-{index}')
                self.assertEqual(len(api.calls),1)
                self.assertFalse(result['repair_ready'])
                if index < 3:
                    self.assertEqual(result['sources'],[])
                    self.assertEqual(result['status'],'FAILED')
                else:
                    self.assertIn('DUPLICATE_SOURCE_DATES',result['repair_blockers'])
                    ref=result['sources'][0]
                    record=json.loads((self.root/f'case-{index}'/ref['relative']).read_bytes())
                    self.assertEqual(record['source_rows'],response)

    def test_owner_reference_hex_run_id_and_same_parent_directory_are_required(self):
        invalid=[]
        job=task(); job['original_reference']['run_id']='synthetic-m14-run'; invalid.append(job)
        job=task(); job['parent_binding']['parent_panel_relative']='panels/other/hkconnect_vipdoc_daily_panel.parquet'; invalid.append(job)
        for job in invalid:
            with self.assertRaises(ValueError): self.m.prepare_plan(job,baseline_root=BASE)
        plan=self.m.prepare_plan(task(),baseline_root=BASE)
        self.assertIs(plan['formal_eligibility_verified'],False)
        self.assertIs(plan['natural_verified'],False)

    def test_dates_are_generic_but_exact_in_the_bound_plan(self):
        job=task(); job['target_date']='20261015'; job['signal_date']='20261014'
        self.assertEqual(self.m.prepare_plan(job,baseline_root=BASE)['task'],job)

    def test_duplicate_json_keys_and_nonfinite_input_are_rejected(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}'):
            with self.assertRaises(ValueError): self.m._json(raw)

    def test_cli_plan_is_offline_and_capture_requires_plan_sha(self):
        path=self.root/'task.json'; path.write_bytes(canonical(task()))
        result=subprocess.run([sys.executable,str(MODULE),'plan','--task',str(path),
            '--baseline-root',str(BASE),'--output-dir',str(self.output)],text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((self.output/'plan.json').is_file())
        result=subprocess.run([sys.executable,str(MODULE),'capture','--plan',str(self.output/'plan.json'),
            '--baseline-root',str(BASE),'--output-dir',str(self.root/'capture')],text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.root/'capture').exists())

if __name__=='__main__':
    unittest.main()

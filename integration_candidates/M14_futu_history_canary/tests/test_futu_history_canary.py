"""Synthetic only: no futu import, socket, credentials, pandas or market calls."""
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).absolute().parents[1]
spec = importlib.util.spec_from_file_location('canary', ROOT / 'futu_history_canary.py')
canary = importlib.util.module_from_spec(spec) if spec and spec.loader and (ROOT / 'futu_history_canary.py').exists() else None
if canary is not None:
    spec.loader.exec_module(canary)

class Frame:
    columns = ['code', 'name', 'time_key', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'extra']
    dtypes = ['object', 'object', 'object', 'float64', 'float64', 'float64', 'float64', 'int64', 'float64', 'float64']
    def __init__(self, rows):
        self.rows = rows
        self.index = list(range(len(rows)))
    def itertuples(self, index=False, name=None):
        return iter(tuple(r) for r in self.rows)

def rows(code, days):
    return Frame([[code, '合成', d[:4]+'-'+d[4:6]+'-'+d[6:]+' 00:00:00', 1.1234567890123457, 1.2, 1.4, 1.0, 0, 0.0, float('nan')] for d in days])

def quota(codes, used=96, remaining=4):
    return (0, (used, remaining, [dict(code=c, name='合成', request_time='2026-10-13 18:51:09') for c in codes]))

class Clock:
    def __init__(self): self.t = 0.0
    def monotonic(self): return self.t
    def sleep(self, amount): self.t += amount
    def utc(self):
        from datetime import datetime, timezone, timedelta
        return datetime(2026, 10, 13, 19, tzinfo=timezone.utc) + timedelta(seconds=self.t)

class API:
    def __init__(self, plan, clock, output, pre=None, pages=None, error=None, post=None):
        self.plan, self.clock, self.output = plan, clock, output
        self.pre = pre if pre is not None else quota(plan['codes'])
        self.post = post if post is not None else self.pre
        self.pages, self.error = pages or {}, error
        self.calls, self.quota_calls, self.closed = [], [], False
    def get_history_kl_quota(self, **kw):
        self.quota_calls.append((self.clock.t, kw))
        return self.pre if len(self.quota_calls)==1 else self.post
    def request_history_kline(self, **kw):
        code = kw['code']
        attempt = self.output / ('attempt-'+code+'.json')
        assert attempt.exists(), 'attempt must be durable before query'
        assert stat.S_IMODE(attempt.stat().st_mode) == 0o400
        self.calls.append((self.clock.t, kw))
        if self.error: raise self.error
        return (0, rows(code, self.plan['required_sessions']), self.pages.get(code))
    def close(self): self.closed = True

class CanaryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(canary, 'Implementation is missing: write tests before code')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.clock = Clock()
    def plan(self, codes=None):
        return canary.prepare_plan(codes or ['HK.00001', 'HK.00376', 'HK.01191'])
    def run_capture(self, plan=None, **kw):
        plan = plan or self.plan()
        output = self.base / 'run'
        api = API(plan, self.clock, output, **kw)
        calls = []
        def connect():
            calls.append(1)
            return api, {'sdk_version':'SYNTHETIC', 'open_quote_context_source_sha256':'0'*64, 'synthetic':True}, canary.symbolic_request
        result = canary.capture_plan(plan, output_dir=output, connector=connect, clock=self.clock.utc, monotonic=self.clock.monotonic, sleep=self.clock.sleep)
        self.assertEqual(calls, [1])
        self.assertTrue(api.closed)
        return result, api, output
    def test_fixed_scope_and_source_window(self):
        p = self.plan()
        self.assertEqual((p['start'], p['end'], p['target_date']), ('2026-07-20', '2026-10-13', '20261014'))
        self.assertEqual(len(p['calendar']['prior60']), 60)
        self.assertEqual(p['required_sessions'][0], '20260720')
        self.assertEqual(p['required_sessions'][-1], '20261013')
        self.assertEqual(len(p['required_sessions']), 61)
        self.assertIn('20260925', p['required_sessions'])
        self.assertFalse(p['formal'])
    def test_reject_unknown_duplicate_empty_codes(self):
        for codes in ([], ['HK.00700'], ['HK.00001']*2, ['HK.00001']*4):
            with self.subTest(codes=codes), self.assertRaises(ValueError): canary.prepare_plan(codes)
    def test_success_exact_one_page_contract_spacing_all_columns(self):
        r, api, out = self.run_capture()
        self.assertEqual(r['status'], 'CAPTURED')
        self.assertEqual(len(api.calls), 3)
        self.assertEqual(len(api.quota_calls), 2)
        all_times = [api.quota_calls[0][0]] + [x[0] for x in api.calls] + [api.quota_calls[1][0]]
        self.assertTrue(all(b-a >= 1 for a,b in zip(all_times, all_times[1:])))
        for _, req in api.calls:
            self.assertEqual(req, canary.symbolic_request(req['code']))
        rec = json.loads((out/'response-HK.00001.json').read_text())
        frame = rec['response']['items'][1]
        self.assertEqual(frame['columns'], Frame.columns)
        self.assertEqual(frame['dtypes'], Frame.dtypes)
        self.assertEqual(frame['rows'][0][3], 1.1234567890123457)
        self.assertEqual(frame['rows'][0][-1]['value'], 'NaN')
        self.assertEqual(rec['diagnostics']['invalid_ohlc_rows'], [])
        self.assertEqual(rec['diagnostics']['zero_volume_rows'], list(range(61)))
        self.assertTrue(rec['diagnostics']['presence_20260925'])
        self.assertEqual(rec['diagnostics']['missing_sessions'], [])
        self.assertEqual(r['quota_change']['remaining_delta'], 0)
        for f in out.iterdir():
            self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o400)
            json.loads(f.read_text(), parse_constant=lambda x: self.fail('nonfinite JSON'))
    def test_preflight_unoccupied_blocks_all_history_but_keeps_raw(self):
        r, api, out = self.run_capture(pre=quota(['HK.00001']))
        self.assertEqual(api.calls, [])
        self.assertEqual(r['status'], 'PREFLIGHT_REJECTED')
        self.assertTrue((out/'quota-before.json').exists())
        self.assertTrue((out/'summary.json').exists())
    def test_official_quota_tuple_shape_counts_gate_no_detail_count_equality(self):
        r, api, _ = self.run_capture(pre=quota(self.plan()['codes'], used=96))
        self.assertEqual(len(api.calls), 3)
        self.assertIn('DETAIL_COUNT_DIFFERS_FROM_USED', r['quota_before']['anomalies'])
        for bad in [(0, {'used':96}), (0, (-1,4,[])), (-1,'error')]:
            other = self.base / ('bad'+str(len(list(self.base.iterdir()))))
            api = API(self.plan(), self.clock, other, pre=bad)
            res = canary.capture_plan(self.plan(), output_dir=other, connector=lambda:(api,{},canary.symbolic_request), clock=self.clock.utc, monotonic=self.clock.monotonic, sleep=self.clock.sleep)
            self.assertEqual(api.calls, [])
            self.assertEqual(res['status'], 'PREFLIGHT_REJECTED')
    def test_nonempty_page_key_partial_no_pagination(self):
        r, api, out = self.run_capture(pages={'HK.00001':b'next'})
        self.assertEqual(r['status'], 'PARTIAL')
        self.assertEqual(len(api.calls), 3)
        rec = json.loads((out/'response-HK.00001.json').read_text())
        self.assertEqual(rec['status'], 'PARTIAL')
        self.assertEqual(rec['response']['items'][2], {'__type__':'bytes', 'hex':'6e657874'})
    def test_exception_stops_history_no_retry_after_quota_attempted(self):
        r, api, out = self.run_capture(error=RuntimeError('synthetic failure'))
        self.assertEqual(len(api.calls), 1)
        self.assertEqual(len(api.quota_calls), 2)
        self.assertEqual(r['status'], 'FAILED')
        self.assertTrue((out/'response-HK.00001.json').exists())
    def test_no_overwrite_symlink_escape(self):
        plan = self.plan()
        (self.base/'existing').mkdir()
        (self.base/'link').symlink_to(self.base, target_is_directory=True)
        for out in (self.base/'existing', self.base/'link'/'leaf', self.base/'..'/'escape'):
            with self.subTest(out=out), self.assertRaises((ValueError,OSError)):
                canary.capture_plan(plan, output_dir=out, connector=lambda:self.fail('connection forbidden'))
    def test_invalid_ohlc_nonfinite_negative_volume_missing_duplicate(self):
        p = self.plan(['HK.00376'])
        frame = rows('HK.00376', ['20260831', '20260831', '20260925'])
        frame.rows[0][3] = 0.0
        frame.rows[1][5] = float('inf')
        frame.rows[2][7] = -1
        d = canary.diagnostics('HK.00376', canary.encode_native(frame), p)
        self.assertEqual(d['invalid_ohlc_rows'], [0,1])
        self.assertEqual(d['invalid_volume_rows'], [2])
        self.assertEqual(d['duplicate_dates'], ['20260831'])
        self.assertEqual(len(d['missing_sessions']), 59)
        self.assertEqual(len(d['ohlc_comparison']['futu_rows']), 2)
        self.assertFalse(d['raw_values_modified'])
    def test_actual_quota_delta_not_inferred(self):
        r, _, _ = self.run_capture(post=quota(self.plan()['codes'], used=97, remaining=3))
        self.assertEqual(r['quota_change']['remaining_delta'], -1)
        self.assertFalse(r['quota_change']['cause_attributed'])
        self.assertFalse(r['full_pool_authorized'])
    def test_args_mode_no_sdk_import_no_connection(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable,str(ROOT/'futu_history_canary.py'),'args','--codes','HK.00001'], capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['codes'], ['HK.00001'])
        self.assertNotIn('futu', sys.modules)
    def test_hard_supervisor_kills_synthetic_blocking_process(self):
        import multiprocessing
        import time
        proc=multiprocessing.get_context('spawn').Process(target=time.sleep,args=(10,))
        result=canary._supervise(proc,0.15)
        self.assertTrue(result['hard_timeout'])
        self.assertFalse(proc.is_alive())
        self.assertLess(result['elapsed_seconds'],2)
    def test_source_mutation_rejected(self):
        import shutil
        root = self.base/'sources'
        shutil.copytree(ROOT/'pinned', root)
        (root/'repair.py').write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError, 'PINNED_SOURCE_SHA'):
            canary.prepare_plan(['HK.00001'], source_root=root)

if __name__ == '__main__': unittest.main()

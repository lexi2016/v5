"""M08 publication adapter unit tests and synthetic engineering integration.

Unit tests inject only the cold reader; the shared publisher and HTTP service
are real. A separate three-route integration test uses no injected components.
"""
import ast
import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from v5_shadow.digests import canonical_bytes, sha256_json
from v5_shadow.module_api import _config, create_module_server, read_response


ROUTE = '/api/v5/hk-stage-selection'
STAGE = 'STAGE_0930_0935'
STAGE8 = 'STAGE_1545_1555'


class HKStageAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.store = self.root / 'private-hk-store'
        self.store.mkdir()
        self.responses = self.root / 'api-responses'
        self.responses.mkdir()
        (self.responses / '.v5-module-root').write_text('v5.module-root.v1:hk_stage\n')
        self.config = dict(schema_version='v5.module_api.v1', module_id='hk_stage',
                           release_id='m08-test-r1', data_root=str(self.responses), routes=[ROUTE])
        self.api = importlib.import_module('v5_shadow.hk_stage_api')
        self.reader = Mock()
        reader_module = types.ModuleType('v5_shadow.hk_stage_reader')
        reader_module.read_hk_stage = self.reader
        self.reader_patch = patch.dict(sys.modules, {'v5_shadow.hk_stage_reader': reader_module})
        self.reader_patch.start()
        self.addCleanup(self.reader_patch.stop)

    def cold_result(self, date='20261008', stage=STAGE, run='selection-run-1', kind='SYNTHETIC'):
        reference = dict(generation_sha256='1' * 64, run_id=run, market='HK_CONNECT',
                         target_date=date, stage_id=stage, artifact_sha256='2' * 64,
                         manifest_sha256='3' * 64, receipt_sha256='4' * 64,
                         product_sha256='5' * 64)
        artifact = dict(schema_version='stage_center.selection.v2', trade_date=date,
                        stage_id=stage, market='HK_CONNECT', artifact_id='artifact-1', run_id=run,
                        algorithm_id='original-owner', algorithm_sha256='6' * 64,
                        raw_artifact_sha256='7' * 64, source_status='PARTIAL_WITH_ROWS',
                        selection_status='PARTIAL_WITH_ROWS', requested_rows=3,
                        source_rows=2, selected_rows=1, coverage_ratio=0.333333,
                        missing_symbols=['HK.00003'], cannot_confirm=['MISSING_LANE'],
                        rows=[dict(code='HK.00001', score=89.0, rank=1,
                                   formula='turnover_hkd / circular_market_cap_hkd_yi',
                                   reasons=['original-score-reason'],
                                   candidate_lanes=['D1_MODEL_TOP100'],
                                   quote=dict(last_price=11, turnover_hkd=100000000))],
                        source_evidence=['raw_sha256=' + '7' * 64,
                                         'formula=turnover_hkd/circular_market_cap_hkd_yi'],
                        production_allowed=False, buy_gate_updated=False, orders_sent=False)
        return dict(artifact=artifact, reference=reference,
                    provenance=dict(data_kind=kind, input_sha256='8' * 64,
                                    source_manifest_sha256='9' * 64,
                                    implementation_identity={'hk_stage_daily.py': 'a' * 64},
                                    source_identity=dict(captured_at=date[:4] + '-' + date[4:6] + '-' + date[6:] + 'T09:35:00+08:00'),
                                    natural_verified=False, formal_admission=False),
                    production_allowed=False, buy_gate_updated=False, orders_sent=False,
                    natural_verified=False)

    def publish(self, result=None, expected=None):
        result = self.cold_result() if result is None else result
        self.reader.return_value = result
        return self.api.publish_hk_stage_response(self.config, self.store, result['reference'],
                                                  expected_generation=expected)

    def query(self, result):
        reference = result['reference']
        return {'date': reference['target_date'], 'stage': reference['stage_id'],
                'run_id': reference['run_id']}

    def record(self, result):
        config, fd = _config(self.config)
        try:
            return read_response(config, fd, ROUTE, self.query(result))[0]
        finally:
            os.close(fd)

    def serve(self):
        server = create_module_server(self.config)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return 'http://127.0.0.1:' + str(server.server_address[1])

    def http_read(self, base, query, method='GET'):
        request = Request(base + ROUTE + '?' + urlencode(query), method=method)
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            with error:
                return error.code, json.load(error)

    def test_uses_exact_cold_reference_and_keeps_original_rows(self):
        source = self.cold_result()
        original = copy.deepcopy(source)
        result = self.publish(source)
        self.reader.assert_called_once_with(self.store, original['reference'])
        record = self.record(source)
        self.assertEqual(record['payload']['artifact'], original['artifact'])
        self.assertEqual(record['payload']['reference'], original['reference'])
        self.assertEqual(record['payload']['provenance'], original['provenance'])
        self.assertEqual(source, original)
        self.assertEqual(record['source_input_sha256'], source['provenance']['input_sha256'])
        self.assertEqual(record['generated_at'], source['provenance']['source_identity']['captured_at'])
        self.assertEqual(record['data_kind'], 'SYNTHETIC')
        self.assertEqual(record['payload_sha256'], sha256_json(record['payload']))
        self.assertRegex(result['generation_sha256'], r'^[0-9a-f]{64}$')
        self.assertFalse(record['payload']['natural_verified'])
        self.assertFalse(record['payload']['provenance']['formal_admission'])

    def test_replay_kind_is_taken_from_reader_and_not_upgraded(self):
        source = self.cold_result(kind='RECORDED_INPUT_REPLAY')
        self.publish(source)
        self.assertEqual(self.record(source)['data_kind'], 'RECORDED_INPUT_REPLAY')

    def test_stage8_is_separate_from_m10_seven_stages(self):
        normal = self.cold_result()
        first = self.publish(normal)['generation_sha256']
        separate = self.cold_result(stage=STAGE8, run='stage8-run')
        self.publish(separate, first)
        self.assertEqual(self.record(normal)['payload']['stage_group'], 'HK_SEVEN_STAGE')
        self.assertTrue(self.record(normal)['payload']['m10_stage_member'])
        payload = self.record(separate)['payload']
        self.assertEqual(payload['stage_group'], 'HK_STAGE8_SEPARATE')
        self.assertFalse(payload['m10_stage_member'])
        self.assertEqual(payload['artifact']['stage_id'], STAGE8)

    def test_partial_empty_and_error_diagnostics_are_preserved(self):
        generation = None
        for status in ('READY', 'READY_EMPTY', 'PARTIAL_WITH_ROWS', 'CANNOT_CONFIRM'):
            with self.subTest(status=status):
                source = self.cold_result(run='run-' + status)
                source['artifact']['selection_status'] = status
                if status in ('READY_EMPTY', 'CANNOT_CONFIRM'):
                    source['artifact']['rows'] = []
                    source['artifact']['selected_rows'] = 0
                generation = self.publish(source, generation)['generation_sha256']
                payload = self.record(source)['payload']
                self.assertEqual(payload['status'], status)
                self.assertEqual(payload['artifact'], source['artifact'])

    def test_public_projection_redacts_paths_without_dropping_evidence(self):
        source = self.cold_result(stage=STAGE8)
        source['artifact']['source_evidence'] += [
            'active_snapshot_path=/Users/private/secret/snapshot.json',
            'manifest_path=private/history/manifest.json',
            'receipt_file=file:///private/receipt.json',
            r'capture_path=C:\Users\private\snapshot.csv',
            'input_root=/workspace/private-inputs',
            'raw_sha256=' + 'f' * 64]
        source['artifact']['cannot_confirm'] += ['OPEN_FAILED: /Users/private/secret/raw.csv unavailable']
        source['provenance']['source_identity'].update(
            input_path='/private/input.json', fixture_root='/private/replays',
            nested={'source_path': 'private/relative/input.csv', 'units': 'HKD'})
        original = copy.deepcopy(source)
        self.publish(source)
        payload = self.record(source)['payload']
        serialized = json.dumps(payload)
        for secret in ('/Users/private', 'private/history', 'file:///private', r'C:\\Users',
                       '/workspace/private', '/private/input', '/private/replays', 'private/relative'):
            self.assertNotIn(secret, serialized)
        self.assertEqual(source, original)
        self.assertEqual(payload['artifact']['rows'], original['artifact']['rows'])
        self.assertEqual(len(payload['artifact']['source_evidence']), len(original['artifact']['source_evidence']))
        self.assertIn('active_snapshot_path=[REDACTED_PATH]', payload['artifact']['source_evidence'])
        self.assertIn('raw_sha256=' + 'f' * 64, payload['artifact']['source_evidence'])
        self.assertIn('OPEN_FAILED:', payload['artifact']['cannot_confirm'][-1])
        self.assertIn('unavailable', payload['artifact']['cannot_confirm'][-1])
        self.assertEqual(payload['provenance']['source_identity']['nested']['units'], 'HKD')

    def test_native_formulas_are_not_mistaken_for_source_paths(self):
        source = self.cold_result()
        expressions = ['(turnover_hkd)/circular_market_cap_hkd_yi',
                       'turnover_hkd /circular_market_cap_hkd_yi',
                       '(turnover_hkd /circular_market_cap_hkd_yi)/volume_ratio']
        source['artifact']['rows'][0]['formula'] = expressions[0]
        source['artifact']['rows'][0]['score_formula'] = expressions[1]
        source['artifact']['rows'][0]['formulas'] = expressions
        source['artifact']['source_evidence'] += ['formula=' + expression for expression in expressions]
        self.publish(source)
        artifact = self.record(source)['payload']['artifact']
        self.assertEqual(artifact['rows'], source['artifact']['rows'])
        self.assertEqual(artifact['source_evidence'], source['artifact']['source_evidence'])

    def test_formula_label_does_not_allow_absolute_path_disclosure(self):
        source = self.cold_result()
        source['artifact']['source_evidence'].append('formula=/Users/private/expression.txt')
        source['artifact']['rows'][0]['formula'] = '/Users/private/expression.txt'
        self.publish(source)
        payload = self.record(source)['payload']
        self.assertNotIn('/Users/private', json.dumps(payload))
        self.assertIn('formula=[REDACTED_PATH]', payload['artifact']['source_evidence'])

    def test_unquoted_paths_and_formula_diagnostics_do_not_leak(self):
        source = self.cold_result()
        source['artifact']['cannot_confirm'] += [
            'OPEN_FAILED: /Users/Alice Doe/secret.csv unavailable',
            'OPEN_FAILED: /Users/Alice Doe/secret final.csv unavailable',
        ]
        source['artifact']['source_evidence'].append('formula=loaded from /Users/private/expression.txt')
        self.publish(source)
        payload = self.record(source)['payload']
        self.assertEqual(payload['artifact']['cannot_confirm'][-2:], [
            'OPEN_FAILED: [REDACTED_PATH] unavailable',
            'OPEN_FAILED: [REDACTED_PATH] unavailable',
        ])
        self.assertEqual(payload['artifact']['source_evidence'][-1],
                         'formula=loaded from [REDACTED_PATH]')

    def test_quoted_paths_with_spaces_are_fully_redacted_from_diagnostics(self):
        source = self.cold_result()
        source['artifact']['cannot_confirm'] += [
            'OPEN_FAILED: "/Users/Alice Doe/secret, draft.csv" unavailable',
            "REPLAY_FAILED: '/private/Alice Doe/annual inputs.csv' checksum invalid",
            'SNAPSHOT_FAILED: "C:\\Users\\Alice Doe\\snapshot.csv" unavailable',
        ]
        self.publish(source)
        diagnostics = self.record(source)['payload']['artifact']['cannot_confirm']
        self.assertEqual(diagnostics[-3:], [
            'OPEN_FAILED: "[REDACTED_PATH]" unavailable',
            "REPLAY_FAILED: '[REDACTED_PATH]' checksum invalid",
            'SNAPSHOT_FAILED: "[REDACTED_PATH]" unavailable',
        ])

    def test_date_stage_run_switches_and_refresh_are_read_only(self):
        sources = [self.cold_result(), self.cold_result(run='selection-run-2'),
                   self.cold_result(date='20261009', run='next-date'),
                   self.cold_result(stage=STAGE8, run='stage8-run')]
        generation = None
        for source in sources:
            generation = self.publish(source, generation)['generation_sha256']
        self.reader.reset_mock()
        self.reader.side_effect = AssertionError('GET must never cold-read or produce')
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        base = self.serve()
        for source in sources + list(reversed(sources)):
            status, payload = self.http_read(base, self.query(source))
            self.assertEqual(status, 200)
            self.assertEqual(payload['reference'], source['reference'])
        bad_query = self.query(sources[0]); bad_query['run_id'] = 'unpublished-run'
        self.assertEqual(self.http_read(base, bad_query)[0], 503)
        self.assertEqual(self.http_read(base, {'date': '20261008', 'stage': STAGE})[0], 503)
        self.assertEqual(self.http_read(base, self.query(sources[0]), 'POST')[0], 405)
        self.reader.assert_not_called()
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(after, before)

    def test_fresh_process_reads_published_record_without_reader_or_producer(self):
        source = self.cold_result()
        self.publish(source)
        script = '''
import json, os, sys
from v5_shadow.module_api import _config, read_response
value = json.loads(sys.stdin.read())
config, fd = _config(value['config'])
try:
    record, digest = read_response(config, fd, value['route'], value['query'])
finally:
    os.close(fd)
assert 'v5_shadow.hk_stage_daily' not in sys.modules
assert 'v5_shadow.hk_stage_reader' not in sys.modules
assert 'v5_shadow.hk_stage_api' not in sys.modules
print(json.dumps(record))
'''
        result = subprocess.run([sys.executable, '-B', '-c', script],
                                input=json.dumps(dict(config=self.config, route=ROUTE, query=self.query(source))),
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['payload']['reference'], source['reference'])

    def test_adapter_contains_no_producer_import_or_call(self):
        source = Path(self.api.__file__).read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn('hk_stage_daily', node.module or '')
                self.assertNotIn('stage_selection', node.module or '')
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn('hk_stage_daily', alias.name)
                    self.assertNotIn('stage_selection', alias.name)
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id, ('run_hk_stage', 'run_stage_selection', 'select_hk_four_lane'))

    def test_same_snapshot_reuses_generation_and_stale_cas_cannot_replace(self):
        source = self.cold_result()
        first = self.publish(source)['generation_sha256']
        self.assertEqual(self.publish(source, first)['generation_sha256'], first)
        active = (self.responses / 'active.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'GENERATION_CONFLICT'):
            self.publish(self.cold_result(run='late-run'), None)
        self.assertEqual((self.responses / 'active.json').read_bytes(), active)

    def test_cold_reader_error_keeps_published_generation(self):
        first = self.publish()['generation_sha256']
        active = (self.responses / 'active.json').read_bytes()
        self.reader.side_effect = ValueError('HK_ARTIFACT_SHA_MISMATCH')
        with self.assertRaisesRegex(ValueError, 'HK_ARTIFACT_SHA_MISMATCH'):
            self.publish(expected=first)
        self.assertEqual((self.responses / 'active.json').read_bytes(), active)

    def test_invalid_metadata_is_rejected_before_publication(self):
        cases = [
            ('kind', lambda r: r['provenance'].update(data_kind='OWNER_RESULT')),
            ('natural', lambda r: r.update(natural_verified=True)),
            ('formal', lambda r: r['provenance'].update(formal_admission=True)),
            ('production', lambda r: r['artifact'].update(production_allowed=True)),
            ('orders', lambda r: r.update(orders_sent=True)),
            ('missing-input', lambda r: r['provenance'].pop('input_sha256')),
            ('bad-input', lambda r: r['provenance'].update(input_sha256='bad')),
            ('bad-time', lambda r: r['provenance']['source_identity'].update(captured_at='2026-10-08T09:35:00')),
            ('wrong-date', lambda r: r['artifact'].update(trade_date='20261009')),
            ('wrong-run', lambda r: r['artifact'].update(run_id='different')),
            ('a-market', lambda r: r['reference'].update(market='A_SHARE')),
            ('unknown-stage', lambda r: r['reference'].update(stage_id='UNKNOWN')),
        ]
        for label, mutate in cases:
            with self.subTest(case=label):
                source = self.cold_result(); mutate(source)
                with self.assertRaises(ValueError):
                    self.publish(source)
                self.assertFalse((self.responses / 'active.json').exists())

    def test_reader_reference_substitution_is_rejected(self):
        source = self.cold_result()
        requested = copy.deepcopy(source['reference'])
        source['reference']['generation_sha256'] = 'b' * 64
        self.reader.return_value = source
        with self.assertRaisesRegex(ValueError, 'HK_API_REFERENCE_MISMATCH'):
            self.api.publish_hk_stage_response(self.config, self.store, requested, expected_generation=None)
        self.assertFalse((self.responses / 'active.json').exists())

    def test_wrong_module_or_route_is_rejected_without_read(self):
        for config in ({**self.config, 'module_id': 'a_stage'}, {**self.config, 'routes': ['/other']}):
            with self.subTest(config=config):
                with self.assertRaisesRegex(ValueError, 'HK_API_CONFIG'):
                    self.api.publish_hk_stage_response(config, self.store, self.cold_result()['reference'], expected_generation=None)
        self.reader.assert_not_called()


class HKStageAPIIntegrationTests(unittest.TestCase):
    def test_original_owner_store_cold_reader_and_published_api(self):
        # No injected readers, selectors, stores, or producers in this test.
        from test_hk_stage_daily import request, stage8_request
        from v5_shadow.hk_stage_daily import init_hk_root, run_hk_stage
        from v5_shadow.hk_stage_api import publish_hk_stage_response
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            store = root / 'private-store'; init_hk_root(store)
            responses = root / 'responses'; responses.mkdir()
            (responses / '.v5-module-root').write_text('v5.module-root.v1:hk_stage\n')
            config = dict(schema_version='v5.module_api.v1', module_id='hk_stage',
                          release_id='m08-real-owner-fixture', data_root=str(responses), routes=[ROUTE])
            generation = None
            published = []
            for value in (request(count=3), request('STAGE_0925', count=3), stage8_request()):
                committed = run_hk_stage(value, store)
                result = publish_hk_stage_response(config, store, committed['reference'],
                                                   expected_generation=generation)
                generation = result['generation_sha256']
                query = dict(date=value['target_date'], stage=value['stage_id'],
                             run_id=committed['reference']['run_id'])
                checked_config, fd = _config(config)
                try:
                    record, _ = read_response(checked_config, fd, ROUTE, query)
                finally:
                    os.close(fd)
                payload = record['payload']
                self.assertEqual(payload['reference'], committed['reference'])
                self.assertEqual(payload['artifact']['rows'], committed['artifact']['rows'])
                self.assertEqual(payload['status'], committed['artifact']['selection_status'])
                self.assertEqual(record['data_kind'], 'SYNTHETIC')
                self.assertFalse(payload['natural_verified'])
                self.assertFalse(payload['provenance']['formal_admission'])
                self.assertNotIn(str(store), json.dumps(payload))
                self.assertEqual(payload['m10_stage_member'], value['stage_id'] != STAGE8)
                published.append((query, payload))
            # Published serving remains possible after its private source moves.
            store.rename(root / 'retained-private-store')
            server = create_module_server(config)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = 'http://127.0.0.1:' + str(server.server_address[1])
                for query, payload in published:
                    with urlopen(base + ROUTE + '?' + urlencode(query), timeout=3) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(json.load(response), payload)
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()

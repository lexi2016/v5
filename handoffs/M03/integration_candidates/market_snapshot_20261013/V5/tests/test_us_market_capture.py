"""Independent market-only capture through the real M03 cold chain."""
import unittest

from m03_fixture import SourceCase
from v5_shadow import us_source_daily as source_daily


class IndependentMarketCaptureTests(SourceCase):
    def test_market_only_capture_routes_to_independent_collector(self):
        self.assertIn(
            'market_snapshot_only', source_daily.USSourceRequest.__dataclass_fields__,
            'market-only capture is unavailable on the public source request',
        )
        request = self.request(
            market_snapshot_only=True, allow_network_capture=True,
            capture_root=self.root / 'capture', allow_late_post_close=True,
        )
        calls = []

        def inspect_collector(args, **kwargs):
            import subprocess
            calls.append(args)
            self.assertIn('v5_shadow.us_market_capture', args[4])
            self.assertIn('--request-json', args)
            import json
            sent = json.loads(args[args.index('--request-json') + 1])
            self.assertTrue(sent['market_snapshot_only'])
            self.assertTrue(sent['allow_network_capture'])
            self.assertEqual(sent['capture_root'], str(request.capture_root))
            return subprocess.CompletedProcess(args, 0, '', '')

        result = source_daily.run_cold_collector(request, runner=inspect_collector)
        self.assertEqual(result['returncode'], 0)
        self.assertEqual(len(calls), 1)


def collector_bootstrap(log_path, *, clock='2026-10-09T20:16:00Z', mode='ok'):
    """Replace only the original clock and HTTP opener seams in a cold child."""
    return r'''
import io, json, os, sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import v5_shadow.us_market_capture as capture
counts = {'quote': 0, 'rss': 0, 'direct': 0, 'socket': 0}
def deny(event, args):
    if event.startswith(('socket.connect', 'socket.getaddrinfo', 'socket.sendto')):
        counts['socket'] += 1
        raise AssertionError('REAL_NETWORK_FORBIDDEN')
sys.addaudithook(deny)
class Response(io.BytesIO):
    status = 200
class Proxy:
    def open(self, request, *args, **kwargs):
        url = request.full_url
        if 'news.google.com/rss/' in url:
            counts['rss'] += 1
            raise AssertionError('RSS_FORBIDDEN_IN_MARKET_ONLY_CAPTURE')
        assert 'qt.gtimg.cn' in url, url
        counts['quote'] += 1
        if MODE == 'connect_rejected':
            import urllib.error
            raise urllib.error.URLError('Tunnel connection failed: 403 Forbidden')
        if MODE == 'http_503':
            result = Response(b'upstream unavailable')
            result.status = 503
            return result
        records = []
        for name in url.split('q=', 1)[1].split(','):
            fields = [''] * 31
            fields[1] = name
            fields[2] = name[2:]
            fields[3] = '110'
            fields[4] = '100'
            fields[30] = '20261008160000' if MODE == 'stale' else '20261009160000'
            records.append('v_' + name + '="' + '~'.join(fields) + '";')
        return Response(('\n'.join(records)).encode())
class Direct:
    def open(self, *args, **kwargs):
        counts['direct'] += 1
        raise AssertionError('DIRECT_FORBIDDEN')
original_load_owner = capture.load_owner
def load_owner(root):
    owner, transport = original_load_owner(root)
    owner._capture_now = lambda value=None: datetime.fromisoformat(CLOCK.replace('Z', '+00:00'))
    return owner, transport
capture.load_owner = load_owner
original_guarded = capture.guarded_transport_class
def guarded_transport_class(owner_transport):
    guard = original_guarded(owner_transport)
    assert issubclass(guard, owner_transport.ProxyAwareHTTPTransport)
    class OfflineOriginalTransport(guard):
        def __init__(self, **kwargs):
            kwargs.update(proxy_url='http://proxy.invalid', proxy_opener=Proxy(), direct_opener=Direct())
            super().__init__(**kwargs)
    return OfflineOriginalTransport
capture.guarded_transport_class = guarded_transport_class
try:
    result = capture.main(sys.argv[2:])
finally:
    with Path(LOG).open('a') as handle:
        handle.write(json.dumps({'counts': counts, 'pid': os.getpid(), 'parent_pid': os.getppid()}) + '\n')
raise SystemExit(result)
'''.replace('MODE', repr(mode)).replace('CLOCK', repr(clock)).replace('LOG', repr(str(log_path)))


def offline_chain_runner(log_path, *, clock='2026-10-09T20:16:00Z', mode='ok'):
    """Keep run_us_source, the chain, and every cold reader unmodified."""
    import subprocess
    script = collector_bootstrap(log_path, clock=clock, mode=mode)
    setup = '''
import v5_shadow.us_source_daily as source_daily
original_run_cold_collector = source_daily.run_cold_collector
fixture_script = SCRIPT
def offline_collector_runner(args, **kwargs):
    args = list(args)
    assert args[:4] == [source_daily.sys.executable, '-I', '-B', '-c']
    assert 'v5_shadow.us_market_capture' in args[4], args[4]
    assert '--request-json' in args, args
    args[4] = fixture_script
    return source_daily.subprocess.run(args, **kwargs)
def run_cold_collector(request):
    return original_run_cold_collector(request, runner=offline_collector_runner)
source_daily.run_cold_collector = run_cold_collector
def deny(event, args):
    if event.startswith(('socket.connect', 'socket.getaddrinfo', 'socket.sendto')):
        raise AssertionError('REAL_NETWORK_FORBIDDEN')
sys.addaudithook(deny)
'''.replace('SCRIPT', repr(script))

    def run(args, **kwargs):
        args = list(args)
        marker = 'request = _request_from_dict'
        assert args[4].count(marker) == 1, args[4]
        args[4] = args[4].replace(marker, setup + '\n' + marker)
        return subprocess.run(args, **kwargs)

    return run


class MarketOnlyColdChainTests(SourceCase):
    def market_request(self, **changes):
        self.assertIn('market_snapshot_only', source_daily.USSourceRequest.__dataclass_fields__)
        values = dict(market_snapshot_only=True, allow_network_capture=True,
                      capture_root=self.root / 'capture', cutoff='2026-10-09T20:20:00Z')
        values.update(changes)
        return self.request(**values)

    def offline(self, request=None, *, clock='2026-10-09T20:16:00Z', mode='ok'):
        if request is None:
            request = self.market_request()
        return source_daily.run_us_source(
            request,
            runner=offline_chain_runner(self.root / 'capture-attempts.jsonl', clock=clock, mode=mode),
        )

    def attempts(self):
        import json
        path = self.root / 'capture-attempts.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def assert_no_network(self):
        for attempt in self.attempts():
            self.assertEqual(attempt['counts'], dict(quote=0, rss=0, direct=0, socket=0))

    def disk_bytes(self, root):
        return {str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob('*') if path.is_file()} if root.exists() else {}

    def test_market_only_real_capture_publishes_original_triplet_and_cold_reuses_it(self):
        import json
        import os
        request = self.market_request()
        result = self.offline(request)
        self.assertEqual(result['status'], 'VALIDATED_SOURCE_BINDING', result)
        self.assertEqual(result['source_status'], 'READY_EMPTY')
        snapshot = result['market_snapshot']
        self.assertEqual(snapshot['schema_version'], 'v3_5.us_market_snapshot.v1')
        self.assertEqual(snapshot['status'], 'READY')
        self.assertEqual(len(snapshot['quotes']), 33)
        self.assertEqual(len(snapshot['rows']), 24)
        self.assertTrue(all(row['status'] == 'READY' for row in snapshot['rows']))
        self.assertEqual(source_daily.parse_utc(snapshot['captured_at']), source_daily.parse_utc('2026-10-09T20:16:00Z'))
        self.assertNotEqual(snapshot['captured_at'], request.cutoff)
        self.assertTrue(result['identity']['original_time_capture'])
        for item in (result, snapshot):
            for key in ('production_allowed', 'orders_sent', 'buy_gate_updated'):
                self.assertIs(item[key], False)
        paths = source_daily.source_paths(request.capture_root, request.trade_date)
        saved = json.loads(paths['payload'].read_bytes())
        self.assertEqual(saved['status'], 'READY_EMPTY')
        self.assertEqual(saved['item_count'], 0)
        self.assertEqual(saved['raw_item_count'], 0)
        self.assertEqual(saved['items'], [])
        self.assertEqual(saved['details'], [])
        self.assertEqual(saved['overview'], [])
        self.assertEqual(saved['feed_receipts'], [])
        self.assertIn('NEWS_NOT_REQUESTED_QUOTE_ONLY_CAPTURE', saved['cannot_confirm'])
        capture = saved['us_session_captures'][0]
        self.assertEqual(capture['rss_status'], 'NOT_REQUESTED')
        self.assertEqual(capture['quote_capture_status'], 'ATTEMPTED')
        self.assertEqual(capture['rss_item_count'], 0)
        self.assertEqual(capture['rss_raw_item_count'], 0)
        self.assertEqual(saved['market_snapshot'], snapshot)
        self.assertEqual(len(list(request.capture_root.rglob('*.json'))), 3)
        self.assertFalse(request.source_root.exists())
        for key, path in paths.items():
            self.assertEqual(path.read_bytes(), source_daily.source_paths(request.snapshot_root, request.trade_date)[key].read_bytes())
        self.assertEqual(len(self.attempts()), 1)
        attempt = self.attempts()[0]
        self.assertEqual(attempt['counts'], dict(quote=1, rss=0, direct=0, socket=0))
        self.assertNotEqual(attempt['pid'], os.getpid())
        self.assertNotEqual(attempt['pid'], attempt['parent_pid'])
        before = self.disk_bytes(self.root)
        self.assertEqual(source_daily.read_cold_snapshot(request), saved)
        self.assertEqual(self.offline(request), result)
        self.assertEqual(self.disk_bytes(self.root), before)
        self.assertEqual(len(self.attempts()), 1, 'binding reuse must not recollect')
        self.assertEqual(len(list(request.binding_root.glob('*.json'))), 1)

    def test_network_authorization_is_never_implied_by_market_only_mode(self):
        request = self.market_request(allow_network_capture=False)
        result = self.offline(request)
        self.assertEqual(result['status'], 'SOURCE_MISSING')
        self.assertEqual(result['reason'], 'EXPLICIT_CAPTURE_REQUIRED')
        with self.assertRaisesRegex(ValueError, 'M03_CAPTURE_NOT_AUTHORIZED'):
            source_daily.run_cold_collector(request, runner=lambda *a, **k: self.fail('collector ran'))
        self.assertFalse(request.capture_root.exists())
        self.assertFalse(list(request.binding_root.glob('*.json')))
        self.assertEqual(self.attempts(), [])

    def test_capture_after_cutoff_fails_before_request(self):
        result = self.offline(self.market_request(cutoff='2026-10-09T20:15:59Z'))
        self.assertEqual(result['status'], 'COLLECTOR_FAILED', result)
        self.assertIn('M03_CAPTURE_AFTER_CUTOFF', result['stderr'])
        self.assert_no_network()
        self.assertFalse(list(self.bindings.glob('*.json')))
        self.assertFalse(list((self.root / 'capture').rglob('*.json')))

    def test_natural_window_and_late_recovery_flags_are_enforced(self):
        result = self.offline(clock='2026-10-09T21:00:00Z', request=self.market_request(cutoff='2026-10-09T21:05:00Z'))
        self.assertEqual(result['status'], 'COLLECTOR_FAILED', result)
        self.assertIn('US_CAPTURE_OUTSIDE_WINDOW', result['stderr'])
        self.assert_no_network()
        self.assertFalse(list(self.bindings.glob('*.json')))

    def test_closed_session_and_not_yet_due_skip_collection(self):
        for changes in (
            dict(trade_date='20261010', session='20261010', cutoff='2026-10-10T22:00:00Z'),
            dict(cutoff='2026-10-09T19:59:59Z'),
        ):
            with self.subTest(changes=changes):
                result = self.offline(self.market_request(**changes))
                self.assertEqual(result['status'], 'NOT_DUE')
        self.assertEqual(self.attempts(), [])
        self.assertFalse(list(self.bindings.glob('*.json')))

    def test_mismatched_session_and_non_boolean_capture_gate_are_rejected(self):
        for changes, message in (
            ({'session': '20261008'}, 'SESSION_DATE_MISMATCH'),
            ({'market_snapshot_only': 'true'}, 'BOOLEAN_REQUIRED'),
            ({'allow_network_capture': 'true'}, 'BOOLEAN_REQUIRED'),
        ):
            with self.subTest(changes=changes), self.assertRaisesRegex((ValueError, RuntimeError), message):
                self.offline(self.market_request(**changes))
        self.assertEqual(self.attempts(), [])
        self.assertFalse(list(self.bindings.glob('*.json')))

    def test_stale_quotes_preserve_original_cannot_confirm_without_binding(self):
        import json
        result = self.offline(mode='stale')
        self.assertEqual(result['status'], 'SOURCE_REJECTED', result)
        self.assertIn(result.get('reason'), (None, 'POST_CLOSE_MARKET_SNAPSHOT_NOT_READY'))
        payload_path = source_daily.source_paths(self.root / 'capture', '20261009')['payload']
        saved = json.loads(payload_path.read_bytes())
        self.assertEqual(saved['status'], 'CANNOT_CONFIRM')
        self.assertEqual(saved['market_snapshot']['status'], 'CANNOT_CONFIRM')
        from dataclasses import replace
        self.assertEqual(source_daily.read_cold_snapshot(replace(self.market_request(), snapshot_root=self.root / 'capture')), saved)
        self.assertEqual(len(list((self.root / 'capture').rglob('*.json'))), 3)
        self.assertEqual(self.attempts()[0]['counts'], dict(quote=1, rss=0, direct=0, socket=0))
        self.assertFalse(list(self.bindings.glob('*.json')))
        self.assertFalse(self.snapshot.exists())

    def test_http_and_proxy_connect_rejections_never_trigger_direct_fallback(self):
        from dataclasses import replace
        import json
        base = self.market_request()
        for mode in ('http_503', 'connect_rejected'):
            with self.subTest(mode=mode):
                request = replace(base, capture_root=self.root / mode,
                                  snapshot_root=self.root / ('snapshot-' + mode),
                                  binding_root=self.root / ('binding-' + mode))
                result = self.offline(request, mode=mode)
                self.assertEqual(result['status'], 'SOURCE_REJECTED', result)
                saved = json.loads(source_daily.source_paths(request.capture_root, request.trade_date)['payload'].read_bytes())
                self.assertEqual(saved['market_snapshot']['status'], 'CANNOT_CONFIRM')
                receipt = saved['market_snapshot']['provider_receipt']
                self.assertTrue(receipt['proxy_used'])
                self.assertFalse(receipt['fallback_used'])
                if mode == 'http_503':
                    self.assertEqual(receipt['http_status'], 503)
                else:
                    self.assertEqual(receipt['proxy_connect_status'], 403)
                    self.assertEqual(receipt['v5_transport_policy'], 'CONNECT_REJECTION_NO_DIRECT_FALLBACK')
                self.assertFalse(list(request.binding_root.glob('*.json')))
        self.assertEqual(len(self.attempts()), 2)
        for attempt in self.attempts():
            self.assertEqual(attempt['counts'], dict(quote=1, rss=0, direct=0, socket=0))

    def test_rejected_next_capture_preserves_successful_snapshot_and_binding(self):
        from dataclasses import replace
        request = self.market_request()
        success = self.offline(request)
        before_snapshot = self.disk_bytes(request.snapshot_root)
        before_binding = self.disk_bytes(request.binding_root)
        result = self.offline(replace(request, capture_root=self.root / 'rejected-capture'), mode='stale')
        self.assertEqual(result['status'], 'SOURCE_REJECTED', result)
        self.assertEqual(self.disk_bytes(request.snapshot_root), before_snapshot)
        self.assertEqual(self.disk_bytes(request.binding_root), before_binding)
        self.assertEqual(self.offline(request), success)
        self.assertEqual(len(self.attempts()), 2)

    def test_each_tampered_or_missing_snapshot_part_fails_and_preserves_binding(self):
        request = self.market_request()
        self.offline(request)
        before_binding = self.disk_bytes(request.binding_root)
        for key, path in source_daily.source_paths(request.snapshot_root, request.trade_date).items():
            raw = path.read_bytes()
            for alteration in ('tampered', 'missing'):
                with self.subTest(part=key, alteration=alteration):
                    if alteration == 'tampered':
                        path.write_bytes(raw + b' ')
                    else:
                        path.unlink()
                    try:
                        with self.assertRaises((ValueError, RuntimeError)):
                            self.offline(request)
                        self.assertEqual(self.disk_bytes(request.binding_root), before_binding)
                    finally:
                        path.write_bytes(raw)
        self.assertEqual(len(self.attempts()), 1)

    def test_each_tampered_or_missing_source_part_cannot_authorize_recapture(self):
        from dataclasses import replace
        request = self.market_request()
        self.offline(request)
        before_binding = self.disk_bytes(request.binding_root)
        for key, path in source_daily.source_paths(request.capture_root, request.trade_date).items():
            raw = path.read_bytes()
            for alteration in ('tampered', 'missing'):
                with self.subTest(part=key, alteration=alteration):
                    if alteration == 'tampered':
                        path.write_bytes(b'{}')
                    else:
                        path.unlink()
                    probe = replace(request, source_root=request.capture_root,
                                    capture_root=self.root / 'must-not-recapture',
                                    snapshot_root=self.root / ('probe-' + key + alteration),
                                    binding_root=self.root / ('probe-binding-' + key + alteration))
                    try:
                        with self.assertRaises((ValueError, RuntimeError)):
                            self.offline(probe)
                        self.assertFalse(list(probe.binding_root.glob('*.json')))
                        self.assertFalse(probe.capture_root.exists())
                        self.assertEqual(self.disk_bytes(request.binding_root), before_binding)
                    finally:
                        path.write_bytes(raw)
        self.assertEqual(len(self.attempts()), 1)

    def test_modified_owner_is_rejected_before_collector(self):
        import shutil
        from m03_fixture import OWNER
        copied_owner = self.root / 'modified-owner'
        shutil.copytree(OWNER, copied_owner)
        target = copied_owner / 'ops/us_market_digest.py'
        target.write_bytes(target.read_bytes() + b'\n# test-only mismatch\n')
        with self.assertRaisesRegex(RuntimeError, 'CLOUD_US_COLLECTOR_SOURCE_SHA'):
            self.offline(self.market_request(owner_root=copied_owner))
        self.assertEqual(self.attempts(), [])
        self.assertFalse(list(self.bindings.glob('*.json')))

    def test_unknown_test_clock_and_provider_fields_are_not_public_inputs(self):
        for key, value in (('captured_at', '2026-10-09T20:16:00Z'),
                           ('now', '2026-10-09T20:16:00Z'),
                           ('fetch_quotes', 'fixture'), ('transport_options', {}),
                           ('market_snapshot_onli', True)):
            with self.subTest(key=key), self.assertRaises(TypeError):
                source_daily._request_from_dict(dict(source_daily._request_dict(self.market_request()), **{key: value}))
        self.assertEqual(self.attempts(), [])

    def test_standalone_cli_defaults_to_market_only_and_reuses_verified_binding(self):
        import json
        import subprocess
        import sys
        from m03_fixture import BASE
        request = self.market_request()
        result = self.offline(request)
        values = source_daily._request_dict(request)
        values.pop('market_snapshot_only')
        request_path = self.root / 'standalone-request.json'
        request_path.write_text(json.dumps(values))
        proc = subprocess.run([sys.executable, '-I', '-B', str(BASE / 'run_market_source.py'),
                               '--request', str(request_path)], text=True, capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout), result)
        self.assertEqual(len(self.attempts()), 1)
        for option in ('--now', '--captured-at', '--fetch-quotes', '--provider'):
            with self.subTest(option=option):
                invalid = subprocess.run([sys.executable, '-I', '-B', str(BASE / 'run_market_source.py'),
                                          '--request', str(request_path), option, 'test'],
                                         text=True, capture_output=True, timeout=30)
                self.assertEqual(invalid.returncode, 2)
                self.assertIn('unrecognized arguments', invalid.stderr)
        values['market_snapshot_only'] = False
        request_path.write_text(json.dumps(values))
        invalid = subprocess.run([sys.executable, '-I', '-B', str(BASE / 'run_market_source.py'),
                                  '--request', str(request_path)], text=True, capture_output=True, timeout=30)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn('M03_STANDALONE_MARKET_ONLY_REQUIRED', invalid.stderr)

    def test_explicit_late_capture_uses_original_recovery_metadata_and_actual_clock(self):
        request = self.market_request(allow_late_post_close=True, cutoff='2026-10-10T10:00:00Z')
        result = self.offline(request, clock='2026-10-10T09:00:16Z')
        self.assertEqual(result['status'], 'VALIDATED_SOURCE_BINDING', result)
        self.assertTrue(result['identity']['late'])
        self.assertTrue(result['market_snapshot']['late'])
        self.assertEqual(source_daily.parse_utc(result['identity']['captured_at']),
                         source_daily.parse_utc('2026-10-10T09:00:16Z'))
        self.assertNotEqual(result['identity']['captured_at'], request.cutoff)
        self.assertEqual(result['identity']['capture_origin'], 'ORIGINAL_TIME_CAPTURE')
        self.assertEqual(self.attempts()[0]['counts'], dict(quote=1, rss=0, direct=0, socket=0))

    def test_expired_late_recovery_cannot_request_quotes(self):
        request = self.market_request(allow_late_post_close=True, cutoff='2026-10-10T21:05:00Z')
        result = self.offline(request, clock='2026-10-10T21:00:00Z')
        self.assertEqual(result['status'], 'COLLECTOR_FAILED', result)
        self.assertIn('US_LATE_POST_CLOSE_RECOVERY_WINDOW_EXPIRED', result['stderr'])
        self.assert_no_network()
        self.assertFalse(list(self.bindings.glob('*.json')))

    def test_valid_capture_triplet_recovers_new_binding_without_recollection(self):
        from dataclasses import replace
        request = self.market_request()
        first = self.offline(request)
        capture_before = self.disk_bytes(request.capture_root)
        recovered_request = replace(request, snapshot_root=self.root / 'recovered-snapshot',
                                    binding_root=self.root / 'recovered-binding')
        # The existing original capture remains valid; a fabricated fresh
        # request at this later test clock would fail the cutoff gate.
        recovered = self.offline(recovered_request, clock='2026-10-10T21:00:00Z')
        self.assertEqual(recovered['status'], 'VALIDATED_SOURCE_BINDING', recovered)
        self.assertEqual(recovered['identity'], first['identity'])
        self.assertEqual(recovered['market_snapshot'], first['market_snapshot'])
        self.assertEqual(self.disk_bytes(request.capture_root), capture_before)
        self.assertEqual(len(self.attempts()), 2)
        self.assertEqual(self.attempts()[1]['counts'], dict(quote=0, rss=0, direct=0, socket=0))
        for key, path in source_daily.source_paths(request.capture_root, request.trade_date).items():
            self.assertEqual(path.read_bytes(), source_daily.source_paths(recovered_request.snapshot_root, request.trade_date)[key].read_bytes())

    def test_damaged_existing_capture_is_never_repaired_by_recollection(self):
        from dataclasses import replace
        request = self.market_request()
        self.offline(request)
        before_binding = self.disk_bytes(request.binding_root)
        for key, path in source_daily.source_paths(request.capture_root, request.trade_date).items():
            raw = path.read_bytes()
            for alteration in ('tampered', 'missing'):
                with self.subTest(part=key, alteration=alteration):
                    if alteration == 'tampered':
                        path.write_bytes(b'{}')
                    else:
                        path.unlink()
                    probe = replace(request, snapshot_root=self.root / ('recovery-' + key + alteration),
                                    binding_root=self.root / ('recovery-binding-' + key + alteration))
                    try:
                        result = self.offline(probe)
                        self.assertEqual(result['status'], 'COLLECTOR_FAILED', result)
                        self.assertFalse(list(probe.binding_root.glob('*.json')))
                        self.assertFalse(probe.snapshot_root.exists())
                        self.assertEqual(self.disk_bytes(request.binding_root), before_binding)
                    finally:
                        path.write_bytes(raw)
        self.assertEqual(len(self.attempts()), 7)
        for attempt in self.attempts()[1:]:
            self.assertEqual(attempt['counts'], dict(quote=0, rss=0, direct=0, socket=0))

"""One fault boundary: persisted collector triplet, lost success response."""
import json
import subprocess
from unittest.mock import patch

import test_us_market_capture as capture_tests
from m03_fixture import SourceCase
from v5_shadow import us_source_daily as daily


class LostCaptureReplyTests(SourceCase):
    def test_real_persist_then_nonzero_reply_recovers_without_second_quote(self):
        req = self.request(market_snapshot_only=True, allow_network_capture=True,
                           capture_root=self.root / 'capture', cutoff='2026-10-09T20:20:00Z')
        log = self.root / 'calls.jsonl'
        original_bootstrap = capture_tests.collector_bootstrap

        def lost_reply(*args, **kwargs):
            script = original_bootstrap(*args, **kwargs)
            assert script.count('raise SystemExit(result)') == 1
            return script.replace('raise SystemExit(result)', 'raise SystemExit(17)')

        with patch.object(capture_tests, 'collector_bootstrap', lost_reply):
            failed = daily.run_us_source(req, runner=capture_tests.offline_chain_runner(log))
        self.assertEqual(failed['status'], 'COLLECTOR_FAILED')
        self.assertEqual(failed['returncode'], 17)
        self.assertFalse(req.snapshot_root.exists())
        self.assertFalse(list(req.binding_root.glob('*.json')))
        before = {key: path.read_bytes() for key, path in daily.source_paths(
            req.capture_root, req.trade_date).items()}
        result = daily.run_us_source(req, runner=capture_tests.offline_chain_runner(log))
        self.assertEqual(result['status'], 'VALIDATED_SOURCE_BINDING')
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual([row['counts']['quote'] for row in calls], [1, 0])
        for row in calls:
            self.assertEqual([row['counts'][key] for key in ('rss', 'direct', 'socket')], [0, 0, 0])
        for key, path in daily.source_paths(req.capture_root, req.trade_date).items():
            self.assertEqual(path.read_bytes(), before[key])
            self.assertEqual(daily.source_paths(req.snapshot_root, req.trade_date)[key].read_bytes(), before[key])

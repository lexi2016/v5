"""Standalone source package entry, from a non-repository working directory."""
import json
from pathlib import Path
import subprocess
import sys

from m03_fixture import SourceCase, BASE
from v5_shadow.us_source_daily import _request_dict


class MarketSourceEntryTests(SourceCase):
    def invoke(self, *args):
        return subprocess.run([sys.executable, '-I', '-B', str(BASE / 'run_market_source.py'),
                               *map(str, args)], cwd=self.root, capture_output=True, text=True)

    def test_help_from_outside_tree_never_creates_data(self):
        before = list(self.root.iterdir())
        result = self.invoke('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--request', result.stdout)
        self.assertEqual(list(self.root.iterdir()), before)

    def test_default_mode_is_market_only_and_no_capture_without_authorization(self):
        values = _request_dict(self.request())
        values.pop('market_snapshot_only')
        request = self.root / 'request.json'
        request.write_text(json.dumps(values))
        result = self.invoke('--request', request)
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         {'status': 'SOURCE_MISSING', 'reason': 'EXPLICIT_CAPTURE_REQUIRED'})
        self.assertFalse(self.source.exists())
        self.assertFalse(self.snapshot.exists())
        self.assertFalse(list(self.bindings.glob('*.json')))

    def test_unknown_fields_and_non_market_override_are_rejected(self):
        for field, value in [('provider', 'invented'), ('captured_at', '2026-10-09T20:16:00Z'),
                             ('market_snapshot_only', False)]:
            with self.subTest(field=field):
                values = _request_dict(self.request())
                values['market_snapshot_only'] = True
                values[field] = value
                request = self.root / 'request.json'
                request.write_text(json.dumps(values))
                result = self.invoke('--request', request)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stderr)['status'], 'FAILED')
                self.assertFalse(self.source.exists())
                self.assertFalse(self.snapshot.exists())
                self.assertFalse(self.bindings.exists())

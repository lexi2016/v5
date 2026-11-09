"""Offline containment regression: local timestamps are not review authority.

These tests install only synthetic bindings. They cannot grant real preparation,
review, delivery or natural-trigger acceptance.
"""
import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import unittest

import execution


ERROR = 'INDEPENDENT_REVIEW_TIME_AUTHORITY_UNBOUND_NO_FORMAL_RECEIPT'


class ReviewTimeQuarantineTests(unittest.TestCase):
    def setUp(self):
        self.chain = execution._controlled_chain()
        self.io, _ = execution.helpers()
        self.bridge = self.chain._bridge()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fd = self.io.directory_fd(self.root)
        self.addCleanup(os.close, self.fd)
        self.now = dt.datetime.fromisoformat('2026-11-09T19:00:00+08:00')
        self.cfg = {'run_date': '20261109'}
        self.core = {'schema': 'SYNTHETIC_ONLY', 'proof': {'reviewer_id': 'fixture'}}
        self.addCleanup(execution.REGISTRY.clear)

    def test_rewritten_freeze_checked_at_is_not_authority(self):
        # Original timestamp is before 18:30. The old implementation accepted
        # replacing only this unbound field by 18:40 without changing the proof.
        record = self.core | {'checked_at': '2026-11-09T18:00:00+08:00'}
        path = self.root / 'freeze.json'
        path.write_bytes(self.io.canonical(record))
        record['checked_at'] = '2026-11-09T18:40:00+08:00'
        changed = self.io.canonical(record)
        path.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, ERROR):
            self.chain._receipt(self.io, self.fd, 'freeze.json', self.core,
                                self.now, False, self.cfg, '1830', self.bridge)
        self.assertEqual(path.read_bytes(), changed)

    def test_rewritten_check_checked_at_is_not_authority(self):
        record = self.core | {'checked_at': '2026-11-09T18:49:59+08:00'}
        path = self.root / 'verification.json'
        path.write_bytes(self.io.canonical(record))
        record['checked_at'] = '2026-11-09T18:55:00+08:00'
        changed = self.io.canonical(record)
        path.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, ERROR):
            self.chain._receipt(self.io, self.fd, 'verification.json', self.core,
                                self.now, False, self.cfg, '1850', self.bridge)
        self.assertEqual(path.read_bytes(), changed)

    def test_creation_does_not_manufacture_original_review_time(self):
        with self.assertRaisesRegex(ValueError, ERROR):
            self.chain._receipt(self.io, self.fd, 'freeze.json', self.core,
                                self.now, True, self.cfg, '1830', self.bridge)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_private_package_path_blocks_before_io(self):
        with self.assertRaisesRegex(ValueError, ERROR):
            self.chain._package({}, '1830', 'synthetic', None, None, None,
                                {}, self.now, self.bridge)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_registered_call_blocks_before_owner_and_callbacks(self):
        calls = []
        @contextlib.contextmanager
        def owner():
            calls.append('owner')
            yield
        def review(**kwargs):
            calls.append('review')
            return {'self_reported_authoritative': True}
        for domain in ('isolated_test', 'reviewed_project'):
            cfg = dict(schema='EVENING_CONTROLLED_BINDING_V2', domain=domain,
                       owner_id='fixture-owner', task_id='fixture-task',
                       environment_id='fixture-env', run_id='fixture-run',
                       binding_version='fixture-v1', run_date='20261109',
                       source_contract_ref='SYNTHETIC_ONLY', authorization_ref='SYNTHETIC_ONLY',
                       calendar_ref='SYNTHETIC_ONLY', owner_context=owner,
                       gate=lambda: None, clock=lambda: self.now,
                       review_freeze=review, review_check=review,
                       review_time_authority_verified=True,
                       resolve_review_time_authority=review)
            execution.REGISTRY['synthetic'] = cfg
            for stage, action in (('1830', 'deliver'), ('1850', 'deliver'),
                                  ('1900', 'prepare'), ('1900', 'deliver'),
                                  ('1900', 'reconcile')):
                with self.subTest(domain=domain, stage=stage, action=action):
                    result = execution.run(stage, 'synthetic', 'a' * 64, action=action)
                    self.assertIn(ERROR, result['reason'])
                    self.assertFalse(result['formal_freeze'])
                    self.assertFalse(result['sent'])
                    self.assertFalse(result['natural_verified'])
        self.assertEqual(calls, [])
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == '__main__':
    unittest.main()

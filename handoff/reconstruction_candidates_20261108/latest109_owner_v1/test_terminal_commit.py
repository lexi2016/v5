import fcntl
import json
import os
import pathlib
import tempfile
import types
import unittest
from unittest.mock import patch

import isolated_owner as owner


class TerminalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        bridge = types.SimpleNamespace(load_code=lambda: None, load_runtime=lambda: None, gate=lambda: None)
        self.modules = {
            'registered_rebuild': types.SimpleNamespace(checked=lambda *args: None, ACTION_SHA='fixture', CANDIDATE_SHA='fixture'),
            'registered_latest109_candidate': object(),
            'source': object(), 'regression': object(),
            'bridge': types.SimpleNamespace(Bridge=lambda p: bridge, MIN_MEMORY=0),
            'runner': types.SimpleNamespace(check_start=lambda *args: None, make_monitor=self.fail_after_lock),
            'monitor': types.SimpleNamespace(MEMORY_FLOOR=0, START=0, available=lambda: 2**30, check_resources=lambda *args: None),
        }

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def fail_after_lock(*args):
        raise RuntimeError('fixture failure after lock')

    def invoke(self):
        with patch.object(owner, 'load', side_effect=lambda path, name, sha: self.modules[name]):
            return owner.run(self.root, self.root, self.root, self.root / 'unused', self.root / 'attempt')

    def test_run_publishes_terminal_while_lock_held(self):
        observations = []
        real_link = os.link

        def link(src, dst, **kwargs):
            fd = os.open(self.root / 'ISOLATED_OWNER.lock', os.O_RDWR)
            try:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                observations.append(True)
            finally:
                os.close(fd)
            return real_link(src, dst, **kwargs)

        with patch.object(os, 'link', side_effect=link):
            result = self.invoke()
        self.assertEqual(observations, [True])
        saved = json.loads((self.root / 'attempt/RESULT.json').read_text())
        self.assertEqual(saved['status'], 'FAILED_OR_BLOCKED_PRESERVED')
        self.assertTrue(saved['lock_held_during_terminal'])
        self.assertNotIn('isolated_lock_released', saved)
        self.assertTrue(result['isolated_lock_released'])

    def test_publication_failure_raises_and_releases_lock(self):
        with patch.object(os, 'link', side_effect=OSError('fixture publication failure')):
            with self.assertRaisesRegex(OSError, 'publication failure'):
                self.invoke()
        self.assertFalse((self.root / 'attempt/RESULT.json').exists())
        self.assertTrue((self.root / 'attempt/RESULT.json.pending').exists())
        fd = os.open(self.root / 'ISOLATED_OWNER.lock', os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)

    def test_terminal_never_overwrites_existing(self):
        path = self.root / 'RESULT.json'
        path.write_text('original')
        with self.assertRaises(FileExistsError):
            owner.seal_terminal(path, {'status': 'fixture'})
        self.assertEqual(path.read_text(), 'original')

    def test_preflight_failure_is_atomic_but_does_not_claim_lock(self):
        with patch.object(owner, 'load', side_effect=RuntimeError('preflight fixture')):
            owner.run(self.root, self.root, self.root, self.root / 'unused', self.root / 'attempt')
        saved = json.loads((self.root / 'attempt/RESULT.json').read_text())
        self.assertFalse(saved['lock_held_during_terminal'])

    def test_existing_pending_evidence_is_preserved(self):
        path = self.root / 'RESULT.json'
        pending = self.root / 'RESULT.json.pending'
        pending.write_text('uncertain previous attempt')
        with self.assertRaises(FileExistsError):
            owner.seal_terminal(path, {'status': 'fixture'})
        self.assertEqual(pending.read_text(), 'uncertain previous attempt')
        self.assertFalse(path.exists())

    def test_directory_sync_failure_is_not_success(self):
        real_fsync = os.fsync
        calls = []
        def fsync(fd):
            calls.append(fd)
            if len(calls) == 2:
                raise OSError('fixture directory sync failure')
            return real_fsync(fd)
        with patch.object(os, 'fsync', side_effect=fsync):
            with self.assertRaisesRegex(OSError, 'directory sync'):
                self.invoke()
        self.assertTrue((self.root / 'attempt/RESULT.json').exists())
        # Existence is explicitly not evidence of a successful durable commit.


if __name__ == '__main__':
    unittest.main()

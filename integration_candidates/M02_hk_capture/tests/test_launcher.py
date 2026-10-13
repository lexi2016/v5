"""Offline launcher tests. The subprocess fixture contains no SDK or network code."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

LAUNCHER = Path(__file__).resolve().parents[1] / 'launcher.py'

FAKE_CAPTURE = '''import json, os
from pathlib import Path

def collect_hk_futu_rows(target_date, *, context_factory=None, batch_size=200,
                         minimum_universe_count=600, required_coverage_ratio=0.0):
    p = Path(os.environ['V35_HK_CAPTURE_PATH'])
    payload = dict(target_date=target_date, home=os.environ['HOME'],
                   capture_run_id=os.environ['V35_HK_CAPTURE_RUN_ID'],
                   defaults=[batch_size, minimum_universe_count, required_coverage_ratio],
                   context_factory_is_none=context_factory is None)
    for name in ('capture.json', 'capture.sdk.capture.json', 'capture.capture.json'):
        (p.parent / name).write_text(json.dumps(payload))
    return {'status': 'FAKE_CAPTURED'}
'''
FAKE_RECOVERY = '''def run_recovery(request):
    return dict(status='FAKE_RECOVERED', fields=sorted(request))
'''


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='m02-launcher-test-')
        self.base = Path(self.temp.name).resolve()
        self.bundle = self.base / 'candidate'
        self.bundle.mkdir()
        if LAUNCHER.exists():
            shutil.copyfile(LAUNCHER, self.bundle / 'launcher.py')
        self.facade = self.bundle / 'collector/ops/macos_research_panel_daily.py'
        self.facade.parent.mkdir(parents=True)
        self.facade.write_text(FAKE_CAPTURE)
        self.recovery = self.bundle / 'recovery/V5/src/v5_shadow/hk_membership_recovery.py'
        self.recovery.parent.mkdir(parents=True)
        self.recovery.write_text(FAKE_RECOVERY)
        self.home = self.base / 'real-home'
        self.home.mkdir()
        self.environment = dict(os.environ, HOME=str(self.home))
        self.output = self.base / 'capture-output'
        self.make_root(self.output)
        self.pin = self.repin()

    def tearDown(self):
        self.temp.cleanup()

    def make_root(self, path, recovery=False):
        path.mkdir(mode=0o700)
        kind = 'membership' if recovery else 'capture'
        (path / f'.v5-hk-{kind}-root').write_bytes(f'v5.hk-{kind}-root.v1\n'.encode())

    def repin(self):
        files = {}
        for path in sorted(self.bundle.rglob('*')):
            if path.is_file() and path.name != 'SOURCE_MANIFEST.json':
                raw = path.read_bytes()
                files[path.relative_to(self.bundle).as_posix()] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        raw = json.dumps(dict(schema_version='v5.m02.capture_candidate.sources.v1', files=files), sort_keys=True).encode()
        (self.bundle / 'SOURCE_MANIFEST.json').write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def run_cli(self, command='verify', *extra, env=None):
        return subprocess.run([sys.executable, '-B', str(self.bundle / 'launcher.py'), command,
                               '--expected-manifest-sha', self.pin, *extra],
                              env=self.environment if env is None else env,
                              text=True, capture_output=True, timeout=15)

    def capture(self, *extra, env=None, output=None):
        return self.run_cli('capture', '--target-date', '20261013', '--output-root',
                            str(output or self.output), *extra, env=env)

    def assert_failed(self, result, reason):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(reason, result.stdout + result.stderr)

    def test_verify_without_capture_or_import(self):
        self.facade.write_text("raise RuntimeError('MUST_NOT_IMPORT')\n")
        self.pin = self.repin()
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)['status'], 'VERIFIED')
        self.assertEqual(list(self.output.iterdir()), [self.output / '.v5-hk-capture-root'])

    def test_default_help_never_captures(self):
        p = subprocess.run([sys.executable, str(self.bundle / 'launcher.py')], capture_output=True, text=True, env=self.environment)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_capture_flag_required_before_import(self):
        self.facade.write_text("raise RuntimeError('MUST_NOT_IMPORT')\n")
        self.pin = self.repin()
        p = self.capture()
        self.assert_failed(p, 'LIVE_CAPTURE_REQUIRES_FLAG')
        self.assertNotIn('MUST_NOT_IMPORT', p.stdout + p.stderr)
        self.assertFalse((self.output / 'capture.claim.json').exists())

    def test_home_missing_or_empty_rejected(self):
        for home in (None, '', str(self.base / 'absent-home')):
            env = self.environment.copy()
            if home is None:
                env.pop('HOME', None)
            else:
                env['HOME'] = home
            self.assert_failed(self.capture('--allow-live-capture', env=env), 'HOME_REQUIRED')
        self.assertFalse((self.output / 'capture.claim.json').exists())

    def test_capture_preserves_home_and_defaults_and_creates_receipts(self):
        env = dict(self.environment, V35_HK_CAPTURE_PATH='/must/not/write', V35_HK_CAPTURE_RUN_ID='old')
        p = self.capture('--allow-live-capture', env=env)
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        raw = json.loads((self.output / 'capture.sdk.capture.json').read_bytes())
        self.assertEqual(raw['home'], str(self.home))
        self.assertEqual(raw['defaults'], [200, 600, 0.0])
        self.assertTrue(raw['context_factory_is_none'])
        self.assertTrue(raw['capture_run_id'].startswith('manual-'))
        self.assertNotEqual(raw['capture_run_id'], 'old')
        self.assertEqual(env['V35_HK_CAPTURE_RUN_ID'], 'old')
        claim = self.output / 'capture.claim.json'
        self.assertEqual(claim.stat().st_mode & 0o777, 0o400)
        receipt = json.loads((self.output / 'capture.result.json').read_bytes())
        self.assertEqual(receipt['status'], 'CAPTURE_COMPLETED')
        self.assertEqual(receipt['expected_manifest_sha256'], self.pin)
        self.assertEqual(set(receipt['files']), {'capture.json', 'capture.sdk.capture.json', 'capture.capture.json'})

    def test_once_claim_blocks_second_capture(self):
        self.assertEqual(self.capture('--allow-live-capture').returncode, 0)
        original = {p.name: p.read_bytes() for p in self.output.iterdir()}
        self.assert_failed(self.capture('--allow-live-capture'), 'CAPTURE_ALREADY_CLAIMED')
        self.assertEqual({p.name: p.read_bytes() for p in self.output.iterdir()}, original)

    def test_failed_capture_still_blocks_retry(self):
        self.facade.write_text("def collect_hk_futu_rows(target_date):\n    raise RuntimeError('FAKE_FAILURE')\n")
        self.pin = self.repin()
        self.assert_failed(self.capture('--allow-live-capture'), 'FAKE_FAILURE')
        self.assertTrue((self.output / 'capture.claim.json').exists())
        self.assertEqual(json.loads((self.output / 'capture.result.json').read_bytes())['status'], 'CAPTURE_FAILED')
        self.assert_failed(self.capture('--allow-live-capture'), 'CAPTURE_ALREADY_CLAIMED')

    def test_capture_lock_blocks_concurrent_launch(self):
        import fcntl
        with (self.output / '.v5-hk-capture-root').open('rb') as locked:
            fcntl.flock(locked, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assert_failed(self.capture('--allow-live-capture'), 'OUTPUT_LOCKED')
        self.assertFalse((self.output / 'capture.claim.json').exists())

    def test_existing_output_never_overwritten(self):
        (self.output / 'capture.json').write_text('original')
        self.assert_failed(self.capture('--allow-live-capture'), 'OUTPUT_NOT_FRESH')
        self.assertEqual((self.output / 'capture.json').read_text(), 'original')

    def test_root_requires_private_mode_and_exact_marker(self):
        self.output.chmod(0o755)
        self.assert_failed(self.capture('--allow-live-capture'), 'OUTPUT_NOT_PRIVATE')
        self.output.chmod(0o700)
        (self.output / '.v5-hk-capture-root').write_bytes(b'wrong')
        self.assert_failed(self.capture('--allow-live-capture'), 'OUTPUT_MARKER')

    def test_symlink_ancestry_and_marker_rejected(self):
        link = self.base / 'linked'
        link.symlink_to(self.output, target_is_directory=True)
        self.assert_failed(self.capture('--allow-live-capture', output=link), 'SYMLINK')
        marker = self.output / '.v5-hk-capture-root'
        marker.unlink()
        marker.symlink_to(self.home / 'marker')
        self.assert_failed(self.capture('--allow-live-capture'), 'SYMLINK')

    def test_candidate_overlap_and_v4_spelling_rejected(self):
        inner = self.bundle / 'capture-output'
        self.make_root(inner)
        self.assert_failed(self.capture('--allow-live-capture', output=inner), 'PROTECTED_PATH')
        self.assert_failed(self.capture('--allow-live-capture', output=self.base / 'V4' / 'anything'), 'PROTECTED_PATH')
        self.assert_failed(self.capture('--allow-live-capture', output=self.base), 'PROTECTED_PATH')

    def test_target_date_strict(self):
        p = self.run_cli('capture', '--allow-live-capture', '--output-root', str(self.output), '--target-date', '20260230')
        self.assert_failed(p, 'TARGET_DATE')
        self.assertFalse((self.output / 'capture.claim.json').exists())

    def test_bad_manifest_pin_rejected(self):
        self.pin = '0' * 64
        self.assert_failed(self.capture('--allow-live-capture'), 'MANIFEST_SHA_MISMATCH')
        self.assertFalse((self.output / 'capture.claim.json').exists())

    def test_changed_source_rejected_before_import(self):
        self.facade.write_text("raise RuntimeError('UNPINNED_IMPORT')\n")
        self.assert_failed(self.capture('--allow-live-capture'), 'SOURCE_MISMATCH')
        self.assertFalse((self.output / 'capture.claim.json').exists())

    def test_unlisted_source_rejected(self):
        (self.facade.parent / 'injected.py').write_text('pass\n')
        self.assert_failed(self.run_cli(), 'SOURCE_INVENTORY')

    def test_source_symlink_rejected(self):
        raw = self.facade.read_bytes()
        self.facade.unlink()
        target = self.base / 'outside.py'
        target.write_bytes(raw)
        self.facade.symlink_to(target)
        self.assert_failed(self.run_cli(), 'SYMLINK')

    def test_post_capture_source_mutation_rejected(self):
        self.facade.write_text(FAKE_CAPTURE.replace("return {'status': 'FAKE_CAPTURED'}", "Path(__file__).write_text('changed')\n    return {'status': 'FAKE_CAPTURED'}"))
        self.pin = self.repin()
        self.assert_failed(self.capture('--allow-live-capture'), 'SOURCE_MISMATCH')
        self.assertTrue((self.output / 'capture.claim.json').exists())
        self.assertEqual(json.loads((self.output / 'capture.result.json').read_bytes())['status'], 'CAPTURE_FAILED')

    def test_isolated_capture_ignores_pythonpath(self):
        hostile = self.base / 'hostile'
        hostile.mkdir()
        (hostile / 'ops').mkdir()
        (hostile / 'ops/__init__.py').write_text("raise RuntimeError('HOSTILE_IMPORT')\n")
        env = dict(self.environment, PYTHONPATH=str(hostile))
        p = self.capture('--allow-live-capture', env=env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_recovery_exact_four_fields_only(self):
        root = self.base / 'recovery-output'
        self.make_root(root, recovery=True)
        sdk = self.base / 'sdk.json'
        sdk.write_text('{}')
        request = dict(sdk_path=str(sdk), sdk_sha256=hashlib.sha256(sdk.read_bytes()).hexdigest(), output_root=str(root), target_date='20261013')
        path = self.base / 'request.json'
        path.write_text(json.dumps(request))
        p = self.run_cli('recover', '--request', str(path))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)['recovery']['fields'], sorted(request))
        request['context_factory'] = 'danger'
        path.write_text(json.dumps(request))
        self.assert_failed(self.run_cli('recover', '--request', str(path)), 'RECOVERY_REQUEST_FIELDS')

    def test_recovery_blocks_socket_creation(self):
        root = self.base / 'recovery-output'
        self.make_root(root, recovery=True)
        sdk = self.base / 'sdk.json'
        sdk.write_text('{}')
        request = self.base / 'request.json'
        request.write_text(json.dumps(dict(sdk_path=str(sdk), sdk_sha256=hashlib.sha256(sdk.read_bytes()).hexdigest(), output_root=str(root), target_date='20261013')))
        self.recovery.write_text("import socket\ndef run_recovery(request):\n    socket.socket()\n")
        self.pin = self.repin()
        self.assert_failed(self.run_cli('recover', '--request', str(request)), 'RECOVERY_NETWORK_FORBIDDEN')

    def test_known_active_v4_home_path_rejected_without_reading(self):
        path = self.home / 'Library/Application Support/com.lexi.v4.local/state/not-created'
        self.assert_failed(self.capture('--allow-live-capture', output=path), 'PROTECTED_PATH')
        self.assertFalse((self.home / 'Library').exists())

    def test_source_manifest_cannot_escape_bundle(self):
        manifest_path = self.bundle / 'SOURCE_MANIFEST.json'
        manifest = json.loads(manifest_path.read_bytes())
        manifest['files']['../escape.py'] = dict(sha256='0'*64, bytes=0)
        raw = json.dumps(manifest).encode()
        manifest_path.write_bytes(raw)
        self.pin = hashlib.sha256(raw).hexdigest()
        self.assert_failed(self.run_cli(), 'MANIFEST_PATH')

    def test_missing_pinned_module_cannot_fall_back(self):
        self.facade.write_text("from ops import forbidden_module\n")
        self.pin = self.repin()
        self.assert_failed(self.capture('--allow-live-capture'), 'UNBUNDLED_IMPORT')
        self.assertTrue((self.output / 'capture.claim.json').exists())

    def test_recovery_rejects_sdk_mismatch_without_import(self):
        root = self.base / 'recovery-output'
        self.make_root(root, recovery=True)
        sdk = self.base / 'sdk.json'
        sdk.write_text('{}')
        path = self.base / 'request.json'
        path.write_text(json.dumps(dict(sdk_path=str(sdk), sdk_sha256='0'*64, output_root=str(root), target_date='20261013')))
        self.recovery.write_text("raise RuntimeError('MUST_NOT_IMPORT')\n")
        self.pin = self.repin()
        p = self.run_cli('recover', '--request', str(path))
        self.assert_failed(p, 'SDK_SHA_MISMATCH')
        self.assertNotIn('MUST_NOT_IMPORT', p.stdout + p.stderr)


if __name__ == '__main__':
    unittest.main()

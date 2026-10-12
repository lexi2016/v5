"""Run the M02 overlay against byte-verified source handoff in a disposable tree.

No installation, service start, network, model acquisition, or active V4 writes.
Use --all to additionally report the retained downstream integration references.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

OVERLAY = (
    'src/v5_shadow/hk_source_daily.py',
    'src/v5_shadow/m02_input_snapshot.py',
    'src/v5_shadow/native_identity_reader.py',
    'tests/test_hk_source_daily.py',
    'tests/test_m02_snapshot.py',
    'tests/test_m02_readers.py',
    'tools/prepare_m02_request.py',
)
TESTS = ('test_hk_source_daily', 'test_m02_snapshot', 'test_m02_readers',
         'test_capture_master', 'test_hk_membership_recovery', 'test_hk_preselection',
         'test_provider_evidence', 'test_snapshot_recording')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all', action='store_true', help='Include retained manager integration references (manager source is intentionally absent).')
    args = parser.parse_args(argv)
    repo = Path(__file__).resolve().parents[2]
    scope = json.loads((repo/'handoffs/M02/PUBLICATION_SCOPE.json').read_text())
    source = repo/'handoffs/M02/source/V5'
    with tempfile.TemporaryDirectory(prefix='v5-m02-isolated-') as temporary:
        root = Path(temporary)/'V5'
        count = 0
        for row in scope['included_files']:
            prefix = 'handoffs/M02/source/V5/'
            if not row['target_path'].startswith(prefix):
                continue
            relative = row['target_path'][len(prefix):]
            raw = (source/relative).read_bytes()
            if hashlib.sha256(raw).hexdigest() != row['sha256']:
                raise ValueError('M02_ORIGINAL_SOURCE_SHA:' + relative)
            target = root/relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
            count += 1
        for relative in OVERLAY:
            target = root/relative; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repo/'V5'/relative, target)
        env = dict(os.environ, PYTHONPATH=str(root/'src') + os.pathsep + str(root/'tests'), PYTHONDONTWRITEBYTECODE='1')
        command = [sys.executable, '-B', '-m', 'unittest']
        command += ['discover', '-s', str(root/'tests'), '-v'] if args.all else ['-v', *TESTS]
        print('Verified original source files:', count, flush=True)
        print('Isolated unittest suite; no real three-source claim unless fixture test runs.', flush=True)
        return subprocess.run(command, cwd=root, env=env, check=False).returncode

if __name__ == '__main__':
    raise SystemExit(main())

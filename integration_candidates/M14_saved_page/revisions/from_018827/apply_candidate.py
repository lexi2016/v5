"""Hash-checked, explicit application to an isolated existing P0 checkout.

No network, package installs, runtime configuration changes, or service starts.
All target preimages are checked before any source replacement. Existing
matching after-images are accepted so rerunning is safe.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def clean_path(path):
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('ABSOLUTE_NONTRAVERSING_PATH_REQUIRED')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('SYMLINK_REJECTED')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, help='Absolute path of isolated existing P0 checkout')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    target = clean_path(Path(args.target))
    if not target.is_dir():
        parser.error('target checkout does not exist')
    candidate = Path(__file__).resolve().parent
    manifest = json.loads((candidate / 'verification.json').read_bytes())
    pending = []
    for record in manifest['files']:
        relative = Path(record['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('CANDIDATE_PATH')
        source = clean_path(candidate / 'files' / relative)
        raw = source.read_bytes()
        if digest(raw) != record['after_sha256']:
            raise ValueError('CANDIDATE_SHA:' + str(relative))
        destination = clean_path(target / relative)
        if destination.exists() and not destination.is_file():
            raise ValueError('TARGET_NOT_FILE:' + str(relative))
        before = digest(destination.read_bytes()) if destination.exists() else None
        if before == record['after_sha256']:
            continue
        if before != record['before_sha256']:
            raise ValueError('PREIMAGE_MISMATCH:' + str(relative))
        pending.append((destination, raw))
    if not args.check_only:
        for destination, raw in pending:
            destination.parent.mkdir(parents=True, exist_ok=True)
            clean_path(destination)
            descriptor, name = tempfile.mkstemp(prefix='.m14-apply-', dir=destination.parent)
            try:
                with os.fdopen(descriptor, 'wb') as stream:
                    stream.write(raw)
                os.replace(name, destination)
            finally:
                if Path(name).exists():
                    Path(name).unlink()
    print(json.dumps(dict(status='PREIMAGES_VERIFIED' if args.check_only else 'APPLIED',
                          changed_files=len(pending), base_commit=manifest['base_commit']), sort_keys=True))


if __name__ == '__main__':
    main()

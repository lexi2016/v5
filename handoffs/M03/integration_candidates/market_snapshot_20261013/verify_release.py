"""Verify the fixed candidate's raw bytes without importing any owner or data."""
import hashlib
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'RELEASE.json').read_bytes())
    entries = manifest['files']
    paths = [row['path'] for row in entries]
    if len(paths) != len(set(paths)):
        raise ValueError('DUPLICATE_RELEASE_PATH')
    for row in entries:
        relative = Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('RELEASE_PATH_INVALID')
        path = root / relative
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise ValueError('RELEASE_SYMLINK')
        raw = path.read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('RELEASE_FILE_MISMATCH:' + row['path'])
    print(json.dumps({'status': 'CANDIDATE_BYTES_VERIFIED', 'files': len(entries),
                      'capture_executed': False, 'owner_executed': False}, sort_keys=True))


if __name__ == '__main__':
    main()

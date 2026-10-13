"""Read-only standard-library checksum verification for this fixed M07 handoff."""
from pathlib import Path
import hashlib
import json


def main():
    handoff = Path(__file__).resolve().parents[1]
    repository = handoff.parents[1]
    manifest = json.loads((handoff / 'DELIVERY.json').read_text())
    failures = []
    for item in manifest['files']:
        path = repository / item['path']
        if path.is_symlink() or not path.is_file():
            failures.append(item['path'] + ': not a regular file')
            continue
        raw = path.read_bytes()
        if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
            failures.append(item['path'] + ': bytes or SHA mismatch')
    closure = json.loads((handoff / 'OWNER_CLOSURE.json').read_text())
    for item in closure['entries']:
        raw = (handoff / 'owner' / item['path']).read_bytes()
        if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
            failures.append('owner/' + item['path'] + ': closure mismatch')
    print(json.dumps({'status': 'FAIL' if failures else 'PASS',
                      'files_checked': len(manifest['files']),
                      'owner_files_checked': len(closure['entries']),
                      'failures': failures}, ensure_ascii=False))
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())

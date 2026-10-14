"""Read-only checks for the explicitly shipped P0 resource manifests.

This is a finite packaging check, not an attestation of all module closures.
No owner is imported or executed and no dependency is installed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import tomllib

from .composition import no_symlinks
from .health import observe_dependencies

RUNTIME_MANIFESTS = (
    'm04_readonly_runtime.json', 'm06_readonly_runtime.json', 'm07_runtime.json',
    'm08_readonly_runtime.json', 'm09_readonly_runtime.json', 'm10_readonly_runtime.json',
    'm11_runtime.json', 'm12_runtime.json', 'm16_readonly_runtime.json',
    'source_owner_runtime.json',
)


def _read(path, limit):
    path = no_symlinks(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('RESOURCE_SIZE_OR_TYPE')
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
        fields = ('st_ino', 'st_dev', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if len(raw) != info.st_size or any(getattr(info, k) != getattr(after, k) for k in fields):
            raise ValueError('RESOURCE_CHANGED')
        return raw


def check_resources(base):
    base = no_symlinks(Path(base))
    rows, errors, unique = [], [], set()
    references = 0
    for name in RUNTIME_MANIFESTS:
        try:
            raw = _read(base / 'contracts' / name, 4 * 1024 * 1024)
            entries = json.loads(raw)['entries']
            if not isinstance(entries, list) or not entries:
                raise ValueError('RESOURCE_ENTRIES_INVALID')
            row = dict(manifest='contracts/' + name, sha256=hashlib.sha256(raw).hexdigest(), entries=len(entries))
            rows.append(row)
            for entry in entries:
                relative = entry['path']
                try:
                    if (not isinstance(relative, str) or '\\' in relative
                            or any(p in ('', '.', '..') for p in relative.split('/'))
                            or Path(relative).is_absolute()):
                        raise ValueError('RESOURCE_PATH_INVALID')
                    if not re.fullmatch('[0-9a-f]{64}', str(entry.get('sha256'))):
                        raise ValueError('RESOURCE_SHA_INVALID')
                    data = _read(base / relative, 64 * 1024 * 1024)
                    if hashlib.sha256(data).hexdigest() != entry['sha256']:
                        raise ValueError('RESOURCE_SHA_MISMATCH')
                    if 'bytes' in entry and len(data) != entry['bytes']:
                        raise ValueError('RESOURCE_BYTES_MISMATCH')
                    unique.add(relative)
                except (OSError, ValueError, TypeError) as exc:
                    errors.append(dict(manifest=name, path=relative, reason=str(exc)))
                references += 1
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(dict(manifest=name, reason=str(exc)))
    return dict(status='MISMATCH' if errors else 'MATCH',
                scope='Ten existing P0 runtime resource manifests only',
                manifests=rows, entry_references=references, unique_files=len(unique), errors=errors,
                complete_release_verified=False, owner_execution='NOT_RUN',
                business_verified=False, natural_verified=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resources-only', action='store_true', help='Do not inspect installed dependency versions')
    args = parser.parse_args(argv)
    base = Path(__file__).resolve().parents[2]
    result = check_resources(base)
    if not args.resources_only:
        lock = base / 'uv.lock'
        try:
            lock_raw = _read(lock, 4 * 1024 * 1024)
            declared = tomllib.loads(_read(base / 'pyproject.toml', 1024 * 1024).decode())['project']['requires-python']
            if not re.fullmatch(r'>=\d+\.\d+', declared):
                raise ValueError('PYTHON_REQUIREMENT_UNSUPPORTED')
            compatible = tuple(map(int, platform.python_version_tuple()[:2])) >= tuple(map(int, declared[2:].split('.')))
            dependencies = observe_dependencies(lock)
            result.update(dependencies=dependencies, dependency_lock_sha256=hashlib.sha256(lock_raw).hexdigest(),
                          python_version=platform.python_version(), python_requirement=declared, python_compatible=compatible)
            if dependencies['status'] != 'MATCH' or not compatible:
                result['status'] = 'MISMATCH'
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result['status'] = 'MISMATCH'
            result['errors'].append(dict(reason=str(exc)))
    else:
        result['dependencies'] = dict(status='NOT_RUN')
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'MATCH' else 3


if __name__ == '__main__':
    raise SystemExit(main())

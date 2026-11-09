"""Read-only M07 admission using the repository's existing pinned owner closure.

This explicitly replaces the missing restored-directory binding, without
reconstructing its historical SOURCE_MANIFEST or admitting a live owner.
"""
from pathlib import Path
import hashlib
import importlib.abc
import importlib.util
import json
import os
import re
import stat
import sys
import tempfile

BASE = Path(__file__).absolute().parents[2]
MANIFEST = BASE / 'contracts/m07_runtime.json'
MANIFEST_SHA256 = '1e3302422d31a595eab83552efe3ba201f56f288f7072288f3e0067978e067c4'
OWNER_COMMIT = 'e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31'
ENTRY_SHA256 = '01c791dee6547e5e1a54ef3c412ac3102dfcafdf7e78be34c702b053f6fb5791'
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_REQUEST_BYTES = 1024 * 1024


def _bytes(path):
    path = Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('M07_REPOSITORY_DEPENDENCY_SYMLINK')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('M07_REPOSITORY_REGULAR_FILE_REQUIRED')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            value = stream.read(MAX_FILE_BYTES + 1)
        if len(value) > MAX_FILE_BYTES:
            raise ValueError('M07_REPOSITORY_FILE_TOO_LARGE')
        return value
    finally:
        os.close(fd)


def _repository_sources():
    raw = _bytes(MANIFEST)
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError('M07_REPOSITORY_MANIFEST_CHANGED')
    manifest = json.loads(raw)
    if manifest.get('schema_version') != 'v5.m07_runtime.v1' or manifest.get('source_commit') != OWNER_COMMIT:
        raise ValueError('M07_REPOSITORY_MANIFEST_IDENTITY')
    sources = {}
    for item in manifest['entries']:
        relative = Path(item['path'])
        if (relative.is_absolute() or '..' in relative.parts or '\\' in item['path']
                or relative.as_posix() != item['path']
                or not (item['path'].startswith('source_owners/m07/')
                        or item['path'] == 'src/v5_shadow/m07_owner_worker.py')):
            raise ValueError('M07_REPOSITORY_PATH')
        path = BASE / relative
        value = _bytes(path)
        if len(value) != item['bytes'] or hashlib.sha256(value).hexdigest() != item['sha256']:
            raise ValueError('M07_REPOSITORY_DEPENDENCY_CHANGED')
        prefix = 'source_owners/m07/V5/src/'
        if item['path'].startswith(prefix) and item['path'].endswith('.py'):
            name = item['path'][len(prefix):-3].replace('/', '.')
            package = name.endswith('.__init__')
            if package:
                name = name[:-9]
            sources[name] = (str(path), value, package)
    if hashlib.sha256(sources['v5_shadow.a_stage_daily'][1]).hexdigest() != ENTRY_SHA256:
        raise ValueError('M07_ORIGINAL_ENTRY_CHANGED')
    return sources


class _PinnedShadowLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Compile checked byte snapshots, never reopen checked Python sources."""
    def __init__(self, sources):
        self.sources = sources

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.sources:
            return importlib.util.spec_from_loader(fullname, self,
                                                  is_package=self.sources[fullname][2])
        if fullname == 'v5_shadow' or fullname.startswith('v5_shadow.'):
            raise ImportError('M07_UNPINNED_SHADOW_MODULE')
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        filename, raw, package = self.sources[module.__name__]
        module.__file__ = filename
        if package:
            module.__path__ = []
        exec(compile(raw, filename, 'exec'), module.__dict__)


def _precise_request_times(request):
    # Preserve original time/cutoff gates by rejecting lossy parser inputs.
    # This is source-admission validation, not a new formula or time authority.
    recording = request.get('recording')
    values = [request.get('cutoff')]
    if isinstance(recording, dict):
        values.extend(recording.get(key) for key in ('captured_at', 'acquired_at'))
    for value in values:
        if isinstance(value, str) and re.search(r'[.,][0-9]{7,}', value):
            raise ValueError('M07_SOURCE_TIME_PRECISION_UNSUPPORTED')
        if isinstance(value, str) and re.search(r'[+-][0-9:]+[.,][0-9]+$', value):
            raise ValueError('M07_SOURCE_OFFSET_PRECISION_UNSUPPORTED')


def main():
    sources = _repository_sources()
    if any(name == 'v5_shadow' or name.startswith('v5_shadow.') for name in sys.modules):
        raise ValueError('M07_FRESH_VERIFIER_PROCESS_REQUIRED')
    sys.meta_path.insert(0, _PinnedShadowLoader(sources))
    import v5_shadow.a_stage_daily as m
    request_raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    if len(request_raw) > MAX_REQUEST_BYTES:
        raise ValueError('M07_SOURCE_REQUEST_TOO_LARGE')
    request = json.loads(request_raw)
    _precise_request_times(request)
    m._load_owner()  # Rechecks and loads the unchanged 97-file original closure.
    with tempfile.TemporaryDirectory(prefix='m07-source-admission-') as temp:
        roots, originals = m._snapshots(request, Path(temp))
        m._guard((Path(temp),))
        spec, pool, raw, rows = m._admit(request, roots)
        for key, files in originals.items():
            for name, data in files.items():
                if m._bytes(m._path(roots[key], name)) != data:
                    raise ValueError('ORIGINAL_READER_MUTATED_INPUT')
        m._owner_sources()
        _repository_sources()
        known_synthetic = any('SYNTHETIC' in str(value).upper()
                              for value in [raw['source_id'], *raw['source_evidence']])
        return dict(status='VERIFIED', known_synthetic=known_synthetic,
                    pool_codes=sorted(pool.codes), source_id=raw['source_id'],
                    rows=len(rows), missing_symbols=raw['missing_symbols'],
                    recording={key: raw[key] for key in
                               ('run_id', 'artifact_sha256', 'manifest_sha256', 'receipt_sha256')})


if __name__ == '__main__':
    try:
        print(json.dumps(main(), sort_keys=True))
    except Exception as error:
        print(json.dumps(dict(status='BLOCKED', reason=str(error))))
        raise SystemExit(2)

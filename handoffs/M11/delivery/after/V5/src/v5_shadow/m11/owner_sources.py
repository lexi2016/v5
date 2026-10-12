"""Pinned original bytes; this descriptor is NOT the missing original manifest."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

SOURCE_PIN = 'bfbc299147708f6874bfa0f80db4618639f9f7e50e67592af677e21d808315c0'
BUILD_MANIFEST_SHA = 'c824e9b9bfdbda716c7f2ce25e584866f99913c224662550d0e68deb8e4bd558'
V5 = Path(__file__).absolute().parents[3]
OWNER_ROOT = V5 / 'vendor/research_review_baseline'
DESCRIPTOR = V5 / 'vendor/research_review_baseline.sources.json'


def _read(path: Path) -> bytes:
    # Code trees are immutable operator-owned inputs, never request-supplied paths.
    import os
    import stat
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in path.parts[1:-1]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
        child = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(child, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError('M11_SOURCE_NOT_REGULAR')
            return stream.read()
    finally:os.close(fd)


def verify_sources() -> dict:
    raw = _read(DESCRIPTOR)
    if hashlib.sha256(raw).hexdigest() != SOURCE_PIN:raise ValueError('M11_SOURCE_DESCRIPTOR_DRIFT')
    descriptor = json.loads(raw)
    expected = {e['path'] for e in descriptor['files']}
    actual = {str(p.relative_to(OWNER_ROOT)) for p in OWNER_ROOT.rglob('*') if p.is_file() or p.is_symlink()}
    if actual != expected:raise ValueError('M11_SOURCE_CLOSURE_DRIFT')
    for entry in descriptor['files']:
        value = _read(OWNER_ROOT / entry['path'])
        if len(value) != entry['bytes'] or hashlib.sha256(value).hexdigest() != entry['sha256']:
            raise ValueError('M11_SOURCE_BYTES_DRIFT')
    return descriptor


def safe_root_class():
    verify_sources()
    name = '_v5_m11_original_owned_io'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, OWNER_ROOT / 'infrastructure/owned_io.py')
        module = importlib.util.module_from_spec(spec)
        # Compile the same no-follow bytes that were just pinned, avoiding pycache.
        exec(compile(_read(Path(spec.origin)), spec.origin, 'exec'), module.__dict__)
        sys.modules[name] = module
    return sys.modules[name].SafeRoot


def implementation_sha256():
    """Bind adapter changes as well as donor bytes into every new run identity."""
    entries=[]
    for path in sorted(Path(__file__).parent.glob('*.py')):
        entries.append((path.name,hashlib.sha256(_read(path.absolute())).hexdigest()))
    return hashlib.sha256(json.dumps({'donor':SOURCE_PIN,'adapter':entries},sort_keys=True).encode()).hexdigest()

"""M16 manifest-bound owner closure loader.

Loads only an explicitly frozen private owner closure. It does not import the
whole application, bypass manifest guards, or substitute simulated providers.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


class SourceClosureError(RuntimeError):
    pass


@dataclass(frozen=True)
class OwnerClosure:
    root: Path
    manifest_path: Path
    manifest_sha256: str
    members: tuple[str, ...]


def _sha256_file(path: Path) -> str:
    h = sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load_owner(closure: OwnerClosure) -> dict[str, Any]:
    if not closure.root.is_dir():
        raise SourceClosureError('MANAGER_SOURCE_CLOSURE_ROOT_MISSING')
    if not closure.manifest_path.is_file():
        raise SourceClosureError('MANAGER_SOURCE_CLOSURE_MANIFEST_MISSING')
    if _sha256_file(closure.manifest_path) != closure.manifest_sha256:
        raise SourceClosureError('MANAGER_SOURCE_CLOSURE_MANIFEST_HASH')
    try:
        manifest = json.loads(closure.manifest_path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise SourceClosureError('MANAGER_SOURCE_CLOSURE_MANIFEST_INVALID') from exc
    members = manifest.get('members')
    if not isinstance(members, list):
        raise SourceClosureError('MANAGER_SOURCE_CLOSURE_MEMBERS_MISSING')
    checked = {}
    for item in members:
        if not isinstance(item, dict):
            raise SourceClosureError('MANAGER_SOURCE_CLOSURE_MEMBER_INVALID')
        rel = item.get('path')
        expected = item.get('sha256')
        if not isinstance(rel, str) or not isinstance(expected, str):
            raise SourceClosureError('MANAGER_SOURCE_CLOSURE_MEMBER_FIELDS')
        path = closure.root / rel
        if not path.is_file():
            raise SourceClosureError(f'MANAGER_SOURCE_MEMBER_MISSING:{rel}')
        actual = _sha256_file(path)
        if actual != expected:
            raise SourceClosureError(f'MANAGER_SOURCE_MEMBER_HASH:{rel}')
        checked[rel] = actual
    return {'root': closure.root, 'members': checked, 'manifest': closure.manifest_path}

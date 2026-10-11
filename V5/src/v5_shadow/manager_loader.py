"""M16 manifest-bound owner closure loader.

This loader validates the frozen source manifest before loading owner classes.
It does not accept caller builders, substitute providers, or bypass the
source-closure guard.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from typing import Any


class SourceClosureError(RuntimeError):
    pass


REQUIRED_COMPONENTS = (
    "v4/manager_research/service.py",
    "v4/manager_research/store.py",
    "v4/manager_research/hkex_provider.py",
    "v4/manager_research/materials.py",
)


@dataclass(frozen=True)
class OwnerClosure:
    root: Path
    manifest_path: Path
    manifest_sha256: str
    members: tuple[str, ...]


@dataclass(frozen=True)
class OwnerComponents:
    service_class: type
    store_class: type
    provider_class: type
    material_store_class: type


def _sha256_file(path: Path) -> str:
    h = sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _safe_member(root: Path, rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute() or '..' in p.parts or not rel or '\\x00' in rel:
        raise SourceClosureError('MANAGER_SOURCE_MEMBER_PATH')
    target = (root / p)
    if target.is_symlink() or any(parent.is_symlink() for parent in target.parents if parent != root):
        raise SourceClosureError('MANAGER_SOURCE_MEMBER_SYMLINK')
    return target


def _load_module(root: Path, rel: str, name: str):
    path = _safe_member(root, rel)
    if not path.is_file():
        raise SourceClosureError(f'MANAGER_SOURCE_MEMBER_MISSING:{rel}')
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SourceClosureError(f'MANAGER_SOURCE_IMPORT:{rel}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if Path(getattr(module, '__file__', '')).resolve() != path.resolve():
        raise SourceClosureError(f'MANAGER_SOURCE_ORIGIN:{rel}')
    return module


def load_owner(closure: OwnerClosure) -> dict[str, Any]:
    if not closure.root.is_dir():
        raise SourceClosureError('MANAGER_SOURCE_CLOSURE_ROOT_MISSING')
    if _sha256_file(closure.manifest_path) != closure.manifest_sha256:
        raise SourceClosureError('MANAGER_SOURCE_CLOSURE_MANIFEST_HASH')
    try:
        raw = closure.manifest_path.read_bytes()
        manifest = json.loads(raw.decode('utf-8'))
    except Exception as exc:
        raise SourceClosureError('MANAGER_SOURCE_CLOSURE_MANIFEST_INVALID') from exc
    if not isinstance(manifest, list):
        raise SourceClosureError('MANAGER_SOURCE_CLOSURE_MANIFEST_SHAPE')

    selected = {}
    for item in manifest:
        package_path = item.get('package_path') if isinstance(item, dict) else None
        if isinstance(package_path, str) and package_path.startswith('fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/'):
            rel = package_path.split('/canonical/', 1)[1]
            if rel.startswith('v4/manager_research/') or rel in ('infrastructure/owned_io.py', 'infrastructure/trading_safety.py'):
                selected[rel] = item

    for required in REQUIRED_COMPONENTS:
        if required not in selected:
            raise SourceClosureError(f'MANAGER_SOURCE_REQUIRED_MISSING:{required}')

    if len(selected) != len(set(selected)):
        raise SourceClosureError('MANAGER_SOURCE_DUPLICATE_MEMBER')

    checked = {}
    for rel, item in selected.items():
        path = _safe_member(closure.root, rel)
        if not path.is_file() or _sha256_file(path) != item.get('sha256'):
            raise SourceClosureError(f'MANAGER_SOURCE_MEMBER_HASH:{rel}')
        checked[rel] = item.get('sha256')

    service = _load_module(closure.root, 'v4/manager_research/service.py', 'm16_owner_service')
    store = _load_module(closure.root, 'v4/manager_research/store.py', 'm16_owner_store')
    provider = _load_module(closure.root, 'v4/manager_research/hkex_provider.py', 'm16_owner_provider')
    materials = _load_module(closure.root, 'v4/manager_research/materials.py', 'm16_owner_materials')

    return {
        'members': checked,
        'manifest': closure.manifest_path,
        'components': OwnerComponents(
            service.ManagerResearchJobService,
            store.ManagerResearchStore,
            provider.HkexOfficialProvider,
            materials.MaterialStore,
        ),
    }

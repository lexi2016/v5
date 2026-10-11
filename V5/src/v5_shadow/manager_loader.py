"""M16 manifest-bound owner closure loader.

Loads the frozen manager_research owner as an isolated package alias.  The
loader validates source identity before importing classes and never falls back
to host v4 modules or shared sys.path resolution.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


class SourceClosureError(RuntimeError):
    pass


PREFIX = "fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/"
REQUIRED = tuple(
    [
        f"v4/manager_research/{name}.py"
        for name in (
            "__init__", "contracts", "hkex_provider", "material_transport",
            "materials", "service", "store", "event_source", "pdf_parser",
            "ports", "reader_source", "recommendation", "cache_contract",
            "errors", "safety", "financial_projection",
            "catalyst_projection", "workspace_read_control",
        )
    ]
    + ["infrastructure/owned_io.py", "infrastructure/trading_safety.py"]
)


@dataclass(frozen=True)
class OwnerClosure:
    root: Path
    manifest_path: Path
    manifest_sha256: str
    members: tuple[str, ...] = ()


@dataclass(frozen=True)
class OwnerComponents:
    service_class: type
    store_class: type
    provider_class: type
    material_store_class: type


def _sha256_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_member(root: Path, rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts or not rel or "\x00" in rel:
        raise SourceClosureError("MANAGER_SOURCE_MEMBER_PATH")
    out = root / p
    if out.is_symlink() or any(x.is_symlink() for x in out.parents if x != root):
        raise SourceClosureError("MANAGER_SOURCE_MEMBER_SYMLINK")
    return out


def _load_package(root: Path):
    package = "m16_owner_manager_research"
    init_path = _safe_member(root, "v4/manager_research/__init__.py")
    spec = importlib.util.spec_from_file_location(
        package,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise SourceClosureError("MANAGER_SOURCE_PACKAGE_SPEC")
    module = importlib.util.module_from_spec(spec)
    sys.modules[package] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(package, None)
        raise
    return package


def _load_class(package: str, module: str, name: str):
    qualified = f"{package}.{module}"
    mod = __import__(qualified, fromlist=[name])
    if Path(getattr(mod, "__file__", "")).resolve() != Path(mod.__file__).resolve():
        raise SourceClosureError("MANAGER_SOURCE_ORIGIN")
    return getattr(mod, name)


def load_owner(closure: OwnerClosure) -> dict[str, Any]:
    if not closure.root.is_dir():
        raise SourceClosureError("MANAGER_SOURCE_CLOSURE_ROOT_MISSING")
    raw = closure.manifest_path.read_bytes()
    if _sha256_file(closure.manifest_path) != closure.manifest_sha256:
        raise SourceClosureError("MANAGER_SOURCE_CLOSURE_MANIFEST_HASH")
    manifest = json.loads(raw.decode("utf-8"))
    if not isinstance(manifest, list):
        raise SourceClosureError("MANAGER_SOURCE_CLOSURE_MANIFEST_SHAPE")

    selected = {}
    for item in manifest:
        rel = item.get("package_path", "") if isinstance(item, dict) else ""
        if isinstance(rel, str) and rel.startswith(PREFIX):
            short = rel.split("/canonical/", 1)[1]
            if short in REQUIRED:
                if short in selected:
                    raise SourceClosureError("MANAGER_SOURCE_DUPLICATE_MEMBER")
                selected[short] = item
    if set(selected) != set(REQUIRED):
        raise SourceClosureError("MANAGER_SOURCE_REQUIRED_SET")

    for rel, item in selected.items():
        path = _safe_member(closure.root, rel)
        if not path.is_file() or _sha256_file(path) != item["sha256"]:
            raise SourceClosureError(f"MANAGER_SOURCE_MEMBER_HASH:{rel}")

    package = _load_package(closure.root)
    return {
        "members": selected,
        "components": OwnerComponents(
            _load_class(package, "service", "ManagerResearchJobService"),
            _load_class(package, "store", "ManagerResearchStore"),
            _load_class(package, "hkex_provider", "HkexOfficialProvider"),
            _load_class(package, "materials", "MaterialStore"),
        ),
    }

"""M16 manifest-bound owner closure loader.

Loads the frozen manager_research owner as an isolated package alias.  The
loader validates source identity before importing classes and never falls back
to host v4 modules or shared sys.path resolution.
"""
from __future__ import annotations

import builtins
from dataclasses import dataclass
from hashlib import sha256
import importlib.abc
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
from threading import RLock
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
    p = PurePosixPath(rel)
    if (p.is_absolute() or ".." in p.parts or not rel or "\x00" in rel
            or "\\" in rel or p.as_posix() != rel):
        raise SourceClosureError("MANAGER_SOURCE_MEMBER_PATH")
    out = root / p
    if out.is_symlink() or any(x.is_symlink() for x in out.parents):
        raise SourceClosureError("MANAGER_SOURCE_MEMBER_SYMLINK")
    return out


_PACKAGE = "m16_owner_manager_research"
_INFRA = _PACKAGE + "._infrastructure"
_LOCK = RLock()
_STATE = None


def _is_owner_name(name: str) -> bool:
    return name == _PACKAGE or name.startswith(_PACKAGE + ".")


class _BoundOwner(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """An importlib boundary for this owner only, never a host import path.

    Every executed source is checked against the pinned manifest. Only the
    two existing infrastructure imports are rebound, through per-module
    builtins; the process's infrastructure and v4 packages are untouched.
    """

    def __init__(self, root: Path, selected: dict[str, dict]):
        self.root = root
        self.selected = selected
        self.modules = {}
        self.paths = {}
        for rel in selected:
            if rel.startswith("v4/manager_research/"):
                tail = rel[len("v4/manager_research/"):]
                name = _PACKAGE + "." + tail[:-3].replace("/", ".")
                if name.endswith(".__init__"):
                    name = name[:-len(".__init__")]
            else:
                name = _INFRA + "." + Path(rel).stem
            self.paths[name] = rel

    def source(self, name):
        rel = self.paths[name]
        path = _safe_member(self.root, rel)
        try:
            raw = path.read_bytes()
        except OSError:
            raise SourceClosureError(f"MANAGER_SOURCE_MEMBER_HASH:{rel}") from None
        if sha256(raw).hexdigest() != self.selected[rel]["sha256"]:
            raise SourceClosureError(f"MANAGER_SOURCE_MEMBER_HASH:{rel}")
        return path, raw

    def check_loaded(self):
        for name in tuple(sys.modules):
            if _is_owner_name(name):
                if name not in self.modules or sys.modules[name] is not self.modules[name]:
                    raise SourceClosureError("MANAGER_SOURCE_ALIAS_CONFLICT")
                module = self.modules[name]
                spec = getattr(module, "__spec__", None)
                if spec is None or spec.loader is not self or module.__loader__ is not self:
                    raise SourceClosureError("MANAGER_SOURCE_ORIGIN")
                if name in self.paths:
                    expected = _safe_member(self.root, self.paths[name])
                    if (getattr(module, "__file__", None) != str(expected)
                            or spec.origin != str(expected)):
                        raise SourceClosureError("MANAGER_SOURCE_ORIGIN")
        for name, module in self.modules.items():
            if sys.modules.get(name) is not module:
                raise SourceClosureError("MANAGER_SOURCE_ALIAS_CONFLICT")

    def find_spec(self, fullname, path=None, target=None):
        if not _is_owner_name(fullname):
            return None
        if fullname == _INFRA:
            return importlib.util.spec_from_loader(fullname, self, is_package=True)
        if fullname not in self.paths:
            raise SourceClosureError("MANAGER_SOURCE_UNBOUND_IMPORT")
        member = self.paths[fullname]
        # Empty search locations prevent any filesystem or host fallback.
        locations = [] if member.endswith("/__init__.py") else None
        return importlib.util.spec_from_file_location(
            fullname, self.root / member, loader=self,
            submodule_search_locations=locations,
        )

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        name = module.__name__
        self.modules[name] = module
        try:
            if name != _INFRA:
                path, raw = self.source(name)
                namespace = dict(vars(builtins), __import__=self.import_source)
                module.__dict__["__builtins__"] = namespace
                # Execute exactly the verified bytes, never a cached .pyc.
                exec(compile(raw, str(path), "exec"), module.__dict__)
        except BaseException:
            self.modules.pop(name, None)
            raise

    def import_source(self, name, globals=None, locals=None, fromlist=(), level=0):
        self.check_loaded()
        if level:
            resolved = importlib.util.resolve_name("." * level + name, globals["__package__"])
            if not _is_owner_name(resolved):
                raise SourceClosureError("MANAGER_SOURCE_UNBOUND_IMPORT")
        elif name == "infrastructure" or name.startswith("infrastructure."):
            mapped = _INFRA + name[len("infrastructure"):]
            imported = builtins.__import__(mapped, globals, locals, fromlist, 0)
            return imported if fromlist else sys.modules[_INFRA]
        elif not _is_owner_name(name) and name.split(".", 1)[0] not in sys.stdlib_module_names:
            raise SourceClosureError("MANAGER_SOURCE_UNBOUND_IMPORT")
        return builtins.__import__(name, globals, locals, fromlist, level)

    def remove_failed_load(self):
        for name, module in self.modules.items():
            if sys.modules.get(name) is module:
                sys.modules.pop(name)
        if self in sys.meta_path:
            sys.meta_path.remove(self)


def _load_class(bound: _BoundOwner, module: str, name: str):
    qualified = f"{_PACKAGE}.{module}"
    mod = importlib.import_module(qualified)
    bound.check_loaded()
    cls = getattr(mod, name, None)
    expected = str(_safe_member(bound.root, bound.paths[qualified]))
    constructor = getattr(getattr(cls, "__init__", None), "__code__", None)
    if (not isinstance(cls, type) or cls.__module__ != qualified
            or constructor is None or constructor.co_filename != expected):
        raise SourceClosureError("MANAGER_SOURCE_CLASS_ORIGIN")
    return cls


def load_owner(closure: OwnerClosure) -> dict[str, Any]:
    global _STATE
    if not closure.root.is_dir():
        raise SourceClosureError("MANAGER_SOURCE_CLOSURE_ROOT_MISSING")
    # Reject aliases through symlinked roots before normalizing identity.
    _safe_member(closure.root, "v4/manager_research/__init__.py")
    root = closure.root.absolute()
    raw = closure.manifest_path.read_bytes()
    if sha256(raw).hexdigest() != closure.manifest_sha256:
        raise SourceClosureError("MANAGER_SOURCE_CLOSURE_MANIFEST_HASH")
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise SourceClosureError("MANAGER_SOURCE_CLOSURE_MANIFEST_SHAPE") from None
    if not isinstance(manifest, list):
        raise SourceClosureError("MANAGER_SOURCE_CLOSURE_MANIFEST_SHAPE")

    selected = {}
    for item in manifest:
        rel = item.get("package_path", "") if isinstance(item, dict) else ""
        if isinstance(rel, str) and rel.startswith(PREFIX):
            short = rel[len(PREFIX):]
            _safe_member(root, short)
            if short.endswith(".py") and (short.startswith("v4/manager_research/") or short in REQUIRED):
                if short in selected:
                    raise SourceClosureError("MANAGER_SOURCE_DUPLICATE_MEMBER")
                selected[short] = item
    if not set(REQUIRED).issubset(selected):
        raise SourceClosureError("MANAGER_SOURCE_REQUIRED_SET")
    for rel, item in selected.items():
        path = _safe_member(root, rel)
        if not path.is_file() or _sha256_file(path) != item.get("sha256"):
            raise SourceClosureError(f"MANAGER_SOURCE_MEMBER_HASH:{rel}")

    with _LOCK:
        first_load = _STATE is None
        if first_load:
            if any(_is_owner_name(name) for name in sys.modules):
                raise SourceClosureError("MANAGER_SOURCE_ALIAS_CONFLICT")
            bound = _BoundOwner(root, selected)
            sys.meta_path.insert(0, bound)
        else:
            bound = _STATE
            if bound.root != root or bound.selected != selected:
                raise SourceClosureError("MANAGER_SOURCE_ALIAS_CONFLICT")
        try:
            if first_load:
                importlib.import_module(_PACKAGE)
                # This dependency is first used in the original constructor.
                importlib.import_module(_PACKAGE + ".workspace_read_control")
            bound.check_loaded()
            components = OwnerComponents(
                _load_class(bound, "service", "ManagerResearchJobService"),
                _load_class(bound, "store", "ManagerResearchStore"),
                _load_class(bound, "hkex_provider", "HkexOfficialProvider"),
                _load_class(bound, "materials", "MaterialStore"),
            )
        except BaseException:
            if first_load:
                bound.remove_failed_load()
            raise
        # Publish only after every original class has passed its origin gate.
        _STATE = bound
        return {"members": selected, "components": components}

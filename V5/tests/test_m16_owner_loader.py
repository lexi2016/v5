"""Executable M16 assembly boundary tests using the fixed original owner.

The real four classes are constructed; no provider request or job is run.
Fixtures below test source integrity, not business or real-data acceptance.
"""
from dataclasses import replace
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import shutil
import socket
import sys
from types import ModuleType
import urllib.request

import pytest

from v5_shadow import manager_loader
from v5_shadow.manager_factory import BindingMissing, M16RuntimeConfig, build_manager_jobs
from v5_shadow.manager_loader import OwnerClosure, SourceClosureError, load_owner

PACKAGE = "m16_owner_manager_research"
SOURCE = Path(__file__).resolve().parents[2] / "handoffs/M16/source"
MANIFEST_SHA256 = "c8f72f9a64cb2dd0c1f37819156e7d26ec457097d3f2bffad79f2beeebeac2ea"


def fixed_closure():
    return OwnerClosure(
        SOURCE / manager_loader.PREFIX,
        SOURCE / "SOURCE_MANIFEST.json",
        MANIFEST_SHA256,
    )


@pytest.fixture(autouse=True)
def isolated_alias_and_no_network(monkeypatch):
    original_modules = {k: v for k, v in sys.modules.items() if k == PACKAGE or k.startswith(PACKAGE + ".")}
    original_meta_path = sys.meta_path[:]
    original_state = getattr(manager_loader, "_STATE", None)
    for name in original_modules:
        sys.modules.pop(name)
    monkeypatch.setattr(manager_loader, "_STATE", None, raising=False)
    calls = []

    def forbid(*args, **kwargs):
        calls.append(True)
        raise AssertionError("M16_ASSEMBLY_MUST_NOT_USE_NETWORK")

    monkeypatch.setattr(socket, "create_connection", forbid)
    monkeypatch.setattr(socket.socket, "connect", forbid)
    monkeypatch.setattr(urllib.request, "urlopen", forbid)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", forbid)
    yield
    for name in list(sys.modules):
        if name == PACKAGE or name.startswith(PACKAGE + "."):
            sys.modules.pop(name)
    sys.modules.update(original_modules)
    sys.meta_path[:] = original_meta_path
    manager_loader._STATE = original_state
    assert calls == []


@pytest.fixture
def copied_closure(tmp_path):
    original = fixed_closure()
    root = tmp_path / "source"
    shutil.copytree(original.root, root)
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(original.manifest_path.read_bytes())
    return OwnerClosure(root, manifest, original.manifest_sha256)


def rewrite_manifest(closure, edit):
    data = json.loads(closure.manifest_path.read_bytes())
    edit(data)
    raw = json.dumps(data).encode()
    closure.manifest_path.write_bytes(raw)
    return replace(closure, manifest_sha256=hashlib.sha256(raw).hexdigest())


def replace_member(closure, member, content):
    (closure.root / member).write_text(content)
    digest = hashlib.sha256(content.encode()).hexdigest()
    return rewrite_manifest(closure, lambda data: [
        item.update(sha256=digest) for item in data
        if item["package_path"] == manager_loader.PREFIX + member
    ])


class UnusedObservationReader:
    """An explicit sentinel: construction must not consume observations."""
    def read(self, date):
        raise AssertionError("ASSEMBLY_MUST_NOT_READ_OBSERVATIONS")


@pytest.mark.parametrize("host_present", [False, True])
def test_factory_constructs_four_original_objects_offline(tmp_path, monkeypatch, host_present):
    host = ModuleType("infrastructure")
    host.__path__ = []
    if host_present:
        monkeypatch.setitem(sys.modules, "infrastructure", host)
        monkeypatch.setitem(sys.modules, "infrastructure.owned_io", ModuleType("infrastructure.owned_io"))
    before_path = sys.path[:]
    before_host = {k: v for k, v in sys.modules.items() if k == "infrastructure" or k.startswith("infrastructure.")}
    closure = fixed_closure()
    reader = UnusedObservationReader()
    jobs = build_manager_jobs(config=M16RuntimeConfig(tmp_path / "runtime", closure), observation_reader=reader)
    try:
        components = load_owner(closure)["components"]
        service = jobs._service
        objects = [service, service.store, service.source_provider, service._material_store]
        classes = [components.service_class, components.store_class, components.provider_class, components.material_store_class]
        files = ["service.py", "store.py", "hkex_provider.py", "materials.py"]
        for obj, cls, filename in zip(objects, classes, files):
            assert type(obj) is cls
            assert Path(inspect.getfile(cls)).resolve() == (closure.root / "v4/manager_research" / filename).resolve()
        assert service.observation_reader is reader
        assert service.source_provider._material_store is service._material_store
        assert service.source_provider._material_transport._store is service._material_store
        assert service.store.root == tmp_path / "runtime"
        assert service._material_store.root == tmp_path / "runtime/materials"
        owned = sys.modules[type(service.store._io).__module__]
        assert Path(owned.__file__).resolve() == (closure.root / "infrastructure/owned_io.py").resolve()
        contracts = sys.modules[PACKAGE + ".contracts"]
        assert contracts.assert_safe_tree.__module__.startswith(PACKAGE + ".")
        assert sys.path == before_path
        assert {k: v for k, v in sys.modules.items() if k == "infrastructure" or k.startswith("infrastructure.")} == before_host
    finally:
        jobs.close()
    assert service._closed is True


def test_manifest_hash_tamper_rejected(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(b"[]")
    with pytest.raises(SourceClosureError, match="MANIFEST_HASH"):
        load_owner(OwnerClosure(tmp_path, manifest, "0" * 64))


def test_required_set_rejects_empty_manifest(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(b"[]")
    with pytest.raises(SourceClosureError, match="REQUIRED_SET"):
        load_owner(OwnerClosure(tmp_path, manifest, hashlib.sha256(b"[]").hexdigest()))


@pytest.mark.parametrize("member", ["infrastructure/owned_io.py", "infrastructure/trading_safety.py", "v4/manager_research/contracts.py"])
def test_missing_dependency_is_rejected_before_import(copied_closure, member):
    (copied_closure.root / member).unlink()
    with pytest.raises(SourceClosureError, match="MEMBER_HASH"):
        load_owner(copied_closure)
    assert PACKAGE not in sys.modules


@pytest.mark.parametrize("member", ["infrastructure/owned_io.py", "v4/manager_research/workspace_projection.py"])
def test_tampered_dependency_is_rejected(copied_closure, member):
    with (copied_closure.root / member).open("a") as handle:
        handle.write("\n# tampered\n")
    with pytest.raises(SourceClosureError, match="MEMBER_HASH"):
        load_owner(copied_closure)


@pytest.mark.parametrize("suffix", ["", ".service", "._infrastructure.owned_io"])
def test_existing_alias_is_rejected_without_overwrite(monkeypatch, suffix):
    name = PACKAGE + suffix
    alien = ModuleType(name)
    monkeypatch.setitem(sys.modules, name, alien)
    with pytest.raises(SourceClosureError, match="ALIAS_CONFLICT"):
        load_owner(fixed_closure())
    assert sys.modules[name] is alien


@pytest.mark.parametrize("field", ["__file__", "spec_origin", "class_origin"])
def test_cached_origin_or_class_substitution_is_rejected(field, monkeypatch):
    closure = fixed_closure()
    load_owner(closure)
    module = sys.modules[PACKAGE + ".service"]
    if field == "__file__":
        monkeypatch.setattr(module, "__file__", "wrong-origin.py")
    elif field == "spec_origin":
        monkeypatch.setattr(module.__spec__, "origin", "wrong-origin.py")
    else:
        monkeypatch.setattr(module, "ManagerResearchJobService", dict)
    with pytest.raises(SourceClosureError, match="ORIGIN"):
        load_owner(closure)


def test_relative_unmanifested_module_cannot_fall_back_to_directory(copied_closure):
    member = "v4/manager_research/workspace_projection.py"
    closure = rewrite_manifest(copied_closure, lambda data: data.__setitem__(slice(None), [
        x for x in data if x["package_path"] != manager_loader.PREFIX + member
    ]))
    load_owner(closure)
    with pytest.raises(SourceClosureError, match="UNBOUND_IMPORT"):
        importlib.import_module(PACKAGE + ".workspace_projection")


@pytest.mark.parametrize("statement", [
    "from infrastructure.unlisted import MARKER",
    "from external_m16_helper import MARKER",
    "from v4.manager_research.service import ManagerResearchJobService",
])
def test_unbound_absolute_import_rejects_host_fallback(copied_closure, monkeypatch, statement):
    member = "v4/manager_research/workspace_projection.py"
    closure = replace_member(copied_closure, member, statement + "\n")
    host = ModuleType("external_m16_helper")
    host.MARKER = "must not be used"
    monkeypatch.setitem(sys.modules, "external_m16_helper", host)
    load_owner(closure)
    with pytest.raises(SourceClosureError, match="UNBOUND_IMPORT"):
        importlib.import_module(PACKAGE + ".workspace_projection")


def test_lazy_relative_import_rechecks_bytes(copied_closure):
    load_owner(copied_closure)
    member = copied_closure.root / "v4/manager_research/workspace_projection.py"
    member.write_text("raise AssertionError('unverified code ran')\n")
    with pytest.raises(SourceClosureError, match="MEMBER_HASH"):
        importlib.import_module(PACKAGE + ".workspace_projection")


def test_import_failure_cleans_only_owned_aliases_and_allows_retry(copied_closure):
    member = "v4/manager_research/service.py"
    original = (copied_closure.root / member).read_text()
    broken = replace_member(copied_closure, member, "raise RuntimeError('bounded import failure')\n")
    before = sys.meta_path[:]
    with pytest.raises(RuntimeError, match="bounded import failure"):
        load_owner(broken)
    assert not any(k == PACKAGE or k.startswith(PACKAGE + ".") for k in sys.modules)
    assert sys.meta_path == before
    restored = replace_member(broken, member, original)
    assert load_owner(restored)["components"].service_class.__name__ == "ManagerResearchJobService"


@pytest.mark.parametrize("member", ["../outside.py", "/absolute.py", "v4/manager_research/../outside.py"])
def test_unsafe_manifest_member_is_rejected(copied_closure, member):
    closure = rewrite_manifest(copied_closure, lambda data: data.append({
        "package_path": manager_loader.PREFIX + member, "sha256": "0" * 64,
    }))
    with pytest.raises(SourceClosureError, match="MEMBER_PATH"):
        load_owner(closure)


def test_symlink_member_is_rejected(copied_closure, tmp_path):
    target = copied_closure.root / "infrastructure/owned_io.py"
    other = tmp_path / "other.py"
    target.rename(other)
    target.symlink_to(other)
    with pytest.raises(SourceClosureError, match="MEMBER_SYMLINK"):
        load_owner(copied_closure)


def test_duplicate_manifest_member_is_rejected(copied_closure):
    closure = rewrite_manifest(copied_closure, lambda data: data.append(next(
        x.copy() for x in data if x["package_path"] == manager_loader.PREFIX + "infrastructure/owned_io.py"
    )))
    with pytest.raises(SourceClosureError, match="DUPLICATE_MEMBER"):
        load_owner(closure)


def test_factory_requires_observation_binding(tmp_path):
    with pytest.raises(BindingMissing, match="OBSERVATION_READER_MISSING"):
        build_manager_jobs(config=M16RuntimeConfig(tmp_path, fixed_closure()), observation_reader=None)


def test_factory_requires_absolute_runtime():
    with pytest.raises(BindingMissing, match="RUNTIME_ROOT_NOT_ABSOLUTE"):
        build_manager_jobs(config=M16RuntimeConfig(Path("relative"), fixed_closure()), observation_reader=UnusedObservationReader())


def test_class_with_forged_module_name_is_rejected(monkeypatch):
    closure = fixed_closure()
    load_owner(closure)
    module = sys.modules[PACKAGE + ".service"]

    class Impostor:
        def __init__(self):
            pass

    Impostor.__module__ = module.__name__
    monkeypatch.setattr(module, "ManagerResearchJobService", Impostor)
    with pytest.raises(SourceClosureError, match="CLASS_ORIGIN"):
        load_owner(closure)


def test_second_root_cannot_replace_loaded_owner(copied_closure):
    original = load_owner(fixed_closure())["components"]
    with pytest.raises(SourceClosureError, match="ALIAS_CONFLICT"):
        load_owner(copied_closure)
    assert load_owner(fixed_closure())["components"] == original


def test_late_cached_submodule_injection_is_rejected(monkeypatch):
    closure = fixed_closure()
    load_owner(closure)
    name = PACKAGE + ".workspace_projection"
    alien = ModuleType(name)
    monkeypatch.setitem(sys.modules, name, alien)
    with pytest.raises(SourceClosureError, match="ALIAS_CONFLICT"):
        load_owner(closure)
    assert sys.modules[name] is alien


def test_first_class_origin_failure_rolls_back_then_original_loads(copied_closure):
    member = "v4/manager_research/service.py"
    original = (copied_closure.root / member).read_text()
    wrong_class = replace_member(copied_closure, member,
        "from .store import ManagerResearchStore as ManagerResearchJobService\n")
    before = sys.meta_path[:]
    with pytest.raises(SourceClosureError, match="CLASS_ORIGIN"):
        load_owner(wrong_class)
    assert not any(k == PACKAGE or k.startswith(PACKAGE + ".") for k in sys.modules)
    assert sys.meta_path == before
    assert manager_loader._STATE is None
    restored = replace_member(wrong_class, member, original)
    assert load_owner(restored)["components"].service_class.__name__ == "ManagerResearchJobService"

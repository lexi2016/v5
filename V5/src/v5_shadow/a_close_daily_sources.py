"""Verified M09 donor imports and the explicit admitted-frame producer I/O bridge.

All donor files are byte-exact copies. Their Python import statements resolve
inside one private namespace; no bare application package or pyarrow module is
installed globally. The daily entry owns real parquet admission, provenance,
cutoffs, and private-root authorization. This module then invokes the original
producer, original store, and an independent original reader.
"""
from __future__ import annotations

import builtins
from contextvars import ContextVar
from copy import deepcopy
import hashlib
import importlib.machinery
import importlib.metadata
import json
import math
from numbers import Real
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import threading
from types import ModuleType
from typing import Any, Mapping
from uuid import uuid4


BASE = Path(__file__).absolute().parents[2]
CAPSULE = BASE / "vendor/m09_a_close_daily"
DESCRIPTOR = BASE / "contracts/m09_a_close_daily_source_manifest.json"
DESCRIPTOR_SHA256 = "7e4f5eb41e0c8f6fc062d9d3f130af47a39eb5ae82a19389c9a5c0788a04901d"
DONOR_COMMIT = "f7cb731c384ee6890a87d16c19a5b5a621779477"
COLUMNS = (
    "trade_date", "ts_code", "name", "pct_chg", "amount", "bar_close_pos",
    "tdx_industry_code", "tdx_industry_name",
)
CONTEXT_KEYS = frozenset((
    "video_acceptance", "video_capture", "stockdict_pointer",
    "ocr_alignment_pointer", "video_gap_pointer",
))
_INTERNAL_ROOTS = frozenset(("ops", "domains", "contracts", "infrastructure"))
_ORIGINAL_IMPORT = builtins.__import__
_LOAD_LOCK = threading.RLock()
_NAMESPACE = None
_PANEL_BINDING: ContextVar[Any] = ContextVar("m09_admitted_frame_binding", default=None)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _absolute(path: Path | str) -> Path:
    raw = Path(path)
    if not raw.is_absolute() or ".." in raw.parts:
        raise ValueError("M09_PATH_MUST_BE_ABSOLUTE_WITHOUT_TRAVERSAL")
    return raw


def _regular_snapshot(path: Path | str, *, retain: bool = False, max_bytes: int | None = None):
    """Read/hash the opened regular inode through O_NOFOLLOW at every level."""
    path = _absolute(path)
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("M09_SOURCE_IO_PLATFORM_UNSUPPORTED")
    parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("M09_SOURCE_NOT_REGULAR")
            if max_bytes is not None and before.st_size > max_bytes:
                raise ValueError("M09_SOURCE_TOO_LARGE")
            digest = hashlib.sha256()
            pieces = []
            count = 0
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                if max_bytes is not None and count > max_bytes:
                    raise ValueError("M09_SOURCE_TOO_LARGE")
                digest.update(chunk)
                if retain:
                    pieces.append(chunk)
            after = os.fstat(fd)
            named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            if identity(before) != identity(after) or identity(after) != identity(named) or count != before.st_size:
                raise ValueError("M09_SOURCE_CHANGED_DURING_READ")
            record = {"sha256": digest.hexdigest(), "bytes": count, "inode": identity(after)}
            return b"".join(pieces) if retain else None, record
        finally:
            os.close(fd)
    finally:
        os.close(parent)


_EXECUTING_LOADER_SHA256 = _regular_snapshot(Path(__file__).absolute(), max_bytes=1024 * 1024)[1]["sha256"]


def _verified_sources():
    try:
        _, loader = _regular_snapshot(Path(__file__).absolute(), max_bytes=1024 * 1024)
        if loader["sha256"] != _EXECUTING_LOADER_SHA256:
            raise ValueError("M09_SOURCE_LOADER_CHANGED_RESTART_REQUIRED")
        descriptor_raw, _ = _regular_snapshot(DESCRIPTOR, retain=True, max_bytes=1024 * 1024)
        if hashlib.sha256(descriptor_raw).hexdigest() != DESCRIPTOR_SHA256:
            raise ValueError("M09_SOURCE_MANIFEST_SHA")
        descriptor = json.loads(descriptor_raw)
        if descriptor.get("schema_version") != "v5.m09.a_close_daily_capsule.v1" or descriptor.get("source_commit") != DONOR_COMMIT:
            raise ValueError("M09_SOURCE_MANIFEST_IDENTITY")
        entries = descriptor["entries"]
        if not isinstance(entries, list) or len(entries) != 16:
            raise ValueError("M09_SOURCE_MANIFEST_ENTRIES")
        sources, identities = {}, {}
        for entry in entries:
            relative = entry["relative_path"]
            parsed = PurePosixPath(relative)
            if parsed.is_absolute() or ".." in parsed.parts or "\\" in relative or relative in sources:
                raise ValueError("M09_SOURCE_MANIFEST_PATH")
            raw, meta = _regular_snapshot(CAPSULE / relative, retain=True, max_bytes=1024 * 1024)
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
            if meta["sha256"] != entry["sha256"] or len(raw) != entry["bytes"] or blob != entry["source_git_blob_sha1"]:
                raise ValueError("M09_SOURCE_BYTES_CHANGED:" + relative)
            sources[relative] = raw
            identities[relative] = {
                "sha256": entry["sha256"], "bytes": entry["bytes"],
                "git_blob_sha1": blob, "source_path": entry["source_path"],
                "target_path": entry["target_path"],
            }
        return sources, identities
    except (OSError, KeyError, TypeError, UnicodeError) as error:
        raise ValueError("M09_SOURCE_UNAVAILABLE") from error


def sources_identity() -> dict[str, Any]:
    """Verify descriptor and every source on each call, including cached imports."""
    _, identities = _verified_sources()
    runtime = {}
    # Include pandas' installed mandatory dependency closure in calculation
    # identity; an unchanged pandas version alone does not pin numpy behavior.
    for dependency in ("pandas", "pyarrow", "numpy", "python-dateutil", "pytz", "tzdata", "six"):
        try:
            runtime[dependency] = importlib.metadata.version(dependency)
        except importlib.metadata.PackageNotFoundError:
            runtime[dependency] = None
    _, loader = _regular_snapshot(Path(__file__).absolute(), max_bytes=1024 * 1024)
    return {
        "schema_version": "v5.m09.a_close_daily_sources.v1",
        "descriptor_sha256": DESCRIPTOR_SHA256,
        "donor_repository": "lexi2016/v4", "donor_commit": DONOR_COMMIT,
        "files": identities, "loader_sha256": loader["sha256"],
        "python": sys.version, "runtime_dependencies": runtime,
        "producer_io_adaptation": "ADMITTED_FRAME_DATASET_ADAPTER",
    }


class _FrozenCalendarPath:
    """Supply only verified JSON bytes to the original lazy calendar loader."""
    def read_text(self, *, encoding="utf-8"):
        sources, _ = _verified_sources()
        return sources["contracts/market_calendar_2026.json"].decode(encoding)


class _Filter:
    def __init__(self, column, value):
        self.column, self.value = column, value


class _Field:
    def __init__(self, column):
        self.column = column

    def __eq__(self, value):
        return _Filter(self.column, value)


def _frame_digest(frame) -> str:
    return hashlib.sha256(_json_bytes({
        "columns": list(frame.columns), "dtypes": [str(kind) for kind in frame.dtypes],
        "rows": frame.to_dict("records"),
    })).hexdigest()


def _validate_frame(frame, trade_date: str) -> None:
    import pandas as pd

    if not isinstance(frame, pd.DataFrame) or tuple(frame.columns) != COLUMNS or not 1 <= len(frame) <= 20_000:
        raise ValueError("M09_ADMITTED_FRAME_SCHEMA")
    seen = set()
    for row in frame.to_dict("records"):
        if not isinstance(row["trade_date"], str) or row["trade_date"] != trade_date:
            raise ValueError("M09_ADMITTED_FRAME_DATE")
        code = row["ts_code"]
        if not isinstance(code, str) or not re.fullmatch(r"[0-9]{6}\.(SH|SZ|BJ)", code) or code in seen:
            raise ValueError("M09_ADMITTED_FRAME_CODE")
        seen.add(code)
        for key in ("name", "tdx_industry_code", "tdx_industry_name"):
            if not isinstance(row[key], str) or not row[key].strip():
                raise ValueError("M09_ADMITTED_FRAME_TEXT")
        for key in ("pct_chg", "amount", "bar_close_pos"):
            if isinstance(row[key], bool) or not isinstance(row[key], Real) or not math.isfinite(row[key]):
                raise ValueError("M09_ADMITTED_FRAME_NUMBER")
        if row["amount"] < 0 or not 0 <= row["bar_close_pos"] <= 1:
            raise ValueError("M09_ADMITTED_FRAME_NUMBER")


class _BoundPanel:
    def __init__(self, pointer, panel, pointer_identity, panel_identity, frame, trade_date):
        self.pointer, self.panel = pointer, panel
        self.pointer_identity, self.panel_identity = pointer_identity, panel_identity
        self.original = frame
        self.frame = frame.copy(deep=True)
        self.frame_sha = _frame_digest(self.frame)
        self.trade_date = trade_date
        self.delivered_frames = []

    def assert_intact(self):
        if _regular_snapshot(self.pointer, max_bytes=16_384)[1] != self.pointer_identity:
            raise ValueError("M09_PANEL_POINTER_CHANGED")
        if _regular_snapshot(self.panel)[1] != self.panel_identity:
            raise ValueError("M09_PANEL_SNAPSHOT_CHANGED")
        for frame in (self.original, self.frame, *self.delivered_frames):
            if _frame_digest(frame) != self.frame_sha:
                raise ValueError("M09_ADMITTED_FRAME_MUTATED")

    def to_table(self, *, columns, filter):
        if tuple(columns) != COLUMNS or not isinstance(filter, _Filter) or filter.column != "trade_date" or filter.value != self.trade_date:
            raise ValueError("M09_DATASET_QUERY_OUTSIDE_ADMISSION")
        self.assert_intact()
        return _BoundTable(self)


class _BoundTable:
    def __init__(self, bound):
        self.bound = bound
        self.num_rows = len(bound.frame)

    def to_pandas(self):
        self.bound.assert_intact()
        frame = self.bound.frame.copy(deep=True)
        self.bound.delivered_frames.append(frame)
        return frame


def _dataset(path, *, format):
    bound = _PANEL_BINDING.get()
    if bound is None:
        raise ValueError("M09_DATASET_REQUIRES_ADMITTED_FRAME")
    if format != "parquet" or _absolute(path) != bound.panel:
        raise ValueError("M09_DATASET_PATH_OUTSIDE_ADMISSION")
    bound.assert_intact()
    return bound


class _PrivateNamespace:
    def __init__(self, sources):
        self.prefix = "v5_shadow._m09_frozen_" + DESCRIPTOR_SHA256[:16] + "_" + uuid4().hex[:8]
        self.sources = sources
        self.modules = {}
        self.root = ModuleType(self.prefix)
        self.root.__path__ = []
        self.root.__spec__ = importlib.machinery.ModuleSpec(self.prefix, loader=None, is_package=True)
        sys.modules[self.prefix] = self.root
        self.pyarrow = ModuleType(self.prefix + ".admitted_pyarrow")
        dataset = ModuleType(self.pyarrow.__name__ + ".dataset")
        dataset.dataset, dataset.field = _dataset, _Field
        self.pyarrow.dataset = dataset

    def load(self, name):
        if name in self.modules:
            return self.modules[name]
        package = name in _INTERNAL_ROOTS
        relative = name.replace(".", "/") + ("/__init__.py" if package else ".py")
        raw = self.sources.get(relative)
        if raw is None and not package:
            raise ValueError("M09_SOURCE_INTERNAL_IMPORT_MISSING:" + name)
        private = self.prefix + "." + name
        module = ModuleType(private)
        module.__package__ = private if package else private.rpartition(".")[0]
        module.__spec__ = importlib.machinery.ModuleSpec(private, loader=None, is_package=package)
        if package:
            module.__path__ = []
        else:
            self.load(name.partition(".")[0])
        module.__builtins__ = dict(vars(builtins), __import__=self.import_module)
        if raw is not None:
            module.__file__ = str(CAPSULE / relative)
        self.modules[name] = module
        sys.modules[private] = module
        parent_name, _, child_name = name.rpartition(".")
        parent = self.modules[parent_name] if parent_name else self.root
        setattr(parent, child_name, module)
        try:
            if raw is not None:
                exec(compile(raw, module.__file__, "exec"), module.__dict__)
            if name == "contracts.trading_calendar":
                module.CALENDAR_PATH = _FrozenCalendarPath()
        except BaseException:
            self.modules.pop(name, None)
            sys.modules.pop(private, None)
            raise
        return module

    def import_module(self, name, globals=None, locals=None, fromlist=(), level=0):
        if level:
            raise ValueError("M09_SOURCE_UNDECLARED_RELATIVE_IMPORT")
        if name.partition(".")[0] in _INTERNAL_ROOTS:
            module = self.load(name)
            for requested in fromlist or ():
                child = name + "." + requested
                if child.replace(".", "/") + ".py" in self.sources:
                    self.load(child)
            return module if fromlist else self.load(name.partition(".")[0])
        if name == "pyarrow.dataset" and globals and globals.get("__name__") == self.prefix + ".ops.build_a_share_close_review":
            return self.pyarrow.dataset if fromlist else self.pyarrow
        return _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)


def load_frozen_module(name: str) -> ModuleType:
    """Use cached code only after re-verifying every frozen file on disk."""
    sources, _ = _verified_sources()
    if not isinstance(name, str) or name.partition(".")[0] not in _INTERNAL_ROOTS:
        raise ValueError("M09_SOURCE_MODULE_NOT_ALLOWED")
    global _NAMESPACE
    with _LOAD_LOCK:
        if _NAMESPACE is None:
            _NAMESPACE = _PrivateNamespace(sources)
        return _NAMESPACE.load(name)


def safe_root(root: Path):
    """Return the unmodified frozen SafeRoot; caller supplies root authority."""
    return load_frozen_module("infrastructure.owned_io").SafeRoot(_absolute(root))


def market_states(trade_date: str) -> dict[str, str]:
    module = load_frozen_module("contracts.trading_calendar")
    result = module.resolve_market_states(module.load_market_calendar(), trade_date)
    _verified_sources()
    return {name: state.value for name, state in result.items()}


def read_original_review(run_root: Path, trade_date: str) -> dict[str, Any] | None:
    store = load_frozen_module("infrastructure.a_share_review_store").AShareReviewStore(_absolute(run_root))
    result = store.read_review(trade_date)
    _verified_sources()
    return result


def build_from_admitted_panel(
    run_root: Path, trade_date: str, panel_pointer: Path, admitted_frame,
    expected_panel_sha256: str, run_id: str, context: Mapping[str, Any],
) -> dict[str, Any]:
    """Invoke exact original producer with a checked, immutable frame binding.

    This is an internal post-admission capability, not a public raw-input
    entry. The caller must establish full member/source/time admission and
    authorize the run root. The producer's original product is not rewritten.
    """
    initial_sources = sources_identity()
    producer = load_frozen_module("ops.build_a_share_close_review")
    load_frozen_module("infrastructure.data_store")._date(trade_date)
    root, pointer = _absolute(run_root), _absolute(panel_pointer)
    load_frozen_module("infrastructure.owned_path").resolve_owned_path(root, "a_share_reviews/manifest.json")
    _validate_frame(admitted_frame, trade_date)
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("M09_RUN_ID_REQUIRED")
    if not isinstance(context, Mapping) or set(context) - CONTEXT_KEYS:
        raise ValueError("M09_CONTEXT_KEYS")
    if any(value is not None and not isinstance(value, Mapping) for value in context.values()):
        raise ValueError("M09_CONTEXT_OBJECT")
    try:
        original_context = _json_bytes(dict(context))
        frozen_context = json.loads(original_context)
    except (TypeError, ValueError) as error:
        raise ValueError("M09_CONTEXT_NOT_FINITE_JSON") from error
    pointer_raw, pointer_identity = _regular_snapshot(pointer, retain=True, max_bytes=16_384)
    try:
        panel = _absolute(pointer_raw.decode("utf-8-sig").strip())
    except (ValueError, UnicodeError) as error:
        raise ValueError("M09_PANEL_POINTER_INVALID") from error
    _, panel_identity = _regular_snapshot(panel)
    if not isinstance(expected_panel_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_panel_sha256) or panel_identity["sha256"] != expected_panel_sha256:
        raise ValueError("M09_PANEL_SHA_MISMATCH")
    bound = _BoundPanel(pointer, panel, pointer_identity, panel_identity, admitted_frame, trade_date)
    bound.assert_intact()
    token = _PANEL_BINDING.set(bound)
    try:
        result = producer.build_review_from_panel(root, trade_date, panel_pointer=pointer, run_id=run_id, **frozen_context)
    finally:
        _PANEL_BINDING.reset(token)
    bound.assert_intact()
    if _json_bytes(dict(context)) != original_context:
        raise ValueError("M09_CONTEXT_MUTATED")
    if sources_identity() != initial_sources:
        raise ValueError("M09_SOURCE_IDENTITY_CHANGED")
    _json_bytes(result)
    independent = read_original_review(root, trade_date)
    if independent != result["review"] or independent["model_review"]["run_id"] != run_id:
        raise ValueError("M09_ORIGINAL_READBACK_MISMATCH")
    if independent["source_evidence"][0]["raw_sha256"] != expected_panel_sha256:
        raise ValueError("M09_ORIGINAL_PANEL_SOURCE_SHA_MISMATCH")
    return result

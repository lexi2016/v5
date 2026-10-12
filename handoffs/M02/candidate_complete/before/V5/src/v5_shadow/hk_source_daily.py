"""M02 HK source binding wrapper.

Keeps existing readers/loaders authoritative. Does not grant eligibility.
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path

from v5_shadow.membership_reader import read_private as read_membership
from v5_shadow.native_identity_reader import read_private as read_native_identity


_SCHEMA = "v5.m02.hk_source_binding.v1"


def _reader_result(name, value, required):
    if not isinstance(value, dict):
        return {"status": "REJECTED", "reason": f"{name}_NOT_MAPPING"}
    missing = [k for k in required if k not in value]
    if value.get("error") or value.get("diagnostic"):
        return {"status": "REJECTED", "source": value}
    if missing:
        return {"status": "REJECTED", "reason": f"{name}_MISSING", "missing": missing, "source": value}
    return {"status": "VALID", "source": value}


def project_frozen_assets(asset):
    fields = (
        "root", "panel_path", "panel_manifest",
        "model_path", "model_manifest", "name_dictionary_path",
    )
    return {"fields": {k: str(getattr(asset, k)) for k in fields}}


def build_binding(*, asset_root, load_frozen_hk_0_2_assets, membership_root, membership_files, native_binding, target_date, signal_date, eligibility_source_date, cutoff, output_path):
    asset = load_frozen_hk_0_2_assets(asset_root)
    panel = project_frozen_assets(asset)
    membership = read_membership(membership_root, membership_files, eligibility_source_date)
    native = read_native_identity(native_binding, eligibility_source_date)

    payload = {
        "schema": _SCHEMA,
        "target_date": target_date,
        "signal_date": signal_date,
        "eligibility_source_date": eligibility_source_date,
        "cutoff": cutoff,
        "sources": {
            "panel": panel,
            "membership": _reader_result("membership", membership, ["target_date", "request_sha256", "source_capsule_sha256", "codes", "source"]),
            "native": _reader_result("native", native, ["master", "manifest", "request_sha256", "owner_source_sha256"]),
        },
        "formal_eligibility_verified": False,
    }
    _atomic_create(Path(output_path), payload)
    return payload


def _atomic_create(path, payload):
    if path.exists():
        raise FileExistsError("binding_exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True, ensure_ascii=False))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_binding(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != _SCHEMA:
        raise ValueError("binding_schema")
    return data

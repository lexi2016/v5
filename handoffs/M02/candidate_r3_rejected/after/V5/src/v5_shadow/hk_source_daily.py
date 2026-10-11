"""M02 source -> immutable binding -> independent read path.

Only composes existing authoritative readers. It does not create
eligibility authority and does not replace owner validation.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

from v5_shadow.membership_reader import read_private as read_membership
from v5_shadow.native_identity_reader import read_private as read_native_identity


def _reader_state(name, value):
    if value is None:
        return {"status": "UNKNOWN", "source": None}

    if not isinstance(value, dict):
        return {"status": "REJECTED", "reason": f"{name}_INVALID_RETURN"}

    if value.get("error") or value.get("diagnostic"):
        return {
            "status": "REJECTED",
            "reason": value.get("error", "READER_DIAGNOSTIC"),
            "diagnostic": value.get("diagnostic"),
            "source": value,
        }

    return {"status": "VALID", "source": value}


def build_source_binding(
    *,
    binding_path,
    target_date,
    signal_date,
    eligibility_source_date,
    cutoff,
    panel_asset_loader,
    panel_root,
    membership_root,
    membership_files,
    native_binding,
):
    panel = panel_asset_loader(panel_root)

    membership = read_membership(
        membership_root,
        membership_files,
        eligibility_source_date,
    )

    native = read_native_identity(
        native_binding,
        eligibility_source_date,
    )

    result = {
        "schema_version": "v5.m02.source_binding.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_date": target_date,
        "signal_date": signal_date,
        "eligibility_source_date": eligibility_source_date,
        "cutoff": cutoff,
        "sources": {
            "panel_history": {
                "status": "VALID" if panel else "UNKNOWN",
                "source": panel,
            },
            "membership": _reader_state(
                "membership", membership
            ),
            "native": _reader_state(
                "native", native
            ),
        },
        # Qualification remains with existing consumer contract.
        "formal_eligibility_verified": False,
    }

    Path(binding_path).write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return result


def read_source_binding(binding_path, *, panel_asset_loader,
                        membership_root, membership_files,
                        native_binding):
    data = json.loads(
        Path(binding_path).read_text(encoding="utf-8")
    )

    membership = read_membership(
        membership_root,
        membership_files,
        data["eligibility_source_date"],
    )

    native = read_native_identity(
        native_binding,
        data["eligibility_source_date"],
    )

    return {
        "binding": data,
        "membership": _reader_state(
            "membership", membership
        ),
        "native": _reader_state(
            "native", native
        ),
    }

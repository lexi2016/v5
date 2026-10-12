"""P0 narrow business slice: saved owner references -> original manager -> checkpoint.

This does not publish HTTP/CAS and does not refresh owners. Inputs must already be
saved owner references. The original manager implementation remains authoritative.
"""
from __future__ import annotations

from copy import deepcopy

from .daily_manager_assembly import assemble_manager_request
from .manager_plan import run_manager_plan


def _require_reference(row):
    """Validate the lane-specific saved owner contract used by assembly.

    Announcement, rebound and US references intentionally have different
    contracts. Do not normalize them into a fake common artifact reference.
    """
    if not isinstance(row, dict):
        raise ValueError("OWNER_REFERENCE_REQUIRED")

    lane = row.get("lane")
    ref = row.get("product_reference")

    if ref is None:
        state = row.get("state")
        attempts = state.get("attempts") if isinstance(state, dict) else None
        if isinstance(attempts, list) and attempts:
            last = attempts[-1]
            if isinstance(last, dict) and last.get("readback_verified") is True:
                ref = last.get("product_reference")

    if not isinstance(ref, dict):
        raise ValueError("OWNER_REFERENCE_REQUIRED")

    if lane == "announcement":
        binding = ref.get("binding")
        if not isinstance(binding, dict):
            raise ValueError("ANNOUNCEMENT_BINDING_REQUIRED")
        required = ("root", "binding_sha256", "target_date", "publication_date")
        if any(not isinstance(binding.get(key), str) for key in required):
            raise ValueError("ANNOUNCEMENT_BINDING_IDENTITY")
        return deepcopy(row)

    if lane == "rebound":
        reference = ref.get("reference")
        if not isinstance(reference, dict):
            raise ValueError("REBOUND_REFERENCE_REQUIRED")
        required = (
            "run_id",
            "artifact_sha256",
            "manifest_sha256",
            "receipt_sha256",
        )
        if any(not isinstance(reference.get(key), str) for key in required):
            raise ValueError("REBOUND_REFERENCE_IDENTITY")
        return deepcopy(row)

    if lane == "us_mapping":
        required = ("target_date", "run_id", "artifact_sha256", "manager_output_root")
        if any(not isinstance(ref.get(key), str) for key in required):
            raise ValueError("US_SAVED_REFERENCE_IDENTITY")
        return deepcopy(row)

    # Compatibility path for callers without a lane is intentionally narrow.
    # It cannot bypass the lane-specific contracts above.
    if not isinstance(ref.get("run_id"), str) or not isinstance(ref.get("artifact_sha256"), str):
        raise ValueError("OWNER_REFERENCE_IDENTITY")
    return deepcopy(row)


def run_saved_owner_checkpoint(template, owner_rows, ledger_root, registration):
    """Execute one already-bound manager run and return exact saved readback."""
    rows = [_require_reference(row) for row in owner_rows]
    request = assemble_manager_request(template, rows, ledger_root, registration)
    result = run_manager_plan(request)
    readback = result.get("readback") or {}
    product = (result.get("payload") or {}).get("plan_product") or {}
    if readback.get("run_id") and product.get("run_id") != readback["run_id"]:
        raise ValueError("MANAGER_CHECKPOINT_RUN_MISMATCH")
    return {
        "request_sha256": result["request_sha256"],
        "run_id": product.get("run_id") or readback.get("run_id"),
        "plan_sha256": product.get("sha256") or readback.get("plan_sha256"),
        "readback": readback,
        "result": result,
        "publication": "NOT_CONNECTED_IN_THIS_SLICE",
        "natural_verified": False,
    }

"""P0 narrow business slice: saved owner references -> original manager -> checkpoint.

This does not publish HTTP/CAS and does not refresh owners. Inputs must already be
saved owner references. The original manager implementation remains authoritative.
"""
from __future__ import annotations

from copy import deepcopy
from .daily_manager_assembly import assemble_manager_request
from .manager_plan import run_manager_plan


def _require_reference(row):
    ref = row.get("product_reference")
    if not isinstance(ref, dict):
        raise ValueError("OWNER_REFERENCE_REQUIRED")
    for key in ("run_id", "artifact_sha256"):
        if not isinstance(ref.get(key), str):
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

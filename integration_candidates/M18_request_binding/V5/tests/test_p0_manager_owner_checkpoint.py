"""P0 saved-owner partial manager checkpoint integration.

The fixture is intentionally narrow: it consumes already-saved owner references,
uses the original manager assembly/plan path, and asserts exact run readback.
It does not collect, rerun owners, trade, or publish.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from v5_shadow import p0_manager_owner_checkpoint as checkpoint
from v5_shadow.daily_manager_assembly import assemble_manager_request



def _reference(run="a" * 32):
    return {
        "run_id": run,
        "artifact_sha256": "b" * 64,
        "manifest_sha256": "c" * 64,
        "receipt_sha256": "d" * 64,
    }


def _row(lane, run="a" * 32):
    return {
        "lane": lane,
        "state": {
            "attempts": [
                {
                    "readback_verified": True,
                    "product_reference": _reference(run),
                }
            ]
        },
    }


def _template(root):
    return {
        "target_date": "20261009",
        "now": "2026-10-09T00:45:05Z",
        "inputs": {
            "manager": {"root": str(root / "manager"), "files": {}},
        },
        "rebound": None,
        "manager_output_root": str(root / "output"),
    }


def test_saved_owner_partial_checkpoint_reaches_manager(monkeypatch, tmp_path):
    """Verify the wrapper consumes saved references and keeps qualification partial."""
    called = {"assembly": 0, "manager": 0}

    def assembly(*args, **kwargs):
        called["assembly"] += 1
        return {"target_date": "20261009", "now": "2026-10-09T00:45:05+00:00"}

    def manager(request):
        called["manager"] += 1
        return {
            "request_sha256": "e" * 64,
            "payload": {"plan_product": {"run_id": "f" * 32, "sha256": "1" * 64}},
            "readback": {"run_id": "f" * 32, "plan_sha256": "1" * 64},
        }

    monkeypatch.setattr(checkpoint, "assemble_manager_request", assembly)
    monkeypatch.setattr(checkpoint, "run_manager_plan", manager)

    result = checkpoint.run_saved_owner_checkpoint(
        _template(tmp_path),
        [_row("rebound")],
        tmp_path,
        {"code_sha256": "1" * 64, "config_sha256": "2" * 64, "dependency_sha256": "3" * 64},
    )

    assert called == {"assembly": 1, "manager": 1}
    assert result["publication"] == "NOT_CONNECTED_IN_THIS_SLICE"
    assert result["natural_verified"] is False


def test_saved_owner_wrong_run_and_sha_reject_before_manager(monkeypatch):
    called = []
    monkeypatch.setattr(checkpoint, "assemble_manager_request", lambda *a, **k: called.append(1))
    bad = {"lane": "rebound", "product_reference": {"run_id": "bad", "artifact_sha256": "x"}}
    try:
        checkpoint.run_saved_owner_checkpoint({}, [bad], Path("/tmp"), {})
    except ValueError:
        pass
    else:
        raise AssertionError("bad saved identity must reject")
    assert called == []


def test_saved_owner_reference_shape_uses_original_attempt_envelope():
    row = _row("rebound")
    result = checkpoint._require_reference(row)
    assert result["state"]["attempts"][-1]["readback_verified"] is True
    assert result["state"]["attempts"][-1]["product_reference"]["run_id"] == "a" * 32

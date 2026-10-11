"""M10 HK close daily default producer/store/reader chain.

The default path owns the canonical HK close build. It does not accept a caller
provided calculation callback. Calculation remains delegated to the frozen owner
modules imported from the M10 source capsule.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


SCHEMA = "v5.hk_close_daily.v2"


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class CloseReviewReceipt:
    run_id: str
    payload_sha256: str
    manifest_sha256: str


class HKCloseReviewStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def publish(self, run_id: str, payload: dict):
        target = self.root / run_id
        payload_sha = _digest(payload)
        if target.exists():
            old = json.loads((target / "payload.json").read_text())
            if _digest(old) != payload_sha:
                raise ValueError("M10_RUN_ID_CONFLICT")
            return self._receipt(target)
        target.mkdir()
        (target / "payload.json").write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        manifest = {"schema": SCHEMA, "run_id": run_id, "payload_sha256": payload_sha}
        (target / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        receipt = {"run_id": run_id, "payload_sha256": payload_sha, "manifest_sha256": _digest(manifest)}
        (target / "receipt.json").write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
        return CloseReviewReceipt(**receipt)

    def _receipt(self, target):
        return CloseReviewReceipt(**json.loads((target / "receipt.json").read_text()))


class HKCloseReviewReader:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def read(self, run_id: str):
        target = self.root / run_id
        payload = json.loads((target / "payload.json").read_text())
        manifest = json.loads((target / "manifest.json").read_text())
        receipt = json.loads((target / "receipt.json").read_text())
        if manifest.get("payload_sha256") != _digest(payload):
            raise ValueError("M10_PAYLOAD_SHA_INVALID")
        if receipt.get("manifest_sha256") != _digest(manifest):
            raise ValueError("M10_MANIFEST_SHA_INVALID")
        return payload


def build_default_hk_close_review(*, data_root: Path, trade_date: str, stage_selection_root: Path | str | None = None):
    from ops.collect_hkconnect_close_snapshot import collect_close_snapshot
    from ops.build_close_review import build_close_review

    collect_close_snapshot(trade_date, data_root=Path(data_root))
    return build_close_review(
        Path(data_root),
        trade_date,
        stage_selection_root=stage_selection_root,
    )


__all__ = ["HKCloseReviewStore", "HKCloseReviewReader", "CloseReviewReceipt", "build_default_hk_close_review"]

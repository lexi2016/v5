"""M10 HK close daily default chain.

Minimal private chain:
producer -> immutable payload store -> independent reader.
This module intentionally keeps calculation ownership in hk_close_review and only
owns execution identity, persistence and verified replay boundaries.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory


SCHEMA = "v5.hk_close_daily.v1"


def _digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class CloseReviewReceipt:
    run_id: str
    payload_sha256: str
    manifest_sha256: str


class HKCloseReviewStore:
    """Small immutable M10 store. Existing ReviewStore integration remains separate."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def publish(self, run_id: str, payload: dict) -> CloseReviewReceipt:
        payload_sha = _digest(payload)
        target = self.root / run_id
        if target.exists():
            old = json.loads((target / "payload.json").read_text())
            if _digest(old) != payload_sha:
                raise ValueError("M10_RUN_ID_CONFLICT")
            return self._receipt(target)
        target.mkdir()
        (target / "payload.json").write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        manifest = {"schema": SCHEMA, "run_id": run_id, "payload_sha256": payload_sha}
        (target / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        return self._receipt(target)

    def _receipt(self, target):
        payload_sha = _digest(json.loads((target / "payload.json").read_text()))
        manifest = json.loads((target / "manifest.json").read_text())
        return CloseReviewReceipt(target.name, payload_sha, _digest(manifest))


class HKCloseReviewReader:
    def __init__(self, root: str | Path):
        self.store = HKCloseReviewStore(root)

    def read(self, run_id: str):
        target = self.store.root / run_id
        if not target.exists():
            raise FileNotFoundError(run_id)
        payload = json.loads((target / "payload.json").read_text())
        manifest = json.loads((target / "manifest.json").read_text())
        if manifest.get("payload_sha256") != _digest(payload):
            raise ValueError("M10_PAYLOAD_SHA_INVALID")
        return payload


def build_default_hk_close_review(*, target_date: str, input_identity: dict, calculate):
    """Execute caller-owned canonical calculation and persist its committed result.

    `calculate` is the existing M10 algorithm owner, not a replacement algorithm.
    Production wiring may replace the boundary adapter without changing storage.
    """
    payload = calculate(target_date=target_date, input_identity=input_identity)
    payload.setdefault("schema", SCHEMA)
    return payload


__all__ = ["HKCloseReviewStore", "HKCloseReviewReader", "build_default_hk_close_review", "CloseReviewReceipt"]

"""M10 HK close default producer/store/reader chain."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

SCHEMA = "v5.hk_close_daily.v4.2"


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


@dataclass(frozen=True)
class CloseReviewReceipt:
    run_id: str
    payload_sha256: str
    manifest_sha256: str
    publication_sha256: str


class HKCloseReviewStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def publish(self, run_id: str, payload: dict, publication: dict):
        payload_sha = _digest(payload)
        publication_sha = _digest(publication)
        target = self.root / run_id
        if target.exists():
            old_manifest = json.loads((target / "manifest.json").read_text())
            if old_manifest.get("payload_sha256") != payload_sha or old_manifest.get("publication_sha256") != publication_sha:
                raise ValueError("M10_RUN_ID_CONFLICT")
            return self._receipt(target)
        target.mkdir()
        manifest = {"schema": SCHEMA, "run_id": run_id, "payload_sha256": payload_sha, "publication_sha256": publication_sha}
        receipt = {"run_id": run_id, "payload_sha256": payload_sha, "manifest_sha256": _digest(manifest), "publication_sha256": publication_sha}
        (target / "payload.json").write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        (target / "publication.json").write_text(json.dumps(publication, sort_keys=True), encoding="utf-8")
        (target / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
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
        publication = json.loads((target / "publication.json").read_text())
        manifest = json.loads((target / "manifest.json").read_text())
        receipt = json.loads((target / "receipt.json").read_text())
        if manifest.get("payload_sha256") != _digest(payload):
            raise ValueError("M10_PAYLOAD_SHA_INVALID")
        if manifest.get("publication_sha256") != _digest(publication):
            raise ValueError("M10_PUBLICATION_SHA_INVALID")
        if receipt.get("manifest_sha256") != _digest(manifest):
            raise ValueError("M10_MANIFEST_SHA_INVALID")
        if receipt.get("publication_sha256") != _digest(publication):
            raise ValueError("M10_RECEIPT_PUBLICATION_INVALID")
        return payload


def _load_frozen_owners():
    from ops.collect_hkconnect_close_snapshot import collect_close_snapshot
    from ops.build_close_review import build_close_review
    if not callable(collect_close_snapshot) or not callable(build_close_review):
        raise ImportError("M10_OWNER_CLOSURE_INVALID")
    return collect_close_snapshot, build_close_review


def build_default_hk_close_review(*, data_root: Path, trade_date: str, run_root: Path, stage_selection_root: Path | str | None = None):
    collect_close_snapshot, build_close_review = _load_frozen_owners()
    data_root = Path(data_root)
    collect_close_snapshot(trade_date, data_root=data_root)
    built = build_close_review(data_root, trade_date, stage_selection_root=stage_selection_root)
    if not isinstance(built, dict) or "review" not in built or "publication" not in built:
        raise ValueError("M10_BUILD_PUBLICATION_INVALID")
    payload = built["review"]
    run_id = f"{trade_date}-{_digest(payload)[:16]}"
    HKCloseReviewStore(run_root).publish(run_id, payload, built["publication"])
    return HKCloseReviewReader(run_root).read(run_id)


__all__ = ["HKCloseReviewStore", "HKCloseReviewReader", "CloseReviewReceipt", "build_default_hk_close_review"]

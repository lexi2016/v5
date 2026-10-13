"""M03 isolated market_snapshot adapter.

This module only adapts the existing US market snapshot producer contract.
It does not replace owner, transport, PIN, guard, or collector logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


MARKET_SNAPSHOT_READY = "READY"


def parse_capture_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("M03_TIME_REQUIRED")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("M03_TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def materialize_market_snapshot(payload: dict[str, Any], *, session: str, phase: str, cutoff: str) -> dict[str, Any]:
    """Accept only an actual market snapshot, never news-only readiness."""
    if not isinstance(payload, dict):
        raise ValueError("M03_MARKET_SNAPSHOT_PAYLOAD_INVALID")
    snapshot = payload.get("market_snapshot")
    if not isinstance(snapshot, dict):
        raise ValueError("US_MARKET_SNAPSHOT_NOT_MATERIALIZED")
    if snapshot.get("status") != MARKET_SNAPSHOT_READY:
        raise ValueError("US_MARKET_SNAPSHOT_NOT_MATERIALIZED")
    if snapshot.get("capture_session_date") != session:
        raise ValueError("M03_SNAPSHOT_SESSION_MISMATCH")
    if snapshot.get("capture_phase") != phase:
        raise ValueError("M03_SNAPSHOT_PHASE_MISMATCH")
    if parse_capture_time(snapshot["captured_at"]) > parse_capture_time(cutoff):
        raise ValueError("M03_CAPTURE_AFTER_CUTOFF")
    return snapshot


def reject_news_only(payload: dict[str, Any]) -> None:
    if isinstance(payload, dict) and payload.get("status") == "READY" and not payload.get("market_snapshot"):
        raise ValueError("US_MARKET_SNAPSHOT_NOT_MATERIALIZED")

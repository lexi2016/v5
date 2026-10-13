"""M03 market snapshot adapter.

Narrow adapter around the frozen US market snapshot producer.

This module:
- calls the existing build_us_market_snapshot contract;
- validates the resulting market snapshot envelope;
- rejects news-only READY payloads.

This module does NOT:
- create a quote algorithm;
- create persistence artifacts;
- replace ResearchPeripheralStore;
- perform network capture itself;
- bypass cloud_us_collector.load_owner validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from ops.us_market_digest import build_us_market_snapshot


MARKET_SNAPSHOT_SCHEMA = "v3_5.us_market_snapshot.v1"

MARKET_SNAPSHOT_NOT_MATERIALIZED = (
    "US_MARKET_SNAPSHOT_NOT_MATERIALIZED"
)


@dataclass(frozen=True)
class MarketSnapshotRequest:
    us_session_date: str
    capture_phase: str
    captured_at: str
    session: str
    cutoff: str
    capture_id: str
    run_id: str


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("M03_TIME_REQUIRED")

    parsed = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if parsed.tzinfo is None:
        raise ValueError(
            "M03_TIMEZONE_REQUIRED"
        )

    return parsed.astimezone(timezone.utc)


def _validate_capture_identity(
    request: MarketSnapshotRequest,
    snapshot: Mapping[str, Any],
) -> None:
    required = (
        "capture_session_date",
        "capture_phase",
        "captured_at",
    )

    for key in required:
        if key not in snapshot:
            raise ValueError(
                f"M03_MARKET_SNAPSHOT_MISSING_{key.upper()}"
            )

    if snapshot["capture_session_date"] != (
        request.us_session_date
    ):
        raise ValueError(
            "M03_MARKET_SNAPSHOT_SESSION_MISMATCH"
        )

    if snapshot["capture_phase"] != (
        request.capture_phase
    ):
        raise ValueError(
            "M03_MARKET_SNAPSHOT_PHASE_MISMATCH"
        )

    if _parse_utc(snapshot["captured_at"]) != (
        _parse_utc(request.captured_at)
    ):
        raise ValueError(
            "M03_MARKET_SNAPSHOT_CAPTURE_MISMATCH"
        )

    if _parse_utc(snapshot["captured_at"]) > (
        _parse_utc(request.cutoff)
    ):
        raise ValueError(
            "M03_MARKET_SNAPSHOT_AFTER_CUTOFF"
        )


def _validate_market_snapshot_contract(
    snapshot: Mapping[str, Any],
) -> None:
    if snapshot.get("schema_version") != (
        MARKET_SNAPSHOT_SCHEMA
    ):
        raise ValueError(
            "M03_MARKET_SNAPSHOT_SCHEMA_INVALID"
        )

    if snapshot.get("status") != "READY":
        raise ValueError(
            MARKET_SNAPSHOT_NOT_MATERIALIZED
        )

    required_fields = (
        "source",
        "provider",
        "source_response_sha256",
        "generated_at",
        "mapping_version",
        "quotes",
        "rows",
        "cannot_confirm",
        "recommendation_status",
        "RESEARCH_ONLY",
        "production_allowed",
        "buy_gate_updated",
        "orders_sent",
    )

    missing = [
        field
        for field in required_fields
        if field not in snapshot
    ]

    if missing:
        raise ValueError(
            "M03_MARKET_SNAPSHOT_FIELDS_MISSING:"
            + ",".join(sorted(missing))
        )

    if snapshot["production_allowed"] is not False:
        raise ValueError(
            "M03_MARKET_SNAPSHOT_SAFETY_INVALID"
        )

    if snapshot["buy_gate_updated"] is not False:
        raise ValueError(
            "M03_MARKET_SNAPSHOT_SAFETY_INVALID"
        )

    if snapshot["orders_sent"] is not False:
        raise ValueError(
            "M03_MARKET_SNAPSHOT_SAFETY_INVALID"
        )

    if not isinstance(snapshot["quotes"], list):
        raise ValueError(
            "M03_MARKET_SNAPSHOT_QUOTES_INVALID"
        )


def build_market_snapshot(
    *,
    request: MarketSnapshotRequest,
    fetch_quotes=None,
    fetch_quote=None,
    transport=None,
    timeout: int = 20,
) -> dict[str, Any]:
    """
    Build one quote-only market snapshot.

    The caller must already be inside the controlled producer execution
    context established by cloud_us_market collector/load_owner.

    captured_at is the original capture identity. It is not replaced by
    cutoff or generated locally.
    """

    snapshot = build_us_market_snapshot(
        request.us_session_date,
        capture_phase=request.capture_phase,
        captured_at=request.captured_at,
        fetch_quotes=fetch_quotes,
        fetch_quote=fetch_quote,
        transport=transport,
        timeout=timeout,
    )

    if not isinstance(snapshot, dict):
        raise ValueError(
            "M03_MARKET_SNAPSHOT_NOT_DICT"
        )

    _validate_capture_identity(
        request,
        snapshot,
    )

    _validate_market_snapshot_contract(
        snapshot,
    )

    return dict(snapshot)


def reject_news_ready(
    payload: Mapping[str, Any],
) -> None:
    """
    Explicitly prevent historical failure:

        news READY != market snapshot READY
    """

    if (
        payload.get("status") == "READY"
        and "quotes" not in payload
        and "rows" not in payload
    ):
        raise ValueError(
            MARKET_SNAPSHOT_NOT_MATERIALIZED
        )


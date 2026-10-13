"""
M14 saved rebound readonly adapter.

Readonly only:
- Calls the pinned rebound_owner.read_rebound_owner(root, reference)
  for every page request.
- Does not accept stored_result.
- Does not build/recompute/model/collect.
- Does not expose private filesystem metadata.

This file is an adapter candidate only.
API routing/frontend wiring remains outside this file.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from v5_shadow.rebound_owner import read_rebound_owner
from v5_shadow.composition import no_symlinks


GROUPS = (
    "strict",
    "near",
    "pending",
    "excluded",
    "screen_unresolved",
)

PAGE_LIMIT = 32
MAX_CURSOR_BYTES = 4096
MAX_PAGE_BYTES = 256 * 1024


class M14ReadonlyError(ValueError):
    pass


class WaitingBinding(M14ReadonlyError):
    pass


@dataclass(frozen=True)
class SavedBinding:
    private_root: Path
    reference: dict[str, str]


def _sha(value: Any) -> str:
    if not isinstance(value, str):
        raise M14ReadonlyError("SHA_TYPE")

    if len(value) != 64:
        raise M14ReadonlyError("SHA_LENGTH")

    lowered = value.lower()

    if any(ch not in "0123456789abcdef" for ch in lowered):
        raise M14ReadonlyError("SHA_FORMAT")

    return lowered


def _run_id(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 32:
        raise M14ReadonlyError("RUN_ID")

    try:
        int(value, 16)
    except ValueError as exc:
        raise M14ReadonlyError("RUN_ID") from exc

    return value


def parse_binding(
    binding: Mapping[str, Any] | None,
) -> SavedBinding:
    """
    Binding is server-side configuration.

    Client never provides private_root.
    """

    if not isinstance(binding, Mapping):
        raise WaitingBinding("WAITING_BINDING")

    if set(binding) != {
        "private_root",
        "reference",
    }:
        raise M14ReadonlyError("BINDING_KEYS")

    root = binding["private_root"]

    if not isinstance(root, (str, Path)):
        raise WaitingBinding("WAITING_PRIVATE_ROOT")

    # Keep original reader responsible for owner root marker,
    # no-follow traversal and root safety checks.
    safe_root = no_symlinks(Path(root))

    reference = binding["reference"]

    if not isinstance(reference, Mapping):
        raise WaitingBinding("WAITING_REFERENCE")

    if set(reference) != {
        "run_id",
        "artifact_sha256",
        "manifest_sha256",
        "receipt_sha256",
    }:
        raise M14ReadonlyError("REFERENCE_KEYS")

    return SavedBinding(
        private_root=safe_root,
        reference={
            "run_id": _run_id(reference["run_id"]),
            "artifact_sha256": _sha(reference["artifact_sha256"]),
            "manifest_sha256": _sha(reference["manifest_sha256"]),
            "receipt_sha256": _sha(reference["receipt_sha256"]),
        },
    )


def _check_query(query: Mapping[str, Any]) -> None:
    if not isinstance(query, Mapping):
        raise M14ReadonlyError("QUERY_TYPE")

    allowed = {
        "group",
        "cursor",
        "limit",
    }

    if set(query) - allowed:
        raise M14ReadonlyError("UNKNOWN_QUERY")


def _limit(value: Any) -> int:
    if value is None:
        return PAGE_LIMIT

    if isinstance(value, bool):
        raise M14ReadonlyError("BOOLEAN_LIMIT")

    if not isinstance(value, int):
        raise M14ReadonlyError("LIMIT")

    if value < 1 or value > PAGE_LIMIT:
        raise M14ReadonlyError("LIMIT")

    return value


def _encode_cursor(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode()

    if len(raw) > MAX_CURSOR_BYTES:
        raise M14ReadonlyError("CURSOR_SIZE")

    return base64.urlsafe_b64encode(raw).decode()


def _decode_cursor(value: str) -> dict[str, Any]:
    if not isinstance(value, str):
        raise M14ReadonlyError("CURSOR_TYPE")

    try:
        decoded = json.loads(
            base64.urlsafe_b64decode(value.encode()),
        )
    except Exception as exc:
        raise M14ReadonlyError("CURSOR") from exc

    if not isinstance(decoded, dict):
        raise M14ReadonlyError("CURSOR")

    if set(decoded) != {
        "run_id",
        "artifact_sha256",
        "manifest_sha256",
        "receipt_sha256",
        "group",
        "offset",
    }:
        raise M14ReadonlyError("CURSOR_KEYS")

    if isinstance(decoded["offset"], bool):
        raise M14ReadonlyError("CURSOR_OFFSET")

    if not isinstance(decoded["offset"], int):
        raise M14ReadonlyError("CURSOR_OFFSET")

    return decoded


def _verify_cursor(
    cursor: Mapping[str, Any],
    binding: SavedBinding,
    group: str,
) -> int:

    reference = binding.reference

    for key in (
        "run_id",
        "artifact_sha256",
        "manifest_sha256",
        "receipt_sha256",
    ):
        if cursor[key] != reference[key]:
            raise M14ReadonlyError(
                "CURSOR_REFERENCE_MISMATCH"
            )

    if cursor["group"] != group:
        raise M14ReadonlyError("CURSOR_GROUP")

    return cursor["offset"]


def _public(value: Any) -> Any:
    """
    Remove private storage information only.
    """

    blocked = {
        "private_root",
        "input_root",
        "root",
        "path",
        "absolute_path",
        "manifest_relative",
        "artifact_relative",
        "raw_capture_relative",
    }

    if isinstance(value, Mapping):
        return {
            key: _public(item)
            for key, item in value.items()
            if key not in blocked
        }

    if isinstance(value, list):
        return [_public(item) for item in value]

    return value


def _artifact(owner_result: Mapping[str, Any]) -> Mapping[str, Any]:
    """
    read_rebound_owner returns artifact directly.
    """

    if not isinstance(owner_result, Mapping):
        raise M14ReadonlyError("OWNER_RESULT")

    return owner_result


def _groups(artifact: Mapping[str, Any]) -> dict[str, list[Any]]:
    observation = artifact.get(
        "research_observation"
    )

    if not isinstance(observation, Mapping):
        return {}

    result = {}

    for group in GROUPS:
        value = observation.get(group)

        if isinstance(value, list):
            result[group] = value

    return result


def _state(artifact: Mapping[str, Any]) -> dict[str, Any]:
    request = artifact.get("request")

    if not isinstance(request, Mapping):
        request = {}

    observation = artifact.get(
        "research_observation"
    )

    if not isinstance(observation, Mapping):
        observation = {}

    return {
        "target_date": request.get("target_date"),
        "signal_date": request.get("signal_date"),

        "formal_status": artifact.get(
            "formal_status"
        ),
        "computation_status": artifact.get(
            "computation_status"
        ),

        "observation_status": observation.get(
            "status"
        ),

        "original_computation_status":
            observation.get(
                "original_computation_status"
            ),

        "gaps": observation.get(
            "gaps"
        ),

        "coverage": observation.get(
            "coverage"
        ),

        "reason_codes": artifact.get(
            "reason_codes"
        ),

        "safety": {
            key: artifact.get(key)
            for key in (
                "research_only",
                "production_allowed",
                "buy_gate_updated",
                "orders_sent",
                "natural_verified",
                "formal_eligibility_verified",
            )
        },
    }


def read_saved_rebound(
    *,
    server_binding: Mapping[str, Any] | None,
    query: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Read one saved rebound page.

    Every request performs original cold reader verification.
    """

    _check_query(query)

    binding = parse_binding(server_binding)

    group = query.get(
        "group",
        "strict",
    )

    if group not in GROUPS:
        raise M14ReadonlyError("UNKNOWN_GROUP")

    limit = _limit(
        query.get("limit")
    )

    offset = 0

    cursor = query.get("cursor")

    if cursor is not None:
        offset = _verify_cursor(
            _decode_cursor(cursor),
            binding,
            group,
        )

    # Fixed owner contract:
    # returns artifact directly after SHA/semantic validation.
    artifact = _artifact(
        read_rebound_owner(
            binding.private_root,
            binding.reference,
        )
    )

    groups = _groups(artifact)

    if group not in groups:
        # Preserve absent observation, do not convert to five empty groups.
        raise M14ReadonlyError(
            "OBSERVATION_GROUP_UNAVAILABLE"
        )

    rows = groups[group]

    if offset < 0 or offset > len(rows):
        raise M14ReadonlyError(
            "OFFSET_RANGE"
        )

    page = rows[offset: offset + limit]

    response = {
        "reference": dict(binding.reference),

        "group": group,

        "group_counts": {
            key: len(value)
            for key, value in groups.items()
        },

        "state": _state(artifact),

        "rows": [
            _public(row)
            for row in page
        ],

        "offset": offset,
        "limit": limit,
    }

    next_offset = offset + len(page)

    if next_offset < len(rows):
        response["next_cursor"] = _encode_cursor(
            {
                **binding.reference,
                "group": group,
                "offset": next_offset,
            }
        )
    else:
        response["next_cursor"] = None

    encoded = json.dumps(
        response,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode()

    if len(encoded) > MAX_PAGE_BYTES:
        raise M14ReadonlyError(
            "PAGE_SIZE"
        )

    return response


# Tests: NOT_RUN


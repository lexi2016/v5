"""M09-only read projection for the existing exact-date review surface.

This module never runs the producer, publishes a generation, or reads another
date. The generation reader owns filesystem verification and pins its head
once. These pure projections verify the returned identity links and retain
the full frozen native review, with separate M09 read evidence.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .contracts import aware, sha, trade_date
from .digests import canonical_bytes, sha256_json


READ_SCHEMA = "v5.m09.read_evidence.v1"
_FLAGS = {"production_allowed": False, "buy_gate_updated": False, "orders_sent": False}
_RESEARCH_FLAGS = {"research_only": True, **_FLAGS}
_ROWS = ("big_picture", "mainlines", "core_stocks", "observation_pool",
         "next_day_trigger_tree", "quality_gate")
_HASH_FIELDS = ("canonical_review_sha256", "raw_review_sha256", "source_sha256",
                "record_sha256", "generation_sha256")
_EXECUTION_KINDS = {"SYNTHETIC": {"ENGINEERING"}, "RECORDED_INPUT_REPLAY": {"HISTORICAL_REPLAY"},
                    "REAL": {"DAILY_RESEARCH", "HISTORICAL_REPLAY"}}
# Schema order from frozen domains.close_review_chain.CHAIN_TASKS. These are
# read-contract identifiers, not additional scheduler slots or runnable jobs.
_CHAIN_TASK_IDS = (
    "FUPAN_CLOSE_MATERIALS", "FUPAN_REVIEW_START", "FUPAN_A_SHARE_STRUCTURE", "FUPAN_VIDEO_CHECK",
    "FUPAN_VIDEO_DOWNLOAD_ASR", "FUPAN_STOCKDICT", "FUPAN_VIDEO_TABLE_OCR_ALIGN", "FUPAN_VIDEO_GAP",
    "FUPAN_V3_PUBLISH", "FUPAN_8771_VERIFY",
)


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("M09_COMMITTED_STRUCTURE_INVALID")
    return value


def _safe_flags(value: Any, expected: Mapping[str, bool]) -> None:
    value = _mapping(value)
    if any(value.get(key) is not flag for key, flag in expected.items()):
        raise ValueError("M09_COMMITTED_SAFETY_INVALID")


def _validate_committed(committed: Mapping[str, Any], target: str) -> None:
    """Check content hashes and cross-layer identity, without any file reads."""
    value = _mapping(committed)
    review, record, generation, identity = (_mapping(value.get(key))
                                            for key in ("review", "record", "generation", "identity"))
    canonical_bytes(value)
    for field in ("latest_attempt", "publication_recovery"):
        if value.get(field) is not None:
            _mapping(value[field])
    if (review.get("schema_version") != "v3_5.a_share_review.v1"
            or record.get("schema_version") != "v5.m09.record.v1"
            or generation.get("schema_version") != "v5.m09.generation.v1"):
        raise ValueError("M09_COMMITTED_SCHEMA_INVALID")
    if any(item.get("trade_date") != target for item in (review, record, generation, identity)):
        raise ValueError("M09_COMMITTED_DATE_MISMATCH")
    for field in _HASH_FIELDS:
        sha(identity.get(field))
    review_path = "a_share_reviews/" + target + ".json"
    store_files = _mapping(record.get("store_files"))
    if set(store_files) != {review_path, "a_share_reviews/receipts/" + target + ".json",
                            "a_share_reviews/manifest.json"}:
        raise ValueError("M09_COMMITTED_STORE_FILES_INVALID")
    for item in store_files.values():
        item = _mapping(item)
        if set(item) != {"sha256", "bytes"} or type(item["bytes"]) is not int or item["bytes"] <= 0:
            raise ValueError("M09_COMMITTED_STORE_METADATA_INVALID")
        sha(item["sha256"])
    if store_files[review_path]["sha256"] != identity["raw_review_sha256"]:
        raise ValueError("M09_COMMITTED_RAW_REVIEW_MISMATCH")
    if (sha256_json(review) != identity["canonical_review_sha256"]
            or record.get("review_sha256") != identity["canonical_review_sha256"]
            or sha256_json(record) != identity["record_sha256"]
            or generation.get("record_sha256") != identity["record_sha256"]
            or sha256_json(generation) != identity["generation_sha256"]):
        raise ValueError("M09_COMMITTED_DIGEST_MISMATCH")
    previous = generation.get("previous_generation_sha256")
    if previous is not None:
        sha(previous)
    if not review.get("source_sha256") == record.get("source_sha256") == identity["source_sha256"]:
        raise ValueError("M09_COMMITTED_SOURCE_MISMATCH")
    if review.get("source_role") != "V3_5_NATIVE_CLOSE_MODEL":
        raise ValueError("M09_COMMITTED_SOURCE_ROLE_INVALID")
    _safe_flags(review, _FLAGS)
    _safe_flags(record.get("safety"), _RESEARCH_FLAGS)
    for field in ("headline", "market_regime", "risk_tone", "write_policy"):
        if not isinstance(review.get(field), str):
            raise ValueError("M09_COMMITTED_REVIEW_FIELD_INVALID")
    for field in _ROWS:
        rows = review.get(field)
        if not isinstance(rows, list) or any(
                not isinstance(row, Mapping) or row.get("trade_date") != target
                or row.get("review_date") not in (None, "", target) for row in rows):
            raise ValueError("M09_COMMITTED_REVIEW_ROWS_INVALID")
    if (not isinstance(review.get("cannot_confirm"), list)
            or any(not isinstance(reason, str) for reason in review["cannot_confirm"])
            or not isinstance(review.get("source_evidence"), list)
            or any(not isinstance(row, Mapping) for row in review["source_evidence"])):
        raise ValueError("M09_COMMITTED_EVIDENCE_INVALID")
    model = _mapping(review.get("model_review"))
    if (model.get("schema_version") != "replay_model_v1"
            or model.get("status") != "INDEPENDENT_CLOSE_REVIEW_READY"
            or model.get("review_date") != target
            or model.get("producer_type") != "DETERMINISTIC_PYTHON"
            or model.get("visibility_stage") != "POST_CLOSE_REVIEW_ONLY"
            or model.get("semantic_model_status") != "DISABLED_BY_V3_5_NO_LLM_PRODUCTION_RULE"
            or model.get("formal_generalization") != "FORMAL_GENERALIZATION_PENDING"
            or model.get("learning_status") != "LEARNING_HYPOTHESIS_FAIL"
            or type(model.get("semantic_model_call_count")) is not int
            or model["semantic_model_call_count"] != 0
            or model.get("model_promotion") != "NO_MODEL_PROMOTED"
            or model.get("target_video_review_status") != "CANNOT_CONFIRM_TARGET_VIDEO_NOT_CONSUMED"
            or type(model.get("target_video_evidence_count")) is not int
            or model["target_video_evidence_count"] != 0
            or model.get("video_augmented_review_complete") is not False):
        raise ValueError("M09_COMMITTED_MODEL_INVALID")
    model_safety = _mapping(model.get("safety"))
    _safe_flags(model_safety, {"SHADOW_ONLY": True, "NOT_BUY_ADVICE": True, "NO_BUY_GATE": True})
    if type(model_safety.get("HOLDOUT_ACCESS_COUNT")) is not int or model_safety["HOLDOUT_ACCESS_COUNT"] != 0:
        raise ValueError("M09_COMMITTED_MODEL_SAFETY_INVALID")
    run_id = model.get("run_id")
    if (not isinstance(run_id, str) or not run_id
            or run_id != identity.get("model_run_id")
            or run_id != generation.get("run_id")
            or ("run_id" in record and run_id != record["run_id"])):
        raise ValueError("M09_COMMITTED_RUN_MISMATCH")
    chain = _mapping(review.get("close_chain"))
    nodes = chain.get("nodes")
    if (chain.get("schema_version") != "v3_5.close_review_chain.v1"
            or chain.get("trade_date") != target
            or not isinstance(nodes, list)
            or any(not isinstance(node, Mapping) for node in nodes)
            or tuple(node.get("task_id") for node in nodes) != _CHAIN_TASK_IDS
            or any(node.get("business_date") != target for node in nodes)):
        raise ValueError("M09_COMMITTED_CHAIN_INVALID")
    _safe_flags(chain, _FLAGS)
    if (record.get("data_kind") not in _EXECUTION_KINDS
            or record.get("execution_kind") not in _EXECUTION_KINDS[record["data_kind"]]
            or not isinstance(record.get("business_status"), str)
            or not record["business_status"]
            or record.get("strict_1500_pit_verified") is not False):
        raise ValueError("M09_COMMITTED_CLASSIFICATION_INVALID")
    aware(record.get("computed_at"))
    _mapping(record.get("provenance"))
    _mapping(record.get("evidence_status"))
    _mapping(record.get("membership"))
    allowed_scope = "OBSERVED_ROWS_ONLY" if record.get("historical_research") is not None else "DECLARED_UNIVERSE_ONLY"
    if record.get("historical_research") is not None:
        historical = _mapping(record["historical_research"])
        if (record.get("data_kind") != "RECORDED_INPUT_REPLAY" or record.get("execution_kind") != "HISTORICAL_REPLAY"
                or any(historical.get(key) is not False for key in ("source_time_verified", "source_available_by_requested_slot",
                       "membership_qualification_verified", "strict_1500_pit_verified", "natural_verified"))):
            raise ValueError("M09_HISTORICAL_PROMOTION_REJECTED")
    if (record.get("scope") != allowed_scope
            or record.get("natural_verified") is not False
            or record.get("source_provenance_independently_verified") is not False
            or not isinstance(record.get("cannot_confirm"), list)
            or any(not isinstance(reason, str) for reason in record["cannot_confirm"])):
        raise ValueError("M09_COMMITTED_LIMITATIONS_INVALID")


def _unavailable(target: str, status: str, reason: str) -> dict[str, Any]:
    """A renderable exact-date absence, without fabricated market values."""
    evidence = {"schema_version": READ_SCHEMA, "trade_date": target,
                "read_status": status, "business_status": "CANNOT_CONFIRM",
                "model_run_id": None, **{key: None for key in _HASH_FIELDS},
                "reason_codes": [reason], "strict_1500_pit_verified": False,
                "natural_verified": False, "source_provenance_independently_verified": False,
                "scope": None, "record_cannot_confirm": [], "membership": None,
                "latest_attempt": None, "latest_attempt_status": None,
                "publication_recovery": None,
                "safety": dict(_RESEARCH_FLAGS)}
    return {
        "schema_version": "v3_5.a_share_review.v1", "trade_date": target,
        "status": status, "headline": f"A股复盘 {target}",
        "market_regime": "CANNOT_CONFIRM", "risk_tone": "CANNOT_CONFIRM",
        **{field: [] for field in _ROWS}, "cannot_confirm": [reason],
        "model_review": {"status": "NOT_MATERIALIZED", "cannot_confirm": [reason]},
        "source_evidence": [], "source_role": "M09_COMMITTED_REVIEW_UNAVAILABLE",
        "source_sha256": "", "close_chain": None,
        "review_surface": {"tier": "COMPACT_NOT_MATERIALIZED", "status": status,
                           "trade_date": target, "source_role": "M09_COMMITTED_REVIEW_UNAVAILABLE",
                           "source_refs": []},
        "write_policy": "review_only_read_only", "m09_publication": evidence, **_FLAGS,
    }


def project_committed_review(committed: Mapping[str, Any] | None, requested_date: str) -> dict[str, Any]:
    """Return the whole native A review plus separate verified read metadata.

    Malformed requested dates raise ValueError. Missing or invalid committed
    evidence produces an explicit A-only unavailable object for that date.
    Neither condition selects another date, generation, or legacy source.
    """
    target = trade_date(requested_date)
    if committed is None:
        return _unavailable(target, "MISSING", "M09_COMMITTED_REVIEW_MISSING")
    try:
        _validate_committed(committed, target)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return _unavailable(target, "CANNOT_CONFIRM", "M09_COMMITTED_REVIEW_INVALID")
    review = deepcopy(dict(committed["review"]))
    record, identity = committed["record"], committed["identity"]
    model = review["model_review"]
    chain = review.get("close_chain") or {}
    # The reader verifies this independent attempt receipt. It can describe a
    # later failed/interrupted run while the pinned successful generation is
    # still served. Never spread its run, digest, status, or trigger fields into
    # the immutable product's identity or computation classification.
    latest_attempt = deepcopy(committed.get("latest_attempt"))
    evidence = {
        "schema_version": READ_SCHEMA,
        **{key: identity[key] for key in ("trade_date", "model_run_id", *_HASH_FIELDS)},
        "read_status": "VERIFIED",
        "data_kind": record["data_kind"], "execution_kind": record["execution_kind"],
        "business_status": record["business_status"], "computed_at": record["computed_at"],
        "provenance": deepcopy(record["provenance"]), "evidence_status": deepcopy(record["evidence_status"]),
        "membership": deepcopy(record["membership"]), "scope": record["scope"],
        "natural_verified": record["natural_verified"],
        "source_provenance_independently_verified": record["source_provenance_independently_verified"],
        "strict_1500_pit_verified": False,
        "scenario_probabilities_status": "FROZEN_LEGACY_CONSTANTS_NOT_CALIBRATED",
        "review_cannot_confirm": deepcopy(review["cannot_confirm"]),
        "record_cannot_confirm": deepcopy(record["cannot_confirm"]),
        "model_cannot_confirm": deepcopy(model.get("cannot_confirm", [])),
        "close_chain_cannot_confirm": deepcopy(chain.get("cannot_confirm", [])),
        "latest_attempt": latest_attempt,
        "latest_attempt_status": latest_attempt.get("status") if latest_attempt is not None else None,
        "publication_recovery": deepcopy(committed.get("publication_recovery")),
        "reason_codes": [], "safety": deepcopy(record["safety"]),
    }
    if record.get("historical_research") is not None:
        evidence["historical_research"] = deepcopy(record["historical_research"])
    # The frozen product has no overall status. Its native model status is
    # preserved; model success does not replace the recorded chain gap state.
    review.setdefault("status", record["business_status"])
    review["review_surface"] = {
        "tier": "COMPACT_NATIVE", "status": record["business_status"], "trade_date": target,
        "source_role": review["source_role"], "source_refs": deepcopy(review["source_evidence"]),
    }
    review["m09_publication"] = evidence
    return review


def _read_committed(root: Path, target: str) -> Mapping[str, Any] | None:
    # Lazy import keeps the pure projection independent of the producer's
    # optional dependencies. This calls only the public committed reader.
    from .a_close_daily import read_a_close_daily
    return read_a_close_daily(root, target)


def _read_latest_attempt(root: Path, target: str) -> Mapping[str, Any] | None:
    from .a_close_daily import read_a_close_latest_attempt
    return read_a_close_latest_attempt(root, target)


def read_a_close_preview(root: Path, requested_date: str) -> dict[str, Any]:
    """Read once through the pinned-generation reader; perform no writes."""
    target = trade_date(requested_date)
    try:
        committed = _read_committed(Path(root), target)
    except Exception:
        # SDK/path/OS messages are not a public API. Absence or corruption must
        # not select a less authoritative source or start a replacement run.
        return _unavailable(target, "CANNOT_CONFIRM", "M09_COMMITTED_READ_FAILED")
    preview = project_committed_review(committed, target)
    if committed is None:
        # No product exists to carry the independent attempt observation. This
        # helper reads only its index/receipt; it never rereads the head.
        try:
            attempt = _read_latest_attempt(Path(root), target)
            if attempt is not None:
                attempt = _mapping(attempt)
                canonical_bytes(attempt)
                preview["m09_publication"]["latest_attempt"] = deepcopy(dict(attempt))
                preview["m09_publication"]["latest_attempt_status"] = attempt.get("status")
        except Exception:
            reason = "M09_LATEST_ATTEMPT_READ_FAILED"
            preview["m09_publication"]["reason_codes"].append(reason)
            preview["cannot_confirm"].append(reason)
    return preview


def _legacy_projection(review: Mapping[str, Any]) -> dict[str, Any]:
    """The inspected A-only fupan aliases, with no stale rich-source fields."""
    return deepcopy({
        "trade_date": review["trade_date"], "headline": review["headline"],
        "market_regime": review["market_regime"], "risk_tone": review["risk_tone"],
        "first_screen_big_picture": review["big_picture"], "mainlines": review["mainlines"],
        "core_stocks": review["core_stocks"], "observation_pool": review["observation_pool"],
        "next_day_trigger_tree_v2": review["next_day_trigger_tree"],
        "human_video_gap_scorecard": review["quality_gate"], "localized_role_rows": review["core_stocks"],
        "replay_model_v1": review["model_review"], "cannot_confirm": review["cannot_confirm"],
        "m09_publication": review["m09_publication"], **_FLAGS,
    })


def merge_a_close_preview(existing_envelope: Mapping[str, Any], preview: Mapping[str, Any]) -> dict[str, Any]:
    """Pure A-only merge; preserve HK and every unrelated envelope value.

    Changed keys: market_reviews.A, an existing fupan_review_v3, and the new
    m09_publication. The inspected A-only review_core_bundle and
    review_evidence_layers are removed so they cannot attribute M09's review
    to a different source/run. Unknown or mixed-market keys are untouched.
    """
    envelope, a_review = _mapping(existing_envelope), _mapping(preview)
    target = trade_date(envelope.get("trade_date"))
    markets = _mapping(envelope.get("market_reviews"))
    _mapping(markets.get("HK"))
    if a_review.get("trade_date") != target:
        raise ValueError("M09_PREVIEW_DATE_MISMATCH")
    _safe_flags(a_review, _FLAGS)
    evidence = _mapping(a_review.get("m09_publication"))
    if evidence.get("schema_version") != READ_SCHEMA or evidence.get("trade_date") != target:
        raise ValueError("M09_PREVIEW_EVIDENCE_INVALID")
    canonical_bytes(a_review)
    result = deepcopy(dict(envelope))
    result["market_reviews"] = deepcopy(dict(markets))
    result["market_reviews"]["A"] = deepcopy(dict(a_review))
    if "fupan_review_v3" in result:
        result["fupan_review_v3"] = _legacy_projection(a_review)
    result.pop("review_core_bundle", None)
    result.pop("review_evidence_layers", None)
    result["m09_publication"] = deepcopy(dict(evidence))
    return result

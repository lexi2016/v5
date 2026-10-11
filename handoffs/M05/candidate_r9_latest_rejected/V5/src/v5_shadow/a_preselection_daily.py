"""M05 daily A preselection bridge.

Production path intentionally keeps assembler/store contracts:
- run_a_preselection(request)
- PreselectionPoolStore.materialize
- read_pool_snapshot
"""
from __future__ import annotations
from typing import Mapping
from pathlib import Path
try:
    from v5_shadow.digests import sha256_json as _canonical_sha256_json
    from v5_shadow.a_preselection import run_a_preselection as _default_run_a_preselection
    from v5_shadow.composition import no_symlinks, shadow_root, parse_binding
    from infrastructure.scope_gate import StoreGateContext
    from infrastructure.preselection_pool_store import PreselectionPoolStore
except Exception:
    _canonical_sha256_json = None
    _default_run_a_preselection = None
    no_symlinks = shadow_root = None

A_POOL_IDS=frozenset({
    "a_d1_premarket_pool",
    "a_d1_fupan_watchlist_pool",
    "a_d1_stage7_fenshi_review_pool",
    "a_share_research_recommendation_pool",
    "a_share_baimao_research_map",
    "wechat_public_account_v3_preselect",
})

def _sha_request(request, sha256_json=None):
    fn = sha256_json or _canonical_sha256_json
    if fn is None:
        raise RuntimeError("M05_CANONICAL_SHA_UNAVAILABLE")
    return fn(request)

def _validate_required_root(private_root, source_root, lane_roots=(), code_root=None, v4_root=None):
    if no_symlinks is None or shadow_root is None:
        raise RuntimeError("M05_ROOT_HELPER_UNAVAILABLE")
    out = shadow_root(Path(private_root))
    if out != Path(private_root).resolve():
        raise ValueError("M05_ROOT_IDENTITY")
    roots=[Path(source_root)]
    for item in lane_roots:
        if not isinstance(item, str) or not item or not Path(item).is_absolute():
            raise ValueError("M05_LANE_ROOT_BINDING_REQUIRED")
        roots.append(Path(item))
    for name, item in (("code_root", code_root), ("v4_root", v4_root)):
        if not isinstance(item, str) or not item or not Path(item).is_absolute():
            raise ValueError("M05_OWNER_ROOT_BINDING_REQUIRED")
        roots.append(Path(item))
    for r in roots:
        a=no_symlinks(r)
        if a == out or a in out.parents or out in a.parents:
            raise ValueError("M05_ROOT_OVERLAP")
    return out

def _classify_exception(exc):
    return isinstance(exc, ValueError) and str(exc)=="conflicting preselection-pool materialization"

def _outcome(lane, status, **extra):
    d={"kind":lane.get("kind"),"accepted":lane.get("accepted"),
       "reason":lane.get("reason"),"status":status}
    d.update(extra)
    return d

def _artifact(lane, target):
    if lane.get("accepted") is not True:
        return None
    a=lane.get("artifact")
    if not isinstance(a,Mapping):
        raise ValueError("M05_ACCEPTED_WITHOUT_ARTIFACT")
    if a.get("trade_date") != target:
        raise ValueError("M05_TRADE_DATE_MISMATCH")
    if a.get("pool_id") not in A_POOL_IDS:
        raise ValueError("M05_POOL_ID_NOT_ALLOWED")
    return a


def build_strict_store(root, write_gate_context):
    if StoreGateContext is None or not isinstance(write_gate_context, StoreGateContext):
        raise ValueError("M05_WRITE_GATE_CONTEXT_TYPE_REQUIRED")
    return PreselectionPoolStore(
        Path(root),
        write_gate_context=write_gate_context,
        require_write_gate_context=True,
    )

def build_m05_daily(request, *, run_a_preselection=None, store,
                    source_root=None, private_root=None, sha256_json=None,
                    code_root=None, v4_root=None,
                    write_gate_context=None):
    if private_root is None or source_root is None:
        raise ValueError("M05_ROOT_BINDING_REQUIRED")
    request_lane_roots=[]
    for lane in request.get("lanes", []):
        root = lane.get("input_root")
        if not isinstance(root, str) or not root or not Path(root).is_absolute():
            raise ValueError("M05_LANE_ROOT_BINDING_REQUIRED")
        request_lane_roots.append(root)
    if not request_lane_roots:
        raise ValueError("M05_LANE_ROOT_BINDING_REQUIRED")
    if (not isinstance(code_root, str) or not code_root or not Path(code_root).is_absolute()
        or not isinstance(v4_root, str) or not v4_root or not Path(v4_root).is_absolute()):
        raise ValueError("M05_OWNER_ROOT_BINDING_REQUIRED")
    _validate_required_root(private_root, source_root, request_lane_roots, code_root, v4_root)
    if store.root != Path(private_root).resolve():
        raise ValueError("M05_STORE_ROOT_IDENTITY")
    if write_gate_context is None:
        raise ValueError("M05_WRITE_GATE_CONTEXT_REQUIRED")
    if StoreGateContext is None or not isinstance(write_gate_context, StoreGateContext):
        raise ValueError("M05_WRITE_GATE_CONTEXT_TYPE_REQUIRED")
    if not isinstance(store, PreselectionPoolStore):
        raise ValueError("M05_STORE_TYPE_REQUIRED")
    if not getattr(store, "_require_write_gate_context", False):
        raise ValueError("M05_STORE_STRICT_GATE_REQUIRED")
    if getattr(store, "_write_gate_context", None) is not write_gate_context:
        raise ValueError("M05_STORE_GATE_CONTEXT_MISMATCH")
    request_sha=_sha_request(request, sha256_json)
    runner = run_a_preselection or _default_run_a_preselection
    if runner is None:
        raise RuntimeError("M05_ASSEMBLER_UNAVAILABLE")
    result=runner(request)
    if result.get("request_sha256") != request_sha:
        raise ValueError("M05_REQUEST_IDENTITY_MISMATCH")
    if result.get("schema_version") != "v5.a_preselection_assembly.v1":
        raise ValueError("M05_SCHEMA_MISMATCH")

    outcomes=[]
    receipts=[]
    required_failures=[]
    for lane in result["lanes"]:
        art=lane.get("artifact")
        if lane.get("accepted") is not True:
            if isinstance(art,Mapping) and art.get("status")=="CANNOT_CONFIRM" and art.get("source_role")=="EXPECTED_MISSING":
                outcomes.append(_outcome(lane,"EXPECTED_MISSING"))
            else:
                outcomes.append(_outcome(lane,"REJECTED",
                    rejected_artifact=lane.get("rejected_artifact"),
                    rejected_artifact_tagged=lane.get("rejected_artifact_tagged"),
                    rejected_artifact_status=lane.get("rejected_artifact_status")))
            continue

        artifact=_artifact(lane,request["target_date"])
        try:
            stored=store.materialize(artifact)
            snap=store.read_pool_snapshot(request["target_date"],artifact["pool_id"])
        except Exception as exc:
            if _classify_exception(exc):
                outcomes.append(_outcome(lane,"CONFLICT",
                    error_type=type(exc).__name__,error=str(exc)))
                continue
            raise

        if stored["sha256"] != snap["artifact_sha256"] or snap["artifact"] != artifact:
            raise ValueError("M05_SNAPSHOT_IDENTITY_MISMATCH")

        receipts.append({
            "pool_id":artifact["pool_id"],
            "artifact_sha256":stored["sha256"],
            "artifact_raw_sha256":snap["artifact_raw_sha256"],
            "manifest_raw_sha256":snap["manifest_raw_sha256"],
            "receipt_raw_sha256":snap["receipt_raw_sha256"],
            "artifact_relative_path":snap["artifact_relative_path"],
            "manifest_relative_path":snap["manifest_relative_path"],
            "receipt_relative_path":snap["receipt_relative_path"],
            "source_role":artifact.get("source_role"),
            "source_sha256":artifact.get("source_sha256"),
            "source_run_id":artifact.get("source_run_id"),
            "source_artifact_sha256":artifact.get("source_artifact_sha256"),
            "source_manifest_sha256":artifact.get("source_manifest_sha256"),
            "source_receipt_sha256":artifact.get("source_receipt_sha256"),
            "rows":artifact.get("rows"),
            "pool_scores":[r.get("pool_score") for r in artifact.get("rows",[])],
        })
        outcomes.append(_outcome(lane,"SUCCESS"))

    if not receipts:
        status="DEFERRED" if all(x["status"]=="EXPECTED_MISSING" for x in outcomes) else "REJECTED"
        return {"status":status,"row_count":None,"request_sha256":request_sha,
                "outcomes":outcomes,"receipts":[]}
    if any(x["status"] in {"EXPECTED_MISSING","REJECTED","CONFLICT"} for x in outcomes):
        status="PARTIAL"
    else:
        status="READY"
    return {"status":status,"request_sha256":request_sha,
            "row_count":sum(len(r["rows"]) for r in receipts),
            "outcomes":outcomes,"receipts":receipts}

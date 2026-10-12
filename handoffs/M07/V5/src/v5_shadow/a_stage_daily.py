"""M07 A stage private adapter.

No authority is created here. Formal admission requires immutable upstream
artifacts supplied by approved owner adapters.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json, math, re

_SHA = re.compile(r"^[0-9a-f]{64}$")

def _canonical_digest(value):
    def bad(x):
        if isinstance(x,float) and (math.isnan(x) or math.isinf(x)):
            raise ValueError("NAN_NOT_ALLOWED")
    json.loads(json.dumps(value, default=bad))
    raw=json.dumps(value, ensure_ascii=False, allow_nan=False,
                   sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()

def _require_receipt(name, value, target_date):
    if not isinstance(value, dict) or value.get("status")!="VERIFIED":
        raise ValueError(f"{name}_NOT_VERIFIED")
    for k in ("sha256","owner","artifact_ref","manifest_sha256","receipt_sha256"):
        if not value.get(k): raise ValueError(f"{name}_{k.upper()}_MISSING")
    for k in ("sha256","manifest_sha256","receipt_sha256"):
        if not _SHA.fullmatch(value[k]): raise ValueError(f"{name}_{k}_INVALID")
    if value.get("target_date")!=target_date:
        raise ValueError(f"{name}_DATE_MISMATCH")

def _merge_rows(pool, live, research):
    pool_rows={_code(r["code"]):deepcopy(r) for r in pool.get("rows",[])}
    if len(pool_rows)!=len(pool.get("rows",[])):
        raise ValueError("M05_DUPLICATE_CODE")
    research_rows={_code(r["code"]):r for r in research.get("rows",[])}
    out=[]
    for r in live.get("rows",[]):
        c=_code(r["code"])
        if c not in pool_rows: continue
        x=deepcopy(pool_rows[c])
        # market data may fill observation fields only
        for k in ("open","high","low","close","volume","amount","bid","ask",
                  "captured_at","acquired_at"):
            if k in r: x[k]=deepcopy(r[k])
        if c in research_rows:
            for k in ("news_quality_score","research_quality_score",
                      "slot","delta","reason","health"):
                if k in research_rows[c]: x[k]=deepcopy(research_rows[c][k])
        out.append(x)
    return out

def _code(v):
    if not isinstance(v,str): raise ValueError("CODE_INVALID")
    c=v.strip()
    if not re.fullmatch(r"[0-9A-Za-z.]{4,10}",c):
        raise ValueError("CODE_INVALID")
    return c.upper()

def run_a_stage_daily(*, target_date, stage_id, cutoff, pool_input,
                      live_input, research_input, selector, publish_verified):
    if stage_id in ("STAGE_0925","STAGE_1545_1555"):
        raise ValueError("A_SPECIAL_WINDOW_REQUIRES_ORIGINAL_ROUTE")
    if live_input.get("market")!="A_SHARE":
        raise ValueError("A_STAGE_MARKET_INVALID")
    _require_receipt("M05",pool_input,target_date)
    _require_receipt("M01",live_input,target_date)
    _require_receipt("M04",research_input,target_date)

    rows=_merge_rows(pool_input,live_input,research_input)
    requested=live_input.get("requested_rows")
    missing=live_input.get("missing_symbols",[])
    cannot=live_input.get("cannot_confirm",[])
    request={
      "market":"A_SHARE","target_date":target_date,"stage_id":stage_id,
      "data_kind":live_input["data_kind"],"rows":rows,
      "rows_sha256":_canonical_digest(rows),
      "source_status":live_input["source_status"],
      "requested_rows":requested if requested is not None else len(rows),
      "missing_symbols":missing,"cannot_confirm":cannot,
    }
    before=_canonical_digest(rows)
    result=selector(request)
    if _canonical_digest(rows)!=before:
        raise ValueError("SELECTOR_MUTATED_INPUT")
    if not isinstance(result,dict) or "artifact" not in result:
        raise ValueError("SELECTOR_ARTIFACT_MISSING")
    payload={
      "identity_sha256":_canonical_digest({
        "target_date":target_date,"stage_id":stage_id,"cutoff":cutoff,
        "request_sha256":_canonical_digest(request),
        "M05":pool_input["sha256"],"M01":live_input["sha256"],
        "M04":research_input["sha256"]}),
      "selection":result,"natural":False,
      "safety_flags":{"production_allowed":False}}
    if publish_verified is None:
        raise ValueError("PUBLISHER_NOT_BOUND")
    return publish_verified(payload)

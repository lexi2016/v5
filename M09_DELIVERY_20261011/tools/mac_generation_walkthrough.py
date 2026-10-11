"""Independent ENGINEERING-only Mac two-slot/CAS/rollback demonstration.

All rows are invented fixtures named SYNTHETIC. All writes stay inside a new
explicit evidence directory. This is never natural or real-data acceptance.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from mac_real_input_check import canonical, checked_path, digest, environment, save


def snapshot(root):
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("unexpected symlink in private engineering evidence")
        if path.is_file():
            result[str(path.relative_to(root))] = {"sha256":digest(path),"bytes":path.stat().st_size}
    return result


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--after", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    after, out = checked_path(args.after), checked_path(args.out)
    if out.is_relative_to(after) or after.is_relative_to(out):
        raise ValueError("candidate and engineering output must be disjoint")
    if any(part in ("com.lexi.v4.local", "com.lexi.v35.local") for part in out.parts):
        raise ValueError("active application roots are not engineering output roots")
    if not out.parent.is_dir():
        raise ValueError("output parent must already exist")
    out.mkdir(mode=0o700)
    sys.path.insert(0, str(after / "V5/src"))
    from v5_shadow.a_close_daily import initialize_a_close_root, read_a_close_daily, rollback_a_close_daily, run_a_close_daily
    from v5_shadow.a_close_daily_api import read_a_close_preview, merge_a_close_preview
    source, root = out / "synthetic_source", out / "private_m09"
    source.mkdir(mode=0o700)
    rows = [dict(trade_date="20261009",ts_code=f"{i:06}.SZ",name=f"SYNTHETIC_MAC_{i}",pct_chg=pct,
                 amount=100000000.0,bar_close_pos=.8,tdx_industry_code="I1" if i < 4 else "I2",
                 tdx_industry_name="SYNTHETIC_INDUSTRY_A" if i < 4 else "SYNTHETIC_INDUSTRY_B")
            for i,pct in enumerate((10.,2.,-10.,-1.,0.,3.),1)]
    save(source / "panel.json", rows)
    (source / "panel.txt").write_text("panel.json\n", encoding="utf-8")
    (source / "members.txt").write_text("".join(row["ts_code"]+"\n" for row in rows), encoding="utf-8")
    provenance = dict(source_id="SYNTHETIC_MAC_PANEL",version="engineering-v1",status="READY",authority_status="VERIFIED",coverage_rate=1.,
                      captured_at="2026-10-09T15:40:00+08:00",acquired_at="2026-10-09T15:40:00+08:00",available_at="2026-10-09T15:41:00+08:00")
    save(source / "receipt.json", dict(trade_date="20261009",**provenance))
    manifest = dict(schema_version="v5.m09.input.v1",trade_date="20261009",data_kind="SYNTHETIC",
                    panel=dict(pointer_path="panel.txt",pointer_sha256=digest(source/"panel.txt"),sha256=digest(source/"panel.json"),format="SYNTHETIC_JSON",row_count=len(rows)),
                    membership=dict(path="members.txt",sha256=digest(source/"members.txt"),scope="DECLARED_UNIVERSE",source_id="SYNTHETIC_MAC_MEMBERS",version="engineering-v1",
                                    captured_at="2026-10-09T15:40:00+08:00",available_at="2026-10-09T15:41:00+08:00"),
                    provenance=dict(provenance,receipt_path="receipt.json",receipt_sha256=digest(source/"receipt.json")),evidence={})
    save(source / "input.json",manifest)
    initialize_a_close_root(root)

    def request(attempt,slot,revision="mac-engineering-v1",**extra):
        return dict(schema_version="v5.m09.daily_request.v1",trade_date="20261009",slot=slot,
                    job_id="m09_mac_engineering_"+slot.replace(":",""),attempt_id=attempt,execution_kind="ENGINEERING",
                    triggered_at=datetime.now(timezone.utc).isoformat(),source_root=str(source),input_manifest="input.json",
                    input_manifest_sha256=digest(source/"input.json"),configuration_revision=revision,**extra)

    first = run_a_close_daily(root,request("first-1605","16:05"))
    require(first["status"]=="SUCCEEDED",repr(first))
    first_run_before = snapshot(root/"runs"/first["run_id"])
    reused = run_a_close_daily(root,request("second-1710","17:10"))
    require(reused["status"]=="SUCCEEDED" and reused["reused"] and reused["run_id"]==first["run_id"],repr(reused))
    require(reused["trigger_sha256"]!=first["trigger_sha256"],"two slots must have separate trigger identities")
    replacement = run_a_close_daily(root,request("new-config-1710","17:10","mac-engineering-v2"))
    require(replacement["status"]=="SUCCEEDED" and replacement["run_id"]!=first["run_id"],repr(replacement))
    require(snapshot(root/"runs"/first["run_id"])==first_run_before,"new generation altered the first run")
    conflict = run_a_close_daily(root,request("cas-conflict","17:10","mac-engineering-v2",expected_generation_sha256="0"*64))
    require(conflict["status"]=="FAILED" and "CAS" in conflict.get("reason",""),repr(conflict))
    require(read_a_close_daily(root,"20261009")["identity"]["generation_sha256"]==replacement["generation_sha256"],"CAS failure altered the serving generation")
    rows[0]["amount"] = -1
    (source/"panel.json").write_bytes(canonical(rows))
    manifest["panel"]["sha256"] = digest(source/"panel.json")
    (source/"input.json").write_bytes(canonical(manifest))
    rejected = run_a_close_daily(root,request("bad-input-1710","17:10","mac-engineering-v2"))
    require(rejected["status"]=="FAILED",repr(rejected))
    require(read_a_close_daily(root,"20261009")["identity"]["generation_sha256"]==replacement["generation_sha256"],"later input failure altered the serving generation")
    pinned_first = read_a_close_daily(root,"20261009",generation_sha256=first["generation_sha256"])
    require(pinned_first["identity"]["model_run_id"]==first["run_id"],"the full first generation is no longer independently readable")
    all_runs_before = snapshot(root/"runs")
    rollback = rollback_a_close_daily(root,"20261009",first["generation_sha256"],replacement["generation_sha256"],
                                     "SYNTHETIC ENGINEERING ONLY: independent Mac predecessor rollback")
    restored = read_a_close_daily(root,"20261009")
    require(restored["identity"]["model_run_id"]==first["run_id"],"rollback did not restore the verified predecessor")
    require(snapshot(root/"runs")==all_runs_before,"rollback deleted or altered immutable runs")
    state_before_reads = snapshot(root)
    hk = {"trade_date":"20261009","source_role":"SYNTHETIC_HK_SENTINEL","rows":[{"symbol":"HK_SENTINEL","value":"unchanged"}]}
    envelope = {"trade_date":"20261009","market_reviews":{"A":{},"HK":hk},"research_review":{"sentinel":"retain"},"production_allowed":False}
    for _ in range(3):
        preview = read_a_close_preview(root,"20261009")
        require(preview["m09_publication"]["read_status"]=="VERIFIED",repr(preview))
        merged = merge_a_close_preview(envelope,preview)
        require(merged["market_reviews"]["HK"]==hk,"A projection changed the HK sentinel")
        require(read_a_close_daily(root,"20261008") is None,"exact-date read selected another date")
    require(snapshot(root)==state_before_reads,"GET-compatible reads wrote private product files")
    save(out/"walkthrough_receipts.json",{"first":first,"reused":reused,"replacement":replacement,"cas_conflict":conflict,"later_rejection":rejected,"rollback":rollback})
    save(out/"immutable_runs_after_rollback.json",all_runs_before)
    report = {"schema_version":"m09.mac_engineering_walkthrough.v1","status":"ENGINEERING_WALKTHROUGH_PASSED",
              "environment":environment(),"fixture_class":"SYNTHETIC","execution_kind":"ENGINEERING",
              "restored_identity":restored["identity"],"private_root":str(root),
              "two_slots_distinct_receipts_one_calculation":True,"new_configuration_new_run":True,
              "cas_and_bad_input_preserve_success":True,"rollback_preserves_all_runs":True,"read_side_effects":False,
              "HK_sentinel_unchanged":True,"actual_HK_service_acceptance":"NOT_RUN","real_input_acceptance":"NOT_RUN","natural_acceptance":"NOT_RUN"}
    save(out/"walkthrough_result.json",report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()

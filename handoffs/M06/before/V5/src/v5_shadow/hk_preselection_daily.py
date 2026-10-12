"""M06 HK02 producer orchestration R4.

Only orchestrates existing HK02 producer and strict reader. No model/ranking changes.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,json,os,tempfile,shutil

from v5_shadow import hk_preselection as strict_reader

def _sha(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def _inventory(root):
    root=Path(root)
    out={}
    for p in sorted(root.rglob("*")):
        if p.is_symlink(): raise ValueError("HK_SYMLINK_INPUT")
        if p.is_file():
            rel=str(p.relative_to(root))
            out[rel]=_sha(p)
    return out

def _same_or_overlap(a,b):
    a=Path(a).resolve(); b=Path(b).resolve()
    return a==b or a in b.parents or b in a.parents

def _restore_master(src,dst,date):
    from shared_data.hk_security_master import restore_verified_hk_security_master
    return restore_verified_hk_security_master(source_store_root=src,target_store_root=dst,trade_date=date)

def _verify_inventory(root,inv):
    if not isinstance(inv,dict) or not inv: raise ValueError("HK_FILE_MAP_REQUIRED")
    for k,v in inv.items():
        if not isinstance(v,str) or len(v)!=64: raise ValueError("HK_BAD_SHA")
        p=Path(root)/k
        if p.is_symlink() or not p.is_file() or _sha(p)!=v:
            raise ValueError("HK_INPUT_CHANGED")

def _strict_readback(staging, dates, filemap):
    req={
      "target_date":dates["target_date"],
      "signal_date":dates["signal_date"],
      "eligibility_source_date":dates["eligibility_source_date"],
      "research_cutoff":dates["cutoff"],
      "data_kind":"HK_CONNECT_D1_TOP100_0_2",
      "input_root":str(staging),
      "files":filemap,
    }
    result=strict_reader.run_hk_preselection(req)
    if result.get("status")!="ASSEMBLED" or "artifact" not in result:
        raise ValueError("HK_STRICT_READER_NOT_ASSEMBLED")
    return result

def produce_hk02_daily(*,store_root,asset_root,private_root,
 signal_date,target_date,eligibility_source_date,cutoff,files):
    store_root=Path(store_root); asset_root=Path(asset_root); private_root=Path(private_root)
    if _same_or_overlap(store_root,private_root) or _same_or_overlap(asset_root,private_root):
        raise ValueError("HK_PRIVATE_ROOT_OVERLAP")
    _verify_inventory(asset_root,files)

    from shared_data.hk_0_2 import load_frozen_hk_0_2_assets,materialize_frozen_hk_0_2,read_verified_hk_0_2_pool
    assets=load_frozen_hk_0_2_assets(asset_root)
    before=_inventory(asset_root)

    private_root.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix=".m06-",dir=str(private_root.parent)))
    try:
        _restore_master(store_root,staging,eligibility_source_date)
        result=materialize_frozen_hk_0_2(staging,asset_root,signal_date=signal_date,target_date=target_date,eligibility_source_date=eligibility_source_date)
        if not isinstance(result,dict) or result.get("ok") is not True or result.get("status")!="READY":
            raise ValueError("HK_GENERATOR_NOT_READY")
        after=_inventory(asset_root)
        if before!=after: raise ValueError("HK_ASSET_CHANGED")

        pool=read_verified_hk_0_2_pool(staging,target_date=target_date,expected_signal_date=signal_date,expected_eligibility_source_date=eligibility_source_date)
        rows=[dict(x) for x in pool.rows]
        if len(rows)!=100: raise ValueError("HK_POOL_SIZE")

        filemap={str(Path(x["artifact_path"]).relative_to(staging)):x["artifact_sha256"] for x in [pool.run.verification]}
        strict=_strict_readback(staging,{"target_date":target_date,"signal_date":signal_date,"eligibility_source_date":eligibility_source_date,"cutoff":cutoff},filemap)

        v=pool.run.verification
        receipt={"schema":"v5.m06.hk02.daily_producer.v3",
        "run_id":v["run_id"],"artifact_sha256":v["artifact_sha256"],
        "manifest_sha256":v["manifest_sha256"],"receipt_sha256":v["receipt_sha256"],
        "panel_sha256":assets.panel_manifest.get("panel_sha256"),
        "model_bundle_sha256":assets.model_manifest.get("bundle_sha256"),
        "reader_status":strict["status"],"row_count":100}
        (staging/"producer_receipt.json").write_text(json.dumps(receipt,sort_keys=True))
        (staging/"reader_receipt.json").write_text(json.dumps(strict,sort_keys=True))
        if private_root.exists() and any(private_root.iterdir()):
            raise ValueError("HK_EXISTING_FINAL")
        os.replace(staging,private_root)
        return receipt
    except Exception:
        shutil.rmtree(staging,ignore_errors=True)
        raise

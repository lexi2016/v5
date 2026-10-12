"""M06 verified SOURCE_SNAPSHOT cold consumer."""
from __future__ import annotations
from pathlib import Path
import hashlib

SCHEMA="v5.hk_preselection_verified_request.v1"
ROLE="HK_CONNECT_D1_TOP100_0_2"
SAFETY={"natural_verified":False,"model_weights_reverified":False}

def _sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def _sha_ok(v,n):
    if not isinstance(v,str) or len(v)!=64:
        raise ValueError("M06_SOURCE_REF_INVALID:"+n)
    int(v,16)
    return v

def _validate_source_ref(e):
    if not isinstance(e,dict): raise ValueError("M06_SOURCE_REF_INVALID")
    for k in ("role","run_id","artifact_sha256","manifest_sha256","receipt_sha256","artifact_relative"):
        if not e.get(k): raise ValueError("M06_SOURCE_REF_MISSING:"+k)
    if e["role"]!=ROLE: raise ValueError("M06_SOURCE_ROLE_INVALID")
    for k in ("artifact_sha256","manifest_sha256","receipt_sha256"): _sha_ok(e[k],k)

def _validate_files(root, files):
    if not isinstance(files,dict) or not files: raise ValueError("M06_REQUIRED_FILE_MISSING")
    root=Path(root)
    for rel,digest in files.items():
        r=Path(rel)
        if r.is_absolute() or ".." in r.parts: raise ValueError("M06_PATH_ESCAPE")
        p=root/r
        if p.is_symlink() or not p.exists(): raise ValueError("M06_REQUIRED_FILE_MISSING")
        if _sha(p)!=digest: raise ValueError("M06_INPUT_CHANGED")

def _validate_request(request):
    req={"schema_version","target_date","signal_date","eligibility_source_date","research_cutoff","data_kind","input_root","files","expected_source"}
    if not isinstance(request,dict) or not req.issubset(request): raise ValueError("M06_REQUIRED_REQUEST_FIELD")
    if request["schema_version"]!=SCHEMA or request["data_kind"]!="SOURCE_SNAPSHOT": raise ValueError("M06_SOURCE_KIND_INVALID")
    _validate_source_ref(request["expected_source"])
    _validate_files(request["input_root"],request["files"])
    return request

def _assemble_verified(request):
    from . import hk_preselection_runtime_capsule as capsule
    return capsule.assemble_verified_source_snapshot(request)

def run_verified_hk_preselection(request):
    _validate_request(request)
    result=_assemble_verified(request)
    if result.get("status")=="ASSEMBLED":
        result["data_kind"]="VERIFIED_SOURCE_SNAPSHOT"
        result.update(SAFETY)
    else:
        result["data_kind"]="SOURCE_SNAPSHOT"
    return result

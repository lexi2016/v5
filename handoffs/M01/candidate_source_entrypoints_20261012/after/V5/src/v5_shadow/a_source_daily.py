
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import hashlib, json, re

from infrastructure.owned_io import SafeRoot
from infrastructure.formula_generation import (
    FORMULA_GENERATION_POINTER_NAME,
    read_formula_generation,
)
from .composition import no_symlinks, shadow_root

class M01BindingError(Exception):
    pass

@dataclass(frozen=True)
class ASourceBinding:
    schema:str
    status:str
    target_date:str
    generation_id:str
    generation_path:str
    generation_sha256:str
    manifest_sha256:str
    manifest_evidence_sha256:str
    sync_receipt_sha256:str
    strict_source_verified:bool
    cutoff_status:str

FIELDS=set(ASourceBinding.__dataclass_fields__)

def validate_date(v):
    if type(v) is not str or re.fullmatch(r"[0-9]{8}", v) is None:
        raise M01BindingError("invalid_date")
    try:
        datetime.strptime(v,"%Y%m%d")
    except ValueError as e:
        raise M01BindingError("invalid_date") from e
    return v

def validate_path(v):
    if type(v) is not str:
        raise M01BindingError("path_type")
    if "\x00" in v or "\\" in v or not v.startswith("/") or ".." in Path(v).parts:
        raise M01BindingError("path")
    return v

def sha(v):
    if type(v) is not str or re.fullmatch(r"[0-9a-f]{64}",v) is None:
        raise M01BindingError("sha")
    return v

def project(r):
    if r.get("status")!="READY":
        raise M01BindingError("status")
    if type(r.get("strict_source_verified")) is not bool or r["strict_source_verified"] is not True:
        raise M01BindingError("strict")
    gid=r["generation_id"]
    if type(gid) is not str or re.fullmatch(r"[0-9a-f]{64}",gid) is None:
        raise M01BindingError("generation_id")
    p=r["path"]
    if isinstance(p,Path):
        p=str(p)
    return ASourceBinding(
        "v5.m01.a_source_binding.r15","BOUND",
        validate_date(r["target_date"]),gid,validate_path(p),
        sha(r["sha256"]),
        sha(r["input_manifest"]["manifest_sha256"]),
        sha(r["input_manifest_evidence"]["sha256"]),
        sha(r["source"]["sync_receipt_sha256"]),
        True,"UNVERIFIED")

def identity(b):
    return hashlib.sha256(json.dumps(asdict(b),sort_keys=True,separators=(",",":")).encode()).hexdigest()

def binding_relative(b):
    return f"m01/a_source/{b.target_date}/{identity(b)}/binding.json"

def parse_binding(raw):
    def dup(pairs):
        out={}
        for k,v in pairs:
            if k in out:
                raise M01BindingError("duplicate_key")
            out[k]=v
        return out
    try:
        obj=json.loads(raw.decode("utf-8"),object_pairs_hook=dup)
    except M01BindingError:
        raise
    except Exception as e:
        raise M01BindingError("json") from e
    if type(obj) is not dict or set(obj)!=FIELDS:
        raise M01BindingError("fields")
    b=ASourceBinding(**obj)
    if b.schema!="v5.m01.a_source_binding.r15" or b.status!="BOUND":
        raise M01BindingError("schema")
    if type(b.strict_source_verified) is not bool or b.strict_source_verified is not True:
        raise M01BindingError("strict")
    if b.cutoff_status!="UNVERIFIED":
        raise M01BindingError("cutoff")
    validate_date(b.target_date)
    validate_path(b.generation_path)
    if type(b.generation_id) is not str or re.fullmatch(r"[0-9a-f]{64}",b.generation_id) is None:
        raise M01BindingError("generation_id")
    for x in (b.generation_sha256,b.manifest_sha256,b.manifest_evidence_sha256,b.sync_receipt_sha256):
        sha(x)
    return b

def verify_binding_bytes(raw,relative,reader,expected=None):
    b=parse_binding(raw)
    if relative != binding_relative(b):
        raise M01BindingError("relative")
    current=project(reader(b.generation_path,expected_target_date=b.target_date,require_source=True))
    if current!=b or (expected is not None and current!=expected):
        raise M01BindingError("drift")
    return b

def _business_path(value):
    # Inspect the original value before Path can coerce or normalise it.
    if type(value) is str:
        text=value
    elif isinstance(value,Path):
        text=str(value)
    else:
        raise M01BindingError("path_type")
    return Path(validate_path(text))


def _make_context(private_root,source_root):
    source_path=_business_path(source_root)
    output_path=_business_path(private_root)
    source=no_symlinks(source_path)
    if not source.is_dir():
        raise M01BindingError("source_directory")
    output=no_symlinks(output_path)
    if source==output or source in output.parents or output in source.parents:
        raise M01BindingError("root_overlap")
    output=shadow_root(output)
    safe=SafeRoot(output)
    if safe.read_bytes(".v5-shadow-root",max_bytes=64)!=b"v5.shadow-root.v1\n":
        raise M01BindingError("marker")
    return safe,source


def bounded_reader(source_root,reader,no_symlinks,FORMULA_GENERATION_POINTER_NAME):
    def call(pointer,**kwargs):
        p=no_symlinks(_business_path(pointer))
        if not p.is_relative_to(source_root):
            raise M01BindingError("source_root")
        if p.is_dir():
            p=p/FORMULA_GENERATION_POINTER_NAME
        # The appended pointer itself may be a symlink; inspect it too.
        p=no_symlinks(_business_path(p))
        if not p.is_relative_to(source_root):
            raise M01BindingError("source_root")
        result=reader(p,**kwargs)
        q=no_symlinks(_business_path(result["path"]))
        if not q.is_relative_to(source_root):
            raise M01BindingError("reader_path")
        return result
    return call


def create_binding_from_roots(*,private_root,source_root,generation_pointer,target_date):
    validate_date(target_date)
    pointer=_business_path(generation_pointer)
    safe,source=_make_context(private_root,source_root)
    return create_binding(safe,pointer,target_date,
        bounded_reader(source,read_formula_generation,no_symlinks,FORMULA_GENERATION_POINTER_NAME))


def read_binding_from_roots(*,private_root,source_root,relative):
    safe,source=_make_context(private_root,source_root)
    return read_and_verify_binding(safe,relative,
        bounded_reader(source,read_formula_generation,no_symlinks,FORMULA_GENERATION_POINTER_NAME))

def read_and_verify_binding(safe_root,relative,reader):
    return verify_binding_bytes(safe_root.read_bytes(relative,max_bytes=65536),relative,reader)

def create_binding(safe_root,generation_pointer,target_date,reader):
    current=project(reader(generation_pointer,expected_target_date=validate_date(target_date),require_source=True))
    rel=binding_relative(current)
    raw=json.dumps(asdict(current),sort_keys=True).encode()
    with safe_root.kernel_lock("m01/.binding.lock",timeout=5):
        try:
            old=safe_root.read_bytes(rel,max_bytes=65536)
        except FileNotFoundError:
            old=None
        if old is not None:
            return verify_binding_bytes(old,rel,reader,expected=current)
        safe_root.write_bytes(rel,raw,require_absent=True)
        return verify_binding_bytes(safe_root.read_bytes(rel,max_bytes=65536),rel,reader,expected=current)

"""M03 incremental orchestration.

Preserves R9 binding semantics and adds explicit cold-process entry adapters.
Production execution still requires the frozen owner runtime fixture.
"""
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess, sys, tempfile


@dataclass(frozen=True)
class USSourceRequest:
    trade_date: str
    capture_phase: str
    session: str
    cutoff: str
    source_root: Path
    snapshot_root: Path
    binding_root: Path
    owner_root: Path
    v5_src: Path


def parse_utc(v):
    if not isinstance(v, str):
        raise ValueError("M03_TIME_REQUIRED")
    if v.endswith("Z"):
        v=v[:-1]+"+00:00"
    d=datetime.fromisoformat(v)
    if d.tzinfo is None:
        raise ValueError("M03_TIMEZONE_REQUIRED")
    return d.astimezone(timezone.utc)


def source_paths(root, date):
    r=Path(root)
    return {
        "payload": r/f"research/peripherals/{date}/external_finance.json",
        "receipt": r/f"receipts/research/peripherals/{date}/external_finance.json",
        "manifest": r/"research/peripherals/manifest.json"
    }


def collector_argv(req):
    return [
        "--owner-root", str(req.owner_root),
        "--allow-network-capture",
        "--",
        "--data-root", str(req.snapshot_root),
        "--trade-date", req.trade_date,
        "--capture-phase", req.capture_phase,
    ]


def run_cold_collector(req, runner=subprocess.run):
    bootstrap = (
        "import sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "from v5_shadow.cloud_us_collector import main;"
        "raise SystemExit(main(sys.argv[2:]))"
    )
    p=runner([sys.executable,"-I","-B","-c",bootstrap,
              str(req.v5_src),*collector_argv(req)],
             capture_output=True,text=True,timeout=300)
    return {"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr}


def select_capture(payload, req):
    rows=[x for x in payload.get("us_session_captures",[])
          if x.get("us_session_date")==req.session
          and x.get("capture_phase")==req.capture_phase]
    if len(rows)!=1:
        raise ValueError("M03_CAPTURE_AMBIGUOUS")
    return rows[0]


def create_binding(req,payload):
    if not isinstance(payload,dict) or not payload:
        raise ValueError("M03_PAYLOAD_NOT_VALIDATED")
    c=select_capture(payload,req)
    if payload.get("trade_date")!=req.trade_date:
        raise ValueError("M03_DATE_MISMATCH")
    if parse_utc(c["captured_at"]) > parse_utc(req.cutoff):
        raise ValueError("M03_CAPTURE_AFTER_CUTOFF")
    paths=source_paths(req.snapshot_root,req.trade_date)
    return {
        "status":"VALIDATED_SOURCE_BINDING",
        "identity":c,
        "market_snapshot":payload.get("market_snapshot",{}),
        "source_sha256":{k:hashlib.sha256(v.read_bytes()).hexdigest()
                         for k,v in paths.items()}
    }


def persist_binding(binding,root):
    if binding["status"]!="VALIDATED_SOURCE_BINDING":
        return binding
    name=hashlib.sha256(json.dumps(binding,sort_keys=True).encode()).hexdigest()+".json"
    target=Path(root)/name
    if target.exists():
        old=json.loads(target.read_text())
        if old!=binding:
            raise ValueError("M03_BINDING_CONFLICT")
        return old
    fd,tmp=tempfile.mkstemp(dir=Path(root))
    with os.fdopen(fd,"w") as f:
        json.dump(binding,f,sort_keys=True)
        f.flush(); os.fsync(f.fileno())
    os.link(tmp,target); os.unlink(tmp)
    return json.loads(target.read_text())

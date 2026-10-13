"""Fresh-process original-owner dispatcher. No replacement research algorithm."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from .owner_sources import OWNER_ROOT, verify_sources


def execute(request):
    verify_sources()
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(OWNER_ROOT))
    op=request['operation']; day=request['target_date']; state=Path(request['state_root'])
    called=False; entry=None
    try:
        if op=='capture':
            from domains.intraday_research import capture_intraday
            entry='domains.intraday_research.capture_intraday'; called=True
            result=capture_intraday(day,request['slot'],config_path=Path(request['config_path']),
                config_sha256=request['config_sha256'],source_manifest_sha256=request['owner_manifest_sha256'])
            return {'status':'OWNER_RETURNED','owner_called':True,'owner_entry':entry,'owner_result':result}
        if op=='generate':
            from domains.research_review_generation.assembly import assemble_runtime
            from domains.research_review_generation.generation import run_generation
            entry='domains.research_review_generation.assembly.assemble_runtime'; called=True
            runtime=assemble_runtime(config_path=Path(request['config_path']),config_sha256=request['config_sha256'],
                implementation_manifest_sha256=request['owner_manifest_sha256'])
            entry='domains.research_review_generation.generation.run_generation'
            result=run_generation(day,review_root=state/'reviews',runtime=runtime,replace=False)
            return {'status':'OWNER_RETURNED','owner_called':True,'owner_entry':entry,'owner_result':result}
        if op=='read':
            from domains.intraday_research import read_intraday_day
            from domains.daily_research_review import load_daily_research_review
            return {'intraday_research':read_intraday_day(day,intraday_root=state/'intraday',review_root=state/'reviews'),
                    'research_review':load_daily_research_review(day,review_root=state/'reviews')}
        if op=='read_slot':
            from infrastructure.owned_io import SafeRoot
            from domains.intraday_research import _commit, read_intraday_day
            io=SafeRoot(state/'intraday'); slot=request['slot']; stem=day+'/'+slot.replace(':','')
            snapshot,proof=_commit(io,day,slot,expected_config=request['config_sha256'])
            raw_receipt=io.read_bytes('receipts/'+stem+'.json'); receipt=json.loads(raw_receipt)
            raw_manifest=io.read_bytes(receipt['manifest']['path']); manifest=json.loads(raw_manifest)
            paths={'receipt':'receipts/'+stem+'.json','manifest':receipt['manifest']['path'],
                   'artifact':manifest['artifact']['path'],'input':manifest['input']['path']}
            # Preserve the exact original envelopes, not a relabelled success flag.
            bundle={key:json.loads(io.read_bytes(path)) for key,path in paths.items()}
            return {'snapshot':snapshot,'proof':proof,'owner_bundle':bundle,
                    'intraday_research':read_intraday_day(day,intraday_root=state/'intraday',review_root=state/'reviews')}
        if op=='read_daily':
            from infrastructure.owned_io import SafeRoot
            from domains.daily_research_review import load_daily_research_review
            raw=SafeRoot(state/'reviews').read_bytes(day+'.json')
            return {'artifact_sha256':hashlib.sha256(raw).hexdigest(),'owner_artifact':json.loads(raw),
                    'research_review':load_daily_research_review(day,review_root=state/'reviews')}
        raise ValueError('M11_OPERATION_INVALID')
    except Exception as exc:
        # Preserve original refusal state without leaking provider errors or local paths.
        missing=OWNER_ROOT/'domains/research_review_generation/OWNED_SOURCE_MANIFEST.json'
        cause=exc
        while cause.__cause__ is not None:cause=cause.__cause__
        if isinstance(cause,FileNotFoundError) and Path(str(getattr(cause,'filename',''))).name==missing.name:
            code='M11_ORIGINAL_SOURCE_MANIFEST_MISSING'
        elif isinstance(exc,ModuleNotFoundError):code='M11_OWNER_DEPENDENCY_MISSING'
        else:code=getattr(exc,'error_code','M11_OWNER_REFUSED')
        return {'status':'BLOCKED','error_code':code,'attempt_state':getattr(exc,'attempt_state',None),
                'owner_entry':entry,'owner_called':called,'exception_type':type(exc).__name__,
                'production_allowed':False,'orders_sent':False,'buy_gate_updated':False}


def main():
    request=json.load(sys.stdin)
    print(json.dumps(execute(request),ensure_ascii=False,sort_keys=True,allow_nan=False))


if __name__=='__main__':main()

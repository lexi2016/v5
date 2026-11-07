"""Read-only callable chain: real V3 receipt reuse + checked dated decision.
No source acquisition, dispatch, owner admission or natural-run success claim.
"""
import argparse,datetime,hashlib,json,sys,importlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=None;PIN_FILE=None;PIN_SHA=None;SOURCE_DIR=None;HISTORICAL_DATE=None;SCOPE_COUNT=None
def need(v,msg):
    if not v: raise ValueError(msg)
def bind():
    need(isinstance(ROOT,Path) and ROOT.is_absolute() and not ROOT.is_symlink() and isinstance(PIN_FILE,Path) and isinstance(PIN_SHA,str) and len(PIN_SHA)==64 and isinstance(SOURCE_DIR,str) and bool(SOURCE_DIR) and type(HISTORICAL_DATE)is int and type(SCOPE_COUNT)is int and SCOPE_COUNT>0,'NO_APPROVED_PRIVATE_BINDING')
    need(PIN_FILE.resolve().is_relative_to(ROOT.resolve()) and not PIN_FILE.is_symlink(),'PIN_PATH')
    raw=PIN_FILE.read_bytes();need(hashlib.sha256(raw).hexdigest()==PIN_SHA,'CHAIN_PIN_MANIFEST')
    pins=json.loads(raw)
    need(isinstance(pins,list) and len(pins)>=5,'INCOMPLETE_CHAIN_PINS')
    for p in pins:
        f=ROOT/p['path'];need(f.resolve()==f and f.resolve().is_relative_to(ROOT.resolve()) and not f.is_symlink(),'CODE_PATH')
        b=f.read_bytes();need(len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'],'CHAIN_INPUT_CHANGED:'+p['path'])
    source=ROOT/SOURCE_DIR
    need(source.resolve().is_relative_to(ROOT.resolve()) and source.resolve()==source,'SOURCE_DIRECTORY')
    declared={x['path'] for x in pins}
    need(all(str((source/n).relative_to(ROOT)) in declared for n in ['isolated_capture.py','isolated_source_prepare_v3.py']),'MISSING_CORE_PINS')
    sys.path.insert(0,str(source))
    try:
        cap=importlib.import_module('isolated_capture')
        v3=importlib.import_module('isolated_source_prepare_v3')
    finally:sys.path.pop(0)
    need(Path(cap.__file__).resolve()==source/'isolated_capture.py' and Path(v3.__file__).resolve()==source/'isolated_source_prepare_v3.py','MODULE_IDENTITY')
    reader=cap.portable.ReferenceReader(ROOT)
    import dated_source_decision as dated
    need(Path(dated.__file__).resolve()==HERE/'dated_source_decision.py','DATED_MODULE_IDENTITY')
    functions=v3.original_functions(reader)
    decide=dated.decision_context(reader,pins[3],cap,functions)
    return reader,pins,decide

def inspect(target):
    need(type(target)is int,'TARGET_DATE_TYPE')
    datetime.datetime.strptime(str(target),'%Y%m%d')
    reader,pins,decide=bind()
    calendar=json.loads(reader.checked(pins[3]));receipt=json.loads(reader.checked(pins[4]))
    need(receipt['target_date']==HISTORICAL_DATE and receipt['scope_count']==SCOPE_COUNT and receipt['status']=='SOURCE_CANDIDATE_PREPARED_PENDING_INDEPENDENT_REVIEW','HISTORICAL_RECEIPT_IDENTITY')
    contract=json.loads(reader.checked(receipt['contract_ref']))
    need(len(contract['inputs'])==receipt['ready_inputs'] and len(contract['source_blocked'])==receipt['blocked_count'],'HISTORICAL_PARTITION_COUNTS')
    now=datetime.datetime.now(datetime.timezone.utc)
    status='REUSE_HISTORICAL_SOURCE_PREPARATION_NO_RERUN' if target==receipt['target_date'] else 'BLOCKED_DATED_SOURCE_NOT_BOUND'
    blockers=[] if target==receipt['target_date'] else ['new-date source capture/conversion receipt and full decoded event provenance','independent same-source review','original-owner lock-domain execution binding']
    if target!=receipt['target_date'] and target!=calendar['target_date']:
        blockers.insert(0,'independently reviewed calendar for requested target')
    if target>int(now.strftime('%Y%m%d')):blockers.insert(0,'target session has not occurred: no future source acquisition')
    return {'schema':'DAILY1540_REUSED_V3_DATED_CHAIN_V1','checked_utc':now.isoformat(),'target_date':target,'status':status,'historical_source_preparation':{'date':receipt['target_date'],'ready_inputs':receipt['ready_inputs'],'blocked_count':receipt['blocked_count'],'receipt_ref':pins[4],'contract_ref':receipt['contract_ref'],'recomputed_stocks':0},'dated_decision_context_loaded':True,'calendar_ref':pins[3],'calendar_target_date':calendar['target_date'],'blockers':blockers,'source_registry_scope':'Only pinned formal historical receipt; new-date source absence globally remains UNKNOWN; nothing fetched or searched recursively.','scheduler_callable_for_status_only':True,'scheduler_business_execution_ready':False,'network_calls':0,'owner_calls':0,'formula_calls':0,'locks_acquired':False,'production_changed':False,'natural_business_verified':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--target-date',required=True,type=int);a=p.parse_args()
    print(json.dumps(inspect(a.target_date),ensure_ascii=False,indent=2))

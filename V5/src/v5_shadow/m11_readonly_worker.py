"""Exact M11 capsule projection. Persistence proof is never natural/PIT proof."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

BASE=Path(__file__).resolve().parents[2]
if __package__ in (None,''):sys.path.insert(0,str(BASE/'src'))
SLOTS=('09:25','09:35','10:00','11:30','14:00','15:00')
FLAGS=dict(research_only=True,natural_verified=False,review_completed=False,production_allowed=False,buy_gate_updated=False,orders_sent=False)
MAX_BYTES=2*1024*1024

def waiting(reason,**extra):
    return dict(schema_version='v5.m11_saved_research.v1',module_id='M11_INTRADAY_RESEARCH',status='WAITING',
        reason_codes=[reason],slots=[dict(slot=s,status='WAITING') for s in SLOTS],**FLAGS,**extra)

def raw(path,limit=MAX_BYTES):
    """Descriptor-walk every component, rejecting symlinks and special files."""
    p=Path(path)
    if not p.is_absolute() or '..' in p.parts:raise ValueError('M11_PATH')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for part in p.parts[1:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=child
        child=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
        with os.fdopen(child,'rb') as stream:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size>limit:raise ValueError('M11_READ_LIMIT')
            result=stream.read(limit+1)
            if len(result)>limit:raise ValueError('M11_READ_LIMIT')
            return result
    finally:os.close(fd)

VIEW_FIELDS={'schema','schema_version','status','artifact_status','trade_date','target_date','date','source_role',
    'source_artifact_sha256','artifact_sha256','source_schema_version','data_as_of','generated_at','generation_status',
    'generation','source_provenance','cannot_confirm','write_policy','focus','market_facts','emotion_metrics',
    'market_breadth','feedback_matrix','loss_effect','theme_tree','event_ledger','money_effect','promotion','ladder_gap',
    'slots','evidence','missing_slots','auction','research_only','production_allowed','buy_gate_updated','orders_sent'}

class PinnedCapsuleBytes:
    """Feed the unchanged original verifier exactly the already bounded bytes."""
    def __init__(self,name,content):self.name=name;self.content=content
    def read_bytes(self,name):
        if name!=self.name:raise ValueError('M11_CAPSULE_PATH_CHANGED')
        return self.content

def public_tree(value,depth=0):
    if depth>24:raise ValueError('M11_PROJECTION_DEPTH')
    if isinstance(value,dict):
        result={}
        for key,item in value.items():
            if not isinstance(key,str):raise ValueError('M11_PROJECTION_KEY')
            if key in {'production_allowed','buy_gate_updated','orders_sent','natural_verified','independently_verified','authority_receipt_independently_verified'} and item is not False:
                raise ValueError('M11_UNVERIFIED_AUTHORITY_CLAIM')
            normal=re.sub('[^a-z0-9]','',key.lower())
            if any(token in normal for token in ('path','root','provider','credential','token','secret','password','apikey','accesskey','authorization','cookie','sessionid','sessionkey','privatekey','clientkey')) or key in {'__proto__','constructor','prototype'}:continue
            result[key]=public_tree(item,depth+1)
        return result
    if isinstance(value,list):return [public_tree(item,depth+1) for item in value]
    if isinstance(value,str) and (re.search(r'/(?:Users|home|workspace|private|tmp)/',value) or re.search(r'[A-Za-z]:\\',value)):
        return '[LOCAL_PATH_REDACTED]'
    return value

def project(binding):
    from v5_shadow.m11_readonly import validate_reference
    from v5_shadow.m11.intraday_capsule import M11Slot,IntradayCapsuleStore
    validate_reference(binding)
    root=Path(binding['archive_root'])
    if json.loads(raw(root/'.m11-private-root.json'))!={'module':'M11','private':True,'schema':'v5.private_root.v1'}:
        raise ValueError('M11_PRIVATE_ROOT_MARKER')
    identity=M11Slot(**binding['identity']);operation=binding['operation']
    store=IntradayCapsuleStore(root/('intraday' if operation=='capture' else 'daily'))
    path=store._artifact_dir(identity)/'commit.json'
    try:content=raw(path)
    except FileNotFoundError:return waiting('M11_COMMITTED_CAPSULE_MISSING',requested_trade_date=identity.target_date.replace('-',''))
    if hashlib.sha256(content).hexdigest()!=binding['commit_sha256']:raise ValueError('M11_COMMIT_PIN')
    store.io=PinnedCapsuleBytes(str(path.relative_to(store.root)),content)
    payload=store.read_verified(identity)
    if payload!=json.loads(content).get('payload'):raise ValueError('M11_PINNED_PAYLOAD_CHANGED')
    # Check the exact envelope again after the unchanged original reader.
    if hashlib.sha256(raw(path)).hexdigest()!=binding['commit_sha256']:raise ValueError('M11_COMMIT_CHANGED')
    if payload.get('pit_status')!='CANNOT_CONFIRM' or payload.get('natural_admission')!='CANNOT_CONFIRM' or payload.get('source_times_validated') is not True:
        raise ValueError('M11_CAPSULE_EVIDENCE_BOUNDARY')
    if not isinstance(payload.get('status'),str):raise ValueError('M11_BUSINESS_STATUS')
    owner=payload.get('owner');key='intraday_research' if operation=='capture' else 'research_review'
    if not isinstance(owner,dict) or not isinstance(owner.get(key),dict):raise ValueError('M11_OWNER_PROJECTION_MISSING')
    view=owner[key]
    for field,expected in [('target_date',identity.target_date),('date',identity.target_date),('trade_date',identity.target_date.replace('-',''))]:
        if field in view and view[field]!=expected:raise ValueError('M11_OWNER_DATE_MISMATCH')
    # Do not return config, source inputs, provider material, or full owner artifacts.
    research={key:public_tree({k:v for k,v in view.items() if k in VIEW_FIELDS})}
    reasons=['GLOBAL_PIT_NOT_PROVEN','NATURAL_RESEARCH_NOT_VERIFIED']
    if operation=='generate':reasons.append('DECLARED_PROVENANCE_NOT_INDEPENDENTLY_VERIFIED')
    return dict(schema_version='v5.m11_saved_research.v1',module_id='M11_INTRADAY_RESEARCH',status='SAVED_RESEARCH_REVIEW_REQUIRED',
        reference=dict(trade_date=identity.target_date.replace('-',''),run_id=identity.run_id,commit_sha256=binding['commit_sha256'],operation=operation,slot=identity.slot),
        data_kind=binding['data_kind'],evidence_status='VERIFIED_PERSISTENCE_ONLY',business_status=payload['status'],research=research,
        slots=[dict(slot=s,status='SAVED' if operation=='capture' and s==identity.slot else 'WAITING') for s in SLOTS],reason_codes=reasons,**FLAGS)

def readonly_audit(event,args):
    if event=='open':
        mode,flags=args[1:3]
        if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
            raise ValueError('M11_READ_ONLY')
    if event in {'os.remove','os.rename','os.mkdir','os.rmdir','subprocess.Popen','socket.connect','socket.bind'}:raise ValueError('M11_READ_ONLY')

if __name__=='__main__':
    request=json.load(sys.stdin);sys.addaudithook(readonly_audit)
    result=project(request)
    if any(n in sys.modules for n in ['v5_shadow.m11.owner_worker','domains.research_review_generation.assembly','domains.research_review_generation.generation']):raise ValueError('M11_PRODUCER_IMPORTED')
    print(json.dumps(result,ensure_ascii=False,allow_nan=False))

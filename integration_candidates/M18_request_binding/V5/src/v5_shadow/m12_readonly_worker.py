"""Cold M12 saved-result projection. Original reader, no producer or writes."""
from pathlib import Path
import hashlib
import json
import os
import re
import stat
import sys

BASE=Path(__file__).resolve().parents[2]
if __package__ in (None,''):sys.path.insert(0,str(BASE/'src'))
from v5_shadow.composition import no_symlinks

FLAGS=dict(research_only=True,natural_verified=False,review_completed=False,production_allowed=False,buy_gate_updated=False,orders_sent=False)
MAX_META=4*1024*1024
MAX_ARTIFACT=256*1024*1024
MAX_TOTAL=512*1024*1024
MAX_TEXT=256*1024

def waiting(reason,**extra):
    return dict(schema_version='v5.m12_saved_video.v1',module_id='M12_VIDEO_FUPAN',status='WAITING',reason_codes=[reason],**FLAGS,**extra)

def raw(path,limit=MAX_META):
    path=no_symlinks(Path(path));fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size>limit:raise ValueError('M12_READ_LIMIT')
        with os.fdopen(os.dup(fd),'rb') as stream:value=stream.read(limit+1)
        if len(value)>limit:raise ValueError('M12_READ_LIMIT')
        return value
    finally:os.close(fd)

def private_root(value):
    root=no_symlinks(Path(value))
    if raw(root/'.v5-m12-root')!=b'v5.m12-private.v1\n':raise ValueError('M12_PRIVATE_ROOT_MARKER')
    return root

def project(binding):
    # Import original code only inside the already pin-checked child.
    from v5_shadow.video_fupan_reader import read_committed_video,VideoReadError
    root=private_root(binding['private_root']);date=binding['trade_date'];run=binding['run_id']
    if not re.fullmatch(r'\d{8}',date) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,255}',run):raise ValueError('M12_REFERENCE')
    manifest_path=root/'video_fupan/runs'/date/run/'manifest.json'
    if not manifest_path.exists():return waiting('M12_SAVED_RUN_MISSING',requested_trade_date=date)
    content=raw(manifest_path)
    if hashlib.sha256(content).hexdigest()!=binding['manifest_sha256']:raise ValueError('M12_MANIFEST_PIN')
    receipt_path=root/'review'/date/'runs'/run/'receipt.json'
    pinned_receipt=raw(receipt_path)
    if hashlib.sha256(pinned_receipt).hexdigest()!=binding['owner_receipt_sha256']:raise ValueError('M12_RECEIPT_PIN')
    manifest=json.loads(content);owner=manifest['owner_manifest'];refs=owner['artifact_refs']
    if not isinstance(refs,list) or not 1<=len(refs)<=256:raise ValueError('M12_ARTIFACT_COUNT')
    # Bound the unchanged reader's whole-file hashing before calling it.
    total=0
    for ref in refs:
        rel=Path(ref['path'])
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('M12_ARTIFACT_PATH')
        path=no_symlinks(root/rel);info=path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_ARTIFACT:raise ValueError('M12_ARTIFACT_LIMIT')
        total+=info.st_size
    if total>MAX_TOTAL:raise ValueError('M12_TOTAL_LIMIT')
    for path in (root/'video_fupan/runs'/date/run/'receipt.json',root/'review'/date/'runs'/run/'manifest.json'):raw(path)
    try:checked=read_committed_video(root,date,run)
    except VideoReadError as error:raise ValueError('M12_ORIGINAL_READER_REJECTED') from error
    receipt=checked['owner_receipt']
    if receipt!=json.loads(pinned_receipt):raise ValueError('M12_RECEIPT_CHANGED')
    for key in ('production_allowed','buy_gate_updated','orders_sent'):
        if owner.get(key) is not False or receipt.get('safety_flags',{}).get(key) is not False:raise ValueError('M12_RESEARCH_BOUNDARY')
    if hashlib.sha256(raw(receipt_path)).hexdigest()!=binding['owner_receipt_sha256']:raise ValueError('M12_RECEIPT_CHANGED')
    reference=dict(trade_date=date,run_id=run,manifest_sha256=binding['manifest_sha256'],owner_receipt_sha256=binding['owner_receipt_sha256'])
    video={k:owner.get(k) for k in ('bv_id','title','upload_date','target_trade_date','date_scope','discovery_status','capture_status','asr_status','asr_segment_count','gap_status','gap_row_count','stockdict_status','video_evidence_boundary')}
    if not(receipt.get('status')=='ACQUIRED' and owner.get('discovery_status')=='TARGET_BV_LOCKED' and owner.get('capture_status') in {'CAPTURED','REUSED_CONTENT'} and owner.get('asr_status')=='ASR_REVIEW_REQUIRED'):
        return waiting('M12_SAVED_RUN_NOT_QUALIFIED',reference=reference,video=video,data_kind=binding['data_kind'])
    def text_artifact(kind):
        matches=[r for r in refs if r.get('kind')==kind]
        if len(matches)!=1:raise ValueError('M12_TEXT_ARTIFACT_REQUIRED')
        ref=matches[0];value=raw(root/ref['path'],MAX_ARTIFACT)
        if hashlib.sha256(value).hexdigest()!=ref['sha256']:raise ValueError('M12_TEXT_CHANGED')
        text=value.decode('utf-8');visible=text[:MAX_TEXT]
        return dict(text=visible,sha256=ref['sha256'],total_characters=len(text),truncated=len(visible)!=len(text))
    transcript=text_artifact('transcript');segments=text_artifact('segment')
    if hashlib.sha256(raw(manifest_path)).hexdigest()!=binding['manifest_sha256']:raise ValueError('M12_CHANGED_DURING_READ')
    if hashlib.sha256(raw(receipt_path)).hexdigest()!=binding['owner_receipt_sha256']:raise ValueError('M12_RECEIPT_CHANGED')
    return dict(schema_version='v5.m12_saved_video.v1',module_id='M12_VIDEO_FUPAN',status='SAVED_ASR_REVIEW_REQUIRED',
        reference=reference,video=video,transcript=transcript,segments=segments,artifact_count=len(refs),
        data_kind=binding['data_kind'],reason_codes=['ASR_REVIEW_REQUIRED','VIDEO_ENHANCEMENT_ONLY'],**FLAGS)

def readonly_audit(event,args):
    if event=='open':
        mode=args[1];flags=args[2]
        if (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
            raise ValueError('M12_READ_ONLY')
    if event in {'os.remove','os.rename','os.mkdir','os.rmdir','subprocess.Popen','socket.connect','socket.bind'}:raise ValueError('M12_READ_ONLY')

if __name__=='__main__':
    request=json.load(sys.stdin);sys.addaudithook(readonly_audit)
    result=project(request)
    if any(n.endswith('review_core.producer') for n in sys.modules):raise ValueError('M12_PRODUCER_IMPORTED')
    print(json.dumps(result,ensure_ascii=False))

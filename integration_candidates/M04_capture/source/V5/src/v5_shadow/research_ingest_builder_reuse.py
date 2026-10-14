"""Isolated read-only verification of a completed original builder checkpoint."""
import sys
from pathlib import Path
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hashlib,json,re
from v5_shadow.archive_builder_v1 import builder_identity,verify_builder,BUILDER_PATTERN
from v5_shadow.archive_article_v2 import CAPTURE_PATTERN
from v5_shadow.current_us_research import _raw_file
from v5_shadow.digests import canonical_bytes,sha256_json,MAX_JSON_BYTES


def verify(request,built):
    fields={'schema_version','capture_root','capture_files','receipt','builder_source','builder_receipt','archive_v1','readback','request_sha256','builder_identity','natural_verified','historical_pit_claimed','production_allowed','buy_gate_updated','orders_sent'}
    if (not isinstance(built,dict) or set(built)!=fields
            or built['schema_version']!='v5.archive_builder_import_source.v1'
            or built['request_sha256']!=sha256_json(request)
            or built['builder_identity']!=builder_identity()
            or built['readback']!='MATCHED'
            or built['capture_root']!=request['capture_root'] or built['receipt']!=request['receipt']
            or any(built[k] is not False for k in ('natural_verified','historical_pit_claimed','production_allowed','buy_gate_updated','orders_sent'))):
        raise ValueError('INGEST_BUILDER_REUSE_IDENTITY')
    root=Path(request['capture_root'])
    if not root.is_absolute() or '..' in root.parts or any(p.is_symlink() for p in (root,*root.parents)):
        raise ValueError('INGEST_BUILDER_REUSE_ROOT')
    files=built['capture_files']
    if not isinstance(files,dict) or not files or len(files)>500 or any(files.get(k)!=v for k,v in request['capture_files'].items()):
        raise ValueError('INGEST_BUILDER_REUSE_CAPTURE_BINDING')
    snapshot={}
    for name,digest in files.items():
        if not re.fullmatch(CAPTURE_PATTERN+'|'+BUILDER_PATTERN,name):raise ValueError('INGEST_BUILDER_REUSE_FILE_SET')
        raw=_raw_file(root,name)
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('INGEST_BUILDER_REUSE_SOURCE_SHA')
        snapshot[name]=raw
        if sum(map(len,snapshot.values()))>MAX_JSON_BYTES:raise ValueError('INGEST_BUILDER_REUSE_SIZE')
    owner=verify_builder(built['archive_v1'],built['builder_source'],built['builder_receipt'],request['receipt'],snapshot.__getitem__)
    if (owner['capture_root']!=str(root) or owner['status']!=request['status']
            or set(files)!=set(owner['files'])|{built['builder_receipt']['path']}):
        raise ValueError('INGEST_BUILDER_REUSE_OWNER_BINDING')
    # Recheck actual files after replay. No owner writer is invoked.
    for name,raw in snapshot.items():
        if _raw_file(root,name)!=raw:raise ValueError('INGEST_BUILDER_REUSE_SOURCE_CHANGED')
    return {'status':'MATCHED','checkpoint_sha256':sha256_json(built)}

if __name__=='__main__':
    try:
        raw=sys.stdin.buffer.read(MAX_JSON_BYTES+1)
        if len(raw)>MAX_JSON_BYTES:raise ValueError('INGEST_BUILDER_REUSE_SIZE')
        value=json.loads(raw)
        if set(value)!={'request','built'}:raise ValueError('INGEST_BUILDER_REUSE_FIELDS')
        print(canonical_bytes(verify(value['request'],value['built'])).decode())
    except Exception as exc:
        print(json.dumps({'status':'FAILED','reason':type(exc).__name__+':'+str(exc)}));raise SystemExit(1)

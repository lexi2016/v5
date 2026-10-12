"""Import exact saved HK owner trios; observe them without re-running selection.

The original bytes remain private and unchanged. This module never collects,
selects, follows latest, or treats a historical output as verified raw input.
"""
import sys
from pathlib import Path
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from datetime import datetime, timezone

from v5_shadow.composition import no_symlinks
from v5_shadow.contracts import aware, exact_keys, sha, trade_date
from v5_shadow.digests import canonical_bytes, sha256_json, MAX_JSON_BYTES
from v5_shadow.hk_stage_sources import SOURCE_SHA, load_owners, source_bytes
from v5_shadow.module_api import _open_directory, _read_regular

STAGES = ('STAGE_0925', 'STAGE_0930_0935', 'STAGE_0935_0940', 'STAGE_0940_0945',
          'STAGE_0945_1030', 'STAGE_1300_1315', 'STAGE_1445_1500', 'STAGE_1545_1555')
FILES = ('artifact.csv', 'manifest.json', 'receipt.json')
SAFETY = dict(production_allowed=False, buy_gate_updated=False, orders_sent=False)
OBSERVED = dict(data_kind='OWNER_RESULT', evidence_mode='HISTORICAL', qualification='OBSERVED_ONLY',
                natural_verified=False, pit_verified=False, formal_admission=False,
                raw_input_verified=False, computation_replayed=False,
                market_data_authenticity_verified=False)
MARKER = b'v5.hk-stage-observed-root.v1\n'
SOURCE_SCHEMA = 'v5.hk_stage_observed_source.v1'
REF_SCHEMA = 'v5.hk_stage_observed_reference.v1'
_SOURCE_FIELDS = ('schema_version', 'target_date', 'stage_id', 'market', 'run_id',
                  'artifact_sha256', 'manifest_sha256', 'receipt_sha256', 'trio')
_REF_FIELDS = ('schema_version', 'import_sha256', 'import_receipt_sha256',
               'target_date', 'stage_id', 'market', 'run_id')


def _identity_fields(value):
    trade_date(value['target_date'])
    if (value['market'] != 'HK_CONNECT' or value['stage_id'] not in STAGES
            or not isinstance(value['run_id'], str)
            or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,254}[A-Za-z0-9])?', value['run_id'])):
        raise ValueError('M08_OBSERVED_IDENTITY')


def _prefix(value):
    return f"selection_runs/{value['target_date']}/HK_CONNECT_SELECTION_{value['stage_id']}/{value['run_id']}"


def _source_reference(value):
    exact_keys(value, _SOURCE_FIELDS)
    if value['schema_version'] != SOURCE_SCHEMA:
        raise ValueError('M08_OBSERVED_SOURCE_SCHEMA')
    _identity_fields(value)
    for key in ('artifact_sha256', 'manifest_sha256', 'receipt_sha256'):
        sha(value[key])
    exact_keys(value['trio'], FILES)
    for name, item in value['trio'].items():
        exact_keys(item, ('relative_path', 'sha256', 'bytes'))
        sha(item['sha256'])
        if (item['relative_path'] != _prefix(value) + '/' + name
                or type(item['bytes']) is not int or not 0 < item['bytes'] <= MAX_JSON_BYTES):
            raise ValueError('M08_OBSERVED_TRIO_IDENTITY')
    if value['artifact_sha256'] != value['trio']['artifact.csv']['sha256']:
        raise ValueError('M08_OBSERVED_ARTIFACT_SHA')
    return json.loads(canonical_bytes(value))


def _reference(value):
    exact_keys(value, _REF_FIELDS)
    if value['schema_version'] != REF_SCHEMA:
        raise ValueError('M08_OBSERVED_REFERENCE_SCHEMA')
    _identity_fields(value)
    sha(value['import_sha256']); sha(value['import_receipt_sha256'])
    return json.loads(canonical_bytes(value))


def _read_file(root, relative):
    # Every directory is opened separately: O_NOFOLLOW must protect intermediate
    # components too, not only the final filename of a slash-containing path.
    parts=relative.split('/')
    if any(p in ('', '.', '..') or '\\' in p for p in parts):
        raise ValueError('M08_OBSERVED_PATH')
    directory=_open_directory(root)
    try:
        for part in parts[:-1]:
            child=os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory); directory=child
        fd=os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:return _read_regular(fd, MAX_JSON_BYTES)
        finally:os.close(fd)
    finally:os.close(directory)


def _json(raw):
    def pairs(items):
        result={}
        for key, value in items:
            if key in result:raise ValueError('M08_OBSERVED_DUPLICATE_JSON_KEY')
            result[key]=value
        return result
    def constant(_):raise ValueError('M08_OBSERVED_NONFINITE_JSON')
    if len(raw)>MAX_JSON_BYTES:raise ValueError('M08_OBSERVED_JSON_SIZE')
    result=json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    canonical_bytes(result)
    return result


def _read_cli_json(path):
    path=Path(path).absolute()
    return _json(_read_file(path.parent,path.name))


def _read_trio(root, expected):
    raw={}
    for name, item in expected['trio'].items():
        data=_read_file(root, item['relative_path'])
        if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
            raise ValueError('M08_OBSERVED_TRIO_BYTES:'+name)
        raw[name]=data
    for name, field in (('manifest.json', 'manifest_sha256'), ('receipt.json', 'receipt_sha256')):
        if sha256_json(_json(raw[name]))!=expected[field]:
            raise ValueError('M08_OBSERVED_CANONICAL_SHA:'+name)
    return raw


def _false_flags(value, *, required=False):
    if isinstance(value, dict):
        for key in SAFETY:
            if (required or key in value) and value.get(key) is not False:
                raise ValueError('M08_OBSERVED_SAFETY')
        for item in value.values():_false_flags(item)
    elif isinstance(value, list):
        for item in value:_false_flags(item)


def _owner_worker(root, expected):
    expected=_source_reference(expected);before=_read_trio(root, expected)
    selection, _, _=load_owners()
    verified=selection.SelectionStore(root)._verify_run(expected['target_date'], expected['stage_id'],
                                                       expected['market'], expected['run_id'])
    for key in ('artifact_sha256', 'manifest_sha256', 'receipt_sha256'):
        if verified[key]!=expected[key]:raise ValueError('M08_OBSERVED_OWNER_SHA')
    artifact=verified['envelope'];manifest=_json(before['manifest.json']);receipt=_json(before['receipt.json'])
    role='HK_CONNECT_SELECTION_'+expected['stage_id']
    if artifact.get('source_status') not in ('READY','READY_EMPTY','PARTIAL_WITH_ROWS','CANNOT_CONFIRM'):
        raise ValueError('M08_OBSERVED_SOURCE_STATUS')
    for value in (artifact, manifest, receipt):
        if any(value.get(key)!=expected[key] for key in ('market','stage_id','run_id')) or value.get('trade_date')!=expected['target_date']:
            raise ValueError('M08_OBSERVED_OWNER_IDENTITY')
        _false_flags(value, required=True)
        if (value.get('algorithm_id')!=selection.SELECTION_ALGORITHM_ID
                or value.get('selection_status')!=artifact.get('selection_status')):
            raise ValueError('M08_OBSERVED_OWNER_METADATA')
    for value in (manifest, receipt):
        if value.get('role')!=role:raise ValueError('M08_OBSERVED_OWNER_ROLE')
        if 'source_status' in value and value['source_status']!=artifact['source_status']:
            raise ValueError('M08_OBSERVED_SOURCE_STATUS')
    if (not isinstance(artifact.get('rows'), list) or len(artifact['rows'])>10
            or artifact.get('selected_rows', len(artifact['rows']))!=len(artifact['rows'])):
        raise ValueError('M08_OBSERVED_OWNER_ROWS')
    if before!=_read_trio(root, expected):raise ValueError('M08_OBSERVED_TRIO_CHANGED')
    source_bytes()
    return artifact


def _verify_owner(root, expected):
    proc=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).resolve()),'--worker'],
                        input=canonical_bytes(dict(root=str(root),reference=expected)),
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    value=_json(proc.stdout)
    if proc.returncode:raise ValueError(value.get('reason','M08_OBSERVED_OWNER_FAILED'))
    return value


def _implementation_identity():
    # Separate from hk_stage_sources.implementation_identity: adding this
    # adapter must not invalidate the existing producer/M06 generations.
    names=('hk_stage_observed.py','hk_stage_observed_api.py','hk_stage_api.py',
           'hk_stage_sources.py','contracts.py','digests.py','composition.py',
           'module_api.py','module_artifacts.py','api_gateway.py')
    return {name:hashlib.sha256(no_symlinks(Path(__file__).with_name(name)).read_bytes()).hexdigest()
            for name in names}


def _manifest(expected):
    return dict(schema_version='v5.hk_stage_observed_import.v1', original_reference=expected,
                source_closure_sha256=SOURCE_SHA, reader_implementation_identity=_implementation_identity(),
                **OBSERVED, **SAFETY)


def init_hk_observed_root(root):
    root=no_symlinks(Path(root))
    if root.exists() and any(root.iterdir()):raise ValueError('M08_OBSERVED_INIT_REQUIRES_EMPTY')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    _write_bytes(root/'.v5-hk-stage-observed-root', MARKER)
    return str(root)


def _root(root):
    root=Path(root)
    try:marker=_read_file(root,'.v5-hk-stage-observed-root')
    except FileNotFoundError as error:
        raise ValueError('M08_OBSERVED_ROOT_MARKER') from error
    if marker!=MARKER:
        raise ValueError('M08_OBSERVED_ROOT_MARKER')
    return root


def _write_bytes(path, raw):
    path=no_symlinks(Path(path));path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd=os.open(path,os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


def _sync_tree(path):
    # Directory entries must be durable before exposing the committed name.
    for directory in sorted((p for p in path.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
        fd=_open_directory(directory)
        try:os.fsync(fd)
        finally:os.close(fd)
    fd=_open_directory(path)
    try:os.fsync(fd)
    finally:os.close(fd)


def prepare_hk_stage_observed_reference(source_root, inventory_entry, *, target_date):
    """Read-only augmentation of one pinned report.stage_runs entry.

    Report raw hashes/sizes are mandatory. Canonical hashes are calculated from
    those exact bytes and verified by the unchanged original reader. Inventory
    labels such as READY or reader=PASS are never accepted as proof.
    """
    if not isinstance(inventory_entry,dict):raise ValueError('M08_OBSERVED_INVENTORY')
    expected=dict(schema_version=SOURCE_SCHEMA,target_date=target_date,market='HK_CONNECT',
                  stage_id=inventory_entry['stage'],run_id=inventory_entry['run_id'],
                  trio=inventory_entry['trio'],artifact_sha256=inventory_entry['trio']['artifact.csv']['sha256'],
                  manifest_sha256='0'*64,receipt_sha256='0'*64)
    expected=_source_reference(expected)
    for name, field in (('manifest.json','manifest_sha256'),('receipt.json','receipt_sha256')):
        item=expected['trio'][name];raw=_read_file(source_root,item['relative_path'])
        if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:
            raise ValueError('M08_OBSERVED_TRIO_BYTES:'+name)
        expected[field]=sha256_json(_json(raw))
    _verify_owner(source_root,expected)
    return expected


def _make_reference(import_sha, receipt_sha, source):
    return dict(schema_version=REF_SCHEMA,import_sha256=import_sha,import_receipt_sha256=receipt_sha,
                **{k:source[k] for k in ('target_date','stage_id','market','run_id')})


def read_hk_stage_observed(recorded_root, reference):
    """Cold read only: recorded root plus exact reference, never source/latest."""
    root=_root(recorded_root);reference=_reference(reference)
    relative='imports/'+reference['import_sha256'];raw=_read_file(root,relative+'/import.json')
    if hashlib.sha256(raw).hexdigest()!=reference['import_sha256']:
        raise ValueError('M08_OBSERVED_IMPORT_SHA')
    manifest=_json(raw);expected=_source_reference(manifest['original_reference'])
    if canonical_bytes(manifest)!=canonical_bytes(_manifest(expected)):
        raise ValueError('M08_OBSERVED_IMPORT_IDENTITY')
    receipt_raw=_read_file(root,relative+'/receipt.json')
    if hashlib.sha256(receipt_raw).hexdigest()!=reference['import_receipt_sha256']:
        raise ValueError('M08_OBSERVED_RECEIPT_SHA')
    receipt=_json(receipt_raw);imported_at=receipt.get('imported_at');aware(imported_at)
    wanted=dict(schema_version='v5.hk_stage_observed_receipt.v1',status='COMMITTED',
                import_sha256=reference['import_sha256'],imported_at=imported_at,**OBSERVED,**SAFETY)
    if (canonical_bytes(receipt)!=canonical_bytes(wanted)
            or reference!=_make_reference(reference['import_sha256'],reference['import_receipt_sha256'],expected)):
        raise ValueError('M08_OBSERVED_COMMIT_IDENTITY')
    artifact=_verify_owner(root/relative/'owner',expected)
    return dict(artifact=artifact,reference=reference,read_status='VERIFIED',
                provenance=dict(**OBSERVED, imported_at=imported_at,captured_at=None,
                                original_reference=expected,source_closure_sha256=SOURCE_SHA,
                                reader_implementation_identity=manifest['reader_implementation_identity']),
                natural_verified=False,**SAFETY)


def import_hk_stage_observed(source_root, recorded_root, expected_original_reference):
    """Copy a fully pinned original trio once, verify, and atomically commit.

    Failures retain an unpublished pending directory for explicit inspection.
    Existing committed files and source files are never overwritten or removed.
    """
    source=no_symlinks(Path(source_root));root=_root(recorded_root)
    if source==root or source in root.parents or root in source.parents:
        raise ValueError('M08_OBSERVED_ROOTS_MUST_BE_SEPARATE')
    expected=_source_reference(expected_original_reference)
    identity=_manifest(expected);import_sha=sha256_json(identity)
    imports=no_symlinks(root/'imports');imports.mkdir(mode=0o700,exist_ok=True)
    lock=os.open(root/'.import.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        if not stat.S_ISREG(os.fstat(lock).st_mode):raise ValueError('M08_OBSERVED_IMPORT_LOCK')
        fcntl.flock(lock,fcntl.LOCK_EX)
        committed=no_symlinks(imports/import_sha)
        if committed.exists():
            receipt_raw=_read_file(committed,'receipt.json')
            reference=_make_reference(import_sha,hashlib.sha256(receipt_raw).hexdigest(),expected)
            return dict(read_hk_stage_observed(root,reference),reused=True)
        _verify_owner(source,expected)
        raw=_read_trio(source,expected)
        pending=Path(tempfile.mkdtemp(prefix='pending-',dir=imports))
        owner=pending/'owner'
        for name,item in expected['trio'].items():_write_bytes(owner/item['relative_path'],raw[name])
        _verify_owner(owner,expected)
        if identity!=_manifest(expected):raise ValueError('M08_OBSERVED_CODE_CHANGED')
        _write_bytes(pending/'import.json',canonical_bytes(identity))
        receipt=dict(schema_version='v5.hk_stage_observed_receipt.v1',status='COMMITTED',
                     import_sha256=import_sha,imported_at=datetime.now(timezone.utc).isoformat(),
                     **OBSERVED,**SAFETY)
        receipt_raw=canonical_bytes(receipt);_write_bytes(pending/'receipt.json',receipt_raw)
        _sync_tree(pending)
        os.rename(pending,committed)
        fd=_open_directory(imports)
        try:os.fsync(fd)
        finally:os.close(fd)
        reference=_make_reference(import_sha,hashlib.sha256(receipt_raw).hexdigest(),expected)
        return dict(read_hk_stage_observed(root,reference),reused=False)
    finally:os.close(lock)


def main(argv=None):
    parser=argparse.ArgumentParser(description='Observe exact saved HK results; never recompute')
    parser.add_argument('action',nargs='?',choices=('init','prepare','import','read'))
    parser.add_argument('--worker',action='store_true')
    parser.add_argument('--root');parser.add_argument('--source-root');parser.add_argument('--inventory')
    parser.add_argument('--run-id');parser.add_argument('--reference');parser.add_argument('--include-artifact',action='store_true')
    args=parser.parse_args(argv)
    if args.worker:
        message=_json(sys.stdin.buffer.read(MAX_JSON_BYTES+1))
        return _owner_worker(message['root'],message['reference'])
    if args.action=='init':return dict(root=init_hk_observed_root(Path(args.root).absolute()))
    if args.action=='prepare':
        report=_read_cli_json(args.inventory)
        entries=[v for v in report['stage_runs'] if v['run_id']==args.run_id]
        if len(entries)!=1:raise ValueError('M08_OBSERVED_EXACT_INVENTORY_RUN_REQUIRED')
        return prepare_hk_stage_observed_reference(Path(args.source_root).absolute(),entries[0],target_date=report['date'])
    if args.action not in ('import','read') or not args.root or not args.reference:
        parser.error('choose an action and provide its root/reference arguments')
    reference=_read_cli_json(args.reference)
    value=(import_hk_stage_observed(Path(args.source_root).absolute(),Path(args.root).absolute(),reference)
           if args.action=='import' else read_hk_stage_observed(Path(args.root).absolute(),reference))
    if args.include_artifact:return value
    if args.action=='import':return value['reference']
    return dict(reference=value['reference'],read_status=value['read_status'],
                selection_status=value['artifact']['selection_status'],rows=len(value['artifact']['rows']),
                imported_at=value['provenance']['imported_at'],**OBSERVED,**SAFETY)


if __name__=='__main__':
    try:print(canonical_bytes(main()).decode())
    except Exception as error:
        from v5_shadow.hk_stage_api import _public_string
        print(canonical_bytes(dict(status='FAILED',reason=_public_string(type(error).__name__+':'+str(error)))).decode())
        raise SystemExit(1)

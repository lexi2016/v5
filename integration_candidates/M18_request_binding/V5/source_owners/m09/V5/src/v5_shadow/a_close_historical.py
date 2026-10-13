"""Explicit retrospective research inputs; no collection or natural/PIT claims.

Large original files are hashed in chunks. Only the exact-date eight-column
projection becomes a bounded immutable snapshot. Frozen algorithms are unchanged.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import stat
from datetime import datetime, timezone
from . import a_close_daily_sources as frozen
from .contracts import sha, trade_date as checked_date
from .digests import canonical_bytes, sha256_json, MAX_JSON_BYTES

SCHEMA='v5.m09.historical_input.v1'
PANEL_FORMAT='M09_TYPED_REPLAY_JSON_V1'
MARKER='.v5-m09-historical-root'
MARKER_BYTES=b'v5.m09.historical-only.v1\n'


def _daily():
    from . import a_close_daily
    return a_close_daily


def _hash_source(path, expected_sha256):
    """Frozen O_NOFOLLOW reader hashes in 1 MiB chunks, never whole-reads."""
    sha(expected_sha256)
    _, info=frozen._regular_snapshot(Path(path),retain=False)
    if info['sha256']!=expected_sha256: raise ValueError('M09_HISTORICAL_SOURCE_SHA_MISMATCH')
    return info


def _read_target_rows(path, target, initial):
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    path=Path(path);safe=frozen.safe_root(path.parent)
    with safe.parent(path.name) as (directory,name):
        fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        with os.fdopen(fd,'rb') as handle:
            st=os.fstat(handle.fileno())
            identity=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
            if not stat.S_ISREG(st.st_mode) or identity!=initial['inode']:
                raise ValueError('M09_HISTORICAL_SOURCE_CHANGED')
            parquet=pq.ParquetFile(handle,pre_buffer=False,buffer_size=0)
            schema=parquet.schema_arrow
            if not set(frozen.COLUMNS)<=set(schema.names): raise ValueError('M09_HISTORICAL_COLUMNS')
            for key in frozen.COLUMNS:
                typ=schema.field(key).type
                numeric=key in ('pct_chg','amount','bar_close_pos')
                if not ((pa.types.is_integer(typ) or pa.types.is_floating(typ)) if numeric else
                        (pa.types.is_string(typ) or pa.types.is_large_string(typ))):
                    raise ValueError('M09_HISTORICAL_COLUMN_TYPE:'+key)
            rows=[]
            # Same exact-date predicate and same columns as the original producer.
            # Batching avoids loading the multi-day container into memory.
            for batch in parquet.iter_batches(batch_size=1024,columns=list(frozen.COLUMNS),use_threads=False):
                selected=batch.filter(pc.equal(batch.column(batch.schema.get_field_index('trade_date')),target))
                rows.extend(selected.to_pylist())
                if len(rows)>20_000: raise ValueError('M09_HISTORICAL_SELECTED_ROW_LIMIT')
            return rows


def _research_gaps(rows, receipt):
    missing={key:sum(r[key] is None or not r[key].strip() for r in rows)
             for key in ('name','tdx_industry_code','tdx_industry_name')}
    positions=sum(r['bar_close_pos'] is None or not math.isfinite(r['bar_close_pos']) for r in rows)
    affected=[]
    if missing['name']: affected.append('APPROXIMATE_ST_LIMIT_COUNTS_UNCERTAIN')
    if missing['tdx_industry_name'] or missing['tdx_industry_code']:
        affected.extend(('INDUSTRY_COVERAGE_INCOMPLETE','INDUSTRY_AND_ROLE_RANKINGS_PARTIAL'))
    if positions: affected.append('CLOSE_POSITION_MISSING_OR_NONFINITE_UNUSED_BY_FROZEN_MODEL')
    return dict(schema_version='v5.m09.historical_research.v1',source_time_verified=False,
                source_available_by_requested_slot=False,membership_qualification_verified=False,
                strict_1500_pit_verified=False,natural_verified=False,original_values_preserved=True,
                snapshot_row_count=len(rows),missing_text=missing,nonfinite_unused_close_position=positions,
                affected_metrics=affected,source_receipt_status='MISSING' if receipt is None else receipt['metadata_status'])


def _validate_rows(rows,target):
    import pandas as pd
    if any(not isinstance(r,dict) or set(r)!=set(frozen.COLUMNS) for r in rows):
        raise ValueError('M09_HISTORICAL_ROW_FIELDS')
    # No coercion/fill/filter here. The exact original model alone owns its
    # legacy transforms; hard core fields must pass before reaching it.
    frozen._validate_frame(pd.DataFrame(rows,columns=list(frozen.COLUMNS)),target,historical_replay=True)


def _write_snapshot(root,target,rows,source,receipt):
    checked_date(target);_daily()._date_slot(target,'16:05');_validate_rows(rows,target)
    if not source.get('hash_verified') is True: raise ValueError('M09_HISTORICAL_UNVERIFIED_SOURCE')
    sha(source['sha256'])
    if type(source.get('bytes')) is not int or source['bytes']<=0: raise ValueError('M09_HISTORICAL_SOURCE_SIZE')
    panel=canonical_bytes(dict(schema_version='v5.m09.typed_rows.v1',trade_date=target,
                               columns=list(frozen.COLUMNS),rows=frozen.encode_rows(rows)))
    if len(panel)>MAX_JSON_BYTES: raise ValueError('M09_HISTORICAL_SNAPSHOT_TOO_LARGE')
    root=_daily()._absolute_root(root)
    if root.exists(): raise ValueError('M09_HISTORICAL_SNAPSHOT_ALREADY_EXISTS')
    with frozen.safe_root(root.parent).directory() as fd:os.mkdir(root.name,0o700,dir_fd=fd)
    handle=frozen.safe_root(root)
    binding=dict(schema_version='v5.m09.historical_source_binding.v1',trade_date=target,
                 source=source,original_receipt=receipt,selection=dict(column_order=list(frozen.COLUMNS),
                 predicate='trade_date == requested_date',row_count=len(rows)),snapshot_sha256=hashlib.sha256(panel).hexdigest(),
                 source_time_verified=False,membership_qualification_verified=False,
                 prepared_at=datetime.now(timezone.utc).isoformat())
    # This reference explicitly does not impersonate an upstream READY receipt.
    reference=dict(schema_version='v5.m09.opaque_source_reference.v1',trade_date=target,
                   original_receipt=receipt,source_status='UNKNOWN',authority_status='UNVERIFIED',
                   captured_at=None,available_at=None,acquired_at=None)
    documents={'panel.json':panel,'panel.txt':b'panel.json\n',
               'members.txt':(''.join(r['ts_code']+'\n' for r in rows)).encode(),
               'source_binding.json':canonical_bytes(binding),'source_reference.json':canonical_bytes(reference)}
    digest=lambda name:hashlib.sha256(documents[name]).hexdigest()
    manifest=dict(schema_version=SCHEMA,trade_date=target,data_kind='RECORDED_INPUT_REPLAY',
        panel=dict(pointer_path='panel.txt',pointer_sha256=digest('panel.txt'),sha256=digest('panel.json'),format=PANEL_FORMAT,row_count=len(rows)),
        membership=dict(path='members.txt',sha256=digest('members.txt'),scope='OBSERVED_ROWS_ONLY',
                        source_id='EXACT_DATE_SNAPSHOT_OBSERVATION',version='v1',captured_at=None,available_at=None),
        provenance=dict(receipt_path='source_reference.json',receipt_sha256=digest('source_reference.json'),
                        source_id='HASH_BOUND_HISTORICAL_PANEL',version='v1',status='UNKNOWN',authority_status='UNVERIFIED',
                        coverage_rate=None,captured_at=None,available_at=None,acquired_at=None),
        evidence={},historical=dict(binding_path='source_binding.json',binding_sha256=digest('source_binding.json')))
    for name,raw in documents.items():handle.write_bytes(name,raw,require_absent=True)
    # Final manifest is the snapshot's commit point; incomplete preparation is
    # never runnable and must not be repaired by overwriting its input objects.
    handle.write_bytes('input.json',canonical_bytes(manifest),require_absent=True)
    return manifest


def prepare_a_close_historical_snapshot(source_root,pointer_path,expected_pointer_sha256,
                                        expected_panel_sha256,trade_date,snapshot_root,*,
                                        receipt_path=None,expected_receipt_sha256=None):
    """Read original bytes, hash/stream-filter, and commit one new private snapshot."""
    d=_daily();target=checked_date(trade_date);d._date_slot(target,'16:05')
    root,handle=d._source_io(source_root);out=d._absolute_root(snapshot_root)
    if root.is_relative_to(out) or out.is_relative_to(root):raise ValueError('M09_HISTORICAL_SOURCE_OUTPUT_OVERLAP')
    d._relative(pointer_path);sha(expected_pointer_sha256)
    pointer=handle.read_bytes(pointer_path,max_bytes=8192)
    if hashlib.sha256(pointer).hexdigest()!=expected_pointer_sha256:raise ValueError('M09_HISTORICAL_POINTER_SHA')
    value=pointer.decode('utf-8-sig').strip();path=Path(value)
    if not path.is_absolute():path=root/d._relative(value)
    path=d._absolute_root(path)
    if not path.is_relative_to(root):raise ValueError('M09_HISTORICAL_POINTER_OUTSIDE_SOURCE')
    before=_hash_source(path,expected_panel_sha256)
    receipt=None;receipt_before=None;receipt_file=None
    if (receipt_path is None)!=(expected_receipt_sha256 is None):raise ValueError('M09_HISTORICAL_RECEIPT_PAIR')
    if receipt_path is not None:
        receipt_file=root/d._relative(receipt_path);receipt_before=_hash_source(receipt_file,expected_receipt_sha256)
        receipt=dict(sha256=receipt_before['sha256'],bytes=receipt_before['bytes'],hash_verified=True,
                     metadata_status='OPAQUE_ORIGINAL_RECEIPT_HASH_ONLY_NO_READY_CLAIM')
    rows=_read_target_rows(path,target,before)
    if _hash_source(path,expected_panel_sha256)!=before or handle.read_bytes(pointer_path,max_bytes=8192)!=pointer:
        raise ValueError('M09_HISTORICAL_SOURCE_CHANGED')
    if receipt_file is not None and _hash_source(receipt_file,expected_receipt_sha256)!=receipt_before:
        raise ValueError('M09_HISTORICAL_RECEIPT_CHANGED')
    source=dict(sha256=before['sha256'],bytes=before['bytes'],format='PARQUET',hash_verified=True,
                pointer_sha256=expected_pointer_sha256,verification='STREAM_HASH_BEFORE_AND_AFTER_EXACT_DATE_FILTER')
    return _write_snapshot(out,target,rows,source,receipt)


def _read_snapshot_rows(raw,target):
    value=_daily()._json(raw)
    if (not isinstance(value,dict) or set(value)!={'schema_version','trade_date','columns','rows'}
            or value['schema_version']!='v5.m09.typed_rows.v1' or value['trade_date']!=target
            or value['columns']!=list(frozen.COLUMNS)):
        raise ValueError('M09_HISTORICAL_SNAPSHOT_SCHEMA')
    rows=frozen.decode_rows(value['rows']);_validate_rows(rows,target)
    return rows


def admit_historical(source_root,manifest_path,manifest_sha,target,slot,execution_kind):
    d=_daily()
    if execution_kind!='RECORDED_INPUT_REPLAY':raise ValueError('M09_HISTORICAL_EXECUTION_ONLY')
    root,source=d._source_io(source_root);files={}
    def read(name,digest,limit=MAX_JSON_BYTES):
        d._relative(name);sha(digest);raw=source.read_bytes(name,max_bytes=limit)
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('M09_HISTORICAL_INPUT_SHA:'+name)
        files[name]={'raw':raw,'sha256':digest,'bytes':len(raw)};return raw
    manifest=d._json(read(manifest_path,manifest_sha))
    if (set(manifest)!={'schema_version','trade_date','data_kind','panel','membership','provenance','evidence','historical'}
            or manifest['schema_version']!=SCHEMA or manifest['trade_date']!=target or manifest['data_kind']!='RECORDED_INPUT_REPLAY'
            or manifest['evidence']!={}):raise ValueError('M09_HISTORICAL_MANIFEST')
    panel=manifest['panel'];member=manifest['membership'];provenance=manifest['provenance'];history=manifest['historical']
    if panel['format']!=PANEL_FORMAT or member['scope']!='OBSERVED_ROWS_ONLY':raise ValueError('M09_HISTORICAL_SCOPE')
    pointer=read(panel['pointer_path'],panel['pointer_sha256'],8192).decode('utf-8-sig').strip();d._relative(pointer)
    raw=read(pointer,panel['sha256']);rows=_read_snapshot_rows(raw,target)
    members=read(member['path'],member['sha256'],2*1024*1024).decode().splitlines()
    if members!=[r['ts_code'] for r in rows] or type(panel['row_count']) is not int or panel['row_count']!=len(rows):raise ValueError('M09_HISTORICAL_OBSERVED_SET')
    binding=d._json(read(history['binding_path'],history['binding_sha256']))
    reference=d._json(read(provenance['receipt_path'],provenance['receipt_sha256']))
    if (binding.get('schema_version')!='v5.m09.historical_source_binding.v1' or binding.get('trade_date')!=target
            or binding.get('snapshot_sha256')!=panel['sha256'] or binding.get('source_time_verified') is not False
            or binding.get('membership_qualification_verified') is not False
            or binding.get('selection')!=dict(column_order=list(frozen.COLUMNS),predicate='trade_date == requested_date',row_count=len(rows))):
        raise ValueError('M09_HISTORICAL_BINDING')
    origin=binding['source'];sha(origin['sha256'])
    if origin.get('hash_verified') is not True or type(origin.get('bytes')) is not int or origin['bytes']<=0:
        raise ValueError('M09_HISTORICAL_SOURCE_IDENTITY')
    receipt=binding.get('original_receipt')
    if receipt is not None:
        sha(receipt['sha256'])
        if (receipt.get('hash_verified') is not True or type(receipt.get('bytes')) is not int or receipt['bytes']<0
                or receipt.get('metadata_status')!='OPAQUE_ORIGINAL_RECEIPT_HASH_ONLY_NO_READY_CLAIM'):
            raise ValueError('M09_HISTORICAL_RECEIPT_REFERENCE')
    if (reference.get('schema_version')!='v5.m09.opaque_source_reference.v1' or reference.get('trade_date')!=target
            or reference.get('original_receipt')!=receipt or reference.get('source_status')!='UNKNOWN'
            or reference.get('authority_status')!='UNVERIFIED'
            or any(reference.get(k) is not None or provenance.get(k) is not None for k in ('captured_at','available_at','acquired_at'))
            or provenance.get('status')!='UNKNOWN' or provenance.get('authority_status')!='UNVERIFIED'
            or provenance.get('coverage_rate') is not None
            or any(member.get(k) is not None for k in ('captured_at','available_at'))):raise ValueError('M09_HISTORICAL_PROVENANCE_PROMOTION')
    gaps=_research_gaps(rows,receipt);gaps['original_source']=origin;gaps['original_receipt']=receipt
    statuses={key:dict(status='UNKNOWN',reason='HISTORICAL_SOURCE_AVAILABILITY_UNVERIFIED') for key in d.EVIDENCE_ROLES}
    diagnostic=dict(schema_version='v5.m09.admission.v1',admitted=True,trade_date=target,slot=slot,
        cutoff=d._date_slot(target,slot).isoformat(),data_kind='RECORDED_INPUT_REPLAY',issues=[],row_count=len(rows),
        scope='OBSERVED_ROWS_ONLY',strict_1500_pit_verified=False,source_provenance_independently_verified=False,
        evidence_status=statuses,historical_research=gaps)
    return dict(diagnostic=diagnostic,rows=rows,panel_raw=raw,manifest=manifest,panel_source_path=pointer,
                source=source,files=files,context={},source_root=root)


def initialize_a_close_historical_root(root):
    d=_daily();path=d._absolute_root(root)
    if path.exists() and any(path.iterdir()):
        handle=frozen.safe_root(path)
        try: marker=handle.read_bytes(MARKER,max_bytes=100)
        except FileNotFoundError as exc: raise ValueError('M09_HISTORICAL_ROOT_REQUIRED') from exc
        if marker!=MARKER_BYTES:raise ValueError('M09_HISTORICAL_ROOT_REQUIRED')
        d._private_io(path);return {'status':'ALREADY_INITIALIZED'}
    d.initialize_a_close_root(path);frozen.safe_root(path).write_bytes(MARKER,MARKER_BYTES,require_absent=True)
    return {'status':'INITIALIZED'}


def _request_for(source_root,target,attempt_id,slot,configuration_revision):
    root=_daily()._absolute_root(source_root);raw=frozen.safe_root(root).read_bytes('input.json',max_bytes=MAX_JSON_BYTES)
    return dict(schema_version='v5.m09.daily_request.v1',trade_date=target,slot=slot,
        job_id='m09_historical_'+slot.replace(':',''),attempt_id=attempt_id,execution_kind='RECORDED_INPUT_REPLAY',
        triggered_at=datetime.now(timezone.utc).isoformat(),source_root=str(root),input_manifest='input.json',
        input_manifest_sha256=hashlib.sha256(raw).hexdigest(),configuration_revision=configuration_revision)


def run_a_close_historical(root,source_root,trade_date,*,attempt_id,slot='17:10',configuration_revision='m09-historical-v1',expected_generation_sha256=None):
    request=_request_for(source_root,trade_date,attempt_id,slot,configuration_revision)
    if expected_generation_sha256 is not None:request['expected_generation_sha256']=expected_generation_sha256
    return _daily().run_a_close_daily(root,request)

"""Independent research-only PyTDX SDK window; never a native-panel repair.

Consumes sealed capture receipts offline. The original _record and _decoder
validate/decode the source; this module contains no screening formula. Numeric
values are SDK native values, not evidence of shares, HKD or unadjusted prices.
"""
from __future__ import annotations
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from .contracts import aware, exact_keys, sha, trade_date
from .rebound_raw_repair import _canonical, _decoder, _read, _record, _sha
from .rebound_owner import _json

REQUEST_SCHEMA = 'v5.rebound_pytdx_window_owner_request.v1'
MANIFEST_SCHEMA = 'v5.rebound_pytdx_window_manifest.v1'
ASSET_SCHEMA = 'v5.rebound_pytdx_sdk_window_asset.v1'
SHARD_SCHEMA = 'v5.rebound_pytdx_sdk_record_shard.v1'
SOURCE_SHA = 'fa7dcbce4ee026b0a02c47220820d0407af183553d3304afcc5db425dce33cbd'
RAW_DECODER_SHA = '0c6236be65fb52c78b04c124dad90b0d5413c41d78e00bc00d73f1706e1985cc'
ENDPOINT = '119.97.142.130:7721'
MAX_JSON_BYTES = 8 * 1024**2
MAX_SHARDS = 23  # 7 input roles + 23 shards + 2 generated routing files <= 32.
MAX_MEMBERS = 2000
COLUMNS = ('trade_date_compact','code_norm','name','open','high','low','close','amount','trade','pre_close')
SOURCE_CONTRACT = dict(
    name='pytdx_exhq_get_instrument_bars_category4_market71_sdk_decoded_native_v1',
    provider='PYTDX_EXHQ_SDK', interface='get_instrument_bars', category=4, market=71,
    endpoint=ENDPOINT, source_sha256=SOURCE_SHA, raw_decoder_sha256=RAW_DECODER_SHA,
    representation='COMPLETE_SDK_DECODED_RESPONSE_NOT_TCP_BYTES',
    high_window='SAME_INTERFACE_EXACT_NATIVE_CALENDAR_PRIOR60',
    volume_window='SAME_INTERFACE_EXACT_PREVIOUS5_FULL_SESSIONS_PLUS_SIGNAL',
    volume_field='trade', scale_applied=1, volume_unit=None, volume_unit_status='NOT_PROVEN',
    price_currency=None, price_basis='NOT_PROVEN', amount_unit=None,
    provider_finality='NOT_ATTESTED', target_membership='NOT_PROVEN',
    member_source='ORIGINAL_SIGNAL_PANEL_EXACT_CODES_NO_FILTER',
    missing_policy='PRESERVE_MEMBER_NULL_SIGNAL_ROW_NO_ZERO_NO_MIXED_FILL',
    qualification='INDEPENDENT_RESEARCH_ONLY_NOT_NATIVE_PANEL_REPAIR')
SAFETY = dict(research_only=True, production_allowed=False, buy_gate_updated=False,
              orders_sent=False, natural_verified=False, formal_eligibility_verified=False)


def _members(values):
    if (not isinstance(values,list) or not 1<=len(values)<=MAX_MEMBERS
            or any(not isinstance(c,str) or not re.fullmatch(r'HK\.[0-9]{5}',c) for c in values)
            or values!=sorted(set(values))):
        raise ValueError('PYTDX_WINDOW_MEMBERS')
    return values


def _sessions(value, signal):
    if not isinstance(value,dict): raise ValueError('PYTDX_WINDOW_SESSIONS')
    for field,count in [('prior60',60),('previous5',5)]:
        days=value.get(field)
        if (not isinstance(days,list) or len(days)!=count or days!=sorted(set(days))
                or any(trade_date(d)>=signal for d in days)):
            raise ValueError('PYTDX_WINDOW_SESSIONS')
    if not set(value['previous5'])<=set(value['prior60']):
        raise ValueError('PYTDX_WINDOW_SESSIONS')
    sha(value.get('calendar_sha256'))
    return {k:copy.deepcopy(value[k]) for k in ('prior60','previous5','calendar_sha256')}


def _source_identity(record, cutoff):
    if record.get('source_sha256')!=SOURCE_SHA or record.get('endpoint')!=ENDPOINT:
        raise ValueError('PYTDX_WINDOW_SOURCE_IDENTITY')
    request=record.get('request')
    if (not isinstance(request,dict) or set(request)!=set(('category','market','code','start','count'))
            or type(request.get('count')) is not int or not 1<=request['count']<=120
            or type(request.get('start')) is not int or request['start']!=0):
        raise ValueError('PYTDX_WINDOW_REQUEST_BOUND')
    if (type(request.get('category')) is not int or request['category']!=4
            or type(request.get('market')) is not int or request['market']!=71
            or request.get('code')!=str(record.get('code',''))[3:]):
        raise ValueError('PYTDX_WINDOW_REQUEST_IDENTITY')
    if _sha(_canonical(request))!=sha(record.get('request_sha256')):
        raise ValueError('PYTDX_WINDOW_REQUEST_SHA')
    started=aware(record.get('request_started_at')); finished=aware(record.get('request_finished_at'))
    if not started<=finished<=cutoff: raise ValueError('PYTDX_WINDOW_CAPTURE_AFTER_CUTOFF')
    acquired=record.get('response_acquired_at')
    if acquired is not None and not started<=aware(acquired)<=finished:
        raise ValueError('PYTDX_WINDOW_CAPTURE_CLOCK_ORDER')
    return started,finished


def decode_window(records, *, members, signal_date, sessions, research_cutoff, now=None):
    """Return same-source calculator columns plus explicit research provenance.

    Integrity/interface/clock errors reject the input. Actual source anomalies,
    missing receipts, failed captures and incomplete calendar windows preserve
    the original member as a null signal row and therefore remain pending in
    the unchanged original calculator. No old panel price/volume is accepted.
    """
    members=_members(members); signal=trade_date(signal_date)
    sessions=_sessions(sessions,signal); cutoff=aware(research_cutoff)
    now=datetime.now(timezone.utc) if now is None else now
    if cutoff>now: raise ValueError('PYTDX_WINDOW_FUTURE_CUTOFF')
    if not isinstance(records,list) or len(records)>MAX_MEMBERS:
        raise ValueError('PYTDX_WINDOW_RECORD_BOUND')
    verify_decoder_pin()
    bar_date,decode=_decoder()  # Unmodified frozen original decoder, hash-checked there.
    by_code={}; starts=[]; finishes=[]; canonical_hashes={}
    for record in records:
        if not isinstance(record,dict) or record.get('code') not in members:
            raise ValueError('PYTDX_WINDOW_UNREQUESTED_RECORD')
        code=record['code']
        if code in by_code: raise ValueError('PYTDX_WINDOW_DUPLICATE_RECORD')
        start,finish=_source_identity(record,cutoff)
        starts.append(start);finishes.append(finish)
        canonical_hashes[code]=_sha(_canonical(record));by_code[code]=record
    wanted=set(sessions['prior60'])|{signal}; output=[]; pending={}; evidence=[]
    for code in members:
        record=by_code.get(code); decoded={}; reason=[]; selected_evidence=[]
        if record is None:
            reason=['RECORD_MISSING']
        elif record.get('status') not in ('RESPONSE_CAPTURED','READY','PENDING'):
            status=record.get('status')
            if status not in ('QUERY_FAILED','RESPONSE_INVALID','CLOCK_INVALID','CONNECT_FAILED'):
                raise ValueError('PYTDX_WINDOW_UNKNOWN_CAPTURE_STATUS')
            # Even failure receipts may carry a complete received response. Bind
            # it rather than dropping it or accepting an unverified SHA claim.
            if record.get('source_rows') is not None:
                if _sha(_canonical(record['source_rows']))!=sha(record.get('response_sha256')):
                    raise ValueError('PYTDX_WINDOW_RESPONSE_SHA')
            elif record.get('response_sha256') is not None:
                raise ValueError('PYTDX_WINDOW_RESPONSE_SHA')
            reason=[status]
        else:
            _,raw_rows,_,_=_record(record,now)  # Original request/response/clocks contract.
            seen=set()
            for index,raw_row in enumerate(raw_rows):
                try:
                    day=bar_date(raw_row)
                    if day in seen:
                        reason.append('DUPLICATE_SOURCE_DATE'); break
                    seen.add(day)
                    value=decode(raw_row,signal,wanted)
                    if value is None: continue
                    value.pop('native_fields'); value.pop('trade_date')
                    decoded[day]=dict(trade_date_compact=day,code_norm=code,name=code,
                                      **value,pre_close=None)
                    selected_evidence.append(dict(code=code,date=day,source_row_index=index,
                        source_row_sha256=_sha(_canonical(raw_row)),record_canonical_sha256=canonical_hashes[code]))
                except (ValueError,KeyError,TypeError,OverflowError):
                    reason.append('SOURCE_ROW_INVALID'); break
            if reason:
                decoded={};selected_evidence=[]
            else:
                if not set(sessions['prior60'])<=set(decoded): reason.append('PRIOR60_KEYS_MISSING')
                if not set(sessions['previous5'])<=set(decoded): reason.append('PREVIOUS5_KEYS_MISSING')
                if signal not in decoded: reason.append('SIGNAL_KEY_MISSING')
        if reason:
            pending[code]=sorted(set(reason))
            # Never let a partial response qualify after a source anomaly.
            decoded[signal]=dict(trade_date_compact=signal,code_norm=code,name=code,
                **{k:None for k in ('open','high','low','close','amount','trade','pre_close')})
            selected_evidence=[e for e in selected_evidence if e['date']!=signal]
        else:
            decoded[signal]['pre_close']=decoded[sessions['prior60'][-1]]['close']
        output.extend(decoded[d] for d in sorted(decoded));evidence.extend(selected_evidence)
    return dict(asset_schema_version=ASSET_SCHEMA,source_contract=copy.deepcopy(SOURCE_CONTRACT),
        rows=output,row_evidence=evidence,members=list(members),members_sha256=_sha(_canonical(members)),
        sessions=sessions,pending_reasons=pending,record_canonical_sha256=canonical_hashes,
        capture_started_at=min(starts).isoformat() if starts else None,
        capture_finished_at=max(finishes).isoformat() if finishes else None,
        research_cutoff=research_cutoff,**SAFETY)


def pack_records(records, *, max_shard_bytes=MAX_JSON_BYTES):
    """Lossless canonical JSON envelopes, each <=8MiB, maximum23 shards.

    Whole SDK receipt objects are retained. Per-record canonical SHA is
    independently recomputable; no field projection or row filtering occurs.
    """
    if (type(max_shard_bytes) is not int or not 1<=max_shard_bytes<=MAX_JSON_BYTES
            or not isinstance(records,list) or len(records)>MAX_MEMBERS):
        raise ValueError('PYTDX_WINDOW_SHARD_BOUND')
    result=[]; current=[]
    def encode(items): return _canonical(dict(schema_version=SHARD_SCHEMA,records=items))
    for record in records:
        if not isinstance(record,dict): raise ValueError('PYTDX_WINDOW_RECORD_OBJECT')
        entry=dict(record=record,canonical_sha256=_sha(_canonical(record)))
        if len(encode([entry]))>max_shard_bytes: raise ValueError('PYTDX_WINDOW_SHARD_SINGLE_RECORD_SIZE')
        if current and len(encode(current+[entry]))>max_shard_bytes:
            result.append(encode(current));current=[]
        current.append(entry)
    # An empty shard explicitly binds a zero-response capture, never absence.
    result.append(encode(current))
    if len(result)>MAX_SHARDS: raise ValueError('PYTDX_WINDOW_SHARD_COUNT')
    return result


def read_records(root, references):
    if not isinstance(references,list) or not 1<=len(references)<=MAX_SHARDS:
        raise ValueError('PYTDX_WINDOW_SHARD_COUNT')
    records=[];seen=set()
    for reference in references:
        exact_keys(reference,('relative','sha256','bytes'))
        relative=reference['relative']
        if relative in seen: raise ValueError('PYTDX_WINDOW_DUPLICATE_SHARD')
        seen.add(relative)
        if type(reference['bytes']) is not int or not 0<reference['bytes']<=MAX_JSON_BYTES:
            raise ValueError('PYTDX_WINDOW_SHARD_SIZE')
        raw=_read(Path(root),relative,MAX_JSON_BYTES)
        if len(raw)!=reference['bytes'] or _sha(raw)!=sha(reference['sha256']):
            raise ValueError('PYTDX_WINDOW_SHARD_SHA')
        document=_json(raw);exact_keys(document,('schema_version','records'))
        if document['schema_version']!=SHARD_SCHEMA or not isinstance(document['records'],list):
            raise ValueError('PYTDX_WINDOW_SHARD_SCHEMA')
        for entry in document['records']:
            exact_keys(entry,('record','canonical_sha256'))
            if not isinstance(entry['record'],dict) or _sha(_canonical(entry['record']))!=sha(entry['canonical_sha256']):
                raise ValueError('PYTDX_WINDOW_RECORD_CANONICAL_SHA')
            records.append(entry['record'])
            if len(records)>MAX_MEMBERS: raise ValueError('PYTDX_WINDOW_RECORD_BOUND')
    return records


def verify_decoder_pin():
    from . import rebound_raw_repair as raw_module
    if hashlib.sha256(Path(raw_module.__file__).read_bytes()).hexdigest()!=RAW_DECODER_SHA:
        raise ValueError('PYTDX_WINDOW_RAW_DECODER_SOURCE_SHA')


def validate_request(value, *, base):
    """Separate opt-in schema; the old owner's request validator stays intact."""
    import sys
    from .composition import no_symlinks
    from .source_capsule import checked_path
    exact_keys(value,('schema_version','target_date','signal_date','research_cutoff','data_kind','input_root','paths','files'))
    if value['schema_version']!=REQUEST_SCHEMA: raise ValueError('PYTDX_WINDOW_REQUEST_SCHEMA')
    day=trade_date(value['signal_date'])
    if trade_date(value['target_date'])<=day: raise ValueError('PYTDX_WINDOW_SIGNAL_DATE')
    if aware(value['research_cutoff'])>datetime.now(timezone.utc): raise ValueError('PYTDX_WINDOW_FUTURE_CUTOFF')
    if value['data_kind'] not in ('SYNTHETIC','RECORDED_INPUT_REPLAY'):raise ValueError('PYTDX_WINDOW_DATA_KIND')
    root=no_symlinks(value['input_root'])
    if not root.is_dir():raise ValueError('PYTDX_WINDOW_INPUT_ROOT')
    for code_root in (Path(base),Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve()):
        if root.is_relative_to(code_root) or code_root.is_relative_to(root):
            raise ValueError('PYTDX_WINDOW_CODE_INPUT_OVERLAP')
    roles={'panel_manifest','panel','master_manifest','master_artifact','master_receipt',
           'window_parent_manifest','window_parent_panel'}
    paths=value['paths'];files=value['files']
    if not isinstance(paths,dict) or set(paths)!=roles or len(set(paths.values()))!=7:
        raise ValueError('PYTDX_WINDOW_ROLES')
    if not isinstance(files,dict) or not 8<=len(files)<=30:
        raise ValueError('PYTDX_WINDOW_INPUT_FILES_WITH_TWO_ROUTING_FILES')
    prefix='assets/m14_pytdx_windows/runs/'+day+'/'
    for relative,digest in files.items():
        checked_path(root,relative);sha(digest)
        if not (re.fullmatch(re.escape(prefix)+r'[A-Za-z0-9_-]+/(manifest\.json|window\.parquet|records-[0-9]{3}\.json)',relative)
            or re.fullmatch(r'assets/hk_0_2/panels/[A-Za-z0-9._-]+/(manifest\.json|hkconnect_vipdoc_daily_panel\.parquet)',relative)
            or re.fullmatch(r'assets/hk_security_master/runs/'+day+r'/[A-Za-z0-9_-]+/(manifest\.json|artifact\.csv|receipt\.json)',relative)):
            raise ValueError('PYTDX_WINDOW_INPUT_PATH')
    if not set(paths.values())<=set(files):raise ValueError('PYTDX_WINDOW_ROLE_NOT_BOUND')
    parent=Path(paths['panel_manifest']).parent.as_posix()
    if (not parent.startswith(prefix) or paths['panel_manifest']!=parent+'/manifest.json'
            or paths['panel']!=parent+'/window.parquet'
            or paths['window_parent_manifest']!=str(Path(paths['window_parent_panel']).with_name('manifest.json'))
            or not paths['window_parent_panel'].startswith('assets/hk_0_2/panels/')
            or not paths['window_parent_panel'].endswith('/hkconnect_vipdoc_daily_panel.parquet')
            or not paths['master_manifest'].startswith('assets/hk_security_master/runs/'+day+'/')
            or paths['master_manifest']!=str(Path(paths['master_artifact']).with_name('manifest.json'))
            or paths['master_receipt']!=str(Path(paths['master_artifact']).with_name('receipt.json'))
            or not paths['master_artifact'].endswith('/artifact.csv')):
        raise ValueError('PYTDX_WINDOW_ROLE_PATH')
    extras=set(files)-set(paths.values())
    if any(not re.fullmatch(re.escape(parent)+r'/records-[0-9]{3}\.json',p) for p in extras):
        raise ValueError('PYTDX_WINDOW_UNBOUND_PATH')
    _canonical(value)
    return copy.deepcopy(value)


def metadata(root, request):
    """Verify new schema while using the old exact-day master/parent checks."""
    from . import rebound_owner as owner
    from .source_capsule import checked_path
    paths=request['paths'];files=request['files'];day=request['signal_date']
    old=copy.deepcopy(request);old['schema_version']='v5.rebound_owner_request.v1'
    old['paths']={key:paths[key] for key in owner.ROLES}
    old['paths']['panel_manifest']=paths['window_parent_manifest'];old['paths']['panel']=paths['window_parent_panel']
    _,master,receipt=owner._metadata(root,old)
    manifest=_json(_read(Path(root),paths['panel_manifest'],MAX_JSON_BYTES))
    fields={'schema_version','asset_schema_version','source_contract','target_date','signal_date',
        'research_cutoff','panel_relative','panel_sha256','panel_rows','panel_code_count','members','members_sha256',
        'sessions','records','capture_started_at','capture_finished_at','manifest_prepared_at','parent_panel_sha256',
        'parent_manifest_sha256','row_projection_sha256','pending_reasons','capture_audit'}|set(SAFETY)
    exact_keys(manifest,fields)
    if (manifest['schema_version']!=MANIFEST_SCHEMA or manifest['asset_schema_version']!=ASSET_SCHEMA
            or manifest['source_contract']!=SOURCE_CONTRACT
            or any(manifest[k] is not v for k,v in SAFETY.items())
            or manifest['target_date']!=request['target_date'] or manifest['signal_date']!=day
            or manifest['research_cutoff']!=request['research_cutoff']
            or manifest['panel_relative']!=paths['panel'] or manifest['panel_sha256']!=files[paths['panel']]
            or manifest['parent_panel_sha256']!=files[paths['window_parent_panel']]
            or manifest['parent_manifest_sha256']!=files[paths['window_parent_manifest']]):
        raise ValueError('PYTDX_WINDOW_MANIFEST_CONTRACT')
    members=_members(manifest['members']);_sessions(manifest['sessions'],day)
    if manifest['members_sha256']!=_sha(_canonical(members)):
        raise ValueError('PYTDX_WINDOW_MEMBERS_SHA')
    sha(manifest['row_projection_sha256'])
    if (type(manifest['panel_rows']) is not int or not len(members)<=manifest['panel_rows']<=61*len(members)
            or manifest['panel_code_count']!=len(members)):
        raise ValueError('PYTDX_WINDOW_ROW_COUNT')
    prepared=aware(manifest['manifest_prepared_at']);cutoff=aware(request['research_cutoff'])
    if prepared>cutoff:raise ValueError('PYTDX_WINDOW_MANIFEST_AFTER_CUTOFF')
    start,finish=manifest['capture_started_at'],manifest['capture_finished_at']
    if (start is None)!=(finish is None):raise ValueError('PYTDX_WINDOW_CAPTURE_CLOCK')
    if start is not None and not aware(start)<=aware(finish)<=prepared:
        raise ValueError('PYTDX_WINDOW_CAPTURE_CLOCK')
    references=manifest['records']
    if not isinstance(references,list) or not 1<=len(references)<=MAX_SHARDS:
        raise ValueError('PYTDX_WINDOW_SHARD_COUNT')
    extra=set(files)-set(paths.values())
    if (len({r['relative'] for r in references})!=len(references)
            or {r['relative'] for r in references}!=extra
            or any(files.get(r['relative'])!=r['sha256'] for r in references)):
        raise ValueError('PYTDX_WINDOW_EXACT_SHARDS')
    validate_capture_audit(manifest['capture_audit'], manifest, request)
    return manifest,master,receipt


def _rows_from_frame(frame):
    """Canonical nullable cell projection; no approximate numeric comparison."""
    import pandas as pd
    if list(frame.columns)!=list(COLUMNS):raise ValueError('PYTDX_WINDOW_PANEL_COLUMNS')
    result=[]
    for values in frame.itertuples(index=False,name=None):
        row={}
        for key,value in zip(COLUMNS,values):
            if pd.isna(value):row[key]=None
            elif key in ('trade_date_compact','code_norm','name'):
                if not isinstance(value,str):raise ValueError('PYTDX_WINDOW_TEXT_COLUMN')
                row[key]=value
            else:
                if isinstance(value,bool):raise ValueError('PYTDX_WINDOW_NUMERIC_COLUMN')
                row[key]=float(value)
        result.append(row)
    return sorted(result,key=lambda r:(r['code_norm'],r['trade_date_compact']))


def bind_private_window(root,request,original):
    """Reconstruct all calculator input from sealed receipts in the private copy.

    This returns a new research witness, never an old native witness. It must
    run after the original owner read/write/network guard has been installed.
    """
    import pandas as pd
    from .source_capsule import checked_path
    manifest,_,_=metadata(root,request)
    sessions=original.rebound_history_sessions(request['signal_date'])
    if _sessions(sessions,request['signal_date'])!=manifest['sessions']:
        raise ValueError('PYTDX_WINDOW_NATIVE_CALENDAR_MISMATCH')
    paths=request['paths'];files=request['files']
    original_frame=pd.read_parquet(checked_path(root,paths['window_parent_panel']),
        columns=['trade_date_compact','code_norm'])
    original_days=original_frame['trade_date_compact'].astype(str).str.zfill(8)
    members=original_frame.loc[original_days==request['signal_date'],'code_norm'].astype(str).str.upper().tolist()
    if sorted(members)!=manifest['members'] or len(set(members))!=len(members):
        raise ValueError('PYTDX_WINDOW_ORIGINAL_MEMBER_SET')
    records=read_records(root,manifest['records'])
    audit=manifest['capture_audit']
    if {r['code']:_sha(_canonical(r)) for r in records}!={r['code']:r['sha256'] for r in audit['receipts']}:
        raise ValueError('PYTDX_WINDOW_AUDITED_RECEIPT_SET')
    for record in records:
        if record.get('original_reference')!=audit['original_reference'] or record.get('parent_binding')!=audit['parent_binding']:
            raise ValueError('PYTDX_WINDOW_CAPTURE_ORIGINAL_REFERENCE')
        binding=record.get('parent_binding') or {}
        if (record.get('target_date')!=request['target_date'] or record.get('signal_date')!=request['signal_date']
                or record.get('expected_panel_sha256')!=files[paths['window_parent_panel']]
                or binding.get('parent_panel_sha256')!=files[paths['window_parent_panel']]
                or binding.get('parent_manifest_sha256')!=files[paths['window_parent_manifest']]
                or 'assets/hk_0_2/'+str(binding.get('parent_panel_relative'))!=paths['window_parent_panel']
                or 'assets/hk_0_2/'+str(binding.get('parent_manifest_relative'))!=paths['window_parent_manifest']):
            raise ValueError('PYTDX_WINDOW_CAPTURE_PARENT_BINDING')
    decoded=decode_window(records,members=manifest['members'],signal_date=request['signal_date'],
        sessions=sessions,research_cutoff=request['research_cutoff'])
    expected=sorted(decoded['rows'],key=lambda r:(r['code_norm'],r['trade_date_compact']))
    frame=pd.read_parquet(checked_path(root,paths['panel']),columns=list(COLUMNS))
    rows=_rows_from_frame(frame)
    if (_canonical(rows)!=_canonical(expected) or _sha(_canonical(expected))!=manifest['row_projection_sha256']
            or len(rows)!=manifest['panel_rows'] or decoded['pending_reasons']!=manifest['pending_reasons']
            or decoded['capture_started_at']!=manifest['capture_started_at']
            or decoded['capture_finished_at']!=manifest['capture_finished_at']):
        raise ValueError('PYTDX_WINDOW_RECONSTRUCTION_MISMATCH')
    witness=dict(owner='V5_INDEPENDENT_PYTDX_RESEARCH_WINDOW',
        panel_manifest_path=str(checked_path(root,paths['panel_manifest'])),
        panel_manifest_sha256=files[paths['panel_manifest']],panel_path=str(checked_path(root,paths['panel'])),
        panel_sha256=files[paths['panel']],panel_max_date=request['signal_date'],
        panel_code_count=len(members),panel_rows=len(rows),source_contract=SOURCE_CONTRACT['name'],
        source_schema=ASSET_SCHEMA,panel_available_at=manifest['manifest_prepared_at'],
        price_currency=None,price_basis='NOT_PROVEN',session_kind='NOT_ATTESTED_BY_PROVIDER',amount_unit=None,
        resolution='EXPLICIT_NEW_RESEARCH_REQUEST_PRIVATE_SHA_RECONSTRUCTED',
        semantics='SDK_NATIVE_SAME_SOURCE_WINDOW_NOT_OLD_CERTIFIED_PANEL')
    native=dict(source_contract=copy.deepcopy(SOURCE_CONTRACT),volume_unit=None,volume_unit_status='NOT_PROVEN',
        price_basis='NOT_PROVEN',scale_applied=1,capture_started_at=decoded['capture_started_at'],
        capture_finished_at=decoded['capture_finished_at'],research_cutoff=request['research_cutoff'],
        original_member_count=len(members),pending_reasons=decoded['pending_reasons'],
        gaps=['PYTDX_WINDOW_RESEARCH_ONLY_UNITS_AND_FINALITY_NOT_PROVEN',
              'PYTDX_WINDOW_ORIGINAL_SIGNAL_MEMBERS_NOT_TARGET_ELIGIBILITY'],**SAFETY)
    return witness,native


def install_research_witness(original, *, private, request, witness):
    """Only replace the input witness in a fresh worker; calculator stays exact."""
    from .composition import no_symlinks
    def research_witness(root,day,*,research_cutoff=None,required_history_date=None):
        if (no_symlinks(root)!=private or day!=request['signal_date']
                or aware(research_cutoff)!=aware(request['research_cutoff'])
                or required_history_date!=witness['previous5_required']):
            raise ValueError('PYTDX_WINDOW_WITNESS_CONTEXT')
        result=copy.deepcopy(witness);result.pop('previous5_required')
        return result,[]
    original._read_hk02_panel_witness=research_witness


def validate_capture_audit(audit, manifest, request):
    fields=('schema_version','status','batch_helper_sha256','plan_sha256','context_file_sha256','run_id',
        'checkpoint_sha256','original_reference','parent_binding','audited_at','receipts','pending_codes','uncertain_codes','failed_codes')
    exact_keys(audit,fields)
    if (audit['schema_version']!='v5.rebound_pytdx_batch_audit_binding.v1'
            or audit['status']!='PINNED_BATCH_READONLY_AUDIT_AT_PREPARATION'
            or audit['batch_helper_sha256']!='4d51d842839d38abd906e4294ff801a9e4d38824dd0b899e62c1f12f58e804dd'
            or not isinstance(audit['run_id'],str) or not re.fullmatch(r'[0-9a-f]{32}',audit['run_id'])
            or aware(audit['audited_at'])>aware(manifest['manifest_prepared_at'])):
        raise ValueError('PYTDX_WINDOW_CAPTURE_AUDIT_CONTRACT')
    for name in ('plan_sha256','context_file_sha256','checkpoint_sha256'):sha(audit[name])
    ref=audit['original_reference'];exact_keys(ref,('run_id','artifact_sha256','manifest_sha256','receipt_sha256'))
    if not isinstance(ref['run_id'],str) or not re.fullmatch(r'[0-9a-f]{32}',ref['run_id']):
        raise ValueError('PYTDX_WINDOW_ORIGINAL_REFERENCE')
    for name in ('artifact_sha256','manifest_sha256','receipt_sha256'):sha(ref[name])
    parent=audit['parent_binding'];exact_keys(parent,('parent_pointer_sha256','parent_manifest_relative','parent_manifest_sha256','parent_panel_relative','parent_panel_sha256'))
    sha(parent['parent_pointer_sha256'])
    if (parent['parent_panel_sha256']!=manifest['parent_panel_sha256']
            or parent['parent_manifest_sha256']!=manifest['parent_manifest_sha256']
            or 'assets/hk_0_2/'+parent['parent_manifest_relative']!=request['paths']['window_parent_manifest']
            or 'assets/hk_0_2/'+parent['parent_panel_relative']!=request['paths']['window_parent_panel']):
        raise ValueError('PYTDX_WINDOW_AUDIT_PARENT_BINDING')
    members=set(manifest['members']);receipts=audit['receipts']
    if not isinstance(receipts,list) or len(receipts)>len(members):raise ValueError('PYTDX_WINDOW_AUDIT_RECEIPTS')
    codes=[]
    for item in receipts:
        exact_keys(item,('code','relative','sha256'));sha(item['sha256']);codes.append(item['code'])
        if item['code'] not in members or item['relative'] not in ('receipt-'+item['code']+'.json','reuse-'+item['code']+'.json'):
            raise ValueError('PYTDX_WINDOW_AUDIT_RECEIPT_IDENTITY')
    if codes!=sorted(set(codes)):raise ValueError('PYTDX_WINDOW_AUDIT_RECEIPT_SET')
    for name in ('pending_codes','uncertain_codes','failed_codes'):
        values=audit[name]
        if not isinstance(values,list) or values!=sorted(set(values)) or not set(values)<=members:
            raise ValueError('PYTDX_WINDOW_AUDIT_STATUS_CODES')

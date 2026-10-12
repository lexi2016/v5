"""M08 default original-owner producer for bounded retained inputs.

No provider connections, trades, publication to V4, or natural qualification.
All eight stage contracts are preserved; Stage8 consumes its own snapshot and
RT_DATA, never ordinary-stage rows. Selectors/store are not injectable.
"""
import sys
from pathlib import Path
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import copy
import fcntl
import hashlib
import json
import math
import os
import re
import subprocess
from datetime import datetime,timedelta,timezone
from v5_shadow.composition import no_symlinks
from v5_shadow.contracts import aware,trade_date,sha,exact_keys
from v5_shadow.digests import canonical_bytes,sha256_json,MAX_JSON_BYTES
from v5_shadow.hk_stage_sources import SOURCE_SHA,implementation_identity,load_owners,source_bytes

SAFETY=dict(production_allowed=False,buy_gate_updated=False,orders_sent=False)
MARKER=b'v5.hk-stage-root.v1\n'
TZ=timezone(timedelta(hours=8))
STAGES=('STAGE_0925','STAGE_0930_0935','STAGE_0935_0940','STAGE_0940_0945','STAGE_0945_1030','STAGE_1300_1315','STAGE_1445_1500','STAGE_1545_1555')
UNITS=dict(price='HKD',turnover='HKD',market_cap='HKD_100M',change='PERCENT',volume_ratio='RATIO')
LANES={'D1_MODEL_TOP100','LIVE_HKCONNECT_GAINER','PREOPEN_AUCTION_CONTINUATION','LOW_FLOAT_FILTER','OLD_DEMON_MEMORY','NEW_HKCONNECT_BATCH','STRENGTH_THEME_WATCH','OPENING_INITIAL_SCREEN'}


def init_hk_root(root):
    root=no_symlinks(Path(root))
    if root.exists() and any(root.iterdir()):raise ValueError('M08_INIT_REQUIRES_EMPTY_DIRECTORY')
    root.mkdir(parents=True,exist_ok=True)
    with (root/'.v5-hk-stage-root').open('xb') as stream:stream.write(MARKER)
    return str(root)


def checked_root(root):
    root=no_symlinks(Path(root));marker=no_symlinks(root/'.v5-hk-stage-root')
    if not marker.is_file() or marker.read_bytes()!=MARKER:raise ValueError('M08_ROOT_MARKER')
    return root


def read_json(path):
    path=no_symlinks(Path(path));raw=path.read_bytes()
    if len(raw)>MAX_JSON_BYTES:raise ValueError('M08_JSON_SIZE')
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise ValueError('M08_DUPLICATE_JSON_KEY')
            out[key]=value
        return out
    def constant(_):raise ValueError('M08_NONFINITE_JSON')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)


def _number(value,*,positive=False):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or (positive and value<=0):
        raise ValueError('M08_REQUIRED_NUMBER')


def _codes(rows,key='code'):
    values=[]
    if not isinstance(rows,list) or any(not isinstance(row,dict) for row in rows):raise ValueError('M08_ROWS')
    for row in rows:
        code=row.get(key)
        if not isinstance(code,str) or not re.fullmatch(r'HK\.[0-9]{5}',code):raise ValueError('M08_CODE')
        values.append(code)
    return values


def _time(date,value):return aware(date[:4]+'-'+date[4:6]+'-'+date[6:]+'T'+value+'+08:00')


def validate_request(request,contracts,calendar):
    exact_keys(request,('schema_version','market','target_date','signal_date','stage_id','data_kind','source','m06','m02','route','payload','payload_sha256'))
    if request['schema_version']!='v5.hk_stage_input.v1' or request['market']!='HK_CONNECT':raise ValueError('M08_INPUT_SCHEMA')
    if request['data_kind'] not in ('SYNTHETIC','RECORDED_INPUT_REPLAY'):raise ValueError('M08_NATURAL_ADMISSION_NOT_BOUND')
    date=trade_date(request['target_date']);signal=trade_date(request['signal_date'])
    if signal>=date:raise ValueError('M08_SIGNAL_DATE')
    stage=request['stage_id'];spec=contracts.STAGE_BY_ID.get(stage)
    if spec is None or stage not in STAGES:raise ValueError('M08_STAGE')
    states=calendar.resolve_market_states(date)
    if states['hk_securities'].value=='HALF_TRADING_DAY_AM':raise ValueError('M08_HALF_DAY_WINDOW_CONTRACT_UNVERIFIED')
    if states['hk_securities'].value!='FULL_TRADING_DAY':raise ValueError('M08_HK_SECURITIES_NOT_OPEN')
    if states['hk_connect'].value=='UNKNOWN':raise ValueError('M08_CONNECT_CALENDAR_UNKNOWN')
    previous=datetime.strptime(date,'%Y%m%d')-timedelta(days=1)
    for _ in range(20):
        p=previous.strftime('%Y%m%d')
        if calendar.resolve_market_states(p)['hk_securities'].value in ('FULL_TRADING_DAY','HALF_TRADING_DAY_AM'):break
        previous-=timedelta(days=1)
    if p!=signal:raise ValueError('M08_SIGNAL_NOT_PREVIOUS_HK_SESSION')
    source=request['source'];pool=request['m06'];membership=request['m02'];payload=request['payload']
    exact_keys(source,('collector_id','source_date','captured_at','available_at','status','requested_rows','missing_symbols','cannot_confirm','source_evidence','source_sha256'))
    exact_keys(pool,('target_date','signal_date','run_id','rows','rows_sha256'))
    exact_keys(membership,('membership_date','source_date','status','codes','receipt_sha256','units'))
    if not isinstance(source['collector_id'],str) or not source['collector_id']:raise ValueError('M08_COLLECTOR_REQUIRED')
    if source['source_date']!=date or pool['target_date']!=date or pool['signal_date']!=signal:raise ValueError('M08_SOURCE_DATE')
    if membership['membership_date']!=date or membership['source_date']!=date:raise ValueError('M08_MEMBERSHIP_DATE')
    if membership['units']!=UNITS:raise ValueError('M08_UNITS')
    if membership['status'] not in ('VERIFIED','UNKNOWN','SYNTHETIC'):raise ValueError('M08_MEMBERSHIP_STATUS')
    sha(membership['receipt_sha256']);sha(pool['rows_sha256']);sha(source['source_sha256']);sha(request['payload_sha256'])
    if not isinstance(pool['run_id'],str) or not pool['run_id']:raise ValueError('M08_M06_RUN_ID')
    poolcodes=_codes(pool['rows'])
    if len(poolcodes)!=100 or len(set(poolcodes))!=100 or sha256_json(pool['rows'])!=pool['rows_sha256']:raise ValueError('M08_M06_EXACT_TOP100')
    for index,row in enumerate(pool['rows'],1):
        if row.get('target_date')!=date or row.get('signal_date')!=signal or row.get('rank')!=index:raise ValueError('M08_M06_ROW_IDENTITY')
        _number(row.get('score_prob_active'))
        if not row.get('preselect_lane'):raise ValueError('M08_M06_LANE_REQUIRED')
    membercodes=membership['codes']
    if not isinstance(membercodes,list) or len(membercodes)!=len(set(membercodes)) or any(not isinstance(c,str) or not re.fullmatch(r'HK\.[0-9]{5}',c) for c in membercodes):raise ValueError('M08_MEMBERSHIP_CODES')
    if not set(poolcodes)<=set(membercodes):raise ValueError('M08_POOL_MEMBERSHIP_UNKNOWN')
    if not isinstance(payload,dict) or sha256_json(payload)!=request['payload_sha256'] or source['source_sha256']!=request['payload_sha256']:raise ValueError('M08_PAYLOAD_SHA')
    status=source['status']
    if status not in ('READY','READY_EMPTY','PARTIAL_WITH_ROWS','CANNOT_CONFIRM'):raise ValueError('M08_SOURCE_STATUS')
    if type(source['requested_rows']) is not int or source['requested_rows']<0:raise ValueError('M08_COVERAGE')
    for field in ('missing_symbols','cannot_confirm','source_evidence'):
        if not isinstance(source[field],list) or any(not isinstance(s,str) for s in source[field]):raise ValueError('M08_SOURCE_DIAGNOSTICS')
    if status in ('READY','READY_EMPTY') and (source['missing_symbols'] or source['cannot_confirm']):raise ValueError('M08_READY_CONTRADICTION')
    captured=aware(source['captured_at']);available=aware(source['available_at'])
    cutoff=_time(date,spec.cutoff);window=spec.hk_window or spec.window;start=_time(date,window.split('-')[0]+':00')
    if not start<=captured<=available<=cutoff or available>datetime.now(timezone.utc):raise ValueError('M08_SOURCE_TIME')
    route=request['route']
    if stage=='STAGE_0925':
        if route not in ('SECOND_FILTER','D1_REFERENCE'):raise ValueError('M08_AUCTION_ROUTE')
        if route=='SECOND_FILTER' and captured>_time(date,'09:20:05'):raise ValueError('M08_AUCTION_CAPTURE_CUTOFF')
    elif stage=='STAGE_1545_1555':
        if route!='STAGE8_RTDATA':raise ValueError('M08_STAGE8_SEPARATE_ROUTE_REQUIRED')
        exact_keys(payload,('snapshot','rtdata','enrichment'))
        if captured!=_time(date,'15:55:00'):raise ValueError('M08_STAGE8_RETAINED_CAPTURE_CUTOFF')
    elif route!='FOUR_LANE':raise ValueError('M08_ORDINARY_ROUTE')
    if stage!='STAGE_1545_1555':
        exact_keys(payload,('rows',));rows=payload['rows'];codes=_codes(rows)
        if route!='FOUR_LANE' and len(codes)!=len(set(codes)):raise ValueError('M08_DUPLICATE_CODE')
        if source['requested_rows']<len(set(codes)):raise ValueError('M08_COVERAGE')
        if status=='READY_EMPTY' and rows:raise ValueError('M08_EMPTY_CONTRADICTION')
        if not rows and status=='READY':raise ValueError('M08_EMPTY_REQUIRES_VERIFIED_STATUS')
        if not set(codes)<=set(membercodes):raise ValueError('M08_ROW_MEMBERSHIP_UNKNOWN')
        seen={}
        for row in rows:
            code=row['code']
            if row.get('target_date')!=date or row.get('signal_date')!=signal:raise ValueError('M08_ROW_DATE')
            if route=='D1_REFERENCE':
                original=pool['rows'][poolcodes.index(code)]
                if row!=original:raise ValueError('M08_D1_REFERENCE_NOT_EXACT_POOL_ROW')
                continue
            if row.get('trade_date')!=date or row.get('stage_id')!=stage:raise ValueError('M08_ROW_STAGE_DATE')
            if 'stage_score' in row or 'score' in row:raise ValueError('M08_RAW_SCORE_OVERRIDE')
            when=aware(row.get('captured_at'));updated=aware(row.get('update_time'))
            if not start<=updated<=when<=captured:raise ValueError('M08_ROW_TIME')
            for k in ('source_last_bar_time','source_last_tick_time'):
                if k in row and not start<=aware(row[k])<=when:raise ValueError('M08_ROW_SOURCE_TIME')
            lanes=row.get('candidate_lanes')
            if not isinstance(lanes,list) or not lanes or len(lanes)!=len(set(lanes)) or any(l not in LANES for l in lanes):raise ValueError('M08_LANES')
            if code in seen and (route!='FOUR_LANE' or set(lanes)&seen[code]):raise ValueError('M08_DUPLICATE_CODE_LANE')
            seen.setdefault(code,set()).update(lanes)
            if 'D1_MODEL_TOP100' in lanes and code not in poolcodes:raise ValueError('M08_D1_CODE_OUTSIDE_POOL')
            for k in ('open_price','last_price','high_price','low_price'):_number(row.get(k),positive=True)
            for k in ('pct_chg','volume_ratio','circular_market_cap_hkd_yi','turnover_hkd'):_number(row.get(k))
            for k in ('volume_ratio','circular_market_cap_hkd_yi','turnover_hkd','platform_circular_market_cap_hkd_yi','turnover_hkd_yi','turnover_rate','futu_turnover_rate','offer_float_market_cap_hkd_yi'):
                if k in row:
                    _number(row[k])
                    if row[k]<0:raise ValueError('M08_NEGATIVE_QUOTE_ALIAS')
            if row['low_price']>min(row['open_price'],row['last_price']) or row['high_price']<max(row['open_price'],row['last_price']):raise ValueError('M08_QUOTE_RANGE')
            if route=='SECOND_FILTER':
                for k in ('rank','auction_score','reference_price_hkd','strict_failure_price_hkd','ask_price','bid_price'):_number(row.get(k))
                if not row.get('second_filter_status') or not row.get('preselect_lane'):raise ValueError('M08_AUCTION_SOURCE_REQUIRED')
    canonical_bytes(request)
    return dict(states={k:v.value for k,v in states.items()},window=window,cutoff=spec.cutoff,calendar=calendar.calendar_provenance())


def _stage8_rows(request,generation):
    from stage_center.hk_stage8 import snapshot,rtdata
    from stage_center.acquisition import AcquisitionPlan,StageUniverseBinding
    payload=request['payload'];snap=payload['snapshot'];codes=request['m02']['codes'];date=request['target_date'];stage=request['stage_id']
    # This is retained source, not a newly fabricated current-day snapshot.
    path=snapshot._snapshot_path(generation,date,stage);path.parent.mkdir(parents=True,exist_ok=True)
    snapshot._atomic_snapshot_create(path,snap)
    loaded=snapshot.load_hk_active_snapshot(generation,trade_date=date,stage_id=stage,codes=codes,cutoff_at='15:55:00')
    if loaded['status']!='READY':raise ValueError('M08_STAGE8_SNAPSHOT:'+','.join(loaded['cannot_confirm']))
    active=rtdata._stage8_active_snapshot_codes(loaded['rows']);raw=payload['rtdata']
    if not isinstance(raw,dict) or not isinstance(raw.get('rows'),list):raise ValueError('M08_STAGE8_RTDATA')
    seen=set()
    for row in raw['rows']:
        if row.get('code') not in active:raise ValueError('M08_STAGE8_RTDATA_CODE')
        when=aware(row.get('time'));key=(row['code'],when)
        if key in seen:raise ValueError('M08_STAGE8_DUPLICATE_TICK')
        seen.add(key)
        if not _time(date,'15:45:00')<=when<=_time(date,'15:55:00'):raise ValueError('M08_STAGE8_RTDATA_WINDOW')
        for k in ('cur_price','high','low'):_number(row.get(k),positive=True)
        for k in ('turnover','volume'):
            _number(row.get(k))
            if row[k]<0:raise ValueError('M08_STAGE8_RTDATA_NUMBER')
    binding=StageUniverseBinding.ready(market='HK_CONNECT',trade_date=date,role='RETAINED_FULL_UNIVERSE',codes=tuple(codes),source_run_id=request['m06']['run_id'],sha256=request['m02']['receipt_sha256'])
    plan=AcquisitionPlan(date,stage,('HK_CONNECT',),None,None,'hk_connect_stage8_natural_rtd_data',historical_backfill=True,universe_bindings={'HK_CONNECT':binding})
    # The original collector owns snapshot/window/aggregation. The provider here
    # is a fixed local payload boundary, not an injectable algorithm or store.
    def recorded_provider(requested,*,batch_size):
        if tuple(sorted(requested))!=tuple(sorted(active)) or batch_size!=30:raise ValueError('M08_STAGE8_CODE_SET')
        return copy.deepcopy(raw)
    result=rtdata._collect_hk_stage8_natural(plan,codes=codes,snapshot_root=generation,rtdata_provider=recorded_provider,natural_now=aware(request['source']['captured_at']))
    enrichment=payload['enrichment'];ecodes=_codes(enrichment)
    if len(ecodes)!=len(set(ecodes)) or set(ecodes)!=set(active):raise ValueError('M08_STAGE8_ENRICHMENT_CODES')
    rows=[]
    for original in result.rows:
        extra=enrichment[ecodes.index(original['code'])]
        exact_keys(extra,('code','circular_market_cap_hkd_yi'))
        _number(extra['circular_market_cap_hkd_yi'],positive=True)
        rows.append(dict(original,circular_market_cap_hkd_yi=extra['circular_market_cap_hkd_yi']))
    return rows,result


def _select(request,generation,selection,identity_sha):
    source=request['source'];rows=request['payload'].get('rows',[]);status=source['status']
    cannot=list(source['cannot_confirm']);missing=list(source['missing_symbols']);requested=source['requested_rows']
    # The original auction adapter normalizes status; preserve upstream failure
    # as original-envelope diagnostics rather than changing its ranking body.
    if status=='CANNOT_CONFIRM' and not cannot:cannot.append('SOURCE_CANNOT_CONFIRM')
    if status=='PARTIAL_WITH_ROWS' and not cannot:cannot.append('SOURCE_PARTIAL_WITH_ROWS')
    evidence=list(source['source_evidence'])+['selection_contract=V3_TOP10_RECOMMENDATION', 'm08_data_kind='+request['data_kind'], 'm08_input_sha256='+sha256_json(request), 'm08_source_manifest_sha256='+SOURCE_SHA, 'natural_verified=false','formal_admission=false']
    if request['m02']['status']=='UNKNOWN':cannot.append('M02_MEMBERSHIP_NOT_VERIFIED')
    if request['data_kind']=='RECORDED_INPUT_REPLAY':cannot.append('REPLAY_POINT_IN_TIME_QUALIFICATION_NOT_ATTESTED')
    route=request['route']
    if route=='STAGE8_RTDATA':
        rows,result=_stage8_rows(request,generation);status=result.status
        cannot+=list(result.cannot_confirm);missing+=list(result.missing_symbols);requested=result.requested_rows
        # Original owner labels describe the exercised implementation. Preserve
        # them with explicit retained-input context, never claim a natural run.
        evidence+=list(result.source_evidence)+['owner_execution=RETAINED_INPUT_ENGINEERING_REPLAY']
    kwargs=dict(source_status=status,requested_rows=requested,missing_symbols=missing,cannot_confirm=cannot,source_evidence=evidence)
    score_details={}
    if route=='SECOND_FILTER':artifact=selection.select_hk_0925_second_filter(rows,request['target_date'],identity_sha,**kwargs)
    elif route=='D1_REFERENCE':artifact=selection.select_hk_0925_d1_reference(rows,request['target_date'],identity_sha,**kwargs)
    else:
        merged=selection.merge_hk_four_lane_candidates(rows)
        score_details={row['code']:selection.hk_four_lane_score(row,request['stage_id'],100.0) for row in merged}
        artifact=selection.select_hk_four_lane(merged,request['target_date'],request['stage_id'],identity_sha,**kwargs)
    return artifact,score_details


def _atomic(path,value,selection):
    path=no_symlinks(path);selection._atomic_write_json(path,value)


def _worker(request,root):
    root=checked_root(root);selection,contracts,calendar=load_owners()
    metadata=validate_request(request,contracts,calendar)
    code=implementation_identity();identity=dict(input_sha256=sha256_json(request),source_manifest_sha256=SOURCE_SHA,implementation_identity=code,config=dict(cap_limit_yi=100,mode='RETAINED_INPUT_ONLY'))
    digest=sha256_json(identity);generations=no_symlinks(root/'generations');generations.mkdir(exist_ok=True)
    generation=no_symlinks(generations/digest)
    lock=os.open(no_symlinks(root/'.m08.lock'),os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if generation.exists():
            attempt=read_json(generation/'attempt.json')
            if attempt['status']!='SUCCEEDED':raise ValueError('M08_EXISTING_ATTEMPT_REQUIRES_EXPLICIT_REVIEW:'+attempt['status'])
            product=read_json(generation/'product.json')
            return dict(reference=product['reference'],reused=True)
        generation.mkdir();started=datetime.now(timezone.utc).isoformat()
        _atomic(generation/'attempt.json',dict(status='RUNNING',identity=identity,started_at=started,**SAFETY),selection)
        committed=False
        try:
            artifact,score_details=_select(request,generation,selection,digest)
            original_root=generation/'owner';original_root.mkdir()
            stored=selection.SelectionStore(original_root).publish(artifact,market='HK_CONNECT')
            verified=selection.SelectionStore(original_root)._verify_run(request['target_date'],request['stage_id'],'HK_CONNECT',stored['run_id'])
            if verified['envelope']!=stored:raise ValueError('M08_OWNER_READBACK')
            reference={key:verified[key] for key in ('run_id','market','stage_id','artifact_sha256','manifest_sha256','receipt_sha256')}
            reference.update(generation_sha256=digest,target_date=request['target_date'])
            provenance=dict(data_kind=request['data_kind'],**identity,source_identity=dict(request['source'],m06_run_id=request['m06']['run_id'],m06_rows_sha256=request['m06']['rows_sha256'],membership_receipt_sha256=request['m02']['receipt_sha256']),stage_contract=metadata,owner_score_details=score_details,natural_verified=False,formal_admission=False)
            product=dict(schema_version='v5.hk_stage_product.v1',reference=reference,artifact=stored,provenance=provenance,request=request,**SAFETY)
            reference=dict(reference,product_sha256=sha256_json(product))
            # Product hash is over the self-hash-free object, never circular.
            product['reference']=reference
            _atomic(generation/'product.json',product,selection)
            source_bytes()
            if implementation_identity()!=code:raise ValueError('M08_SOURCE_CHANGED_DURING_RUN')
            _atomic(generation/'attempt.json',dict(status='SUCCEEDED',identity=identity,reference=reference,started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),readback_verified=True,natural_verified=False,**SAFETY),selection)
            committed=True
            if stored['selection_status'] in ('READY','READY_EMPTY'):
                latest_path=no_symlinks(root/'latest_success.json');latest=read_json(latest_path) if latest_path.exists() else {}
                key=request['target_date']+'/'+request['stage_id'];old=latest.get(key)
                if old is None or aware(old['captured_at'])<aware(request['source']['captured_at']):
                    latest[key]=dict(reference=reference,captured_at=request['source']['captured_at'])
                    _atomic(latest_path,latest,selection)
            return dict(reference=reference,reused=False)
        except Exception as error:
            if committed:raise  # Index failure cannot uncommit the verified exact run.
            _atomic(generation/'attempt.json',dict(status='FAILED',identity=identity,started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),reason=type(error).__name__+':'+str(error),**SAFETY),selection)
            raise
    finally:os.close(lock)


def _process(script,message):
    result=subprocess.run([sys.executable,'-I','-B',str(script),'--worker'],input=canonical_bytes(message),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
    if len(result.stdout)>MAX_JSON_BYTES:raise ValueError('M08_RESPONSE_SIZE')
    try:out=json.loads(result.stdout)
    except Exception as e:raise ValueError('M08_WORKER_OUTPUT:'+result.stderr.decode(errors='replace')[-1000:]) from e
    if result.returncode:raise ValueError(out.get('reason','M08_WORKER_FAILURE'))
    return out


def run_hk_stage(request,output_root):
    """Compute once, publish by original store, then return separate-process read."""
    request=json.loads(canonical_bytes(request));root=checked_root(output_root)
    result=_process(Path(__file__).resolve(),dict(request=request,root=str(root)))
    from v5_shadow.hk_stage_reader import read_hk_stage
    out=read_hk_stage(root,result['reference'])
    return dict(out,reused=result['reused'])


def main(argv=None):
    parser=argparse.ArgumentParser(description='M08 original-owner retained-input producer; no natural/live admission')
    parser.add_argument('--worker',action='store_true');parser.add_argument('--init-root');parser.add_argument('--input');parser.add_argument('--root')
    args=parser.parse_args(argv)
    if args.worker:
        raw=sys.stdin.buffer.read(MAX_JSON_BYTES+1)
        if len(raw)>MAX_JSON_BYTES:raise ValueError('M08_INPUT_SIZE')
        message=json.loads(raw);return _worker(message['request'],message['root'])
    if args.init_root:return dict(root=init_hk_root(args.init_root))
    if not args.input or not args.root:parser.error('--input and --root are required')
    return run_hk_stage(read_json(Path(args.input).absolute()),Path(args.root).absolute())

if __name__=='__main__':
    try:print(canonical_bytes(main()).decode())
    except Exception as error:
        print(canonical_bytes(dict(status='FAILED',reason=type(error).__name__+':'+str(error))).decode());raise SystemExit(1)

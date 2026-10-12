"""Fixed-source subprocess assembly; original owner and algorithm bytes unchanged."""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

CAPSULE_SHA256='be3c369df297d0ddd6985e0c0f0aa136849a931fe6f388f7f8355f3188574c38'
REPOSITORY=Path(__file__).resolve().parents[3]
MANIFEST='integration_candidates/M10/CAPSULE_INTEGRATION_CANDIDATE/manifest.json'
FLAGS=('production_allowed','buy_gate_updated','orders_sent')


def _bytes(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


def _safe(root,relative):
    parts=relative.split('/')
    if any(p in ('','.','..') for p in parts) or '\\' in relative: raise ValueError('M10_INPUT_PATH_INVALID')
    path=Path(root).absolute().joinpath(*parts)
    if any(p.is_symlink() for p in (path,*path.parents)): raise ValueError('M10_INPUT_SYMLINK')
    return path


@contextmanager
def prepare_owner_capsule():
    source=_safe(REPOSITORY,MANIFEST); raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=CAPSULE_SHA256: raise ValueError('M10_OWNER_MANIFEST_SHA_INVALID')
    mapping=json.loads(raw)
    with tempfile.TemporaryDirectory(prefix='m10-owner-') as directory:
        root=Path(directory)
        for entry in mapping['entries']:
            data=_safe(REPOSITORY,entry['source']).read_bytes()
            blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if (hashlib.sha256(data).hexdigest()!=entry['sha256'] or blob!=entry['git_blob_sha'] or len(data)!=entry['bytes']):
                raise ValueError('M10_OWNER_SOURCE_SHA_INVALID')
            target=_safe(root,entry['destination']);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        # Empty package markers are assembly metadata, never presented as donor files.
        for name in ('ops','contracts','domains','infrastructure','stage_center','stage_center/_selection_parts'):
            (root/name/'__init__.py').write_text('')
        yield root


def run_owner(action,data_root,trade_date,stage_root,**extra):
    with prepare_owner_capsule() as capsule:
        request={'action':action,'data_root':str(Path(data_root).absolute()),'trade_date':trade_date,
                 'stage_root':str(Path(stage_root).absolute()) if stage_root else None,'capsule':str(capsule),**extra}
        result=subprocess.run([sys.executable,'-I','-S','-B',str(Path(__file__).resolve())],
                              input=json.dumps(request),text=True,capture_output=True,timeout=60)
        if result.returncode:
            try: reason=json.loads(result.stdout)['error']
            except (ValueError,KeyError): reason='M10_OWNER_PROCESS_FAILED'
            raise ValueError(reason)
        return json.loads(result.stdout)


def _copy_inputs(request,work):
    date=request['trade_date']; source=Path(request['data_root']); records={}
    def copy(root,relative,destination,*,select=None):
        path=_safe(root,relative)
        if not path.is_file():
            records[destination]=None;return None
        data=path.read_bytes()
        if len(data)>64*1024*1024: raise ValueError('M10_INPUT_SIZE_LIMIT')
        if select is not None:
            try: value=json.loads(data);data=_bytes(select(value))
            except (ValueError,TypeError,KeyError): pass  # Preserve bad evidence for the original reader.
        target=_safe(work,destination);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        records[destination]=hashlib.sha256(data).hexdigest()
        return data
    close=f'hkconnect_close_snapshots/{date}.json'
    copy(source,close,'native/'+close)
    copy(source,f'receipts/hkconnect_close_snapshots/{date}.json',f'native/receipts/hkconnect_close_snapshots/{date}.json')
    copy(source,'manifest.json','native/manifest.json',select=lambda v:{close:v[close]} if isinstance(v,dict) and close in v else {})
    pool=f'preselection_pools/{date}/'
    for suffix in ('hkconnect_d1_top100.json','receipts/hkconnect_d1_top100.json'):
        copy(source,pool+suffix,'native/'+pool+suffix)
    copy(source,pool+'manifest.json','native/'+pool+'manifest.json',select=lambda v:{'hkconnect_d1_top100':v['hkconnect_d1_top100']} if isinstance(v,dict) and 'hkconnect_d1_top100' in v else {})
    if request['stage_root']:
        from domains.close_review import _REVIEW_STAGE_IDS
        keys={date+'/'+s+'/HK_CONNECT' for s in _REVIEW_STAGE_IDS}
        def selected_latest(value):
            if isinstance(value,dict) and isinstance(value.get('entries'),dict):
                return {**value,'entries':{k:v for k,v in value['entries'].items() if k in keys}}
            return value
        latest=copy(request['stage_root'],'selection_latest.json','stages/selection_latest.json',select=selected_latest)
        if latest:
            try: value=json.loads(latest)
            except ValueError: value={}
            if not isinstance(value,dict) or not isinstance(value.get('entries',{}),dict): value={}
            for stage in _REVIEW_STAGE_IDS:
                entry=value.get('entries',{}).get(date+'/'+stage+'/HK_CONNECT',{})
                run_id=entry.get('run_id') if isinstance(entry,dict) else None
                if not isinstance(run_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',run_id): continue
                prefix=f'selection_runs/{date}/HK_CONNECT_SELECTION_{stage}/{run_id}/'
                for suffix in ('artifact.csv','manifest.json','receipt.json'):
                    copy(request['stage_root'],prefix+suffix,'stages/'+prefix+suffix)
    return records


def _execute(request):
    date=request['trade_date']
    if not isinstance(date,str) or not re.fullmatch(r'\d{8}',date): raise ValueError('M10_DATE_INVALID')
    datetime.strptime(date,'%Y%m%d')
    sys.path.insert(0,request['capsule'])
    from ops.collect_hkconnect_close_snapshot import collect_close_snapshot
    from ops.build_close_review import build_close_review,_model_rows
    from domains.close_review import _REVIEW_STAGE_IDS
    from infrastructure.hkconnect_close_store import CloseSnapshotStore
    from infrastructure.preselection_pool_store import PreselectionPoolStore
    from infrastructure.review_store import ReviewStore
    from stage_center.consumer import StageSelectionConsumer
    with tempfile.TemporaryDirectory(prefix='m10-native-') as directory:
        work=Path(directory);files=_copy_inputs(request,work);native=work/'native';stages=work/'stages'
        # Preflight exact snapshot before collector call. Missing current-day input
        # is a hard stop too; no fallback path can reach a quote SDK.
        try: snapshot,snapshot_sha=CloseSnapshotStore(native).read_snapshot(date)
        except (OSError,ValueError) as error: raise ValueError('M10_CLOSE_INPUT_UNAVAILABLE_OR_INVALID') from error
        model_error=None
        try: model=PreselectionPoolStore(native).read_pool(date,'hkconnect_d1_top100')
        except (OSError,ValueError,TypeError) as error: model={};model_error=str(error)
        responses={s:StageSelectionConsumer(stages).get(date,s,markets=('HK_CONNECT',)) for s in _REVIEW_STAGE_IDS}
        reasons=['M02_MEMBERSHIP_PIT_UNVERIFIED']
        if not _model_rows(model,date): reasons.append('M06_STRICT_INPUT_UNAVAILABLE_OR_INVALID')
        for stage,response in responses.items():
            market=response.get('markets',{}).get('HK_CONNECT',{})
            for reason in [*response.get('cannot_confirm',[]),*market.get('cannot_confirm',[])]:
                reasons.append(stage+':'+str(reason))
            status=market.get('status') or market.get('selection_status')
            if status not in ('READY','READY_EMPTY'): reasons.append(stage+':'+str(status or 'CANNOT_CONFIRM'))
        evidence={'files':files,'close_snapshot_sha256':snapshot_sha,
                  'model':{'payload':model,'error':model_error},'stages':responses,
                  'close_membership_status':'CANNOT_CONFIRM','close_membership_reason':'M02_MEMBERSHIP_PIT_UNVERIFIED'}
        code_sha=_digest({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                         (Path(__file__),Path(__file__).with_name('hk_close_daily.py'))})
        identity={'trade_date':date,'input_sha256':_digest(evidence),'owner_capsule_sha256':CAPSULE_SHA256,
                  'code_sha256':code_sha,'config_sha256':_digest({'network_collection':False,'data_kind':'RECORDED_INPUT_REPLAY',
                       'schedule':'HK_SECURITIES_TRADE_DAY/16:10','half_day':'SCHEDULE_BINDING_UNVERIFIED'}),
                  'calendar_sha256':hashlib.sha256((Path(request['capsule'])/'contracts/market_calendar_2026.json').read_bytes()).hexdigest()}
        if request['action']=='inspect': return {'identity':identity,'input_evidence':evidence}
        if identity!=request.get('expected_identity'): raise ValueError('M10_INPUT_CHANGED_DURING_BUILD')
        previous=request.get('previous_review')
        if previous:
            if _digest(previous)!=request.get('expected_native_sha256'): raise ValueError('M10_NATIVE_CAS_CONFLICT')
            ReviewStore(native).publish_native(previous,expected_sha256=None)
        elif request.get('expected_native_sha256') is not None: raise ValueError('M10_NATIVE_CAS_CONFLICT')
        collected=collect_close_snapshot(date,data_root=native)
        if collected['publication'].get('status')!='IDEMPOTENT_REUSE': raise ValueError('M10_COLLECTION_NOT_REUSE')
        built=build_close_review(native,date,stage_selection_root=stages)
        readback=ReviewStore(native).read_reference(date)
        if readback!=built['review']: raise ValueError('M10_NATIVE_READBACK_MISMATCH')
        if built['publication'].get('previous_sha256')!=(request.get('expected_native_sha256') or ''):
            raise ValueError('M10_NATIVE_CAS_PUBLICATION_MISMATCH')
        receipt=json.loads((native/f'receipts/close_reviews/{date}.json').read_text())
        manifest=json.loads((native/'manifest.json').read_text())
        return {**built,'identity':identity,'input_evidence':evidence,'cannot_confirm':sorted(set(reasons)),
                'native_evidence':{'manifest':manifest,'receipt':receipt,'collector_publication':collected['publication']}}


if __name__=='__main__':
    try: print(json.dumps(_execute(json.load(sys.stdin)),ensure_ascii=False,sort_keys=True))
    except Exception as error:
        print(json.dumps({'error':str(error) if str(error).startswith('M10_') else 'M10_OWNER_'+type(error).__name__}))
        sys.exit(1)

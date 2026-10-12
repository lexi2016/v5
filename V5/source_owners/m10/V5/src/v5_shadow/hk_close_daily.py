"""M10 offline default owner -> immutable publication -> cold readback.

No network collection or service start. Native source inputs are copied into a
private workspace, and the frozen original collector takes its reuse path.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

SCHEMA = 'v5.hk_close_daily.v4.2'
DAILY_SCHEMA = 'v5.hk_close_daily.envelope.v1'


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


def _path(root, relative):
    root = Path(root).absolute()
    parts = relative.split('/')
    if not relative or any(p in ('', '.', '..') for p in parts) or '\\' in relative:
        raise ValueError('M10_PATH_INVALID')
    target = root.joinpath(*parts)
    if any(p.is_symlink() for p in (target, *target.parents)):
        raise ValueError('M10_SYMLINK_FORBIDDEN')
    return target


def _run_path(root, run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', run_id):
        raise ValueError('M10_RUN_ID_INVALID')
    return _path(root, run_id)


def _read(root, relative):
    return json.loads(_path(root, relative).read_text(encoding='utf-8'))


def _write(path, value):
    path = Path(path)
    _path(path.parent, path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name('.' + path.name + '.' + uuid4().hex)
    with temp.open('xb') as stream:
        stream.write(_bytes(value)); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)


@dataclass(frozen=True)
class CloseReviewReceipt:
    run_id: str
    payload_sha256: str
    manifest_sha256: str
    publication_sha256: str


class HKCloseReviewReader:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def read(self, run_id: str):
        return self._read_run(run_id, require_commit=True)

    def _read_run(self, run_id, *, require_commit=False):
        target = _run_path(self.root, run_id)
        payload = _read(target, 'payload.json')
        publication = _read(target, 'publication.json')
        manifest = _read(target, 'manifest.json')
        receipt = _read(target, 'receipt.json')
        if manifest.get('schema') != SCHEMA or manifest.get('run_id') != run_id or receipt.get('run_id') != run_id:
            raise ValueError('M10_RUN_IDENTITY_INVALID')
        if manifest.get('payload_sha256') != _digest(payload):
            raise ValueError('M10_PAYLOAD_SHA_INVALID')
        if manifest.get('publication_sha256') != _digest(publication):
            raise ValueError('M10_PUBLICATION_SHA_INVALID')
        if receipt.get('manifest_sha256') != _digest(manifest):
            raise ValueError('M10_MANIFEST_SHA_INVALID')
        if receipt.get('publication_sha256') != _digest(publication):
            raise ValueError('M10_RECEIPT_PUBLICATION_INVALID')
        if receipt.get('payload_sha256') != _digest(payload):
            raise ValueError('M10_RECEIPT_PAYLOAD_INVALID')
        if payload.get('schema') == DAILY_SCHEMA:
            identity = payload['identity']
            if payload.get('run_id') != run_id or run_id != identity['trade_date'] + '-' + _digest(identity)[:24]:
                raise ValueError('M10_INPUT_IDENTITY_INVALID')
            review = payload['review']; date = identity['trade_date']
            relative = 'close_reviews/' + date + '.json'
            receipt_relative = 'receipts/close_reviews/' + date + '.json'
            native = payload['native_evidence']
            if (review.get('trade_date') != date or publication.get('payload_path') != relative
                    or publication.get('receipt_path') != receipt_relative
                    or publication.get('sha256') != _digest(review)
                    or publication.get('previous_sha256') != (payload.get('previous_native_sha256') or '')
                    or native.get('manifest', {}).get(relative) != _digest(review)
                    or native.get('receipt') != {'schema_version':'v3_import_receipt.v1', 'payload_path':relative,
                                                'source_sha256':_digest(review), 'trade_date':date}
                    or _digest(payload['input_evidence']) != identity.get('input_sha256')
                    or any(review.get(k) is not False for k in ('production_allowed','buy_gate_updated','orders_sent'))):
                raise ValueError('M10_NATIVE_PUBLICATION_IDENTITY_INVALID')
        if require_commit:
            pointer = _path(self.root, 'latest_success.json')
            latest = _read(self.root, 'latest_success.json') if pointer.exists() else {}
            if latest.get('committed_runs', {}).get(run_id) != _digest(receipt):
                raise ValueError('M10_RUN_NOT_COMMITTED')
        return payload

    def latest_identity(self):
        path = _path(self.root, 'latest_success.json')
        if not path.exists():
            return None
        latest = _read(self.root, 'latest_success.json')
        payload = self.read(latest['run_id'])
        receipt = _read(_run_path(self.root, latest['run_id']), 'receipt.json')
        if (latest.get('run_id') != receipt['run_id'] or latest.get('generation') != _digest(receipt)
                or not isinstance(latest.get('committed_runs'), dict)):
            raise ValueError('M10_LATEST_IDENTITY_INVALID')
        return latest

    def read_latest(self):
        latest = self.latest_identity()
        if latest is None:
            raise FileNotFoundError('M10_NO_LATEST_SUCCESS')
        return self.read(latest['run_id'])


class HKCloseReviewStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        _path(self.root, '.publish.lock')
        self.root.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def lock(self):
        with _path(self.root, '.publish.lock').open('a+b') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def publish(self, run_id: str, payload: dict, publication: dict, *, expected_generation=None):
        with self.lock():
            return self._publish(run_id, payload, publication, expected_generation)

    def _publish(self, run_id, payload, publication, expected_generation):
        target = _run_path(self.root, run_id)
        payload_sha = _digest(payload); publication_sha = _digest(publication)
        reader = HKCloseReviewReader(self.root)
        latest = reader.latest_identity()
        receipt = None
        if target.exists():
            old = reader._read_run(run_id)
            receipt = _read(target, 'receipt.json')
            if _digest(old) != payload_sha or receipt['publication_sha256'] != publication_sha:
                raise ValueError('M10_RUN_ID_CONFLICT')
            if latest and latest['committed_runs'].get(run_id) == _digest(receipt):
                return CloseReviewReceipt(**receipt)
            if _read(target, 'manifest.json').get('previous_generation') != expected_generation:
                raise ValueError('M10_ORPHAN_PARENT_CAS_CONFLICT')
        if (latest['generation'] if latest else None) != expected_generation:
            raise ValueError('M10_GENERATION_CAS_CONFLICT')
        manifest = {'schema':SCHEMA,'run_id':run_id,'payload_sha256':payload_sha,'publication_sha256':publication_sha, 'previous_generation':expected_generation}
        receipt = {'run_id':run_id,'payload_sha256':payload_sha,'manifest_sha256':_digest(manifest),'publication_sha256':publication_sha}
        # Completed orphan directories remain uncommitted until this atomic pointer.
        if not target.exists():
            with tempfile.TemporaryDirectory(prefix='.pending-', dir=self.root) as staging:
                staged = Path(staging)/run_id; staged.mkdir()
                for name, value in (('payload',payload),('publication',publication),('manifest',manifest),('receipt',receipt)):
                    _write(staged/(name+'.json'), value)
                HKCloseReviewReader(staging)._read_run(run_id)
                os.rename(staged, target)
        committed = dict(latest['committed_runs']) if latest else {}
        committed[run_id] = _digest(receipt)
        _write(self.root/'latest_success.json', {'run_id':run_id,'generation':_digest(receipt), 'committed_runs':committed})
        return CloseReviewReceipt(**receipt)

    def failed_attempt(self, trade_date, error):
        # Deliberately no host path, credential, payload or traceback in persisted evidence.
        _write(self.root/'attempts'/(uuid4().hex+'.json'), {'trade_date':trade_date,'status':'FAILED',
                'reason':str(error) if str(error).startswith('M10_') else type(error).__name__,
                'production_allowed':False,'buy_gate_updated':False,'orders_sent':False})


@contextmanager
def prepare_owner_capsule():
    from .hk_close_owner import prepare_owner_capsule as prepare
    with prepare() as root:
        yield root


def build_default_hk_close_review(*, data_root: Path, trade_date: str, run_root: Path,
                                  stage_selection_root: Path | str | None = None,
                                  expected_generation=None, expected_native_sha256=None):
    """Execute frozen owners on copied, recorded inputs; never contacts a provider.

    Both expected values must match latest success. Exact identity reuse is a
    read-only fast path after input inspection and never recomputes/publishes.
    """
    from .hk_close_owner import run_owner
    destination = Path(run_root).resolve()
    for input_root in (data_root, stage_selection_root):
        if input_root is not None:
            source = Path(input_root).resolve()
            if destination.is_relative_to(source) or source.is_relative_to(destination):
                raise ValueError('M10_ROOT_OVERLAP')
    store = HKCloseReviewStore(run_root)
    try:
        with store.lock():
            reader = HKCloseReviewReader(run_root)
            latest = reader.latest_identity()
            previous = reader.read_latest() if latest else None
            prepared = run_owner('inspect', data_root, trade_date, stage_selection_root)
            identity = prepared['identity']; run_id = trade_date+'-'+_digest(identity)[:24]
            if latest and run_id in latest['committed_runs']:
                return reader.read(run_id)
            if (latest['generation'] if latest else None) != expected_generation:
                raise ValueError('M10_GENERATION_CAS_CONFLICT')
            previous_review = previous['review'] if previous else None
            native_sha = _digest(previous_review) if previous_review and previous_review.get('trade_date') == trade_date else None
            if native_sha != expected_native_sha256:
                raise ValueError('M10_NATIVE_CAS_CONFLICT')
            if _run_path(run_root, run_id).exists():
                orphan = reader._read_run(run_id)
                publication = _read(_run_path(run_root, run_id), 'publication.json')
                if publication.get('previous_sha256') != (native_sha or ''):
                    raise ValueError('M10_NATIVE_CAS_CONFLICT')
                store._publish(run_id, orphan, publication, expected_generation)
                return reader.read(run_id)
            built = run_owner('build', data_root, trade_date, stage_selection_root,
                              previous_review=previous_review if native_sha else None,
                              expected_identity=identity, expected_native_sha256=native_sha)
            payload = {'schema':DAILY_SCHEMA,'run_id':run_id,'identity':identity,
                       'data_kind':'RECORDED_INPUT_REPLAY','review':built['review'],
                       'input_evidence':built['input_evidence'],'native_evidence':built['native_evidence'],
                       'cannot_confirm':built['cannot_confirm'], 'natural_admission':'UNVERIFIED',
                       'previous_native_sha256':native_sha}
            store._publish(run_id,payload,built['publication'],expected_generation)
            return reader.read(run_id)
    except Exception as error:
        store.failed_attempt(trade_date, error)
        raise


def read_hk_close_projection(run_root, run_id=None):
    """Read-only API/scheduler integration seam. Calling it never invokes owners."""
    reader=HKCloseReviewReader(run_root)
    payload = reader.read(run_id) if run_id else reader.read_latest()
    if payload.get('schema') != DAILY_SCHEMA:
        return payload
    # Preserve original native review for digest/audit; apply evidence semantics
    # only in this read-only UI projection.
    result = json.loads(json.dumps(payload))
    review = result['review']
    model_known = review['models']['0.2_prob_active']['evidence_status'] == 'READY'
    stage_known = True
    for stage, response in payload['input_evidence']['stages'].items():
        market = response.get('markets', {}).get('HK_CONNECT', {})
        status = market.get('status') or market.get('selection_status')
        reasons = list(dict.fromkeys([*response.get('cannot_confirm', []), *market.get('cannot_confirm', [])]))
        metric = review['stages'][stage]
        metric['source_status'] = status
        metric['cannot_confirm'] = reasons
        if status not in ('READY', 'READY_EMPTY'):
            stage_known = False
            metric['evidence_status'] = 'PARTIAL' if status == 'PARTIAL_WITH_ROWS' else 'CANNOT_CONFIRM'
            for key in ('hit_count', 'coverage', 'precision', 'coverage_pct', 'precision_pct'):
                metric[key] = None
    if not stage_known:
        review['stage_union']['evidence_status'] = 'CANNOT_CONFIRM'
        for key in ('hit_count','coverage','precision','coverage_pct','precision_pct'):
            review['stage_union'][key] = None
        review['kpi']['stage_union_close_top20_hits'] = None
    for row in review['top20_attribution']:
        if not model_known: row['model_0_2_hit'] = None
        if not stage_known: row['stage_union_hit'] = None
        if not model_known or not stage_known: row['classification'] = 'CANNOT_CONFIRM'
    review['cannot_confirm'] = sorted(set(review['cannot_confirm'] + payload['cannot_confirm']))
    review['source_status'] = review['status']
    review['status'] = 'PARTIAL' if review['cannot_confirm'] else review['status']
    review['evidence_mode'] = payload['data_kind']
    result['native_review_sha256'] = _digest(payload['review'])
    result['generation'] = _digest(_read(_run_path(run_root, payload['run_id']), 'receipt.json'))
    return result


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description='M10 isolated recorded-input replay / cold reader')
    parser.add_argument('action', choices=('build','read'))
    parser.add_argument('--run-root', required=True, type=Path)
    parser.add_argument('--data-root',type=Path);parser.add_argument('--date')
    parser.add_argument('--stage-selection-root',type=Path)
    parser.add_argument('--expected-generation');parser.add_argument('--expected-native-sha256')
    args=parser.parse_args()
    if args.action=='build':
        if args.data_root is None or not args.date: parser.error('build requires --data-root and --date')
        result=build_default_hk_close_review(data_root=args.data_root,trade_date=args.date,run_root=args.run_root,
            stage_selection_root=args.stage_selection_root,expected_generation=args.expected_generation,
            expected_native_sha256=args.expected_native_sha256)
    else: result=read_hk_close_projection(args.run_root)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))

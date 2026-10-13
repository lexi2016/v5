"""M04 explicit captured-input owner bridge. No fetch, scheduler, or HTTP writes.

Resume only a fully checkpointed original builder result. A partial builder stays
blocked by its existing exclusive slot guard. Import retries get fresh roots;
completed references are checked by the independent original archive reader.
"""
import sys
from pathlib import Path
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fcntl
import hashlib
import json
import os
import uuid
from v5_shadow.archive_builder_v1 import run_build, builder_identity
from v5_shadow.archive_article_v2 import run_import
from v5_shadow.archive_reader import read_private, article_v2_identity
from v5_shadow.current_us_research import _raw_file
from v5_shadow.digests import canonical_bytes, sha256_json, MAX_JSON_BYTES

FIELDS = {'capture_root', 'capture_files', 'receipt', 'status', 'state_root'}
SAFETY = dict(natural_verified=False, historical_pit_claimed=False,
              production_allowed=False, buy_gate_updated=False, orders_sent=False)


def _root(value):
    root = Path(value)
    if (not root.is_absolute() or '..' in root.parts or not root.is_dir()
            or any(p.is_symlink() for p in (root, *root.parents))):
        raise ValueError('INGEST_PRIVATE_ROOT')
    return root


def _write(path, value, *, immutable=False):
    raw = canonical_bytes(value)
    if immutable:
        with path.open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    else:
        pending = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
        with pending.open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(pending, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _json(path):
    if path.is_symlink() or path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError('INGEST_CHECKPOINT_PATH_OR_SIZE')
    return json.loads(path.read_bytes())


def cold_read(binding):
    if not isinstance(binding, dict) or set(binding) != {'root', 'files'}:
        raise ValueError('INGEST_BINDING_FIELDS')
    return read_private(_root(binding['root']), binding)


def _verify_success(result):
    if (result.get('status') != 'SUCCEEDED'
            or any(result.get(key) is not value for key, value in SAFETY.items())):
        raise ValueError('INGEST_SUCCESS_SAFETY')
    records = cold_read(result['archive_binding'])['records']
    articles = []
    for record in records.values():
        if record.get('error'):
            raise ValueError('INGEST_READER_REJECTED:' + str(record['error']))
        if record.get('payload'):
            articles.extend(record['payload'].get('articles', []))
    ids = [article['article_id'] for article in articles]
    if ids != result['article_ids'] or len(ids) != result['article_count']:
        raise ValueError('INGEST_SUCCESS_READBACK')
    return result


def run(request):
    if not isinstance(request, dict) or set(request) != FIELDS:
        raise ValueError('INGEST_REQUEST_FIELDS')
    if len(canonical_bytes(request)) > MAX_JSON_BYTES:
        raise ValueError('INGEST_REQUEST_SIZE')
    capture = _root(request['capture_root']); state = _root(request['state_root'])
    if capture == state or capture in state.parents or state in capture.parents:
        raise ValueError('INGEST_ROOT_OVERLAP')
    try:
        marked = _raw_file(state, '.v5-research-ingest') == b'v5.research-ingest.v1\n'
    except FileNotFoundError:
        marked = False
    if not marked:
        raise ValueError('INGEST_STATE_MARKER')
    if _raw_file(capture, '.v5-archive-acquisition') != b'v5.archive-acquisition.v2\n':
        raise ValueError('INGEST_CAPTURE_MARKER')
    # Input bytes must still match even when a completed request is reused.
    files = request['capture_files']
    if not isinstance(files, dict) or not files or len(files) > 500:
        raise ValueError('INGEST_CAPTURE_FILES')
    for name, digest in files.items():
        if hashlib.sha256(_raw_file(capture, name)).hexdigest() != digest:
            raise ValueError('INGEST_CAPTURE_CHANGED')
    code = dict(builder=builder_identity(), article=article_v2_identity(),
                bridge=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    identity = sha256_json(dict(request=request, code=code))
    lock_path = state/'writer.lock'
    if lock_path.is_symlink():
        raise ValueError('INGEST_LOCK_PATH')
    descriptor = os.open(lock_path, os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'r+b') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('INGEST_WRITER_BUSY') from exc
        runs = state/'runs'; runs.mkdir(exist_ok=True)
        if runs.is_symlink():
            raise ValueError('INGEST_STATE_PATH')
        root = runs/identity; root.mkdir(exist_ok=True)
        if root.is_symlink():
            raise ValueError('INGEST_STATE_PATH')
        success = root/'success.json'
        if success.exists():
            result = _json(success)
            if result['request_sha256'] != identity or result['code'] != code:
                raise ValueError('INGEST_SUCCESS_IDENTITY')
            return _verify_success(result)
        attempt = dict(schema_version='v5.research_ingest_attempt.v1',
                       request_sha256=identity, status='RUNNING', **SAFETY)
        _write(state/'latest_attempt.json', attempt)
        try:
            builder_path = root/'builder.json'
            if builder_path.exists():
                built = _json(builder_path)
            else:
                built = run_build({k:request[k] for k in ('capture_root','capture_files','receipt','status')})
                _write(builder_path, built, immutable=True)
            # The unchanged import owner fully verifies source, clocks, owner
            # replay, acquisition receipt and every capture byte on each retry.
            imports = root/'imports'; imports.mkdir(exist_ok=True)
            if imports.is_symlink():
                raise ValueError('INGEST_IMPORT_PATH')
            output = imports/uuid.uuid4().hex; output.mkdir(mode=0o700)
            (output/'.v5-archive-article-v2').write_bytes(b'v5.archive-article.v2\n')
            import_request = {k:built[k] for k in
                              ('capture_root','capture_files','receipt','archive_v1','builder_source','builder_receipt')}
            if built['capture_root'] != request['capture_root'] or built['receipt'] != request['receipt']:
                raise ValueError('INGEST_BUILDER_IDENTITY')
            import_request['output_root'] = str(output)
            imported = run_import(import_request)
            readback = cold_read(imported['archive_binding'])
            articles = []
            for record in readback['records'].values():
                if record.get('error'):
                    raise ValueError('INGEST_READER_REJECTED:' + str(record['error']))
                if record.get('payload'):
                    articles.extend(record['payload'].get('articles', []))
            result = dict(schema_version='v5.research_ingest_result.v1', status='SUCCEEDED',
                          request_sha256=identity, code=code, archive_binding=imported['archive_binding'],
                          article_ids=[a['article_id'] for a in articles], article_count=len(articles),
                          **SAFETY)
            _write(success, result, immutable=True)
            _write(state/'latest_success.json', result)
            _write(state/'latest_attempt.json', dict(attempt,status='SUCCEEDED'))
            return result
        except Exception as exc:
            _write(state/'latest_attempt.json', dict(attempt,status='FAILED',reason=type(exc).__name__+':'+str(exc)))
            raise


def main():
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in {'run','read'}:
            raise ValueError('USAGE: research_ingest_daily run|read; JSON on stdin')
        raw = sys.stdin.buffer.read(MAX_JSON_BYTES+1)
        if len(raw) > MAX_JSON_BYTES:
            raise ValueError('INGEST_REQUEST_SIZE')
        request = json.loads(raw)
        print(canonical_bytes(run(request) if sys.argv[1]=='run' else cold_read(request)).decode())
    except Exception as exc:
        print(json.dumps({'status':'FAILED','reason':type(exc).__name__+':'+str(exc),**SAFETY}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

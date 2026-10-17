"""Bounded local manager IPC; no API/archive/global budget changes.

Control <=64 KiB, each chunk <=1 MiB, full response/saved file <=64 MiB.
The wire digest covers the complete response BEFORE parent receipt attachment.
Saved semantic SHA excludes only the saved product's top-level sha256 field.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import select
import stat
import struct
import subprocess
import tempfile
import time
from v5_shadow.digests import canonical_bytes, sha256_json
from v5_shadow.module_api import _open_directory

RESULT_BYTES = 64 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024
CONTROL_BYTES = 64 * 1024
STDERR_BYTES = 64 * 1024
MAGIC = b'V5MR1\n'

# Closed disclosure vocabulary. Unknown owner exceptions become the generic code;
# uppercase/underscore shape alone is never authorization to disclose a message.
OWNER_ERROR_CODES = frozenset(('MANAGER_INPUT_SHA_OR_LIMIT', 'SYMLINK_REJECTED'))
ERROR_CODES = frozenset((
    'LOCAL_MANAGER_WORKER_FAILED',
    'LOCAL_RESULT_CHUNK_COUNT_LIMIT',
    'LOCAL_RESULT_CHUNK_HASH',
    'LOCAL_RESULT_CHUNK_LIMIT',
    'LOCAL_RESULT_CHUNK_ORDER',
    'LOCAL_RESULT_COMPLETE_HASH',
    'LOCAL_RESULT_CONTROL_LIMIT',
    'LOCAL_RESULT_CONTROL_TYPE',
    'LOCAL_RESULT_DIRECTORY',
    'LOCAL_RESULT_ERROR_SCHEMA',
    'LOCAL_RESULT_FILE_CHANGED',
    'LOCAL_RESULT_FILE_LIMIT',
    'LOCAL_RESULT_FILE_TYPE',
    'LOCAL_RESULT_JSON_CYCLE',
    'LOCAL_RESULT_JSON_DEPTH',
    'LOCAL_RESULT_JSON_TYPE',
    'LOCAL_RESULT_LATEST_CHANGED',
    'LOCAL_RESULT_PROTOCOL',
    'LOCAL_RESULT_REQUEST_IDENTITY',
    'LOCAL_RESULT_RUN',
    'LOCAL_RESULT_SAVED_BINDING',
    'LOCAL_RESULT_SAVED_IDENTITY',
    'LOCAL_RESULT_SAVED_RUN_REQUIRED',
    'LOCAL_RESULT_STDERR_LIMIT',
    'LOCAL_RESULT_TARGET',
    'LOCAL_RESULT_TIMEOUT',
    'LOCAL_RESULT_TOTAL_LIMIT',
    'LOCAL_RESULT_TRAILING_BYTES',
    'LOCAL_RESULT_TRUNCATED',
    'LOCAL_RESULT_WORKER_EXIT',
    'MANAGER_INPUT_SHA_OR_LIMIT',
    'SYMLINK_REJECTED',
))
ERROR_STAGES = frozenset(('transport', 'assemble', 'exact_saved_readback', 'encode_result'))
ERROR_FIELDS = frozenset(('code', 'stage', 'actual_bytes', 'allowed_bytes', 'saved'))


def _saved_schema(saved):
    if saved is None:
        return True
    if not isinstance(saved, dict) or not saved or not set(saved) <= {
            'run_id', 'target_date', 'relative', 'plan_sha256', 'raw_sha256', 'bytes'}:
        return False
    patterns = {'run_id': r'[0-9a-f]{32}', 'target_date': r'[0-9]{8}',
                'plan_sha256': r'[0-9a-f]{64}', 'raw_sha256': r'[0-9a-f]{64}',
                'relative': r'(?:current_recovery/)?workspace_plans/[0-9]{8}/[0-9a-f]{32}\.json'}
    for key, value in saved.items():
        if key == 'bytes':
            if type(value) is not int or not 0 <= value <= RESULT_BYTES:
                return False
        elif not isinstance(value, str) or len(value) > 128 or not re.fullmatch(patterns[key], value):
            return False
    if 'relative' in saved:
        parts = saved['relative'].split('/')
        if saved.get('run_id') != parts[-1][:-5] or saved.get('target_date') != parts[-2]:
            return False
    return 'run_id' in saved


def _diagnostic_schema(value):
    return (isinstance(value, dict) and set(value) == ERROR_FIELDS
            and isinstance(value['code'], str) and value['code'] in ERROR_CODES
            and isinstance(value['stage'], str) and value['stage'] in ERROR_STAGES
            and all(value[key] is None or (type(value[key]) is int and 0 <= value[key] <= 2**63-1)
                    for key in ('actual_bytes', 'allowed_bytes'))
            and _saved_schema(value['saved']))


class ResultTransportError(ValueError):
    def __init__(self, code, *, stage='transport', actual_bytes=None, allowed_bytes=None, saved=None):
        self.diagnostic = dict(code=code, stage=stage, actual_bytes=actual_bytes,
                               allowed_bytes=allowed_bytes, saved=saved)
        super().__init__(code)


def _fail(code, **fields):
    raise ResultTransportError(code, **fields)


def _check_deadline(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        _fail('LOCAL_RESULT_TIMEOUT')


def _pieces(value):
    """Canonical JSON with budget checks before bounded string token encoding.

    JSONEncoder.iterencode still allocates a complete escaped string token.
    Encode string fragments instead; charge every byte before yielding it.
    """
    total = 0
    active = set()
    def charge(piece):
        nonlocal total
        total += len(piece)
        if total > RESULT_BYTES:
            _fail('LOCAL_RESULT_TOTAL_LIMIT', stage='encode_result',
                  actual_bytes=total, allowed_bytes=RESULT_BYTES)
        return piece
    def lower_bound(size):
        if size > RESULT_BYTES - total:
            _fail('LOCAL_RESULT_TOTAL_LIMIT', stage='encode_result',
                  actual_bytes=total + size, allowed_bytes=RESULT_BYTES)
    def string(text):
        # Each character needs at least one UTF-8 byte. Check before any copy.
        lower_bound(len(text) + 2)
        yield charge(b'"')
        for offset in range(0, len(text), 16384):
            token = json.dumps(text[offset:offset + 16384], ensure_ascii=False)
            yield charge(token[1:-1].encode('utf-8'))
        yield charge(b'"')
    def encode(item, depth=0):
        if depth > 128:
            _fail('LOCAL_RESULT_JSON_DEPTH')
        if isinstance(item, str):
            yield from string(item)
        elif item is None or type(item) in (bool, int, float):
            if type(item) is int:
                # Conservative decimal-length lower bound, before conversion.
                lower_bound(max(1, (item.bit_length() - 1) * 3 // 10))
            yield charge(json.dumps(item, allow_nan=False).encode('ascii'))
        elif isinstance(item, (dict, list, tuple)):
            lower_bound(len(item) + 2)
            if id(item) in active:
                _fail('LOCAL_RESULT_JSON_CYCLE')
            active.add(id(item))
            try:
                mapping = isinstance(item, dict)
                if mapping and any(not isinstance(key, str) for key in item):
                    _fail('LOCAL_RESULT_JSON_TYPE')
                yield charge(b'{' if mapping else b'[')
                for index, key in enumerate(sorted(item) if mapping else item):
                    if index:
                        yield charge(b',')
                    if mapping:
                        yield from string(key)
                        yield charge(b':')
                    yield from encode(item[key] if mapping else key, depth + 1)
                yield charge(b'}' if mapping else b']')
            finally:
                active.remove(id(item))
        else:
            _fail('LOCAL_RESULT_JSON_TYPE')
    yield from encode(value)


def _digest(value, deadline=None):
    digest = hashlib.sha256()
    for piece in _pieces(value):
        _check_deadline(deadline)
        digest.update(piece)
    _check_deadline(deadline)
    return digest.hexdigest()


def _file(path, deadline=None):
    _check_deadline(deadline)
    parent = _open_directory(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            _fail('LOCAL_RESULT_FILE_TYPE')
        if before.st_size > RESULT_BYTES:
            _fail('LOCAL_RESULT_FILE_LIMIT', actual_bytes=before.st_size, allowed_bytes=RESULT_BYTES)
        raw = bytearray()
        while True:
            _check_deadline(deadline)
            part = os.read(fd, min(CHUNK_BYTES, RESULT_BYTES + 1 - len(raw)))
            if not part:
                break
            raw.extend(part)
            if len(raw) > RESULT_BYTES:
                _fail('LOCAL_RESULT_FILE_LIMIT', actual_bytes=len(raw), allowed_bytes=RESULT_BYTES)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            _fail('LOCAL_RESULT_FILE_CHANGED')
        _check_deadline(deadline)
        return bytes(raw)
    finally:
        os.close(fd)


def saved_identity(result, request, deadline=None):
    _check_deadline(deadline)
    readback = result.get('readback') or {}
    product = result.get('payload', {}).get('plan_product') or {}
    if product.get('consumed') is not True and request['action'] == 'read':
        # Original legacy missing-journal preview is NOT a saved success.
        return None
    run = readback.get('run_id')
    if run is None:
        if product.get('consumed') is True or request['action'] == 'refresh':
            _fail('LOCAL_RESULT_SAVED_RUN_REQUIRED')
        return None
    if not isinstance(run, str) or not re.fullmatch('[0-9a-f]{32}', run):
        _fail('LOCAL_RESULT_RUN')
    scope = readback.get('store_relative')
    if scope not in ('.', 'current_recovery'):
        _fail('LOCAL_RESULT_DIRECTORY')
    root = Path(request['manager_output_root'])
    relative = Path(scope) / 'workspace_plans' / request['target_date'] / (run + '.json')
    raw = _file(root / relative, deadline)
    _check_deadline(deadline)
    saved = json.loads(raw)
    _check_deadline(deadline)
    expected = readback.get('plan_sha256')
    if (saved.get('run_id') != run or saved.get('target_trade_date') != request['target_date']
            or saved.get('sha256') != expected or product.get('run_id') != run
            or product.get('sha256') != expected or product.get('consumed') is not True
            or saved.get('input_identity') != readback.get('input_identity')
            or _digest({k: v for k, v in saved.items() if k != 'sha256'}, deadline) != expected):
        _fail('LOCAL_RESULT_SAVED_IDENTITY')
    # History may select an earlier qualified exact run. Only the original
    # reader's historical branch supplies this selection identity. Recovery
    # and dynamic reads retain their existing latest race check.
    historical = (request['action'] == 'read' and request.get('view') in ('historical', 'auto')
                  and scope == '.' and readback.get('selection_mode') == 'HISTORICAL_AS_OF'
                  and result['payload'].get('read_context', {}).get('mode') == 'HISTORICAL_AS_OF')
    if not historical and _file((root / relative).with_name('latest.json'), deadline) != raw:
        _fail('LOCAL_RESULT_LATEST_CHANGED')
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    _check_deadline(deadline)
    return dict(run_id=run, target_date=request['target_date'], relative=str(relative),
                plan_sha256=expected, raw_sha256=raw_sha256, bytes=len(raw))


def _control(stream, value):
    raw = canonical_bytes(value)
    if len(raw) > CONTROL_BYTES:
        _fail('LOCAL_RESULT_CONTROL_LIMIT', actual_bytes=len(raw), allowed_bytes=CONTROL_BYTES)
    stream.write(struct.pack('!I', len(raw)))
    stream.write(raw)


def write_result(stream, result, request):
    try:
        saved = saved_identity(result, request)
    except Exception as error:
        write_failure(stream, error)
        raise
    stream.write(MAGIC)
    _control(stream, dict(kind='start', request_sha256=sha256_json(request),
                         output_root=request['manager_output_root'], target_date=request['target_date'], saved=saved))
    digest = hashlib.sha256(); total = 0; index = 0; buffer = bytearray()
    def emit(data):
        nonlocal total, index
        total += len(data)
        if total > RESULT_BYTES:
            _fail('LOCAL_RESULT_TOTAL_LIMIT', stage='encode_result', actual_bytes=total,
                  allowed_bytes=RESULT_BYTES, saved=saved)
        digest.update(data)
        _control(stream, dict(kind='chunk', index=index, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
        stream.write(data); index += 1
    try:
        for piece in _pieces(result):
            buffer.extend(piece)
            while len(buffer) >= CHUNK_BYTES:
                emit(bytes(buffer[:CHUNK_BYTES])); del buffer[:CHUNK_BYTES]
        if buffer:
            emit(bytes(buffer))
        _control(stream, dict(kind='end', count=index, bytes=total, sha256=digest.hexdigest()))
        stream.flush()
    except ResultTransportError as error:
        error.diagnostic['saved'] = saved
        _control(stream, dict(kind='error', **error.diagnostic)); stream.flush()
        raise


def write_failure(stream, error, context=None):
    # Used only before result framing starts. No exception message/body leaks.
    stream.write(MAGIC)
    owner_code = (error.args[0] if type(error) is ValueError and len(error.args) == 1
                  and isinstance(error.args[0], str) and error.args[0] in OWNER_ERROR_CODES
                  else 'LOCAL_MANAGER_WORKER_FAILED')
    diagnostic = (dict(error.diagnostic) if isinstance(error, ResultTransportError) else
                  dict(code=owner_code, stage='assemble', actual_bytes=None,
                       allowed_bytes=RESULT_BYTES, saved=None))
    if context:
        diagnostic = {**diagnostic, 'stage': context.get('stage', diagnostic['stage']),
                      'saved': diagnostic.get('saved') or context.get('saved')}
    if not _diagnostic_schema(diagnostic):
        diagnostic = dict(code='LOCAL_RESULT_ERROR_SCHEMA', stage='transport',
                          actual_bytes=None, allowed_bytes=None, saved=None)
    _control(stream, dict(kind='error', **diagnostic)); stream.flush()


def _exact(stream, count):
    result = bytearray()
    while len(result) < count:
        part = stream.read(min(count - len(result), CHUNK_BYTES))
        if not part:
            _fail('LOCAL_RESULT_TRUNCATED')
        result.extend(part)
    return bytes(result)


def _read_control(stream):
    size = struct.unpack('!I', _exact(stream, 4))[0]
    if not 0 < size <= CONTROL_BYTES:
        _fail('LOCAL_RESULT_CONTROL_LIMIT', actual_bytes=size, allowed_bytes=CONTROL_BYTES)
    value = json.loads(_exact(stream, size))
    if not isinstance(value, dict):
        _fail('LOCAL_RESULT_CONTROL_TYPE')
    if value.get('kind') == 'error':
        diagnostic = {k: v for k, v in value.items() if k != 'kind'}
        if not _diagnostic_schema(diagnostic):
            _fail('LOCAL_RESULT_ERROR_SCHEMA')
        _fail(**diagnostic)
    return value


def read_result(stream, request, deadline=None):
    _check_deadline(deadline)
    if _exact(stream, len(MAGIC)) != MAGIC:
        _fail('LOCAL_RESULT_PROTOCOL')
    start = _read_control(stream)
    if (set(start) != {'kind','request_sha256','output_root','target_date','saved'} or start['kind'] != 'start'
            or start['request_sha256'] != sha256_json(request) or start['output_root'] != request['manager_output_root']
            or start['target_date'] != request['target_date']):
        _fail('LOCAL_RESULT_REQUEST_IDENTITY')
    if not _saved_schema(start['saved']):
        _fail('LOCAL_RESULT_ERROR_SCHEMA')
    data = bytearray(); digest = hashlib.sha256(); count = 0
    while True:
        header = _read_control(stream)
        if header.get('kind') == 'end':
            if (type(header.get('count')) is not int or type(header.get('bytes')) is not int
                    or header != dict(kind='end', count=count, bytes=len(data), sha256=digest.hexdigest())):
                _fail('LOCAL_RESULT_COMPLETE_HASH')
            if stream.read(1):
                _fail('LOCAL_RESULT_TRAILING_BYTES')
            break
        if set(header) != {'kind','index','bytes','sha256'} or header.get('kind') != 'chunk' or type(header['index']) is not int or header['index'] != count:
            _fail('LOCAL_RESULT_CHUNK_ORDER')
        size = header['bytes']
        if type(size) is not int or not 0 < size <= CHUNK_BYTES:
            _fail('LOCAL_RESULT_CHUNK_LIMIT')
        if len(data) + size > RESULT_BYTES:
            _fail('LOCAL_RESULT_TOTAL_LIMIT', actual_bytes=len(data)+size, allowed_bytes=RESULT_BYTES, saved=start['saved'])
        if count >= RESULT_BYTES // CHUNK_BYTES:
            _fail('LOCAL_RESULT_CHUNK_COUNT_LIMIT')
        chunk = _exact(stream, size)
        if hashlib.sha256(chunk).hexdigest() != header['sha256']:
            _fail('LOCAL_RESULT_CHUNK_HASH')
        digest.update(chunk); data.extend(chunk); count += 1
    _check_deadline(deadline)
    value = json.loads(data)
    _check_deadline(deadline)
    if not isinstance(value, dict) or value.get('payload', {}).get('target_trade_date') != request['target_date']:
        _fail('LOCAL_RESULT_TARGET')
    saved = saved_identity(value, request, deadline)
    _check_deadline(deadline)
    if saved != start['saved']:
        _fail('LOCAL_RESULT_SAVED_BINDING')
    receipt = dict(protocol='v5.manager_local_result.v1', response_sha256=digest.hexdigest(),
                   response_bytes=len(data), chunk_count=count, chunk_limit=CHUNK_BYTES,
                   result_limit=RESULT_BYTES, saved=saved,
                   hash_scope='FULL_RESPONSE_BEFORE_LOCAL_RESULT_TRANSPORT_FIELD')
    _check_deadline(deadline)
    return value, receipt


class _Pipe:
    def __init__(self, process, deadline):
        self.process = process; self.deadline = deadline; self.stderr_bytes = 0
        self.error_open = True; self.output_open = True
    def read(self, size):
        # stdout defines the framed protocol boundary. A descendant may inherit
        # stderr after the worker exits; waiting for stderr EOF here can hold the
        # protocol parser hostage even though stdout has definitively ended.
        while self.output_open:
            if self.stderr_bytes > STDERR_BYTES:
                _fail('LOCAL_RESULT_STDERR_LIMIT')
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                _fail('LOCAL_RESULT_TIMEOUT')
            streams = ([self.process.stdout] if self.output_open else []) + ([self.process.stderr] if self.error_open else [])
            ready, _, _ = select.select(streams, [], [], remaining)
            if not ready:
                _fail('LOCAL_RESULT_TIMEOUT')
            if self.error_open and self.process.stderr in ready:
                raw = os.read(self.process.stderr.fileno(), min(CHUNK_BYTES, STDERR_BYTES + 1 - self.stderr_bytes))
                self.stderr_bytes += len(raw)
                if self.stderr_bytes > STDERR_BYTES:
                    _fail('LOCAL_RESULT_STDERR_LIMIT')
                if not raw:
                    self.error_open = False
            if self.output_open and self.process.stdout in ready:
                raw = os.read(self.process.stdout.fileno(), min(size, CHUNK_BYTES))
                if raw:
                    return raw
                self.output_open = False
                return b''
        return b''

    def drain_stderr_after_worker_exit(self):
        # Called only after wait() confirms the worker itself has exited. Drain
        # bytes already emitted by that worker without requiring inherited pipe
        # handles in unrelated descendants to close.
        while self.error_open:
            ready, _, _ = select.select([self.process.stderr], [], [], 0)
            if not ready:
                return
            raw = os.read(self.process.stderr.fileno(), min(CHUNK_BYTES, STDERR_BYTES + 1 - self.stderr_bytes))
            self.stderr_bytes += len(raw)
            if self.stderr_bytes > STDERR_BYTES:
                _fail('LOCAL_RESULT_STDERR_LIMIT')
            if not raw:
                self.error_open = False
                return


def run_worker(argv, request, env, *, timeout=120):
    # Input is bounded by the unchanged 16 MiB canonical request guard.
    with tempfile.TemporaryFile() as source:
        source.write(canonical_bytes(request)); source.seek(0)
        with subprocess.Popen(argv, stdin=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env) as process:
            deadline = time.monotonic() + timeout
            pipe = _Pipe(process, deadline)
            try:
                value, receipt = read_result(pipe, request, deadline)
                _check_deadline(deadline)
                try:
                    status = process.wait(timeout=deadline-time.monotonic())
                except subprocess.TimeoutExpired:
                    _fail('LOCAL_RESULT_TIMEOUT')
                pipe.drain_stderr_after_worker_exit()
                if status != 0:
                    _fail('LOCAL_RESULT_WORKER_EXIT')
                _check_deadline(deadline)
                return value, receipt
            finally:
                if process.poll() is None:
                    process.kill(); process.wait()

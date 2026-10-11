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


class ResultTransportError(ValueError):
    def __init__(self, code, *, stage='transport', actual_bytes=None, allowed_bytes=None, saved=None):
        self.diagnostic = dict(code=code, stage=stage, actual_bytes=actual_bytes,
                               allowed_bytes=allowed_bytes, saved=saved)
        super().__init__(code)


def _fail(code, **fields):
    raise ResultTransportError(code, **fields)


def _pieces(value):
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    # Slice encoder strings before UTF-8 encoding, never encode a giant token twice.
    for token in encoder.iterencode(value):
        for offset in range(0, len(token), CHUNK_BYTES // 4):
            yield token[offset:offset + CHUNK_BYTES // 4].encode('utf-8')


def _digest(value):
    digest = hashlib.sha256()
    for piece in _pieces(value):
        digest.update(piece)
    return digest.hexdigest()


def _file(path):
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
            part = os.read(fd, min(CHUNK_BYTES, RESULT_BYTES + 1 - len(raw)))
            if not part:
                break
            raw.extend(part)
            if len(raw) > RESULT_BYTES:
                _fail('LOCAL_RESULT_FILE_LIMIT', actual_bytes=len(raw), allowed_bytes=RESULT_BYTES)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            _fail('LOCAL_RESULT_FILE_CHANGED')
        return bytes(raw)
    finally:
        os.close(fd)


def saved_identity(result, request):
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
    raw = _file(root / relative)
    saved = json.loads(raw)
    expected = readback.get('plan_sha256')
    if (saved.get('run_id') != run or saved.get('target_trade_date') != request['target_date']
            or saved.get('sha256') != expected or product.get('run_id') != run
            or product.get('sha256') != expected or product.get('consumed') is not True
            or saved.get('input_identity') != readback.get('input_identity')
            or _digest({k: v for k, v in saved.items() if k != 'sha256'}) != expected):
        _fail('LOCAL_RESULT_SAVED_IDENTITY')
    # Never use latest as the payload. Detect concurrent changes explicitly.
    if _file((root / relative).with_name('latest.json')) != raw:
        _fail('LOCAL_RESULT_LATEST_CHANGED')
    return dict(run_id=run, target_date=request['target_date'], relative=str(relative),
                plan_sha256=expected, raw_sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


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
        _control(stream, dict(kind='error', **error.diagnostic)); stream.flush()
        raise


def write_failure(stream, error, context=None):
    # Used only before result framing starts. No exception message/body leaks.
    stream.write(MAGIC)
    diagnostic = (error.diagnostic if isinstance(error, ResultTransportError) else
                  dict(code=(str(error) if re.fullmatch(r'[A-Z][A-Z0-9_:.-]{0,255}', str(error)) else 'LOCAL_MANAGER_WORKER_FAILED'), stage='assemble', actual_bytes=None,
                       allowed_bytes=RESULT_BYTES, saved=None))
    if context:
        diagnostic = {**diagnostic, 'stage': context.get('stage', diagnostic['stage']),
                      'saved': diagnostic.get('saved') or context.get('saved')}
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
        _fail(value.get('code', 'LOCAL_RESULT_ERROR'), stage=value.get('stage'),
              actual_bytes=value.get('actual_bytes'), allowed_bytes=value.get('allowed_bytes'), saved=value.get('saved'))
    return value


def read_result(stream, request):
    if _exact(stream, len(MAGIC)) != MAGIC:
        _fail('LOCAL_RESULT_PROTOCOL')
    start = _read_control(stream)
    if (set(start) != {'kind','request_sha256','output_root','target_date','saved'} or start['kind'] != 'start'
            or start['request_sha256'] != sha256_json(request) or start['output_root'] != request['manager_output_root']
            or start['target_date'] != request['target_date']):
        _fail('LOCAL_RESULT_REQUEST_IDENTITY')
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
    value = json.loads(data)
    if not isinstance(value, dict) or value.get('payload', {}).get('target_trade_date') != request['target_date']:
        _fail('LOCAL_RESULT_TARGET')
    saved = saved_identity(value, request)
    if saved != start['saved']:
        _fail('LOCAL_RESULT_SAVED_BINDING')
    receipt = dict(protocol='v5.manager_local_result.v1', response_sha256=digest.hexdigest(),
                   response_bytes=len(data), chunk_count=count, chunk_limit=CHUNK_BYTES,
                   result_limit=RESULT_BYTES, saved=saved,
                   hash_scope='FULL_RESPONSE_BEFORE_LOCAL_RESULT_TRANSPORT_FIELD')
    return value, receipt


class _Pipe:
    def __init__(self, process, deadline):
        self.process = process; self.deadline = deadline; self.stderr_bytes = 0; self.error_open = True
    def read(self, size):
        while True:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                _fail('LOCAL_RESULT_TIMEOUT')
            streams = [self.process.stdout] + ([self.process.stderr] if self.error_open else [])
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
            if self.process.stdout in ready:
                return os.read(self.process.stdout.fileno(), min(size, CHUNK_BYTES))


def run_worker(argv, request, env, *, timeout=120):
    # Input is bounded by the unchanged 16 MiB canonical request guard.
    with tempfile.TemporaryFile() as source:
        source.write(canonical_bytes(request)); source.seek(0)
        with subprocess.Popen(argv, stdin=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env) as process:
            deadline = time.monotonic() + timeout
            try:
                value, receipt = read_result(_Pipe(process, deadline), request)
                if process.wait(timeout=max(0.001, deadline-time.monotonic())) != 0:
                    _fail('LOCAL_RESULT_WORKER_EXIT')
                return value, receipt
            finally:
                if process.poll() is None:
                    process.kill(); process.wait()

"""Read an exact existing M03 binding, without a source/collector/write fallback.

This adapter can live in P0's older owner bundle. It starts a fresh child and
loads only the byte-pinned efea market runtime named by the ORIGINAL request.
It does not rewrite owner_root, v5_src, capture permission, dates, or cutoff.
"""
import argparse
import hashlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

RUNTIME_COMMIT = 'efeaeb8fc04474b1f38ebda98b35953b580049df'
RUNTIME_SHA256 = {
    'src/v5_shadow/__init__.py': 'c53107e04e471793978e7ea517445a937bf46fd8f3005452e34f683712c1774c',
    'src/v5_shadow/us_source_daily.py': '55c4291c191d56639559ca2d96fdbfb1d274116bd21a821b24a922627efce8fa',
    'src/v5_shadow/cloud_us_collector.py': '8a98fba4022d775852685d12343e753f0d31ffe7f46a3bd8e9243f11eb4cdd06',
    'src/v5_shadow/cloud_transport.py': 'b3430662338cac674ca4f0f8d241a84f6d5ff6891b89a1bd0c519c4d7affed89',
    'src/v5_shadow/composition.py': '258462c4ee53a3ee7acc4f8e0e0f35b4b20994f9ec4dd6ee48f37a6a68c981b0',
    'src/v5_shadow/contracts.py': 'eee026873e0d765fcedf52077daea823edf6ee7013f37c106c82b66a4582d85a',
    'src/v5_shadow/digests.py': '134b1a13b7ff677afef6f556e2a750d94cc54a396cbdcff111c5d67e645280e5',
    'contracts/cloud_us_collector_sources.json': '34f45318dd89132a496ac0edf98147455b41d9ea926198d83ce1bd8810c20d8b',
}
FIELDS = frozenset(('request_file', 'expected_request_sha256',
                    'expected_binding_sha256', 'expected_source_sha256'))
MAX_BYTES = 16 * 1024 * 1024


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _sha_value(value):
    if not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError('M03_SAVED_SHA_REQUIRED')
    return value


def _canonical(value):
    # This is the original R14 request/binding convention, not a new identity.
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('M03_SAVED_DUPLICATE_JSON_KEY')
        value[key] = item
    return value


def _decode(raw):
    value = json.loads(raw, object_pairs_hook=_pairs,
                       parse_constant=lambda value: (_ for _ in ()).throw(ValueError('M03_SAVED_NONFINITE')))
    if not isinstance(value, dict):
        raise ValueError('M03_SAVED_JSON_OBJECT_REQUIRED')
    return value


def _read_file(value):
    """Bounded, stable read using no-follow descriptors for every component."""
    if not isinstance(value, (str, Path)):
        raise ValueError('M03_SAVED_ABSOLUTE_PATH_REQUIRED')
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or '\x00' in str(path):
        raise ValueError('M03_SAVED_ABSOLUTE_PATH_REQUIRED')
    if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'):
        raise ValueError('M03_SAVED_PLATFORM_UNSUPPORTED')
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = None
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
            raise ValueError('M03_SAVED_FILE_CONTRACT')
        chunks = []
        remaining = MAX_BYTES + 1
        while remaining:
            raw = os.read(fd, min(remaining, 1024 * 1024))
            if not raw:
                break
            chunks.append(raw)
            remaining -= len(raw)
        raw = b''.join(chunks)
        after = os.fstat(fd)
        visible = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if len(raw) > MAX_BYTES or identity(before) != identity(after) or identity(after) != identity(visible):
            raise ValueError('M03_SAVED_FILE_CHANGED')
        return raw
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def _check_envelope(value):
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError('M03_SAVED_READ_FIELDS')
    _sha_value(value['expected_request_sha256'])
    _sha_value(value['expected_binding_sha256'])
    sources = value['expected_source_sha256']
    if not isinstance(sources, dict) or set(sources) != {'payload', 'receipt', 'manifest'}:
        raise ValueError('M03_SAVED_SOURCE_SHA_FIELDS')
    for digest in sources.values():
        _sha_value(digest)
    if not isinstance(value['request_file'], str) or not value['request_file']:
        raise ValueError('M03_SAVED_REQUEST_FILE_REQUIRED')


def _verify_runtime(v5_src):
    root = Path(v5_src).parent
    for relative, expected in RUNTIME_SHA256.items():
        if _sha(_read_file(root / relative)) != expected:
            raise ValueError('M03_SAVED_RUNTIME_SHA_MISMATCH:' + relative)



def _install_runtime_loader(v5_src):
    """Compile the pinned bytes, never a valid/poisoned pyc or path fallback."""
    if any(name == 'v5_shadow' or name.startswith('v5_shadow.') for name in sys.modules):
        raise ValueError('M03_SAVED_FRESH_PROCESS_REQUIRED')
    root = Path(v5_src).parent
    modules = {}
    for relative, expected in RUNTIME_SHA256.items():
        if not relative.endswith('.py'):
            continue
        path = root / relative
        raw = _read_file(path)
        if _sha(raw) != expected:
            raise ValueError('M03_SAVED_RUNTIME_SHA_MISMATCH:' + relative)
        package = path.name == '__init__.py'
        parts = Path(relative).parts[1:]
        name = '.'.join(parts[:-1] if package else (*parts[:-1], path.stem))
        modules[name] = (path, raw, package)
    class Loader(importlib.abc.Loader):
        def create_module(self, spec):
            return None
        def exec_module(self, module):
            path, raw, _ = modules[module.__name__]
            exec(compile(raw, str(path), 'exec', dont_inherit=True), module.__dict__)
    class Finder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname != 'v5_shadow' and not fullname.startswith('v5_shadow.'):
                return None
            if fullname not in modules:
                raise ModuleNotFoundError('M03_SAVED_UNPINNED_RUNTIME_MODULE:' + fullname)
            source, _, package = modules[fullname]
            return importlib.util.spec_from_file_location(fullname, source, loader=Loader(),
                submodule_search_locations=[str(source.parent)] if package else None)
    sys.meta_path.insert(0, Finder())


def _install_readonly_audit(allowed_reader):
    """Do not permit this child to produce, repair, create locks, or network."""
    mutations = {'os.mkdir', 'os.remove', 'os.rmdir', 'os.rename', 'os.link',
                 'os.symlink', 'os.chmod', 'os.chown', 'os.truncate', 'os.utime'}
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
    def audit(event, args):
        if event.startswith('socket.') or event in mutations:
            raise ValueError('M03_SAVED_READ_ONLY_VIOLATION:' + event)
        if event == 'open':
            mode, flags = args[1], args[2]
            if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or flags & write_flags:
                raise ValueError('M03_SAVED_READ_ONLY_VIOLATION:open')
        if event == 'subprocess.Popen' and list(args[1]) != allowed_reader:
            raise ValueError('M03_SAVED_PRODUCER_PROCESS_FORBIDDEN')
    sys.addaudithook(audit)


def _projection(binding, request_sha, binding_sha):
    snapshot = binding['market_snapshot']
    identity = binding['identity']
    request = binding['request']
    return dict(
        schema_version='v5.m03.saved_binding_public_view.v1',
        status=binding['status'], source_status=binding['source_status'],
        readback_verified=True, request_sha256=request_sha, binding_sha256=binding_sha,
        source_sha256=binding['source_sha256'],
        request={key: request[key] for key in ('trade_date', 'session', 'capture_phase', 'cutoff')},
        identity={key: identity[key] for key in ('us_session_date', 'capture_phase', 'captured_at',
            'capture_id', 'run_id', 'capture_origin', 'original_time_capture',
            'rss_status', 'quote_capture_status') if key in identity},
        market_snapshot=dict(
            **{key: snapshot[key] for key in ('schema_version', 'status', 'capture_session_date',
                'capture_phase', 'captured_at', 'source_response_sha256') if key in snapshot},
            quote_count=len(snapshot.get('quotes', [])), theme_count=len(snapshot.get('rows', []))),
        runtime_commit=RUNTIME_COMMIT, orchestrator_sha256=binding['orchestrator_sha256'],
        owner_descriptor_sha256=binding['owner_descriptor_sha256'],
        production_allowed=False, orders_sent=False, buy_gate_updated=False,
        natural_verified=False, formal_eligibility_verified=False)


def _read_owned(envelope):
    _check_envelope(envelope)
    original_raw = _read_file(envelope['request_file'])
    values = _decode(original_raw)
    required = {'trade_date', 'capture_phase', 'session', 'cutoff', 'source_root',
        'snapshot_root', 'binding_root', 'owner_root', 'v5_src', 'allow_network_capture',
        'capture_root', 'allow_late_post_close', 'development_dates_file', 'market_snapshot_only'}
    if set(values) != required:
        raise ValueError('M03_SAVED_REQUEST_FIELDS')
    if _sha(original_raw) != envelope['expected_request_sha256']:
        raise ValueError('M03_SAVED_REQUEST_SHA_MISMATCH')
    _verify_runtime(values['v5_src'])
    _install_runtime_loader(values['v5_src'])
    from v5_shadow import us_source_daily as original
    from v5_shadow.cloud_us_collector import load_owner, verify, audit_modules, admit_output
    req = original._request_from_dict(values)
    if original._request_dict(req) != values:
        raise ValueError('M03_SAVED_REQUEST_ROUNDTRIP_MISMATCH')
    original._validate_request(req)
    # Only prepend the byte-pinned import boundary. The original reader body,
    # request, owner loader and semantic validation are unmodified.
    reader_body = original._reader_child_code()
    path_line = '    sys.path.insert(0, sys.argv[1])\n'
    if reader_body.count(path_line) != 1:
        raise ValueError('M03_SAVED_READER_BOOTSTRAP_CONTRACT')
    reader_body = reader_body.replace(path_line, '')
    loader_prefix = ("import runpy, sys\n" +
        "runpy.run_path(" + repr(str(Path(__file__).absolute())) +
        ")['_install_runtime_loader'](sys.argv[1])\n")
    original._reader_child_code = lambda: loader_prefix + reader_body
    allowed_reader = [sys.executable, '-I', '-B', '-c', original._reader_child_code(),
                      str(req.v5_src), str(req.owner_root), str(req.snapshot_root),
                      req.trade_date, req.capture_phase]
    _install_readonly_audit(allowed_reader)
    load_owner(req.owner_root)
    try:
        admit_output(req.binding_root, req.owner_root)
        admit_output(req.snapshot_root, req.owner_root)
        name = original._binding_name(req)
        if name != _sha(_canonical(values)) + '.json':
            raise ValueError('M03_SAVED_BINDING_NAME_MISMATCH')
        io = original._safe_root(req.binding_root)
        try:
            raw = io.read_bytes(name)
        except FileNotFoundError as error:
            raise ValueError('M03_SAVED_BINDING_MISSING') from error
        if _sha(raw) != envelope['expected_binding_sha256']:
            raise ValueError('M03_SAVED_BINDING_SHA_MISMATCH')
        binding = _decode(raw)
        if binding.get('source_sha256') != envelope['expected_source_sha256']:
            raise ValueError('M03_SAVED_SOURCE_SHA_MISMATCH')
        # Original reconstruction checks every binding field, exact original
        # request, stable snapshot bytes, and fresh-child original store reader.
        original._verify_binding(binding, req)
        if io.read_bytes(name) != raw or _read_file(envelope['request_file']) != original_raw:
            raise ValueError('M03_SAVED_INPUT_CHANGED')
        result = _projection(binding, envelope['expected_request_sha256'], _sha(raw))
        result['request_identity_sha256'] = name[:-5]
    finally:
        verify(req.owner_root)
        audit_modules()
        original._verify_orchestrator()
        _verify_runtime(req.v5_src)
    return result


def read_saved_binding(*, request_file, expected_request_sha256,
                       expected_binding_sha256, expected_source_sha256):
    """Read existing bytes only. Capture=True in the original request is identity."""
    envelope = dict(request_file=str(request_file), expected_request_sha256=expected_request_sha256,
                    expected_binding_sha256=expected_binding_sha256,
                    expected_source_sha256=expected_source_sha256)
    _check_envelope(envelope)
    try:
        proc = subprocess.run([sys.executable, '-I', '-B', str(Path(__file__).absolute()), '--child'],
            input=_canonical(envelope), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    except subprocess.TimeoutExpired as error:
        raise ValueError('M03_SAVED_READ_TIMEOUT') from error
    if len(proc.stdout) > MAX_BYTES:
        raise ValueError('M03_SAVED_RESPONSE_LIMIT')
    try:
        value = _decode(proc.stdout)
    except ValueError as error:
        raise ValueError('M03_SAVED_BAD_RESPONSE:' + proc.stderr.decode(errors='replace')[-1000:]) from error
    if proc.returncode:
        raise ValueError(value.get('error', 'M03_SAVED_READ_FAILED'))
    if set(value) != {'result'} or not isinstance(value['result'], dict):
        raise ValueError('M03_SAVED_RESPONSE_CONTRACT')
    return value['result']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--request', type=Path, help='local saved-read envelope JSON; contains no producer options')
    mode.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.child:
            raw = sys.stdin.buffer.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError('M03_SAVED_REQUEST_LIMIT')
            result = _read_owned(_decode(raw))
            print(json.dumps({'result': result}, sort_keys=True, allow_nan=False))
        else:
            envelope = _decode(_read_file(args.request))
            _check_envelope(envelope)
            print(json.dumps(read_saved_binding(**envelope), sort_keys=True, allow_nan=False))
        return 0
    except Exception as error:
        failure = dict(status='SOURCE_REJECTED', error_type=type(error).__name__, error=str(error))
        print(json.dumps(failure, sort_keys=True), file=sys.stdout if args.child else sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

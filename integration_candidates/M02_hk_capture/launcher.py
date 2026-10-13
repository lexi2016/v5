#!/usr/bin/env python3
"""Fail-closed, single-use entry point for the isolated M02 HK candidate.

No command captures implicitly. Runtime bundle imports execute manifest-verified
source bytes in a fresh isolated Python process. This launcher does not log in,
change HOME, locate credentials, publish into V4, or invoke a full panel lane.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import uuid

SCHEMA = 'v5.m02.capture_candidate.sources.v1'
BUNDLE = Path(os.path.abspath(__file__)).parent
MANIFEST = 'SOURCE_MANIFEST.json'
CAPTURE_FILES = ('capture.json', 'capture.sdk.capture.json', 'capture.capture.json')
CLAIM = 'capture.claim.json'
RESULT = 'capture.result.json'
LIMIT = 32 * 1024 * 1024
FLAGS = dict(production_allowed=False, buy_gate_updated=False, orders_sent=False)


class GateError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def absolute(value):
    if not isinstance(value, str) or not value.startswith('/') or '\x00' in value or '..' in value.split('/'):
        raise GateError('ABSOLUTE_PATH_REQUIRED')
    return Path(value)


@contextlib.contextmanager
def directory(path):
    """Open each ancestor without following links, keeping the final dir-fd."""
    path = absolute(str(path))
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            info = os.stat(part, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                raise GateError('SYMLINK_PATH')
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def read_file(path, limit=LIMIT):
    path = absolute(str(path))
    with directory(path.parent) as parent:
        info = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode):
            raise GateError('SYMLINK_FILE')
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise GateError('REGULAR_FILE_REQUIRED')
            if info.st_size > limit:
                raise GateError('FILE_SIZE_LIMIT')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                raw = stream.read(limit + 1)
            if len(raw) > limit:
                raise GateError('FILE_SIZE_LIMIT')
            return raw
        finally:
            os.close(fd)


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise GateError('JSON_DUPLICATE_KEY')
            out[key] = value
        return out
    def nonfinite(value):
        raise GateError('JSON_NONFINITE')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def require_home():
    home = os.environ.get('HOME')
    if not home or not os.path.isabs(home) or not os.path.isdir(home):
        raise GateError('HOME_REQUIRED: preserve an existing absolute HOME')
    return home


def protected(path, home):
    """Reject known V4 and candidate overlaps before touching those paths."""
    path = absolute(str(path))
    denied = (BUNDLE, Path(home) / 'Library/Application Support/com.lexi.v4.local')
    if any(path.is_relative_to(root) or root.is_relative_to(path) for root in denied):
        raise GateError('PROTECTED_PATH')
    if any(part.casefold() in {'v4', 'v35_dispatcher', 'com.lexi.v4.local'} for part in path.parts):
        raise GateError('PROTECTED_PATH')
    return path


def target_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{8}', value):
        raise GateError('TARGET_DATE')
    try:
        datetime.strptime(value, '%Y%m%d')
    except ValueError as exc:
        raise GateError('TARGET_DATE') from exc
    return value


def verify_sources(expected):
    if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise GateError('MANIFEST_SHA_REQUIRED')
    raw = read_file(BUNDLE / MANIFEST)
    if digest(raw) != expected:
        raise GateError('MANIFEST_SHA_MISMATCH')
    manifest = strict_json(raw)
    if not isinstance(manifest, dict) or manifest.get('schema_version') != SCHEMA:
        raise GateError('MANIFEST_SCHEMA')
    files = manifest.get('files')
    if not isinstance(files, dict) or 'launcher.py' not in files or MANIFEST in files:
        raise GateError('MANIFEST_FILES')
    frozen = {}
    for relative, identity in files.items():
        name = PurePosixPath(relative)
        if (not relative or name.is_absolute() or '..' in name.parts or '\\' in relative
                or name.as_posix() != relative or ':' in relative):
            raise GateError('MANIFEST_PATH')
        if (not isinstance(identity, dict) or set(identity) != {'sha256', 'bytes'}
                or type(identity['bytes']) is not int or identity['bytes'] < 0
                or not isinstance(identity['sha256'], str)
                or not re.fullmatch(r'[0-9a-f]{64}', identity['sha256'])):
            raise GateError('MANIFEST_IDENTITY')
        content = read_file(BUNDLE / relative)
        if len(content) != identity['bytes'] or digest(content) != identity['sha256']:
            raise GateError('SOURCE_MISMATCH: ' + relative)
        frozen[relative] = content
    required = {'launcher.py'}
    for tree in ('collector', 'recovery'):
        with directory(BUNDLE / tree):
            pass
        for root, dirs, names in os.walk(BUNDLE / tree, followlinks=False):
            for name in dirs + names:
                path = Path(root) / name
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode):
                    raise GateError('SYMLINK_SOURCE')
                if not stat.S_ISDIR(info.st_mode) and not stat.S_ISREG(info.st_mode):
                    raise GateError('REGULAR_FILE_REQUIRED')
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
            for name in names:
                if name.endswith(('.pyc', '.pyo')):
                    raise GateError('SOURCE_INVENTORY: bytecode is not a source')
                required.add((Path(root) / name).relative_to(BUNDLE).as_posix())
    if not required.issubset(files):
        raise GateError('SOURCE_INVENTORY')
    return frozen


class FrozenBundle(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Never fall back to installed/active modules for reserved package names."""
    def __init__(self, frozen, prefix, packages):
        self.sources = {name[len(prefix) + 1:]: raw for name, raw in frozen.items() if name.startswith(prefix + '/')}
        self.prefix = prefix
        self.packages = packages

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] not in self.packages:
            return None
        relative = fullname.replace('.', '/')
        for name, package in ((relative + '/__init__.py', True), (relative + '.py', False)):
            if name in self.sources:
                spec = importlib.util.spec_from_loader(fullname, self, is_package=package)
                spec.loader_state = (name, self.sources[name])
                return spec
        if any(name.startswith(relative + '/') for name in self.sources):
            spec = importlib.util.spec_from_loader(fullname, self, is_package=True)
            spec.loader_state = (relative + '/__init__.py', None)
            return spec
        raise ImportError('UNBUNDLED_IMPORT: ' + fullname)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        relative, raw = module.__spec__.loader_state
        module.__file__ = str(BUNDLE / self.prefix / relative)
        if module.__spec__.submodule_search_locations is not None:
            module.__path__ = []
        if raw is not None:
            exec(compile(raw, module.__file__, 'exec'), module.__dict__)


@contextlib.contextmanager
def pinned_imports(frozen, prefix, packages):
    if any(name.split('.')[0] in packages for name in sys.modules):
        raise GateError('BUNDLE_IMPORT_ALREADY_LOADED')
    loader = FrozenBundle(frozen, prefix, packages)
    sys.meta_path.insert(0, loader)
    try:
        yield
    finally:
        sys.meta_path.remove(loader)


def exclusive_json(fd, name, value):
    child = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400, dir_fd=fd)
    try:
        with os.fdopen(child, 'wb', closefd=False) as stream:
            stream.write(canonical(value))
            stream.flush()
            os.fsync(child)
        os.fchmod(child, 0o400)
        os.fsync(fd)
    finally:
        os.close(child)


@contextlib.contextmanager
def private_root(path, home, kind):
    path = protected(path, home)
    marker = '.v5-hk-' + kind + '-root'
    with directory(path) as fd:
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise GateError('OUTPUT_NOT_PRIVATE')
        identity = (info.st_dev, info.st_ino)
        if read_file(path / marker) != ('v5.hk-' + kind + '-root.v1\n').encode():
            raise GateError('OUTPUT_MARKER')
        lock = os.open(marker, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            lock_info = os.fstat(lock)
            if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_uid != os.getuid() or lock_info.st_nlink != 1:
                raise GateError('OUTPUT_MARKER')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise GateError('OUTPUT_LOCKED') from exc
            yield fd, marker
            with directory(path) as current:
                now = os.fstat(current)
                if (now.st_dev, now.st_ino) != identity:
                    raise GateError('OUTPUT_ROOT_REPLACED')
        finally:
            os.close(lock)


@contextlib.contextmanager
def capture_environment(output, run_id):
    values = {'V35_HK_CAPTURE_PATH': str(output / 'capture.json'), 'V35_HK_CAPTURE_RUN_ID': run_id}
    previous = {name: os.environ.get(name) for name in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def capture(args, frozen, home):
    output = protected(absolute(args.output_root), home)
    target_date(args.target_date)
    with private_root(output, home, 'capture') as (fd, marker):
        existing = set(os.listdir(fd))
        if CLAIM in existing:
            raise GateError('CAPTURE_ALREADY_CLAIMED')
        if existing != {marker}:
            raise GateError('OUTPUT_NOT_FRESH')
        run_id = 'manual-' + args.target_date + '-' + uuid.uuid4().hex
        receipt = dict(schema_version='v5.m02.capture_candidate.launcher_receipt.v1',
                       execution_kind='MANUAL_CAPTURE', natural_verified=False,
                       target_date=args.target_date, capture_run_id=run_id,
                       expected_manifest_sha256=args.expected_manifest_sha,
                       started_at=datetime.now(timezone.utc).isoformat(), **FLAGS)
        exclusive_json(fd, CLAIM, dict(receipt, status='CLAIMED'))
        try:
            with pinned_imports(frozen, 'collector', {'ops', 'infrastructure'}), capture_environment(output, run_id):
                with contextlib.redirect_stdout(sys.stderr):
                    facade = importlib.import_module('ops.macos_research_panel_daily')
                    facade.collect_hk_futu_rows(args.target_date)
            verify_sources(args.expected_manifest_sha)
            if os.environ.get('HOME') != home:
                raise GateError('HOME_CHANGED')
            if set(os.listdir(fd)) != {marker, CLAIM, *CAPTURE_FILES}:
                raise GateError('CAPTURE_OUTPUT_SET')
            receipt['files'] = {name: digest(read_file(output / name)) for name in CAPTURE_FILES}
            receipt['status'] = 'CAPTURE_COMPLETED'
        except Exception as exc:
            receipt.update(status='CAPTURE_FAILED', reason=type(exc).__name__ + ': ' + str(exc))
            # Even a failed import/capture must recheck the complete source pin.
            try:
                verify_sources(args.expected_manifest_sha)
            except Exception as changed:
                receipt['source_verification_error'] = type(changed).__name__ + ': ' + str(changed)
            exclusive_json(fd, RESULT, receipt)
            raise
        exclusive_json(fd, RESULT, receipt)
    return receipt


def recovery_request(path, home):
    path = protected(absolute(path), home)
    request = strict_json(read_file(path))
    if not isinstance(request, dict) or set(request) != {'sdk_path', 'sdk_sha256', 'output_root', 'target_date'}:
        raise GateError('RECOVERY_REQUEST_FIELDS')
    target_date(request['target_date'])
    source = protected(absolute(request['sdk_path']), home)
    output = protected(absolute(request['output_root']), home)
    if source.is_relative_to(output) or path.is_relative_to(output):
        raise GateError('RECOVERY_INPUT_OUTPUT_OVERLAP')
    if not isinstance(request['sdk_sha256'], str) or digest(read_file(source)) != request['sdk_sha256']:
        raise GateError('SDK_SHA_MISMATCH')
    return request


def recover(args, frozen, home):
    # This is a Python-level guard for this isolated wrapper, not an OS sandbox.
    # The original pinned recovery launches its own pure recovery subprocess.
    def forbid_network(event, arguments):
        if event.startswith('socket.'):
            raise GateError('RECOVERY_NETWORK_FORBIDDEN')
    sys.addaudithook(forbid_network)
    request = recovery_request(args.request, home)
    with private_root(Path(request['output_root']), home, 'membership') as (fd, marker):
        if set(os.listdir(fd)) != {marker}:
            raise GateError('OUTPUT_NOT_FRESH')
        try:
            with pinned_imports(frozen, 'recovery/V5/src', {'v5_shadow'}):
                with contextlib.redirect_stdout(sys.stderr):
                    module = importlib.import_module('v5_shadow.hk_membership_recovery')
                    result = module.run_recovery(request)
        finally:
            verify_sources(args.expected_manifest_sha)
        if os.environ.get('HOME') != home:
            raise GateError('HOME_CHANGED')
        if recovery_request(args.request, home) != request:
            raise GateError('RECOVERY_REQUEST_CHANGED')
    return dict(status='RECOVERY_COMPLETED', expected_manifest_sha256=args.expected_manifest_sha, recovery=result, **FLAGS)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    worker = bool(argv and argv[0] == '--_isolated-worker')
    if worker:
        argv.pop(0)
        if not sys.flags.isolated or not sys.flags.dont_write_bytecode:
            raise GateError('ISOLATED_WORKER_REQUIRED')
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('verify', 'capture', 'recover'):
        sub = commands.add_parser(command)
        sub.add_argument('--expected-manifest-sha', required=True)
        if command == 'capture':
            sub.add_argument('--target-date', required=True)
            sub.add_argument('--output-root', required=True)
            sub.add_argument('--allow-live-capture', action='store_true')
        elif command == 'recover':
            sub.add_argument('--request', required=True)
    args = parser.parse_args(argv)
    if args.command == 'capture' and not args.allow_live_capture:
        raise GateError('LIVE_CAPTURE_REQUIRES_FLAG')
    home = require_home()
    # Check protected output paths before scanning or importing candidate files.
    if args.command == 'capture':
        protected(absolute(args.output_root), home)
        target_date(args.target_date)
    frozen = verify_sources(args.expected_manifest_sha)
    if args.command == 'verify':
        return dict(status='VERIFIED', expected_manifest_sha256=args.expected_manifest_sha, file_count=len(frozen), **FLAGS)
    if not worker:
        environment = {key: value for key, value in os.environ.items() if not key.startswith(('PYTHON', 'V4_', 'V35_'))}
        process = subprocess.run([sys.executable, '-I', '-B', str(BUNDLE / 'launcher.py'), '--_isolated-worker', *argv],
                                 env=environment, cwd=str(BUNDLE), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        verify_sources(args.expected_manifest_sha)
        sys.stderr.buffer.write(process.stderr)
        if process.returncode:
            sys.stdout.buffer.write(process.stdout)
            raise SystemExit(process.returncode)
        return strict_json(process.stdout)
    return capture(args, frozen, home) if args.command == 'capture' else recover(args, frozen, home)


if __name__ == '__main__':
    try:
        print(canonical(main()).decode(), end='')
    except Exception as error:
        print(canonical(dict(status='REJECTED', reason=type(error).__name__ + ': ' + str(error), **FLAGS)).decode(), end='')
        raise SystemExit(1)

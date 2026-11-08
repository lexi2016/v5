"""Reviewed retry entry candidate. Empty registry; no production activation.

This is a NEW subset-owner interface, not the old full-argv approval renamed.
Only code-reviewed registry entries supply the clock, canonical ledger, exact
evidence refs and original owner hooks. Requests cannot supply these values.
The original owner retains its source/calendar/resource gates, locks, monitor,
writer and cleanup. A returned callback is never independent reconciliation.
"""
import builtins
from dataclasses import dataclass
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import types
from typing import Callable, Mapping


HERE = Path(__file__).resolve().parent
LIMIT = 16 * 1024**2
NODES = ('retry-1610', 'retry-1640')


def _need(ok, reason):
    if not ok:
        raise ValueError(reason)


@dataclass(frozen=True)
class FilePin:
    path: str
    bytes: int
    sha256: str

    def as_dict(self):
        return {'path': self.path, 'bytes': self.bytes, 'sha256': self.sha256}


@dataclass(frozen=True)
class OwnerHooks:
    """Reviewed adapters to the ORIGINAL owner; no shell/argv runner here.

    guard(original_binding) must hold the original owner/queue lock domains,
    validate source/calendar and start resources, and yield a monitor pulse.
    pulse() returns None or raises. execute_subset receives ONLY failed symbols
    plus the same claim identity; it must retain the owner's writer/cleanup and
    call pulse at original runtime checkpoints. It returns bytes or None per
    requested symbol. Returned bytes remain provisional until independent review.
    """
    identity: str
    guard: Callable
    execute_subset: Callable


@dataclass(frozen=True)
class ReviewedRun:
    run_id: str
    environment_id: str
    contract_ref: FilePin
    approval_ref: FilePin
    reconciliation_refs: Mapping[str, FilePin]
    success_output_refs: Mapping[str, FilePin]
    owner: OwnerHooks
    clock: Callable


# Publication REGISTRY.json is descriptive metadata, never this authorization.
# A separately reviewed revision is required to add any real run/environment.
TRUSTED_RUNS = ()


def _pin(value):
    if isinstance(value, FilePin):
        return value
    _need(type(value) is dict and set(value) == {'path', 'bytes', 'sha256'}, 'PIN_SCHEMA')
    return FilePin(**value)


def _pin_path(pin, original_root=None):
    _need(isinstance(pin.path, str), 'PIN_PATH')
    path = Path(pin.path)
    _need('..' not in path.parts and path.name, 'PIN_PATH_SCOPE')
    if not path.is_absolute():
        _need(original_root is not None, 'REGISTERED_ORIGINAL_ROOT_REQUIRED')
        path = Path(original_root) / path
    _need(path.is_absolute(), 'ABSOLUTE_PIN_PATH')
    return path


def _read_pin(value, original_root=None):
    """Read, hash and consume the SAME bounded no-follow descriptor bytes."""
    pin = _pin(value)
    path = _pin_path(pin, original_root)
    _need(type(pin.bytes) is int and 0 < pin.bytes <= LIMIT, 'PIN_SIZE')
    _need(isinstance(pin.sha256, str) and re.fullmatch('[0-9a-f]{64}', pin.sha256), 'PIN_SHA256')
    fds = []
    try:
        fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        fds.append(fd)
        for part in path.parts[1:-1]:
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            fds.append(fd)
        f = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        fds.append(f)
        before = os.fstat(f)
        _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size == pin.bytes,
              'PIN_FILE_IDENTITY_SIZE')
        chunks, remaining = [], pin.bytes + 1
        while remaining:
            chunk = os.read(f, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b''.join(chunks)
        def identity(s):
            return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns
        _need(identity(before) == identity(os.fstat(f)) ==
              identity(os.stat(path.name, dir_fd=fd, follow_symlinks=False)), 'PIN_FILE_CHANGED')
        _need(path == path.resolve() and len(raw) == pin.bytes and
              hashlib.sha256(raw).hexdigest() == pin.sha256, 'PIN_CHANGED')
        return raw
    finally:
        for fd in reversed(fds):
            os.close(fd)


def _json(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            _need(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))


def _load_components(dependencies, original_root):
    """No sys.path/sys.modules substitution and no reopen after byte checking."""
    checked = {}
    for value in dependencies:
        pin = _pin(value)
        path = str(_pin_path(pin, original_root))
        _need(path not in checked, 'DUPLICATE_DEPENDENCY')
        checked[path] = _read_pin(pin, original_root)
    expected = [str(HERE / name) for name in ('entrypoint.py', 'subset_plan.py', 'coordinator.py')]
    _need(all(path in checked for path in expected), 'ENTRY_DEPENDENCY_CLOSURE')

    def load(name, imports):
        path = str(HERE / (name + '.py'))
        module = types.ModuleType('_reviewed_retry_' + name)
        module.__file__ = path
        namespace_builtins = dict(vars(builtins))
        def checked_import(requested, globals=None, locals=None, fromlist=(), level=0):
            if level == 0 and requested in imports:
                return imports[requested]
            return builtins.__import__(requested, globals, locals, fromlist, level)
        namespace_builtins['__import__'] = checked_import
        module.__dict__['__builtins__'] = namespace_builtins
        exec(compile(checked[path], path, 'exec'), module.__dict__)
        return module
    subset = load('subset_plan', {})
    return subset, load('coordinator', {'subset_plan': subset})


class _OutputBytes:
    """Read successful output evidence lazily, without retaining a whole pool."""
    def __init__(self, refs, original_root):
        self.refs = dict(refs)
        self.original_root = original_root

    def get(self, sha):
        ref = self.refs.get(sha)
        if ref is None:
            return None
        _need(_pin(ref).sha256 == sha, 'SUCCESS_OUTPUT_REFERENCE')
        return _read_pin(ref, self.original_root)


def _ledger_identity(contract):
    path = Path(contract['ledger_root'])
    _need(path.is_absolute() and path == path.resolve(), 'LEDGER_CANONICAL_PATH')
    root = path.stat(follow_symlinks=False)
    lock = (path / 'OWNER.lock').stat(follow_symlinks=False)
    _need(stat.S_ISDIR(root.st_mode) and [root.st_dev, root.st_ino] == contract['ledger_inode'],
          'LEDGER_ROOT_IDENTITY')
    _need(stat.S_ISREG(lock.st_mode) and lock.st_nlink == 1 and
          [lock.st_dev, lock.st_ino] == contract['lock_inode'], 'LEDGER_LOCK_IDENTITY')
    return path


def _preflight(registration, node):
    _need(callable(registration.clock), 'REGISTERED_CLOCK_REQUIRED')
    now = registration.clock()
    _need(isinstance(now, dt.datetime) and now.tzinfo is not None and now.utcoffset() is not None,
          'REGISTERED_AWARE_CLOCK_REQUIRED')
    contract_raw = _read_pin(registration.contract_ref)
    contract = _json(contract_raw)
    _need(contract.get('schema') == 'REVIEWED_RETRY_SUBSET_ENTRY_V1' and
          contract.get('owner_api') == 'RETRY_SUBSET_OWNER_API_V1', 'NEW_SUBSET_CONTRACT_REQUIRED')
    binding = contract['binding']
    original_root = Path(contract['original_root'])
    _need(original_root.is_absolute() and original_root == original_root.resolve() and
          original_root.is_dir(), 'REGISTERED_ORIGINAL_ROOT_REQUIRED')
    _need(binding['run_id'] == registration.run_id and
          contract['environment_id'] == registration.environment_id, 'REGISTERED_IDENTITY')
    approval = _json(_read_pin(registration.approval_ref))
    _need(approval.get('schema') == 'RETRY_SUBSET_ENTRY_APPROVAL_V1' and
          approval.get('status') == 'PASS_RETRY_SUBSET_ENTRY' and
          approval.get('reviewer_role') == 'independent_reviewer' and
          approval.get('contract_ref') == registration.contract_ref.as_dict() and
          approval.get('binding') == binding and
          approval.get('environment_id') == registration.environment_id, 'SUBSET_INDEPENDENT_APPROVAL')
    original = binding['original_binding']
    _need(original['contract_ref']['sha256'] != registration.contract_ref.sha256,
          'OLD_FULL_ARGV_CONTRACT_IS_NOT_SUBSET_APPROVAL')
    original_contract = _json(_read_pin(original['contract_ref'], original_root))
    for key in ('date', 'node', 'input_refs', 'code_refs', 'argv', 'resources', 'locks'):
        _need(original_contract.get(key) == original[key], 'ORIGINAL_CONTRACT_CHANGED')
    subset, coordinator = _load_components(contract['dependencies'], original_root)
    _need(original['identity'] == subset.digest({'date': original['date'], 'node': original['node'],
                                                 'inputs': original['input_refs']}), 'ORIGINAL_IDENTITY')
    _need(original_contract.get('source_date') == binding['data_date'], 'ORIGINAL_SOURCE_DATE')
    available = subset.aware(original_contract['available_after'])
    _need(available <= now, 'SOURCE_NOT_AVAILABLE')
    for ref in original['input_refs'] + original['code_refs']:
        _read_pin(ref, original_root)
    _need(isinstance(registration.owner, OwnerHooks) and
          registration.owner.identity == contract['owner_identity'] and
          callable(registration.owner.guard) and callable(registration.owner.execute_subset),
          'ORIGINAL_OWNER_HOOKS_REQUIRED')
    root = _ledger_identity(contract)
    review_ref = registration.reconciliation_refs.get(node)
    _need(review_ref is not None, 'NODE_RECONCILIATION_NOT_REGISTERED')
    raw = _read_pin(review_ref, original_root)
    outputs = _OutputBytes(registration.success_output_refs, original_root)
    plan = subset.plan(binding, raw, review_ref.sha256, outputs, node, now)
    return contract, binding, root, raw, review_ref, outputs, plan, coordinator, now


def dispatch(node_id, run_id, environment_id, *, execute=False):
    """Use the existing node IDs and schedules; default is read-only planning.

    No state-dir, clock, argv, resource floor, proof or owner override is accepted
    from a request. Unregistered runs are refused before any path is read.
    """
    flags = {'production_allowed': False, 'business_accepted': False, 'natural_verified': False}
    if node_id not in NODES:
        return {'status': 'BLOCKED', 'reason': 'RETRY_NODE_REQUIRED', **flags}
    matches = [r for r in TRUSTED_RUNS if r.run_id == run_id and r.environment_id == environment_id]
    if len(matches) != 1:
        return {'status': 'BLOCKED', 'reason': 'NO_REVIEWED_SUBSET_BINDING', **flags}
    registration, phase = matches[0], 'PREFLIGHT'
    try:
        _need(type(execute) is bool, 'EXPLICIT_BOOLEAN_EXECUTE_REQUIRED')
        (contract, binding, root, raw, review_ref, outputs, candidate,
         coordinator, now) = _preflight(registration, node_id)
        if not execute:
            return {'status': 'PLAN_ONLY_NOT_EXECUTED', 'plan': candidate, **flags}
        # The original owner lock/source/calendar/start/runtime gates surround
        # the shared retry ledger. The candidate never invents replacement gates.
        with registration.owner.guard(binding['original_binding']) as monitor:
            _need(callable(monitor), 'ORIGINAL_MONITOR_REQUIRED')
            def pulse():
                _need(monitor() is None, 'ORIGINAL_MONITOR_RETURN_CONTRACT')
            pulse()
            second = _preflight(registration, node_id)
            _need(second[0] == contract and second[6]['intent_id'] == candidate['intent_id'],
                  'PREFLIGHT_CHANGED_UNDER_OWNER_LOCK')
            _ledger_identity(contract)
            context = {'schema': 'RETRY_SUBSET_OWNER_ATTEMPT_V1',
                       'binding': binding, 'owner_identity': registration.owner.identity,
                       'attempt_id': candidate['intent_id'],
                       'attempt_ordinal': candidate['next_attempt_ordinal'],
                       'node_id': node_id, 'environment_id': environment_id,
                       'entry_contract_ref': registration.contract_ref.as_dict(),
                       'reconciliation_ref': review_ref.as_dict()}
            def owner_call(symbols):
                pulse()
                result = registration.owner.execute_subset(symbols, _json(
                    json.dumps(context, allow_nan=False).encode()), pulse)
                pulse()
                _ledger_identity(contract)
                # Input/code/review drift after side effects stays UNKNOWN.
                after = _preflight(registration, node_id)
                _need(after[0] == contract and after[6]['intent_id'] == candidate['intent_id'],
                      'DEPENDENCY_CHANGED_DURING_OWNER')
                return result
            c = coordinator.Coordinator(root)
            try:
                phase = 'CLAIM_OR_EXECUTION'
                result = c.execute(binding, raw, review_ref.sha256, outputs, node_id, now, owner_call)
            finally:
                c.close()
            pulse()
        return {**result, 'entry_contract_sha256': registration.contract_ref.sha256, **flags}
    except Exception as error:
        # No exception path fabricates a clean failure or independent review.
        return {'status': ('UNKNOWN_RECONCILIATION_REQUIRED' if phase == 'CLAIM_OR_EXECUTION'
                           else 'BLOCKED'), 'reason': type(error).__name__ + ':' + str(error),
                'phase': phase, **flags}

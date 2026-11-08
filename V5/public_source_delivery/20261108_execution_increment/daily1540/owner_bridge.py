"""New owner-internal integration of recovered stages and persisted checkpoints.

This is OWNER_STAGE_BRIDGE_V1, not the recovered original latest109 or an
admission registry. Only reviewed owner startup code may populate TRUSTED_RUNS.
Requests contain identifiers/stage only; no JSON runtime, approval flag, source
reference or recipient can construct an owner here. No automatic stage chaining.

The enclosing owner retains its canonical locks, monitor, native runner, writer,
attempt ledger, failure reconciliation and independent sealing. This module never
creates a replacement lock or removes an unknown one. It does not collect data.
"""
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types


IMPLEMENTATION = 'OWNER_STAGE_BRIDGE_V1_NEW_IMPLEMENTATION'
STAGES_SHA256 = '827ee261ad7b7ef978ddb89d1e4eeba5e8c2081e6a73a01bc94633e4ffe055cd'
TRUSTED_RUNS = {}
STAGES = ('compute_persist', 'finalize', 'select')
FLAGS = {'production_allowed': False, 'business_accepted': False,
         'natural_verified': False, 'original_owner_restored': False}
_STAGE_MODULE = None


def _need(ok, reason):
    if not ok:
        raise ValueError(reason)


def _error_reason_after_reconciliation(error):
    """Best-effort display only, after the owner's context saw the primary."""
    try:
        return str(error)
    except BaseException:
        return 'EXCEPTION_TEXT_UNAVAILABLE_PRIMARY_PRESERVED'


def _key(ref):
    return json.dumps(ref, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _pin(ref):
    return (isinstance(ref, dict) and isinstance(ref.get('path'), str) and bool(ref['path'])
            and type(ref.get('bytes')) is int and ref['bytes'] > 0
            and isinstance(ref.get('sha256'), str) and len(ref['sha256']) == 64
            and all(c in '0123456789abcdef' for c in ref['sha256']))


def _check_gate(gate):
    verdict = gate()
    _need(verdict is None or verdict is True, 'ORIGINAL_RESOURCE_GATE_REJECTED')


def _stages():
    global _STAGE_MODULE
    path = Path(__file__).with_name('stages.py')
    raw = path.read_bytes()
    _need(hashlib.sha256(raw).hexdigest() == STAGES_SHA256, 'STAGE_CODE_PIN')
    if _STAGE_MODULE is None:
        name = 'daily1540_verified_stages_' + STAGES_SHA256[:16]
        module = types.ModuleType(name)
        module.__file__ = str(path)
        sys.modules[name] = module  # dataclasses requires the defining module.
        exec(compile(raw, str(path), 'exec'), module.__dict__)
        _STAGE_MODULE = module
    return _STAGE_MODULE


class _GatedRuntime:
    def __init__(self, owner_runtime, lock_guard=None):
        self._owner = owner_runtime
        self._lock_guard = lock_guard

    def __getattr__(self, name):
        return getattr(self._owner, name)

    def gate(self):
        _check_gate(self._owner.gate)
        if self._lock_guard is not None:
            self._lock_guard()


class _BoundRuntime(_GatedRuntime):
    def __init__(self, owner_runtime, checkpoint_binding, lock_guard=None):
        super().__init__(owner_runtime, lock_guard)
        self._binding = checkpoint_binding
        self._bound_refs = set()

    def bound_checkpoint_ref(self, prior_selection):
        self.gate()
        ref = self._binding.bound_checkpoint_ref(prior_selection)
        self._bound_refs.add(_key(ref))
        return ref

    def checked(self, ref):
        self.gate()
        if _key(ref) in self._bound_refs:
            return self._binding.checked(ref)
        return self._owner.checked(ref)


def bind_runtime(owner_runtime, checkpoint_binding, *, lock_guard=None):
    """Adapt services already owned by the original owner; never create authority.

    The direct Python API is private. Registered dispatch additionally verifies
    the canonical lock bindings and held descriptors at every stage gate.
    """
    methods = ('gate', 'completed', 'verify_completed', 'verify_inputs', 'started',
               'checked', 'compute', 'save', 'connection',
               'remove_committed_temporary_links', 'receipt_ref')
    _need(all(callable(getattr(owner_runtime, name, None)) for name in methods),
          'ORIGINAL_OWNER_SERVICES_REQUIRED')
    _need(callable(getattr(getattr(owner_runtime, 'provider', None), 'prepare', None))
          and callable(getattr(getattr(owner_runtime, 'writer', None), 'write_stock', None))
          and all(hasattr(owner_runtime, name) for name in ('monitor', 'mods', 'schema', 'parquet_dir', 'flags')),
          'ORIGINAL_OWNER_SERVICES_REQUIRED')
    _need(callable(getattr(checkpoint_binding, 'bound_checkpoint_ref', None))
          and callable(getattr(checkpoint_binding, 'checked', None)), 'CHECKPOINT_BINDING_REQUIRED')
    runtime = _BoundRuntime(owner_runtime, checkpoint_binding, lock_guard)
    runtime.gate()
    return runtime


def compute_for_original_owner(compute, checkpoint_binding, prior_selection, gate):
    """Return the unchanged daily_owner.compute_prepared callable signature.

    The saved checkpoint snapshot supplies V2's keyword; current rows never create
    a missing checkpoint. Invoke within the original owner's held lock/monitor.
    """
    _need(callable(compute) and callable(gate), 'ORIGINAL_OWNER_SERVICES_REQUIRED')
    _need(callable(getattr(checkpoint_binding, 'bound_checkpoint_ref', None))
          and callable(getattr(checkpoint_binding, 'checked', None)), 'CHECKPOINT_BINDING_REQUIRED')
    prior = copy.deepcopy(prior_selection)
    _check_gate(gate)
    checkpoint_binding.bound_checkpoint_ref(prior)  # Refuse absent owner registration now.
    runtime = types.SimpleNamespace(compute=compute,
        bound_checkpoint_ref=checkpoint_binding.bound_checkpoint_ref, checked=checkpoint_binding.checked)

    def original_signature(rows, context, prior_state=None):
        _check_gate(gate)
        result = _stages().compute_with_checkpoint(
            {'rows': rows, 'context': context, 'prior_component_state': prior_state}, prior, runtime)
        _check_gate(gate)
        return result
    return original_signature


def advance_from_owner(owner_runtime, checkpoint_binding, *, symbol, target_date,
                       prior_selection, input_ref, expected_input_sha256, lock_guard=None):
    """Run one registered stock; preserve its Attempt on exceptions for owner E1.

    A returned persisted result still awaits owner seal and independent review.
    This function neither creates a task nor seals a successful business result.
    """
    runtime = bind_runtime(owner_runtime, checkpoint_binding, lock_guard=lock_guard)
    stage = _stages()
    attempt = stage.Attempt(symbol, target_date)
    try:
        result = stage.advance_stock(attempt, runtime, prior_selection, input_ref, expected_input_sha256)
    except BaseException as error:
        error.daily1540_attempt = attempt
        raise
    return {'symbol': symbol, 'target_date': target_date, 'phase': attempt.phase,
            'result_ref': result, 'events': list(attempt.events), **FLAGS}


def _verify_held_locks(bindings, held):
    """Check the original monitor's tuples without substituting lock paths."""
    _need(isinstance(bindings, (list, tuple)) and bool(bindings)
          and isinstance(held, (list, tuple)) and len(bindings) == len(held), 'ORIGINAL_LOCK_BINDING_REQUIRED')
    declared = {}
    for entry in bindings:
        _need(isinstance(entry, dict) and isinstance(entry.get('path'), str)
              and type(entry.get('device')) is int and type(entry.get('inode')) is int,
              'ORIGINAL_LOCK_BINDING_REQUIRED')
        path = Path(entry['path'])
        _need(path.is_absolute() and path == path.resolve() and str(path) not in declared,
              'ORIGINAL_LOCK_PATH')
        declared[str(path)] = (entry['device'], entry['inode'])
    seen = set()
    for proof in held:
        _need(isinstance(proof, (list, tuple)) and len(proof) == 4, 'ORIGINAL_LOCK_DESCRIPTOR')
        path, fd, device, inode = proof
        path = Path(path)
        _need(str(path) in declared and str(path) not in seen and type(fd) is int,
              'ORIGINAL_LOCK_PATH')
        seen.add(str(path))
        expected = declared[str(path)]
        opened = os.fstat(fd)
        linked = path.stat(follow_symlinks=False)
        _need(stat.S_ISREG(opened.st_mode) and stat.S_ISREG(linked.st_mode)
              and expected == (device, inode) == (opened.st_dev, opened.st_ino)
              == (linked.st_dev, linked.st_ino), 'ORIGINAL_LOCK_IDENTITY_CHANGED')
        probe = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            try:
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise ValueError('ORIGINAL_LOCK_NOT_HELD')
        finally:
            os.close(probe)
        # A blocked probe proves that *some* open description holds the lock.
        # Confirm the supplied owner's description can retain it; a separately
        # opened, unlocked fd for the same inode must not borrow that evidence.
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('ORIGINAL_OWNER_DESCRIPTOR_NOT_LOCKED') from error


def _validate_record(record):
    _need(isinstance(record, dict) and record.get('stage') in STAGES, 'OWNER_STAGE')
    for name in ('owner_context', 'verify_contracts'):
        _need(callable(record.get(name)), 'ORIGINAL_OWNER_SERVICES_REQUIRED')
    _need(isinstance(record.get('lock_bindings'), (tuple, list)) and bool(record['lock_bindings']),
          'ORIGINAL_LOCK_BINDING_REQUIRED')
    for name in ('source_contract_ref', 'source_review_ref', 'calendar_ref'):
        _need(_pin(record.get(name)), 'OWNER_PIN_REQUIRED:' + name)
    if record['stage'] == 'compute_persist':
        _need(callable(record.get('runtime_for_item')) and record.get('checkpoint_binding') is not None,
              'ORIGINAL_OWNER_SERVICES_REQUIRED')
        items = record.get('items')
        _need(isinstance(items, (tuple, list)) and bool(items), 'OWNER_FIXED_INPUT_SCOPE_REQUIRED')
        seen = set()
        for item in items:
            _need(isinstance(item, dict) and isinstance(item.get('symbol'), str)
                  and bool(item['symbol']) and item['symbol'] not in seen
                  and type(item.get('target_date')) is int and isinstance(item.get('prior_selection'), dict)
                  and _pin(item.get('input_ref'))
                  and item.get('expected_input_sha256') == item['input_ref']['sha256'], 'OWNER_INPUT_BINDING')
            seen.add(item['symbol'])
    elif record['stage'] == 'finalize':
        for name in ('prior_catalog_ref', 'owner_manifest_ref', 'independent_sample_ref'):
            _need(_pin(record.get(name)), 'OWNER_PIN_REQUIRED:' + name)
        _need(record.get('owner_runtime') is not None and record.get('destination') is not None,
              'FINALIZER_BINDING_REQUIRED')
    else:
        for name in ('catalog_ref', 'selection_review_ref'):
            _need(_pin(record.get(name)), 'OWNER_PIN_REQUIRED:' + name)
        args = record.get('selector_args')
        _need(record.get('owner_runtime') is not None and getattr(args, 'execute', None) is True
              and getattr(args, 'review', None) is not None, 'SELECTION_REVIEW_REQUIRED')


def dispatch(run_id, environment_id, stage=None):
    """Dispatch one independently registered stage using existing owner services.

    verify_contracts must check the source/calendar/review, immutable runtime/code
    and all stage arguments under the original owner lock. For finalize it must
    bind the actual terminal owner manifest and independent sample; for select it
    must bind the finalized catalog and original selector review/arguments.
    A callback that returns approval booleans is not the verifier contract.
    """
    result = {'status': 'BLOCKED_NO_TRUSTED_OWNER_BINDING', 'jobs_started': 0,
              'stage_calls': 0, 'items': [], 'source_fetches': 0, **FLAGS}
    if not isinstance(run_id, str) or not isinstance(environment_id, str):
        return result
    record = TRUSTED_RUNS.get((run_id, environment_id))
    if record is None:
        return result
    if not isinstance(record, dict) or (stage is not None and stage != record.get('stage')):
        return dict(result, status='BLOCKED_OWNER_STAGE')
    try:
        _validate_record(record)
        stage_code = _stages()
        with record['owner_context']() as held:
            lock_guard = lambda: _verify_held_locks(record['lock_bindings'], held)
            lock_guard()
            _need(record['verify_contracts'](record) is None, 'OWNER_VERIFIER_PROTOCOL')
            selected_stage = record['stage']
            if selected_stage == 'compute_persist':
                for item in record['items']:
                    lock_guard()
                    runtime = record['runtime_for_item'](item)
                    result['stage_calls'] += 1
                    try:
                        value = advance_from_owner(runtime, record['checkpoint_binding'],
                                                   lock_guard=lock_guard, **item)
                    except Exception as error:
                        attempt = getattr(error, 'daily1540_attempt', None)
                        result['jobs_started'] += int(bool(attempt and attempt.events))
                        value = {'symbol': item['symbol'], 'target_date': item['target_date'],
                                 'phase': getattr(attempt, 'phase', 'BLOCKED_BEFORE_STAGE'),
                                 'error_type': type(error).__name__,
                                 'reason': 'OWNER_STAGE_EXCEPTION_REQUIRES_RECONCILIATION',
                                 'automatic_retry_allowed': False}
                        result['items'].append(value)
                        result.update(status='UNKNOWN_RECONCILIATION_REQUIRED',
                                      automatic_retry_allowed=False)
                        # Let the original owner's context observe the exact error
                        # and attached Attempt before it reconciles/releases locks.
                        # UNKNOWN stops this shared side-effect chain, not other jobs.
                        raise
                    else:
                        result['jobs_started'] += int(value['phase'] != 'REUSE_COMPLETED_NO_RECOMPUTE')
                    result['items'].append(value)
                result['status'] = ('UNKNOWN_RECONCILIATION_REQUIRED'
                    if any('error_type' in item for item in result['items'])
                    else 'OWNER_STAGES_AWAIT_SEAL_AND_INDEPENDENT_REVIEW')
            else:
                runtime = _GatedRuntime(record['owner_runtime'], lock_guard)
                _need(callable(getattr(runtime, 'gate', None))
                      and callable(getattr(runtime, 'checked', None)), 'ORIGINAL_OWNER_SERVICES_REQUIRED')
                runtime.gate()
                result['stage_calls'] += 1
                if selected_stage == 'finalize':
                    _need(callable(getattr(getattr(runtime, 'finalizer', None), 'build', None))
                          and callable(getattr(runtime.finalizer, 'write_new', None)), 'FINALIZER_BINDING_REQUIRED')
                    result['result_ref'] = stage_code.finalize_reviewed_catalog(runtime,
                        record['prior_catalog_ref'], record['owner_manifest_ref'],
                        record['independent_sample_ref'], record['destination'])
                    result['status'] = 'CATALOG_WRITTEN_AWAIT_DOWNSTREAM_REVIEW'
                else:
                    _need(callable(getattr(getattr(runtime, 'selector', None), 'run', None)),
                          'SELECTOR_BINDING_REQUIRED')
                    result['result'] = stage_code.select_reviewed_catalog(runtime, record['selector_args'])
                    result['status'] = 'SELECTOR_RETURNED_AWAIT_DOWNSTREAM_REVIEW'
            lock_guard()
            _need(record['verify_contracts'](record) is None, 'OWNER_VERIFIER_PROTOCOL')
    except Exception as error:
        result.update(status='UNKNOWN_RECONCILIATION_REQUIRED' if result['stage_calls']
                      else 'BLOCKED_OWNER_CONTRACT', error_type=type(error).__name__,
                      reason=_error_reason_after_reconciliation(error),
                      automatic_retry_allowed=False)
    return result

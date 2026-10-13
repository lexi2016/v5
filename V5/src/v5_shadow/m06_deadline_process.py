"""Bound the fixed M06 owner's inherited POSIX process group.

The caller's request/replay clock is never accepted here. Actual UTC and a
monotonic timeout are checked throughout execution. Only the fresh group created
by this call is signalled, while its unreaped leader pins the group identity.
The pinned owner must not detach descendants or have another waiter reap it.

This is not a hard real-time OS guarantee: process creation, scheduling and
uninterruptible kernel work can delay observation or SIGKILL. Cleanup has a
separate 1.5-second observation/drain budget; inability to verify it is UNKNOWN.
UNKNOWN must retain the caller's RUNNING ledger and previous successful product.
No retry/rollback or success publication is performed here.
"""
from datetime import datetime, timezone
import math
import os
import selectors
import signal
import subprocess
import time

from .digests import MAX_JSON_BYTES

_CLEANUP_SECONDS = 1.5
_POLL_SECONDS = .05


class BoundedProcessError(TimeoutError):
    """The caller must treat the owner's side effects/outcome as UNKNOWN."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__('M06_EXECUTION_OUTCOME_UNKNOWN:' + reason)


def _utc_now():
    return datetime.now(timezone.utc)


def _remaining(deadline, timeout_at):
    wall = (deadline - _utc_now()).total_seconds()
    if wall <= 0:
        raise BoundedProcessError('DEADLINE_EXPIRED')
    monotonic = timeout_at - time.monotonic()
    if monotonic <= 0:
        raise BoundedProcessError('TIMEOUT_EXPIRED')
    return min(wall, monotonic)


def _members(pgid, timeout):
    # POSIX has no group-member enumeration call. Read only group identity and
    # state from the fixed system utility; never traverse or signal listed PIDs.
    result = subprocess.run(['/bin/ps', '-A', '-o', 'pid=,pgid=,stat='],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
        timeout=min(.25, timeout), check=True)
    members = {}
    for line in result.stdout.splitlines():
        pid, group, state = line.split()
        if int(group) == pgid:
            members[int(pid)] = state
    if pgid not in members:
        raise BoundedProcessError('GROUP_LEADER_OWNERSHIP_LOST')
    return members


def run_bounded(argv, *, input_bytes, timeout_seconds, execution_deadline):
    """Return binary CompletedProcess or raise UNKNOWN after owned-group cleanup.

    Requires POSIX waitid/WNOWAIT (including the pinned macOS Python 3.13 runtime)
    and /bin/ps. stdout/stderr are individually capped at MAX_JSON_BYTES. Normal
    nonzero exit codes are returned unchanged, but leaked live descendants fail.
    KeyboardInterrupt/SystemExit are re-raised after cleanup; ordinary execution
    exceptions become BoundedProcessError. Invalid arguments never launch.
    """
    if not isinstance(execution_deadline, datetime) or execution_deadline.utcoffset() is None:
        raise ValueError('M06_EXECUTION_DEADLINE_MUST_BE_AWARE')
    if not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError('M06_EXECUTION_TIMEOUT_INVALID')
    if not isinstance(input_bytes, bytes) or len(input_bytes) > MAX_JSON_BYTES:
        raise ValueError('M06_EXECUTION_INPUT_INVALID')
    if not isinstance(argv, (list, tuple)) or not argv:
        raise ValueError('M06_EXECUTION_ARGV_INVALID')
    if os.name != 'posix' or not all(hasattr(os, key) for key in ('waitid', 'WNOWAIT')):
        raise BoundedProcessError('PROCESS_GROUP_RUNTIME_UNSUPPORTED')
    if signal.getsignal(signal.SIGCHLD) == signal.SIG_IGN:
        raise BoundedProcessError('CHILD_REAP_OWNERSHIP_UNAVAILABLE')
    started = time.monotonic()
    initial_deadline_budget = (execution_deadline - _utc_now()).total_seconds()
    if initial_deadline_budget <= 0:
        raise BoundedProcessError('DEADLINE_EXPIRED')
    # A later wall-clock rollback must never extend the initial UTC budget.
    timeout_at = started + min(timeout_seconds, initial_deadline_budget)
    _remaining(execution_deadline, timeout_at)
    process = None
    buffers = {'stdout': bytearray(), 'stderr': bytearray()}
    pending = memoryview(input_bytes)

    with selectors.DefaultSelector() as selector:
        def close_pipe(pipe):
            try:
                selector.unregister(pipe)
            except KeyError:
                pass
            pipe.close()

        def pump(wait, collecting=True):
            nonlocal pending
            for key, event in selector.select(wait):
                pipe, name = key.fileobj, key.data
                try:
                    if name == 'stdin':
                        pending = pending[os.write(pipe.fileno(), pending[:65536]):]
                        if not pending:
                            close_pipe(pipe)
                    else:
                        chunk = os.read(pipe.fileno(), 65536)
                        if not chunk:
                            close_pipe(pipe)
                        elif collecting:
                            buffers[name].extend(chunk)
                            if len(buffers[name]) > MAX_JSON_BYTES:
                                raise BoundedProcessError('OUTPUT_LIMIT_EXCEEDED')
                except BrokenPipeError:
                    close_pipe(pipe)
                except BlockingIOError:
                    pass

        def cleanup():
            # Never signal after reaping: that would allow PID/group-ID reuse.
            if process is None or process.returncode is not None:
                return
            until = time.monotonic() + _CLEANUP_SECONDS
            if os.getpgid(process.pid) != process.pid:
                raise BoundedProcessError('GROUP_LEADER_OWNERSHIP_LOST')
            os.killpg(process.pid, signal.SIGKILL)
            if not process.stdin.closed:
                close_pipe(process.stdin)
            try:
                while True:
                    left = until - time.monotonic()
                    if left <= 0:
                        raise BoundedProcessError('CLEANUP_NOT_CONFIRMED')
                    members = _members(process.pid, left)
                    if all(state.startswith(b'Z') for state in members.values()):
                        break
                    pump(min(_POLL_SECONDS, left), collecting=False)
            finally:
                # A failed membership probe still must not skip draining/reaping.
                # No group signals occur after this point, including on failure.
                try:
                    while selector.get_map() and time.monotonic() < until:
                        pump(min(_POLL_SECONDS, max(0, until - time.monotonic())), collecting=False)
                finally:
                    process.wait(timeout=max(.001, until - time.monotonic()))
                if selector.get_map():
                    raise BoundedProcessError('PIPE_DRAIN_NOT_CONFIRMED')

        try:
            process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, shell=False, start_new_session=True, bufsize=0)
            _remaining(execution_deadline, timeout_at)
            for name in ('stdin', 'stdout', 'stderr'):
                pipe = getattr(process, name)
                os.set_blocking(pipe.fileno(), False)
                if name == 'stdin' and not pending:
                    pipe.close()
                else:
                    selector.register(pipe, selectors.EVENT_WRITE if name == 'stdin' else selectors.EVENT_READ, name)
            while True:
                left = _remaining(execution_deadline, timeout_at)
                exited = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                if exited is not None:
                    members = _members(process.pid, left)
                    if any(pid != process.pid and not state.startswith(b'Z') for pid, state in members.items()):
                        raise BoundedProcessError('DESCENDANT_LEAK')
                    if not selector.get_map():
                        code = process.wait(timeout=_remaining(execution_deadline, timeout_at))
                        _remaining(execution_deadline, timeout_at)
                        return subprocess.CompletedProcess(argv, code, bytes(buffers['stdout']), bytes(buffers['stderr']))
                pump(min(_POLL_SECONDS, _remaining(execution_deadline, timeout_at)))
        except BaseException as error:
            try:
                cleanup()
            except Exception as cleanup_error:
                raise BoundedProcessError('CLEANUP_NOT_CONFIRMED:' + type(cleanup_error).__name__) from error
            if isinstance(error, (BoundedProcessError, KeyboardInterrupt, SystemExit)):
                raise
            raise BoundedProcessError('PROCESS_ERROR:' + type(error).__name__) from error
        finally:
            if process is not None:
                for name in ('stdin', 'stdout', 'stderr'):
                    pipe = getattr(process, name)
                    if pipe is not None and not pipe.closed:
                        pipe.close()

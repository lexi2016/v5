"""Real isolated POSIX writers: no source-owner, service, or trading calls."""
from datetime import datetime, timedelta, timezone
import importlib
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'src'))

# Each generation inherits the initial owner's process group and writes its own
# heartbeat. A leaked descendant can close both pipes and still mutate files.
WRITER = '''import os,subprocess,sys,time
from pathlib import Path
root=Path(sys.argv[1]); role=sys.argv[2]; mode=sys.argv[3]
(root/(role+'.pid')).write_text(str(os.getpid()))
if role in ('owner','child'):
    next_role='child' if role=='owner' else 'grandchild'
    streams={'stdout':subprocess.DEVNULL,'stderr':subprocess.DEVNULL} if mode=='closed_leak' else {}
    subprocess.Popen([sys.executable,'-I','-B',__file__,str(root),next_role,mode],**streams)
if role=='owner' and mode in ('leak','closed_leak'):
    while not (root/'grandchild.heartbeat').exists(): time.sleep(.005)
    print('owner finished',flush=True)
    sys.exit(0)
while True:
    with (root/(role+'.heartbeat')).open('ab',buffering=0) as handle: handle.write(b'x')
    time.sleep(.005)
'''


@unittest.skipUnless(os.name == 'posix', 'Fresh session/process-group contract is POSIX only')
class M06DeadlineProcessTests(unittest.TestCase):
    def setUp(self):
        try:
            self.guard = importlib.import_module('v5_shadow.m06_deadline_process')
        except ImportError as error:
            self.fail('Bounded M06 owner runner is not implemented: ' + str(error))
        self.temp = tempfile.TemporaryDirectory(prefix='m06-deadline-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.script = self.root / 'writer.py'
        self.script.write_text(WRITER)
        self.spawned = []
        real_popen = subprocess.Popen

        def track(*args, **kwargs):
            proc = real_popen(*args, **kwargs)
            if kwargs.get('start_new_session'):
                self.spawned.append(proc)
            return proc

        self.addCleanup(self.cleanup_owned)
        self.popen = patch.object(self.guard.subprocess, 'Popen', side_effect=track)
        self.popen.start()
        self.addCleanup(self.popen.stop)

    def cleanup_owned(self):
        for proc in self.spawned:
            # Emergency fixture cleanup only while its leader is still ours.
            if proc.returncode is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=2)
                for pipe in (proc.stdin, proc.stdout, proc.stderr):
                    if pipe is not None and not pipe.closed:
                        pipe.close()

    def deadline(self, seconds=5):
        return datetime.now(timezone.utc) + timedelta(seconds=seconds)

    def run_writer(self, mode='running', **kwargs):
        return self.guard.run_bounded(
            [sys.executable, '-I', '-B', str(self.script), str(self.root), 'owner', mode],
            input_bytes=b'', timeout_seconds=kwargs.pop('timeout_seconds', 3),
            execution_deadline=kwargs.pop('execution_deadline', self.deadline()), **kwargs)

    def assert_writers_stopped(self):
        paths = [self.root / (role + '.heartbeat') for role in ('child', 'grandchild')]
        self.assertTrue(all(path.is_file() for path in paths), 'Real descendants must have started')
        before = [path.stat().st_size for path in paths]
        time.sleep(.12)
        self.assertEqual([path.stat().st_size for path in paths], before)
        self.assertTrue(self.spawned)
        for proc in self.spawned:
            self.assertIsNotNone(proc.returncode, 'Owned leader must have been reaped')

    def test_success_preserves_binary_input_stdout_stderr_and_exit_code(self):
        argv = [sys.executable, '-I', '-B', '-c',
                'import sys; data=sys.stdin.buffer.read(); sys.stdout.buffer.write(data[::-1]); '
                'sys.stderr.buffer.write(b"diagnostic"); sys.exit(7)']
        result = self.guard.run_bounded(argv, input_bytes=b'\x00hello\xff',
            timeout_seconds=3, execution_deadline=self.deadline())
        self.assertIsInstance(result, subprocess.CompletedProcess)
        self.assertEqual(result.args, argv)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (7, b'\xffolleh\x00', b'diagnostic'))

    def test_expired_deadline_never_starts_owner(self):
        marker = self.root / 'must-not-exist'
        with self.assertRaisesRegex(self.guard.BoundedProcessError, 'OUTCOME_UNKNOWN.*DEADLINE'):
            self.guard.run_bounded([sys.executable, '-c', 'open(__import__("sys").argv[1],"w").close()', str(marker)],
                input_bytes=b'', timeout_seconds=3, execution_deadline=self.deadline(-1))
        self.assertFalse(marker.exists())
        self.assertEqual(self.spawned, [])

    def test_execution_deadline_stops_child_grandchild_and_keeps_sentinel_alive(self):
        sentinel = subprocess.Popen([sys.executable, '-I', '-B', '-c', 'import time;time.sleep(30)'])
        self.addCleanup(lambda: (sentinel.kill(), sentinel.wait()) if sentinel.poll() is None else None)
        before = time.monotonic()
        with self.assertRaisesRegex(self.guard.BoundedProcessError, 'OUTCOME_UNKNOWN.*DEADLINE'):
            self.run_writer(execution_deadline=self.deadline(.6), timeout_seconds=8)
        self.assertLess(time.monotonic() - before, 3)
        self.assert_writers_stopped()
        self.assertIsNone(sentinel.poll(), 'Unrelated process must remain alive')

    def test_timeout_is_independent_of_later_execution_deadline(self):
        before = time.monotonic()
        with self.assertRaisesRegex(self.guard.BoundedProcessError, 'OUTCOME_UNKNOWN.*TIMEOUT'):
            self.run_writer(timeout_seconds=.6, execution_deadline=self.deadline(10))
        self.assertLess(time.monotonic() - before, 3)
        self.assert_writers_stopped()

    def test_parent_success_with_inherited_pipe_writer_is_unknown(self):
        with self.assertRaisesRegex(self.guard.BoundedProcessError, 'OUTCOME_UNKNOWN.*DESCENDANT'):
            self.run_writer(mode='leak')
        self.assert_writers_stopped()

    def test_parent_success_with_closed_pipe_writer_is_unknown(self):
        with self.assertRaisesRegex(self.guard.BoundedProcessError, 'OUTCOME_UNKNOWN.*DESCENDANT'):
            self.run_writer(mode='closed_leak')
        self.assert_writers_stopped()

    def test_keyboard_cancellation_stops_all_owned_writers(self):
        previous = signal.getsignal(signal.SIGALRM)
        def cancel(signum, frame):
            raise KeyboardInterrupt('fixture cancellation')
        signal.signal(signal.SIGALRM, cancel)
        signal.setitimer(signal.ITIMER_REAL, .6)
        try:
            with self.assertRaises(KeyboardInterrupt):
                self.run_writer()
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)
        self.assert_writers_stopped()

    def test_exceptional_inspection_timeout_still_reaps_and_stops_writers(self):
        # Even the observation utility failing must not skip kill/drain/reap.
        with patch.object(self.guard, '_members', side_effect=subprocess.TimeoutExpired('/bin/ps', .1)):
            with self.assertRaisesRegex(self.guard.BoundedProcessError, 'OUTCOME_UNKNOWN.*CLEANUP_NOT_CONFIRMED'):
                self.run_writer(mode='leak')
        self.assert_writers_stopped()

    def test_late_completion_is_unknown_even_after_owner_exits(self):
        inspect = self.guard._members
        def slow_inspection(*args, **kwargs):
            result = inspect(*args, **kwargs)
            time.sleep(.15)
            return result
        with patch.object(self.guard, '_members', side_effect=slow_inspection):
            with self.assertRaisesRegex(self.guard.BoundedProcessError, 'OUTCOME_UNKNOWN.*DEADLINE'):
                self.guard.run_bounded([sys.executable, '-I', '-B', '-c', 'print("done")'],
                    input_bytes=b'', timeout_seconds=3, execution_deadline=self.deadline(.1))
        self.assertTrue(all(proc.returncode is not None for proc in self.spawned))

    def test_output_limit_aborts_and_reaps_actual_writer(self):
        with patch.object(self.guard, 'MAX_JSON_BYTES', 1024):
            with self.assertRaisesRegex(self.guard.BoundedProcessError, 'OUTCOME_UNKNOWN.*OUTPUT_LIMIT'):
                self.guard.run_bounded([sys.executable, '-I', '-B', '-c',
                    'import os,time;os.write(1,b"x"*8192);time.sleep(20)'],
                    input_bytes=b'', timeout_seconds=3, execution_deadline=self.deadline())
        self.assertTrue(all(proc.returncode is not None for proc in self.spawned))

    def test_backward_wall_clock_cannot_extend_initial_deadline_budget(self):
        actual_now = self.guard._utc_now
        calls = 0
        def stepped_back_clock():
            nonlocal calls
            calls += 1
            return actual_now() - (timedelta(days=1) if calls > 1 else timedelta())
        before = time.monotonic()
        with patch.object(self.guard, '_utc_now', side_effect=stepped_back_clock):
            with self.assertRaisesRegex(self.guard.BoundedProcessError, 'OUTCOME_UNKNOWN.*EXPIRED'):
                self.guard.run_bounded([sys.executable, '-I', '-B', '-c',
                    'import time;time.sleep(2)'], input_bytes=b'', timeout_seconds=5,
                    execution_deadline=self.deadline(.3))
        self.assertLess(time.monotonic() - before, 1.5)
        self.assertTrue(self.spawned)
        self.assertTrue(all(proc.returncode is not None for proc in self.spawned))

    def test_bad_deadline_and_timeout_are_rejected_before_launch(self):
        for deadline, timeout in [(datetime(2030, 1, 1), 1), (self.deadline(), 0),
                                  (self.deadline(), -1), (self.deadline(), math.nan),
                                  (self.deadline(), math.inf)]:
            with self.subTest(deadline=deadline, timeout=timeout):
                with self.assertRaises(ValueError):
                    self.guard.run_bounded([sys.executable, '-c', 'pass'], input_bytes=b'',
                        timeout_seconds=timeout, execution_deadline=deadline)
        self.assertEqual(self.spawned, [])


if __name__ == '__main__':
    unittest.main()

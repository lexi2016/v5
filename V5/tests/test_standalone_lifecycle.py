"""Regression tests for process/root boundaries required by standalone entry."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from v5_shadow import main_runtime

class RuntimeBoundaryTests(unittest.TestCase):
    def config(self,root):
        data=root/'data';data.mkdir();(data/'.v5-module-root').write_text('v5.module-root.v1:p0_test\n')
        return dict(runtime_root=str(root/'runtime'),composition='unused',module_api=dict(schema_version='v5.module_api.v1',module_id='p0_test',release_id='synthetic',data_root=str(data),routes=[]))

    def test_child_config_symlink_cannot_overwrite_external_file(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=self.config(root);runtime=root/'runtime';runtime.mkdir()
            sentinel=root/'sentinel';sentinel.write_text('original')
            (runtime/'module_api_child.json').symlink_to(sentinel)
            with patch.object(main_runtime.subprocess,'Popen',side_effect=AssertionError('must reject before spawn')):
                with self.assertRaises(ValueError):main_runtime.start(config)
            self.assertEqual(sentinel.read_text(),'original')

    def test_child_config_hardlink_cannot_overwrite_external_file(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=self.config(root);runtime=root/'runtime';runtime.mkdir()
            sentinel=root/'sentinel';sentinel.write_text('original')
            os.link(sentinel,runtime/'module_api_child.json')
            with patch.object(main_runtime.subprocess,'Popen',side_effect=AssertionError('must reject before spawn')):
                with self.assertRaises(ValueError):main_runtime.start(config)
            self.assertEqual(sentinel.read_text(),'original')

    def test_child_ignores_poisoned_caller_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=self.config(root);poison=root/'v5_shadow';poison.mkdir()
            (poison/'__init__.py').write_text('')
            (poison/'module_process.py').write_text("raise RuntimeError('CALLER_CWD_EXECUTED')\n")
            cwd=Path.cwd()
            try:
                os.chdir(root)
                result=main_runtime.start(config)
                self.assertEqual(result['status'],'STARTED')
            finally:
                if (root/'runtime/runtime.json').exists():main_runtime.stop(config)
                os.chdir(cwd)

    def test_identity_write_failure_reaps_owned_child(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=self.config(root);children=[]
            real_popen=main_runtime.subprocess.Popen
            def track(*args,**kwargs):
                child=real_popen(*args,**kwargs);children.append(child);return child
            original=main_runtime.canonical_bytes
            def fail_identity(value):
                if value.get('marker')==main_runtime.MARKER:raise OSError('synthetic identity write failure')
                return original(value)
            try:
                with patch.object(main_runtime.subprocess,'Popen',side_effect=track),patch.object(main_runtime,'canonical_bytes',fail_identity):
                    with self.assertRaises(OSError):main_runtime.start(config)
                self.assertTrue(children)
                self.assertIsNotNone(children[0].poll(),'startup failure leaked child')
            finally:
                for child in children:
                    if child.poll() is None:child.terminate()
                    child.wait(timeout=5)
                    if child.stdout:child.stdout.close()
                    if child.stderr:child.stderr.close()

    def test_partial_identity_write_is_removed_and_retry_succeeds(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=self.config(root);original=Path.open
            class BrokenWrite:
                def __init__(self,file):self.file=file
                def __enter__(self):self.file.__enter__();return self
                def __exit__(self,*args):return self.file.__exit__(*args)
                def fileno(self):return self.file.fileno()
                def write(self,data):self.file.write(b'{');raise OSError('partial identity write')
            def broken(path,*args,**kwargs):
                file=original(path,*args,**kwargs)
                return BrokenWrite(file) if path.name=='runtime.json' and args==('xb',) else file
            with patch.object(Path,'open',broken):
                with self.assertRaises(OSError):main_runtime.start(config)
            self.assertFalse((root/'runtime/runtime.json').exists())
            try:self.assertEqual(main_runtime.start(config)['status'],'STARTED')
            finally:main_runtime.stop(config)

    def test_concurrent_starts_leave_exactly_one_owned_child(self):
        import concurrent.futures
        import threading
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=self.config(root);barrier=threading.Barrier(2)
            def start():
                barrier.wait()
                try:return main_runtime.start(config)['status']
                except ValueError as error:return str(error)
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    values=list(pool.map(lambda _:start(),range(2)))
                self.assertEqual(values.count('STARTED'),1,values)
                self.assertTrue(any(x in ('RUNTIME_ALREADY_EXISTS','RUNTIME_START_BUSY') for x in values))
            finally:
                if (root/'runtime/runtime.json').exists():main_runtime.stop(config)

    def test_duplicate_start_preserves_existing_child_handle(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=self.config(root);main_runtime.start(config)
            child=main_runtime._OWNED_CHILDREN[str(root/'runtime/runtime.json')]
            try:
                with self.assertRaisesRegex(ValueError,'RUNTIME_ALREADY_EXISTS'):main_runtime.start(config)
                self.assertIs(main_runtime._OWNED_CHILDREN.get(str(root/'runtime/runtime.json')),child)
            finally:main_runtime.stop(config)
            self.assertIsNotNone(child.poll())
            self.assertTrue(child.stdout.closed)

    def test_stop_and_new_start_share_admission_lock(self):
        import concurrent.futures
        import threading
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=self.config(root);main_runtime.start(config)
            entered=threading.Event();release=threading.Event();original=main_runtime._reap
            def paused(child):
                entered.set();release.wait(5);return original(child)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                with patch.object(main_runtime,'_reap',side_effect=paused):
                    first=pool.submit(main_runtime.stop,config)
                    self.assertTrue(entered.wait(5))
                    second=pool.submit(main_runtime.stop,config)
                    try:
                        with self.assertRaisesRegex(ValueError,'RUNTIME_START_BUSY'):main_runtime.start(config)
                        self.assertFalse(second.done())
                    finally:release.set()
                    self.assertEqual(first.result(timeout=5)['status'],'STOPPED')
                    self.assertEqual(second.result(timeout=5)['status'],'ALREADY_STOPPED')
            try:self.assertEqual(main_runtime.start(config)['status'],'STARTED')
            finally:main_runtime.stop(config)

    def test_silent_child_timeout_is_bounded_and_reaped(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=self.config(root);children=[];original=main_runtime.subprocess.Popen
            def silent(*args,**kwargs):
                child=original([sys.executable,'-I','-B','-c','import time;time.sleep(30)'],**kwargs)
                children.append(child);return child
            started=time.monotonic()
            try:
                with patch.object(main_runtime.subprocess,'Popen',side_effect=silent):
                    with self.assertRaisesRegex(ValueError,'MODULE_API_START_FAILED'):main_runtime.start(config)
                self.assertLess(time.monotonic()-started,16)
                self.assertIsNotNone(children[0].poll())
            finally:
                for child in children:
                    if child.poll() is None:child.terminate()
                    child.wait(timeout=5)

if __name__=='__main__':unittest.main()

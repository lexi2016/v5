"""Read-only page worker isolation, bounded IPC, original gates, and cleanup."""
import json
import multiprocessing
import os
import struct
import shutil
import subprocess
import sys
import time
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
import test_m18_v2_disk_pages as base
from v5_shadow import m18_offline_v2 as m
from v5_shadow import m18_v2_read_process as p


def empty_worker(request, sender):
    sender.close()


def excessive_header_worker(request, sender):
    os.write(sender.fileno(), struct.pack('!I', p.PAGE_RECEIPT_BYTES + 1))
    time.sleep(95)


def slow_worker(request, sender):
    os.write(sender.fileno(), b'\x00')
    time.sleep(95)


def rss_worker(request, sender):
    block = bytearray(m.PROFILE['rss_bytes'])
    sender.send(dict(pid=os.getpid(), status='OK', payload={}))
    assert block is not None


def wrong_page_worker(request, sender):
    from v5_shadow.module_api import _m18_disk_reader
    reader = _m18_disk_reader(request['binding'])
    if request['kind'] == 'content':
        value = reader.content(0);value['index'] = 1
    elif request['kind'] == 'section':
        value = reader.detail('unknown')
    else:
        value = reader.detail('gaps')
    sender.send(dict(pid=os.getpid(), status='OK', payload=value))


class ReadProcessTests(unittest.TestCase):
    setUp = base.DiskPagesTests.setUp
    snapshot = base.DiskPagesTests.snapshot

    def request(self, kind='overview', **query):
        return dict(binding=self.config['m18_v2_binding'], kind=kind, query=query)

    def test_repeated_reads_use_fresh_exited_workers_and_preserve_files(self):
        before = self.snapshot()
        pids = []
        for request in [self.request(), self.request('section', section='gaps'),
                        self.request('content', page=0), self.request()]:
            result = p.run(request)
            self.assertEqual(result['status'], 'OK', result)
            self.assertTrue(result['worker_reaped'])
            self.assertEqual(result['worker_exit'], 0)
            self.assertNotEqual(result['pid'], os.getpid())
            pids.append(result['pid'])
            self.assertEqual(result['payload']['identity'], self.identity)
            m.enforce_usage(result['usage'])
        self.assertEqual(len(set(pids)), 4)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(multiprocessing.active_children())

    def test_each_worker_rereads_disk_and_detects_tampering(self):
        self.assertEqual(p.run(self.request())['status'], 'OK')
        key = json.loads(self.bundle.manifest)['chunks'][0]['object_sha256']
        (self.bundle_root / 'objects' / key).write_bytes(b'{}')
        result = p.run(self.request())
        self.assertEqual(result['status'], 'REJECTED')
        self.assertEqual(result['error'], 'M18_V2_OBJECT_HASH')
        self.assertTrue(result['worker_reaped'])
        self.assertNotIn('payload', result)

    def test_missing_files_keep_not_available_mapping(self):
        request = self.request()
        request['binding'] = dict(request['binding'], bundle_root=str(self.root / 'missing'))
        result = p.run(request)
        self.assertEqual(result['error'], 'MODULE_RESULT_NOT_AVAILABLE')
        self.assertTrue(result['worker_reaped'])

    def test_correct_pins_do_not_accept_wrong_kind_page_or_section(self):
        for request in [self.request(), self.request('content', page=0),
                        self.request('section', section='gaps')]:
            with self.subTest(kind=request['kind']), patch.object(p, '_worker', wrong_page_worker):
                result = p.run(request)
                self.assertEqual(result['status'], 'REJECTED')
                self.assertTrue(result['worker_reaped'])
                self.assertNotIn('payload', result)

    def test_bad_eof_and_oversized_frame_fail_and_reap(self):
        for worker, error in [(empty_worker, 'M18_V2_RECEIPT_EOF'),
                              (excessive_header_worker, 'M18_V2_RECEIPT_LENGTH')]:
            with self.subTest(worker=worker.__name__), patch.object(p, '_worker', worker):
                start = time.monotonic()
                result = p.run(self.request())
                self.assertEqual(result['error'], error)
                self.assertTrue(result['worker_reaped'])
                self.assertNotIn('payload', result)
                self.assertLess(time.monotonic() - start, 5)
        self.assertFalse(multiprocessing.active_children())

    def test_request_and_receipt_are_closed_and_bounded(self):
        for request in [dict(self.request(), output_root=str(self.root)),
                        self.request('build'), self.request('section', section='gaps', extra='x')]:
            with self.subTest(request=request):
                self.assertEqual(p.run(request)['status'], 'REJECTED')
        for value in [dict(pid=1,status='OK',payload={}, extra='x'),
                      dict(pid=1,status='OK',payload={'x':'x' * p.PAGE_RECEIPT_BYTES}),
                      dict(pid=1,status='REJECTED',error='private path')]:
            with self.subTest(keys=list(value)), self.assertRaises(m.ContractError):
                p.encode_page_receipt(value)

    def test_http_heavy_read_slot_is_bounded_and_released_after_error(self):
        from v5_shadow import module_api as api
        from v5_shadow.m18_v2_publication_bridge import ROUTE
        entered = threading.Event();release = threading.Event()
        def blocked(*args):
            entered.set();release.wait(3)
            raise ValueError('SYNTHETIC_READER_FAILURE')
        self.config['routes'] += [ROUTE + '/overview', ROUTE + '/sections']
        base_url = base.DiskPagesTests.serve(self)
        path = ROUTE + '/overview?run_id=' + base.RUN + '&generation_id=' + self.descriptor['generation_id']
        result = []
        with patch.object(api, '_m18_read_value', blocked):
            first = threading.Thread(target=lambda: result.append(base.DiskPagesTests.get(self, base_url, path)))
            first.start()
            self.assertTrue(entered.wait(2))
            self.assertEqual(base.DiskPagesTests.get(self, base_url, path)[0:2],
                             (503, dict(status='CANNOT_CONFIRM', reason_codes=['MODULE_BUSY'], module_id='manager')))
            self.assertEqual(base.DiskPagesTests.get(self, base_url, '/__v5/module-health')[0], 200)
            release.set();first.join(3)
        self.assertEqual(result[0][0], 409)
        self.assertEqual(base.DiskPagesTests.get(self, base_url, path)[0], 200)

    def test_library_service_without_B_does_not_write_source_on_get(self):
        from v5_shadow.m18_v2_publication_bridge import ROUTE
        source = self.root / 'isolated-source'
        shutil.copytree(Path(m.__file__).parent, source / 'v5_shadow',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        config = dict(self.config, routes=self.config['routes'] + [ROUTE + '/overview'])
        config_path = self.root / 'config.json';config_path.write_text(json.dumps(config))
        script = '''
import hashlib,json,os,sys,threading
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from v5_shadow.module_api import create_module_server,M18_ROUTE
from v5_shadow.m18_offline_v2 import generation
assert not sys.flags.dont_write_bytecode
config=json.loads(Path(sys.argv[1]).read_bytes())
server=create_module_server(config)
source=Path(sys.argv[2])
def snapshot():
 return {str(p.relative_to(source)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns) for p in source.rglob('*') if p.is_file()}
before=snapshot();thread=threading.Thread(target=server.serve_forever);thread.start()
try:
 query=urlencode(dict(run_id=config['m18_v2_binding']['identity']['run_id'],generation_id=generation(config['m18_v2_binding']['identity'])))
 with urlopen('http://127.0.0.1:'+str(server.server_address[1])+M18_ROUTE+'/overview?'+query,timeout=10) as r:
  assert r.status==200;r.read()
finally:server.shutdown();server.server_close();thread.join(2)
assert before==snapshot()
assert not thread.is_alive()
print('NO_GET_SOURCE_WRITES')
'''
        env = dict(os.environ, PYTHONPATH=str(source));env.pop('PYTHONDONTWRITEBYTECODE', None)
        result = subprocess.run([sys.executable, '-c', script, str(config_path), str(source)],
                                env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('NO_GET_SOURCE_WRITES', result.stdout)

    @unittest.skipUnless(os.environ.get('M18_READ_PROCESS_STRESS'), 'opt-in original RSS and 90s wall gates')
    def test_actual_rss_and_wall_failure_reap(self):
        for worker, code in [(rss_worker, 'M18_V2_RESOURCE_PEAK_RSS_BYTES'),
                             (slow_worker, 'M18_V2_RESOURCE_WALL_SECONDS')]:
            with self.subTest(worker=worker.__name__), patch.object(p, '_worker', worker):
                result = p.run(self.request())
                self.assertEqual(result['status'], 'REJECTED', result)
                self.assertEqual(result['error'], code)
                self.assertTrue(result['worker_reaped'])
                self.assertNotIn('payload', result)
        self.assertFalse(multiprocessing.active_children())

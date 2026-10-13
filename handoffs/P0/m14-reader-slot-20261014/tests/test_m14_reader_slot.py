"""Synthetic M14 slot lifecycle regression: real bounded reader, loopback HTTP only."""
import concurrent.futures
import hashlib
import http.client
import inspect
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen
import weakref

ROOT=Path(sys.argv.pop(1)).resolve()
sys.path[:0]=[str(ROOT/'V5/src'),str(ROOT/'V5/tests')]
from v5_shadow import module_api
import test_m14_saved_rebound as fixture_module
ROUTE=fixture_module.ROUTE
SOURCE=Path(module_api.__file__)
SOURCE_SHA=hashlib.sha256(SOURCE.read_bytes()).hexdigest()


class Writer:
    def __init__(self,original,on_body):self.original=original;self.on_body=on_body
    def write(self,data):
        is_body=data.startswith(b'{')
        if is_body:self.on_body(data,'before')
        result=self.original.write(data)
        if is_body:self.on_body(data,'after')
        return result
    def __getattr__(self,name):return getattr(self.original,name)


class M14ReaderSlotTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture_module.M14SavedBoundaryTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.republish([dict(code=f'SYNTHETIC_{i}',previous5_session_count=3,
            prior60_session_count=57,history_unknown_reasons='SYNTHETIC_GAP') for i in range(70)])
        self.fixture.config['routes'].append(module_api.M04_ROUTE)
        self.server=module_api.create_module_server(self.fixture.config)
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        self.before=self.fixture.snapshot()
        self.enterContext(patch.object(fixture_module.owner,'run_rebound_owner',
            side_effect=AssertionError('PRODUCER_FORBIDDEN')))

    def get(self,query=None,path=ROUTE):
        try:r=urlopen(self.url+path+'?'+urlencode(query or {}),timeout=5)
        except HTTPError as error:r=error
        with r:return r.status,json.load(r)

    def intercept_body(self,callback):
        handler=self.server.RequestHandlerClass;setup=handler.setup
        def wrap(instance):
            setup(instance)
            instance.wfile=Writer(instance.wfile,lambda data,stage:callback(instance,data,stage))
        return patch.object(handler,'setup',wrap)

    def wait_free(self,name='m14_read_slot'):
        slot=inspect.getclosurevars(self.server.RequestHandlerClass.do_GET).nonlocals[name]
        self.assertTrue(slot.acquire(timeout=5));slot.release()

    def unchanged(self):
        self.assertEqual(self.before,self.fixture.snapshot())
        self.assertEqual(SOURCE_SHA,hashlib.sha256(SOURCE.read_bytes()).hexdigest())

    def body_barrier(self,target=ROUTE):
        sent=threading.Event();release=threading.Event()
        def on_body(instance,data,stage):
            if stage=='after' and instance.path.startswith(target) and not sent.is_set():
                sent.set()
                if not release.wait(10):raise AssertionError('PROBE_BODY_BARRIER_TIMEOUT')
        return sent,release,self.intercept_body(on_body)

    def test_next_page_after_complete_body_is_not_busy(self):
        sent,release,intercept=self.body_barrier()
        with intercept:
            try:
                first_status,first=self.get(dict(group='pending'))
                self.assertTrue(sent.wait(5));self.assertEqual(first_status,200)
                query=dict(group='pending',cursor=first['next_cursor'])
                next_status,next_page=self.get(query)
            finally:release.set()
        self.wait_free();retry_status,retry=self.get(query);self.unchanged()
        print(json.dumps(dict(case='complete_body_before_old_handler_exit',source_sha256=SOURCE_SHA,
            first_status=first_status,next_status=next_status,next_reason=next_page.get('reason_codes'),
            retry_status=retry_status,retry_offset=retry.get('offset'),original_files_unchanged=True)),flush=True)
        self.assertEqual(retry_status,200)
        self.assertEqual(next_status,200,'completed sequential page must release heavy-read slot before transmission')
        self.assertEqual(next_page['offset'],32)

    def test_actual_read_in_progress_still_rejects_concurrency(self):
        entered=threading.Event();release=threading.Event();original=module_api.read_response
        def read(*args,**kwargs):
            if not entered.is_set():
                entered.set()
                if not release.wait(10):raise AssertionError('PROBE_READER_BARRIER_TIMEOUT')
            return original(*args,**kwargs)
        with patch.object(module_api,'read_response',read),concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            first=pool.submit(self.get,dict(group='pending'))
            try:
                self.assertTrue(entered.wait(5));status,payload=self.get(dict(group='pending'))
            finally:release.set()
            first_status,_=first.result(timeout=10)
        self.unchanged();self.assertEqual(first_status,200);self.assertEqual(status,503)
        self.assertEqual(payload['reason_codes'],['MODULE_BUSY'])

    def test_m14_failure_response_releases_before_complete_error_body(self):
        sent,release,intercept=self.body_barrier();original=module_api.read_response;calls=[]
        def read(*args,**kwargs):
            calls.append(1)
            if len(calls)==1:raise ValueError('SYNTHETIC_BAD_REFERENCE')
            return original(*args,**kwargs)
        with patch.object(module_api,'read_response',read),intercept:
            try:
                status,payload=self.get();self.assertEqual(status,409)
                self.assertEqual(payload['reason_codes'],['MODULE_RESULT_INVALID'])
                self.assertTrue(sent.wait(5));next_status,_=self.get()
            finally:release.set()
        self.unchanged();self.assertEqual(next_status,200)

    def test_m14_oversize_response_is_rejected_then_slot_recovers(self):
        original=module_api.read_response
        def too_large(*args,**kwargs):
            record,digest=original(*args,**kwargs)
            record['payload']={'synthetic_padding':'x'*(256*1024)}
            return record,digest
        with patch.object(module_api,'read_response',too_large):status,payload=self.get()
        self.wait_free();self.assertEqual(self.get()[0],200);self.unchanged()
        self.assertEqual(status,409);self.assertEqual(payload['reason_codes'],['MODULE_RESULT_INVALID'])

    def test_m14_serialization_failure_releases_slot(self):
        original=module_api.read_response
        def invalid(*args,**kwargs):
            record,digest=original(*args,**kwargs);record['payload']={'bad':object()};return record,digest
        with patch.object(module_api,'read_response',invalid):status,payload=self.get()
        self.wait_free();self.assertEqual(self.get()[0],200);self.unchanged()
        self.assertEqual(status,409);self.assertEqual(payload['reason_codes'],['MODULE_RESULT_INVALID'])

    def test_m14_record_is_released_and_only_bounded_bytes_are_sent(self):
        class Record(dict):pass
        refs=[];observed=[];original=module_api.read_response
        def read(*args,**kwargs):
            record,digest=original(*args,**kwargs);record=Record(record);refs.append(weakref.ref(record));return record,digest
        def on_body(instance,data,stage):
            if stage=='before' and instance.path.startswith(ROUTE):
                observed.append(dict(record_released=refs[-1]() is None,bytes=len(data)))
        with patch.object(module_api,'read_response',read),self.intercept_body(on_body):status,payload=self.get()
        self.unchanged();self.assertEqual(status,200);self.assertEqual(len(observed),1)
        self.assertTrue(observed[0]['record_released']);self.assertLessEqual(observed[0]['bytes'],256*1024)
        self.assertLessEqual(sum(e['bytes'] for e in payload['entries'] if e['value_state']=='LOADED'),128*1024)

    def test_m14_disconnect_releases_slot(self):
        failed=threading.Event()
        def on_body(instance,data,stage):
            if stage=='before' and instance.path.startswith(ROUTE) and not failed.is_set():
                failed.set();raise BrokenPipeError('SYNTHETIC_DISCONNECTED_CLIENT')
        with self.intercept_body(on_body):
            with self.assertRaises((http.client.IncompleteRead,http.client.RemoteDisconnected)):self.get()
        self.assertTrue(failed.is_set());self.wait_free();self.assertEqual(self.get()[0],200);self.unchanged()

    def test_non_m14_reply_retains_original_slot_lifecycle(self):
        sent,release,intercept=self.body_barrier(module_api.M04_ROUTE)
        with intercept:
            try:
                status,_=self.get(path=module_api.M04_ROUTE);self.assertEqual(status,200)
                self.assertTrue(sent.wait(5));busy,payload=self.get(path=module_api.M04_ROUTE)
                m14_status,_=self.get()
            finally:release.set()
        self.unchanged();self.assertEqual(busy,503);self.assertEqual(payload['reason_codes'],['MODULE_BUSY'])
        self.assertEqual(m14_status,200)

if __name__=='__main__':unittest.main(verbosity=2)

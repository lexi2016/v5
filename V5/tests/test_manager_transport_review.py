"""Synthetic regressions for independent transport review; no real inputs."""
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import tracemalloc
import unittest
from test_manager_result_transport import ResultTransportTests, raw
from test_manager_current_recovery import ManagerCurrentRecoveryTests
from v5_shadow import manager_result_transport as transport
from v5_shadow.manager_plan import run_manager_plan


class TransportReviewTests(ResultTransportTests):
    def test_single_oversize_string_rejected_without_full_encoded_token(self):
        # Allocate the input before tracing. Encoding must not copy this whole token.
        self.result['payload']['large'] = '\x00' * (transport.RESULT_BYTES + 1)
        tracemalloc.start()
        try:
            with tempfile.TemporaryFile() as stream:
                with self.assertRaisesRegex(transport.ResultTransportError, 'TOTAL_LIMIT'):
                    transport.write_result(stream, self.result, self.request)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        print(json.dumps({'allocation_case':'oversize_string','peak_additional_bytes':peak}))
        self.assertLess(peak, 8 * 1024 * 1024, 'encoder allocated an unbounded escaped token')

    def test_error_frame_rejects_untrusted_fields(self):
        valid = dict(kind='error', code='LOCAL_RESULT_TOTAL_LIMIT', stage='encode_result',
                     actual_bytes=67108865, allowed_bytes=67108864, saved=None)
        variants = [dict(valid, code='PRIVATE_BODY'), dict(valid, code='x'*10000),
            dict(valid, stage='PRIVATE_BODY'), dict(valid, saved={'body':'PRIVATE_BODY'}),
            dict(valid, actual_bytes=True), dict(valid, allowed_bytes=-1),
            dict(valid, unknown='PRIVATE_BODY'), {k:v for k,v in valid.items() if k!='stage'},
            dict(valid, saved={'run_id':'PRIVATE_BODY'}),
            dict(valid, saved={'run_id':'a'*32,'relative':'../../PRIVATE_BODY'})]
        for value in variants:
            with self.subTest(field=list(value)):
                wire=transport.MAGIC+struct.pack('!I',len(raw(value)))+raw(value)
                with self.assertRaises(transport.ResultTransportError) as caught:
                    transport.read_result(io.BytesIO(wire),self.request)
                self.assertEqual(caught.exception.diagnostic['code'],'LOCAL_RESULT_ERROR_SCHEMA')
                self.assertNotIn('PRIVATE_BODY',str(caught.exception.diagnostic))

    def test_outbound_uppercase_exception_is_not_a_whitelisted_code(self):
        stream=io.BytesIO();transport.write_failure(stream,ValueError('PRIVATE_BODY'))
        with self.assertRaises(transport.ResultTransportError) as caught:
            transport.read_result(io.BytesIO(stream.getvalue()),self.request)
        self.assertEqual(caught.exception.diagnostic['code'],'LOCAL_MANAGER_WORKER_FAILED')

    def test_stderr_after_stdout_close_still_enforces_budget(self):
        path=self.root/'wire';path.write_bytes(self.wire())
        code="import os,sys,time;from pathlib import Path;sys.stdout.buffer.write(Path(sys.argv[1]).read_bytes());sys.stdout.flush();os.close(1);time.sleep(.1);os.write(2,b'x'*70000)"
        with self.assertRaisesRegex(transport.ResultTransportError,'STDERR_LIMIT'):
            transport.run_worker([sys.executable,'-I','-B','-c',code,str(path)],self.request,os.environ.copy(),timeout=2)

    def test_escaped_string_crosses_budget_with_bounded_allocation(self):
        self.result['payload']['large'] = '\x00' * (transport.RESULT_BYTES // 6 + 1)
        tracemalloc.start()
        try:
            with tempfile.TemporaryFile() as stream:
                with self.assertRaisesRegex(transport.ResultTransportError, 'TOTAL_LIMIT'):
                    transport.write_result(stream,self.result,self.request)
            _,peak=tracemalloc.get_traced_memory()
        finally:tracemalloc.stop()
        print(json.dumps({'allocation_case':'escape_expansion','peak_additional_bytes':peak}))
        self.assertLess(peak,8*1024*1024)

    def test_fragment_encoding_matches_canonical_escaping_at_boundaries(self):
        values=['"\\\b\f\n\r\t\x00汉😀', '汉😀"\\'*20000,
                {'b':[None,True,False,-12,1.2e20], 'a':'x'*16383+'"\\😀'}]
        for value in values:
            with self.subTest(type=type(value).__name__):
                self.assertEqual(b''.join(transport._pieces(value)),raw(value))

    def test_valid_error_identity_roundtrips_and_unknown_context_is_removed(self):
        saved=transport.saved_identity(self.result,self.request)
        error=transport.ResultTransportError('LOCAL_RESULT_TOTAL_LIMIT',stage='encode_result',
            actual_bytes=transport.RESULT_BYTES+1,allowed_bytes=transport.RESULT_BYTES,saved=saved)
        stream=io.BytesIO();transport.write_failure(stream,error)
        with self.assertRaises(transport.ResultTransportError) as caught:
            transport.read_result(io.BytesIO(stream.getvalue()),self.request)
        self.assertEqual(caught.exception.diagnostic,error.diagnostic)
        stream=io.BytesIO();transport.write_failure(stream,ValueError('SYNTHETIC_PRIVATE_ARTICLE_BODY'),
            {'stage':'PRIVATE_BODY','saved':{'run_id':'a'*32,'body':'PRIVATE_BODY'}})
        with self.assertRaises(transport.ResultTransportError) as caught:
            transport.read_result(io.BytesIO(stream.getvalue()),self.request)
        self.assertEqual(caught.exception.diagnostic['code'],'LOCAL_RESULT_ERROR_SCHEMA')
        self.assertNotIn('PRIVATE_BODY',str(caught.exception.diagnostic))

    def test_stdout_close_with_bounded_late_stderr_completes(self):
        path=self.root/'wire';path.write_bytes(self.wire())
        code="import os,sys,time;from pathlib import Path;sys.stdout.buffer.write(Path(sys.argv[1]).read_bytes());sys.stdout.flush();os.close(1);time.sleep(.05);os.write(2,b'x'*65536)"
        result,_=transport.run_worker([sys.executable,'-I','-B','-c',code,str(path)],self.request,os.environ.copy(),timeout=2)
        self.assertEqual(result,self.result)

    def test_both_pipes_closed_but_worker_alive_obeys_deadline(self):
        path=self.root/'wire';path.write_bytes(self.wire())
        code="import os,sys,time;from pathlib import Path;sys.stdout.buffer.write(Path(sys.argv[1]).read_bytes());sys.stdout.flush();os.close(1);os.close(2);time.sleep(5)"
        with self.assertRaisesRegex(transport.ResultTransportError,'TIMEOUT'):
            transport.run_worker([sys.executable,'-I','-B','-c',code,str(path)],self.request,os.environ.copy(),timeout=.2)

    def test_historical_selection_keeps_exact_file_hash_root_and_run_checks(self):
        self.request.update(action='read',view='historical')
        self.result['payload']['read_context']={'mode':'HISTORICAL_AS_OF'}
        self.result['readback']['selection_mode']='HISTORICAL_AS_OF'
        self.latest.write_bytes(b'{"later":"synthetic"}')
        wire=self.wire()
        self.assertEqual(transport.read_result(io.BytesIO(wire),self.request)[0],self.result)
        with self.assertRaisesRegex(ValueError,'REQUEST_IDENTITY'):
            transport.read_result(io.BytesIO(wire),dict(self.request,manager_output_root=str(self.root/'other')))
        self.result['readback']['run_id']='b'*32
        with self.assertRaises((ValueError,FileNotFoundError)):self.wire()
        self.result['readback']['run_id']='a'*32
        self.path.write_bytes(raw(dict(self.saved,workspace={'changed':True})))
        with self.assertRaisesRegex(ValueError,'SAVED_IDENTITY'):
            transport.read_result(io.BytesIO(wire),self.request)


    def test_post_eof_parsing_and_saved_validation_share_deadline(self):
        # Real elapsed time, real JSON parse and transport file read; only inject
        # scheduling delays at these transport checkpoints, never owner mocks.
        from unittest.mock import patch
        import time
        path=self.root/'wire';path.write_bytes(self.wire())
        code="import sys;from pathlib import Path;sys.stdout.buffer.write(Path(sys.argv[1]).read_bytes())"
        argv=[sys.executable,'-I','-B','-c',code,str(path)]
        original_parse=transport.json.loads;original_file=transport._file
        def slow_parse(value,*args,**kwargs):
            if isinstance(value,bytearray):time.sleep(.6)
            return original_parse(value,*args,**kwargs)
        def slow_file(*args,**kwargs):
            time.sleep(.6)
            return original_file(*args,**kwargs)
        for target,hook in [('json.loads',slow_parse),('_file',slow_file)]:
            with self.subTest(checkpoint=target),patch('v5_shadow.manager_result_transport.'+target,side_effect=hook):
                with self.assertRaisesRegex(transport.ResultTransportError,'TIMEOUT'):
                    transport.run_worker(argv,self.request,os.environ.copy(),timeout=.5)


class HistoricalTransportReviewTests(ManagerCurrentRecoveryTests):
    def historical_fixture(self):
        # Real original owner creates empty synthetic workspace + journal.
        # Only test fixture timestamps are then resealed to represent past saves.
        early=run_manager_plan(dict(self.request,now='2026-10-09T08:45:00+08:00'))
        later=run_manager_plan(dict(self.request,now='2026-10-09T10:00:00+08:00'))
        import hashlib
        for result,stamp in [(early,'2026-10-09T08:46:00+08:00'),(later,'2026-10-09T10:01:00+08:00')]:
            run=result['readback']['run_id']
            for directory in ['workspace_plans','workspace_plan_runs']:
                path=self.output/directory/'20261009'/(run+'.json')
                value=json.loads(path.read_bytes())
                if directory=='workspace_plans':value['generated_at']=stamp
                else:value.update(finished_at=stamp,last_success_at=stamp)
                value['sha256']=hashlib.sha256(raw({k:v for k,v in value.items() if k!='sha256'})).hexdigest()
                path.write_bytes(raw(value))
                if result is later:path.with_name('latest.json').write_bytes(raw(value))
            result['fixture_plan']=json.loads((self.output/'workspace_plans/20261009'/(run+'.json')).read_bytes())
        return early,later

    def test_original_historical_reader_selects_earlier_run_when_latest_is_later(self):
        early,later=self.historical_fixture();before=self.snapshot()
        try:
            read=run_manager_plan(dict(self.request,action='read',view='historical'))
        except ValueError as error:
            self.fail('Legal original historical read was rejected: '+str(error))
        self.assertTrue(read['payload']['plan_product']['consumed'])
        self.assertEqual(read['payload']['read_context']['mode'],'HISTORICAL_AS_OF')
        self.assertEqual(read['readback']['run_id'],early['readback']['run_id'])
        self.assertEqual(read['readback']['plan_sha256'],early['fixture_plan']['sha256'])
        self.assertNotEqual(read['readback']['run_id'],later['readback']['run_id'])
        self.assertEqual(read['local_result_transport']['saved']['run_id'],early['readback']['run_id'])
        self.assertEqual(read['readback']['latest_observation']['run_id'],later['readback']['run_id'])
        self.assertFalse(read['readback']['latest_observation']['matches_exact_run'])
        self.assertEqual(self.snapshot(),before)

# Fixture reuse only: the original 65 are loaded separately, exactly once.
for base,child in [(ResultTransportTests,TransportReviewTests),(ManagerCurrentRecoveryTests,HistoricalTransportReviewTests)]:
    for name in base.__dict__:
        if name.startswith('test_'):setattr(child,name,None)

"""Synthetic protocol negatives; no product return or original reader mocked."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import time
import subprocess
import unittest
from v5_shadow import manager_result_transport as transport


def raw(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()


class ResultTransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();run='a'*32
        self.request=dict(target_date='20261009',action='refresh',manager_output_root=str(self.root))
        saved=dict(run_id=run,target_trade_date='20261009',input_identity='input',workspace={'only':'SYNTHETIC'})
        saved['sha256']=hashlib.sha256(raw(saved)).hexdigest()
        self.saved=saved;folder=self.root/'workspace_plans/20261009';folder.mkdir(parents=True)
        self.path=folder/(run+'.json');self.path.write_bytes(raw(saved)+b'\n');self.latest=folder/'latest.json';self.latest.write_bytes(self.path.read_bytes())
        self.result=dict(payload=dict(target_trade_date='20261009',plan_product=dict(run_id=run,sha256=saved['sha256'],consumed=True),research_observation={'read_time_field':'SYNTHETIC'}),readback=dict(run_id=run,plan_sha256=saved['sha256'],input_identity='input',store_relative='.'))

    def wire(self):
        stream=io.BytesIO();transport.write_result(stream,self.result,self.request);return stream.getvalue()

    def frames(self,wire):
        stream=io.BytesIO(wire);magic=stream.read(len(transport.MAGIC));items=[]
        while stream.tell()<len(wire):
            n=struct.unpack('!I',stream.read(4))[0];header=json.loads(stream.read(n))
            body=stream.read(header['bytes']) if header['kind']=='chunk' else b''
            items.append([header,body])
        return magic,items

    def pack(self,frames):
        return transport.MAGIC+b''.join(struct.pack('!I',len(raw(h)))+raw(h)+body for h,body in frames)

    def test_three_distinct_hash_scopes_and_read_time_field(self):
        result,receipt=transport.read_result(io.BytesIO(self.wire()),self.request)
        self.assertEqual(result,self.result)
        self.assertEqual(receipt['response_sha256'],hashlib.sha256(raw(self.result)).hexdigest())
        self.assertEqual(receipt['saved']['raw_sha256'],hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(receipt['saved']['plan_sha256'],self.saved['sha256'])
        self.assertEqual(len({receipt['response_sha256'],receipt['saved']['raw_sha256'],receipt['saved']['plan_sha256']}),3)

    def test_truncated_payload_and_end_rejected(self):
        wire=self.wire()
        for size in [0,3,len(wire)//2,len(wire)-1]:
            with self.subTest(size=size),self.assertRaisesRegex(ValueError,'TRUNCATED'):
                transport.read_result(io.BytesIO(wire[:size]),self.request)

    def test_chunk_hash_and_complete_hash_rejected(self):
        for kind in ['chunk','end']:
            _,frames=self.frames(self.wire());next(h for h,b in frames if h['kind']==kind)['sha256']='0'*64
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'HASH'):
                transport.read_result(io.BytesIO(self.pack(frames)),self.request)

    def test_wrong_sequence_and_oversized_chunk_rejected_before_read(self):
        for field,value,reason in [('index',1,'ORDER'),('bytes',transport.CHUNK_BYTES+1,'CHUNK_LIMIT')]:
            _,frames=self.frames(self.wire());next(h for h,b in frames if h['kind']=='chunk')[field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,reason):
                transport.read_result(io.BytesIO(self.pack(frames)),self.request)

    def test_wrong_run_rejected_even_with_resealed_wire(self):
        self.result['readback']['run_id']='b'*32
        with self.assertRaises((ValueError,FileNotFoundError)):
            self.wire()

    def test_wrong_directory_rejected(self):
        self.result['readback']['store_relative']='../escape'
        with self.assertRaisesRegex(ValueError,'DIRECTORY'):self.wire()

    def test_different_authorized_root_rejected(self):
        with self.assertRaisesRegex(ValueError,'REQUEST_IDENTITY'):
            transport.read_result(io.BytesIO(self.wire()),dict(self.request,manager_output_root=str(self.root/'other')))

    def test_latest_changed_after_child_receipt_rejected(self):
        wire=self.wire();replacement=dict(self.saved,run_id='b'*32)
        self.latest.write_bytes(raw(replacement))
        with self.assertRaisesRegex(ValueError,'LATEST_CHANGED'):
            transport.read_result(io.BytesIO(wire),self.request)

    def test_exact_file_changed_after_receipt_rejected(self):
        wire=self.wire();self.path.write_bytes(raw(dict(self.saved,workspace={'changed':True})))
        with self.assertRaisesRegex(ValueError,'SAVED_IDENTITY'):
            transport.read_result(io.BytesIO(wire),self.request)

    def test_symlink_file_rejected(self):
        other=self.root/'other.json';other.write_bytes(self.path.read_bytes());self.path.unlink();self.path.symlink_to(other)
        with self.assertRaises(OSError):self.wire()

    def test_total_budget_error_has_saved_identity_and_no_body(self):
        self.result['payload']['oversized_synthetic']='X'*(transport.RESULT_BYTES+1)
        with tempfile.TemporaryFile() as stream:
            with self.assertRaisesRegex(transport.ResultTransportError,'TOTAL_LIMIT') as caught:
                transport.write_result(stream,self.result,self.request)
            d=caught.exception.diagnostic
            self.assertEqual(d['saved']['run_id'],self.saved['run_id'])
            self.assertEqual(d['allowed_bytes'],transport.RESULT_BYTES)
            self.assertGreater(d['actual_bytes'],transport.RESULT_BYTES)
            self.assertNotIn('XXXX',str(d))

    def test_stdout_eof_does_not_wait_for_descendant_stderr_eof(self):
        child = "import subprocess,sys; subprocess.Popen([sys.executable, '-I', '-B', '-c', 'import time;time.sleep(2)'], stdout=subprocess.DEVNULL); sys.stdout.close()"
        process = subprocess.Popen([sys.executable, '-I', '-B', '-c', child], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        deadline = time.monotonic() + 5
        started = time.monotonic()
        try:
            self.assertEqual(transport._Pipe(process, deadline).read(1), b'')
            self.assertLess(time.monotonic() - started, 1.0)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=2)
            process.stdout.close()
            process.stderr.close()

    def test_pipe_timeout_is_bounded(self):
        with self.assertRaisesRegex(ValueError,'TIMEOUT'):
            transport.run_worker([sys.executable,'-I','-B','-c','import time;time.sleep(5)'],self.request,os.environ.copy(),timeout=.1)

    def test_pipe_oversized_control_and_stderr_are_bounded(self):
        scripts=[("import sys;sys.stdout.buffer.write(b'V5MR1\\n'+b'\\xff'*4);sys.stdout.flush()",'CONTROL_LIMIT'),("import sys;sys.stderr.write('x'*70000);sys.stderr.flush()",'STDERR_LIMIT')]
        for code,reason in scripts:
            with self.subTest(reason=reason),self.assertRaisesRegex(ValueError,reason):
                transport.run_worker([sys.executable,'-I','-B','-c',code],self.request,os.environ.copy(),timeout=5)

    def test_end_count_boolean_is_not_integer(self):
        _,frames=self.frames(self.wire());frames[-1][0]['count']=True
        with self.assertRaisesRegex(ValueError,'COMPLETE_HASH'):
            transport.read_result(io.BytesIO(self.pack(frames)),self.request)

    def test_receiver_total_budget_rejected_before_reading_extra_chunk(self):
        _,frames=self.frames(self.wire())
        block=b'x'*transport.CHUNK_BYTES
        with tempfile.TemporaryFile() as wire:
            wire.write(self.pack([frames[0]]))
            for i in range(transport.RESULT_BYTES//transport.CHUNK_BYTES+1):
                header=dict(kind='chunk',index=i,bytes=len(block),sha256=hashlib.sha256(block).hexdigest())
                wire.write(struct.pack('!I',len(raw(header)))+raw(header))
                if i<transport.RESULT_BYTES//transport.CHUNK_BYTES:wire.write(block)
            wire.seek(0)
            with self.assertRaisesRegex(ValueError,'TOTAL_LIMIT'):
                transport.read_result(wire,self.request)

    def test_all_synthetic_pit_gaps_and_observations_preserved(self):
        gaps=['ARCHIVE_ARTICLE_ACQUISITION_TIME_MISSING:'+str(i) for i in range(3075)]
        gaps += ['ARCHIVE_ARTICLE_STRUCTURED_THEME_MISSING:'+str(i) for i in range(175)]
        self.result['payload']['gaps']=gaps
        self.result['payload']['rebound_research_observation']={'status':'CANNOT_CONFIRM','eligible_screen':None,'reason_codes':['SYNTHETIC_UNIT_NOT_PROVEN']}
        result,receipt=transport.read_result(io.BytesIO(self.wire()),self.request)
        self.assertEqual(result['payload'],self.result['payload'])
        self.assertEqual(len(result['payload']['gaps']),3250)

    def test_assemble_failure_diagnostic_is_body_free_and_keeps_saved_identity(self):
        stream=io.BytesIO()
        transport.write_failure(stream,ValueError('SYNTHETIC PRIVATE ARTICLE BODY'),{'stage':'exact_saved_readback','saved':{'run_id':'a'*32}})
        with self.assertRaises(transport.ResultTransportError) as caught:
            transport.read_result(io.BytesIO(stream.getvalue()),self.request)
        diagnostic=caught.exception.diagnostic
        self.assertEqual(diagnostic['stage'],'exact_saved_readback')
        self.assertEqual(diagnostic['saved']['run_id'],'a'*32)
        self.assertNotIn('PRIVATE',str(diagnostic))

    def test_chunk_count_is_bounded_independently_of_total_bytes(self):
        _,frames=self.frames(self.wire());frames=frames[:1]
        for i in range(65):
            frames.append([dict(kind='chunk',index=i,bytes=1,sha256=hashlib.sha256(b'x').hexdigest()),b'x'])
        with self.assertRaisesRegex(ValueError,'CHUNK_COUNT_LIMIT'):
            transport.read_result(io.BytesIO(self.pack(frames)),self.request)

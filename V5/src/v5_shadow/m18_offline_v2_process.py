"""Supervise one local offline build/read in a fresh spawn process.

Only fixed build/read actions, local files, no service/network or owner calls.
RSS is checked using the worker's process high-water measurement, not hard
memory isolation. Parent terminates on wall deadline; no success marker until
worker exit and all measured resource gates pass. No automatic retries.
"""
import hashlib
import json
import multiprocessing
import select
import struct
import resource
import math
import re
import os
from pathlib import Path
import stat
import sys
import time
from . import m18_offline_v2 as m


def _read(path, limit):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        m.require(stat.S_ISREG(before.st_mode) and 0<before.st_size<limit,'V2_FILE_LIMIT')
        with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(limit)
        after=os.fstat(fd)
        m.require(len(raw)==before.st_size and (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==
                  (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'V2_FILE_CHANGED')
        return raw
    finally:os.close(fd)


def _validate(request):
    m.require(type(request) is dict,'V2_REQUEST')
    action=request.get('action')
    m.require(action in ('build','read'),'V2_ACTION')
    shared={'action','output_root','identity','profile_sha256'}
    keys=shared|({'response_path','saved_path'} if action=='build' else {'bundle_root','manifest_sha256'})
    m.v1.exact(request,keys,'V2_REQUEST')
    m.profile_check(request['profile_sha256']);m.v1.identity_check(request['identity'])
    for key in keys & {'response_path','saved_path','bundle_root','output_root'}:
        value=request[key]
        m.require(type(value) is str and len(value)<=4096 and Path(value).is_absolute(),'V2_PATH')
    m.require(len(m.v1.canonical(request))<65536,'V2_REQUEST_BYTES')


def _worker(request, connection):
    guard=m.ResourceGuard();result=dict(pid=os.getpid(),status='REJECTED')
    def audit(event,args):
        if event.startswith('socket.') or event=='subprocess.Popen':
            raise m.ContractError('M18_V2_EXECUTION_DENIED')
    sys.addaudithook(audit)
    try:
        _validate(request)
        output=Path(request['output_root'])
        m.require(not output.exists(),'V2_OUTPUT_EXISTS')
        if request['action']=='build':
            raw=_read(request['response_path'],m.PROFILE['generation_bytes'])
            saved=_read(request['saved_path'],m.PROFILE['generation_bytes'])
            guard.checkpoint('inputs_loaded')
            bundle=m.build(raw,saved,request['identity'],expected_profile=request['profile_sha256'],guard=guard)
            del raw,saved
            output.mkdir();(output/'objects').mkdir()
            (output/'manifest.json').write_bytes(bundle.manifest)
            for key,value in bundle.objects.items():
                (output/'objects'/key).write_bytes(value);guard.checkpoint()
            result.update(manifest_sha256=m.sha(bundle.manifest),objects=len(bundle.objects),
                          generation_bytes=len(bundle.manifest)+sum(map(len,bundle.objects.values())))
        else:
            root=Path(request['bundle_root'])
            manifest=_read(str(root/'manifest.json'),m.PROFILE['object_bytes'])
            m.require(m.sha(manifest)==request['manifest_sha256'],'V2_MANIFEST_HASH')
            # Enumerate only the local generated object directory; count/byte
            # admission precedes holding all objects. Reader rejects extra files.
            m.require((root/'objects').is_dir() and not (root/'objects').is_symlink(),'V2_OBJECT_DIRECTORY')
            objects={};total=len(manifest)
            for path in (root/'objects').iterdir():
                m.require(len(objects)+2<=m.PROFILE['records'],'V2_RECORDS')
                m.require(m.v1.re.fullmatch('[0-9a-f]{64}',path.name) is not None,'V2_OBJECT_NAME')
                value=_read(str(path),m.PROFILE['object_bytes']);total+=len(value)
                m.require(total<m.PROFILE['generation_bytes'],'V2_STORED_BYTES');objects[path.name]=value
                guard.checkpoint()
            reader=m.Reader(m.Bundle(manifest,objects),request['manifest_sha256'],request['identity'],
                            expected_profile=request['profile_sha256'],guard=guard)
            del objects
            overview=reader.overview();pages=0
            for section in overview['sections']:
                cursor=None;offset=0
                while True:
                    page=reader.detail(section,cursor=cursor)
                    reader.verify_page(page,expected_section=section,expected_selection=None,
                                       expected_cursor=cursor,expected_offset=offset)
                    pages+=1;offset+=len(page['entries']);cursor=page['next_cursor']
                    if cursor is None:break
            output.mkdir();h=hashlib.sha256();bytes_written=0
            with (output/'reassembled.json').open('xb') as stream:
                for index in range(overview['content_chunks']):
                    part=reader.content(index);reader.verify_content(part,expected_index=index)
                    block=m.base64.b64decode(part['data'],validate=True);stream.write(block);h.update(block);bytes_written+=len(block)
                    guard.checkpoint()
            m.require(h.hexdigest()==request['identity']['response_sha256'],'V2_REASSEMBLED_HASH')
            result.update(counts=reader.counts,detail_pages=pages,content_chunks=overview['content_chunks'],
                          response_bytes=bytes_written,response_sha256=h.hexdigest(),
                          gaps=overview['sections'].get('gaps',{}).get('total'),
                          not_loaded_sections=len(overview['sections']),
                          not_loaded_items=sum(row['not_loaded_count'] for row in overview['sections'].values()))
        guard.checkpoint('worker_complete');result['status']='OK'
    except m.ContractError as error:result['error']=str(error)
    except Exception:result['error']='M18_V2_WORKER_FAILED'
    finally:
        result['usage']=guard.usage();result['stages']=guard.stages
        try:m.enforce_usage(result['usage'])
        except m.ContractError as error:result.update(status='REJECTED',error=str(error))
        connection.send(result);connection.close()


# Internal local IPC contract: bounded JSON summary plus a fixed 24-byte footer.
# No pickle on the return path. Footer is sampled AFTER body encode/write.
RECEIPT_BYTES=16*1024
FOOTER=struct.Struct('!Qdd')
COMMON={'pid','status','scan_nodes','scan_bytes','stage_count'}
BUILD={'manifest_sha256','objects','generation_bytes'}
READ={'counts','detail_pages','content_chunks','response_bytes','response_sha256','gaps','not_loaded_sections','not_loaded_items'}
COUNTS={'input_nodes','metadata_nodes','logical_nodes','stored_bytes','records','response_nodes','saved_nodes'}


def check_summary(value):
    m.require(type(value) is dict and COMMON<=set(value),'V2_RECEIPT_SCHEMA')
    if value['status']=='REJECTED':
        m.v1.exact(value,COMMON|{'error'},'V2_RECEIPT_SCHEMA')
        error=value['error']
        m.require(type(error) is str and re.fullmatch(r'M18_[A-Z0-9_]{1,128}',error) is not None,'V2_RECEIPT_ERROR')
    else:
        m.require(value['status']=='OK' and (set(value)==COMMON|BUILD or set(value)==COMMON|READ),'V2_RECEIPT_SCHEMA')
    for key,item in value.items():
        if key in ('status','error'):continue
        if key in ('manifest_sha256','response_sha256'):
            m.require(type(item) is str and re.fullmatch('[0-9a-f]{64}',item) is not None,'V2_RECEIPT_HASH')
        elif key=='counts':
            m.v1.exact(item,COUNTS,'V2_RECEIPT_COUNTS')
            m.require(all(m.v1.integer(n,0,2**63-1) for n in item.values()),'V2_RECEIPT_COUNTER')
        elif key=='gaps' and item is None:pass
        else:m.require(m.v1.integer(item,1 if key=='pid' else 0,2**63-1),'V2_RECEIPT_COUNTER')


def compact_receipt(result):
    m.require(type(result) is dict and set(result)<=COMMON|BUILD|READ|{'error','usage','stages'},'V2_RECEIPT_SCHEMA')
    usage=result.get('usage',{});stages=result.get('stages',[])
    m.require(type(usage) is dict and type(stages) is list,'V2_RECEIPT_SCHEMA')
    value={k:v for k,v in result.items() if k not in ('usage','stages')}
    if result.get('status')=='REJECTED':
        value={k:v for k,v in value.items() if k in ('pid','status','error')}
    value.update(scan_nodes=usage.get('scan_nodes',0),scan_bytes=usage.get('scan_bytes',0),stage_count=len(stages))
    check_summary(value);return value


def encode_receipt(value):
    check_summary(value)
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    m.require(0<len(raw)<=RECEIPT_BYTES,'V2_RECEIPT_LENGTH')
    return raw


class ReceiptSender:
    def __init__(self,connection):self.connection=connection;self.started=time.monotonic();self.sent=False
    def fileno(self):return self.connection.fileno()
    def close(self):self.connection.close()
    def _write(self,raw):
        view=memoryview(raw)
        while view:
            count=os.write(self.fileno(),view)
            if count<=0:raise OSError('receipt write closed')
            view=view[count:]
    def send(self,result):
        m.require(not self.sent,'V2_RECEIPT_DUPLICATE');self.sent=True
        body=encode_receipt(compact_receipt(result))
        self._write(struct.pack('!I',len(body)));self._write(body)
        # Includes summary compaction, JSON encoding and the entire body send.
        # CPU is process lifetime CPU (including spawn imports), stronger than
        # the business Guard's operation CPU. Final fixed footer/teardown is
        # outside this sample; the parent still supervises wall time to exit.
        usage=resource.getrusage(resource.RUSAGE_SELF)
        peak=usage.ru_maxrss if sys.platform=='darwin' else usage.ru_maxrss*1024
        self._write(FOOTER.pack(peak,time.process_time(),time.monotonic()-self.started))


def receive_receipt(fd,deadline):
    data=bytearray();total=None
    try:
        os.set_blocking(fd,False)
        while True:
            remaining=deadline-time.monotonic()
            m.require(remaining>0,'V2_RESOURCE_WALL_SECONDS')
            ready,_,_=select.select([fd],[],[],min(.05,remaining))
            if not ready:continue
            try:block=os.read(fd,min(4096,RECEIPT_BYTES+4+FOOTER.size+1-len(data)))
            except (BlockingIOError,InterruptedError):continue
            m.require(time.monotonic()<=deadline,'V2_RESOURCE_WALL_SECONDS')
            if not block:
                m.require(bool(data),'V2_RECEIPT_EOF')
                m.require(total is not None and len(data)==total,'V2_RECEIPT_TRUNCATED')
                break
            data.extend(block)
            if len(data)>=4 and total is None:
                length=struct.unpack('!I',data[:4])[0]
                m.require(0<length<=RECEIPT_BYTES,'V2_RECEIPT_LENGTH');total=4+length+FOOTER.size
            if total is not None:m.require(len(data)<=total,'V2_RECEIPT_TRAILING')
        value,_=m.v1.parse(bytes(data[4:-FOOTER.size]),object_limit=True)
        check_summary(value)
        peak,cpu,wall=FOOTER.unpack(data[-FOOTER.size:])
        m.require(all(math.isfinite(x) and x>=0 for x in (cpu,wall)),'V2_RECEIPT_USAGE')
        value['usage']=dict(peak_rss_bytes=peak,cpu_seconds=cpu,wall_seconds=wall,
                            scan_nodes=value['scan_nodes'],scan_bytes=value['scan_bytes'])
        m.require(time.monotonic()<=deadline,'V2_RESOURCE_WALL_SECONDS')
        return value
    except (OSError,ValueError) as error:
        if isinstance(error,m.ContractError):raise
        raise m.ContractError('M18_V2_RECEIPT_IO') from None


def _entry(worker,request,connection):
    sender=ReceiptSender(connection)
    try:worker(request,sender)
    except (OSError,m.ContractError):pass  # EOF/truncation is rejected by parent.
    finally:sender.close()


def _reap(process):
    if process.pid is None:return True
    if process.is_alive():process.terminate();process.join(1)
    if process.is_alive():process.kill();process.join(2)
    else:process.join(0)
    return not process.is_alive()


def run(request):
    """Fixed local actions with bounded, deadline-aware return framing."""
    try:_validate(request)
    except (m.ContractError,ValueError,TypeError) as error:
        return dict(status='REJECTED',error=str(error) if isinstance(error,m.ContractError) else 'M18_V2_REQUEST')
    context=multiprocessing.get_context('spawn');parent,child=context.Pipe(duplex=False)
    process=context.Process(target=_entry,args=(_worker,request,child));start=time.monotonic()
    deadline=start+m.PROFILE['wall_seconds'];result=None;accepted_owned=False
    try:
        process.start();child.close()
        result=receive_receipt(parent.fileno(),deadline)
        process.join(max(0,deadline-time.monotonic()))
        m.require(time.monotonic()<=deadline and not process.is_alive(),'V2_RESOURCE_WALL_SECONDS')
        m.require(process.exitcode==0,'V2_WORKER_EXIT')
        m.require(result['pid']==process.pid,'V2_RECEIPT_PID')
        if result['status']=='OK':
            m.require(set(result)-{'usage'}==COMMON|(BUILD if request['action']=='build' else READ),'V2_RECEIPT_ACTION')
            if request['action']=='read':m.require(result['response_sha256']==request['identity']['response_sha256'],'V2_RECEIPT_IDENTITY')
        m.enforce_usage(dict(result['usage'],wall_seconds=time.monotonic()-start))
        if result['status']=='OK':
            # This small parent-owned local marker is outside worker CPU/RSS.
            m.require(time.monotonic()<=deadline,'V2_RESOURCE_WALL_SECONDS')
            with (Path(request['output_root'])/'ACCEPTED.json').open('x') as f:
                accepted_owned=True
                json.dump(dict(profile_sha256=m.PROFILE_SHA256,identity=request['identity'],usage=result['usage']),f)
        m.require(time.monotonic()<=deadline,'V2_RESOURCE_WALL_SECONDS')
        return dict(result,supervisor_wall_seconds=time.monotonic()-start,worker_exit=process.exitcode,worker_reaped=True)
    except (m.ContractError,OSError,EOFError) as error:
        reaped=_reap(process)
        if accepted_owned:(Path(request['output_root'])/'ACCEPTED.json').unlink(missing_ok=True)
        diagnostic={'usage':result['usage']} if result is not None else {}
        return dict(**diagnostic,status='REJECTED',error=str(error) if isinstance(error,m.ContractError) else 'M18_V2_RECEIPT_IO',
                    supervisor_wall_seconds=time.monotonic()-start,worker_exit=process.exitcode,worker_reaped=reaped)
    finally:
        if process.pid is not None:_reap(process)
        parent.close();child.close()

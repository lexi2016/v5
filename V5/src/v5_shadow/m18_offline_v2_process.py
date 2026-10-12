"""Supervise one local offline build/read in a fresh spawn process.

Only fixed build/read actions, local files, no service/network or owner calls.
RSS is checked using the worker's process high-water measurement, not hard
memory isolation. Parent terminates on wall deadline; no success marker until
worker exit and all measured resource gates pass. No automatic retries.
"""
import hashlib
import json
import multiprocessing
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
                          not_loaded=overview['sections'])
        guard.checkpoint('worker_complete');result['status']='OK'
    except m.ContractError as error:result['error']=str(error)
    except Exception:result['error']='M18_V2_WORKER_FAILED'
    finally:
        result['usage']=guard.usage();result['stages']=guard.stages
        try:m.enforce_usage(result['usage'])
        except m.ContractError as error:result.update(status='REJECTED',error=str(error))
        connection.send(result);connection.close()


def run(request):
    """Trusted local API: fixed actions only, never shell commands from input."""
    try:_validate(request)
    except (m.ContractError,ValueError,TypeError) as error:
        return dict(status='REJECTED',error=str(error) if isinstance(error,m.ContractError) else 'M18_V2_REQUEST')
    context=multiprocessing.get_context('spawn');parent,child=context.Pipe(duplex=False)
    process=context.Process(target=_worker,args=(request,child));start=time.monotonic()
    result=None
    try:
        process.start();child.close()
        while time.monotonic()-start<=m.PROFILE['wall_seconds']:
            if parent.poll(.05):
                try:result=parent.recv()
                except EOFError:pass
                break
            if not process.is_alive():break
        remaining=max(0,m.PROFILE['wall_seconds']-(time.monotonic()-start))
        process.join(remaining if result is not None else 0)
        if process.is_alive():
            process.terminate();process.join(1)
            if process.is_alive():process.kill();process.join()
            return dict(status='REJECTED',error='M18_V2_RESOURCE_WALL_SECONDS',supervisor_wall_seconds=time.monotonic()-start)
        if result is None or process.exitcode!=0:
            return dict(status='REJECTED',error='M18_V2_WORKER_EXIT',worker_exit=process.exitcode)
        result['supervisor_wall_seconds']=time.monotonic()-start
        result['worker_exit']=process.exitcode
        try:
            m.enforce_usage(dict(result['usage'],wall_seconds=result['supervisor_wall_seconds']))
        except m.ContractError as error:result.update(status='REJECTED',error=str(error))
        if result['status']=='OK':
            # No CAS/pointer publication: a local acceptance marker in this
            # operation's new directory only, after successful child exit.
            with (Path(request['output_root'])/'ACCEPTED.json').open('x') as f:
                json.dump(dict(profile_sha256=m.PROFILE_SHA256,identity=request['identity'],usage=result['usage']),f)
        return result
    finally:
        parent.close();child.close()

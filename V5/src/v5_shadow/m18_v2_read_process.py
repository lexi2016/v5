"""One fresh, read-only M18 page process using the existing bounded supervisor.

No output directory, rebuilt data, acceptance marker, Reader cache or pool.
Every request fully validates the persisted bundle under the unchanged profile.
Only a bounded page is returned, and only after footer gates and worker exit.
"""
import multiprocessing
import os
from pathlib import Path
import re
import sys
import time
from . import m18_offline_v2 as m
from . import m18_offline_v2_process as process

PAGE_RECEIPT_BYTES = 512 * 1024


def _validate(request):
    m.v1.exact(request, ('binding', 'kind', 'query'), 'V2_PAGE_REQUEST')
    binding = request['binding']
    m.v1.exact(binding, ('bundle_root', 'identity', 'manifest_sha256', 'profile_sha256'), 'V2_PAGE_BINDING')
    m.profile_check(binding['profile_sha256']);m.v1.identity_check(binding['identity'])
    m.require(type(binding['manifest_sha256']) is str and
              re.fullmatch('[0-9a-f]{64}', binding['manifest_sha256']) is not None, 'V2_MANIFEST_PIN')
    root = binding['bundle_root']
    m.require(type(root) is str and len(root) <= 4096 and Path(root).is_absolute()
              and '..' not in Path(root).parts, 'V2_PATH')
    kind = request['kind'];query = request['query']
    m.require(kind in ('overview', 'section', 'content', 'announcement', 'rebound'), 'V2_PAGE_ACTION')
    keys = () if kind == 'overview' else ('page',) if kind == 'content' else ('section',)
    if kind in ('announcement', 'rebound'):keys += ('projection',)
    if kind == 'rebound':keys += ('group',)
    if kind in ('section', 'announcement', 'rebound') and isinstance(query, dict) and 'cursor' in query: keys += ('cursor',)
    m.v1.exact(query, keys, 'V2_PAGE_QUERY')
    if kind == 'content':m.require(m.v1.integer(query['page'], 0, 2**63-1), 'V2_PAGE_INDEX')
    else:m.require(all(type(value) is str and len(value) <= 8192 for value in query.values()), 'V2_PAGE_QUERY')
    if kind == 'announcement':
        m.require(query['section'] == 'announcement_reviewed_analysis'
                  and query['projection'] == 'announcement_references', 'V2_PAGE_PROJECTION')
    if kind == 'rebound':
        from .module_api import M18_REBOUND_SECTION, M18_REBOUND_PROJECTION, M18_REBOUND_GROUPS
        m.require(query['section'] == M18_REBOUND_SECTION
                  and query['projection'] == M18_REBOUND_PROJECTION
                  and query['group'] in M18_REBOUND_GROUPS, 'V2_PAGE_PROJECTION')
    m.require(len(m.v1.canonical(request)) < 65536, 'V2_REQUEST_BYTES')


def check_page_receipt(value):
    m.require(type(value) is dict and value.get('status') in ('OK', 'REJECTED'), 'V2_RECEIPT_SCHEMA')
    keys = ('pid', 'status', 'payload') if value['status'] == 'OK' else ('pid', 'status', 'error')
    m.v1.exact(value, keys, 'V2_RECEIPT_SCHEMA')
    m.require(m.v1.integer(value['pid'], 1, 2**63-1), 'V2_RECEIPT_PID')
    if value['status'] == 'OK':
        m.require(type(value['payload']) is dict, 'V2_RECEIPT_SCHEMA')
    else:
        error = value['error']
        m.require(type(error) is str and (error == 'MODULE_RESULT_NOT_AVAILABLE'
                  or re.fullmatch(r'M18_[A-Z0-9_]{1,128}', error) is not None), 'V2_RECEIPT_ERROR')


def encode_page_receipt(value):
    check_page_receipt(value)
    raw = m.v1.canonical(value)
    m.require(0 < len(raw) <= PAGE_RECEIPT_BYTES, 'V2_RECEIPT_LENGTH')
    return raw


def _check_payload(value, request):
    binding = request['binding'];kind = request['kind'];query = request['query']
    m.require(value.get('identity') == binding['identity']
              and value.get('generation_id') == m.generation(binding['identity'])
              and value.get('profile_sha256') == binding['profile_sha256']
              and value.get('manifest_sha256') == binding['manifest_sha256'], 'V2_RECEIPT_IDENTITY')
    keys = ('schema', 'manifest_sha256', 'generation_id', 'identity', 'profile_sha256')
    if kind == 'overview':
        keys += ('content_chunks', 'sections')
    elif kind == 'content':
        keys += ('index', 'offset', 'bytes', 'sha256', 'data')
    else:
        keys += ('section', 'selection', 'cursor', 'offset', 'matched_total', 'not_loaded_count',
                 'remaining_entries', 'entries', 'next_cursor', 'loaded_count')
        if kind == 'announcement':keys += ('projection', 'announcement')
        if kind == 'rebound':keys += ('projection', 'group', 'rebound')
    m.v1.exact(value, keys, 'V2_RECEIPT_PAGE')
    schema = 'detail' if kind in ('section', 'announcement', 'rebound') else kind
    m.require(value['schema'] == m.VERSION + '.' + schema, 'V2_RECEIPT_PAGE')
    if kind == 'content':
        page = query['page']
        m.require(m.v1.integer(value['index'], page, page)
                  and m.v1.integer(value['offset'], page*m.PROFILE['chunk_bytes'], page*m.PROFILE['chunk_bytes']),
                  'V2_RECEIPT_PAGE')
    elif kind in ('section', 'announcement', 'rebound'):
        cursor = query.get('cursor');offset = 0
        if cursor is not None:
            encoded = m.base64.b64decode(cursor, altchars=b'-_', validate=True)
            cursor_value, _ = m.v1.parse(encoded, object_limit=True)
            offset = cursor_value['offset']
        m.require(value['section'] == query['section'] and value['selection'] is None
                  and value['cursor'] == cursor and m.v1.integer(value['offset'], offset, offset),
                  'V2_RECEIPT_PAGE')
        if kind == 'announcement':
            from .module_api import _m18_announcement_cursor
            m.require(value['projection'] == query['projection'], 'V2_RECEIPT_PAGE')
            meta = value['announcement']
            m.v1.exact(meta, ('status', 'plan_cutoff', 'gaps', 'source_section_sha256',
                             'reference_count', 'products'), 'V2_RECEIPT_PAGE')
            m.require(type(meta['source_section_sha256']) is str
                      and re.fullmatch('[0-9a-f]{64}', meta['source_section_sha256']) is not None
                      and m.v1.integer(meta['reference_count'], 0, m.v1.MAX_ENTRIES)
                      and meta['reference_count'] == value['matched_total'], 'V2_RECEIPT_PAGE')
            if cursor is not None:
                m.require(cursor == _m18_announcement_cursor(value, meta['source_section_sha256'], offset)
                          and m.v1.integer(offset, m.v1.PAGE_SIZE, meta['reference_count']-1)
                          and offset % m.v1.PAGE_SIZE == 0, 'V2_RECEIPT_PAGE')
        if kind == 'rebound':
            from .module_api import _m18_rebound_cursor, M18_REBOUND_GROUPS
            m.require(value['projection'] == query['projection'] and value['group'] == query['group'],
                      'V2_RECEIPT_PAGE')
            meta = value['rebound']
            m.v1.exact(meta, ('source_section_sha256', 'group_counts', 'source', 'observation'),
                       'V2_RECEIPT_PAGE')
            m.v1.exact(meta['group_counts'], M18_REBOUND_GROUPS, 'V2_RECEIPT_PAGE')
            m.require(type(meta['source_section_sha256']) is str
                      and re.fullmatch('[0-9a-f]{64}', meta['source_section_sha256']) is not None
                      and all(m.v1.integer(count, 0, m.v1.MAX_ENTRIES) for count in meta['group_counts'].values())
                      and meta['group_counts'][query['group']] == value['matched_total']
                      and type(meta['source']) is dict and type(meta['observation']) is dict,
                      'V2_RECEIPT_PAGE')
            if cursor is not None:
                m.require(cursor == _m18_rebound_cursor(value, meta['source_section_sha256'], query['group'], offset)
                          and m.v1.integer(offset, m.v1.PAGE_SIZE, value['matched_total']-1)
                          and offset % m.v1.PAGE_SIZE == 0, 'V2_RECEIPT_PAGE')


class PageSender(process.ReceiptSender):
    def encode(self, result):
        return encode_page_receipt(result)


def _worker(request, sender):
    sys.dont_write_bytecode = True
    def audit(event, args):
        if event.startswith('socket.') or event == 'subprocess.Popen':
            raise m.ContractError('M18_V2_EXECUTION_DENIED')
        if event == 'open':
            mode, flags = args[1:3]
            if ((isinstance(mode, str) and any(c in mode for c in 'wax+'))
                    or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))):
                raise m.ContractError('M18_V2_WRITE_DENIED')
    sys.addaudithook(audit)
    result = dict(pid=os.getpid(), status='REJECTED')
    try:
        _validate(request)
        from .module_api import _m18_disk_reader, _m18_semantic_value
        reader = _m18_disk_reader(request['binding'])
        if request['kind'] == 'content':
            value = reader.content(request['query']['page'])
        else:
            value = _m18_semantic_value(reader, request['kind'], request['query'])
        reader._guard.checkpoint('read_page_complete')
        result.update(status='OK', payload=value)
    except FileNotFoundError:result['error'] = 'MODULE_RESULT_NOT_AVAILABLE'
    except m.ContractError as error:result['error'] = str(error)
    except Exception:result['error'] = 'M18_V2_WORKER_FAILED'
    sender.send(result)


def _entry(worker, request, connection):
    sender = PageSender(connection)
    try:worker(request, sender)
    except (OSError, m.ContractError):pass  # Parent rejects missing/truncated receipt.
    finally:sender.close()


def run(request):
    """Return no page until the fresh reader exits and original resource gates pass."""
    try:_validate(request)
    except (m.ContractError, ValueError, TypeError):
        return dict(status='REJECTED', error='M18_V2_PAGE_REQUEST')
    context = multiprocessing.get_context('spawn');parent, child = context.Pipe(duplex=False)
    worker = context.Process(target=_entry, args=(_worker, request, child))
    start = time.monotonic();deadline = start + m.PROFILE['wall_seconds'];result = None
    try:
        worker.start();child.close()
        result = process.receive_receipt(parent.fileno(), deadline,
                     receipt_bytes=PAGE_RECEIPT_BYTES, check=check_page_receipt)
        worker.join(max(0, deadline-time.monotonic()))
        m.require(time.monotonic() <= deadline and not worker.is_alive(), 'V2_RESOURCE_WALL_SECONDS')
        m.require(worker.exitcode == 0, 'V2_WORKER_EXIT')
        m.require(result['pid'] == worker.pid, 'V2_RECEIPT_PID')
        m.enforce_usage(dict(result['usage'], wall_seconds=time.monotonic()-start))
        if result['status'] == 'OK':_check_payload(result['payload'], request)
        elapsed = time.monotonic()-start
        m.enforce_usage(dict(result['usage'], wall_seconds=elapsed))
        return dict(result, supervisor_wall_seconds=elapsed,
                    worker_exit=worker.exitcode, worker_reaped=True)
    except (m.ContractError, OSError, EOFError) as error:
        reaped = process._reap(worker)
        return dict(status='REJECTED',error=str(error) if isinstance(error,m.ContractError) else 'M18_V2_RECEIPT_IO',
                    supervisor_wall_seconds=time.monotonic()-start,worker_exit=worker.exitcode,worker_reaped=reaped)
    finally:
        if worker.pid is not None:process._reap(worker)
        parent.close();child.close()

"""Bounded, append-only M14 history capture, with strict offline resume audit.

Only CLI ``capture`` selects the unchanged real connector. ``plan`` and
``resume`` are offline. Callables require an explicit connector. This module
never repairs/publishes panels, changes the original task, or qualifies data.
"""
from __future__ import annotations
import argparse
import ast
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import sys
import time
import types
import uuid

CAPTURE_HELPER_SHA256 = 'e1a5fc5dba23dd10c727f002848b38e6d688b98316c99480bbef95fd97c66312'
RECORD_HELPER_SHA256 = '0c6236be65fb52c78b04c124dad90b0d5413c41d78e00bc00d73f1706e1985cc'
TASK_SCHEMA = 'v5.m14_history_batch_task.v1'
PLAN_SCHEMA = 'v5.m14_history_batch_plan.v1'
CONTEXT_SCHEMA = 'v5.m14_history_batch_context.v1'
REUSE_CODES = frozenset(('HK.00001', 'HK.02825', 'HK.03469'))
MAX_MEMBERS, MAX_KEYS, MAX_SECONDS = 1000, 20000, 3600
MAX_EVIDENCE_BYTES = 512 * 1024**2
GROUPS = ('strict', 'near', 'pending', 'excluded', 'screen_unresolved')


def _bootstrap_read(path):
    """Read the pinned helper without executing imports or following symlinks."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('BATCH_HELPER_ABSOLUTE_PATH')
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = next_fd
        source_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            before = os.fstat(source_fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > 1024**2:
                raise ValueError('BATCH_HELPER_BOUNDED_REGULAR_FILE')
            with os.fdopen(os.dup(source_fd), 'rb') as handle:
                raw = handle.read(1024**2 + 1)
            if _identity(before) != _identity(os.fstat(source_fd)):
                raise ValueError('BATCH_HELPER_CHANGED')
            return raw
        finally:
            os.close(source_fd)
    finally:
        os.close(fd)


def _identity(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def _helper(path):
    raw = _bootstrap_read(path)
    if hashlib.sha256(raw).hexdigest() != CAPTURE_HELPER_SHA256:
        raise ValueError('BATCH_CAPTURE_HELPER_SHA')
    module = types.ModuleType('_m14_pinned_canary')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def _aware(value):
    if not isinstance(value, str): raise ValueError('BATCH_CLOCK_TEXT')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('BATCH_CLOCK_NAIVE')
    return parsed.astimezone(timezone.utc)


def _record_validator(h, baseline_root):
    path = Path(baseline_root) / 'src/v5_shadow/rebound_raw_repair.py'
    raw = h._read(path)
    if h._sha(raw) != RECORD_HELPER_SHA256:
        raise ValueError('BATCH_RECORD_HELPER_SHA')
    nodes = [n for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef) and n.name == '_record']
    if len(nodes) != 1: raise ValueError('BATCH_RECORD_HELPER_AST')
    scope = dict(re=re, _sha=h._sha, _canonical=h._canonical, sha=h._digest, aware=_aware,
                 SUCCESS_STATUSES=frozenset(('RESPONSE_CAPTURED', 'READY', 'PENDING')))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
    return scope['_record']


def _codes(h, value):
    if (not isinstance(value, list) or not 1 <= len(value) <= MAX_MEMBERS
            or any(not isinstance(c, str) or not re.fullmatch(r'HK\.[0-9]{5}', c) for c in value)
            or len(value) != len(set(value)) or value != sorted(value)):
        raise ValueError('BATCH_EXACT_MEMBER_CODES')
    return value


def _task(h, task, now):
    h._exact(task, ('schema_version', 'target_date', 'signal_date', 'prepared_at', 'valid_until',
        'exact_member_codes', 'exact_member_codes_sha256', 'keys', 'keys_sha256',
        'expected_panel_sha256', 'original_reference', 'parent_binding', 'initial_reuse'))
    if task['schema_version'] != TASK_SCHEMA: raise ValueError('BATCH_TASK_SCHEMA')
    members = _codes(h, task['exact_member_codes'])
    if h._digest(task['exact_member_codes_sha256']) != h._sha(h._canonical(members)):
        raise ValueError('BATCH_MEMBER_SHA')
    keys = task['keys']
    if not isinstance(keys, list) or not 1 <= len(keys) <= MAX_KEYS:
        raise ValueError('BATCH_KEYS_BOUND')
    pairs = []
    for k in keys:
        h._exact(k, ('code', 'date'))
        if k['code'] not in members: raise ValueError('BATCH_KEY_OUTSIDE_ORIGINAL_POOL')
        pairs.append((k['code'], h._day(k['date'])))
    if len(set(pairs)) != len(pairs) or pairs != sorted(pairs):
        raise ValueError('BATCH_KEYS_DUPLICATE_OR_ORDER')
    if h._digest(task['keys_sha256']) != h._sha(h._canonical(keys)):
        raise ValueError('BATCH_KEYS_SHA')
    # Reuse the original full identity/date/request-scope validation per code.
    for code in sorted({c for c, _ in pairs}):
        small = {k: copy.deepcopy(task[k]) for k in ('target_date', 'signal_date',
            'expected_panel_sha256', 'original_reference', 'parent_binding')}
        small.update(schema_version=h.TASK_SCHEMA, canary_codes=[code],
                     keys=[k for k in keys if k['code'] == code])
        h._task(small)
    prepared, expires = _aware(task['prepared_at']), _aware(task['valid_until'])
    if not prepared <= now <= expires or not 0 < (expires - prepared).total_seconds() <= 7200:
        raise ValueError('BATCH_TASK_STALE_OR_TIME_WINDOW')
    reuse = task['initial_reuse']
    if not isinstance(reuse, list) or len(reuse) != 3:
        raise ValueError('BATCH_THREE_CANARY_RECEIPTS_REQUIRED')
    seen = set()
    for descriptor in reuse:
        h._exact(descriptor, ('code', 'receipt_path', 'receipt_sha256', 'plan_path', 'plan_sha256'))
        code = descriptor['code']
        if code in seen or code not in REUSE_CODES or code not in {c for c, _ in pairs}:
            raise ValueError('BATCH_REUSE_CODE_SCOPE')
        seen.add(code)
        for field in ('receipt_path', 'plan_path'):
            if not isinstance(descriptor[field], str) or not Path(descriptor[field]).is_absolute():
                raise ValueError('BATCH_REUSE_ABSOLUTE_PATH')
            h._absolute(descriptor[field])
        h._digest(descriptor['receipt_sha256']); h._digest(descriptor['plan_sha256'])
    if seen != REUSE_CODES: raise ValueError('BATCH_REUSE_SET')
    return copy.deepcopy(task)


def _file_snapshot(h, path, *, content=False):
    path = h._absolute(path)
    parent = h._open_directory(path.parent)
    try: fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally: os.close(parent)
    try:
        before = os.fstat(fd)
        limit = 16 * 1024**2 if content else MAX_EVIDENCE_BYTES
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError('BATCH_EVIDENCE_BYTES_BOUND')
        digest, chunks, total = hashlib.sha256(), [], 0
        while True:
            chunk = os.read(fd, 1024**2)
            if not chunk: break
            total += len(chunk)
            if total > limit: raise ValueError('BATCH_EVIDENCE_BYTES_BOUND')
            digest.update(chunk)
            if content: chunks.append(chunk)
        if _identity(before) != _identity(os.fstat(fd)): raise ValueError('BATCH_EVIDENCE_CHANGED')
        return dict(path=str(path), sha256=digest.hexdigest(), identity=_identity(before),
                    raw=b''.join(chunks) if content else None)
    finally: os.close(fd)


def _context(h, task, path):
    raw = h._read(path); ctx = h._json(raw)
    h._exact(ctx, ('schema_version', 'target_date', 'signal_date', 'original_reference',
        'parent_binding', 'exact_member_codes', 'keys', 'files'))
    if ctx['schema_version'] != CONTEXT_SCHEMA: raise ValueError('BATCH_CONTEXT_SCHEMA')
    for key in ('target_date', 'signal_date', 'original_reference', 'parent_binding', 'exact_member_codes', 'keys'):
        if h._canonical(ctx[key]) != h._canonical(task[key]): raise ValueError('BATCH_CONTEXT_IDENTITY:'+key)
    names = ('original_artifact', 'original_manifest', 'original_receipt', 'parent_pointer', 'parent_manifest', 'parent_panel')
    h._exact(ctx['files'], names)
    snapshots = {}
    for name in names:
        p = ctx['files'][name]
        if not isinstance(p, str) or not Path(p).is_absolute(): raise ValueError('BATCH_CONTEXT_PATH')
        snapshots[name] = _file_snapshot(h, p, content=name != 'parent_panel')
    original, parent = task['original_reference'], task['parent_binding']
    for name in names:
        expected = original[name[9:]+'_sha256'] if name.startswith('original_') else parent[name+'_sha256']
        if snapshots[name]['sha256'] != expected: raise ValueError('BATCH_CONTEXT_FILE_SHA:'+name)
    docs = {k: h._json(s['raw']) for k,s in snapshots.items() if s['raw'] is not None}
    artifact, manifest, receipt = (docs['original_'+k] for k in ('artifact','manifest','receipt'))
    if (any(d.get('run_id') != original['run_id'] for d in (artifact,manifest,receipt))
        or artifact.get('schema_version') != 'v5.rebound_owner.v1'
        or manifest.get('schema_version') != 'v5.rebound_owner_manifest.v1'
        or receipt.get('schema_version') != 'v5.rebound_owner_receipt.v1'
        or receipt.get('status') != 'COMMITTED'
        or manifest.get('artifact_sha256') != original['artifact_sha256']
        or receipt.get('artifact_sha256') != original['artifact_sha256']
        or receipt.get('manifest_sha256') != original['manifest_sha256']):
        raise ValueError('BATCH_ORIGINAL_REFERENCE_CONTRACT')
    request = artifact['request']
    if (request.get('target_date') != task['target_date'] or request.get('signal_date') != task['signal_date']
        or artifact.get('request_sha256') != h._sha(h._canonical(request))
        or manifest.get('request_sha256') != artifact['request_sha256']
        or manifest.get('target_date') != task['target_date']):
        raise ValueError('BATCH_ORIGINAL_REQUEST_IDENTITY')
    observed = []
    for group in GROUPS:
        rows = artifact['research_observation'].get(group)
        if not isinstance(rows, list): raise ValueError('BATCH_ORIGINAL_MEMBER_GROUP')
        observed.extend(row['code'] for row in rows)
    if len(observed) != len(set(observed)) or sorted(observed) != task['exact_member_codes']:
        raise ValueError('BATCH_ORIGINAL_MEMBER_POOL')
    for role in ('panel', 'panel_manifest'):
        field = 'parent_panel' if role == 'panel' else 'parent_manifest'
        expected_path = 'assets/hk_0_2/' + parent[field+'_relative']
        if request['paths'].get(role) != expected_path or request['files'].get(expected_path) != parent[field+'_sha256']:
            raise ValueError('BATCH_ORIGINAL_PARENT_BINDING')
    pointer, panel_manifest = docs['parent_pointer'], docs['parent_manifest']
    if (pointer.get('manifest_relative') != parent['parent_manifest_relative']
        or panel_manifest.get('panel_relative') != parent['parent_panel_relative']
        or panel_manifest.get('panel_sha256') != parent['parent_panel_sha256']
        or panel_manifest.get('panel_max_date') != task['signal_date']):
        raise ValueError('BATCH_LIVE_PARENT_POINTER')
    return dict(sha256=h._sha(raw), snapshots=snapshots, path=str(h._absolute(path)))


def _check_context_unchanged(h, snapshot, *, full=False):
    if h._sha(h._read(snapshot['path'])) != snapshot['sha256']: raise ValueError('BATCH_CONTEXT_CHANGED')
    for name, expected in snapshot['snapshots'].items():
        path = Path(expected['path']); fd = h._open_directory(path.parent)
        try:
            current = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
            if not stat.S_ISREG(current.st_mode) or _identity(current) != expected['identity']:
                raise ValueError('BATCH_CONTEXT_STAT_CHANGED:'+name)
        finally: os.close(fd)
        if full or name == 'parent_pointer':
            if _file_snapshot(h, path)['sha256'] != expected['sha256']:
                raise ValueError('BATCH_CONTEXT_FILE_CHANGED:'+name)


def _check_record(h, record, task, code, plan_sha, validator, now):
    for field in ('original_reference', 'parent_binding', 'expected_panel_sha256', 'target_date', 'signal_date'):
        if record.get(field) != task[field]: raise ValueError('BATCH_RECEIPT_IDENTITY:'+field)
    request = dict(h.QUERY, code=code[3:])
    if (record.get('code') != code or record.get('plan_sha256') != plan_sha
        or record.get('source_sha256') != h.SOURCE_SHA or record.get('endpoint') != h.ENDPOINT
        or record.get('request') != request or record.get('request_sha256') != h._sha(h._canonical(request))
        or record.get('query_attempted') is not True
        or any(record.get(k) is not v for k,v in h.SAFETY.items())):
        raise ValueError('BATCH_RECEIPT_REQUEST_OR_SAFETY')
    for field in ('request_started_at','request_finished_at'):
        if _aware(record[field]) > now: raise ValueError('BATCH_RECEIPT_FUTURE_CLOCK')
    if record['status'] == 'RESPONSE_CAPTURED':
        validator(record, now)
        if record.get('diagnostics') != h._diagnostics(code, record['source_rows'], task):
            raise ValueError('BATCH_RECEIPT_DIAGNOSTICS')
    elif record['status'] not in ('QUERY_FAILED','RESPONSE_INVALID','CLOCK_INVALID'):
        raise ValueError('BATCH_RECEIPT_STATUS')
    elif record.get('source_rows') is not None and record.get('response_sha256') != h._sha(h._canonical(record['source_rows'])):
        raise ValueError('BATCH_RECEIPT_FAILED_RESPONSE_SHA')


def _reuse(h, task, baseline_root, validator, now):
    records = []
    for d in task['initial_reuse']:
        raw, plan_raw = h._read(d['receipt_path'], h.MAX_RESPONSE_BYTES*2), h._read(d['plan_path'])
        if h._sha(raw) != d['receipt_sha256'] or h._sha(plan_raw) != d['plan_sha256']:
            raise ValueError('BATCH_REUSE_FILE_SHA')
        plan, record = h._json(plan_raw), h._json(raw)
        if h._canonical(plan) != h._canonical(h.prepare_plan(plan['task'], baseline_root=baseline_root)):
            raise ValueError('BATCH_REUSE_CANARY_PLAN')
        small = plan['task']
        for field in ('original_reference','parent_binding','expected_panel_sha256','target_date','signal_date'):
            if small[field] != task[field]: raise ValueError('BATCH_REUSE_CANARY_IDENTITY')
        if (d['code'] not in small['canary_codes'] or record['status'] != 'RESPONSE_CAPTURED'
            or not {(k['code'],k['date']) for k in small['keys']} <= {(k['code'],k['date']) for k in task['keys']}):
            raise ValueError('BATCH_REUSE_CANARY_SCOPE')
        _check_record(h, record, small, d['code'], d['plan_sha256'], validator, now)
        records.append(dict(descriptor=copy.deepcopy(d), record=record, raw=raw))
    return records


def _prepare(task, *, baseline_root, capture_helper, context_file, clock=None):
    h = _helper(capture_helper); functions, source = h._baseline(baseline_root)
    clock = functions['_clock'] if clock is None else clock
    now = _aware(h._time(clock)); task = _task(h, task, now)
    context = _context(h, task, context_file)
    validator = _record_validator(h, baseline_root)
    reused = _reuse(h, task, baseline_root, validator, now)
    plan = dict(schema_version=PLAN_SCHEMA, task=task, source=source,
        capture_helper_sha256=CAPTURE_HELPER_SHA256, record_helper_sha256=RECORD_HELPER_SHA256,
        context_file_sha256=context['sha256'], request_template=dict(h.QUERY), endpoint=h.ENDPOINT,
        max_connections_per_invocation=1, max_members=MAX_MEMBERS, max_keys=MAX_KEYS,
        query_codes=sorted({k['code'] for k in task['keys']}-REUSE_CODES),
        initial_reuse=[copy.deepcopy(r['descriptor']) for r in reused],
        minimum_query_interval_seconds=1.0, auto_retry=False,
        date_selection='EXACT_KEYS_AFTER_NATIVE_OFFSET_COUNT_RESPONSE',
        qualification='CAPTURE_ONLY_NO_REPAIR_OR_FORMAL_AUTHORITY',
        calendar_scope_validation='EXISTING_OWNER_PRIOR60_VALIDATION_REQUIRED', **h.SAFETY)
    return h, functions, validator, context, reused, plan, clock


def prepare_plan(task, *, baseline_root, capture_helper, context_file, clock=None):
    """Offline pinning against actual original artifact and live parent bytes."""
    return _prepare(task, baseline_root=baseline_root, capture_helper=capture_helper,
                    context_file=context_file, clock=clock)[5]


class _Journal:
    """Create-once hash chain. Unknown/orphan files fail closed, never retry."""
    def __init__(self, h, path, plan, reused, *, create):
        self.h=h; self.path=h._absolute(path); self.plan=plan; self.plan_sha=h._sha(h._canonical(plan))
        self.fd=None; self.refs={}; self.events=[]; self.head=None
        try:
            try: self.fd=h._open_directory(self.path); fresh=False
            except FileNotFoundError:
                if not create: raise
                self.fd=h._new_output(self.path); fresh=True
            fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if fresh:
                self.run_id=uuid.uuid4().hex
                refs=[h._write_once(self.fd,'plan.json',plan),h._write_once(self.fd,'run.json',dict(
                    schema_version='v5.m14_history_batch_run.v1',run_id=self.run_id,
                    plan_sha256=self.plan_sha,task_sha256=h._sha(h._canonical(plan['task']))))]
                for item in reused:
                    # Canary wrote canonical JSON; preserving that whole record is byte-identical.
                    if h._canonical(item['record']) != item['raw']: raise ValueError('BATCH_REUSE_CANONICAL_BYTES')
                    refs.append(h._write_once(self.fd,'reuse-'+item['descriptor']['code']+'.json',item['record']))
                self.append('INITIALIZED',refs)
            self._audit()
        except BaseException:
            if self.fd is not None: os.close(self.fd); self.fd=None
            raise
    def close(self):
        if self.fd is not None: os.close(self.fd); self.fd=None
    def append(self, kind, references):
        event=dict(schema_version='v5.m14_history_batch_checkpoint.v1',index=len(self.events),
            run_id=self.run_id,plan_sha256=self.plan_sha,previous_sha256=self.head,
            kind=kind,files=references)
        ref=self.h._write_once(self.fd,f'checkpoint-{len(self.events):06d}.json',event)
        self.events.append(event); self.head=ref['sha256']
        for r in references: self.refs[r['relative']]=r
    def write(self,name,value,kind):
        ref=self.h._write_once(self.fd,name,value); self.append(kind,[ref]); return ref
    def read(self,name): return self.h._json(self.h._read(self.path/name,MAX_EVIDENCE_BYTES))
    def _audit(self):
        h=self.h; names=set(os.listdir(self.fd)); checkpoints=sorted(n for n in names if re.fullmatch(r'checkpoint-[0-9]{6}\.json',n))
        if not checkpoints: raise ValueError('BATCH_INITIALIZATION_INCOMPLETE')
        run=self.read('run.json'); self.run_id=run.get('run_id')
        if (not isinstance(self.run_id,str) or not re.fullmatch(r'[0-9a-f]{32}',self.run_id)
            or run.get('plan_sha256')!=self.plan_sha or run.get('task_sha256')!=h._sha(h._canonical(self.plan['task']))
            or h._canonical(self.read('plan.json'))!=h._canonical(self.plan)):
            raise ValueError('BATCH_RESUME_PLAN_OR_RUN_IDENTITY')
        self.events=[]; self.refs={}; self.head=None
        for index,name in enumerate(checkpoints):
            if name!=f'checkpoint-{index:06d}.json': raise ValueError('BATCH_CHECKPOINT_SEQUENCE')
            raw=h._read(self.path/name); event=h._json(raw)
            h._exact(event,('schema_version','index','run_id','plan_sha256','previous_sha256','kind','files'))
            if (event['schema_version']!='v5.m14_history_batch_checkpoint.v1' or event['index']!=index
                or event['run_id']!=self.run_id or event['plan_sha256']!=self.plan_sha
                or event['previous_sha256']!=self.head or not isinstance(event['files'],list)):
                raise ValueError('BATCH_CHECKPOINT_IDENTITY')
            for r in event['files']:
                h._exact(r,('relative','sha256','record_pointer'))
                if (r['record_pointer']!='' or not re.fullmatch(r'[A-Za-z0-9._-]+\.json',r['relative'])
                    or r['relative'] in self.refs or r['relative'].startswith('checkpoint-')):
                    raise ValueError('BATCH_CHECKPOINT_REFERENCE')
                if h._sha(h._read(self.path/r['relative'],MAX_EVIDENCE_BYTES))!=h._digest(r['sha256']):
                    raise ValueError('BATCH_CHECKPOINT_FILE_SHA')
                self.refs[r['relative']]=r
            self.events.append(event); self.head=h._sha(raw)
        if names!=set(checkpoints)|set(self.refs): raise ValueError('BATCH_ORPHAN_OR_UNEXPECTED_FILE')
        if set(self.events[0]['files'][i]['relative'] for i in range(len(self.events[0]['files']))) != {'plan.json','run.json'}|{'reuse-'+c+'.json' for c in REUSE_CODES}:
            raise ValueError('BATCH_INITIAL_CHECKPOINT')


def _state(h,journal,validator,clock):
    task=journal.plan['task']; now=_aware(h._time(clock)); records={}; attempts={}; receipts=[]; sources=[]
    round_ids=[]
    for name,ref in journal.refs.items():
        if name.startswith('round-') and name.endswith('-start.json'):
            record=journal.read(name)
            if record.get('run_id')!=journal.run_id or record.get('plan_sha256')!=journal.plan_sha:
                raise ValueError('BATCH_ROUND_IDENTITY')
            round_ids.append(record['round_number'])
        elif name.startswith('attempt-'):
            record=journal.read(name); code=record.get('code')
            if (name!='attempt-'+str(code)+'.json' or code not in journal.plan['query_codes'] or code in attempts
                or record.get('run_id')!=journal.run_id or record.get('plan_sha256')!=journal.plan_sha
                or record.get('status')!='STARTED' or _aware(record['request_started_at'])>now
                or record.get('request')!=dict(h.QUERY,code=code[3:])):
                raise ValueError('BATCH_ATTEMPT_IDENTITY')
            attempts[code]=record
        elif name.startswith('receipt-') or name.startswith('reuse-'):
            record=journal.read(name); code=record.get('code')
            if code in records: raise ValueError('BATCH_DUPLICATE_CODE')
            if name.startswith('reuse-'):
                d=next((d for d in task['initial_reuse'] if d['code']==code),None)
                if d is None or name!='reuse-'+code+'.json' or ref['sha256']!=d['receipt_sha256']:
                    raise ValueError('BATCH_REUSE_CHECKPOINT_IDENTITY')
                # Original diagnostics were validated against its own canary plan.
            else:
                if name!='receipt-'+str(code)+'.json' or code not in attempts or record.get('batch_run_id')!=journal.run_id:
                    raise ValueError('BATCH_RESPONSE_WITHOUT_ATTEMPT')
                if record['request_started_at']!=attempts[code]['request_started_at']:
                    raise ValueError('BATCH_RESPONSE_ATTEMPT_CLOCK')
                _check_record(h,record,task,code,journal.plan_sha,validator,now)
            records[code]=record; receipts.append(ref)
            if record['status']=='RESPONSE_CAPTURED': sources.append(ref)
    if sorted(round_ids)!=list(range(1,len(round_ids)+1)): raise ValueError('BATCH_ROUND_SEQUENCE')
    missing={(k['code'],k['date']) for k in task['keys']}; blockers=set()
    for code,record in records.items():
        if record['status']!='RESPONSE_CAPTURED': blockers.add(record['status']); continue
        d=h._diagnostics(code,record['source_rows'],task); blockers.update(d['repair_blockers'])
        for index in d['exact_key_row_indexes']: missing.discard((code,h._row_day(record['source_rows'][index])))
    uncertain=sorted(set(attempts)-set(records)); failed=sorted(c for c,r in records.items() if r['status']!='RESPONSE_CAPTURED')
    pending=sorted(set(journal.plan['query_codes'])-set(attempts))
    if uncertain: blockers.add('UNKNOWN_UNCERTAIN')
    if missing: blockers.add('EXACT_KEYS_MISSING')
    if pending: status='PARTIAL'
    elif uncertain or failed: status='FINISHED_WITH_ERRORS'
    else: status='CAPTURED'
    return dict(schema_version='v5.m14_history_batch_result.v1',status=status,
        plan_sha256=journal.plan_sha,run_id=journal.run_id,task=copy.deepcopy(task),source=journal.plan['source'],
        checkpoint_sha256=journal.head,sources=sorted(sources,key=lambda r:r['relative']),
        receipts=sorted(receipts,key=lambda r:r['relative']),receipt_count=len(receipts),
        successful_receipt_count=len(sources),reused_count=len(REUSE_CODES),attempted_count=len(attempts),
        remaining_query_count=len(pending),pending_codes=pending,uncertain_codes=uncertain,failed_codes=failed,
        missing_keys=[dict(code=c,date=d) for c,d in sorted(missing)],repair_blockers=sorted(blockers),
        exact_keys_present=not missing,repair_ready=False,round_count=len(round_ids),
        last_query_started_at=max((a['request_started_at'] for a in attempts.values()),default=None),
        qualification=journal.plan['qualification'],calendar_scope_validation=journal.plan['calendar_scope_validation'],**h.SAFETY)


def _validated(plan,**kwargs):
    if not isinstance(plan,dict) or 'task' not in plan: raise ValueError('BATCH_PLAN')
    prepared=_prepare(plan['task'],**kwargs)
    if prepared[0]._canonical(plan)!=prepared[0]._canonical(prepared[5]): raise ValueError('BATCH_PLAN_MISMATCH')
    return prepared


def resume_plan(plan,*,baseline_root,capture_helper,context_file,output_dir,clock=None):
    """Read-only audit: does not connect, query, or write another checkpoint."""
    h,_,validator,context,reused,_,clock=_validated(plan,baseline_root=baseline_root,capture_helper=capture_helper,context_file=context_file,clock=clock)
    journal=_Journal(h,output_dir,plan,reused,create=False)
    try:
        result=_state(h,journal,validator,clock); _check_context_unchanged(h,context,full=True); return result
    finally: journal.close()


def _limit(value,maximum,name,*,integer=False):
    if (isinstance(value,bool) or not isinstance(value,int if integer else (int,float))
        or not math.isfinite(value) or not 0<value<=maximum): raise ValueError('BATCH_'+name+'_BOUND')
    return value


def capture_plan(plan,*,baseline_root,capture_helper,context_file,output_dir,connector,
                 clock=None,monotonic=time.monotonic,sleep=time.sleep,max_calls=MAX_MEMBERS,max_seconds=900):
    """Capture or strictly resume. One connection; every started code is final.

    max_seconds gates new operations on the injected monotonic clock. The CLI
    additionally enforces a real POSIX wall-clock alarm, including stuck calls.
    A killed/interrupted STARTED attempt becomes UNKNOWN_UNCERTAIN, never retried.
    """
    _limit(max_calls,MAX_MEMBERS,'MAX_CALLS',integer=True); _limit(max_seconds,MAX_SECONDS,'MAX_SECONDS')
    started_mono=monotonic()
    h,functions,validator,context,reused,_,clock=_validated(plan,baseline_root=baseline_root,capture_helper=capture_helper,context_file=context_file,clock=clock)
    journal=_Journal(h,output_dir,plan,reused,create=True); api=None
    try:
        result=_state(h,journal,validator,clock)
        existing_receipt_count=result['receipt_count']
        if not result['pending_codes']:
            _check_context_unchanged(h,context,full=True)
            result.update(existing_receipt_count=existing_receipt_count,invocation_attempted_count=0,stop_reason='NO_UNATTEMPTED_CODES')
            return result
        round_number=result['round_count']+1; prefix=f'round-{round_number:06d}'
        journal.write(prefix+'-start.json',dict(schema_version='v5.m14_history_batch_round.v1',
            run_id=journal.run_id,plan_sha256=journal.plan_sha,round_number=round_number,
            started_at=h._time(clock),max_calls=max_calls,max_seconds=max_seconds), 'ROUND_STARTED')
        attempted=0; last_start=None; stop_reason=None
        if result['last_query_started_at'] is not None:
            elapsed=(_aware(h._time(clock))-_aware(result['last_query_started_at'])).total_seconds()
            last_start=monotonic()-max(0.,elapsed)
        if monotonic()-started_mono>=max_seconds: stop_reason='TIME_BUDGET'
        else:
            _check_context_unchanged(h,context)
            connect_started=h._time(clock)
            try:
                api,endpoint=connector()
                if endpoint!=h.ENDPOINT: raise ValueError('BATCH_ENDPOINT_MISMATCH')
                connection=dict(status='CONNECTED',error_type=None)
            except Exception as error:
                connection=dict(status='CONNECT_FAILED',error_type=type(error).__name__)
                stop_reason='CONNECT_FAILED'
            journal.write(prefix+'-connection.json',dict(connection,
                run_id=journal.run_id,plan_sha256=journal.plan_sha,endpoint=h.ENDPOINT,
                request_started_at=connect_started,request_finished_at=h._time(clock),**h.SAFETY),'CONNECTION_FINISHED')
            if stop_reason is None:
                for code in result['pending_codes']:
                    if attempted>=max_calls: stop_reason='MAX_CALLS'; break
                    delay=0. if last_start is None else max(0.,1.0-(monotonic()-last_start))
                    if monotonic()-started_mono+delay>=max_seconds: stop_reason='TIME_BUDGET'; break
                    if delay: sleep(delay)
                    _task(h,plan['task'],_aware(h._time(clock))); _check_context_unchanged(h,context)
                    if monotonic()-started_mono>=max_seconds: stop_reason='TIME_BUDGET'; break
                    request=dict(h.QUERY,code=code[3:]); started=h._time(clock)
                    journal.write('attempt-'+code+'.json',dict(schema_version='v5.m14_history_batch_attempt.v1',
                        run_id=journal.run_id,plan_sha256=journal.plan_sha,round_number=round_number,
                        code=code,status='STARTED',request=request,request_started_at=started,**h.SAFETY),'QUERY_STARTED')
                    last_start=monotonic(); attempted+=1
                    record=dict(schema_version='v5.m14_history_response_receipt.v1',code=code,
                        plan_sha256=journal.plan_sha,batch_run_id=journal.run_id,source_sha256=h.SOURCE_SHA,endpoint=h.ENDPOINT,
                        original_reference=copy.deepcopy(plan['task']['original_reference']),parent_binding=copy.deepcopy(plan['task']['parent_binding']),
                        expected_panel_sha256=plan['task']['expected_panel_sha256'],target_date=plan['task']['target_date'],signal_date=plan['task']['signal_date'],
                        request=request,request_sha256=h._sha(functions['_canonical'](request)),request_started_at=started,
                        response_acquired_at=None,request_finished_at=None,source_rows=None,response_sha256=None,
                        returned_count=None,status='QUERY_FAILED',error_code=None,query_attempted=True,**h.SAFETY)
                    try:
                        response=api.get_instrument_bars(4,71,code[3:],0,120)
                        record['response_acquired_at']=h._time(clock)
                        raw=functions['_canonical'](response)
                        if len(raw)>h.MAX_RESPONSE_BYTES: raise ValueError('HISTORY_CAPTURE_RESPONSE_BYTES_BOUND')
                        record['source_rows']=h._json(raw); record['response_sha256']=h._sha(raw)
                        if not isinstance(response,list) or len(response)>120 or any(not isinstance(r,dict) for r in response):
                            raise ValueError('HISTORY_CAPTURE_RESPONSE_SHAPE_OR_COUNT')
                        record['returned_count']=len(response); record['diagnostics']=h._diagnostics(code,record['source_rows'],plan['task'])
                        record['status']='RESPONSE_CAPTURED'
                    except Exception as error:
                        record['status']='QUERY_FAILED' if record['response_acquired_at'] is None else 'RESPONSE_INVALID'
                        record['error_code']='HISTORY_CAPTURE_'+record['status']; record['error_type']=type(error).__name__
                        # Avoid copying service messages that could contain unexpected private strings.
                    record['request_finished_at']=h._time(clock)
                    times=[_aware(record[k]) for k in ('request_started_at','response_acquired_at','request_finished_at') if record[k] is not None]
                    if times!=sorted(times): record.update(status='CLOCK_INVALID',error_code='HISTORY_CAPTURE_CLOCK_ORDER')
                    journal.write('receipt-'+code+'.json',record,'QUERY_FINISHED')
                    if record['status']!='RESPONSE_CAPTURED': stop_reason=record['status']; break
        if api is not None:
            try: api.disconnect()
            except Exception: stop_reason=stop_reason or 'DISCONNECT_FAILED'
            api=None
        _check_context_unchanged(h,context,full=True)
        journal._audit(); result=_state(h,journal,validator,clock)
        result.update(existing_receipt_count=existing_receipt_count,invocation_attempted_count=attempted,stop_reason=stop_reason,
                      capture_finished_at=h._time(clock),max_calls=max_calls,max_seconds=max_seconds)
        journal.write(prefix+'-result.json',result,'ROUND_FINISHED')
        return result
    except _DeadlineExpired:
        # CLI exits and the OS closes the socket. Never start another blocking
        # disconnect after the hard deadline has already fired.
        api=None
        raise
    finally:
        if api is not None:
            try: api.disconnect()
            except Exception: pass
        journal.close()


class _DeadlineExpired(BaseException): pass

@contextmanager
def _hard_deadline(seconds):
    """CLI-only hard deadline. BaseException preserves indeterminate attempts."""
    if not hasattr(signal,'setitimer'): raise ValueError('BATCH_POSIX_DEADLINE_REQUIRED')
    def expire(signum,frame): raise _DeadlineExpired('BATCH_WALL_CLOCK_DEADLINE')
    previous=signal.getsignal(signal.SIGALRM)
    if signal.getitimer(signal.ITIMER_REAL)!=(0.0,0.0): raise ValueError('BATCH_EXISTING_PROCESS_ALARM')
    signal.signal(signal.SIGALRM,expire); signal.setitimer(signal.ITIMER_REAL,seconds)
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0); signal.signal(signal.SIGALRM,previous)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='action',required=True)
    for name in ('plan','capture','resume'):
        p=sub.add_parser(name)
        p.add_argument('--baseline-root',required=True); p.add_argument('--capture-helper',required=True)
        p.add_argument('--context-file',required=True); p.add_argument('--output-dir',required=True)
        if name=='plan': p.add_argument('--task',required=True)
        else:
            p.add_argument('--plan',required=True); p.add_argument('--plan-sha256',required=True)
        if name=='capture':
            p.add_argument('--max-calls',type=int,required=True); p.add_argument('--max-seconds',type=float,required=True)
    args=parser.parse_args(argv); h=_helper(args.capture_helper)
    kwargs=dict(baseline_root=args.baseline_root,capture_helper=args.capture_helper,context_file=args.context_file)
    if args.action=='plan':
        plan=prepare_plan(h._json(h._read(args.task)),**kwargs); fd=h._new_output(args.output_dir)
        try: ref=h._write_once(fd,'plan.json',plan)
        finally: os.close(fd)
        print(json.dumps(dict(status='PLANNED_OFFLINE',plan=ref,**h.SAFETY),sort_keys=True)); return 0
    raw=h._read(args.plan)
    if h._sha(raw)!=h._digest(args.plan_sha256): raise ValueError('BATCH_PLAN_FILE_SHA')
    plan=h._json(raw)
    if args.action=='resume': result=resume_plan(plan,output_dir=args.output_dir,**kwargs)
    else:
        _limit(args.max_seconds,MAX_SECONDS,'MAX_SECONDS'); _limit(args.max_calls,MAX_MEMBERS,'MAX_CALLS',integer=True)
        functions,_=h._baseline(args.baseline_root)
        with _hard_deadline(args.max_seconds):
            result=capture_plan(plan,output_dir=args.output_dir,connector=functions['_connect'],
                                max_calls=args.max_calls,max_seconds=args.max_seconds,**kwargs)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True)); return 0 if result['status']=='CAPTURED' else 2

if __name__=='__main__':
    try: raise SystemExit(main())
    except (_DeadlineExpired,ValueError,OSError,KeyError,TypeError) as error:
        print(f'{type(error).__name__}: {error}',file=sys.stderr); raise SystemExit(2)

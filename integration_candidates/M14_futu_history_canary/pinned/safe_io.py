"""Bounded research-only M14 history capture; no owner/pointer publication.

Only CLI ``capture`` selects the real pinned connector. ``plan`` is offline.
The callable capture_plan requires an explicit connector for offline testing.
This preserves SDK-decoded native response rows, not TCP packet bytes. Dates
are selected after one offset/count request; there is no historical cutoff
argument and capture timestamps are never inferred from bar dates.
"""
from __future__ import annotations

import argparse
import ast
import copy
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any

SOURCE_SHA = 'fa7dcbce4ee026b0a02c47220820d0407af183553d3304afcc5db425dce33cbd'
SOURCE_RELATIVE = 'vendor/rebound_repair_baseline/hk_daily_supplement.py'
MANIFEST_SHA = '057a2c453ae562bc94564829dd8f78aba2b303bb7182a0b493fde9d4bedbafcd'
MANIFEST_RELATIVE = 'contracts/rebound_repair_source_manifest.json'
HOST, PORT = '119.97.142.130', 7721
ENDPOINT = '119.97.142.130:7721'
QUERY = dict(category=4, market=71, start=0, count=120)
SAFETY = dict(research_only=True, production_allowed=False, buy_gate_updated=False,
              orders_sent=False, formal=False, natural=False,
              formal_eligibility_verified=False, natural_verified=False)
TASK_SCHEMA = 'v5.m14_history_capture_task.v1'
PLAN_SCHEMA = 'v5.m14_history_capture_plan.v1'
MAX_INPUT_BYTES = 2 * 1024**2
MAX_RESPONSE_BYTES = 8 * 1024**2


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _exact(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('HISTORY_CAPTURE_EXACT_FIELDS')


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
        raise ValueError('HISTORY_CAPTURE_SHA256')
    return value


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{8}', value):
        raise ValueError('HISTORY_CAPTURE_DATE')
    date(int(value[:4]), int(value[4:6]), int(value[6:]))
    return value


def _absolute(path):
    path = Path(path)
    if '..' in path.parts:
        raise ValueError('HISTORY_CAPTURE_PARENT_TRAVERSAL')
    return Path(os.path.abspath(path))


def _open_directory(path):
    """Walk every component using held directory descriptors, never symlinks."""
    path = _absolute(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read(path, limit=MAX_INPUT_BYTES):
    path = _absolute(path)
    parent = _open_directory(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError('HISTORY_CAPTURE_INPUT_NOT_BOUNDED_REGULAR_FILE')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(raw) > limit or identity(before) != identity(after):
            raise ValueError('HISTORY_CAPTURE_INPUT_CHANGED')
        return raw
    finally:
        os.close(fd)


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('HISTORY_CAPTURE_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('HISTORY_CAPTURE_NONFINITE_JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def _new_output(path):
    """Create exactly one private, previously absent leaf under an existing parent."""
    path = _absolute(path)
    parent = _open_directory(path.parent)
    try:
        os.mkdir(path.name, 0o700, dir_fd=parent)  # Existing even empty directory is rejected.
        fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        os.fsync(parent)
        return fd
    finally:
        os.close(parent)


def _write_once(directory, name, value):
    if not re.fullmatch(r'[A-Za-z0-9._-]+\.json', name):
        raise ValueError('HISTORY_CAPTURE_OUTPUT_NAME')
    raw = _canonical(value)
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o400, dir_fd=directory)
    try:
        with os.fdopen(os.dup(fd), 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)
    os.fsync(directory)
    return dict(relative=name, sha256=_sha(raw), record_pointer='')


def _baseline(baseline_root):
    root = _absolute(baseline_root)
    manifest_raw = _read(root / MANIFEST_RELATIVE)
    if _sha(manifest_raw) != MANIFEST_SHA:
        raise ValueError('HISTORY_CAPTURE_SOURCE_MANIFEST_SHA')
    manifest = _json(manifest_raw)
    raw = _read(root / SOURCE_RELATIVE)
    if (len(raw) != manifest['bytes'] or _sha(raw) != SOURCE_SHA
            or manifest['sha256'] != SOURCE_SHA or manifest['relative_path'] != SOURCE_RELATIVE):
        raise ValueError('HISTORY_CAPTURE_SOURCE_SHA')
    names = ['_canonical', '_clock', '_connect']
    selected = [n for n in ast.parse(raw).body
                if isinstance(n, ast.FunctionDef) and n.name in names]
    if [n.name for n in selected] != names:
        raise ValueError('HISTORY_CAPTURE_SOURCE_FUNCTIONS')
    # No collector imports, module globals, or top-level executable code run.
    scope = dict(Any=Any, json=json, datetime=datetime, timezone=timezone,
                 SOURCE_HOST=HOST, SOURCE_PORT=PORT)
    exec(compile(ast.Module(body=selected, type_ignores=[]),
                 str(root / SOURCE_RELATIVE), 'exec'), scope)
    identity = dict(relative=SOURCE_RELATIVE, sha256=SOURCE_SHA,
        manifest_relative=MANIFEST_RELATIVE, manifest_sha256=MANIFEST_SHA,
        repository=manifest['repository'], commit=manifest['commit'],
        snapshot_path=manifest['snapshot_path'], extracted_functions=names,
        extraction_contract='UNCHANGED_FUNCTION_AST_NO_COLLECTOR_IMPORT',
        original_collector_count=6, bounded_history_count=120)
    return scope, identity


def _task(value):
    _exact(value, ('schema_version', 'target_date', 'signal_date', 'canary_codes',
                   'keys', 'expected_panel_sha256', 'original_reference', 'parent_binding'))
    if value['schema_version'] != TASK_SCHEMA:
        raise ValueError('HISTORY_CAPTURE_TASK_SCHEMA')
    target, signal = _day(value['target_date']), _day(value['signal_date'])
    if target <= signal:
        raise ValueError('HISTORY_CAPTURE_TARGET_SIGNAL_ORDER')
    codes = value['canary_codes']
    if (not isinstance(codes, list) or not 1 <= len(codes) <= 3
            or any(not isinstance(code, str) or not re.fullmatch(r'HK\.[0-9]{5}', code) for code in codes)
            or len(set(codes)) != len(codes)):
        raise ValueError('HISTORY_CAPTURE_EXPLICIT_CANARY_CODES')
    keys = value['keys']
    if not isinstance(keys, list) or not 1 <= len(keys) <= 360:
        raise ValueError('HISTORY_CAPTURE_KEYS_BOUND')
    seen = set()
    for key in keys:
        _exact(key, ('code', 'date'))
        if not isinstance(key['code'], str) or key['code'] not in codes or _day(key['date']) >= signal:
            raise ValueError('HISTORY_CAPTURE_KEY_SCOPE')
        pair = (key['code'], key['date'])
        if pair in seen:
            raise ValueError('HISTORY_CAPTURE_DUPLICATE_KEY')
        seen.add(pair)
    if {code for code, _ in seen} != set(codes):
        raise ValueError('HISTORY_CAPTURE_UNUSED_CANARY_CODE')
    for code in codes:
        if sum(stock == code for stock, _ in seen) > 120:
            raise ValueError('HISTORY_CAPTURE_KEYS_EXCEED_REQUEST_BOUND')
    original = value['original_reference']
    _exact(original, ('run_id', 'artifact_sha256', 'manifest_sha256', 'receipt_sha256'))
    if not isinstance(original['run_id'], str) or not re.fullmatch(r'[0-9a-f]{32}', original['run_id']):
        raise ValueError('HISTORY_CAPTURE_ORIGINAL_RUN_ID')
    for name in ('artifact_sha256', 'manifest_sha256', 'receipt_sha256'):
        _digest(original[name])
    binding = value['parent_binding']
    _exact(binding, ('parent_pointer_sha256', 'parent_manifest_relative', 'parent_manifest_sha256',
                     'parent_panel_relative', 'parent_panel_sha256'))
    for name in ('parent_pointer_sha256', 'parent_manifest_sha256', 'parent_panel_sha256'):
        _digest(binding[name])
    for name, suffix in (('parent_manifest_relative', 'manifest.json'),
                         ('parent_panel_relative', 'hkconnect_vipdoc_daily_panel.parquet')):
        path = binding[name]
        if (not isinstance(path, str) or not re.fullmatch(r'panels/[A-Za-z0-9._-]+/'+re.escape(suffix), path)
                or '..' in Path(path).parts):
            raise ValueError('HISTORY_CAPTURE_PARENT_BINDING_PATH')
    if Path(binding['parent_manifest_relative']).parent != Path(binding['parent_panel_relative']).parent:
        raise ValueError('HISTORY_CAPTURE_PARENT_BINDING_DIRECTORY')
    if _digest(value['expected_panel_sha256']) != binding['parent_panel_sha256']:
        raise ValueError('HISTORY_CAPTURE_EXPECTED_PANEL_SHA')
    return copy.deepcopy(value)


def prepare_plan(task, *, baseline_root):
    """Offline binding only. Owner integration must still validate prior60 keys."""
    validated = _task(task)
    _, identity = _baseline(baseline_root)
    return dict(schema_version=PLAN_SCHEMA, task=validated, source=identity,
        request_template=dict(QUERY), endpoint=ENDPOINT, max_connections=1,
        max_queries=len(validated['canary_codes']), auto_retry=False,
        date_selection='EXACT_KEYS_AFTER_NATIVE_OFFSET_COUNT_RESPONSE',
        calendar_scope_validation='EXISTING_OWNER_PRIOR60_VALIDATION_REQUIRED',
        qualification='CAPTURE_ONLY_NO_REPAIR_OR_FORMAL_AUTHORITY', **SAFETY)


def _time(clock):
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('HISTORY_CAPTURE_NAIVE_CLOCK')
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds')


def _row_day(row):
    """Date diagnostics match the pinned decoder; numeric decoding stays there."""
    value = row.get('datetime')
    if value:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').strftime('%Y%m%d')
    return date(int(row['year']), int(row['month']), int(row['day'])).strftime('%Y%m%d')


def _diagnostics(code, rows, task):
    wanted = {k['date'] for k in task['keys'] if k['code'] == code}
    seen, future, invalid, duplicates, selected = set(), [], [], [], []
    for index, row in enumerate(rows):
        try:
            day = _row_day(row)
        except (ValueError, KeyError, TypeError, OverflowError):
            invalid.append(index)
            continue
        if day in seen:
            duplicates.append(day)
        seen.add(day)
        if day > task['signal_date']:
            future.append(index)
        if day in wanted:
            selected.append(index)
    blockers = []
    for items, reason in ((future, 'FUTURE_ROWS_AFTER_SIGNAL_KEEP_RAW'),
                          (invalid, 'SOURCE_DATE_INVALID'),
                          (duplicates, 'DUPLICATE_SOURCE_DATES'),
                          (wanted-seen, 'EXACT_KEYS_MISSING')):
        if items:
            blockers.append(reason)
    return dict(future_row_indexes=future, invalid_date_row_indexes=invalid,
        duplicate_dates=sorted(set(duplicates)), exact_key_row_indexes=selected,
        missing_keys=[dict(code=code, date=day) for day in sorted(wanted-seen)],
        repair_blockers=blockers, source_rows_filtered=False)


def capture_plan(plan, *, baseline_root, output_dir, connector, clock=None):
    """Run the exact bounded requests using an explicitly supplied connector.

    The real connector is chosen only by CLI ``capture``. Tests supply a fake.
    Files are append-only by exclusive create, read-only, and hash-addressed;
    they are not claimed to resist deletion by the operating-system owner.
    """
    if not isinstance(plan, dict) or 'task' not in plan:
        raise ValueError('HISTORY_CAPTURE_PLAN')
    expected = prepare_plan(plan['task'], baseline_root=baseline_root)
    if _canonical(plan) != _canonical(expected):
        raise ValueError('HISTORY_CAPTURE_PLAN_MISMATCH')
    functions, _ = _baseline(baseline_root)
    clock = functions['_clock'] if clock is None else clock
    encode = functions['_canonical']
    task = plan['task']
    directory = _new_output(output_dir)
    api = None
    sources, receipts, records = [], [], []
    plan_sha = _sha(_canonical(plan))
    try:
        _write_once(directory, 'plan.json', plan)
        started = _time(clock)
        _write_once(directory, 'attempt.json', dict(schema_version='v5.m14_history_attempt.v1',
            plan_sha256=plan_sha, capture_started_at=started, endpoint=ENDPOINT, **SAFETY))
        connect_started = _time(clock)
        connect_error = None
        try:
            api, endpoint = connector()
            if endpoint != ENDPOINT:
                raise ValueError('HISTORY_CAPTURE_CONNECTOR_ENDPOINT_MISMATCH')
        except Exception as error:
            connect_error = error
        if connect_error is not None:
            receipt = dict(schema_version='v5.m14_history_connect_receipt.v1',
                status='CONNECT_FAILED', error_code='HISTORY_CAPTURE_CONNECT_FAILED',
                error_type=type(connect_error).__name__, error_message=str(connect_error)[:500],
                request_started_at=connect_started, response_acquired_at=None,
                request_finished_at=_time(clock), query_attempted=False,
                plan_sha256=plan_sha, endpoint=ENDPOINT, **SAFETY)
            receipts.append(_write_once(directory, 'connection.json', receipt))
        else:
            for index, code in enumerate(task['canary_codes']):
                request = dict(QUERY, code=code[3:])
                record = dict(schema_version='v5.m14_history_response_receipt.v1', code=code,
                    plan_sha256=plan_sha, source_sha256=SOURCE_SHA, endpoint=ENDPOINT,
                    original_reference=copy.deepcopy(task['original_reference']),
                    parent_binding=copy.deepcopy(task['parent_binding']),
                    expected_panel_sha256=task['expected_panel_sha256'],
                    target_date=task['target_date'], signal_date=task['signal_date'],
                    request=request, request_sha256=_sha(encode(request)),
                    request_started_at=_time(clock), response_acquired_at=None,
                    request_finished_at=None, source_rows=None, response_sha256=None,
                    returned_count=None, status='QUERY_FAILED', error_code=None,
                    query_attempted=True, **SAFETY)
                try:
                    response = api.get_instrument_bars(4, 71, code[3:], 0, 120)
                    record['response_acquired_at'] = _time(clock)
                    # Hash and preserve the WHOLE native decoded response before diagnostics.
                    response_raw = encode(response)
                    if len(response_raw) > MAX_RESPONSE_BYTES:
                        raise ValueError('HISTORY_CAPTURE_RESPONSE_BYTES_BOUND')
                    record['source_rows'] = _json(response_raw)
                    record['response_sha256'] = _sha(response_raw)
                    if (not isinstance(response, list) or len(response) > 120
                            or any(not isinstance(row, dict) for row in response)):
                        raise ValueError('HISTORY_CAPTURE_RESPONSE_SHAPE_OR_COUNT')
                    record['returned_count'] = len(response)
                    record['diagnostics'] = _diagnostics(code, record['source_rows'], task)
                    record['status'] = 'RESPONSE_CAPTURED'
                except Exception as error:
                    record['status'] = 'QUERY_FAILED' if record['response_acquired_at'] is None else 'RESPONSE_INVALID'
                    record['error_code'] = 'HISTORY_CAPTURE_'+record['status']
                    record['error_type'] = type(error).__name__
                    record['error_message'] = str(error)[:500]
                record['request_finished_at'] = _time(clock)
                times = [record['request_started_at'], record['response_acquired_at'], record['request_finished_at']]
                actual = [value for value in times if value is not None]
                if actual != sorted(actual):
                    record['status'] = 'CLOCK_INVALID'
                    record['error_code'] = 'HISTORY_CAPTURE_CLOCK_ORDER'
                reference = _write_once(directory, f'request-{index:03d}-{code}.json', record)
                receipts.append(reference)
                records.append(record)
                if record['status'] == 'RESPONSE_CAPTURED':
                    sources.append(reference)
        disconnect_error = None
        if api is not None:
            try:
                api.disconnect()
            except Exception as error:
                disconnect_error = dict(error_type=type(error).__name__, error_message=str(error)[:500])
            api = None
        missing = {(key['code'], key['date']) for key in task['keys']}
        blockers = set()
        for record in records:
            if record['status'] != 'RESPONSE_CAPTURED':
                blockers.add(record['status'])
                continue
            diagnostics = record['diagnostics']
            blockers.update(diagnostics['repair_blockers'])
            for index in diagnostics['exact_key_row_indexes']:
                missing.discard((record['code'], _row_day(record['source_rows'][index])))
        if missing:
            blockers.add('EXACT_KEYS_MISSING')
        if connect_error is not None:
            blockers.add('CONNECT_FAILED')
        success = len(sources) == len(task['canary_codes'])
        result = dict(schema_version='v5.m14_history_capture_result.v1',
            status='CAPTURED' if success else ('PARTIAL' if sources else 'FAILED'),
            plan_sha256=plan_sha, task=copy.deepcopy(task), source=copy.deepcopy(plan['source']),
            sources=sources, receipts=receipts, capture_started_at=started,
            capture_finished_at=_time(clock), missing_keys=[dict(code=c,date=d) for c,d in sorted(missing)],
            repair_blockers=sorted(blockers), exact_keys_present=not missing,
            repair_ready=False, qualification=plan['qualification'],
            calendar_scope_validation=plan['calendar_scope_validation'],
            disconnect_error=disconnect_error, **SAFETY)
        _write_once(directory, 'result.json', result)
        return result
    finally:
        if api is not None:
            try:
                api.disconnect()
            except Exception:
                pass
        os.close(directory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    plan_parser = sub.add_parser('plan', help='offline validation and immutable plan only')
    plan_parser.add_argument('--task', required=True)
    capture_parser = sub.add_parser('capture', help='explicit one-connection bounded live acquisition')
    capture_parser.add_argument('--plan', required=True)
    capture_parser.add_argument('--plan-sha256', required=True)
    for child in (plan_parser, capture_parser):
        child.add_argument('--baseline-root', required=True)
        child.add_argument('--output-dir', required=True)
    args = parser.parse_args(argv)
    if args.action == 'plan':
        plan = prepare_plan(_json(_read(args.task)), baseline_root=args.baseline_root)
        directory = _new_output(args.output_dir)
        try:
            reference = _write_once(directory, 'plan.json', plan)
        finally:
            os.close(directory)
        print(json.dumps(dict(status='PLANNED_OFFLINE', plan=reference, **SAFETY), sort_keys=True))
        return 0
    raw = _read(args.plan)
    if _sha(raw) != _digest(args.plan_sha256):
        raise ValueError('HISTORY_CAPTURE_PLAN_FILE_SHA')
    plan = _json(raw)
    functions, _ = _baseline(args.baseline_root)
    result = capture_plan(plan, baseline_root=args.baseline_root, output_dir=args.output_dir,
                          connector=functions['_connect'])
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result['status'] == 'CAPTURED' else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        raise SystemExit(2)

"""One read-only aa42 projection diagnostic: scalar error, never business payload.

Run with the existing Python -B and the retained saved-view config. Uses the
unchanged supervised page worker exactly once; no oracle, trace, API listener,
new budget, cache, fixture build, publication or product mutation.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import sys
from v5_shadow import m18_offline_v2 as m
from v5_shadow import module_api
from v5_shadow import m18_v2_read_process as process


_ORIGINAL_WORKER = process._worker


def diagnostic_worker(request, sender):
    # Observe only a caught exception at the two existing boundaries. No tracing,
    # locals, payload text or retained exception/Reader objects.
    for name in ('_m18_disk_reader', '_m18_semantic_value'):
        original = getattr(module_api, name)
        def observed(*args, _original=original, _name=name, **kwargs):
            try:
                return _original(*args, **kwargs)
            except Exception as error:
                code = str(error)
                frame = error.__traceback__
                while frame is not None and frame.tb_next is not None:
                    frame = frame.tb_next
                print(json.dumps(dict(boundary=_name, exception_type=type(error).__name__,
                    error=code if re.fullmatch(r'M18_[A-Z0-9_]{1,128}', code) else 'REDACTED_NON_CODE',
                    terminal_function=frame.tb_frame.f_code.co_name if frame else None,
                    terminal_line=frame.tb_lineno if frame else None)), file=sys.stderr, flush=True)
                raise
        setattr(module_api, name, observed)
    _ORIGINAL_WORKER(request, sender)


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            result.update(block)
    return result.hexdigest()


def snapshot(roots):
    rows = {}
    for root in roots:
        for path in sorted(Path(root).rglob('*')):
            if path.is_symlink():
                raise ValueError('PROBE_SYMLINK_REJECTED')
            if path.is_file():
                info = path.stat()
                rows[str(path)] = (digest(path), info.st_size, info.st_mtime_ns)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config')
    args = parser.parse_args()
    if not sys.dont_write_bytecode:
        raise SystemExit('Run this one-shot diagnostic with Python -B')
    config, root_fd = module_api._config(json.loads(Path(args.config).read_text()))
    os.close(root_fd)
    binding = config['m18_v2_binding']
    roots = (binding['bundle_root'], config['data_root'])
    before = snapshot(roots)
    process._worker = diagnostic_worker
    result = process.run(dict(binding=binding, kind='rebound', query=dict(
        section='rebound_research_observation', projection='rebound_references', group='strict')))
    after = snapshot(roots)
    output = {key: result.get(key) for key in (
        'status', 'error', 'pid', 'usage', 'worker_exit', 'worker_reaped', 'supervisor_wall_seconds')}
    output.update(profile_sha256=m.PROFILE_SHA256,
        module_api_sha256=digest(Path(module_api.__file__)),
        read_process_sha256=digest(Path(process.__file__)),
        data_unchanged=before == after, file_count=len(before),
        request_count=1, oracle_used=False, trace_used=False)
    print(json.dumps(output, sort_keys=True))
    return 0 if before == after and result.get('worker_reaped') is True else 1


if __name__ == '__main__':
    raise SystemExit(main())

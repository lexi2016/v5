"""One external, read-only Reader lifetime diagnostic. No product/GC overrides.

Run with the fixed source on PYTHONPATH, --config <existing config> --port 0.
Stdout retains the ordinary API URL; stderr contains bounded metadata only.
The caller sends descriptor, overview, summary, gaps once then stops this child.
"""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import threading
import tempfile
import time
import weakref

from v5_shadow import m18_offline_v2 as m, module_api as api

EXPECTED = {
    'module_api': '72954bafd6d52a5e7f113fc870f912c4f85b2722e9a1a3db34dafc7a8553b188',
    'm18_offline_v2': 'ec243e381fe556acd3ff51880f8f2bace20c944f233894a9849ba963d047c680',
}
for name, module in (('module_api', api), ('m18_offline_v2', m)):
    if hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() != EXPECTED[name]:
        raise RuntimeError('FIXED_4C_SOURCE_MISMATCH_' + name)

live = weakref.WeakSet()
local = threading.local()
sequence = 0


def emit(event, **fields):
    # ps is an existing OS utility, not a loaded Reader/oracle. Do not sample in
    # scanner hot loops. RUSAGE_SELF always refers only to this service child.
    result = subprocess.run(['ps', '-o', 'rss=', '-p', str(os.getpid())],
                            check=True, capture_output=True, text=True)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    value = dict(event=event, sequence=getattr(local, 'sequence', None),
                 thread_id=threading.get_ident(), native_id=threading.get_native_id(),
                 active_threads=threading.active_count(),
                 current_rss_bytes=int(result.stdout.strip()) * 1024,
                 peak_rss_bytes=peak * (1 if sys.platform == 'darwin' else 1024),
                 live_readers=len(live), gc_counts=gc.get_count(), **fields)
    print(json.dumps(value, separators=(',', ':')), file=sys.stderr, flush=True)


original_init = m.Reader.__init__
original_parse = m.parse
original_checkpoint = m.ResourceGuard.checkpoint
original_disk = api._m18_disk_reader
original_semantic = api._m18_semantic_response


def reader_init(self, bundle, *args, **kwargs):
    live.add(self)
    local.bundle = bundle
    emit('reader_enter', consume_content=kwargs.get('consume_content', False),
         object_count=len(bundle.objects), object_bytes=sum(map(len, bundle.objects.values())))
    try:
        return original_init(self, bundle, *args, **kwargs)
    finally:
        del local.bundle


def parse(raw, scope, *args, **kwargs):
    if scope != 'response':
        return original_parse(raw, scope, *args, **kwargs)
    bundle = local.bundle
    emit('response_parse_enter', raw_bytes=len(raw), object_count=len(bundle.objects),
         object_bytes=sum(map(len, bundle.objects.values())))
    result = original_parse(raw, scope, *args, **kwargs)
    emit('response_parse_return')
    return result


def checkpoint(self, stage=None):
    if stage == 'json_response':
        emit('response_json_loaded')
    try:
        return original_checkpoint(self, stage)
    except m.ContractError as error:
        # Fixed ContractError vocabulary only, no exception text from input.
        emit('resource_failure', code=str(error), usage=self.usage())
        raise


def disk(binding):
    emit('disk_enter')
    return original_disk(binding)


def semantic(*args, **kwargs):
    global sequence
    sequence += 1
    local.sequence = sequence
    emit('semantic_enter')
    try:
        result = original_semantic(*args, **kwargs)
    except Exception:
        emit('semantic_error')
        raise
    emit('semantic_return')
    return result


def serve(config, mode):
    m.Reader.__init__ = reader_init
    m.parse = parse
    m.ResourceGuard.checkpoint = checkpoint
    api._m18_disk_reader = disk
    if mode == 'fixed_thread':
        from concurrent.futures import ThreadPoolExecutor
        executor = ThreadPoolExecutor(max_workers=1)
        def dispatch(*args, **kwargs):
            return executor.submit(semantic, *args, **kwargs).result()
        api._m18_semantic_response = dispatch
    else:
        api._m18_semantic_response = semantic
    emit('startup', python_version=sys.version.split()[0], platform=sys.platform,
         gil_enabled=getattr(sys, '_is_gil_enabled', lambda: True)(), source_sha256=EXPECTED,
         mode=mode)
    api.main(['--config', config, '--port', '0'])


def diagnose(config):
    from urllib.error import HTTPError
    from urllib.parse import urlencode
    from urllib.request import urlopen
    config_value = json.loads(Path(config).read_bytes())
    identity = config_value['m18_v2_binding']['identity']
    route = '/api/v4/manager/m18/v2'
    def snapshot():
        return {(kind, str(path.relative_to(root))):
                (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
                for kind, root in [('bundle', Path(config_value['m18_v2_binding']['bundle_root'])),
                                   ('publication', Path(config_value['data_root']))]
                for path in root.rglob('*') if path.is_file()}
    before = snapshot()
    arms = []
    with tempfile.TemporaryDirectory(prefix='v5-reader-boundary-') as temporary:
        for mode in ('ordinary', 'fixed_thread'):
            log = Path(temporary) / (mode + '.jsonl')
            requests = []
            with log.open('w') as errors:
                child = subprocess.Popen([sys.executable, '-B', __file__, '--config', config,
                                          '--serve', mode], stdout=subprocess.PIPE, stderr=errors,
                                         text=True)
                try:
                    url = child.stdout.readline().strip()
                    if not url.startswith('http://127.0.0.1:'):
                        raise RuntimeError('CHILD_START_FAILED')
                    generation = None
                    for section in ('descriptor', 'overview', 'summary', 'gaps'):
                        query = dict(run_id=identity['run_id'])
                        suffix = ''
                        if section != 'descriptor':
                            query['generation_id'] = generation
                            suffix = '/overview' if section == 'overview' else '/sections'
                            if section != 'overview': query['section'] = section
                        start = time.monotonic()
                        try: response = urlopen(url + route + suffix + '?' + urlencode(query), timeout=100)
                        except HTTPError as error: response = error
                        with response:
                            raw = response.read(256 * 1024 + 1)
                            if len(raw) > 256 * 1024: raise RuntimeError('BOUND_EXCEEDED')
                            value = json.loads(raw)
                            requests.append(dict(section=section, status=response.status, bytes=len(raw),
                                                 elapsed=time.monotonic()-start))
                        if response.status != 200: break
                        if value['identity'] != identity: raise RuntimeError('IDENTITY_MISMATCH')
                        if section == 'descriptor': generation = value['generation_id']
                        elif (value['generation_id'] != generation
                              or value['manifest_sha256'] != config_value['m18_v2_binding']['manifest_sha256']):
                            raise RuntimeError('PIN_MISMATCH')
                        if value['profile_sha256'] != config_value['m18_v2_binding']['profile_sha256']:
                            raise RuntimeError('PROFILE_MISMATCH')
                finally:
                    child.terminate()
                    child.wait(timeout=10)
            events = [json.loads(line) for line in log.read_text().splitlines()]
            arms.append(dict(mode=mode, requests=requests, events=events,
                             peak_rss_bytes=max(event['peak_rss_bytes'] for event in events),
                             child_stopped=child.poll() is not None))
            print(json.dumps(arms[-1], separators=(',', ':')), flush=True)
    print(json.dumps(dict(diagnostic_complete=True, data_unchanged=snapshot()==before,
                          file_count=len(before), product_changed=False, gc_forced=False,
                          budgets_changed=False, cross_request_reader_cache=False)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--serve', choices=('ordinary', 'fixed_thread'))
    args = parser.parse_args()
    if args.serve: serve(args.config, args.serve)
    else: diagnose(args.config)

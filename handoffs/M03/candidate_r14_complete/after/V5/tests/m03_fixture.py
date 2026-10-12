"""Offline original producer fixture. Never installed in the production runner."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ['M03_FIXED_SOURCE'])
OWNER = SOURCE / 'collector_owner'


def original_script():
    tree = ast.parse((SOURCE / 'V5/tests/test_cloud_us_collector.py').read_text())
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'test_successful_synthetic_rss_and_quotes_publish_and_original_reader_roundtrip')
    return next(n.value for n in ast.walk(method) if isinstance(n, ast.Constant) and isinstance(n.value, str) and 'class Proxy:' in n.value)


def child(script, *args, timeout=60):
    return subprocess.run([sys.executable, '-I', '-B', '-c', script, str(BASE / 'src'), str(OWNER), *map(str,args)], capture_output=True, text=True, timeout=timeout)


def make_source(root):
    from v5_shadow.cloud_us_collector import initialize_output
    initialize_output(root, OWNER)
    proc = child(original_script(), root)
    if proc.returncode:
        raise AssertionError(proc.stdout + proc.stderr)
    data = json.loads(proc.stdout)
    assert data['exit'] == 0 and data['counts'] == {'quote': 1, 'rss': 5, 'direct': 0}, data
    return data


class SourceCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='m03-r14-offline-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source'
        self.snapshot = self.root / 'snapshot'
        self.bindings = self.root / 'bindings'

    def request(self, **changes):
        from v5_shadow.us_source_daily import USSourceRequest
        values = dict(trade_date='20261009', capture_phase='POST_CLOSE', session='20261009', cutoff='2026-10-10T10:00:00Z', source_root=self.source, snapshot_root=self.snapshot, binding_root=self.bindings, owner_root=OWNER, v5_src=BASE / 'src')
        values.update(changes)
        return USSourceRequest(**values)


def inner_chain(req, setup=''):
    from v5_shadow.us_source_daily import _request_dict
    code = '''import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import v5_shadow.us_source_daily as m
req=m._request_from_dict(json.loads(sys.argv[3]))
def deny(event,args):
    if event.startswith(('socket.connect','socket.getaddrinfo','socket.sendto')):
        raise AssertionError('REAL_NETWORK_FORBIDDEN')
sys.addaudithook(deny)
''' + setup + '''\nprint(json.dumps(m._run_owned(req),sort_keys=True))\n'''
    return child(code, json.dumps(_request_dict(req)))


def variant_source(root, changes):
    from v5_shadow.cloud_us_collector import initialize_output
    initialize_output(root, OWNER)
    script = original_script()
    for old,new in changes:
        assert old in script, old
        script=script.replace(old,new)
    proc=child(script,root)
    if proc.returncode:
        raise AssertionError(proc.stdout+proc.stderr)
    return json.loads(proc.stdout)



def offline_collector_script():
    """Inject original Proxy fixture into the original main's transport seam."""
    import textwrap
    script=original_script()
    seam=script[script.index('owner._capture_now='):script.index('output=io.StringIO()')]
    return ("import sys,io,json\nfrom datetime import datetime,timezone\n"
            "sys.path.insert(0,sys.argv[1])\n"
            "import v5_shadow.cloud_us_collector as original\n"
            "saved=original.run_original_us_cli\n"
            "def offline(owner,transport,values,**ignored):\n"
            +textwrap.indent(seam,'    ')
            +"    return saved(owner,transport,values,allow_network_capture=True,transport_options={'proxy_url':'http://proxy.invalid','proxy_opener':Proxy(),'direct_opener':Direct()})\n"
            +"original.run_original_us_cli=offline\n"
            +"raise SystemExit(original.main(sys.argv[2:]))\n")

"""Managed read-only module_api subprocess launcher for P0 runtime.

The child only hosts the existing module_api contract. It never invokes owners,
producers, daily jobs, or ledger code.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
import tempfile
import signal

# The source bundle is relocatable; a managed child must not rely on the
# parent's in-memory sys.path or an inherited PYTHONPATH.
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = 'v5_shadow'


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--config',required=True)
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--port',type=int,required=True)
    a=p.parse_args(argv)
    # -B prevents cache writes, but does not prevent reads of old timestamp pyc.
    # Keep a fresh import prefix alive for the complete service lifetime.
    with tempfile.TemporaryDirectory(prefix='v5-module-import-') as cache:
        sys.pycache_prefix=cache
        sys.dont_write_bytecode=True
        from .module_api import create_module_server
        value=json.loads(Path(a.config).read_bytes())
        server=create_module_server(value,host=a.host,port=a.port)
        def terminate(signum,frame):
            raise SystemExit(0)
        signal.signal(signal.SIGTERM,terminate)
        try:
            print(json.dumps({'status':'READY','pid':__import__('os').getpid(),'port':server.server_address[1]},separators=(',',':')),flush=True)
            server.serve_forever()
        finally:
            server.server_close()

if __name__=='__main__':
    main()

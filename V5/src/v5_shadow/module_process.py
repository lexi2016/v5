"""Managed read-only module_api subprocess launcher for P0 runtime.

The child only hosts the existing module_api contract. It never invokes owners,
producers, daily jobs, or ledger code.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys

# The source bundle is relocatable; a managed child must not rely on the
# parent's in-memory sys.path or an inherited PYTHONPATH.
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = 'v5_shadow'
from .module_api import create_module_server


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--config',required=True)
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--port',type=int,required=True)
    a=p.parse_args(argv)
    value=json.loads(open(a.config,'rb').read())
    server=create_module_server(value,host=a.host,port=a.port)
    print(json.dumps({'status':'READY','pid':__import__('os').getpid(),'port':server.server_address[1]},separators=(',',':')),flush=True)
    server.serve_forever()

if __name__=='__main__':
    main()

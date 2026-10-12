"""V5 P0 runtime lifecycle and safe entrypoints.

Lifecycle owns process identity only. Status is read-only. Tick delegates to the
existing daily_tick contract and never runs from start/status.
"""
from __future__ import annotations
import argparse,json,os,signal,subprocess,sys,time
from pathlib import Path
from .digests import canonical_bytes,sha256_json
from .main_registry import registration_snapshot,validate_registry

MARKER='v5-main-runtime.v2'


def load_config(path):
    value=json.loads(Path(path).read_bytes())
    if not isinstance(value,dict): raise ValueError('CONFIG_INVALID')
    return value


def validate_config(config):
    validate_registry()
    for k in ('runtime_root','composition'):
        if k not in config: raise ValueError('RUNTIME_CONFIG_REQUIRED')
    if 'module_api' not in config: raise ValueError('MODULE_API_CONFIG_REQUIRED')
    return {'status':'CONFIGURATION_VALID','registry':registration_snapshot(),'config_sha256':sha256_json(config),'natural_verified':False}


def identity(config):
    return {'marker':MARKER,'pid':os.getpid(),'config_sha256':sha256_json(config),'code':'main_runtime.v2','started_at':time.time()}


def start(config):
    validate_config(config)
    root=Path(config['runtime_root']);root.mkdir(parents=True,exist_ok=True)
    path=root/'runtime.json'
    if path.exists(): raise ValueError('RUNTIME_ALREADY_EXISTS')
    value=identity(config);path.write_bytes(canonical_bytes(value))
    return {'status':'STARTED','identity':value,'natural_verified':False}


def status(config):
    path=Path(config['runtime_root'])/'runtime.json'
    if not path.is_file(): return {'status':'STOPPED','natural_verified':False}
    value=json.loads(path.read_bytes())
    alive=False
    try: os.kill(int(value['pid']),0); alive=True
    except OSError: pass
    if value.get('marker')!=MARKER: return {'status':'STALE_IDENTITY','identity':value,'natural_verified':False}
    return {'status':'RUNNING' if alive else 'STALE','identity':value,'config_match':value.get('config_sha256')==sha256_json(config),'natural_verified':False}


def stop(config):
    path=Path(config['runtime_root'])/'runtime.json'
    if not path.is_file(): return {'status':'ALREADY_STOPPED','natural_verified':False}
    value=json.loads(path.read_bytes())
    if value.get('marker')!=MARKER or value.get('config_sha256')!=sha256_json(config): raise ValueError('RUNTIME_IDENTITY_MISMATCH')
    try: os.kill(int(value['pid']),signal.SIGTERM)
    except ProcessLookupError: pass
    path.unlink()
    return {'status':'STOPPED','identity':value,'natural_verified':False}


def tick(config):
    validate_config(config)
    from .daily_tick import tick as daily_tick
    return daily_tick(config['daily'])


def api_status(config):
    # Read-only health probe. It does not import owners or invoke producers.
    return {'status':'API_CONFIGURED','module_api':config['module_api'],'natural_verified':False}


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('command',choices=('validate','start','status','stop','tick','api-status'));p.add_argument('--config',required=True)
    a=p.parse_args(argv);c=load_config(a.config)
    fn={'validate':validate_config,'start':start,'status':status,'stop':stop,'tick':tick,'api-status':api_status}[a.command]
    print(canonical_bytes(fn(c)).decode())

if __name__=='__main__': main()

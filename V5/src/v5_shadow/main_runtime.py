"""V5 P0 runtime lifecycle with managed read-only module_api process."""
from __future__ import annotations
import argparse,json,os,signal,subprocess,sys,time,socket
from pathlib import Path
from .digests import canonical_bytes,sha256_json
from .main_registry import registration_snapshot,validate_registry

MARKER='v5-main-runtime.v3'

def load_config(path):
    value=json.loads(Path(path).read_bytes())
    if not isinstance(value,dict): raise ValueError('CONFIG_INVALID')
    return value

def validate_config(config):
    validate_registry()
    if 'module_api' not in config: raise ValueError('MODULE_API_CONFIG_REQUIRED')
    for key in ('runtime_root','composition'):
        if key not in config: raise ValueError('RUNTIME_CONFIG_REQUIRED')
    return {'status':'CONFIGURATION_VALID','registry':registration_snapshot(),'config_sha256':sha256_json(config),'natural_verified':False}

def _runtime_path(c): return Path(c['runtime_root'])/'runtime.json'

def _child_config(c):
    root=Path(c['runtime_root']);p=root/'module_api_child.json'
    p.write_bytes(canonical_bytes(c['module_api']))
    return p

def start(config):
    validate_config(config)
    root=Path(config['runtime_root']);root.mkdir(parents=True,exist_ok=True)
    path=_runtime_path(config)
    if path.exists(): raise ValueError('RUNTIME_ALREADY_EXISTS')
    child_cfg=_child_config(config)
    proc=subprocess.Popen([sys.executable,'-m','v5_shadow.module_process','--config',str(child_cfg),'--port',str(int(config['module_api'].get('port',0)))],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    ready=None;deadline=time.time()+10
    while time.time()<deadline:
        line=proc.stdout.readline() if proc.stdout else ''
        if line: ready=json.loads(line);break
        if proc.poll() is not None: break
        time.sleep(.05)
    if not ready or ready.get('status')!='READY':
        proc.terminate();proc.wait(timeout=5);raise ValueError('MODULE_API_START_FAILED')
    identity={'marker':MARKER,'pid':os.getpid(),'module_pid':ready['pid'],'port':ready['port'],'config_sha256':sha256_json(config),'code':'main_runtime.v3','started_at':time.time()}
    path.write_bytes(canonical_bytes(identity))
    return {'status':'STARTED','identity':identity,'natural_verified':False}

def status(config):
    path=_runtime_path(config)
    if not path.is_file(): return {'status':'STOPPED','natural_verified':False}
    value=json.loads(path.read_bytes())
    if value.get('marker')!=MARKER or value.get('config_sha256')!=sha256_json(config): return {'status':'STALE_IDENTITY','identity':value,'natural_verified':False}
    try: os.kill(int(value['module_pid']),0);alive=True
    except OSError: alive=False
    socket_ok=False
    if alive:
        try:
            with socket.create_connection(('127.0.0.1',int(value['port'])),timeout=1): socket_ok=True
        except OSError: pass
    return {'status':'RUNNING' if alive and socket_ok else 'STALE','identity':value,'socket_ready':socket_ok,'natural_verified':False}

def stop(config):
    path=_runtime_path(config)
    if not path.is_file(): return {'status':'ALREADY_STOPPED','natural_verified':False}
    value=json.loads(path.read_bytes())
    if value.get('marker')!=MARKER or value.get('config_sha256')!=sha256_json(config): raise ValueError('RUNTIME_IDENTITY_MISMATCH')
    try: os.kill(int(value['module_pid']),signal.SIGTERM)
    except ProcessLookupError: pass
    path.unlink();return {'status':'STOPPED','identity':value,'natural_verified':False}

def tick(config):
    validate_config(config)
    from .daily_tick import tick as daily_tick
    return daily_tick(config['daily'])

def source_bundle(config):
    from .source_bundle import run_config
    return run_config(config.get('source_bundle', {'enabled': False}))

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('command',choices=('validate','start','status','stop','tick','source-bundle'));p.add_argument('--config',required=True)
    a=p.parse_args(argv);c=load_config(a.config)
    print(canonical_bytes({'validate':validate_config,'start':start,'status':status,'stop':stop,'tick':tick,'source-bundle':source_bundle}[a.command](c)).decode())

if __name__=='__main__': main()

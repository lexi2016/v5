"""V5 P0 runtime lifecycle with managed read-only module_api process."""
from __future__ import annotations
import argparse,json,os,signal,subprocess,sys,time,socket,selectors,fcntl,stat
from pathlib import Path
from .digests import canonical_bytes,sha256_json
from .main_registry import registration_snapshot,validate_registry
from .composition import no_symlinks

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

def _runtime_path(c): return no_symlinks(Path(c['runtime_root'])/'runtime.json')


_OWNED_CHILDREN={}


def _child_config(c):
    root=no_symlinks(c['runtime_root']);p=no_symlinks(root/'module_api_child.json')
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        metadata=os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink!=1:raise ValueError('RUNTIME_FILE_TYPE')
        os.ftruncate(fd,0)
        with os.fdopen(fd,'wb',closefd=False) as output:output.write(canonical_bytes(c['module_api']))
    finally:os.close(fd)
    return p


def _reap(proc):
    if proc.poll() is None:proc.terminate()
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill();proc.wait(timeout=5)
    for stream in (proc.stdout,proc.stderr):
        if stream:stream.close()


def start(config):
    validate_config(config)
    root=no_symlinks(config['runtime_root']);root.mkdir(parents=True,exist_ok=True)
    lock_path=no_symlinks(root/'.runtime-lock')
    lock=os.open(lock_path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    proc=None;created_identity=None;path=None
    try:
        if not stat.S_ISREG(os.fstat(lock).st_mode):raise ValueError('RUNTIME_FILE_TYPE')
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('RUNTIME_START_BUSY') from None
        path=_runtime_path(config)
        if path.exists():raise ValueError('RUNTIME_ALREADY_EXISTS')
        child_cfg=_child_config(config)
        source=Path(__file__).resolve().parents[1]
        bootstrap="import sys;sys.path.insert(0,sys.argv.pop(1));from v5_shadow.module_process import main;main()"
        proc=subprocess.Popen([sys.executable,'-I','-B','-c',bootstrap,str(source),'--config',str(child_cfg),
            '--port',str(int(config['module_api'].get('port',0)))],cwd=source,
            # The read-only child reports readiness on stdout only. Never leave
            # an undrained stderr pipe that can block all request workers.
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        deadline=time.monotonic()+10;raw=b''
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout,selectors.EVENT_READ)
            while b'\n' not in raw:
                remaining=deadline-time.monotonic()
                if remaining<=0 or not selector.select(remaining):break
                chunk=os.read(proc.stdout.fileno(),4096)
                if not chunk:break
                raw+=chunk
                if len(raw)>16384:raise ValueError('MODULE_API_READY_LIMIT')
        ready=json.loads(raw.split(b'\n',1)[0]) if b'\n' in raw else None
        if (not ready or ready.get('status')!='READY' or ready.get('pid')!=proc.pid
                or type(ready.get('port')) is not int or not 1<=ready['port']<=65535):
            raise ValueError('MODULE_API_START_FAILED')
        identity={'marker':MARKER,'pid':os.getpid(),'module_pid':proc.pid,'port':ready['port'],
            'config_sha256':sha256_json(config),'code':'main_runtime.v3','started_at':time.time()}
        raw=canonical_bytes(identity)
        with path.open('xb') as output:
            metadata=os.fstat(output.fileno());created_identity=(metadata.st_dev,metadata.st_ino)
            output.write(raw)
        _OWNED_CHILDREN[str(path)]=proc
        return {'status':'STARTED','identity':identity,'natural_verified':False}
    except BaseException:
        if proc is not None:_reap(proc)
        if proc is not None and path is not None and _OWNED_CHILDREN.get(str(path)) is proc:
            _OWNED_CHILDREN.pop(str(path),None)
        if created_identity is not None:
            try:
                current=path.lstat()
                if (current.st_dev,current.st_ino)==created_identity:path.unlink()
            except FileNotFoundError:pass
        raise
    finally:
        os.close(lock)


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
    if not path.is_file():return {'status':'ALREADY_STOPPED','natural_verified':False}
    root=no_symlinks(config['runtime_root'])
    lock=os.open(no_symlinks(root/'.runtime-lock'),os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        if not stat.S_ISREG(os.fstat(lock).st_mode):raise ValueError('RUNTIME_FILE_TYPE')
        # Serialize old stop with new start: it must never unlink a later identity.
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=_runtime_path(config)
        if not path.is_file():return {'status':'ALREADY_STOPPED','natural_verified':False}
        value=json.loads(path.read_bytes())
        if value.get('marker')!=MARKER or value.get('config_sha256')!=sha256_json(config):raise ValueError('RUNTIME_IDENTITY_MISMATCH')
        proc=_OWNED_CHILDREN.pop(str(path),None)
        if proc is not None and proc.pid==int(value['module_pid']):_reap(proc)
        else:
            try:os.kill(int(value['module_pid']),signal.SIGTERM)
            except ProcessLookupError:pass
        path.unlink();return {'status':'STOPPED','identity':value,'natural_verified':False}
    finally:os.close(lock)


def tick(config):
    validate_config(config)
    from .daily_tick import tick as daily_tick
    return daily_tick(config['daily'])

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('command',choices=('validate','start','status','stop','tick'));p.add_argument('--config',required=True)
    a=p.parse_args(argv);c=load_config(a.config)
    print(canonical_bytes({'validate':validate_config,'start':start,'status':status,'stop':stop,'tick':tick}[a.command](c)).decode())

if __name__=='__main__': main()

"""V5 P0 runtime lifecycle with managed read-only module_api process."""
from __future__ import annotations
import argparse,json,os,signal,subprocess,sys,time,select,tempfile,fcntl,stat
from contextlib import contextmanager
from http.client import HTTPConnection,HTTPException
from pathlib import Path
from .composition import no_symlinks
from .digests import canonical_bytes,sha256_json
from .main_registry import registration_snapshot,validate_registry

MARKER='v5-main-runtime.v3'
START_TIMEOUT=10
STOP_TIMEOUT=5

def load_config(path):
    value=json.loads(Path(path).read_bytes())
    if not isinstance(value,dict): raise ValueError('CONFIG_INVALID')
    return value

def validate_config(config):
    validate_registry()
    if 'module_api' not in config: raise ValueError('MODULE_API_CONFIG_REQUIRED')
    for key in ('runtime_root','composition'):
        if key not in config: raise ValueError('RUNTIME_CONFIG_REQUIRED')
    no_symlinks(Path(config['runtime_root']))
    from .module_api import _config
    _,root_fd=_config(config['module_api'])
    os.close(root_fd)
    from .p0_close_recapture import validate_registration
    close_recapture=validate_registration(config.get('daily',{}).get('close_recapture'))
    from .p0_hk_preselection import validate_registration as validate_m06
    hk_preselection=validate_m06(config.get('daily',{}).get('hk_preselection'))
    return {'hk_preselection':hk_preselection,'close_recapture':close_recapture,'status':'CONFIGURATION_VALID','registry':registration_snapshot(),'config_sha256':sha256_json(config),'natural_verified':False}

def _runtime_path(c): return no_symlinks(Path(c['runtime_root'])/'runtime.json')

@contextmanager
def _lifecycle_lock(root):
    # A second start/stop must not overwrite an in-flight child's identity.
    fd=os.open(root/'.runtime.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):raise ValueError('RUNTIME_FILE_TYPE')
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:raise ValueError('RUNTIME_BUSY') from exc
        yield
    finally:
        os.close(fd)

def _write_json(path,value):
    no_symlinks(path)
    fd,name=tempfile.mkstemp(prefix='.runtime-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(canonical_bytes(value));stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        Path(name).unlink(missing_ok=True)

def _child_config(c):
    root=Path(c['runtime_root']);p=root/'module_api_child.json'
    _write_json(p,c['module_api'])
    return p

def _ready(proc):
    deadline=time.monotonic()+START_TIMEOUT
    raw=b''
    while time.monotonic()<deadline:
        if not select.select([proc.stdout],[],[],max(0,deadline-time.monotonic()))[0]:break
        part=os.read(proc.stdout.fileno(),4096)
        if not part:break
        raw+=part
        if len(raw)>65536:break
        if b'\n' in raw:
            try:value=json.loads(raw.split(b'\n',1)[0])
            except (ValueError,UnicodeDecodeError):break
            if (isinstance(value,dict) and value.get('status')=='READY'
                    and value.get('pid')==proc.pid and type(value.get('port')) is int
                    and 1<=value['port']<=65535):return value
            break
    raise ValueError('MODULE_API_START_FAILED')

def _health_matches(config,value):
    pid=value.get('module_pid');port=value.get('port')
    if type(pid) is not int or pid<=0 or type(port) is not int or not 1<=port<=65535:return False
    connection=HTTPConnection('127.0.0.1',port,timeout=1)
    try:
        connection.request('GET','/__v5/module-health')
        response=connection.getresponse();raw=response.read(65537)
        if response.status!=200 or len(raw)>65536:return False
        body=json.loads(raw);module=config['module_api']
        if not isinstance(body,dict):return False
        return (body.get('status')=='READ_ONLY_RESPONSE_SERVICE' and body.get('pid')==pid
                and body.get('config_sha256')==sha256_json(module)
                and body.get('module_id')==module['module_id']
                and body.get('release_id')==module['release_id'])
    except (OSError,ValueError,KeyError,TypeError,HTTPException):return False
    finally:connection.close()

def start(config):
    validate_config(config)
    root=no_symlinks(Path(config['runtime_root']));root.mkdir(parents=True,exist_ok=True)
    with _lifecycle_lock(root):
        path=_runtime_path(config)
        if path.exists(): raise ValueError('RUNTIME_ALREADY_EXISTS')
        child_cfg=_child_config(config)
        child_entry=Path(__file__).resolve().with_name('module_process.py')
        # A log file cannot fill an unread stderr pipe during child startup.
        log=no_symlinks(root/'module_api.stderr.log')
        logfd=os.open(log,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
        with os.fdopen(logfd,'ab') as stderr:
            if not stat.S_ISREG(os.fstat(stderr.fileno()).st_mode):raise ValueError('RUNTIME_FILE_TYPE')
            proc=subprocess.Popen([sys.executable,'-I','-B',str(child_entry),'--config',str(child_cfg),'--port','0'],stdout=subprocess.PIPE,stderr=stderr)
        try:
            ready=_ready(proc)
            identity={'marker':MARKER,'pid':os.getpid(),'module_pid':ready['pid'],'port':ready['port'],'config_sha256':sha256_json(config),'code':'main_runtime.v3','started_at':time.time()}
            if not _health_matches(config,identity):raise ValueError('MODULE_API_START_FAILED')
            _write_json(path,identity)
            return {'status':'STARTED','identity':identity,'natural_verified':False}
        except BaseException:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=STOP_TIMEOUT)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=STOP_TIMEOUT)
            raise
        finally:
            proc.stdout.close()

def status(config):
    path=_runtime_path(config)
    if not path.is_file(): return {'status':'STOPPED','natural_verified':False}
    value=json.loads(path.read_bytes())
    if value.get('marker')!=MARKER or value.get('config_sha256')!=sha256_json(config): return {'status':'STALE_IDENTITY','identity':value,'natural_verified':False}
    verified=_health_matches(config,value)
    return {'status':'RUNNING' if verified else 'STALE','identity':value,'socket_ready':verified,'natural_verified':False}

def stop(config):
    path=_runtime_path(config)
    if not path.is_file(): return {'status':'ALREADY_STOPPED','natural_verified':False}
    with _lifecycle_lock(path.parent):
        if not path.is_file():return {'status':'ALREADY_STOPPED','natural_verified':False}
        value=json.loads(path.read_bytes())
        if value.get('marker')!=MARKER or value.get('config_sha256')!=sha256_json(config): raise ValueError('RUNTIME_IDENTITY_MISMATCH')
        pid=value.get('module_pid')
        if type(pid) is not int or pid<=0:raise ValueError('RUNTIME_PROCESS_IDENTITY_UNVERIFIED')
        fd=None
        try:
            try:
                if hasattr(os,'pidfd_open') and hasattr(signal,'pidfd_send_signal'):fd=os.pidfd_open(pid)
                else:os.kill(pid,0)
            except ProcessLookupError:
                path.unlink();return {'status':'STOPPED','identity':value,'natural_verified':False}
            if fd is not None and select.select([fd],[],[],0)[0]:
                try:os.waitpid(pid,os.WNOHANG)
                except ChildProcessError:pass
                path.unlink();return {'status':'STOPPED','identity':value,'natural_verified':False}
            if not _health_matches(config,value):raise ValueError('RUNTIME_PROCESS_IDENTITY_UNVERIFIED')
            if fd is not None:signal.pidfd_send_signal(fd,signal.SIGTERM)
            else:os.kill(pid,signal.SIGTERM)
            deadline=time.monotonic()+STOP_TIMEOUT
            stopped=False
            while time.monotonic()<deadline:
                if fd is not None:
                    stopped=bool(select.select([fd],[],[],max(0,deadline-time.monotonic()))[0])
                    break
                try:
                    waited,_=os.waitpid(pid,os.WNOHANG)
                    if waited==pid:stopped=True;break
                except ChildProcessError:pass
                try:os.kill(pid,0)
                except ProcessLookupError:stopped=True;break
                time.sleep(.05)
            if not stopped:raise ValueError('RUNTIME_STOP_UNCONFIRMED')
            try:os.waitpid(pid,os.WNOHANG)
            except ChildProcessError:pass
            path.unlink();return {'status':'STOPPED','identity':value,'natural_verified':False}
        finally:
            if fd is not None:os.close(fd)

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

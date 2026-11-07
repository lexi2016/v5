"""Real transport implementation; live registry intentionally EMPTY and fail-closed."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
from urllib.parse import urlencode,urlsplit
from adapter import adapt

# No runtime registration API or caller-supplied approval booleans.
# A reviewed code change must bind original owner/resource/lock/source identities.
TRUSTED_LIVE_REGISTRY = {}
# 5 x 128KiB raw bytes hex-encoded plus bounded metadata; same read/write cap.
CHECKPOINT_MAX_BYTES = 2 * 1024 * 1024

def run_live(registration_id, **kwargs):
    return {'status':'BLOCKED','reason':'TRUSTED_ORIGINAL_OWNER_RESOURCE_LOCK_SOURCE_REGISTRATION_MISSING','network_requests':0,'production_allowed':False}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('REDIRECT_REJECTED')

def https_get(url, timeout=15, max_bytes=131072):
    u=urlsplit(url)
    if u.scheme!='https' or u.hostname!='push2his.eastmoney.com' or u.port not in (None,443) or u.username or u.password or u.path!='/api/qt/stock/kline/get':raise ValueError('DESTINATION_REJECTED')
    if not 0<timeout<=30 or not 0<max_bytes<=131072:raise ValueError('TRANSPORT_LIMIT_INVALID')
    opener=urllib.request.build_opener(NoRedirect())
    with opener.open(urllib.request.Request(url,headers={'User-Agent':'HKResearchCandidate/2'}),timeout=timeout) as response:
        if response.status!=200:raise ValueError('HTTP_STATUS_NOT_200')
        raw=response.read(max_bytes+1)
        if len(raw)>max_bytes:raise ValueError('HTTP_RESPONSE_TOO_LARGE')
        return raw

def _url(code, day):
    d=dt.date.fromisoformat(day)
    return 'https://push2his.eastmoney.com/api/qt/stock/kline/get?'+urlencode(dict(secid='116.'+code,klt=101,fqt=0,beg=(d-dt.timedelta(days=10)).strftime('%Y%m%d'),end=d.strftime('%Y%m%d'),fields1='f1,f2,f3,f4,f5,f6',fields2='f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61'))

def _write(root,state):
    # Original durable writer remains unbound. This standalone writer only supports
    # a caller-owned isolated directory, opened without following final symlinks.
    encoded=json.dumps(state,sort_keys=True).encode()
    if len(encoded)>CHECKPOINT_MAX_BYTES:raise ValueError('CHECKPOINT_TOO_LARGE_BEFORE_WRITE')
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    name='checkpoint.tmp.'+os.urandom(8).hex()
    try:
        f=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
        try:
            with os.fdopen(f,'wb') as out:out.write(encoded);out.flush();os.fsync(out.fileno())
            os.replace(name,'checkpoint.json',src_dir_fd=fd,dst_dir_fd=fd);os.fsync(fd)
        finally:
            try:os.unlink(name,dir_fd=fd)
            except FileNotFoundError:pass
    finally:os.close(fd)

def _read(root):
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        try:f=os.open('checkpoint.json',os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
        except FileNotFoundError:return None
        with os.fdopen(f,'rb') as inp:
            raw=inp.read(CHECKPOINT_MAX_BYTES+1)
            if len(raw)>CHECKPOINT_MAX_BYTES:raise ValueError('CHECKPOINT_TOO_LARGE')
            return json.loads(raw)
    finally:os.close(fd)

def _isolated_engine(root,scope,day,codes,*,mock_transport,check_gates,clock=time.time,sleep=time.sleep):
    """Test-only orchestrator. Requires injected mock, never calls https_get.
    Does not establish original production owner/lock/resource registration.
    """
    root=Path(root)
    if not root.is_absolute() or any(p.is_symlink() for p in [root,*root.parents]):raise ValueError('UNSAFE_ROOT')
    if not root.is_dir():raise ValueError('ISOLATED_ROOT_MISSING')
    adapt({},scope,day,codes,{})
    if len(codes)>5:raise ValueError('ISOLATED_TEST_MAX_FIVE')
    check_gates()
    lock=root/'test.lock'
    lockfd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        identity=hashlib.sha256(json.dumps({'scope':scope,'day':day,'codes':codes,'version':2},sort_keys=True).encode()).hexdigest()
        state=_read(root) or {'identity':identity,'completed':{},'attempts':[],'not_before':0,'production_allowed':False,'natural_verified':False}
        if state.get('production_allowed',False) is not False or state.get('natural_verified',False) is not False:raise ValueError('CHECKPOINT_BOUNDARY_CORRUPT')
        state.update(production_allowed=False,natural_verified=False)
        if state['identity']!=identity:raise ValueError('INPUT_CHANGED')
        for c,r in state['completed'].items():
            if c not in codes:raise ValueError('SCOPE_EXPANSION')
            x=adapt({c:bytes.fromhex(r['raw_hex'])},scope,day,[c],{c:r['receipt']})
            if x['parsed_count']!=1:raise ValueError('CHECKPOINT_CORRUPT')
        for c in codes:
            if c in state['completed']:continue
            delay=max(0,state['not_before']-clock())
            if delay:sleep(delay)
            check_gates()
            state['not_before']=clock()+1.0
            attempt={'code':c,'started':clock(),'status':'INTENT_UNKNOWN'}
            state['attempts'].append(attempt);_write(root,state)
            try:
                raw=mock_transport(_url(c,day))
                if not isinstance(raw,bytes) or len(raw)>131072:raise ValueError('RESPONSE_LIMIT_OR_TYPE')
                receipt={'url':_url(c,day),'status':200,'sha256':hashlib.sha256(raw).hexdigest()}
                parsed=adapt({c:raw},scope,day,[c],{c:receipt})
                if parsed['parsed_count']!=1:raise ValueError('PARSER_REJECTED')
                check_gates()
                state['completed'][c]={'raw_hex':raw.hex(),'receipt':receipt}
                attempt['status']='PARSED_NOT_ADMITTED'
            except Exception as e:
                attempt.update(status='FAILED_UNKNOWN',error=type(e).__name__+': '+str(e));state['status']='STOPPED_UNKNOWN';_write(root,state);return state
            _write(root,state)
        state.update(status='ISOLATED_COMPLETE_NOT_ADMITTED',production_allowed=False,natural_verified=False);_write(root,state);return state
    finally:
        os.close(lockfd);lock.unlink()

"""Read-only view of same-day checker evidence; never a business receipt."""
import json
import os
import stat
from contextlib import ExitStack
from datetime import datetime, time
from hashlib import sha256
from zoneinfo import ZoneInfo

BJ=ZoneInfo('Asia/Shanghai')
NODES={'morning-delivery':time(8,10),'opening-prep':time(8,50)}
MISSING={'TODAY_READY_CARD':'当日就绪卡','OWNER_REGISTRATION':'原执行者绑定',
         'BOARD_READBACK':'原看板读回','TODAY_FROZEN_SCOPE':'当日冻结范围',
         'PRIOR_SESSION_BASELINE':'前一交易日同池基准','REVIEWED_QUOTE_SOURCE':'已审报价入口'}
LIMIT=8192

def _read(root,day,node):
    fd_flags=os.O_RDONLY|os.O_NOFOLLOW
    with ExitStack() as stack:
        fd=os.open(root,fd_flags|os.O_DIRECTORY)
        stack.callback(os.close,fd)
        for part in (day,node):
            fd=os.open(part,fd_flags|os.O_DIRECTORY,dir_fd=fd)
            stack.callback(os.close,fd)
        fd=os.open('check-only.json',fd_flags|os.O_NONBLOCK,dir_fd=fd)
        with os.fdopen(fd,'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('CHECK_ONLY_NOT_REGULAR')
            data=stream.read(LIMIT+1)
    if len(data)>LIMIT:
        raise ValueError('CHECK_ONLY_SIZE')
    return data

def project(state, day, item):
    node=item.get('node_id')
    if item.get('runtime_status')!='UNKNOWN' or node not in NODES:
        return
    try:
        if type(day) is not str or len(day)!=8 or not day.isascii() or not day.isdecimal():
            return
        raw=_read(state,day,node); a=json.loads(raw)
        if not isinstance(a,dict) or (a.get('schema'),a.get('node_id'),a.get('business_date'))!=('BOARD_MORNING_CHECK_ONLY_V1',node,day):
            return
        if any(a.get(k) is not False for k in ('business_started','formal_delivery','natural_verified')):
            return
        when=datetime.fromisoformat(a['observed_at'])
        if when.utcoffset() is None:
            return
        local=when.astimezone(BJ)
        if local.strftime('%Y%m%d')!=day or local.time()<NODES[node]:
            return
        missing=a['missing']
        if not isinstance(missing,list) or not missing or not all(type(k) is str and k in MISSING for k in missing) or len(missing)!=len(set(missing)):
            return
    except (OSError,ValueError,TypeError,KeyError):
        return
    item.update(runtime_status='CHECK_BLOCKED_NOT_EXECUTED',
                receipt_time=when.isoformat(),
                detail='仅准点查验，尚未核到业务执行。缺：'+'、'.join(MISSING[k] for k in missing)+'。',
                check_only={'sha256':sha256(raw).hexdigest(),'missing':missing,'natural_verified':False})

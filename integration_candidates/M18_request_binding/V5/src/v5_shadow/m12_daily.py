"""Callable M12 daily owner seam. Explicit invocation only; no automatic provider.

No global cwd changes. The original owner and its cold child run from the pinned
V5 repository root. Existing daily dispatcher registration is intentionally absent.
"""
import json
import os
from pathlib import Path
import subprocess
from .contracts import exact_keys,trade_date
from .digests import canonical_bytes
from .m12_readonly import BASE,verify_runtime
from .m12_readonly_worker import waiting,private_root

def run_daily(request):
    if request.get('execution_authorized') is not True:return waiting('M12_OWNER_EXECUTION_NOT_AUTHORIZED')
    exact_keys(request,('execution_authorized','private_root','trade_date','source_identity','tool_identity','config_identity','data_kind','python_executable'))
    trade_date(request['trade_date']);private_root(request['private_root']);verify_runtime()
    for key in ('source_identity','tool_identity','config_identity'):
        if not isinstance(request[key],str) or not 1<=len(request[key])<=1024:raise ValueError('M12_OWNER_IDENTITY')
    if request['data_kind'] not in {'SYNTHETIC','RECORDED_INPUT_REPLAY','OWNER_RESULT'}:raise ValueError('M12_DATA_KIND')
    python=request['python_executable']
    if not isinstance(python,str) or not Path(python).is_absolute() or '..' in Path(python).parts:raise ValueError('M12_PYTHON')
    try:
        process=subprocess.run([python,'-I','-B',str(BASE/'src/v5_shadow/m12_daily_worker.py')],input=canonical_bytes(request),
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=str(BASE.parent),timeout=1800,env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'})
    except subprocess.TimeoutExpired:return waiting('M12_OWNER_OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY')
    if process.returncode or len(process.stdout)>4*1024*1024:return waiting('M12_OWNER_OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY')
    result=json.loads(process.stdout);verify_runtime();return result

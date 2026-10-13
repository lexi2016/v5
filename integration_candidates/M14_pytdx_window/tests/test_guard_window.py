"""Real original guard in disposable subprocess; no owner run, no networking."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from test_rebound_pytdx_window import ROOT,BASE

class GuardWindowTests(unittest.TestCase):
    def test_guard_allows_only_existing_resource_directory_traversal(self):
        code=f'''
import sys,json,os
from pathlib import Path
sys.path.insert(0,{str(ROOT/'tests')!r})
from test_rebound_pytdx_window import fixture,ROOT,BASE
from v5_shadow import rebound_pytdx_window as w,rebound_owner as owner,rebound_raw_repair as raw
BASE=Path(raw.__file__).resolve().parents[2]
owner.BASE=BASE;owner.CAPSULE=BASE/'vendor/rebound_baseline'
signal,sessions,record=fixture()
private=ROOT/'guard-private';private.mkdir(exist_ok=True)
violations=owner._guard(private)
result=w.decode_window([record],members=['HK.00001'],signal_date=signal,sessions=sessions,research_cutoff='2026-10-13T10:00:00+00:00')
assert len(result['rows'])==61
assert not violations,violations
blocked=[]
for path in [BASE/'vendor/rebound_repair_baseline/not-allowed.json',BASE/'vendor/rebound_supplement/not-allowed.json']:
    try:path.read_bytes()
    except PermissionError as error:blocked.append(str(error))
assert blocked==['REBOUND_READ_OUTSIDE_PRIVATE_INPUT']*2,blocked
try:(private/'write-denied').write_text('never')
except PermissionError as error:assert str(error)=='REBOUND_WRITE_DENIED'
else:raise AssertionError('guard admitted write')
print(json.dumps(dict(status='GUARD_DECODE_OK',blocked=blocked)))
'''
        result=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'GUARD_DECODE_OK')

if __name__=='__main__':unittest.main()

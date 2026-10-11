"""IR-03 reverse-cache check: disk restored before daily imports its helpers."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).parent))
from test_review_findings import SNAPSHOT, canonical_bytes, daily, make_input, make_request


class RestoredHelperIdentityReview(unittest.TestCase):
    def test_restored_disk_does_not_hide_cached_nonbaseline_helper_code(self):
        with tempfile.TemporaryDirectory(prefix="m09-restored-helper-review-") as temp:
            base=Path(temp)
            copied,source,root=base/"candidate",base/"source",base/"m09"
            shutil.copytree(SNAPSHOT/"V5",copied/"V5")
            make_input(source)
            daily.initialize_a_close_root(root)
            request_path=base/"request.json"
            request_path.write_bytes(canonical_bytes(make_request(source,"restored-contracts")))
            script='''from pathlib import Path
import hashlib,json,sys
directory=Path(sys.argv[1])/"V5/src"
sys.path.insert(0,str(directory))
path=directory/"v5_shadow/contracts.py"
original=path.read_bytes()
needle=b'def trade_date(value):\\n'
assert original.count(needle)==1
changed=original.replace(needle,needle+b'    _m09_review_cached_marker = "CACHED_NONBASELINE_FUNCTION"\\n')
path.write_bytes(changed)
from v5_shadow import contracts
path.write_bytes(original)
from v5_shadow import a_close_daily as d
answer={"original_disk_sha":hashlib.sha256(original).hexdigest(),"cached_source_sha":hashlib.sha256(changed).hexdigest(),"restored_disk_sha":hashlib.sha256(path.read_bytes()).hexdigest()}
try:
    result=d.run_a_close_daily(Path(sys.argv[2]),json.loads(Path(sys.argv[3]).read_bytes()))
    answer.update(status=result["status"],reason=result.get("reason"))
except Exception as exc:
    answer.update(status="REJECTED",reason=type(exc).__name__+":"+str(exc))
print(json.dumps(answer))
'''
            result=subprocess.run([sys.executable,"-B","-c",script,str(copied),str(root),str(request_path)],capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            answer=json.loads(result.stdout)
            print(json.dumps(answer),flush=True)
            self.assertNotEqual(answer["status"],"SUCCEEDED","Restoring source bytes concealed stale cached helper code")
            self.assertIn("CACHED_SHARED_HELPER_MISMATCH",answer.get("reason", ""),"The code-object comparison branch was not exercised")


if __name__=="__main__":
    unittest.main(verbosity=2)

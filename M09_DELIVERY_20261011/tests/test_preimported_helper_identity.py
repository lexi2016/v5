"""IR-03 targeted check: shared helper imported before daily's identity pin."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).parent))
from test_review_findings import SNAPSHOT, canonical_bytes, daily, make_input, make_request


class PreimportedHelperIdentityReview(unittest.TestCase):
    def test_preimported_contracts_cannot_be_relabelled_with_new_disk_sha(self):
        with tempfile.TemporaryDirectory(prefix="m09-preimported-helper-review-") as temp:
            base = Path(temp)
            copied, source, root = base/"candidate", base/"source", base/"m09"
            shutil.copytree(SNAPSHOT/"V5",copied/"V5")
            make_input(source)
            daily.initialize_a_close_root(root)
            request_path = base/"request.json"
            request_path.write_bytes(canonical_bytes(make_request(source,"preimported-contracts")))
            script = '''from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,str(Path(sys.argv[1])/"V5/src"))
from v5_shadow import contracts
path=Path(contracts.__file__)
old=path.read_bytes()
needle=b'def trade_date(value):\\n'
assert old.count(needle)==1
new=old.replace(needle,needle+b'    raise ValueError("NEW_CONTRACT_MUST_EXECUTE")\\n')
path.write_bytes(new)
from v5_shadow import a_close_daily as d
answer={"old_helper_sha":hashlib.sha256(old).hexdigest(),"new_helper_sha":hashlib.sha256(new).hexdigest()}
try:
    out=d.run_a_close_daily(Path(sys.argv[2]),json.loads(Path(sys.argv[3]).read_bytes()))
    answer.update(status=out["status"],reason=out.get("reason"))
    if out["status"]=="SUCCEEDED":
        committed=d.read_a_close_daily(Path(sys.argv[2]),"20261009")
        answer["claimed_helper_sha"]=committed["record"]["implementation_identity"]["modules"]["contracts.py"]
except Exception as exc:
    answer.update(status="REJECTED",reason=type(exc).__name__+":"+str(exc))
print(json.dumps(answer))
'''
            result=subprocess.run([sys.executable,"-B","-c",script,str(copied),str(root),str(request_path)],capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            answer=json.loads(result.stdout)
            print(json.dumps(answer),flush=True)
            self.assertNotEqual(answer["status"],"SUCCEEDED","Cached old helper code is recorded under the changed source SHA")


if __name__=="__main__":
    unittest.main(verbosity=2)

"""Independent frozen-candidate negative cases; constructed data is SYNTHETIC.

These tests assert the required fail-closed behavior and are intentionally RED
on the reviewed candidate when the corresponding finding is present.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SNAPSHOT = Path(os.environ.get("M09_REVIEW_SNAPSHOT", "/workspace/scratch/a5458cb06b78/m09_work/review_snapshot"))
sys.path[:0] = [str(SNAPSHOT / "V5/src"), str(SNAPSHOT / "V5/tests")]

from test_a_close_daily import make_input, file_sha
from v5_shadow import a_close_daily as daily
from v5_shadow.a_close_daily_api import read_a_close_preview
from v5_shadow.digests import canonical_bytes, sha256_json


def make_request(source, attempt="first", configuration="review-v1"):
    return dict(schema_version="v5.m09.daily_request.v1", trade_date="20261009", slot="16:05",
                job_id="a_share_close_review_1605", attempt_id=attempt, execution_kind="ENGINEERING",
                triggered_at=datetime.now(timezone.utc).isoformat(), source_root=str(source),
                input_manifest="input.json", input_manifest_sha256=file_sha(source / "input.json"),
                configuration_revision=configuration)


def child_crash(root, request_path):
    original = daily._activate
    def stop_after_activate(*args, **kwargs):
        original(*args, **kwargs)
        os._exit(73)
    daily._activate = stop_after_activate
    daily.run_a_close_daily(Path(root), json.loads(Path(request_path).read_bytes()))
    raise AssertionError("crash injection was not reached")


class IndependentM09Review(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m09-independent-review-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source, self.root = self.base / "source", self.base / "m09"
        make_input(self.source)
        daily.initialize_a_close_root(self.root)

    def successful_run(self):
        result = daily.run_a_close_daily(self.root, make_request(self.source))
        self.assertEqual(result["status"], "SUCCEEDED", result)
        return result

    def test_crash_after_head_switch_preserves_previous_success(self):
        first = self.successful_run()
        request = make_request(self.source, "crash", "review-v2")
        request_path = self.base / "crash_request.json"
        request_path.write_bytes(canonical_bytes(request))
        result = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "child-crash", str(self.root), str(request_path)], capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 73, (result.returncode, result.stdout, result.stderr))
        after_crash = daily.read_a_close_daily(self.root, "20261009")
        resumed = daily.run_a_close_daily(self.root, request)
        after_resume = daily.read_a_close_daily(self.root, "20261009")
        print(json.dumps({"finding":"hard_crash_commit_window", "child_exit":result.returncode,
                          "old_generation":first["generation_sha256"], "after_crash":after_crash["identity"]["generation_sha256"],
                          "retry_status":resumed["status"], "retry_reason":resumed.get("reason"),
                          "after_resume":after_resume["identity"]["generation_sha256"]}), flush=True)
        self.assertEqual(after_resume["identity"]["generation_sha256"], first["generation_sha256"],
                         "A hard-interrupted attempt remains the visible success even after retry returns UNKNOWN")

    def test_reader_rejects_mutated_calculation_or_input_snapshot(self):
        result = self.successful_run()
        run = self.root / "runs" / result["run_id"]
        for relative in ("calculation.json", "inputs/source/panel.json", "inputs/admitted_panel.json", "inputs/source/members.txt"):
            with self.subTest(relative=relative):
                path = run / relative
                original = path.read_bytes()
                try:
                    path.write_bytes(b"independent review corruption\n")
                    preview = read_a_close_preview(self.root, "20261009")
                    status = preview["m09_publication"]["read_status"]
                    print(json.dumps({"finding":"unverified_saved_calculation_and_inputs", "corrupted":relative, "read_status":status}), flush=True)
                    self.assertNotEqual(status, "VERIFIED", "Saved immutable calculation/input corruption is served as VERIFIED")
                finally:
                    path.write_bytes(original)

    def test_loaded_daily_code_does_not_claim_changed_on_disk_implementation(self):
        copied = self.base / "copied_candidate"
        shutil.copytree(SNAPSHOT / "V5", copied / "V5")
        request = make_request(self.source, "changed-code")
        request_path = self.base / "code_request.json"
        request_path.write_bytes(canonical_bytes(request))
        script = '''from pathlib import Path
import hashlib, json, sys
sys.path.insert(0, str(Path(sys.argv[1]) / "V5/src"))
from v5_shadow import a_close_daily as d
path=Path(d.__file__)
old=path.read_bytes()
needle=b'    request, cutoff = _request(request)'
assert old.count(needle) == 1
new=old.replace(needle,b'    raise ValueError("INDEPENDENT_NEW_CODE_MUST_EXECUTE")\\n'+needle)
path.write_bytes(new)
out=d.run_a_close_daily(Path(sys.argv[2]),json.loads(Path(sys.argv[3]).read_bytes()))
answer={"status":out["status"],"reason":out.get("reason"),"old_source_sha":hashlib.sha256(old).hexdigest(),"new_source_sha":hashlib.sha256(new).hexdigest()}
if out["status"]=="SUCCEEDED":
    committed=d.read_a_close_daily(Path(sys.argv[2]),"20261009")
    answer["claimed_daily_sha"]=committed["record"]["implementation_identity"]["modules"]["a_close_daily.py"]
print(json.dumps(answer))
'''
        result = subprocess.run([sys.executable, "-B", "-c", script, str(copied), str(self.root), str(request_path)], capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        answer = json.loads(result.stdout)
        print(json.dumps({"finding":"stale_loaded_daily_implementation", **answer}), flush=True)
        self.assertNotEqual(answer["status"], "SUCCEEDED", "Old loaded code runs and records the hash of different new on-disk code")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "child-crash":
        child_crash(sys.argv[2], sys.argv[3])
    else:
        unittest.main(verbosity=2)

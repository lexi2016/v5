"""Cloud-only synthetic multi-root HTTP integration; never uses real archives."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "V5/src"))
from v5_shadow.module_api import create_module_server


class MultiRootHttpTests(unittest.TestCase):
    def test_exact_latest_reversed_roots_missing_tamper_and_no_writes(self):
        package = Path(os.environ["M04_CAPTURE_PACKAGE"])
        m04_python = os.environ.get("M04_PYTHON", sys.executable)
        self.assertEqual(hashlib.sha256((package / "RELEASE.json").read_bytes()).hexdigest(),
                         "2bafef714a5d35352d54ff8a4d2dde0898fb1fb2ce48e71b3a0eafc4108828de")
        code = """import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'tests'))
from test_multi_binding import MultiBindingTests
fixture=MultiBindingTests();fixture.setUp()
try:
 print(json.dumps({'binding':fixture.bundle,'day':fixture.c.day,'body':fixture.c.body}),flush=True)
 sys.stdin.read()
finally:fixture.doCleanups()
"""
        fixture = subprocess.Popen([m04_python, "-I", "-B", "-c", code, str(package)],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: fixture.communicate("", timeout=20))
        data = json.loads(fixture.stdout.readline())
        descriptor = data["binding"]

        def snapshot():
            return {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                    for binding in descriptor["bindings"]
                    for p in Path(binding["root"]).rglob("*") if p.is_file()}

        before = snapshot()
        with tempfile.TemporaryDirectory(prefix="v5-synthetic-http-") as temp:
            root = Path(temp)
            (root / ".v5-module-root").write_text("v5.module-root.v1:source_bundle\n")
            config = dict(schema_version="v5.module_api.v1", module_id="source_bundle",
                          release_id="SYNTHETIC_CLOUD_MULTI_ROOT", data_root=temp,
                          routes=["/api/v5/research/lane"])
            config["m04_research_lane_binding"] = dict(
                package_root=str(package), archive_binding=descriptor,
                package_manifest_sha256=hashlib.sha256((package / "RELEASE.json").read_bytes()).hexdigest(),
                python_executable=str(Path(m04_python).resolve()))
            for bindings in (descriptor["bindings"], list(reversed(descriptor["bindings"]))):
                config["m04_research_lane_binding"]["archive_binding"] = dict(descriptor, bindings=bindings)
                server = create_module_server(config)
                thread = threading.Thread(target=server.serve_forever)
                thread.start()

                def get(query="", method="GET"):
                    connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=40)
                    try:
                        connection.request(method, "/api/v5/research/lane" + query)
                        response = connection.getresponse()
                        return response.status, json.loads(response.read())
                    finally:
                        connection.close()

                try:
                    for day in ("20200102", data["day"]):
                        status, payload = get("?research_date=" + day)
                        self.assertEqual(status, 200, payload)
                        self.assertEqual(payload["research_date"], day)
                        self.assertEqual(payload["archive_materials"]["article_count"], 1)
                        self.assertFalse(payload["production_allowed"])
                        expected = descriptor["bindings"][0 if day == data["day"] else 1]
                        self.assertEqual(payload["archive_materials"]["source_reference"]["archive_binding"], expected)
                        if day == data["day"]:
                            self.assertEqual(payload["archive_materials"]["articles"][0]["body_text"], data["body"])
                        else:
                            self.assertEqual(payload["archive_materials"]["acquisition_status"], "UNKNOWN")
                            self.assertIsNone(payload["source_run_id"])
                    self.assertEqual(get()[1]["research_date"], data["day"])
                    self.assertEqual(get("?research_date=19990101")[1]["status"], "NOT_MATERIALIZED")
                    self.assertEqual(get(method="POST")[0], 405)
                    self.assertEqual(before, snapshot())
                    old_manifest = Path(descriptor["bindings"][1]["root"]) / "manifest.json"
                    raw = old_manifest.read_bytes()
                    try:
                        old_manifest.write_bytes(raw + b" ")
                        self.assertEqual(get("?research_date=" + data["day"])[0], 409)
                    finally:
                        old_manifest.write_bytes(raw)
                        stamp = before[str(old_manifest)][1]
                        os.utime(old_manifest, ns=(stamp, stamp))
                finally:
                    server.shutdown()
                    thread.join()
                    server.server_close()
            self.assertEqual(before, snapshot())


if __name__ == "__main__":
    unittest.main()

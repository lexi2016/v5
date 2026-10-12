# Mac managed-process retest — 9d73d

Fixed candidate: `9d73d866d06b84b4804e22d9f9c61ee3ae0ac694`.
Parent: `739d7180177e51830731851f6e61c97cd5e2f965`.
Branch: `dev/v5-main-integration-20261012`.
Remote compare: ahead 1, exactly one changed file:
`V5/tests/test_p0_managed_module_process.py`, blob `ed11d3e35fc8e8c2d546946544405ece1c4f187a`.
Product code unchanged. No local product/test edits or source re-review; main and its unrelated misdelivery were not touched.

## Actual command / result

CWD=separate task-owned fixed candidate subset. All 75 materialized files verified against the remote candidate tree before and after execution. Existing Python 3.14.6 and pytest 9.0.2, same existing dependency setup as prior feedback; no install. Plugin autoload, bytecode and pytest cache disabled; isolated TMPDIR.

Private absolute interpreter/source/tmp paths are redacted.
```sh
$PY -m pytest -vv -p no:cacheprovider V5/tests/test_p0_managed_module_process.py
```
- Start UTC: **2026-10-12T04:42:32.373267+00:00**
- End UTC: **2026-10-12T04:42:32.770870+00:00**
- **pytest exit 1; 2 PASS / 2 FAIL**, 4 collected (pytest 0.19s).
- The outer evidence harness exited 0, not a successful test verdict.

## Real coverage and failures

1. **PASS** test_real_start_ready_health_identity_stop: real child READY, health HTTP 200, module_id p0_test and Popen/READY PID equality; terminate/wait and listener closure assertions reached. Child used --port 0 on loopback.

2. **FAIL** test_duplicate_port_is_rejected_by_real_server:
```text
test_p0_managed_module_process.py:64
  str(_module_fixture(tmp_path))  # while building second Popen arguments
test_p0_managed_module_process.py:18
  data_root.mkdir()
FileExistsError: [Errno 17] File exists: '<TEST_TMP>/p0_test-data'
```
First child had reached READY. The second call to the same fixture fails before second Popen executes. **Second process / actual port conflict / nonzero-exit assertion NOT_REACHED**. First child was terminated/waited in finally.

3. **FAIL** test_wrong_identity_runtime_stop_is_rejected:
```text
test_p0_managed_module_process.py:74
  main_runtime.start(cfg)
main_runtime.py:43
  proc.terminate(); proc.wait(timeout=5)
  raise ValueError('MODULE_API_START_FAILED')
ValueError: MODULE_API_START_FAILED
```
The runtime attempted a real child start, but no READY was returned. Post-test read-only fixture check: configured data root exists; its .v5-module-root marker does NOT exist; runtime.json does NOT exist. Child stderr is swallowed by this runtime and is not present in pytest output, so no invented child traceback is reported.
**wrong-config stop call, RUNTIME_IDENTITY_MISMATCH assertion, RUNNING-after-refusal assertion, and final valid stop block are NOT_REACHED**. This run does not prove wrong-identity rejection. Configuration creation or child launch attempt is not counted as a ready/running service.

4. **PASS** test_no_owner_or_producer_import_contract: AST ImportFrom module-name check reached and passed. This is a static direct-import check, not dynamic proof of all transitive imports, plain import calls, or absence of producer side effects. It is not substituted for lifecycle behavior.

Return the two fixture failures to the original author; no local test repairs or retries were performed.

## Cleanup / scope

At 04:42:32.771412–04:42:32.808030 UTC, ps exit 0 filtered to this task's module_process config roots found zero remaining task children.
At 04:42:32.808373–04:42:32.872358 UTC, lsof exit 0 confirmed protected 8873/8910/54777/54778/54779 listeners retained the prior PIDs. Only task-created process handles were terminated by these tests.

Ledger/config tests and manual smoke were NOT_RUN in this batch. Prior ledger PASS remains fixed to 88b5e96; prior smoke evidence remains bound to its original candidate. No frontend, business owner, natural-window, full suite, 18-module or P0–P5 acceptance claim. No real collection/trading, credentials, private excluded-source recovery, system changes or other task directories.

Only this minimal sanitized report is appended under the requested feedback path using fresh integration HEAD/base and expected-SHA CAS. Raw local logs remain private.

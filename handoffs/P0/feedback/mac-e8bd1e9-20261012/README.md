# Mac managed-process test increment — e8bd1e9

Fixed candidate: `e8bd1e9601240d4c5212aa917e3b799590d0b0db`.
Parent: `60e2659a88b53f5a0af35a104017fea389dc83a1`.
Remote compare: ahead 1, only `V5/tests/test_p0_managed_module_process.py` changed; blob `11da1a610f0afc6edb7123afd3fe0b0888be9f31`. Product code unchanged from 60e265. Separate isolated source directory; 75 file identities verified by prior candidate tree plus exact one-file diff. No local product/test edits.

## Actual execution

Existing Python 3.14.6 / pytest 9.0.2, same existing dependency setup as prior feedback; no installation. Task-owned TMPDIR, bytecode/cache disabled, plugin autoload disabled.
Private absolute paths replaced with logical variables; CWD is the e8bd candidate root.
```sh
$PY -m pytest -vv -p no:cacheprovider V5/tests/test_p0_managed_module_process.py
```
- Start UTC: 2026-10-12T04:29:57.528322+00:00
- End UTC: 2026-10-12T04:29:58.046080+00:00
- **pytest exit 1; 3 PASS / 1 FAIL**. Outer recording harness exit 0 is not test success.
- No unrelated tests or manual lifecycle smoke repeated.

| Test | Actual result and limit |
|---|---|
| test_real_start_ready_health_identity_stop | PASS: real module_process child, READY PID matched Popen PID, health HTTP 200 and module/release identity, terminate/wait and port closure |
| test_duplicate_port_is_rejected_by_real_server | PASS: second real process on first task child's port exited nonzero; task children terminated/waited |
| test_wrong_identity_fixture_does_not_stop_existing_process | PASS as written: creates wrong config file and checks original child still alive; DOES NOT invoke wrong-config start or main_runtime.stop, so wrong-identity refusal is NOT_TESTED |
| test_no_owner_or_producer_import_contract | FAIL at line 110: text assertion matches docstring word owners |

Minimal failure:
```text
assert "owner" not in source.lower()
AssertionError
```
The executed test reads module_process.py as text. Its existing docstring says the child never invokes owners/producers, so the assertion fails on documentation text. This failure is not evidence that an owner or producer executed. The subsequent producer assertion is **NOT_REACHED**. No local repair applied; return to original author for a precise executable contract test.

## Cleanup / evidence boundary

The test uses direct Popen handles for task-created children and terminates only those children. A post-test process snapshot at 04:29:58.046452–04:29:58.083142 UTC (ps exit 0), filtered to this task's module_process command/config roots, found zero remaining children. Protected listeners 8873/8910/54777/54778/54779 retained their prior PIDs.

These new tests directly run v5_shadow.module_process and terminate its process handle. They do not exercise main_runtime CLI status/stop identity refusal or duplicate runtime start. Do not infer those contracts from their test names.

The separate 60e265 targeted regression result remains **6 PASS / 1 FAIL** (missing .v5-daily-run-ledger marker), recorded in [its feedback](../mac-60e265-20261012/README.md). This file neither reruns nor resolves that failure. Prior c2644 manual start/health/status/stop evidence remains bound to that candidate in [prior feedback](../mac-c2644-20261012/README.md).

Full-suite/frontend/business publication/CAS/natural-input/scheduling tests were NOT_RUN. Overall 18-module/P0–P5 acceptance remains incomplete. No credentials, real collection/trading, excluded private material, frontend directories, or system settings were touched. Only this minimal sanitized feedback is published.

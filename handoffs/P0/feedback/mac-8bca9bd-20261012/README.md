# Mac managed-process retest — 8bca9bd

Fixed candidate: `8bca9bd6d84d2864c04e96ef8a4f46701a9c1d33`.
Parent: `39aec051948ca10d3da5eba037bf0913c7d1a834`.
Branch: `dev/v5-main-integration-20261012`.
Remote compare confirmed ahead 1 and only `V5/tests/test_p0_managed_module_process.py` changed, blob `4031834c19eb4cc49fe2608dfde03adfe47a6046`. Product code unchanged.

## Actual execution: 4 PASS, exit 0

CWD=separate task-owned fixed source subset. All 75 files verified against candidate tree before and after execution. Existing Python 3.14.6 / pytest 9.0.2, same dependency setup as prior feedback (existing pure-Python pytest site-packages, no new locked environment or installation). Plugin autoload/bytecode/cache disabled, task-only TMPDIR. Private paths redacted.

```sh
$PY -m pytest -vv -p no:cacheprovider V5/tests/test_p0_managed_module_process.py
```
- Start UTC: **2026-10-12T04:48:07.475811+00:00**
- End UTC: **2026-10-12T04:48:07.965781+00:00**
- Actual pytest **exit 0**, **4 collected / 4 PASS**, reported 0.25s; stderr empty.

Actual reached assertions:
1. test_real_start_ready_health_identity_stop: real child READY, HTTP 200, module/release identity, Popen PID matches READY PID; terminate/wait and loopback port closure.
2. test_duplicate_port_is_rejected_by_real_server: first child READY, second real server process attempted the occupied task-child port and exited nonzero; cleanup executed. Unlike the prior failed fixture, the second Popen and exit assertion were reached.
3. test_wrong_identity_runtime_stop_is_rejected: main_runtime.start(cfg) returned; actual main_runtime.stop(wrong) was invoked and raised **RUNTIME_IDENTITY_MISMATCH**; subsequent main_runtime.status(cfg) returned **RUNNING**; finally main_runtime.stop(cfg) executed. This is actual API refusal evidence for changed release/config identity, not a text or configuration-only assertion.
4. test_no_owner_or_producer_import_contract: AST ImportFrom name check passed. Limited to direct ImportFrom statements; it does not dynamically verify transitive imports or all possible side effects.

## Cleanup and limits

Post-test task-filtered ps: 04:48:07.966148–04:48:08.004315 UTC, exit 0, zero remaining task module_process children.
Protected-listener check: 04:48:08.004645–04:48:08.077639 UTC, lsof exit 0; 8873/8910/54777/54778/54779 retained original PIDs.

Only this new test file ran. Ledger/config test files and manual smoke were not repeated. No local product/test edits, second source review, main changes, real collection/trading, credential access, or other task modifications.
This proves the listed isolated synthetic process/refusal cases only: not arbitrary PID-reuse/tampered-identity safety, a full CLI deployment, full producer-effect tracing, business publication/frontend/natural windows, or 18-module/P0–P5 acceptance.
Prior evidence remains tied to its own fixed candidate. Raw command/output paths stay local; only this minimal sanitized result is published via current integration HEAD/base and expected-SHA CAS.

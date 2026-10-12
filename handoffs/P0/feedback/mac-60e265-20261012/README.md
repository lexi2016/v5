# Mac targeted retest — 60e265

Candidate: `lexi2016/v5@60e2659a88b53f5a0af35a104017fea389dc83a1`
Branch: `dev/v5-main-integration-20261012`
Overall result: **FAIL — 6 passed, 1 failed; pytest exit 1.**

Remote compare confirmed candidate descends from prior feedback `f2975aabab9313f69c824ef61499d6f38a969993`, ahead by 3 commits. Exactly three changed files:
- V5/src/v5_shadow/main_runtime.py — blob 3aa7b5fd41cd87a4a1f62d53a503b1166ca10cf6
- V5/tests/test_p0_runtime_lifecycle.py — blob 890b153f3fd93297b57c3ac725b35e7ceb6f79a7
- integration_tests/test_p0_ledger.py — blob 0e0018711fa983a2ed5eae1b9fecdbfad87b2f60

Reused the prior verified dependency subset in a separate task-only directory and replaced only these three files with exact remote bytes. All 75 local candidate files verified against the 60e265 tree. No product/test edits, second source review, package installation, private fixture recovery, frontend work, or service startup.

## Actual execution

Existing Python 3.14.6; existing pytest 9.0.2 pure-Python package from the same pre-existing site-packages used previously. Plugin autoload disabled; bytecode disabled; pytest cache disabled; task-only TMPDIR. The prior environment caveat remains: not a new fully locked pytest environment.

CWD = isolated candidate root. Private absolute paths are replaced with logical names.
```sh
$PY -m pytest -vv -p no:cacheprovider \
  V5/tests/test_p0_runtime_entrypoints.py::test_validate_requires_module_api \
  V5/tests/test_p0_runtime_lifecycle.py \
  integration_tests/test_p0_ledger.py
```

- Started UTC: 2026-10-12T04:27:08.256587+00:00
- Ended UTC: 2026-10-12T04:27:08.540294+00:00
- Actual pytest exit: **1**. The outer evidence-recording harness exited 0; that is not the test result.
- Collected 7 tests; **6 PASS / 1 FAIL**.
- The four previously failing test nodes were selected. Three additional ledger cases were run because the ledger test file and fixtures changed; no unrelated full-suite repetition.

| Test | Actual result / coverage |
|---|---|
| test_validate_requires_module_api | PASS; expected MODULE_API_CONFIG_REQUIRED now observed |
| test_validate_registry_contract | PASS; updated config passes validation |
| test_lifecycle_identity | PASS; now only asserts module_id in generated config; no start/status/stop or runtime identity verification |
| test_six_lanes_real_persistence_no_overwrite[order0] | PASS; changed ledger fixture regression |
| test_six_lanes_real_persistence_no_overwrite[order1] | PASS; changed ledger fixture regression |
| test_actual_saved_m07_product_preserves_same_run | FAIL; missing isolated ledger marker |
| test_new_lane_not_implicitly_registered_for_dispatch | PASS |

## Minimal failure / return to original author

At `integration_tests/test_p0_ledger.py:30`, the new portable fixture reaches:
```python
claim = claim_run(tmp_path, identity)
```
Actual exception:
```text
FileNotFoundError: [Errno 2] No such file or directory: '.v5-daily-run-ledger'
```
Stack: run_ledger.py:84 claim_run → run_ledger.py:31 locked → module_api.py:71 _read_at.
The isolated directory lacks the ledger identity marker when claim_run is invoked. No local marker/test/product repair was applied. finish_run, REUSED_SUCCESS assertion, and product_reference readback in this test are **NOT_REACHED**. Original author should correct the fixture under the existing ledger identity contract and submit a new fixed candidate.

The old external/private fixture dependency is no longer the observed failure; this run uses a synthetic M07-shape fixture. Its name must not imply real saved M07 business evidence.

## Coverage retained and NOT_RUN

- Prior actual managed-process smoke remains evidence only for fixed `c2644b854bf669417617f499571771692d9c41b3`: see [prior feedback](../mac-c2644-20261012/README.md). It is not reclassified as a new-candidate execution result.
- Actual start/READY/health/status/stop on 60e265: **NOT_RUN**, intentionally not repeated per requested narrow scope.
- test_p0_managed_module_process.py was unchanged and **NOT_RUN**; its constant-True assertions do not prove managed behavior. The lifecycle test comment claiming coverage there is not accepted as execution evidence.
- Full suite, publication/CAS, browser/frontend, business owner inputs, daily tick, natural windows, all 18 modules and P0–P5 acceptance remain **NOT_RUN / NOT_ACCEPTED** as applicable.
- This retest started/stopped no services and did not operate on V4, protected ports, credentials, system settings, or other tasks' frontend directories.
- Feedback is a new path only, appended using current remote HEAD as parent/base and expected-SHA CAS. Raw local evidence remains private; only this minimal sanitized report is uploaded.

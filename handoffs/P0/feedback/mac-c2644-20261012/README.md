# Mac fixed-candidate P0 execution feedback

- Candidate: `lexi2016/v5@c2644b854bf669417617f499571771692d9c41b3`
- Candidate tree: `a7ff501e99278bcb70dae506fb28aa564d5b7364`
- Branch: `dev/v5-main-integration-20261012`
- Date: 2026-10-12; all execution times below UTC.
- Scope: isolated P0 tests and actual managed read-only module_api lifecycle only. Overall result: **FAIL (test regressions); real lifecycle smoke PASS**. This is not acceptance of P0–P5 or all 18 modules.
- Remote branch/tree checked before execution: HEAD was candidate; no feedback/handoffs directory or prior fixed-candidate execution feedback in that tree. No repository AGENTS.md or .agents/skills present.
- Read root START_HERE.md and P0_INTEGRATION_TASK.md first. No second source review, product modifications, frontend snapshot changes, excluded-file recovery, trading, real collection, credential access, system permission/proxy changes, or Codex application operations.
- Materialized only needed candidate files: all 66 V5/src blobs plus four test_p0 files, example config, pyproject, two root instructions, and integration_tests/test_p0_ledger.py (75 blobs). Every local byte sequence verified against its fixed Git blob SHA. This was not a full repository checkout.
- Existing interpreter Python 3.14.6 with existing pandas/pyarrow; existing pytest 9.0.2 imported from an existing Python 3.13 environment's pure-Python site-packages. No installation. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; PYTHONDONTWRITEBYTECODE=1. No claim of a fully locked pytest environment.

## Actual commands and results

Private absolute paths are replaced by logical variables: PY=existing Python 3.14.6, CANDIDATE=isolated fixed source root, CFG=isolated smoke/config.json, CHILD_CFG=isolated smoke/runtime/module_api_child.json. CWD=CANDIDATE. PYTHONPATH contained CANDIDATE/V5/src and the existing pytest site-packages. TMPDIR was task-owned evidence. The commands below were executed, with only path/PID redaction.

| Command | UTC start → end | Exit/result |
|---|---|---|
| `$PY -m pytest -q -p no:cacheprovider V5/tests/test_p0_main_registry.py V5/tests/test_p0_managed_module_process.py V5/tests/test_p0_runtime_entrypoints.py V5/tests/test_p0_runtime_lifecycle.py` | 04:19:35.831215 → 04:19:36.081541 | exit 1; 6 passed, 3 failed |
| `$PY -m pytest -q -p no:cacheprovider integration_tests/test_p0_ledger.py` | 04:20:09.212007 → 04:20:09.479760 | exit 1; 3 passed, 1 failed |
| `$PY -m v5_shadow.main_runtime validate --config $CFG` | 04:19:48.608316 → 04:19:48.639271 | exit 0; CONFIGURATION_VALID |
| `$PY -m v5_shadow.main_runtime status --config $CFG` | 04:19:48.639596 → 04:19:48.670690 | exit 0; STOPPED |
| `$PY -m v5_shadow.main_runtime start --config $CFG` | 04:19:48.671040 → 04:19:48.749140 | exit 0; STARTED; actual child and port 63305 |
| `/bin/ps -p $CHILD_PID -o pid=,ppid=,lstart=,command=` | 04:19:48.749501 → 04:19:48.752289 | exit 0; expected interpreter, v5_shadow.module_process, exact CHILD_CFG, --port 0 |
| `/usr/sbin/lsof -nP -a -p $CHILD_PID -iTCP -sTCP:LISTEN` | 04:19:48.752501 → 04:19:48.805038 | exit 0; 127.0.0.1:63305 only |
| Python urllib ProxyHandler({}) GET `http://127.0.0.1:63305/__v5/module-health` | 04:19:48.805368 → 04:19:48.809962 | HTTP 200; PID matched child; implementation SHA matched fixed candidate |
| `$PY -m v5_shadow.main_runtime status --config $CFG` | 04:19:48.810094 → 04:19:48.844702 | exit 0; RUNNING, socket_ready=true |
| `$PY -m v5_shadow.main_runtime stop --config $CFG` | 04:19:48.845107 → 04:19:48.880229 | exit 0; STOPPED |
| `$PY -m v5_shadow.main_runtime status --config $CFG` | 04:19:49.185590 → 04:19:49.217732 | exit 0; STOPPED |
| `/usr/sbin/lsof -nP -a -p $CHILD_PID -iTCP -sTCP:LISTEN` | 04:19:49.218071 → 04:19:49.245624 | exit 1, no output: child listener absent |

Subsequent ps returned exit 1/no child. All protected 8873/8910/54777/54778/54779 listeners retained their pre-test PIDs. No broad kill was used. Only the task-created child, whose command/config/PID/health identity was verified, was stopped.

## Reproducible failures (no local fixes)

1. `test_validate_requires_module_api`: expected MODULE_API_CONFIG_REQUIRED; actual RUNTIME_CONFIG_REQUIRED. Runtime entrypoints test line 21.
2. `test_validate_registry_contract`: config has runtime_root/composition but lacks module_api; validate raises RUNTIME_CONFIG_REQUIRED. Lifecycle test line 5.
3. `test_lifecycle_identity`: same missing module_api; start fails validation before spawning; the test's subsequent status/stop assertions are **NOT_REACHED**. Lifecycle test line 11.
4. `test_actual_saved_m07_product_preserves_same_run`: FileNotFoundError for logical `CANDIDATE/../v5-ledger-r3-local/ledger`. This fixture is outside the candidate tree. No private historical fixture was recovered, fabricated, or uploaded. Ledger test line 30.

The passing `test_contract_cases_documented` only asserts five constant True values; it does not execute those five scenarios. Its PASS is included in the raw six passes but must not be counted as a process integration proof. The independently executed smoke above is the actual process evidence.

## Smoke configuration and identity

A new task-only module data directory held only the marker `.v5-module-root` with bytes `v5.module-root.v1:p0_smoke\n`. Runtime config used:
```json
{
  "runtime_root": "<ISOLATED_ROOT>/runtime",
  "composition": "<ISOLATED_ROOT>/unused-composition.json",
  "module_api": {
    "schema_version": "v5.module_api.v1",
    "module_id": "p0_smoke",
    "release_id": "c2644-mac-isolated",
    "data_root": "<ISOLATED_ROOT>/module-data",
    "routes": []
  },
  "daily": {"enabled": false}
}
```
No composition file or business response was fabricated. Empty routes mean this verifies process and health only, not business API publication. The candidate's supplied example was read but not used verbatim because its module_api object does not contain this server's required module identity/root/routes fields. No product or example file was edited.

The runtime consumed the child's READY handshake before returning STARTED; independent ps/lsof/HTTP checks then proved a live process rather than config/identity-file creation.
- runtime marker: v5-main-runtime.v3; runtime code label: main_runtime.v3 (not a full commit attestation).
- module_api Git blob: d9d3f5f2ac06cb7802fade58829d00d6ca93c091
- Health implementation_sha256: 9a0fc23a18b7499961fa14d57fb097dc293f64f27c6f87b5bc0354921784e510.
- Health status READ_ONLY_RESPONSE_SERVICE; release c2644-mac-isolated; source_provenance_verified=false preserved.
- natural_verified=false throughout. Full candidate identity was independently established by blob verification; health itself does not claim provenance verification.

## Remaining scope / NOT_RUN

Full suite, integration_tests/test_plan_publication.py, business routes, frontend build/browser, CAS publication/recovery/rollback, duplicate-start/port-conflict/wrong-identity scenarios, dead-child stale status, daily tick, real inputs and natural windows were **NOT_RUN** in this bounded batch. No P0–P5 or 18-module completion claim.

Local raw evidence retains true command paths, timestamps, exits and identity details; only this minimal sanitized feedback is published. Feedback must be an append-only new path inherited from current branch HEAD with expected-SHA CAS, preserving concurrent changes.

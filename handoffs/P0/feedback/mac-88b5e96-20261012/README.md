# Mac ledger-only retest — 88b5e96

Fixed candidate: `88b5e96fae87f351f6b190f63e78ce614e899c39`.
Parent: `4777572b6a9c19807ccc2cf6ee641bb913dc9f83`.
Branch: `dev/v5-main-integration-20261012`.
Remote compare confirmed ahead 1 and exactly one changed file: `integration_tests/test_p0_ledger.py`, blob `303e0bd5a2d413f0f3d77477e551792eb6c3f818`.

## Actual execution: PASS

Only this test file ran, using existing Python 3.14.6 and pytest 9.0.2 in the same dependency setup as earlier feedback (existing pure-Python pytest site-packages, no installation). A separate task-owned candidate directory reused prior verified dependencies; all 75 materialized files were verified against the exact 88b5e96 remote tree before execution.

CWD=isolated candidate root; PY=existing interpreter (private absolute paths redacted).
```sh
$PY -m pytest -vv -p no:cacheprovider integration_tests/test_p0_ledger.py
```

- Start UTC: **2026-10-12T04:37:50.836521+00:00**
- End UTC: **2026-10-12T04:37:51.093703+00:00**
- Actual pytest exit: **0**
- **4 collected, 4 PASS**, pytest reported 0.04s.
- stdout: 4 passed; stderr empty.
- Plugin autoload/bytecode/cache disabled; temporary files confined to task-owned evidence root.

Passed nodes:
1. test_six_lanes_real_persistence_no_overwrite[order0]
2. test_six_lanes_real_persistence_no_overwrite[order1]
3. test_actual_saved_m07_product_preserves_same_run
4. test_new_lane_not_implicitly_registered_for_dispatch

The previously observed missing `.v5-daily-run-ledger` failure is resolved for this fixed candidate's synthetic fixture. This is synthetic ledger compatibility/reuse evidence, not a real M07 business result.

## Boundaries

No product/test modifications, source re-review, other test files, managed-process tests, manual smoke, frontend work, real collection/trading, credential access, system settings, or process start/stop occurred. No action on main or its unrelated misdelivery. The pending managed-process test repair was not assumed present or executed. Prior test/smoke evidence remains bound to its original fixed candidates; full P0–P5/18-module acceptance is not implied.

Feedback is appended only under handoffs/P0/feedback using fresh integration branch HEAD/base tree and expected-SHA CAS, preserving concurrent commits. No raw private paths or machine metadata are published.

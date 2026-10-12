# Independent review and verification limits

Two main-chain medium findings were reproduced and fixed before final acceptance:

1. Final pinned-source verification followed success-index publication. It now
   precedes SUCCEEDED/latest publication. Regression proves a final source failure
   preserves previous latest-success bytes. An index-write failure after a verified
   commit cannot retroactively mark that committed product FAILED.
2. Reader checked a supplied product hash but did not bind display provenance back
   to the retained request. It now rechecks the allowed data kind, exact source
   identity, stage/calendar metadata and fixed configuration. A rehashed invented
   future capture is rejected with M08_PROVENANCE_REQUEST_BINDING.

Original auction normalization also exposed two wrapper-level failures: an empty
failed source became READY_EMPTY and a partial source became READY. Both were
observed in failing tests. Explicit upstream diagnostics now keep the unchanged
original owner envelope fail-closed; original order, scores and Top10 remain.

The API adapter's separate review reproduced quoted/unquoted paths with spaces
and formula-like diagnostics. Final tests preserve real arithmetic formulas while
redacting private paths. Actual no-injection producer/store/reader/API/HTTP tests
exercise ordinary, auction and independent Stage8 routes; source private root
can be moved after publication and GET continues reading only committed records.

Final bounded acceptance is recorded under `V5/tests/logs/M08_FINAL/` with exact
commands, UTC start/end, exits and runtime versions. Successful logs are raw.
Older failure traces are path-redacted for publication only; substantive output
is unchanged and the original capture was retained in the engineering workspace.

The complete supplied V5 unittest discovery was also executed. It has one
collection error: `test_daily_owner_adapters` imports `v5_shadow.daily_rebound_owner`,
which is absent from this original M08 material branch. A fresh exact baseline
reconstruction from 5da7322 reproduces the same error (54 tests, one error).
It is not hidden, and unrelated module code is not copied or repaired to obtain
an artificial all-green result. Final full-suite output accompanies delivery.

Production package requirements are not satisfied by this cloud interpreter
(Python 3.12.14, pandas 2.2.3, no pyarrow, no pytest). The bounded original-owner
chain uses stdlib and its tests run here. Full donor pytest tests, supported Mac
runtime, live inputs, page deployment, automatic/natural scheduling and two-day
acceptance are NOT_RUN. No claim of full M08 completion is made.

Shared code integration remains unchanged: no shared ledger allowlist was altered,
no existing lane was impersonated, and no main/P0/UI file was overwritten.
The public API adapter is a callable implementation using the existing immutable
module publisher/server. A real active mount requires the integrator's verified
Mac baseline and separate acceptance; it is not represented by a guessed URL.

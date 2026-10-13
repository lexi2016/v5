# M06 P0 daily integration — Mac focused validation

Fixed candidate: `211fe3e38946bc07285c1a027f63f25b23c9eb1f`; product parent: `5b32a0916fbe486bbf7a33c1ce6ad9e3e4618e51`.
Source closure: 146 entries, SHA256 `75482f54ccc5e2fa0bd9216273fdc7ee2276a32171cc94cfd1c7ba6ca9e44ab9`.

Mac result: **21 new tests PASS + 9 necessary targeted regressions PASS**, both exit 0. Exact commands, UTC start/end, environment aliases and closure checks are in report.json. Existing HK02 Python 3.13.12 was used; no dependencies installed. No old M06 85-suite or M17 suite rerun. No product changes, deployment, live-service changes, real provider collection, model deserialization/scoring or scheduler enablement.

New tests exercise tick → dispatch → original M06 produce → independent fresh-process reader using synthetic fixtures. They verify two ledgers and distinct run IDs, P0 admission versus M06 completion cutoffs, publication digest separation, saved reuse, mismatched/corrupt receipts, unknown outcomes, concurrent dispatch, explicit slots and other-lane configuration isolation. Fixture tests are not real-source P0 acceptance.

## Actual runtime blocker

**MAC_30_TESTS_PASS_REAL_REGISTRATION_RUNTIME_BLOCKED.** The existing HK02 venv interpreter is a symbolic link. `V5/src/v5_shadow/p0_hk_preselection.py:25` requires `no_symlinks(python_executable)`; the worker launches that exact path with `-I -B` (line 41). Resolving the link to the pinned base Python preserves executable bytes but loses the venv package context. A metadata-only probe of both interpreters with `-I -B` confirmed the venv has numpy 2.5.2, pandas 2.3.3, scikit-learn 1.9.0, joblib 1.5.3 and pyarrow 23.0.1; the resolved base interpreter reports all five MISSING. See interpreter-preflight.json for exact commands, times and exit codes. No model was loaded.

Consequently the prepared disabled configuration is **not ready to execute**. Using the venv link violates registration; using its resolved path cannot reproduce the original owner dependency identity. Do not enable it or replace the cutoff to force a new identity. Product owner must reconcile the pinned-interpreter validation with the existing venv execution context. No local product fix, package install, wrapper workaround or real owner call was made. Passing synthetic tests do not remove this blocker.

## Prepared existing-pool contract — disabled, blocked, not executed

planned-bundle.json is the exact prepared request with eight source hashes and ten asset hashes. planned-daily.disabled.json uses redacted root aliases; a local copy has resolved absolute roots and Python path. Both daily and M06 registration remain disabled. No tick, prepare/inspect, original owner or original cold reader was invoked against real materials in this task.

- Proposed single manual slot: `2026-10-13T10:00:00+08:00` to `2026-10-13T10:30:00+08:00`, half_day_bound=true, max_attempts=1. This is a proposed controlled slot, not an enabled or historical V4 schedule. If expired before a later authorized call, prepare a new explicit eligible slot; never alter the clock or silently roll the date.
- Target `20261013`, signal and eligibility `20261012`; method `EXISTING_VERIFIED_POOL`, mode `MANUAL_RECOVERY`.
- P0 admission cutoff is the actual observation time recorded in planned-bundle.json. M06 completion/research cutoff remains `2026-10-12T17:11:34.690550+00:00` to preserve the existing original-owner computation identity. Both are on the target HK date. For the existing-pool branch this past completion cutoff describes the saved product. It must not be reused for GENERATE_IF_ABSENT, which requires a genuinely future bounded completion cutoff.
- P0 ledger: `<NEW_P0_TASK_ROOT>/p0-ledger`, new, correctly marked, zero runs. P0 UUID remains null until an actual claim.
- M06 ledger: `<EXISTING_M06_TASK_ROOT>/output/.m06-ledger`, separate from P0, one existing SUCCEEDED attempt. The registration private_root points at the already isolated original M06 output, deliberately retaining its receipt rather than constructing a second output/publication.
- Existing M06 UUID: `f745c78857d54fa89849f2adbfa3602f`.
- Existing publication digest: `f7d1e1d4f4472c5e0733f1ca5cbc32d2c297e651fd3d5a0e3874a6c7ba5cd92b`.
- Existing producer receipt SHA256: `041c857b7f31c19e64e1e4bbed7ca29ba0d50b556445d5de82853d01c101abdc`.

Raw bytes of all 18 declared input/asset files and the five referenced publication/receipt files were checked. Saved ledger identity, latest success, run UUID and committed reference match the existing result. This is a read-only receipt/inventory check, not a new product cold-reader run. The exact expected original identity is recorded in report.json. Before any later authorized real invocation, the candidate's fresh inspection must reproduce it under the actual interpreter and unchanged dependency context; abort on mismatch rather than generating a new M06 publication. A later actual P0 run would still need its own P0 UUID plus independently verified M06 reuse and reader mapping. That real path remains NOT_RUN.

No real-model or natural-scheduler acceptance is claimed. The overall 18-module/P0–P5 system remains unaccepted.

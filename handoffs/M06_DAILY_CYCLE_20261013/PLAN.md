# M06 daily candidate closed-loop implementation plan

Goal: connect explicitly configured input delivery to one frozen daily request,
the existing dispatcher/original owner, and a two-ledger-verified current-success
reference consumed by the existing read-only API.

Architecture: reuse the pinned original HK securities calendar, P0/M06 owners and
ledgers. Keep a M06-only immutable day bundle under the existing bundle marker,
and atomically CAS a private current-success pointer only after fresh readback.
No frontend, original model/owner, other lane or V4 changes.

## Explicit unresolved runtime configuration

The original panel interface has no specified persisted completion-time receipt.
This candidate requires a new explicit upstream input-delivery record containing
completion time, dates and exact original file inventories. The scheduler never
creates such evidence. Its real publisher/path and the full/half-day windows
remain unconfigured and defaultDisabled. Calendar close times and the former
manual deadline are not recurring schedule authorization.

## Steps

- [x] Add failing focused tests for daily admission: original HK previous session,
  2026 range, explicit half-day policy, future/missing/late deliveries and budget.
- [x] Implement prepare_daily_candidate in p0_hk_preselection.py: validate the
  delivery, lock and atomically freeze one day bundle, then reuse prepare_job.
  Changed input/config/code/dependencies must block reuse; never mint a new
  cutoff per tick. Missing inputs must not claim a ledger run.
- [x] Add failing tests and implement promote_current_success after dispatcher
  success plus fresh read_saved. CAS against the frozen prior-pointer digest;
  unknown/failure/stale candidates preserve the old pointer.
- [x] Add reader tests and implement exclusive current-success binding alongside
  the unchanged fixed-reference shape, exact two-ledger mapping, original cold
  read, and post-read pointer/ledger stability checks. GET never writes.
- [x] Normalize flat versus nested daily CLI config; integrate candidate in tick
  without other-lane config rekeying or implicit M06 slots. Reject two M06 jobs.
- [x] Run only new focused suites and a few affected regressions, record actual
  results/limits, provide disabled examples and Mac commands, CAS commit and
  verify remote diff/readback. Do not enable launchd or run real provider/model.

Review focus: concurrent first-freeze and publication; changed bytes under the
same delivery name; restart after unknown owner outcome; symlink/path escapes;
pointer or ledger tampering while a read is in progress. Each is covered in the
focused tests, not assumed from a happy-path result.

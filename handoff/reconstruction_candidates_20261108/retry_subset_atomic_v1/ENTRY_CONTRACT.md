# Retry subset entry candidate — new interface, no production binding

Baseline: `71666f8d6c04ffea387c8d2273f5c63d1463f571`.
Scope: the existing `retry-1610` and `retry-1640` nodes, Asia/Shanghai.
No task ID, frequency, timezone, original formula, source gate or resource floor
is changed. `TRUSTED_RUNS` remains empty. Publication `REGISTRY.json` is retained
byte-for-byte as the historical baseline inventory, not an execution
authorization or this patch's file list. `PATCH_MANIFEST.json` records new bytes
and actual isolated tests without creating authoritative registrations.

## What changed

1. `subset_plan.py` reuses independently verified all-success results after the
   third attempt. Completed work consumes no fourth attempt and no retry
   cooldown. A remaining failure still requires fewer than three attempts and
   at least 30 minutes from the previous independently confirmed end. A future
   end time is always refused.
2. `entrypoint.py` supplies the missing reviewed owner seam. It reuses the
   existing atomic coordinator and planner. It does not interpret the original
   full-argv approval as permission to change argv or to run a subset.
3. The coordinator's existing immutable claim, retained UNKNOWN state,
   shared same-date budget, successful-output preservation, directory/lock
   identity protection and process lock are retained.

## Call map and defaults

```
existing after-10 router
  -> entrypoint.dispatch(node_id, run_id, environment_id, execute=False)
  -> exact ReviewedRun in TRUSTED_RUNS (otherwise BLOCKED before any I/O)
  -> new subset contract + independent entry approval + original contract pins
  -> pinned reconciliation and lazy verified successful-output bytes
  -> subset_plan.plan
  -> original OwnerHooks.guard (source/calendar/start gate/original locks)
  -> original monitor pulse + repeated pinned preflight
  -> Coordinator.execute (same canonical ledger for both slots)
  -> durable claim
  -> OwnerHooks.execute_subset(failed_symbols, same_attempt_context, pulse)
  -> RETURNED_AWAIT_INDEPENDENT_RECONCILIATION
```

`execute=False` only makes a plan; it does not claim an attempt, create a day
directory, take the original owner's execution guard or call the executor. It
is not proof that the current local attempt state is dispatchable.

`execute=True` must be an explicit boolean. The request has no clock, state-dir,
argv, resource floor, reviewer hash, successful output or owner override. The
aware clock is supplied by the reviewed registry. Existing node schedules are
not created or modified by this interface.

## New reviewed contract

`ReviewedRun` contains the exact run/environment key, a new contract `FilePin`,
an independent entry-approval `FilePin`, per-node reconciliation pins, successful
output pins, owner hooks and the registered clock. The production tuple is
empty; tests inject explicitly synthetic entries only.

The new contract has schema `REVIEWED_RETRY_SUBSET_ENTRY_V1` and owner API
`RETRY_SUBSET_OWNER_API_V1`. It binds:

- the complete original `binding`, without rewriting its paths or hashes;
- `environment_id` and the reviewed `owner_identity`;
- canonical `original_root`, used only to resolve existing relative refs while
  preserving their identity;
- canonical `ledger_root`, its device/inode, and the existing lock device/inode;
- exact dependency refs including this entry, `subset_plan.py`, `coordinator.py`
  and the actual original owner adapters/dependency closure.

The independent entry approval has schema `RETRY_SUBSET_ENTRY_APPROVAL_V1`,
status `PASS_RETRY_SUBSET_ENTRY`, role `independent_reviewer`, and binds that
exact **new** contract ref, environment and complete binding. An old
`PASS_DATED_DISPATCH` full-argv review is rejected. The original contract file
is still read under its original pin; its date, identity, source date,
availability, input/code refs, argv, resources and locks must match. Missing
source/calendar/owner contracts remain blocked by the original guard; no
weekday inference or replacement source approval is generated here.

Pins use bounded regular single-link, no-follow file reads. Hashing, JSON
parsing and compilation consume the same bytes. Checked planner/coordinator
modules use a private import mapping, avoiding global `sys.path` or
`sys.modules` substitution. Successful outputs are read one at a time rather
than retained as a full-pool byte dictionary. The small-evidence reader has a
16 MiB per-file ceiling; larger real output evidence needs an independently
reviewed bounded/streaming consumer before live binding, not a larger caller
override.

## Original owner callback contract

`OwnerHooks.guard(original_binding)` is an adapter around the original owner,
not a substitute lock or resource policy. It must verify the original source
and calendar contracts, acquire the original queue/owner lock domains, apply
original start/resource gates, and own monitor/process/database cleanup. It
yields `pulse()`, which returns `None` or raises on a failed original runtime
gate. The entry adds no fake resource measurements or alternative budgets.

`execute_subset(tuple(symbols), context, pulse)` receives only independently
reconciled failed stocks. `context` includes the same durable `attempt_id`,
ordinal, original binding, owner identity, node, environment and review/entry
refs. It must retain per-stock original writer, checkpoint and input checks and
invoke the original monitor at its runtime checkpoints. A caller may bridge
each stock to `daily1540/owner_bridge.advance_from_owner` while the original
owner runtime is held. Merely reaching `PERSISTED_AWAIT_OWNER_SEAL_AND_INDEPENDENT_SAMPLE`
must return an unresolved result, not a business success.

The return is a mapping with exactly the requested symbols: byte evidence for
an observed successful output or `None` for an unresolved result. Neither form
is an independent reconciliation. Exceptions or dependency/input drift after
claim retain UNKNOWN; no output or unknown lock is deleted. An execution
result cannot create the next review or safe-retry approval.

## Resume, retry and failure handling

- A fresh caller output directory does not select a fresh ledger. The entry
  takes no directory argument and requires the registered root/lock inode.
  It never calls `initialize`, creates a replacement lock, or clears history.
- Both slots use the same root and day identity. New run/version labels cannot
  obtain another same-date budget. The reviewer must retain all local attempt
  IDs; a partial or missing terminal cannot be inferred clean.
- Successful stocks must retain verified output bytes and are excluded from
  the callback. UNKNOWN, partial effects or active work require independent
  reconciliation first. Only `FAILED_CLEAN` with reviewed no-persisted-effects
  semantics is retryable under this contract.
- The maximum is three total attempts including the original attempt. Completed
  third attempts can be reused. A third failed attempt remains blocked.
- Startup/contract failures return `BLOCKED`. Failures after entering the
  claim/execution phase conservatively return `UNKNOWN_RECONCILIATION_REQUIRED`.
  `KeyboardInterrupt`, `SystemExit` and other BaseException interruptions still
  propagate; existing claims remain for independent reconciliation.

## Validation and remaining limits

Run from this directory in an isolated checkout:

```bash
python -m unittest test_subset.Tests test_atomic.AtomicTests test_review_paths.ReviewPaths.test_review_moved_day_does_not_reset test_review_paths.ReviewPaths.test_review_moved_lock_does_not_split test_completion_reuse.CompletionReuseTests test_entrypoint.EntryTests
python -O -m unittest test_subset.Tests test_atomic.AtomicTests test_review_paths.ReviewPaths.test_review_moved_day_does_not_reset test_review_paths.ReviewPaths.test_review_moved_lock_does_not_split test_completion_reuse.CompletionReuseTests test_entrypoint.EntryTests
python -m unittest test_daily_bridge_integration.DailyBridgeIntegrationTests
python -O -m unittest test_daily_bridge_integration.DailyBridgeIntegrationTests
```

Tests cover synthetic successful/failed stock subsets, repeated calls, shared
slot accounting, preserved partial effects, process interruption/competition,
input/dependency/version changes, canonical path/lock replacement, relative
original pins, old-approval rejection and verified-byte loading. Original
resource and owner hooks in these tests are explicitly synthetic.

The cross-module tests use the actual `owner_bridge`/checkpoint interfaces and
the explicitly synthetic owner fixture. They verify that persisted-but-unsealed
work is still unresolved, writer partial effects are retained, missing checkpoint
registration does not synthesize state, a cold changed checkpoint is rejected,
and independently reviewed fixture success is reused. These five tests require
the daily1540 bridge/fixture and recovered provider delivered by the companion
patch. They do not run native calculation or real Parquet I/O.

Real original-owner integration, actual writer/native outputs, target-day
inputs, original source/calendar contracts, production registration and natural
16:10/16:40 triggers remain UNKNOWN. No test result grants those approvals.

Rollback: revert this patch's new files and restore `subset_plan.py`, the
coordinator documentation and publication inventory to the pinned baseline.
Do not delete runtime ledgers, claims, output files or locks during rollback.

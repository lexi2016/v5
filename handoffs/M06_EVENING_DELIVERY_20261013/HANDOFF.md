# M06 close-day → next-HK-session candidate

Continues f157b59833fc0a10bf04ae9ea5df5d6166be0c64, its independent Mac acceptance 6449bb3348e40fea5edab88dbf8d1df28b10ee49, and exact Mac interface evidence da278dfdc533b83a491762aab9fc96466cf0d0db. The original observed evening successes are shared-data producer successes, not natural V5 daily-owner successes.

## Contract

New `date_contract=CLOSE_TO_NEXT_HK_SESSION_V1` explicitly binds scheduled/business date = signal date = master date D. Target is the next HK **securities** session resolved through the unchanged 2026 source calendar; previous-session and next-session boundaries are checked. No A-share/HK Connect holiday substitution, inferred weekday, or unsupported 2027 calendar.

Four meanings remain separate:

1. Original source PIT/data labels are preserved verbatim in copied manifests/receipts. A `17:30` source label does not prove actual data availability.
2. A new immutable snapshot's actual completion precedes P0 `admission_cutoff` on D. The original worker separately rejects source captures/finishes after admission.
3. `execution_deadline` is the real D execution-window end. Preclaim budget, all original inspect/invoke/read subprocesses, ledger completion checks, fresh readback and current-success CAS use this deadline.
4. `owner_contract_cutoff` is an explicitly configured target-day compatibility upper bound for the unchanged original M06 interface. It is not PIT, a demonstrated historical value, or permission to work past execution_deadline. The configuration has no default for this field.

The original M06 capsule, algorithm, model PIN, original ledger implementation and old committed references are not modified/re-pinned. New P0 request/product identities include the explicit evening contract and all three operational timestamps. The original M06 identity continues to use its compatibility cutoff; both identities/run IDs/reference/product hashes must match. Legacy explicit same-target requests and existing fixed/current read-only bindings remain valid.

## Deadline-owned processes

The evening adapter creates a fresh POSIX session/process group for each original worker. Original nested children inherit it. Actual UTC deadline and monotonic timeout are checked independently of the request's replay clock. Expiry, cancellation, exceptions or leaked descendants trigger cleanup of only that owned group, bounded drain and parent reaping; uncertainty is never success or automatic retry. A failed/unconfirmed attempt leaves the previous current-success reference intact.

This is bounded owned-process handling, not a hard real-time OS guarantee. OS scheduling/process creation/uninterruptible kernel work may delay signal handling. Cleanup has its own bounded observation interval; inability to confirm termination remains UNKNOWN. The guard requires `waitid/WNOWAIT`, `/bin/ps`, and inherited process groups; an unsupported runtime fails closed. Synthetic child/grandchild heartbeat tests verify cleanup and an unrelated sentinel's survival. Mac must run those focused tests in the existing pinned HK02 environment before acceptance.

A GET has no current-time deadline gate. It can read a previously saved successful evening result after its window, but validates that **both** persisted ledger finished_at timestamps are strictly before execution_deadline. It rereads the pointer/ledger state around the unchanged original cold reader and never starts an owner.

## Read-only input delivery

The new adapter reads only explicit original roots and bounded relative paths. It verifies the successful dispatcher → exact workload envelope → raw lane receipt bytes/SHA → panel manifest/payload chain, plus exact signal-date master and original model/name input hash links. It does not update, collect, score or load a model. Hash verification alone is not model-validity verification: the original cold inspector remains authoritative.

Only declared pointer-chain bytes are copied into a separate V5 snapshot; they are streamed, hashed, rechecked and sealed. The seal retains separate upstream evidence. A new completed_at records actual completion of the newly validated snapshot, never historical panel completion, mtime, preparation time, or an unperformed tick. Subsequent ticks reuse that sealed snapshot and original completion timestamp even if live latest pointers change. Changed/corrupt sealed bytes, config, inputs, code or dependencies cannot become a new retry identity for a frozen job. Missing inputs wait before ledger claim.

Original asset roots may be nested inside their original store. Snapshot, delivery, P0 ledger, frozen-bundle and private output roots must be isolated from each other and originals; symlink/root/PIN constraints remain enforced. Required existing markers:

- snapshot root: `.v5-m06-input-snapshots`, bytes `v5.m06-input-snapshots.v1\n`
- delivery root: `.v5-m06-input-deliveries`, bytes `v5.m06-input-deliveries.v1\n`
- bundle root: `.v5-daily-bundles`, bytes `v5.daily-bundles.v1\n`
- P0 ledger: `.v5-daily-run-ledger`, existing exact run_ledger.MARKER
- private output: `.v5-shadow-root`, bytes `v5.shadow-root.v1\n`

Markers and local paths are explicit setup values, not permissions to reuse arbitrary roots. Do not delete old pools, ledgers, snapshots or frozen bundles to force retry.

## Configuration still disabled

`V5/examples/m06_daily_runtime.template.json` has all execution switches false. Original trigger slots support 17:30 (and later 18:00) on full/half days; 18:00 is not an inferred 17:30 deadline and is not a second authorization to recompute. The first admitted input is frozen once. Required operator decisions remain:

- D full/half-day execution-window ends
- complete chain budget, including inspection, original owner, separate readback and publication overhead
- target-day owner compatibility cutoff time
- verified original receipt locators and isolated V5 roots

The original 600-second per-process timeout is not a complete chain budget. No real model/provider run, launchd/service enablement, deployment or natural schedule has been performed by this change.

## Acceptance

Use only the existing HK02 Python environment and the focused command in verification.json. Verify source-closure.json before and after. Do not install dependencies, execute the real owner/model, enable scheduling, change the active backend/binding, or rerun unrelated historical suites as part of candidate acceptance. The old real 100-row publication stays intact.

Cloud tests use synthetic fixtures. A real original-owner existing-pool end-to-end test uses actual process/ledger time on an eligible current 2026 session; unavailable current calendar dates are reported as skipped, not passed. Separate historical-calendar tests exercise Friday/weekend/holiday/half-day semantics with test-only clocks. Nothing marks synthetic results natural_verified.

### Focused Mac command (no installation)

From the fixed checkout, using the already approved HK02 interpreter:

```sh
PYTHONPATH=V5/src:V5/tests "$HK02_PYTHON" -B -W error::ResourceWarning -m unittest \
  test_m06_evening_cycle test_m06_evening_reader test_m06_input_delivery test_m06_deadline_process \
  test_daily_dispatch \
  test_m06_daily_cycle.M06DailyCycleTests.test_tick_original_owner_dual_ledger_success_promotion_and_reuse \
  test_m06_readonly_api.M06ReadOnlyAPITests.test_actual_original_cold_projection_all100_and_readonly \
  test_m06_readonly_api.M06ReadOnlyAPITests.test_saved_artifact_tamper_rejected_and_no_republication \
  test_m06_current_success_reader.M06CurrentSuccessReaderTests.test_pinned_venv_leaf_retains_original_cold_reader_projection -v
```

The dispatcher/envelope JSON-shape clarifications were read from the same authorized Mac evidence continuation: succeeded_workload_ids / invoked_workload_ids string arrays; resolved_dates.research_panel_daily_hk has scheduled_date/signal_date/target_date; workload_results rows use workload_id. Both row._authoritative_payload and row.source_result are direct equal envelope objects, both containing status=READY and overall_status=READY. No guessed nested fallback is accepted.

Cloud has no real model bytes or approved live source roots. End-to-end positive tests invoke the original owner/reader using explicit existing-pool synthetic fixtures. The real snapshot adapter is also connected to original cold inspection in a negative integration test: hash-complete fake model bytes are rejected before any P0 claim or current publication. Full real-receipt + real-frozen-model snapshot admission remains NOT_RUN until the runtime paths/policies are supplied on Mac; no synthetic pass is reported as real model verification.

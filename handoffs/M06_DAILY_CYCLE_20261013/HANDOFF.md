# M06 daily candidate: delivery → frozen job → verified current success

Inspection base: `af758f0beeb3e9518de05e62a0af23f9e032690c`.
Branch: `lexi2016/v5:dev/v5-main-integration-20261012` only.

## Product changes

- `p0_hk_preselection.py`: original HK securities calendar/previous session;
  explicitly configured full/half-day windows and execution budget; input-delivery
  admission; immutable day-bundle freeze; post-success current-reference CAS.
- `daily_tick.py`: accepts the existing nested main-runtime config or a flat daily
  config (ambiguous forms reject); integrates the candidate without a hand-made
  legacy day bundle. M06 gets no other-lane default slot. Candidate plus explicit
  M06 job rejects both. Other-lane config identities exclude M06-only settings.
- `m06_readonly.py`: keeps fixed-reference binding and adds an exclusive
  current-success binding. Every GET reads the pointer anew, validates the exact
  two ledger successes, calls the unchanged original cold reader, then rechecks
  pointer, ledgers and pinned Python launch identity. It never writes or computes.

No frontend, original M06 owner/model/worker, run_ledger, dispatcher, M17, M18,
other module or V4 source changes. The existing disabled launchd render contract
remains disabled; no service has been installed, enabled or deployed by this task.

## Input completion is an explicit unresolved runtime dependency

The pinned original panel updater persists parquet/manifest/latest and returns a
READY result, but defines no persisted completion-time receipt. The real Mac
manifest may carry additional provenance; this task does not guess its meaning.
The original security master has a READY receipt and a dated captured_at manifest,
but no completed_at field. Neither file mtime nor the tick clock is completion
evidence.

The new **P0 handoff contract**, not a changed original M06 contract, is
`v5.m06_daily_input_delivery.v1`; see `V5/examples/m06_input_delivery.template.json`.
An explicitly verified upstream publisher must atomically provide one
`YYYYMMDD.json` under a configured root marked
`.v5-m06-input-deliveries` with bytes `v5.m06-input-deliveries.v1\n`.
It binds READY, actual completion time, exact target/signal/master dates and raw
SHA256 inventories of original source/assets. This scheduler never creates it.
Use all files required by the original owner, including any present optional
asset/name receipts; remove inapplicable placeholder entries, not real inputs.

Admission requires the original previous HK securities session, exact panel
`panel_max_date == signal_date` when panel assets are present, the original
master receipt's READY/date identity, and original source capture/finish times
no later than handoff completion. The original inspect path then verifies the
complete byte/identity/model-asset chains without running a model. Missing
handoff or declared input file returns WAITING before a ledger claim. Wrong,
future, changed or malformed evidence rejects. Synthetic replay fixtures remain
explicitly synthetic and never prove a real model computation.

Still to be confirmed before any activation: real input-handoff publisher and
path; full-day window; half-day window or explicit skip; execution budget; exact
master-date policy. The original calendar is 2026 only; unknown year/session
blocks. Calendar close times and the former manual run's deadline are not
recurring schedule authorization.

## Freeze and success semantics

Under the existing `.v5-daily-bundles` root, a stable no-follow M06 lock freezes
`.m06-YYYYMMDD.json` once, with delivery hash, candidate configuration/root hash,
prepared job/identities, and expected current-pointer digest. Admission cutoff is
the first actual admitted observation; completion cutoff is the explicitly
configured window end. These never slide on later ticks. **The M06 legacy
completion cutoff is not a PIT data cutoff.** P0 retains admission cutoff in its
own identity. Source, configuration, code, Python identity or dependency changes
cannot reuse the frozen success; they block instead of minting a new retry key.

The execution budget is explicit, at least two configured process timeouts, and
must also cover the chosen inspection/readback/publication overhead. The remaining
window is checked before and after inspection and immediately before claim.
No finite budget is inferred from the original calendar or another lane.

The unchanged dispatcher/owner retains one-attempt/UNKNOWN semantics. After P0
finish/readback, promotion performs another independent original read checking
the M06 ledger. Only matching P0 and M06 successes may CAS the fixed private
`.m06-current-success.json` under the marked M06 output root. A stale CAS, late
completion, failed/missing/unknown run, or failed fresh read leaves the previous
pointer unchanged. Same successful candidate is idempotent; older/equal-date
different candidates cannot roll back the current reference.

The pointer is private runtime state, not an API payload and not hand-edited
configuration. Do not delete frozen bundles, pools or ledgers to force retries.

## Configuration and Mac checks

`V5/examples/m06_daily_runtime.template.json` has all three execution switches
false. Replace placeholders only from verified existing source/runtime contracts;
the budget placeholder must become an integer. Half-day null means an explicitly
chosen skip, not an inferred policy. Keep the original venv launch path; pin its
real binary SHA and the existing four venv identity fields. Never resolve the
launch path to the base interpreter or rebuild/install an environment.

In the existing Mac V5 checkout and existing Python environment, focused isolated
verification only:

```sh
PYTHONPATH=V5/src:V5/tests "$HK02_PYTHON" -B -m unittest \
  test_m06_daily_cycle test_m06_current_success_reader test_daily_dispatch \
  test_m06_readonly_api.M06ReadOnlyAPITests.test_actual_original_cold_projection_all100_and_readonly \
  test_m06_readonly_api.M06ReadOnlyAPITests.test_saved_artifact_tamper_rejected_and_no_republication -v
```

These use synthetic original-source fixtures, not real collection or model jobs.
Do not rerun old M06/M17 suites, real model generation, or natural scheduling for
this acceptance. Verify source-closure.json before and after the scoped run.

For the existing source-bundle API, leave its fixed binding unchanged until an
authorized daily candidate has established a valid pointer. The exclusive new
shape is in `V5/examples/m06_current_success_binding.template.json`; put it at
the existing `m06_hk_preselection_binding` key, without committed_reference.
It must use the same marked private output and separate P0 ledger as the daily
config. A missing pointer returns NOT_CONFIGURED; it never auto-selects a pool.
Once configured, later valid current-success updates are visible without an API
restart; every failed/corrupt GET remains fail-closed and cannot trigger production.

Actual local schedule enablement, live input-publisher binding, real generation,
deployment and natural verification are **NOT_RUN** for this candidate. The
previous Mac real 100-row result remains separate evidence, not a new run here.

## Cloud result

58/58 scoped tests passed (24 new daily-cycle, 27 new current-reader, 5 existing
dispatch, 2 existing fixed-reader) in 111.253 seconds. See verification.json and
cloud-tests.txt. The 150-file source closure SHA256 is
`3fbc5607186f831e1d230b06512070f455a7fa39db71b9c8fb6fa60ba5c8783f`; bytes were rechecked after tests.

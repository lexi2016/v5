# M06 native-pool compatibility and explicit sealed selection

Candidate only; all activation switches remain false. Two production files change:
`m06_input_delivery.py` and `p0_hk_preselection.py`. Original owner/reader, their
50-file pin, old committed references, V4 and other lanes are unchanged.

## Evidence and fix

Mac feedback `f22517b73520e5c1758fad400c317298ed716077` found the historical UUID
receipt but stopped at `M06_DELIVERY_SAFETY`. This was the target-pool manifest
schema mismatch, not a missing flag on the delivered upstream panel chain.
The original frozen M06 capsule at `08ed9de9ddb5fd2c62eb1762df2f6106464d823b`:

- `V5/source_owners/m06/V5/vendor/hk_preselection_baseline/upstreams/v3_shared_data/shared_data/collectors.py:168–190`
  creates `v3_shared_data.manifest.v1` without the three safety flags.
- Same directory `store.py:451–483` binds its canonical hash in
  `v3_shared_data.receipt.v1`, which asserts all three flags false.
- `store.py:173–218` / `consumer.py:36–56` validate those receipt assertions;
  `hk_0_2.py:1134–1191` and the fixed owner retain their actual pool validation.

Only that exact manifest/receipt schema pair gets receipt-authoritative safety:
`production_allowed`, `buy_gate_updated`, `orders_sent` must each be boolean false
on the receipt. If any appears on the manifest, it must also be false. Schema,
owner/run, signal/target, 100-row and temporal identity, canonical manifest SHA,
raw artifact SHA, source inventory and completion-time checks remain enforced.
Unknown-schema manifests retain the old strict gate. No source bytes are patched.

## Opt-in selection, not fallback

The existing default template remains `GENERATE_IF_ABSENT`. The separate
`V5/examples/m06_daily_reuse_or_generate.disabled.template.json` opts into
`REUSE_VERIFIED_OR_GENERATE_IF_ABSENT` only with the evening date contract and
input-delivery adapter. It differs from the default by that single policy value.

After full input/receipt validation and seal readback, exact-target pool presence
in the hash-verified sealed `store/latest.json` selects `EXISTING_VERIFIED_POOL`.
A truly absent target selects `GENERATE_IF_ABSENT`. A present null/bad entry,
bad receipt, mismatched SHA, invalid cold read or later inspect failure is never
reclassified as absent. Later live latest changes cannot change a sealed choice.

The selected concrete value is written into the existing `owner_request`; no
new owner API or receipt schema is introduced. The unmodified producer writes
`production_method=EXISTING_VERIFIED_POOL` for reuse, or `FROZEN_MODEL_PRODUCER`
for generation, and the existing fresh reader checks that against the request.
Existing-pool reuse does not rerun the model, so this run's producer and reader
`model_weights_reverified` remain false. Original provenance is retained.

D scheduled/signal, next HK-session target, PIT admission and D execution_deadline
are unchanged. Target-day `owner_contract_cutoff` is compatibility metadata, not
permission to extend the actual deadline. Frozen request/config/input identity,
both ledgers, UNKNOWN handling and current-success CAS remain unchanged.

## Verification scope

Two pre-fix RED assertions reproduced the native-schema safety rejection and
unsupported opt-in policy. Final **19 PASS, 0 skip, exit 0**: 16 new methods and
three narrow resolver regressions. See `red.txt`, `tests.txt`, `report.json`.

- New adapter/policy tests use synthetic source bytes, test receipt missing/true,
  manifest conflicts, wrong target/owner/schema/hash, null entry, absent target,
  no source rewrite and first-seal stability.
- Two tests actually call the fixed original inspector using selected concrete
  requests. Fake assets are rejected before claim; this is not model success.
- Three original-owner tests use a 100-row synthetic original-schema pool and
  actual cold processes: native reader ASSEMBLED; two ledgers SUCCEEDED; fresh
  reader/CAS; second tick REUSED_SUCCESS and owner called once. Bad receipts and
  manifest hash are rejected by the actual original cold reader before claim.
- Full real-assets auto-policy end-to-end, model generation and natural schedule
  are NOT_RUN here. No dependency was installed. Old 85/89, guard15 and resolver24
  suites were not rerun in full.

Tests used inherited parent `39a903afbdd95f110463c8372aa493e81b7209cd`, including
its actual `main_registry.py` code identity. `source-closure.json` records the
163-file candidate/test closure (raw file SHA-256 in `report.json`). Inherited
files are references, not repeated source additions or deployment instructions.

## Mac application and focused verification

1. Read this fixed commit, preserving current preview and original references.
   Use an isolated candidate; verify every source-closure byte/hash. Do not
   overlay these changed daily files into an already bound successful execution.
2. Use the existing verified HK02 Python/venv with no install. Set `TMPDIR` to a
   new owned isolated test directory and run from candidate repo root:

```sh
PYTHONPATH=V5/src:V5/tests PYTHONDONTWRITEBYTECODE=1 "$EXISTING_HK02_PYTHON" -B -W error::ResourceWarning -m unittest \
  test_m06_native_pool_admission test_m06_native_pool_owner \
  test_m06_dispatch_resolver.M06DispatchResolverTests.test_existing_pool_missing_safety_is_not_repaired_or_ignored \
  test_m06_dispatch_resolver.M06DispatchResolverTests.test_uuid_discovery_seals_actual_relative_bytes_without_invented_run_id \
  test_m06_dispatch_resolver.M06DispatchResolverTests.test_future_finished_candidate_is_not_admitted -v
```

The original-owner synthetic test uses the actual clock and fixed 2026 HK
calendar; a non-session/unsupported date is explicitly a skip, never evidence
of a current natural run. It passed without skips in the cloud on 2026-10-13.

3. Historical D12→13 originals: read-only validate dispatcher→lane→panel and
   native pool receipt/hash chain, then use independent candidate snapshot roots
   if sealing is part of the authorized Mac acceptance. Seal completion must be
   the real current completion; never backdate it. Confirm selected method is
   EXISTING_VERIFIED_POOL and original cold reader accepts the exact 100 rows.
   The historical D execution deadline has passed: do not invoke daily owner or
   claim a newly successful historical execution by changing its clock/deadline.
4. Retain all three false switches in the separate disabled template. Real root,
   executable/venv pins remain locally resolved placeholders. The CLI supports
   both the existing nested `daily` object and a flat daily object.
5. Activation is a separate production decision after Mac acceptance. Setting
   these switches true arms owner execution when its window/input gates pass;
   it is not read-only monitoring. Today's absent directory before close remains
   ordinary WAITING. Future natural completion still needs its own real evidence.

### D13 disabled-configuration acceptance (no activation)

For 2026-10-13, call the read-only original-calendar mapping
`calendar_day('20261013', evening=True)` and require scheduled/signal `20261013`,
target `20261014`, FULL_TRADING_DAY. In the local disabled opt-in draft verify:
full/half windows explicitly 17:30–18:30 Hong Kong; complete-chain budget 1200s;
per-process timeout 600s; target-day compatibility cutoff 09:00; UUID discovery
and exact receipt locator remain mutually exclusive; existing verified venv
launch/realpath identities and nonoverlapping original/snapshot/delivery/output/
bundle/ledger roots are exact. All three enabled switches must remain false.

Do not reuse the D12 delivery as D13, create an admission time in advance, or
change an existing frozen delivery to update its identity. D13 dispatcher/lane,
panel and master must independently arrive with exact D13 identities. If a later
authorized preflight seals them, record its actual completion time. When future
activation is separately approved, the runtime must derive admission from that
actual tick and retain D13 18:30 as execution_deadline and D14 09:00 only as
owner_contract_cutoff. At any tick with fewer than 1200 seconds left, no launch.
Until that approval, no enabled tick or launchd installation is part of this task.

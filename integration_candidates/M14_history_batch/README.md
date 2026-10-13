# M14 exact-gap bounded history collection

## What is ready

This capture-only candidate extends the fixed c52aca canary without changing that helper, the original owner, existing panels, page binding, strategy calculator, eligibility, PIT, or trading. It prepares the actual original 690-member pool and its 2,574 absent prior60 row keys, reuses all three successful canary responses byte-for-byte, and requests only the other missing-key codes. The expected new-request count is 687. The original per-code request is category 4 / market 71 / start 0 / count 120 on the same pinned endpoint, one connection, at least one second between starts, no retries or alternate source.

Do not apply the optional repaired-owner bridge from the previous package for this dataset. The real cross-source volume mismatch means these captures cannot be inserted into the original mixed-source panel. `repair_ready` stays false even if all responses are captured. A separate explicit single-source full-window research adapter is being developed; it is not part of this capture delivery and must not be implied by its success.

## Original evidence and source

- Inherits original M14 branch `dev/m14-github-handoff-20261011` at c52aca63e7aac5a1f450bd5d1e11ae805fe0cb31; new files only under this candidate directory. No P0/V4 files change.
- Reuses `integration_candidates/M14_history_recovery/capture/v5_shadow/rebound_history_capture.py` at c52aca, SHA-256 `e1a5fc5dba23dd10c727f002848b38e6d688b98316c99480bbef95fd97c66312`.
- Original runtime source: Mac local HEAD 884548fea0a0056483e8175564eaee015a964023. That commit was not resolved in the connected GitHub repository; no substitute GitHub identity is claimed. The exact six Mac-reported runtime source hashes matched the previously verified c7b/386d source bytes. Owner SHA-256 is `dc1b68715ba38a97a1df029a1934dab58b84b7f7486cb60b2a75a4d71491aa15`.
- Original collector is `vendor/rebound_repair_baseline/hk_daily_supplement.py`, SHA-256 `fa7dcbce4ee026b0a02c47220820d0407af183553d3304afcc5db425dce33cbd`; original raw validator `src/v5_shadow/rebound_raw_repair.py`, SHA-256 `0c6236be65fb52c78b04c124dad90b0d5413c41d78e00bc00d73f1706e1985cc`.
- Existing canary result bytes must hash to `4c310bf63f0941b8dc022dcef276d250bce62db98fb0176c7a842a6e4a700938`. It captured three 120-bar responses on 2026-10-13 at 17:58:16–17 UTC. Ten of eleven missing keys returned; HK.03469/20261012 did not. That successful partial response is reused, never queried again here.
- Calendar is read by unchanged original `rebound_panel_repair._history_window`. For signal 20261013, prior60 is 20260720–20261012 and previous5 is 20261006/07/08/09/12. Calendar SHA-256 `9e2638b69e25495478cecb6ed551713178fcb989a63ebb4ecfd59689615f0acb`.

No real source response, private path, member file, or data artifact is included in this GitHub delivery. The scalar Mac results below are an attributed summary, not uploaded raw evidence.

## Mac execution

Use existing approved Python environments. `$PY_M14` must be the original owner environment with its existing pandas/Parquet dependency; `$PY_FUTU` is the existing pytdx 1.72 environment. No install or credential step is required.

Bind these variables to already verified local paths:

- `CAND`: this candidate directory from the fixed delivery commit.
- `M14_CAPTURE_HELPER`: the unchanged c52aca helper file identified above.
- `M14_BASELINE_ROOT`: original actual884548 V5 root, not the optional changed owner runtime.
- `M14_API_CONFIG`: existing deployed JSON source-API config containing the original `m14_rebound_binding` and four-reference identity.
- `HK02_ASSET_ROOT`: actual original hk_0_2 asset root selected by the saved owner's panel request.
- `CANARY_RESULT`: actual canary `result.json` with the above SHA and adjacent plan/receipt files.
- `RUN_PARENT`: existing authorized scratch directory outside every original source, owner-results, asset and canary directory. `preparation`, `plan`, `capture` below must be new leaf directories. Keep them private and preserve them after interruptions.

Run the bounded offline tests first. The test files accept the two source locations explicitly; they do not depend on cloud filesystem paths.

```sh
export PYTHONDONTWRITEBYTECODE=1 M14_CAPTURE_HELPER M14_BASELINE_ROOT
"$PY_FUTU" -m unittest discover -s "$CAND/batch/tests" -v
"$PY_M14" -m unittest discover -s "$CAND/preparation/tests" -v
```

Prepare from actual original saved-owner and panel bytes, offline:

```sh
"$PY_M14" "$CAND/preparation/prepare_history_batch.py" \
  --capture-helper "$M14_CAPTURE_HELPER" --v5-root "$M14_BASELINE_ROOT" \
  --source-api-config "$M14_API_CONFIG" --hk02-asset-root "$HK02_ASSET_ROOT" \
  --canary-result "$CANARY_RESULT" \
  --canary-result-sha256 4c310bf63f0941b8dc022dcef276d250bce62db98fb0176c7a842a6e4a700938 \
  --target-date 20261014 --signal-date 20261013 \
  --expected-members 690 --expected-missing-keys 2574 \
  --output-dir "$RUN_PARENT/preparation"

"$PY_FUTU" "$CAND/batch/rebound_history_batch.py" plan \
  --baseline-root "$M14_BASELINE_ROOT" --capture-helper "$M14_CAPTURE_HELPER" \
  --task "$RUN_PARENT/preparation/task.json" \
  --context-file "$RUN_PARENT/preparation/context.json" \
  --output-dir "$RUN_PARENT/plan"
```

Preparation reads the original owner through `read_rebound_owner`, verifies its three saved hashes/marker/identity, reads the exact panel columns without modifying it, derives absence from the original calendar rather than the most recent available rows, and verifies the three original canary receipts. Missing rows and invalid cells are not interchangeable. A pool/date/hash/count mismatch aborts rather than replacing the expected values. `preparation.json` must show member_count 690, missing_key_count 2574, initial_reuse_count 3, new_query_count 687. Check the printed plan SHA and keep its raw bytes. Preparation validity is two hours from the actual new preparation time; do not edit it to revive expired work.

Execute the authorized one-round capture using the plan's exact raw SHA:

```sh
PLAN_SHA=$("$PY_FUTU" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$RUN_PARENT/plan/plan.json")
"$PY_FUTU" "$CAND/batch/rebound_history_batch.py" capture \
  --baseline-root "$M14_BASELINE_ROOT" --capture-helper "$M14_CAPTURE_HELPER" \
  --context-file "$RUN_PARENT/preparation/context.json" \
  --plan "$RUN_PARENT/plan/plan.json" --plan-sha256 "$PLAN_SHA" \
  --output-dir "$RUN_PARENT/capture" --max-calls 687 --max-seconds 900
```

One connection only. A query error/invalid response stops that round. A 900-second hard deadline can leave the current attempt UNKNOWN_UNCERTAIN; it is not repeated. All complete receipts already committed to the journal remain available. A code with a response, failed attempt or uncertain attempt is never automatically requested again. Do not create a new output directory to evade an earlier attempt. Report partial/failed results before deciding to invoke another bounded round for only still-unattempted codes.

An independent read-only audit selects no connector:

```sh
"$PY_FUTU" "$CAND/batch/rebound_history_batch.py" resume \
  --baseline-root "$M14_BASELINE_ROOT" --capture-helper "$M14_CAPTURE_HELPER" \
  --context-file "$RUN_PARENT/preparation/context.json" \
  --plan "$RUN_PARENT/plan/plan.json" --plan-sha256 "$PLAN_SHA" \
  --output-dir "$RUN_PARENT/capture"
```

Return the plan/result/checkpoint hashes, connection/attempt counts, whole-response counts, actual capture interval, remaining/failed/uncertain code counts, exact missing-key count, and protected-source before/after hashes. Actual provider rows remain on the Mac. `CAPTURED` describes source receipts only; `exact_keys_present` is separate. Missing/halted/invalid rows are left unresolved, never invented or zero-filled.

See `batch/README.md` for exact JSON schemas and the crash journal behavior. A process killed between a file write and its checkpoint can leave an orphan; the next audit safely refuses networking instead of guessing or rewriting it.

## Known source-comparability boundary

Mac's read-only comparison found signal-day OHLC agreement but different native trade values: HK.00001 old 3,498,184 versus PyTDX 34,982; HK.02825 10,000 versus 100; HK.03469 200 versus 2. HK.00001 disproves exact blanket multiplication by 100; historical 76/117 trade comparisons were already equal, consistent with mixed sources. Original manifest contract is `tdx_vipdoc_71_day+verified_zero_trade_repairs`, whereas new SDK quantity units, adjustment and finality are unproven. Three non-target old HK.03469 response dates have invalid OHLC and must remain in the unaltered captured response. The existing decoder can decode the ten returned requested keys but rejects the complete eleven-key requirement with RAW_REPAIR_EXACT_KEYS_MISSING. None of that proves source equivalence or formal authorization.

Collection is therefore usable provenance for a later explicitly labeled single-source research window. It is not a unit conversion, old-panel repair witness, owner verification, source-finality proof or eligibility pass. Real acquisition timestamps must stay real; the old pre-capture cutoff cannot certify newly acquired rows.

## Verification and attribution

- Packaged batch tests: 28 passed, including original unchanged raw `_record` validator and the preparation-to-batch schema integration, all fake network responses.
- Packaged preparation tests: 8 passed, exact pool/calendar/duplicates/canonical hashes/expiry/output-isolation.
- Actual original calendar function: passed offline with the SHA/window recorded above.
- Real Parquet preparation, real 687-code batch collection and resulting raw comparisons: NOT_RUN in cloud; Mac execution required. No dependency installation, real owner calculation or provider network occurred during development.
- Original collector/decoder/owner/calendar contributions are preserved; the M14 original saved-page work and prior runtime remain separately attributed in previous candidate handoffs. This delivery adds scheduling-side exact-gap preparation, bounded checkpointed capture and isolated tests only.

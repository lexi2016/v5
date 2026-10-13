# M14 independent same-source PyTDX window candidate

Status: offline implementation candidate. No real Parquet preparation, Python 3.14 owner run, Mac execution, publication, network collection, or formal qualification has been performed by this delivery.

## Apply to a complete isolated V5 runtime only

Two runtime files:

- Replace `src/v5_shadow/rebound_owner.py` only when its preimage SHA256 is `dc1b68715ba38a97a1df029a1934dab58b84b7f7486cb60b2a75a4d71491aa15`. After: `ab4cea7668300c8eecb5678710c1e862d73bdfc7f45d1b9aa03339bac0c4b6ab`.
- Add the previously absent `src/v5_shadow/rebound_pytdx_window.py`. SHA256 `d50b6c643b17c36bfe9677d8a3344b9e83c31dd4a50c1b2019a1c47207760d7c`.

Add standalone offline entry point `preparation/prepare_pytdx_window.py` from this package, SHA256 `00145e9214f94b926651e243d1843a0fa0e9da818dcc60c59913af1314c55f87`.

Do not overwrite a differently patched owner, including an owner with an optional native-repair bridge. This full candidate is based on the exact original owner preimage. It preserves the old request route, old reference reader, capsule verification, selected-role checks, owner subprocess isolation, and final CANNOT_CONFIRM downgrade. Its one guard change permits only O_DIRECTORY traversal of ancestors of files already listed in the original resources allowlist. It does not permit additional files or any writes/network/processes in the guarded worker.

Unchanged required source pins:

- `src/v5_shadow/rebound_raw_repair.py`: `0c6236be65fb52c78b04c124dad90b0d5413c41d78e00bc00d73f1706e1985cc`
- `vendor/rebound_repair_baseline/hk_daily_supplement.py`: `fa7dcbce4ee026b0a02c47220820d0407af183553d3304afcc5db425dce33cbd`
- `vendor/rebound_supplement/workspace_plan.py`: `29c47c3836f0b26a9106626a990f03cae47c2ac22f2b4ca10be68c916c75f897`
- Batch helper: `4d51d842839d38abd906e4294ff801a9e4d38824dd0b899e62c1f12f58e804dd`
- Capture helper: `e1a5fc5dba23dd10c727f002848b38e6d688b98316c99480bbef95fd97c66312`

## Exact offline preparation command

Use the existing environment's Python with pandas and pyarrow. Do not install dependencies to satisfy this candidate. BASELINE must be the complete isolated V5 runtime after the two-file application. PACKAGE, BATCH_HELPER, CAPTURE_HELPER, PLAN, PLAN_SHA, CONTEXT, CAPTURE_DIR and OUTPUT are explicit existing workflow paths/verified identities. OUTPUT must be a previously absent directory, separate from code, original assets and the batch journal.

```sh
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" "$PACKAGE/preparation/prepare_pytdx_window.py" \
  --baseline-root "$BASELINE" \
  --batch-helper "$BATCH_HELPER" \
  --capture-helper "$CAPTURE_HELPER" \
  --plan "$PLAN" --plan-sha256 "$PLAN_SHA" \
  --context-file "$CONTEXT" \
  --capture-dir "$CAPTURE_DIR" \
  --output-dir "$OUTPUT"
```

If the original saved request's input_root is no longer present, supply the explicitly verified existing root containing the original three master files:

```sh
# Add this argument to the same command; paths and original SHA values do not change.
--original-input-root "$EXPLICIT_ORIGINAL_MASTER_ROOT"
```

There is no guessed asset-root fallback. Parent pointer/manifest/panel and original artifact/manifest/receipt paths come from the batch context's six SHA-checked files. The master uses exactly its original three relative paths and three SHA values. The existing signal-date master supplies names only; it does not prove target-date eligibility.

The script runs the pinned batch `_validated`, `_Journal(create=False)`, `_state`, and full context recheck. It retains successful, failed and reused whole receipt objects, with their original canonical byte SHA. It holds the journal lock and rejects orphans, changed checkpoints, missing shards and changed source bytes. It does not invoke a connector, owner, capture, publication, or subprocess. An audit hook blocks network and process execution. It rechecks the task's original two-hour validity window immediately before output request publication. Expiration fails closed; the script never adjusts capture clocks or backdates cutoff.

Outputs:

- `$OUTPUT/input/`: the exact bounded new owner input closure
- `$OUTPUT/owner-request.json`: `v5.rebound_pytdx_window_owner_request.v1`
- `$OUTPUT/capture-audit.json`: pinned batch audit result
- `$OUTPUT/preparation-result.json`: preparation evidence and `owner_execution=NOT_RUN`

The script stops here. The Mac controller runs the existing owner separately after actual preparation verifies the full journal and source bundle. Do not report a prepared request as an owner result.

## Source and schema boundaries

The source contract is `pytdx_exhq_get_instrument_bars_category4_market71_sdk_decoded_native_v1`; the new panel is `v5.rebound_pytdx_sdk_window_asset.v1` and its manifest is `v5.rebound_pytdx_window_manifest.v1`. It is neither a v3 shared native-panel asset nor a native repair.

Every prior60 high and previous5-plus-signal trade comes from the same pinned `get_instrument_bars(category=4, market=71, start=0, count<=120)` interface. The original `_record` and `_decoder` are reused unchanged. SDK trade is retained with scale 1. Shares, currency, adjustment basis, provider finality and target membership are NOT_PROVEN. No multiplication by 100, zero fill, or prices/volumes from the mixed original panel are accepted.

The old signal panel supplies only the exact member set. All members survive. Failed/missing captures, missing exact history dates, malformed rows, duplicate dates and future rows retain a null signal row for the original calculator's pending result. Integrity, identity, hash, unsupported-source, clock and closure failures reject the bundle rather than silently weakening evidence.

The original pinned `read_rebound_screen` and its 80%/1.5 formulas are not changed or replaced. A fresh worker installs only a new explicit research input witness. The output keeps strict, near, pending, excluded and unresolved computations from the original function. The research projection corrects that legacy function's hardcoded native source/adjustment assertions, retains the untrusted original diagnostic separately, and remains CANNOT_CONFIRM.

The manifest includes actual capture start/finish, a newly observed prepared-at/cutoff after input/Parquet copies and SHA checks, exact native calendar identity, parent SHA values, canonical row SHA, every shard SHA/size, and a batch audit binding to the original four-value reference, parent binding, plan/context SHA, checkpoint head and complete receipt SHA list. This is preparation provenance, not provider/owner certification of data semantics.

Maximum closure: 7 role files + at most 23 SDK record shards + 2 generated routing files = 32. JSON/shard <=8 MiB, Parquet <=512 MiB, total private closure <=1 GiB. Missing any declared shard rejects the bundle. The routing file uses the new `assets/m14_pytdx_windows` namespace; no old native panel pointer is fabricated.

## Verification

Fresh test command:

```sh
M14_ORIGINAL_RUNTIME="$ORIGINAL_COMPLETE_V5" \
M14_WINDOW_RUNTIME="$ISOLATED_COMPLETE_V5_WITH_CANDIDATE" \
M14_BATCH_MODULE="$BATCH_HELPER" \
M14_CAPTURE_HELPER="$CAPTURE_HELPER" \
PYTHONDONTWRITEBYTECODE=1 "$TEST_PYTHON" -m unittest discover -s "$PACKAGE/tests" -v
```

Use the explicit environment overrides shown above for portable Mac/runtime paths. The shipped guard test resolves its allowlisted root from the actual imported raw-decoder module, so two separate complete original/candidate trees are supported. They only write under the package test directory. The integration test copies a disposable runtime under its own test directory; it never edits the supplied original runtime.

Observed: 33 tests passed using Python 3.12.14 / pandas 2.2.3. Coverage includes whole-receipt hashes, source/clock bounds, null member preservation, same-source value reconstruction, new manifest/request, private routing/file count, actual original guard in a subprocess (read only allowed resource, deny other files and writes), unchanged source/calculator boundaries, 80%/1.5 strict/near/excluded behavior, Hong Kong/UTC equivalent cutoff, and full pinned synthetic capture journal -> preparation -> request/metadata flow.

The last flow uses a synthetic pandas Parquet I/O seam. Actual pyarrow Parquet I/O: NOT_RUN. Actual 3.14 fresh owner subprocess and actual 690-member result: NOT_RUN. No dependency installation, V4 change, Mac use, collection, trading or preview publication occurred in cloud verification. This fixed candidate is published only to the original private M14 development branch.


## Application, unchanged old references and Mac handoff

This package serially inherits commit `02193d90221b24f59b0678fc3035eaa128791259`, which delivered capture independently. Only this candidate directory is added to GitHub. The exact two runtime before/after images are in `verification.json`; all other source is reused from the existing complete V5 runtime. No shared P0 file is directly changed. The original 884548 Mac owner-source SHA matches the preimage above; that local Git commit itself is not claimed to be a GitHub-resolvable source capsule.

Use an isolated existing complete runtime, and verify then apply only the two files:

```sh
"$PY_M14" "$PACKAGE/apply_candidate.py" --target "$BASELINE" --check-only
"$PY_M14" "$PACKAGE/apply_candidate.py" --target "$BASELINE"
```

A different preimage aborts before any replacement. Repeating the application accepts exact after-images and changes zero files. It does not fetch dependencies, edit configuration, bind a new saved result or start a service.

After the actual full journal is available, use the offline preparation command above with `$PYTHON` set to the existing `$PY_M14`. The resulting request is the explicit new source route. Its actual input bundle must validate before the separate original owner run:

```sh
PYTHONDONTWRITEBYTECODE=1 "$PY_M14" "$BASELINE/src/v5_shadow/rebound_owner.py" \
  --request "$OUTPUT/owner-request.json" --output-root "$NEW_SAVED_M14_ROOT"
```

`NEW_SAVED_M14_ROOT` is a new dedicated existing-workflow output location, separate from the previous owner-results root and all inputs. Inspect computation status, all five group counts and missing reasons, exact member accounting, source/cutoff disclosure and unchanged safety flags; a process exit code alone is not evidence of a result. Record the new run_id/artifact/manifest/receipt reference and run the original reader before changing a page binding. Preserve the old target14 and M18 target12 references. Do not insert this new target14 reference into the older target12 manager run.

The saved-page API reading this new request needs these same two owner/adapter files in its isolated runtime. Its existing read-only M14 route/client/page and four-ref binding remain unchanged. The updated reader accepts old original request/reference shapes; it does not relabel them or search historical roots. Update only the explicit saved M14 binding after Mac validation. No front-end or manager-generation code is included or needed in this candidate.

Packaged verification:

- 33 new tests passed again from the packaged files with two complete, separately located original/candidate runtimes. This includes the corrected test-only root selection; production SHA values above are unchanged.
- Original `test_rebound_owner.py`: 28 passed, 1 skipped because the real original-owner case requires Python 3.14+ locked runtime and explicit test opt-in. Old reference readback, three-hash tamper checks, marker, no-symlink boundaries and legacy request paths remain covered.
- A separate old stored-supplement suite attempted 7 fixture setups in the minimal 3.12 venv and failed before product execution because pandas was absent there. This is ENVIRONMENT_BLOCKED; no old fixture or dependency was modified. Those real Parquet/product cases are NOT_RUN, not claimed passed.
- Exact apply/check/idempotence verification is recorded in evidence. Real 690-result owner and preview binding remain NOT_RUN in cloud.

Original collector/decoder, calendar, strategy and saved-result reader contributions are retained. This delivery adds the explicit same-source research adapter, its minimal owner route and the offline audited batch-to-window preparation; original M14 Chat work and earlier page/capture deliveries remain separately attributed in their original handoffs.

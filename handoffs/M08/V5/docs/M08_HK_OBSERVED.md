# M08 saved-owner observations

This is an additive candidate after the M06 delivery. It copies already-saved
HK SelectionStore results and reads them independently. It does not reconstruct
missing ordinary-stage inputs, rerun Stage8, collect quotes, or attest natural
execution/PIT safety. No existing producer, M06 adapter, frozen source, source
manifest, shared API, UI, scheduler, or ledger file is changed.

## Fixed inventory and evidence boundary

Inventory: `lexi2016/v5@7aaf58b07daa70f3efb2554b82ee8195cb7a1185`,
`handoffs/M08/feedback/mac-historical-materials-20261012/report.json`.
It lists 10 saved runs across eight stages for 20261012. Each `stage_runs` entry
contains `stage`, `run_id`, and `trio[name]` with `relative_path`, raw `sha256`,
and `bytes`. Its PASS/status labels are descriptive, not accepted as proof.
This independent delta is based on
`4053d4e89101b8d47861f48813686234dc063ba9`; its existing Mac feedback is preserved.

The inventory lacks the stage manifest/receipt **canonical** hashes. The
read-only `prepare` operation first verifies the pinned raw bytes and then the
unchanged pinned `SelectionStore._verify_run`, returning a complete reference:

- `schema_version=v5.hk_stage_observed_source.v1`
- `target_date`, `stage_id`, `market=HK_CONNECT`, `run_id`
- Original `artifact_sha256`, `manifest_sha256`, `receipt_sha256`
- `trio`: the three exact inventory-relative paths, raw SHA-256 values and sizes

Original CSV SHA hashes raw bytes. Original manifest/receipt SHA hashes
canonical JSON, excluding formatting and the trailing newline. Both identities
are retained. CSV may contain only the legacy projection; the full original
envelope is read from the manifest. Neither JSON nor CSV is reserialized during
copying. No real historical payload or absolute source path is included in this
code or its fixtures.

## Storage and cold-read contract

Initialize a distinct empty private directory. Its marker is
`.v5-hk-stage-observed-root` with `v5.hk-stage-observed-root.v1\n`.
Each committed import has:

```
imports/<import_sha256>/
  import.json
  receipt.json
  owner/selection_runs/<date>/HK_CONNECT_SELECTION_<stage>/<run>/
    artifact.csv
    manifest.json
    receipt.json
```

`import.json` binds the exact source reference, the pinned original source
closure, this importer/reader/API implementation, and the reused public path
redactor/shared publication helpers. The original producer identity function
is unchanged. `receipt.json` records actual `imported_at` and COMMITTED state.
Repeated identical imports reuse these bytes and timestamp. Changed metadata
can produce a distinct import for the same original run, without replacing the
old observation.

The public/cold-read reference pins `import_sha256`, `import_receipt_sha256`,
market, date, stage, and run. Cold reads verify both sidecars and all trio byte
and canonical hashes, then call the original `_verify_run` with the exact run.
They never consult latest pointers or the old source root. Original source
paths inside private envelope evidence remain unchanged text and are never
opened. Invalid safety/identity/status metadata is rejected in addition to the
original verifier's checks. Boolean safety values must be literal false.

Publication happens only after the copied trio verifies. A failed copy leaves
an unpublished `pending-*` directory for explicit inspection; committed imports
are not overwritten or removed. Source/destination overlap, unmarked roots,
symlinks, non-regular inputs, wrong sizes/hashes and malformed JSON are rejected.
No automatic cleanup or latest-success pointer is added.

## Python interfaces and CLI

New interfaces:
- `prepare_hk_stage_observed_reference(source_root, inventory_entry, *, target_date)`
- `import_hk_stage_observed(source_root, recorded_root, expected_original_reference)`
- `read_hk_stage_observed(recorded_root, exact_import_reference)`
- `publish_hk_stage_observed_response(config, recorded_root, exact_import_reference, *, expected_generation)`

Example operator flow, substituting approved absolute local paths and the exact
inventory run. These commands have not been executed against the Mac materials:

```sh
set -eu
# Run from the module checkout: handoffs/M08
export PYTHONPATH=V5/src
python -B -m v5_shadow.hk_stage_observed init --root "$RECORDED_ROOT"
python -B -m v5_shadow.hk_stage_observed prepare --source-root "$SOURCE_ROOT" --inventory "$INVENTORY_JSON" --run-id "$EXACT_RUN" > "$EXPECTED_REFERENCE_JSON"
python -B -m v5_shadow.hk_stage_observed import --source-root "$SOURCE_ROOT" --root "$RECORDED_ROOT" --reference "$EXPECTED_REFERENCE_JSON" > "$IMPORTED_REFERENCE_JSON"
python -B -m v5_shadow.hk_stage_observed read --root "$RECORDED_ROOT" --reference "$IMPORTED_REFERENCE_JSON"
python -B -m v5_shadow.hk_stage_observed_api --config "$API_CONFIG_JSON" --root "$RECORDED_ROOT" --reference "$IMPORTED_REFERENCE_JSON" --expected-generation NONE
```

`import` prints only the reusable exact reference. `read` prints a small
classification/status/row-count summary. Explicit `--include-artifact` prints
the private original envelope; keep that output private and do not upload it.
All CLI file reads use bounded regular-file/no-follow checks.

API config uses the unchanged `v5.module_api.v1` contract, module `hk_stage`, an
independent marked response root, and route `/api/v5/hk-stage-observed`.
`NONE` is only the first publication; subsequent calls require the current
**API generation** SHA, distinct from the import SHA. Existing
`v5_shadow.module_api` serves the result; there is no new server.

GET requires `date`, `stage`, `run_id`, and `import_sha256`. It reads immutable
published responses and cannot call importers, readers, producers or collectors.
Existing compare-and-swap generation activation provides response rollback.
It does not by itself roll back code, UI, or private copied imports.

## Public meaning

- `data_kind=OWNER_RESULT`, `evidence_mode=HISTORICAL`, `qualification=OBSERVED_ONLY`
- `natural_verified`, `pit_verified`, `formal_admission`, `raw_input_verified`,
  `computation_replayed`, `market_data_authenticity_verified` are false
- Production/BUY-gate/order flags remain false
- `captured_at=null`; a historical capture time is never guessed
- API `generated_at` is the recorded import time, not historical market capture
- `source_input_sha256` identifies the observed import manifest, not unseen raw quotes
- Original selection status, rows, formulas, coverage and diagnostics are retained
- Public paths are redacted; the independently pinned original private bytes remain unchanged
- Stage8 is `HK_STAGE8_SEPARATE`, outside the seven-stage M10 grouping

Original source-mode labels may describe a historical natural route; they do
not override these explicit observation limits. Saved output verification does
not prove the full original input set or enable recomputation.

## Verification

Only synthetic original-owner trios in temporary cloud directories are used.
No actual Mac data, provider access or broad suite rerun is part of this change.
The targeted tests cover eight-stage exact copies, PARTIAL/empty/error retention,
rehashed metadata attacks, byte/canonical hash distinction, source removal,
latest-pointer independence, immutable retries, failed copies, CLI boundaries,
HTTP cold reads and explicit observation-only classification.

```sh
PYTHONPATH=V5/src:V5/tests python -B -m unittest test_hk_stage_observed -v
PYTHONPATH=V5/src:V5/tests python -B -m unittest test_hk_stage_observed.HKObservedTests.test_cli_prepare_import_read_and_publish_without_payload_stdout -v
```

Initial RED was 16 missing-module failures. Further negative regressions were
observed failing before fixes. Final targeted counts and raw logs accompany the
handoff. Cloud Python is 3.12.14; the declared >=3.14 Mac acceptance environment
and the fixed real inventory remain separate validation steps.

Final cloud result: **21/21 PASS**, exit 0. See
`V5/tests/logs/M08_OBSERVED/` for the raw targeted logs, review, and runtime
receipt. The existing aggregate acceptance command includes this new test file
for future use; the prior 90 or combined 124 tests were not rerun in this delta.
The CLI path is included in the 21-test run. Patch roundtrip/source SHA records
are in `delivery/M08_OBSERVED_20261012/`. This is a complete saved-output adapter
candidate, not complete M08 real-input/product acceptance.

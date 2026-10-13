# M12 explicit native saved import candidate

## Scope and prerequisite

This adds only `V5/src/v5_shadow/m12_native_import.py` and its test file. Apply the two-file `SOURCE_CLOSURE.json` overlay to the existing M12 runtime previously Mac-verified in feedback commit `57523dd2c0e254c05b5e4aa8f9a069290f336c4c`. Keep the currently deployed composition and all M04/M06/M11 changes. Do not deploy the whole P0 HEAD or enable a daily producer. No frontend/shared file or original M12 implementation is changed.

The adapter uses the unchanged original store for new immutable JSON wrappers, the original native evidence checker, and the deployed saved reader's cold subprocess. `verify_runtime()` checks the existing source pins before loading original reader/store code. The cold child has an explicit verified repository cwd, without changing the parent cwd.

The observed source structure is fixed at [23b49cc native contract](https://github.com/lexi2016/v5/blob/23b49cc88dc4183519f00c9e3760e437b2476090/handoffs/P0/m12-native-schema-20261012/native-20261012-contract.json). That sanitized contract is not reconstructable source evidence. Never generate a native manifest or receipt from it.

## Exact selected Mac source

- Date: `20261012`
- Run: `rcv1-20261012-BV1eKpR6TEAN-a802b45429651e71`
- Native manifest SHA256: `cb718159ee2a402ffba6541e7c54431d29f4d35303852fefd8c660a56bd908bc`
- Native receipt SHA256: `cbf5e82a0f89c64412368e0cec802e2318c4e5328f77f19b227680aaa2c4fd6e`
- Original 15 artifact refs: 46,704,778 bytes, plus 21,974-byte manifest and 2,007-byte receipt
- Expected preserved source state: `ASR_REVIEW_REQUIRED`, 54 segments, `VIDEO_GAP_AUDIT_EMPTY`, `stockdict_status=NOT_AVAILABLE`, `transcript_reviewed=false`

Only the actual authorized Mac files may supply these bytes. No original media, transcript, manifest, receipt, private configuration or private path is included in this handoff. Keep the real import request, binding and import artifacts local to the Mac.

## Local request and invocation

Create a private JSON request with exactly these keys:

- `source_root`: existing absolute native data root containing `review/20261012/runs/RUN/manifest.json`, `receipt.json`, and the original media/audio/artifact refs
- `destination_root`: new, nonexistent, independent absolute V5 import container, outside the source; its parent must already exist
- `trade_date`, `run_id`, `owner_manifest_sha256`, `owner_receipt_sha256`: the exact selected values above
- `data_kind`: `RECORDED_INPUT_REPLAY` for this historical native import; tests use `SYNTHETIC`
- `python_executable`: existing absolute Mac interpreter

Do not use symlink aliases for the roots. Resolve authorized root locations locally before invocation. From the verified candidate repository, with existing dependencies only:

    "$EXISTING_PYTHON" -I -B "$V5_REPO/V5/src/v5_shadow/m12_native_import.py" --request "$PRIVATE_REQUEST_JSON"

The CLI emits one local JSON result. A successful result is `IMPORTED_SAVED_NATIVE` and includes the binding whose `private_root` is the completed destination's `data` subdirectory. An exact repeat returns `REUSED_SAVED_NATIVE` without writing or changing `imported_at`. Failure exits 1 with `CANNOT_CONFIRM` and no binding. Preserve interrupted destination evidence; do not overwrite it or automatically resume it. A deliberate retry needs a new explicitly chosen empty destination.

Only after success, add the returned binding as the source_bundle configuration's `m12_video_fupan_binding`, preserving every other binding and route. That configuration change and any service restart are separate Mac-controlled steps, not actions performed by this adapter. The existing default-page M12 entry should then show the bound saved transcript and segments through the existing endpoint. A wrong requested date remains WAITING. No binding means WAITING; it is not a real-data-page acceptance.

## Validation and publication boundary

The original manifest and receipt must have matching schema/date/run/target-date and original receipt-to-manifest SHA. The three original owner and receipt safety flags must already exist and be exactly false; they are never added to source evidence. Every native artifact must have the pinned SHA; a declared size must also match. Only relative artifact paths are traversed. Any `source_path` inside original metadata stays opaque and byte-preserved, and is never followed.

A fresh destination is exclusively reserved. Files are streamed into `staging` as ordinary independent copies with exact SHA/size checks, bounded to 256 MiB/file and 512 MiB total. The remaining total budget is checked before reading each artifact. Original metadata and source artifacts are checked again after staging. The original cold saved reader validates the staged wrapper. A complete stage is renamed to `data`; an independent `import.json` commits the import receipt; the final cold read must pass before a binding is returned. Copy/rename/commit failure never returns a binding; an uncommitted destination is not reused. Atomic rename is not a claim of power-loss durability or an OS security sandbox.

The new wrapper says `NATIVE_SAVED_IMPORT`; the separate import receipt uses the dedicated `v5.m12_native_import.v1.receipt` schema. Both retain original manifest/receipt SHA and record the actual independent import UTC time. They do not invent a collection time, owner attempt, owner receipt or ASR execution. New import flags are scoped to this import: producer/network/ASR false, natural_verified/review_completed false, and all production/trading flags false. Original historical fields remain unchanged inside original bytes. No `current.json` or `latest_success.json` selector is created or advanced.

## Verification and Mac acceptance

Fresh cloud verification against P0 dependencies at `acf8d23f9c191e4cb2da5737ca715002e83648c2`: 81 tests and 33 pytest subtests passed. This comprises the prior 59 tests/21 subtests plus 22 native-import tests/12 subtests. A separate stdlib run passed all 22 native-import tests. Fixtures are synthetic; fixture-owner subprocess sockets are blocked. Original runtime pins remain unchanged. Independent review's cumulative read-budget finding was reproduced RED and fixed GREEN; post-rename commit failure was also covered.

Run the following on the existing Mac test environment before applying the two-file overlay:

    PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:V5/src:<existing-pytest-site> <existing-python> -B -m pytest -q -p no:cacheprovider V5/tests/test_m12_integration.py V5/tests/test_m12_native_import.py tests/m12/test_video_fupan_default_chain.py V5/tests/test_p0_main_registry.py V5/tests/test_module_api.py V5/tests/test_m04_readonly_api.py

Then run only the selected real native import locally, compare the original 17 copied file SHA/size values and source before/after bytes, retain `ASR_REVIEW_REQUIRED` and `NOT_AVAILABLE`, and cold-read the returned binding through the existing API. Verify wrong-date WAITING, immutable repeat, and the real reachable M12 view. Do not upload private artifacts or raw diagnostics; report sanitized counts/status/digests.

Mac native-copy/binding/deployment and actual saved-content page acceptance are NOT_RUN for this candidate. Provider/download/new ASR execution are NOT_RUN and outside this import. Full release suite is not claimed passed; no frontend file changes or new DOM/build claim is made here.

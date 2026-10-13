# M02 saved-source read and status-only publication

Base: `e200cafbece378343d04a654c9819746357ae03e` on the existing
`dev/v5-main-integration-20261012` branch. The full inherited source tree,
including all 65 pinned M02 owner members, remains part of the delivery.
Only two executable files change; the original M02 owner is unchanged from
`ce6cddce1ef52d63241f0d8192b6adcc118ea750`.

## Supported entry point

Use **only** `v5_shadow.source_bundle.publish_m02_saved_binding` for this
partial update. Do not send this task through `run_source_bundle`, `run_config`,
or `main_runtime source-bundle`: their generic four-slot attempt resets
unrequested rows, and its owner result is not this public-safe projection.
Do not call the low-level publisher with a manually assembled success.

```python
from v5_shadow.source_bundle import publish_m02_saved_binding

outcome = publish_m02_saved_binding(
    {
        'action': 'read',
        'private_root': local_existing_m02_private_root,
        'target_date': local_expected_target_date,
        'receipt_hash': independently_recorded_receipt_hash,
    },
    current_complete_source_bundle_module_config,
    expected_generation=freshly_read_source_bundle_generation,
    data_kind='RECORDED_INPUT_REPLAY',
)
```

The four request fields are exact. The receipt hash must be the independently
recorded original M02 receipt hash for the already-validated target/run/signal;
do not discover and adopt a replacement receipt, current pointer, or another
run. The original `read_binding` verifies that external receipt anchor, disk
and source byte identities, private root, dates, immutable request, safety
flags and full recomputed binding. It still reads its three existing bound
sources and frozen assets; it does not build, collect, score, generate, or
rewrite the M02 product. Missing/invalid source or receipt never falls back
to `build_binding`. Existing omitted-action build behavior stays unchanged.

The new entry point:

1. Requires an existing source-bundle status and an exact generation SHA.
2. Reads that generation's immutable status object, avoiding a head A→B→A
   race. Rejects malformed/missing/duplicate rows and a data-kind mismatch.
3. Calls only the isolated M02 saved reader; no other owner is invoked.
4. Keeps the M01/M03/M05 rows exactly as saved, including nested products.
   Changes only the M02 row. Top-level data_kind stays unchanged and must
   equal the requested kind; `OWNER_RESULT` is not accepted here.
5. Publishes through existing `publish_source_result` and generation CAS.
   Existing route records and all 11 configured routes/bindings are retained.
   This CAS belongs to the source-bundle module root, not M02's receipt root,
   M18, or a live-model pointer. A conflict requires a fresh predecessor read
   and a new bounded call; never force or silently retry a stale merge.

`m02_saved_publication` records only bounded predecessor scalar provenance
and `M02_ONLY_SAVED_READ`. Its new observed time is the M02 update time, not
evidence that the other three rows ran again.

## Public-safe projection

The existing page can render the projected owner_result JSON unchanged.
`projection_schema=v5.m02.saved_public_view.v1` makes the reduction explicit.
It preserves original run/request/receipt identities, dates, verified source
statuses, member count, `SOURCE_IDENTITY_ONLY`, temporal `CANNOT_CONFIRM`,
PIT false, and all original false authority flags. It excludes private roots,
input file maps, panel/model/name paths, raw source identities and arbitrary
receipt extras. Unchecked receipt `purpose` is omitted; binding purpose is
verified by the original reader and preserved.

`identity_metadata_canonical_sha256` is a derived canonical-JSON digest of
each original source identity, not an original file SHA. The explicitly named
`original_saved_result_sha256` hashes the original full saved object. Original
receipt/binding hashes still refer to original objects, not the projected
view. No raw request, raw saved object, or source exception is published by
this helper. Read/projection failure leaves the previous publication active.

## Mac acceptance and narrow integration, separately authorized

Do not replace the mixed runtime tree. Before applying only the two bridge
files, compare their actual original raw SHA256 with these known baselines:

- `V5/src/v5_shadow/source_bundle_worker.py`:
  `782c523c96ce9494c616aac04cb02276e59ced55ff1814309c192e067ec171d7`
- `V5/src/v5_shadow/source_bundle.py`:
  `8a1730e25b45cc042abf20ab15f62e33af8f819cad2c9ec1bfc20fb4d4bc2f0e`

Stop on a mismatch and reconcile the actual overlay. Preserve module_api,
module_artifacts, original M02 owner/manifest, M01 guard, M06 dynamic reader,
all other owner files, configs, listeners and V4. The new Python caller and
its child must both resolve the intended verified bridge files. This delivery
does not install, restart or deploy anything.

Cloud verification already passed the following 18 focused tests, with zero
skips. The command is recorded for reproducibility; do not repeat this passed
suite on Mac for this handoff. Mac should run only the still-pending real
saved-reader/publication and page acceptance below:

```sh
PYTHONPATH=V5/src:V5/tests "$PYTHON" -B -W error::ResourceWarning -m unittest -v \
  test_source_bundle_m02_saved \
  test_source_bundle_publication_routes \
  test_source_bundle.SourceBundleTests.test_source_publication_is_readonly_and_separate_from_manager \
  test_source_bundle.SourceBundleTests.test_m05_missing_v192_and_permit_never_publish
```

The new tests use synthetic source identities through the original owner's
declared `_collect` unit seam, with real immutable persistence, original
read_binding reconstruction, file/hash/private-root checks and original
module publication. A guard proves no builder is called after fixture setup.
Transport is replaced only in publication unit tests by that tested reader
result. This is not a real three-source/Parquet integration claim and requires
no pyarrow installation. Mac real saved-reader/publication acceptance remains
a separate check. Do not repeat the prior model/materialization tests.

Before the real call, retain the current full status, the canonical three-row
bytes, all other source-route response identities and relevant file hashes.
Re-read the active source-bundle generation immediately before publishing.
Afterward, direct/proxied GET and the existing page must show the exact safe
M02 identities and unchanged M01/M03/M05 rows; compare the other route
semantics including M06, protected bytes and listener identities as before.
HTTP/page reads must not run owners. Failure/unknown status must not be
relabelled success or overwrite prior output. Keep real paths, requests,
receipts, input metadata and data local; do not upload them with feedback.

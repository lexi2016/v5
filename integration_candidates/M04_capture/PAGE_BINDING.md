# Existing read-only research-page binding

Use the existing independent ResearchView and its existing M04 lane bridge. No shared API/frontend mutation is included here. Binding/deployment remains a separate explicitly managed action.

## Original saved binding

Take `archive_binding` unchanged from the successful saved `resume` result. It is:

```json
{"root":"<absolute verified private archive root>","files":{"<relative original artifact>":"<sha256>","manifest.json":"<sha256>"}}
```

Keep **all** `files` entries, including raw pages, acquisition receipt, source/builder evidence, daily archive and its receipt. Do not reconstruct a three-file binding for this v2 archive. Do not use capture root as archive root, or mix the old 18-article binding into this fresh eight-article root. File hashes and archived manifest are unchanged.

## Existing launcher commands

With `PY` the existing CPython 3.13.12 executable and `APP` the complete fixed M04 package `launch.py`:

```sh
"$PY" -I -B "$APP" lane --research-date 20261014 < archive-binding.json > research-lane-20261014.json
"$PY" -I -B "$APP" lane < archive-binding.json > research-lane-latest.json
"$PY" -I -B "$APP" read < archive-binding.json > research-materials.json
```

These commands verify RELEASE and original saved source/owner/archive identities, then cold-read only. They do not call capture/build/import. EXACT never falls back. LATEST selects only the dates already bound in this root, not a global newest source. `read` exports complete raw materials and unchanged original article fields; `lane` additionally supplies the existing page's display projection.

## Existing public bridge field

```json
{"m04_research_lane_binding":{
  "package_root":"<absolute complete fixed M04 package root>",
  "package_manifest_sha256":"<SHA256 of that package RELEASE.json>",
  "archive_binding":{"root":"<unchanged successful binding root>","files":{}},
  "python_executable":"<existing CPython 3.13.12 executable>"
}}
```

`files:{}` above is a placeholder, not runnable: insert the entire successful binding. The existing bridge validates package manifest and all files before invoking the launcher. Existing GET routes are `/api/v5/research/lane?research_date=20261014` for EXACT and `/api/v5/research/lane` for LATEST. The page is the existing `?view=research` entry, not manager-workbench.

## Display safety without a new UI

Existing ResearchFeedCard displays `card.summary || card.evidence_sentence` in its summary region. Its full-original-text detail uses `body/body_text/content/text`, not summary. For cold-reader-verified `acquisition_v2.evidence_semantics.kind=ORIGINAL_BUILDER_SUMMARY` and `quote_status=NOT_A_SOURCE_QUOTE`, lane now adds:

- `summary`: `原owner派生摘要（非原文引句）：` plus the untouched original `evidence_sentence`
- `summary_display_only`: true

Every original article field remains unchanged. No summary is assigned to body_text. Literal/whitespace-bound articles retain their existing projection. The full original fields include the raw/decoded body hashes, fixed decoder provenance, issuer positions, title transformation and acquisition timestamps. Archive evidence and page display metadata are distinct; the page label is not written into the archive or counted as a source quote.

The current live capture yielded 21 raw items / 11 research items / **8 archive articles**: 1 literal, 4 whitespace-bound, 3 original owner summaries labelled nonquote. Full-source coverage remains bounded; natural/PIT/production flags remain false.

## Explicit historical + fresh independent roots

To preserve both the old 18 articles and the new eight, `archive_binding` for **lane only** can be this bounded descriptor:

```json
{"schema_version":"v5.m04_archive_bindings.v1","bindings":[
  {"root":"<original historical root>","files":{"<all historical binding entries>":"<original hashes>"}},
  {"root":"<original fresh eight-article root>","files":{"<all successful new binding entries>":"<original hashes>"}}
]}
```

Each child is an unchanged original `{root,files}` binding. Keep separate roots/manifests; never merge archives or write combined data. Single binding remains fully compatible. Maximum 16 roots; duplicate root, unknown descriptor fields and same archive date in different roots are rejected. Every root is cold-read and SHA-verified on every request, including roots not selected by EXACT. EXACT chooses only that verified date's unique root; missing date is NOT_MATERIALIZED. LATEST picks the greatest verified date regardless of descriptor order. Selected source_reference.archive_binding remains the original single-root binding. `available_archive_dates` lists verified dates; `archive_binding_diagnostics` preserves per-root out-of-scope errors. Historical unknown clocks and 53 out-of-scope errors stay unchanged. `read` remains per-single-binding; use it separately for each original archive.

The existing public bridge strictly accepted `{root,files}`. The complete candidate `page_bridge/research_workbench_readonly.py` changes **only validate_binding** to also permit this controlled descriptor; subprocess forwarding, routes, source verification and safety behavior remain unchanged. `bridge.patch` is the narrow diff. `BRIDGE_IDENTITY.json` binds the exact original d3c52b bridge and new candidate. No shared live code is modified by this package.

```sh
"$PY" -I -B "$PACKAGE/page_bridge/prepare_bridge.py" --source <verified-existing-bridge> --output <new-isolated-bridge-file>
"$PY" -I -B "$PACKAGE/page_bridge/prepare_binding.py" --existing-config <existing-source-config> --package "$PACKAGE" --python "$PY" --archive-binding <two-root-descriptor.json> --expected-manifest-sha256 <this-RELEASE-sha256> --output <new-isolated-config.json>
```

Both outputs must not already exist. Bridge preparation fails on preimage drift, rather than replacing unrelated changes. Config preparation verifies the exact package manifest and bytes, preserves all other fields/bindings, and changes only research routes/binding. It avoids the old workbench configure_binding.py's hardcoded earlier M04 pin. The unique publisher applies the isolated bridge/config using the existing deployment process only after old-date=18, new-date=8, latest=new-date, missing-date, nonquote labels and unrelated-route preservation checks. This package does not publish or modify M14.

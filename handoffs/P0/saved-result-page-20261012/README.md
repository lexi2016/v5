# V5 saved-run ordinary page

This increment connects an ordinary V5 page to the already-published, same-run
M18 result. It is not complete P0/P1–P5 acceptance or an 18-module deployment.

## Complete source and preserved base

Use the complete repository at this commit, not snippets or a ZIP. The existing
backend tree is retained. `frontend/` incorporates all 130 safe source/config/
lock/test files from fixed frontend base
`d94cfc86111dc33a76e651e15fb6668dcefa849c`, with the small changes listed in
`CHANGES.json` and four new frontend files. Unchanged files use the same Git
blobs. The four excluded old private-path tests remain excluded; no private
business fixtures are uploaded or fabricated.

Frontend base provenance:
https://github.com/lexi2016/v5/blob/d94cfc86111dc33a76e651e15fb6668dcefa849c/SOURCE_MANIFEST.json

The established Vue framework, dependencies, lockfile, dashboard styling,
`App.vue`, app shell, manager view and research view remain in the tree. Main
and manager entry points lazily select the saved-run view by default. Their
explicit `?view=legacy` entries retain the old reference components; those
components are not loaded and their workspace/job calls are not executed by
saved-run mode. The legacy reference is not claimed as integrated V5 business
acceptance. Daily research source remains unchanged and is not marked ready.

## What the ordinary page reads

- `/` and `/manager-selection/` render `SavedManagerResultView.vue`, with V5
  titles, exact run/target date, identity details, saved section counts, honest
  missing-module labels and one selected section at a time.
- Default run is the existing saved run
  `46596b03c2ab4e29b1219fd2e5eb698f`. `?run_id=<exact run>` or the run input
  selects an explicit run; unknown runs fail closed. There is no latest/live
  or date-substitution fallback.
- Descriptor READY means saved transport availability, not business completion.
  Actual values such as PARTIAL, CANNOT_CONFIRM, false, null, empty arrays and
  gaps are preserved. Empty stocks do not become a successful selection.
- The section selector includes actual saved fields; summary, gaps and materials
  have ordinary labels and counts. A page has at most 32 entries. Exact saved
  small entries are readable in the table and expandable in full. Oversized
  entries remain NOT_LOADED with original bytes/hash and the precise cap reason.
- New requests abort and suppress older responses. Page navigation carries the
  exact generation, section, opaque cursor and expected offset. The client
  verifies all six identity fields plus offline generation/profile/manifest.
  It never fetches the content-chunk route or assembles the full 30 MB response.

## Narrow read-only API extension

The descriptor and `/pages` contracts are unchanged. Two explicitly configured
GET routes reuse the same published descriptor and validated disk Reader:

- `/api/v4/manager/m18/v2/overview?run_id=…&generation_id=…` returns the original
  bounded `Reader.overview()` including counts and NOT_LOADED metadata.
- `/api/v4/manager/m18/v2/sections?run_id=…&generation_id=…&section=…[&cursor=…]`
  returns `Reader.detail()` plus verified small saved entry values. An item is
  loaded only when its exact `item_parts` bytes and SHA match its index entry.

Per-entry values are capped at 16 KiB, total loaded values per page at 128 KiB,
HTTP semantic responses and frontend reads at 256 KiB. Large entries retain
NOT_LOADED / ITEM_BYTES_LIMIT or PAGE_BYTES_LIMIT. `loaded_count` is for the
current page; `not_loaded_count` includes all section entries outside it and
unloaded entries on it. No global budget, Reader identity/profile contract,
publication, CAS, producer, owner or trading behavior is changed. GET writes
nothing, creates no cache and never calls `Reader.full_response()`.

## Existing-environment commands

Repository root contains the complete Python runtime `V5/src/v5_shadow/`,
`V5/pyproject.toml`, `V5/uv.lock` and complete `frontend/` package/lockfiles.
Reuse the existing authorized Python and Node dependencies; no installation is
required by this increment.

1. Copy the previously verified complete local module config to a separate
   local saved-view config. Preserve release_id, data_root, all six identity
   values, manifest/profile SHA and bundle_root unchanged. Add only the two new
   routes to its routes array. `V5/examples/m18_v2_saved_view_config.json` shows
   the full schema, but its placeholders are intentionally NOT runnable pins.
   Do not commit the actual local config, republish or rebuild the saved bundle.

2. Start the backend as its own OS process, separate from any verification
   Reader/oracle, with an unused test port that is not V4's port:

   ```sh
   PYTHONPATH="$PWD/V5/src" "$PYTHON" -B -m v5_shadow.module_api \
     --config "$SAVED_VIEW_CONFIG" --port "$API_PORT"
   ```

3. In `frontend/`, use the existing locked dependencies and build/serve:

   ```sh
   npm run test:p0
   npx --no-install vue-tsc --noEmit -p tsconfig.cloud-product.json
   npm run build
   V5_MODULE_API_ORIGIN="http://127.0.0.1:$API_PORT" \
     npm run preview:p0 -- --port "$UI_PORT" --strictPort
   ```

   Open `http://127.0.0.1:$UI_PORT/?run_id=46596b03c2ab4e29b1219fd2e5eb698f`.
   The Vite preview proxy accepts only an explicitly configured loopback API
   origin and only the M18 route prefix. It does not alter CORS or security
   settings. It rewrites the backend Host and drops browser Origin/cookie/auth
   headers for the local read-only API. Missing origin gives an honest missing
   API error; it never guesses the old V4 port. Stop these task-owned processes
   with their own terminal/session; no broad kill or existing-service changes.

## Actual isolated cloud verification

Existing Python 3.12.14 / pytest 9.1.1 and Node 24.19.0; no dependencies installed.
New transport tests were run RED before implementation. Final commands:

```sh
node --test frontend/tests/m18SavedResult.node.mjs
PYTHONPATH=V5/src:V5/tests "$PYTHON" -m pytest -q \
  V5/tests/test_m18_v2_semantic_pages.py \
  V5/tests/test_m18_v2_disk_pages.py \
  V5/tests/test_m18_v2_module_api_binding.py \
  V5/tests/test_m18_v2_http_bridge.py \
  V5/tests/test_m18_v2_publication_bridge.py \
  V5/tests/test_module_api.py V5/tests/test_module_artifacts.py
```

- Node transport/session: **12 passed**.
- Python focused regression: **56 passed, 32 subtests passed**, exit 0 (25.71s).
  Includes real synthetic HTTP consumed by the actual TypeScript frontend
  client, cursor next/previous, exact values, oversize and page-byte limits,
  generation/cursor rejection, null/false/empty preservation and unchanged
  bundle/publication hashes and mtimes. Existing API/CAS regressions included.
- Python AST syntax and Node TypeScript syntax checks passed.
- Full frontend `npm test`, `npm run typecheck`, `npm run build`: **BLOCKED before
  execution**, binaries vitest/vue-tsc/vite absent in this cloud workspace.
  Product Vue build, new Vue rendering test and full retained frontend suite
  are **NOT_RUN**, to be run with existing Mac dependencies. Earlier d94c Mac
  build evidence is only the unchanged source base, not this increment.
- Full repository suite, Mac real semantic endpoints, rendered browser behavior,
  preview deployment and natural/business acceptance: **NOT_RUN here**.

## Mac acceptance still required

Use this fixed complete candidate, run product typecheck/build, the new Vue
view test and Node test:p0, then test real descriptor/overview/sections and the
ordinary V5 page. Keep the server in a separate process from the verification
Reader; a same-process retained oracle inflated RSS in the earlier 248f test.
Do not extend Reader lifetimes across lengthy HTTP waits or change its budgets.

Verify run/target and all identity fields; read actual summary, gap pages 0/1,
materials and at least one original small status section. Confirm visible
PARTIAL/CANNOT_CONFIRM/gaps where loaded, empty stocks remain explicit and
oversized sections remain NOT_LOADED. Test refresh, selection changes, paging,
rapid repeated requests, failure/recovery and browser width. Verify before/after
bundle/publication files and clean shutdown. Publication generation remains
separate from offline generation. Do not call this P0 done or deploy on the
basis of the synthetic tests alone.

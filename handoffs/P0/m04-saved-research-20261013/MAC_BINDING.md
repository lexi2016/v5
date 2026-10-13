# M04 fixed saved-research preview integration

This is a small integration of the existing M04 module. It is not a new research algorithm or module. GitHub contains code, synthetic tests, and source hashes only; no real article payload or filled private path/config is included.

## Exact scope

- P0 reviewed source base: `6449bb3348e40fea5edab88dbf8d1df28b10ee49`. Final commit inherits fresh `da278dfdc533b83a491762aab9fc96466cf0d0db` by expected-head CAS, preserving the added M06 task-2 documents.
- Existing live backend base: `287de959ac160f6ae2792ca1f9684b4c86750012`. Its `module_api.py` blob `78aab6ce46e92e3b0dff7d41fcf2ce947b8df707` is identical to the reviewed P0 source base. Do not deploy the entire newer P0 HEAD or activate pending M06 daily work.
- Preserve the existing 0332c6b/c5ba22fa frontend navigation fixes. The file-specific prior digests in `FILES.json` must match before overlaying an existing file; a mismatch means inspect that specific file, not reset the repository.
- The original reader comes from M04 `8a3c1d2013e34b7e070fd924e1ee754f7dfd8de7`. `V5/contracts/m04_readonly_runtime.json` pins 110 already-present reader/capsule files, each byte-identical in P0. None of these dependencies is replaced or copied by this integration. The original `archive_reader.py` CLI is invoked directly with `-I -B`; neither `research_ingest_daily run`, builder, importer, provider, nor model is called.

## Apply only the exact candidate files

`FILES.json` is the authoritative file overlay list with before/after SHA256. Production files only:

1. `V5/src/v5_shadow/m04_readonly.py` (new)
2. `V5/contracts/m04_readonly_runtime.json` (new pin manifest, no dependency source)
3. `V5/src/v5_shadow/module_api.py` (M04 registration and independent read slot only)
4. `frontend/src/api/m04SavedResearch.ts` (new)
5. `frontend/src/components/M04SavedResearch.vue` (new)
6. `frontend/src/components/SourceBundleStatus.vue` (add the M04 card; all old modules retained)
7. `frontend/src/views/SavedManagerResultView.vue` (M04 direct-entry button; existing manager/source navigation retained)
8. `frontend/vite.config.ts` (one route on the existing read-only source proxy)

The remaining listed files are synthetic tests and an inactive binding example. Do not overwrite V4, source owner code, manager/M18 configs, daily scheduling, other bindings, or pending M06 implementation files. Do not check out or copy the whole branch as a deployment step.

## Bind the already-verified historical sample

Use the existing independent V5 copy verified in M04 feedback `8261160018537c71de0af17584d371a2d31913c8`, `modules/M04/feedback/mac-existing18-8a3c-20261013/report.json`. This is historical archive compatibility, not newly collected input.

The data root must contain exactly these original files and their parent directories:

- `manifest.json` SHA256 `b3018c40ba6ffb88f1eec00a48448b5f3414fd55f067fb39a7518febb012fb52`
- `research/archives/20261012.json` SHA256 `3fdf8ce89eefc4e6c39b03201e56dd3a4aaaefca125c5b3ae787228fa7bb21af`
- `receipts/research/archives/20261012.json` SHA256 `8b62a83a0dcc85879734af21a309a7e464ff0cbabbad6e68271b4d11a9766ecd`
- Dedicated marker `.v5-m04-saved-root` containing exactly `v5.m04-saved-reference.v1\n` (one LF, not literal backslash-n)

The marker is a one-time explicit Mac setup step on the independent V5 copy. GET never creates it. If the existing copy has output reports or unrelated files, create a separate marked V5 subdirectory using only the same verified three copied files. Keep report/binding/response output files outside that directory. Never pass an active V4 source root. Symlinks, extra files/directories, byte changes, a missing marker, changed sample scope, or an unexpected sample-outside outcome fail closed.

In a task-local copy of the existing `source_bundle` module API config:

1. Preserve all existing routes, release identity, roots and M06/M08/M09/M10/M17 bindings.
2. Append `/api/v5/source-bundle/research-intelligence` once to `routes`.
3. Add `m04_saved_research_binding` using the two fields in the example. Fill `archive_root` with the verified independent copy and `python_executable` with the existing approved interpreter. No new dependency installation, security access, credentials, or environment changes are required.
4. Keep the existing `V5_SOURCE_API_ORIGIN` loopback proxy. It strips origin/cookie/authorization headers. If the existing deployment uses the gateway route list, append this exact GET route to `source_bundle` there as well; preserve all existing routes and limits. Keep the manager/M18 origin and run intact.

GET accepts no selectors or query fields. Every accepted request rechecks the fixed runtime and sample hashes, runs the original cold reader, and verifies its source/request identities. It returns only the selected original archive plus explicit provenance/boundaries. The complete unchanged manifest's 53 out-of-sample errors are preserved as a count and must remain 53; they are not called validated or hidden as empty success. M04 has its own single non-queuing read slot. Timeout fails without a fallback or new acquisition, and releases the slot.

## Mac acceptance, then authorized preview update

Cloud verification is scoped to synthetic HTTP/client tests; real sample acceptance and Vue build/UI checks remain required.

- From repository root: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=V5/src:V5/tests <EXISTING_PYTHON> -B -m unittest V5/tests/test_m04_readonly_api.py V5/tests/test_module_api.py V5/tests/test_api_gateway.py -v`.
- From frontend, using the existing installed/locked toolchain: `node --test tests/m04SavedResearch.node.mjs tests/savedManagerNavigation.node.mjs`; `npm test -- --run src/components/M04SavedResearch.spec.ts src/views/SavedManagerResultView.navigation.spec.ts src/components/SourceBundleStatus.m08.spec.ts src/components/SourceBundleStatus.m09.spec.ts src/components/SourceBundleStatus.m17.spec.ts`; `npm run typecheck`; `npm run build`.
- After task-local source configuration, confirm direct source API GET and actual preview-proxied GET return JSON, not Vite HTML, and are bound to this fixed candidate. The marker/inventory must pass before requests are made.
- Confirm the exact original 18 article objects equal the original archive payload, archive date `20261012`, source slot `2100`, run `hip-49cb26f7f3a0661bde1d1440`, 18 missing retrieved_at, 18 missing available_at, PIT UNKNOWN, 53 sample-outside errors, and every production/buy/order/natural/formal flag remains false. The batch time and publication record time are not article availability.
- Record original/copy/runtime byte hashes and mtimes before and after repeated GETs. Expect zero builder/import/provider/model calls and unchanged evidence files. Keep raw article responses private; GitHub feedback should contain hashes/counts, not article bodies/private absolute paths.
- In the actual V5 page, click `研究情报 · M04` from the top. Both source and M04 disclosures must open, scroll/focus the M04 summary, and show the 18 records and boundary text. Close/reopen and repeat-click must not start another automatic read. Explicit refresh must clear old rows during loading or failure. Existing M18 strategies, source modules, and run ID must remain intact.
- Capture screenshots for real Mac acceptance in the existing private task; do not upload private research content into a public demo. If a dependency or runtime check cannot run, report NOT_RUN/CANNOT_CONFIRM with the exact blocker.

A passed synthetic suite is not deployment, complete M04/new collection, natural-run evidence, full-manifest verification, PIT approval, or trading permission. V4 remains unchanged.

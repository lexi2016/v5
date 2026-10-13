# M14 independent saved-result page: complete integration candidate

## Status and exact scope

This is a source-only integration candidate for P0 **386d5ce67a6a9914a96162cd47528290b8e7d75f**. It contains complete after-files, exact before/after SHA256 and baseline Git blob IDs, a unified patch, checked application helper, isolated API launcher, synthetic tests and verification evidence. It does not change the P0 branch or activate a Mac service.

Seven runtime files are added/changed:

1. `V5/src/v5_shadow/m14_readonly.py`
2. `V5/src/v5_shadow/module_api.py`
3. `frontend/src/api/m14SavedRebound.ts`
4. `frontend/src/components/M14SavedRebound.vue`
5. `frontend/src/views/SavedManagerResultView.vue`
6. `frontend/src/manager-selection/reboundPanelObservation.ts`
7. `frontend/vite.config.ts`

Ten additional test/fixture/declaration files are included. See `verification.json` for every path and exact preimage. Source-only fixtures are explicitly synthetic; there are no real saved artifacts, account secrets, private owner roots or real run references in this package.

## Mac feedback revision after 018827

Mac's original redacted [result and typecheck feedback](evidence/mac-018827/README.md) are retained byte-for-byte with their verified SHA256. On 018827, check-only/apply and build succeeded; typecheck found two query-group typing errors, and Vue reported 372 passed / 24 failed / 3 skipped. The obsolete M07 navigation assertion was among the delivered-test failures. Missing default Python/private historical fixtures are recorded separately, not relabelled product failures.

This revision changes only `m14SavedRebound.ts` and `SavedManagerResultView.spec.ts`, plus delivery manifests/patches/evidence. It fixes the typed group narrowing and tests the real M07 enabled/open/focused interaction. Node remains 182/182. Fixed Vue/typecheck are still NOT_RUN in the cloud; the prior Mac build pass applies to 018827, not this new revision. Backend sources and prior backend evidence are unchanged.

If the isolated checkout already has 018827 applied, use `revisions/from_018827/apply_candidate.py --target /absolute/isolated-checkout --check-only`, then the same command without `--check-only`. That delta validates exactly the two prior candidate after-SHAs and is idempotent. For a pristine P0 base, continue to use the top-level full `apply_candidate.py`. Never use the full-base helper to overwrite unknown or mixed source bytes.

The minimal next check is existing `$NODE node_modules/vue-tsc/bin/vue-tsc.js --noEmit`, followed by the four targeted new-M14/old-manager Vue files listed in the feedback. Use an existing explicit `$PY_M14` or `$PY_FUTU` when needed. No owner rerun, real fixture fabrication, P0 direct write or service deployment is included.

## Contributions and preserved source

- Original M14 Chat supplied the adapter in `provenance/original_chat_4f3da9dd.py`, unchanged, SHA256 `954f614b2888b2c67961cd03d7f431fcc53c385ddf5d15d39e610fa3a20664b8`. Its contribution is the independent server-owned saved binding, per-request original reader call, corrected direct-artifact return shape, `no_symlinks`, four-reference/group cursors, research-state separation and no producer execution. Its original tests were NOT_RUN and its header explicitly excluded route/frontend wiring.
- Integration completion adapts that reader contract into the existing module API, closes query/cursor validation, applies server-side public field allowlists and byte/page limits, supplies the independent frontend reader/session/component/navigation/proxy, and adds executable synthetic disk/HTTP/pagination tests and package helpers.
- The original `rebound_owner.py`, its algorithm, source capsule and reader are not modified. The old M18 rebound reference view, fixed manager run, dynamic manager opt-in and other source modules remain supported. No M19, replacement framework, new dependency or strategy/PIT/credential change is introduced.

The original reader is `V5/src/v5_shadow/rebound_owner.py::read_rebound_owner(root, reference)` at the pinned P0 baseline; its body directly returns the artifact. Its marker is `.v5-rebound-owner-root` containing exactly `v5.rebound-owner-root.v1\n`. This candidate neither creates nor rewrites an actual owner root marker.

## Read contract

Route: `GET /api/v5/source-bundle/rebound-saved` on the existing source-bundle read-only API.

Add `m14_rebound_binding` to its server configuration:

- `private_root`: the existing marked original M14 owner output root; server-only, never a client query.
- `reference`: exactly `run_id`, `artifact_sha256`, `manifest_sha256`, `receipt_sha256` from one committed original owner result.

`source-api.example.json` is a schema example with unmistakable zero placeholders. It is not a usable data reference. Keep private roots and real references in local runtime configuration, not this repository. Merge the one route and binding into a copy of the existing isolated source API configuration; do not replace its other routes. When a separate gateway route map is used, explicitly add only this source route there as well. The included Vite proxy uses the existing loopback-only `V5_SOURCE_API_ORIGIN`.

Each GET checks the original configured path with `no_symlinks`, calls the original cold reader, and verifies the original artifact, manifest and committed receipt SHA and identity/semantic contract. No owner/build/model/acquisition/daily/publish call is made. No response cache is used. A source-specific read slot bounds simultaneous heavy reads.

Query keys are only `group`, `cursor`, and optionally **all four** reference fields. Default group is `pending`. An unpinned first request reads only the exact server-configured reference. The frontend then pins all four fields for group changes and next/previous pages. An explicit mismatch fails; it never silently redirects to another run. Reload is the explicit way to resolve a newly configured reference. This is not a history-search API or a multi-root browser. After configuration changes, the original cold reader can still verify the retained old artifact by its old reference, as tested.

The five groups remain `strict`, `near`, `pending`, `excluded`, `screen_unresolved`. A missing observation/group fails closed, never becomes five empty arrays. Empty groups retain all five counts and history gaps. The page shows the original signal/target dates, original computation status and separate CANNOT_CONFIRM formal/observation status. Pending history is not normal zero-candidate completion or formal admission; `natural_verified`, `formal_eligibility_verified`, `production_allowed`, `buy_gate_updated` and `orders_sent` remain false.

Pagination is 32 rows maximum, 16 KiB per loaded raw row, 128 KiB aggregate loaded raw values, 256 KiB complete response and 4096-character cursors. Oversized rows advance as explicit NOT_LOADED with their original canonical-row SHA; byte-deferred rows are served on the next page rather than skipped. Cursors bind the exact four references, group and offset; malformed, duplicate-key, extra-key, wrong-reference, cross-group and invalid-offset cursors reject. Unknown query keys reject. Public projections allow only explicit observation/row/reference fields and suppress filesystem locations, including in errors. Source hashes, original row hashes and public projected-row hashes are distinct. No raw byte offsets, M18 identity or M18 generation are fabricated.

The independent M14 navigation is available even when the manager overview is unavailable. The existing M18 entry is separately labelled “经理同次运行超跌引用”. The M14 component is lazy, bounds reads, aborts old requests, ignores stale results, clears old rows on failure, and distinguishes missing configuration WAITING from a verified empty group. Existing rebound rendering is reused through its actual structural fields.

## Apply to an isolated complete P0 checkout

Use the already available Python/dependencies. Do not run against an active/mixed checkout. No package installation is required for the saved API's stdlib-only read path.

1. Obtain a complete isolated checkout at P0 `386d5ce67a6a9914a96162cd47528290b8e7d75f` from the existing repository. All product-source preimages are also unchanged from `c7b815c065da83bd2db2b3023be4607ce9f194ec`; the navigation test preimage is the later pinned version.
2. Run `python -B apply_candidate.py --target /absolute/isolated-checkout --check-only` from this candidate directory.
3. Run `python -B apply_candidate.py --target /absolute/isolated-checkout`. It verifies all before-images before changes and verifies candidate after-image hashes. Exact already-applied after-images are accepted. A preimage mismatch or symlink refuses application. It never force-overwrites an unknown source version.
4. Alternatively, use `candidate.patch` only after the same hash check. The full changed files are under `files/` for inspection; do not mix patch application with a different runtime baseline.
5. Prepare a private isolated source API config using the existing local marked source API root and exact existing owner reference. Do not invent missing owner artifacts or create a new owner run to make the page look ready.
6. Start the existing API from any working directory with `python -B /absolute/candidate/run_saved_api.py --checkout /absolute/isolated-checkout --config /absolute/private-source-api.json --port 0`. It prints the assigned loopback address. This invokes the existing `module_api.main`; it neither starts a scheduler nor runs an owner.
7. In the isolated frontend with its already-installed dependencies, run `npm test`, `npm run typecheck`, `npm run build`, then start the existing local preview with `V5_SOURCE_API_ORIGIN` set to that loopback API address. Keep the existing manager origin unchanged. Do not replace V4 or claim live preview activation from these instructions alone.

`python -B verify_package.py --base-checkout /absolute/pristine-P0-checkout` copies sources to a temporary isolated directory, verifies refused wrong-preimage/symlink application, check-only/idempotence/all after hashes, creates an explicitly synthetic persisted trio, starts the actual saved API from outside the checkout with no PYTHONPATH, and reads a real HTTP page. It does not read real owner data or alter the supplied baseline checkout.

## Verification performed

Environment: existing cloud Python 3.12.14/pytest 9.1.1 and Node 24.19.0. No new dependency was installed. The V5 project declares Python >=3.14; Mac's existing pinned environment remains the required product-runtime check. These cloud results exercise the stdlib-only saved-reader path, not a claim that all owners support Python 3.12.

- M14 disk/HTTP/standalone tests: **13 passed, 16 subtests passed**. Command from the isolated checkout: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=V5/src:V5/tests python -m pytest V5/tests/test_m14_saved_rebound.py V5/tests/test_m14_saved_launch.py -q`.
- Includes full synthetic 690-pending pagination across 22 pages, strict/near/excluded/unresolved zero with retained history gaps, original reader verification on every request, each trio-file tamper, rehashed cross-file identity mismatch, paths/symlinks, old reference preservation, unknown query, cursor failures, public projection, byte budgets and no producer/read-only checks. This does not claim a new real market run or natural acceptance.
- Existing module API, M18 daily publication, disk pages, fixed binding, historic rebound and original owner persistence regressions were run alongside M14. Final result: **70 passed, 76 subtests passed**, recorded in `evidence/focused-backend-final.txt`.
- Full frontend `npm run test:p0`: **182 passed, 0 failed**. Includes identity pinning, stale requests, errors/WAITING, group/page navigation, independent-vs-historic renderer, and 690 observation gaps within the response byte limit. The frontend also accepted an actual safe response emitted by this backend's synthetic persisted reader (32/70 pending).
- Package application and actual CLI launch/HTTP read from outside repository cwd: **PASS**; details in `evidence/package-verification.txt`.
- Full backend `pytest -q` was attempted: **collection blocked**, not a full pass. Existing `tests/m11/test_original_owner_contracts.py` lacks `pydantic`; existing `tests/test_rebound_date_compat.py` lacks `pandas` in this cloud environment.
- Vue DOM test files are supplied. `npm test`, `npm run typecheck` and `npm run build` were attempted but the tools `vitest`, `vue-tsc`, `vite` are absent: **NOT_RUN**. No real browser/Mac UI/preview activation or real-data acceptance occurred here.

## Mac/P0 handoff and stopping condition

The next integration step is exact preimage-checked application in the existing isolated V5 environment, then the supplied Python and frontend checks using installed dependencies. Use the already-existing original M14 reader root/reference supplied privately by the coordinator. Verify that the page retains that artifact's actual dates, five group counts and pending history gaps, not the manager's older target date. Check next/previous pages, group changes, an error clearing old rows, the independent navigation while manager results are unavailable, and the unchanged historic M18 view.

If an active source SHA differs, stop the application and reconcile through the single P0 writer; do not replace the active shared module API or rewrite the manager binding. Do not report this candidate as integrated, deployed, naturally verified or formally eligible until those corresponding checks actually occur. This delivery stops at the complete candidate, verified branch commit and the explicit Mac integration handoff.

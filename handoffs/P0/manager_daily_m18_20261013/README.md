# Daily manager to M18 v2: isolated candidate

Base product source: `5846b3c117397431dbaed041af2d9e1533f9f631`.
Commit parent: fresh original P0 head `7eac09efd3ffcb0e48d58b8d10e7b92a525c41df` (the later change is two M02 feedback documents only).

## Exact contract

- Add `m18_v2_daily_publication: true` explicitly to the manager module API configuration AND the same module configuration supplied as `daily.manager_publication`. Absence/false preserves the fixed reader and legacy publication path. No active runtime configuration is included or changed by this candidate.
- Keep the existing `m18_v2_binding`, including fixed run `46596b03c2ab4e29b1219fd2e5eb698f`, unchanged. Keep the manager marked data root and release identity. The intended reader routes are the existing `/api/v4/manager/m18/v2`, `/pages`, `/overview`, `/sections`; retain the old workspace route if required.
- Daily consumes the already verified original auto-read result after the same saved manager attempt. It does not make an extra manager call in dynamic mode. Original partial/business-blocked status and every admission/PIT/safety field remain unchanged.
- The existing bounded offline spawn builder consumes actual saved-plan bytes plus the canonical result (transport envelope excluded). The six identity fields are `run_id`, `target_date`, `plan_sha256`, `raw_sha256`, `response_sha256`, `input_identity`; they derive from those inputs, never today's date substituted onto old data.
- Builder output is copied with existing immutable fd-relative writers into the marked manager root's `m18-v2-bundles/<generation_id>`. Directory handles remain pinned. A fresh existing read-only worker no-follow-opens every ancestor and validates the full persisted bundle under the unchanged M18 profile before publication.
- The descriptor adds optional `manifest_sha256`. It contains no filesystem root. Dynamic readers derive the sole allowed bundle location from the marked configured data root and the validated generation digest. Existing descriptor format remains valid for the fixed reader.
- One existing `publish_generation` CAS publishes both the exact `{run_id: ...}` descriptor and empty-query current descriptor, plus the old workspace record if that route is configured. Source SHA is the actual verified read request SHA. Failed validation/CAS does not partially advance the two descriptors.
- An existing run's identity/profile/manifest is immutable. This is checked against the immutable expected publication generation; the final CAS rejects a concurrent change. A valid orphan bundle from failed publication can be safely revalidated and reused without rerunning an owner. Corrupt files, collisions, symlinks and path swaps reject.
- Explicit run links remain exact and never redirect. A blank frontend run requests the empty-query descriptor. With dynamic mode enabled and no current descriptor, it fails closed. With dynamic mode disabled, it reads the fixed descriptor and shows its actual old target date. Subsequent overview/section navigation stays pinned to the selected run/generation.

This does not create missing `manager_request`/`manager_template`, fabricate today's owner products, enable a schedule, widen the 08:45–09:00 window, or run a manager outside it. A current legal request and original input/readback contracts are still required. No actual daily manager result or natural/business acceptance was produced here.

## Changed runtime sources and integration order

Exactly three backend files:

1. `V5/src/v5_shadow/daily_owner_adapters.py`
2. `V5/src/v5_shadow/m18_v2_publication_bridge.py`
3. `V5/src/v5_shadow/module_api.py`

Exactly two frontend files:

1. `frontend/src/api/m18SavedResult.ts`
2. `frontend/src/views/SavedManagerResultView.vue`

All before/after raw SHA256 values are in `verification.json`. No source-bundle/M06/M14 file, owner algorithm, V4 file, credential or security setting changes.

Mac next step is isolated candidate verification only: first compare each active source against the recorded before SHA, copy these five source files into an isolated existing V5 checkout, use its already-installed frontend dependencies for tests/typecheck/build, and run the same synthetic backend tests. Do not overwrite a mixed runtime when its baseline differs. Do not enable the active opt-in, restart a live API, deploy frontend assets or invoke a real manager as part of this candidate receipt. Future runtime activation requires a separately coordinated matching publication/API config and a lawful same-day manager request.

## Verification

- Test-first red observed for missing current lookup/publication, redundant owner read, CAS orphan retry, same-run replacement and attempted symlink escape.
- Final focused backend: **40 passed, 33 subtests passed**. Command from repository root: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=V5/src:V5/tests python -m pytest V5/tests/test_m18_daily_publication.py V5/tests/test_m18_v2_disk_pages.py V5/tests/test_m18_v2_module_api_binding.py V5/tests/test_daily_owner_adapters.py V5/tests/test_daily_manager_assembly.py -q`.
- Frontend existing `npm run test:p0`: **164 passed, 0 failed, 0 skipped**. Includes default lookup, explicit-run identity/no fallback, pinned navigation and blank URL handling.
- Vue integration tests added but **NOT RUN**; `npm test`, `npm run typecheck`, `npm run build` could not start because `vitest`, `vue-tsc`, `vite` are absent from the cloud environment. No dependencies were installed. Existing Mac dependencies are the follow-up route.
- Full backend pytest was attempted once and stopped during collection: `tests/m11/test_original_owner_contracts.py` lacks `pydantic`; `tests/test_rebound_date_compat.py` lacks `pandas` in the existing pytest environment. This is **not a full-suite pass**.
- Backend environment: Python 3.12.14, pytest 9.1.1. All exercised manager inputs are explicit synthetic fixtures. No Mac/native UI, live inputs, real publication, deployment, transactions or natural daily verification occurred.

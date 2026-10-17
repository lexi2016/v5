# UI/API and backend defect fixes — 2026-10-17

## Fixed source

- Base integration commit: `01d93717905813705732161d4d79062ae5af2d99`
- Working branch: `fix/v5-integration-publication-test-harness-20261017`
- Latest commit at document creation is linked from PR #4; use the live branch HEAD for final verification.
- This is a candidate repair set. No production deployment or V4 runtime change was performed.

## Changes made

### UI-001 — manager target-date → saved-run lookup
- Added a native target-date input to the saved manager results page.
- Uses read-only `GET /api/v4/manager/research/workspace?date=YYYYMMDD&view=auto` to find an already-consumed exact-date plan.
- Requires the response target date to equal the requested date, `plan_product.consumed === true`, a 32-hex run ID and 64-hex product SHA before opening the M18 run.
- Persists `target_date`, `date`, and the confirmed `run_id` in the URL. No producer trigger and no latest fallback.
- Added success-path and mismatched-date tests; NOT_RUN in this environment.

### UI-002 — requested date versus actual source date
- `research_workbench_readonly._lane` now returns `requested_date` separately and `research_date: null` when the M04 source binding is absent.
- Backend validator accepts this only for `NOT_MATERIALIZED` with matching requested date; a materialized source must match the exact requested date.
- Active `frontend/src/research-workbench/api/research_lane.ts` and active `ResearchView.vue` preserve this distinction and display `CANNOT_CONFIRM` for the absent source date.
- Added backend/API/view regression tests; NOT_RUN in this environment.

### UI-003 / UI-004 — exact day route and date catalog
- Added GET-only gateway compatibility aliases for `/api/v3/research/day` and `/api/v1/runs/date-list`, routed only to an existing `source_bundle` module.
- `module_api` permits those exact paths as read-only aliases and validates saved record identity/digest as usual.
- The day endpoint cold-reads only the exact `archive_date` record. Missing records remain 503 `CANNOT_CONFIRM / MODULE_RESULT_NOT_AVAILABLE`.
- The date catalog scans only published exact research-day records and derives `default_date` from those records; it does not invent today's date or fall back to latest. If none exist, it returns explicit `NOT_MATERIALIZED` with an empty catalog.
- Catalog declares its limited scope: broader V4 run-date, review-date and stage-date catalogs have not been migrated.
- Added gateway and module API tests; NOT_RUN in this environment.

### UI-005 — M16 selected date persistence
- Changed the M16 date field to a native `type=date` input.
- Persists the compact date as `m16_date=YYYYMMDD`, restores it after refresh, validates calendar dates and keeps the requested date in the API query.
- Added refresh/persistence test; NOT_RUN in this environment.

### UI-006 — manager publication source identity contract
- Missing or malformed `source_input_sha256` is rejected as `MANAGER_SOURCE_IDENTITY_REQUIRED`, rather than leaking the lower-level `CONTRACT_SHA_INVALID` error.
- Added coverage for missing and malformed values; NOT_RUN in this environment.

### UI-007 — visible errors and disabled-lane reasons
- Daily page catalog/API failures now remain visible as `ERROR`, with retry and Chinese explanations for 404, 503 and network failures; raw transport reason is retained.
- Manager page maps known missing-binding, invalid-result and route errors to actionable Chinese text while retaining raw diagnostics in an expandable section.
- Missing lane references are explained as unconfirmed, not as zero rows.
- Tests updated; NOT_RUN in this environment.

### UI-008 — IPC stderr backpressure
- `_Pipe.read` drains stderr while the worker remains alive after stdout EOF, preventing a worker blocked on a full stderr pipe from deadlocking parent `wait()`.
- It polls worker exit on a bounded 50 ms interval after stdout EOF so descendant-held stderr does not block indefinitely; it does not wait for descendant EOF after the worker exits.
- Added a small-pipe, 60 KB stderr regression in addition to the stdout/descendant-held-stderr test; NOT_RUN in this environment.

### UI-009 — readable status and navigation identity
- Long status/source identity values wrap rather than truncate with ellipsis.
- Daily research navigation preserves `run_id`, `target_date` and selected `date` while switching views.
- Added navigation test; NOT_RUN in this environment.

### Path mapping correction
- HK preselection candidates are `hk_preselection.py` and `p0_hk_preselection.py`, not `hk_source_daily.py`.
- Close-review candidates are `a_close_review.py` and `hk_close_review.py`, not the obsolete `*_daily.py` paths.
- This is a source-index correction only, not evidence that those features are missing or accepted.

### M17 read-only route error classification
- Missing M17 binding is now a specific `503 M17_BINDING_NOT_CONFIGURED`; it cannot fall through to a forged/cached module-response record.
- Malformed date/run/query is `400 M17_QUERY_INVALID`; wrong exact date/run identity is `409 M17_REQUEST_IDENTITY_MISMATCH`.
- Missing saved success is `503 M17_SAVED_PRODUCT_NOT_AVAILABLE`; invalid product/ledger identity is `409 M17_PRODUCT_INVALID`; reader unavailable/timeout is a 503; unexpected internal errors are 500 `M17_INTERNAL_ERROR` instead of being mislabeled as invalid product.
- Updated `V5/tests/test_m17_readonly_api.py` to pin these distinctions. NOT_RUN in this environment.

### P0 runtime example
- Replaced the stale `module_api.host/mode` example with the actual `v5.module_api.v1` schema, absolute placeholder paths, read-only routes, and disabled daily registrations.
- Added `V5/docs/operations/p0-runtime-example.md` with non-symlink root checks, marker initialization without overwrite, frozen dependency instructions and `runtime validate/start/status/stop` commands.
- Runtime service readiness is explicitly not data or natural-scheduler acceptance.

## Verification status

- No local shell or test runner is exposed in this connected session; therefore none of the newly added tests or frontend builds were executed here.
- GitHub Actions workflow runs and combined status checks were queried for the then-current commit; no runs/statuses were returned. This is NOT evidence of a pass.
- Earlier user-supplied evidence reports the pre-existing publication six-test module passed three consecutive rounds on Python 3.14.8. That evidence predates these changes and does not verify the current candidate.
- Current feature parity remains `NOT_ACCEPTED`. Real Friday data was not captured by these code changes. Actual source-bundle day-product records, M04 source binding, manager workspace records, deployed browser behavior, natural scheduling and the full V4 parity inventory remain acceptance gates.

## Required local/deployment verification

Run on the intended isolated machine with Python >=3.14 and frontend dependencies from the existing lockfile:

1. `PYTHONPATH=V5/src pytest -q V5/tests/test_manager_result_transport.py`
2. `PYTHONPATH=V5/src pytest -q V5/tests/test_p0_manager_publication_bridge.py V5/tests/test_api_gateway.py V5/tests/test_module_api.py V5/tests/test_research_workbench_readonly.py`
3. `cd frontend && npm test -- src/research-workbench/api/research_lane.spec.ts src/research-workbench/views/ResearchView.spec.ts src/views/DailyResearchCommandView.spec.ts src/components/M16SavedResearch.spec.ts src/views/SavedManagerResultView.spec.ts`; then `npm run typecheck`, `npm test`, `npm run test:p0`, and `npm run build`.
4. Run the full publication integration module repeatedly with a hard process deadline and confirm clean exit code 0 and no leaked child/thread.
5. Deploy only the reviewed candidate under the existing authorized process, then verify real HTTP response codes, browser screenshots, date-bound saved product hashes, exact-date no-data behavior, M16 refresh persistence, and a real Friday data capture. No source record or synthetic fixture can substitute for the last item.

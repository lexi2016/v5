# V4 → V5 Feature Parity Matrix

This matrix is evidence-first. It currently contains 22 source/feature rows, including the fixed V4 API route families, manager workspace/job endpoints, archive reads, UI, scheduler, Stage 8, persistence, and V4 non-regression. Every row remains `NOT_ACCEPTED` until its V4 behavior is mapped to a specific V5 implementation and the corresponding save → independent cold read → ordinary API → original UI → schedule/recovery chain is verified.

## Machine-readable records

- [CSV matrix](V4_V5_FEATURE_PARITY.csv)
- [JSON matrix](V4_V5_FEATURE_PARITY.json)
- [Fixed V4 source inventory and source SHA evidence](2026-10-17-v4-source-inventory.md)
- [Completion plan](../superpowers/plans/2026-10-17-v4-parity-completion.md)

## Evidence basis

> Scope limitation: the separate 1,814-source-file Drive package mentioned in the latest handoff has not yet been extracted and compared byte-for-byte in this connected session. The matrix currently cites the pinned GitHub V4 snapshot; it is not evidence that this tree is identical to the Drive package or the currently deployed V4 runtime.


The initial inventory uses `lexi2016/v4@24c6d60d524f43fcf4209ec8b078ec02cb34417e`, whose recursive Git tree reported 2,124 paths and was not truncated. The following file blob identities were read directly:

- `canonical/apps/api/v35_api/app.py`: `e1b58a34bd73297008a7b3d318d4ddd4ae5ea6ee`
- `canonical/apps/api/v35_api/manager_research_router.py`: `1e89a2b2cdc9c6192eed188ac53d8b4027aa77be`
- `canonical/apps/api/v35_api/research_router.py`: `5e94245514b02476c5c24876270c144f799fab4b`
- `canonical/apps/api/v35_api/_review_router_parts/http_routes.py`: `f884abb7215902e8e42b8d598458a14ca49dfbc9`
- `canonical/apps/web/src/views/ManagerSelectionView.vue`: `75b848172dd2a3fbc00b44dfb720759867209e42`

The source tree confirms route families for health/readiness, run dates, preselection pools, workbench stages, stage-center selection, manager stage selection, manager research job lifecycle, catalyst observations, manager workspace refresh, announcements, article/day/hourly research, review generation/read, scheduler operations, and HK Stage 8 capture. This is historical source evidence, not proof of the currently deployed V4 version.

## Corrected source-path mappings

The earlier candidate path labels for V5 preselection and close-review modules were incorrect. The actual source candidates are:

- HK preselection: `V5/src/v5_shadow/hk_preselection.py` and `V5/src/v5_shadow/p0_hk_preselection.py`; do not infer feature absence from the obsolete `hk_source_daily.py` label.
- A-share close review: `V5/src/v5_shadow/a_close_review.py`; do not infer feature absence from the obsolete `a_close_review_daily.py` label.
- HK close review: `V5/src/v5_shadow/hk_close_review.py`; do not infer feature absence from the obsolete `hk_close_review_daily.py` label.

These are path-mapping corrections only. Their behavior and end-to-end acceptance remain separately unverified until original algorithms, real input identities, save/cold-read, ordinary API/UI and scheduled-run evidence are checked.

## Newly wired date-scoped read paths

The API gateway now provides GET-only compatibility aliases for `/api/v3/research/day` and `/api/v1/runs/date-list` to the existing `source_bundle` read-only module. The day route returns only the exact published `archive_date` record; a missing record remains `503 CANNOT_CONFIRM`. The catalog enumerates only exact published research-day products and explicitly reports that the broader V4 run-date catalog has not been migrated. This prevents 404s for the known UI paths without inventing data or falling back to latest.

## Current acceptance state

- Fixed historical V4 tree inventory: PASS for tree completeness only.
- Current deployed V4 release identity and read-only health/config snapshot: BLOCKED / NOT VERIFIED.
- Route-by-route behavioral and schema comparison: NOT RUN in full.
- Real V5 input/provider and natural trigger acceptance: NOT ACCEPTED.
- Overall V4→V5 parity: NOT ACCEPTED.

Do not promote a row to PASS based on source-file presence, a route existing, synthetic tests, or a page opening. Record exact input/output SHA, test command/exit code/log, independent cold reader, API/UI evidence, schedule window, and recovery/rollback evidence per feature.

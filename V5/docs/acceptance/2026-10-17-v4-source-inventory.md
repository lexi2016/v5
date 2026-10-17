# V4 Source Inventory Evidence — 2026-10-17

## Scope and source identity

> Scope limitation: the separate 1,814-source-file Drive package described in the 2026-10-17 handoff has not been extracted and compared byte-for-byte in this connected session. This inventory is based on the pinned GitHub V4 snapshot below; it must not be treated as equivalent to that Drive package or the currently deployed V4 runtime.


Read-only Git tree inventory of `lexi2016/v4` at fixed commit `24c6d60d524f43fcf4209ec8b078ec02cb34417e`.

- Git tree API reported `truncated=false`, 2,124 paths.
- This is a fixed historical repository snapshot, not proof of the currently deployed V4 runtime version.
- No V4 files, active runtime, scheduler, or data roots were modified.
- The exact current deployed V4 release/entrypoint and its read-only health/config snapshot remain unverified and must remain a parity acceptance blocker until authorized evidence is available.

## V4 entrypoint families confirmed in the fixed tree

### API and manager workspace
- `handoff/v4-running-source-20261005/api/apps/api/v35_api/app.py`
- `handoff/v4-running-source-20261005/api/v4/manager_research/workspace_plan.py`
- `handoff/v4-running-source-20261005/api/v4/manager_research/workspace_announcements.py`
- `handoff/v4-running-source-20261005/canonical/apps/api/v35_api/app.py`
- `handoff/v4-running-source-20261005/canonical/apps/api/v35_api/_research_lane_router_parts/http_routes.py`
- `handoff/v4-running-source-20261005/canonical/apps/api/v35_api/_review_router_parts/http_routes.py`

### Manager UI and API contracts
- `handoff/v4-running-source-20261005/api/apps/web/src/api/managerWorkspace.ts`
- `handoff/v4-running-source-20261005/canonical/apps/web/src/api/managerWorkspace.ts`
- `handoff/v4-running-source-20261005/canonical/apps/web/src/api/managerPreselection.ts`
- `handoff/v4-running-source-20261005/canonical/apps/web/src/api/managerStageSelection.ts`
- `handoff/v4-running-source-20261005/canonical/apps/web/src/views/ManagerSelectionView.vue`
- `handoff/v4-running-source-20261005/canonical/apps/web/src/views/ManagerSelectionView.spec.ts`
- `handoff/v4-running-source-20261005/canonical/apps/web/src/manager-selection/businessStatus.ts`
- `handoff/v4-running-source-20261005/canonical/apps/web/src/manager-selection/announcementObservation.ts`
- `handoff/v4-running-source-20261005/canonical/apps/web/src/manager-selection/researchAttention.ts`

### Preselection and selection
- `handoff/v4-running-source-20261005/api/domains/preselection.py`
- `handoff/v4-running-source-20261005/api/domains/preselection_materializer.py`
- `handoff/v4-running-source-20261005/api/infrastructure/preselection_pool_store.py`
- `handoff/v4-running-source-20261005/api/infrastructure/review_core_stage7_pool_source.py`
- `handoff/v4-running-source-20261005/api/ops/materialize_preselection.py`
- `handoff/v4-running-source-20261005/api/ops/materialize_scheduled_preselection.py`
- `handoff/v4-running-source-20261005/api/ops/refresh_research_preselection.py`
- `handoff/v4-running-source-20261005/api/stage_center/selection.py`
- `handoff/v4-running-source-20261005/api/upstreams/review_core/stage7_pool.py`
- `handoff/v4-running-source-20261005/api/upstreams/review_core/stage7_sources.py`
- `handoff/v4-running-source-20261005/canonical/stage_center/selection.py`

### Announcement cycle and scheduling
- `handoff/v4-running-source-20261005/api/ops/run_manager_announcement_cycle.py`
- `handoff/v4-running-source-20261005/api/ops/run_v35_macos_scheduler.py`
- `handoff/v4-running-source-20261005/api/ops/run_v35_macos_scheduler_daemon.py`
- `handoff/v4-running-source-20261005/canonical/ops/run_v35_macos_scheduler.py`
- `handoff/v4-running-source-20261005/canonical/infrastructure/scheduling/manager_announcement_supervisor.py`
- `handoff/hk-close-hk-calendar-20261007/canonical/ops/run_v35_macos_scheduler.py`
- `handoff/hk-close-hk-calendar-20261007/scheduler/ops/run_scheduled_slot.py`
- `handoff/hk-close-hk-calendar-20261007/scheduler/ops/run_v35_macos_scheduler_due.py`

### Stage 8 and close/review
- `handoff/hk-daily-runtime-r2-20261007/candidate/stage_center/hk_stage8/precapture.py`
- `handoff/hk-daily-runtime-r2-20261007/candidate/stage_center/hk_stage8/rtdata.py`
- `handoff/hk-daily-runtime-r2-20261007/candidate/stage_center/hk_stage8/snapshot.py`
- `handoff/hk-oct8-preparation-20261007/close/scheduler_candidate/ops/build_close_review.py`

## Consequences for the parity matrix

These are source-tree entrypoint candidates, not a complete behavioral specification. Each must be read at its pinned source SHA and matched to its corresponding route, UI action, scheduler trigger, persisted artifact, cold reader, and failure recovery. Similar names across `api`, `canonical`, and dated handoffs are distinct candidates until lineage and manifest evidence identifies the authoritative one.

Known module-level candidates in the fixed V5 source are listed in `handoffs/20261016-chat-completion/SOURCE_INDEX.md`; this does not prove current runtime equivalence. The next inventory pass must extract route decorators/registrations, UI actions, scheduler workload configuration and store readers from the selected V4 snapshot, then add one stable row per actual feature/subfeature to `V4_V5_FEATURE_PARITY.csv/.json/.md`.

## Status

- Fixed historical V4 tree inventory: PASS (2,124 paths, not truncated).
- Current deployed V4 release identity: BLOCKED / NOT VERIFIED.
- Complete V4 route/UI/job/reader semantic inventory: NOT RUN.
- V5 feature parity: NOT ACCEPTED.

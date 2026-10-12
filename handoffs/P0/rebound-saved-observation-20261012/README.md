# M14 independent research observation in the existing V5 page

Adds an adjacent “超跌研究” tab. Announcement research remains the default. Reads only the existing same-run frozen response, not an M14 rerun or formal manager selection. The accepted read-only process/identity/resource protections remain unchanged.

## Source and display

The existing V4 stock card was extracted from the `catalystObservationPanel.ts` closure into the already-existing `reboundPanelObservation.ts`. The legacy caller delegates to that shared function with its old behavior. A separate observation mode keeps the same reason/gate/detail layout but reads `amount_native`, `observed_session`, and original downgraded qualification/unit fields. It does not reuse unsupported HKD, verified-panel or formal-candidate wording. No business classification or numerical test is recomputed.

The five closed groups are `strict`, `near`, `pending`, `excluded`, and `screen_unresolved`. Original group reasons, near-condition failed gates/values/gaps, pending history reasons, and exclusion reasons remain distinct. The duplicate `cards` array is neither an API group nor an extra count. Source SHA keys retain their original names; local source paths are omitted from displayed details and are never converted into links.

Source status and inner observation status stay separate from `original_computation_status`. The scope remains `INDEPENDENT_READ_TIME_OBSERVATION_NOT_SAVED_PLAN_OR_FORMAL_SELECTION`; this is not saved-plan consumption. `eligible_screen=null`, CANNOT_CONFIRM, UNVERIFIED, null currency/units and native evidence NOT_PROVEN are preserved. The original empty `market_screen` and manager `stocks` are not changed. Dates are read from the source; preparation/read times are not relabelled as the manager research cutoff.

Parent-coordinated Mac source inspection (not candidate execution) established693 rows: strict214, near286, pending34, excluded159, unresolved0. The section is5,205,410 bytes at `[16164450,21369860)`, SHA256 `920a43c45bd7ee7bff75192d965dd4a56e3023ccbb946b3363ea4b0c61737bca`. Actual observed session20261009 and target20261012 are displayed from saved values, never hardcoded by the view. Original calculation READY_WITH_GAPS does not override CANNOT_CONFIRM.

## Closed bounded API

Existing `/api/v4/manager/m18/v2/sections` route; no config migration:

```
?run_id=<exact run>&generation_id=<offline generation>
&section=rebound_research_observation&projection=rebound_references
&group=strict[&cursor=<opaque group cursor>]
```

The response keeps the detail envelope and adds `projection`, `group`, and `rebound` metadata (`source_section_sha256`, `group_counts`, `source`, `observation`). Source and observation metadata are whitelisted independently. Each row retains its original absolute response offset, byte length and SHA. Cursors bind the exact group, projection, source section SHA and existing run/generation/profile/manifest identities. Arbitrary paths, `cards`, cross-group cursors and wrong projection selectors are rejected.

A fresh supervised worker fully validates the original bundle. Only the validated section is additionally parsed/indexed; no `full_response()` API, cache, owner execution or GET writes. Original resource budgets remain fixed. Pages are at most32 entries with16KiB per loaded row,128KiB total loaded values and256KiB HTTP. **A row fitting16KiB does not imply32 rows fit128KiB.** Item/page caps remain visible NOT_LOADED with exact original metadata, rather than returning a partial value or claiming all rows were loaded.

## Existing-environment commands

Use the complete fixed repository and existing authorized dependencies. Preserve the same local saved-view config and data pins; use a fresh candidate API process on a non-V4 port. Do not upload private data/config or interrupt the user's Mac screen.

```sh
PYTHONPATH="$PWD/V5/src" "$PYTHON" -B -m v5_shadow.module_api \
  --config "$SAVED_VIEW_CONFIG" --port "$API_PORT"
cd frontend
npm run test:p0
npx --no-install vitest run src/views/SavedManagerResultView.spec.ts \
  src/manager-selection/reboundPanelObservation.spec.ts
npx --no-install vue-tsc --noEmit -p tsconfig.cloud-product.json
npm run build
V5_MODULE_API_ORIGIN="http://127.0.0.1:$API_PORT" \
  npm run preview:p0 -- --port "$UI_PORT" --strictPort
```

The existing ordinary `/` and `/manager-selection/` entries keep the same exact default run; query string optional. New backend and new built assets are required together. Prior announcement assets do not contain this tab.

Focused real acceptance: retain announcement default and first-page behavior; inspect M14 groups and paging against original counts/row slices/hash/identity, including pending/excluded and empty unresolved. Explicitly record LOADED versus NOT_LOADED due to the unchanged aggregate page cap. Confirm the original stocks/market_screen stay empty/unconfirmed, independent scope and unknown units remain visible, group changes reset cursors, and returning to announcements restores that view. Verify worker exit/reap and data hashes/mtimes. Do not attach an oracle Reader to the service process. Only after acceptance should the task-owned preview be switched, with the prior version retained.

Cloud evidence is separate from real Mac/browser acceptance: see `VALIDATION.json`. Vue/typecheck/build are NOT_RUN in cloud because the existing binaries are absent; the parent owns Mac validation and preview updates.

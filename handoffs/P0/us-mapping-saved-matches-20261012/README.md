# M15 saved daily US-to-HK research matches

Adds the “美股驱动” tab beside the accepted announcement and rebound tabs. Announcements remain the default. The existing V4 `renderUsMappingCoverage` function is retained unchanged and used for its stock grouping, original relation reasons, official source links, product stages and limitations. The new adapter supplies only the current bounded daily matches and their small original metadata.

## Scope and original source

Only `payload.us_mapping_research.daily_run.matches` becomes relationship rows. They are grouped by the original `hk_symbol`: four relationships can mean three HK companies. The page labels relationships and HK subjects separately, including “本页” for partial pages. PRODUCT_PEER and OPTICAL_TRANSPORT_PEER remain non-supply peer relationships; DIRECT_NAMED_COMPONENT_SUPPLY remains the source's named component-supply category. No relation, investment classification or screening rule is recomputed. US positive change is not relabelled as a large-gain screen.

Coverage retains PARTIAL, the configured sample size, rising/assessed/unassessed counts, reviewed symbol keys, full-market/formal/natural false flags, and reasons. The small historical registry scope/seed date is separate from current daily matches. Registry cards, retrospective reviewed rows and the wider coverage rows are not counted as daily matches. Missing/null data remains unknown. Official links use the old renderer's http/https and credential-free URL checks; no new source link is invented.

The sibling `payload.owner_chain.us_mapping_daily_plan_reference` is shown as the **original plan-consumption status in this frozen response**. Daily COMPLETED and visible matches do not imply CONSUMED. The exact original status, run/artifact, availability, plan cutoff, reason and safety flags are retained, excluding the duplicate matches. A missing/invalid/oversized reference is explicitly NOT_LOADED. Historic registry SOURCE_FAILED is a separate state and does not overwrite this daily plan reference.

Parent-coordinated Mac source inspection, before this candidate:
- Saved run `46596b03c2ab4e29b1219fd2e5eb698f`; source section24,515B, range `[28148161,28172676)`, SHA `678b04c5fb0c17d1e1c56f3a42f11232ab659e756b4357e1abc0dcbf44947ce0`.
- Daily matches4 / distinct HK3, max row1,576B. Daily run `f8041aabc13e4715b5b1fe8bdd95b5ed`; artifact `ce5fe342c9ae1c937fb3b7dfe724401c11642bb1abdecb71acc69b7e6d78b263`.
- Target20261012, US session20261009, daily research cutoff2026-10-12T04:39:26.258807+08, generated2026-10-11T20:39:26Z. Per-match target-date eligibility CANNOT_CONFIRM.
- Configured33, rising23, assessed4, unassessed19; only reviewed keys AVGO/CIEN/COHR/LITE. Historical registry seed20260930 is not the current target.
- Owner-chain section1,331,642B, target reference5,980B. Original reference CONSUMED, same run/artifact, availability2026-10-11T20:39:26Z, plan cutoff2026-10-12T07:42:13.933163+08, reason null; RESEARCH_ONLY true and production/buy-gate-update/order flags false.
These source facts do not assert this candidate's Mac execution passed.

## Closed bounded API

The existing read-only route accepts one additional exact selector, with no group or arbitrary path:

```text
/api/v4/manager/m18/v2/sections?run_id=<run>&generation_id=<generation>
&section=us_mapping_research&projection=us_mapping_matches[&cursor=<opaque>]
```

The detail envelope retains the exact identity/generation/profile/manifest and adds `projection: us_mapping_matches` plus `us_mapping: {source_section_sha256, match_count, source, daily_run, coverage_diagnostics, plan_reference}`. Whitelisted metadata excludes duplicate matches, registry cards and coverage rows. Current entry hashes, lengths and absolute offsets refer to the exact original response slices. Cursor binds the source SHA and all existing pins. Pages have at most32 entries and defer a loadable row to the next page when the unchanged128KiB aggregate value budget is full; each loaded value is at most16KiB. A genuinely oversized item remains explicit and advances.

Each request uses the existing fresh supervised worker and fully validating pinned Reader. The24.5KB M15 section is a bounded semantic object; it is not the full saved response. For the large owner-chain sibling, the already-existing optional scan observer captures only the one fixed reference span during the Reader's original full scan. No additional Reader hook or whole-owner-chain object parse is introduced. Only after full manifest/content/response/index verification is the small reference slice hash checked and parsed. `plan_reference.source_span` hashes the complete original reference; `plan_reference.value` is its metadata projection, so do not hash the projected value as if it were the full source slice.

Original Reader/process/profile budgets, the256KiB HTTP cap, read-only restrictions, default non-observed Reader, and existing announcement/rebound contracts remain unchanged. No owner run, collection, cache, publication or GET write is added.

## Existing-environment start and focused checks

Use the complete fixed repository and the existing saved-view config/dependencies. No config or dependency change is required. Keep the accepted54780 preview until candidate acceptance.

```sh
PYTHONPATH="$PWD/V5/src" "$PYTHON" -B -m v5_shadow.module_api \
  --config "$SAVED_VIEW_CONFIG" --port "$API_PORT"
cd frontend
npm run test:p0
npx --no-install vitest run src/views/SavedManagerResultView.spec.ts \
  src/manager-selection/usMappingCoverage.spec.ts
npx --no-install vue-tsc --noEmit -p tsconfig.cloud-product.json
npm run build
V5_MODULE_API_ORIGIN="http://127.0.0.1:$API_PORT" \
  npm run preview:p0 -- --port "$UI_PORT" --strictPort
```

Focused real acceptance: descriptor/overview, announcement default, new M15 page4 exact relationships/3 HK, original dates/cutoffs/counts/statuses and explicit finite scope, exact original row slices/SHA and owner reference span/status, then rebound first page/return and announcement return. Preserve stocks/market_screen and all safety flags. Record fresh worker exit/reap/resource limits and saved file hashes/mtimes unchanged. Do not rerun collection or algorithms, attach an oracle to the service process, or take the user's browser/window control. Build matching assets; old assets lack this tab. Switch the preview only after success and retain rollback.

Cloud synthetic Node/DOM/API evidence is in `VALIDATION.json`. Cloud Vue/typecheck/build remain NOT_RUN because their existing binaries are absent. Mac real and browser validation are separate gates. This connects the saved research view and does not establish complete module readiness or formal stock eligibility.

# Same-run M13 announcement research on the ordinary V5 page

This increment connects the already-consumed announcement research in the saved run to the existing V5 page. It preserves the complete V4-derived frontend and the accepted `cff144` read-only page-process memory fix. It does not rerun M13 or replace the empty top-level manager `stocks`.

## Small integration

- `/` and `/manager-selection/` retain the exact default run `46596b03c2ab4e29b1219fd2e5eb698f`. If the saved overview contains `announcement_reviewed_analysis`, the first visible business view is now its announcement research references. The original manager saved sections remain one click away. The run identity panel is collapsible to keep research content visible.
- The established V4 `frontend/src/manager-selection/announcementAnalysis.ts` stock, reason, risk and related-article renderer is reused. Only the saved field names are adapted: `research_status` to `status`, `article_refs` to `articles`. No classifications or selection reasons are recalculated. The full older renderer remains available and unchanged.
- Cards show stock code/name, research status, original selection reasons, risk notes, related announcement facts, separate publication/target/review/availability dates, and existing source codes/hashes. Consumed references do not contain source URLs; the page explicitly says that links were not provided and constructs none.
- PIT `CANNOT_CONFIRM` and eligibility `NOT_ASSESSED` stay conspicuous. Product `READY`/`CONSUMED`/`VERIFIED` are saved consumption/validation states, not formal stock recommendations or trading permission. Product counts and cutoff metadata are original fields, not counts inferred from the current page.

## API contract

The existing explicitly configured GET `/api/v4/manager/m18/v2/sections` accepts one additional closed selector:

```
?run_id=<exact run>&generation_id=<exact offline generation>
&section=announcement_reviewed_analysis&projection=announcement_references
[&cursor=<opaque cursor>]
```

It uses the same pinned, fully validating Reader in one fresh supervised read-only worker. Only the validated announcement section is additionally parsed; it never calls `Reader.full_response()` or sends the large section to the browser. The existing object/depth/node/resource budgets remain unchanged. No Reader cache, worker pool, file mutation, publication or owner action is added.

The response retains the existing detail schema, identity/generation/profile/manifest, section/cursor/offset, and bounded entry envelope. It adds `projection: announcement_references` and `announcement` metadata (`status`, `plan_cutoff`, `gaps`, `reference_count`, `source_section_sha256`, and whitelisted original product metadata excluding the duplicate reference arrays). Entry SHA and byte offsets refer to the original saved response spans. Opaque cursors additionally bind the projection and source section SHA and cannot be replayed against ordinary sections.

Pages remain at most32 entries, a loaded row16KiB, total loaded values128KiB, HTTP256KiB. Larger values retain `NOT_LOADED` and the original hash/byte count. The client validates projection and metadata totals rather than confusing the one container object with its nested reference count. Latest-request-wins, failure clearing and previous/next navigation are retained.

## Source evidence versus execution evidence

Mac read-only inspection reported the saved object is921000B, its outer references147 (103 SELECTED +44 CONDITIONAL_WATCH),459548B total, max13094B for one reference. Product counts are280 stocks /103 selected /44 watch /79 not selected /54 not assessed from383 announcement records. These are supplied real-source findings, not cloud fixture claims. This candidate's real HTTP, build and preview acceptance remains pending until separately recorded by Mac.

## Existing-environment run and tests

No dependencies or configuration fields change. Use the complete repository at this fixed candidate commit and the existing authorized Python/Node environments. Retain the same saved-view config, data pins and `/overview` + `/sections` routes.

```sh
PYTHONPATH="$PWD/V5/src" "$PYTHON" -B -m v5_shadow.module_api \
  --config "$SAVED_VIEW_CONFIG" --port "$API_PORT"
cd frontend
npm run test:p0
npx --no-install vitest run src/views/SavedManagerResultView.spec.ts
npx --no-install vue-tsc --noEmit -p tsconfig.cloud-product.json
npm run build
V5_MODULE_API_ORIGIN="http://127.0.0.1:$API_PORT" \
  npm run preview:p0 -- --port "$UI_PORT" --strictPort
```

Open the ordinary root or `/manager-selection/`. A query string is optional for the default exact run. The existing preview must switch to the new built assets and candidate backend only after the focused tests pass; the old b2a assets do not contain this announcement integration.

Focused real acceptance: use a fresh standalone API, inspect descriptor/overview, then all5 announcement pages for the147 references while respecting the existing caps. Verify identity, product SHA, source section SHA, cursor offsets0/32/64/96/128 and original research statuses/reasons. Check original stocks remains[], ordinary gap reading still works, and saved-data hashes/mtimes are unchanged. Record worker exit/reap and original limits. Do not construct an oracle in the service process. The user is operating the Mac screen: perform background tests without taking control of their browser or moving windows.

Cloud results and exact commands are recorded in `VALIDATION.json`; Vue/Vite execution is NOT_RUN in this cloud workspace because their existing dependencies are absent. Linux synthetic/Node/DOM evidence does not assert real Mac or browser success.

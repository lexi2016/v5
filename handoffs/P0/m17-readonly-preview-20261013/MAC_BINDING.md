# P0 M17 exact-run preview wiring

Implemented by the dispatch-side continuation. Neither the original P0 Chat nor the original M17 Chat authored this continuation. This is a fixed-source candidate for separate Mac acceptance; this delivery does not deploy, collect data, run an owner, register natural execution, or alter V4.

## Fixed inputs

- P0 implementation base: `ba8128830b1422e669f9f6d872e251a8d5a6e1cc`.
- M17 read-only adapter: `64e112573eb5cbac47ff2db1dd0887f459f38213`, under `integration_candidates/M17_READONLY/after/V5` on its original module branch.
- The integrated adapter, its 13-test suite and inactive binding example are byte-identical to those fixed M17 blobs. The 34 other original dependency files match P0 byte-for-byte. P0 keeps its own shared `module_api.py`; the standalone candidate's old dependency copy is not substituted.
- Existing reuse evidence: `handoffs/P0/feedback/mac-m17-existing-reuse-20261013/report.json` at the P0 parent. No real response body or filled private binding is published here.

## Bind a task-local copy of the existing source API config

1. Preserve every existing route and binding in the existing `source_bundle` module API configuration, including M06/M08/M09/M10. Do not use or overwrite the manager/M18 configuration.
2. Add `/api/v5/manager/close-recapture` once to that source config's `routes` list.
3. Add `m17_close_recapture_binding` with the object from `V5/examples/m17_readonly_binding.example.json`. Fill only its four path placeholders with the already verified independent V5 M17 state, external universe, daily ledger and existing Python interpreter. Do not publish the filled config or change the seven original ledger identity fields.
4. Use the existing source API loopback origin for `V5_SOURCE_API_ORIGIN`. The new Vite route uses that origin, strips cookies/authorization/origin, and works in both dev and preview. It is separate from `V5_MODULE_API_ORIGIN`, which retains the existing M18 proxy. No proxy implies no binding and must not be reported as successful data.
5. Use the Mac's existing locked frontend dependencies to run the checks below before updating the authorized V5 preview. Keep the current V4 process untouched. This document does not itself start/restart services.

The required GET is:

`/api/v5/manager/close-recapture?source_trade_date=20261012&run_id=ca2c344b61334ad28f4b6146117643cd`

Only these two scalar string query keys are accepted. No latest/date fallback, limit parameter, slot=1530, mutation method, owner/collector or ledger writing is reachable through this route. Missing binding/record rejects as CANNOT_CONFIRM; corrupt/mismatched products reject rather than producing empty READY data. The M17 reader has its own single non-queuing read slot so a second concurrent GET returns 503 MODULE_BUSY without starving the four other module routes. Each accepted GET uses a new isolated original reader with a 30-second subprocess timeout and a 256-KiB response cap; a reader timeout rejects the request, never triggers collection or switches date/run. The browser cancels the previous read on repeat load and on unmount, and ignores old completions. The display remains bound to the original captured/available timestamps, regardless of the current wall clock.

## Separate Mac verification

- Check source API and proxied preview GET return JSON, not Vite HTML, and refer to the fixed candidate release. The prior deployed 54780 snapshot was `08c101d6e7f53d1d1519c3859c6b1d985c32d221`; this document does not imply it changed.
- Snapshot hash and mtime for state, external universe and ledger before and after repeated GETs. Expect no changes and exactly the original single successful ledger attempt.
- Verify source date 20261012, plan date 20261013, run `ca2c344b61334ad28f4b6146117643cd`, 100 original rows, four original file hashes and pool identity matching the original reuse evidence.
- Verify original capture time `2026-10-12T15:55:15.370877+08:00`. This is a historical saved-product reuse, not a new capture, natural-run proof, or historical 15:30 result.
- Confirm UI MANUAL_RECOVERY, EXISTING_VERIFIED_PRODUCT_REUSE, RESEARCH_ONLY=true, natural_verified=false and all production/buy/order/formal flags false. Currency and turnover units remain unverified; do not convert original amounts to assumed units.
- Confirm the independent M17 card/table appears in SourceBundleStatus inside the default saved-manager view; M18 keeps its own run `46596b03c2ab4e29b1219fd2e5eb698f` and three strategies. Old `managerWorkbenchResearch.ts` is unchanged.
- Wrong date/run, malformed/oversize data and failed refresh must remove prior rows and show CANNOT_CONFIRM. Repeated click, changed inputs and unmount must not publish a stale response.

## Verification commands

The fixed upstream adapter already passed its 13 checks and real saved-product acceptance on Mac; feedback commit: `f350602512ee14f825bb53a976fbaada93a0b921`. Do not repeat that completed adapter suite. For this P0 candidate, run only the new HTTP seam from V5: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests python -B -m unittest test_m17_readonly_api -v`. The cloud combined 22-check command remains recorded in VERIFICATION.json as completed evidence.

From frontend: `node --test tests/closeRecapture.node.mjs tests/sourceBundle.node.mjs`, `npm run typecheck`, and `npm run build` using the existing dependency lock. No dependency or lock upgrades are required. Run targeted component checks if the local Vitest toolchain is available.

Cloud results and NOT_RUN limits are recorded in `VERIFICATION.json`. Synthetic cloud success does not substitute for the separate real-product Mac and preview checks. Do not rerun the old M17 owner/collector or old 17/9/18 suites for this read-only wiring.

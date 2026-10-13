# M04 independent capture and ResearchLane candidate

## Scope and attribution

Original branch base: `8261160018537c71de0af17584d371a2d31913c8` on `dev/m04-github-handoff-20261011`. The original Chat already delivered the complete durable ingest bridge at `8a3c1d2013e34b7e070fd924e1ee754f7dfd8de7` and the historical 18-article readback. Those are not new contributions and are not rerun here. The known 53 out-of-scope read errors and missing historical acquisition clocks remain intact.

This candidate adds only independent configuration/launch, explicit capture/recovery, body/source-time references, and an EXACT/LATEST read adapter for the distinct ResearchView. It does not change the P0 shared API/UI, V4, trading/risk semantics, active configuration, or any original algorithm. It does not implement all M04/M11 lanes or claim module acceptance.

The unchanged original producer, collector, builder, archive store, durable ingest, and independent reader are packaged in `source/V5`. The original producer previously lacked its default pure analyzer in this module bundle. This adds the exact `upstreams/shared_research/__init__.py` and `v3_zsxq_adapter.py` from V4 fixed `f7cb731c384ee6890a87d16c19a5b5a621779477`, under `handoff/v4-running-source-20261005/canonical/`. The analyzer SHA-256 is `23d79572bcbb979e7dc81db44c7e5854ad2ac670c45c52399f2e630f7ae1ee57`. It is a pure topic analyzer, with no model, fetch, push, image, or legacy-state writer. Structural infrastructure dependencies are original bytes, including the previously documented `_namespace.py` mapping. The receipt-bound producer itself is unchanged.

All packaged files are hashed in `RELEASE.json`, excluding the manifest itself. `PROVENANCE.json` identifies original Git blobs and new files. The launch path verifies all hashes before any action. Run from any working directory without a V4 service, PYTHONPATH, or implicit V4 source/data path.

## Existing dependencies and checks

Use the already approved interpreter/dependencies. Original declaration remains Python >=3.14, pandas >=2.3,<3 and pyarrow >=21,<25, unchanged. No installation is performed. The original analyzer retains its stock lookup errors/health in the captured summary; lack of pyarrow or an inadequate selector is not converted into verified security identity or strategy eligibility.

    PYTHON_BIN=/absolute/existing/python sh /absolute/package/test_offline.sh

Only this candidate's new tests run. The test wrapper clock is fixed to an elapsed slot on the actual Shanghai day so the offline test is not time-of-day dependent; the frozen producer still measures its own acquisition clocks. They use a synthetic, local pinned CLI executable, the real frozen producer/default analyzer, original builder/import, and independent cold reader. No real provider/model/credential access. Historical 18-article acceptance and the original 53 scope errors are not retested as real data. A synthetic v1 archive uses the original store and 53 intentionally unmaterialized manifest references to test scope handling.

## Independent configuration and launch

Prepare `config.example.json` locally with real absolute paths and SHA-256s. The runtime root must be an existing empty directory, independent of the package; input snapshots and CLI must be outside it. The CLI is the existing explicitly approved official ZSXQ executable; no CLI or credentials are discovered, installed, copied, saved, or granted. The selector must be an authorized independent migrated snapshot. Do not point to live V4 output roots. The sample placeholders intentionally fail validation.

    PY=/absolute/existing/python
    APP=/absolute/package/launch.py
    "$PY" -B "$APP" validate < config.json
    "$PY" -B "$APP" init < config.json

Validate and help do not fetch. Init creates only the explicit marked runtime's captures/ingest layout. No schedule is enabled. A new acquisition requires the explicit capture command and execution flag, plus separately applicable authority to use the existing CLI/source. Source-branch authorization does not grant real acquisition permission.

    "$PY" -B "$APP" capture --date YYYYMMDD --slot 0900 --run-id UNIQUE_ID --execute-acquisition < config.json > result.json

Only current Shanghai date and an elapsed original 0830/0900…2300 slot are accepted. A delayed manual capture keeps real receipt clocks; it is not a natural/on-time run or a PIT claim. Each new run has its own marked capture root. The original producer receives every path explicitly, so its legacy defaults are unused. Original pages/summary/status/receipt are retained; original ingest publishes into a sibling independent state root. `result.json` carries the immutable `archive_binding`.

## Recovery, stop, and rollback

This is a one-shot process, not a daemon. SIGINT/normal process termination stops the invocation; retain its root. A per-runtime writer lock prevents overlapping capture/resume. Reusing a capture ID with a different date or slot is rejected. Wrapper checkpoint writes are atomic and no-replace, so interruption cannot expose a half-written final request/result receipt. No claim deletion or automatic recapture is used.

    "$PY" -B "$APP" resume --run-id UNIQUE_ID < config.json > result.json

Resume performs no CLI, model, or network call, even if the CLI/selector has since gone away. The config identity must remain the same. It reads the original committed status/receipt, derives the exact pinned request, then calls the existing durable ingest. It does not manufacture clocks.

| Condition | Behavior |
|---|---|
| Config/CLI/selector pin invalid before claim | Refuse before capture; correct the explicit config and retry |
| Original status committed but wrapper request receipt lost | Reconstruct request from original pinned status/receipt; no fetch |
| Original import succeeded but wrapper response lost | Existing ingest validates/reuses original success; no new import |
| Checkpointed builder plus incomplete import | Existing ingest revalidates builder and uses fresh private import root |
| Original status missing after started capture | CAPTURE_INCOMPLETE; retain evidence, review before explicitly choosing new run |
| Incomplete original builder guard | Preserve original blocking reason; no guard removal or blind rerun |
| Hash/tamper/concurrent writer | Refuse; previous saved success remains unchanged |

Rollback is to stop selecting this candidate and keep the previous M04 binding/release in P0. No publication pointer is changed here. Do not delete partial attempts or rewrite prior success. Actual preview publish/rollback belongs to the one P0 owner and is not executed by this package.

## M13/M15 and ResearchView read contracts

The M13/M15 material view accepts only the original `{"root": absolute_path, "files": {relative_path: sha256}}` binding, from a saved result or an approved migration. It invokes the original independent reader before returning the original body and original article, exact archive file/SHA, published/retrieved/available times, and full source binding. Missing clocks remain null or literal UNKNOWN; `acquisition_status=UNKNOWN` is never filled from publication/file mtime. Formal source/issuer/PIT eligibility still belongs to the unchanged consumer.

    "$PY" -B "$APP" read < binding.json

The distinct ResearchView contract is implemented at `research_lane.py::research_lane(binding, query)` and the side-effect-free CLI below. Query is exactly `{}` for LATEST or `{"research_date":"YYYYMMDD"}` for EXACT. LATEST chooses only explicitly pinned daily archives, never unmaterialized manifest references. EXACT missing date returns NOT_MATERIALIZED for that requested date, never falls back.

    "$PY" -B "$APP" lane < binding.json
    "$PY" -B "$APP" lane --research-date YYYYMMDD < binding.json

The response schema is `v3_5.research_lane.v1`, status LIVE_PERIPHERAL_ONLY for a valid selected archive, and a distinct `archive_materials` block with original articles, count, clocks status, source reference/SHA/date. Original source run comes only from a bound acquisition receipt. If the original v1 archive has no provable run field, source_run_id is null with M04_SOURCE_RUN_UNKNOWN. No manager run is invented. Missing morning/news/wechat/zsxq/day-product/timeline lanes are omitted and M04_OTHER_LANES_NOT_CONFIGURED remains visible. The original archive's cannot_confirm/status are retained. This is not an hourly-ready or whole research-lane success claim.

Out-of-scope reader errors are returned verbatim in `out_of_scope_record_errors` rather than hidden or counted as success. An error in an explicitly bound selected archive is fatal. The original 18-article binding can be consumed without refreshing or relabeling its date. P0 alone integrates the ordinary `/api/v5/research/lane` route, view navigation, and preview; this candidate creates no server or route side effect.

## Mac handoff and remaining acceptance

Fixed candidate source and manifest must be read back first. Use a new isolated root with the existing interpreter, run only `test_offline.sh`, and test help/validate/read/lane from a directory outside the checkout. Do not repeat the historical 18-article verification or broad 53-error original suite. New tests are synthetic; real CLI/source/selector credentials and providers are not authorized by this handoff. Do not point to V4 active roots, modify application write gates, restart services, or publish a preview.

Current verification: see `TEST_REPORT.md`. Locked dependency acceptance, real acquisition, real ResearchView HTTP/DOM/native visual, deployment, schedule/natural follow-through, all research lanes and whole-module acceptance remain NOT_RUN unless separately recorded. No actual private body/input data is included in GitHub.

# M11 backend integration candidate — NOT_DEPLOYED

Scope narrowed by the parent task: private backend service/API and existing scheduler contracts only. No new UI, no shared source replacement, no P0 changes, no GitHub action and no deployment have been performed here.

## Delivered entry points

- `after/V5/src/v5_shadow/m11/service.py`: default real `daily.capture` / `daily.generate` invocation, immutable-capsule same-run readback, durable opaque jobs, async POST, read-only GET, process lease and descriptor-safe job I/O.
- `Service.dispatch_due(now=None, trading_dates=...)`: register this callable in the existing approved scheduler composition; the caller supplies its pinned real trading-date evidence. It only considers 09:25, 09:35, 10:00, 11:30, 14:00, 15:00 Asia/Shanghai, only that day, and the owner's inclusive integer-minute 0..8 boundary. Thus +08:59 is admitted, +09:00 is not. Default clock is actual UTC now. Original capture still owns actual calendar/previous-session verification; a date list cannot override its refusal. Never call with a synthetic historical clock in production. There is no automatic daily-generation scheduler.
- CLI: `python -m v5_shadow.m11.service --settings /absolute/operator-approved/m11-service.json --settings-sha256 <verified-sha256> --port <approved-unused-loopback-port>`.

## Required startup settings

Exact keys: `schema` = `v5.m11.service.v1`, `job_root`, `plans`, `trading_dates`. Every plan has exact keys `binding`, `target_date` (YYYY-MM-DD), `cutoff` (aware ISO timestamp), `sources`, `slot` (one of six strings, or null for explicit generation). Binding has the five M11Binding fields: state_root, archive_root, config_path, config_sha256, owner_manifest_sha256. Root paths must be absolute, separate module-private roots; job_root must not overlap config/state/archive. A source must include sha256, event_time, published_at, observed_at, available_at; original timestamps are retained and must satisfy event/published/observed <= available <= cutoff. The startup settings bytes must match the externally supplied SHA256. No fictitious active bindings are supplied.

## API / gateway registration

Add only these three routes to the integrator's verified active gateway config under a new dedicated `m11` module, using the selected loopback port, timeout_seconds 2, max_inflight 4 and the actual release identity. Run existing `api_gateway.validate_config` before activation. No shared Python patch is necessary because the frozen gateway already dispatches exact config-defined routes.

- GET `/api/v5/m11/day?date=YYYYMMDD`: date-scoped job metadata and independently re-read committed capsule projections.
- GET `/api/v5/m11/job?job_id=<32-lowercase-hex>`: fast job state; never generates.
- POST `/api/v5/m11/generate`: exactly `{"date":"YYYYMMDD","intent_id":"<32-lowercase-hex>"}`. Explicit request only, response 202, background owner execution. Paths, providers, source data, replace, reset and credential parameters are rejected.

Client retains an intent ID for retries of the same click; intentional new generation uses a new ID. Same intent/binding is deduplicated. Changed binding with same intent is refused. Interrupted jobs become ATTEMPT_UNKNOWN without GET writes and block new attempts on that date/operation/slot. No marker deletion/reset route exists. A fresh explicit attempt is allowed only after COMMITTED or proven FAILED_NO_REQUEST / owner_called false; owner remains final authority. Scheduler reuses a deterministic intent and does not automatically retry even FAILED_NO_REQUEST. Operator may invoke the existing owner retry contract explicitly after review. Different jobs run in a two-worker pool; the same date/operation/slot never overlaps. Ordinary GET stays independent of slow generation, but immutable readback itself is synchronous and bounded by the owner's local reader.

Owner statuses and missing slots are preserved. COMMITTED and VERIFIED_PERSISTENCE_ONLY mean verified storage, never global PIT/READY promotion. Global PIT is always CANNOT_CONFIRM. Owner path/root/provider/secret-like keys are stripped from browser payloads. M04 eight-slot contracts, M09/M10 review fields, original ReviewView and original review_router are untouched. UI/P0 wiring is deferred.

## Application and rollback

1. Install and verify the parent M11 owner/capsule runtime first; preserve V4.
2. Verify `CHANGE_MANIFEST.json`, apply `runtime.patch` in a separate candidate tree, rerun tests with parent V5/src on PYTHONPATH.
3. Integrator supplies real approved settings, fixed verified V5 build manifest and independent SHA pins. Wrong source pins remain BLOCKED. No request occurred in these tests.
4. Start private service on an approved unused loopback port. Register the three routes and, separately, the approved six-slot callback in one controlled integration window. The service CLI itself does not start scheduling.
5. Verify actual input -> original owner -> immutable capsule -> new-process readback -> same-run HTTP. Mac, natural slots and full acceptance remain NOT_RUN here.
6. Rollback: unregister only M11 routes/callback, stop M11 service, preserve all job/capsule records, then apply `reverse.patch`. Never delete unknown attempt markers or revert V4/shared modules.

## Verification limits

18 candidate contract tests passed. Most tests inject a small fake owner to test orchestration and do not represent market/provider/model evidence. Default paths call the parent real owner and parent capsule reader without requiring injection. Parent owns full backend regression and real-owner chain verification. No frontend tests/build, Mac execution, provider calls, natural trading evidence or live route registration took place. Real source settings and approved build pins are deployment prerequisites, not substitute fixtures.

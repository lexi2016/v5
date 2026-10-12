# M17 exact-run read-only adapter

This candidate was implemented by the dispatch-side continuation. It is not attributed to the original M17 Chat. No main/shared module API, frontend, route registry, production configuration, V4, credential, permission, trading or collector changes are included.

## Entry points

- `v5_shadow.m17_readonly.get_response(binding, query)` returns the payload dictionary.
- `query` must have exactly two scalar strings: `source_trade_date` and `run_id`.
- `read_m17(binding, *, source_trade_date, run_id)` is the equivalent lower-level function.
- Intended GET path: `/api/v5/manager/close-recapture`. This candidate does **not** register it.
- Exceptions reject the reference; the host must not substitute another date/run or fall back to collection. CLI failure returns exit 2 and a generic path-free REJECTED response.
- Response limit is 262144 UTF-8 bytes; no pagination, arbitrary limits or mutation verbs.

## Binding

All fields are mandatory; extras are rejected:

`schema_version` = `v5.m17.readonly-binding.v1`; `state_root`, `universe_root`, `ledger_root`, and `python_executable` are explicit absolute local paths. The three data roots cannot overlap and require the original existing M17/ledger markers. Both existing real and synthetic M17 markers are supported; execution_kind is preserved from the original ledger.

`identity` contains exactly the original seven ledger fields: lane, target_date, input_sha256, research_cutoff, code_sha256, config_sha256, dependency_sha256. Lane must be manager_close_recapture. Target is the **source** date. `run_id` is the exact successful original ledger run ID. `execution_label` is MANUAL_RECOVERY and `operation` is EXISTING_VERIFIED_PRODUCT_REUSE; these describe this display/reuse operation, not the original acquisition.

The example has the verified existing ledger identity and placeholders for private roots. It is deliberately inactive and must not be bound globally by this task. Fill only a task-local copy with the previously verified independent V5 roots and existing interpreter. Never copy production data to this candidate or publish filled private paths.

## Read chain

Original `run_ledger.read_run` reads the seven-identity state without creating locks/directories. The requested exact run must be a SUCCEEDED, readback-verified attempt matching latest_success and its original product reference. A fresh `python -I -B` process uses the frozen original 24-file owner/reader closure and `ManagerWorkbenchResearchReader.read_close_recapture(source_date)`. It cross-checks the external pool with original `_read_close_recapture_pool`, and reads all four product files before/after original validation. Hashes, pool, dates, capture/availability, status, candidate count and cannot_confirm must match the original ledger. The parent rereads the ledger and rejects changes.

GET never invokes claim_run, finish_run, recapture_close_minutes, runtime collection/probe, or ledger writes. Existing original reader audit guards are reused; this is not OS sandbox certification. Original rows are retained except private absolute paths are redacted. The adapter never imports arbitrary modules or accepts worker/owner code from binding.

## Response

`schema_version=v5.m17.readonly-response.v1`; status READY or PARTIAL preserved. Fields: source_trade_date, plan_trade_date, run_id, identity, execution_kind, execution_label, operation, captured_at, available_at, received_not_historical_1530, candidate_count, rows, files, pool, cannot_confirm, bar_window, coverage, source, reader_pid.

`files` has artifact, receipt, snapshot, candidate_overlay, each `{artifact_ref, sha256}`; all refs are relative. `pool` is the original frozen D1 pool reference including its three hashes. `rows` are the original validated candidate overlay rows, never manufactured from pool entries. Reader PID is diagnostic, changes on each GET and is not a stable business identity.

Always: RESEARCH_ONLY=true; production_allowed=false; buy_gate_updated=false; orders_sent=false; natural_verified=false; formal_eligibility_verified=false. Currency/unit remains UNKNOWN/unverified. No 1530/historical close, formal eligibility, continuous tracking or natural execution is claimed.

## Fixed sources and integration

`SOURCE_CLOSURE.json` pins every dependency blob and SHA-256. The 24 original vendor files, owner and ledger come from P0 5eb5f29fb5ee9c96fbbdd8d7db3aaa905f2c5509. The candidate's unchanged lightweight `module_api.py` comes from M17_REAL 6f1a70d9ce5cc1dd759347a3ff6fad7a0c06117f, avoiding unrelated P0 optional imports. It is only a standalone dependency copy, **never** a replacement for P0's live shared module_api.

`after/V5` is a complete isolated runnable source closure. `forward.patch` adds only the three new adapter/test/example files and `reverse.patch` reverses those additions. The remaining `after/` files are immutable dependencies, not integration overwrites. A P0 host should invoke the fixed isolated candidate CLI if it cannot load the module without replacing shared dependencies.

## Commands from repository root

Run only the new synthetic suite with the existing interpreter:

`<EXISTING_PYTHON> -I -B integration_candidates/M17_READONLY/after/V5/tests/test_m17_readonly.py`

Read the verified existing real run after preparing a task-local private binding:

`<EXISTING_PYTHON> -I -B integration_candidates/M17_READONLY/after/V5/src/v5_shadow/m17_readonly.py --config <TASK_LOCAL_BINDING_JSON> --source-trade-date 20261012 --run-id ca2c344b61334ad28f4b6146117643cd`

The Mac acceptance must snapshot SHA-256 and mtime for state, external universe and ledger before/after; confirm READY, 100 original rows, four hashes matching feedback ba8128830b1422e669f9f6d872e251a8d5a6e1cc, original capture 2026-10-12T15:55:15.370877+08:00, source 20261012, plan 20261013, and all risk boundaries. Do not rerun the owner/collector or old 17/9/18 suites. Cloud tests are synthetic and do not substitute for Mac acceptance or preview deployment.

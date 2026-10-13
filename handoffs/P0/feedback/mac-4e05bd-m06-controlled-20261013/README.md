# Mac M06 pinned-venv repair and one controlled existing-pool execution

Candidate `4e05bd422d1f6bdedb7bff8b2faf5218fac9e58a`, parent `1ad98175e582ccc39e350341f97f5c9f9a97fa4e`, branch `dev/v5-main-integration-20261012`.
147-entry source closure SHA256: `dae57f54bedc7632b4beafa9cd29fb2158db83162ac3d7bacdace2bf9fe1a1e4`; verified before and after execution. No product files changed.

## Engineering checks

Only the new `test_m06_python_launch` suite ran under existing HK02 Python: **14 PASS**, 5.856 seconds, exit 0, UTC 01:35:23.590557–01:35:29.556457 on 2026-10-13. Exact command and environment are in execution.json. Old 21/85/M17 suites were not rerun. No packages, venv files, links, permissions or system configuration changed.

The actual venv launch leaf was retained; binary bytes, final realpath, pyvenv.cfg and link-text hashes were registered using the handoff's read-only pin logic. Actual paths remain private; python-pins.json contains aliases and hashes. The candidate accepted registration and verified child launch/prefix identities. The resulting original M06 code, config and dependency hashes match the prior legal HK02 result; new input and research-cutoff identities differ intentionally for this newly authorized controlled publication.

## One successful controlled owner call

Per the latest explicit task instruction, this run used **new independent P0 ledger and new independent M06 output/ledger**, new observed admission and actual future completion cutoffs. This supersedes the handoff paragraph suggesting retention of the old cutoff and old owner receipt. No old clock, pool or ledger was changed or deleted.

- Target 20261013; signal and eligibility 20261012; MANUAL_RECOVERY; EXISTING_VERIFIED_POOL.
- Admission UTC `2026-10-13T01:37:45.989496+00:00`.
- Completion cutoff UTC `2026-10-13T01:52:45.989496+00:00`; successful execution finished at 01:40:02.155166, before that cutoff.
- Explicit slot UTC 01:37:44.989496–01:57:45.989496, half_day_bound=true, max_attempts=1. No scheduler was installed or enabled.
- Original `main_runtime.tick → daily_tick.tick → daily_dispatch.dispatch_due → original produce_hk02_daily → fresh original reader` completed the M06 lane. Both ledgers contain exactly one SUCCEEDED attempt with verified readback.
- P0 run UUID: `b1ee95c077be4e05871dcec557071e26`.
- M06 run UUID: `cad577f7ddaf4cc28e6c3b9ac93087e3`.
- Publication digest: `08526bffcf945a122afff8f69e38e7a54ee6a13371afd2b7e6100adf3c02e4cc`.
- Producer PID 49775 and reader PID 49815 differ; 100 rows, fixture_only=false, model_weights_reverified=false, natural_verified=false. The source pool reference is exactly the already verified existing pool. owner_reused=false means this new isolated M06 ledger published its first receipt; it does not mean model recomputation occurred.

The top-level tick label remains DISPATCH_ATTEMPT_ONLY. M06 succeeded; the intentionally absent manager request returns BLOCKED_POST_OWNER_REQUEST_MISSING. This is not whole-system or manager acceptance.

## Observation and the initial harness failure

The first tick stopped before any ledger claim or owner call: the task observer tried writing its profile inside the original reader's guarded process and correctly received A_WORKER_WRITE_DENIED. That is a harness error, not a product failure. initial-observer-block.json records the failed command/time/exit. A read-only uninstrumented inspection passed. Only the task observer was corrected to return profile summaries on stderr, with no relaxation or bypass of the original write boundary. A read-only profiled inspection then passed. The failed path was continued once; the original owner ran exactly once across the attempts, and neither ledger contains retries.

The recursive observer executes unchanged scripts through runpy, retaining the existing interpreter, isolation flags, original script argv and input envelopes. It records function calls and Python child launches; model generation/scoring and socket connect/DNS attempts are guarded. It does not alter product return payloads, source, input data, identities or gate logic. Corrected controlled execution covered **34 processes / 33 child launches**, with zero child failures, exactly one original owner call, zero original generation-worker launches, zero model generation/scoring/load calls and zero provider network attempts. See profile-summary.json. Raw profiles contain private paths and remain on the Mac.

The original 18 input/asset files, old M06 output, live preview configuration and preview dist were protected by before/after hash, size and mtime comparisons: **73 files unchanged**. Existing ports 8873, 8910, 54777, 54778, 54779 and 54780 remained listening; preview 54780 retained PID 40161. No service was started, stopped or deployed. Private configuration stays on Mac and an explicitly disabled copy is retained.

This establishes the 14 new engineering checks and one controlled P0 existing-pool execution only. Real model generation, provider collection, natural scheduling and overall 18-module/P0–P5 acceptance remain unverified.

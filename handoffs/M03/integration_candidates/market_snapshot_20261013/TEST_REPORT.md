# M03 A2 actual verification — 2026-10-13 UTC

## PASS / FAIL / NOT_RUN

- Environment: Linux/POSIX Python 3.12.14; existing standard library only. No package installation.
- Initial intended **RED / FAIL**: `IndependentMarketCaptureTests.test_market_only_capture_routes_to_independent_collector` against unmodified R14 failed because `market_snapshot_only` was absent from `USSourceRequest`. This was observed before integration; the test subsequently exercised dispatch/serialized request. It is a feature-gap RED, not a collector success claim. A later immutable-baseline reproduction confirmed the same failure without swapping candidate files.
- New market-only tests: **19 PASS / 0 skip / exit 0**; latest focused run 45.445 s. Earlier development runs are not counted as additional coverage.
- Standalone entry tests: **3 PASS / 0 skip / exit 0**, 1.520 s.
- One complete affected M03 suite: **70 PASS / 0 skip / exit 0**, 140.392 s. This included all original 48 collector/transport/R14 tests plus those 22 new tests.
- After that suite was already running, one additional fault-injection test was added: `test_market_capture_recovery`, **1 PASS / 0 skip / exit 0**, 4.005 s. It ran separately; this is **70 + 1**, not a claimed single 71-test run. No runtime code changed after the full-suite launch.
- All 59 unchanged copied original runtime/test files (including all 48 owner members) match the fixed Git blobs after tests. The original descriptor remains unchanged. Candidate source has no generated `.pyc` files.
- Real provider/network requests, Mac execution, M15/P0 page deployment, actual scheduled/natural capture: **NOT_RUN here**. No actual future session was manufactured.

Commands (variables are caller-local paths, not user machine paths):

```sh
M03_FIXED_SOURCE="$CANDIDATE" python -B -W error::ResourceWarning \
  "$CANDIDATE/V5/tests/run_m03_offline_suite.py"

M03_FIXED_SOURCE="$CANDIDATE" \
PYTHONPATH="$CANDIDATE/V5/src:$CANDIDATE/V5/tests" \
python -B -W error::ResourceWarning -m unittest -v test_market_capture_recovery
```

The final offline runner now discovers all 71 tests if later rerun. Do not rerun already-passed suites merely to rename a result; Mac should prioritize the not-yet-run isolated installation/source acceptance steps.

## Actual success and refusal boundaries

The market-only success case executes the original public `run_us_source`, real child chain, independent collector child, original guarded HTTP transport with a synthetic Proxy response, original producer, original store persistence, separate unmodified cold reader, stable three-file copy and original binding/revalidation. Only the existing clock/opener test seams are injected. There is no fake READY object, no mocked store/readback, and no substitution of the original producer result.

Actual observed counts: quote 1, RSS 0, direct 0, real socket 0. Successful original snapshot has 33 quotes and 24 canonical rows. Actual synthetic capture time is 20:16 UTC, distinct from the 20:20 cutoff. Original schema, complete safety flags, source-response evidence and quote arithmetic survive original validation. The zero-news envelope is explicitly NOT_REQUESTED while the actual snapshot is READY.

Verified refusals cover: no capture authorization; actual capture after cutoff; out-of-window and closed/not-due session; mismatched session and invalid booleans; stale provider session; HTTP 503 and proxy CONNECT 403 without direct fallback; changed owner bytes; unknown caller clock/provider fields; payload/receipt/manifest tamper and missing member; prior-success preservation; controlled late success and expired late refusal.

Verified persistence/recovery:
- Capture and snapshot have identical raw three-file bytes and binding hashes name that read snapshot.
- Pure cold read leaves artifacts unchanged; same complete request reuses its binding without another collector or quote request.
- A complete saved capture can populate a new snapshot/binding after strict original readback; malformed or partial capture is never repaired by another quote request.
- The extra response-loss test really lets `capture.main` complete original store publication, then exits the collector child with code 17. R14 returns COLLECTOR_FAILED with no snapshot or success binding. Repeating the bounded original request cold-reads the saved triplet and succeeds with quote counts `[1, 0]`; all saved bytes remain exact. No fake return or fake persistence simulates this effect.
- Standalone `--help` and explicit missing-source/default-no-capture requests run from outside the repository. Unknown provider/captured_at fields and a false market-only override fail rather than changing execution mode.

No full eighteen-module tests, V4 mutation, security/credential changes, real data or private machine metadata are part of this report. Raw local synthetic logs are retained outside the delivered source tree; no user input artifacts are uploaded.

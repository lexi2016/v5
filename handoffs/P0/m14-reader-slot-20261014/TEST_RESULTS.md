# Actual narrow test results

Complete before file was fetched at fixed commit 8318c3fe0a758fdf832ed790a8da82b76ce814b3 and verified as 61,692 bytes / SHA256 94c1c26a36a7d1881602b7780077c056615344bf5ab21a54bf2b749904af1d21 before testing. The exact same eight test functions ran before and after the product change.

| Command form | Source | Actual result |
|---|---|---|
| python -I -B tests/test_m14_reader_slot.py STAGE | exact before | 8 run, 4 failures, 4 pass; 4.251s; expected behavioral RED |
| python -I -B tests/test_m14_reader_slot.py STAGE | after | 8/8 PASS; 4.257s |
| PYTHONPATH=STAGE/V5/src:STAGE/V5/tests python -B -m unittest -v test_m14_saved_rebound test_module_api | after | 23/23 PASS; 13.440s |
| git apply --check/apply runtime.patch; verify after; git apply --check/apply reverse.patch; verify before | isolated one-file tree | PASS, exact bytes restored |

The first page's complete body was received before requesting its cursor successor. The event barrier deliberately holds the old handler after body transmission: before returned 200 → 503 → retry 200; after returned 200 → 200 → retry 200. Independent in-progress-reader barrier continues to produce 503, distinguishing the intended concurrency guard from the completed-page race.

The four RED failures are: next page busy; next request busy after completed error body; record retained at transmission; lack of a handler-level 256 KiB final serialized-body guard. Serialization-error recovery, disconnected-client recovery, actual-read concurrency rejection and non-M14 lifecycle controls passed before and after.

Evidence logs preserve actual test output; only the isolated workspace prefix in traceback paths is normalized to <ISOLATED_WORK>. No results/counts/hashes were rewritten. Raw local logs were retained. Fixtures create synthetic temporary data, compare its hashes before/after each case and forbid the rebound producer. The full P0 suite was deliberately not rerun; no unrelated old failures are hidden by a full-suite-success claim.

Independent focused source review additionally checked normal/read-error × header/body disconnect in four in-memory probes; it reported no blocking issue. These supplemental probes are review evidence, not part of the 31 test count or Mac acceptance.

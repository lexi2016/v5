# R07 original temporal-admission regression evidence

Baseline commit: `db2b49ca4643e715aad72eb798d78eaa11411004`.
Baseline `replay.py` blob: `6540a11ee209a1d59627c0f5166a6a471e2ad6d5`.
No implementation or production registration changed. This addition is regression evidence, not a fix or completion of R07.

## What is tested

`test_quote_time.py` changes synthetic quote timestamps before the original fixture's `RawStore.publish` generates stored artifacts and hash receipts. It does not corrupt already-published file hashes or replace the replay/admission implementation. Each test runs the existing isolated replay CLI, including original `_request`, `_snapshots` and `_admit`.

Four cases cover future-date quotes at 09:25 and 09:30–09:35, previous-date auction quotes, and opening quotes one second beyond the window. All are rejected with `BLOCKED_NEW_REPLAY`, `M07_RAW_COVERAGE_NOT_EXACT`, and false production/natural flags. `_select` follows `_admit` and is not reached on these failures. Thus the hypothesized future-update-time bypass was not reproduced; no implementation fix is claimed.

## Reproduction

Use the existing restored M07 source tree with its pinned owner closure and `V5/tests/m07_fixture.py`. From this directory:

```sh
M07_TEST_ROOT=/path/to/restored/m07 python -B -m unittest test_replay test_review test_quote_time
M07_TEST_ROOT=/path/to/restored/m07 python -O -B -m unittest test_replay test_review test_quote_time
```

Both suites passed 13 tests, without skips, including four new cases and nine existing tests. Independent review reran both. The target replay subprocess inherits `-O`; fixture generation remains ordinary Python. These are synthetic offline regressions, not real-market data or natural-trigger evidence.

## Remaining boundary

Production input provenance, a dated authorized pool, real canonical input receipts, owner/resource/lock bindings, persistent recovery authority, and shared 09:30/ten-minute sampling and lunch semantics remain unverified. This test does not grant any of them, change source admission, or connect a collector.

# M04 test-launcher portability correction

The 9736bf2e807b2aa22e2541a4375b182e1ddceb24 Mac run failed at the synthetic test CLI launcher: 8 PASS, 2 FAIL, 11 ERROR, 2026-10-13 15:42:37.805–15:42:38.369 UTC. Embedding a Python executable containing spaces directly in a shebang causes the kernel to split the interpreter path; the synthetic CLI therefore raised FileNotFoundError before the intended original-owner/recovery checkpoints. TMPDIR was valid. Mac result receipt: `m04-9736bf-isolated/result.safe.json`, 6279 bytes, SHA-256 `af64331774c519de4677ac9f530e32ab358086e1c0261582c0d87f3904f5fee0`; stderr safe SHA-256 `e56a17f1a2cbcec499cb083e17c97f42d5c64b69c6360a5fd45d4f4c1ace5dbf`. These are parent-reported receipt identities; raw Mac receipts remain with the Mac evidence owner.

Only the test launcher changed. Both synthetic CLI fixtures now use `/bin/sh` and a shell-quoted explicit exec of the existing Python executable and code. No PATH-based interpreter selection or new installation. All original production/owner/reader code is byte-identical to 9736bf. No assertion or real original-chain step was removed.

A new regression first reproduced the same FileNotFoundError using an interpreter path containing both `Application Support` and an apostrophe. After the fix it executes the real frozen capture/default analyzer/builder/import/reader chain and successful no-refetch recovery. The complete new suite then passed **22/22, 0 skipped, 38.921 seconds**, from `/tmp`; see `evidence/launcher-spaces-tests.txt`. Cloud interpreter remains Python 3.12.14 without pyarrow. This is not Mac acceptance.

Mac rerun remains pending for this correction. The original dependency declaration remains unchanged; Mac Python 3.14.6 with pandas 3.0.5/pyarrow 25.0.1 is outside the declared dependency upper bounds, so locked-dependency acceptance is still NOT_RUN. No real acquisition, model, credentials, V4 changes, deployment, or natural acceptance occurred.

## Previous candidate evidence, retained

# M04 candidate verification

2026-10-13 UTC. New candidate offline suite: **21 tests passed, 0 failures, 0 skipped**, 46.819 seconds, launched from `/tmp` through the independent `test_offline.sh`. See `evidence/offline-tests.txt`. Release file SHA verification passed before running; after adding this report/log the final manifest is regenerated and reverified. Python is **3.12.14**, below the unchanged original declaration >=3.14; pyarrow is absent. **Locked dependency acceptance is NOT_RUN**, not a passing supported-runtime claim. The original analyzer retains stock_lookup_error, with no formal issuer/selector qualification.

## Exercised actual code

Synthetic local executable transport; unchanged producer/default pure analyzer; unchanged collector/full builder; unchanged durable ingest/import/store; independent fresh-process cold reader. Body, original publication time, actual page retrieval and availability clocks, source file SHA and binding survive. Test window clock is fixed only at wrapper level to avoid a time-of-day-dependent offline gate; acquisition clocks are still the frozen producer's measured values. No dict-success owner replacement.

Capture/config pin rejection, forbidden config fields/root overlap, marked initialization recovery, writer contention, old-date rejection, duplicate-ID date/slot/claim identity rejection, no blind refetch after incomplete capture, original status response loss, original successful ingest response loss, partial wrapper-checkpoint write, immutable no-overwrite checkpoint, read hash/tamper and run-path rejection are covered.

ResearchLane EXACT/LATEST, requested missing date with no fallback, empty latest with no invented date, unknown/null/bad-date query rejection, no mutations on read, original articles/source references, v1 UNKNOWN acquisition clocks, and 53 out-of-scope original reader errors preserved are covered. The v1/53 test uses synthetic original-store publication, not the existing real 18-article batch.

The intermediate new-suite failures (missing implementation, scoped legacy fixture initially including an unaccepted lock path, then run-ID identity/partial checkpoint/null query/empty latest) were corrected and are not hidden as passing history. This final 21-test run is the evidence for the delivered runtime code.

## Not executed or claimed

No real provider/CLI source call, model, credential access, real selector qualification, actual private body upload, V4 active root/service use, deployment, HTTP/DOM/native visual, natural schedule, full research-lane coverage, or whole-module acceptance. Original 18-article readback and original full-suite scope failures were not rerun; historical evidence remains attributed to the original Chat. Formal PIT and trading flags remain false. This candidate is ready for fixed-version Mac isolated verification, not final business acceptance.

## Source-contract / healthy-Parquet increment

Cloud Python 3.12.14: 27 tests, 26 PASS, 1 SKIPPED (46.029s). Healthy Parquet remains NOT_RUN here because pyarrow is not installed. All previous 22 tests passed. Four added executable envelope tests pass, including unknown envelope through the real capture boundary with no successful status and no recovery-as-success. Before repair, the added envelope subcases produced 6 failures / 2 errors; unknown dict envelopes had been accepted as zero rows.

Mac existing 3.13.12 / pandas 2.3.3 / pyarrow 23.0.1 must run all 27, with no skips, to close the healthy-Parquet gap. No real CLI, new source acquisition, model, credentials, old 18-article rerun, full V5 dependency-lock test or deployment was performed for this increment. The 1001-row fixture is explicitly synthetic and uses selector date 20200102; assertions require the original analyzer to preserve it and report healthy lookup before body/clock/source-bound archive cold read. Full package Python >=3.14 metadata remains unchanged.

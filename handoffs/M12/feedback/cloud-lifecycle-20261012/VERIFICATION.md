# M12 lifecycle publication verification

Base: `b635878a2d34f121182e213f38e5295759bf3530`, inheriting `d68a4a8f77554df31f83765f2a25b2649dd0731d`.

## Scope

Only the M12 daily/store/reader modules and their test file change. Vendor Review Core remains byte-for-byte unchanged. Original public function signatures and reader disk layout (`video_fupan/runs/<date>/<run>/manifest.json` and `receipt.json`) remain unchanged. No shared API, page, integration branch, V4 runtime, credentials, network acquisition, or trading actions are changed.

- Bind the actual immutable owner receipt under the same private root/date/run to the exact persisted owner manifest and its SHA; cold reader repeats this validation without importing the producer.
- Promote only cold-verified owner `ACQUIRED` evidence with the original successful capture/ASR states. Preserve `ASR_FAILED`; `OK` remains normalized by vendor to `ASR_REVIEW_REQUIRED`. Top-level discovery status and `current_advanced` are never treated as success. No `gap READY` condition is added.
- Failed acquisitions remain stored/readable with `promoted=false`; they do not create or replace `latest_success`.
- Atomic temporary write/replace protects existing pointer bytes. Same-run publication does not rewrite the pointer.
- A reproduced staging-write/commit-replace failure now gets a new staging attempt on retry, preserving failed evidence. A complete run directory is committed atomically instead of moving its two files separately. Existing committed runs are never overwritten.
- Legacy envelopes remain readable/reusable without rewriting historical files. They must still pass exact canonical receipt/date/run/manifest validation; newly written envelopes additionally pin receipt bytes.

## Executed cloud verification

Python standard library only, unchanged local vendor code, synthetic `AcquisitionTools.discover/capture/asr` boundary. All tests call the actual vendor `run_video` through `run_video_fupan`; sockets are blocked. Separate Python processes perform cold reads and assert the producer was not imported.

`python -m unittest discover -s tests/m12 -p 'test_*.py' -v`

Result: **17 tests passed, 0 skipped**. Full output is `unittest.log`.

`python -m compileall -q V5/src/v5_shadow tests/m12`

Result: PASS.

`python -m pytest` was attempted: **NOT RUN**, cloud Python has no pytest (`No module named pytest`). No dependencies were installed. The unittest test class is also pytest-discoverable; Mac validation is still pending and must be reported separately.

TDD evidence observed before production changes:
- Failure publication/receipt binding/atomic pointer tests: 11 failing assertions on the base implementation.
- Legacy-envelope compatibility: failed on `owner receipt bytes mismatch`, then passed after compatibility handling.
- Staging manifest write, staging receipt write, and complete-run replace recovery: each same-input retry failed on `attempt already exists`, then all passed after the bounded staging fix.

Coverage retains the latest four tests and restores all four executable tests from `3997cdeae2239b2314123e88901919eb8780cd25`. Added coverage includes two legitimate runs promoting while the old run stays cold-readable; first ASR failure despite `TARGET_BV_LOCKED/current_advanced=true`; later different-BV ASR failure preserving success; real pointer write/replace failures and retry; receipt identity/hash/status mutation and symlink rejection; legacy envelopes; new-process verification failure; and staging/commit I/O recovery without overwritten evidence.

## Unchanged upstream limit

After owner success A then owner failure B, repeating identical B can raise the original vendor `ImmutableRunError` before entering wrapper reuse because B did not become owner current. This patch does not alter vendor algorithms. Idempotency claims cover successful/current runs, cached first-failure runs, and M12 publication/staging I/O recovery, not that upstream repeated-failed-refresh path.

## Mac targeted command

Run from the fixed commit's repository root using the existing environment:

`python -m pytest -q tests/m12/test_video_fupan_default_chain.py`

Alternatively, the same standard-library command above executes the full 17-test file without adding dependencies.

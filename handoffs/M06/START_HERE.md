# V5 M06 complete source handoff — 2026-10-12

This directory is the current M06 handoff. Start here before the historical START_HERE files inside source/ and before/. The full original M06 SOURCE, historical R4/R6/R8 reports, frozen original vendor code and predecessor bytes are retained. No active shared V5 or V4 file is replaced by this commit.

## Delivered result

- Runnable SOURCE_SNAPSHOT consumer using the actual original cold reader, guard, calendar, projector and validator; mandatory six-field expected_source; exact original 100-row artifact comparison.
- Complete daily owner orchestration with unchanged fixed M07 ledger, actual original materializer call path, source/runtime/asset identities, explicit recorded-input replay and failure preservation.
- Immutable no-clobber publication, independent saved-byte cold readback, exact committed-reference reader and pure original module-response projection for the existing API/page writer.
- Complete source, tests, exact predecessor, forward/reverse diffs, SHA inventory and raw red/green test logs.

Final cloud run: 85 tests passed, 0 skips/failures/errors, exit 0, 140.150 seconds. See [VALIDATION.json](VALIDATION.json) and [full raw log](evidence/full-suite.log). Real-clock original-owner synthetic publication produced 100 rows and both original and new readers returned the same full artifact; fixture provenance remains explicit. No model or market dataset is included.

This is source/fixture acceptance only. New frozen-model generation is blocked by the actual Python/scikit-learn pin mismatch and unavailable original model/panel assets. Mac tests, active P0 routes/page, M08 activation, source qualification/PIT and natural sessions are not verified. A synthetic READY result is not real-source or trading acceptance.

## Read and run

1. [Exact source contract and provenance](source/V5/docs/M06_CONTRACT.md)
2. [Mac commands and rollback](source/V5/docs/M06_MAC_APPLY_AND_ROLLBACK.md)
3. [Single-writer integration request](source/V5/docs/M06_INTEGRATION_REQUEST.md)
4. [Evidence and limits](source/V5/docs/M06_VALIDATION_STATUS.md)

Use an existing interpreter and an isolated checkout. From source/:

    PYTHONPATH=V5/src:V5/tests python -B -m unittest discover -s V5/tests -p 'test_hk_preselection*.py' -v

Do not install dependencies or substitute a model merely to make this test green. Tests need no real input directory or credentials. Owner date tests honestly skip outside their real-date calendar prerequisites. Python dependencies are inventoried in [environment.log](evidence/environment.log); the absent pytest invocation is explicitly recorded as an unavailable check.

## Directory and patch identities

- source/: complete after tree. Original 60 SOURCE files are byte-identical.
- before/: exact original SOURCE + R4 daily + R6 publication + R8 consumer predecessor. Historical defects remain here for inspection only.
- patches/runtime.patch and patches/reverse.patch: the 17-file exact before/after change. Forward/reverse actual application and exact byte round-trip passed. Apply only to a new copy of before/, never blindly to an active checkout.
- patches/BEFORE_AFTER_SHA.json: precise bytes, SHA256 and Git blob SHA1 for every changed path.
- FILE_MANIFEST.json: inventory of every delivery file except itself. The GitHub commit also binds this manifest.
- evidence/: raw test logs, genuinely failing pre-fix regressions, final full run and clearly labeled publication excerpts. Excerpts are not represented as full raw logs.

## Git branch boundary

Target is private lexi2016/v5, dev/m06-github-handoff-20261011. The M06 branch was absent and was created from verified P0 base d3ebf33c40d1b5f06e3729b11d5ece0506f34c91 (tree b904d5cb57ed934740bc6a4283c780de7d9baf55). The original f7cb donor commit is in lexi2016/v4 and was not available as a v5 base; only the fixed M06 source closure is carried here. The delivery adds handoffs/M06/ exclusively, uses a non-force expected-HEAD update, and does not update main or P0. Exact resulting commit and remote readback are reported separately after publication.

# M09 bounded historical research delivery

## Fixed baseline and scope

Parent: `9026365aae36e490a12719399b85cdbc8d075b11`, real branch `v5/m09-handoff-20261011`, private repository `lexi2016/v5`. Parent retains e951e566 receipt repairs, its Mac 136/136 evidence, and the strict real-input diagnostic. All original handoffs, SOURCE, raw payloads, feedback, frozen vendor and manifests remain unchanged. This increment changes only M09 adapters and dedicated tests; it does not change P0, M01, API server/UI wiring, scheduler, V4, main or another market.

The goal is an honestly classified, immutable historical research product from existing saved bytes, while strict REAL/NATURAL admission continues to reject unverified source timing/authority/membership. It does not make the historical day eligible for a natural slot.

## Executable path

1. `prepare_a_close_historical_snapshot` verifies the supplied pointer SHA and safely opens the exact referenced file within its source root. Original panel and optional original receipt hashes are streamed using 1 MiB reads, with O_NOFOLLOW and stable inode/size/time checks. The panel is hash-checked before and after extraction, and the pointer/receipt are rechecked. No whole-file JSON/parquet read or file-size-limit increase is used.
2. Existing PyArrow reads eight original columns in 1024-row batches with prefetch and parallel decoding disabled. The exact `trade_date == requested_date` predicate matches the frozen producer's date selection. At most 20000 selected rows and a 16 MiB typed snapshot are accepted. There is no fill, numeric coercion, sorting, duplicate removal or missing-row removal.
3. A new private snapshot preserves null, NaN bit patterns, positive/negative infinity, strings and signed zero through an explicit tagged scalar representation. Its final manifest is the snapshot commit point. Source SHA/size, selected date, predicate, column order and selected row count are bound to it.
4. An optional large original source receipt is represented by an explicitly opaque, verified SHA/size reference. It is not parsed into a READY substitute. Status/authority/coverage/time remain UNKNOWN/UNVERIFIED/null. Known external PARTIAL/REBUILD_REQUIRED reports remain preserved in the original feedback; this adapter does not replace them with positive evidence.
5. The historical-only root carries a separate marker. REAL, ENGINEERING, MANUAL_RECOVERY and NATURAL requests cannot enter it; a historical snapshot cannot publish in a strict root. Do not point the strict consumer binding at this separate root.
6. `run_a_close_historical` uses the existing immutable calculation/run/receipt/generation machinery, real frozen builder/model/chain/review/store, independent store readback and cold reader. It records `RECORDED_INPUT_REPLAY` / `HISTORICAL_REPLAY`, `PARTIAL`, `OBSERVED_ROWS_ONLY`, and false source-time/membership/PIT/natural flags. Two historical slot-labelled attempts can reuse a computation; they never prove historical slot availability.

## Missing-value behavior

- Exact date, valid unique A codes, all eight columns, finite numeric pct_chg/amount, nonnegative amount and valid scalar types remain hard requirements. Finite out-of-range close positions are rejected.
- Empty or null names and industry fields can remain in historical research. The frozen model's own behavior is preserved. Approximate ST limit counts and industry/role coverage/rankings are explicitly marked uncertain/partial.
- Missing or nonfinite bar_close_pos remains unchanged and is marked as unused by the frozen model. The new adapter never fills it.
- Observed snapshot codes are recorded for exact preservation only; they are not an independent membership/qualification assertion and are not full-market coverage.
- Stage/video evidence remains UNKNOWN and cannot be promoted by this path.

## Verification and remaining work

The dedicated command runs only the new historical tests, 11 receipt-integrity tests, and six selected original-owner/strict/CAS controls; it does not rerun 136. The final `evidence/report.json` is authoritative. Cloud lacks PyArrow, so the multi-day parquet extraction test is NOT_RUN; owner/store/cold-reader and typed-identity cases do execute. No dependency was installed. Existing Mac supported Python/pandas/PyArrow must run the same command once.

Original-source identity remains frozen. Forward/reverse patches, before bytes, per-file hashes and actual patch roundtrip are in this directory. Production-size source parsing, the saved 20261009 real input, current Mac compatibility for this new commit, browser/UI deployment and natural runs are NOT_RUN until the Mac returns their actual results. Prior 136/136 evidence is not reused as a pass for this new code.

## One Mac handoff

Use the existing Python 3.14.6 / pandas 2.3.3 / PyArrow 24.0.0 environment, an isolated checkout of the delivered fixed commit, and new private output roots. Do not install packages or modify source inputs.

Run the dedicated command with `--require-supported --require-zero-skip`. To include the existing 20261009 input in that same invocation, supply all seven explicit source/output arguments:

    <existing-python> V5/tests/run_m09_historical_acceptance.py --require-supported --require-zero-skip --evidence-dir <new-evidence-dir> --source-root <private-staged-input-root> --pointer <relative-pointer-file> --pointer-sha256 <verified-pointer-sha> --panel-sha256 7dfa12fa03ad76d5e946088f88993748a3fffd8943281a12eb364c35712f8c47 --trade-date 20261009 --snapshot-root <new-snapshot-root> --run-root <new-historical-only-run-root> --receipt <relative-original-receipt-file> --receipt-sha256 de652e8ddc540433bef8d0dd9f13da54eb973cf520156109d9e61794dace2a6e

The already supplied original projection is `originals/panel_20261009_required8.parquet`: 279209 bytes, the panel SHA above. The optional original receipt is 80017050 bytes with the SHA above. These identities are in the unchanged `handoff/m09-20261011/MAC_INPUT_FILES_MANIFEST.json` and the existing runtime-input package. These are projected-input hashes, not a new verification of the original 1.38 GB multi-day container.

If its archived pointer still names a former active location, leave it untouched. In a new private staging directory, make a byte-identical verified copy of the existing projection (and receipt if used) and a clearly labelled new local pointer to that copy. Record this derivative pointer SHA separately; it is not a historical availability witness. Do not follow an archived pointer into a different live source or mutate original files.

The runner saves full private input snapshots and products only in the supplied private roots. Return only the bounded `report.json`, source identities, test stdout/stderr with private paths redacted, and actual commit/exit status. Do not upload raw panel, original large receipt, private paths or entire run directories. A failed real replay must retain its precise reason and previous successful generation.

## Rollback

Do not replace any live binding in this acceptance. Code can be reversed only in an isolated checkout after checking exact after hashes and dry-running reverse.patch. Keep all snapshots/runs/attempts intact. The existing expected-generation CAS rollback applies only to the historical root selected by this workflow; strict roots and V4 remain untouched.

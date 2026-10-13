# M05 verified-empty adapter candidate

Parent: d0ec68fa0daffe6ce8d3d47f24c81e2cf65b9f30. Original runtime: 2c5d1eb2c9572469bf04ad86fd61e92ee8674fe8. Only the M05 adapter, its dedicated test and this handoff change; frozen owner/vendor/descriptor are unchanged.

The Mac RED at fad33997c619d1c8239aecda64180aad81f5ccc9 is recorded in the parent commit: the default frozen oracle and original strict reader produced verified zero rows, then M05 failed with LEGACY_EMPTY_STATUS_CONTRACT_MISMATCH (1 test, exit 1).

The candidate maps only independently reread READY_EMPTY with zero rows and matching original source identity to VALID_EMPTY. Original CANNOT_CONFIRM, missing inputs, wrong date, checksum drift and unsafe receipt remain rejected. Nonempty artifacts take the unchanged path. The existing coverage_evidence field retains the version, original status, complete original artifact, its canonical JSON SHA256, and unchanged original source-verification fields. An artifact's canonical SHA is distinct from the independently checked physical file raw SHA.

Cloud verification: source and embedded-worker AST parsing only. Runtime tests NOT_RUN here because the existing cloud Python lacks pyarrow. No dependency installed. An independent static review found and closed the CANNOT_CONFIRM-zero upgrade case; this is not a GREEN claim.

Use the existing Mac Python with numpy, pandas and pyarrow, in this fixed candidate only:

    PYTHONPATH=V5/src:V5/tests "$PYTHON" -B -m unittest -v test_m05_v192_valid_empty test_m05_daily_boundary.M05DailyTests.test_six_original_lanes_publish_one_batch_with_hourly_research

Expected: six dedicated empty-source tests and one existing nonempty/six-lane publication regression, with no skip. The six-lane case uses its existing synthetic source fixtures; it does not rerun a real nonempty oracle. Record actual command/UTC times/exit and counts. The new positive test covers default oracle, original strict reader/owner mismatch, adapter, real strict writer, independent cold reader, raw-byte identities and idempotency. Negative cases cover missing manifest, changed artifact SHA, other trading date, unsafe receipt and original CANNOT_CONFIRM-zero status.

No real source payload, runtime metadata, V4 modification, gate change or production deployment is part of this candidate.

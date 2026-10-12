# M06 isolated Mac acceptance and rollback

Use the already-authorized Mac and its existing interpreter/dependencies. Do not install packages, move V4 roots, change credentials or permissions, or run a model against live market data as part of the source test.

## Before application

1. Read handoffs/M06/START_HERE.md at the delivered fixed commit. Record the actual checkout, branch and HEAD. The only delivery namespace is handoffs/M06; there is no patch for active P0/main/M02/M08/V4 files.
2. Verify FILE_MANIFEST.json and before/after patch identities. The source bundle's original SOURCE_MANIFEST.json describes donor origins; it is not an instruction to overwrite the Mac's active copies.
3. Inspect the existing interpreter. Confirm its executable and package versions. A different model runtime is a genuine BLOCKED condition, not permission to upgrade packages or weaken pins.
4. Extract or check out the source bundle into a new isolated directory. Keep any current M06 success and existing service configuration intact. The tests use task-owned temporary directories and do not need a real market-data root.

## Commands from the isolated source directory

Set PYTHON to the verified existing interpreter path, then run:

    "$PYTHON" -VV
    PYTHONPATH=V5/src:V5/tests "$PYTHON" -B -m unittest discover -s V5/tests -p 'test_hk_preselection*.py' -v

There are no pytest-only tests in this delivery. If pytest is present, its optional equivalent is:

    PYTHONPATH=V5/src:V5/tests "$PYTHON" -B -m pytest V5/tests

Keep the raw command, exit code and full logs. Do not turn a missing pytest/parquet dependency into a passed test. Owner clock tests explicitly disclose a skip when their real-date prerequisite is inapplicable.

The original-owner fixture tests call the actual original publisher/store/reader with SYNTHETIC_FIXTURE master and rows. They do not load, create or substitute frozen models. The original materializer is also called on genuinely missing assets to verify failure and old-success preservation.

## Real input acceptance is a separate authorized window

- Verify all actual source file identities, three dates, cutoff and acquisition times before any generation.
- Verify original panel, model manifests, models.joblib, optional names and exact eligibility master closure; preserve authoritative M02 provenance and qualification gaps.
- Verify the exact model runtime before invoking the original materializer. Never invent a model or bypass its SHA/version checks.
- Use a dedicated V5-marked output root and disjoint input roots. Record the original producer result, independent consumer result, all 100 original fields/ordering/probability text and numbers, and run/artifact/manifest/receipt identities.
- Verify the exact committed reference and ledger product mapping. A READY/ASSEMBLED synthetic result is not real-source production acceptance.
- P0 integration uses only the module's pure reference projection and an already-verified runtime route configuration. No URL, port or active generation is assumed here.

## Rollback

This source delivery does not activate a service or generation. For a test-only install, stop using the new isolated source directory and retain it for inspection; no original file was overwritten.

If P0 later activates an authorized M06 generation, record its previous generation ID beforehand. On failure, the single P0 writer reactivates that previously verified generation through its existing CAS flow. Do not delete published objects, edit ledger history, rewrite committed.json, copy an old day's pool into a new date, or change V4. Verify V4 and unrelated modules remain healthy using the actual known endpoints.

A precommit incomplete object or interrupted RUNNING ledger entry is an unknown outcome. Inspect the existing bytes and exact run references; do not retry, clear the marker or fabricate a successful receipt. Recovery authority is separate from ordinary idempotent reuse.

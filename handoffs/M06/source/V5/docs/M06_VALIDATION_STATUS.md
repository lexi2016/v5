# M06 validation status

This document separates engineering evidence from real-source production.

## Evidence established in the cloud source workspace

- Original SOURCE 60-file identity validation and unchanged-original comparison.
- Real original eight-file fixture through the default new cold consumer, with complete original artifact equality to the original legal SYNTHETIC reader.
- Empty/missing/malformed/wrong six-field expected_source, missing each of eight files, lexical/ancestor symlink rejection, input tamper, wrong dates/cutoff, 99/101/duplicate rows, nonfinite scores, actual clock ordering and unchanged safety.
- Real original publish_hk_0_2_rows -> store -> original low-level reader. Exact 100 fields/rows and repeated-run identity preserved.
- A real-clock current HK-day synthetic original-owner publication is independently read by both the original and new consumers; full artifacts match and synthetic master provenance remains fixture_only=true.
- Genuine original materialize_frozen_hk_0_2 missing-asset calls reject without creating a new output store or changing an old successful store. Genuine original _load_models rejects the actual nonpinned runtime without a fake model.
- Immutable source publication and reference readback, raw SHA including JSON-format changes, full manifests, same-input revalidation, conflict, symlink, concurrent one-success publication, incomplete/crash unknown preservation, recorded asset retention, and rejection of fabricated model proof.
- Existing recorded daily path uses the unchanged fixed M07 ledger; invalid existing pool cannot fall back to generation or overwrite old success. Default manual/natural modes cannot silently omit original assets.
- Pure route-record projection is checked with the original module-response validator, using supplied test route configuration, without activating a server or generation.

Final command, count, exit status and exact final-file hashes are recorded in handoffs/M06/VALIDATION.json and evidence/full-suite.log. Preliminary red/fix logs are retained as failures, not counted as extra successful tests.

## Not established

- New model-generated Top100: BLOCKED by actual Python/package pin mismatch and missing original panel/model assets. No replacement model, fake inference or altered vendor hash is used.
- Formal eligibility, authoritative M02 source/PIT or real-market-data equivalence: NOT_VERIFIED. Synthetic rows and receipt files do not establish these.
- Mac application/tests: NOT_RUN in this cloud workspace. The documented commands use the existing authorized Mac environment.
- Active P0 API/page/generation/M08 integration: NOT_RUN. A validated pure record is not a deployed endpoint.
- Continuous natural sessions, actual operational recovery and active single-module rollback: NOT_RUN.

The original producer's three exact pins are Python 3.13.12, scikit-learn 1.9.0 and joblib 1.5.3. The observed cloud interpreter is Python 3.12.14 with scikit-learn 1.8.0/joblib 1.5.3. Pytest and parquet engines are absent; tests use the existing standard-library unittest runner. These missing packages are not silently installed and are not green tests.

# M04 execution evidence

Cloud isolated execution only; no Mac, network provider, credentials, V4 write or preview deployment. Python 3.12.14 on Linux.

- Original owner/builder/import/cold-reader positive control: 1 PASS, 1.901s. Prior Chat startup timeout was not reproduced with standard unittest.
- New entrypoint RED: 9 assertion failures because the module was absent, 0.018s.
- First GREEN attempt: 8 PASS/1 error (unmarked root raised the wrong exception); fixed only marker error handling.
- Initial bridge suite: 9 PASS, 14.504s.
- Full supplied V5 suite at that bridge revision: 97 PASS, 99.410s (includes those 9 tests; do not add counts).
- Extended CLI/partial-builder/symlink/unknown-field suite: 13 PASS, 18.970s.
- Additional real regression RED: checkpoint production claim was accepted; 1 expected test failure, 2.411s.
- Final bridge-only suite after the minimal safety check: 14 PASS, 19.993s. The old 97-test suite was not redundantly rerun after this local guard change; it is not called a final-revision whole-suite run.
- Two original canonical pytest files: NOT_RUN. Primary and system interpreters have no pytest. Another existing environment has pytest but no fastapi. No dependency installed and no old PASS substituted. Original tests are retained for the approved Mac environment with the complete original source dependencies.

Published logs retain all assertions and messages; only cloud workspace prefixes are substituted. LOG_IDENTITIES.json preserves SHA256 for raw originals and published forms. Raw originals remain available to the parent task.

The fixture substitutes only bounded external provider response and analyzer. Original materialize, collector, builder, archive store and independent reader execute; original vendor/manifests were not edited. Test success is not real material acquisition, PIT, production, natural continuity, preview availability or complete M04 acceptance.

Packaged-source verification: the actual standalone test script assembled all 15 bound dependencies and ran 14/14 final tests in 19.820s, exit 0, using only the delivered tree and an isolated temporary root. This rerun verifies packaging, not additional unique tests.

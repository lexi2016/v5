# Retrospective M17 vendor-controls Mac receipt

This upload records the existing 2026-10-11 run. It is not a new execution or a newly passed test. Original recorded execution: 2026-10-11T18:18:14.575623Z through 2026-10-11T18:18:15.457145Z, exit 0, CANDIDATE_CONTROLS_PASS. The later 18:18:55 report time is not the actual execution interval.

The original private execution/summary.json SHA-256 is `4ad325690f94f7f3e282880f8b3ab7fd97bbf2964c2b803b49e2af519b940bba`. That original file is not uploaded: result.json is a deliberately smaller, redacted structured summary and has its own bytes/hash. Original source and result files were not modified.

Product candidate: `fe0a1890ebe59b476af6c8a0e1878fca059c24f4`. This is the product-code commit, not a previous Mac feedback commit. The original receipt explicitly recorded no external upload; the inspected M17 branch history/tree had no corresponding Mac feedback.

Four controls passed: original owner materialization plus separate original cold-reader verification; intact retry with zero collector calls and unchanged four products; corrupted-overlay reader rejection with zero writes; corrupted-product owner rejection with zero collector calls and no overwrite. All inputs were SIMULATED, with a 100-row fixture. Real Futu/PyTDX/network collection did not occur.

The fixed closure contains 24 files, not 24 proven imported Python modules. The retained probe checked loaded source origins and byte identity, but did not export a complete per-process module trace. The sole changed producer was 61132 bytes, SHA-256 `998275df085d886a6c4b5a44b3737c6b31de40cbe5b791d561db93968c062bfd`. The other 173 files in the candidate comparison were unchanged. This receipt does not claim additional pre-15:55 rejection coverage.

Scope remains the original vendor owner/reader subchain. Independent V5 wrapper execution and P0 registration are NOT_RUN. The subsequent P0 admission audit was BLOCKED_NO_M17_EXECUTION_REGISTRATION_CONTRACT, with invoke count zero; it is not a completed integration. Natural-run verification is false and full M17 acceptance remains NOT_RUN.

Only redacted receipt, command/time, result/hash summary and source identities are included. No original business payload, private absolute path, credentials, live-service change, code change or new test run is included.

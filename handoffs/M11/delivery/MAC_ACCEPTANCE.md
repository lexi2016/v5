# Fixed-candidate Mac verification (not yet run)

Use the exact published candidate commit and an existing authorized Python environment. Do not install software, read credentials, create a replacement trusted owner manifest, modify V4/P0 or trigger live acquisition just to make a test green.

1. Read README, DEPENDENCIES, TEST_STATUS and source descriptor. Verify code/donor SHA, then run:
   `PYTHONPATH=V5/src python -B -m pytest -q -p no:cacheprovider V5/tests/m11`
2. Run the explicit API/scheduler candidate's tests from its own README. No UI build, browser deployment or P0 acceptance is claimed by these checks.
3. Check descriptor-safe symlinks/escape, subprocess concurrency, partial publication recovery, durable unknown-attempt no-retry and independent readback. Root markers and fixtures may only use a fresh designated M11 scratch directory.
4. Verify the six new build-manifest tests: real unchanged validator HASH_BOUND; tamper/missing/extra/wrong-pin reject; real assemble_runtime succeeds without reading credential DB. Full default execution still needs genuine operational inputs and existing dependencies.
5. When the fixed V5 build pin, original config/profile and required dependencies are genuinely supplied, verify a single authorized real slot: original capture result SHA → fresh original reader proof → immutable V5 envelope → separate V5 cold reader → same run API response. Do not change the clock, fetch historical/current data as past, or equate one slot with all six.
6. For real explicit daily generation: original assemble_runtime → run_generation(replace=False) → exact original daily artifact SHA in new process → independent capsule read. Preserve declared-only provenance and natural CANNOT_CONFIRM. A new explicit generation requires distinct approved private state/config, not replacing old output.
7. Page use, real source input, natural trading-day evidence, automatic resumption and full-module acceptance each need separate receipts. The current candidate does not supply them.
8. Roll back M11 adapter registration only; keep V4 and existing successes. See ROLLBACK.

## Focused diff acceptance after f932

For the later config-boundary fix only, use the new fixed commit and run:
`PYTHONPATH=V5/src python -B -m pytest -q -p no:cacheprovider V5/tests/m11/test_binding_config_boundary.py`
Expected four passing cases. Do not repeat unrelated successful f932 suites merely for this two-line boundary guard.

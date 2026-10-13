# Mac original frozen-model generation — one controlled P0 call

Fixed product: `4e05bd422d1f6bdedb7bff8b2faf5218fac9e58a`. Feedback base: `b378e18005ddbaba51e3c483cd7fd54e4a96ef7f`. The 147-entry source closure (`dae57f54bedc7632b4beafa9cd29fb2158db83162ac3d7bacdace2bf9fe1a1e4`) was verified before and after execution. No product or venv changes; no dependency installation. No old tests or previous existing-pool execution were repeated.

## Result

**One actual original frozen-model computation completed successfully**, followed by the original fresh reader and two independent successful ledger records. Exact command, UTC start/end, cutoffs, identities and exit 0 are in execution.json. Run: **2026-10-13 01:47:48.017364–01:48:37.848983 UTC** (about 49.832 seconds). Original output is 100 rows; no clipping or replacement was performed by the test harness.

- P0 UUID `4c8295528ca7450daf2dc48b014f0af5`.
- M06 UUID `1112ecbd4b95467799eaee153520f2f0`.
- Publication digest `d6726881b5c4fc29c2753d45283968ea69bbb48f212d0bc8879efd233577580b`.
- Original generated pool run `20261013-hk-connect-d1-top100-0-2-7c48617a751f`; already_exists=false.
- Producer receipt SHA256 `4bb5a7ef33a9cca884ba7c64dd4118f93a511ddfc64d2fa4e90a6bf928ca6c30`.
- Producer PID 51793, independent fresh-reader PID 51898.
- Method FROZEN_MODEL_PRODUCER; producer model_weights_reverified=true; reader keeps its original false semantics. fixture_only=false, natural_verified=false.

The top-level label DISPATCH_ATTEMPT_ONLY is unchanged; the hk_preselection lane and both ledgers are SUCCEEDED. No manager request or other lane was admitted, so this does not establish whole-tick or whole-system acceptance.

## Inputs and isolation

The earlier 7006 and b378 references were fetched and compared with the retained original evidence. All **18 original input/asset SHA256s** were reverified, including model PIN `3b0d5d5239342439cabf25b30012365a64d78839bc3cd4d90bad7be6ff4aaa07`. Full relative-path hashes, sizes and generation-use flags are in input-identities.json. No business rows, model bytes or private absolute paths are uploaded.

A newly created independent store received only the original contract's four security-master files, byte-for-byte and with timestamps preserved. A separate asset root received the ten exact original assets. The four old pool/pointer files were verified but never copied into the new source. No pool was deleted or altered. The candidate's original GENERATE_IF_ABSENT admission legitimately observed absence in this new store. Original M06 then generated in its own temporary isolated store, published the original result and retained the committed V5 artifacts; it did not copy the prior 100-row pool. The declared new source store remains unchanged and has no pool pointer after execution, as required by the original staging design.

Target 20261013; signal and eligibility 20261012. Admission UTC 01:47:48.017026; completion cutoff 02:17:48.017026, 30 minutes ahead. Explicit slot ended at 02:22:48.017026, max_attempts=1. Original generator subprocess timeout remains 600 seconds, registration timeout 1800 seconds. No clock override. Original captured/available metadata and existing PIT gaps were retained, not replaced with this execution time.

Both new ledgers contain exactly one attempt. The original 18 files, old M06 state, prior P0/M06 controlled result and live preview files were protected by before/after SHA256, size and mtime checks: **111 files unchanged**. The new 14 input/asset copies also remain byte-identical. No services were started, stopped, deployed or reconfigured; private configs remain on Mac, with a disabled copy retained.

## Observed computation and network boundary

Task-only recursive observation covered **27 processes and 26 Python child launches**, preserving interpreter, isolation flags, original argv/stdin and unchanged product scripts. Original functions observed: produce_hk02_daily=1; original generation worker=1; materialize_frozen_hk_0_2=1; score_frozen_hk_0_2=1; _load_models=1; joblib.load=1; _score_with_strategies=1; _probability=4; pipeline.predict_proba=4. Detailed main-thread function counts are in profile-summary.json; lower-level estimator threads are not exhaustively profiled.

Network socket creation/connect/DNS/sendto were guarded and recorded **0 attempts**. Shell and unobserved external processes were also blocked. **One external-process launch was blocked before execution; its command was not retained, so its category cannot be established retrospectively.** This is an observation limitation, not a claim that no subprocess was ever requested. The original computation handled that rejection and completed; no unobserved child ran. No second model computation was performed to investigate it. No provider collection was invoked or authorized.

The newly computed and old pools have the same 100 codes in the same ranking. Some numeric score fields differ; exact counts and maximum absolute differences are in comparison-summary.json. Their artifact hashes differ. Neither result was substituted for the other.

This establishes one controlled local computation branch and fresh-reader/ledger integration. It does **not** establish natural scheduling, new PIT correctness, formal eligibility, trading readiness, provider acquisition or overall 18-module/P0–P5 acceptance.

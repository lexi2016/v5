# Mac M06 native-pool compatibility — scoped PASS

Fixed candidate `b5a832e165f5af72eba9347135a8525092c76fc0`. Verified 163-file closure before and after: SHA-256 `0175f6eda459025d6cc0b12ccf8a1f6a05f7f0507a1dbb5cae5bf0bdc6aafda7`. Isolated candidate only; no whole-HEAD or active-service overlay. Existing HK02 dependencies; no installation.

## Focused synthetic engineering tests

Only the required new admission/owner tests and three selected resolver regressions ran. **19 passed, zero skipped/errors, exit 0**, 2026-10-13 05:50:17.027085–05:50:29.920534 UTC. Exact command/environment are in verification.json. No old 24/15/85 suite repeat. These include genuine fixed-owner/cold-reader processes over synthetic source pools; they are separate from the historical real-input check below.

## Historical real D12→D13 chain and seal

Original dispatcher UUID → lane → panel/native-pool receipt chain passed. Original native manifest.v1 has no three safety keys; bound receipt.v1 already has all three false. No original bytes or flags were amended. A new independent historical snapshot sealed 20 files / 55,109,291 bytes at actual `2026-10-13T05:51:45.254433+00:00`; no clock override. Delivery SHA `10db84cdaf1b724174fe19846d074087048687d3e911a23df111a1b03ebaa34f`; seal SHA `64ba513a8374efc4bdd270d9144e95f1759c34c746a7cd689b6ea2b991649303`. Verified sealed selection is **EXISTING_VERIFIED_POOL**.

The unchanged original cold reader accepted those sealed bytes: **ASSEMBLED, 100 rows, exit 0**, 05:52:26.934755–05:52:27.177638 UTC. model_weights_reverified=false. Original source hashes/bytes remained identical. No daily owner, model recomputation, expired historical execution, new success publication or natural-completion claim occurred.

Harness history is retained: first cold invocation omitted the required isolated `-X pycache_prefix` and returned FAILED/A_SOURCE_CACHE_REQUIRED; its worker exit was not retained separately, and harness exit was 1. Retrying only the cold reader with the original test's required cache argument passed without resealing. After that, a direct validator call on an intentionally disabled registration correctly raised M06_EXECUTION_DISABLED (second harness exit 1). The separate disabled-config shape/pin check then passed using an in-memory validator copy; no persisted switch was enabled and no daily tick ran. No product fix or lowered validation was made locally.

## D13 disabled configuration

Independent daily roots still contain ownership markers only. D13 calendar is FULL_TRADING_DAY with scheduled/signal 20261013 and target 20261014; explicit full/half windows 17:30–18:30, complete budget1200s, process600s, UUID discovery only, original venv pins verified. Three switches remain false. D13 18:30 is the execution deadline; D14 09:00 is owner compatibility metadata only. Historical D12 delivery was not reused for D13. No scheduler or launchd installation.

Post-history verification: 156 protected files, all protected listener PIDs and all163 candidate files unchanged, including current M11/M12 preview and original committed references. Historical input acceptance does not establish a natural daily run, model generation, business completeness or full P0–P5 acceptance.

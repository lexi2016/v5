# Mac c68fa0 targeted tests / existing HTTP canary

Fixed candidate: **c68fa0a374355fb510a9d0e3fa595da09296f033**.
Author source: https://chatgpt.com/c/6acc5cb3-7dd0-83ee-86d2-03437894dca3?messageId=ccfe5459-a4d0-4518-a23f-2aef23a28b95
Inherited e83458 feedback on original dev/v5-main-integration-20261012 branch.
Only exact unique line changed:
```diff
-from .m18_v2_http_bridge import ROUTE as M18_ROUTE
+M18_ROUTE = "/api/v4/manager/m18/v2"
```
module_api blob: d23779dd0497a2b8ffd3d47ae0d1f69beac5fa6b. Local execution file matched this blob. No independent code repair.

## Executed once

1. `<EXISTING_PYTHON> -m pytest -q -p no:cacheprovider V5/tests/test_m18_v2_http_bridge.py V5/tests/test_m18_v2_module_api_binding.py`
   - UTC 2026-10-12T07:57:56.029435–07:57:56.287034
   - exit **1**, **2 failed, 5 passed in 0.04s**.
   - Import collection now succeeds.
   - First failure at test_m18_v2_module_api_binding.py:39: expected manifest_sha256 length 64, actual placeholder `<EXISTING_V2_MANIFEST_SHA256>` length 29.
   - Second at test line 48: _config attempts opening example /ABSOLUTE/PATH/TO/PUBLISHED/MODULE_ROOT and raises `FileNotFoundError: [Errno 2] No such file or directory: 'ABSOLUTE'`. The placeholder was not replaced inside product test/example files.

2. `<EXISTING_PYTHON> <TASK>/http_canary_eefe978.py`
   - UTC 2026-10-12T07:57:56.287418–07:57:56.871429
   - exit **1**, `AssertionError: PAGES_GET_NOT_READABLE`.
   - Original server on 127.0.0.1:54065.
   - Health GET 200, PID matched; descriptor GET 200 / 804 bytes; six identity fields and existing offline generation MATCHED.
   - Pages GET `/api/v4/manager/m18/v2/pages?run_id=46596b03c2ab4e29b1219fd2e5eb698f&page=0`: **409 / 90 bytes**:
```json
{"module_id":"manager","reason_codes":["MODULE_RESULT_INVALID"],"status":"CANNOT_CONFIRM"}
```

## Canary configuration boundary

The exact existing canary was reused with new candidate PYTHONPATH: original successful publication root/release mac-912941-canary, both routes in routes list. It **does not inject m18_v2_binding**. Thus this is an existing-publication compatibility/pages failure observation, **not a completed correctly bound v2 pages test**. No diagnosis beyond the returned HTTP error is claimed. Full binding/page success and page six-identity verification remain NOT_REACHED.

Reused manager run 46596b03c2ab4e29b1219fd2e5eb698f, target20261012; offline generation 8bf699c6bc1fc47a869d2e21d53989a5f5f18d31b52ddef24071c88c4c7ffa8a; publication generation 01726f5d6c64e9afb7d4a06278f5ae6e2fb1a4eba784865bde2c5981ffa5f36b.

PASS cleanup: own server shutdown/close, thread ended; all existing publication file SHA256 values unchanged. No existing service stopped, no protected port used, no owner/acquisition/rebuild/browser/trading. No full P0 acceptance. Raw execution receipts retained locally. Product left exactly as author instructed.

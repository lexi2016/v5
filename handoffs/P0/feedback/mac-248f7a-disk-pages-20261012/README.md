# Mac 248f7a: focused tests pass; real page 0 passes, page 1 fails

Fixed candidate **248f7adec7bb329219c1b4f68cde13ba137c5b19**.
Complete repository materialized: 764 files, each matched fixed-tree Git blob. No product edits/installations. Existing Python 3.14.6 and pytest 9.0.2 reused.

## Focused tests: PASS

From V5/:
```text
PYTHONPATH=src:tests:<EXISTING_PYTEST_SITE> <EXISTING_PYTHON> -m pytest -q -p no:cacheprovider tests/test_m18_v2_disk_pages.py tests/test_m18_v2_module_api_binding.py tests/test_m18_v2_http_bridge.py tests/test_m18_v2_publication_bridge.py tests/test_module_api.py tests/test_module_artifacts.py
```
UTC 2026-10-12T09:51:50.709058–09:52:12.090596.
exit **0**, **50 passed, 27 subtests passed in 21.12s**.
Unchanged offline/resource suite not repeated.

## Real-bound sequential HTTP canary: FAIL on second page

`<EXISTING_PYTHON> <TASK>/http_real_248f7a.py`
UTC 2026-10-12T09:52:30.926400–09:52:43.004902.
exit **1**, AssertionError HTTP_NOT_200.

Retained LOCAL_ONLY_config.json unchanged. Existing run46596b03c2ab4e29b1219fd2e5eb698f, target20261012, existing v2/publication only. Server 127.0.0.1:56379. One original server in a thread within the canary process; requests sequential.

| Request | Status | Bytes | Request seconds | Verification |
|---|---:|---:|---:|---|
| /__v5/module-health | 200 | 315 | 0.001 | PID matched |
| /api/v4/manager/m18/v2?run_id=46596b03c2ab4e29b1219fd2e5eb698f | 200 | 804 | 0.001 | six identities and offline generation/profile matched |
| /api/v4/manager/m18/v2/pages?run_id=46596b03c2ab4e29b1219fd2e5eb698f&page=0 | **200** | **351042** | **4.339** | six identities matched; original Reader.verify_content(expected_index=0) passed and Reader.content(0) equality passed |
| same pages query, page=1 | **409** | **90** | **2.709** | no content returned |

Page 1 response:
```json
{"module_id":"manager","reason_codes":["MODULE_RESULT_INVALID"],"status":"CANNOT_CONFIRM"}
```

Harness detail relevant to reproduction: before starting the HTTP server, the same process loaded the existing Bundle and instantiated the original Reader for independent expected-page verification. That Reader remained in memory during both HTTP requests. The response handler also uses the original runtime Reader. No resource limits were changed. The generic HTTP error does not establish its internal cause; no specific memory/resource diagnosis is claimed and no repeat request was made.

## Preservation / limits

Before/after SHA256 **and mtime_ns** maps of all bundle and publication files are identical. Own server shutdown/close completed and thread ended. No rebuild, republish, owner, collection, trading, browser, protected port or existing-service change.

Offline generation: 8bf699c6bc1fc47a869d2e21d53989a5f5f18d31b52ddef24071c88c4c7ffa8a.
Publication generation: 01726f5d6c64e9afb7d4a06278f5ae6e2fb1a4eba784865bde2c5981ffa5f36b.
All six descriptor/page0 identity values are the retained real binding values; no synthetic replacement.

**Page 0 real HTTP succeeds; consecutive real pagination is not accepted.** Page1 identity/content, full real reconstruction and frontend deployment remain NOT_REACHED. Temporary URL is no longer live.

Preliminary read-only frontend check only: existing d94c managerWorkspace.ts still fetches /api/v4/manager/research/workspace; no m18/v2 reader reference was found in its src tree. No frontend implementation/build/deployment performed. Do not treat backend page0 success as normal-page acceptance.

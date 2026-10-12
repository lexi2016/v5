# Mac 924644 real-bound HTTP canary: startup fixed, pages still 409

Fixed candidate: **924644d096aa62a746185112dcf345a36a919a83**.
Parent: 2bc383d09063bcd9762ef7b54d5b4c0bc04bf6a8.
module_api.py blob: 75bd4d5cfaeb5479673a7855990f6b67ca9819a0.
Original reply verified locally: 4113 bytes, SHA256 5da87e9cb477a992bd4fbe829593ff239276417a4c4e761ceca68b4420974716.

Applied only the original author's exact unique _config old/new replacement and immediately following supplied validation block. No fixture/example/pages edits or independent repair. Original source: handoffs/P0/chat-delivery/binding-contract-repair-20261012, message e7800136-5b59-4b71-9cb4-d29a907b3f49.

First ref update was automatically rejected for possible stale HEAD. Fresh remote ref and candidate parent were then explicitly checked: both 2bc383d09063bcd9762ef7b54d5b4c0bc04bf6a8. The same guarded non-force direct fast-forward subsequently succeeded. No intervening commits discarded.

## One actual real-bound canary

Command: `<EXISTING_PYTHON> <TASK>/http_bound_canary_924644.py`.
UTC 2026-10-12T08:11:23.189317–08:11:23.748181.
Exit **1**: AssertionError PAGES_GET_NOT_READABLE.

External harness reuses previous HTTP canary, replacing only its config construction with the retained LOCAL_ONLY_config.json from the true-binding attempt. All actual saved six-field identity values, manifest/profile pins and bundle_root are present. data_root and release_id match the unchanged 912941 publication. No in-memory Bundle substitution, rebuild or republish.

Original create_module_server succeeded at **127.0.0.1:55351**.

| Actual GET | Result |
|---|---|
| /__v5/module-health | 200, 315 bytes, PID matched |
| /api/v4/manager/m18/v2?run_id=46596b03c2ab4e29b1219fd2e5eb698f | 200, 804 bytes, all six identity fields MATCHED, offline generation MATCHED |
| /api/v4/manager/m18/v2/pages?run_id=46596b03c2ab4e29b1219fd2e5eb698f&page=0 | **409**, 90 bytes |

Pages response:
```json
{"module_id":"manager","reason_codes":["MODULE_RESULT_INVALID"],"status":"CANNOT_CONFIRM"}
```

This is now a **real-bound configuration accepted by startup**, unlike c68fa0 bound attempt's CONTRACT_FIELDS_INVALID before startup, and unlike the earlier unbound configuration's 409. The HTTP service returns a generic error; no more specific internal cause is asserted from this run.

Reused run 46596b03c2ab4e29b1219fd2e5eb698f / target20261012.
Offline generation 8bf699c6bc1fc47a869d2e21d53989a5f5f18d31b52ddef24071c88c4c7ffa8a.
Publication generation 01726f5d6c64e9afb7d4a06278f5ae6e2fb1a4eba784865bde2c5981ffa5f36b.

PASS: own server shutdown/close completed, thread ended; publication file SHA256 map unchanged. Existing data and services retained. No owner, collection, v2 rebuild, publish, browser or trading. Old seven tests were **NOT_RERUN** as requested. Page content/six-identity success remains **NOT_REACHED**. No complete P0 acceptance.

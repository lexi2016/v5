# Mac eefe978 HTTP/binding canary — FAIL at pages GET

Fixed candidate: `eefe9784f60433eb5c0d8f8d15107761edf8e1b3`.
Branch: `dev/v5-main-integration-20261012`.
No earlier execution/feedback for this candidate was present in this task or the checked remote tree; executed once.
New files fetched at fixed commit; source/test closure verified by Git blob. No product edits.

## Actual commands and results

Private executable/workspace prefixes below are replaced by logical placeholders.

1. From candidate root, `<EXISTING_PYTHON> -m pytest -q -p no:cacheprovider V5/tests/test_m18_v2_http_bridge.py V5/tests/test_m18_v2_module_api_binding.py`
   - UTC 2026-10-12 06:52:31.774432–06:52:32.037306.
   - exit **0**, **5 passed in 0.03s**.

2. `<EXISTING_PYTHON> <TASK>/http_canary_eefe978.py`
   - UTC 2026-10-12 06:52:32.037642–06:52:32.623077.
   - exit **1**, first failing assertion `AssertionError: PAGES_GET_NOT_READABLE`.
   - Actual original `create_module_server(config, host="127.0.0.1", port=0)` listening on **127.0.0.1:49216**; one in-process server thread, shut down and closed in finally.
   - Config schema `v5.module_api.v1`, module `manager`, release `mac-912941-canary` matching existing publication. Both descriptor and pages routes explicitly listed, using the candidate's supplied route shape.
   - Reused successful 912941 publication root and original active generation; no republish or copying response into records.

| Request | Actual HTTP result |
|---|---|
| GET /__v5/module-health | 200, 314 bytes; returned PID matched canary process |
| GET /api/v4/manager/m18/v2?run_id=46596b03c2ab4e29b1219fd2e5eb698f | 200, 804 bytes; six-field identity MATCHED, offline generation MATCHED |
| GET /api/v4/manager/m18/v2/pages?run_id=46596b03c2ab4e29b1219fd2e5eb698f&page=0 | **503**, 96 bytes; body below |

```json
{"module_id":"manager","reason_codes":["MODULE_RESULT_NOT_AVAILABLE"],"status":"CANNOT_CONFIRM"}
```

Pages route was admitted by the explicit route configuration (not a 404 route rejection), but no readable page was returned by the real HTTP service. This is a failing end-to-end page request despite the five narrow tests passing. No alternate page-query guesses or fabricated records were tried. The author should provide actual page request/binding wiring and its contract; this run does not claim a source audit.

## Reused identities

- manager run: `46596b03c2ab4e29b1219fd2e5eb698f`; target `20261012`
- plan_sha256: `fed238e033181b159f419918c8c54dcb4743791b18f93d31e2a1e2006f5924ce`
- raw_sha256: `7de6ea9fc6b10462fcc75af1c02c9d9d5111288a9d993b7f154ca988fea4e4db`
- response_sha256: `ae840ac69d9fdc8f25bd675c41e8e3f6d028ef17147987b36220a35a6d786d22`
- input_identity: `c99d03b5dfe289f93382d14e1aa4c083283283270c27287e1e752b71f2d465de`
- offline generation: `8bf699c6bc1fc47a869d2e21d53989a5f5f18d31b52ddef24071c88c4c7ffa8a`
- publication generation: `01726f5d6c64e9afb7d4a06278f5ae6e2fb1a4eba784865bde2c5981ffa5f36b`
- previous publication receipt: feedback commit `68db7cb18197287b9678f175a6172d55e44e827d`.

## Cleanup and remaining scope

PASS: own server shutdown/server_close completed; server thread no longer alive; SHA256 map of all pre-existing publication files unchanged before/after GET. Protected V4/preview ports were excluded, and no existing process was stopped.

NOT_RUN/NOT_REACHED: successful bounded page response and page identity verification, UI/browser, deployment, broad regression, owners, manager refresh, v2 rebuild, collection, trading. Existing v2 133-object inventory was reused, not repeated. Budgets unchanged. Only this new targeted test pair and one loopback canary were executed. No real body or private absolute path is included in feedback.

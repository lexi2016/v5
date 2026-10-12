# 248f7a one no-trace boundary diagnostic — original page1 RSS rejection reproduced

Product unchanged: **248f7adec7bb329219c1b4f68cde13ba137c5b19**.
Command: `<EXISTING_PYTHON> <TASK>/diagnose_boundary_248f7a.py`.
UTC 2026-10-12T10:01:33.846955–10:01:45.687173. Exit **1** (HTTP_NOT_200).

Exactly one diagnostic. No settrace/event tracing, no tests rerun. External wrapper around original module_api._m18_page_response invokes it unchanged. Only after an exception, the wrapper traverses its traceback once, copies the five authorized resource counters, records exception type/code and re-raises the same exception. No other locals, body or private paths logged; no product source, budget, identity check or caching changes.

## Actual sequence, same original topology

Existing independent Bundle/Reader retained in the same process as original HTTP server. Sequence preserved: descriptor → page0 → independent original Reader verification → page1.

- Health200,315B, PID matched.
- Descriptor200,804B, six identities matched.
- Page0 **200**,351042B,4.262s; six identities matched, Reader.verify_content and content equality PASS.
- Page1 **409**,90B,2.705s, public error MODULE_RESULT_INVALID.
- Original exception observed at page-response boundary:
  **ContractError: M18_V2_RESOURCE_PEAK_RSS_BYTES**.

Captured original usage:
```json
{
  "peak_rss_bytes": 620478464,
  "cpu_seconds": 2.702736,
  "wall_seconds": 2.7037225000094622,
  "scan_nodes": 1122085,
  "scan_bytes": 71203343
}
```

Original RSS budget is 536870912 bytes (512 MiB), unchanged. The observed process high-water RSS exceeds it. This identifies the underlying original exception for this reproduced same-process page1 HTTP409, unlike the prior trace-induced independent-verifier CPU failure. It does not establish the result for a standalone server with a separate oracle; that deployment topology was intentionally not tested here.

Server127.0.0.1:57845 shut down and closed; thread ended. Bundle/publication SHA256 and mtime maps unchanged. Existing real run46596b03c2ab4e29b1219fd2e5eb698f and v2/publication reused. No rebuild, publish, owner, acquisition, trading, browser, protected ports or existing-service changes.

No further diagnostic or fix performed; awaiting next instruction.

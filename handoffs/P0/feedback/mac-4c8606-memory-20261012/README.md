# Mac 4c8606 real sequence — gaps first page still HTTP409 / child RSS exceeds budget

Fixed candidate **4c8606044b6004025998cff3cb0ebe5f3a5c4ed0**.
Complete fixed tree materialized and all 914 file Git blobs rechecked after execution. Existing134 frontend files unchanged; no rebuild/tests/installations. Retained LOCAL_ONLY_saved-view-config unchanged.

## One fresh independent API acceptance

Harness command: `<EXISTING_PYTHON> <TASK>/memory_acceptance_4c8606.py`.
UTC2026-10-12T10:39:31.258311–10:39:42.595831, exit **1**.
Only API child:
```text
PYTHONPATH=<FIXED_CHECKOUT>/V5/src:<EXISTING_PYTEST_SITE> <EXISTING_PYTHON> -B -m v5_shadow.module_api --config <RETAINED_SAVED_VIEW_CONFIG> --port 0
```
Fresh child PID31990, URL127.0.0.1:63872 (now stopped). No independent Reader/oracle in child or harness, no trace or diagnostic wrapper.

| Request | HTTP | Bytes | Seconds |
|---|---:|---:|---:|
| descriptor |200|804|0.002|
| overview |200|6638|4.233|
| summary |200|1321|4.311|
| gaps first page |**409**|90|2.620|

Successful responses matched all six retained identity fields and profile; overview/summary also matched manifest pin and offline generation. Summary total1,entries1,loaded1,not_loaded0.

Original HTTP error:
```json
{"status":"CANNOT_CONFIRM","reason_codes":["MODULE_RESULT_INVALID"],"module_id":"manager"}
```

Fresh harness has exactly one child. After its SIGINT shutdown:
- RUSAGE_CHILDREN ru_maxrss (Darwin bytes): **542277632**
- unchanged RSS budget: **536870912**
- child total CPU:11.220187 seconds
- child returncode:**-2** (requested SIGINT); waited successfully.

No internal error-code wrapper was added in this acceptance. The observed HTTP409 and measured RSS over budget are facts; no new traceback inside Reader is asserted.

Harness first raised HTTP_FAILURE, then final resource assertion also raised CHILD_RSS_OVER_BUDGET after recording the complete summary. Both actual failures are retained; no failure swallowed.

## Preservation / not reached

Bundle/publication SHA256+mtime maps unchanged. Only this child stopped. No product edits, data rebuild, publish, owner, collection, trading, browser or old-service/port changes.

Stopped at the first failed HTTP response as requested. Gaps next page, materials, original small status, empty stocks and the repeat cycle **NOT_REACHED**. Preview **NOT_STARTED** because acceptance did not pass. No preview URL is offered as live. Raw local command receipts retained; machine-readable sanitized summary adjacent. Real payloads/private roots/config/credentials are not uploaded.

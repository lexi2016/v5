# b2a297 independent semantic boundary diagnosis — gaps RSS rejection

Fixed product unchanged: **b2a2975832aa1cc9f3cc8efc62535c0f07099999**.
Exactly one no-trace diagnostic, no build/tests/browser rerun.
Command: `<EXISTING_PYTHON> <TASK>/b2a_diagnostic_once.py`.
UTC2026-10-12T10:18:14.550858–10:18:26.019336. Harness exit **1**.

A separate API child imports the unchanged original module and wraps only _m18_semantic_response in external harness try/except. On failure it records exception class/fixed code, product-relative file/function/line and process resource counters, then re-raises the same exception. No oracle/Reader in the API process except product's own Reader. No trace, locals/payload dump, product edits, cache or budget changes.

Sequential requests, each once:
- descriptor:200 /804B
- overview:200 /6638B
- summary section:200 /1321B
- gaps first section page:**409 /90B**, public MODULE_RESULT_INVALID.

Original exception: **ContractError: M18_V2_RESOURCE_PEAK_RSS_BYTES**.
API process ru_maxrss (Darwin bytes): **542490624**; unchanged budget536870912.
Boundary process_time delta **2.680617999999999s**, monotonic delta **2.682322959008161s**.
These times are measured around the original semantic-response call, not claimed as its ResourceGuard.usage timer.

Traceback source positions:
- V5/src/v5_shadow/module_api.py:193 _m18_semantic_response
- V5/src/v5_shadow/module_api.py:129 _m18_disk_reader
- V5/src/v5_shadow/m18_offline_v2.py:257 __init__
- V5/src/v5_shadow/m18_offline_v2.py:132 parse
- V5/src/v5_shadow/m18_offline_v2.py:66 checkpoint
- V5/src/v5_shadow/m18_offline_v2.py:41 enforce_usage
- V5/src/v5_shadow/m18_offline_pages.py:27 require

Only owned child SIGINT, waited to exit; returncode-2. Bundle/publication hashes+mtimes unchanged. Existing config/real run reused, no rebuild/republish/owner/acquisition/trading. No further retries or local repair. Minimal machine-readable evidence adjacent; no business bodies or private paths.

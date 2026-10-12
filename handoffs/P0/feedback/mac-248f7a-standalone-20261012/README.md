# Mac 248f7a independent API subprocess: two-page deployment-topology PASS

Fixed unchanged product: **248f7adec7bb329219c1b4f68cde13ba137c5b19**.
One fresh harness, one child; no tests rerun, product edits, resource-limit changes, caching, rebuild, publication or owner calls.

## Actual execution

Harness command: `<EXISTING_PYTHON> <TASK>/standalone_248f7a.py`.
UTC 2026-10-12T10:05:48.490765–10:06:01.515405.
Harness exit **0**.

Harness first loads existing Bundle/Reader, computes original content(0/1) canonical SHA256 plus index/offset/bytes and overview count117, then deletes Reader/Bundle/object references and runs gc.collect before spawning. No Reader is created during HTTP verification and no trace is used.

Only child command:
```text
PYTHONPATH=<FIXED_CHECKOUT>/V5/src:<EXISTING_PYTEST_SITE> <EXISTING_PYTHON> -B -m v5_shadow.module_api --config <RETAINED_LOCAL_ONLY_CONFIG> --port 0
```
First-line URL was read with a15-second startup deadline: http://127.0.0.1:58514 (now stopped).
health.pid **27779** matched Popen.pid and differed from harness.pid **27776**.

| Request, each once in order | HTTP | Response bytes | Seconds |
|---|---:|---:|---:|
| health | 200 | 315 | 0.002 |
| descriptor for run46596b03c2ab4e29b1219fd2e5eb698f | 200 | 804 | 0.001 |
| pages, same run, page0 | 200 | 351042 | 4.331 |
| pages, same run, page1 | 200 | 351047 | 4.391 |

Descriptor and both pages match retained six-field identity, profile and offline generation.
Precomputed original Reader comparisons:
- page0: index0, offset0, content bytes262144, canonical SHA256 010bee22c5376f50882b472b4444a3ea52b7bc611ad4fbe69af8f74dab624433.
- page1: index1, offset262144, content bytes262144, canonical SHA256 3d4ac36211f842609cde4562ae4e3a5590ef74caa6e0a4312c41658d0a1dbd4e.
Both MATCHED.

## Separate resource/cleanup evidence

Fresh harness RUSAGE_CHILDREN has exactly this one child. Darwin ru_maxrss units are bytes:
- **API child peak RSS434536448**, below unchanged budget536870912 (512MiB).
- Harness peak RSS317931520, reported separately and not added to service RSS.
- Child total CPU8.761682 seconds.
- After requests only this owned Popen child received SIGINT. communicate returned within15seconds; child returncode **-2** (SIGINT), with KeyboardInterrupt in stderr; this is the requested signal shutdown, not an exit0 claim. No force kill or other process operation.
- Bundle/publication before-after SHA256 and mtime_ns maps identical.

## Acceptance boundary

**PASS only health/descriptor/page0/page1 in the independent API service topology.** This resolves the two-page deployment-topology check without changing the product or its budgets. Prior same-process oracle/server RSS rejection remains a valid observation of that different topology.

117 total content pages exist; **page2+ NOT_RUN**, no full-stream acceptance. Normal frontend/preview deployment remains NOT_RUN. URL is no longer live. Retained config is reusable for a future explicitly started service; private paths stay local. V4/old ports/services untouched, no collection/trading/browser.

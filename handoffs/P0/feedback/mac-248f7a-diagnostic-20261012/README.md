# 248f7a one diagnostic attempt — observer overhead blocked page1 reproduction

Fixed product unchanged: 248f7adec7bb329219c1b4f68cde13ba137c5b19.
Prior actual page1 HTTP409: 4e0a5538ec2783c62f0e56dca30ec63c85348a24.

Command: `<EXISTING_PYTHON> <TASK>/diagnose_248f7a.py`.
UTC 2026-10-12T09:56:16.632774–09:57:24.624297; exit **1**.
Exactly one diagnostic run, no tests rerun. The external harness used sys.settrace/threading.settrace to observe original exception frames and ResourceGuard.usage return values; no product methods, budgets, identity checks or caches changed.

## Observed result and limitation

Health and descriptor HTTP200, descriptor six identity fields matched. The page0 request returned to the caller, but its subsequent independent Reader verification threw before the harness printed its HTTP summary or sent page1. No exception was captured from _m18_disk_reader or _m18_page_response.

Actual **direct independent verifier** exception:
```text
reader.verify_content(content, expected_index=0)
→ Reader.content(0) → ResourceGuard.checkpoint()
ContractError: M18_V2_RESOURCE_CPU_SECONDS
```

Guard usage at failure:
- peak_rss_bytes: **399917056**
- cpu_seconds: **67.32188500000001**
- wall_seconds: **67.45850787499512**
- scan_nodes: 1259418
- scan_bytes: 72786751

Last captured HTTP-thread Reader usage:
- peak_rss_bytes: 399917056
- cpu_seconds: 33.930001
- wall_seconds: 33.98700345799443
- scan_nodes: 1259418
- scan_bytes: 72786751

**This is not the underlying cause of the previous page1 HTTP409.** Full tracing materially inflated CPU/wall time relative to the previous uninstrumented run and caused the long-lived independent verifier's 60-second CPU budget to reject first. Page1 and its internal exception were NOT_REACHED in this diagnostic. No separate direct call to page-response/disk-reader was made; the direct verification failure is distinct from an HTTP response.

Own server on127.0.0.1:56991 closed cleanly; bundle/publication SHA256 and mtime maps unchanged. No repeat beyond the authorized one diagnostic, no rebuild/publish/owner/acquisition/browser, no protected services touched. A lower-overhead diagnostic remains needed to establish the original page1 code.

## Frontend schema supplement

frontend-schema-summary.json reuses only existing manifest metadata and the earlier sanitized status inventory; no new Reader or validation run. It includes all 55 section names, kinds and total counts, plus actual status/gap field paths. Values are metadata/status/counts only, with no stock entries, business text or private paths.

Key states: announcement_reviewed_analysis.status READY; announcement_observation.status NOT_RUN; us_mapping_research.coverage_diagnostics.status PARTIAL; rebound_research_observation.status CANNOT_CONFIRM; market_screen.status CANNOT_CONFIRM and main_screen_ready=false. gaps has3258 entries; materials3186; rejected_relations1503; existing_material_bindings53; lanes3; themes4; stocks/focus_symbols0. These counts do not imply business completion.

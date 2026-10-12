# Mac real saved-page acceptance — cff144 — 2026-10-12

Fixed candidate: `cff1449646c3bf0e30b3dfdf25e707cc4cda2772`.
Result: targeted real read-only acceptance PASS; not full P0–P5 or 18-module acceptance.

Executed once at 2026-10-12T11:15:38.354863+00:00–11:16:39.208221+00:00 using existing Python 3.14.6, retained config/data pins, fresh isolated API and the candidate's metadata-only `m18_semantic_memory_probe.py serve` instrumentation. No synthetic prepare/build command ran.

Sanitized actual commands:
```sh
PYTHONPATH=<candidate>/V5/src <existing-python> -B <harness>/acceptance_cff144.py
# Harness child:
<existing-python> -B <candidate>/V5/tests/m18_semantic_memory_probe.py serve <retained-config>
# After acceptance passed, reuse existing dist:
V5_MODULE_API_ORIGIN=http://127.0.0.1:51977 <existing-node> node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 54780 --strictPort
```

The harness reached all acceptance assertions and remains running to retain its API for the authorized preview. The API and preview have no final process exit yet; they are intentionally live. Each of 14 page workers has an actual recorded exit 0, a successful supervisor receipt, worker_reaped=true, distinct PID, and absent PID after the sequence. See acceptance-summary.json for every PID, resource measurement, HTTP result and timing.

Descriptor → overview → summary → gaps0 → gaps1 → materials → market_screen → stocks ran twice: all 16 HTTP responses 200. Six-field identity and profile matched on every response; generation and semantic manifest pins matched. Section selectors and offsets checked; gaps1 advanced to offset32. Both cycles' complete response hashes matched per request. market_screen retained CANNOT_CONFIRM; stocks retained zero entries. No payloads are saved in feedback.

Maximum worker peak RSS: 319422464 bytes. Maximum API peak RSS: 35700736 bytes. Maximum worker CPU: 4.451301 seconds; maximum worker measured wall: 4.411904708002112 seconds; maximum supervisor wall: 4.473042792000342 seconds. All remain within original 512MiB/60CPU/90wall gates; no budgets, Reader validation, product code or data were changed. API peak measured independently in API process, not from harness child-rusage.

Original bundle/publication hashes and mtimes unchanged across 141 files. Existing frontend source's 134 tracked files exactly match the fixed candidate; prior dist reused with no rebuild or dependency installation. No old suite rerun, oracle, real collection/trading, credentials access, or unrelated service stop.

Retained local preview: http://127.0.0.1:54780/
Manager entry: http://127.0.0.1:54780/manager-selection/
API: http://127.0.0.1:51977 (PID35966).
Homepage and manager entry HTTP200, title V5 经理已保存结果; proxied descriptor HTTP200 with matching identity, checked 2026-10-12T11:17:17.296655+00:00. Browser interaction not rerun; this is HTTP verification plus the real API acceptance above.

Only this README and metadata JSON are appended. No real payload, local config, private absolute path or LOCAL_ONLY file is uploaded.

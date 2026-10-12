# Mac aa42f4 real rebound acceptance — stopped on first failure

Fixed candidate aa42f4db63a59367d7eb2740c52ffb9aa30f58c3. Targeted real acceptance FAIL. No product modification or retry performed.

Existing environment: view2 + legacy reboundPanelObservation4 tests PASS, Node test:p0 24 PASS, cloud-product vue-tsc PASS, Vite build PASS, each exit0; command timestamps in tests-summary.json.

Actual acceptance: 2026-10-12T12:28:06.550574+00:00 to 12:28:20.522740+00:00, harness exit1. Command (private paths replaced): PYTHONPATH=<candidate>/V5/src <existing-python> -B <task>/acceptance_aa42f4.py. Fresh child: <existing-python> -B <candidate>/V5/tests/m18_semantic_memory_probe.py serve <retained-config>. Run46596b03c2ab4e29b1219fd2e5eb698f, generation8bf699c6bc1fc47a869d2e21d53989a5f5f18d31b52ddef24071c88c4c7ffa8a.

Descriptor200, overview200, announcement first projection page200 (32 entries matching original saved references) succeeded. First rebound request:
GET /api/v4/manager/m18/v2/sections?run_id=46596b03c2ab4e29b1219fd2e5eb698f&generation_id=8bf699c6bc1fc47a869d2e21d53989a5f5f18d31b52ddef24071c88c4c7ffa8a&section=rebound_research_observation&projection=rebound_references&group=strict
returned HTTP409. The existing candidate observation wrapper logged worker status REJECTED and API exception M18_READER_REJECTED. It does not emit the worker's more specific rejection reason; the harness HTTPError did not save the response body. No deeper root cause claimed and no second request made.

Rejected worker PID48612 still exited0 and was reaped; measured peak319799296B, CPU4.732468s, wall4.694134000004851s. Earlier worker48608 and48611 were OK/exit0/reaped. API peak36028416B. Observed peaks were below512MiB; this evidence does not establish an RSS-budget failure. All events captured in acceptance-summary.json.

Stopped only the owned candidate API PID48606 via SIGINT; returncode -2.141 original data hashes and mtimes unchanged. No successful rebound page, LOADED/NOT_LOADED counts or group totals accepted. Remaining strict/near/pending/excluded/unresolved pages, announcement return and stocks/market_screen rechecks NOT_REACHED.

Preview54780 remains efdc43 with existing API60088; no preview switch, Chrome/window control, V4 or other-service stop. No aa42f4 static asset commit because the real acceptance gate failed. Build output remains local. No original payload, private config or absolute path uploaded. Full18-module/P0–P5 acceptance is not claimed.

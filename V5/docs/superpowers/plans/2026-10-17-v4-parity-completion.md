# V5 V4-Parity Completion Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task. Steps use checkbox syntax.

**Goal:** Bring V5 to evidence-backed parity with every evidenced V4 user-visible and operational feature, independently runnable and tested.

**Architecture:** Preserve the fixed integration baseline and module owner closures. Stabilize the manager IPC/test harness first; inventory V4 entrypoints and trace each feature into V5; then repair end-to-end paths in P0–P5 dependency order. Use failing regression tests before implementation and exact cold-read/API/UI/scheduler checks after it. Keep real-provider, review/ack, and natural-window gates blocked unless actual evidence exists.

**Tech Stack:** Python >=3.14 with existing uv.lock; frontend dependencies from existing lockfile; pytest and repository-specific checks; GitHub isolated branch/Draft PR; immutable artifact stores/readers.

**Spec:** PROMPT_FULL_V4_PARITY.md in the 2026-10-17 Drive supplement: https://drive.google.com/file/d/1vVmKnwiyL_soN7f28ah1XdiibTKNjXow/view

## Global constraints
- Fixed baseline: 01d93717905813705732161d4d79062ae5af2d99. Do not use default main as the integration tree.
- Working branch: fix/v5-integration-publication-test-harness-20261017. Latest known commit at plan time: 35829264a7edbeb1b7e54337433080a8fdd94a62.
- Keep M01–M18 and P0–P5 original numbering; B01=M18.
- Preserve algorithms, thresholds, source identity, PIT/qualification/date/session rules, immutable outputs and fail-closed behavior.
- No trading/orders, BUY-gate changes, production switch, V4 writes/restarts, forced pushes, automatic merge, credential transfer, or unauthorized provider/security changes.
- Never treat synthetic/manual/replay/DOM/page-open/WAITING/old results as natural acceptance.
- Do not relax dependency guards or alter lockfiles to pass tests. Preserve historical failures and raw logs.
- Classify every result PASS/FAIL/BLOCKED/NOT_RUN. Real external inputs and natural windows remain separate gates.

## Review focus
- Worker stdout closes while a descendant still holds stderr; IPC must terminate correctly or time out cleanly.
- Result saved but receipt lost; recover by exact cold read without duplicate execution.
- CAS committed but response lost; reconcile ledger/current before retry.
- Request/run/generation/SHA/date/session mismatch; fail closed and preserve old current.
- Missing source/provider/review/window; show truthful WAITING/BLOCKED/UNKNOWN.

## Task 1 — Stabilize manager IPC and test process lifecycle
**Files:** V5/src/v5_shadow/manager_result_transport.py; V5/tests/test_manager_result_transport.py; V5/tests/test_manager_current_recovery.py; integration_tests/test_plan_publication.py.
- [ ] Capture environment, HEAD, full stack, per-test durations, worker PIDs/exit states and stdout/stderr EOF state while reproducing the full-module hang.
- [ ] Add a regression for stdout EOF while stderr is retained by a child/descendant; verify it fails before changing implementation.
- [ ] Trace the failing boundary across _Pipe.read, read_result, run_worker and test HTTP server cleanup. Fix only the confirmed cause.
- [ ] Run the complete transport tests and publication module with bounded per-test/process timeouts; preserve raw logs and exit codes.
- [ ] Verify cleanup after success, malformed/truncated IPC, worker failure and timeout; no leaked process/thread and no duplicate owner run.
- [ ] Commit the narrow repair and update the Draft PR with fresh evidence.
**Acceptance:** whole test module exits reliably with exit code 0 and no leaked child/thread. A Python 3.13 run cannot satisfy the project’s >=3.14 strict environment gate.

## Task 2 — Freeze candidate identity and build the feature parity matrix
**Sources:** actual V4 source ZIP, September patch ZIP, deployment/UI/API receipts; V5 fixed baseline, PROJECT_EXECUTION_PLAN, SOURCE_INDEX, each owner manifest and test receipt.
**Create:** V5/docs/acceptance/V4_V5_FEATURE_PARITY.md, .csv, .json.
- [ ] Hash/version/date-check each available V4 source and receipt; distinguish historical snapshots from current deployed V4.
- [ ] Reverse-inventory V4 routes, templates/components/buttons, CLI, cron/scheduler, collectors, persistent stores/readers, exports, status, management, recovery and rollback.
- [ ] Add one row per feature/subfeature with V4 evidence, observable behavior, inputs/eligibility/PIT/session, algorithm, output schema, cold reader, API/pagination, UI, trigger/timezone, recovery, V5 mapping, tests, hashes and status.
- [ ] Compare V4→V5 and V5→V4; record unmapped and isolated features. Different paths alone do not prove missing functionality.
- [ ] Preserve unverified V4 version/entrypoint facts as explicit gaps.
**Acceptance:** complete evidence-linked machine-readable and human-readable inventory; no feature inferred complete from module count.

## Task 3 — P0 ledger, publication, CAS, retry and rollback
**Files:** run_ledger.py, daily_tick.py, daily_dispatch.py, daily_owner_adapters.py, module_artifacts.py, module_api.py, manager_result_transport.py and focused tests.
- [ ] Trace claim→owner→saved artifact→exact cold read→CAS/current→API response.
- [ ] Test saved-but-receipt-lost, CAS-committed-but-response-lost, and confirmed-never-executed safe retry as three distinct failures.
- [ ] For unknown outcomes, reconcile exact cold read and ledger; never delete claims or blindly rerun.
- [ ] Test stale run/generation/SHA, malformed store, symlink, partial write and rollback; old current and unrelated module roots remain unchanged.
- [ ] Prove GET/refresh/page/date/pagination are read-only and cannot start producers.
- [ ] Verify isolated start/stop/health/recovery/rollback instructions.
**Acceptance:** idempotent publication, correct recovery, exact identity binding, fail-closed corruption behavior.

## Task 4 — P1 M13/M14/M03/M15 → M18 end-to-end path
- [ ] M13: legitimate capture→original builder/reviewer decision import→immutable save→detail/pagination/cutoff. Missing genuine review/ack remains blocked; never fabricate it.
- [ ] M14: preserve 80%/1.5 rules and distinguish observation, READY_WITH_GAPS, CANNOT_CONFIRM, valid empty and formal selection. Preserve 690 pending; do not extrapolate from three symbols.
- [ ] M03: bind real POST_CLOSE/session to original collector, locked dependencies, source identity/cutoff, save and cold read. News is not quotes.
- [ ] M15: verify seed and material paths independently; exact HK identity and supported evidence required; unknown PIT remains unknown and unsupported relationships remain UNASSESSED.
- [ ] M18: same manager run/generation/SHA references the three lanes; upstream retain their own run/date/session. Verify immutable publication, ordinary API, pagination, original UI and independent cold process.
- [ ] Test missing/blocked lane beside healthy lane; no fabricated success. Test natural triggers separately from manual/replay.
**Acceptance:** real saved artifacts consumed by independent readers and ordinary API/page. Synthetic tests prove contracts only.

## Task 5 — P2 M01/M02/M03/M05/M06
- [ ] Compare complete pinned owner manifests/closures before transplanting code; preserve passing work.
- [ ] M01: immutable formula/source binding, strict identity/SHA/cutoff, no overwrite and cold reread.
- [ ] M02: native security identity and HK Connect membership/eligibility reader; reject dictionary-only VALID claims; atomic frozen assets.
- [ ] M03: complete collector owner, cold-process readback, UTC/cutoff/daily binding and explicit unavailable-provider behavior.
- [ ] M05: original A preselection algorithm→six immutable pools→readback→M07; strict root/marker and expected-missing semantics.
- [ ] M06: real HK master/eligibility→verified publication; enforce expected source, 100-row readback and four identity checks where contracted.
- [ ] Add focused negative tests and evidence receipts per module.
**Acceptance:** source-bound input, original calculation, immutable save and exact cold reader; gaps remain explicit.

## Task 6 — P3 M07/M08/M09/M10
- [ ] M07: A-only admission, selector binding, research/publication and daily descriptors.
- [ ] M08: eight-stage identities/windows/original formulas; mismatch rejected and absent Stage 8 input remains absent.
- [ ] M09: two-slot A-share close review, immutable save and cold read using fixed M09 lineage.
- [ ] M10: original 698-row replay, seven-stage partial/null behavior and independent daily publication.
- [ ] Test cutoff/session boundaries, partial/empty/provider failure and idempotent rerun.
- [ ] Do not substitute historical replay for a new-day natural run.
**Acceptance:** original semantics and reproducible saved artifacts, with date/session mismatches rejected.

## Task 7 — P4 M04/M11/M12/M16/M17
- [ ] M04: capture→original builder→import/store→cold archive read; preserve UNKNOWN/out-of-scope and exact dependency profile.
- [ ] M11: six review slots and trusted bindings; WAITING stays WAITING.
- [ ] M12: video lifecycle, retry/recovery, archive readback, ASR_REVIEW_REQUIRED and missing stock dictionary.
- [ ] M16: public-source task lifecycle, ensure/retry/cancel/events and saved-result readback.
- [ ] M17: real 15:30 discovery/monitoring, prepare/materialize/reader, cutoff and follow-up; late readback is not proof of original-window execution.
- [ ] Run non-daily modules at their real trigger when available; otherwise BLOCKED.
**Acceptance:** producer/save/cold-reader/recovery lifecycle with trigger semantics preserved.

## Task 8 — P5 full regression, independent operation and release
- [ ] Create fixed release candidate from reviewed commits and generate manifest/SHA-256.
- [ ] Use isolated Python >=3.14 and frontend dependencies from existing lockfiles via authorized official sources; if blocked, record exact missing binary/package/version/command and continue independent tests.
- [ ] Reproduce recorded historical failures; run focused and full backend tests, type checks, frontend tests/build, API/pagination/cold-read, real browser UI, isolated start/upgrade/rollback and safety checks.
- [ ] Record exact source/input hashes, command, environment, exit code and raw stdout/stderr; separate PASS/FAIL/BLOCKED/NOT_RUN.
- [ ] Check V4 read-only snapshots/health where permitted; never write/restart V4.
- [ ] Verify two consecutive eligible natural trading-day continuations and real non-daily triggers without clock changes/manual substitution; unavailable windows remain blockers.
- [ ] Deliver via authorized isolated GitHub branch/Draft PR or new Drive results folder; do not overwrite, force-push, change permissions or merge.
- [ ] Re-read remote commit/files and verify hashes/sizes. If ZIP exceeds transfer limits, provide <=9 MB parts and self-contained verifier.
- [ ] Obtain independent review; fix findings and rerun impacted tests.
- [ ] Report code, test, natural operation and remote delivery statuses separately.
**Acceptance:** claim full acceptance only after every parity row and required same-version test passes, real paths work, independent start/rollback is reproducible, natural windows pass, and remote delivery is read-back verified. Otherwise status is V5_FULL_ACCEPTANCE_BLOCKED with evidence and exact remaining dependencies.

## Final evidence package
- V4_V5_FEATURE_PARITY.md/.csv/.json
- Base/parent/candidate commits and SHA-256 manifest
- Focused/full logs, environment, exit codes and raw failure output
- API/cold-read/browser evidence for every claimed end-to-end path
- Scheduler, CAS ambiguity, retry, rollback and independent-start evidence
- Start/stop/health/upgrade/rollback runbook
- PASS/FAIL/BLOCKED/NOT_RUN ledger
- Verified remote branch/PR or isolated Drive folder and chunked transfer package

## Execution rule
Continue all tasks executable within current access and safety boundaries; do not stop after the plan or interim PR. Isolate genuine provider, authorization and natural-window blockers while continuing independent code work. Stop only after all runnable work is implemented and verified, remaining blockers are evidenced and itemized, and the final remote artifact has been re-read and verified.
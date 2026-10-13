# M06 deterministic dispatcher receipt discovery

## Fixed evidence and scope

This small continuation follows real Mac read-only admission feedback [4bf6001](https://github.com/lexi2016/v5/blob/4bf6001332126870076eac1d1f827775fe6dfc57/handoffs/P0/feedback/mac-m06-bridge-20261013/REPORT.md) and the [original interface evidence](https://github.com/lexi2016/v5/blob/da278dfdc533b83a491762aab9fc96466cf0d0db/handoffs/M06_DAILY_CONTINUATION_MAC_20261013/ORIGINAL_INTERFACES.md).

The historical D12->13 chain's hashes passed on Mac, but its existing pool manifest lacks three mandatory safety fields and GENERATE_IF_ABSENT conflicts with the existing target pool. This change does not repair, delete, filter or regenerate that pool. D13 inputs had not arrived at 12:42–12:44 Beijing; ordinary pre-close waiting is not an adapter failure.

Only m06_input_delivery.py, its new targeted test, and the disabled example change. Original owner/model/reader, both ledgers, deadline guard, calendar, other lanes, shared module registration and frontend remain unchanged.

## Explicit locator and deterministic choice

Old dispatch_receipt_relative remains supported. New dispatch_receipt_discovery="DAY_SLOT_UUID_V1" is mutually exclusive with it. No wildcard configuration, arbitrary nested scan or latest pointer is introduced.

The resolver opens only the trusted dispatch_receipt_root / scheduled_date / dispatch_slot directory, with no symlink traversal. It considers direct lowercase 32-hex UUID.dispatch-receipt.json regular files only. Limits: 256 directory entries, 64 candidates, 64 MiB total candidate bytes and the existing 16 MiB per-JSON bound. Unsupported mode, symlink/special file, malformed JSON, safety failure, byte limit and observed mutation fail closed.

Each candidate uses the unchanged validator: v3_5.dispatch.v1 LIVE/SUCCEEDED; business_date=scheduled_date=D; configured slot; exact unique research_panel_daily_hk success/invocation; one successful result with integer exit_code=0; resolved_dates scheduled/signal/target all D; equal direct source_result/_authoritative_payload envelopes; envelope -> exact lane raw bytes/SHA -> authority -> captured panel identity/payload. The panel workload target is D, whereas the V5 target is D+1 from the unchanged original HK securities calendar in P0. No dispatcher run_id or unverified new safety fields are required.

Eligible finished_at must be aware, on D, not before the configured panel slot, and not in the actual future. It is upstream panel evidence, never full-delivery completion or the V5 execution deadline. Every eligible receipt must bind the same stable lane raw bytes and captured panel; an observed lane change rejects the attempt.

Among full-chain eligible candidates, the new V5 rule is ascending parsed finished_at, then raw dispatcher SHA256, then exact relative path. It does not claim that the upstream writer already had this policy or was immutable. No eligible receipt returns WAITING_M06_INPUT_DELIVERY. Missing day/slot directory waits before the still-current previous-day panel can be misclassified. Other input integrity failures remain blockers.

The selection's exact path/SHA is retained by the existing seal and copied as original bytes. All scanned candidate files and directory identity are rechecked before and after copy; selected or unselected mutation or directory replacement/addition prevents sealing. Once a seal exists, reuse verifies its bytes and never rescans live receipts or moves selection to a newer candidate.

## Disabled configuration

In the existing private disabled draft, remove dispatch_receipt_relative including UNRESOLVED_EXACT_RECEIPT; add dispatch_receipt_discovery="DAY_SLOT_UUID_V1". Keep dispatch_slot="1720", lane_receipt_relative="hk-{signal_date}.json" and the same verified read-only roots and independent marked outputs. Do not include both locator keys.

The repository template now records the explicitly confirmed NEW V5 policy: full/half 17:30–18:30, complete budget1200, process timeout600, target-day09:00 compatibility cutoff. All three enable switches stay false. 300s is the external trigger cadence, not permission to install or enable one. The whole-chain budget is not guaranteed sufficient for every real input; preclaim rechecks continue to reject insufficient remaining time. Do not carry over old timeout1800. The template is full application config with nested daily; the daily CLI requires that daily object as its flat configuration file.

The compatibility cutoff does not extend D18:30, replace PIT labels or backdate completed_at. No real snapshot/delivery, claim, model, provider, natural scheduler or deployment ran in this cloud repair.

## Mac verification and read-only preflight

Verify the 12-file source-closure.json. It covers the focused tests and their imported helpers at the stated dependency base; shared helpers are inherited, not changed by this patch. Run the exact 24-case command in verification.json using existing HK02 and an isolated TMPDIR. There are 19 new real-file synthetic tests plus five existing exact-locator regressions. Cloud24/24 PASS, no skips, ResourceWarning=error; two positive cases first failed on the old missing discovery contract. Mac candidate acceptance and real receipt discovery are NOT_RUN here. Do not rerun the old89/85/15 suites.

For a read-only actual-input preflight, no prepare_input_delivery/prepare_daily_candidate/owner call is needed. With the configured original roots and exact D/next-session pair, call _dispatch_candidates(config,D), then _capture_inputs(config,D,target), _capture_upstream(capture,config,D,target,candidates=candidates), and _recheck_capture(capture). Report capture['upstream_evidence'] only after all succeed; FileNotFoundError means WAITING. These calls do not write a snapshot, delivery, ledger or product. The old D12 pool safety failure must remain visible; today's missing receipts must not be relabeled as ready.

Leave all switches disabled, retain old pools/references and record actual Mac results before any separately authorized execution or deployment.

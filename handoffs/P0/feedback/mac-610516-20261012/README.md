# Mac checkpoint continuation — 610516

Fixed product: **610516d6c53fa29ec2e9f0444a2fadd6158db0c7**, parent cab5167ae3bf55d5953803709fafc35206cdb74e.
Only product change: V5/src/v5_shadow/p0_manager_owner_checkpoint.py, blob **25ca9030c3bf22d583233e7285eb1718bfca980c**.
674 materialized product/dependency blobs verified before and after execution. No local product edits or mock tests.

## Result: real manager save and fresh reader matched; partial business state retained

Reused the exact saved announcement from the prior original fixture preparation:
- Fixture source 0fec605b5c0607f1433f9adaaf684c90f702606b.
- Evidence run **c04777eba0a5312c7350981b569f78e2**.
- binding SHA **999f31648e2c60f9a34e187b25a45ecbddb8d91aea0d3a5bdb6ffc667288b696**.
- target **20261009**, publication **2026-10-08**; assembly test clock **2026-10-09T00:45:05Z**.
- Canonical announcement row {lane, state.attempts[-1].readback_verified=true, product_reference:{binding}}; no generic run/artifact fields added.
- Factory/capture preparation was **NOT rerun**. No US/rebound saved artifacts had been generated in the prior stopped probe; they remain explicitly unbound in this same-input continuation, not silently fabricated or claimed tested.

Actual checkpoint -> assembly -> original manager worker reached and saved:
- Manager run **07fd3f9ae27c427a8185a397db5fff9b**.
- plan SHA **4a4f89327ebf4439f5d684f2452b9d885f2860131a8f7492fbb6fb0766ddff21**.
- input_identity **1288b2571d1777577e55915df363750e942f22ec1411f76599364ff2beea8c8a**.
- checkpoint request SHA **4a89cd187e936cb2138449aa4f458ac6613118e9617590febeaaa463d95cdd93**.
- Saved adapter readback status **MATCHED**, store_relative "."; four saved plan/attempt JSON files.
- A subsequent fresh original manager worker with action=read matched **run_id, plan SHA and input_identity**, plan_product CURRENT / consumed=true.
- All **186 announcement fixture files** unchanged; the independent read left saved plan files unchanged.
- announcement_reviewed_analysis **PARTIAL**; market_screen **CANNOT_CONFIRM**, main_screen_ready=false; announcement_observation **NOT_RUN**.
- Original announcement read transport VERIFIED_READ_TRANSPORT, but announcement consumption **NOT_CONSUMED_AFTER_CUTOFF**, gap **ANNOUNCEMENT_ANALYSIS_NOT_AVAILABLE_AT_PLAN_CUTOFF**. This is legitimate PIT rejection retained at the requested early historical cutoff. A saved manager plan being consumed does NOT mean announcement business inputs were consumed.
- Other retained gaps include SCREEN_AUTHORITY_ROOT_NOT_BOUND, HK_CONNECT_TARGET_AUTHORITY_ROOT_NOT_BOUND, RESEARCH_ARCHIVE_READER_NOT_BOUND and missing original market/native bindings.
- natural_verified=false; publication remains NOT_CONNECTED_IN_THIS_SLICE.

## Actual commands, UTC times and honest harness outcome

Existing Python 3.14.6; private interpreter/task paths redacted. External harness files only; no other tests run.
```sh
$PY <TASK_HARNESS>/consume_checkpoint_610516.py
```
**2026-10-12T05:30:44.637788+00:00 → 05:30:45.880801+00:00**, outer probe **exit 1**.
The product checkpoint returned successfully and its full result was saved locally. The harness then used a nonrecursive ledger request glob and failed an assertion; actual sealed request lives under ledger/manager_plan/20261009/. This is a **harness locator error after successful save**, not a product rejection:
```text
consume_checkpoint_610516.py:30
  requests=list(ledger.glob('request-*.json')); assert len(requests)==1
AssertionError
```
No second refresh was run to hide or retry that event. The saved exact request was located read-only, and the next command resumed at independent read:
```sh
$PY <TASK_HARNESS>/read_checkpoint_610516.py
```
**2026-10-12T05:32:29.521397+00:00 → 05:32:30.677046+00:00**, **exit 0**, PASS_SAME_RUN_INDEPENDENT_READ.
The fresh worker executed original run_manager_plan(dict(sealed_request, action="read")); assertions compared the above three identities and before/after source/plan hashes.

## Observation boundaries

External instrumentation delegates original Python child commands through an audit wrapper; it does not replace product functions or returned results. Only assembly.datetime is patched to the declared historical test clock. The wrapper denies network events and original PrivateOwner.begin_capture during consumption and observes relevant calls. Product source and capsule identities remain unchanged.

Save phase parent counters: checkpoint=1, assembly=1, manager adapter=1, child command manager_plan.py=1, network attempts=0, begin_capture attempts=0. **Save-child counter files were not retained:** the initial observer attempted to open its log after product I/O restrictions were installed. Do not extrapolate parent counts into complete child-phase zero-call evidence. Network/capture guards were installed in the child, but a complete persisted save-child count is an explicit remaining evidence limitation.

For the independent read only, the external observer opened its own diagnostic stream before product execution and retained all three process reports:
- parent adapter -> fresh manager_plan.py -> announcement_offline_reader.py.
- Each reports network attempts **0**, begin_capture attempts **0**.
- Original read_owner and read-only validation calls observed; no refresh_workspace_plan in the reader.
- CaptureBudget class initialization and _read_capture_partition/validate_terminal_body_capture names are reader/validation calls, not capture execution.

Do not claim full zero-upstream-computation coverage beyond the named observer hooks, and do not rerun saved-input refresh solely to overwrite the missing initial observer evidence. Raw hashes/results and diagnostics stay local. No network fetch, new fixture generation, real input edits, orders, V4/preview changes, startup/ledger/frontend-test repeats, or main changes occurred.

## Handoff

The prior announcement-shape rejection is resolved for this native row. Real backend **save -> independent same-run read** is demonstrated with preserved partial/PIT outcomes; all-three-owner acceptance and announcement post-cutoff consumption are not demonstrated. No preview deployment occurred in this batch. Append this receipt under the requested feedback path using fresh integration HEAD/base and expected-SHA CAS.

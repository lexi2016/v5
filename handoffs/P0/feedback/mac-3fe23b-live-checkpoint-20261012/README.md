# Real original announcement factory → checkpoint contract failure

Product fixed candidate: **3fe23b52508dd53d1dc2c9f56c86afb4d221f583** (checkpoint blob ac8199aa06a72f89c0abfe49f0e95d085c61b04c).
Fixture fixed source: **0fec605b5c0607f1433f9adaaf684c90f702606b**, branch dev/p0-announcement-fixture-source-20261012.
Read fixture START_HERE first; its declared privacy-derived metadata/SHA256SUMS scope was preserved. Verified 674 materialized product/dependency blobs and all 36 fixture-branch blobs at their respective fixed commits. No product edits; no mock-positive tests run.

## 1. Original legal synthetic factory: PASS

External task-owned harness imported original tests/test_offline_analysis_chain.py and executed exactly:
- OfflineAnalysisChainTests.setUpClass()
- case.setUp()
- case.test_prepare_verify_import_and_readback_keep_failed_pages_unassessed()
- case.tearDown() preservation assertions

This invokes the supplied original factory chain and assembler, original synthetic transport capture, recovery, prepare, registered handoff, verify, import and owner readback. It does not replace owner results with mocked success. The original fixture's documented synthetic trust-anchor patch is retained as part of that factory, not a production trust claim.

Actual command (private interpreter/task paths replaced):
```sh
$PY <TASK_HARNESS>/live_checkpoint_harness.py prepare
```
UTC **2026-10-12T05:17:45.520860+00:00 → 05:17:47.816804+00:00**, **exit 0**.
Existing Python 3.14.6, no installation. Temporary fixture stays in task-owned isolation for exact failure reproduction.

Observed:
- Original owner readback assertions passed.
- Evidence run: **c04777eba0a5312c7350981b569f78e2**.
- binding_sha256: **999f31648e2c60f9a34e187b25a45ecbddb8d91aea0d3a5bdb6ffc667288b696**.
- target_date **20261009**, publication_date **2026-10-08**.
- BODY_CAPTURE_FAILED / NOT_ASSESSED / TEXT_INSUFFICIENT_UNASSESSED preserved.
- Retained pages **60**, expected pages **108**.
- Preparation counts: owner begin_capture **1**, manager **0**, network audit attempts **0**, subprocess attempts **0**. Do not describe fixture preparation as zero owner computation.
- Original fixture deny-network hook and external harness audit hook active. No real capture, credentials or business data involved.

Binding adapter uses original manager_binding.v1.json bytes:
```text
binding = {
  root: <ORIGINAL_DERIVED_FIXTURE_ROOT>,
  binding_sha256: SHA256(exact manager_binding.v1.json bytes),
  target_date: file.target_trade_date,
  publication_date: file.publication_date
}
```
The original binding file has evidence_run_id/product_sha256/product_file_sha256 and original import/readback receipt identities. These are not silently relabeled as a different lane's artifact identity.

## 2. Actual checkpoint invocation: FAIL before assembly

Actual command:
```sh
$PY <TASK_HARNESS>/live_checkpoint_harness.py consume
```
UTC **2026-10-12T05:17:56.902320+00:00 → 05:17:57.023489+00:00**, **exit 1**.

The harness used a new marked ledger/output, empty manager/materials/us bindings for the deliberately missing lanes, target **20261009**, and explicitly patched only assembly.datetime.now to **2026-10-09T00:45:05Z**, as requested for this declared historical synthetic test. No real input dates or PIT were edited. No manager result/output function was mocked.

Canonical existing assembly row shape passed:
```json
{
  "lane": "announcement",
  "state": {
    "attempts": [
      {
        "readback_verified": true,
        "product_reference": {
          "binding": {
            "root": "<ORIGINAL_DERIVED_FIXTURE_ROOT>",
            "binding_sha256": "<EXACT_BINDING_SHA256>",
            "target_date": "20261009",
            "publication_date": "2026-10-08"
          }
        }
      }
    ]
  }
}
```

Actual stack, no private paths:
```text
live_checkpoint_harness.py:65
  run_saved_owner_checkpoint(template, rows, ledger, registration)
V5/src/v5_shadow/p0_manager_owner_checkpoint.py:40
  rows = [_require_reference(row) for row in owner_rows]
V5/src/v5_shadow/p0_manager_owner_checkpoint.py:34
  raise ValueError("OWNER_REFERENCE_IDENTITY")
ValueError: OWNER_REFERENCE_IDENTITY
```

The current wrapper accepts the ledger envelope but still requires every lane-specific product_reference to contain top-level string run_id and artifact_sha256. The actual announcement reference contract is {binding: ...}; the original assembly announcement case consumes that binding. This legal factory reference is rejected before assembly is called. No extra fields, fake success or product patch were inserted to pass the guard.

Observed consumption phase counts from a call-profile observer:
- checkpoint **1**
- assembly **0**
- manager **0**
- owner begin_capture **0**
- network attempts **0**
- subprocess attempts **0**

All saved announcement fixture bytes unchanged across checkpoint call; manager output contains **0** JSON plans. Assembly, manager save and new-reader same-run readback are **NOT_REACHED**. The test's conditional guard against an uninstrumented manager child was never hit; no child was spawned in consumption. Thus this run makes no claim of manager subprocess network/call coverage beyond the confirmed pre-assembly failure.

Per instruction to stop at a real function-contract failure, US/rebound helper consumption and additional missing-lane variants were **NOT_RUN** after this first canonical announcement-row rejection. This is not a claim those lanes are absent from the product or that they passed. Correct the lane-specific admission contract in the original product and return a new fixed candidate; do not invent generic run/artifact fields for announcement/rebound solely to satisfy this wrapper.

## 3. Preserved boundary

No startup/ledger/frontend-build repetitions, deployment, live preview replacement, external acquisition, trading, system changes, credentials or real body upload. The saved synthetic fixture and raw command evidence remain local. The original 60/108 failure state remains; no formal eligibility or full-market success claim.

This is **factory PASS + checkpoint FAIL**, not backend end-to-end PASS. Manager-only refresh from admitted saved references remains authorized; no refusal is based merely on the action name. The explicit simulated clock and this fixture's preserved timestamps were not yet evaluated by downstream manager PIT because execution stopped earlier.

Append minimal sanitized feedback using fresh integration HEAD/base and expected-SHA CAS; preserve concurrent commits.

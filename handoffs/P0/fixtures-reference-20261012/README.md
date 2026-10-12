# P0 saved-owner fixture/reference handoff — read-only, 2026-10-12

This is a short input-contract inventory, not a new source review or test receipt. No old tests, 62a96 negative tests, collectors, owners or manager runs were executed. No real bodies, private paths or credentials are included. Fixed source links below use the already available 3d5458 candidate; no source repackaging.

## 1. Original assembly 21602: date and clock are an explicit synthetic pair

The preserved local 21602 PASS receipt reports original 8/8 plus targeted 8/8 on 2026-10-12 01:27 UTC (not rerun here). Its assembly file blob is **63e5a84215962bd74703ef80d39f5db54fe1373c**, identical to the file present in the linked fixed candidate.

- [V5/tests/test_daily_manager_assembly.py](https://github.com/lexi2016/v5/blob/3d5458d9608c2ff53fffd7d36e23e6f194d2e9e8/V5/tests/test_daily_manager_assembly.py), class DailyManagerAssemblyTests.setUp/row/assemble.
- [V5/tests/daily_ledger_fixture.py](https://github.com/lexi2016/v5/blob/3d5458d9608c2ff53fffd7d36e23e6f194d2e9e8/V5/tests/daily_ledger_fixture.py), **make_ledger_fixture(add_cleanup)** creates a temporary ledger root and writes MARKER to .v5-daily-run-ledger. It returns root, identity and success fixture.
- [V5/src/v5_shadow/daily_manager_assembly.py](https://github.com/lexi2016/v5/blob/3d5458d9608c2ff53fffd7d36e23e6f194d2e9e8/V5/src/v5_shadow/daily_manager_assembly.py), **assemble_manager_request(template, lanes, ledger_root, registration)**; no default parameters.

The original assembly fixture declares target_date **20261009**, template.now **2026-10-09T00:00:00Z**, and patches only the assembly module's datetime.now to **2026-10-09T00:45:05+00:00** (08:45:05 UTC+8). It later advances the synthetic clock to 00:50 and asserts the originally sealed request/cutoff is reused. Registration selects code_sha256/config_sha256/dependency_sha256 from the ledger fixture identity.

Therefore the correct historical synthetic assembly scenario is that declared 20261009 target + declared 2026-10-09 assembly clock, not a 20261009 target under the real 20261012 wall clock. This is an explicit test clock, not evidence of natural operation. Do not change real saved input dates or bypass PIT. The earlier b10f probe used a different empty-owner recovery fixture under actual clock and correctly hit DAILY_MANAGER_TEMPLATE_TARGET; it did not reproduce this original assembly clock fixture.

**product_reference(row)** reads row.state.attempts[-1].product_reference only when the last attempt readback_verified is True. Original test row shape:
```text
{lane: <lane>, state: {attempts: [
  {readback_verified: true, product_reference: <lane-specific saved reference>}
]}}
```

The 3d5458 wrapper additionally requires top-level row.product_reference with string run_id/artifact_sha256. That is not the same row envelope as the existing assembly helper. Original P0 author must deliberately reconcile these input contracts; do not silently fabricate a second identity or treat top-level-only references as consumed.

## 2. Reusable exact factories and what each actually proves

| Existing fixed source/helper | Factory / saved contract | Limit |
|---|---|---|
| [test_daily_manager_assembly.py](https://github.com/lexi2016/v5/blob/3d5458d9608c2ff53fffd7d36e23e6f194d2e9e8/V5/tests/test_daily_manager_assembly.py) :: test_us_exact_run_bytes_copied_and_changed_pointer_rejected | Generates SYNTHETIC VALID_EMPTY US run for 20261009; run='a'*32; artifact_sha256=sha256_json(unsigned daily); writes canonical runs/<run>.json and matching latest.json. Ref has target_date/run_id/artifact_sha256/manager_output_root. | Assembly copying/head identity fixture only; minimal payload is not proof of full manager consumer acceptance. |
| [test_manager_plan.py](https://github.com/lexi2016/v5/blob/3d5458d9608c2ff53fffd7d36e23e6f194d2e9e8/V5/tests/test_manager_plan.py) :: ManagerPlanAdapterTests.setUp(), save_daily(self, generated='2026-10-09T09:00:00+08:00') | Creates manager/materials/us input roots, .v5-manager-plan-root, complete synthetic US daily/pointer and SHA-bound files. Declares target 20261008, session 20261007, cutoff 2026-10-08; fixed synthetic run='1'*32. | Explicit CANNOT_CONFIRM qualification and synthetic gaps. Do not relabel this 20261008 fixture as 20261009 or real current data. Its save test asserts MATCHED and same-run plan/attempt, but US reference is not CONSUMED. |
| [test_manager_current_recovery.py](https://github.com/lexi2016/v5/blob/3d5458d9608c2ff53fffd7d36e23e6f194d2e9e8/V5/tests/test_manager_current_recovery.py) :: ManagerCurrentRecoveryTests.setUp(), read(self, **changes), snapshot(self) | Empty owner inputs, marked output, target 20261009, actual current now; direct manager refresh/current-recovery and independent action=read tests compare run/plan SHA and unchanged files. | Reusable manager save/read infrastructure, not saved three-owner evidence; direct manager historical recovery differs from assembly current-target gate. |
| [test_manager_rebound_observation.py](https://github.com/lexi2016/v5/blob/3d5458d9608c2ff53fffd7d36e23e6f194d2e9e8/V5/tests/test_manager_rebound_observation.py) :: ManagerReboundObservationTests.setUp() | Uses existing **rebound_owner._publish(root, artifact)** to materialize a synthetic saved recorded-input failure, target 20261009, signal 20261008, run='9'*32. Marked .v5-rebound-owner-root; receives original immutable reference. | CANNOT_CONFIRM / MASTER_RECEIPT_MISSING deliberately retained; no live computation. Reference has run_id/artifact_sha256/manifest_sha256/receipt_sha256. Useful positive saved-reference consumption without claiming formal selection. |
| [test_manager_offline_announcement.py](https://github.com/lexi2016/v5/blob/3d5458d9608c2ff53fffd7d36e23e6f194d2e9e8/V5/tests/test_manager_offline_announcement.py) :: OfflineAnnouncementOriginalChainTests.setUpClass() | Requires V5_ANNOUNCEMENT_OFFLINE_TEST_BUNDLE; invokes upstream tests/test_offline_analysis_chain.py synthetic original-owner preparation with child deny-network hook; reads derived manager_binding.v1.json into root/binding_sha256/target_date/publication_date. | Upstream bundle/test is NOT in the linked candidate tree. Missing object is the exact shareable upstream synthetic fixture bundle, not a future trading day. Do not fake binding/receipt files. |
| [tools/cloud_preview/make_synthetic_recovery_fixture.py](https://github.com/lexi2016/v5/blob/3d5458d9608c2ff53fffd7d36e23e6f194d2e9e8/V5/tools/cloud_preview/make_synthetic_recovery_fixture.py) | Existing command --out <new file> uses recovery fixture, original run_manager_plan, then separate action=read and returns expected_run/expected_sha. | SYNTHETIC_EMPTY_OWNER_NOT_BUSINESS_EVIDENCE. Reference only; not executed here and not a three-owner positive test. |

Important exact interfaces:
- **run_manager_plan(request)** in [manager_plan.py](https://github.com/lexi2016/v5/blob/3d5458d9608c2ff53fffd7d36e23e6f194d2e9e8/V5/src/v5_shadow/manager_plan.py).
- **read_owner(binding, cutoff, *, default_analysis=False)** in [announcement_offline_reader.py](https://github.com/lexi2016/v5/blob/3d5458d9608c2ff53fffd7d36e23e6f194d2e9e8/V5/src/v5_shadow/announcement_offline_reader.py).
- **rebound_owner._publish(root, artifact)** is an existing test-used private helper, not permission to fabricate real records.
- **m18_offline_v2.Reader(bundle, expected_manifest_sha256, expected_identity, *, expected_profile, guard=None)** reads an already-built v2 bundle.

An announcement lane reference uses {binding: {root, binding_sha256, target_date, publication_date, optional revision_manifest_sha256}}; a rebound lane uses {root, reference: {run_id, artifact_sha256, manifest_sha256, receipt_sha256}}. They are not interchangeable US references.

## 3. Already-saved local results: metadata-only findings

A known isolated M18 v2 bundle **exists**. Only marker/identity/receipts and file existence/size were checked; no response/object/business body was opened or uploaded in this inventory.
- bundle/manifest.json: exists, 29,714 bytes.
- bundle/ACCEPTED.json: exists, 658 bytes, keys profile_sha256/identity/usage.
- response.canonical.json: exists, 30,465,412 bytes.
- run_id **46596b03c2ab4e29b1219fd2e5eb698f**, target_date **20261012**.
- plan_sha256 fed238e033181b159f419918c8c54dcb4743791b18f93d31e2a1e2006f5924ce.
- raw_sha256 7de6ea9fc6b10462fcc75af1c02c9d9d5111288a9d993b7f154ca988fea4e4db.
- response_sha256 ae840ac69d9fdc8f25bd675c41e8e3f6d028ef17147987b36220a35a6d786d22.
- input_identity c99d03b5dfe289f93382d14e1aa4c083283283270c27287e1e752b71f2d465de.
- v2 generation 8bf699c6bc1fc47a869d2e21d53989a5f5f18d31b52ddef24071c88c4c7ffa8a.
- manifest SHA f655cdfcd5894861318a3d4d72ec2559580ea2f942440a3a9bfaeba0d041595d.
- profile SHA a8b56161f6d19de0d5222775e132d78f75d7ad707a1824b4d2b861ff285ecc6c.
- Existing build-result/read-result receipts: status OK, worker_exit 0. Existing receipt says original cutoff 2026-10-11T23:42:13.933163+00:00, one build + fresh-process read, manager=0/producer=0. These are **prior evidence**, not a new validation.
- Business remains **PARTIAL / CANNOT_CONFIRM**; target module publication head null. Offline generation is not a CAS module head.

The known saved-input audit records US run **f8041aabc13e4715b5b1fe8bdd95b5ed**, reviewed-announcement target/publication pair **20261012 / 20261009**, and saved rebound research READY_WITH_GAPS. It also records announcement selection capture missing for the required window, formal rebound SCREEN_AUTHORITY_ROOT_NOT_BOUND, and THREE_LANE_BUSINESS_ACCEPTANCE_NOT_VERIFIED. These are existing metadata assertions, not a newly admitted complete owner bundle. No complete three-owner bundle with exact owner hashes/roots/receipts was independently validated here.

## 4. Minimum next positive test

Reuse marked temp ledger/output and original snapshot/read helpers. The author can author a new explicitly synthetic, internally date-consistent saved-owner fixture from these factories, with unchanged historical source meaning; keep target/session/publication/cutoff/finished_at relationships explicit and inject a declared assembly clock for a historical scenario. Bind the original owner capsule/dependencies. Test original manager save -> independent exact read with same run/hash and preserved failure/qualification states, plus deny-network and zero upstream owner-computation counters. Do not mock manager output into a PASS.

Clarified refresh authorization: manager-only assembly/save from already admitted saved references is allowed in isolation; external acquisition, upstream owner rerun and trading remain forbidden. Judge actual calls/effects, not the word refresh. This note corrects the overly broad no-refresh reading in b10f; it does not retroactively change that run's NOT_REACHED result.

No new execution or complete business acceptance claimed. Append-only documentation, fresh integration HEAD/CAS; real bodies and private source paths remain local.

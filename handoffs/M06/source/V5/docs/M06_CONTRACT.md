# M06 HK Top100: verified consumer, daily owner and immutable publication

This is an isolated V5 M06 source delivery. It does not install into V4, change a shared guard, edit M02/M08/P0, start a service, collect prices, send orders, or certify real production data. The original source tree is retained byte-for-byte.

## Provenance and scope

- Original SOURCE: lexi2016/v4 at f7cb731c384ee6890a87d16c19a5b5a621779477. SOURCE_MANIFEST.json retains the original 60-file inventory and donor paths.
- The original hk_preselection.py SHA256 remains 00ccdaa1890675335836351d33c4fea5f9458a8dd287e3724efb9f0cb0fb1b21. All original guard, calendar, reader, projector, validator and 34-file capsule bytes remain unchanged.
- Latest consumer predecessor: R8 ZIP SHA256 17c35ba35df7214b6bf48c2e91ac8deacde49f5fa225f6d8e119c7f38c0097b8. R8 fixed lexical relative paths but called a missing runtime capsule. This delivery replaces that missing chain with actual default cold-worker calls.
- Publication predecessor: R6 ZIP SHA256 dc5e1c0b62497099526042558a2b821835994826072b54d1e3212e3264b05ea1. Daily predecessor: R4 ZIP SHA256 dd641392f247c535843c040a79e0a43d9e645aeaa607ca38cc1180fcec70f12b.
- M07's fixed run_ledger.py after SHA256 d3ba8dc00de2525ccfc2756193be1338bb800c796c2302f6c97f525a76b5748e is copied unchanged as a private runtime dependency. Its original module_api/module_artifacts/api_gateway helper closure is copied unchanged from f7cb, not edited or installed over P0.

## Consumer

Public signature: run_verified_hk_preselection(request), from v5_shadow.hk_preselection_verified. No caller-supplied callback, runner, verifier or strict_reader is accepted.

Request exact fields:

- schema_version = v5.hk_preselection_verified_request.v1
- target_date, signal_date, eligibility_source_date, research_cutoff
- data_kind = SOURCE_SNAPSHOT
- input_root: absolute root, no symlink in any ancestor
- files: relative path to raw file SHA256
- expected_source: exact role, run_id, artifact_sha256, manifest_sha256, receipt_sha256, artifact_relative

role is HK_CONNECT_D1_TOP100_0_2. The expected values are only comparison targets. Manifest identity is canonical JSON SHA256; receipt identity and file-map hashes are raw disk-byte SHA256. Missing, null, empty, malformed, mismatched or escaping identities are rejected.

The original eight-file closure is resolved from the actual latest pointers and manifests: pool latest plus artifact/manifest/receipt; master latest plus eligibility-day artifact/manifest/receipt. No template path or verification['artifact_path'] is invented. Every declared byte is checked before and after the worker. Parent and worker bind request, implementation, original capsule and production descriptor identities.

The real path is original _source_bytes/_HKLoader -> HK securities calendar -> unchanged shared _guard/_verify_lane -> original read_verified_hk_0_2_pool -> original master reader -> original _verify_pool -> original build_shared_hk_0_2_pool -> original validate_pool_artifact -> full identity and row comparisons -> postchecks. An internal checked_reader closes over the fixed request only; it is not a public authority callback.

ASSEMBLED returns the original artifact and VERIFIED_SOURCE_SNAPSHOT only after that path passes. CANNOT_CONFIRM returns no artifact and keeps SOURCE_SNAPSHOT. Structural failures raise the actual bounded ValueError reason. The result also preserves the actual original source_verification dictionary; the existing-pool daily receipt records it verbatim, rather than rebuilding a READY dictionary from requested identities. Every original CSV field that the projector preserves stays byte/text-equivalent; the projector's explicit derived/overridden fields are checked against its original transformations, including its boolean safety fields. It is incorrect to compare CSV text 'False' against the projector's boolean False as a supposed regression.

The consumer retains model_weights_reverified=false and all original SAFETY values, including natural_verified=false and formal_eligibility_verified=false. File/source verification is not proof of formal eligibility, point-in-time qualification, model execution, or an actionable trading signal. Fixture provenance remains explicit.

## Daily orchestration

produce_hk02_daily accepts the original named roots/dates/cutoff/files plus execution_mode. Modes are NATURAL, MANUAL_RECOVERY and RECORDED_INPUT_REPLAY. NATURAL is only a trigger label; it never turns on natural_verified.

Calendar and date admission happen in a fixed cold process before any producer execution. Input/output roots must be disjoint and the output must already contain the exact .v5-shadow-root marker. The fixed M07 ledger is used without source changes: claim before producer, no retry of RUNNING/unknown, max_attempts=1, success only after exact committed-reference readback. The seven-field ledger identity includes the canonical source-descriptor plus observed runtime/executable dependency manifest, captured before claim and rechecked on success and reuse. Ledger UUID, producer run_id, publication computation identity and their mappings remain separate.

An existing exact-day pool is first reverified by the new consumer. A damaged, wrong-day or invalid pool never becomes 'missing' and never triggers generation. NATURAL and MANUAL_RECOVERY require the full original frozen panel/model asset closure and bind the selected pool's actual panel/model provenance to it. Optional name pointers cannot be silently omitted. Only explicit RECORDED_INPUT_REPLAY may read an existing recorded pool without model/panel assets; its receipt says NOT_REVERIFIED_RECORDED_INPUT_ONLY, with model_weights_reverified=false.

A genuinely missing exact pool may call the original materialize_frozen_hk_0_2, using only copied declared source/master/assets and the unchanged frozen source loader. The source requires Python 3.13.12, scikit-learn 1.9.0 and joblib 1.5.3. The wrapper does not weaken those checks, replace the pinned model, or implement another ranking algorithm. Actual numpy/pandas/parquet-engine versions and executable identity are recorded separately. A failed generation preserves existing committed objects.

The original producer SHA pins, 155-feature model contract, four model keys, >=500 eligible signal-date symbols and original Top100 ordering remain unchanged. Actual panel/model loading is separate evidence in the producer receipt; the independent consumer always continues to report model_weights_reverified=false.

## Immutable publication

publish_verified_hk_preselection(request, *, bound_root, producer_receipt, execution_mode='MANUAL_RECOVERY') reads the real consumer before publication. A producer receipt alone grants no source admission.

It stores the real source closure, producer and strict-reader receipts, input/code/config/dependency manifests, original artifact, and an exact reference. Producer assets, when supplied as verified producer evidence, are retained as immutable input copies. It independently reads the saved bytes in another cold consumer before commitment.

The bound-root lock serializes cooperating writers. Each computation directory is created exclusively. The final committed.json is installed with the kernel's no-clobber link operation, never check-then-os.replace. A pre-existing final file, empty directory, conflicting input or incomplete same-computation object cannot be overwritten. Unknown outcomes require inspection, not automatic recomputation.

read_verified_hk_preselection_reference(bound_root, reference) verifies the exact committed object and all bytes; it never follows another day's latest pointer or silently replaces the reference. Same-input reuse invokes this reader again. An altered receipt, metadata formatting, source byte, implementation or dependency identity fails exact readback.

## Preserved limitations

- The original score_prob_active formula includes a z-score term and is not mathematically guaranteed to stay in [0,1]. The frozen V5 _verify_pool explicitly requires [0,1]. This delivery preserves that gate; it does not change scores, clip, widen thresholds or conceal a rejected original output.
- The original publisher uses the actual wall clock. Historical synthetic or recorded output published now must fail a historical cutoff. Tests do not backdate timestamps.
- Real frozen model/panel assets, authoritative M02/master/eligibility and acquisition/PIT evidence, production runtime, Mac installation, actual routes and two consecutive natural sessions are not established by synthetic tests.
- A model SHA printed in a historical pool manifest is not evidence that this consumer loaded the model. Qualified-source/PIT gaps do not become formal or natural approval.

# M16 original saved-result inventory (read only)

The active original API plist explicitly sets V4_MANAGER_RESEARCH_STATE_ROOT; only that configured ManagerResearchStore root was inventoried. No whole-disk search or credential access. The default V35 root was not used as an alternative result source. Counts: 7 commit files, 7 job files, 7 receipt files, 0 independent product files. All seven commits passed the unchanged original `_read_commit` from fixed M16 5bb1d635. Original product objects are embedded in commits; absence of separate product JSON is not a missing-result failure under original read_product semantics.

One selected latest saved result:
- date: 20261005
- input_identity: e61c8900ab53d0e894839d7b8fdafac0cbc4d3764a8a0ed86c77c8a2f33c79fa
- job_id: mr-20261005-e61c8900ab53d0e894839d7b8fdafac0
- attempt: 1
- generation: fb32d35a9cf14516a588d1ea84568170
- original commit canonical SHA: 270f4bfc116266234d3c70edfd8fc159d22258035f065d41cf8c8977f71017cb
- original commit file SHA256: 3718d8113576ae028f3517412251879f09a24c1683b6723d7c81abf24e3a68b3 (1,333,446 bytes)

Original read_job/read_product/read_receipt all return the corresponding commit members. Job/product/receipt status is PARTIAL_WITH_ROWS, with 10 original product rows and 10 source-receipt entries; provider identity is v4.hkex.official_titlesearch.v1. This is a complete readable committed envelope with partial business coverage, not READY business acceptance or verified underlying PDF material.

The separate job JSON differs from its committed member in can_retry/completed_at/status/updated_at, but attempt and generation match. The original reader resolves to the committed member, as tested. The standalone receipt equals its committed member. Original receipt schema has no attempt/generation fields; these are anchored through the committed job and were not invented. Original research-only flag is true; production_allowed/buy_gate_updated/orders_sent are all false.

The original Store writable constructor, service/provider constructors, ensure, tasks, models and collection were never called. A read-only shell of the original Store was used solely for original read methods, with its unchanged SafeRoot reader and a process audit hook rejecting writes/network/process launches. All 21 inspected original files retained SHA/size/mtime. No source body, private path or original artifact was copied/uploaded. Only field names/types and required identities/digests are included.

No migration, V5 binding or deployment occurred. The integration may use this pinned saved envelope after its own admission/import checks; until then its current unbound state remains WAITING. Underlying PDF/provider closure and broader business completeness remain unverified.

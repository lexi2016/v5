# M09 A close daily candidate implementation plan

Spec: R3 TASK_M09.md / DELIVERY_CONTRACT.md, superseded publication identity at lexi2016/v5@782bfc9ae91ff9cfe897afffc52aad43b7c1b78c. Immutable source F=f7cb731c384ee6890a87d16c19a5b5a621779477.

The user has approved the complete local candidate and expressly requested direct implementation. No repeated design/18-module approval is required. This work is isolated in the assembled before/after trees. Shared APIs, UI, scheduler, manifests and V4 are not edited.

## Tasks and interfaces

1. Freeze the exact producer, model, chain, product, store and SafeRoot/calendar dependencies in a new M09 namespace, with source SHA/blob mapping. `a_close_daily_sources.py` exposes `sources_identity`, `safe_root`, `market_states`, `build_from_admitted_panel`, `read_original_review`. RED tests first; immutable admitted-frame I/O adapter must call the untouched producer. Default real parquet admission uses the real pyarrow package. No global fake pyarrow or bare donor modules.
2. `a_close_daily.py` implements `initialize_a_close_root(root)`, `diagnose_a_close_input(source_root, manifest_path, expected_manifest_sha256, trade_date, slot)`, `run_a_close_daily(root, request)`, `read_a_close_daily(root, trade_date, generation_sha256=None)`, `rollback_a_close_daily(root, trade_date, target_generation_sha256, expected_generation_sha256, reason)`. Source files are bounded SafeRoot reads, fully hashed and rechecked; output root must be separately marked and disjoint. Real data requires an admitted immutable parquet/member snapshot and source timing/authority; explicitly synthetic JSON fixtures are admitted only for engineering execution.
3. Every call produces a trigger identity independent of its calculation identity. Each run owns an immutable original store, input snapshot and record; independent original read verifies the store. Per-date locks serialize same-day contenders; generation activation uses expected-head CAS. Failed/interrupted attempts are preserved independently of successful heads. Trigger receipts keep their cutoff, execution kind and actual times. Identical admitted computation may be reused across the two slots without losing receipts. No third slot is inferred.
4. `a_close_daily_api.py` exposes `read_a_close_preview`, `project_committed_review`, `merge_a_close_preview`. It pins one generation, checks date/run/digest semantics, retains exact native algorithm fields, shows missing/partial state and preserves HK. Shared-owner requests describe the exact route/UI/dispatcher insertion sites and actual before SHAs. GET is read-only.
5. Run the available complete unittest suite, independent adversarial review, original/candidate parity, source and patch verification. Retain full logs and all actual limitations. Package complete after, before, changes, forward/reverse patches, manifests, interface requests, Mac verification/rollback and publication evidence.

## Review focus

- Changing a pointer, source member, code byte or context after admission must fail without changing the last successful generation.
- Original store writes may fail after any of payload/receipt/manifest; such partial runs remain unserved and older runs remain byte-identical.
- Whole-panel validation must reject other-day rows, missing/duplicate members, string/nonfinite numbers, empty names/industries before the donor can filter them.
- Missing, unknown-time, or post-cutoff stage/video evidence remains visible; no M12 collection or semantic-consumption claim occurs.
- Read-only GET, rollback and concurrent same-day execution preserve date/run/digest identities and never alter HK or V4.

## Environment ruling

Current cloud runtime is Python 3.12.14, pandas 2.2.3, no pyarrow or pytest. User disallows environment/dependency changes. Use existing unittest and an explicitly SYNTHETIC in-memory dataset adapter for engineering execution; real parquet decode and declared-environment certification stay NOT_RUN/BLOCKED. Mac Python 3.14.6/pandas 3.0.5/pyarrow 25.0.1 require separate independent compatibility execution, not a relaxed pyproject. Tests that need real pyarrow must report an explicit skip, never PASS.

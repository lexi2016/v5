# M09 frozen donor chain audit

Audit scope: all twelve Python modules in `producer_static_internal_import_closure`, the calendar Python/JSON pair, existing V5 replay loader/manifest, original model/chain/store tests, and R2/R3 runtime addenda. Read-only audit performed against `original/source`; no original or shared candidate file changed.

Donor identity is `lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`. All twelve closure files independently matched both the SHA-256 and the Git blob SHA-1 in DEPENDENCY_MANIFEST.json. The subsequent V5 handoff publication identity supplied by the parent is `lexi2016/v5@782bfc9ae91ff9cfe897afffc52aad43b7c1b78c`, branch `v5/m09-handoff-20261011`; this is distinct from the immutable donor provenance.

## Implemented source boundary (supersedes provisional names below)

The approved implementation is `V5/src/v5_shadow/a_close_daily_sources.py`, the sixteen exact copies are under `V5/vendor/m09_a_close_daily/`, and the pinned new descriptor is `V5/contracts/m09_a_close_daily_source_manifest.json`. The public API names are `sources_identity`, `load_frozen_module`, `safe_root`, `market_states`, `build_from_admitted_panel`, and `read_original_review`. A single private namespace is retained per interpreter to avoid accumulating the donor lock module's at-fork registrations. Every load re-verifies all sixteen files and the manifest, and live loader source changes require restart. Per-invocation admitted-frame binding uses ContextVar; no global import hook, bare module, or sys.path mutation is introduced. The original lazy calendar receives a capability returning only freshly verified frozen JSON bytes. Synthetic `ops` and `domains` packages do not claim nonexistent initializer files.

Final source-specific verification: 18 unittest tests pass; actual RED and all intermediate/final logs are preserved. The full byte-original producer and independent original store reader were separately executed against the same engineering admitted frame and all review/publication/reader data compared exactly. `sources_full_parity.stdout.json` contains both complete products; `sources_dependency_report.json` contains all donor mappings/imports, executable and package identities, lock-file reference hashes and honest environment statuses. Real parquet decoding remains NOT_RUN and the original pytest suite is BLOCKED because neither pyarrow nor pytest is installed.

## Exact dependency set

The new capsule should byte-copy the following paths, preserving their package-relative names below a new `V5/vendor/m09_a_close_baseline/` directory and record the full donor repository path, commit, blob SHA-1, raw SHA-256, bytes, and new target path. The existing vendor and its manifest must remain unchanged.

- `ops/build_a_share_close_review.py`
- `domains/a_share_close_model.py`
- `domains/a_share_review.py`
- `domains/close_review_chain.py`
- `contracts/a_share_review.py`
- `infrastructure/a_share_review_store.py`
- `infrastructure/data_store.py`
- `infrastructure/interprocess_lock.py`
- `infrastructure/market_time.py`
- `infrastructure/owned_io.py`
- `infrastructure/owned_path.py`
- `infrastructure/trading_safety.py`

Copy the two present package initializers (`contracts/__init__.py`, `infrastructure/__init__.py`) exactly. `ops` and `domains` have no attached initializer and should be synthetic namespace packages; do not invent donor files/provenance. Copy `contracts/trading_calendar.py` and `contracts/market_calendar_2026.json` as a separately identified daily-admission dependency (not falsely part of the producer's static closure).

External dependencies are pandas in the model and eager `pyarrow.dataset` in the producer. All other imports are standard-library modules, including lazy `fcntl` inside `SafeRoot.kernel_lock`, and lazy `json` in store `_read`. The new loader must include the complete imported Python closure, not merely the three algorithm files. The calendar JSON is the only `__file__`-relative lazy read in the proposed expanded capsule. The pure model, product builder and chain do not read files or the wall clock. `market_time.shanghai_now` is present via `data_store` but is not called by this product chain.

## Recommended loading and callable boundary

Use an M09-specific loader that verifies a separately pinned new manifest and every source byte before execution. Compile original bytes unchanged with their copied `__file__`. Give each invocation a unique private namespace such as `v5_shadow._m09_donor_<token>` and a per-module private `__builtins__['__import__']` mapping for internal imports. Register only the private fully qualified module names in `sys.modules` (needed by dataclasses); never insert bare `domains`, `contracts`, `infrastructure`, or `ops`, never edit `sys.path`, and never install a global import hook. Clean up the invocation's private modules after its plain-JSON result has been obtained. Preserve imported package attributes and correct fromlist/top-package semantics. The import closure is known; fail closed for unknown internal targets.

The producer is not a pure function: it imports pyarrow eagerly, reads pointer+panel, calls all three original constructors, and writes the store. To preserve the untouched producer while using the already admitted in-memory DataFrame, bind **only this invocation's** `pyarrow.dataset` import to a narrow adapter. It must accept exactly the staged panel path, format='parquet', the original ordered eight columns, and the predicate `trade_date == T`; return a deep-copied admitted frame and its exact row count. Reject any unexpected method/query instead of silently filtering. The adapter is an explicit I/O boundary, not a claim that pyarrow decoded parquet in this environment. It must never appear as bare global `pyarrow` in `sys.modules` and must not interfere with pandas' normal optional-pyarrow import. This lets the original producer build the exact review, source evidence, source SHA, original store payload/receipt/manifest without rebuilding its business logic in M09.

Proposed helper:

```python
build_from_admitted_panel(
    run_root: Path,
    trade_date: str,
    *,
    panel_pointer: Path,
    admitted_frame: pandas.DataFrame,
    expected_panel_sha256: str,
    run_id: str,
    context: Mapping[str, Mapping | None],
) -> dict  # original {'review': ..., 'publication': ...}

read_review(run_root: Path, trade_date: str) -> dict | None
source_identity() -> dict
market_states(trade_date: str) -> dict[str, str]
```

The daily caller first validates/decodes the original bytes, makes immutable private snapshots, gates all context by source SHA/T/availability/cutoff, passes only frozen plain mappings, and computes its broader computation identity. The wrapper must independently bind the admitted frame to the expected staged raw bytes and check snapshots before/after the producer call. `run_root` must have already been authorized and verified as a fresh M09 run/attempt directory under the private V5 root. Do not expose `replace_previous_sha`; always import into a fresh run store, then create a new independent reader instance and require exact review equality plus receipt/manifest consistency before publication. Actual pyarrow decode, same-input original-vs-adapter producer parity, and Mac fs behavior remain separately qualified until run on suitable installed environments.

## Material semantic findings

1. `prepare_close_rows` selects T after `.astype(str)`, selects only .SZ/.SH/.BJ codes, converts pct_chg and amount with errors='coerce', drops missing ts_code/pct_chg/amount, and drops missing sector_name only for sector metrics. The caller must reject incomplete/invalid declared data before these silent drops. It must preserve input order, because sorting ties can affect selected roles.
2. Model `as_of` is always T at 15:30 +08:00. It does not prove source availability or strict 15:00 PIT. It must remain unchanged inside the frozen product, with actual source and trigger/execution time in the outer envelope.
3. Model probabilities remain stronger=0.12, inline=0.28, weaker=0.60; no calibration is performed. All trigger and invalidation strings, branch order, and role reasons are frozen.
4. `core_stocks` and model core watch pool are empty; the original producer puts anchor roles only in `observation_pool`. Roles are WATCH_ONLY. LLM is disabled, count 0, model promotion absent, learning FAIL and generalization PENDING remain unchanged.
5. Original `source_sha256` is canonical JSON SHA of T, panel raw SHA, and the constant model contract. It deliberately does not cover context or implementation bytes. M09's computation identity must cover those independently; do not redefine source_sha256 or require all SHA strings to be equal.
6. Producer's only optional context inputs are `video_acceptance`, `video_capture`, `stockdict_pointer`, `ocr_alignment_pointer`, and `video_gap_pointer`. It does not accept M07 stage rows; M07 source coverage belongs in the outer M09 envelope and the integration request. Context arguments are plain objects, not file pointers to be followed by the product.
7. `_video_state` validates acceptance T, and capture T only when same-day video is locked. Stockdict/OCR/gap date mismatch usually makes that node not materialized, rather than raising. None validates raw SHA, availability, capture time, cutoff, or actual source files. M09 admission must do these checks before the original call.
8. Original chain lets stockdict/OCR/gap own nodes become READY_WITH_REVIEW_BOUNDARY from their individual status/count even if predecessors are missing. Preserve this exact local-node semantics; the full chain remains partial.
9. Original chain tasks contain legacy display slots 15:00/15:55/16:05/20:30/20:40/20:50/21:05/21:08/21:10/21:15. Those are frozen product fields, not authorization for additional daily triggers. M09 triggers remain the independent configured 16:05 and 17:10 slots.
10. Producer never passes `ui_acceptance` to chain, so even when all video dependencies are ready, verify stays NOT_MATERIALIZED/UI_ACCEPTANCE_PENDING and chain stays PARTIAL_REVIEW. Do not mutate frozen product after API/UI inspection to pretend the computation consumed later acceptance.
11. Model always retains CANNOT_CONFIRM_TARGET_VIDEO_NOT_CONSUMED, target_video_evidence_count=0, video_augmented_review_complete=False. Chain metadata readiness does not change model semantic consumption.
12. Product always includes the three original cannot_confirm entries: target video not consumed, strict D0 15:00 panel cannot confirm, and formal generalization pending. Original quality gate and source_role=V3_5_NATIVE_CLOSE_MODEL are preserved.
13. Original `read_review(T)` validates payload schema/T/safety, canonical payload SHA, receipt exactness and manifest. It returns None only for genuinely unmaterialized date, rejects partially written evidence. A changed raw serialization that parses to identical JSON is canonically equal; M09 may additionally record raw file SHA as a distinct type.

## Root and mutation hazards

- Producer `_panel_path` accepts absolute paths and symlinks with only `is_file`. Its stat check is only `(size, mtime_ns)` around dataset materialization plus a final raw hash. It does not prove stable inode, reject replaced same-size/mtime content, or constrain roots. M09 must not pass the original external pointer directly. Use strictly verified private snapshots and detect original pointer/raw file mutation over the operation before commit.
- `AShareReviewStore` accepts any root and has no M09/V5 authority marker. Its SafeRoot prevents symlink traversal and pins root inode after first I/O but does not decide whether a legitimate path is a V4 root. Parent daily/storage boundary must enforce the exact configured private root, namespace and marker before creating anything.
- SafeRoot is POSIX-only and intentionally fails closed without O_NOFOLLOW. Its fd-relative parent/create/rename/fsync protects against symlink path races. It assumes a private local state root; ordinary `Path.exists/is_file` in store is advisory and actual reads/writes still use SafeRoot.
- Store publication is three file writes; it is not a whole-run transaction. `replace_review` replaces the only same-date payload and retains only summary supersession, not old payload bytes. Never use it for the two daily slots. New immutable attempt/run directories + independently verified complete generation + CAS pointer are required.
- Store import can recover a same-payload interruption before receipt/manifest, but a failed candidate directory should remain isolated from the current successful generation. M09 failure attempts and successful generations must be different records; failed later attempts do not change latest_success.
- Original kernel locks leave a persistent `.mutex` inode. They create/remove PID-token owner records and register an at-fork cleanup callback. Do not unlink the persistent mutex to "clean up" normal runs. The active lease registry is private per loaded capsule.

## Required parity comparison

Same admitted DataFrame, exact order, same T, same run_id, same staged panel raw SHA, and identical context should produce exact JSON equality of full review. There is no model wall-clock field to ignore. Compare all model fields; all market counts and amounts; board order/ranks/metrics/reasons; role membership/order/explanations; scenario keys/probabilities/triggers/invalidation; core/conditional/risk pools; review row collections, source_role, source evidence/source SHA, market regime/risk tone, quality gates/cannot_confirm; full chain task order/status/reasons/evidence; and all safety flags. Original writer results and independent reader payload should match exact canonical SHA for each side. Only paths external to payload, private import namespace, adapter evidence, and separately identified wrapper/trigger metadata are intended changes. Do not broadly normalize away differences or safety meanings.

## Environment qualification

Parent reports current cloud Python 3.12.14 and pandas 2.2.3; pyarrow and pytest are absent. These do not satisfy original V5 declarations Python>=3.14, pandas>=2.3,<3, pyarrow>=21,<25. Do not change declarations or install packages. unittest engineering fixtures can verify the adapter and original pure chain, but must be labeled as tests on the actual out-of-declaration environment. Attached Mac Python3.14.6/pandas3.0.5/pyarrow25.0.1 is a separate out-of-declaration dependency environment. Real historical panel decoding, genuine pyarrow-vs-adapter parity and Mac acceptance need their own actual execution evidence, not inferred PASS.

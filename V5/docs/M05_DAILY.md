# M05 daily A-share pool publication

This is a runnable standalone M05 tree, materialized without edits from the
fixed GitHub handoff source plus three new implementation files and two tests.
The original 40-file source descriptor and owner bytes are unchanged. Root
`V5/src/v5_shadow/a_preselection_daily.py` did not exist in the base commit.
The rejected R9 file remains unchanged under `handoffs/M05` as provenance.

## Public entry point

```python
from v5_shadow.a_preselection_daily import build_m05_daily

result = build_m05_daily(
    request,
    source_root=source_root,
    private_root=initialized_v5_output_root,
    code_root=code_root,
    v4_root=v4_root,
    write_gate_context={
        "control_dir": control_directory,
        "expected_permit_sha256": externally_bound_permit_byte_sha256,
        "expected_owner_id": caller_bound_owner,
        "expected_release_sha256": caller_bound_release_sha256,
        "expected_root": initialized_v5_output_root,
    },
)
```

The output root must already contain `.v5-shadow-root` with exactly
`v5.shadow-root.v1\n`. All paths must be absolute and free of symlinks. The
output must be disjoint in both directions from every input lane, source root,
actual code root, caller code root and V4 root. The caller must supply real
permit/gate bindings; production code never mints permits or changes gates.
The permit must include every successful date/pool key. Synthetic test permits
are created exclusively by the tests in temporary isolated directories.

`request` retains the original exact four-field assembler contract:
`target_date`, `signal_date`, `data_kind`, `lanes`. Supported data kinds remain
`SYNTHETIC` and `RECORDED_INPUT_REPLAY`. Lanes remain v192, fupan, stage7,
wechat, baimao and the single combined research lane. Hourly/preview priority,
source verification, ranking, scores, rows and calendars remain original.

## Process and store boundary

1. The original read-only assembler executes its own isolated worker and keeps
   its permanent guard. No writes are added to it.
2. A separate `-I -B` writer installs the original `_FrozenLoader` only after
   checking the unchanged descriptor and all frozen bytes. Host top-level
   `infrastructure` modules cannot supply a store or context.
3. `a_preselection_store_factory.build_strict_store` constructs the real
   `StoreGateContext` and `PreselectionPoolStore` from that same loader, with
   `require_write_gate_context=True`; private strict flag, class and context
   object identity are verified. All gates and all artifacts are preflighted
   before a write lock can create files.
4. Each `materialize(payload)` retains the original store locking API. There
   is no invented `materialize(lock_lease=...)` argument. Once every attempt
   finishes, all successful snapshots are collected under the same actual
   live root-lock lease after all pending reconciliation. Shared manifest
   bytes, canonical artifact/receipt digests and final batch identity agree.

The Python process boundary is not asserted to be an OS security sandbox.
The writer cannot prove natural data provenance or production authority beyond
the explicitly bound protocol identities. Those safety flags remain false.

## Results and failures

`READY`, `PARTIAL`, `DEFERRED`, and `REJECTED` describe publication outcomes.
Missing expected sources never materialize a pool or occupy a success key.
Rejected/missing lanes retain their full artifact and diagnostic fields.
Success receipts retain full artifacts, original rows/scores, upstream lineage
and artifact/manifest/receipt raw SHA-256 values. Assembly evidence is retained.
`VALID_EMPTY` is a real zero-row success when the existing artifact contract
accepts it. The existing V192 verified-empty mismatch is not repaired here.

Only the exact original ValueError message `conflicting preselection-pool
materialization` is aggregated. Healthy sibling publications finish and final
snapshots are captured, then `M05PublicationError` is raised with `.result`
and `.results`; a conflict is never reported as ordinary partial success.
Unknown store/gate/readback errors propagate as `M05WriterError`, preserving
`remote_type` and `remote_message`. Publication is per-pool, not a new atomic
multi-pool transaction: earlier successful writes remain if a later unknown
error occurs. Callers should reconcile/retry using the immutable store keys.

## Verification

From repository root, using existing dependencies only:

```sh
PYTHONPATH=V5/src:V5/tests python -m unittest discover -s V5/tests -v
```

Focused M05 suite:

```sh
PYTHONPATH=V5/src:V5/tests python -m unittest test_m05_daily_boundary test_m05_frozen_factory -v
```

The original fixture helpers are imported unchanged. The six-lane positive
control uses original V192 and hourly fixture publishers; it needs existing
pandas/numpy/pyarrow. Other M05 controls exercise real assembler and strict
store behavior, including 250 rows, gate failures with byte-for-byte no-write
checks, root boundaries, retry, narrow conflict aggregation, all final reads
sharing one live lease, poisoned host-module isolation and explicit valid-empty
contract handling. The valid-empty test uses the documented contract seam;
it does not claim the default V192 verified-empty path is supported.

M07 integration status is always `WAIT_INTEGRATION`. Production binding,
natural input evidence, Mac acceptance and preview/consumer wiring are separate
checks. Nothing in this delivery changes V4, a trading gate or any credentials.

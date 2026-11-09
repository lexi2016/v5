# M07 recorded-source handoff and repository closure binding

This entry validates an already recorded four-root input descriptor. It does not
collect quotes, calculate new stock-selection rules, activate live execution,
publish a production result or send a message. REGISTRY remains empty.

## 2026-11-09 repair and replacement relationship

At baseline fc9ea68a2432dcfb279745d65819d3d853f5321a, verify_worker.py pointed to
public_source_delivery/opening_owner_code_restore_20261107/m07 and required the
historical SOURCE_MANIFEST.json with SHA-256
46b9d71a8cd1f43afe41f472d320d0245f3cf9ff0e5909dc2ea020a657ac8807.
Those paths were absent from this repository checkout. The historical manifest
has not been reconstructed or declared recovered.

The repository already contains the same original entry and complete original
owner closure. This repair explicitly uses:

- V5/contracts/m07_runtime.json, pinned SHA-256
  1e3302422d31a595eab83552efe3ba201f56f288f7072288f3e0067978e067c4.
- All 113 files in that manifest, checked for regular-file type, bounded size,
  exact bytes and SHA-256; symbolic links and invalid paths are refused.
- V5/source_owners/m07/V5/src/v5_shadow/a_stage_daily.py, unchanged SHA-256
  01c791dee6547e5e1a54ef3c412ac3102dfcafdf7e78be34c702b053f6fb5791.
- The unchanged 97-file original owner closure, independently checked by its
  original loader.

The worker compiles the verified v5_shadow byte snapshots rather than reopening
them for import. It rechecks the repository closure after admission. It copies
the registered inputs to temporary storage and calls only original _admit.
The original natural-execution refusal and source admission rules are unchanged.

This is a new repository binding recorded in REPLACEMENT_BINDING.json.
It does not replace the missing historical manifest with a file bearing its
name, fabricate a source identity or recover any cloud job/lock/receipt.

## Input, output and existing caller

Existing call path: adapter.dispatch(job_id, environment_id) finds an exact
private Binding; verify_registered_recording(binding) enters the supplied
original gate and lock, then launches verify_worker.py in a fresh interpreter.

The Binding must identify the job/environment, named source, original scope
and its identity, independent source/owner review references, four pinned roots
(pool, live, research, morning), completed RawStore references, original lock
and resource gate. A hash-shaped review reference alone is not source authority.

Output remains SOURCE_RECORDING_VERIFIED_ONLY, with production_allowed,
natural_verified, business_verified and collector_executed all false.
source_authority remains UNKNOWN. Known synthetic inputs cannot be relabelled
as real. RawStore, M05 frozen pools, current quotes and an actual live owner
must still come from the original system or an independently admitted provider.

## Verification

Run from this directory in a complete repository checkout:

    python3 -B -m unittest -v test_public test_repository_closure
    python3 -O -B -m unittest -v test_public test_repository_closure

The repository tests create explicitly synthetic 09:25 and 09:30/09:35 inputs
in temporary directories using the original fixture. They exercise the real
adapter subprocess and original _admit, verify both stages and unchanged input
bytes, and separately run the worker with explicit -O because the adapter's
fixed -I/-B command does not inherit the parent optimization flag.
Manifest/dependency tampering, symlinks, empty registry, source/scope mismatch,
synthetic relabelling and the unchanged natural-execution refusal are covered.

The source verifier also rejects fractions beyond microseconds and fractional
UTC offsets before original owner loading and input snapshots. The original
owner's parser can otherwise discard precision before its cutoff comparison.
The separate M07 replay correction in parent commit 84e7843 is retained; it
does not protect this source-verification entry by itself. The additional
regression exercises actual adapter calls and explicit optimized child calls
for cutoff, captured_at and acquired_at in both stages. Eight cutoff/acquired-at
cases were accepted before this boundary guard; four captured-at variants
were already rejected by the original window rule and now receive the earlier
precision error. Original formulas, owner bytes and original window checks
remain unchanged.

These tests establish repository source wiring only. Real data collection,
deployment, current-day source admission and natural business acceptance are
not established. The Python write guard is not an OS sandbox certification.

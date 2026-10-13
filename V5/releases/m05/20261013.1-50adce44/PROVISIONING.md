# M05 code release and bounded local provisioning

This defines a **new V5 component control identity**, not an existing V4 owner,
an external signature, a production admission, or an already-issued permit.
This delivery creates no permit, gate, data product, or Mac-side file.

## Fixed identity

- Component owner: `v5.m05.a_preselection_daily`.
- Code release version: `20261013.1-50adce44`.
- Source repository/commit: `lexi2016/v5@50adce44ea047c8ee9435a5e703a2125264243c4`.
- Manifest: `V5/releases/m05/20261013.1-50adce44/release.json`.
- Release SHA256: `f77c0ead2053a15cbd089c02cce2cf0c7bea59ac2fb0e86ad2cc032c9d87adbb`.

The release SHA is the SHA256 of the **entire exact canonical UTF-8 JSON
manifest**, without a trailing newline: sorted object keys, separators `,`
and `:`, `ensure_ascii=False`, `allow_nan=False`. It is not the 40-character
Git commit, the old capsule digest, a panel hash, or a permit hash. The manifest
does not contain its own digest, its delivery commit, or this document, so
there is no circular identity. Fetch this document/manifest at the fixed
delivery commit and independently bind the expected release SHA before use.

`runtime_files` covers 50 source/runtime members: all 9 V5 Python modules,
the unchanged source descriptor, and its 40 frozen vendor members (including
the market calendar). `verification_files` separately identifies 5 tests;
both lists are part of the release digest. The closure is scoped to the M05
public build/assembly/strict-store entrypoints and six A-share lanes. It does
not claim every dormant HK/day-product API in the vendor modules is runnable.
Python/stdlib, POSIX locking, timezone data, numpy, pandas and pyarrow are existing external
runtime requirements; their bytes/versions are not pinned by this code-only
manifest. Record the actual existing interpreter/dependencies locally. Python >=3.11 is
a source-level minimum (StrEnum), not a compatibility claim for every newer
version. The unchanged runtime does not consume this release manifest: its
full-file verification is the independent operator's responsibility. Gate
comparison of the supplied release SHA alone is not code attestation.

No executable member or source descriptor is changed by this release
definition. The verified-empty adapter in source commit 50ad supersedes the
older `M05_DAILY.md` statement that V192 empty was unsupported; it does not
change nonempty behavior or admit missing/unverified inputs.

## Read-only verification before provisioning

From the fixed candidate repository root, with the existing Python, verify
the independently supplied release SHA, then every listed member's raw SHA
and byte length. Reject absolute/parent-traversing paths, symlinks, duplicate
paths, missing members, extra executable members in `V5/src/v5_shadow` or
`V5/vendor/a_preselection_baseline`, and a changed descriptor. Use an isolated
M05 candidate, not a merged P0 tree with unrelated modules on its import path.
The manifest file itself must equal the canonical bytes used for its digest.
An existing interpreter/dependency mismatch is a separate runtime decision;
do not install packages as part of this procedure.

The original `_source_bytes()` must still verify its unchanged descriptor and
all 40 vendor members before `_FrozenLoader` is installed. Use a fresh `-I -B`
process, add only the verified candidate's `V5/src`, then load the original
scope module through that loader. The following fragment **only computes and
validates text/digests**; it neither issues a permit nor changes a gate:

```python
import importlib, sys
from v5_shadow.a_preselection import _FrozenLoader, _source_bytes
sys.meta_path.insert(0, _FrozenLoader(_source_bytes()))
gate = importlib.import_module('infrastructure.scope_gate')
owner_id = gate._exact_text('v5.m05.a_preselection_daily', 'owner id')
business_key = gate._exact_text(
    'v5.m05.a_preselection_daily:20261012:a_d1_premarket_pool', 'business key')
keys = [dict(business_key=business_key, trade_date='20261012',
             pool_id='a_d1_premarket_pool')]
keyset_sha256 = gate._business_key_set_sha256(keys)
assert keyset_sha256 == 'f43ad7e2bb6c12a04c076f4cbd9cdf5deaf4d8b40a9af7ff0dd719da0624187b'
```

There is no original business-key generator. This is an explicitly new audit
label checked by the original `_exact_text`; the original function computes
the key-set hash after sorting by `(business_key, trade_date, pool_id)`.
`PreselectionPoolStore._assert_write_allowed` and `scope_gate.assert_write_allowed`
do **not** accept a business_key argument. Their runtime key is
`(trade_date, pool_id)`. The unchanged M05 writer additionally requires each
successful artifact's exact tuple in the permit scope before any pool write.
Thus this one-item permit matches the actual writer's
`('20261012', 'a_d1_premarket_pool')` request; the label adds no second match
rule and no authority over another date or pool.

## Independent, one-time operator provisioning

Authorization reference: the user's existing V5 isolated-development/local-test
task, with V4 retained, no trading, and no security/credential expansion.
The current delivery is definition-only; this document is an operator plan,
not self-authorization to execute it. Provisioning starts only when the
authorized operator receives the separately recorded, bounded execution
decision under that existing task. This does not imply a new external signer
or another user's approval. It is a local application-control decision, not
an external approval or historic admission.
Use the new decision id `V5_M05_ISOLATED_REPLAY_20261013_20261012` and retain
that scope/authorization reference in a separate local operator decision
record. It must say **newly provisioned for recorded historical replay**.

1. Independently verify this code release, the intended one-item keys above,
   and the actual local roots. Source root is the already-verified immutable
   V192 source; target is a new, separately marked V5 private product root.
   `expected_root` is the target. Source/target/control/code/V4 bindings stay
   local; no absolute path or real input metadata belongs in this repository.
   The target must satisfy the existing M05 no-symlink/disjoint-root checks
   and `.v5-shadow-root` marker. No source-root gate or V4 store is opened.
2. Bind `target_release_sha256` to the release SHA above. The same SHA may be
   used for `source_release_sha256` **only after** confirming locally that
   the V192 source was produced with the same verified 50ad code release's
   frozen source members. This is code identity, not a claim that the raw
   store's original `v3_shared_data` owner became the M05 product owner.
   Keep all original source receipt/owner/provenance fields unchanged. If
   producer code identity is different or unverified, stop and bind its
   actual release definition; do not substitute an arbitrary 64-hex value.
3. In the independent operator step, construct a NEW permit with exactly:
   `schema_version='v4.preselection.exact_scope.v1'`, the new `decision_id`,
   `owner_id`, `source_release_sha256`, `target_release_sha256`, actual
   `source_root`, actual `target_root`, the one-item `keys`, and the original
   computed `business_key_set_sha256`. Validate with original
   `gate._validate_permit(..., expected_owner_id=owner_id,
   expected_release_sha256=release_sha256, expected_root=target_root,
   pool_ids=original_store.POOL_ORDER)` before issuing anything.
4. Canonically serialize the validated planned permit with the original
   `gate.canonical_bytes`. Freeze its **raw-byte SHA256** in the independent
   local decision/context record before writing `control_dir/permit.json`.
   Create this new file exclusively; do not replace an existing permit.
   Re-read and compare exact planned bytes and the previously fixed hash.
   An unexpected existing file or mismatch stops the operation. Do not read
   an arbitrary existing permit and silently adopt its own hash as trust.
5. The caller context has exactly `control_dir`, `expected_permit_sha256`,
   `expected_owner_id`, `expected_release_sha256`, `expected_root`. The
   permit SHA is the independent planned-byte hash; owner/release/root are
   the separately fixed target-side identities above. Keep this context and
   the decision record separate from the permit; no automatic discovery or
   fallback to the former source owner is permitted.
6. In a NEW fresh process, construct the existing
   `build_strict_store(target_root, context)`. Confirm this new control root
   has no gate. Call only the original
   `runtime.store.set_write_gate(expected_revision=0, state='OPEN')`.
   It revalidates permit/context, takes original locks, and atomically writes
   `v4.preselection.gate.v1` with revision 1 and the bound permit SHA. Do not
   handwrite gate.json or bypass a CAS conflict. This is an application gate,
   not an OS/network/account permission or trading gate.
7. Run only the existing M05 build with `RECORDED_INPUT_REPLAY`, target
   20261012, signal 20261009, and the single genuinely bound V192 lane, then
   independently cold-read its original pool snapshot. Five unbound lanes
   remain unbound; one-lane READY is not six-pool completion. The P0 M01
   same-signal/official-selector checks remain unchanged and blocked unless
   their original evidence actually exists. This release grants no PIT,
   natural-completion, M07, preview-publication, or production status.
8. Attempt FENCED cleanup through the original setter in a finally path after
   the bounded attempt, including build/cold-read failure or interruption,
   using the independently expected revision (normally 1 -> 2). Retain all
   evidence. After a hard interruption, inspect this exact gate on resumption
   before doing anything else. A failed cleanup, unexpected revision, or
   uncertain gate state must be reported as unresolved; do not silently leave
   OPEN or bypass CAS. Preserve pending recovery evidence, and do not run
   hidden repair/retry after fencing. Any necessary recovery must be an
   explicitly bounded operator decision using original checks and the same
   exact scope. Never broaden keys or repurpose the control root.

Stop on a changed release/file/root, missing independent decision/context,
existing unrelated permit/gate, bad source identity, or any request for new
system permission, credential, external approval, or real-data upload.
No part of this document instructs production code to mint/open gates.

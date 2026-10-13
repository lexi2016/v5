# M06 producer/reader verification copy

Parent: `dfab56ed5b73f61404fff836bcc19e1604a902d9` on
`lexi2016/v5:dev/v5-main-integration-20261012`.

## Scope and evidence

Only `frontend/src/components/HkPreselectionPool.vue` changes product behavior.
The panel's reader `model_weights_reverified=false` now explicitly means no
model re-verification during this read. Producer text uses the existing
`committed_reference.producer_reference.production_method`:

- `FROZEN_MODEL_PRODUCER`: producer verified model weights.
- `EXISTING_VERIFIED_POOL`: producer reused a verified pool without re-verifying weights.
- Missing/unknown method: producer verification cannot be confirmed.

This is not a new API field or a promotion of the reader's false flag. The fixed
original `hk_preselection_publication.py::_producer` already requires
producer receipt `model_weights_reverified=true` for `FROZEN_MODEL_PRODUCER` and
false for `EXISTING_VERIFIED_POOL`. The cold reader validates the receipt and
reconstructs the committed reference; the frontend does not verify a model itself.

Mac feedback at the parent commit records real generation separately in
`handoffs/P0/feedback/mac-4e05bd-m06-generation-20261013/`. That result's method is
`FROZEN_MODEL_PRODUCER`; its reader flag remains false. No real generation was
run for this UI correction. All research/trading/PIT/formal/natural boundaries,
all rows, API contracts and other modules are unchanged.

## Verification actually run in cloud

- Before the component change: `node --test tests/hkPreselectionModelCopy.node.mjs`
  failed both new source guards, specifically missing reader-scoped copy and
  method-dependent producer display.
- After the change, from `frontend`:
  `node --test tests/hkPreselectionModelCopy.node.mjs tests/hkPreselectionPool.node.mjs`
  passed 17/17: 2 new source guards and 15 existing M06 GET/client checks.
- `npm test -- src/components/HkPreselectionPool.model-copy.spec.ts` could not
  start: exit 127, `sh: 1: vitest: not found`. Its 5 rendered-view cases are
  **NOT_RUN in cloud**, not passes. They use explicitly synthetic view state,
  not a model computation. No dependency installation was attempted.
- Full frontend build/typecheck and browser acceptance are **NOT_RUN in cloud**.
  The existing Mac frontend environment must perform the focused checks below.

## Mac application (no recomputation)

1. Fetch the development branch normally and use the exact fixed commit supplied
   with this handoff. Preserve local changes; do not reset an active worktree.
   For an existing preview source tree, apply only this component and the two
   new tests from that fixed commit. No backend change is required by this patch.
2. In the existing frontend environment, without installing dependencies:

   ```sh
   node --test tests/hkPreselectionModelCopy.node.mjs
   npm test -- src/components/HkPreselectionPool.model-copy.spec.ts
   npm run build
   ```

3. Reuse the already verified real M06 generation. Switch only the M06
   `bound_root` / `committed_reference` through the existing preview procedure;
   the committed reference is in the parent feedback directory above. Do not
   rerun the owner, provider, model, scheduler, or old integration suites.
4. Confirm the one read-only GET displays its unchanged 100 rows and source
   identities, producer `FROZEN_MODEL_PRODUCER` / weights verified, and reader
   `model_weights_reverified=false` / this read does not reverify. Keep
   `fixture_only=false`, research-only and formal/natural verification boundaries
   visible. Refresh/loading or a failed/missing read must clear the old producer
   claim together with its rows. Preserve every other module binding.

Component SHA256: `8e964d2dd52fd66b6003870812b9f7cc42cf6970cc7cf9649dae113eb2cb09b8`.
New node guard SHA256: `fed6e3c3e35bdad3768ee93193b375044b2fa72b2a3b1f262bc47ff66f1b63ca`.
New Vue spec SHA256: `f99ebd6c3a6e9bbbb75e4bc4d8b7b8015820623e39d6f2395dc370fe9ec3207e`.

The three code/test files above have closure SHA256
`8d5757dba7ce5b1fbdcfd37cfbe0731cff561413467ab805e43d431a014f54a8`:
SHA256 of a path-sorted JSON list of `{path, sha256}`, with sorted object keys,
compact separators, UTF-8 and one final newline. The handoff is excluded to
avoid a self-referential hash.

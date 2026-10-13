# Mac 018827 feedback and bounded repair

Feedback applies to candidate `018827908e6f5feae87d27dbc9e8d6f2a0935a8e`, not to an untested later revision. The supplied redacted files are retained byte-for-byte:

- `result.json`: SHA256 `3f34a1ac1f1055dbdbb78abf07abbca8615088b91e04c32e522a009af7db76cf`
- `typecheck.stdout.txt`: SHA256 `f40aa5159a91d2f80b94a924398713cda1533c45e854a0fa70dbc1c9c0f4a112`

## Confirmed prior result

Mac verified 33 candidate blobs and 17 source preimages, and check-only/application exited 0. Existing dependency copying was corrected before tools ran, without product edits or package installation. Build exited 0. Typecheck exited 2 with exactly these diagnostics:

- `src/api/m14SavedRebound.ts(99,136): error TS2345: Argument of type '{}' is not assignable to parameter of type '"strict" | "near" | "pending" | "excluded" | "screen_unresolved"'.`
- `src/api/m14SavedRebound.ts(103,35): error TS2322: Type '{}' is not assignable to type '"strict" | "near" | "pending" | "excluded" | "screen_unresolved" | undefined'.`

Full Vue results were 372 passed, 24 failed, 3 skipped, not a pass. The delivered `SavedManagerResultView.spec.ts:10` still expected the obsolete disabled “阶段选股 · 未接入” entry, although the current view exposes the actual M07 saved-stage component. That assertion is repaired without removing the page's CANNOT_CONFIRM, absent-table or manager-request-count checks.

The other observed failures are not treated as new M14 product regressions: Mac follow-up confirms the four exporter scripts exist, but the runner did not set `PYTHON` and its PATH has no `python`; an existing `$PY_FUTU` or `$PY_M14` can be used when those tests are needed. Historical `V5_REAL_CURRENT_RECOVERY_RESPONSE` and related private/recorded fixtures were not bound. Do not fabricate or restore real fixtures merely to force a full-suite pass. The complete older Vue logs remain on Mac with their hashes in the original result; this repair does not pretend those omitted logs were re-executed or fully diagnosed.

Real M14 configuration/HTTP/pagination/DOM, native visual verification, deployment and owner execution were NOT_RUN. M02 generation and all 2671 protected files were reported unchanged. No live service change is part of this repair.

## Changes in this revision

Only two candidate after-files change:

1. `frontend/src/api/m14SavedRebound.ts`: retain explicit object, array, allowed-key and group validation without narrowing the typed query through `Record<string, unknown>`. A local typed group is reused for membership checking and request construction; no type assertion or validation bypass is introduced.
2. `frontend/src/views/SavedManagerResultView.spec.ts`: check the real enabled M07 navigation, click it, wait for the actual saved-stage disclosure to open and receive focus, and verify its region and unchanged manager read count. Existing error-state assertions remain.

The full candidate manifest/patch is refreshed from the original P0 base; the `revisions/from_018827/` package contains the exact two old after-images as preimages for an already-applied 018827 isolated checkout. Source provenance and all other product files are unchanged.

## Verification and minimal Mac recheck

Cloud Node suite after the reader fix: 182 passed, 0 failed. Null/array/nonobject requests additionally reject before transport. Both full-package and two-file delta application/hash checks pass; the saved API still launches with a synthetic persisted trio. Backend code is byte-unchanged, so previous backend evidence remains identified as the prior run rather than a new backend test run.

Cloud typecheck and targeted Vue commands were attempted; `vue-tsc` and `vitest` are unavailable. Therefore the fixed revision's typecheck and Vue DOM status remain NOT_RUN pending Mac. Prior build exit 0 is evidence for 018827 only.

On the already-applied isolated 018827 checkout, first run the delta helper with `--check-only`, then apply its two files. Using existing tools, run:

1. `$NODE node_modules/vue-tsc/bin/vue-tsc.js --noEmit`
2. `PYTHON="$PY_M14" "$NODE" node_modules/vitest/vitest.mjs run src/components/M14SavedRebound.spec.ts src/views/SavedManagerResultView.m14.spec.ts src/views/SavedManagerResultView.spec.ts src/views/SavedManagerResultView.navigation.spec.ts`

Use `$PY_FUTU` instead if that is the coordinator's appropriate existing interpreter; no install is requested. Do not repeat unrelated historical fixture tests. Keep the active M02 service and protected files unchanged. This revision is a scoped return for those targeted checks, not deployment permission or evidence of a real M14 page.

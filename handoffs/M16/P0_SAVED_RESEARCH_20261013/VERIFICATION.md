# Sanitized verification summary

Date: 2026-10-13. Tested code base: `66b3d7b87789b432d12a9365b6add035017a8326`; publication parent: `a529a2e37b3d091bda0cdb66ee994080ad365f8a` (intervening commits only add feedback) on `lexi2016/v5`, `dev/v5-main-integration-20261012`. No Mac actions were performed by this development task.

## Executed

- New M16 backend suite: **27 passed**. Fixtures are explicitly synthetic commits created by the unchanged original `ManagerResearchStore`; no real provider/service/ensure is invoked.
- Combined focused Python command: **66 passed, exit 0**. Includes M16 27, M11 14, M12 11 and shared registry/module API 14.
- Full existing P0 Node frontend command after the M16 addition: **142 passed, 0 failed**. M16 contributes 18 tests, including its actual proxy and shared-view mount.
- Backend-to-frontend contract check: actual new-reader synthetic WAITING, saved original-business CANNOT_CONFIRM, and rejected-file CANNOT_CONFIRM payloads parsed by the new frontend client.
- Exactly 20 original owner files: byte count, SHA-256 and Git blob SHA-1 match their fixed original descriptor. The loader/factory/jobs copies are unchanged from `5bb1d635abe03cec61d0e52bf1150f2c70b5fe6a`.
- Shared module API, registry, view and Vite proxy were compared with the fresh integration HEAD. Only M16 additions are included; existing M11/M12 sections remain intact.

## Red/green and coverage

The initial 18 new backend tests failed on the missing adapter before implementation. The original-writer EVENT_REFRESH catalyst-receipt test then failed on the wrong receipt schema and passed after the conditional original-schema correction. Public provider provenance, credential-bearing URL redaction and case-normalized authority-claim regressions were observed failing before their narrow fixes. A malformed child product reproduced an HTTP disconnect before adding explicit child-record shape checks. The proxy test failed because the M16 proxy was absent before its one-line addition.

Coverage includes exact original `_read_commit` consumption of the pinned bounded bytes; verifier-output equality; constructor/provider/service call absence; no GET writes; raw and canonical digests kept distinct; date/input/job/attempt/generation; legacy missing commits; original receipt without invented fields and explicit receipt conflicts; 10-row PARTIAL_WITH_ROWS; ordinary and EVENT_REFRESH schemas; safety-tree rejection; private-root marker; symlink/size boundaries; child timeout/runtime-pin/shape failures; same-module concurrency rejection; unsupported queries/write verbs; source and credential redaction; stale/late frontend response clearing; and truthful registry capability.

The early M12 regression attempt could not import its pre-existing fixture because that one file was absent from the cloud snapshot. After restoring the unchanged GitHub-pinned fixture locally, all 11 M12 tests passed. The fixture is not part of this change.

## Not established

- Vue component test, typecheck and build commands were attempted but could not execute their tools: `vitest`, `vue-tsc`, and `vite` are absent here, each exit 127. Existing Mac dependencies must run them. No dependency was installed.
- Actual private result migration, live P0 binding, preview deployment and real 10-row UI validation: pending the authorized Mac handoff.
- Full donor repository collection, real provider/network/PDF runs, persistent execution lifecycle and natural-business completion: not run or claimed.
- Source PDF bytes and the withheld original PDF dependency manifest are unverified. No replacement manifest was created.

No raw diagnostics, private root, original saved research content, PDF or local binding is included in this handoff.

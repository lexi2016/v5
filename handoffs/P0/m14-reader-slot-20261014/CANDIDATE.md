# M14 reader-slot candidate, exact live preimage

Candidate only. The existing freeze README and before/module_api.py are preserved. No repository top-level runtime, running Mac file, service, data or preview was changed by this delivery.

## Fixed input and complete output

- Preimage commit: 8318c3fe0a758fdf832ed790a8da82b76ce814b3.
- Preimage: before/module_api.py, 61,692 bytes, SHA256 94c1c26a36a7d1881602b7780077c056615344bf5ab21a54bf2b749904af1d21, Git blob 2151b643ac0dc6df9363a626ed9b2f045d46b240.
- Complete after: after/module_api.py, 63,870 bytes, SHA256 6435783655a1cca6f86e2a2f262510d87a7abd335b495f1be172cd7b8b12615c, Git blob 41865d39eea11d622d083ffbda410fa6a2589aa9.
- Runtime target: V5/src/v5_shadow/module_api.py. Exact identities: PREIMAGE_AND_AFTER.json.

## Narrow change

Only the source_bundle M14 rebound-saved route is dispatched to a new reply_m14 method after successful acquisition of its existing slot. The original cold reader, response projection, digest and serialization execute while holding that single slot. The body is capped at the existing M14 256 KiB limit. The record is dropped and the slot released exactly once in finally before headers/body are sent. Read/validation/serialization errors are prepared as the same closed error JSON before release. Disconnects therefore cannot retain or double-release the heavy-reader slot.

All original AST remains identical after removing this one new method and one dispatch (see evidence/narrow-diff-check.json). Other routes retain their original processing and slot lifecycle; no wildcard route, request identity, original binding, producer, source card or publication code was changed.

Memory scope: one M14 heavy reader remains permitted at a time. The original global eight HTTP connections remain unchanged. At transmission, each completed M14 handler retains at most one 256 KiB serialized body and no record; at most 2 MiB of completed M14 body buffers can coexist across these eight slots, excluding the original single-reader working set, encoding temporaries and socket/header overhead. This is not a claim of a 2 MiB process-RSS limit. The original 128 KiB loaded-entry budget remains unchanged.

## Verification

- Exact 94c1 preimage: 8 targeted tests, 4 expected RED failures, 4 passing controls, 4.251s.
- Candidate: same 8 tests, all PASS, 4.257s. The completed first page and next page both return 200 under an explicit post-write barrier; genuine concurrent heavy reads still return 503/MODULE_BUSY. Error-response boundary, serialization failure, oversize refusal, disconnect recovery, record release, and non-M14 original lifecycle are checked.
- Original M14 saved/boundary tests plus generic module API tests: 23/23 PASS, 13.440s, including 690-row pagination, cursor/SHA guards, 256/128 KiB bounds and unrelated generic API behavior.
- Exact one-file forward/reverse patch roundtrip: PASS.
- Independent focused review: no blocker; no double release, original global eight-slot cleanup remains unchanged.

All fixture data is explicitly synthetic and only loopback HTTP is used. No live artifact/provider/credentials/trade was used. These tests ran with the existing cloud Python 3.12.14 and dependencies; the consuming Mac should use its existing compatible 3.14 environment. No full-P0-suite PASS is claimed; a previous broad run's unrelated gaps remain separately recorded, and it was not repeated for this narrow change.

## Isolated application and rollback

1. Make a new isolated copy of the already-authorized current P0 runtime. Do not treat this single-file preimage commit as the whole active release. Read the current target SHA; require the exact preimage above. Stop on any mismatch.
2. From the isolated root: git apply --check "$CANDIDATE/runtime.patch", then git apply "$CANDIDATE/runtime.patch". Verify the exact after SHA. Do not also copy the full after file over later changes.
3. Run the commands in TEST_COMMANDS.sh with CANDIDATE and STAGE pointing only to the candidate and isolated copy. Required test fixture files are supplied under test_support; use byte-verified equivalents already present in STAGE/V5/tests or place these copies there only in the isolated tree. Their hashes are in DELIVERY_MANIFEST.json.
4. The Mac independently verifies the actual saved M14 pagination and unaffected routes before deciding whether to publish. This candidate does not authorize a service restart or perform publication itself.
5. Rollback is only the code patch, never the data. Require target after SHA exactly; git apply --check "$CANDIDATE/reverse.patch" then apply, and verify the exact preimage SHA. If subsequent code differs, stop rather than clobber it. Restoring a file alone does not reload a running Python process; service lifecycle remains the Mac coordinator's separate decision.

The source request, saved record trios, active generation, M03 published card, V4 and paused module boundaries remain untouched.

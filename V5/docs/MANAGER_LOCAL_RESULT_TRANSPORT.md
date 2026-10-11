# Bounded local manager result transport

Scope: local candidate on 884548. No owner/consumer/algorithm/PIT changes, no API publication changes, no archive-reader changes, no global budget changes. This is not real-input acceptance or deployment.

## Contract

The existing manager request remains canonical JSON <=16 MiB. Only the manager subprocess result changes from a captured monolithic JSON stdout to a versioned framed stream. Python callers still receive the complete original result, plus `local_result_transport` as parent-generated transport evidence.

Fixed local budgets: control frame 64 KiB, data frame 1 MiB, at most 64 data frames, complete response 64 MiB, each saved file 64 MiB, stderr 64 KiB, total worker time 120 seconds. The original owner storage ceiling remains 320 MiB. API, archive reader and shared digests retain their existing 16 MiB boundaries. A locally readable response is not implicitly publishable through the API.

Wire: `V5MR1\n`, followed by length-prefixed JSON controls. Start binds request SHA, exact authorized output root, target date and saved identity. Each data control binds consecutive index, byte length and chunk SHA256, followed by exactly those bytes. End binds count, total length and complete response SHA. Missing, extra, oversized, out-of-order or mismatched content is rejected. The parent reads stdout/stderr in bounded increments with a deadline, rather than capturing unbounded output and checking later. The complete result is parsed only after all framing and digest checks.

The child serializes all result fields after `_assemble`, including read-time research observations; nothing is truncated, filtered, deduplicated or declared valid by the transport. The original `_read_plan`, `verified_plan_attempt`, SafeRoot, input checks and source identity checks continue to run. The new transport source is included in implementation identity.

## Three identities

- `saved.plan_sha256`: original saved product semantic SHA, computed on canonical saved JSON excluding its top-level `sha256` field only.
- `saved.raw_sha256` and `saved.bytes`: exact immutable saved file bytes, including its seal and original serialization.
- `response_sha256` and `response_bytes`: complete canonical worker response, including read-time fields, BEFORE the parent attaches `local_result_transport`. This response digest is never confused with the saved plan digest.

A consumed result must bind an exact hex run and target to an immutable file beneath the request's output root (`.` or `current_recovery`). Both child and parent recheck the file with no-follow directory/regular-file access, bounded reads, semantic identity and raw hash. Latest is never selected as the returned payload: its bytes must still match that exact run; a concurrent different latest is rejected. These extra static transport checks supplement, not replace, the original owner reader. A legacy read-only unconsumed preview remains a preview and receives `saved=null`, preserving the original missing-journal behavior.

## Failures

`ResultTransportError.diagnostic` contains a code, stage, actual/allowed byte counts where applicable and saved identity where known. No arbitrary exception text, stderr or research body is copied into a diagnostic. A serialization budget failure retains saved identity and emits a bounded error control, never a completion footer. Parent cancellation kills/waits only its own worker. There is no retry.

Original owner persistence and IPC completion remain different outcomes: an owner may have written a PARTIAL run before transport fails. No rollback, retry, latest repair or success promotion is performed by this module. Existing failed input receipts and older successful output roots remain untouched.

## Verification scope

A synthetic original archive fixture produces a >16 MiB manager response. The baseline fails with JSON_SIZE_EXCEEDED; the candidate completes the original manager save and an independent cold-process read, comparing the entire payload and exact run/plan SHA. Read-time fields and full response digest are checked.

Protocol tests cover distinct digest scopes, truncated data/footer, chunk/full hash corruption, strict integer counts, wrong order, chunk/total/count budgets, wrong run/root/scope, changed exact file, symlink file, concurrent latest, timeout, oversized controls and stderr, and body-free failure diagnostics. Synthetic lists preserve all 3075 missing-acquisition and 175 missing-theme reasons without reclassification. Existing archive/native/rebound, manager-save and non-HTTP current-recovery tests cover compatibility.

No real archive/manager/producer is run. No HTTP tests or services are started. Real 53-archive acceptance remains blocked pending independent review and separately authorized incremental verification. API publication remains out of scope and can still reject large responses.

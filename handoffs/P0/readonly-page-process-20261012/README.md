# Read-only saved-page worker, original resource profile

This is a complete candidate on the existing V5 development branch. It preserves the working frontend and all prior Mac feedback. Real Mac acceptance of this candidate is pending; the earlier 4c candidate failed.

## Established cause boundary

The fixed Mac paired diagnosis (`c458988a88b7ca367e715f7785b2d7ac6a0eb3b6`, `handoffs/P0/feedback/mac-5bbbc9-boundary-pair-20261012`) measured repeated full-response decoding in a persistent API process. Current RSS before successive response parses stayed at 140 / 273 / 388 MB; after JSON loading it reached 319 / 432 / 543 MB. Every request began with zero weakly live Readers, and encoded content release ran. A persistent reader thread still failed. This supports an accumulating process-memory lifecycle problem; it does **not** identify a particular Darwin allocator or Python bug.

## Small corrective boundary

- Each M18 content/overview/section read now uses a fresh, short-lived read-only worker. It rereads the pinned bundle and runs the unchanged complete Reader/hash/index/canonical/identity checks and original ResourceGuard.
- Reuses the existing offline process supervisor's spawn pattern, bounded framing, final resource footer, deadline-aware receive and reap. Existing build/read writer actions are never called from GET. Their default 16 KiB receipt behavior is unchanged.
- The new page receipt alone allows at most 512 KiB because an existing 256 KiB binary content page uses base64. Semantic HTTP responses remain at their original 256 KiB, per-item16 KiB and loaded-value128 KiB limits. Nothing admits a full response over IPC or HTTP.
- Parent accepts a page only after EOF, complete receipt/footer, correct child PID, successful exit and unchanged 512 MiB / 60 CPU seconds / 90 wall seconds gates. It verifies exact identity/generation/profile/manifest, schema, and requested content index/offset or section/cursor/selection/offset.
- One nonblocking heavy-read slot per API service bounds active workers; overlap returns existing `503 MODULE_BUSY`. Health/descriptor/ordinary module routes remain independent. No worker pool or cross-request Reader cache.
- Missing files retain `503 MODULE_RESULT_NOT_AVAILABLE`; other invalid/resource/worker failures retain `409 MODULE_RESULT_INVALID`. Failure receipts expose no page.
- Worker writes/network/owner work are absent. The worker denies write-mode file opens and socket/subprocess execution. M18 service startup disables bytecode writes in its process and child environment before GET, including callers that started Python without `-B`.
- Reader code/profile, frontend source, dependency lock, route shapes, config and stored data remain unchanged.

## Runtime

Use the same retained V5 saved-view config and all original data pins. No config migration, data rebuild/publication or frontend rebuild is needed:

```sh
PYTHONPATH=<FIXED_CHECKOUT>/V5/src <EXISTING_PYTHON> -B -m v5_shadow.module_api \
  --config <RETAINED_SAVED_VIEW_CONFIG> --port 0
```

Keep the same `V5_MODULE_API_ORIGIN=http://127.0.0.1:<port>` and previously built frontend assets. The existing `/` and `/manager-selection/` views are unchanged. This handoff does not start a deployment or claim a live URL.

## Validation

Relevant complete regression run: 93 tests and 90 subtests passed, including actual original512 MiB RSS rejection and original90-second timeout/termination/reap, plus existing offline receipt/build/read regressions. Subsequent final tests add wrong-kind/page/section receipt rejection and no-bytecode-write library startup; final exact counts are in `VALIDATION.json`.

Large synthetic run: the existing explicitly SYNTHETIC 28,647,597-byte response / 1,103,793-node fixture is read in a separate API process. Overview, summary, gaps, next gaps, materials, empty and repeats total10 reads; each must have its own exited/reaped PID. Machine-readable final metrics are adjacent. Linux synthetic evidence is separate from pending real Darwin acceptance.

A focused Mac acceptance should run the original real descriptor→overview→summary→gaps first/next→materials→small original status→empty stocks→repeat sequence in a fresh standalone API. Record the API and page-worker peaks/exit status separately and verify saved-data hashes/mtimes. Do not put an oracle Reader in either process. Stop on the first unexpected error. Reuse the unchanged built frontend only after the real read sequence passes.

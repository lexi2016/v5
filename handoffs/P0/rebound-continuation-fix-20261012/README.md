# M14 byte-bounded continuation without skipped values

## Confirmed gap and correction

Mac feedback `b23cc0342689d4fc1ba94bf1a83a8894158e8bf2`, `handoffs/P0/feedback/mac-509d18-rebound-resumed-20261012/README.md`, confirmed all 24 original group pages returned HTTP 200 and all 693 entry identities/spans matched. Only 662 values were loaded: 31 rows had `PAGE_BYTES_LIMIT` even though every individual row fit the unchanged 16 KiB item limit. Fixed 32-entry cursor advancement meant those 31 values were never reached on a later page.

The rebound projection now stops **before** the first otherwise-loadable row that would exceed the original 128 KiB aggregate value cap. Its next cursor points to that exact row. A page has at most 32 entries; a nonempty group always advances. A genuinely oversized single item still returns its original metadata with `ITEM_BYTES_LIMIT` and advances, so it cannot cause an infinite loop. Empty groups remain empty. The 256 KiB HTTP cap and all Reader/process resource/profile limits remain unchanged.

The closed rebound cursor still binds run, generation, profile, manifest, source section SHA and group. Only rebound continuation permits offsets that are not multiples of 32. Announcement and ordinary section paging retain their existing contract. Every returned row keeps its exact original index, absolute byte offset, byte count and SHA.

## Frontend compatibility

There are two necessary client changes: allow rebound continuation offsets such as 31, and validate a rebound page with 1–32 entries rather than requiring exactly 32. The existing session already advances by `page.offset + page.entries.length` and stores opaque cursors for Previous; its logic, Vue view, renderer, markup and styles are unchanged. Identity, exact selector, consecutive entry indices, remaining count and positive-progress checks remain enforced.

This requires new built static assets containing the updated `m18SavedResult.ts`; old aa42 assets reject the new variable page lengths. Reuse the existing Mac dependencies and build flow. No dependency or config change is needed.

## Run and focused acceptance

Use the retained saved-run config and a fresh candidate API process:

```sh
PYTHONPATH=<FIXED_CHECKOUT>/V5/src <EXISTING_PYTHON> -B -m v5_shadow.module_api \
  --config <RETAINED_CONFIG> --port <UNUSED_TEST_PORT>
```

Run the targeted Node paging checks, product typecheck and build once for the changed client. No algorithm, owner input, Reader, Vue template or renderer changed. Keep the currently accepted preview until the new backend and assets pass.

For the real saved run `46596b03c2ab4e29b1219fd2e5eb698f`, iterate each original group by the returned cursor and **actual entry count**, not `page_number * 32`. Verify all 693 rows are eventually `LOADED`, no duplicate/missing indices, every loaded sum ≤128 KiB, every response ≤256 KiB and exact original slice/hash/value equality. Test Previous on a non-32 boundary and a group switch. Preserve original row date types (`observed_session` and `target_monday` integers) and all original CANNOT_CONFIRM, UNVERIFIED and unit states. Confirm announcement default/return, worker exit/reap/limits and all saved-data hashes/mtimes unchanged. Do not operate the user's browser or move windows.

Cloud synthetic checks are recorded in `VALIDATION.json`; they do not assert real Mac acceptance. Prior span capture/full Reader validation and process-isolation fixes remain in force. This change does not make the research rows formal selections or trading permission.

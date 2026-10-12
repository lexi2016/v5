# M14 projection: reuse the original validated response scan

## Confirmed failure

Mac diagnostic `f71081168eec44fcad769ecb68642a36dd7ab1be`, `handoffs/P0/feedback/mac-b13ed2-rebound-rejection-20261012/diagnostic.json`, confirmed aa42's first strict request failed with `M18_V2_OBJECT_NODES`. The original full Reader had already validated the saved response. The new projection then rescanned the entire5.2MB section, including duplicate cards and large native/authority metadata, as a new object subject to the200,000-node object gate.

The rejected real worker exited0 and was reaped, with319,029,248-byte peak and unchanged141 data files. This was not an RSS-limit failure. A synthetic matching-cardinality fixture reproduced the node failure at206,033 nodes /5,220,624 bytes, while a smaller193,482-node variant passed.

## Correct bounded boundary

The corrective path captures exact requested nested spans during the original complete response scan. The default capture mode is off. It does not replace the scanner, skip full-response validation, change the original token/section/index counts or raise a resource/profile limit. The full manifest, encoded content, response identity/canonical hash and persisted index checks must all succeed before captured values are exposed.

For an M14 page, capture is limited to the current requested group's32 row spans, five original group counts, and closed whitelisted metadata. Each returned value is read from its exact original slice and checked against its span SHA. Large duplicate cards/native objects are still covered by full-source validation, but are not materialized and rescanned as a new projection object. They are not removed from the saved source.

Per-value/page/HTTP caps remain16KiB /128KiB /256KiB. The original200k object-node gate,1.5M response-node gate,512MiB RSS,60 CPU seconds and90 wall seconds remain unchanged. Oversized current-page values remain NOT_LOADED; no needed business row is silently dropped to avoid a limit. Group/source/cursor identity checks remain exact. No cache, thread pool, owner execution, rebuild/publication or GET write is introduced.

## Runtime and verification

Frontend, dependency lock, projection HTTP schema, config and source data remain identical to aa42. Its Mac Node24 tests, Vue6 tests, product typecheck and build passed at `c44acaaa885ff4637fddb9b84c38a23b693d5a63`; reuse those exact built assets. Do not rebuild or re-run unchanged frontend tests for this backend-only fix.

Start a fresh candidate API process with the retained saved-view config and unchanged pins:

```sh
PYTHONPATH=<FIXED_CHECKOUT>/V5/src <EXISTING_PYTHON> -B -m v5_shadow.module_api \
  --config <RETAINED_CONFIG> --port <UNUSED_TEST_PORT>
```

Focused Mac acceptance: descriptor/overview and announcement first page, then the original M14 strict/near/pending/excluded/unresolved pagination sequence, matching exact original counts, absolute row offsets, hashes and loaded values. Record NOT_LOADED due to unchanged page caps separately. Check worker exit/reap/peaks and data hash/mtime equality. No same-process oracle. Only after real success switch the task preview to this API and the already-built aa42 assets, retaining the current announcement version for rollback. Do not control the user's browser or move windows.

Cloud isolated tests and scale evidence are recorded in `VALIDATION.json`. Synthetic results do not assert real Mac success. This fix does not complete all18 modules or authorize trading.

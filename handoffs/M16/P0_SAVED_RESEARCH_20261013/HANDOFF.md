# M16 P0 saved public research

## Delivered capability

`GET /api/v5/source-bundle/manager-public-research` reads one explicitly bound, committed original M16 result. Optional query: `trade_date=YYYYMMDD`. This route is read-only; POST/PUT/DELETE remain rejected. The preview has a separate “公开资料研究 · M16” entry and loopback-only proxy. Existing M11/M12 entries and bindings are not replaced.

Missing binding or selected file: `WAITING`. Corrupt source/runtime pins, malformed commit, identity conflicts, unsafe claims or failed cold reader: `CANNOT_CONFIRM`, with no old business content. A successful read is `SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED`, `VERIFIED_PERSISTENCE_ONLY`, `can_execute=false`, `natural_verified=false`. Original business status is separate. Reading `PARTIAL_WITH_ROWS` does not make it READY.

The original store `_read_commit` consumes exactly the bounded bytes whose raw SHA was checked. It also performs the original manager safety checks and canonical commit verification. The reader allocates the original store with `__new__`; it never runs the store constructor, service, provider, ensure or lifecycle methods. A cold child has read-only auditing, a 30-second deadline, 8 MiB input and 4 MiB output limits. One M16 reader may run at a time. Public source IDs and facts remain visible; local paths, secret fields and credential-bearing URLs are redacted. The product/job/receipt hashes describe original committed members before this display redaction.

## Fixed source provenance

- Original owner: `lexi2016/v4`, commit `f7cb731c384ee6890a87d16c19a5b5a621779477`, `handoff/v4-running-source-20261005/canonical/`.
- Exactly 20 required original Python members are present byte-for-byte under `V5/source_owners/m16/canonical/`. No locally rewritten owner source is mixed into that directory.
- `V5/contracts/m16_owner_source_manifest.json` is an explicitly selected source descriptor, retaining each original repository path, commit, Git blob ID, byte count and SHA-256. It is not represented as the complete original source manifest.
- Loader/factory/jobs are copied unchanged from M16 commit `5bb1d635abe03cec61d0e52bf1150f2c70b5fe6a`. `V5/contracts/m16_readonly_runtime.json` pins this exact read-only closure.
- The original four-object execution entry remains `manager_factory.build_manager_jobs`. P0 does not invoke it. Its persistent lifecycle and real observation-reader binding are the next separate work item.
- Original PDF dependency manifest is unavailable in this delivery. No substitute manifest, installation claim, source-PDF verification or real-provider completion is asserted.

## Exact binding contract

Add only the route above and `m16_saved_public_research_binding` to the existing local `source_bundle` module config. Keep all other keys and M11/M12 bindings intact. The binding has exactly these keys:

```json
{
  "private_root": "/absolute/new/independent/v5/m16-root",
  "trade_date": "YYYYMMDD",
  "input_identity": "64 lowercase hex characters",
  "job_id": "original committed job_id",
  "generation": "original committed generation",
  "attempt": 1,
  "commit_sha256": "original commit.sha256 canonical-object digest",
  "commit_file_sha256": "SHA256 of unchanged complete original file bytes",
  "data_kind": "OWNER_RESULT",
  "python_executable": "/absolute/existing/python"
}
```

These placeholders are documentation, not a deployable config. Do not put the actual local binding or private root in GitHub feedback.

Private root marker must be exactly this JSON object: `{"module":"M16","private":true,"schema":"v5.private_root.v1"}` in `.m16-private-root.json`.

The only required saved artifact is `.commits/<trade_date>/<input_identity>.json`. Product, selected job and receipt are authoritative embedded commit members. Original standalone product files are not required. An old standalone job may differ from its committed terminal version. Do not rewrite the commit to match it. Original ordinary receipts lack attempt/generation; those are anchored to the committed job. Explicit contradictory receipt fields are rejected. Original EVENT_REFRESH catalyst receipts are also accepted, preserving their distinct job and product statuses.

## Mac byte-preserving admission and deployment checklist

1. Start from the latest integration branch and the exact delivered commit. Preserve the currently deployed M11/M12/M06 changes. Verify all new runtime pins and the 20 original source blob identities. Do not replay the old 32-test loader task as a substitute for the new tests below.
2. The already reported original inventory is pinned by integration feedback commit `6a1abf6b5ae06621ad54bdb83cd677fe513bd3d4`, files `handoffs/P0/feedback/mac-m16-original-inventory-20261013/{REPORT.md,selected-contract.json}`. Use that exact local selected reference, then re-read and recheck the original selected file before copying. The known selection is 20261005, one original committed product/job/receipt with PARTIAL_WITH_ROWS and 10 rows; receipt has no attempt/generation. Both canonical and file digests are recorded in that feedback.
3. Resolve the known original configured root through the authorized local inventory only. Do not search unrelated directories or credentials. Record the protected original-file digests and V4 process identity before migration. Use descriptor-safe `m16_readonly_worker.raw` for bounded regular-file reads; reject symlink components, overlapping source/destination roots or an existing destination. Never add the V5 marker to the V4 root.
4. Validate the selected original bytes before copying: check raw file SHA, call the fixed original `_read_commit` using `PinnedCommitBytes` and a `__new__` store, require exact equality to the parsed original bytes, and validate the selected original members against the intended binding. Do not construct the store, call any producer or manufacture fields.
5. Exclusively create a new independent V5 private directory, then exclusively create `.commits/<date>/<identity>.json` from those exact bytes. Do not JSON-reserialize, overwrite an existing destination, modify source files, copy credentials or synthesize standalone products. Write only the new V5 marker. Verify source and destination raw file SHA and byte count again; leave any failed unpublished destination for explicit review rather than automatically deleting or resuming it.
6. Cold-read the new V5 root using `m16_readonly.read_record` and the intended exact binding. Require saved status, 10 rows, original PARTIAL_WITH_ROWS, exact date/input/job/attempt/generation, both commit digests, and three original-member digests. Check receipt has no invented attempt/generation. This check must succeed without the live V4 service or original runtime directory being used by the reader.
7. Only after that check, narrowly add the route/binding to the current local `source_bundle` config, rebuild the preview with existing dependencies, and restart only the relevant V5 read-only process. Preserve all existing bindings and source response artifacts. No scheduler or producer enablement is part of this delivery.
8. Verify direct and preview-proxied GET, same-date read, other-date WAITING, bad-pin CANNOT_CONFIRM, no product after failed re-read, repeated reads and late-response isolation. Check M11/M12 entries and exact bindings still work. Inspect the real 10-row public-research panel, source facts and raw business status. No trade or write endpoint should become available.
9. Recheck protected original files, V4 process identity and other module bindings. Return only a sanitized commit/test summary, status counts and digests. Do not upload original research, PDFs, private paths, local configs or raw diagnostics.

## Required focused tests

From repository root with the existing Python environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=V5/src python -m unittest discover -s V5/tests -p test_m16_saved_integration.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=V5/src python -m unittest discover -s V5/tests -p test_m11_integration.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=V5/src python -m unittest discover -s V5/tests -p test_m12_integration.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=V5/src python -m pytest V5/tests/test_p0_main_registry.py V5/tests/test_module_api.py -q
cd frontend
npm run test:p0
npm test -- src/components/M16SavedResearch.spec.ts src/components/M11SavedResearch.spec.ts src/components/M12SavedVideo.spec.ts
npm run typecheck
npm run build
```

Do not install dependencies or broaden permissions as part of this handoff. If a command lacks an existing dependency, report NOT_RUN with the missing component. UI/component/typecheck/build remain pending Mac execution.

## Remaining lifecycle work

Saved results alone do not complete M16. Next: bind the original stage-observation reader and PDF dependency closure, own one persistent original service/worker lifecycle with the four-object factory in an independent V5 root, then add a separately controlled command surface and targeted restart/retry/cancellation tests. The current GET child must not be turned into a short-lived producer or mount the original write router wholesale.

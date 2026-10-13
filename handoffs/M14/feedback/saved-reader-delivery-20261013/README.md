# M14 saved-reader delivery feedback — 2026-10-13

## Disposition and scope

**RETURN FOR REPAIR. Static source review only; executable tests: NOT_RUN.**

Reviewed candidate: [ba347d83ce3697028fa7b3ec1f7fce4ff058ac54](https://github.com/lexi2016/v5/commit/ba347d83ce3697028fa7b3ec1f7fce4ff058ac54).
GitHub comparison against its parent `b61df9bb7876d410bd517c6857812137c49ac1d4` confirms exactly two added files:

- `integration_candidates/M14_saved_page/m14_readonly.py`, 109 lines; blob `139bb0374f3870109e765218762c4f42f6d261d5`.
- `integration_candidates/M14_saved_page/test_m14_readonly.py`, 30 lines; blob `76183fb935e1a8b02f53067d9f44c79b7f2b25f4`.

At review time the original `dev/m14-github-handoff-20261011` branch still pointed to `b61df9bb7876d410bd517c6857812137c49ac1d4`; the candidate commit had not advanced that branch. This feedback is a documentation-only descendant of the fresh original branch HEAD. It does not import the candidate tree, update a ref to that candidate, or modify runtime sources, the P0 branch, V4, Mac files, credentials, permissions, or real saved data.

## Existing contract to reuse

The integration baseline is `c7b815c065da83bd2db2b3023be4607ce9f194ec`. The existing production reader is:

[`V5/src/v5_shadow/rebound_owner.py::read_rebound_owner(root, reference)`, lines 490–537](https://github.com/lexi2016/v5/blob/c7b815c065da83bd2db2b3023be4607ce9f194ec/V5/src/v5_shadow/rebound_owner.py#L490-L537).

It requires the exact four-field reference `run_id/artifact_sha256/manifest_sha256/receipt_sha256`, validates the 32-hex run ID and three SHA256 values, opens the marked configured root and `runs/<run_id>` with no-follow traversal, reads each original artifact/manifest/receipt byte string, checks its corresponding SHA, checks the committed receipt and cross-file identity, then validates artifact semantics. Root marker and root restrictions are in [lines 444–454](https://github.com/lexi2016/v5/blob/c7b815c065da83bd2db2b3023be4607ce9f194ec/V5/src/v5_shadow/rebound_owner.py#L444-L454); semantic checks are in [lines 540–587](https://github.com/lexi2016/v5/blob/c7b815c065da83bd2db2b3023be4607ce9f194ec/V5/src/v5_shadow/rebound_owner.py#L540-L587).

The returned object is the complete owner artifact. The groups live in `artifact["research_observation"]`; dates live in `artifact["request"]["target_date"]` and `["signal_date"]`. Its `formal_status`, `computation_status`, observation status, reason codes and safety fields are separate facts. Do not call the producer, rebuild an artifact, or wrap this identity in fabricated M18 generation/identity fields.

## Concrete blocking findings

### 1. No original saved-disk read or three-file verification

[`m14_readonly.py` lines 78–89](https://github.com/lexi2016/v5/blob/ba347d83ce3697028fa7b3ec1f7fce4ff058ac54/integration_candidates/M14_saved_page/m14_readonly.py#L78-L89) accepts arbitrary caller-supplied `stored_result` and hashes only that dictionary. There is no call to `read_rebound_owner`, no disk read, no root marker verification, and no manifest/receipt verification anywhere in the 109-line file. `private_root` is stored but never used. A matching caller-created dictionary is not evidence of a committed original owner run.

Minimum repair: the public adapter accepts only validated server configuration plus an allowed query. On every page request call the original `read_rebound_owner(private_root, reference)`. Keep any pure projection helper private and downstream of that verified read. Missing, changed, or semantically inconsistent original files must fail closed; never replace this with owner/build/model/collection/daily execution.

### 2. Hashing and data shape are incompatible with the original artifact

[`m14_readonly.py` lines 30–31 and 86–91](https://github.com/lexi2016/v5/blob/ba347d83ce3697028fa7b3ec1f7fce4ff058ac54/integration_candidates/M14_saved_page/m14_readonly.py#L30-L31) reserialize a Python object with default `ensure_ascii=True` and `allow_nan=True`. The original persisted encoding uses `ensure_ascii=False, allow_nan=False` in [`V5/src/v5_shadow/digests.py` lines 6–10](https://github.com/lexi2016/v5/blob/c7b815c065da83bd2db2b3023be4607ce9f194ec/V5/src/v5_shadow/digests.py#L6-L10). Rehashing a dictionary is not raw-file SHA verification and differs for non-ASCII data. Line 89 then reads the group at the artifact top level. A complete original artifact has its groups nested in `research_observation`; passing only that nested object would no longer match the full artifact SHA.

Minimum repair: use the original reader's raw-byte verification, retain its full artifact identity, and page only the verified observation's selected group. Preserve the distinction between an absent observation, malformed observation, and a verified empty group.

### 3. Binding, request and cursor contracts are open or incomplete

[`m14_readonly.py` lines 34–43](https://github.com/lexi2016/v5/blob/ba347d83ce3697028fa7b3ec1f7fce4ff058ac54/integration_candidates/M14_saved_page/m14_readonly.py#L34-L43) checks reference values only for nonempty strings. It accepts non-SHA manifest/receipt strings, non-32-hex run IDs and an unvalidated root. [Lines 106–109](https://github.com/lexi2016/v5/blob/ba347d83ce3697028fa7b3ec1f7fce4ff058ac54/integration_candidates/M14_saved_page/m14_readonly.py#L106-L109) rejects only the exact query key `private_root`; all other unknown keys, including unrecognized root/run/digest keys, are silently ignored.

[Lines 57–75](https://github.com/lexi2016/v5/blob/ba347d83ce3697028fa7b3ec1f7fce4ff058ac54/integration_candidates/M14_saved_page/m14_readonly.py#L57-L75) do not require a dictionary or exact cursor keys, bound encoded/decoded cursor length, reject duplicate JSON keys or boolean offsets, or reject an offset outside the actual group. An out-of-range offset can produce a misleading empty READY_WITH_GAPS response. [Lines 84–94](https://github.com/lexi2016/v5/blob/ba347d83ce3697028fa7b3ec1f7fce4ff058ac54/integration_candidates/M14_saved_page/m14_readonly.py#L84-L94) permit up to 128 records and do not validate `limit` as an exact integer; HTTP query strings are not parsed into a closed contract here.

Minimum repair: validate the configured root and exact four reference fields; never accept a client root. Reject all unknown query keys. Pin every continuation to all four reference fields and the selected group. Use a strict, length-bounded cursor schema with an exact integer in range. Reuse the existing 32-row page limit and established byte budgets rather than adding a general pagination framework.

### 4. Raw rows can expose private paths and bypass page byte limits

[`m14_readonly.py` lines 94–100](https://github.com/lexi2016/v5/blob/ba347d83ce3697028fa7b3ec1f7fce4ff058ac54/integration_candidates/M14_saved_page/m14_readonly.py#L94-L100) returns the sliced input rows unchanged. Original source references can contain local payload/manifest/artifact paths; this adapter has no server-side public projection, row byte limit, aggregate byte limit, or explicit not-loaded representation. A row-count limit does not bound response bytes.

Minimum repair: project only approved public fields and source SHA references before returning rows; exclude private roots/paths throughout rows, nested metadata and errors. Preserve original reference hashes and clear projected-row hash semantics. Apply bounded row/page bytes and explicit NOT_LOADED reasons where appropriate, with forward-progress pagination that does not silently drop deferred rows.

### 5. Hard-coded state loses dates, gaps and research boundaries

[`m14_readonly.py` lines 89–103](https://github.com/lexi2016/v5/blob/ba347d83ce3697028fa7b3ec1f7fce4ff058ac54/integration_candidates/M14_saved_page/m14_readonly.py#L89-L103) hard-codes READY_WITH_GAPS for every list, returns only two safety flags, and omits the original reference, target/signal dates, original computation/formal statuses, source/observation reasons, five group counts and coverage. The WAITING branch omits even those two flags. The frontend cannot distinguish history-insufficient pending observations from a genuinely verified empty group, or pin identity from the response.

Minimum repair: return the original target/signal dates and four-field reference, preserve original computation and formal/observation status separately, retain all five groups, counts, history reasons, coverage and research-only safety values. Make clear that zero strict rows with pending history is not a completed normal zero-candidate screen. Keep independent M14 data separate from the old saved manager target and run; retain the existing M18 historic rebound path.

### 6. Tests do not establish an executable or positive saved-reader path

[`test_m14_readonly.py` lines 7 and 28](https://github.com/lexi2016/v5/blob/ba347d83ce3697028fa7b3ec1f7fce4ff058ac54/integration_candidates/M14_saved_page/test_m14_readonly.py#L7) import `v5_shadow.integration_candidates.M14_saved_page`, but the candidate is delivered at repository-root `integration_candidates/M14_saved_page`. The reviewed tree contains no matching package at that import path. [Line 11](https://github.com/lexi2016/v5/blob/ba347d83ce3697028fa7b3ec1f7fce4ff058ac54/integration_candidates/M14_saved_page/test_m14_readonly.py#L10-L11) uses an invalid owner run ID and non-SHA manifest/receipt values. [Lines 14–30](https://github.com/lexi2016/v5/blob/ba347d83ce3697028fa7b3ec1f7fce4ff058ac54/integration_candidates/M14_saved_page/test_m14_readonly.py#L14-L30) contain only three rejection cases; the test named group_and_cursor_binding never creates or checks a cursor.

Minimum repair: supply runnable package/import wiring and exact test commands using an existing environment. Add synthetic persisted artifact/manifest/receipt fixtures that pass the original reader, then exercise multi-page reads across all five groups, retained pending/history gaps, unknown queries, wrong/cross-group cursors, each file's tampering, rehashed cross-file identity tampering, path traversal, symlinks, missing binding, byte bounds, and repeated read-only reads. Assert no producer is invoked and files remain unchanged. Test replacing the configured reference while the original reader can still validate an old explicit reference; do not claim a general history browser or accept arbitrary client roots.

### 7. Delivery is not yet an integrated saved page

The verified candidate diff contains only the adapter and three tests. There is no `module_api.py` binding/route wiring, independent frontend client/component/navigation, or preview proxy change. Existing P0 integration points are `V5/src/v5_shadow/module_api.py`, `frontend/src/views/SavedManagerResultView.vue`, `frontend/src/manager-selection/reboundPanelObservation.ts` and the explicit source-route proxy list in `frontend/vite.config.ts` at `c7b815c065da83bd2db2b3023be4607ce9f194ec`.

Minimum repair: finish the verified disk adapter and its tests first. For the scoped page handoff, provide exact executable integration files or a minimal reviewed patch using the existing renderer and navigation. Keep the original owner algorithm and reader, V4, current manager dynamic opt-in and historic M18 identity behavior unchanged. Do not add M19, a new framework, real-data fixtures, or another writer to shared P0 files.

## Verification status and required return

- GitHub candidate metadata, parent, exact two-file diff, file bodies and blobs: read and verified.
- Original reader path and disk/reference/semantic contract at `c7b815c065da83bd2db2b3023be4607ce9f194ec`: read and compared.
- Candidate tests, positive persisted readback, HTTP/UI tests, typecheck/build, Mac checks and preview activation: **NOT_RUN**. This document claims no executable pass or production acceptance.
- This review does not include real run IDs, actual artifact references, market records, private roots or credentials.

Return a fixed commit on the original M14 development branch, exact changed-file list and before/after hashes, runnable synthetic test evidence with any NOT_RUN limits, and a small P0/Mac integration handoff. If branch HEAD changes, inherit it without force. Keep the rejected candidate available only by its reviewed commit reference; do not advance the branch to its entire tree.

# M10 fixed saved HK close review → existing source API → main page

## Scope and provenance

This is a bounded P0 read-only integration. It adds one GET route and one panel to the existing source section. It does not rerun the collector, builder, model, original 39-test suite, daily scheduler, V4 services or any trading flow. No dependency, lockfile, credential or permission changes are required.

- Original M10 product: `lexi2016/v5@1c0d56d0ea350f8f2178d8b0c6b7e66dfa113585`, branch `dev/m10-github-handoff-20261011`.
- Original handoff: `V5/docs/M10_HK_CLOSE_HANDOFF.md` at that commit.
- Saved real-input evidence: `9ab214b0ad5542111c04d10f50cac989644205f7`. The prior Mac acceptance is 29 product + 10 frozen-owner tests; this integration does not claim to have repeated those tests.
- Known saved trade date: `20261012`, run `20261012-2a08a3fadb260ecd3f8dc17f`, generation `4fc105e27355b4a9dfc6dde25331dea05e48ab513deaf7c4bcf31b6bc2e479a1`.
- That run has 698 source rows, 20 close-Top20 rows, 100 model rows, 70 stage rows and seven `PARTIAL_WITH_ROWS` stages. The read projection is `PARTIAL`; unconfirmed stage metrics and attribution hits stay null. Membership, PIT and natural admission are unverified.
- Original saved Top20/model arrays matched the old review; stage rows/attribution did not. Neither the API nor the page claims byte equality with the old review. The original native label `MODEL_REVIEW_READY` is shown only as its audit label, never as a formal admission claim.

The runtime closure under `V5/source_owners/m10/` is one byte-identical original `hk_close_daily.py` (Git blob `e5e936c8c4cc06008cff048bbe5c5afcbe9c3d7c`). The original uses a namespace package; extra importable files, package initializers and bytecode caches in the private M10 closure are rejected. Only `HKCloseReviewReader`/`read_hk_close_projection` are reachable from the new worker; builder/capsule dependencies are not added. `V5/contracts/m10_readonly_runtime.json` pins file bytes and origin, and the bridge pins that manifest SHA256.

The API returns the original projected `review` unchanged, with its exact run, generation, input identity, native-review SHA256, reasons and fixed safety boundaries. Raw `input_evidence` and `native_evidence` envelopes are not exposed through this HTTP surface.

## Local binding

Keep the current source API's module ID, release, data root, existing M06 binding, source status generation and routes. Add one route and this binding to a new local candidate config:

```json
{
  "routes": [
    "/api/v5/source-bundle/status",
    "/api/v5/source-bundle/hk-preselection",
    "/api/v5/source-bundle/hk-close-review"
  ],
  "m10_hk_close_binding": {
    "run_root": "<ABS_PRIVATE_EXISTING_M10_RUN_ROOT>",
    "run_id": "20261012-2a08a3fadb260ecd3f8dc17f",
    "generation": "4fc105e27355b4a9dfc6dde25331dea05e48ab513deaf7c4bcf31b6bc2e479a1",
    "python_executable": "<ABS_EXISTING_PYTHON_EXECUTABLE>"
  }
}
```

This is a partial config example: retain the existing `schema_version=v5.module_api.v1`, `module_id=source_bundle`, `release_id`, `data_root` and full M06 binding. Do not copy the literal angle-bracket values or commit real absolute paths. The Mac executor supplies the already verified private run root and existing Python; do not collect, republish or change the saved result to satisfy the UI.

The new worker uses the configured existing Python with `-I -S -B`; the original reader needs only stdlib. It cannot import an alternate checkout through PYTHONPATH or site `.pth` files. Do not install a new environment.

## HTTP and UI behavior

- `GET /api/v5/source-bundle/hk-close-review` accepts no query parameters. Run/date/latest selectors and writes are rejected.
- A configured route without a binding returns HTTP 200 with `NOT_CONFIGURED / M10_REFERENCE_NOT_CONFIGURED`, without review rows.
- Wrong run/generation, uncommitted objects, altered receipt/manifest/payload/source code, symlinked root or failed reads return the existing `CANNOT_CONFIRM` error surface, without prior rows or private exception details.
- Advancing latest cannot change the configured exact historical run. The original reader still verifies committed membership.
- Reads do not produce, publish, create bytecode, alter source generation, update ledgers or touch V4. Mutating HTTP methods remain 405.
- M10 has one independent local read slot; the existing M06/M18 slot is unchanged. Simultaneous M06/M10 mounting is supported, while concurrent M10 reads fail fast with the existing `MODULE_BUSY` response.
- The main page retains its current source cards and M06 panel. The M10 child renders all rows in their original order: Top20, model, stages and attribution, with expandable tables and seven-stage evidence metrics. No ranking or selection is recomputed.
- For partial stages, original row-level `hit_top20` audit values are explicitly labeled `CANNOT_CONFIRM (original field: …)`; the page does not present those raw native booleans as confirmed hits. Original projected values remain unchanged in the response.
- Refresh immediately removes old rows. Late responses, failed requests and unmount cannot restore stale rows.
- The existing `V5_SOURCE_API_ORIGIN` proxy forwards the new route to the same local source API. No external origin or new browser permission is added.

## One Mac acceptance command

Use a fresh candidate checkout at the fixed delivery commit, existing dependencies, the private local source config above and a private evidence directory:

```sh
"$PYTHON" -I -S -B V5/tests/run_m10_readonly_acceptance.py \
  --expected-commit "$FIXED_DELIVERY_COMMIT" \
  --source-config "$PRIVATE_SOURCE_CONFIG" \
  --evidence-dir "$PRIVATE_EVIDENCE_DIR"
```

The runner verifies checkout HEAD, rejects tracked/untracked modifications to exercised runtime, tests, runner and frontend build inputs (including HTML entrypoints), records their code hashes and checks the source closure, runs only the targeted integration tests, starts a temporary loopback HTTP server for a real fixed-reference GET, compares its review with an independent original cold projection, and confirms both the M10 run root and current source API root stayed unchanged. It closes that temporary server; it does not modify or restart active services.

It then runs targeted Node parser/session tests, the Vue component DOM checks against the same private real response, product TypeScript checking and the frontend build with existing dependencies. The real response is held only in a temporary local file and removed after the checks. It is never embedded in report.json or uploaded.

Upload only the sanitized `report.json`, source/commit identities and carefully reviewed acceptance summaries to GitHub. `*.local.log` files can contain local paths or test failure DOM and must remain private unless separately sanitized. Do not upload market payloads, local configs or raw private paths.

A successful command is required before the Mac executor uses the existing P0 preview-deployment flow. Preserve the currently verified M06 preview, source/API config, process identities and static manifest as the rollback target. Add the route to the candidate source service using the same existing module entrypoint, then deploy the built main page through the already authorized preview process. Verify actual browser rows/counts/identity and existing source/M06/manager three-way navigation. Do not claim preview deployment from this cloud source delivery.

## Verification status and limits

Cloud checks use synthetic inputs only. The targeted Python/Node tests exercise original frozen store/reader/projection bytes; synthetic envelope construction is test-only and does not assert model or market evidence correctness. The cloud's existing frontend tree lacks Vue/Vite/Vitest/vue-tsc. Typecheck, component DOM and build were attempted and return missing-command errors, not PASS. No packages were installed. Those three checks and real saved-response/browser validation belong to the Mac fixed-commit acceptance.

The acceptance runner supports `--skip-frontend` only for synthetic cloud verification; it emits `PARTIAL_VERIFICATION`, never a full acceptance. Real mode forbids this option.

Rollback uses the existing source-config/process/static candidate switch. No M10 saved run, committed pointer, native source, M06 artifact or ledger entry is deleted or rewritten.

# M12 original-runtime integration candidate

## Delivered scope

The exact ten original runtime files from M12 commit `4bbf069b435d8f0ba28db8e2eba1d358ea5e283c` are included unchanged, together with the unchanged original 21-test lifecycle suite. The added adapter runs the original daily owner in its own Python process with the verified repository root as cwd, and cold-reads an explicitly pinned saved run through the original reader. No ASR/video algorithm is rewritten.

The main saved-results page has a reachable, lazy `视频复盘 · M12` entry. Its GET reader displays saved video identity, ASR transcript and original segments, with the original `ASR_REVIEW_REQUIRED`, gap and stock-dictionary statuses. Synthetic inputs are visibly labeled. Missing configuration/date/run or a non-qualified saved run is WAITING; corrupt evidence is CANNOT_CONFIRM. Neither state is acceptance of a real-data page.

Registry status is `CALLABLE_CANDIDATE_REQUIRES_INPUT`. The callable daily seam is `v5_shadow.m12_daily.run_daily`; it is not registered in the scheduled daily dispatcher. `daily_tick.py`, `daily_dispatch.py`, V4 and current production services were not changed by this overlay. No automatic provider execution, download, schedule, trading, credentials, or deployment occurred.

## Strict overlay, not whole-HEAD deployment

`SOURCE_CLOSURE.json` is the complete 27-file M12 code/test allowlist with exact hashes. Apply only these entries onto the currently deployed M04 composition. Five existing files have `overlay_base_git_blob` checks: module API, registry, registry test, default saved view and Vite config. Preserve any newer unrelated edits by applying the M12-only increment rather than replacing a changed file wholesale.

The GitHub commit inherits P0 `9b73e0fcd29d200fa3f6376187bae7b5432ece3f` (M06 code `5eddebf5c6ecf530ece3fdb31a054b56bf2f1d57` plus its Mac feedback) to preserve M06 changes, but that does NOT authorize deploying its M06 daily backend. Do not deploy the whole repository HEAD. The runtime original-source pin is `V5/contracts/m12_runtime.json`; it includes the original ten files and the two added worker files.

## Read-only API configuration

Append `/api/v5/source-bundle/video-fupan` to the existing source_bundle module API routes, keeping every existing route/configuration. With no `m12_video_fupan_binding` the endpoint returns WAITING, with no acquisition or synthetic fallback. Existing Vite source proxy configuration handles the new route.

Bind real saved evidence only after its exact provenance and original artifacts have been verified. The optional `m12_video_fupan_binding` has exactly these fields:

- `private_root`: absolute independently owned V5 M12 directory, with `.v5-m12-root` containing `v5.m12-private.v1` plus newline
- `trade_date`: exact YYYYMMDD
- `run_id`: exact immutable original run; no latest selector
- `manifest_sha256`: bytes digest of `video_fupan/runs/DATE/RUN/manifest.json`
- `owner_receipt_sha256`: bytes digest of `review/DATE/runs/RUN/receipt.json`
- `data_kind`: SYNTHETIC, RECORDED_INPUT_REPLAY or OWNER_RESULT, chosen from verified provenance
- `python_executable`: existing absolute interpreter

The root must contain the original wrapper manifest/receipt, canonical owner manifest/receipt and every original artifact reference. No copying from or reading live V4 roots is part of this candidate. Client query accepts only optional trade_date; a different date returns WAITING and never substitutes the bound day's content.

The unchanged original reader hashes whole files, so this seam enforces 256 MiB per artifact, 512 MiB total and 256 references; metadata is limited to 4 MiB. Exceeding a bound rejects the read. Transcript/segment display is limited to the first 262144 characters, with exact total and explicit truncation. Media bytes are never returned by the API.

## Explicit daily callable

`run_daily({})` returns WAITING without starting a subprocess. A future explicit owner invocation requires execution_authorized=true plus private_root, trade_date, source_identity, tool_identity, config_identity, data_kind and python_executable. Identity strings are nonempty original binding/configuration descriptions, not credentials. The worker uses the original AcquisitionTools and run_video_fupan; none was run against a real provider during this task. Do not enable this flag or invent provider inputs during the read-only deployment.

The child verifies output descendants have no symlinks before the original writer runs, and installs a Python-side output write guard. This is not an OS sandbox for native subprocesses or a claim of adversarial concurrent-filesystem protection. Unknown/timed-out owner outcome returns WAITING with no automatic retry. Original immutable-run and success-promotion semantics remain intact. Cwd is set on the child only, never on the API/main process.

## Verification and Mac commands

All fixtures are explicitly synthetic, and owner fixture subprocesses block sockets. Latest isolated cloud targeted run: 59 passed, 21 subtests passed. This covers original M12 lifecycle, 11 new integration tests, main registry, module API and M04. The new cases include original owner execution from an unrelated parent cwd, repeat reuse, exact pinned cold content, date isolation, false-success refusal, source-pin order, symlink write rejection, legacy receipt race, timeout, safe root and non-mutating HTTP.

Targeted Node tests: 12 passed for M12, M04 and saved-manager navigation. The complete existing frontend Node script suite subsequently passed all 108 tests, including original synthetic owner fixtures. Full pytest was attempted but collection stops in existing test_rebound_date_compat because the cloud interpreter lacks pandas. `npm test` was attempted but vitest is absent. No dependencies were installed. DOM tests, typecheck and Vite build are provided for the existing Mac environment and are not claimed passed here.

From the isolated candidate repository root, with the existing Mac Python/site path and no dependency installation:

    PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:V5/src:<existing-pytest-site> <existing-python> -B -m pytest -q -p no:cacheprovider V5/tests/test_m12_integration.py tests/m12/test_video_fupan_default_chain.py V5/tests/test_p0_main_registry.py V5/tests/test_module_api.py V5/tests/test_m04_readonly_api.py
    cd frontend
    node --experimental-strip-types --test tests/m12SavedVideo.node.mjs tests/m04SavedResearch.node.mjs tests/savedManagerNavigation.node.mjs
    npm test -- src/components/M12SavedVideo.spec.ts src/views/SavedManagerResultView.m12.spec.ts src/components/M04SavedResearch.spec.ts src/views/SavedManagerResultView.navigation.spec.ts
    npm run typecheck
    npm run build

Then verify default-page M12 button opens/focuses the actual content disclosure, source area stays collapsed, M04 still opens, and prior manager navigation still works. A separate synthetic fixture may prove content rendering; it must never be configured as real saved evidence or accepted as natural verification. A no-binding WAITING page proves only the missing-input boundary.

Mac test/deployment, real video/provider/ASR execution, natural daily acceptance and completed human ASR review are all NOT_RUN/NOT_VERIFIED. Preserve V4 and existing services.

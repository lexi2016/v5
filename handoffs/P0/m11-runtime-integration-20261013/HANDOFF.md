# M11 original-runtime and saved-research integration

## Delivered boundary

This bounded integration imports the unchanged complete M11 runtime from `cc29974b15f2199aef3f19100c91a9195f217074`, including the configuration/archive overlap guard, immutable capsule reader/writer, original owner subprocess, 54 original vendor files plus the V5 build manifest, and original source descriptor/build manifest. The existing asynchronous service candidate is promoted byte-for-byte to `V5/src/v5_shadow/m11/service.py`. `research_review_daily.capture`, `generate`, and `read_owner_day` remain the real original callable entry points. The registry names `research_review_daily.generate` with `CALLABLE_CANDIDATE_REQUIRES_INPUT`; it never declares business readiness.

The added `/api/v5/source-bundle/intraday-research` GET route and reachable default-page M11 disclosure read one explicitly bound saved capsule. They show original intraday/review business content, preserved uncertainty/provenance and six-slot status. A captured slot alone is SAVED; a daily-generation capsule does not mark any intraday slot SAVED. Default missing binding and absent/wrong-date capsule are WAITING. Invalid hashes, envelope, unsafe flags or runtime bytes are refused. No mock is substituted into the deployed page.

The original 09/11 review previously observed at 107389 bytes and SHA256 `b335a6dda1bc02fe6d1a7ecf1c8ff8ee4619458c4099728d4928baa091bbedba` remains DECLARED_ONLY, independently verified false. No separately verified owner-generation receipt or six-slot success has been established. Input authority receipts are not generation receipts. This release supplies no real-data binding. No real provider, model, credential database, capture or generation is called by the browser GET route.

## Exact overlay, never whole HEAD

Use `SOURCE_CLOSURE.json` as the complete code/test allowlist. Entries with `deploy=true` form the runtime overlay; test/source-provenance entries belong in an isolated acceptance tree. Every entry includes byte length, SHA256, Git blob, and the prior main-branch blob where applicable. Original runtime files and promoted service have verified original blob identities.

Overlay only these M11 entries on the already deployed M04/M12 composition. Preserve current M04/M12 API routes, saved bindings, buttons and focus behavior. Only module_api.py, main_registry.py, SavedManagerResultView.vue and vite.config.ts overlap existing files; if any base blob changed, apply the M11 increment rather than overwriting a newer edit. The GitHub parent preserves M06 development work, but that does not authorize whole-HEAD deployment or enabling its daily chain. This change does not edit daily_tick.py or daily_dispatch.py.

Append `/api/v5/source-bundle/intraday-research` to the existing source_bundle service routes. Keep `m11_saved_research_binding` absent for the current real preview: it must visibly return WAITING. Use the existing loopback source API and frontend proxy settings. Do not start the separate M11 acquisition service, add a schedule, enable providers, change permissions or touch V4. Restart/rebuild only the existing authorized V5 preview processes as needed after testing.

## Future saved binding contract

An independently approved exact saved reference has six fields: archive_root, identity, operation, commit_sha256, data_kind, python_executable. The identity has target_date (ISO date), slot, cutoff (timezone-bound), trigger, run_id, input_sha, config_sha, code_sha and source_sha. The source_sha must equal the unchanged approved M11 build manifest. Operation is capture or generate; trigger must match capture or explicit-daily-generation; generate uses the original 15:00 identity slot.

The archive root requires the unchanged `.m11-private-root.json` marker. The route resolves only `intraday/DATE/SLOT/IDENTITY/commit.json` or `daily/DATE/1500/IDENTITY/commit.json`, never latest, a plain dated review or an input-authority receipt. Requests accept only optional trade_date=YYYYMMDD, never paths or run selectors. A changed day cannot show the bound day's content.

Read limits: 2 MiB exact capsule and runtime input files; frontend response 4 MiB; 30-second cold child. Descriptor-walk reads reject symlink components and special files. The unchanged original envelope verifier receives exactly the already bounded and SHA-pinned in-memory bytes, closing the intermediate-file replacement/ABA and unbounded reread window. A post-read SHA check rejects concurrent changes. Child auditing forbids filesystem mutation, process creation and socket connect/bind. The child does not import owner_worker or producer assembly/generation. This is a Python read-only guard, not a new OS sandbox.

Only named original business view fields are projected. Nested local-path/provider/credential/session keys are removed, unsafe independent-verification/trading claims rejected, and original DECLARED_ONLY and false verification fields preserved. The top state is SAVED_RESEARCH_REVIEW_REQUIRED with VERIFIED_PERSISTENCE_ONLY, natural_verified=false and all trading flags false. Persistence proof is not owner, PIT, real-day or strategy acceptance.

## Original callable service

`v5_shadow.research_review_daily.generate` and `.capture` retain all original argument, binding, source-availability, owner isolation, no-replacement and independent readback rules. `v5_shadow.m11.service` exposes the original BoundPlan/Service/default_owner/default_readback/explicit CLI. Neither the module registry nor GET reader starts this service. Real execution still requires valid operator-bound private state, config/source pins, approved source timing and original owner inputs; missing dependencies or inputs retain original refusal details. No synthetic owner function replaces the original.

## Acceptance on the existing Mac environment

Run only in the isolated candidate tree with existing dependencies and interpreter. Do not install dependencies or run real provider inputs. Use bytecode suppression and fixture temporary directories resolved to real paths.

    PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=V5/src <existing-python> -B -m pytest -q -p no:cacheprovider V5/tests/m11 V5/tests/test_m11_integration.py V5/tests/test_m04_readonly_api.py V5/tests/test_m12_integration.py V5/tests/test_module_api.py V5/tests/test_p0_main_registry.py handoffs/M11/delivery/integration_candidate/tests
    <existing-python> -B V5/tools/build_m11_source_manifest.py --check
    cd frontend
    npm run test:p0
    npm test -- src/components/M11SavedResearch.spec.ts src/views/SavedManagerResultView.m11.spec.ts src/components/M12SavedVideo.spec.ts src/views/SavedManagerResultView.m12.spec.ts src/components/M04SavedResearch.spec.ts src/views/SavedManagerResultView.navigation.spec.ts
    npm run typecheck
    npm run build

On the default page, verify M11 opens and focuses its real lazy disclosure, shows six WAITING slots without binding, and does not trigger capture/generate. Confirm M04 and M12 entries still open and earlier manager/source navigation works. Any synthetic visual exercise must be visibly synthetic and must not become the real preview binding. Verify healthy prior read-only routes before/after restart.

Cloud verification is recorded separately in VERIFICATION.json, including failures and unavailable checks. Mac acceptance/deployment remains pending until its own fixed-commit receipt. Full-module/PIT/natural research acceptance remains open regardless of engineering test success.

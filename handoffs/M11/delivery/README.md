# M11 backend candidate: original owner, durable private publication, cold read

Implementation base: `lexi2016/v5@2c408de0888d1e3ab0c3f000d6fc2fa2217bced8`; publication inherits original supplement `8fc903527554044bf7d6beb11b96abbe7e8cabad`, branch `dev/m11-github-handoff-20261011`.
Scope: M11 only. V4, P0, active shared ledger/dispatch/API, M04 and M09/M10 are unchanged. No live deployment, credentials, orders or security changes occurred.

## What is delivered

- Byte-identical original source closure, 54 files copied from fixed donor F with exact origin/blob/SHA/bytes in `V5/vendor/research_review_baseline.sources.json`.
- Default entry `V5/src/v5_shadow/research_review_daily.py`; implementation `m11/daily.py`; explicit CLI `python -m v5_shadow.m11`.
- Real original calls: capture_intraday; independent read_intraday_day; assemble_runtime followed by run_generation(replace=False); exact-date daily reader. No replacement research algorithm, alternate provider or production fake runner.
- Reused original SafeRoot and kernel_lock. Immutable artifact/manifest/receipt are one atomic no-replace commit envelope. Partial legacy files are not accepted as committed. Cross-process read verifies identity, payload, manifest and receipt hashes.
- Durable process intent: unknown interruption reconciles through read only; it never silently calls capture/generation again. Only the original FAILED_NO_REQUEST outcome permits retry. Successful original output is retained; archive interruption can resume from saved owner result.
- Six exact Shanghai slots, original inclusive integer-minute 0–8 boundary; bound source times reject unknown and late availability. Valid timestamps alone do not prove PIT, so PIT and natural admission remain CANNOT_CONFIRM.
- API/scheduler adapter candidate is separate and not applied to active shared files. No new UI is part of this delivery. Existing P0/page integration is a later explicitly scoped step.

## Source trust and the explicit new V5 build identity

Historical F did not contain OWNED_SOURCE_MANIFEST.json. The real research-desk r4 manifest was later recovered unchanged in `handoffs/M11/owner_manifest_supplement_20261013/` at 8fc903. Its SHA is 104ac49a1dc3e2bb970878da096a9b7d6dc86db9b63f0d6ac561109fb5829914. It validates the older 39-file owner, not F: F has a 6830-byte assembly.py with optional Iwencai binding plus iwencai_binding.py; r4 declares the 5780-byte older assembly and no Iwencai file. No silent version downgrade was made.

With explicit authorization, `V5/tools/build_m11_source_manifest.py` creates a NEW reproducible V5 build manifest over all 40 unchanged F owner Python files and the five unchanged required external files. Schema is `v5.m11.build_source_manifest.v1`; build_origin names F; historical_original_manifest=false. It is not a recovered historical F manifest and not r4's original.

The unchanged original validator accepts caller-pinned manifests, verifies every hash/size, exact complete Python set and all five external files. The wrapper externally pins this build manifest to `c824e9b9bfdbda716c7f2ce25e584866f99913c224662550d0e68deb8e4bd558`. Original validator bytes and its read-only/source-boundary checks are unchanged. The separate V5 packaging descriptor covers 54 original files plus this one generated metadata file.

Real original validator and real default assemble_runtime now pass with the new build identity using isolated explicit fixtures; no credential DB was opened. This does not establish actual acquisition/model generation, PIT, natural trading-day evidence or deployment. Real operational config/input/cache/profile/dependencies remain separately required. Trusted F manifest validation is no longer blocked by the historical missing file.

## Verification

See `evidence/m11-runtime-suite.{json,stdout,stderr}` for the pre-build-pin runtime suite (37 passed), and `evidence/original-selected.*` for original regressions (14 passed, 5 deselected). These are separate scopes, not a claimed 51-test full natural chain. After the source-pin change, `source-pin-affected-tests.*` records 17 affected/default/CLI/publication/build tests passed, including the six new validator/assembly tests. Unrelated unchanged tests were not rerun or added to a fabricated total. Integration candidate has its own scope and logs. `TEST_STATUS.json` records remaining NOT_RUN/BLOCKED checks.

Initial RED logs are preserved under `evidence/tdd/` as raw transcripts. Their exact launch metadata was not recorded at the time; final and later recorded runs have full command, interpreter, cwd, start/end, exit status. No unrecorded timing is invented.

`runtime.patch` and `reverse.patch` are independently generated valid Git binary patches covering runtime, vendor, build tool and tests. All source files remain normal readable UTF-8 in the source tree and after/. Binary patch encoding avoids repeating large original-source text in tool payloads. `before/`, `after/`, CHANGE_MANIFEST and PATCH_VERIFICATION bind complete changed files; inherited handoff original sources are retained unchanged. Delivery metadata is intentionally outside the runtime patch to avoid recursive self-hashes.

## Entry

Use the existing authorized interpreter/environment. Bind explicit private M11 state and archive roots with the exact marker `.m11-private-root.json`: `{"module":"M11","private":true,"schema":"v5.private_root.v1"}`. The roots must be disjoint from each other and code. Creation/activation of real bindings is an operator integration step, not something HTTP may request.

A CLI binding JSON has exactly state_root, archive_root, config_path, config_sha256, owner_manifest_sha256. The config remains the original owner format; no fields are silently rewritten. Pin the binding file itself with --binding-sha256. Read:

`PYTHONPATH=V5/src python -B -m v5_shadow.m11 --binding-file /approved/m11-binding.json --binding-sha256 <sha256> read --date YYYY-MM-DD`

Explicit capture adds `capture --date ... --slot 09:25 --cutoff <aware ISO> --run-id <id> --sources-file <approved JSON> --sources-sha256 <sha256>`.
Explicit daily uses `generate` with the same arguments except slot. Source-time records require event_time, published_at, observed_at and available_at, all explicitly time-zoned. No source-time record grants permission to fetch or to access a credential.

A new explicit daily generation uses a separately bound private owner state/config and a new run ID, retaining the previous state and archive. The wrapper never passes --replace and never mutates old successful output. A changed config cannot reuse an old owner slot under different facts; the original owner refuses that and the integrator must bind a distinct private generation state.

## Post-f932 configuration/input boundary fix

A focused negative test found that an operator-bound config file could be placed inside archive output. Binding now rejects equality and every archive descendant before any config or marker reads, using M11_CONFIG_OUTPUT_OVERLAP. Three negative cases plus a separate-config zero-write positive case progressed RED 3 failed/1 passed to GREEN 4 passed. No original algorithm or V4/shared path changed, and no unrelated test suite was rerun. Evidence: config-boundary-red/green. This is a source-safety fix, not new data/PIT/production evidence.

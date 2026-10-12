# M06 fixed committed pool → existing source API → main-page 100 rows

## Scope and fixed inputs

This change extends the existing P0 source API and its main-page source panel. It does not add a service framework or a producer route. Existing M01/M02/M03/M05 job semantics, M03 owner bytes, shared ledger, manager run, M13/M14/M15/M18 routes and pages remain unchanged.

- P0 input HEAD: `aa59bfb8551b0d2f86ed88b28e9127354ff8b976` on `dev/v5-main-integration-20261012`.
- Private original M06 closure: exactly 50 runtime files from `08ed9de9ddb5fd2c62eb1762df2f6106464d823b/handoffs/M06/source/V5`, copied byte-for-byte under `V5/source_owners/m06/V5`. The explicit file identities are in `V5/contracts/m06_readonly_runtime.json`. Original M06 manifests, reader, projection, vendor and private ledger/API helper versions are not modified or installed over shared helpers.
- Mac M06 engineering feedback: `aa5fdca87de4b23d60d6b730609350d35cadd748`, 85/85 tests passed. These are prior M06-module results, not rerun as part of this P0 change.
- Real existing-pool publication feedback: `7006c6ab6e2b4f1f9f6a00da0b3b490dcd4d4fd8/handoffs/M06/feedback/mac-08ed9de9-real-admission-20261013/committed-reference.json`. The feedback reports original `ASSEMBLED`, `fixture_only=false`, daily `SUCCEEDED`, `EXISTING_VERIFIED_POOL`, cold100 readback, and no new model execution.
- Target `20261013`; signal and eligibility source `20261012`; original run `20261013-hk-connect-d1-top100-0-2-b4a529e45fd4`; computation `f7d1e1d4f4472c5e0733f1ca5cbc32d2c297e651fd3d5a0e3874a6c7ba5cd92b`; published artifact SHA256 `3a56de134302f545c89c021e1184d1ecadf735f1f263c18e4c266e488b6469df`.

No raw real pool, model, market input or Mac absolute path is part of this commit. Tests generate clearly synthetic data in temporary roots.

## Local configuration, same existing source API

Keep the current source API's `schema_version`, `module_id=source_bundle`, `release_id` and `data_root` exactly unchanged. Add the second route and one immutable local binding to a new local config file:

```json
{
  "schema_version": "v5.module_api.v1",
  "module_id": "source_bundle",
  "release_id": "<CURRENT_SOURCE_RELEASE_ID>",
  "data_root": "<ABS_EXISTING_SOURCE_API_ROOT>",
  "routes": [
    "/api/v5/source-bundle/status",
    "/api/v5/source-bundle/hk-preselection"
  ],
  "m06_hk_preselection_binding": {
    "bound_root": "<ABS_EXISTING_M06_PUBLISHED_OUTPUT_ROOT>",
    "python_executable": "<ABS_EXISTING_VERIFIED_HK02_PYTHON_3_13_12>",
    "committed_reference": "<REPLACE_WITH_COMPLETE_ORIGINAL_REFERENCE_OBJECT>"
  }
}
```

The last value must be the full original JSON object from the fixed feedback/local publication, not this placeholder string, a relative pointer, a guessed SHA, or a `latest` lookup. The actual output root and interpreter remain local. The data root must retain its existing source-module marker and saved generation. Do not recreate source jobs just to add this page.

M06's publication binds its actual executable and stdlib identities. Use the same existing verified HK02 interpreter as that publication; do not change identities, copy/upgrade an interpreter or republish the pool merely to satisfy this page. The configurable interpreter applies only to the isolated M06 reader, so the P0 source service and M03 environment do not need to change.

This existing HK02 environment is a transition/test binding. Final standalone V5 HK02 environment assembly and a newly identified independent-runtime product remain unfinished. This change does not package an independent final runtime or make its V35 release-directory dependency permanent.

## Read path and failure semantics

`GET /api/v5/source-bundle/hk-preselection` accepts no query fields. The local config fixes the exact reference. P0 verifies the private M06 code closure, starts the configured interpreter with `-I -B`, and calls the original `project_hk_preselection_record`. That helper invokes the original committed-reference cold reader, checks source/artifact/manifest/receipt/code/dependency identities, and returns the unchanged original module-response record. P0 checks that record again with its existing validator and returns its payload.

No GET calls daily/materialize/publish, creates cache/ledger/generation files, switches the source active generation, or recomputes a score/model. The cold worker cannot import the shared P0 ledger in place of M06's pinned private copy. Errors are returned through the existing module API without raw tracebacks or local paths. POST and other mutating HTTP methods remain 405.

An explicitly configured route without a binding returns `NOT_CONFIGURED / M06_REFERENCE_NOT_CONFIGURED`, no artifact. Wrong or damaged references fail closed with `CANNOT_CONFIRM`; unavailable service or missing route is a visible read failure. A read failure or new request clears previous browser rows. The UI does not promote PIT, formal eligibility, natural status or model-weight verification.

The existing four-module status parser is unchanged. The M06 panel is an independent child of the existing main-page source section. It displays target/signal/eligibility dates, source run and hashes, fixture status, research boundary and every original field for all100 rows in original order. It does not rank, clip, summarize away rows or label them formal recommendations.

The original source-status publication permits either its previous single route or that route plus M06. This preserves future explicit source-status generation publication under the combined local API config; it does not make the M06 GET a producer.

## Targeted source checks

From the checkout, with existing Python:

```sh
PYTHONPATH=V5/src:V5/tests "$PYTHON" -B -m unittest test_m06_readonly_api test_source_bundle.SourceBundleTests.test_source_publication_is_readonly_and_separate_from_manager -v
PYTHONPATH=V5/src:V5/tests "$PYTHON" -B -m unittest test_module_api -v
cd frontend
node --test tests/hkPreselectionPool.node.mjs tests/sourceBundle.node.mjs
npm run typecheck -- --project tsconfig.cloud-product.json
npm run build
```

The cloud's targeted Python/Node execution evidence is recorded separately. Its existing dependency tree lacks `vue-tsc`, Vue/Vite/Vitest; a real attempted typecheck returns exit127, not PASS. No packages are installed, no lockfile is changed, and existing Node types remain in tsconfig. Mac must use its already installed frontend dependencies for typecheck/build. Do not rerun the prior85 M06 module suite for this narrow integration.

## Mac single fixed-reference acceptance and deployment

1. Check out the delivered fixed P0 commit into the existing isolated V5 candidate location. Verify the private50-file runtime manifest. Preserve current deployed code/static manifest, source API config, process identity and preview rollback target.
2. Use the original M06 output root and exact complete reference from the successful real admission. Add the local binding above using the same existing verified HK02 interpreter. Keep the source module release/root and its four-module active generation unchanged.
3. Run the targeted checks with existing dependencies. Start the candidate via the same existing `v5_shadow.module_process` entry and current module API configuration workflow, using a verified free loopback port. Do not add a daemon, framework, schedule or source collection.
4. For the one real-reference acceptance, GET the new route and compare the entire returned artifact with the locally saved committed artifact, not just row_count. Confirm all100 rows/order/original fields, three dates, run, computation and artifact identity. Confirm fixture=false and model_weights_reverified=false; retain PIT/natural/formal flags false. Compare output-root files/ledger before and after; no changes are expected.
5. The Vite config forwards the new route through the same `V5_SOURCE_API_ORIGIN` as the status route. Build the candidate using existing dependencies and perform the existing single preview deployment window. Verify the main page's actual rendered100 rows and identity text, not just a READY label; keep real payload and local paths local. Verify the old four source cards and manager/announcement/rebound/US-mapping same-run navigation still use their existing saved identities.
6. Save sanitized commit/config-hash/static-manifest/test/HTTP/DOM/unchanged-root evidence on the authorized branch. If any acceptance fails, retain the existing active preview and exact M06 output; do not republish or recompute it.

Rollback is the existing P0 candidate/process/static/config switch back to the recorded prior verified release. No M06 object, source generation or ledger history is deleted or rewritten. Real Mac API/DOM acceptance of this new integration remains NOT_RUN until its own fixed-commit feedback returns.

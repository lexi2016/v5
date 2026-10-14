# Cloud P0 source startup and M04 research integration

This is an isolated Linux development candidate. All executed business inputs are
**SYNTHETIC**. No Mac/Windows access, real capture, live configuration change,
deployment, natural run, PIT acceptance, trading, merge or force push occurred.
The M01–M18 / P0–P5 plan and acceptance counts are unchanged.

## Fixed inputs and delivered code

- P0 parent: `1053e27b94cfdbd71abaa2edc69fc23b33cfcab4`, original development branch
  `dev/v5-main-integration-20261012`.
- Unmodified M04 dependency: `0bb46df890d4b1a57fcc17982a9800cac2f18146`,
  `integration_candidates/M04_capture`; 504 files including RELEASE, 503 manifest
  members; RELEASE SHA256
  `2bafef714a5d35352d54ff8a4d2dde0898fb1fb2ce48e71b3a0eafc4108828de`.
- Complete research namespace (21 files) copied from the existing P0 candidate,
  including the existing rapid date-selection fix. No research algorithm was rewritten.
- Six shared files received the original `apply_candidate.transforms` delta after
  verifying their bytes against P0's fixed Git HEAD. This is a new cloud integration
  against that HEAD, not a replacement of the Mac's different live composition.
- Complete multi-root bridge copied byte-for-byte from M04 `page_bridge/`.
  `ASSEMBLY.json` records preimages, transformations and reused file hashes.
- Source launcher now supports `run_shadow.py runtime ...`; the managed child uses
  its absolute source entry with `-I -B`. The reproduced pre-fix failure was
  `MODULE_API_START_FAILED`, caused by `python -m v5_shadow.module_process` requiring
  a separately inherited package path. No PYTHONPATH is needed by the new source entry.
- Updated navigation expectations for the newly integrated research link; also
  corrected a pre-existing stale M07-disabled expectation, independently reproduced
  on the original P0 HEAD. No M07 behavior changed.

## Executed verification

See `VERIFICATION.json` and `evidence/` for exact logs and environment identities.
Targeted suites only: the historic full-P0 failures are not erased or declared fixed.

| Check | Result |
|---|---|
| P0 source lifecycle / registry / managed process | 13 passed |
| P0 module API / gateway / publication routes | 30 passed, 2 subtests passed |
| Existing M04 package on its declared exact environment | 54 passed, 0 skipped |
| Existing research HTTP integration | 2 passed, synthetic single-root cold reader |
| New ordinary HTTP multi-root integration | 1 passed, old/new synthetic dates, reverse order, missing date, POST refusal, unselected-root tamper, unchanged bytes/mtime |
| Research / manager navigation / M04 component DOM | 63 passed, 9 files; jsdom only |
| Frontend Node contracts | 164 passed |
| Typecheck / production build | exit 0 / exit 0 |

The initial M04 attempt on Python 3.14.7 was correctly rejected by its exact-profile
guard (54 run, 2 failures, 1 error). Its log remains. No profile was relaxed. The
successful M04 environment is Python 3.13.12, pandas 2.3.3, pyarrow 23.0.1.
P0 uses Python 3.14.7 and its existing frozen lock (pandas 2.3.3 / pyarrow 24.0.0).
The new multi-root HTTP test can run P0 and its M04 subprocess in these separate
interpreters using `M04_PYTHON`.

System-call traces cover the P0 lifecycle and synthetic M04 HTTP scenarios only.
They record no `/workspace/v4` access, no port 8873, and no non-loopback INET
connections. Read-only M04 checks retain file SHA and mtime; tests deliberately
tamper only their temporary synthetic manifest and restore it afterwards.
Raw traces remain in the cloud evidence directory; hashes are in
`evidence/runtime-access-summary.json`. This does not prove every unexecuted owner
or all 18 modules independent.

## Source-distribution startup from outside the checkout

Keep the full repository tree (including contracts, vendors, producers and UI).
This delivery uses the existing source-distribution model, not a wheel missing its
non-package resources. `V5/examples/p0_runtime_config.json` is an older placeholder,
not a runnable module API configuration; use the explicit schema below.

Set `V5_SOURCE` to an absolute V5 checkout and `PY` to a Python >=3.14 environment
with dependencies from the unchanged `V5/uv.lock`. Choose a new empty private
directory outside V4 for `PREVIEW_ROOT`. Create `data/.v5-module-root` containing
`v5.module-root.v1:source_bundle` and a newline. Save this config with absolute paths:

```json
{
  "runtime_root": "<PREVIEW_ROOT>/runtime",
  "composition": "cloud-readonly-source-preview",
  "module_api": {
    "schema_version": "v5.module_api.v1",
    "module_id": "source_bundle",
    "release_id": "SYNTHETIC_OR_EXPLICIT_SAVED_BINDING_ONLY",
    "data_root": "<PREVIEW_ROOT>/data",
    "routes": ["/api/v5/research/lane", "/api/v5/research/wechat/materials"]
  }
}
```

Without a binding, research is explicitly NOT_MATERIALIZED; wechat is NOT_CONFIGURED.
No owner runs on GET. `composition` remains the existing required metadata field;
this startup does not claim to validate an 18-module composition.

```sh
cd /tmp
"$PY" -I -B "$V5_SOURCE/V5/run_shadow.py" runtime validate --config "$PREVIEW_ROOT/config.json"
"$PY" -I -B "$V5_SOURCE/V5/run_shadow.py" runtime start --config "$PREVIEW_ROOT/config.json"
"$PY" -I -B "$V5_SOURCE/V5/run_shadow.py" runtime status --config "$PREVIEW_ROOT/config.json"
"$PY" -I -B "$V5_SOURCE/V5/run_shadow.py" runtime stop --config "$PREVIEW_ROOT/config.json"
```

Start returns the allocated loopback port; health is `/__v5/module-health`.
Stop before restarting; preserve the same configuration and runtime identity.
No tick/schedule/source-bundle execution is implied. For the independent UI, run
the existing frontend with `V5_SOURCE_API_ORIGIN=http://127.0.0.1:<allocated-port>`
and open `/?view=research`; keep it on loopback.

To reproduce the actual synthetic tests, bind the **unchanged** M04 package:

```sh
PYTHON_BIN="$M04_PY" sh "$M04_PACKAGE/test_offline.sh"
M04_CAPTURE_PACKAGE="$M04_PACKAGE" M04_PYTHON="$M04_PY" \
  "$PY" -B "$V5_SOURCE/integration_tests/test_m04_multi_root_http.py"
```

For saved archives, follow the fixed M04 `PAGE_BINDING.md` and
`page_bridge/prepare_binding.py`. Embed its generated source module configuration
under `module_api` in a new runtime config. Preserve all original root/files bindings
and pins. Never point at a V4 active root or apply this candidate to the live release.

## Remaining gaps and precise handoff

- Cloud has no original saved old-18/new-8 archive roots or their complete
  `{root,files}` bindings. The exact required inputs are the historical binding
  plus the successful d598 resume result's `archive_binding`, with every file named
  by those descriptors (archive, manifest, receipt, raw acquisition and builder
  evidence). Their real Mac evidence is already recorded in
  `../feedback/mac-m04-real-window-recovery-20261014/{README.md,summary.json}`.
  Do not request all source again or fabricate acquisition clocks. Existing Mac
  54 PASS and old18/new8 HTTP/cold-reader results remain historical evidence.
- Native browser visual acceptance, real archive execution here, natural/PIT and
  full module acceptance remain NOT_RUN. Tests stop all test listeners; no persistent
  hosted preview is promised.
- The earlier two M04 live-release rejections and M14 release restriction remain
  binding. This cloud work neither retries nor bypasses those actions.
- Full release composition, all owner closures, full release regression, wheel
  packaging (if chosen), and P5 multi-day natural acceptance remain outstanding.
  Source/vendor names containing `v4` are provenance, not proof of active runtime
  dependence; unexecuted owners still require individual checks.

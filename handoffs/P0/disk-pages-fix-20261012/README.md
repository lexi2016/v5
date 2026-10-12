# M18 persisted bounded-pages request path

Base: `54215e4b49d45409f50477aad4e8c0b243640a0a` on
`dev/v5-main-integration-20261012`. V4 is unchanged.

## Complete runnable delivery

Use the complete repository tree at the delivered commit, not extracted code
snippets. The commit retains the existing runtime files and dependency contract:

- Runtime entry: `V5/src/v5_shadow/module_api.py` (`python -m` entry below).
- Runtime closure in the same directory: `composition.py`, `contracts.py`,
  `digests.py`, `api_gateway.py`, `m18_offline_v2.py`, `m18_offline_pages.py`,
  `manager_result_transport.py`, and `__init__.py`.
- Existing offline writer/layout reference: `m18_offline_v2_process.py`.
  GET does not execute this worker.
- Existing publication path: `module_artifacts.py` and
  `m18_v2_publication_bridge.py`; it is not a GET preparation step.
- Existing dependencies: `V5/pyproject.toml` and `V5/uv.lock`. Reuse the authorized
  Mac's existing locked environment; no new dependency or installer is needed.
- Config template: `V5/examples/m18_v2_module_api_config.json`. Its placeholders
  are intentionally unbound. For the real canary use the retained complete
  `LOCAL_ONLY_config.json` from the previous successful server startup unchanged,
  including its actual absolute roots and manifest/profile/six-identity values.
- Necessary tests and results: commands below. This document is the deployment
  handoff; no manual source assembly or new wrapper is required.

From the complete checkout's repository root, `$PYTHON` is the existing Mac
interpreter, `$CONFIG` is that retained complete local config path, and `$PORT`
is an unused loopback test port selected by the existing test process (not V4's
8873). Standalone startup is:

```sh
PYTHONPATH="$PWD/V5/src" "$PYTHON" -B -m v5_shadow.module_api \
  --config "$CONFIG" --port "$PORT"
```

For acceptance prefer the existing canary, which starts on port 0 and owns its
server shutdown. No rebuild, republish or application installation is necessary.

## Repair

- Validate the exact descriptor schema emitted by `descriptor_from_bundle`,
  including date, pages route and timestamp. Verify all six identity fields,
  the pinned profile, and the offline generation separately from publication.
- Resolve the configured `bundle_root` using read-only directory descriptors:
  `manifest.json` plus extensionless `objects/<64 lowercase hex>` files.
  Construct the existing `Bundle` and `Reader`, then return one `content(page)`.
- Reuse no-follow regular-file reads, strict object `<16 MiB`, aggregate
  `<64 MiB`, record-count admission, and the existing Reader/resource checks.
  Never call the offline process writer, rebuild, publish, collect, or run owners
  from GET. Missing/invalid input remains an error, never empty READY data.
- Keep the original exact ordinary-module config schema; the M18 pages route
  still requires its binding. Do not change publication/CAS or global budgets.
- Correct the static example test to treat placeholders as placeholders and
  resolve its path relative to the test file. The example itself is unchanged.

## Verification

Isolated cloud scratch directory; existing Python 3.12.14 / pytest 9.1.1.
No dependencies installed. All 22 unchanged fetched files were verified against
their fixed-base Git blob SHA after materialization.

RED: the real persisted synthetic fixture returned pages HTTP 409 while health
and the published descriptor returned HTTP 200. The test expected HTTP 200.
The existing ordinary-module tests also reproduced the unintended config
regression; the old example test reproduced its placeholder-SHA assertion.

From `V5/`, using the existing interpreter as `$PYTHON`:

```sh
PYTHONPATH=src:tests "$PYTHON" -m pytest -q \
  tests/test_m18_v2_disk_pages.py \
  tests/test_m18_v2_module_api_binding.py \
  tests/test_m18_v2_http_bridge.py \
  tests/test_m18_v2_publication_bridge.py \
  tests/test_module_api.py tests/test_module_artifacts.py
```

Final result: **50 passed, 27 subtests passed, exit 0** (21.31 seconds).
The real synthetic path uses two content pages; their verified bytes reassemble
exactly, with unavailable-input gaps preserved. Publication and bundle file
hashes/mtimes stay unchanged. Negative cases include all six identity fields,
pins, missing/invalid binding, pages/run queries, bad generation/date/route,
missing/tampered/extra objects, object size, FIFO, symlink and directory objects.
Existing API isolation, publication, and CAS regressions are included.

The unchanged offline/worker/resource regressions also ran:

```sh
PYTHONPATH=src:tests "$PYTHON" -m pytest -q \
  tests/test_m18_offline_v2.py tests/test_m18_v2_process.py \
  tests/test_m18_v2_receipt_transport.py tests/test_m18_v2_resource_stress.py
```

Result: **28 passed, 48 subtests passed, exit 0** (241.51 seconds). This includes
the real subprocess receipt-deadline and RSS/CPU/wall-limit checks. Combined
focused coverage: **78 tests and 75 subtests passed**. AST syntax validation of
all three changed Python files also passed.

Mac Python 3.14, the real saved run, full-repository suite, frontend and preview
deployment: **NOT_RUN here**. The full project requires Python >=3.14 and
pyarrow; neither is available in this cloud interpreter. These focused tests
are synthetic engineering evidence, not complete P0 or business acceptance.

## Mac next step

Check out the delivered commit in the existing authorized isolated Mac test
workspace. Run the focused command above with its existing Python, then rerun
the existing real-bound HTTP canary using the retained `LOCAL_ONLY_config.json`
for run `46596b03c2ab4e29b1219fd2e5eb698f`. Keep the saved bundle and current
publication intact; do not rebuild or republish them to make the test pass.

Expected: health/descriptor/pages page 0 all HTTP 200; page content matches the
pinned Reader and all six identities; offline generation remains separate from
publication generation. Record the before/after publication and bundle file
hash maps and clean shutdown. Only then proceed to preview/page acceptance.

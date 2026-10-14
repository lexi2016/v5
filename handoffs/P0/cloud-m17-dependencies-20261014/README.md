# M17 runtime dependency closure in the independent P0 source bundle

Base P0: `10ac74424fd7a0793cd1a51053a3a78231050aee`.
Original M17 development head: `6d459cbc1e694eed413d142c75be64241a727e7f`.
Work remains on `dev/v5-main-integration-20261012`.

This increment fixes the verified `ModuleNotFoundError: fastapi` in the actual
M17 producer → shared router import chain. All 24 frozen M17 source members match
both the original branch and `contracts/close_recapture_source_manifest.json`
(SHA256 `f3c6eedee74ea4d2f72641e4c0e9386b844ff0dfd40506f8c2e1ba566a94cf50`).
No M17 algorithm, worker, manifest or data contract was changed.

## Dependency decisions

| Dependency | Role and disposition |
|---|---|
| FastAPI | Required by the current frozen producer and cold reader: router line 17 imports `APIRouter`, `HTTPException`, `Query` before service creation. Added to root runtime dependencies. |
| FastAPI transitive packages | Resolved and hash-locked from official PyPI, including Starlette/Pydantic and their required dependencies. 18 total runtime distributions; original 7 versions retained. |
| Uvicorn | ASGI service launcher; neither the M17 worker/reader nor P0's stdlib HTTP entry uses it. Not installed for this runtime. |
| HTTPX / pytest | Optional HTTP test client / test runner. Not imported by the tested production chain and not installed in either clean environment. Targeted checks use stdlib unittest. |
| PyTDX / Futu SDK | Separate real-provider interpreter dependencies. Existing explicit runtime/source hash admission gates remain. Neither installed nor called in this synthetic run. |

No M17-local dependency manifest was found on the original branch. The FastAPI
range `>=0.128,<1.0` is the existing V5 donor declaration in
`V5/vendor/rebound_baseline/pyproject.toml`, not a newly discovered M17 lock.
The P0 resolver selected FastAPI `0.143.0`; exact versions and artifact hashes are
in `V5/uv.lock`. No service extras were requested. Framework/server separation is
also described by [FastAPI's server documentation](https://fastapi.tiangolo.com/deployment/manually/).

`health.observe_dependencies` now recognizes this finite runtime closure, including
a distribution-owned file in the OpenTelemetry namespace. Exact version,
installation origin, recorded-file membership and complete expected package-set
checks remain mandatory. Unknown future dependencies still fail closed.

## Evidence and scope

- Reproduced original cold import failure in the previous frozen environment.
- New dependency tests: **5 passed** (lock match, omitted FastAPI lock entry,
  version mismatch, original producer/reader cold import, CLI help).
- Focused existing regression: **12 passed** (6 M17 process/registration cases,
  6 health contract cases). No full M04/UI/module-suite rerun.
- Actual M17 CLI with synthetic private-root fixtures: distinct producer/reader
  processes, `SUCCEEDED`, then `REUSED_SUCCESS`.
- Actual P0 CLI: `STARTED → RUNNING`, HTTP health verified, `STOPPED`.
- `package-check`: `MATCH`, 18 installed runtime distributions and finite source
  manifests verified. This command still declares `complete_release_verified=false`.
- Relocated clean source and second clean environment: the same CLI smoke passed;
  5 dependency tests passed again. These are repeatability checks, not new coverage.
- Relocated process trace: no `/workspace/v4`, original V5 checkout or port 8873
  access; observed IPv4 addresses only `127.0.0.1`. This is scenario evidence only.
- Independent read-only review confirmed lock closure and unchanged M17 bytes,
  and verified missing package, wrong version and wrong origin rejection.

The first new CLI probe deliberately used isolated mode on the raw original
producer file and exposed its existing module-root path prerequisite (`No module
named apps`). The production P0 adapter already supplies that root before import.
The final original-owner CLI check uses explicit root bootstrap and `run_module`;
it does not claim the raw standalone file entry was fixed. If raw-file isolated
invocation becomes required, return only that entry bootstrap to the M17 owner;
do not rewrite its algorithm. A smoke fixture initially used an invalid hyphenated
module ID; the validator rejected it. The fixture was corrected to underscores,
with no validator relaxation. Both initial diagnostic logs are retained.

All market inputs in these checks are **SYNTHETIC / SIMULATED**. They are not real
capture, PIT, natural-window or Mac acceptance. Real collection still requires
the original `real_binding` provider root, interpreter/source hashes, verified
universe/state roots and qualified future input. No remaining missing package was
observed in the tested P0/M17 isolated chain; the complete M01–M18 runtime and
external provider closure are not claimed here. No V4, live configuration,
credentials, security settings, trading, merge or force push was touched.

## Reproduction from an extracted full source tree

Use Python 3.14+ and install only the committed runtime lock into a new environment:

```sh
UV_PROJECT_ENVIRONMENT=/absolute/new-env uv sync --project /absolute/v5/V5 \
  --python /absolute/python3.14 --frozen --no-install-project --no-dev
/absolute/new-env/bin/python -I -B /absolute/v5/V5/tests/test_runtime_dependencies.py -v
/absolute/new-env/bin/python -I -B \
  /absolute/v5/handoffs/P0/cloud-m17-dependencies-20261014/verify_cli.py /absolute/v5
```

The supported deliverable remains the full source bundle, not a standalone wheel
that omits contracts/vendor/source-owner resources. `verify_cli.py` uses temporary
marked roots, explicitly synthetic test inputs and a transient loopback listener.
Complete modified files are in the source tree; `FILES.json` records their hashes
and the attached logs. `VERIFICATION.json` records scope and check counts.

# V5 Testing and Maintenance Guide

This guide standardizes test discovery and reporting. It does not assert that any command has been run on the current integration snapshot.

## 1. Pin the source before testing

Record the exact commit and tree under test. For the current documented integration snapshot:

- Branch: `dev/v5-main-integration-20261012`
- Commit: `01d93717905813705732161d4d79062ae5af2d99`
- Tree: `29e4de722ccf35bb789ba29ad32c883ce9df8adb`

If the branch has moved, test the newly resolved full commit SHA and report it; do not copy the old SHA into a new receipt.

## 2. Backend Python

Requirements are declared in `V5/pyproject.toml` and `V5/uv.lock`. Use Python 3.14 as declared by the project. In an isolated checkout:

```bash
python3.14 --version
uv sync --project V5 --locked
uv run --project V5 --with pytest --locked python -m pytest V5/tests
```

If the package runner cannot resolve the optional test runner with the locked project, do not edit the lockfile just to run tests; use a separate disposable test environment and record that environment difference explicitly.

Useful focused commands:

```bash
PYTHONPATH=V5/src:V5/tests uv run --project V5 --with pytest --locked \
  python -m pytest -q V5/tests/test_daily_dispatch.py V5/tests/test_daily_manager_assembly.py

PYTHONPATH=V5/src:V5/tests uv run --project V5 --with pytest --locked \
  python -m pytest -q V5/tests/test_m18_daily_publication.py V5/tests/test_m18_v2_read_process.py
```

These commands exercise bounded contracts only. They do not prove real-provider capture, live service deployment, natural scheduler execution or all-module acceptance.

## 3. Frontend

Run from `frontend/` and preserve the committed lockfile:

```bash
npm ci
npm test
npm run typecheck
npm run build
npm run test:p0
```

Do not run `npm install` as a substitute for `npm ci` in a reproducibility check. Do not update `package-lock.json` unless dependency changes are intended and separately reviewed.

## 4. Cross-module checks

Run root-level integration checks separately from unit suites:

```bash
python -m pytest -q integration_tests
```

The repository also contains `tests/` at the root. Inspect its test imports and source paths before adding it to a broad command; don't silently assume all root tests target the same runtime.

## 5. Required receipt format

For every executed command, record:

- Repository, branch and full commit SHA.
- OS/architecture and Python/Node/package-manager versions.
- Dependency lockfile SHA and whether installation used locked mode.
- Exact command and working directory.
- Start/end timestamp with timezone and exit code.
- Passed, failed, skipped and deselected counts.
- Log path and SHA-256; preserve raw logs as immutable evidence.
- Whether the run used fixtures, synthetic clock/provider, manual recovery or real sources.
- Explicit NOT_RUN rows for native visual, real input, natural run, deployment and rollback when not performed.

## 6. Suggested CI split

Keep CI small and scoped at first:

1. Backend contract/unit checks for changed Python owners and shared infrastructure.
2. Frontend test, typecheck and build for changed frontend files.
3. Integration tests for changes to run ledger, module API, daily dispatcher, manager assembly/publication or source contracts.
4. Full regression as a separate gate before a release candidate, not a replacement for focused tests.

A green unit/contract job must never be represented as production acceptance. Do not weaken or delete a failing assertion to make CI green.

## 7. Repository cleanup safeguards

Before moving or deleting any file:

1. Search all source manifests, PINs, imports, scripts, tests, workflows and receipt references.
2. Compare Git blob SHA as well as path; equal filenames do not prove equal content.
3. If a source is frozen or PIN-bound, create a new versioned source and update the relevant owner manifest under a narrow review; never edit the frozen bytes in place.
4. Preserve before/after identity and rollback map.
5. Run focused tests, relevant integration tests and cold-read checks after the move.
6. If a file is only a historical receipt or rejected candidate, keep it in place unless an archive migration has explicit, tested path mapping.

## 8. Inventory consistency check

A standard-library audit verifies that the pinned source inventory and duplicate-blob groups still match the exact Git tree:

```bash
python V5/tools/audit_repository_inventory.py --repo . --commit 01d93717905813705732161d4d79062ae5af2d99
```

The corresponding GitHub Actions workflow runs on pull requests that touch architecture inventory/docs or the audit script. It validates source inventory only; it does not run product tests.

## 9. Known exclusions

- The 2026-10-15 stopped-task checkpoint of 24 uncommitted files is not in the fixed integration source manifest. Do not reconstruct it from summaries.
- The 2026-10-17 M18 plan-window patch is a separate Draft PR and is not part of the documented integration commit.
- This documentation pass has not run product tests, changed runtime code, merged PRs or deployed services.

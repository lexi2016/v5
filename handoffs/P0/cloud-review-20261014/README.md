# Independent review fixes and finite source-package checks

Base: `bc11b542bbe83be5a3abc7756f93d0010dbfae46` on the existing
`dev/v5-main-integration-20261012` branch. This is a Linux cloud-only candidate.
No live release, Mac/Windows, real provider, credentials, trading, merge or force
push is involved. M01–M18 / P0–P5 scope and acceptance counts remain unchanged.

## Independent review and fixes

Two read-only reviewers independently checked M04 identity/read safety and P0
source startup/resource completeness, then reviewed the resulting fixes.

| Finding | Disposition |
|---|---|
| P0 child could execute a valid old timestamp `.pyc` while health returned the current source SHA | Fixed: a fresh cache prefix is installed before importing module API and retained for the managed service lifetime. Source and existing pyc remain unchanged. Clean first-round archives contained no pyc; the flaw was reuse after cache contamination/upgrade. |
| Inherited stop sent SIGTERM to any saved PID, including an unrelated process after PID reuse | Fixed in tested Linux path: open pidfd before checking HTTP health PID/module/config identity, signal that handle, wait for exit, then remove runtime identity. Unverified live processes are preserved and rejected. |
| Inherited blocking readline defeated the startup deadline | Fixed with bounded select/read, bounded READY parsing, owned-child termination/reaping on failure and retained stderr diagnostic log. |
| Inherited validate accepted invalid module API config | Fixed using the existing module API validator; no owner execution. Three registration tests now use valid marked API fixtures. |
| M04 read of RELEASE.json could block on FIFO before its subprocess timeout | Fixed with nonblocking/no-follow open, fstat regular-file/size validation and before/after file identity. Applied to initial/final manifest reads and every manifest member; SHA checks remain unchanged. |
| Reviewer found FD leak introduced by the new validate call | Fixed and regression-tested: close the returned root FD immediately. |
| Reviewer found exited-but-unreaped PID blocked recovery | Fixed and regression-tested: pidfd readiness proves the process exited, allowing safe identity cleanup without HTTP. |

Start/stop also serialize through a local runtime lock and write child config and
runtime identity atomically. Concurrent starts retain one owned process. These are
lifecycle changes only; no strategy, data contract, qualification or PIT gate changed.

M04 bridge is now an explicitly derived P0 wrapper. It is **no longer claimed
byte-identical** to the M04 page_bridge file. The external fixed M04 package remains
unchanged at `0bb46df890d4b1a57fcc17982a9800cac2f18146`, RELEASE SHA
`2bafef714a5d35352d54ff8a4d2dde0898fb1fb2ce48e71b3a0eafc4108828de`.
The independent M04 reviewer verified its RELEASE and all 503 source members with
the new reader; no 54-test full rerun was needed.

## Actual checks

- Red evidence: seven initial safety cases failed before repair; subsequent FD and
  exited-child findings each failed their focused regression before repair.
- Final targeted Python run: **28 passed**, comprising safety, finite package
  check, source lifecycle, managed-process tests and two impacted registration cases.
- Ordinary multi-root M04 HTTP regression: **1 passed**, synthetic inputs only;
  old/new selection, reversed roots, missing date, original body/reference, read-only
  method refusal, unselected-root tamper and unchanged archive SHA/mtime.
- Independent reviewer reruns: M04 malformed-package tests **3 passed**; P0 FD and
  exited-child fixes **2 passed**. These overlap the targeted suite, not extra coverage counts.
- No frontend changes; no rerun of earlier 63/164 frontend or full 54 M04 tests.

Original red logs, final results, review dispositions and source hashes are attached.
All fixture inputs remain explicitly synthetic. These are not new Mac acceptance,
real capture, native visual, natural or complete module results.

## Reusable package check

From outside a complete extracted source tree, with its declared Python/dependencies:

```sh
env -u PYTHONPATH "$PY" -I -B /absolute/v5/V5/run_shadow.py package-check
```

This new read-only command verifies exactly these existing manifests under
`V5/contracts`: m04_readonly_runtime, m06_readonly_runtime, m07_runtime,
m08_readonly_runtime, m09_readonly_runtime, m10_readonly_runtime, m11_runtime,
m12_runtime, m16_readonly_runtime, source_owner_runtime (all `.json`).
It validates safe regular resource paths, byte counts and SHA256; reports manifest
hashes; and observes current Python plus installed versions/origins against the
unchanged `uv.lock`. It does not install anything or execute owners.

Actual result: **MATCH, 593 entry references, 591 unique files**, all ten manifests;
Python 3.14.7 compatible, installed declared lock dependencies MATCH. The difference
is an unchanged M08 manifest listing the same namespace file three times with the
same identity. Those references are checked, not silently rewritten. For an explicit
resource-only check, use `--resources-only`; dependencies then report NOT_RUN.

Output always retains `complete_release_verified=false`, `owner_execution=NOT_RUN`,
`business_verified=false`, `natural_verified=false`. MATCH means only the enumerated
resources and declared dependencies match, not that every module's imports are closed.

## Confirmed remaining packaging gap

The pre-existing test
`test_p0_close_recapture_registration.py::RegistrationTests::test_previous_source_dispatch_real_process_cold_reuse_and_pool_corruption`
failed identically in the original bc11 source archive and the working tree:
`OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY`. A bounded diagnostic found the exact cause:

```text
daily_close_recapture_owner.py::_process
  -> vendor/close_discovery_baseline/ops/materialize_manager_close_discovery.py:26
  -> apps/api/v35_api/manager_workbench_router.py:17
  -> ModuleNotFoundError: No module named 'fastapi'
```

The root pyproject and uv.lock declare no FastAPI. This is an inherited dependency
declaration gap, not an uninstalled declared dependency, a source hash failure, or a
fixture date problem. Failure occurs before the synthetic collector executes.
The lock and original producer are not guessed or rewritten here. The next M17
packaging increment must obtain its original dependency contract, complete the
declared closure and rerun this exact path; adding FastAPI alone is not yet proven
sufficient. The diagnostic and baseline/current failure logs are preserved.

## Recovery and limits

- Continue using `run_shadow.py runtime validate/start/status/stop` with a new,
  independent marked data root and unchanged config, as in the prior handoff.
- On failed startup, inspect `module_api.stderr.log`; no runtime identity is committed.
  Do not remove a claim or rerun a business owner to fix a server startup failure.
- `RUNTIME_PROCESS_IDENTITY_UNVERIFIED` preserves the unrelated/unconfirmed process
  and identity. `RUNTIME_STOP_UNCONFIRMED` preserves identity after the bounded stop
  wait; a long read may still be winding down. Recheck status and stop after exit.
- Linux pidfd prevents the health-to-signal PID reuse race. The POSIX fallback uses
  health checks and normal signals and retains that race; it is not claimed verified
  on Mac. No blanket cross-platform safety or full P5 independence claim is made.
- Earlier M04/M14 live-publication denials remain in force. No such action was retried.
- Full release composition, all module import closures, dependency contracts,
  scheduler/recovery/rollback and natural multi-day acceptance remain open.

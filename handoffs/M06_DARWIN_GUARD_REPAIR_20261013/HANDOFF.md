# M06 Darwin deadline-guard repair

## Evidence and root cause

The failed candidate is `5eddebf5c6ecf530ece3fdb31a054b56bf2f1d57`. Its Mac feedback `bdef77a421f840c795b986896b4f4203e890aefd` records 89 executed, 85 passed, four guard failures and one teardown error. That candidate was not deployed.

The one finite diagnostic in `9b73e0fcd29d200fa3f6376187bae7b5432ece3f`, `handoffs/P0/feedback/mac-darwin-owned-groups-20261013/`, confirms on the actual HK02 runtime:

- A live session leader supports getpgid/getsid, and its owned group accepted SIGTERM.
- An exited, unreaped leader remains visible as Z in the original group but getpgid/getsid return ESRCH. Its live child/grandchild group still accepted SIGTERM.
- A zombie-only group returned EPERM on SIGTERM; final wait succeeded. All three groups were empty after wait.

The diagnostic used SIGTERM, not SIGKILL. It neither proves every EPERM harmless nor authorizes permission changes. The candidate tests must verify the guard's real SIGKILL cleanup on Mac.

Apple's fixed [getpgid implementation](https://github.com/apple-oss-distributions/xnu/blob/xnu-12377.1.9/bsd/kern/kern_prot.c#L207-L226) uses the live PID lookup. The [exit path](https://github.com/apple-oss-distributions/xnu/blob/xnu-12377.1.9/bsd/kern/kern_exit.c#L1944-L1948) removes zombies from that lookup. [killpg1](https://github.com/apple-oss-distributions/xnu/blob/xnu-12377.1.9/bsd/kern/kern_sig.c#L1606-L1624) excludes zombies and can return EPERM with no signalable members; [MAC rejection](https://github.com/apple-oss-distributions/xnu/blob/xnu-12377.1.9/bsd/kern/kern_sig.c#L347-L355) can also produce denial. No sandbox failure is inferred from errno alone.

The old guard placed getpgid and killpg before its drain/reap try/finally. Thus the expected Darwin zombie ESRCH skipped both group cleanup and leader reaping. The fixture had the same early-exception teardown problem.

## Small repair

Only `V5/src/v5_shadow/m06_deadline_process.py` and its test change. Cleanup verifies that the fresh-session leader is still this call's unreaped direct child with waitid/WNOWAIT. A live leader still requires the expected PGID; an ESRCH race requires a second exited-child observation. An exited leader does not require the live-only getpgid lookup. The unreaped leader still pins the ID; no signal occurs after reap.

All identity/signal/probe steps now sit inside bounded drain/reap finally handling. EPERM/ESRCH on signalling are tolerated only after independent group inspection positively shows every member is a zombie. A live member, missing anchor or failed inspection remains UNKNOWN. There is no alternate-PID signal, retry with increased permission, or other-group fallback. The exception retains the original deadline/leak reason if cleanup itself is unconfirmed.

Fixtures have finite five-second writer lifetimes and always attempt wait/pipe close even after a signal error. Real heartbeat assertions and the unrelated sentinel remain. Two new platform-API regressions failed before the fix; a third negative case proves a denied signal to real live writers cannot be treated as an empty group. Fault injection affects only named syscalls in those tests, not owner outputs or heartbeat checks.

Actual UTC deadline, monotonic timeout, the 1.5-second cleanup observation budget, UNKNOWN handling, both ledgers and current-success publication behavior are unchanged. No owner/model/reader/config/other-lane/frontend files change.

## Verification and Mac application

Cloud focused result: 15/15 passed, zero skips, ResourceWarning treated as error; see cloud-tests.txt. The repaired candidate is NOT_RUN on Mac at publication. Prior 85 unrelated passes are not reported as freshly rerun.

1. Materialize this fixed commit into the existing isolated Mac candidate, preserving the old publication and all live services. Verify source-closure.json against its four paths before and after. For a minimal overlay onto the previously verified 5edde candidate, replace only the two changed product/test files and retain the unchanged init/digests. No dependency install is required.
2. Use the already approved HK02 interpreter and task-local TMPDIR:

```sh
PYTHONPATH=V5/src:V5/tests PYTHONDONTWRITEBYTECODE=1 TMPDIR="$TASK_TMP" \
  "$HK02_PYTHON" -B -W error::ResourceWarning -m unittest test_m06_deadline_process -v
```

3. Expect 15 executions, zero failures/errors/skips; verify finite child/grandchild heartbeats stop, unrelated sentinel survives, and leaders are reaped. Record exact output and read-only residual check. No manual signals to older or unproven PIDs.
4. Return feedback on the same development branch. Do not enable scheduling, change active bindings, deploy, invoke real model/provider, or rerun the previous 85 unrelated cases as part of this guard-only acceptance.

The old 158-file evening closure is historical evidence for 5edde, not a hash manifest for the changed guard. This handoff supplies the complete four-file guard-test closure and an explicit two-file delta; all other source and parallel module files are inherited unchanged by the repair commit.

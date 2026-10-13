# Mac 5eddebf evening delivery acceptance: FAIL, no deployment

Fixed candidate 5eddebf5c6ecf530ece3fdb31a054b56bf2f1d57. Used exact handoff command in existing HK02 environment with ResourceWarning treated as error, task-isolated TMPDIR and synthetic fixtures. No dependency installation or local product/test edits. No repeat run.

Executed 2026-10-13T04:08:37.916272Z–04:09:14.262096Z; wall36.342s, unittest36.182s; exit1. 89 tests ran,85 passed,4 test cases failed; one failed case additionally produced a cleanup ERROR. Zero skipped.

All failed cases are in test_m06_deadline_process.M06DeadlineProcessTests:

- test_exceptional_inspection_timeout_still_reaps_and_stops_writers: child/grandchild heartbeat sizes grew from [12,10] to [32,29] after attempted cleanup. This is observed continued writing, not merely a message mismatch.
- test_late_completion_is_unknown_even_after_owner_exits: DEADLINE_EXPIRED was replaced by M06_EXECUTION_OUTCOME_UNKNOWN:CLEANUP_NOT_CONFIRMED:ProcessLookupError, failing expected OUTCOME_UNKNOWN.*DEADLINE. Additional cleanup_owned line69 raised PermissionError [Errno1] Operation not permitted from os.killpg(proc.pid,SIGKILL). Final Popen destructor warned subprocess70109 still running.
- test_parent_success_with_closed_pipe_writer_is_unknown: DESCENDANT_LEAK replaced by CLEANUP_NOT_CONFIRMED:ProcessLookupError, failing expected DESCENDANT.
- test_parent_success_with_inherited_pipe_writer_is_unknown: same cleanup confirmation failure and message mismatch.

Exact sanitized stacks and every case result are in tests.txt. Product trace locations include run_bounded lines175/177; fixture assertions91,133,138,161,170 and cleanup69. PermissionError's root cause is not established. No approval-review rejection occurred; no system permissions were changed. Return to the original author for Mac cleanup correction, without locally patching code or weakening the acceptance criteria.

The ordinary real child/grandchild deadline and unrelated-sentinel survival case passed, but does not override the failing cases. Original-owner synthetic existing-pool evening mapping, dual ledgers, reader/reuse and focused legacy regressions passed. No real model/collection/snapshot/natural run.

Post-run read-only process check at2026-10-13T04:09:59.814459Z found no writer command using this task's deadline-test directory and no warned PID70109; no manual kill issued. Later absence does not erase test-time heartbeat growth or cleanup ERROR.

158 files match fixed remote Git blobs and before/after source-closure SHA2567c50df1697f5e46e82cc91358d150c007b0d4526b37fa3600d8fd70c321f500a. All50 source_owners/m06 paths listed in that closure also equal accepted f157 bytes. 91 protected files remain SHA/size/mtime identical; listener PIDs unchanged on8873,8910,54777,54778,54779,54780,62116,65413,63668,64303,62906,55753,62870.

NOT_RUN: live-receipt/frozen-asset snapshot admission, real snapshot, real model/provider, deployment, scheduler enablement and natural verification. Active backend/binding, V4 and M04 preview remain unchanged. Window ends, budget and owner-compatibility cutoff policy were not inferred.

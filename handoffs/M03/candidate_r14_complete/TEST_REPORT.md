# M03 R14 actual verification

## Environment and result

- Interpreter: Python 3.12.14, Linux/POSIX, standard library only.
- Complete offline command (variables denote absolute isolated paths):

```sh
M03_FIXED_SOURCE="$FIXED_SOURCE" python -B "$WORK/V5/tests/run_m03_offline_suite.py"
```

- Final result: **48 tests passed, exit 0**. This includes 30 new chain/reader behaviors, all 10 original collector tests, and all 8 original transport tests.
- All 63 original source files were checked against fixed SHA256, bytes and Git blob before implementation. SHA256/bytes were checked again after the suite; none changed. The original loader independently verifies all 48 owner files in actual child executions.
- Forward `git apply --check` and apply produced exact after bytes. Genuine reverse `git apply --check` and apply restored exact before bytes and absence of new files. Both patch checks/applications exited 0.

## What actually ran

- Public default `run_us_source`, real fresh owner worker, independent default reader child, original store validation, stable source-to-snapshot copy and binding publication/readback.
- Original successful synthetic provider script: 5 RSS responses, 1 quote response, no direct fallback, 33 original quote records and 24 original mapping rows. The script denies real socket connect/DNS/sendto; the source and reader paths preserve the exact three artifact bytes.
- Qualified source reuse and existing binding revalidation. No implicit collection on absence.
- Each payload, receipt and manifest contract tamper; each snapshot physical-SHA change, including whitespace-only changes; invalid marker; symlink, overlap and alternate-code-root rejection.
- Wrong session/phase/date/cutoff, naive timestamps, ambiguous same-session captures, valid empty READY_EMPTY and original PRE_OPEN NOT_DUE behavior.
- Original historical producer/store path and research-only identity, including its distinct payload/receipt paths.
- Explicit collection gate/argv, nonzero collector diagnostics, zero-with-no-source, timeout, and actual cold original main with test-only Proxy transport followed by the real reader. The cold collector receives the real original CLI arguments; only its test bootstrap installs the original offline Proxy/Direct/clock seam. This does not count as a successful real network provider run.
- Source mutation during copy; changed source against an immutable snapshot; two concurrent default chain child processes publishing one identical binding; no leftover `.tmp`; failure preserving existing successful binding bytes.
- Fresh reader nonzero diagnostics, malformed JSON, wrong envelope/payload type, timeout and actual read-only artifact equality.
- Full binding request, version and source-reference revalidation from disk.

## Failures found, reproduced and fixed

1. R11 initially failed the new default-chain assertion because `run_us_source` did not exist; R13 reader was then incorporated into the complete file rather than replacing it.
2. A real original-producer CANNOT_CONFIRM update between initial READY admission and copying was incorrectly bound by the first implementation. The failing regression was observed. Qualification is now rechecked before snapshot writes and at binding construction; selected payload identity is checked across copying. The regression now passes and no rejected snapshot root is created.
3. A reader could load a different supplied code tree. An actual alternate-code-tree test first failed, then passed after the reader checked the controlled V5 source identity before import.
4. An imported orchestrator could claim a later modified disk SHA. A copied-code-tree regression first reproduced this; import-time SHA and preflight/finally checks now reject the change.

5. The original historical reader returns None for an orphan payload, receipt or manifest entry. A regression first demonstrated that these malformed sources could reach the explicit collector gate. The orchestration layer now independently proves absence and rejects each orphan with M03_SOURCE_INCOMPLETE before collection; the original owner is unchanged.

The original unmodified generic discovery command was also run. `test_cloud_us_collector.CloudUSCollectorTests.setUpClass` failed because the historical assembler uses `git show` on the V4 owner commit in a non-git isolated tree. This was not hidden or counted as a pass. The supplied offline runner substitutes only this assembly setup with the already published, hash-verified owner. All original test method bodies subsequently ran unchanged and passed. A temporary PRE_OPEN test-clock fixture error was corrected to use the original `fetched_at` test seam; the actual PRE_OPEN behavior then passed.

## Deliberately not claimed

- Actual remote provider requests / real network capture: **NOT_RUN**.
- Mac isolated acceptance: **NOT_RUN here**; the parent schedules it separately.
- Scheduler, gateway, M15 consumption and preview-page integration: **NOT_RUN / outside this candidate's shared-file scope**; see integration request.
- Natural daily continuation, production deployment or trading: **NOT_RUN**. No orders, credential access, expanded security permissions, main or V4 changes occurred.

The source chain is implemented and executable. Offline success is not a claim of live provider, Mac, API, UI or natural-run success.

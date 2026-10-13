# M06 current-pointer outcome diagnosis

Disabled candidate; Mac narrow verification required before activation.

## Exact defect and minimal fix

At base `66b3d7b87789b432d12a9365b6add035017a8326`,
`daily_tick.py:116–117` caught every promotion exception and returned
`CURRENT_SUCCESS_UNCHANGED_READBACK_FAILED`. But
`p0_hk_preselection.py:574–575` performs atomic `_write` before reading back;
`run_ledger.py:70–76` can raise on directory fsync after os.replace has already
committed the pointer. The previous status asserted something not known.

Only `V5/src/v5_shadow/daily_tick.py` changes. Promotion exceptions now return:
- status: `CURRENT_SUCCESS_UPDATE_OUTCOME_UNKNOWN`
- reason: exception class, without private paths/artifacts
- action_required: `READ_ONLY_VERIFY_CURRENT_AND_BOTH_LEDGERS_NO_OWNER_RETRY`

The compact CLI log also exposes this action as `current_success_action`.
No publication, rollback, retry, ledger, owner, reader, deadline or CAS logic
changes. The exception class is conservative even if failure happened before
replace: code does not guess which side of the atomic update was reached.
Do not roll back a possibly valid new pointer, delete state, or invoke the owner
again. Independently read current and both ledgers using the existing readers.

Existing ordinary failure, CAS mismatch and late-promotion paths still return
their explicit unchanged/not-promoted statuses. UNKNOWN from dispatch also does
not imply a RUNNING ledger: an exception after finish_run may leave SUCCEEDED.
Read actual records rather than making recovery decisions from a status label.

## Evidence

Two RED assertions first reproduced the old false UNCHANGED result after real
replace. The new test uses actual fixed original owner/cold readers and two
ledgers over a synthetic 100-row source pool, with faults only at the filesystem
boundary: directory fsync after replace, and pointer readback after replace.
Both prove the newly written pointer remains present and independently valid,
the original/P0 successes remain intact, and a later tick reuses success with
one total owner invocation. No real model/provider was run.

Final narrow run: 4 PASS, 0 skipped/errors, exit 0, 100.435 seconds: two new tests,
old CAS/late/normal-failure preservation, and original-owner unknown/no restart.
See red.txt, tests.txt, report.json. No prior 19/24/15/85 suite repeat.

## Mac verification

Use the existing HK02 environment and a separate fixed candidate, preserving
active services and old source bindings. Verify source-closure.json (164 files,
raw file SHA-256 recorded in report.json); all inherited bytes match the base.
Only daily_tick.py is a runtime delta. Do not overlay into an already frozen
execution, since code identity is intentionally part of the immutable binding.

Set an isolated existing task TMPDIR. From candidate repository root:

```sh
PYTHONPATH=V5/src:V5/tests PYTHONDONTWRITEBYTECODE=1 "$EXISTING_HK02_PYTHON" -B -W error::ResourceWarning -m unittest \
  test_m06_current_update_outcome \
  test_m06_daily_cycle.M06DailyCycleTests.test_cas_and_late_promotion_preserve_pointer_without_new_owner \
  test_m06_evening_cycle.M06EveningCycleTests.test_evening_unknown_after_original_owner_does_not_restart_or_promote -v
```

Two actual-clock synthetic tests require a supported HK session day; report any
skip rather than claiming natural success. Follow ACTIVATION_CHECKLIST.md only
after Mac verification and the parent's activation instruction. This commit
does not install, enable, invoke or deploy any real daily workload.

Final verification inherited M16 commit `257ca6425c4d489e09430605ee82bf22a4e02da8`,
including its unchanged main_registry.py and module_api.py. Both are retained
closure dependencies, not modified runtime files in this fix.

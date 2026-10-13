# Existing M06 user launchd activation checklist

Operator plan only. This delivery has not activated anything. Use this commit's
fixed candidate after its narrow Mac tests, with the previously verified HK02
environment. Preserve V4 and all existing preview services. No sudo, privilege,
security/privacy change, credentials or dependency installation is needed.

## 1. Confirm lifecycle and prevent a second instance

`daily_tick.py` performs one tick then exits; `main_runtime start` only launches
the read-only API. The existing `launchd_contract` renders a periodic invocation,
not an installation. No full-tick process lock exists. M06 has separate seal,
freeze, claim and current-CAS locks; they prevent duplicate same-identity owner
calls, not concurrent preparation by two unrelated launchers.

On the Mac first read `man launchctl` and `man launchd.plist` for the installed
version. In particular confirm periodic same-job non-overlap and enable/disable
semantics. One job/label in one domain is the serialization boundary; a second
label/domain or a direct shell invocation is outside it. Do not run hand ticks
in parallel or use kickstart -k to replace an in-flight tick.

Resolve these variables from verified local identities, not examples:

```sh
DOMAIN="gui/$(id -u)"
LABEL="com.lexi.v5.daily.candidate"
TARGET="$DOMAIN/$LABEL"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
# PYTHON = verified existing venv launch path (do not replace with base realpath)
# SCRIPT = absolute fixed candidate V5/src/v5_shadow/daily_tick.py
# CONFIG = absolute approved local run configuration
```

Read-only preflight:
- `launchctl print "$DOMAIN"` must confirm the intended logged-in user domain.
- `launchctl print "$TARGET"` and `launchctl print-disabled "$DOMAIN"`.
- Check the exact same label in readable user/UID and system domains too, without
  sudo. If inspection is denied, report the exact limit; do not bypass it.
- Inspect existing V5 launch definitions and scoped process commands for this
  exact script/config pair, including other labels, wrappers, previous schedulers
  or manual ticks. An idle scheduler may have no PID; ps alone is insufficient.
- If the label or script/config already exists, verify ownership/arguments and
  reuse that exact job or stop for reconciliation. Never install a second copy,
  remove an unknown job or touch V4. No automatic fallback to another domain.

## 2. Configuration, fixed paths and dates

Preserve a copy/hash of the disabled draft. For the approved active copy only:
`daily.enabled`, `daily.hk_preselection.enabled`, and
`daily.hk_preselection_daily.enabled` change false -> true.
Both flat daily objects and the current nested daily configuration are supported.
Keep the other verified values unchanged:

- NATURAL; REUSE_VERIFIED_OR_GENERATE_IF_ABSENT
- CLOSE_TO_NEXT_HK_SESSION_V1
- full and half windows both 17:30–18:30 Hong Kong time
- execution_budget_seconds=1200; timeout_seconds=600
- owner_contract_cutoff_time=09:00
- DAY_SLOT_UUID_V1 discovery; dispatch_slot=1720;
  lane_receipt_relative=hk-{signal_date}.json; no exact dispatcher locator
- Original store/assets/dispatcher/lane roots and verified Python/venv pins
- Separate marked snapshot/delivery/bundle/P0-ledger/private-output roots;
  original roots remain untouched. Preserve these paths across ticks/restarts.
- Dedicated M06 bundle root contains no other-lane jobs or explicit duplicate
  M06 bundle. Do not use the historical D12 snapshot/delivery as D13 input.

No dated request, cutoff, completion time or hash is manually generated in this
configuration. A date in a task-directory's name is not itself a data filter;
the input locator templates and original roots must remain day-independent.

Actual `calendar_day(..., evening=True)` read-only results from the fixed owner:
D13->D14, D14->D15, D15->D16, D16->D20. Each tick gets today's Hong Kong date in
`daily_tick.tick`; `prepare_daily_candidate` calls `calendar_day`, which uses the
pinned original 2026 HK securities calendar. The same configuration therefore
constructs D14 signal/scheduled and D15 target tomorrow. New target-specific seals
and bundles are created; old files remain unchanged. No daily config rewrite or
new constructor is needed. Missing next session/year returns UNKNOWN: 20261231
and 20270104 are not supported automatically. Do not invent a new year's calendar.

## 3. Render and load only the existing user job

Render to an owned staging file with the existing command:

```sh
"$PYTHON" -I -B "$SCRIPT" --config "$CONFIG" --render-launchd --python "$PYTHON"
```

Check exact ProgramArguments: Python, -I, -B, absolute SCRIPT, --config, absolute
CONFIG. Keep Label fixed, StartInterval=300, RunAtLoad=false, ProcessType=Background.
The renderer emits Disabled=true. The approved active plist must use Disabled=false
and the actual launchd disabled override must be checked separately. No KeepAlive,
new wrapper, custom polling daemon or system LaunchDaemon is needed.

StandardOutPath/StandardErrorPath may point to existing owned task log paths;
TMPDIR may name its existing isolated writable directory. Do not rely on shell
startup or PYTHONPATH under -I. Do not publish private paths or log content.

After provenance/duplicate checks and approval, put the verified plist at PLIST
without overwriting an unrelated file. For a genuinely not-yet-loaded job, the
normal user-domain sequence, verified against the Mac's own man pages, is:

```sh
/usr/bin/plutil -lint "$PLIST"
/bin/launchctl enable "$TARGET"
/bin/launchctl bootstrap "$DOMAIN" "$PLIST"
/bin/launchctl print-disabled "$DOMAIN"
/bin/launchctl print "$TARGET"
```

A loaded verified matching job does not need another bootstrap. On any error,
read actual service state before deciding what happened; do not blindly retry,
change label/domain or escalate. Do not kickstart/start or set RunAtLoad=true to
manufacture automatic-trigger evidence.

## 4. Observe schedule, then separately establish daily success

StartInterval is a trigger interval, not an exact 17:30 wall-clock reservation.
While the same job is active, do not accumulate manual replacement invocations.
The Mac must remain usable during the slot; no power-setting change is included.
The user-agent's login/session lifecycle must be recorded. Do not claim execution
through logout, sleep or shutdown. Late wake does not authorize backfill.

Before 17:30, record two different automatic runs from the registered job using
its actual runs/exit state, log entries and observation timestamps. They should
show WAITING_M06_WINDOW (the lane status, not a model result). This proves timer
activation only; it is not successful daily input/model/business acceptance.

Within the slot, missing original D inputs remains WAITING without a claim.
After delivery/inspection and again before owner admission, at least 1200 seconds
must remain. This is a minimum remaining-budget gate, not a 1200-second total
tick watchdog. Because checks take time, a new claim must ordinarily be admitted
before 18:10. Each subprocess gets at most 600 seconds and the remaining D18:30
wall-clock deadline. Hard execution cutoff remains D18:30 through inspect/invoke/
freshread/finish/CAS. Next-session 09:00 is owner compatibility only, never PIT
admission or an extension of the actual deadline.

For a real success record exact D->next-session dates, original receipt/hash
chain, real seal completion, selected production mode, frozen request identity,
both original and P0 ledger successes, independent fresh reader, and successful
current CAS/readback. CLI exit 0 / DISPATCH_ATTEMPT_ONLY is not business success;
its natural_verified=false remains unchanged. A current-update UNKNOWN requires
read-only pointer and both-ledger inspection. Never roll back a possibly valid
pointer, delete locks/ledger/frozen state or retry owner due to this diagnosis.

## 5. Stop safely and retain a reversible installation

An already running tick has read its config. To prevent future business work:
1. Atomically set the three config enabled switches false, preserving all other
   values and the approved active backup. Existing work still needs to finish.
2. `launchctl disable "$TARGET"`; verify its persistent disabled state. Do not
   assume this alone terminates a loaded job or changes its active invocation.
3. Let the existing tick and owned children finish under their guard. Observe
   their identities and ledger state; do not kill, kickstart -k or immediately
   bootout an active process. If unresolved, stop for explicit diagnosis.
4. Only when no active instance remains: `launchctl bootout "$TARGET"`.
5. Verify the exact service is absent, scoped script/config processes are absent,
   and disabled state is retained. Keep plist, backups, logs, snapshots, frozen
   bundles, both ledgers and products; do not delete anything to reset identity.

To restore, repeat exact job/identity/duplicate checks, restore the same approved
active fields, enable and bootstrap the same target. RUNNING/UNKNOWN records are
not cleared. Same-identity success is independently read and reused, not computed
again. Unsupported inputs, source/config/code drift or expired window stay blocked.

## 6. Page binding remains a separate narrow step

Keep today's fixed committed_reference until the first real daily success is
verified. Scheduler activation does not update the existing API binding.
After that success, separately deploy the already supported current binding:
bound_root, current_success_ledger_root, python_executable, python_sha256 and the
verified python_venv. It is mutually exclusive with fixed committed_reference.
Keep old binding bytes for rollback; test the exact reference/dates/rows on the
preview API and preserve every other module. Do not switch to an empty new current
root prematurely and describe HTTP200 as data success.

References: fixed daily_tick.py, p0_hk_preselection.py:279–307/464–544,
run_ledger.py, m06_input_delivery.py, and
[Apple launchd guide](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html).
The Mac's installed manual/state is authoritative for launchctl command behavior.

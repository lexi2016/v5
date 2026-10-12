# M17 standalone late registration candidate

## Exact scope and status

Base module HEAD: 5a2cbd69e8a3eb99fc2167f0d2a41638b5af2c03.
Original late producer revision: fe0a1890ebe59b476af6c8a0e1878fca059c24f4.
This candidate adds a runnable independent late adapter/CLI and a single ledger lane
admission. It does not modify the deployed P0 branch, main, the page, the shared
ledger, daily_tick, daily_dispatch, general worker, M18, or V4.

The fixed 24-file late producer/reader closure is already at repository
V5/vendor/close_discovery_baseline. The adapter verifies its complete pinned
manifest before execution and again in each fresh worker. The 7 unchanged P0
imports bundled under after/V5/src are a runnable narrow test scaffold, copied
byte-for-byte from the fixed p0_integration_base. Do not overlay these scaffold
copies onto a newer deployed P0 tree. The forward patch modifies only the four
application files listed in FILE_MANIFEST.json.

## Public registration and invocation

- bind_close_recapture_owner(config) returns invoke, code_sha256,
  config_sha256, dependency_sha256. invoke is the concrete module function.
- run_close_recapture_owner(request, ledger_run_id) returns exactly the original
  five receipt fields. Caller owns its original ledger claim/finish lifecycle.
- run_close_recapture_daily(request, ledger_root, binding) is the standalone
  claim -> producer process -> new reader/pool process -> finish -> read_run path.
- CLI: python -I -B integration_candidates/M17/after/V5/src/v5_shadow/daily_close_recapture_owner.py
  --request /absolute/request.json --ledger-root /absolute/private-ledger
  (one shell command; no shell commands or import callbacks are accepted in JSON).

Use the same existing Python interpreter that has FastAPI available; no software
is installed. Clock/quote input is accepted only in an explicitly SIMULATED
request. A real request is terminal BLOCKED / REAL_COLLECTOR_NOT_BOUND without
starting an owner worker. This delivery is not authorization to turn collection on.

## Request / config contract

Request has config, source_trade_date, research_cutoff, execution_kind. SIMULATED
also requires simulation with clocks and result. result contains only status,
rows, requested_code_count, completed_code_count, no_data_codes, cannot_confirm.
These feed the original owner's narrow clock / pytdx_collector ports; they are
not fabricated owner artifacts or fabricated ledger success returns.

config has exactly capture_mode=PYTDX_LATE_OBSERVATION, owner_root, python,
state_root, universe_root, source_manifest, timeout_seconds (1..120). All roots
and the existing interpreter are absolute. state_root must be isolated from both
owner_root and universe_root and contain .v5-m17-close-root with exact bytes
v5.m17.simulated-close.v1 followed by newline. The original private ledger marker
is .v5-daily-run-ledger with v5.daily-run-ledger.v1 followed by newline. Nothing
initializes or enables production roots implicitly. Tests create only temp roots.

The ledger identity is exactly lane, target_date, input_sha256, research_cutoff,
code_sha256, config_sha256, dependency_sha256. target_date is source_trade_date;
plan_trade_date is obtained from the original artifact, never used as a substitute
ledger date. Full request bytes participate in input identity. The pool run ID is
separate from the ledger run ID. Four-file hashes are read from original bytes,
including the receipt's own byte digest.

## Sole-integrator scheduling request (disabled / NOT_BOUND)

Register manager_close_recapture independently from a_stage. Its invoke is
run_close_recapture_owner, not the standalone daily wrapper (avoid double claim).
Use the source date and real request cutoff, an explicitly approved evening slot
and deadline, and max_attempts=1. Never inherit the 08:00–08:45 default slot.

The fixed daily_dispatch still admits only announcement/us_mapping/rebound and
requires target_date=today. daily_tick has no late binding. Therefore adding the
ledger name or passing this binding does NOT complete P0 global scheduling. A
separate integrator change must account for current/previous source session and
an explicitly bound evening deadline before enabling invocation. The original
owner still enforces HK_CONNECT full session, current or previous applicable
session, and 15:55:05 lower bound for same-day invocation. Its minute observation
window is [15:46:00,15:55:05), and actual capture/available times remain separate.
No deadline is guessed here and no historical arbitrary backfill is introduced.
Stage failure must neither gate this late job nor be upgraded by its success.

## Readback, UI, and safety

The original reader verifies READY/PARTIAL and the new process independently
rereads the exact D1 pool. SUCCEEDED means only original simulated publication
and cold-read closure; owner PARTIAL, OBSERVATION_ONLY, currency/unit UNKNOWN,
non-final-close cannot_confirm, received_not_historical_1530, and all four safety
flags remain in the receipt/reference. natural_verified always remains false.

REUSED_SUCCESS starts only a cold reader, never a producer. A changed pool,
corrupt receipt/overlay or invalid saved product returns BLOCKED_SAVED_PRODUCT_INVALID
without replacing prior ledger success or files. RUNNING, lost worker, timeout,
invalid envelope or mismatched product remain outcome unknown and never retry.
Python audit guards block network and extra subprocesses before owner import;
reader guards reject writes. These are Python guards, not OS sandbox evidence.

No GET endpoint is registered here. The existing original read contract remains
/api/v4/manager/workbench-research with exact date/market/slot, and CLOSE_RECAPTURE
must stay separate from 1530. A future GET integration must use read_run and only
fresh reader readback; do not route GET to run_close_recapture_daily, which claims.
Preserve X-V5-Workspace-Access: READ_ONLY. Page/M18 publication is NOT_RUN.

## 1530 and tracking remain explicitly blocked

The runtime 24-file late closure is not a complete 1530 closure. It lacks these
actual deferred-import files: infrastructure/manager_close_attempt.py,
domains/manager_condition_evidence.py, v4/manager_research/workspace_plan.py,
v4/manager_research/workspace_projection.py (plus their full transitive closure).
Those are source-assembly gaps, not merely four data inputs. Original copies are
in the source/supplement handoff tree, not bound into this runtime owner root.
1530 further requires verified universe owner, pre-capture history, snapshot
attestation, news owner and complete prior evidence at the real window. No 1530
input is invented and no tracking/new-catalyst or natural-run acceptance is claimed.

## Application and rollback

Apply forward.patch only to the exact fixed P0 ledger preimage (sha in manifest)
in a disposable checkout first. A changed current P0 ledger requires an integrator
rebase, not overwrite. Original V5/vendor/close_discovery_baseline is a prerequisite.
reverse.patch restores the exact ledger preimage and removes only these added
candidate files in that disposable checkout; it never removes runtime evidence.
For any eventual production binding, disable only the M17 new invocation first,
retain attempts and all four files, and restore only its prior binding. No worker
or scheduler is enabled by this commit.

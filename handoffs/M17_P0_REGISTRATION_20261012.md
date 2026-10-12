# M17 late: existing P0 execution registration

## Scope and baseline

Base integration HEAD: bae6184b99d289f394b0cc3c3d5370e9f3155715.
M17 source: 6f1a70d9ce5cc1dd759347a3ff6fad7a0c06117f.
This is the minimal existing P0 execution/configuration registration increment.
It addresses BLOCKED_NO_M17_EXECUTION_REGISTRATION_CONTRACT, not production
activation or natural-run acceptance. No real binding/output root was created.

The existing main_runtime.tick -> daily_tick -> daily_dispatch -> run_ledger
claim/finish/read_run path remains the sole scheduling and ledger path. The new
p0_close_recapture helper validates the binding and connects that path to the
original concrete run_close_recapture_owner callable. It creates no scheduler,
shared ledger, callback loader, UI page, or producer for GET.

READY in the static registry means a callable adapter exists, never current
inputs or natural operation. Runtime config independently reports DISABLED,
BLOCKED_M17_REGISTRATION, or BOUND_NOT_NATURALLY_VERIFIED. Global lifecycle and
other lanes remain available if M17 is unbound/invalid.

## Exact imported source

Reused unchanged from the fixed M17 source:
- V5/vendor/close_discovery_baseline: tree 3b892f56c67939f04f3f61352fe59284872732c8 (24 source files).
- daily_close_recapture_owner.py: blob 3976ce1b9900f298e21a6bd9f5d92d70e3a80108.
- close_recapture_source_manifest.json: blob 4574d6ffd9f33a2a838609f21e5965d94f396003.
- test_daily_close_recapture_owner.py: blob 47a322db8e26d2f78b29933cb1cb195b9d62dc9c, imported only for fixture helpers; its old tests were NOT rerun.

No candidate scaffold overlays module_api, api_gateway, composition, contracts,
module_artifacts, or the current P0 ledger. The ledger change adds only the
original manager_close_recapture lane, retaining all other six lane names and
all seven identity fields / five receipt fields / durable locking semantics.
Original collector/probe, 64-code batches, 180-second probe timeout, 420-second
real owner maximum, independent fresh reader, external D1 pool, observed/source
and plan dates, failure preservation, and unknown-no-retry behavior are retained.

## Disabled default and explicit binding

The example daily config has close_recapture = {"enabled": false}. There is no
implicit activation. Absent config also means DISABLED. An enabled registration
must contain exactly these four fields:
- enabled: true
- execution_kind: SIMULATED or OWNER_VERIFIED, explicitly chosen
- config: the original M17 owner config, including capture_mode, owner_root,
  existing python, state_root, universe_root, source_manifest, timeout_seconds;
  OWNER_VERIFIED additionally requires the complete original real_binding
- pool_reference: the complete original external D1 pool identity

The original REAL_BINDING.md at fixed source commit defines the runtime binary
and pytdx.exhq hashes, provider root, real vs simulated markers and runtime
checks. Missing/invalid real evidence is BLOCKED before claim or owner capture.
The real code path can pass; it is not permanently rejected. The new test uses
only a synthetic read-only runtime-boundary result to establish this fact.
It does not prove a live Mac runtime or a real collection.

pool_reference contains owner, role, trade_date, signal_date, source_id, run_id,
artifact_ref, artifact_sha256, manifest_ref, manifest_sha256, receipt_ref,
receipt_sha256, captured_at, row_count. The three original file byte hashes and
metadata must agree. No reference is inferred from unrelated snapshots. Original
owner schema/CSV admission remains authoritative; the independent reader's pool
must equal this bound identity before success can finish. Pool/reference drift
fails closed, including a change between preflight and readback.

## Existing bundle and slots

Keep the existing exact-current-date bundle file/marker. Add a job with:
- lane: manager_close_recapture
- scheduled_at and deadline: explicit timezone-aware approved slot endpoints
- max_attempts: exactly 1
- owner_request: the original M17 request, with config matching registration,
  source_trade_date matching pool_reference.trade_date, research_cutoff and
  execution_kind; SIMULATED alone additionally includes simulation

This job bypasses default_slots entirely. No morning 08:00-08:45 default is
inherited and no new evening deadline is invented. The selected slot starts on
the current bundle day; before it is WAITING_TIME and at/after its deadline is
MISSED_WINDOW_NO_BACKFILL. A new approved current bundle is required on another
day. Slot approval/activation on Mac remains separate.

The ledger target_date is the source_trade_date, not bundle date or plan date.
Admission uses the original frozen HK Connect calendar: source must be current
or the immediately previous session, and must be FULL_TRADING_DAY. Same-day
source requires >=15:55:05. Calendar bytes are verified before parser execution.
No arbitrary historical backfill or old payload labeled current natural evidence.
The original owner rechecks eligibility and its unchanged observation window.

The dispatcher claims once and invokes run_close_recapture_owner (never the
standalone daily wrapper, so there is no double claim). Success requires original
producer -> independent reader -> external pool -> four file hashes -> five-field
finish -> ledger readback. Reused success starts only a fresh reader, compares
saved files and pool, and never restarts the producer. Invalid saved data retains
its prior success. Lost/failed calls with uncertain effects retain RUNNING and
never retry automatically; known terminal failure also has no second attempt.

## Directed verification

Cloud existing Python 3.13 / existing FastAPI; no dependency installation.
- NEW P0 registration suite: 18 PASS, 0 FAIL, 0 SKIP.
- Existing daily_dispatch compatibility suite: 5 PASS, 0 FAIL, 0 SKIP.
- Original M17 simulated 17, vendor 4, and real-path 9 PASS/1 SKIP suites: NOT RERUN.
- Full repository suite, real market collection, Mac natural triggers, deployment:
  NOT RUN in this increment.

The new 18 include original subprocess simulated producer/fresh-reader through
P0 tick, exact source-date identity, cold reuse/corruption preservation, no-retry,
all six original ledger lanes, M17-config changes preserving unrelated owner success identities, config/mode/root/pool gates, source drift,
metadata mismatch, terminal failure, and no permanently blocked real branch.
All fixture products are SYNTHETIC, never current market evidence. Red-to-green
logs and sanitized final logs are under handoffs/evidence/m17-p0-registration-20261012.

### Mac isolated command

Use a fresh isolated checkout of the fixed delivered commit and set
VERIFIED_EXISTING_PYTHON to the already verified existing interpreter with
FastAPI (no installation, no private absolute path published here). From repo root:

    "$VERIFIED_EXISTING_PYTHON" -I -B V5/tests/test_p0_close_recapture_registration.py

Expected: NEW P0 18 tests, OK. This does not run the old M17 17-test suite even
though it imports that file's fixture function. Do not run discovery over M17.
No active binding is needed: tests create only temporary synthetic roots.

For the existing five dispatcher controls only, when requested:

    "$VERIFIED_EXISTING_PYTHON" -I -B -c 'import sys, unittest; sys.path[:0] = ["V5/src", "V5/tests"]; r = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName("test_daily_dispatch")); raise SystemExit(not r.wasSuccessful())'

## Preview/other modules and deferred work

Frontend tree remains 9d913c4a6e55c295dce39fe2848184e15c21afe2. Existing module_api,
read-only GET implementation, source cards, M06/M08/M09/M10 read-only modules,
M13/M14/M15 research, M18 and all existing vendor trees are unchanged. The commit
has no deployment or workflow activation. See preservation.json for exact hashes.
This is a code-tree non-change proof, not a new browser/page acceptance claim.

1530 remains blocked on manager_close_attempt, manager_condition_evidence,
workspace_plan, workspace_projection, their transitive runtime closure and real
inputs. No 1530 expansion, trading, V4 mutation, software installation, credential
access, security-setting change or natural verification is part of this work.

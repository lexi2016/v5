# M06 P0 daily execution bridge, 2026-10-13

## Scope and fixed source

This delivery adds an opt-in executable daily lane to P0. It is not a rerun of the earlier 100-row pool acceptance or the old M06 test suite. No real provider, model deserialization, collection, deployment, natural scheduling, trade, credentials, V4 change, or dependency installation was performed.

- P0 parent: `5b32a0916fbe486bbf7a33c1ce6ad9e3e4618e51`, private `lexi2016/v5`, `dev/v5-main-integration-20261012`.
- Original M06: `08ed9de9ddb5fd2c62eb1762df2f6106464d823b`, already present at `V5/source_owners/m06/`. No original owner, algorithm, ledger, source descriptor, or GET reader file is modified.
- Existing original runtime closure: `V5/contracts/m06_readonly_runtime.json`, raw SHA256 `6594ddff403e4ef268662021427ec74dcbc589b57bd2035bc0754dba8a02f303`.
- Admission contract actually read: `ddb07572e7bd24efff2a9624806e2487129d208a/handoffs/M06/daily-integration-admission-20261013/DAILY_INTEGRATION_CONTRACT.md` and `report.json`.

## Actual call chain

`main_runtime.tick` → `daily_tick.tick` explicit `hk_preselection` job → `p0_hk_preselection.prepare_job` → `daily_dispatch.dispatch_due` → P0 claim → isolated `m06_daily_worker` → original `produce_hk02_daily` (including its existing original provider worker when genuinely admitted) → original committed-reference reader → another fresh isolated process invoking that same original reader and original ledger read → P0 receipt validation → P0 finish → exact P0 ledger readback.

The bridge uses the existing `hk_preselection` ledger lane. It does not add a scheduler, rewrite the model, copy the old source tree, or call the producer from any GET route. M06 registration is independent of M17. M06-specific config is excluded from other lanes' config digests, matching the existing M17 isolation convention.

## Two cutoffs and two ledgers

The request has two explicit time fields. They are not interchangeable:

- `admission_cutoff`: the observed input boundary. P0 `identity.research_cutoff` equals this value, never a future value. Original master captured time and, for existing pools, pool captured/finished times must not exceed it.
- `completion_cutoff`: maps only to original M06 `cutoff` and its publication/computation `research_cutoff`. For generation it must be strictly later than admission and the dispatch instant, and no later than the explicit slot deadline. Both fields and slot dates must be the target HK date. The unchanged owner still enforces actual wall-clock generation and source completion checks.

P0 identity hashes the entire explicit request including both cutoffs and all raw source/asset hashes. Its code digest pins the P0 bridge/worker and existing M06 source manifest; its dependency digest includes the original owner's actual runtime/dependency/input computation snapshot. Config has its own digest. These are rechecked before invocation, finish, and saved reuse.

P0's UUID is `p0_ledger_run_id`. The original owner's separate UUID is `m06_ledger_run_id`, under `private_root/.m06-ledger`. The publication computation digest is neither UUID. Each product records all three and the original M06 seven-field computation identity. The original ledger's producer receipt hash must equal the publication's pinned producer receipt hash. Only matching original ledger, committed reference, source identity, original rows, method, and producer/reader semantics can finish P0 success.

P0 `RUNNING` or an unknown invocation result never invokes the owner again for the same identity. Max attempts is fixed at one. Saved success is cold-read again; corruption fails closed. Outside the explicit slot, M06 does not receive the generic unverified saved-state fallback used for other lanes' manager assembly.

## Explicit branch selection

`production_method` is required:

1. `EXISTING_VERIFIED_POOL`: exact pool must exist; strict original consumer validates it. Corrupt/wrong-date pools never fall back to generation. `RECORDED_INPUT_REPLAY` may explicitly use an empty asset inventory; other modes require original frozen asset verification. Success retains `producer_model_weights_reverified=false` and `reader_model_weights_reverified=false`.
2. `GENERATE_IF_ABSENT`: exact pool must truly be absent in the supplied independent input snapshot. Replay mode is forbidden. Original Python/scikit-learn/joblib runtime, parquet availability, full frozen asset closure, PIN, calendar, source/root and time gates remain. The original owner copies declared inputs into its own staging; it never removes a pool to force this branch. A true model result would carry `FROZEN_MODEL_PRODUCER`, producer verification true, consumer verification false.

No branch changes `natural_verified=false` or production/trading safety flags. Synthetic tests retain `fixture_only=true`.

## Parameterized private config

Templates are at:

- `V5/examples/m06_daily_runtime.template.json`
- `V5/examples/m06_daily_bundle.template.json`

They are intentionally disabled and contain placeholders. Fill every placeholder locally, use only existing interpreters, and retain the private configs off GitHub. Bundle filename is the exact HK target date, e.g. `YYYYMMDD.json`. `bundle_root/.v5-daily-bundles` must contain `v5.daily-bundles.v1\n`; P0 ledger marker is `.v5-daily-run-ledger` / `v5.daily-run-ledger.v1\n`; independent M06 output marker is `.v5-shadow-root` / `v5.shadow-root.v1\n`. The bridge does not silently create roots or these markers.

`source_files` contains exact relative paths and raw SHA256 values. Existing branch requires the original exact eight-file pool/master closure. Generation requires the original exact master closure plus `latest.json` if that file exists (even with no target pool). It cannot list old pool files while pretending they are absent. `files` is the complete explicit frozen asset inventory: panel/model pointers/manifests/payloads and every existing optional name pointer, manifest, dictionary and receipt. The original model PIN remains `3b0d5d5239342439cabf25b30012365a64d78839bc3cd4d90bad7be6ff4aaa07`.

For controlled future generation, create a new request and independent output/store identity. Do not reuse the expired `2026-10-12T17:11:34.690550Z` request, delete the existing pool, change the system clock, or claim the original pool is missing. The verified Mac model/panel inputs already exist; no model download is required. Choose a real target-day future completion cutoff that covers actual computation and publication work.

`half_day_bound=true` asserts that the explicitly supplied slot has been checked for the target session; it is not a claim that the old P0 08:00–08:45 default is the original M06 schedule. M06 never inherits that default.

## Mac verification and controlled operation

Use the existing Mac task and an existing interpreter, after checking the fixed delivery SHA and source closure. Do not install dependencies or enable launchd.

Run from the checked-out repository root:

```sh
PYTHONPATH=V5/src:V5/tests "$EXISTING_HK02_PYTHON" -B -m unittest test_p0_hk_preselection_daily
```

The test invokes the fixed original daily owner and cold readers on isolated synthetic CSV input; it never deserializes a model. It patches only P0 calendar observation for historical test fixtures, never the original producer's clock.

Read-only request validation, after locally filling a private config and bundle:

```sh
PYTHONPATH=V5/src "$EXISTING_P0_PYTHON" -B - "$PRIVATE_RUNTIME_CONFIG" "$PRIVATE_DATE_BUNDLE" <<'PY'
import json,sys
from v5_shadow.p0_hk_preselection import prepare_job
config=json.load(open(sys.argv[1]));bundle=json.load(open(sys.argv[2]))
for job in bundle['jobs']:
    if job['lane']=='hk_preselection':
        prepared,binding=prepare_job(job,config['daily']['hk_preselection'],bundle['target_date'])
        print(json.dumps({'status':'PREFLIGHT_ONLY_NO_CLAIM','p0_identity':prepared['identity'],
          'm06_identity':binding['owner_snapshot']['computation_identity'],'natural_verified':False},sort_keys=True))
PY
```

Only for a separately admitted controlled run, set both daily and M06 registration enabled in the private config and execute one tick with the actual clock:

```sh
PYTHONPATH=V5/src "$EXISTING_P0_PYTHON" -B -m v5_shadow.main_runtime tick --config "$PRIVATE_RUNTIME_CONFIG"
```

A missed slot or completion window requires a new legitimate request, not a clock override or automatic retry. Do not repeat the completed `7006c6ab` real existing-pool acceptance as new progress. True frozen-model recomputation and natural daily operation remain NOT_RUN in this delivery. The Mac's existing HK02/pyarrow environment is the next controlled validation boundary.

## Results and rollback

See `verification.json` for exact focused test results and `source-closure.json` for the source closure SHA. Full legacy M06/M17 suites were not rerun. The enabled natural schedule, deployed preview, live data and real model result are not claimed.

Rollback requires disabling this registration or restoring the P0 parent on its development branch through the existing controlled workflow. Preserve all P0/M06 ledger and committed objects, original GET bindings, V4, and unrelated lane configs. Do not delete a RUNNING/unknown state to retry.

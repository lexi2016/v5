# M14 bounded PyTDX history capture candidate

Research-only, private canary acquisition. No original owner, panel, root pointer,
V4 process, order path, credentials, scheduler, GitHub branch, or preview is changed
by this module. `formal_eligibility_verified` and `natural_verified` are always
false. `formal`, `natural`, `production_allowed`, `buy_gate_updated`, and
`orders_sent` are also false.

## Files and frozen identities

- `v5_shadow/rebound_history_capture.py`
  - SHA256 `e1a5fc5dba23dd10c727f002848b38e6d688b98316c99480bbef95fd97c66312`
- `tests/test_rebound_history_capture.py`
  - SHA256 `7d45503f8e06706765bced1199da19ee02749f2885a94f035d8981f44329b142`
- Original collector SHA256, verified before AST extraction:
  `fa7dcbce4ee026b0a02c47220820d0407af183553d3304afcc5db425dce33cbd`
- Original source-manifest SHA256:
  `057a2c453ae562bc94564829dd8f78aba2b303bb7182a0b493fde9d4bedbafcd`
- Existing decoder used in offline compatibility tests, unchanged SHA256:
  `0c6236be65fb52c78b04c124dad90b0d5413c41d78e00bc00d73f1706e1985cc`

## Exact baseline-root layout

`--baseline-root` is a directory containing these two unchanged files:

```
BASELINE_ROOT/
  contracts/rebound_repair_source_manifest.json
  vendor/rebound_repair_baseline/hk_daily_supplement.py
```

The source manifest and source bytes must match the pins above. Runtime does not
import the collector module. It extracts only the original `_canonical`, `_clock`,
and `_connect` AST function nodes, unchanged. No other original executable code
runs. The fixed connector uses `pytdx.exhq.TdxExHq_API`,
`heartbeat=False, auto_retry=False, raise_exception=True`, and exactly
`119.97.142.130:7721` with a 2-second connection timeout. Existing PyTDX is needed
only for explicit live `capture`; do not install dependencies for this candidate.

Paths are traversed with held directory descriptors and `O_NOFOLLOW`. Use physical
paths, including on macOS where `/tmp` can be a symlink; do not substitute a
symlinked baseline or output parent. The output parent must already exist. Each
command requires its own previously absent output leaf, created mode 0700.

## Task contract

`prepare_plan(task, baseline_root=...)` is offline. The task has exactly:

- `schema_version`: `v5.m14_history_capture_task.v1`
- `target_date` and `signal_date`: real compact `YYYYMMDD` dates with target > signal
- `canary_codes`: 1–3 unique explicit ASCII `HK.00000`-format codes
- `keys`: exact unique `{code,date}` objects; every code must be represented,
  each key date must be before signal, at most 120 keys per code
- `expected_panel_sha256`: expected original panel SHA256
- `original_reference`: the real existing M14 four-part reference:
  `run_id` (32 lowercase hex), `artifact_sha256`, `manifest_sha256`, `receipt_sha256`
- `parent_binding`: the original HK02 panel lineage:
  `parent_pointer_sha256`, `parent_manifest_relative`, `parent_manifest_sha256`,
  `parent_panel_relative`, `parent_panel_sha256`

The panel SHA must equal `expected_panel_sha256`. Manifest and panel paths must
share one `panels/<revision>/` directory, ending in `manifest.json` and
`hkconnect_vipdoc_daily_panel.parquet`, respectively. Unknown fields, dynamic
endpoints, custom query limits, cutoff clocks, credentials, and duplicate JSON
keys are rejected.

This module binds the supplied identities but does not load or authenticate
actual owner artifacts or actual panel bytes. The existing owner integration
must compare those bytes/references and validate every requested day against
`rebound_panel_repair._history_window(signal_date)['prior60']` before authorizing
the canary. It must retain the original security-master scope checks. The plan
records `EXISTING_OWNER_PRIOR60_VALIDATION_REQUIRED`; this candidate creates no
new eligibility or repair authority. The parent builds the actual task privately.
No real task reference or real acquired response belongs in source control.

## CLI

There are exactly two actions:

```
PYTHON rebound_history_capture.py plan \
  --task PRIVATE_TASK_JSON \
  --baseline-root BASELINE_ROOT \
  --output-dir NEW_PRIVATE_PLAN_DIR
```

`plan` makes no network connection. It validates and writes one read-only
`plan.json`; its exact file SHA256 is printed. Then, only when explicitly running
the already authorized canary:

```
PYTHON rebound_history_capture.py capture \
  --plan NEW_PRIVATE_PLAN_DIR/plan.json \
  --plan-sha256 EXACT_PRINTED_PLAN_SHA256 \
  --baseline-root BASELINE_ROOT \
  --output-dir DIFFERENT_NEW_PRIVATE_CAPTURE_DIR
```

Live capture uses one connection and one request per explicit code, in task order:
`get_instrument_bars(4, 71, code_without_HK_prefix, 0, 120)`. There is no retry,
second endpoint, pagination, range API, subscription, or credential access.
The callable `capture_plan(..., connector=...)` requires an explicitly injected
connector; only the CLI selects the real original connector by default.

The SDK's own source confirms the native signature
`get_instrument_bars(category, market, code, start=0, count=700)` and forwards
start/count to its parser. This candidate deliberately sets count=120 instead
of the original daily collector's count=6:
https://github.com/rainx/pytdx/blob/master/pytdx/exhq.py#L72

This confirms the supported call shape, not provider availability, complete
history coverage, or any guarantee of exactly 120 returned bars.

## Receipts and existing-decoder compatibility

A capture writes only inside its new directory:

- `plan.json`: bound task and source identities
- `attempt.json`: real capture start, persisted before connection
- `request-000-HK.00000.json`, etc.: one final response/error receipt per attempted
  request, including exact request/hash, full unfiltered native SDK-decoded rows,
  response hash/count, endpoint, source pin, real request-start/acquisition/finish
  clocks, original reference, and parent binding
- `connection.json`: a failed connection receipt, if connection failed
- `result.json`: sources, receipts, errors, missing exact keys, and diagnostics

Each file is created with `O_EXCL|O_NOFOLLOW`, mode 0400, flushed and fsynced. Runs
never reopen or replace a receipt or an existing output directory. This is
append-only-by-application evidence, not an OS immutable-file claim; the OS owner
can still delete files. A killed process or storage failure may leave an attempt
marker without a final result, and must be treated as incomplete, not successful.

Successful receipts have the fields expected by existing
`rebound_raw_repair._record`; `result['sources']` consists of exact
`{relative,sha256,record_pointer}` references with the empty JSON pointer. Call:

```
decode_raw_repair(capture_dir, sources=result['sources'],
                  keys=task['keys'], through_date=task['signal_date'])
```

`source_rows` preserves the entire SDK-decoded response in canonical JSON; this
is not a claim to preserve network packets. Request and response hashes use the
unchanged source canonicalizer. Numeric values are not scaled, traded-volume
units and price basis are not inferred, and no missing key is padded or invented.
Malformed non-JSON/nonfinite responses are failure receipts without a successful
source reference; they cannot be misrepresented as valid response hashes.

Bars newer than the signal date are retained. Their indexes are reported with
`FUTURE_ROWS_AFTER_SIGNAL_KEEP_RAW`; the unchanged decoder is expected to reject
that source. Never delete such rows to manufacture an acceptable source or
backdate capture clocks. A successful fetch is only `CAPTURED`, never owner repair
approval. `repair_ready` stays false; downstream checks remain with the existing
owner and decoder. Even a complete exact-key set establishes neither daily
finality nor formal/natural admission.

## Offline verification performed

Initial candidate contract suite: 11/11 passed. Final complete candidate suite:
18/18 passed. Existing raw-decoder synthetic compatibility suite: 22/22 passed.
No real PyTDX endpoint was contacted; these results do not establish real provider
availability, historical data recovery, or owner/panel publication success.
No full product/runtime suite was run in this cloud-only synthetic scope.

The final tests cover exact one-per-code calls, no retry, fixed SDK constructor
and endpoint, failure receipts, partial runs, exact source/response/file hashes,
actual injected clocks, native number preservation, real decoder compatibility,
future-row retention/blocking, missing/duplicate dates, invalid response types,
nonfinite values, >3 codes, invalid date/key/query/ref bindings, immutable output,
and symlink traversal rejection.

On another machine the tests can read its existing V5 tree using
`V5_HISTORY_TEST_BASELINE_ROOT`. That tree must also include existing `src/v5_shadow`
for the unchanged decoder compatibility imports. No pytdx is imported by tests;
the SDK connection test injects a synthetic module.

```
V5_HISTORY_TEST_BASELINE_ROOT=EXISTING_V5_ROOT PYTHON -m unittest discover \
  -s capture/tests -v
```

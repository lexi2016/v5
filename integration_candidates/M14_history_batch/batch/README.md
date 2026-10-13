# M14 bounded history batch candidate

This is an isolated capture-only extension. It does not publish a repair, modify the original task or parent panel, establish eligibility/units, send orders, change credentials/security settings, or upload response data. The original collector is not copied or imported. Only CLI `capture` selects the original pinned `_connect`.

## Source pins and prerequisites

- `rebound_history_capture.py` from the fixed c52aca canary: `e1a5fc5dba23dd10c727f002848b38e6d688b98316c99480bbef95fd97c66312`
- Original `src/v5_shadow/rebound_raw_repair.py`: `0c6236be65fb52c78b04c124dad90b0d5413c41d78e00bc00d73f1706e1985cc`. Only its unchanged `_record` AST is loaded for successful-receipt validation, with its contract dependencies bound.
- The canary's original source pin and source-manifest pin remain enforced by its unchanged `_baseline` helper. Only its `_canonical`, `_clock`, and `_connect` function ASTs are extracted. Fixed endpoint: `119.97.142.130:7721`; category 4, market 71, offset 0, count 120. No alternate host, reconnect, retries, collector imports, or credentials.
- POSIX Python with existing dependencies; CLI capture requires the original `pytdx` dependency already available. Offline tests use only the standard library plus the pinned source files. No installations.

## Task contract

Exact schema `v5.m14_history_batch_task.v1`:

- `target_date`, `signal_date`: YYYYMMDD; signal precedes target
- `prepared_at`, `valid_until`: aware ISO times, valid for at most two hours; checked before planning/capture/resume and before every new query
- `exact_member_codes`: sorted, unique, complete original member pool, at most 1,000 (the authorized task is 690)
- `exact_member_codes_sha256`: SHA-256 of the canonical sorted member array
- `keys`: sorted unique `{code, date}` entries, at most 20,000, at most 120 per code, every code in the original pool and every date before signal (the authorized original task is 2,574 exact missing keys)
- `keys_sha256`: SHA-256 of that canonical keys array
- `expected_panel_sha256`
- `original_reference`: `run_id`, `artifact_sha256`, `manifest_sha256`, `receipt_sha256`
- `parent_binding`: `parent_pointer_sha256`, `parent_manifest_relative`, `parent_manifest_sha256`, `parent_panel_relative`, `parent_panel_sha256`
- `initial_reuse`: exactly three descriptors for HK.00001, HK.02825, HK.03469. Each descriptor has `code`, absolute `receipt_path`, `receipt_sha256`, absolute `plan_path`, `plan_sha256`.

Canonical JSON uses UTF-8, sorted object keys, compact separators, `ensure_ascii=False`, `allow_nan=False`. SHA values are lower-case hexadecimal.

Each canary receipt is checked against its own original plan SHA and its source/request/response hashes, true capture clocks, original 4-reference identity, parent binding, dates and safety flags. The three canary plans need not share a plan SHA with each other or with the batch plan. A successful response lacking some requested dates is still a successful capture. In particular, HK.03469's missing 10/12 key does not authorize fetching it again.

## Independent current context

Exact schema `v5.m14_history_batch_context.v1` has `target_date`, `signal_date`, `original_reference`, `parent_binding`, `exact_member_codes`, `keys`, and `files`. `files` contains six actual absolute paths:

- `original_artifact`, `original_manifest`, `original_receipt`
- `parent_pointer`, `parent_manifest`, `parent_panel`

The context is prepared independently from the original owner source and actual current parent. It is an identity snapshot, not authority to modify/publish anything. Keep it private. It must not use copied substitutes for the actual current parent files.

Plan, capture and offline resume hash all six actual files, verify the original run/manifest/receipt linkage, target/signal, the five original observation groups (`strict`, `near`, `pending`, `excluded`, `screen_unresolved`) against the exact member pool, original request paths/files against the parent hashes, and current pointer/manifest/panel linkage. The original observation can be `CANNOT_CONFIRM`; this module does not reinterpret it as formal qualification. Keys are computed and fixed by the separate original-owner prior60 preparation; this capture module does not introduce pandas or recompute calendar semantics.

Original JSON evidence has a 16 MiB bound. The panel has a 512 MiB bound and is streamed into SHA-256, never read as JSON or loaded into memory as a whole. Before each query the module checks the context-file hash, all six held initial stat identities, and current pointer bytes SHA. It hashes all six files again before a normal result. Symlinked inputs/directories are rejected.

## Actions and callable API

The three offline/live boundaries are explicit:

- `prepare_plan(task, baseline_root=..., capture_helper=..., context_file=..., clock=None)` is offline.
- `resume_plan(plan, baseline_root=..., capture_helper=..., context_file=..., output_dir=..., clock=None)` is an offline read-only audit. It does not resume network traffic.
- `capture_plan(plan, ..., connector=..., clock=None, monotonic=..., sleep=..., max_calls=1000, max_seconds=900)` creates a fresh capture directory or strictly resumes the same one. The callable requires an explicit connector; tests inject a fake. Only the `capture` CLI chooses the real connector.

CLI examples, with actual verified paths and plan SHA supplied by the owner:

```sh
python rebound_history_batch.py plan \
  --task /private/path/batch-task.json \
  --baseline-root /actual/V5 \
  --capture-helper /actual/c52aca/rebound_history_capture.py \
  --context-file /private/path/context.json \
  --output-dir /private/path/new-plan-directory

python rebound_history_batch.py capture \
  --plan /private/path/new-plan-directory/plan.json \
  --plan-sha256 <exact-raw-plan-file-sha256> \
  --baseline-root /actual/V5 \
  --capture-helper /actual/c52aca/rebound_history_capture.py \
  --context-file /private/path/context.json \
  --output-dir /private/path/new-capture-directory \
  --max-calls 687 --max-seconds 900

python rebound_history_batch.py resume \
  --plan /private/path/new-plan-directory/plan.json \
  --plan-sha256 <same-exact-sha256> \
  --baseline-root /actual/V5 \
  --capture-helper /actual/c52aca/rebound_history_capture.py \
  --context-file /private/path/context.json \
  --output-dir /private/path/new-capture-directory
```

A later explicitly invoked `capture` against the same exact plan, context and output resumes only still-unattempted original missing-key codes. It never revisits a code with an earlier attempt, failure, response, or reused receipt. Do not choose a new directory to bypass a stopped/uncertain attempt. Once the task's validity expires, fail closed; a new explicit task/review is needed. The module does not automatically update time windows or authorize retries.

Each invocation uses at most one connection and at most `max_calls` queries, with at least one second between request starts, including immediate resume. Failed/invalid responses stop that round without reconnecting. A subsequent explicit invocation can process other previously unattempted codes. A connection failure records no per-code attempt. `max_seconds` is the monotonic admission budget; CLI capture also uses a POSIX wall-clock alarm to interrupt stuck operations. On alarm it leaves any STARTED query indeterminate and exits, without beginning a further potentially blocking disconnect. No background network thread is used.

## Checkpoint and evidence behavior

Output creation uses an exclusive new leaf directory; all files are write-once, fsynced, mode 0400. An advisory exclusive directory lock rejects concurrent writers/readers while a writer is active. No JSON file is overwritten.

`plan.json`, `run.json`, and the three byte-identical complete `reuse-HK.*.json` source records are the first hash-linked checkpoint. Every round, connection result, per-code attempt, response, and round result is recorded in an append-only SHA-linked journal. An attempt is persisted and checkpointed before making the query. Receipts preserve the whole native SDK-decoded source response, exact request, response/request hash, endpoint/source pin, original identities, and real request/acquired/finished clocks. They preserve original trade/volume fields without conversion, zero-fill, filtering, or fabricated bars. This is not TCP-packet capture.

If an interruption leaves an attempt with no receipt, `uncertain_codes` reports it with blocker `UNKNOWN_UNCERTAIN` and no retry. Other unattempted codes can proceed on explicit capture. A successful but incomplete response keeps its missing keys blank. `sources` uses the original exact `{relative, sha256, record_pointer: ""}` format for whole source records; failed/invalid responses are listed in `receipts` but excluded from `sources`.

Counters distinguish:

- `existing_receipt_count`: source receipts already present when this invocation began, including initial reuse
- `receipt_count`: current total successful/failed response records, including reuse
- `successful_receipt_count`: current successful source count
- `reused_count`: exactly three preserved canary receipts
- `attempted_count`: cumulative newly attempted batch codes, including failed/indeterminate
- `invocation_attempted_count`: queries begun by this invocation
- `remaining_query_count`: codes still never attempted

`CAPTURED` means every planned code has a successful source response; it does not mean all requested keys exist. `exact_keys_present` reports missing-key completeness separately and `repair_ready` is always false. `formal`, `natural`, `production_allowed`, `buy_gate_updated`, and `orders_sent` remain false.

Fail-closed limits: a kill during the tiny file-write/checkpoint interval can leave a partial or orphan file; the next audit rejects the directory without connecting. It does not guess, delete, rewrite, or reissue anything. The operator must preserve that evidence and decide next steps. Hash chains/read-only modes are integrity checks, not protection against an OS owner rewriting or deleting the entire directory and every hash. No cross-directory global retry authority is implied. No automatic repair request is generated, even when every capture succeeds; known source-window numeric/volume inconsistencies require separate diagnosis.

## Offline verification

```sh
PYTHONDONTWRITEBYTECODE=1 M14_CAPTURE_HELPER="$M14_CAPTURE_HELPER" \
  M14_BASELINE_ROOT="$M14_BASELINE_ROOT" "$PY_FUTU" \
  -m unittest discover -s "$CAND/batch/tests" -v
```

Tests use synthetic original-owner evidence, the real unchanged source helper/record validator, and injected fake API/clock/monotonic/sleep. They cover exact pool/keys/three reuse, the incomplete HK.03469 success, whole raw rows, caps, throttled resume, interrupted/failed/no-result no-retry, source/receipt/context tampering, stale tasks and live context, cross-run identity, symlink rejection, concurrent lock rejection, no alternate endpoint, hard deadline, and offline resume. No live connector was used during development.

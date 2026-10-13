# M14 Futu single-window diagnostic canary

This is a complete, standalone bounded wrapper, not an owner repair, data admission,
full-pool collector, or trading path. Development and verification used synthetic
responses only. This V5 candidate is published on the authorized M14 development
branch. No Futu connection, market request, Mac operation, credential read,
dependency installation, or V4 mutation was performed during development.
Actual Futu capture remains NOT_RUN until the Mac executor performs the command.

## Exact scope

- Explicit 1–3 unique codes, restricted to `HK.00001 HK.00376 HK.01191`.
- One original quote context at `127.0.0.1:11111`.
- On that same context: before quota, at most one history request per selected
  code, after quota, then close. At least one second between API call starts.
- Same-connection before quota must succeed and its current detail must explicitly
  contain every selected code. Otherwise zero history requests. Historical quota
  receipts and the reported 96 used / 4 remaining are not used as live authority.
- Actual quota response shape is `(ret, (used_quota, remain_quota, detail_list))`.
  Nonnegative integer counts and list details are required. Detail length/duplicates
  and malformed entries are reported as anomalies; detail length is not assumed to
  equal used quota. Selected-code membership is checked against valid detail rows.
- Request dates: `2026-07-20` through `2026-10-13`; target `20261014`.
- Exact parameters: `code`, `start`, `end`, `ktype=KLType.K_DAY`,
  `autype=AuType.NONE`, `fields=[KL_FIELD.ALL]`, `max_count=100`,
  `page_req_key=None`, `extended_time=False`, `session=Session.NONE`.
- No application retry, pagination, subscription, trade object, or order method.
  A nonempty next-page key is preserved and marks that code `PARTIAL`; it is never
  followed. A history exception or error response stops subsequent history calls.
  A single after-quota read is still attempted as cleanup when the deadline allows.
- A separate stdlib spawn supervisor kills the acquisition process at its 60-second
  deadline, including SDK import, connection, requests, and close. OS process kill
  and final local evidence writing can finish just after that deadline. No worker
  is allowed a grace period for more acquisition. Hard timeout can prevent the
  after-quota observation; its absence is explicitly reported, never inferred.

## Run

Use the existing Python with the existing Futu SDK. Nothing is installed. Copy the
whole directory with `pinned/` intact; source files are SHA-checked before execution.
Python 3.11+ is required by the unchanged original calendar (`StrEnum`).
Set `PY_FUTU` to the already-existing SDK interpreter and `CAND` to the absolute
path of this candidate directory. Do not install or upgrade dependencies.

Read-only argument/source/calendar verification, without importing Futu or making
any connection:

```sh
PYTHONDONTWRITEBYTECODE=1 "$PY_FUTU" "$CAND/futu_history_canary.py" args \
  --codes HK.00001 HK.00376 HK.01191
```

Explicit live capture, only in the already-authorized existing environment:

```sh
PYTHONDONTWRITEBYTECODE=1 "$PY_FUTU" "$CAND/futu_history_canary.py" capture \
  --codes HK.00001 HK.00376 HK.01191 \
  --output-dir /ABSOLUTE/EXISTING/PHYSICAL/PARENT/futu-canary-UNIQUE-NEW-LEAF
```

The output parent must exist and every component must be a physical directory, not
any symlink. On macOS, `/tmp` is commonly a symlink: use an existing physical path.
The new leaf must not already exist, even if empty. Existing files are never
replaced. File names are fixed safe relative names, written with `O_EXCL`,
`O_NOFOLLOW`, mode `0400`, and fsync. The leaf is `0700`. This is append-only evidence,
not a claim that the OS owner cannot delete its own files.

The existing Futu SDK can write its own logs to stdout/stderr. Do not treat the
entire console stream as a single JSON document. Read the fixed output files
`summary.json` and `supervisor.json` with the ordinary JSON reader; also inspect
per-code receipts for diagnostics and raw next-page keys. The supervisor result
is authoritative for a hard timeout even if a summary had already been written.

`--source-root` is optional and defaults to adjacent `pinned/`. It cannot change
any source SHA. Scope/date/endpoint/maximum-call settings are fixed, not CLI knobs.

Synthetic suite, stdlib only:

```sh
PYTHONDONTWRITEBYTECODE=1 "$PY_FUTU" -m unittest discover -s "$CAND/tests" -v
```

## Original function/source reuse

`pinned/safe_io.py` is the exact original bounded capture helper SHA
`e1a5fc5dba23dd10c727f002848b38e6d688b98316c99480bbef95fd97c66312`.
Only its safe-I/O/canonical JSON AST function definitions execute. Its PyTDX
connector is never extracted, imported, called, or used as a Futu connector.

`pinned/repair.py` is SHA
`9f547b8d2307b847b3d284eff2e5914d715283a06eb427044074b34bdc3114da`.
The unchanged `repair._history_window(signal_date)` AST executes with a read-only
source-provider shim returning the independently pinned original calendar and
workspace-plan bytes. The unchanged `trade_date` AST comes from pinned contracts.
The calendar source and JSON bytes are unchanged from that original source route.
No owner module is imported or built, and no owner write/pointer path is reached.
This produces the original 60 prior HK-security sessions (from 20260720 to
20261012) plus signal 20261013: 61 required dates. It is not a weekday calendar,
not a southbound-connect calendar, and it includes 20260925.

The actual quote constructor reuses the unchanged `_default_context` AST from:
`lexi2016/v4@74478a0e62be215c8527ccc9a14b89b51042d014`,
`handoff/v4-running-source-20261005/canonical/infrastructure/futu_quote_provider.py`,
SHA `b8ce38b6e255a0048a0028024c6c5bb376762e906a2dc4602c32dcb1ac91faae`.
Only its existing `import futu` and `OpenQuoteContext(host="127.0.0.1",port=11111)`
body executes; the provider class and subscription paths do not execute.

The previous five-code script is only documented as a parameter-contract source:
`/Users/lexi/Documents/Codex/2026-10-09/task/rebound-owner-ebe5944e/evidence/capture_five_once.py`,
SHA `e5006ec6f1f7e4b327d67e51005123a9ad58caff596854e7d501d413292cc05a`.
Its body was not provided. This wrapper does not claim to copy its capture function.
The prior documentation uses 2026-07-15 to 2026-10-08; this approved wrapper uses
the explicit new full-window dates above. All source pins appear in `plan.json`.

## Evidence and interpretation

Outputs include a supervisor attempt, plan, capture attempt, connection identity,
a durable per-call attempt written before each query, whole quota responses,
per-code response receipts, summary, and supervisor completion. Every available
response includes request/response SHA-256 and actual UTC started/acquired/finished
times. Connection metadata includes the installed SDK version and the SHA-256 of
the actual installed `OpenQuoteContext` source file, read without credentials.

The entire SDK-decoded return is preserved, including return code, all DataFrame
columns in original order, original dtype labels, index, every row/cell, and page
key. This is not a wire-level packet capture. JSON uses Python's round-trip float
encoding, never pandas' precision-limited `to_json`. NaN and infinities are explicit
typed cell objects with IEEE-754 bytes, not illegal JSON tokens or replacement zero.
Bytes are typed hex. Finite values are not rounded, scaled, projected or corrected.

Diagnostics report exact original-calendar missing dates, duplicate dates,
20260925 presence, original raw OHLC for HK.00376/20260831 and
HK.01191/20260724, strict positive finite OHLC plus full high/low envelope validity,
and finite nonnegative volume. Zero volume remains valid. Invalid rows are kept
unchanged. The prior side's concrete OHLC values were not supplied, so comparison
reports `ORIGINAL_VALUES_NOT_PROVIDED; ORIGINAL_DECODER_OHLC_INVALID_OPEN_GT_HIGH`.
No fabricated numeric comparison or repair is made.

`CAPTURED` means all requested single pages returned and were recorded, and both
quota observations passed their shape/membership gates. It does not mean the
rows passed every diagnostic, the quota balance stayed unchanged, or the source
is admitted. Inspect code diagnostics and exact before/after quota deltas.
Concurrent quota changes are not attributed to this wrapper. Four remaining
slots are not described as full-pool capacity; full-pool authorization is false.
A successful capture never asserts repair readiness.

Source contract: `FUTU_HISTORY_K_DAY_AUTYPE_NONE_SDK_NATIVE`.
`AuType.NONE` is explicitly unadjusted; the SDK's default QFQ is not relied on.
Volume/turnover/price scales remain 1. Volume unit and currency equivalence are not
proven. The history field page says Volume, not SHARES. No PyTDX/VIPDOC unit mixing,
owner admission, historical PIT claim, provider-finality attestation, or promotion
is performed. Formal, natural, production, orders, and buy flags remain false.

Official parameter/field references:
- https://openapi.futunn.com/futu-api-doc/en/quote/request-history-kline.html
- https://openapi.futunn.com/futu-api-doc/en/quote/get-history-kl-quota.html
- https://openapi.futunn.com/futu-api-doc/quote/request-history-kline.html
- https://openapi.futunn.com/futu-api-doc/quote/get-history-kl-quota.html

The official documentation is evidence for the API contract, not proof of installed
SDK version, today's quota, present connection, units, authorization, or returned data.

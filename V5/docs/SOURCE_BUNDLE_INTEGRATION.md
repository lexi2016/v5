# P0 M01/M02/M03/M05 source-bundle integration

Fixed P0 base: b52334941e712dc642f78eae8970349332969aac.
This is a one-shot invocation and read-only status publication, not a new
scheduler or a new numbered module. Existing M13/M14/M15/M18 owners, manager
same-run pages, HK tick, scoring, frozen descriptors and production gates stay
unchanged. The original source entrypoints run in separate pinned processes.

Accepted candidates: M01 02cefc41aadb4358cb8485b71858ae5d6b903a56 (44 Mac pass),
M02 ce6cddce1ef52d63241f0d8192b6adcc118ea750 (107 pass, 1 full-real-request skip),
M03 3c3ed922cb653bb8ef411bce685b1d47fb322f02 (48 pass), and
M05 2c5d1eb2c9572469bf04ad86fd61e92ee8674fe8 (52 pass).

## Minimal boundary

- M01, M02 and M03 byte-preserved code lives under source_owners/<owner>.
  Its source map records exact origin, Git blob, SHA256 and bytes. M02's older
  private API helpers never replace P0 module_api or the shared native reader.
- M05 adds its three accepted entry files and reuses P0's identical 49 runtime
  dependencies. It does not generate V192 input or permits.
- Registry source identities are m01_a_source, m02_hk_source, m03_us_source,
  m05_a_preselection. M15 remains us_mapping.
- A source bundle always returns all four module slots. Absent requests, missing
  inputs, original rejection and owner-specific statuses remain distinguishable.
  No source result is promoted to natural, formal, historical-PIT or trading success.
- M03 network capture is disabled and rejected if requested here. It may read
  pre-admitted recorded input and create its original immutable snapshot/binding.
- M05 requires an existing verified V192 lane, M01 binding whose generation date
  matches signal_date and selector SHA matches original V192 provenance, and a
  separately provided strict gate context. Missing/rejected prerequisites stop
  before publisher invocation. No old manifest is repaired or relabelled.

## Real input limits at implementation time

The observed M01 generation is historical, not proof of the current day. The
observed V192 run was rejected by its original reader for missing current oracle
provenance; no new source is manufactured. An existing US POST_CLOSE triplet can
be replayed from a newly admitted V5 private root with unchanged original bytes,
identity and timestamps. This is RECORDED_INPUT_REPLAY, never a new natural capture.
No private machine paths, source payloads or credentials are stored in this repo.

## Delivery sequence

1. Run the source-bundle unit/integration tests on the fixed code using existing
   dependencies. Do not rerun or alter the already accepted algorithms.
2. Mac creates an explicit private bundle file and independent module-output root.
3. Run the one-shot source-bundle command with source capture disabled.
4. Serve its saved result through the existing read-only module_api and add only
   the source-bundle route to the gateway configuration. Keep manager route and
   generation binding unchanged.
5. Main page's source panel fetches only this saved status. HTTP GET never invokes
   a source producer, collector, writer or the daily tick.

## Explicit local configuration and invocation

Use the existing Python environment. No installation, provider access, automatic
collection, scheduler registration or old-root marker change is required.
All paths below are placeholders for **new V5-owned private paths**, outside the
code tree, mutually disjoint. Do not commit filled-in configuration or results.

A `request.json` for the first M03 recorded replay:

```json
{
  "schema_version": "v5.source_bundle.request.v1",
  "data_kind": "RECORDED_INPUT_REPLAY",
  "jobs": {
    "M03_US_MARKET": {
      "trade_date": "20261009",
      "capture_phase": "POST_CLOSE",
      "session": "20261009",
      "cutoff": "2026-10-10T10:00:00Z",
      "source_root": "/ABS/V5-PRIVATE/us-recorded-source",
      "snapshot_root": "/ABS/V5-PRIVATE/us-snapshots",
      "binding_root": "/ABS/V5-PRIVATE/us-bindings",
      "allow_network_capture": false
    }
  }
}
```

The source root must already have been initialized/admitted by the original
M03 contract, then filled with the explicitly authorized original triplet bytes.
Do not change capture dates, receipts, manifest or source identity to represent
this as a new capture. The entrypoint initializes only its new output roots using
its unchanged owner protocol. M01, M02 and M05 absent jobs return
`BLOCKED_REQUEST_MISSING`; this does not claim they were tested on real input.

Initialize a **separate new** module-output directory with its original marker
`.v5-module-root`, exactly `v5.module-root.v1:source_bundle\n`. Set `data_root`
to it in a private `source-api.json`:

```json
{
  "schema_version": "v5.module_api.v1",
  "module_id": "source_bundle",
  "release_id": "p0-source-bundle-20261012",
  "data_root": "/ABS/V5-PRIVATE/source-api",
  "routes": ["/api/v5/source-bundle/status"]
}
```

The one-shot `source-runtime.json` uses the same entire API config object under
`publication.config`. It does not require changing the manager lifecycle config:

```json
{
  "source_bundle": {
    "enabled": true,
    "request_file": "/ABS/V5-PRIVATE/request.json",
    "publication": {
      "config": {
        "schema_version": "v5.module_api.v1",
        "module_id": "source_bundle",
        "release_id": "p0-source-bundle-20261012",
        "data_root": "/ABS/V5-PRIVATE/source-api",
        "routes": ["/api/v5/source-bundle/status"]
      },
      "expected_generation": null
    }
  }
}
```

```sh
PYTHONPATH="$CHECKOUT/V5/src" "$PYTHON" -m v5_shadow.main_runtime source-bundle --config "$PRIVATE/source-runtime.json"
PYTHONPATH="$CHECKOUT/V5/src" "$PYTHON" -m v5_shadow.module_process --config "$PRIVATE/source-api.json" --port "$SOURCE_API_PORT"
```

First publication uses `expected_generation: null`. Subsequent publication must
use the exact `generation_sha256` returned by the previous publication. Keep
that result as the caller's CAS anchor; do not overwrite it by guessing current
state. A conflict is a publication failure, never a successful new result.
Omit `publication` for a one-shot invocation without API publication. Omit the
source_bundle config or set enabled=false for `SOURCE_BUNDLE_DISABLED`.

For existing Vite preview, keep `V5_MODULE_API_ORIGIN` unchanged and provide
`V5_SOURCE_API_ORIGIN=http://127.0.0.1:<SOURCE_API_PORT>` on the new preview process.
For a gateway-hosted frontend, add `source_bundle` with a distinct existing-free
loopback port to the gateway module map and only this route:

```json
{"path":"/api/v5/source-bundle/status","module_id":"source_bundle","methods":["GET"]}
```

The added module uses the gateway's existing `port`, `timeout_seconds`,
`max_inflight`, `release_id` config contract. No manager routes, response binding,
source API helpers or scheduled workloads are replaced.

## Other exact job interfaces

- M01 job forwards `private_root`, `source_root`, `generation_pointer`,
  `target_date` to original `create_binding_from_roots`. `private_root` must have
  its original `.v5-shadow-root` marker. Optional `action: "read"` instead accepts
  only `private_root`, `source_root`, `relative`; independently rereads the strict
  formula generation and returns selector SHA. The bound generation date is not
  silently changed to today's target date.
- M02 job forwards original `build_binding` keyword fields: `private_root`,
  `asset_binding`, `membership_root`, `membership_files`, `native_binding`,
  `target_date`, `signal_date`, `eligibility_source_date`, `cutoff`, optional
  `require_pit`. It independently calls `read_binding` using the returned external
  `receiptHash`. The output root requires the accepted private-mode marker.
  Three-reader proof files must be explicitly supplied; no empty success fallback.
  Its result remains `SOURCE_IDENTITY_ONLY`, with temporal/PIT gaps untouched.
- M05 job forwards the accepted `build_m05_daily` business arguments, plus
  `m01_binding` containing the M01 **read** arguments above. `request` has exactly
  `target_date`, `signal_date`, `data_kind`, `lanes`. Each original lane has `kind`,
  `input_root`, `paths`, `files`. `write_gate_context` has the five required keys
  `control_dir`, `expected_permit_sha256`, `expected_owner_id`,
  `expected_release_sha256`, `expected_root`. No permit is created here.
  Existing lane bytes and original V192 oracle provenance are independently read
  before any daily publication; M01 selector/date must match. A missing gate is
  `BLOCKED_WRITE_GATE_REQUIRED`; a present request rejected by the original
  source reader is `SOURCE_REJECTED`. Do not provide fake gate identities just
  to get past this check. M07 stays `WAIT_INTEGRATION` in the original daily result.

## Mac acceptance and stopping point

1. Verify the fixed integration commit, owner manifest hashes and recorded input
   triplet SHAs before running. Use the already approved Python interpreter.
2. Run `PYTHONPATH=V5/src "$PYTHON" -m unittest discover -s V5/tests -p test_source_bundle.py -v`.
3. Run the explicit M03 recorded replay request once. Expected positive status is
   `VALIDATED_SOURCE_BINDING` with original `source_status=READY`. Inspect original
   capture/session/date and snapshot/binding readback evidence. Do not call this
   natural capture; all outer safety flags remain false.
4. Compare the three source byte hashes again. Only new output roots may change.
5. GET `/api/v5/source-bundle/status` must exactly equal the saved result; POST
   must return 405. The source service's own READY only means HTTP service ready.
6. Main page shows actual four owner statuses; repeat reads and a disconnected
   source service must clear previous source results and show CANNOT_CONFIRM.
   Existing manager/announcement/rebound/US-mapping same-run views remain intact.
7. Run existing frontend `npm run test:p0`, `npm run typecheck`, `npm run build`
   with installed dependencies. No install needed for this handoff.

This handoff stops at explicit source entrypoints, status publication and preview
readback. New M05 source production, new permits, real collection, natural-day
acceptance and current M01→M05 business closure are separate blocked work.

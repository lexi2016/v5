# M08 immutable read-only API publication

## Added module-local files

- `V5/src/v5_shadow/hk_stage_api.py` (new; prior path ABSENT)
- `V5/tests/test_hk_stage_api.py` (new; prior path ABSENT)
- `integration_candidates/M08/API_READONLY.md` (new; prior path ABSENT)

No changes to `module_api.py`, `module_artifacts.py`, gateway, ledger, scheduler,
shared UI, V4 source, frozen vendors, or source manifests are required by this
adapter. It adds neither a server nor a frontend framework. Activity in this
cloud workspace does not establish a Mac mount or an active preview URL.

## Explicit publication, separate from GET

The producer first commits a private immutable HK run. The publisher receives
its exact reference and calls the independently implemented cold reader:

```python
from v5_shadow.hk_stage_api import publish_hk_stage_response

result = publish_hk_stage_response(
    config, private_hk_store, exact_reference,
    expected_generation=current_module_api_generation,
)
next_module_api_generation = result['generation_sha256']
```

`exact_reference` contains `generation_sha256`, `run_id`, `market`,
`target_date`, `stage_id`, `artifact_sha256`, `manifest_sha256`,
`receipt_sha256`, and `product_sha256`. It must identify one `HK_CONNECT` run;
there is no `latest` lookup or fallback to a different date, stage, or run.

`expected_generation` is the current **module API response generation**, or
`None` only for the first publication. It is distinct from the private HK
product generation inside `exact_reference`. A stale expected head fails with
`GENERATION_CONFLICT`; a bad cold read cannot replace the public head.

The existing module config contract is used unchanged:

```json
{
  "schema_version": "v5.module_api.v1",
  "module_id": "hk_stage",
  "release_id": "ACTUAL_APPROVED_M08_RELEASE",
  "data_root": "/ABSOLUTE/PRIVATE/V5/HK/RESPONSE_ROOT",
  "routes": ["/api/v5/hk-stage-selection"]
}
```

The response root must already have its existing-contract marker
`.v5-module-root` containing `v5.module-root.v1:hk_stage\n`. The cold-reader
store root and the response root are separate inputs; provisioning or mounting
an active root is outside this adapter. The authorized integrator supplies the
actual release, approved roots, gateway route, and available loopback port.
Run the existing server with its existing CLI:

```sh
PYTHONPATH=V5/src python -B -m v5_shadow.module_api --config /approved/hk-api.json --port APPROVED_PORT
```

Published keys require all three exact string query parameters:

`GET /api/v5/hk-stage-selection?date=20261008&stage=STAGE_0930_0935&run_id=EXACT_COMMITTED_RUN`

Date/stage/run switches and refreshes read published immutable response objects.
The server imports no HK producer, reader, or publication adapter; it never
opens the private HK store or calls a selector. Unpublished keys return the
existing service's unavailable result, and POST is rejected. Existing
`activate_generation` provides compare-and-swap response-generation rollback;
this alone is not a code, UI, or private-product rollback.

## Public payload and provenance

`payload.artifact` preserves the full original SelectionStore envelope,
including ordered rows, formulas, scores, reasons, lane/quote evidence,
coverage, missing symbols, and `cannot_confirm`. No recalculation, row sorting,
or conversion of missing evidence into a valid empty result takes place.
`payload.status` mirrors the original `selection_status`; a valid read returns
HTTP 200 even when the business status is `CANNOT_CONFIRM`.

The exact private reference remains in `payload.reference`, with its original
hashes. These hashes identify the private original artifact, not its redacted
public projection. The shared record's `payload_sha256` separately binds the
public bytes. `source_input_sha256` comes from cold-verified provenance.

Local path values are replaced with `[REDACTED_PATH]` throughout public source
identity/evidence, including `active_snapshot_path=...`, nested path fields,
and local paths in diagnostic text. Labels, hashes, error codes, and other
non-path evidence remain. The private envelope is not mutated. Formula
expressions such as `turnover_hkd / circular_market_cap_hkd_yi` are retained.

`data_kind` remains `SYNTHETIC` or `RECORDED_INPUT_REPLAY`, exactly as returned
by the cold reader. `natural_verified` and `formal_admission` remain false;
production, BUY-gate, and order flags must be false. Record `generated_at` is
the verified source identity's timezone-aware `captured_at`, not a fabricated
natural-run or new capture timestamp; this makes repeat publication stable.

The original eight stage IDs are accepted. The first seven carry
`stage_group=HK_SEVEN_STAGE` and `m10_stage_member=true`. `STAGE_1545_1555`
carries `stage_group=HK_STAGE8_SEPARATE` and `m10_stage_member=false`.
Membership describes the downstream seven-stage grouping only; it is not
formal market qualification or production admission.

## Verification scope

Executed in the cloud workspace under Python 3.12.14, below the repository's
declared production Python >=3.14 environment:

```sh
PYTHONPATH=V5/src python -B -m unittest discover -s V5/tests -p 'test_hk_stage_api.py' -v
PYTHONPATH=V5/src python -B -m unittest discover -s V5/tests -p 'test_module_artifacts.py' -v
```

- RED first: 13 tests, exit 1, `ModuleNotFoundError: v5_shadow.hk_stage_api`.
- GREEN: 18/18 tests pass, exit 0 (17 boundary/unit tests and one three-route
  original-owner integration test).
- Review regressions for quoted/unquoted local paths and division-expression preservation
  were observed failing first, then fixed; a formula-label path bypass is covered.
- Existing immutable publication compatibility: 23/23 tests pass, exit 0.
- Tests exercise the real shared publisher, cold `read_response` in a fresh
  interpreter, the existing HTTP service, exact query switching, no-write GETs,
  Stage8 separation, path redaction, safety/metadata rejection, unchanged
  diagnostics, repeated publication, and compare-and-swap conflict handling.
- Only the independent cold-reader boundary is injected in the adapter unit
  tests. The separate integration test uses the actual producer, original
  SelectionStore, cold reader, and existing API for four-lane, auction, and
  Stage8 synthetic fixtures with no injections. It compares original rows,
  statuses, and references and verifies published HTTP reads after moving the
  private store out of reach. This establishes the synthetic engineering chain,
  not actual Mac/API/UI deployment, natural input provenance, or complete M08
  acceptance. Target-environment and real-input verification remain separate.

# M08 eight-stage observed history on the existing V5 page

This candidate adds an independent read-only M08 panel and GET route to the
existing source/status section. M06, M09, M10, the four source cards, manager
research, V4, selectors, stores and the original M08 implementation are retained.
No new module number, framework, dependency, collection, production selection,
trade, credential or permission change is introduced.

## Frozen source and meaning

Owner: `lexi2016/v5@0a9e49a088358954ce36093f6c068e694fde961f`,
`handoffs/M08/V5/docs/M08_HK_OBSERVED.md`. Existing Mac observation feedback:
`01f1a6347722081cbbf97b54204bf033e6d01938` (21/21 for the separate owner delta).
The new `V5/contracts/m08_readonly_runtime.json` pins 58 unique byte-exact files (60 source entries, including two reused
namespace-helper paths) under
`V5/source_owners/m08`, including the observation implementation identities and
all original owner source dependencies. These are private source copies; nothing
is imported into the main process from the old V4 root. The bridge calls only
`read_hk_stage_observed` and the unchanged `_public_value` path redactor in a
fresh `-I -B` interpreter. Frozen files are not edited.

This verifies saved original output, not original full input availability or
natural execution. `OWNER_RESULT / HISTORICAL / OBSERVED_ONLY` remain explicit.
`captured_at=null`; `natural_verified`, `pit_verified`, `formal_admission`,
`raw_input_verified`, `computation_replayed`, and
`market_data_authenticity_verified` are literal false. Safety flags stay false.
Original PARTIAL/CANNOT_CONFIRM status, 10 rows, raw fields, formulas, gaps and
row order are preserved. Only local path text is redacted for the browser.

## Exact local binding, never checked into GitHub

Add `m08_hk_stage_observed_binding` to a **private copy** of the existing
source-bundle API config, preserving all prior bindings and routes. Its exact
keys are:

- `recorded_root`: absolute path to the already imported, marked, new V5 observed
  root used by the completed M08 Mac proof. This is the only data root M08 reads.
- `python_executable`: absolute existing supported Python >=3.14 executable.
- `references`: all 10 original **public/cold-read reference objects**, in the
  private proof's recorded order. Each object has exactly `schema_version`,
  `import_sha256`, `import_receipt_sha256`, `target_date`, `stage_id`, `market`,
  and `run_id`. These must be copied from the completed proof, never inferred
  from paths/latest or regenerated from the source. Do not drop the repeated
  09:25 runs, merge stage results, or replace an old run with the latest run.

The full source config remains private. Do not upload source/recorded absolute
paths, original trios, responses or private logs. No production payload is in
this source delivery; all checked-in fixtures are synthetic.

Add `/api/v5/source-bundle/hk-stage-observed` to that config's `routes`. The
existing marked source API root may be read unchanged. GET without query returns
the configured reference catalogue (`references_verified=false`); it does not
claim these have already cold-verified. A selected GET requires exactly `date`,
`stage`, `run_id`, and `import_sha256`; it matches a configured reference and
verifies that reference's pinned receipt, import manifest and trio via the owner.
Unknown, partial, duplicate, altered and unconfigured selected refs fail closed.
No binding gives `NOT_CONFIGURED`, with no synthetic fallback.

The M08 reader has its own bounded slot. Its busy/read failure cannot consume the
M06/M09/M10 slots. The page offers stage and run selectors, preserves all ten
references, separates SECOND_FILTER/D1_REFERENCE through original source labels,
and calls Stage8 `HK_STAGE8_SEPARATE` outside M10's seven stages. Refresh, run
changes, missing configuration, disconnect, rejection and superseded replies
cannot retain or restore old tables. Existing controls use independent sessions.

## New checks and one Mac acceptance command

Cloud checks use existing Python/Node and synthetic temporary owner trios only.
Read `VALIDATION.json` for the final results. No original M08 90/16/21 suite was
rerun. Cloud DOM/typecheck/build are **NOT_RUN**: existing `vitest`, `vue-tsc`
and `vite` executables are absent. No install was attempted. The added Vue DOM
specs and real-response hook are delivered for the existing Mac dependencies.

On an isolated checkout of the final candidate commit, with its existing Mac
Python/frontend environment and the private config above:

```sh
"$EXISTING_V5_PYTHON" -I -B V5/tests/run_m08_readonly_acceptance.py \
  --expected-commit "$EXACT_CANDIDATE_SHA" \
  --source-config "$PRIVATE_M08_SOURCE_CONFIG" \
  --baseline-source-origin "$CURRENT_SOURCE_API_ORIGIN" \
  --protected-root "$PRIVATE_ORIGINAL_SOURCE_ROOT" \
  --evidence-dir "$PRIVATE_M08_P0_EVIDENCE"
```

`CURRENT_SOURCE_API_ORIGIN` must be the verified existing loopback source API
(e.g. the currently confirmed M09 source process), not an invented/new server.
The acceptance command does not start/stop or deploy any persistent process. It
starts a temporary loopback read-only server, performs all ten exact real GETs,
compares each original artifact/reference/provenance against a separate cold
reader, verifies 10 rows each, unknown-reference rejection and hash/mtime
non-mutation of recorded/API/protected original roots. It checks equality of the
existing four source/M06/M10/M09 route responses against the baseline service.
It also verifies the exact clean checkout and both Python runtimes, runs the new
seam tests and old read-only integration regressions, feeds the private real
responses into the Vue DOM tests, and runs product typecheck/build. Old component
DOM tests and the five-panel independent mount test are included.

Only the small `report.json` is intended for feedback publication. Temporary
real-response files are deleted at the end. Detailed logs remain private.
A real run cannot skip frontend checks, omit the baseline, or omit the fixed
commit and still report PASS. The synthetic cloud-only command uses
`--skip-frontend` and reports `PARTIAL_VERIFICATION`.

After acceptance, the original authorized Mac executor can bind the new config
and built preview through the existing source-origin/Vite proxy mechanism. This
source candidate does **not** claim deployment. Keep the current fixed preview,
previous source process and its config as rollback. Roll back by restoring that
known preview/config/source origin; do not delete any observed import or V4 data.

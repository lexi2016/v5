# M08 minimal M06 original-mapping adapter

## Fixed baseline and scope

Parent is `7aaf58b07daa70f3efb2554b82ee8195cb7a1185` on the existing
`dev/m08-github-handoff-20261011` branch. It preserves the Mac feedback at `bfdb43fd3ac40f2134635e53bec22619fbaf9f97`, recording the preceding
candidate's 90/90 isolated engineering tests, not a real-input producer run.
This delta preserves that feedback and all original donor bytes. It changes
only M08 integration code and its own tests/docs; no new dependencies.

The actual wiring defect was a fabricated M08 prerequisite: native M06 rows
do not require `preselect_lane`, and their original `rank` and
`score_prob_active` can remain strings. The original M06 materializer already
provides `symbol`, integer `pool_rank`, and numeric `pool_score`.

Sources inspected:

- `lexi2016/v5@7006c6ab6e2b4f1f9f6a00da0b3b490dcd4d4fd8`,
  `handoffs/M06/source/V5/src/v5_shadow/vendor/hk_preselection_baseline/domains/_preselection_materializer_parts/hk_pool.py`
  (`_build_shared_hk_0_2_pool_body`) and `hk_preselection_verified.py`
  (`_verify_chain`, `run_verified_hk_preselection`).
- Same M06 source tree, `hk_preselection_publication.py`,
  `read_verified_hk_preselection_reference(bound_root, reference)`: exact
  committed reference cold read, no latest/date fallback.
- Original M08 donor `handoff/v4-running-source-20261005/canonical/stage_center/_runner_parts/hk_candidate_authority.py`:
  D1 contributes membership/metadata; LIVE evidence is separate.
- Original `_selection_parts/hk_auction_reference.py`: its code alias is
  `code/ts_code/stock_code`, while rank/score already prefer `pool_rank/pool_score`.

## Implemented boundary

`v5_shadow.hk_stage_m06.bind_m06_verified_result(request, result, expected_source_reference)`
accepts an unbound existing M08 request (no `m06` key), the original M06 strict
cold-reader result, and an independently pinned six-field source reference.
It does not import/rewrite M06's algorithm or execute an external collector.

- Requires `ASSEMBLED / VERIFIED_SOURCE_SNAPSHOT`, original READY verification,
  exact source-reference projection, exact target/signal dates, eligible mapped
  artifact, 100 unique HK symbols, ordered native integer ranks/probabilities,
  original row contract, and literal false safety flags.
- Retains every original row field and value unchanged, including raw code and
  numeric strings. Never rebuilds missing mapped fields from raw strings.
- Binds original source hashes plus the mapped artifact and reference digests
  in existing source evidence; does not export source filesystem paths.
- Does not invent candidate lanes, timestamps, prices, cap/volume/turnover,
  units, M02 membership, eligibility, PIT proof, or source files.
- M08's existing request validation accepts native mapped rows. Existing
  legacy synthetic fixture rows remain supported without a fake D1 lane gate.
- Only `D1_REFERENCE` projects `code=symbol` in a copy passed to the unchanged
  original owner. Retained request/pool/payload rows are unmodified. Reference
  output remains `CANNOT_CONFIRM`; it cannot become `SECOND_FILTER`.
- Explicit `fixture_only=true` cannot be tagged as recorded replay, including
  after binding at the producer/independent-reader validation boundary.
- The new module is covered by M08 implementation identity. New generations
  are code-version-bound; use the old pinned checkout to cold-read old V5
  engineering generations. This does not migrate or rewrite any prior output.

This is consistency checking of a supplied original-reader result, not an
independent replay of M06's storage verification. Calling the adapter with a
JSON-shaped claim does not authenticate the source. The upstream original
reader and exact reference must actually be checked. M08 remains
`natural_verified=false`, `formal_admission=false`; LIVE fails closed.

## Local command and API

Use absolute paths; output must not already exist. The result and reference
must be obtained from the original M06 reader above, not a CSV-only substitute.
The request file supplies actual stage/M02 evidence and omits only `m06`.

```sh
cd handoffs/M08
PYTHONPATH=V5/src python -B -m v5_shadow.hk_stage_m06 \
  --request "$M08_UNBOUND_REQUEST" --m06-result "$M06_COLD_RESULT" \
  --expected-source "$M06_PINNED_SOURCE_REFERENCE" --output "$M08_BOUND_REQUEST"
```

Then use the existing `hk_stage_daily` run command documented in
`M08_HK_STAGE_HANDOFF.md`, only when the remaining original evidence is complete.
The adapter never changes a 20261013 pool into a 20261012 pool, sets an
eligibility date, or populates missing payload fields to get a green result.

Targeted verification, using installed dependencies only:

```sh
cd handoffs/M08
PYTHONPATH=V5/src:V5/tests python -B -m unittest discover \
  -s V5/tests -p test_hk_stage_m06_adapter.py -v
```

The existing full `run_m08_acceptance.py` now includes these 13 tests for future
runs (103 total if all previous counts stay unchanged). The previous 90-test
suite was deliberately not rerun in this delta. Cloud results are 13 new tests
plus 3 specifically selected existing compatibility tests, with logs and
runtime details in `V5/tests/logs/M08_M06_ADAPTER/`. Mac test of this delta and
real-data execution are NOT_RUN here.

## Remaining evidence versus adapter work

Same-day historical pool and saved original SelectionStore products can exist
independently of ordinary-stage raw runner inputs. Read saved products only
through their original exact-run reader; readable output is not proof of
reproducible source input. Saved auction reference is not SECOND_FILTER.
Stage8 aggregate or summaries are not its full retained snapshot and RT_DATA.
This delta does not copy historical results or claim their natural/PIT
qualification, and it does not wait for future dates to finish source code.

See the fixed parent Mac feedback for inspected evidence and any later
independent historical-result adapter. Shared ledger contracts remain
unchanged. Complete M08 product/real-input acceptance remains open.

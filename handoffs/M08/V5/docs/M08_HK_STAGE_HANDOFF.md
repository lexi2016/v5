# M08 HK stage original-owner engineering candidate

## Delivery and scope

This candidate continues `dev/m08-github-handoff-20261011` from verified HEAD
`5da73228d40d991e8f73ba84f7c66553e9235bc3`. No original source byte,
shared ledger, main, P0, other module, V4 service, credential or trade path changed.
The complete default retained-input chain is executable; it is **not complete
M08 product acceptance**. Natural data admission, scheduler activation, Mac
integration, existing UI mounting and two eligible natural days remain unverified.

Five separate states:

| Layer | Result |
|---|---|
| Code engineering | Default original owners → original immutable store → independent exact-run reader implemented; see exact final test receipt |
| Real inputs | SYNTHETIC/RECORDED_INPUT_REPLAY only; no new market capture performed; M02/M06 declaration hashes are consistency evidence, not independently attested eligibility/PIT |
| API/page | Existing immutable module API publication adapter and actual loopback HTTP tests; no Mac route or existing page deployment |
| Automatic continuation | Natural scheduling/collection not activated; LIVE input fails closed; retained CLI may be called explicitly by existing orchestration |
| Complete acceptance | NOT COMPLETE; neither synthetic fixtures, HTTP tests nor retained replay equal natural qualification |

## Original code and compatibility

Donor is `lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`.
`integration_candidates/M08/CAPSULE_INTEGRATION_CANDIDATE.json` pins every
selected source by path, Git blob, SHA-256 and bytes. The loader checks all bytes
on entry and before committing success. Frozen original formulas, auction
owners, Stage8 collector, publication and verification bodies execute unchanged.

The canonical split `_namespace.py` files are absent in the supplied donor
closure. Three in-memory compatibility aliases explicitly use the existing
V5 vendor `read_global` helper and are labeled
`EXPLICIT_COMPATIBILITY_ALIAS_NOT_CANONICAL`. No canonical file is invented.
`stage_center` and `infrastructure` are virtual package scaffolds so importing
one owner does not eagerly import unrelated runtimes. Missing imports fail closed.
This isolated capsule remains an integration candidate, not frozen-vendor approval.

## Routes and original contracts

- Six ordinary stages: `merge_hk_four_lane_candidates` followed by
  `select_hk_four_lane`. Cross-lane merges preserve first-live-value precedence;
  duplicate same-code/same-lane input is rejected. Source fields are not zero-filled.
- `STAGE_0925 / SECOND_FILTER`: original `select_hk_0925_second_filter`, preserves
  original order/rank then original Top10 cap. Explicit 09:15–09:20 HK window,
  09:20:05 input cutoff and separate shared 09:25:05 cutoff remain visible.
- `STAGE_0925 / D1_REFERENCE`: only exact supplied M06 pool rows; original
  `select_hk_0925_d1_reference`, always unconfirmed. It never impersonates the
  missing second filter. Failed/partial upstream auction sources receive explicit
  diagnostics before original envelope normalization, preventing false READY_EMPTY.
- `STAGE_1545_1555 / STAGE8_RTDATA`: original persisted snapshot validator,
  original active-code filter, original RT_DATA window aggregation and original
  four-lane selector. The provider boundary is a retained JSON payload; no SDK,
  quote connection or network fetch occurs. `natural_now` is the retained capture
  clock used to exercise the original collector, explicitly labeled replay;
  natural verification stays false. Snapshot capture is 15:50–15:55, RT_DATA
  window 15:45–15:55, shared Stage8 cutoff 15:55:05. No ordinary-stage substitute.
- `read_m10_seven`: exactly seven ordered references with the same target date;
  missing, duplicate or appended Stage8 references are rejected.

The original score details/reasons/risks are retained separately in provenance
for four-lane routes using the original `hk_four_lane_score`; the immutable
original envelope/rows remain unchanged. No formula or coefficient is rewritten.

## Input contract

`V5/tests/test_hk_stage_daily.py::request` and `stage8_request` are complete
synthetic input examples. They are fixture-only, not actual historical quotes.

Every request binds market, exact target/signal dates, stage, data kind, collector,
source capture/availability, payload digest, Top100 run/row digest and original
rank/lane, membership date/code set/receipt digest, field units and source status.
The prior signal day is checked against the original HK-securities calendar;
A-share, HK securities and HK Connect calendar states remain separate.

This boundary accepts normalized retained M06/API data, not arbitrary private
filesystem roots. It does not fetch M06 or create eligibility evidence.
The existing M06 reader/API must supply its verified exact run before a real
integration. A matching SHA for caller-supplied bytes alone does not prove
provider origin, historical availability or official Connect eligibility.
Recorded inputs explicitly carry `REPLAY_POINT_IN_TIME_QUALIFICATION_NOT_ATTESTED`;
unknown qualification carries `M02_MEMBERSHIP_NOT_VERIFIED`. All formal/natural
flags remain false. Half-day active window contracts are blocked, not guessed.
Missing quote enrichment, unsafe alias, raw score override, mixed market/day,
unknown source status, bad units/hash, future clock and duplicate records fail.

## Immutable output and independent read

Initialize an empty, separate V5-only root with the CLI. A marker is mandatory;
existing non-empty directories and symlinks are rejected. The root contains:

- `generations/<identity SHA>/owner/selection_runs/.../{artifact.csv,manifest.json,receipt.json}`:
  exactly original SelectionStore publication and independent verification
- `product.json`: full retained input, source/config/code identity, original
  envelope and exact original trio reference; private local only
- `attempt.json`: durable RUNNING/SUCCEEDED/FAILED state. Interrupted attempts
  require review rather than automatic rerun
- `latest_success.json`: convenience success index; never used by exact reader

Each original SelectionStore has its own generation root because the unchanged
owner permits one immutable input per date/stage slot. A changed input/version
creates another generation without weakening that original conflict contract.
Exact retry uses committed output without resampling or rewriting; FAILED/RUNNING
attempts cannot silently restart. Failed/partial products cannot replace success;
older or equal capture times cannot advance the success index. Final source/code
checks precede success publication. Root producer lock serializes commits.

`read_hk_stage(root, reference)` always spawns a fresh process and independently
checks commit state, product/input/source/code bindings, requested date/stage/run,
original trio hashes/content and safety flags. It never follows a latest pointer,
chooses another run, or calls a selector. Keep the matching code release to read
its historical generation; current code cannot silently reinterpret old code identity.

## Commands

From the checked-out module root `handoffs/M08`, using existing supported Python:

```sh
PYTHONPATH=V5/src python -B V5/tests/run_m08_acceptance.py
PYTHONPATH=V5/src python -B -m v5_shadow.hk_stage_daily --init-root /ABSOLUTE/EMPTY/V5_M08_ROOT
PYTHONPATH=V5/src python -B -m v5_shadow.hk_stage_daily --root /ABSOLUTE/V5_M08_ROOT --input /ABSOLUTE/INPUT.json
PYTHONPATH=V5/src python -B -m v5_shadow.hk_stage_reader --root /ABSOLUTE/V5_M08_ROOT --reference /ABSOLUTE/EXACT_REFERENCE.json
```

Save the returned `reference` object as JSON for the read command. No path above
is an actual deployment path. API publication uses `hk_stage_api` and the existing
`module_artifacts.publish_generation`; see `integration_candidates/M08/API_READONLY.md`.
GET/refresh/date/stage/run selection reads immutable published records only.
No extra server framework, frontend, dependency, provider or recurring scheduler.

## Verification and limits

Cloud has Python 3.12.14 and pandas 2.2.3; these are below `pyproject.toml`'s
production Python >=3.14/pandas >=2.3 contract. No packages were installed.
M08's default chain itself uses standard library owners only. Exact tests, start,
end, exit, failure counts and interpreter evidence are in the acceptance receipt.
Pytest, pyarrow, complete donor runtime, Mac execution, SDK/live capture, UI
build/browser and natural execution are NOT_RUN, with reasons in the receipt.
Existing unrelated baseline suite failures are reported, not hidden or repaired.

## Mac integration / independent rollback

1. Pin this delivered commit; verify the delivery manifest and original hashes.
2. Use a separate checkout/release directory and the existing supported Mac Python.
   Do not overwrite a dirty active tree; run the one-command acceptance there.
3. Consume the existing verified M06 input without recollecting it; keep all
   retained market payloads and actual root paths local. Do not upload them.
4. Apply only approved M08 API registration/mount work after reviewing the actual
   current integrator baseline. Shared `run_ledger.py`, `daily_*`, `stage_selection.py`,
   gateway and UI remain byte-identical here. No lane is forged into the shared ledger.
5. Publish separate HK response generation with CAS. Keep code release, private
   data generation, API response generation and UI mount identities separate.
6. Roll back only the HK release binding and its expected API generation.
   Keep A code/API bindings untouched: A1/B1 → A2/B1 → A2/B2 → A1/B2 is enforced
   by independent bindings, not git reset or whole-tree replacement. This candidate
   has not executed that Mac integration/rollback sequence, so no such pass is claimed.

No merge, V4/8910 mutation, trade, credential read, system-security expansion,
public deployment, new market data collection or recurring operation is included.

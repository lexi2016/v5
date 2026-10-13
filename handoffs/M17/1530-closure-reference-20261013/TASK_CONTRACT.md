# M17 1530 fixed-source closure handoff — 2026-10-13

## Result and fixed identities

This is a source/reference handoff, not a new product or runtime acceptance. The four reported missing modules already exist in `lexi2016/v5` on `dev/m17-github-handoff-20261011` at fixed commit `f350602512ee14f825bb53a976fbaada93a0b921`. Their original donor is `lexi2016/v4` commit `f7cb731c384ee6890a87d16c19a5b5a621779477`, canonical snapshot `handoff/v4-running-source-20261005/canonical/`. No additional source upload is needed. Use `closure.json` for exact repository paths, byte counts, Git blobs and SHA256.

Existing manifests `handoffs/M17/source/SOURCE_MANIFEST.json` (37 entries) and `handoffs/M17/supplement/SOURCE_MANIFEST.json` (95 entries) match all 132 corresponding Git blobs in the fixed M17 tree. Original input/supplement verification receipts already record byte validation. This pass independently read and verified the four modules plus eleven dependency/package files against those manifests. It did not execute imports, tests, providers, 1530, or inspect real business inputs.

## Minimal four-module map

| Import | Existing capsule | Why needed |
| --- | --- | --- |
| `infrastructure.manager_close_attempt` | `supplement/.../canonical/infrastructure/manager_close_attempt.py` | `materialize_manager_close_discovery._status` writes original attempt diagnostics; original reader validates failures. Direct dependency `infrastructure.owned_path`. |
| `domains.manager_condition_evidence` | `source/.../canonical/domains/manager_condition_evidence.py` | Original discovery, rebound evidence and workbench reader condition projections. Direct dependencies `domains.manager_research_evidence`, `infrastructure.manager_input_attestation`, `contracts.trading_calendar`. |
| `v4.manager_research.workspace_plan` | `supplement/.../canonical/v4/manager_research/workspace_plan.py` | Original `read_rebound_history`, calendar sessions, native witnesses, history rows and `rebound_v3_metrics`; do not substitute another module's revised implementation. |
| `v4.manager_research.workspace_projection` | `supplement/.../canonical/v4/manager_research/workspace_projection.py` | Original `HK`, `date_token`, canonical symbol, timestamp and digest helpers required by workspace_plan and 1530 rebound code. |

For workspace_plan's history path, the original fixed capsule also contains `contracts.trading_calendar`, `infrastructure.owned_io`, `infrastructure.manager_input_attestation`, `workspace_read_control`, and `upstreams/v3_shared_data/shared_data/{hk_security_master,hk_daily_supplement,store}.py`. `pandas` is an external runtime dependency, not donor source; this pass neither installs nor tests it. Preserve the calendar's own static data dependency and explicit upstream import roots.

`v4.manager_research.__init__` eagerly imports `contracts`, `hkex_provider`, `material_transport`, `materials`, `service`, and `store`. All six have same-donor entries in the existing supplement. Reuse the existing package closure and its manifest; do not replace `__init__` with an empty file or inject fake modules. The eleven directly read files are not a claim that only eleven files suffice for every eager/transitive import.

Five additional direct imports occur in lazy functions outside the minimal history/arithmetic call path: `announcement_materials` in `temporal_role`; `workspace_actions` in `stock_plan`; `infrastructure.hkconnect_close_store` in `read_plan_quotes`; `workspace_semantics` and `workspace_briefing` in `build_workspace`. They have fixed P0 references at `287de959ac160f6ae2792ca1f9684b4c86750012`, recorded separately. They are not silently substituted into the fixed-F donor. If a proposed 1530 candidate makes those functions reachable, establish their matching donor/transitive closure explicitly before claiming that path is complete.

## Exact boundary against current late/readonly chain

Current accepted product/deployment is P0 `287de959ac160f6ae2792ca1f9684b4c86750012`; its feedback is `5b32a0916fbe486bbf7a33c1ce6ad9e3e4618e51`. M17 readonly adapter is `64e112573eb5cbac47ff2db1dd0887f459f38213`. Existing late reuse run is `ca2c344b61334ad28f4b6146117643cd`, source date 20261012, plan date 20261013, captured at `2026-10-12T15:55:15.370877+08:00`. These facts prove no 15:30 capture, original 1530 history witness, natural execution or full close. Keep `received_not_historical_1530=true` and original gaps.

1530 uses `prepare_universe/materialize`, original Futu bridge, original universe/snapshot attestations, pre-capture history and catalyst/prior validators. Outputs are `workbench_research/{date}/1530.json`, `1530.receipt.json`, `inputs/1530_futu_snapshot.json` and `inputs/1530_rebound_history.json`, with original attempts/diagnostics. Late uses `recapture_close_minutes` and separate close_recapture products. Do not overwrite either chain, rename late results as 1530, borrow M18's run, or change deployed UI/API bindings.

## Known input contract; actual inputs NOT_VERIFIED here

1. Bind independent V5 state, original data/news/universe owner and history authority roots explicitly. Original app/import-origin checks and owner code digests must be satisfied by a documented isolated mapping, not arbitrary string replacement. Unknown capture mode must reject execution.
2. Original calendar must establish a full HK Connect session and appropriate HK securities history sessions. 1530 materialize is current-date-only. Original live quote start and return must be within `[15:30,15:32)` Hong Kong time. After the window, missing snapshot is terminal; no current quote can repair historical 1530.
3. Exact-date original universe membership and authority receipt chain are required. A late D1 Top100 pool is not proof of this 1530 universe contract. Existing universe preparation is a separate owner activity; this handoff does not authorize running it.
4. Require original Futu snapshot bytes, codes, start/availability times, attestation/receipt and digest validation. Quote timestamp is not source availability. Do not invent clock values or allow production clock/fetcher overrides; synthetic seams remain explicitly SIMULATED.
5. Require immutable history witness captured before the quote request, original authority-root identity, exact master, immutable prior HK0.2 panel/manifest, actual read start/completion, native evidence, and original reader digest. Previous five full sessions and prior sixty HK sessions follow the original calendar. An updated/latest panel cannot replace an unavailable historical witness. Missing units/currency/history remain unverified.
6. Catalyst materials must pass original source/owner/PIT validation as of actual snapshot availability; missing catalyst input stays a gap. Continued tracking accepts only fully verified prior date/run/SHA; preserve first_seen/last_seen and original invalidation conditions. Absence of a subsequent quote/event does not prove invalidation or a new catalyst.
7. Preserve original strict/near/unknown and diagnostic semantics, incomplete rule authorities and unverified currency/units. `RESEARCH_ONLY=true`; production, orders, buy-gate and formal/natural admission remain false. Reader success is not business completeness.
8. Candidate success must require original output/receipt plus independent original reader validation. Failed/current attempts must not display previous success as current. GET/page reload may read only; it must never prepare universe, run an owner or collect.

Source contracts above are available. This pass deliberately did not inspect real data, runtime configuration or credentials, so actual 1530 snapshot, history, universe, catalyst/prior and active-mode evidence remain NOT_VERIFIED, not asserted physically absent. They are the outstanding runtime admission requirements before any future real execution; source availability alone is enough to start a static minimal candidate and synthetic contract work in the original M17 chat.

## Assignment for original M17 writer

Read the existing complete `handoffs/M17/M17_FIRST_CHAT_PROMPT_20261011.txt`, `source/handoff/PROMPT_FOR_CHAT.md`, `SOURCE_MAP.md`, and supplement README at the fixed M17 commit, then this narrower continuation. Implement the smallest separate 1530 candidate in that chat, reusing original owners and a fully explicit path/manifest mapping. Preserve the frozen donor and current late/readonly/feedback. Do not implement product changes on Mac as part of this handoff.

Deliver complete candidate files, genuine forward/reverse patches, fixed base/candidate commits, exact before/after hashes, reachable dependency closure, original/synthetic failure evidence, input contract and isolated Mac instructions. Shared UI/API/scheduler changes require a separate integration candidate. Do not run live 1530, collect market data, enable natural scheduling, deploy, modify V4, touch credentials/permissions, or infer approval for a new production lane from this source handoff.

No new source was copied into the branch. No sensitive personal-path defaults were found in the four and directly inspected dependency/reference files. This is not a whole-capsule privacy certification. If further reachable source contains such defaults, record relative path/line and pause that file's upload without editing original bytes; continue safe references only. Previously excluded private-path sources remain excluded.

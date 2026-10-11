# Fixed source locations for M16 integration repair

All links below are pinned to M16 2fec401df6e9bf125f875ea2f6fcff88b2eb64ed. The original production default observation resolver/factory and app mount are NOT PRESENT in the supplied candidate/P0 source scope. Do not confuse the protocol or fixture observation with that missing factory; no concrete factory path is invented. HkexOfficialProvider exists, but default application/provider wiring remains unverified.

- [Original service constructor; store/observation_reader/source_provider required](https://github.com/lexi2016/v5/blob/2fec401df6e9bf125f875ea2f6fcff88b2eb64ed/handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/v4/manager_research/service.py#L310) — `handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/v4/manager_research/service.py`, line 310, Git blob `8c7cc0357aa9c203fe088edb1fd88900290c9aec`.
- [Original observation dispatch and missing-reader handling](https://github.com/lexi2016/v5/blob/2fec401df6e9bf125f875ea2f6fcff88b2eb64ed/handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/v4/manager_research/service.py#L431) — `handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/v4/manager_research/service.py`, line 431, Git blob `8c7cc0357aa9c203fe088edb1fd88900290c9aec`.
- [Original ObservationReader protocol; this is not a concrete default factory](https://github.com/lexi2016/v5/blob/2fec401df6e9bf125f875ea2f6fcff88b2eb64ed/handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/v4/manager_research/ports.py#L9) — `handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/v4/manager_research/ports.py`, line 9, Git blob `b4fad4ff57694f5d4a7ea27071160ffaf7f85036`.
- [Original ResearchSourceProvider protocol](https://github.com/lexi2016/v5/blob/2fec401df6e9bf125f875ea2f6fcff88b2eb64ed/handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/v4/manager_research/ports.py#L41) — `handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/v4/manager_research/ports.py`, line 41, Git blob `b4fad4ff57694f5d4a7ea27071160ffaf7f85036`.
- [Original HkexOfficialProvider implementation; constructor at364; not instantiated or network-tested here](https://github.com/lexi2016/v5/blob/2fec401df6e9bf125f875ea2f6fcff88b2eb64ed/handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/v4/manager_research/hkex_provider.py#L357) — `handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/v4/manager_research/hkex_provider.py`, line 357, Git blob `8b7aa95d7ff93a6aed32a92a0f0897b3cfaee240`.
- [M16 facade requires already assembled service](https://github.com/lexi2016/v5/blob/2fec401df6e9bf125f875ea2f6fcff88b2eb64ed/V5/src/v5_shadow/manager_jobs.py#L27) — `V5/src/v5_shadow/manager_jobs.py`, line 27, Git blob `ee154f185a7ed1d39d18f173f73c0a2428671d3e`.

## Six full-router calls missing from the thin facade

Router Git blob: `1e89a2b2cdc9c6192eed188ac53d8b4027aa77be`. The narrower job methods match; this list concerns mounting the entire original router against the facade.

| Missing method | Original call |
|---|---|
| `get_catalyst_observations` | [router:155](https://github.com/lexi2016/v5/blob/2fec401df6e9bf125f875ea2f6fcff88b2eb64ed/handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/apps/api/v35_api/manager_research_router.py#L155) |
| `refresh_catalyst_observations` | [router:165](https://github.com/lexi2016/v5/blob/2fec401df6e9bf125f875ea2f6fcff88b2eb64ed/handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/apps/api/v35_api/manager_research_router.py#L165) |
| `get_workspace` | [router:178](https://github.com/lexi2016/v5/blob/2fec401df6e9bf125f875ea2f6fcff88b2eb64ed/handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/apps/api/v35_api/manager_research_router.py#L178) |
| `refresh_workspace_plan` | [router:210](https://github.com/lexi2016/v5/blob/2fec401df6e9bf125f875ea2f6fcff88b2eb64ed/handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/apps/api/v35_api/manager_research_router.py#L210) |
| `get_announcements` | [router:219](https://github.com/lexi2016/v5/blob/2fec401df6e9bf125f875ea2f6fcff88b2eb64ed/handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/apps/api/v35_api/manager_research_router.py#L219) |
| `refresh_announcements` | [router:248](https://github.com/lexi2016/v5/blob/2fec401df6e9bf125f875ea2f6fcff88b2eb64ed/handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/apps/api/v35_api/manager_research_router.py#L248) |

## Fixed P0 local source positions

P0 local commit `b8b524edc8922d87a7c8f5b426709d42ae619bb1`; this is a local integration commit, NOT a GitHub M16 source ref.

- `V5/src/v5_shadow/manager_plan.py`, lines 73,86; SHA256 `9f6c05188e776e190832269aa65a9a369c3fb3f5c0984189a9a4bb77170a6a0d`: Frozen loader rejects missing original service; exact observed error MANAGER_SOURCE_CLOSURE:v4.manager_research.service.
- `V5/src/v5_shadow/manager_plan.py`, lines 382,459; SHA256 `9f6c05188e776e190832269aa65a9a369c3fb3f5c0984189a9a4bb77170a6a0d`: Plan-only store/namespace bypasses full task-owner lifecycle; observation_reader=None.
- `V5/src/v5_shadow/module_api.py`, lines 203; SHA256 `9a0fc23a18b7499961fa14d57fb097dc293f64f27c6f87b5bc0354921784e510`: POST returns405 MODULE_READ_ONLY; published-result reader cannot be treated as task command API.

Missing P0 capsule paths: `V5/vendor/manager_plan_baseline/v4/manager_research/service.py`, `.../reader_source.py`, `.../apps/api/v35_api/manager_research_router.py`. The M16 original source links above are available; no loader bypass or second router was implemented. No tests rerun for this documentation supplement.

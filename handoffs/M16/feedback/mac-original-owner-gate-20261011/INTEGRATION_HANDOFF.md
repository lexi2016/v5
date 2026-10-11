# M16 → P0 default factory / system entry: BLOCKED

P0 inspected: b8b524edc8922d87a7c8f5b426709d42ae619bb1 (local isolated complete V5 baseline plus P0 overlay).
M16 inspected: 2fec401df6e9bf125f875ea2f6fcff88b2eb64ed.
No product edits or deployment performed. The original owner offline gate was not repeated.

## Reproduced closure gap

P0 `V5/src/v5_shadow/manager_plan.py:86` loads a manifest-bound workspace closure in a fresh process. Its `_Loader.find_spec` rejects missing members (`:73`). In an independent existing Python -S -B process, calling original load_owner() followed by importing v4.manager_research.service returned exactly:

`MANAGER_SOURCE_CLOSURE:v4.manager_research.service`

Raw probe: p0-loader-probe.json. P0 capsule lacks service.py and reader_source.py. These originals exist in the M16 handoff at `handoffs/M16/source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/v4/manager_research/`, but importing them through a new sys.path does not satisfy P0's frozen loader/manifest. Replacing the shared source manifest or bypassing its import guard is not an established thin factory contract.

## Default assembly gap

P0 `V5/src/v5_shadow/manager_plan.py:382` intentionally bypasses full Store constructor side effects; `:459` constructs a SimpleNamespace for workspace methods, with observation_reader=None. It does not create ManagerResearchJobService or its lifecycle. That namespace cannot be treated as a real research job owner.

Original M16 handoff `.../canonical/v4/manager_research/service.py:310` requires store, observation_reader and source_provider. M16 `V5/src/v5_shadow/manager_jobs.py:27` accepts an already-assembled service only. Neither P0 V5/src nor M16's supplied factory implementation provides a production observation-reader/provider resolver, private runtime binding, or process/lifecycle assembly contract. The previously passing test supplies a SIMULATED original fixture provider; it cannot become a default business provider.

## Existing HTTP contract gap

P0 `V5/src/v5_shadow/module_api.py:203` intentionally rejects POST with 405 MODULE_READ_ONLY. It is a published-result reader, not the job command router. No original manager_research_router exists in that P0 capsule.

Original router exists at M16 handoff `.../canonical/apps/api/v35_api/manager_research_router.py:81`. Job subset uses get/ensure/retry/job/cancel/ensure_events and matches M16 thin facade. The complete router also calls six methods absent from the facade: get_announcements, get_catalyst_observations, get_workspace, refresh_announcements, refresh_catalyst_observations, refresh_workspace_plan. Passing the facade as a wholesale router replacement would break those endpoints. This is a full-router mismatch, not proof that the narrower job subset is incompatible.

## Requested original M16 follow-up

Provide a fixed, source-bound production factory using original Store/Service and the actual server-owned observation/provider adapters, with an explicit isolated runtime root and lifecycle owner. Supply the original system router/app mounting contract or the reviewed narrow job-route composition that preserves other manager owners and original same-origin/body/date validation. Resolve the frozen loader boundary through an explicit integration proposal; do not suppress its checks, add fake observation defaults, or convert the published reader into a new job engine.

Until those inputs are fixed, default factory and system HTTP integration are NOT_RUN/BLOCKED. No empty diagnostic page, second algorithm, job model, or data model added. 61796 remains old historical preview with no new P0 wiring; 8873/8910 unchanged.

## GitHub feedback already delivered

Commit 8fc72939c13733396f0fa5fbf5df845029fed148 on dev/m16-github-handoff-20261011 adds only handoffs/M16/feedback/mac-original-owner-gate-20261011/ (8 files). All 8 remote blobs match sanitized local evidence; all 147 preexisting blobs unchanged. Original stdout preserved except local home/workspace prefix redaction. Includes result, execution receipt, script SHA, full verified source-tree identities, verified 22 gate inputs, checkout receipt and command. No runtime input payload, source code, credentials or personal records uploaded.

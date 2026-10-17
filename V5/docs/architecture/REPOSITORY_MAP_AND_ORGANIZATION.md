# Repository Map and Organization Rules

Audit date: 2026-10-17 (UTC). Snapshot commit: `01d93717905813705732161d4d79062ae5af2d99`.
This is a structural inventory and organization proposal, not a claim that the product is complete, tested, deployed, or naturally running.

## 1. Canonical source and branch policy

- Integration snapshot: [`dev/v5-main-integration-20261012@01d93717905813705732161d4d79062ae5af2d99`](https://github.com/lexi2016/v5/tree/01d93717905813705732161d4d79062ae5af2d99).
- The repository default branch `main` is not the integration baseline. Do not infer source completeness from the default branch.
- Module candidate branches are source evidence, not automatic overlays. Their directory layouts and file manifests differ; a missing same-path file does not prove missing functionality.
- Any code change must begin from a freshly read HEAD, use a dedicated branch, and preserve the full source commit, owner manifest, dependency closure and test receipt.
- Do not merge or deploy from this organization pass. Changes here only establish navigation and maintenance rules.

## 2. Snapshot inventory

The fixed integration tree has 2,363 blobs across 2,904 tree entries; the recursive tree was not truncated.

| Path | Files | Responsibility |
|---|---:|---|
| `V5/` | 1,369 | Main V5 backend package, contracts, source-owner closures, vendor capsules, tests, tools, examples and module documentation |
| `handoffs/` | 686 | Historical module handoffs, review evidence, Mac/cloud receipts and recovery records |
| `frontend/` | 214 | Integrated Vue/Vite application, frontend tests and runtime code |
| `integration_candidates/` | 84 | Isolated candidate overlays and bounded integration artifacts; not all are release code |
| `integration_tests/` | 3 | Root-level P0 integration checks |
| root support files | 4 | `README.md`, `START_HERE.md`, `P0_INTEGRATION_TASK.md`, `SOURCE_MANIFEST.json`, plus the root readback/schedule support files listed in the source manifest |

The inventory is descriptive. It does not label any file safe to delete.

## 3. Directory responsibilities

### Runtime / product code
- `V5/src/v5_shadow/`: Python runtime modules and adapters. Keep business owners, transport, scheduling and read-only API responsibilities explicit.
- `frontend/src/`: application shell, API adapters, contracts, views and component tests.
- `V5/contracts/`: source manifests, schema pins and contract metadata. Changes to a pinned source require an explicit new identity and matching tests.
- `V5/pyproject.toml`, `V5/uv.lock`, `frontend/package.json`, `frontend/package-lock.json`: runtime/development dependency declarations. Keep lockfiles synchronized with declared dependencies.

### Frozen or imported owner source
- `V5/vendor/`: frozen source capsules. Treat pinned bytes as immutable. A legitimate update creates a new versioned capsule/PIN and a reviewable manifest diff; do not edit a capsule in place to make tests pass.
- `V5/source_owners/`: imported owner closures and supporting originals. Preserve provenance and manifest links; do not deduplicate solely by identical filename.
- `V5/producers/`: producer entry points. Runtime paths and provider access must be explicit, configurable and admission-gated.

### Verification and support
- `V5/tests/`: backend/unit/contract tests that belong to the V5 package.
- `frontend/tests/`, `frontend/src/**/__tests__`, `frontend/src/**/*.spec.ts`: frontend tests. Prefer colocated tests for focused module behavior and integration tests for cross-module contracts.
- `integration_tests/`: cross-boundary checks only; avoid copying every module unit test here.
- `V5/tools/`: explicit maintenance/verification commands. Tools must not silently trigger production work.
- `V5/examples/`: non-production examples only; synthetic inputs must be clearly marked.
- `V5/docs/`: stable architecture, plans, operations and acceptance criteria.

### Historical evidence and candidates
- `handoffs/`: append-only evidence and handoff history. Keep original receipts and rejected results; corrections should add a dated superseding note rather than silently rewrite history.
- `integration_candidates/`: isolated candidate output. Every candidate should identify source commit, owner/manifest, included files, omitted files, tests run, tests not run and integration disposition.
- Do not move historical evidence into runtime directories just to make the tree look smaller.

## 4. Stable module map

Keep the original numbering and names; P0 is the shared platform layer, not M19. B01 is M18, not an extra module.

| Phase | Modules | Scope |
|---|---|---|
| P0 | Shared platform | API, immutable artifacts, run ledger, scheduling, publication, recovery and rollback |
| P1 | M13, M14, M15 → M18 | Announcement research, oversold research, US-to-HK mapping and manager saved-result/page chain |
| P2 | M01, M02, M03, M05, M06 | A/HK/US source inputs and preselection |
| P3 | M07, M08, M09, M10 | A/HK stage selection and close review |
| P4 | M04, M11, M12, M16, M17 | Research archive, intraday review, video review, public-source tasks and late-session discovery |
| P5 | Whole system | Fixed-release regression, natural applicable-day continuity, independent startup and rollback |

One module can span multiple files and owners. Module number, scheduler lane, HTTP route and page are different concepts; do not force a one-to-one mapping.

## 5. Evidence vocabulary

Every status report and candidate manifest should distinguish:

- **SOURCE_PRESENT** — files exist at a fixed source identity.
- **UNIT_TESTED** — named tests ran against the named commit.
- **CONTRACT_TESTED** — module boundary and failure cases were exercised.
- **HTTP_DOM_TESTED** — actual HTTP and DOM path tested; not visual browser acceptance.
- **NATIVE_VISUAL_TESTED** — real browser visual behavior checked.
- **SAVED_COLD_READ** — immutable product read by a fresh process.
- **DEPLOYED** — release and runtime environment independently read back.
- **REAL_INPUT** — source capture, as-of/cutoff, identity and receipt verified.
- **NATURAL_RUN** — expected scheduler/owner trigger occurred without synthetic clock or manual recovery.
- **ACCEPTED** — all module-specific exit conditions passed.

A test receipt must include commit SHA, environment/dependency identity, command, exit status, log location/hash, and skipped/not-run cases. Never promote one status to another implicitly.

## 6. Organization backlog

### O1 — Establish navigable entry points
- Keep this root README short and current.
- Use `START_HERE.md` for the fixed integration source and current handoff sequence.
- Use `V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md` as the execution-plan entry, while checking its dated evidence and append-only updates.
- Use the handoff folder's source index and evidence matrix for module candidate provenance.

### O2 — Add a per-module registry (next step)
Create one registry row for M01–M18 with: canonical owner path, current integration commit, source/manifest PIN, entry point, consumer, lane, configuration schema, tests, current evidence tier and outstanding blocker. Derive the row from actual manifests and receipts; unknowns remain UNKNOWN.

### O3 — Separate candidate and history
- Keep rejected candidates and historical source trees in their existing locations for now.
- Add a small candidate index with statuses `PROPOSED`, `REJECTED`, `PARTIALLY_INTEGRATED`, `INTEGRATED`, `SUPERSEDED`.
- A candidate is `INTEGRATED` only when its actual required files and tests are present in the selected integration tree; branch existence is not enough.

### O4 — Make tests discoverable without flattening them
- Backend tests run from the declared V5 environment; frontend tests/typecheck/build run from the frontend lockfile.
- Add targeted CI jobs by change surface (backend owner, scheduler/ledger, manager publication, frontend, integration) before expanding to expensive full regression.
- Do not delete tests or weaken assertions to get a green run.

### O5 — Review duplicate and stale files safely
- Identify duplicate content by Git blob SHA and path, not filename alone.
- Before any deletion or move, prove the file is not the only owner source, not referenced by a manifest/PIN, not needed for historical replay, and not referenced by a receipt or script.
- Archive only after a machine-readable move map and tests validate all references.
- Never recover the 2026-10-15 uncommitted 24-file checkpoint by reconstructing from a summary; require the original patch/manifest and SHA verification.

## 7. Explicit non-goals for this pass

- No production code deletion or broad renaming.
- No module algorithm, threshold, PIT, qualification or BUY-gate changes.
- No real provider capture, trade/order activity, production deployment or V4 modification.
- No claim of complete frontend, all-18-module readiness or full natural-run acceptance.

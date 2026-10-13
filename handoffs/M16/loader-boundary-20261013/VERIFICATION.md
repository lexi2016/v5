# M16 manifest-bound loader repair

## Scope and provenance

Base: `a98160c214f53235deb7b41f163f0927c0e32778` on
`dev/m16-github-handoff-20261011`.

Only `V5/src/v5_shadow/manager_loader.py`, its executable boundary tests,
and this handoff change. `manager_factory.py`, `manager_jobs.py`, the fixed
owner source, and V4 remain byte-for-byte unchanged.

The test source is the existing GitHub `handoffs/M16/source` material, verified
against the base tree's Git blob identities. Its `SOURCE_MANIFEST.json` SHA-256 is
`c8f72f9a64cb2dd0c1f37819156e7d26ec457097d3f2bffad79f2beeebeac2ea`.
No old local candidate or raw diagnostics are included in this change.

## Boundary behavior

- Retains the original service/store/HKEX provider/material-store constructors.
- Validates the required closure and all manifest-listed manager Python sources.
- Executes verified source bytes, with no `.pyc` or arbitrary directory fallback.
- Keeps relative imports within the private owner alias; lazy imports are checked
  against the manifest again when their source is executed.
- Rebinds the original `infrastructure.owned_io` and
  `infrastructure.trading_safety` imports to private verified modules. It does
  not modify host `infrastructure`, `v4`, or `sys.path`.
- Rejects unlisted relative imports, unbound non-stdlib absolute imports,
  conflicting aliases, substituted modules/classes, and incorrect file/spec/code origins.
- Allows repeated assembly from the same closure. A different closure/root in
  the same process is rejected rather than replacing existing classes.
- Publishes cached loader state only after all four classes pass. Initial import
  or class validation failures remove only this loader's modules and finder.

This is an integrity boundary for trusted pinned Python, not a sandbox for
arbitrary Python. Standard-library behavior and the original owner's algorithms
are unchanged. Dependencies outside the available manifest remain fail-closed.

## Executed engineering evidence

Environment: existing cloud Python 3.12.14 and pytest 9.1.1; no installation.

1. Original tests: 3 passed, but loading the real fixed owner failed with
   `ModuleNotFoundError: infrastructure`.
2. New initial regression set on the old loader: 18 failed, 10 passed.
3. Added source/class substitution and initial-transaction rollback probes;
   each new defect was observed failing before its correction.
4. Final focused set: **32 passed, exit 0**.

Command, from this branch's repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=V5/src python -m pytest -q V5/tests/test_m16_owner_loader.py
```

The positive controls construct the four actual pinned original objects, assert
class and infrastructure origins, shared material-store wiring, independent
runtime roots, unchanged host imports, and clean service shutdown. Observation
reads and network entry points fail the test if called. No source-provider
request, financial collection, event refresh, or job is submitted.

Negative controls cover missing/tampered dependencies, manifest hash/required
set/duplicates, unsafe paths and symlinks, root and submodule alias conflicts,
late cached-module injection, origin and class replacement, relative and absolute
import fallback, changed lazy source, failure cleanup, and successful retry.

### Broader donor probe: not a full pass

A default repository discovery attempt had 10 collection errors. A subsequent
read-only offline probe using the existing donor import paths completed with
138 passed, 10 failed, and 2 collection errors. It was not pursued or repaired;
these results do not count as acceptance of the new loader or the full product.

Collection errors: `test_manager_lifecycle_hardening.py` and
`test_manager_research_decision_recovery_contract.py`.

Failed donor tests:
- `test_exact_five_hkex_fixtures_recover_documented_financial_rows`
- `test_07666_aggregate_row_does_not_promote_note_number_as_revenue`
- `test_vibe_fanout_requires_only_a_share_sessions_and_preserves_hk_window`
- `test_vibe_with_no_legal_a_share_date_cannot_be_ready`
- `test_vibe_unknown_calendar_date_is_not_read_and_blocks_ready`
- `test_real_vibe_unavailable_theme_tree_has_verified_source_but_no_context`
- `test_empty_vibe_context_does_not_remove_verified_archive_material`
- `test_mixed_vibe_dates_are_partial_and_keep_usable_context`
- `test_vibe_context_count_uses_rows_after_temporal_filter`
- `test_five_recovered_financial_sets_stay_researchable`

No broader failure is claimed fixed or diagnosed by this narrow change.

## Required targeted Mac handoff

1. Verify the delivered commit on the original M16 development branch, with no
   replacement local candidate. Recheck the source-manifest hash above.
2. Use the existing authorized Python with pytest, in a fresh isolated process.
   If unavailable, report the exact missing dependency; do not install anything.
3. Run only the focused command above. Expected: 32 passed and exit 0. All test
   writes use temporary private test roots. Do not run the full app, start jobs,
   configure credentials, contact a provider, or change V4 services.
4. Retain the commit, manifest hash, interpreter version, count, exit code and
   a short sanitized result. Do not publish raw local paths or diagnostic logs.
5. Keep later P0 application integration, real observation-reader binding,
   actual PDF/provider closure checks, and business acceptance separate. The
   incomplete stage-center dependencies are not fabricated by this repair.

Status: offline four-object assembly verified in cloud. Mac targeted run,
P0 integration, real-data acceptance, page availability, automatic continuation,
and complete product acceptance are **NOT_RUN** for this change.

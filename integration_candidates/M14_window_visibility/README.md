# M14 saved-window visibility candidate

Scope: original M14/P0 saved projection and human-readable display only. No producer, new collection, original calculation, input or owner change. Existing research date queue, main/Vite routes and other modules remain byte-identical.

Exact baselines: fac269ade842eb1d9b54c604b77091b0cd58bd44 under integration_candidates/M14_saved_page/files; Mac confirmed both full files match. PREIMAGE.json contains exact SHA256 plus the unchanged frontend API contract check. Full before/files and candidate.patch included.

Public projection adds only saved native_evidence research_cutoff/capture clocks/member count/unit metadata, a closed source_contract allowlist and validated HK-code-to-reason-list pending_reasons. Original per-GET owner cold-read, references, SHA, pagination, 256KiB bounds, private-path redaction and safety remain unchanged. Private endpoint/path fields are not projected. Missing fields remain missing.

The M14 page now shows the saved cutoff, panel row/code counts, source/interface and same-source window semantics, unknown unit/finality, and per-reason stock counts. These counts are a display grouping of saved reasons, not stock recomputation. One stock can have multiple reasons. Original projected machine fields are collapsed. Specific missing dates and invalid-row dates/OHLC values are not invented from an enum; this artifact's pending_reasons contain reason enums rather than those details. All pending/formal-false boundaries remain.

## Apply once on Mac isolated copies
1. Make separate isolated copies of current API checkout and frontend root; preserve current running release and rollback paths.
2. Verify PACKAGE_MANIFEST.json. Run python -B <candidate>/apply_candidate.py --api-checkout <isolated-api-checkout> --frontend-root <isolated-frontend-root>. It checks both exact source SHA plus unchanged API contract before either write. Unknown or already-patched files reject. No root tree overwrite.
3. Backend test: PYTHONPATH=<isolated-api-checkout>/V5/src python -B <candidate>/tests/test_projection.py. Tests use synthetic metadata and never invoke owner calculation or acquisition.
4. Copy tests/M14WindowVisibility.spec.ts into isolated frontend src/components/; run existing vitest for that file plus M14SavedRebound.spec.ts, existing vue-tsc and vite build.
5. With unchanged real saved binding, validate GET still returns run9c70cc6cb8e34afb9e34b366acf8becd, saved cutoff2026-10-13T18:40:58.776354Z, panel40930, strict0/near0/pending690, reasons688 PRIOR60_KEYS_MISSING and2 SOURCE_ROW_INVALID; flags all original false. These are expected Mac observations, not values embedded in product code. Check page text and closed machine details, then parent-controlled reversible release.
6. Roll back by restoring prior API/frontend release paths; never alter saved inputs/history.

Cloud tests are synthetic projection/UI checks only; real Mac HTTP/DOM acceptance remains required.

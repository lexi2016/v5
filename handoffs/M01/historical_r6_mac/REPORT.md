# M01 R6 isolated Mac engineering acceptance

Fixed publication input commit: `30d795bca2ed28c6b182eb8778f25dfdc2b2bc0f`.
Candidate runtime/test afterSHA: `922f1d3300ad94c5309964fb22d19b23f44b515fe3d2414cf04ad1220c527960` / `e753bfb98ac7887d55532df2981806aeabbc87f5d1cdb243015404cf01128dc5`.
This acceptance agent wrote its isolated copies, fixtures, logs, and reports only under `acceptance/`; the parent’s successful pytest-install receipt is in the sibling `acceptance-integration/`. No active V4/V5 root or business source was changed.

## Candidate tests

Status: **PASS — 2 passed in 0.00s** using the isolated `acceptance/pytest-venv/bin/python` path. The original supplied interpreter and the previously available 3.14.6 interpreter lacked pytest. The first isolated `pip install pytest` attempt exited 1 because DNS could not resolve `pypi.org`; the parent later installed pytest 9.1.1 into the same isolated venv and recorded the successful install in `../acceptance-integration/pytest-install-venv-receipt.json`.

The final test command ran the original supplied test file unchanged. The earlier NOT_RUN and DNS failure records remain in `RESULT.json` and `rawlogs/`; no pytest shim was used for the result, and `run_candidate_tests.py` is an unused compatibility-shim draft.

## Independent boundary reproduction

Expected SafeRoot/reader cases passing: 2 — normal SafeRoot write -> disk read_and_verify -> same identity reuse, SafeRoot rejects traversal and symlinked binding ancestry.
Known candidate defects reproduced: 7 — same generation_id with different complete source identity and pointer, corrupt existing binding error is masked while old bytes are preserved, existing source drift error is masked as no-replace collision, binding accepted with missing .v5-shadow-root marker, binding accepted when private output root overlaps formula source root, read_and_verify accepted valid generation_path outside the designated source root, binding parser accepted JSON strict_source_verified=1 as True.
Unexpected boundary failures: 0 — none.

The fixtures use only synthetic, reader-valid Parquet/JSON artifacts with the fixed original SafeRoot and `read_formula_generation(require_source=True)`. No market data, recomputation, service, preview, or network operation was used by the boundary harness.

## Evidence

- `RESULT.json`: machine-readable status and case evidence.
- `rawlogs/commands.jsonl`: command, cwd, relevant environment, UTC start/end, exit code, stdout/stderr paths.
- `rawlogs/`: command output, the final pytest receipt/output, and `boundary_results.json`.
- `execute_acceptance.py`, `run_candidate_tests.py` (unused draft), `reproduce_boundaries.py`: acceptance harness sources.
- `fixed_original/SOURCE_HASHES.json`: SHA-256 of the copied original reader and SafeRoot.

This is isolated engineering evidence only; it is not production acceptance or M01 completion.

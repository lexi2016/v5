# Mac checkpoint slice execution — 3d5458

Fixed candidate: `3d5458d9608c2ff53fffd7d36e23e6f194d2e9e8`.
Branch: `dev/v5-main-integration-20261012`.
Compare from prior feedback ebf36e8f1e53606cec8146350372aa4b8b5aba1c: ahead 2, only two added files:
- V5/src/v5_shadow/p0_manager_owner_checkpoint.py — ca4c883433a22dfa3c7bde262fe5b9246591316d
- V5/tests/test_p0_manager_owner_checkpoint.py — 70b075af27202c53f57181f4cc421b13f52d71d7

No product edits or second source review. Existing isolated dependency subset reused; 77 fixed-candidate files verified for tests, plus exact candidate test_manager_current_recovery.py for a safe fixture probe (78 total). Existing Python 3.14.6 / pytest 9.0.2, no installation; same dependency caveat as earlier feedback.

## New supplied tests: FAIL

CWD=isolated candidate. PY=existing interpreter; private absolute paths redacted.
```sh
$PY -m pytest -vv -p no:cacheprovider V5/tests/test_p0_manager_owner_checkpoint.py
```
Start UTC **2026-10-12T04:53:22.109293+00:00**; end **04:53:22.357540+00:00**.
Actual pytest **exit 1; 2 PASS / 1 FAIL**, three collected, reported 0.04s.

- test_requires_saved_owner_reference PASS: direct _require_reference({}) rejects missing reference.
- test_slice_keeps_publication_unconnected FAIL at line 22: expected substring "original manager" in function docstring; actual docstring is "Execute one already-bound manager run and return exact saved readback."
- test_no_http_or_refresh_claims PASS: source-text absence check only.

None of these supplied tests executes run_saved_owner_checkpoint, manager save, or independent same-run readback. Their result must not count as business integration proof.

## Actual safe entry call: reaches assembly, stops at date gate

Executed once with the candidate's existing ManagerCurrentRecoveryTests.setUp fixture, without running that fixture's refresh tests. It creates empty synthetic owner roots and marked manager output root, retains its original target 20261009, and uses actual current clock. The local probe sets action=read, supplies an isolated marked ledger root and empty owner rows (as used by existing assembly fixture cases). It does not invent saved owner results or claim these inputs are valid business references.

Actual command:
```sh
$PY <TASK_PROBE>/probe_checkpoint.py
```
Start UTC **2026-10-12T04:54:14.507161+00:00**; end **04:54:14.575515+00:00**.
Actual exit **1**:
```text
probe_checkpoint.py:23 -> run_saved_owner_checkpoint(template, [], ledger, registration)
p0_manager_owner_checkpoint.py:26 -> assemble_manager_request(...)
daily_manager_assembly.py:166 -> ValueError: DAILY_MANAGER_TEMPLATE_TARGET
```
A Python call-profile observer (no function mocking) recorded entry into run_saved_owner_checkpoint and assemble_manager_request. It recorded no run_manager_plan or refresh_workspace_plan call. Fixture byte snapshot was unchanged across the call, and fixture cleanup completed.

- Assembly function: **REACHED**, rejected old fixture target against current date.
- Manager computation/save: **NOT_REACHED**.
- Same-run independent readback/checkpoint: **NOT_REACHED**.
- Publication/CAS/HTTP: **NOT_CONNECTED / NOT_RUN**.
- No new collection, owner refresh, manager refresh, real data access/upload, or existing-service process changes.

## Exact outstanding input/contract boundary

Within this verified candidate fixture set, no admitted current-target saved owner-reference bundle is available. The reused recovery fixture contains empty manager/materials/us file bindings and no saved owner run/artifact references; it cannot prove consumption of already-saved strategy results. The original target was not rewritten to manufacture current business input or to bypass the gate.

For a complete allowed run, the author must provide a portable synthetic saved-owner fixture or an explicitly admitted exact saved-owner reference bundle with the required run/artifact identities, current-target assembly template, valid input roots/file hashes, ledger marker/registration and manager-output marker. The checkpoint wrapper expects each row.product_reference to include run_id/artifact_sha256; the existing assembly consumes saved references through state.attempts/readback_verified. No replacement contract was fabricated locally.

Additionally, the existing assembly sets the assembled request action to refresh. The authorized batch explicitly forbids refresh, so this probe did not advance past the date gate or alter the action/clock after assembly. A save/readback execution must have an explicitly safe synthetic/no-external-effect contract consistent with that boundary; the present source-text assertions do not establish one. This is an execution/input boundary, not a demand to wait for a future trading day.

Overall: **supplied tests FAIL; actual entry/assembly rejection observed; manager saved same-run end-to-end NOT_RUN**. No claim that all P0–P5 or 18 modules are accepted. Existing previews/production preserved; unrelated startup/ledger tests not repeated. Only this minimal sanitized feedback is appended using fresh integration HEAD/base plus expected-SHA CAS.

# Mac publication canary — 912941 — PASS

Fixed candidate: `912941feebd7ceff5ca63e1a355b3b45d53a90f6`.
Branch: `dev/v5-main-integration-20261012`.
Bridge blob: `9f9caa584e131963014cc787bc083aba51396873`.
Targeted test blob: `3e2152b2cceb15ff294f525bd9c292916a7d57a6`.
Existing Python 3.14.6 and pytest 9.0.2; no dependency installation or product modifications. Candidate source/dependency files used were verified against fixed-tree Git blobs.

## Actual execution

Paths below are logical placeholders; private roots and real response bodies remain on Mac.

1. From isolated candidate, `<EXISTING_PYTHON> -m pytest -q -p no:cacheprovider V5/tests/test_m18_v2_publication_bridge.py`
   - 2026-10-12 05:44:11.976436–05:44:12.231998 UTC; exit 0.
   - **2 passed in 0.02s**. This is only the newly delivered narrow test file.
2. `<EXISTING_PYTHON> <TASK>/publication_canary_912941.py`
   - 2026-10-12 05:44:12.232386–05:44:12.305869 UTC; exit 0.
   - Reused existing verified v2 bundle metadata and local identity binding. Did not rerun the prior 133-object inventory or construct/rebuild v2.
   - Created a fresh isolated publication root with the original manager root marker and module config (release `mac-912941-canary`, route `/api/v4/manager/m18/v2`).
   - Actual product calls:
     ```python
     descriptor = descriptor_from_bundle(None, identity, bundle_meta)
     receipt = publish_m18_descriptor(config, descriptor, expected_generation=None)
     cfg, fd = module_api._config(config)
     try:
         record, record_sha256 = module_api.read_response(
             cfg, fd, ROUTE, {"run_id": identity["run_id"]})
     finally:
         os.close(fd)
     ```
   - Descriptor canonical size **804 bytes**; exactly one published record object **1,266 bytes**. No 30MB response or 42MB bundle in records.
   - Original publisher/CAS receipt: previous_generation=null, changed=true.
   - Original publication reader successfully returned the saved descriptor. Follow-up comparison of captured result against the pre-existing local identity: **all six fields MATCHED**, exit 0.
   - This call uses the bridge's current metadata interface (`reader=None`); it does **not** claim the bridge invoked a v2 Reader or newly reverified the entire bundle.

## Pinned identities

- run_id: `46596b03c2ab4e29b1219fd2e5eb698f`
- target_date: `20261012`
- plan_sha256: `fed238e033181b159f419918c8c54dcb4743791b18f93d31e2a1e2006f5924ce`
- raw_sha256: `7de6ea9fc6b10462fcc75af1c02c9d9d5111288a9d993b7f154ca988fea4e4db`
- response_sha256: `ae840ac69d9fdc8f25bd675c41e8e3f6d028ef17147987b36220a35a6d786d22`
- input_identity: `c99d03b5dfe289f93382d14e1aa4c083283283270c27287e1e752b71f2d465de`
- offline v2 generation: `8bf699c6bc1fc47a869d2e21d53989a5f5f18d31b52ddef24071c88c4c7ffa8a`
- profile_sha256: `a8b56161f6d19de0d5222775e132d78f75d7ad707a1824b4d2b861ff285ecc6c`
- existing manifest_sha256: `f655cdfcd5894861318a3d4d72ec2559580ea2f942440a3a9bfaeba0d041595d` (reused prior binding; not a returned descriptor field)
- **new publication generation**: `01726f5d6c64e9afb7d4a06278f5ae6e2fb1a4eba784865bde2c5981ffa5f36b`
- published record SHA256: `0b8ce7a315ec6501177495f5641c9fe7a0ff9b35a5503c4bc4e2c17551f65fe7`
- payload SHA256: `340841fa0749afd1ba36f6d734db8c4478689e8e1d632760fb00277321e4a072`

Publication generation and offline generation are distinct and were not interchanged. The successful local publication and receipt are retained for reuse; no second publication was run.

## Scope

**PASS: publication canary only.** No HTTP server, page reader, Chrome, ports 54780–54782, daily scheduling, owner, collection, manager refresh, or trading was run. Existing publication roots/services were not touched; no global budgets changed.

HTTP/pages and module route wiring remain **NOT_REACHED**, as declared by the author. Descriptor READY describes this descriptor, not business readiness. Existing US PARTIAL and rebound/formal-screen CANNOT_CONFIRM remain unchanged; no whole-P0/P1–P5/18-module acceptance claim. No broader source review or CAS conflict/rollback suite was performed.

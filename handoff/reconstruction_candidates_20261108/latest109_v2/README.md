# Latest109 rebuild V2 — isolated adapter

User requested reconstruction of missing code on 2026-11-08. This is new code, not restoration of missing original `latest109.py` (original pin b1183e88d9b07bc5f4cc9039193a0fccd84197e2cc3a6874ec8abc992699c9c2).

## Reuse and execution map
`load(candidate_path, action_path)` verifies original candidate and ACTION_RULES hashes, then loads the existing formula candidate. `build` requires the unchanged original owner's monitor callback. Candidate calls remain candidate-only; no source collection, lock ownership, Parquet write, scheduling or production binding is added.

Existing candidate still has its own resource checks; the adapter does not replace the original owner's higher checks. Original owner, source admission, active lock and original child process monitoring must be integrated separately and independently reviewed. A callable is not proof of owner identity. This adapter alone is never production admission.

`validate_checkpoint` binds identity/count/date and records exact input digest. It does not grant trusted provenance to a caller's checkpoint. All outputs override production/source/selection admission to false.

## Verification
`python -B -m unittest -v` and `python -B -O -m unittest -v`: 11 interface/synthetic tests each (including two real SHA-pin checks).
Real dependency import + frozen module load PASS (`REAL_DEPENDENCY_CHECK.json`). Full 109-field native output, persisted checkpoint parity, original-owner monitored integration, Parquet round-trip, source admission and natural trigger: NOT_RUN.

## Recovery/rollback
Files are isolated. Nothing replaces production original pins. Rollback is simply not selecting this adapter. Reuse the original immutable input, formula pins and persisted state. Do not recreate checkpoints from later values or declare production success from these tests.

## Publication
Only new source, synthetic test, this README and registration metadata are eligible for the user's requested development-branch synchronization. No historical data, credentials, personal memory or internal instructions are included. Parent coordinates branch writes. GitHub upload and remote byte verification remain pending.

## Review correction
The build path now rechecks the candidate file pin and the actual relative ACTION_RULES path, requires a caller-provided checkpoint prefix digest, and validates output identity and all 109 schema fields via frozen core.check_field. The digest is a new reconstruction interface requirement, not a claim about the missing original API. A trusted owner must obtain it from a verified immutable checkpoint, not compute it from an untrusted changed history at resume time.

Unit tests intentionally stub formula computation, field checks and code-pin IO to test adapter control flow. They do not establish formula equivalence; REAL_DEPENDENCY_CHECK separately loads the actual pinned candidate and all formula modules. Original monitor callback identity and full original child monitoring are NOT VERIFIED. No production integration allowed.

# Frozen live module_api preimage

- Frozen for a minimal M14 reader-slot repair; no patch applied, restart, test, or collection performed by this handoff.
- File: `before/module_api.py`, exact UTF-8 bytes, 61,692 bytes.
- SHA-256: `94c1c26a36a7d1881602b7780077c056615344bf5ab21a54bf2b749904af1d21`.
- Locally computed Git blob: `2151b643ac0dc6df9363a626ed9b2f045d46b240`.
- Identity check: live source API on loopback port 54165, PID 31088; process command selects the checkout containing this file. Its HTTP 200 `/__v5/module-health` reported PID 31088 and the same `implementation_sha256`; `source_provenance_verified=false` remains unchanged.
- Health hashes the disk file at request time; neither that response nor this frozen file attests to an in-memory code snapshot.
- Historical remote commit/blob ownership is UNKNOWN. An older local application receipt records this after-SHA, but does not establish that the complete file exists in remote candidate d4ff8d. The local computed blob alone did not establish prior remote availability.
- This commit supplies a fixed readable preimage only. No claim that a race was reproduced on the live process or on the complete live file.
- No runtime configuration, private absolute paths, credentials, or business data included.

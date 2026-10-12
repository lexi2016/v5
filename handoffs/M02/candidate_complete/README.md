# M02 complete source-identity candidate

This replaces the 81-line wrapper and 20-line tests at parent `50c4b4ce2e9e63070c38d3c6a1a618e1f5388e80`. It inherits original handoff `088a62b588be20d9d80dda13f02136a05a2a6a1b`. It is a complete source overlay, not an installed product, production-data proof, or eligibility approval.

## Executable files

- `V5/src/v5_shadow/hk_source_daily.py`: default three-owner binding, source states, private immutable publication and independent disk readback.
- `V5/src/v5_shadow/m02_input_snapshot.py`: standalone fixed-F snapshot extraction using the original helpers and exact limits.
- `V5/src/v5_shadow/native_identity_reader.py`: full original reader with one import-line change to the standalone snapshot. No owner/loader/audit logic changed.
- Three complete test files and two isolated preparation/execution tools under `V5/tests` and `V5/tools`.

`after/` contains exactly those eight final files. `before/` contains the two files that existed at the parent commit. The other six branch destinations were ABSENT; `SOURCE_MAP.json` identifies all byte sizes, SHA256, Git blobs, original native source, and real patch hashes. `forward.patch` and `reverse.patch` are repository-relative, applicable patches, including tests/tools; both directions were applied and compared byte-for-byte.

## Contract

`build_binding(private_root=..., asset_binding={root, files}, membership_root=..., membership_files=..., native_binding={root, files}, target_date=..., signal_date=..., eligibility_source_date=..., cutoff=..., require_pit=False)`

- Uses exact `membership_reader.read_private(root, files, target_date)`, exact seven-file membership owner/SDK checks, and native `read_private(binding, eligibility_source_date)` in original isolated processes.
- A fresh isolated process installs the original pinned `_HKLoader` and calls `load_frozen_hk_0_2_assets(asset_root)`. No callback, fabricated reader, model deserialization, scoring, collection or PIN override.
- Original HK calendar verifies target/reference sessions and previous-session signal. Native capture's Hong Kong date equals the reference date. Membership acquire/available dates equal target, in order and no later than cutoff. Cutoff must have a timezone and its Hong Kong date must equal target.
- A newer frozen panel can supply reference identity where `panel_max_date >= signal`; this says nothing about its availability at that historical cutoff. Known source timestamps after cutoff are rejected.
- Every source is either VERIFIED identity or REJECTED with a reason. Exceptions carry all three results. Incomplete result dictionaries never count as success.
- All source `pit_verified`, overall `historical_eligible`, `formal_eligibility_verified`, production and order flags remain False. The original membership historical as-of gate also constrains the read witness; source timestamps alone do not establish it. Native/panel owners do not provide a verified publication-availability witness. `require_pit=True` fails closed. `created_at` only records this binding receipt's creation.

## Private persistence and independent readback

Private output must already exist, be owned by the current user, have no group/other permission bits, and contain `.v5-hk-source-root` with exact bytes `v5.hk-source-root.v1\n`. Absolute ancestry and referenced paths cannot contain symlinks. Output cannot equal, contain, or be inside an input root.

The unchanged pinned SafeRoot supplies FD-based writes and a persistent kernel lock. Immutable objects and receipts are written first; one no-replace `slots/<target>.json` pointer is the atomic commit point. Existing success is never overwritten, same input/result is idempotent, and changed input/result conflicts. A failed pre-commit write can leave an unreferenced content object, not a visible success; no automatic cleanup or deletion runs.

Keep the returned `receiptHash` as the external identity anchor. Call `read_binding(private_root, target_date, receipt_hash=...)`. It accepts no replacement roots/files. It validates the pointer, object/receipt hashes, schemas, request/run/date/flags, then rereads all three saved source bindings and compares canonical JSON identities. `read_at` from the membership reader is excluded from immutable source identity because it changes on each current read; it never becomes historical evidence.

## Boundaries

Native/membership snapshot: original regular-file FD reads, O_NOFOLLOW/O_NONBLOCK, inode/device/size/mtime/ctime/length stability, SHA equality, default 16 MiB per file, only exact registered body-corpus path exception 32 MiB, total 64 MiB. No shared limit changes.

Frozen assets use a separate M02-local streaming FD snapshot: the exact six panel/model pointer/manifest/data files plus optional three name files, at most 64 MiB per asset and 128 MiB total. The observed fixed model (~33 MB), panel (~21 MB), and names (~97 KB) fit. All JSON pointer/manifest reads remain 16 MiB. Extra declared files are rejected. The loader's original panel/model/name checksum and model/oracle identity checks remain mandatory. FD-verified manifests and lexical references are bound to returned dataclass fields, paths and declared artifact SHA; canonical JSON comparison distinguishes booleans from numbers.

These are Python boundaries around original path-opening owners, not an OS sandbox or a globally atomic filesystem snapshot. They do not claim protection against an adversary with write access to the same private source tree. Source roots must remain stable during each read.

## Verification and integration

See `TEST_RESULTS.json`, `MAC_ACCEPTANCE.md`, and `INTEGRATION_REQUEST.md`. Source-only and real-fixture evidence are explicitly separated. No raw test logs, model/data bytes, private machine paths or credentials are published. Original source, R3, review, owners, shared guards, main, V4 and active integration/preview remain unchanged.

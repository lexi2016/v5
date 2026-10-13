# M02 HK capture: isolated, versioned candidate

Status: **offline candidate verified; live capture, Mac deployment and M02 page integration NOT_RUN**.
This directory is a complete runnable capture/recovery candidate, not a replacement for the entire M02 module or the V4 daily lane. It does not change the already-passed owner files under `handoffs/M02`.

## Authorship and narrowly scoped change

- Original M02 Chat reply `f528dbe5-6bdc-43ec-9d65-0f8203cdd07f` supplied the two verbatim fragments in `original_chat/`: optional-metadata normalization and the security-master projection replacement.
- Integration supplied the full source closure, the scope-preserving insertion into the original collector, the launcher, a candidate-local exact producer-version contract, provenance and synthetic tests. The collector already imported `Any` and `math`; no new imports were necessary. Original `_v4_global(..., 'str')` behavior is retained in the name projection.
- Only optional security-master metadata is normalized: float NaN/None and supported missing-value sentinels become JSON null, finite values and strings remain unchanged, and infinity is rejected. Source snapshot rows, prices, quote validation, eligibility, algorithms and all safety flags are unchanged. A missing `stock_owner` does not establish a security type or membership qualification.
- `PATCH_SCOPE.diff` shows the complete collector/recovery edits. `PROVENANCE.json` records fixed source commits, blobs and original/candidate hashes. References are full byte-identical originals for comparison and synthetic old-version compatibility tests, never the default runner.

## Source closure and producer identities

`collector/` contains the full original producer plus eight dependency files (nine Python files total). Seven were read from `lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`, below `handoff/v4-running-source-20261005/canonical`. The missing namespace helper and package initializer were obtained from the existing M02 V5 namespace donor at `8a4a6cefde128c4cb21b73ae4afd6dc4b72eb384`; their exact bytes match the separately verified original Mac hashes:

- `_namespace.py`: `45da791482883c7c371268a99056960c577f299b43a5629394b3178fbea9f8b1` (527 bytes)
- `__init__.py`: `29b3765f63f15078432ca53a34b28cb726c961e7dd0839022b8a87b3d8b373d8` (70 bytes)

`recovery/V5/` contains the existing M02 pure recovery/readback closure and unchanged three-file membership owner capsule. Its original source-capsule PIN remains `e06a2898a8d5247101acd8b85169d1d51e4d359d6e197ef55d52e0f1c4c7068d`.

The candidate recovery verifies the raw bytes of `contracts/hk_capture_producers.json` against `5655957feb033459af37ce2a4cb9d50a384fa0b9e9608138192b69360f702724`, and admits exactly:

| Actual collector SHA-256 | Explicit version |
| --- | --- |
| `0a9651f88bc8a50d4b5e8ec4b6775a5291918f9f2556cf37c05b80a55cdfd84a` | `hk-capture-v2-original-0a9651` |
| `5a5d8a3867f6661c58a71ca01f43b90c734a6ad1b0f2ba4791011f22a830be66` | `hk-capture-v2-metadata-null-v1` |

No arbitrary SHA, old-identity relabeling or fabricated SDK envelope is accepted. The producer hashes its real source file. The inherited logical workload/code reference and upstream `forward_source_set` remain source-lineage fields; they are not proof that this manual candidate ran as the original natural dispatcher. Manual receipts retain `natural_verified=false`. The old recovery outside this candidate still rejects the new SHA, intentionally; use this versioned candidate recovery for new candidate SDKs. A later producer edit requires another explicit version/pin review and new sealed manifest.

## Runtime and network boundary

- Use an existing Python 3.10+ installation; offline tests use only the standard library. Cloud validation used Python 3.12.14. No packages are installed by this candidate.
- Live capture additionally requires the already-installed `futu` SDK, its existing dependencies, and the user's existing local OpenD service at `127.0.0.1:11111`. SDK import can create its ordinary log files beneath the real HOME. The launcher preserves the existing absolute HOME exactly; do not use `env -i`, a fabricated HOME or a temporary-home workaround.
- No credentials are located, read or configured by candidate code. It performs no login or trade operation. SDK/OpenD account/data-access readiness must already exist; authentication issues are a stop condition, not permission to read credentials.
- The original capture calls `get_plate_stock` for `HK.GangGuTong` and `HK.LIST1922`, then `get_market_snapshot` in batches of 200. The unchanged defaults are minimum universe 600 and required quote coverage 0.0. Do not turn this into SDK-only capture, alter those gates or change qualification to compensate for quote gaps.
- Capture runs only the retained capture function, not the daily lane, scheduler, updater or publisher. No active V4 code is imported at runtime. The full facade contains other original functions that are outside the supported candidate entry point.
- Recovery uses only the supplied retained SDK and bundled pure owner/reader. It makes no market requests. Its wrapper has a Python socket audit guard; the nested original pure recovery subprocess is source-pinned. These are application controls, not an OS network sandbox.
- Launcher imports are manifest-pinned in a fresh `-I -B` subprocess. Known active-V4 paths, V4/v35_dispatcher path components, candidate overlap, symlink paths and non-private output roots are rejected. Select an explicitly designated V5 private root; path checks do not discover every possible active V4 location.

## Start with read-only verification

Obtain this entire directory from the delivered fixed commit. Set `CANDIDATE` to its absolute, non-symlink local path and `PYTHON` to the approved existing Python interpreter. Set `PIN` to the **SOURCE_MANIFEST.json SHA-256 in the delivery receipt**. The adjacent checksum file is a convenience copy, not an independent trust anchor.

```sh
cd "$CANDIDATE"
"$PYTHON" -I -B launcher.py verify --expected-manifest-sha "$PIN"
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -B -m unittest discover -s tests -v
```

These commands neither import Futu nor capture market data. The synthetic tests write only temporary test fixtures. `verify` checks every declared file and the complete collector/recovery inventory. Keep sources read-only during an operation; pre/post verification detects modifications but is not a substitute for an OS filesystem sandbox.

## Future single-use live capture (not executed for this delivery)

Only an explicitly scheduled/authorized Mac validation may run this section. First confirm no original natural job or other capture owner is being repeated. A lock here protects only the selected candidate output root, not the original scheduler or all possible roots.

Choose a new absolute V5 `CAPTURE_ROOT` whose parent already exists. Create it once, with mode 0700 and exactly one regular marker `.v5-hk-capture-root` containing `v5.hk-capture-root.v1\n`. It must be owned by the current user; do not reuse an old root or clear failed receipts. This preparation example fails rather than reusing an existing directory:

```sh
export CAPTURE_ROOT
"$PYTHON" -I -B -c 'import os; from pathlib import Path; p=Path(os.environ["CAPTURE_ROOT"]); p.mkdir(mode=0o700); f=(p/".v5-hk-capture-root").open("xb"); f.write(b"v5.hk-capture-root.v1\n"); f.close()'
# TARGET must be the actual HK current date, never a backfilled historical date.
TARGET=$("$PYTHON" -I -B -c 'from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo("Asia/Hong_Kong")).strftime("%Y%m%d"))')
"$PYTHON" -I -B "$CANDIDATE/launcher.py" capture \
  --expected-manifest-sha "$PIN" --target-date "$TARGET" \
  --output-root "$CAPTURE_ROOT" --allow-live-capture
```

The launcher locks the private marker, creates `capture.claim.json` with exclusive creation, and retains `capture.result.json` on success or ordinary failure. Both receipts are mode 0400. A claim prevents a second invocation even after failure; never remove it to retry. A process killed after the claim may have no result receipt, and is still not retryable without a new explicit decision.

Original output names are `capture.json`, `capture.sdk.capture.json`, and `capture.capture.json`. The SDK file is created before quote snapshots; if a later step fails, retain the original SDK bytes and receipts. Do not reconstruct or patch a missing SDK. Successful launcher completion alone does not establish full quote coverage, PIT availability, signal eligibility, natural execution or formal readiness.

## Retained SDK -> candidate recovery -> exact seven-file readback

Both admitted original and candidate SDK identities can use this path. The untouched original recovery rules require `RAW_CAPTURED`, both complete plates, valid original owner/hash fields, an acquired HK date equal to `target_date`, acquisition not in the future, and **recovery on that same actual HK day**. It cannot backfill an old SDK on a later day. Previously recovered seven-file sets remain usable for read-only evaluation under their original gates.

Create a separate new mode-0700 V5 membership root with only `.v5-hk-membership-root` containing `v5.hk-membership-root.v1\n`, using the same exclusive-create pattern above. Keep a local request file and launcher stdout outside that root. The request has exactly four fields; use the real SDK file's SHA-256:

```json
{
  "sdk_path": "/ABSOLUTE/V5_PRIVATE_CAPTURE/capture.sdk.capture.json",
  "sdk_sha256": "EXACT_64_HEX_RAW_FILE_SHA256",
  "output_root": "/ABSOLUTE/NEW_V5_PRIVATE_MEMBERSHIP",
  "target_date": "ACTUAL_SDK_HK_DATE_YYYYMMDD"
}
```

```sh
"$PYTHON" -I -B "$CANDIDATE/launcher.py" recover \
  --expected-manifest-sha "$PIN" --request "$REQUEST_JSON"
```

Successful stdout contains `recovery.files` (the exact seven relative-path/hash bindings), `producer_version`, the producer-contract SHA, source-capsule PIN and original evidence readback. Preserve it locally. `tests/test_pipeline.py` demonstrates the complete call to the unchanged `v5_shadow.membership_reader.read_private(root, files, target)` in its own subprocess, including missing-SDK and hash-mutation rejection. Do not substitute a six-file set or drop `sdk_raw_sha256` binding.

For M02, pass the actual private membership root and the returned seven-file mapping to the existing builder. Choose the target/signal/eligibility dates from real membership/native/panel intersections; do not manufacture today's source or retrospectively available evidence. Membership source/acquired/available HK day, cutoff, native capture/trade day, previous HK trading signal day and `panel_max >= signal` gates stay unchanged. This candidate does not alter the existing job builder or automatically wire the UI. `SOURCE_IDENTITY_ONLY`, temporal `CANNOT_CONFIRM` and `formal=false` remain until separately evidenced by the existing contracts.

## Verification evidence and limits

`TEST_RESULTS.json` records the executed cloud tests; 38/38 passed. The suite covers real original/candidate collectors with synthetic contexts, strict SDK/capture JSON and seals, snapshot preservation, null/strings/infinity/invalid objects, actual versioned recovery and independent seven-file reader, exact old producer compatibility, unknown producer/contract/hash rejection, full closure frozen imports, real launcher-to-recovery path, private roots/locks/claims, HOME preservation and import/output tampering.

All market rows in those tests are synthetic. The old and new SDKs used by tests are genuinely emitted by the corresponding source modules against fake contexts, never copied into a real evidence root. The launcher control tests also use deliberately small fake bundles. No SDK version, OpenD connectivity, Mac runtime, real quote coverage, temporal readiness, natural scheduler behavior, full M02 suite or preview page deployment is claimed tested here. There is no automatic retry, scheduler installation, production enablement or trading action.

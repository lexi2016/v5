# Original M11 owner manifest supplement

Source release: `research-desk-20261012-r4`, original `app/` source tree. The three files below are copied byte-for-byte, with their paths relative to that source tree preserved. No original source, runtime, service, or data was modified. No tests, collection, generation, or deployment were run for this supplement.

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `domains/research_review_generation/OWNED_SOURCE_MANIFEST.json` | 6430 | `104ac49a1dc3e2bb970878da096a9b7d6dc86db9b63f0d6ac561109fb5829914` |
| `contracts/vibe_runtime_profile.json` | 439 | `1081c31d4f12e5ae62cbfe651c413c124d80794089a923c15e807e90170c249d` |
| `ops/run_research_review_generation.py` | 2537 | `b783bfc1c9d3c593c49a7f775c9e861767cc1f82373530536ec4df0f87e04622` |

The existing manifest declares `v4.vibe.owned_source_manifest.v2` and `CANDIDATE_REQUIRES_CALLER_PIN`. Read-only byte verification of the source release matched all 39 listed owner Python files and all five external files against their declared SHA-256 and sizes; no unlisted owner Python files were found. The manifest bytes also match research-desk-20261012-r1, r2, and r3.

The retained archive-reader baseline has identical bytes for the 39 owner files and three available external files. Its two missing external files are the runtime profile and CLI source supplied here. The baseline's source contract records commit `8342862f05ca9f6516f51b3164b6110651e5af77` and canonical API source paths. This evidence establishes byte compatibility, not direct Git ancestry of this manifest. **The release metadata does not establish that these supplemental files originated at `f7cb731c384ee6890a87d16c19a5b5a621779477`.** Do not relabel this supplement as proven content of that commit.

The files contain no personal absolute paths or credentials. The runtime profile contains non-secret provider/model/public-endpoint settings, which are preserved unchanged. Private local identity records and absolute source paths are excluded. This supplement supplies original missing files only; it is not runtime approval, a test result, or full M11/product acceptance. A caller must explicitly pin the original manifest digest when integrating it.

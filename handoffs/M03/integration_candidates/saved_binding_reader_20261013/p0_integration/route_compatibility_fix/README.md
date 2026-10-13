# e18 exact route-compatibility increment

Parent candidate: e18c6c9aa8e5ba84dd0b0b412ed7d62b5ebc2b67.

Only production change: extend publish_source_result.allowed with exactly these four already-configured routes:
- /api/v5/source-bundle/rebound-saved
- /api/v5/research/lane
- /api/v5/research/wechat/materials
- /api/v5/source-bundle/us-mapping-saved

No new route handlers, wildcard allowance, route removal, request changes, producer invocation, reader/loader changes, or other-card changes.

This two-file increment applies only to an isolated tree whose source_bundle.py and single-card test match PREIMAGE_AND_AFTER.json. Verify hashes; git apply --check runtime.patch; apply once; verify after hashes. Full before/after files and reverse.patch are provided. Both-direction exact-byte roundtrip passed. The parent directory's five-file patch is the alternative starting from the original deployed preimages; do not apply both.

Use the updated ../test_support/test_source_bundle_publication_routes.py for tests. It retains all previous binding metadata and expands the fixture inventory from 11 to 15 exact routes. Seven single-card tests plus five publication-route tests and thirteen original source-bundle tests ran: 25 total, 24 passed and one original M01 Mac Parquet skip. The full-inventory positive case failed with SOURCE_MODULE_ID_REQUIRED before the fix. The positive case uses the real synthetic M03 quote/binding/reader and actual generation storage, proves the other three cards and all 14 sibling reference hashes are retained, and confirms no original data/config mutation. Unknown routes and stale/racing CAS are rejected without publication.

Mac acceptance still uses the original current config and original saved request anchors, the existing compatible Python, and exact-current-generation CAS. This cloud synthetic evidence is not a claim of live HTTP/page publication.

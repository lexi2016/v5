# M03 saved reader / P0 candidate test report

Final adapter source SHA256: 7e2ce3f43b660a5d20b4bc52adf10c8da6770f148adb390b666cc47c132ad864.

- Final saved-reader suite: 12 tests passed, 42.114 seconds. Actual original synthetic quote-only producer/store/binding and fresh R14 reader; file byte preservation, true-capture original request unchanged, formatted raw versus canonical identity, each source member tamper, resealed binding mismatch, missing roots, bad marker, unknown fields, valid poisoned pyc and unlisted top-level dependency shadow are covered.
- Final P0 new/retained regression suite: 24 tests run, 23 passed, 1 skipped, 27.343 seconds. The skip is the original M01 Mac Parquet environment requirement. Six new tests exercise real saved binding dispatch and actual module artifact/CAS persistence, other three cards and all sibling routes, reader failure, stale/racing generation, malformed status/authority, no request rewriting, and no producer fallback. Existing source bundle and current route inventory tests also ran.
- Original M03 offline suite plus the first 11 adapter tests: 82 passed, 126.046 seconds. This preceded the final source-path-shadow hardening. The final 12-test adapter suite and final 24-test P0 suite above include that hardening; do not label the earlier 82-test run as final-code full-suite evidence.
- Exact five-file P0 forward patch -> after SHA -> reverse patch -> before SHA/absence: PASS in an isolated directory. Before identities match the coordinating Mac's byte-verified mixed deployed preimages, not an assumed single checkout commit.
- TDD evidence: missing adapter and missing P0 publisher failed first; formatted request/raw identity and poisoned pyc failed before their fixes; unlisted dataclasses shadow failed before the final pinned-import-only fix.

Python/POSIX, existing dependencies only. No real provider, credentials, trade, V4, shared integration branch, API or page publication was executed by these tests. Production-time Mac inputs were not copied into these fixtures or this commit.

The earlier adapter commit 7c9facdcff148f669a48e3093bde10374103d397 was independently run by the Mac task before its pause: real saved binding VALIDATED_SOURCE_BINDING, 33 quotes/24 themes, 11 tests passed, source bytes unchanged, no publication. This is prior-version evidence, not final-loader or final-P0 acceptance. The final version requires the coordinating Mac's read-only check/publication workflow.

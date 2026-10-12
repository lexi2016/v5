# P0 frontend missing-source supplement

This independent branch contains exactly seven authorized runtime/build source files under `frontend/`, plus this note and `SOURCE_MANIFEST.json`. It starts from clean `2489ea1e04a26a9e2f318f498ac3f5f8c970fe48`; it does not inherit later main changes.

Files preserve original UTF-8 bytes, including line endings and EOF. The manifest records repository-relative paths, byte lengths, Git blob SHA1 and SHA256. No source Git commit is fabricated for the original working copy.

This is a narrow supplement, not a full frontend application or a replacement for `dev/p0-frontend-source-20261012`. The other upload branch is unchanged. No withheld private-path tests, other frontend files, business data or credentials are included. Existing V4/V5 title strings are preserved exactly.

Tests/build: NOT_RUN. Integrators should consume a fixed commit and verify these seven blobs against the manifest; this source delivery is not P0 or full-system acceptance.

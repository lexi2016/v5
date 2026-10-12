# P0 frontend missing-source supplement

This independent branch contains nine authorized runtime/build source files under `frontend/`, plus this note and `SOURCE_MANIFEST.json`. It starts from clean `2489ea1e04a26a9e2f318f498ac3f5f8c970fe48`; it does not inherit later main changes.

Files preserve original UTF-8 bytes, including line endings and EOF. The manifest records repository-relative paths, byte lengths, Git blob SHA1 and SHA256. No source Git commit is fabricated for the original working copy.

This is a narrow supplement, not a full frontend application or a replacement for `dev/p0-frontend-source-20261012`. The other upload branch is unchanged. No withheld private-path tests, other frontend files, business data or credentials are included. Existing V4/V5 title strings are preserved exactly.

Tests/build: NOT_RUN. Integrators should consume a fixed commit and verify these nine blobs against the manifest; this source delivery is not P0 or full-system acceptance.

## Current app_shell supplement

Two current same-root files, `frontend/src/app_shell/types.ts` and `frontend/src/app_shell/useAppShell.ts`, are appended after the initial seven-file delivery. Their original bytes differ from the older handoff snapshot; consume these pinned current blobs rather than overwrite them with older snapshot versions. The original seven blobs are unchanged.

All six direct relative imports from useAppShell.ts resolve to files in the existing frontend working root. Its package import is vue. This is a direct-import existence check, not a full dependency/build validation; no additional dependency files are included. No product edits or build/tests were performed for this source transfer.

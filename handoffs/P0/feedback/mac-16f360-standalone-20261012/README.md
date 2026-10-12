# Mac standalone fixed-candidate verification

Candidate: `16f360cf6506cc38665e7d95a6e4754a574e4d83` on `dev/v5-standalone-packaging-20261012`.

PASS: existing Python 3.14.6, 16 targeted unittest tests, zero failures/skips. Actual UTC commands/exits are in verification.json. No dependencies installed, frontend rebuilt, product code changed, collection, trading, or real daily executed.

Two builds each contain 679 files and have SHA256 `c6f16533ce4b486639a6526cb8c4f10b408d7eaf047ee943027cb3868ac84d56`, matching the cloud build. The 678-resource manifest verifies before and after unpacking. All 856 materialized tracked source/resource blobs matched the fixed commit and remained unchanged after tests.

Independent extracted-package smoke started launcher PID 75702 and managed module API PID 75703. The API listened on loopback 50049, gateway on 50050. ps verified the owned child command and parent, lsof verified loopback, health returned the same PID. All three synthetic saved-view routes returned HTTP 200 and exact fixture values. Data and installation hashes/mtime remained unchanged across GETs. SIGHUP to our launcher exited 0, removed runtime identity, and child ps returned exit 1 (reaped). The candidate test additionally checked the outside sentinel, bad request identity, POST and foreign Origin rejection.

External-source simulation used a nonexistent PYTHONPATH and isolated Python startup. The independent launcher used a process-local unavailable HTTP(S) proxy with loopback bypass; no system proxy settings changed. This is dependency simulation, not an OS-level deny rule for all external filesystem/network access. Existing V4 and preview services were not stopped or modified. Current 54780 was not touched; no browser/app automation was performed.

Acceptance is limited to the independent readonly application package and synthetic engineering fixtures. Full 18-module acceptance, real business data, owner execution, collection and natural daily production remain NOT RUN. No product failure or remaining blocker in this scoped test.

# HK bridge V4 source-only candidate

Production remains BLOCKED. Empty TRUSTED_RUNS; real HK09 binding is unconditionally refused. HK16/CAS validation unchanged. No real scope, bindings, credentials, locks, calendar, market input or private paths are included. Historical HK666 does not authorize a current scope.

Public export changes: unbind original SOURCE and original HK09 helper path, explicitly refuse absent dependencies; preserve original SHA and review checks in their unreachable-until-bound paths. This package is not production-ready. Neither real source nor natural business acceptance is verified.

Run `python -B -m unittest test_public` or optimized `python -B -O -m unittest test_public`: 14 synthetic tests, including two missing-dependency refusals plus twelve tests using a synthetic timing stub. The stub replaces the absent original reviewed helper ONLY in the tests, so these tests do not verify that helper, its hashes/review, actual source availability or production locks. Original test files alone require absent dependencies and are not standalone public tests. No collector or network invocation.

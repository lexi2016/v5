# V5 Task 1 IPC/Test Harness Evidence — 2026-10-17

## Fixed source identity

- Integration parent commit: `01d93717905813705732161d4d79062ae5af2d99`
- Working branch: `fix/v5-integration-publication-test-harness-20261017`
- Relevant commits:
  - `e0bfaaf358631a67238bd6ca8cca58deebaf43b9` — initial harness fixes
  - `35829264a7edbeb1b7e54337433080a8fdd94a62` — rootdir-independent fixture import
  - `1e6a04e80abfdb34f498c1ac923a1a450d1c5234` — completion plan
  - `2df08080f51188c13197e78cfecff39bc878f301` — IPC EOF behavior
  - `8070607b5578f7bbdfa34de983b2d90f52d578e5` — regression test

## Environment

- Linux x86_64
- Python 3.13.5, pytest 9.0.2
- Project declares Python >=3.14; strict environment gate therefore remains BLOCKED.
- Frontend dependencies/vitest not installed.\n- Attempted official isolated interpreter install with `uv python install 3.14.3`; blocked by DNS/network failure fetching the official python-build-standalone release. No lockfile/guard was changed. Strict Python >=3.14 gate remains BLOCKED.

## Regression: stdout EOF while descendant retains stderr

Test: `V5/tests/test_manager_result_transport.py::ResultTransportTests::test_stdout_eof_does_not_wait_for_descendant_stderr_eof`

Before implementation:
```
FAILED
AssertionError: 3.234016446000169 not less than 1.0
1 failed in 3.31s
```

After implementation:
```
.                                                                        [100%]
1 passed in 0.68s
```

## Transport suite

Command:
```bash
PYTHONPATH=V5/src pytest -q V5/tests/test_manager_result_transport.py
```

Result:
```
...................
19 passed, 10 subtests passed in 2.27s
```

## Publication module status

The full six-test `integration_tests/test_plan_publication.py` module remains flaky at sequence level. One run with test-local progress prints completed **6 passed in 65.14s**. A subsequent clean run timed out after only the first two test dots; earlier bounded runs stalled at different worker calls, with the parent waiting in `_Pipe.read` and the child consuming CPU before emitting the first protocol frame. The progress prints alter timing, so that single run is evidence of a possible pass, not stable acceptance. Record full-module status as FAIL/BLOCKED until repeated clean runs reliably exit 0. Next investigate the pre-first-frame worker computation, especially the path after `load_owner()` and before the owner action; capture stage timing without changing source identity or relying on timeout increases. Do not weaken tests.

## Scope of this evidence

The IPC regression and transport suite are synthetic contract tests, not proof of real provider acquisition, natural scheduler operation, V4 feature parity, deployment, or V5 full acceptance. No production or V4 runtime was changed; PR remains Draft and unmerged.

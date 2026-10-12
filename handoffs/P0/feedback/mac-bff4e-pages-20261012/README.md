# Mechanically assembled P0 pages candidate: import failure

Fixed tested candidate: **bff4e140b7e92a09fbdd1a2814ce0e7872a2aa8c**.
Parent: 8f849c0e8686822e0e2ac631941529a31b60c4f3.
Branch: dev/v5-main-integration-20261012.

## Mechanical provenance

Applied exactly the two uniquely matching module_api.py old/new blocks from original diff at 1874f956; replaced example and test with complete original after-files at 8f849c0e. All three HEAD preimages still matched fixed baseline 37c35a3b. No guessed algorithm, import correction, design change or second source review.
Original materials and prior feedback remain inherited.

Frozen blobs:
- V5/src/v5_shadow/module_api.py: c09f4339e2a0427842a68c123320a5db7677992d
- V5/examples/m18_v2_module_api_config.json: 4ec9d3bd953e969f498686b3b569f87b40fa037f
- V5/tests/test_m18_v2_module_api_binding.py: 4ac75dfe26aaf63e0fd1b0346cb4e28484393359

Both after-file SHA256 values matched the delivery README. Source/test/example closure verified against the frozen candidate after tests (191 files). No local product repair.

## Actual executions

Existing Python/dependencies, new candidate/evidence directory. Paths below are sanitized logical aliases.

1. `<EXISTING_PYTHON> -m pytest -q -p no:cacheprovider V5/tests/test_m18_v2_http_bridge.py V5/tests/test_m18_v2_module_api_binding.py`
   - UTC 2026-10-12T07:45:45.236510–07:45:45.524886.
   - exit **2**; **2 errors during collection**, no tests executed.
2. `<EXISTING_PYTHON> <TASK>/http_canary_eefe978.py`
   - Reused the prior canary harness with PYTHONPATH pointing only to this candidate and existing dependencies.
   - UTC 2026-10-12T07:45:45.525248–07:45:45.573476.
   - exit **1** at import, before reading publication or starting a server.

Both fail with:

```text
V5/src/v5_shadow/module_api.py:20:
    from .m18_offline_v2_http_bridge import ROUTE as M18_ROUTE
ModuleNotFoundError: No module named 'v5_shadow.m18_offline_v2_http_bridge'
```

The exact missing import is retained as delivered; no alias or alternate filename was invented.

## Outcome

**FAIL at module import.** Descriptor GET, pages GET, same-run/six-identity HTTP checks and live read-only checks are **NOT_REACHED** for this candidate. No port was opened, existing publication was not modified, and V4/old services were untouched. No owner, collection, v2 build or browser operation. Prior 912941 publication and real bundle remain available for reuse after the author supplies a fixed candidate.

This feedback is an execution failure report, not acceptance of pages repair or the full P0 scope.

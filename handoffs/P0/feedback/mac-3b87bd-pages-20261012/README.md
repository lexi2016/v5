# Mac 3b87bd: author import correction applied; circular import failure

Fixed tested candidate: **3b87bd361c74ab65dfbbe7f997bafe356d01bf6b**.
Baseline/parent: 30566ebcd91f704139a6ed787e7987de628b8245.
Branch: dev/v5-main-integration-20261012.
Author instruction: https://chatgpt.com/c/6acc5cb3-7dd0-83ee-86d2-03437894dca3?messageId=8c41cd48-5302-45e1-a971-c6628e0ae0ce

Exactly one unique line replaced in V5/src/v5_shadow/module_api.py:
```diff
-from .m18_offline_v2_http_bridge import ROUTE as M18_ROUTE
+from .m18_v2_http_bridge import ROUTE as M18_ROUTE
```
New blob fd5a9d0399cc33088dde76f511b552f6da79120b matched local execution file. Other implementation unchanged. No independent repair.

## Actual commands

1. `<EXISTING_PYTHON> -m pytest -q -p no:cacheprovider V5/tests/test_m18_v2_http_bridge.py V5/tests/test_m18_v2_module_api_binding.py`
   - UTC 2026-10-12T07:52:03.385275–07:52:03.717763.
   - exit **2**, **2 errors during collection**, no tests ran.
2. `<EXISTING_PYTHON> <TASK>/http_canary_eefe978.py`
   - Existing harness with PYTHONPATH set to the new fixed candidate.
   - UTC 2026-10-12T07:52:03.718114–07:52:03.779878.
   - exit **1** at import; no server started and no GET executed.

## Runtime error

Actual traceback import chain:
```text
module_api.py:20 → m18_v2_http_bridge.py:8
→ m18_offline_v2.py:13 → m18_offline_pages.py:7
→ manager_result_transport.py:19 → module_api._open_directory

ImportError: cannot import name '_open_directory' from partially initialized module
'v5_shadow.module_api' (most likely due to a circular import)
```

The other pytest collection path starts at m18_v2_http_bridge and reports:
```text
ImportError: cannot import name 'ROUTE' from partially initialized module
'v5_shadow.m18_v2_http_bridge' (most likely due to a circular import)
```

## Outcome

FAIL at import. Descriptor/pages GET, six-identity HTTP verification and read-only live checks are **NOT_REACHED**. No port opened, no existing publication touched, no v2 rebuild, owner, collection, browser, trading, V4 or old-service change. Original publication/real v2 remain available. Raw command receipts remain local with exact stdout/stderr. This report preserves the first actual error and does not prescribe or apply a product fix.

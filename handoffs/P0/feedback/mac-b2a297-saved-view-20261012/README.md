# Mac b2a297: frontend build passes; real gaps request fails, browser unconfirmed

Fixed candidate **b2a2975832aa1cc9f3cc8efc62535c0f07099999**. Complete907-file tree materialized and Git blobs rechecked unchanged after execution. Existing d94c node_modules copied into isolated frontend; existing Node24.19.0/npm11.17.0 reused; no install/product edits.

## Actual frontend commands

From frontend/:
| Command | UTC start–end on2026-10-12 | Exit/result |
|---|---|---|
| npm run test:p0 | 10:12:37.947274–10:12:38.127844 | 0;12 passed |
| node node_modules/vitest/vitest.mjs run src/views/SavedManagerResultView.spec.ts | 10:12:38.128105–10:12:40.245619 | 0;1 passed |
| node node_modules/vue-tsc/bin/vue-tsc.js --noEmit -p tsconfig.cloud-product.json | 10:12:40.246153–10:12:43.071073 | 0 |
| npm run build | 10:12:43.071644–10:12:45.241411 | 0;Vite7.3.6,125 modules |

Full retained frontend suite and Python regression not rerun. These results do not imply real page acceptance.

## Independent service and actual client

Copied retained LOCAL_ONLY_config; added only /overview and /sections routes. All original roots,pins,identity,release unchanged.

Started API in its own OS process:
```text
PYTHONPATH=<FIXED_CHECKOUT>/V5/src <EXISTING_PYTHON> -B -m v5_shadow.module_api --config <LOCAL_SAVED_VIEW_CONFIG> --port 0
```
Actual API URL http://127.0.0.1:59917.
Started:
```text
V5_MODULE_API_ORIGIN=http://127.0.0.1:59917 npm run preview:p0 -- --port 54780 --strictPort
```
Actual preview URL http://127.0.0.1:54780. Both are now stopped.

External harness command `<EXISTING_NODE> real_saved_view_b2a297.mjs`, exit **1**. It imports the **candidate's actual M18SavedClient**, using fetch through Vite proxy (not a replacement client or mock). It compares real descriptor identity and overview manifest/profile with retained binding. No in-process Python oracle or Reader.

Observed:
| Request | HTTP | Bytes | Time |
|---|---:|---:|---:|
| / and /manager-selection/ HTML |200 each|not recorded|not recorded|
| descriptor |200|804|5ms|
| overview |200|6638|4466ms|
| sections summary |200|1321|4326ms|
| sections gaps, first page |**409**|90|2734ms|

Both HTML titles: **V5 经理已保存结果**.
Overview returned55sections/117content chunks. Summary had1entry loaded,0not_loaded.
Next gaps request raised original client error:
```text
M18_HTTP_409: MODULE_RESULT_INVALID
```
Internal backend code not diagnosed in this task. Do not assume a resource cause from the generic response.

Intended remaining gaps page1/materials/market_screen/stocks/us_mapping requests **NOT_REACHED** after first failure. The recorded client requests used only descriptor/overview/sections; no content /pages or whole-response endpoint was requested.

## Browser boundary

Supported local Chrome createBrowserTab attempted the exact preview run URL once with20-second timeout. It returned `js execution timed out; kernel reset, rerun your request` after21.65seconds. No rendered DOM/screenshot evidence was obtained. The command could have opened a tab before timing out; its page/network state is unknown and not included in the client request count. Therefore HTML HTTP200 and simulated Vue test are **not** a claim the real page was seen. Refresh/navigation/rapid interaction/recovery/responsive behavior **NOT_VERIFIED**.

## Cleanup and outcome

Because real semantic reading failed and page verification was unavailable, both task-owned terminal sessions received Ctrl-C and exited (reported exit1; API KeyboardInterrupt). No old process operated on; no new preview retained or offered as live.
At10:14:50.335228UTC, bundle/publication SHA256+mtime snapshots matched; all907source blobs remained unchanged.
No v2 rebuild, publication, owner, acquisition, trading, credential/security change or old-port use.

**FAIL real saved-view acceptance at gaps GET; frontend build/typecheck/new tests PASS.** No full P0/18-module acceptance. Raw logs/local private config remain on Mac; no business values or private paths uploaded.

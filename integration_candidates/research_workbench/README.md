# V5 独立研报决策台接入候选

这是原 M04 研究资料 + P0 页面/GET 接线的完整候选，不是 M18 新算法或 M19。V4 现役服务、目录、调度、BUY gate 和凭据不变。此目录不表示已在 Mac 发布。

## 固定来源

- 用户指定 V4 `codex/research-workbench-buttons-20261013-r1` / `6e0134ef0daaf6525f12176e12b3fe8ceca606e0`。该提交的五文件增量已上传但未合主分支、未部署8873；本候选复用其三栏研究UI/筛选改进并在 V5 独立构建测试，不能称 V4 新版已上线。
- M04 完整只读原owner依赖：`lexi2016/v5@8266c6ed9606b0912328670c7411743a85af5727` 的 `integration_candidates/M04_capture`。`RELEASE.json` 原字节 SHA256 `156d7f1ab030a8c7427a7c079eef62ed6615071d37e8c9fd41efa1d61ffdcbec`。
- 共享前像：M14 `fac269ade842eb1d9b54c604b77091b0cd58bd44` 的 `integration_candidates/M14_saved_page/files`；main.ts 为 P0 `2a124b87bf64793f8c0226a049ae2ac9700c9b86` 已读原文件。静态GitHub前后 SHA 在 PREIMAGE_MANIFEST.json。最新Mac实读四文件在 MAC_OBSERVED_PREIMAGE.json；main一致，其余三文件是c7b+fac的组合，与单独fac源码不同。因此静态after绝不可覆盖现役；apply_candidate读取新隔离副本实际内容，仅移植唯一锚点增量。Mac实读SHA已由主控核过，不把分支名当运行身份。

## 代码与用途

- `frontend/src/research-workbench/`：完整隔离 Vue 研究阅读闭包，避免修改现有经理消费者所用 research_lane.ts。保存原三栏、8种筛选、公众号入口、EXACT/LATEST、原文/获取时钟、状态/缺口和窄屏样式；新增明确“归档原文”来源，全文以纯文本显示，保留原字段，不把归档自动分类成早盘、星球、股票结论。
- `bridge/research_workbench_readonly.py`：同一个 V5 source_bundle module_api 中的 GET桥，独立子进程调用固定 M04 `launch.py lane`，不调用 capture/build/import/model，不新建常驻服务。执行前校验完整manifest源字节，拒symlink、未列代码和pyc；30秒限时。仅允许 exact research_date 或显式LATEST，不隐式跨日回退。
- `apply_candidate.py`：只在指定隔离 checkout 对六个共享文件做唯一锚点变化，然后复制独立namespace和桥；不整体覆盖fac/root，不改任何运行配置。对主控实核四文件强制精确SHA准入；未知前像或锚点不唯一均在写入前拒绝，原CRLF/LF及所有未改字节保留。现有M14/其它proxy及binding保留。
- `before/`、`after/`、`integration.patch`：共享源码完整前后像和精确差量。用于检查，不能盲目用after覆盖新现役文件。
- `configure_binding.py`：从现有source_bundle配置产生新文件，只追加两个路由和M04绑定，保留所有既有模块、release_id、data_root及其它bindings；output必须尚不存在。

## 独立接口

GET `/api/v5/research/lane?research_date=20261012` 为EXACT；省略query为LATEST。返回 `v3_5.research_lane.v1`，真实研究日期、原来源引用/SHA、`archive_materials.articles`正文及取得时点、原缺口、安全false。只提供归档时 `LIVE_PERIPHERAL_ONLY`，股票主线/质量/小时研究未生成明确保留；不是研究结果全覆盖。原v1档案的未知取得时间与未知run仍保留。

GET `/api/v5/research/wechat/materials` 当前显式 `NOT_CONFIGURED`。不伪造公众号归档、正文、索引或成功零结果；不会请求运行中V4。没有索引时详情/下载没有可点击条目，未提供对应动态路由。M11盘中结果未绑定时保留未生成，不等待六槽齐才读已有材料。

## Mac 集成流程（仅唯一主控执行）

1. 固定当前 c7b + fac269 健康组合，保存当前release/config/预览选择与 main.ts、module_api.py、vite.config.ts、SavedManagerResultView.vue SHA。复制到全新隔离候选，保留M02、M14和其它已有路由。不能对V4或活动release直接运行apply。
2. 将本固定commit完整目录，以及固定M04依赖包落到V5隔离源码目录。校验 M04 RELEASE SHA；不要复制运行产生的 __pycache__。M04包必须来源于固定源码，不依赖V4路径。
3. `python3 -B <本目录>/apply_candidate.py --isolated-checkout <隔离V5根>`。检查打印前后SHA及 diff；如当前前像漂移，只保留精确增量和原M14变化，不套整棵after。
4. 已授权独立V5保存归档根生成原 `archive_binding={root,files}`（relative→原SHA），不重采、不改档案、不制造时间。用固定M04 `python -I -B <M04包>/launch.py lane --research-date 20261012`，stdin输入binding，先核同原18篇/原SHA/53范围外错误边界；这一步是只读，不用capture命令。
5. `python3 -B <本目录>/configure_binding.py --existing-config <现配置> --m04-package <固定M04包> --python <现Python> --archive-binding <binding.json> --output <新配置>`。它解析Python实际路径，保留其它配置；核新旧差异只有两个routes与新binding。保留当前 V5_SOURCE_API_ORIGIN，不猜端口，不接8873。
6. 在隔离checkout/frontend运行现依赖 `npm test -- src/research-workbench src/views/SavedManagerResultView.spec.ts src/views/SavedManagerResultView.navigation.spec.ts src/views/SavedManagerResultView.m14.spec.ts src/components/M14SavedRebound.spec.ts`；`npm run typecheck`；`npm run build`。不升级依赖、不安装到V4。
7. 在临时loopback启动原module_api隔离候选，验证lane EXACT/LATEST/缺日期、公众号NOT_CONFIGURED、POST405、重复参数400、错误身份409、原档案字节无写、其它所有既有路由一致。已有公开HTTP owner结果不重新执行。
8. 唯一Mac发布者按现有切换流程部署组合。入口 `/?view=research&date=20261012`；默认经理保持，经理导航研报链接现在可用。检查完整原文、来源SHA、未知时点、按日/显式latest、筛选>42条回归、窄屏和Back/Forward。真实页与HTTP同日/同原来源，断开V4仍可读。现场/native visual验收在Mac完成，本目录不冒充已完成。

## 回退与停止

任一既有路由/M14输出/源身份变化、日期串读、未知显示成功、出现V4请求即停止发布。回退到此前健康release及其原config/preview选择，不改原数据、不重置源模块、不删历史，不将候选文件覆盖到V4。apply只运行于全新隔离checkout，失败保留候选排查；不要在部分已应用目录重复跑。

## 验证边界

定向研究/入口/桥/HTTP/原冷reader及整合typecheck/build结果见 VERIFICATION.json。所有业务输入为合成离线fixture；没有真实provider/model/原owner生产、没有Mac部署或自然触发。整库UI有已复现缺fixture等失败及一次并行负载下5000ms导航超时，必须单列，不能声称全库绿。当前能够交付已有合法V5保存资料的完整阅读链；完整M04来源采集、M11盘中研究、公众号索引及自然日生产各自仍按原模块验收。

### M04 dependency pin update (2026-10-13)
The new M04 package changes only the synthetic test launcher for interpreter paths containing spaces/quotes plus its report, log and RELEASE (482 files / 481 manifest entries; owner reports 22/22 cloud tests). Business runtime, launch.py, research_lane.py and original owner bytes are unchanged. The research tests above were run against the previous 9736bf2 dependency; they are historical evidence, not a claim of new Mac verification. Only dependency/configuration pins and this package manifest changed. Mac isolated verification remains the deployment gate.

### Rapid date selection fix
Apply only in a new isolated copy of the deployed d3 research checkout: `python -B <candidate>/apply_date_queue_fix.py <isolated-v5-root>`. All five before/after identities are checked before any write; unknown originals or existing new files are rejected. This changes only the isolated research namespace; original main/Vite/manager/API/SHA guards remain untouched. `date_queue_fix.patch` is the reviewable diff.
One lane GET stays in flight. Selecting another date invalidates the displayed result immediately and replaces the single pending selection. The last selection starts when the old read settles. Repeated identical in-flight selections are deduplicated; explicit retry after completion is allowed. Obsolete results never display. HTTP 503 alone permits two retries (250ms then750ms), never overlapping; other errors exit immediately. Changing date interrupts obsolete backoff. Unmount cancels pending work/timers and ignores active completion without aborting the server reader. Permanent503 shows an explicit failure and re-enables manual reread. No capture/model/provider invocation or worker expansion.
Cloud focused research regression:51/51 PASS, typecheck exit0. These are isolated cloud tests, not a deployment claim for this fix. Prior d3 Mac deployment evidence remains in the P0 deployment receipt.

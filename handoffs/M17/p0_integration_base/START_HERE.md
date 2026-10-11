# M17 独立 15:55 late 接线：完整接口源码审阅基线

本目录用于原 M17 会话继续提交独立 manager_close_recapture 的 15:55 晚间接线完整代码。它是接线审阅基线，不是完整发行物，也不代表接线功能已经完成。当前运行候选的代码身份仍为 fe0a1890ebe59b476af6c8a0e1878fca059c24f4；本补件只新增 handoffs 参考目录，不改现有运行文件。

## 先读取完整文件

- V5/src/v5_shadow/run_ledger.py
- V5/src/v5_shadow/daily_dispatch.py
- V5/src/v5_shadow/daily_tick.py
- V5/src/v5_shadow/composition.py
- V5/src/v5_shadow/cli.py
- V5/src/v5_shadow/worker.py
- V5/src/v5_shadow/module_api.py
- V5/src/v5_shadow/daily_owner_adapters.py
- V5/src/v5_shadow/manager_plan.py
- V5/vendor/daily_schedule_baseline/contracts/runtime_workloads.json
- integration_tests/test_p0_ledger.py
- integration_tests/test_plan_publication.py
- saved_product_readback.py
- schedule-binding.json

SOURCE_MANIFEST.json 给出每件完整原路径、固定来源commit、原SHA/blob、当前SHA/blob，以及四件精确差分后像的来源。本目录中的 integration_tests、probe和schedule-binding保持它们相对于原 P0 overlay 根的路径；其完整远端原路径也在清单，不要误放进 V5/src。

## 同版本来源与边界

10件核心前像都来自 lexi2016/v4@6daed6271313b5ae5324c8948f163258ab8d1fa3 的同一个 V5 源树（tree 5a568d3d8bd653cc33c1ab35750871910c3e700d）。其中 run_ledger、daily_tick、daily_owner_adapters、manager_plan 已精确应用 lexi2016/v5@e6092e769d0d69fdbc731d338885c0b399f5e265 的 integration.patch；每处hunk原文零模糊匹配，四个后像Git blob与patch index一致。其余6件核心文件及4件overlay辅助件保持原字节。

原完整依赖树仍可只读定位：
https://github.com/lexi2016/v4/tree/6daed6271313b5ae5324c8948f163258ab8d1fa3/V5
固定原差分：
https://github.com/lexi2016/v5/blob/e6092e769d0d69fdbc731d338885c0b399f5e265/integration_candidates/P0_20261011/integration.patch
M17原late owner及reader运行候选：
https://github.com/lexi2016/v5/tree/fe0a1890ebe59b476af6c8a0e1878fca059c24f4/V5/vendor/close_discovery_baseline

b8b524edc8922d87a7c8f5b426709d42ae619bb1 是 Mac 本地整合commit，不能构造它在远端仓库的源码链接。Mac已向协调者确认四patch后像加module_api的5件身份，以及这4份overlay辅助件，与本地冻结版本一致；本补件只使用已核远端原件/差分，不包含Mac日志或本机新包。

不要用 M17 老 handoff source 中的 module_api.py 替换本目录版本：它缺少 manager 的 X-V5-Workspace-Access: READ_ONLY 响应头。本目录必须保留该头；run_ledger也已是P0六lane后像，不是旧四lane前像。

## 本轮需要交付的实际代码

在原 M17 范围，基于本目录完整接口与 fe0 原late owner，完成独立 manager_close_recapture 的15:55晚间接线。保留原采集算法、late产物/receipt/snapshot/overlay身份、原reader与所有拒绝语义；不得把它冒充15:30或全部M17闭环。

请先实际读取这些完整文件和当前运行候选，再交完整候选源码、精确前后像/差分、来源与路径映射、新增/修改测试及实际执行记录。缺运行依赖时给精确文件/工具错误，未跑标NOT_RUN；不能继续只交片段、接口名或未来计划。

接线须与既有ledger、dispatcher/tick、worker/composition及原只读消费入口核对真实签名和数据身份；仅添加lane名字不算执行owner已经注册。现有六lane与P0保存/发布合同必须保持，不改原策略或现有其他业务owner。需要共享接线变更时在本M17候选中交精确完整变更和集成请求，由协调者核前像后整合；不要推P0整合分支、main、其他模块分支或V4。

所有本模块后续代码工作通过 dev/m17-github-handoff-20261011，回传真实固定candidate commit与diff。不要把本次材料发布计为代码实现完成。工程fixture、原late子链验证、完整日常接线、真实数据/自然运行分别报告，不能互相代替。不交易、不联网采集真实业务、不扩权限/凭据、不自行部署。


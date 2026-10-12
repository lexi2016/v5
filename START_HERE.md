# V5 主框架源码整合底座

这是私有 lexi2016/v5 的独立开发分支 `dev/v5-main-integration-20261012`，供“V5 P0｜主框架与模块集成”接续。它不是M19。

## 当前交付

- 固定原底座：lexi2016/v4@6daed6271313b5ae5324c8948f163258ab8d1fa3 的 V5 子树 5a568d3d8bd653cc33c1ab35750871910c3e700d。
- 原772件的source-core计划694件；另暂不复制6件含个人机器路径元数据的源说明/测试/producer，实际保留688件底座原源。原V5/docs/及V5/handoff/共78件历史文档/运行记录/预览包仍全部排除。
- 在该底座按已指定白名单机械叠加P0、M13、M14、M18容量、assembly及v2原字节，共42次选定映射，实际发布711件源码/工程材料。
- 详细逐路径来源、Git blob和bytes见 [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json)。该清单区分原donor与新目标，不假造统一来源SHA。
- P0根辅助材料保持原布局：integration_tests/、saved_product_readback.py、schedule-binding.json；V5运行源码在V5/。
- manager_plan.py唯一采用0b3495容量版本，避免M13较早文件反向覆盖；M13其余8件保留。publisher未合并或改写任何产品逻辑。
- 分支继承核实main@2489ea1e04a26a9e2f318f498ac3f5f8c970fe48；原main、V4及模块分支不变。

## 明确未完成

本次只做来源/字节传输与机械组装，**NOT_RUN**。没有运行产品或测试，没有部署，没有安装依赖、服务或调度。既有模块验收不自动构成本新组合的验收。

18模块尚未全部统一注册、启动；真实每日调度和自然窗口准入仍需接续。V5/ui仅发布原29件前端overlay中24件，不是完整前端应用；不能称整个前后端已完整可运行。manager 30MB读回、离线v2通过也不等于本底座的CAS/HTTP/页面/daily已完成。

## 下一步原主框架Chat任务边界

在本独立分支继承实际HEAD，读取完整源码后复用已有模块接口，交统一启动、18模块显式注册、现有日调度接线与主页面接入的完整代码和测试。不要另造业务算法或改变模块资格/PIT语义；不要覆盖main/V4/其他模块，不执行交易、不触凭据/安全设置。代码由原Chat完成自审后，现有Mac直接集成测试反馈。任何真实执行/发布结果单独记固定commit，不能把此源码底座的材料数量算功能完成。

## 明确缺件与来源身份

以下6件原文件暂不复制；没有更改其字节后冒称原文件，也没有复制其中的本机目录值：

- `V5/producers/archive-acquisition-v2/source/ops/run_zsxq_hourly_delta.py`
- `V5/ui/manager-workbench/NEXT.md`
- `V5/ui/manager-workbench/source/apps/web/src/api/managerWorkspace.announcementReview.spec.ts`
- `V5/ui/manager-workbench/source/apps/web/src/manager-selection/__tests__/workspaceAfterReadback.spec.ts`
- `V5/ui/manager-workbench/source/apps/web/src/manager-selection/catalystObservationPanel.runtime.spec.ts`
- `V5/ui/manager-workbench/source/apps/web/src/views/ManagerSelectionView.spec.ts`

原 acquisition manifest 保持原字节，仍绑定缺失producer的原SHA。此底座不能直接称为完整可运行采集闭包。P0后续如做可移植化，应保留历史donor身份，显式记录派生前后SHA并更新当前producer manifest的两处after_sha256；不得静默重写冻结vendor PIN。现有合成注入接口和测试调用亦需保留。具体各文件原donor/blob/bytes及排除原因见SOURCE_MANIFEST.json的privacy_exclusions。

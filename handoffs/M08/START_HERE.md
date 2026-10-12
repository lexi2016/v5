# V5 M08｜港股阶段选股

## 2026-10-12 原已保存结果独立只读增量

原 SelectionStore 已保存三件可按固定原字节 SHA/长度搬入独立 V5 私有 recorded root，再用仓库内冻结原 reader 精确 run 冷读；移走旧源不影响读，GET 只读已发布响应。入口与命令见 [M08_HK_OBSERVED.md](V5/docs/M08_HK_OBSERVED.md)，SHA 与正反补丁见 [独立增量交付](delivery/M08_OBSERVED_20261012/)。这是 OWNER_RESULT / HISTORICAL / OBSERVED_ONLY，不重新执行算法，不把历史输出当原行情输入，natural/PIT/formal 均为 false。

基于 `4053d4e89101b8d47861f48813686234dc063ba9` 保留全部 Mac 反馈：前一 M06 适配 13+3 项以及 10/12 原池 100 行真实 mapping-only 均通过。本次历史观察新增 21 项隔离测试通过，原 90 项未重跑；真实三件迁移与页面部署仍待 Mac 验证。M06/producer 原有实现和身份函数不改。

## 2026-10-12 M06 原映射接线增量

在 Mac 固定反馈 `bfdb43fd3ac40f2134635e53bec22619fbaf9f97` 后补齐 M06 原冷读结果的字段适配：保留原行，直接消费 `symbol / pool_rank / pool_score`，不再错误要求 pool 的 `preselect_lane`，不生成阶段 lane。新增本地 JSON 适配命令、原 owner/store/冷读正负测试，见 [M08_M06_ADAPTER.md](V5/docs/M08_M06_ADAPTER.md) 和 [增量交付 SHA/正反补丁](delivery/M08_M06_ADAPTER_20261012/)。

固定 Mac 反馈已记录上一候选 90/90 工程测试通过；本增量仅运行定向测试，未重跑该 90 项，也未执行真实入口或改动历史反馈。真实同日成员、时间、单位与行情原证据仍须独立满足；不允许用 10/13 池改日期配 10/12 阶段。以下首轮交付状态为历史记录。

## 2026-10-12 原 owner 工程候选交付

默认港股输入 → 原普通/竞价/Stage8 owner → 原 SelectionStore 三件 → 独立精确 run 冷读链已实现，并提供现有只读模块 API 发布适配器。完整代码、边界、测试及 Mac 单次验收入口见 [M08_HK_STAGE_HANDOFF.md](V5/docs/M08_HK_STAGE_HANDOFF.md)；固定前像/后像、真正正反 patch 与核验见 [delivery/M08_20261012](delivery/M08_20261012/)。

这是合成/录制输入工程候选，不是 M08 完整产品验收。正式资格/PIT、Mac、活动页面和自然调度尚未验证；共享 ledger、V4 与其他模块未修改。下列原材料说明保留作历史依据，原“仅材料字节核验完成”不再描述本次新增工程实现。

本分支材料属于原18模块的M08/P3。用户已授权继续编码，不再等逐模块范围确认，不新增M19。

## 先读

1. [完整本轮任务](handoff/M08_CHAT_20261011/PROMPT_FOR_CHAT.txt)：必须交完整after、真正反向patch、前后SHA、定向测试原日志，默认producer→不可变store→独立reader→可接API/UI/调度的实际代码。
2. [来源事实与边界](handoff/M08_CHAT_20261011/SOURCE_FACTS.md)。旧ZIP只作身份备查，默认直接读本分支固定commit的工程树。
3. [原109文件清单](handoff/M08_CHAT_20261011/SOURCE_MANIFEST.json)与[补31文件清单](handoff/M08_CHAT_20261011/SUPPLEMENT_MANIFEST.json)。源码路径直接位于本模块目录handoffs/M08/V5/和handoffs/M08/handoff/下，所有原字节未修改。

## 身份与实施

固定donor=lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477。本分支commit是本次材料交付身份，不是Mac现役、候选测试或部署完成证明。请用发布者回传的固定commit，不跟随可变分支头推断版本。140份源码已核Git blob/SHA-256/bytes且无路径覆盖。

真实未来交易日不是编写代码的前置；先复用已有原历史fixture验证，自然准入与真实运行另记。共享文件修改交隔离integration_candidates/M08/，由唯一集成者核当前前像后合并，不能覆盖其他模块。保留V4/8910，不交易、不改BUY门、不扩凭据/安全/网络权限。

当前仅材料字节核验完成；本轮产品代码/测试、Mac、API/UI、自然运行均未执行。

## 最新GitHub交付约定（优先）

本轮GitHub-only：在私有lexi2016/v5的dev/m08-github-handoff-20261011分支直接读取工程源码、编写并提交本模块完整实现、测试、文档和原始测试日志。此授权替代旧材料中“ZIP优先”“只能交方案”“不得写任何远端分支”等流程限制；原算法、业务范围与安全边界不变。仓库模块根为handoffs/M08/，文中V5/与handoff/均相对此根解释。

共享文件仅以integration_candidates/M08/隔离候选交付，由唯一集成者核当前前像后处理；不修改main，不合并，不覆盖其他模块，不改V4，不执行交易，不扩大安全或凭据权限。本次首次发布仅为材料交接，不能当作业务代码已经实现、测试或上线。

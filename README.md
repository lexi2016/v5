# V5 独立研究与选股系统

本仓库包含 V5 后端、前端、模块 owner 闭包、来源合同、测试和历史交接证据。**源码存在、测试通过、部署成功、真实输入合格、自然运行和完整验收是不同状态，不能互相替代。**

## 从这里开始

1. **仓库结构与维护规则**：[V5 Repository Map](V5/docs/architecture/REPOSITORY_MAP_AND_ORGANIZATION.md)
2. **固定集成源码**：[dev/v5-main-integration-20261012 @ `01d93717905813705732161d4d79062ae5af2d99`](https://github.com/lexi2016/v5/tree/01d93717905813705732161d4d79062ae5af2d99)
3. **当前交接入口**：[2026-10-16 START_HERE](handoffs/20261016-chat-completion/START_HERE.md) · [完整执行 Prompt](handoffs/20261016-chat-completion/PROMPT.md)
4. **统一执行计划**：[PROJECT_EXECUTION_PLAN.md](V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)
5. **原始集成来源清单**：[SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) · [P0 集成任务书](P0_INTEGRATION_TASK.md)

> 注意：仓库默认分支 `main` 不是完整 V5 集成基线。开始任何开发前，应读取目标分支最新 HEAD，并记录所用的完整 commit SHA。

## 目录职责

| 目录 | 用途 |
|---|---|
| `V5/src/v5_shadow/` | 后端运行模块、owner adapter、调度、账本和 API |
| `V5/contracts/` | 输入/输出合同、来源 manifest 与 PIN |
| `V5/vendor/` | 冻结 owner 源码闭包；按 PIN 校验，不原地改写 |
| `V5/source_owners/` | 来源 owner 原件及其闭包 |
| `V5/tests/` | 后端单元、合同与模块回归 |
| `frontend/` | Vue/Vite 应用、API 适配、页面和前端测试 |
| `integration_tests/` | 跨模块/平台集成测试 |
| `integration_candidates/` | 隔离候选，不等于正式集成代码 |
| `handoffs/` | 原始交接、测试回执、失败记录和恢复线索，保留历史 |
| `V5/docs/` | 架构、执行计划、操作说明与验收标准 |

完整边界、原 M01–M18 对应关系、候选状态和安全整理规则见 [Repository Map](V5/docs/architecture/REPOSITORY_MAP_AND_ORGANIZATION.md)。

## 模块与阶段

- **P0：** 共享 API、不可变产物、run ledger、调度、发布、恢复和回滚底座。
- **P1：** M13 公告、M14 超跌、M15 美股到港股映射，接入 M18 经理工作台。
- **P2：** M01/M02/M03 行情与来源，M05/M06 预选池。
- **P3：** M07/M08 阶段选股，M09/M10 收盘复盘。
- **P4：** M04 研究归档、M11 盘中研究、M12 视频复盘、M16 公开资料任务、M17 尾盘发现。
- **P5：** 固定版本全量回归、适用交易日自然接续、独立启动和回滚验收。

P0 不是 M19；B01 是 M18。模块、调度 lane、API 路由和页面不是同一个概念。

## 验证要求

任何交付均应附固定 commit、环境与依赖、实际命令、exit code、日志位置/哈希、失败与跳过项。单元测试、HTTP/DOM、原生视觉、保存冷读、部署、真实输入和自然运行分别报告。

不要删除或弱化失败测试以制造绿色结果；不要把合成输入、手动恢复或旧回执写成新日自然通过。

## 安全边界

- 保留 V4，不覆盖 V4 或修改现役服务。
- 仅研究，不交易、不下单；不修改 BUY 门、策略算法、PIT、资格或风险语义。
- 不扩大凭据、系统权限或真实数据访问。
- 未经独立验证，不合并候选、不部署、不宣称 V5 全部模块完成。
- 2026-10-15 停止任务的 24 个未提交文件尚未被原始补丁和 manifest 重新取回；不得凭描述重造后冒称恢复。

# M16 GitHub 开发入口

本分支是独立私有仓库 `lexi2016/v5` 的 M16 首次实现材料交接。源码、原任务书和逐文件来源均直接展开，可在 GitHub 阅读；无需以 ZIP 作为主输入。

## 先读这些文件

1. [本次完整任务书](TASK_ORIGINAL.txt)
2. [原始来源清单](source/SOURCE_MANIFEST.json)
3. [原交接说明](source/handoff/PROMPT_FOR_CHAT.md) 与 [源码映射](source/handoff/SOURCE_MAP.md)
4. [原验收要求](source/handoff/ACCEPTANCE.md)
5. [完整原工程树](source/)：`fixed-f7cb731c/` 和 `reference-plans/` 原字节保持，来源 commit、path、Git blob、SHA256 见原 manifest。


## 最新交付方式与授权边界

用户最新指令要求通过 GitHub 工作。原任务书中“ZIP 为主要输入”“本 Chat 不得推送任何分支”等旧交付方式限制由本段更新；其业务算法、验收约束、只读共享边界仍有效。

- 仓库：`lexi2016/v5`，本模块开发分支：`dev/m16-github-handoff-20261011`。可以在本独立分支提交本模块完整实现、测试和脱敏工程日志，并返回真实固定 commit、diff、准确文件映射。
- 如果当前 Chat/工具没有该仓库读写权限，必须明确说出实际限制。不得假造读取、推送、commit、测试结果或 Mac 验收；不要用反复上传 ZIP 替代已有可读的 GitHub 工程树。
- 仅修改本模块授权写根。其他模块、共享 owner/API/UI/调度文件只读，必要跨模块整合改动独立放在 integration-candidate 并提交 INTEGRATION_REQUEST.md，由唯一整合者核当前前像。
- 不修改或合并默认 main，不合并其他模块分支，不改 `lexi2016/v4`、V4 运行系统、原数据或原交易门。禁止交易，不读取新凭据，不扩大系统安全权限。
- 所有本次发布材料均位于 `handoffs/M16/`，来自已核共同基线 `2489ea1e04a26a9e2f318f498ac3f5f8c970fe48`；未带入 M09 业务候选。
- `source/fixed-f7cb731c/V5/` 是原 donor 路径，不能凭猜测直接认定新仓库最终根。交付 REPO_PATH_MAP.json，逐项写清 donor、after、目标路径与整合待核。

## 证据状态

本提交只证明材料已放入 GitHub，不是业务实现、部署或验收。产品测试、Mac 实测、API/UI、自然触发和完整验收均未在本发布步骤执行。实现候选必须另报固定 commit，随后由既有 Mac 环境独立验收。

[PUBLISH_MANIFEST.json](PUBLISH_MANIFEST.json) 记录每个交接文件的字节数、SHA256 和 Git blob。原来源文件保持原字节；旧文档作为历史材料保留，发生交付方式冲突时以本入口为准。

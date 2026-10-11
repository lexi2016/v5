# M09 A 股收盘复盘完整候选交付

本交付已经实现 M09 私有 daily、完整冻结原链调用、不可变保存/独立读回、两槽回执、故障恢复、A 只读投影以及单日回滚。代码、失败用例、原算法逐字段对照和实际产物均随包提供。**本候选完成工程交付；Mac 环境认证、现役普通 API/原 ReviewView 接线和自然运行验收仍未完成。**

## 固定身份与源码范围

- 目的仓库：独立私有 `lexi2016/v5`；开发交接基点 `782bfc9ae91ff9cfe897afffc52aad43b7c1b78c`。
- 原源码只读出处 F：`f7cb731c384ee6890a87d16c19a5b5a621779477`，来源仍标为 `lexi2016/v4`。
- 原 R3 ZIP SHA：`15ef8fb20cbc7d0a306d066bf43ec9377726d22d7a08b3efcb65d68afc0d8c3f`，7424890 bytes；封包原字节未改。
- `before/` 为全部 52 份固定源码；`after/` 为完整 77 文件候选，共新增 25 文件，没有修改/删除原 52 文件。`BASELINE_PATH_VERIFICATION.json` 使用完整 F 的 2746 条、不截断远端树再次证明原 52 Git blob 一致及 25 个新增路径不存在。
- 仅为本地装配/检验创建的源码切片基点是 `e45aee9e185dda6f9d4b5032e6d60231cce27809`，最终本地源码提交是 `4f874c23daaa96787ebeebb5b772079635193cb0`。它们不是原 F，也不冒充最终 GitHub 提交。
- 最终 GitHub 版本由包含本交付的完整提交确定；同版本离线包的外层 `EXPORT_VERIFICATION.json` 给出实际返回的 commit、tree、逐文件身份及完整核验结果。

GitHub 根目录保留 `V5/...` 与原 source 相对路径；本目录的 `after/` 提供完全相同的交付副本，路径映射见 `REPOSITORY_LAYOUT.json`。原交接入口/内 ZIP 的旧状态保留历史原字节，新实现状态以本交付和外层导出回执为准。

## 先看哪些实体

| 内容 | 入口 |
|---|---|
| 完整 after 和调用合同 | `after/V5/docs/M09_A_CLOSE_HANDOFF.md` |
| before/after SHA、动作及原因 | `CHANGED_FILES.json` |
| 可逆补丁与实际整树核验 | `forward.patch`、`reverse.patch`、`PATCH_VERIFICATION.json`、`logs/patch/` |
| 原闭包、依赖、声明与实际环境 | `SOURCE_DEPENDENCIES.json`、`ENVIRONMENT.json` |
| 输入原件、真实缺口与新输出清单 | `INPUTS_MANIFEST.json`、`OUTPUTS_MANIFEST.json` |
| 原算法完整比较与运行实体 | `ALGORITHM_PARITY.json`、其中引用的完整 oracle/candidate 数据 |
| 当前固定候选测试与未跑项 | `FINAL_VERIFICATION.json`、`logs/`、`evidence/independent_review/` |
| 独立 Mac 验收/发布/回滚 | `MAC_ACCEPTANCE.md`、`tools/` |
| 唯一集成者的共享文件请求 | `INTERFACE_REQUESTS/`，三个函数级请求及 16 个真实前像 |
| 当前候选真实生成的工程产品 | `outputs/engineering/`，包括完整 store/run/generation/receipt/投影 |
| 未清洗真实输入的两槽拒绝结果 | `outputs/historical_rejection/`，包括请求、准入错误、失败回执和 MISSING 投影 |

## 实现行为与保留含义

原 producer → model → close chain → review builder → AShareReviewStore 以 16 份原字节闭包运行。导入使用 M09 私有命名空间，不污染 `domains/contracts/infrastructure`。原内容字段和数组顺序不做归一化删减；涨跌平守恒、行业/角色指标及排序、分数/理由、风险态势、情景树和原拒绝/未知/研究资格保留。固定概率 0.12 / 0.28 / 0.60 不声称校准，LLM 禁用，观察池仍 WATCH_ONLY，`core_stocks` 不晋升，没有 BUY、订单或生产权限变化。

daily 在调用前验证完整声明集合和每一行的日期、代码、8 列、有限数值及名称/行业，拒绝原模型可能静默过滤的坏行。声明集合与全市场资格分开；来源 capture/acquired/available、模型历史 15:30、严格 15:00 PIT、两槽 cutoff 和实际执行时间分开记录。

两个触发槽各有回执。完整计算身份相同可复用同一不可变 run；来源、可用证据、配置或实现变更则新建。晚到证据只进入真实 available_at 允许的槽；缺视频、阶段和语义消费证据保留 PARTIAL。新 run 用独立原 store；generation 只在原 reader 和全部 SHA 链核验后准备发布，且必须有匹配的成功触发回执才可对外读取。

正常异常、原 store 三步写入中断、超时、读回不一致、CAS 冲突和进程硬退出均有验证。进程在 head 切换后、成功回执前退出时，GET 服务同日已验证 predecessor；下次任务在日期锁内恢复并记账。`latest_attempt` 显示后续 FAILED/UNKNOWN，不遮盖正在服务的成功身份。磁盘代码替换或预先缓存的共享 helper 与执行字节不符时拒绝并要求重启/rebase。

## 实际验证结果

当前固定候选的完整 unittest 运行 **125 项：121 PASS，4 SKIPPED，0 失败，0 错误，exit 0**。四个 skip 是真实 pyarrow 的 PARQUET 工程测试；当前 Linux 没有 pyarrow，不能算通过。候选中提供了这些测试，Mac 可用其原环境直接运行。独立审查另有 **6/6 PASS**，覆盖硬退出、四种保存输入破坏、daily/共享 helper 执行身份以及 API raw digest 绑定。各 RED、后续 GREEN、固定候选回归完整日志分开保存。

真实原件已经经过两次实际 historical daily 准入和失败回执/只读投影路径。16:05、17:10 各返回 FAILED，均无已提交行情产物，API 投影为 MISSING。原字节保持一致，未把未解码的 panel 报成零行或 5126 行已复核：decoded row_count 为 null，5126 只记为声明行数；成员文本 5126/5126 唯一是本环境直接计数。

真实 parquet 尚未解码。交接 Mac 报告的 2 个缺失 close position、137 空名称、两个行业字段各 240 空值原样保留。来源回执直接可见 PARTIAL/REBUILD_REQUIRED、覆盖率 0.8858620689655172；accepted_count=5138、target_count=5800 与投影 5126 是不同字段，未猜测差异原因。完整 panel available_at 未知。原回执 80017050 bytes 又超过本候选 16777216-byte JSON 上限；这也作为真实拒绝原因记录，未缩造 READY 回执。

当前工程执行环境是 Python 3.12.14 / pandas 2.2.3，缺 pyarrow 和 pytest，未改变依赖。原 V5 声明仍是 Python≥3.14、pandas≥2.3且<3、pyarrow≥21且<25。用户 Mac 的 Python 3.14.6 / pandas 3.0.5 / pyarrow 25.0.1 必须按 `MAC_ACCEPTANCE.md` 独立实测；本轮没有 Mac 执行事实，不能用 Linux 工程测试替代兼容认证。原 pytest 套件因 pytest 缺失 BLOCKED，未算 PASS。

## 五层状态

| 层 | 本轮事实 |
|---|---|
| 工程 | 完整候选、52/77 字节核对、测试、独立审查、算法 admitted-frame 等价、正反 patch 与回滚工程证据已交付；声明环境认证未满足 |
| 真实数据 | 真实原件 SHA/成员文本及两槽拒绝路径已跑；真实 parquet decode 和合法价格链成功 NOT_RUN，PIT/来源资格未证 |
| 消费 | A 只读投影和 HK sentinel 隔离已跑；活动普通 HTTP API、原 ReviewView 浏览器消费 NOT_RUN，等待唯一集成者按请求接入 |
| 自动 | 两槽/并发/幂等/失败/恢复工程测试已跑；现役 scheduler 自然触发、睡眠恢复现场证据 NOT_RUN |
| 完整 | 未达到。Mac 认证、现场 API/UI、单模块现场发布/回滚、连续两个适用交易日自然接续尚缺独立证据 |

## Mac 执行者入口

解压外层包后，完整 Git 树在 `repository/`。原 runtime 内 ZIP 已随同一提交保留在 `repository/handoff/m09-20261011/`。先把 `M09_PYTHON` 设为现场已核现有解释器，再用 `"$M09_PYTHON" -B /实际交付绝对路径/tools/extract_pinned_runtime.py --archive <实际绝对 ZIP 路径> --out <尚不存在的新目录>` 解出并重核 40 份原件。`M09_RUNTIME_INPUTS` 应指向该输出目录内的 `M09_ORIGINAL_INPUTS_RUNTIME_BINDINGS_20261011` 子目录。直接以本交付的 `after/`、`before/`、`original/` 和 `evidence/independent_review/` 配置 `MAC_ACCEPTANCE.md` 中的路径变量；`tests/` 是完全相同的四个独立测试便捷副本，无需另索取新 M09 输出。

候选 API/UI/dispatcher 的接线先按 `INTERFACE_REQUESTS` 审核实际前像，只在 M09 私有 root 和单模块绑定中实施。现役 API 8873 读取 V4 root、原 producer 写 V3.5 root 的断点不能靠写 V4 或改全局共享 root 绕过。原 strict API 分支与后置 evidence layers 都必须明确选择 M09 A reader，HK 保留原路径。

回滚仅选择该 T 已验证的 predecessor，CAS 校验当前 generation，保留所有 run/输入/回执。代码 reverse patch 仅用于隔离验证；现役前像不符时不能覆盖。完成 Mac/共享集成后应补回实际命令、完整日志、普通 API 响应、原页面证据、版本/路径/SHA 和发布/回滚回执，再逐层更新验收状态。

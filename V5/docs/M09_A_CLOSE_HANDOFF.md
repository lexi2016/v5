# M09 A 股收盘复盘：候选实现与独立验收入口

本候选实现 M09 私有 daily 入口、冻结原 producer/model/chain/builder/store 的可校验闭包、不可变运行和 generation、两槽触发回执、原 store 独立读回、普通复盘页面所需的只读 A 投影和单日回滚。共享 API、ReviewView、调度器及全局 root 由唯一集成者按交付包 `INTERFACE_REQUESTS/` 接入。本文件不是现役发布或自然运行的证明。

## 固定来源与边界

- 新工作仓库：私有 `lexi2016/v5`；交接固定提交：`782bfc9ae91ff9cfe897afffc52aad43b7c1b78c`。
- 原源码只读出处：`lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`。交付包含全部 52 份原始源码的前像；来源中的 V4/V3.5 名称保留原字节。
- 新代码仅在 M09 私有名字空间；`a_close_review.py` 历史回放、BUY、HK、共享 dispatcher/API/UI、现役目录均不被替换。
- 冻结概率仍为 0.12 / 0.28 / 0.60，属于原固定常量，不是校准概率。原市场、行业、角色、排序、理由、情景触发/失效、拒绝码、quality_gate 及模型研究资格保持原义。
- `core_stocks` 不从观察池晋升；`WATCH_ONLY`、禁用 LLM、零语义调用、无交易/无 BUY gate/无生产许可不放宽。视频链 READY 不代表模型已消费视频。

## 文件职责

| 路径 | 职责 |
|---|---|
| `V5/src/v5_shadow/a_close_daily.py` | 输入准入、时点/成员/摘要核验、执行、不可变保存、发布、读回、恢复和回滚 |
| `V5/src/v5_shadow/a_close_daily_worker.py` | 有时间上限的私有子进程，根/运行/指针/实现身份校验后调用原链 |
| `V5/src/v5_shadow/a_close_daily_sources.py` | 逐文件校验冻结闭包，私有导入，不占据共享顶层模块名 |
| `V5/contracts/m09_a_close_daily_source_manifest.json` | 原 repo/完整 commit/path/blob/SHA/bytes 到 M09 capsule 的精确映射 |
| `V5/vendor/m09_a_close_daily/` | 16 份原字节依赖闭包，包含原日历 JSON，不能单独漏拷 |
| `V5/src/v5_shadow/a_close_daily_api.py` | 精确 T 的无写入读取、原生模型完整投影、仅 A 的 envelope 合并 |
| `V5/tests/test_a_close_daily*.py` | 合成工程输入、原链等价、准入、并发、错误、恢复及 API 投影测试 |

应从完整源码树运行，设置 `PYTHONPATH` 指向该树的 `V5/src`。必须同时保留 `V5/contracts` 与 `V5/vendor`；本轮没有修改共享打包配置或依赖范围。

## 调用方式

先由集成者选择一个新建、空的、权限为 0700 的 **M09 专属目录**。它不得是 V4/V3.5 现役 root，也不得与输入目录包含或互相包含。`initialize_a_close_root` 只初始化空目录，已有非空无标记目录一律拒绝。

```python
from pathlib import Path
from v5_shadow.a_close_daily import (
    initialize_a_close_root, diagnose_a_close_input,
    run_a_close_daily, read_a_close_daily, read_a_close_latest_attempt,
    rollback_a_close_daily,
)
from v5_shadow.a_close_daily_api import read_a_close_preview, merge_a_close_preview

# root 和 source_root 由已核验配置明确传入；不从共享全局 root 推导。
initialize_a_close_root(root)
diagnostic = diagnose_a_close_input(source_root, "input.json", manifest_sha256, T, "16:05")
receipt = run_a_close_daily(root, request)
committed = read_a_close_daily(root, T)
preview = read_a_close_preview(root, T)
response = merge_a_close_preview(existing_review_response, preview)
```

`root` 和 `source_root` 是绝对路径；拒绝 symlink、`..`、越界指针、非普通文件和不符合大小限制的文件。读入采用已打开 inode 和 raw SHA 验证；计算后重新核对原输入。调用方持有调度和授权配置，本模块不自行启动定时任务、联网采集或扩大凭据。

请求采用下列字段，不接受任意额外参数：

```json
{
  "schema_version": "v5.m09.daily_request.v1",
  "trade_date": "20261009",
  "slot": "16:05",
  "job_id": "a_share_close_review_1605",
  "attempt_id": "由调度者保存并在精确重试时复用的标识",
  "execution_kind": "RECORDED_INPUT_REPLAY",
  "triggered_at": "真实有时区的触发时间",
  "source_root": "已核验的绝对输入目录",
  "input_manifest": "input.json",
  "input_manifest_sha256": "64位原始文件SHA256",
  "configuration_revision": "m09-candidate-r1",
  "expected_generation_sha256": null
}
```

此示例是字段说明，中文占位必须由实际值替换。`expected_generation_sha256` 可省略；显式 `null` 要求当前没有已提交 head，非空值要求与当前 generation 一致。冲突返回失败回执，不覆盖其他发布。标识字段只允许 `[A-Za-z0-9_.-]`，长度 1–128。

`ENGINEERING` 只能消费显式 `SYNTHETIC`；`RECORDED_INPUT_REPLAY` 是历史回放；`MANUAL_RECOVERY` 是人工恢复；`NATURAL` 必须是当天且位于对应触发窗口，但仍不能自行宣称独立自然验收。四种触发不合并记账。当前产物 `natural_verified` 恒为 false，独立验收证据另存。

## 输入合同及真实材料的处置

`input.json` 必须是 `v5.m09.input.v1`，具有 `trade_date`、`data_kind`、`panel`、`membership`、`provenance`、`evidence`，不接受其他顶层字段。完整可执行合成样本由 `test_a_close_daily.make_input` 创建，并明确标注 SYNTHETIC。

| 分区 | 必要身份和验证 |
|---|---|
| panel | `pointer_path`、指针 raw SHA、panel raw SHA、`format`、整数 `row_count`；PARQUET 由真实 pyarrow 从已锁定字节解码 |
| membership | 声明全体代码文件、raw SHA、`scope=DECLARED_UNIVERSE`、source_id、version、captured_at、available_at |
| provenance | source_id、version、READY、VERIFIED、coverage_rate=1、captured_at/available_at、可选 acquired_at、原 receipt 路径和 SHA |
| receipt_fields | 可选 JSON Pointer 映射，逐项核对原 receipt 中的 T、来源、版本、状态、覆盖和时间；不允许用包装对象自封可信 |
| evidence | 已存在 stage/video/stockdict/OCR/对齐/缺口 JSON 的路径、SHA、T、来源/版本和真实 captured/available；缺失可为 null |

panel 必须包含完整 8 列：`trade_date`、`ts_code`、`name`、`pct_chg`、`amount`、`bar_close_pos`、`tdx_industry_code`、`tdx_industry_name`。逐行 T 一致、代码唯一且后缀为 SH/SZ/BJ、全体代码与声明成员完全一致。数值必须为有限数值；不把 bool/数字字符串/NaN/Inf 转换为正常数值；amount 不为负；close position 在 [0,1]；名称及行业不为空。不删除、不补零、不清洗不合格行。范围只宣称已声明集合，不宣称全市场。

所有来源时间必须带时区，capture ≤ available ≤ 对应槽 cutoff，同日且 panel 采集不早于收盘。`acquired_at` 如有值必须不晚于 available。原模型 `15:30` 标签、16:05/17:10 触发槽和严格 15:00 PIT 是三个独立概念，不互相填充。

真实 T=20261009 的原 8 列投影和成员文件保留原字节。交接报告给出 5126 行/5126 唯一代码、2 个缺失 bar_close_pos、137 空 name、240 空 industry，原回执 PARTIAL/REBUILD_REQUIRED、覆盖率 0.8858620689655172，完整 panel available_at 未知。它们只能进入真实历史诊断、回放材料核验和拒绝/缺口路径；不能变成自然/PIT 成功。原来源回执约 80 MB，大于本候选 JSON 读取上限，也按实际限制返回拒绝，不能伪造小型 READY 回执绕过。

缺 pyarrow 的环境可运行合成工程/原冻结算法桥接测试；真实 parquet 解码必须记为 NOT_RUN/BLOCKED。Mac 已有 pandas 3.0.5 / pyarrow 25.0.1 超声明上界，应在原环境实测并保留版本和结果，不修改 `pandas>=2.3,<3`、`pyarrow>=21,<25` 或自动安装依赖。

## 两槽、不可变身份与发布

按 T 持有内核锁。trigger identity 含 T、slot、job、attempt、execution kind 和真实 triggered_at；完全相同的请求直接返回同一回执。相同 attempt 身份却请求摘要不同则拒绝。运行身份由全部已读输入 raw SHA/bytes、manifest、证据可用状态、完整冻结来源和执行代码/依赖身份、配置、数据类别共同决定，不仅按 T 复用。

16:05 和 17:10 同一完整计算身份可复用同一 run 和 generation，但始终保存各自触发回执和 cutoff。若 16:10 可用的阶段证据仅在 17:10 准入，后一槽身份不同，产生新 run。17:10 后证据不会被旧槽读取或反向填充；available_at 未知保持 UNKNOWN；缺失视频/阶段不阻断合法价格链，但业务始终保留 PARTIAL。

保存结构：

- `attempts/<trigger_sha>/started.json`, `admission.json`, `receipt.json`, 可选 `error.txt`；每次尝试独立留痕。
- `runs/<run_id>/inputs/source/` 保存本次实际读取的原字节；`admitted_panel` 与原 producer 指针另存；`calculation.json`、原 `product/a_share_reviews/` 三文件与 `record.json` 永不覆盖。
- `calculations/<calculation_sha>.json` 是已验证不可变运行索引，不等同于已经发布。
- `generations/<sha>.json` 绑定 run、record、同日 predecessor、创建 trigger 和 request 摘要。
- `heads/<T>.json` 是仅此日期的 CAS 发布选择；`attempt_heads/<T>.json` 是独立的最近尝试元数据。
- `recoveries/` 与 `rollbacks/` 保存显式状态变更证据，保留全部历史对象。

新 generation 必须关联身份完全匹配的不可变 SUCCEEDED 触发回执，才可对外读取。若进程在 head 切换后、回执写入前硬退出，GET 不写修复文件，而是返回同日已验证 predecessor 并附 `publication_recovery=UNCOMMITTED_HEAD_NOT_SERVED`。没有 predecessor 时返回缺失。下一次任务在 T 锁内保存恢复记录并回退未完成 head；旧 attempt 记 UNKNOWN，新 attempt 可恢复。显式读取未提交 generation 被拒绝。

普通异常、超时、原 payload/receipt/manifest 任一步失败、计算中输入变化、独立读回不一致或 CAS 冲突均不替换旧成功。常驻进程如果发现已加载实现的磁盘文件被替换，则拒绝新执行并要求重启，不记录未实际加载的新代码 SHA。

## 只读 API 和原页面接入

`read_a_close_daily(root,T)` 只读一次 head，核对 generation/成功回执/record/calculation/全部输入快照/原 store payload+receipt+manifest。验证 SHA 使用各自语义：原 review 文件 raw SHA、规范化 review SHA、原 source SHA、record SHA、generation SHA 不混用。原 `AShareReviewStore` 重新构造并独立读回。同日产物无效则 CANNOT_CONFIRM；没有目标日则 MISSING，不退到其他日期或历史 REPLAY。

`read_a_close_preview` 和 `project_committed_review` 保留完整原生 review/model/chain，另加 `m09_publication`。`latest_attempt` 只展示最近尝试状态，不覆盖正在服务的成功 run/身份/业务状态。首个尝试失败且没有产物时，MISSING 和失败回执同时可见。

`merge_a_close_preview` 只替换 `market_reviews.A` 与已存在的 A fupan 兼容位置，清除原活动 envelope 中已知的过时 A strict/evidence bundle，保留 HK、research、intraday、ref 和全局安全标志。GET、刷新、回退、切日、重复点击均不得调用 producer。

现役 API 的 strict 分支和后置 evidence layers 可能绕过普通 store；必须由集成者在这些分支之前做明确的 M09 A reader 选择，HK 保持原分支。仅改 store root 并不能完成接线。原 ReviewView/AshareReviewPanel 通过三份接口请求做最小展示和类型补充，不另建无关页面，不替换共享整文件。

## 验证与回滚

从交付树运行：

```bash
PYTHONPATH="$M09_AFTER/V5/src" PYTHONDONTWRITEBYTECODE=1 "$M09_PYTHON" -m unittest discover -s "$M09_AFTER/V5/tests" -v
```

`M09_AFTER`、`M09_PYTHON` 必须是当前执行者明确选择的绝对路径。交付包的 `logs/` 保留实际命令、cwd、UTC/上海时间、exit、完整 stdout/stderr 和 SHA。RED、GREEN、最终固定候选回归各自独立；缺引擎、Mac、活动 API/UI、自然调度或连续两个交易日的验证明确记 NOT_RUN，不折算为 PASS。

程序化回滚只允许同日已验证的 predecessor：

```python
receipt = rollback_a_close_daily(
    root, T, target_generation_sha256=previous_verified_sha,
    expected_generation_sha256=current_verified_sha,
    reason="实际回滚原因",
)
```

它只切换该 T 的 M09 head，保留运行/输入/原产物和各次回执。shared API/UI/dispatcher 的接线回滚由各 owner 按接口请求执行。`reverse.patch` 仅用于隔离树的实际可逆性验证；不得不核对活动前像就对现役共享目录应用。完整 Mac 命令、现场证据回填表、发布先后及停用边界见交付包 `MAC_ACCEPTANCE.md`。

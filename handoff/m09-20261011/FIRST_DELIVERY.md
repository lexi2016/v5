> R2现场输入增补（2026-10-11）：先读 RUNTIME_INPUT_ADDENDUM_R2.md。本包已附T=20261009真实8列panel投影及Mac源码/运行绑定；旧文中“尚待取得”须以R2已取得清单更新。5126行原样保留但存在缺值、来源REBUILD_REQUIRED、完整available_at/PIT未知；只可作真实历史诊断/回放材料，不作16:05/17:10自然成功。Mac pandas3.0.5/pyarrow25.0.1超原声明范围，旧REPLAY不当新生产。新私有lexi2016/v5登录/固定身份仍待建立；本次可先提交完整自包含Chat材料，不冒称GitHub已提交，不改回v4。

# M09 A 收盘复盘：首份材料与真实缺件

日期：2026-10-11。状态：仅本地交接材料；业务代码、产品测试、Mac运行、部署均未执行。

## 现成可用的离线原件

- 同目录 `v5-module09-source-20261010.zip`：145374 bytes，52 份源码/配置，源码合计 404637 bytes。
- SHA-256：`ee45e1cb627df660d15574a5a0a023be00e7fac0a29e983109b202e7e3af25fa`。
- 原始出处：`lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`。逐文件原相对路径、Git blob、SHA-256、字节数完整保存在 `ORIGINAL_SOURCE_MANIFEST.json`。本轮重核 ZIP CRC、源码字节与 manifest、ZIP 内外源码字节全部一致。
- 新工作目的仓库为用户指定的独立私有 `lexi2016/v5`；其创建、分支及首个固定提交由主线程核实。此材料不向 v4 写入，也不声称 v5 已创建或提交。
- 原 ZIP 中旧 handoff 仅作历史证据，本次更新任务书优先。原件来源里的 v4 字样不能改成 v5，以免伪造来源；新候选、发布材料和后续写入必须在 v5。

## 已确认的真实断点

`build_review_from_panel → build_close_model → build_close_review_chain → build_a_share_review → AShareReviewStore.import_review / replace_review` 的固定源码已附。V5 当前 `a_close_review.py` 仅为 SYNTHETIC / RECORDED_INPUT_REPLAY 的固定模型回放；新 `a_close_daily.py` 在固定版本不存在。

复盘日期是当前被处理的真实 A 股交易日 T，panel 的 trade_date 必须等于 T；不是“10/12 预选消费 10/9”的跨日选择器合同。16:05 / 17:10 是上海时区的触发槽，和原模型 15:30 标签、严格 15:00 PIT 三者不同，不能相互倒填。

## 立即需要 Mac 只读取件的项目

1. 现用 panel_pointer 的真实路径、原始字节/解析目标、SHA-256；目标 parquet 的真实路径/字节数/SHA-256、按 T 筛选的行数与字段 schema。固定 producer 要求 pointer 指向单个现存文件，不能猜目录或捏造文件。
2. 同日 panel 的完整声明成员清单及其来源/版本/SHA；明确是 declared universe 还是可证明的全市场集合，不能拿阶段 Top10 代替。
3. 来源真实 acquired_at / captured_at / available_at / 时区、目标 T 与交易日历版本；若时点只能从说明中取得，保留未独立核实标志，不能以文件 mtime 冒采集时间。
4. M07 已存在阶段工件与 M12 已存在视频/ASR/OCR/对齐/缺口材料的精确引用、SHA、available_at；不存在即记录独立 PARTIAL，不要求上游先产生不存在的材料。
5. 当前解释器、依赖/锁文件、活动源码版本；原 store 的活动根与代码版本、V5 已授权私有根及现有发布/读回合同；API/原 ReviewView 的活动绑定与进程/配置事实。只能从现有配置/进程/已知入口取证，不猜端口和路径。

尚未生成的 review、store payload/receipt/manifest、API 响应、UI 截图属于本次实现之后要生成并验证的输出，绝不能倒要求用户先提供这些输出才开始编码。已有历史输出可作为可选对照，不能成为必要输入。

## 首轮可开始的工作

固定源码静态诊断、失败用例设计与候选实现可从现有包开始；工程 fixture 只证明工程行为，不证明真实生产、PIT 或全市场覆盖。真实运行/发布在对应 Mac 必要输入齐备、候选前像核验后进行。缺任一现场件只能阻断依赖它的验收层，不把整模块退回只交方案。

最终交付必须包括完整 after 树、前后 SHA、可正向/反向应用 diff、实际测试命令/完整日志、原算法逐字段等价证据及未跑项。不得只交链接或 Markdown 声明。详细任务书和取件表继续补齐。

# V5 代码续写交接包 · 2026-10-16

这是给接手 Chat 的源码与问题入口。此次仅新增交接文档；没有恢复开发、运行业务、修改生产或重新部署。用户最新选择 GitHub 交接，因此不再把重复源码压成 ZIP。

## 先打开正确源码

- **完整集成工作树：** [lexi2016/v5@01d93717905813705732161d4d79062ae5af2d99](https://github.com/lexi2016/v5/tree/01d93717905813705732161d4d79062ae5af2d99)，原分支 `dev/v5-main-integration-20261012`。2026-10-16只读清点为2363个文件，29,178,407字节，GitHub递归树未截断；它是本包的固定源码基线，不是完整验收或部署声明。
- **不要默认克隆后直接用 main 开工。** 本次读到 main 为 `d3ebf33c40d1b5f06e3729b11d5ece0506f34c91`，树仅README和1个测试文件。它不是上述整合代码；这个差异不证明仓库损坏。
- 原18模块的独立候选源码、补充包与固定commit见 [SOURCE_INDEX.md](SOURCE_INDEX.md)。没有把未合入候选强行叠加，也没有把小补丁当完整模块。
- 2026-10-15有一轮已停止的24文件未提交修改。回执明确“未commit/push”；本包没有取得其checkpoint补丁原字节，不能声称已经包含。取回前先检查是否值得恢复，不能凭描述重造再宣称恢复。

## 给 Chat 的阅读顺序

1. 复制 [PROMPT.md](PROMPT.md) 的全文给 Chat，并保证它有这个私有仓库的既有授权读取能力。
2. 读 [VERIFIED_GAPS_AND_EVIDENCE.md](VERIFIED_GAPS_AND_EVIDENCE.md)：首批业务、历史失败、已修问题、停止回执、验收边界。
3. 读 [MODULE_MATRIX.md](MODULE_MATRIX.md)：原 M01–M18，B01=M18，原 P0–P5 不变。
4. 读 [SOURCE_INDEX.md](SOURCE_INDEX.md) 与原总计划；按固定SHA打开实际源码、owner闭包、依赖、配置、测试和回执。
5. 用 [BRANCH_SNAPSHOT.json](BRANCH_SNAPSHOT.json) / [SOURCE_FILE_MANIFEST.json](SOURCE_FILE_MANIFEST.json) 对照版本。交接文档自身SHA-256见 [MANIFEST_SHA256.json](MANIFEST_SHA256.json)。Git blob SHA-1和文件SHA-256是不同概念。

## 首要交付

公告M13、超跌M14、美股到港股映射M15 → 经理M18保存 → 普通API、原页面和独立冷读，同一经理run/generation/产物SHA可追溯，再收口合法自动触发、失败恢复和连续适用日接续。上游保留各自真实日期/session/run与引用，不能为了“同run”改造来源身份。

源码有文件、Chat自报、独立测试、HTTP/DOM、真实可视、部署、业务生产、自然运行分别记。18部分接入/14局部读回或状态页/完整0是历史台账，不是本次2026-10-16重新验收统计。此次未重跑产品测试，现役部署版本/健康状态待核。

## 不变边界

保留V4；复用原算法和完整固定源码闭包。不得交易、发订单、改BUY门/PIT/资格/风险语义、扩大权限或凭据，不在V4活动根写入，不以V4服务/目录作最终V5隐式依赖。缺数据、权限、窗口分别列出；合成输入和手动恢复不能冒充自然结果。此包不授予新生产、外传、provider或发布权限。

本包不复制凭据、.env、浏览器资料、真实行情大文件或私有材料。它引用已存在的私有仓库源码；未对全部2363份源码重新做逐字节秘密扫描，不把这个范围边界写成“全仓安全通过”。

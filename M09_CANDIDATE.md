# M09 A 股收盘复盘完整候选

本提交在独立私有 `lexi2016/v5` 中提供 M09 完整候选实现与实体交付。父提交为固定交接 `782bfc9ae91ff9cfe897afffc52aad43b7c1b78c`；原只读出处 F 仍为 `lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`。原交接 32 文件（含 R3 ZIP）原字节保留。

## 入口

- [完整交付与资格状态](M09_DELIVERY_20261011/README.md)
- [实际代码入口、数据合同和调用](V5/docs/M09_A_CLOSE_HANDOFF.md)
- [before/after、逐文件 SHA 和动作](M09_DELIVERY_20261011/CHANGED_FILES.json)
- [当前固定候选的实际验证](M09_DELIVERY_20261011/FINAL_VERIFICATION.json)
- [完整原算法等价](M09_DELIVERY_20261011/ALGORITHM_PARITY.json)
- [新 review/store/run/generation/两槽回执与投影](M09_DELIVERY_20261011/OUTPUTS_MANIFEST.json)
- [Mac 独立验收及单模块回滚](M09_DELIVERY_20261011/MAC_ACCEPTANCE.md)
- [唯一集成者的函数级请求](M09_DELIVERY_20261011/INTERFACE_REQUESTS)

根目录的 `V5/...` 等 77 份源码与 `M09_DELIVERY_20261011/after/` 完全相同：52 份原件保持不变，新增 25 文件。实现 M09 私有 daily、原完整链、不可变 run/generation、两槽回执、失败保旧、提交见证和硬中断恢复、独立验读及 A 只读 API 投影。固定概率、PIT/研究资格、禁用 LLM、WATCH_ONLY 和空 core pool 保留。

实际工程回归 125 项：121 通过、4 因缺少 pyarrow 跳过；独立审查另 6 项通过；正反 patch 已实际应用并做全树字节核对。原算法两个完整工程对照及一个原拒绝异常一致。真实 T=20261009 原件两槽拒绝路径已执行并留失败回执；未解码的 panel 行数保持 null。

**本提交不是部署完成或生产验收。** Mac 现有 pandas 3.0.5 / pyarrow 25.0.1 超固定 V5 声明上界，未改依赖/环境；Mac 实测、真实 parquet 解码、活动普通 API/原 ReviewView 接线、自然两槽及连续两个自然交易日验收均保留 NOT_RUN。共享接线只交函数级请求；不写 V4、不修改全局 root、不交易。

同提交离线导出包含整个 `repository/` 树和外层 `EXPORT_VERIFICATION.json`。外层回执记录实际远端完整 commit/tree 与逐文件核验；回执本身不是提交树中的自引用文件。

# Manager c7b：Mac 隔离验收主控回执

仅转存主控已读取的 Mac 回执；本件作者没有重测或读取 Mac 文件。时间均为 2026-10-13 北京时间。候选代码固定为 `c7b815c065da83bd2db2b3023be4607ce9f194ec`，11 个 blob 匹配，5 个执行前像匹配。

## 构建与测试：保留失败

19:29:08–19:29:11：vue-tsc --noEmit PASS，Vite build PASS。Vitest 的 SavedManagerResultView.default.spec.ts 与 navigation.spec.ts 合计 11 PASS、1 FAIL，exit 1；新 default 4 项通过。旧 navigation.spec.ts:68 仍期待“阶段选股 · 未接入”，当前 M07 已接入；原 P0 Chat 的窄范围测试返修待回。本回执不将该候选称为全部测试通过，也不以后续合成验证掩盖此失败。

## 获许可后的隔离 HTTP / DOM 验证

19:40:07–19:41:02，实际 exit 0。该步骤单独取得执行许可，未修改系统安全设置。四种合成场景：
1. opt-in 关闭、空 query：保留旧固定 target=20261012。
2. opt-in 开启、无 current：503 / CANNOT_CONFIRM；DOM 不回退旧结果。
3. opt-in 开启、有 current：显示新的 synthetic run、target=20261013；导航六字段的 run / generation 一致。
4. 显式旧 run：仍显示旧结果，不重定向；坏 generation 返回 409，未知 run 返回 503。

fixture 仅被读取、未修改。早期探针的静态资源加载及 Mac spawn 脚本问题日志保留；修正对象为测试脚本，不是产品代码。验证使用 jsdom，不是原生浏览器视觉验收。

## 隔离与未完成边界

- 2,812 个文件 hash、5 个候选 SHA 及 PID 不变；临时服务已关闭。
- 真实 owner、manager、daily 运行次数均为 0；现役 opt-in 未启用，无部署。
- natural_verified=false，deployed=false。此次仅为候选的隔离合成验证，不构成真实自然运行或现役上线结论。

来源：主控读取 Mac 线程 `01a12e51-a0ec-705c-96e5-26cfd89360f8`，turn `01a13504-33c9-7188-a6d1-28fdd1dba4e0` 与 `01a13509-a497-72c0-91cd-251851d0cc5f` 的回执。本提交只新增两份摘要文档，不包含真实数据或私有路径，不修改源码。

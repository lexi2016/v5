# M05 R9 最小完整返修任务

本任务仅限原 A股预选池模块，在 `dev/m05-github-handoff-20261011` 接续原 Chat。先通过 GitHub 读本目录固定版本，不能仅引用说明冒充读取完整源码。此处 source 与被退候选保持不改；新实现应在独立候选运行 V5 树中完整提交，保留原相对布局及逐件前像。此材料提交不算实现完成。

## 已具备且必须复用

- source/V5 的六件 v5_shadow Python、原 descriptor、40件 owner、两件原 unittest 文件；原 `run_a_preselection` 是独立只读子进程，加载固定字节并保持永久 guard。
- 原 `PreselectionPoolStore`、`StoreGateContext`、SafeRoot、锁、store readers/transactions、五种原 fixture helper 都有完整源码，不要求用户再交同一个 SOURCE。
- SOURCE SHA256 `241f56dbff2bd91514eaa976239007ca53f73d48cfce20bf173fbfadfd6a4d27`；R8 SHA `61164b69960de0741dbaa157e4704cff431538a00eadf99550b0eaa934edfab2`；R9 SHA `318ca8aa01d644ff5e0f4f95e8b412f82e4aaec105adc2893bd7c1e2ef76bcfa`。这些归档身份仅用于来源核实，正文已在 GitHub 解包。
- R9 daily SHA `55e126a19157d16ba490c248211c5ed6b7bdc53ab7d5d5654dcfa82336ad2049`；测试 SHA `fcc4de775890e3e79bd0debddc6107872fdae0cf21e9e7cf97e4511775953ebc`。

## 下一份代码必须解决

1. 默认 writer/readback 的真实冻结源码装配。R9 L11–20 的宿主顶层 infrastructure import 未绑定原胶囊身份；失败还清空已导入 helpers，类名可能未定义。应在独立、明确的私有 writer 边界加载原核定类，保持同 loader 的 context 类型；不能借宿主偶然存在的同名模块、添加假字段、清除 guard 或把写入塞进原只读 worker。
2. 将 R9 L80–87 已存在的真实 factory 接入默认 daily；显式绑定 context 的 control_dir、expected_permit_sha256、expected_owner_id、expected_release_sha256、expected_root，生产值必须由明确调用者提供且缺失拒绝。不能自行生成生产许可。合成 fixture 可在临时隔离目录生成明确测试 permit/gate/marker。
3. 保留已修的私有 strict/context 同一对象检查、逐 lane 与 code/V4/output 双向隔离、canonical 请求身份、原 assembler、原 pool_score/rows、raw snapshot 身份和窄冲突分类。不要删已有有效校验或重写算法。
4. 真实 fixture 通过前置 marker/独立根/合法 make_lane，再走默认 daily→原 assembler→真 strict store→snapshot 正控；逐项 gate 错误负控精确断言错误与无写入。当前四个薄测试未调用这些产品路径，fake_gate 只判断假对象属性；/tmp/out 未初始化不能代表目标 gate 失败。
5. 完成同锁最终 batch identity 与 publisher 冲突聚合。当前逐池快照后其他池继续改共享 manifest，不能把早期回执当最终完整批次。只读原 publisher 合同，不能盲 import 其未齐的 V4 依赖。M07消费集成未完成前保持 WAIT_INTEGRATION。
6. 交完整 after 与准确 before→after/reverse diff。R9 现存两 patch 仅缺末尾 LF，不是缺差分正文；不要虚称已经应用通过。新增源码应如实 before=ABSENT，R9修改以本次真实R9为前像，原source descriptor/PIN不可随意改以通过。

## 证据与边界

本交接只做字节/AST/patch解析，不含运行结果。原文件中的历史测试描述不构成本轮验证。实际测试若未跑标 NOT_RUN；代码未写标 UNIMPLEMENTED，生产 binding 未接标 WAIT_INTEGRATION。原 V192 verified-empty 仍有独立合同缺口，不能把非空路径或历史只读通过等同新daily通过。

现有环境的 numpy/pandas/pyarrow、fcntl、O_NOFOLLOW/dir_fd 与时区数据由执行端核实，不新增安装/权限/交易凭据。最终回传固定 commit、全部变化文件、前后 bytes/SHA/Git blob、真实命令/退出码或准确 NOT_RUN，以及仍缺生产/自然/页面证据。必须由 Mac 独立验证，再讨论运行部署。禁止 V4/main/其他模块写入、合并、真实采集和交易。本任务不含任何以前被拒的 Mac/M13/M18 材料。

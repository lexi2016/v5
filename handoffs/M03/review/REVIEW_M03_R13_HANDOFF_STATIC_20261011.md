# M03 R13 reader 切片交接静态审查

日期：2026-10-11。结论：**可作为隔离的源码候选发表；R13 reader 有实质修复，但不是完整 M03，也不是可直接应用的 R11 增量补丁。**

本审查只读取 ZIP 字节、核 SHA256/CRC、解析 AST、比对文本。没有导入候选、调用 child、执行候选测试、应用补丁、进行采集或操作 Mac。下文行号指 ZIP 内完整 after 文件，不是 patch 行号。

## 1. 已核身份

- 原 SOURCE：`V5_M03_SOURCE_REVIEW_20261010.zip`，SHA256 `4d5cc792923aed31bc0867ff8abbca85b1cb6fbdabd882a3581c827bb91e4d45`；其 SOURCE_MANIFEST 列 63 件原件。
- R11：`V5_M03_R11_DELIVERY_20261010.zip`，SHA256 `a771029a5ea97ac98fb53d85ef826c022fe7fcc7e4b75505d3f9a73c8e796fa5`。
- R13：`V5_M03_R13_READER_SLICE_DELIVERY_20261010.zip`，SHA256 `f731e6edca95ba8da171ad47f81728eaad2e21a7d9a55d947af97aeaec96ba4f`。
- R11 的 `after/V5/src/v5_shadow/us_source_daily.py`：3545 bytes / 111 行，SHA256 `464faaf371bd5eb6e3cea899842131173544292e0452e6c39063e121925ed4d8`。
- R13 同名 after：2122 bytes / 68 行，SHA256 `78cff69c77097aa45507596becf78b762498ca966a18438101340c15a9a14334`。
- R13 `after/V5/tests/test_us_reader_slice.py`：350 bytes / 13 行，SHA256 `005ed686d064531adda8d3e857afca7a1a8f773b3e965840374cec3f7beb0f99`。
- R11/R13 ZIP CRC 无错误；各自 manifest 的全部 after SHA 与实物一致。两个候选的四件 Python 文件 AST 可解析；从 R13 AST 的返回常量取出 child 字符串后，child AST 亦可解析。未运行 `_reader_child_code()`。

## 2. R13 已实现的内容

源码 C = R13 `after/V5/src/v5_shadow/us_source_daily.py`。

- C11–36 将 child 改成多行脚本，修复 R12 的 `;try:` 语法错误。
- C18–26 调用 SOURCE 原 `load_owner`、`admit_output` 和 `ResearchPeripheralStore.read_exact(trade_date, "external_finance")`。SOURCE 的 loader 核 descriptor/48 件闭包及模块来源；准入检查私有 marker、绝对路径、symlink 与 source/output 重叠边界。原 reader 保留 payload/receipt/manifest 一致性验证。
- C25–32 将成功 JSON 输出放在 `verify(owner)`、`audit_modules()` 之后；验证失败不会走成功输出。
- C39–52 默认使用 `subprocess.run`，参数含现有解释器、`-I`、`-B`、固定四项请求值，捕获 stdout/stderr，并设置 300 秒 timeout。
- C53–68 拒绝非零退出，错误信息保留 stdout/stderr；解析 JSON，要求 envelope 有 `payload`，只接受 dict 或 None，并返回 payload 本身。

这些是静态可见的实现进展；不应再沿用 R12 的“child 语法不通、未接准入、输出在 finally 前、返回未解包 envelope”等旧结论。

## 3. R11/R13 接口与覆盖风险

**路径冲突是确定问题。** R13 的完整 after 在与 R11 相同的模块路径下仅定义 `_reader_child_code`、`read_cold_snapshot`。文件头“保留外部 orchestration”的文字不等于实际保留源码。

若用 R13 after 覆盖 R11，该模块会失去：

- `USSourceRequest`
- `parse_utc`、`source_paths`、`collector_argv`、`run_cold_collector`
- `select_capture`、`create_binding`、`persist_binding`

R11 测试第 2 行导入 `parse_utc, collector_argv`，因此与覆盖后的 R13 模块不兼容。这是定义/导入关系的静态结论，未运行测试。

两版可衔接的最小接口已存在：R13 reader 读取请求的 `v5_src/owner_root/snapshot_root/trade_date`，这四项都在 R11 `USSourceRequest` 中；返回非空 dict 时可传入 R11 `create_binding`。但 None 会被 R11 拒绝为 `M03_PAYLOAD_NOT_VALIDATED`，仍须由总入口处理缺源状态，不能把 reader 返回自动当作成功 binding。

返修应在**完整 R11 after 上增量加入 reader 并保留原 API**，或在独立模块中提供 reader 并明确导入接线。交接仓库应继续将 SOURCE、历史 R11、最新 R13 分目录保存，不能叠盖成一份“已完成”源码。

## 4. 完整入口仍缺什么

R11 和 R13 均没有把 collector、稳定三文件快照、reader、binding、保存串成的总入口；没有该入口的真实调用证据。现有 helper 不能替代以下待交付能力：

1. 按原日历/窗口决定是否到期，先复用合格精确来源，缺源才按原流程采集；保留真实触发/取得时点和原拒绝码。
2. 在独立私有 root 形成稳定 payload/receipt/manifest 三件快照，再由 fresh child 独立读回；R11 `source_root` 未被其 helper 使用，没有快照构建或并发稳定性检查。
3. 在同一入口衔接 session/phase/cutoff、独立读回与三件原字节 SHA，并分别处理缺源、有效空、NOT_DUE、失败与成功保留。
4. 修复原 binding 发布边界。R11 `persist_binding` C96–111 直接操作传入 root，没有 marker/来源不重叠/SafeRoot 准入，也不创建新 root；两个写者同时过 `target.exists()` 后，输家 `os.link` 会抛异常，没有同内容回读分支或 finally 清理暂存文件。此处未因 R13 reader 加入而修复。
5. 共享调度/API/原预览页接线与 M15 只读消费仍须单独集成及验收；这两个候选包没有相应实现或运行证据。

R11 `create_binding` 的“VALIDATED_SOURCE_BINDING”来自其自身赋值；函数只要求非空 dict、匹配日期/单 capture 和 cutoff，再读取三件 SHA，没有调用原 reader。只有后续总入口证明传入的是独立验证结果，才能把该标签视为验证证据。

## 5. R13 尚未验证的 reader 边界

- 测试 T6–7 只解析 child 字符串；T9–10 只检查 callable。整个测试没有一次调用 `read_cold_snapshot`，没有 fixture、原 store、child 行为、marker 或篡改测试。作者日志中的“两条通过”只覆盖这两项，不是 reader 行为通过；本审查未复跑。
- timeout 有设置，但 `TimeoutExpired` 原样向外传播；尚无统一 M03 timeout 状态/诊断处理。非零退出和坏 JSON 的诊断已有改进，不能笼统说“所有错误都丢输出”。
- 原 loader 在内部自带 verify/audit；R13 的额外 finally 从 store 读取处才开始。准入或 store 导入失败时走外层错误并非成功返回，不应误判为成功绕过验证。
- R13 直接调用路径里没有 collector `main` 或 provider 请求；但 `-I/-B` 本身不是断网沙箱，也不能替代运行时无副作用证明。

下一轮最小行为证据：实际调用默认 reader，以原 SOURCE 的离线 fixture 生成三件，在新标记私有 root 核返回与前后字节不变；覆盖缺失/篡改三件、坏 marker、owner SHA 漂移，以及非零退出/坏 JSON/payload 类型/timeout。局部通过只计 reader 层，不计真实采集、Mac、页面或自然接续。

## 6. patch 身份仍不成立

- R13 manifest 的 `before` 为字面 `R11-after`，不是 R11 实际前像 SHA256；真实前像见第 1 节。
- R13 `runtime.patch` 与 `reverse.patch` 逐字节相同，SHA256 均为 `e36e938b380916db05b08a8bc3ececfc3921923e6e8f6628e77ef9eaaa774628`。
- patch 仍以 `/dev/null` 为前像、`new file mode` 新增，并指向制作环境的 `mnt/data/.../after/...` 路径；没有 R11→R13 的差异或正确反向差异。
- R11 也有相同类别包装问题；其 runtime/reverse 同 SHA256 `04c1a66597c19cf8470efa33af7317465ddba95e0d1b8afc5e03d71e5a131bf5`。
- 作者 apply 记录明确未对目标 checkout 应用。本轮也没有做 patch apply/roundtrip。

应提交实际基线 before/完整 after、仓库相对路径 delta、真正反向 delta 和逐文件 before/after 身份；在授权隔离 checkout 核往返后再称可安装。当前 patch 仅可作隔离历史证据，不能进入自动应用流程。

## 7. 静态发表与安全排除建议

- 可发表：原 SOURCE 63 件及原 manifest、各轮候选 after 源码/测试、必要 hash 元数据与本审查；按轮次独立归档，保留原字节身份。未在本审查中重新验证 SOURCE 全部 63 件的逐项来源，只核 SOURCE ZIP 身份并读取相关源码。
- 默认排除原执行日志、个人运行路径、真实行情产物、provider 原响应、浏览器/会话导出、账号资料、凭据及临时缓存；用无私密内容的状态摘要替代日志发布。不要把 R13 `TEST_LOG` 中无关环境 traceback 当模块证据。
- R11/R13 archive 内未见绝对路径/`..` 成员名、symlink 成员、嵌套 archive、凭据类文件名；有限静态模式检查未命中私钥、常见 GitHub/AWS/OpenAI token。此为受限字节检查，不是“无任何秘密”的保证。
- R11 的 `run_cold_collector` 明确传 `--allow-network-capture`；源码归档不授权调用。R13 reader 也不在本轮启动。无真实网络、交易、部署、V4 写入或新增权限动作。
- 无需为此次静态交接扩大权限。发布状态须写清：代码候选已有；reader 仅语法/存在性证据；完整工程/真实业务/API页面/自然接续均没有本轮通过证据。


# M14 候选 R1 独立静态审查

## 结论

**RETURN_FOR_MINIMAL_REPAIR。可以接收为部分修复草稿，不能作为可落地候选接入 Mac、每日 owner 或 V5 预览。**

价格门确实改善了原来的 80% 边界，前像也找对了；拒收原因是明确存在的依赖闭包断裂、AST 抽取失配和未完成的精度/交付要求，**不是因为 NOT_RUN**。来源准入、master/成员资格、单位/finality 等外部证据缺口不归类为这次代码缺陷，不要求伪造填补。

本轮只读取 ZIP/源码、核验字节、以标准库解析 AST、重建 patch 文本和演算独立数学例子。没有导入或执行产品，没有运行 pytest、候选主函数或 Mac 测试，没有修改产品源码、部署、GitHub 写入或交易。

## 1. 固定对象和已确认的改进

候选：`/workspace/shared/V5_M14_decimal_candidate_20261010.zip`

- ZIP SHA256：`07ebefb077b6af4a0ead5a2e6feeffed716d67717c95e37ef6cff25565b6ac8b`
- 声明目标：`V5/vendor/rebound_baseline/v4/manager_research/workspace_plan.py`
- before SHA256：`be0d5e69ff72efd07d2caca4e68948245db4900a8c41f467e9c30f6899c044b1`
- after SHA256：`4c77fe2e1424e56d24a12cf93e6eab49d05a16e5a4e31d9d81c35098b1c45a34`
- after Git blob SHA：`faa5ee44047804a99b15ca4c1d23f08e1cba2703`
- before 与源 ZIP 内 `BASELINE_F/V5/vendor/rebound_baseline/v4/manager_research/workspace_plan.py` 逐字节一致，也与已展开的 F 一致。
- `runtime.patch` 只有一个 hunk；静态按上下文和删除行逐行校验、重建后与 after 完全一致。before/after 均可被 AST 解析。
- 改动仅在主 `read_rebound_screen(authority_root, context)` 内，没把另一四项 `rebound_v3_metrics` 换成筛选算法，没有整文件移植 D 的 V4 实现。
- 窗口选择、缺/重复日处理、strict/near/unknown 条件、分组与排序代码未被删改；没有增加容差或补缺值。

本报告路径约定：`F/...` 指源包的 `BASELINE_F/V5/...`；`C` 指候选 `tmp/m14_delivery/workspace_plan.after.py`；其行号也就是替换目标后该文件的行号。D 指源包 `DONOR_D/after/v4/manager_research/workspace_plan.py`。

## 2. 必须返修的具体问题

### M14-R1-01 / P1：只替换源文件必定不能通过原 owner 字节验证

位置：

- `F/contracts/rebound_source_manifest.json:6–13` 仍固定旧 commit/path/blob/SHA256。
- `F/contracts/rebound_owner_capsule.json:6–10` 仍绑定旧 source SHA 和旧 manifest 字节。
- `F/src/v5_shadow/rebound_owner.py:38,223–236`：PIN 验 descriptor，随后逐文件验 SHA256 和 Git blob。
- `F/contracts/rebound_observation_capsule.json:5,65–70`、`F/src/v5_shadow/rebound_observation.py:34,73–88` 还继续绑定这条旧闭包。

候选包不包含上述任一更新。其唯一源码 after 与 manifest 声明的 before 不同。按现有代码路径，单独替换 source 会在 `rebound_owner._sources()` 的 235–236 行被 `REBOUND_CAPSULE_BYTES:v4/manager_research/workspace_plan.py` 拒绝。`legacy_adapter.load_pinned_reader()` 的 76–80 行也会经 `source_capsule.verify_capsule()` 的 70–73 行发现 SHA/blob 失配；不能把它解释成缺行情。

**最小修复：**提交完整、可验证的 source manifest → owner capsule → owner.PIN → observation capsule bindings → observation.PIN 更新。对修改源明确记录真实候选代码 commit/path/blob，保留原 F/D 来源映射，不能把新字节宣称为旧 commit 的原件。按现有 canonical digest/文件字节 digest 的各自定义生成，不能混用。无需因 Decimal 标准库导入修改锁文件；若锁未变，应保持其原绑定。

### M14-R1-02 / P1：仅补 hash 仍不够，原 AST 固定抽取位置已经失效

位置：`F/src/v5_shadow/rebound_observation.py:103–115`；descriptor 的 `extracted_spans/structural_boundaries` 在 `F/contracts/rebound_observation_capsule.json:37–63`。

原抽取要求 setup 874–889、loop 893、arithmetic 894–993、row 997、background 1046–1052。静态 AST 解析结果：

- before：setup_count=11，arithmetic_count=59，row=997–1043，background 三个顶层节点在 1046、1047–1051、1052。
- 当前 after：setup_count=11，loop 仍为893；完整 arithmetic=894–1006，共64个顶层节点；row=1010–1056；background 三个节点在1059、1060–1064、1065。
- 旧 arithmetic 894–993 会选出61个节点但截掉原 near gap 计算尾部；997行现在是嵌套 if，**并不存在旧提取器要求的顶层 row Assign**。即使人为补了哈希，106行的 `next(...)` 也找不到 row。

这是从源码结构推导的确定失配，不是声称已经运行并获得异常日志。

**最小修复：**等最终数学改动定稿后，重新固定准确 setup/arithmetic/row/background 位置、span SHA、结构数量与 descriptor/PIN，保留现有 fail-closed 校验。以上 after 数字只用于证明当前失配，下一版新增/删减行后必须重算，不能机械照抄。增加完整主函数与抽取函数的逐字段差分测试，并覆盖 source、span、结构及 PIN 篡改拒绝；禁止删断言或改成宽松未知源码抽取。

### M14-R1-03 / P1 验收缺口：量能 Decimal 放在浮点除法之后，没有修好 1.5 精确边界

位置：`C:918–920,929–930,947,950–951`。均值与除法先在 float 中完成，然后 `_decimal_screen(volume_ratio)` 只把已经舍入的商转成 Decimal。

独立数学反例（不是实际行情/产品执行）：5个 prior trade 均为0.1，current trade=0.15。原公式的精确答案为1.5，应包含等号；float mean=0.1，float ratio=1.4999999999999998，候选 Decimal 转换后仍为这个值，门判 False。该数值形态没有被 F 的 `_screen_number`（502–511行，有限非负数）禁止；此处没有推断单位或正式资格。

对有限 float ratio，相对精确可表示阈值1.5而言，这种转换实质保留原 float 比较结果，不能恢复除法前丢失的精度。**这是要求修复但仍遗留的问题，不是声称本补丁新引入量能回归。**

**最小修复：**复用 D 1282–1285 行的数值思路，在原 F 的完整5日、缺/重复日和非零均值守卫之内，以原5个值分别转 Decimal 比较：current × 5 ≥ 1.5 × sum(previous5)。在 denominator>0 时，这与原 current / (sum(previous5)/5) ≥1.5 完全等价，不改阈值、日期集合或分母定义；展示 ratio 可以保留 float。不要复制 D 的 `volume_proven`/supplement 整套接口，也不要凭这次算术修复新造单位准入。保留所有原 unknown 判定，并补等于/略低/略高及此反例测试。

### M14-R1-04 / P2：判断用 Decimal，返回和 near 距离仍用旧 float cutoff

位置：`C:948–949` 对比 `C:1002–1006,1028`。

close=0.28、prior high=0.35 时，新 oversold=True，但返回的 `oversold_cutoff_80pct_prior60_high` 仍是0.27999999999999997，造成“价格高于回传阈值却通过”的自相矛盾。near 价格失败时的 gate_value/gap 也继续按旧 float 乘法计算。D 的修复并不只修改 bool，还在 D 1352、1382 附近将同一个 Decimal cutoff 转 float 供输出；应按语句核对而非跨版本硬套行号。

**最小修复：**复用一个 `oversold_cutoff` Decimal 值；价格 bool、`near_gate_value` 和 `oversold_cutoff_80pct_prior60_high` 均从它派生。展示字段保持 float，原排序键和分组流程不改。测试 close/cutoff/flag 一致性及 near 顺序；不要给接口塞 Decimal 对象导致 JSON 序列化变化。

## 3. 数学等价和边界证据

以下是标准库独立演算，未执行 `read_rebound_screen`：

- 0.28 / high0.35：旧 cutoff=0.27999999999999997，旧 False；候选 Decimal cutoff=0.280，候选 True。
- 0.56 / high0.70：旧 cutoff=0.5599999999999999，旧 False；候选 Decimal cutoff=0.560，候选 True。
- 0.2800000000000001 / high0.35：候选 False，未加入 epsilon 容差。
- 0.2799999999999999 / high0.35：候选 True。
- None/非法/非有限 close 和 high 在原 `_screen_number` / valid_highs 层已有过滤；本 diff 没更改这些守卫。但其主函数路径仍须实际回归，不能把标准库演算当作 owner 实测。
- 量能等式反例如 M14-R1-03；交叉乘积结果同时由 Decimal 和 Fraction 独立确认 True。

静态机器可读证据：`/workspace/shared/review_m14_r1/static_evidence.json`。

## 4. 原接口与最小可落地范围

应保持的入口和职责：

1. `V5/vendor/rebound_baseline/v4/manager_research/workspace_plan.py:827`：`read_rebound_screen(authority_root, context)`，本次只改其数值精度及一致的展示阈值。
2. `rebound_owner._calculate()`（F 355–397行）通过冻结 loader 调原主函数；保持 research observation/legacy diagnostic 分离。`manager_projection()`（546–561行）继续 `eligible_screen=None`。
3. `rebound_observation.extract_calculator()`（92–141行）必须从已固定主函数 AST 提取，修准确合同，不另写第二套筛选。
4. `legacy_adapter.run_legacy_screen()`（93–110行）保持 `OWNER_VERIFIED` 的 `OWNER_INPUT_STABILITY_UNVERIFIED` 门禁。数字修正不等于具备正式准入协议。
5. `daily_rebound_owner.py:9,12–20,37–48` 固定独立 S checkout=`2d8e38ec61792b3e75581f96318e9c284f72b7ba`，并拒绝 dirty。仅改 F 的 vendor 不会自动修正独立 S 执行链。由 M14 提供新固定依赖映射/原接口验证要求，经唯一集成者升级该桥；不能放开为任意 HEAD，也不能复制乱改 S checkout 后绕过 dirty。
6. M18 的 `manager_plan_baseline/.../workspace_plan.py` 是另一 owner，必须只交精确集成请求；M14 不能跨模块覆盖同名文件。M02 source/master/membership producer、sharedUI/gateway/scheduler 同理。

最小代码闭包通常是6个既有文件：主 vendor、source manifest、owner capsule、owner.PIN 所在文件、observation capsule、observation 的 PIN/抽取器，加相关测试。shared daily/M18 接入另列 INTEGRATION_REQUEST，由统一写入者实施。

F 的 `_same_code` 和 `_align_repair_trade_dates` 已在 `rebound_panel_repair.py:60–97,263–313`。本轮核得 F 与 R 该完整文件 SHA256 均为 `9f547b8d2307b847b3d284eff2e5914d715283a06eb427044074b34bdc3114da`。不要重写日期修复；保留原测试及 owner 身份测试。

这一最小修复完成后可以进入隔离 child 的源/数学/观察路径验收；真实67 cells、authority、units/finality、master/membership未齐时继续 CANNOT_CONFIRM/观察，不要求为了通过本轮而制造正式screen。

## 5. 交付包仍需补齐的材料（与代码缺陷分列）

候选实有：REPORT、before/after、runtime.patch、两文件SHA、一个仅含 `exit=0` 的 test.log、CPython3.13 pyc。REPORT 22–23行自报执行 `python3 -m py_compile workspace_plan.after.py`；这只能作为提供方编译声明，不能升级为主函数、Python≥3.14 owner、AST或Mac通过。

缺少任务要求的完整测试源码/原始日志、固定候选commit与SOURCE_TARGET_MAP/COMPOSITION_MANIFEST、各依赖新旧SHA、reverse.patch、INTEGRATION_REQUEST、MAC_APPLY_AND_ACCEPTANCE。`runtime.patch:1–2` 头是 `/tmp/m14_delivery/workspace_plan.before.py` → `workspace_plan.after.py`，虽内容可准确重建，但不是声明的仓库目标路径；需重打为明确 a/V5/... → b/V5/... 的补丁及反向补丁，不能要求执行者猜覆盖位置。不要将 pyc 当部署源或运行证据。

这不是要求原Chat在没有真实输入时伪造运行日志。它可以交完整可执行测试和明确 NOT_RUN，让统一 Mac 执行者按已核目标跑。

## 6. 返回原 Chat 的最小验收清单

- 修完01–04，提交上述完整6文件闭包及逐文件前后像/新固定pin，不复制D整文件，不改M18/M02。
- 在真实主函数上补 0.28/0.35、0.56/0.70、略高/略低；量能1.5及非整数浮点反例；None/NaN/inf/zero mean、缺/重复日期。保持半日高点/全日量能窗口及strict/near/pending/excluded/unresolved守恒。
- 复用并扩展 `F/tests/test_rebound_observation.py:278–423` 的主函数/AST差分测试，核每个原字段、顺序、理由及上述边界。按原真实loader验证整条新闭包和篡改拒绝；不要用 mock掉 `_verify_owner` 的dtype fixture代替身份测试。
- 不复写已有日期修复；保留 `test_rebound_date_compat.py`、`test_rebound_owner_identity.py` 等既有覆盖，执行状态如实分列。
- 提交exact source run/三件套引用和依赖映射要求供M18/平台集成；尚无真实run就明确待Mac生成，不能编一个。
- Mac实际动作前先绑定实际owner checkout、精确before、解释器/锁、私有输入与输出根和原资产保护清单；不猜当前活动路径，不改V4/8910/原panel pointer。先隔离child、独立readback，再API/页面与单模块回滚验证。

审查完成状态：静态核验完成；产品/pytest/Mac/API/页面/自然交易日验证均未运行。本结论不对其通过与否作推定。

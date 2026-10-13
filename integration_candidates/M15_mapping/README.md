# M15 两路径独立候选

本包只位于原 M15 开发分支的 `integration_candidates/M15_mapping`，不改变共享 P0、现役 V4 或其他模块。按统一计划 `386d5ce67a6a9914a96162cd47528290b8e7d75f` 的 A5/M15 交付。

## 交付与来源

- 种子 daily 直接复用原 M15 `1dede80b4ff18781849e87e85ca693890ed57979`，39 件 owner 闭包、原四关系范围、registry 时点与恢复资格完全保留。
- 材料路径直接调用 `386d5ce67a6a9914a96162cd47528290b8e7d75f` 的原 manager workspace / issuer parser / 原 archive 和 native identity readers。80 件 manager 闭包与其原调用依赖按原字节打包；没有复制一套映射算法，没有调用经理模型或新建服务池。
- `SOURCE_ORIGINS.json` 给每个复用文件的来源 commit、Git blob。原 Chat 提供既有 owner；本次调度补装的是 `m15_delivery.py`、launcher、保存引用/分页转换、UI 候选与测试/打包，不能归为原 Chat 新提交。
- M03 合成行情使用固定候选 `efeaeb8fc04474b1f38ebda98b35953b580049df` 的原采集与保存链。两份 fixture 是合成报价，不是真实行情。报价 opener 为合成返回、quote=1 / RSS=0 / direct=0 / real socket=0。
- 材料正例是原 acquisition producer + original builder + original archive store/reader + native master writer/reader 生成的合成资料。没有真实外采或模型调用。原 acquisition producer 文件按已固定 manifest 的 SHA256 `1fe2caadfd6b2f67848b05393a02114583d0b05f6790a9b22872971dc6d7a288` 恢复，来自 V4 `f7cb731c384ee6890a87d16c19a5b5a621779477` 来源包；仅 fixture builder 使用它。

## 边界

种子与材料是不同路径。材料内行业映射、显式个股关系各自分页；没有正文、主体/action/span、真实 available/retrieved、原 native identity 时原 owner 拒绝。未配置材料为 NOT_RUN，缺证据为原 INSUFFICIENT/NOT_EVALUATED，不变成合法空。

M03 的顶层 READY_EMPTY 是新闻条数为零；独立 market_snapshot 仍可为 READY。原行情 reader 决定行情准入，不能把新闻当报价。正文材料走独立 archive/native 绑定，不把行情标签当发行人关系。

所有本候选执行标为 MANUAL_RECOVERY；真实开始/生成时间来自原 owner。指定 cutoff 不回写生成时间，不宣称历史 PIT、自然运行、正式资格或全市场覆盖。当前 target eligibility 的 CANNOT_CONFIRM 保留。没有 scheduler 自动启动、订单、真实 provider/model 或凭据路径。

## 默认运行（源码包方式，不要求当前工作目录在仓库内）

先校验：

    python3 /ABSOLUTE/integration_candidates/M15_mapping/verify_release.py
    python3 /ABSOLUTE/integration_candidates/M15_mapping/run_mapping.py --help

依赖：保留 `runtime/V5/pyproject.toml` 和 `uv.lock` 原锁。发布要求 Python >=3.14、pandas >=2.3,<3、pyarrow >=21,<25；使用已获准 Mac 环境现有依赖，不在本任务自动安装或升级。此次云端仅以 Python 3.12.14 / pandas 2.2.3 验证本包执行路径；这些测试不依赖 pyarrow。不能把它记为原 3.14 锁定环境已验。时区数据库需包含 HK/Shanghai/New_York。

1. 拷贝 `examples/both.spec.json`，填写独立 V5 输入根、确切日期/cutoff 和文件列表。例子占位符不可执行。archive v2 必须列全原 reader 需要的 capture/acquisition/builder 证据文件，不能只列三件；由原 M04 reader 返回的完整绑定展开文件列表。native 使用原 exact-date latest/CSV/manifest/receipt 四件。只跑四键种子时 mode=seed 并去掉 material/native/archive 项。
2. 准备不可变输入哈希，不产生行情、正文、关系或资格：

    python3 /ABSOLUTE/.../run_mapping.py prepare --spec /ABSOLUTE/spec.json > /ABSOLUTE/prepared.json

3. 仅初始化一个全新独立 V5 输出目录，不接受已有目录或符号链接：

    python3 /ABSOLUTE/.../run_mapping.py init --root /ABSOLUTE/V5/m15-private-run

4. 显式计算并调用原保存/reader：

    python3 /ABSOLUTE/.../run_mapping.py run --request /ABSOLUTE/prepared.json --root /ABSOLUTE/V5/m15-private-run > /ABSOLUTE/receipt.json

5. 取 receipt 的 `reference` 对象存为 reference.json，然后在新进程冷读：

    python3 /ABSOLUTE/.../run_mapping.py read --reference /ABSOLUTE/reference.json --root /ABSOLUTE/V5/m15-private-run

`read` 先校验已提交 envelope 和每个原 owner 文件的固定字节，再分别启动全新子进程调用原 `us_mapping_research._read_saved`、原 `workspace._read_plan` 与 `verified_plan_attempt`；匹配原 run/target/SHA。子进程禁止写入、网络和再派生进程，绝不重新计算。所有原结果保存于独立 attempts 下，生成过的 run 不覆盖。JSON 路径、符号链接、SHA、session、未来 cutoff、源/输出重叠均严格拒绝。输入哈希证明字节一致，不证明来源真实性。

## 普通 API / 原页面接入（P0 唯一集成者）

普通路由 `/api/v5/source-bundle/us-mapping-saved` 使用现有 `module_api.create_module_server` 与 `module_artifacts.publish_generation`，无需更改共享 Python API。`export` 只产生原 API 的完整标准 records，不激活预览：

    python3 /ABSOLUTE/.../run_mapping.py export --root /ABSOLUTE/V5/m15-private-run --reference /ABSOLUTE/reference.json --module-config /ABSOLUTE/module-api.json --data-kind RECORDED_INPUT_REPLAY > /ABSOLUTE/records.json

测试输入必须使用 SYNTHETIC。现候选不允许把未证来源改成 OWNER_RESULT。P0 在既有 source_bundle 配置 routes 中加入该路由，保留其他 routes 和绑定；以当前 generation 做正常 CAS publish。已有 publisher 合并旧 records，不删除健康 lane。根须有既有 source_bundle marker；本包不创建或替换活动配置。

- overview 查询 `date=YYYYMMDD`，亦支持显式 `date&run_id`。
- 页查询 `date&run_id&lane=seed|industry|individual&offset=0|50|...`；每页 50，全部原行保留，未知总数仍为 null。
- 原 owner 与 delivery run、hash、target 及 session 分开，不人为统一 run。
- `frontend/src/api/m15Mapping.ts` 和 `components/M15SavedMapping.vue` 是完整候选文件。
- `p0_integration/candidate` 提供完整 SavedManagerResultView.vue、vite.config.ts；`preimage`、`manifest.json` 与 `integration.patch` 给出精确前像。前像固定于上述计划 commit。若 P0 已有后续修改，先比较 SHA，再只移植本包新增 import/section/proxy；不得整文件覆盖新变化。
- 组件按用户明确目标日读，不跟旧经理结果偷换日期。切日、失败、翻页先清旧行；翻页固定同 run/SHA。原 UI 仍保留旧经理与其他模块。
- 默认组件是普通页面嵌入，不是测试专用 API。Vue 编译/type/build、原生 DOM/视觉与预览部署仍 NOT_RUN，必须由 Mac 针对固定 commit 验收后 P0 决定接入。

## 失败、停止、恢复、回退

- CLI 成功 exit 0，拒绝 exit 2 并保留原原因；owner 业务 FAILED/PARTIAL 仍可能是成功保存的研究结果，必须读 seed_status/material_status，不能仅看 exit 0。
- 可用 Ctrl-C 停止外层调用；本包未开启后台 scheduler。若中断发生在 owner 保存之后，先读保留的 attempts/原 owner 回执，不能把超时当未执行而重跑。
- 若仅 stdout receipt 丢失，`run_mapping.py list --root ...` 只读重建所有已保存 reference，再用 read；不会运行 owner。
- 若 results 尚未提交但 attempts 中已有产物，此状态为需核查，保留文件；没有自动清 claim、删除锁或自动 retry。不得承诺这一未完成 attempt 已恢复。
- 缺源/SHA/session/registry/正文/时点/身份失败先修输入，不重试同坏输入。所有真实业务仍遵原窗口；错过记 MISSED，未实现自然调度不伪报自然通过。
- 单模块回退由 P0 以已有 generation 的已验证引用恢复原 module records，移除本候选的页面接线即可。保留所有候选、原 owner 保存文件和旧 release；不删除/停止 V4。

## 测试与剩余验收

运行 `python3 run_offline_tests.py`：本候选 Python 全套、原回归独立进程、Node client 全套。详细真实输出见 `evidence/offline-tests.log`；测试会创建/清理自己的临时隔离目录，不用生产根。

包含：M03 quote-only→seed→原保存与新进程冷读；当前合成资料经原 producer/builder/archive/native reader→原行业/个股映射→原 workspace 保存；缺正文/时点/身份、错 span/来源独立性、新闻冒行情、错 session、未来 cutoff、篡改字节、旧成功保留、stdout 丢失后的只读恢复；原 API GET/分页同 run、POST405、错日期503、GET 前后磁盘无变。

NOT_RUN：Mac、锁定3.14环境安装、Vue type/build与原生页面交互、P0激活/预览部署、真实目标日三源及真实材料资格、经理当日窗口、新日自然/跨日与完整18模块 release 回归。旧 20261007 原真实测试需要其独立真实 request，未在本次以合成数据冒充重跑。此包是可运行完整代码候选，不是 M15 全业务/自然/正式验收完成。

## 固定候选历史说明

首版 `0d53c6d64299897fbfccaa5e4eca1e96ca285ed4` 的530件字节曾逐件远端回读，但当时冷读仅校验封存 envelope 和原owner字节，尚未在冷读子进程实际调用原 saved reader；因此不将它记为完整验收。本次修订只补该必要冷读接线和对应正反/独立进程证据，不改算法、共享P0或真实执行范围。

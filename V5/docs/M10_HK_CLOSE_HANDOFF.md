# M10 默认原 owner 与冷读链交付

## 固定前像和本次范围

- 仓库：私有 `lexi2016/v5`。
- 唯一分支：`dev/m10-github-handoff-20261011`。
- 实施前 HEAD：`21e9991dc81b540e46765bdb6895cf0a281ab253`。
- 原算法 donor：`lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`。
- 本次只补 M10 默认原 owner、不可变发布、冷读、CAS 与离线验收。原 5 个 publication 测试先实跑通过，保留不改。
- `handoffs/M10/V5/`、全部原 SOURCE/历史反馈、main/P0/其他模块未修改。

## 真实执行路径

`build_default_hk_close_review(data_root, trade_date, run_root, stage_selection_root, expected_generation, expected_native_sha256)`：

1. 核对隔离 capsule manifest 自身 SHA、每个原件 SHA-256、Git blob 和字节数。
2. 仅复制目标日收盘快照三件套、exact-date 模型三件套及原七阶段 selection 三件套到临时私有目录。输入根只读，与 run_root 不可重叠。
3. 子进程以 `-I -S -B` 隔离启动，避免 `.pth`、环境 PYTHONPATH 或其他 checkout 的同名 ops 注入。无安装、网络、服务或真实凭据。
4. 先用原 CloseSnapshotStore 验证现成快照。即便当前日缺快照也硬拒绝，不调用真实采集。合格快照由原 collector 走 IDEMPOTENT_REUSE，再执行原 builder → 原 ReviewStore.publish_native(expected_sha256) → 原 ReviewStore 冷读。
5. 输入文件、原 model payload、原 stage 响应和原因、source/code/config/calendar SHA 形成计算 identity。相同成功 identity 只读复用。不同输入新 run。
6. 原 native expected SHA 与 V5 expected generation 分别核对。原 native 数据写入仅在临时 V5 工作区；最后整套不可变 run 原子改名，再原子提交 latest_success。失败留下 attempt，旧成功可读。
7. pointer 写失败的 orphan 不算已提交，冷 reader 拒绝。重试必须满足创建时 parent generation 和 native SHA，才能补交指针。不会重算或覆盖旧 run。

`HKCloseReviewReader.read(run_id)` 重读 payload/publication/manifest/receipt，核对 run、schema、全体 SHA、输入身份、原 publication 路径/date/payload SHA、原 native manifest/receipt、提交记录。`read_latest()` 同时验证 generation。

## API 只读接入接口

`read_hk_close_projection(run_root, run_id=None)` 仅冷读，不调用 producer；输出同一提交 run/generation。

- 原计算产物完整保留在 store，读回 SHA 可复核。
- 展示层为 RECORDED_INPUT_REPLAY；不会把原 native 内层标签冒充自然运行。
- 原 PARTIAL_WITH_ROWS 原因保留，未能确认的 stage 指标及命中设为 null/CANNOT_CONFIRM。
- 缺模型/阶段仍展示 Top20；verified READY_EMPTY 与缺失不同。
- 该接口尚未部署到普通 HTTP 或 UI。本次没有修改共享 `/api/v3/review` 或 A 股内容。
- 自然调度仍未开启。冻结全天槽为 HK_SECURITIES_TRADE_DAY 16:10；半日未核时 SCHEDULE_BINDING_UNVERIFIED。禁止以 16:08/12:10 回放代替生产触发。

## Capsule 的明确边界

`integration_candidates/M10/CAPSULE_INTEGRATION_CANDIDATE/manifest.json` 只描述隔离候选装配，不修改原 vendor/source manifest。

原 canonical 的 `stage_center/_selection_parts/_namespace.py` 缺失；使用已交 M10 vendor 的同用途冻结文件，manifest 明确记录真实来源，绝不伪装成 canonical 原件。空 package markers 为临时装配元数据。

## 单次 Mac 验收

在新的隔离 checkout 固定到本次交付 commit 后执行，不覆盖活动目录，不启动/停止任何服务：

```sh
# 使用 Mac 已有 Python 和 pytest 依赖目录，不安装、不读取凭据。
# PYTHON 为现有解释器，PYTEST_SITE 为其已有、包含 pytest/__init__.py 的 site-packages。
"$PYTHON" -I -S -B V5/tests/run_m10_acceptance.py \
  --pytest-site-packages "$PYTEST_SITE" \
  --evidence-dir "$ISOLATED_EVIDENCE_DIR"
```

runner 一次完成 28 项 M10 产品测试与 10 项原冻结测试，并保存开始/结束、完整 argv、退出码、stdout/stderr 和被测源码 SHA/bytes。使用 Python `-S` 避免旧环境 `.pth` 指向其他 checkout 的历史问题。工具只使用临时合成 fixture，没有生产数据或 Futu 连接。

Mac 验收必须独立核对 `git rev-parse HEAD` 等于发布者的固定 commit；本地代码字节须与 report.json 一致。不能用本说明或云端通过替代 Mac 测试结果。

## CLI

```sh
PYTHONPATH=V5/src "$PYTHON" -m v5_shadow.hk_close_daily build \
  --data-root "$ISOLATED_RECORDED_INPUT_ROOT" --date 20260730 \
  --stage-selection-root "$ISOLATED_STAGE_ROOT" --run-root "$PRIVATE_V5_RUN_ROOT"
PYTHONPATH=V5/src "$PYTHON" -m v5_shadow.hk_close_daily read --run-root "$PRIVATE_V5_RUN_ROOT"
```

第一次 generation/native SHA 均为 None；变更输入时从上次成功的 latest_identity().generation 和原 review SHA 获得两项 CAS，分别传入 `--expected-generation` 与 `--expected-native-sha256`。同一成功 identity 重试保持纯复用，不倒退 latest。

## 准入与未跑状态

- 工程：离线真实原 owner/default chain 已测；fixture 始终标明合成/录制回放。
- 真实输入：原冻结 CloseSnapshotStore 验证不等于 M02 成员资格/PIT证明。当前没有可核的该证据，输出一直显式 `M02_MEMBERSHIP_PIT_UNVERIFIED` 与 natural_admission=UNVERIFIED，不手填 formal verified。
- 页面：只读投影函数已测；普通 HTTP/UI 集成与发布 NOT_RUN。
- 自动接续：自然调度与真实网络采集 NOT_RUN，未启用。
- 完整验收：Mac 独立测试、连续两个适用日自然验收 NOT_RUN。
- 原测试中 2 项未跑：vipdoc importer 不在给定闭包；完整 scheduler/runtime_tasks 也不在该闭包。runner 明列原因，不能宣称全仓测试通过。
- 云端使用现有 Python 3.12；Mac 原环境版本另验，不声称已验证全部依赖/平台版本。

## 应用与回滚

独立 checkout 使用固定 Git commit 或本次 forward.patch；先 apply --check。reverse.patch 是真正 after→before，并已验证可恢复全部前像字节。只回滚本次 M10 源码，不 reset --hard，不回滚其他模块/B 数据。此交付未发布 API/UI，也没有宣称完成代码/UI独立回滚验收。数据 run 不可变，旧成功保留；任何上线/指针回退由集成者另核当前 CAS。

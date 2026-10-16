# 固定源码、计划与回执索引
核验时点：2026-10-16T13:20:56.216Z。仓库私有；接手人需使用其已有仓库授权。没有更改共享权限。
## 实际集成源码

- 分支：`dev/v5-main-integration-20261012`
- commit：`01d93717905813705732161d4d79062ae5af2d99`
- Git tree：`29e4de722ccf35bb789ba29ad32c883ce9df8adb`
- [打开完整2363文件树](https://github.com/lexi2016/v5/tree/01d93717905813705732161d4d79062ae5af2d99)
- 源码入口：[V5/run_shadow.py](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/run_shadow.py)、[V5/src](https://github.com/lexi2016/v5/tree/01d93717905813705732161d4d79062ae5af2d99/V5/src)、[frontend](https://github.com/lexi2016/v5/tree/01d93717905813705732161d4d79062ae5af2d99/frontend)
- [Python声明](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/pyproject.toml)、[uv.lock](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/uv.lock)、[前端锁](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/frontend/package-lock.json)
- [源码包隔离运行说明](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/handoffs/P0/cloud-isolation-20261014/README.md)、[package-check边界](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/handoffs/P0/cloud-review-20261014/README.md)、[M17依赖后续修复](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/handoffs/P0/cloud-m17-dependencies-20261014/README.md)
- 默认main只有2文件，不作为整合基线。原START_HERE、V5/README含较早状态，最新限定修订按具体固定证据判定，不按文件标题“当前”推定今日状态。
## 原计划（原样保留编号和目标）

- [原总计划24c6d60d](https://github.com/lexi2016/v4/blob/24c6d60d524f43fcf4209ec8b078ec02cb34417e/V5/docs/superpowers/plans/2026-10-09-v5-master-delivery.md)
- [原迁移执行计划d1bf0346](https://github.com/lexi2016/v4/blob/d1bf034640ca2e5957423de2745a98e159b69af2/V5/docs/superpowers/plans/2026-10-10-v5-migration-execution.md)
- [10/13统一方案固定版386d5ce6](https://github.com/lexi2016/v5/blob/386d5ce67a6a9914a96162cd47528290b8e7d75f/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)
- [本次集成树中统一方案及后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)

计划中的前部队列表和后部增量可能停留在不同时间；以固定SHA+具体回执的范围和时间核对，不删除失败历史，也不用旧段落覆盖后续已通过事实。

## 18模块真实源码入口
### M01 A行情与公式面板来源

- `dev/m01-github-handoff-20261011` @ `ea96a80cf9d79e638ee08e15cb0bf92368261ada`
- [源码树](https://github.com/lexi2016/v5/tree/ea96a80cf9d79e638ee08e15cb0bf92368261ada)；[入口/manifest](https://github.com/lexi2016/v5/blob/ea96a80cf9d79e638ee08e15cb0bf92368261ada/handoffs/M01/START_HERE.md)
- 来源/公式候选与历史回执；不认定真实新日闭环完整。
- 115文件；相同路径+blob在整合树中0件，相同blob在任一路径中21件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M02 HK行情、主表与资格来源

- `dev/m02-github-handoff-20261011` @ `776acce9328aa102e3db6973405f01260f15239d`
- [源码树](https://github.com/lexi2016/v5/tree/776acce9328aa102e3db6973405f01260f15239d)；[入口/manifest](https://github.com/lexi2016/v5/blob/776acce9328aa102e3db6973405f01260f15239d/handoffs/M02/START_HERE.md)
- 已有完整候选报告；本次核了树，未重验全部运行闭包。
- 149文件；相同路径+blob在整合树中0件，相同blob在任一路径中96件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M03 US行情来源

- `dev/m03-github-handoff-20261011` @ `3020bb6b0abd30fc9a243cfdee7ec0f121e2c178`
- [源码树](https://github.com/lexi2016/v5/tree/3020bb6b0abd30fc9a243cfdee7ec0f121e2c178)；[入口/manifest](https://github.com/lexi2016/v5/blob/3020bb6b0abd30fc9a243cfdee7ec0f121e2c178/handoffs/M03/START_HERE.md)
- 包含完整行情collector候选、旧被拒版本和接页增量；按manifest选原件。
- 200文件；相同路径+blob在整合树中0件，相同blob在任一路径中120件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M04 研究情报与归档

- `dev/m04-github-handoff-20261011` @ `0bb46df890d4b1a57fcc17982a9800cac2f18146`
- [源码树](https://github.com/lexi2016/v5/tree/0bb46df890d4b1a57fcc17982a9800cac2f18146)；[入口/manifest](https://github.com/lexi2016/v5/blob/0bb46df890d4b1a57fcc17982a9800cac2f18146/integration_candidates/M04_capture/README.md)
- 包含M04_capture完整候选及modules/M04；环境和来源闭包需原manifest约束。
- 995文件；相同路径+blob在整合树中0件，相同blob在任一路径中887件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M05 A预选池

- `dev/m05-github-handoff-20261011` @ `5d868fc09fba7f7fe210e603a28015e271117077`
- [源码树](https://github.com/lexi2016/v5/tree/5d868fc09fba7f7fe210e603a28015e271117077)；[入口/manifest](https://github.com/lexi2016/v5/blob/5d868fc09fba7f7fe210e603a28015e271117077/handoffs/M05/START_HERE.md)
- 实际源码与release；七业务来源/六执行lane覆盖仍待精确映射。
- 152文件；相同路径+blob在整合树中55件，相同blob在任一路径中109件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M06 HK预选池

- `dev/m06-github-handoff-20261011` @ `ddb07572e7bd24efff2a9624806e2487129d208a`
- [源码树](https://github.com/lexi2016/v5/tree/ddb07572e7bd24efff2a9624806e2487129d208a)；[入口/manifest](https://github.com/lexi2016/v5/blob/ddb07572e7bd24efff2a9624806e2487129d208a/handoffs/M06/START_HERE.md)
- 原source、patch及daily增量；已过自然current有限步骤不等全链。
- 212文件；相同路径+blob在整合树中0件，相同blob在任一路径中117件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M07 A阶段选股

- `dev/m07-github-handoff-20261011` @ `e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31`
- [源码树](https://github.com/lexi2016/v5/tree/e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31)；[入口/manifest](https://github.com/lexi2016/v5/blob/e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31/handoffs/M07/DELIVERY.json)
- 已有完整链交付/OWNER_CLOSURE；本次未重跑。
- 159文件；相同路径+blob在整合树中0件，相同blob在任一路径中133件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M08 HK阶段选股

- `dev/m08-github-handoff-20261011` @ `01f1a6347722081cbbf97b54204bf033e6d01938`
- [源码树](https://github.com/lexi2016/v5/tree/01f1a6347722081cbbf97b54204bf033e6d01938)；[入口/manifest](https://github.com/lexi2016/v5/blob/01f1a6347722081cbbf97b54204bf033e6d01938/handoffs/M08/START_HERE.md)
- 已有完整owner报告；全部窗口与Stage8实际覆盖仍待验。
- 214文件；相同路径+blob在整合树中0件，相同blob在任一路径中118件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M09 A收盘复盘

- `v5/m09-handoff-20261011` @ `3d1d04283f4d5ca05923b05c496a97e79145d275`
- [源码树](https://github.com/lexi2016/v5/tree/3d1d04283f4d5ca05923b05c496a97e79145d275)；[入口/manifest](https://github.com/lexi2016/v5/blob/3d1d04283f4d5ca05923b05c496a97e79145d275/M09_CLOSE_CHAIN_20261012/START_HERE.md)
- 完整候选、before/after/历史回放并存，不可整树无脑叠加。
- 1099文件；相同路径+blob在整合树中18件，相同blob在任一路径中344件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M10 HK收盘复盘

- `dev/m10-github-handoff-20261011` @ `9ab214b0ad5542111c04d10f50cac989644205f7`
- [源码树](https://github.com/lexi2016/v5/tree/9ab214b0ad5542111c04d10f50cac989644205f7)；[入口/manifest](https://github.com/lexi2016/v5/blob/9ab214b0ad5542111c04d10f50cac989644205f7/handoffs/M10/START_HERE.md)
- 原HK收盘源码与回执；完整新日scheduler能力待验。
- 189文件；相同路径+blob在整合树中0件，相同blob在任一路径中116件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M11 盘中研究与研究复盘

- `dev/m11-github-handoff-20261011` @ `6abba1b36dce3d9696b5a0e401ba86a96d9b10ec`
- [源码树](https://github.com/lexi2016/v5/tree/6abba1b36dce3d9696b5a0e401ba86a96d9b10ec)；[入口/manifest](https://github.com/lexi2016/v5/blob/6abba1b36dce3d9696b5a0e401ba86a96d9b10ec/handoffs/M11/START_HERE.md)
- 原owner、依赖、fixture与补丁存在，不属于只有方案。
- 333文件；相同路径+blob在整合树中81件，相同blob在任一路径中237件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M12 视频FUPAN

- `dev/m12-github-handoff-20261011` @ `385b1068054f3d20688344961b3a3cf34d6a7bb4`
- [源码树](https://github.com/lexi2016/v5/tree/385b1068054f3d20688344961b3a3cf34d6a7bb4)；[入口/manifest](https://github.com/lexi2016/v5/blob/385b1068054f3d20688344961b3a3cf34d6a7bb4/handoffs/M12/START_HERE.md)
- 原生命周期源码与集成补充存在；真实新视频全链未验。
- 139文件；相同路径+blob在整合树中11件，相同blob在任一路径中45件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M13 公告研究与选股

- `dev/m13-partial-pages-20261012` @ `308af26862daf005c5c5800d15c5053c84275938`
- [源码树](https://github.com/lexi2016/v5/tree/308af26862daf005c5c5800d15c5053c84275938)；[入口/manifest](https://github.com/lexi2016/v5/blob/308af26862daf005c5c5800d15c5053c84275938/README.md)
- 仅10文件partial-pages补充；不是完整公告owner，原主分支待核。
- 10文件；相同路径+blob在整合树中8件，相同blob在任一路径中8件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M14 超跌研究与选股

- `dev/m14-github-handoff-20261011` @ `ad9a61d26c487748ba017b69250571ae5a38bbab`
- [源码树](https://github.com/lexi2016/v5/tree/ad9a61d26c487748ba017b69250571ae5a38bbab)；[入口/manifest](https://github.com/lexi2016/v5/blob/ad9a61d26c487748ba017b69250571ae5a38bbab/handoffs/M14/START_HERE.md)
- 原source、历史被拒候选、canary/接页候选并存；不是所有数据已合格。
- 220文件；相同路径+blob在整合树中0件，相同blob在任一路径中105件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M15 美股到港股映射

- `dev/m15-github-handoff-20261011` @ `821a25b1667a28073360c96cf8702ab57dbd233f`
- [源码树](https://github.com/lexi2016/v5/tree/821a25b1667a28073360c96cf8702ab57dbd233f)；[入口/manifest](https://github.com/lexi2016/v5/blob/821a25b1667a28073360c96cf8702ab57dbd233f/handoffs/M15/START_HERE.md)
- 包含M15_mapping实际runtime候选、release与原材料；seed与material分开。
- 681文件；相同路径+blob在整合树中48件，相同blob在任一路径中570件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M16 经理候选公开资料任务

- `dev/m16-github-handoff-20261011` @ `d18469212c86bec95303ca746cb4b90dd9a863de`
- [源码树](https://github.com/lexi2016/v5/tree/d18469212c86bec95303ca746cb4b90dd9a863de)；[入口/manifest](https://github.com/lexi2016/v5/blob/d18469212c86bec95303ca746cb4b90dd9a863de/handoffs/M16/START_HERE.md)
- 包含独立生命周期/接纳修复候选和原source；不等所有job能力终验。
- 403文件；相同路径+blob在整合树中3件，相同blob在任一路径中171件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M17 尾盘量价发现与持续跟踪

- `dev/m17-github-handoff-20261011` @ `6d459cbc1e694eed413d142c75be64241a727e7f`
- [源码树](https://github.com/lexi2016/v5/tree/6d459cbc1e694eed413d142c75be64241a727e7f)；[入口/manifest](https://github.com/lexi2016/v5/blob/6d459cbc1e694eed413d142c75be64241a727e7f/handoffs/M17/START_HERE.md)
- 实际owner/vendor与1530闭包参考；不能用late读回替代15:30现场。
- 314文件；相同路径+blob在整合树中24件，相同blob在任一路径中154件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

### M18 经理决策账本、汇总与计划

- `dev/m18-bounded-manager-readback-20261012` @ `5c327e45d99468d0ade73ee4acff6e0130f02852`
- [源码树](https://github.com/lexi2016/v5/tree/5c327e45d99468d0ade73ee4acff6e0130f02852)；[入口/manifest](https://github.com/lexi2016/v5/blob/5c327e45d99468d0ade73ee4acff6e0130f02852/integration_candidates/M18_request_binding/README.md)
- bounded/request-binding源码候选；另有daily/offline小补充，完整首批经理业务未验。
- 1370文件；相同路径+blob在整合树中8件，相同blob在任一路径中1351件。仅用于定位，不能据此断言已合入/缺实现/测试通过。

## 其他已核候选/补充分支

- [dev/m14-stored-supplement-20261012](https://github.com/lexi2016/v5/tree/a20ea3b04cac63fbbfc4610e891ae1f6e8c171ba)，`a20ea3b04cac63fbbfc4610e891ae1f6e8c171ba`，10文件。保留独立候选，不自动合并。
- [dev/m18-daily-assembly-20261012](https://github.com/lexi2016/v5/tree/eae78ea4d2842a71d64721ae0f633e5583e80642)，`eae78ea4d2842a71d64721ae0f633e5583e80642`，4文件。保留独立候选，不自动合并。
- [dev/m18-offline-pages-20261012](https://github.com/lexi2016/v5/tree/325730f0979a9989d53dd0ff3bade5b238912455)，`325730f0979a9989d53dd0ff3bade5b238912455`，4文件。保留独立候选，不自动合并。
- [dev/m18-offline-v2-20261012](https://github.com/lexi2016/v5/tree/8bea98c2bd506d42c00f2616dd04949d7a2b232d)，`8bea98c2bd506d42c00f2616dd04949d7a2b232d`，17文件。保留独立候选，不自动合并。
- [v5/m09-candidate-20261011-r1](https://github.com/lexi2016/v5/tree/d0f9905940584777abbcae248850ebc487cade63)，`d0f9905940584777abbcae248850ebc487cade63`，870文件。保留独立候选，不自动合并。

## 完整refs与文件清单

BRANCH_SNAPSHOT.json保留本次32个分支的固定HEAD及23个模块相关树的比较摘要。SOURCE_FILE_MANIFEST.json列2363个集成文件的Git blob SHA-1、大小和模式；不是执行验收，也不是逐文件SHA-256。被拒/旧候选在原仓库保留作历史，不可视为推荐实现。

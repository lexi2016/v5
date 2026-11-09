# V5 Module Registry

Audit baseline: integration commit `01d93717905813705732161d4d79062ae5af2d99`.
This registry is a navigation aid derived from the 2026-10-16 source index and bounded evidence notes. It is **not** a runtime registry, release manifest, or current branch-head assertion. Before changing a module, re-read the branch HEAD and its owner manifest.

## Ownership index

| ID | Module | Candidate source ref | Fixed source commit | Bounded evidence / remaining gap |
|---|---|---|---|---|
| M01 | A行情与公式面板来源 | [dev/m01-github-handoff-20261011](https://github.com/lexi2016/v5/tree/ea96a80cf9d79e638ee08e15cb0bf92368261ada) | `ea96a80cf9d79e638ee08e15cb0bf92368261ada` | 真实新日来源与消费身份、自然运行待验 |
| M02 | HK行情、证券主表与资格 | [dev/m02-github-handoff-20261011](https://github.com/lexi2016/v5/tree/776acce9328aa102e3db6973405f01260f15239d) | `776acce9328aa102e3db6973405f01260f15239d` | 限定真实采集/恢复/冷读/HTTP-DOM已证；PIT与资格仍CANNOT_CONFIRM |
| M03 | US行情来源 | [dev/m03-github-handoff-20261011](https://github.com/lexi2016/v5/tree/3020bb6b0abd30fc9a243cfdee7ec0f121e2c178) | `3020bb6b0abd30fc9a243cfdee7ec0f121e2c178` | 一次真实session与M15 seed已证；自然下一session及全链待验 |
| M04 | 研究情报与归档 | [dev/m04-github-handoff-20261011](https://github.com/lexi2016/v5/tree/0bb46df890d4b1a57fcc17982a9800cac2f18146) | `0bb46df890d4b1a57fcc17982a9800cac2f18146` | 真实8档恢复有历史证据；Mac发布被拒，整体验收未过 |
| M05 | A股预选池 | [dev/m05-github-handoff-20261011](https://github.com/lexi2016/v5/tree/5d868fc09fba7f7fe210e603a28015e271117077) | `5d868fc09fba7f7fe210e603a28015e271117077` | 已接入v192 valid-empty限定适配；七来源全链未证 |
| M06 | 港股预选池 | [dev/m06-github-handoff-20261011](https://github.com/lexi2016/v5/tree/ddb07572e7bd24efff2a9624806e2487129d208a) | `ddb07572e7bd24efff2a9624806e2487129d208a` | 部分自然步骤已证；整体自然链未过 |
| M07 | A股阶段选股 | [dev/m07-github-handoff-20261011](https://github.com/lexi2016/v5/tree/e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31) | `e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31` | 独立候选/历史测试回执存在；整链自然验收待核 |
| M08 | 港股阶段选股 | [dev/m08-github-handoff-20261011](https://github.com/lexi2016/v5/tree/01f1a6347722081cbbf97b54204bf033e6d01938) | `01f1a6347722081cbbf97b54204bf033e6d01938` | 原阶段候选存在；完整窗口与Stage8真实覆盖待验 |
| M09 | A股收盘复盘 | [v5/m09-handoff-20261011](https://github.com/lexi2016/v5/tree/3d1d04283f4d5ca05923b05c496a97e79145d275) | `3d1d04283f4d5ca05923b05c496a97e79145d275` | 历史回放/PARTIAL有证；新日完整自然链未验 |
| M10 | 港股收盘复盘 | [dev/m10-github-handoff-20261011](https://github.com/lexi2016/v5/tree/9ab214b0ad5542111c04d10f50cac989644205f7) | `9ab214b0ad5542111c04d10f50cac989644205f7` | 原收盘源码与回执存在；完整scheduler待验 |
| M11 | 盘中研究与研究复盘 | [dev/m11-github-handoff-20261011](https://github.com/lexi2016/v5/tree/6abba1b36dce3d9696b5a0e401ba86a96d9b10ec) | `6abba1b36dce3d9696b5a0e401ba86a96d9b10ec` | 原owner与依赖闭包存在；六槽真实窗口待验 |
| M12 | 视频复盘 | [dev/m12-github-handoff-20261011](https://github.com/lexi2016/v5/tree/385b1068054f3d20688344961b3a3cf34d6a7bb4) | `385b1068054f3d20688344961b3a3cf34d6a7bb4` | 生命周期与导入源码存在；真实新视频全链待验 |
| M13 | 公告研究与选股 | [dev/m13-partial-pages-20261012](https://github.com/lexi2016/v5/tree/308af26862daf005c5c5800d15c5053c84275938) | `308af26862daf005c5c5800d15c5053c84275938` | 此ref仅10文件partial-pages补件，不是完整公告owner；真实审核revision/详情分页消费未闭合 |
| M14 | 超跌研究与选股 | [dev/m14-github-handoff-20261011](https://github.com/lexi2016/v5/tree/ad9a61d26c487748ba017b69250571ae5a38bbab) | `ad9a61d26c487748ba017b69250571ae5a38bbab` | 690 pending观察与独立页有证；不能视作正式选股；单位/资格/PIT仍待证 |
| M15 | 美股到港股映射 | [dev/m15-github-handoff-20261011](https://github.com/lexi2016/v5/tree/821a25b1667a28073360c96cf8702ab57dbd233f) | `821a25b1667a28073360c96cf8702ab57dbd233f` | seed两关系真实执行/普通页有证；material路径/自然运行/完整资格未过 |
| M16 | 经理候选公开资料任务 | [dev/m16-github-handoff-20261011](https://github.com/lexi2016/v5/tree/d18469212c86bec95303ca746cb4b90dd9a863de) | `d18469212c86bec95303ca746cb4b90dd9a863de` | 限定cache-root→240 facts→冷读/页面有证；全job与资格边界未整体验收 |
| M17 | 尾盘量价发现与持续跟踪 | [dev/m17-github-handoff-20261011](https://github.com/lexi2016/v5/tree/6d459cbc1e694eed413d142c75be64241a727e7f) | `6d459cbc1e694eed413d142c75be64241a727e7f` | 依赖闭包限定修复有证；15:30真实自然窗口未验 |
| M18 | 经理账本、汇总与计划（B01） | [dev/m18-bounded-manager-readback-20261012](https://github.com/lexi2016/v5/tree/5c327e45d99468d0ade73ee4acff6e0130f02852) | `5c327e45d99468d0ade73ee4acff6e0130f02852` | 请求拒绝路径/离线页候选有证；三策略同run业务闭环未完成 |

## Integration rules

1. P0 is shared infrastructure, not M19. B01 is M18.
2. Candidate refs identify review material; they do not imply their full trees belong in the integration branch.
3. M13's listed ref is explicitly partial-pages only. Its complete owner/source branch remains unresolved in this snapshot; do not treat this row as a complete M13 source declaration.
4. Module owner identity, scheduler lane, API route and frontend page are distinct. A module may use shared infrastructure without becoming a separate service.
5. Each future update must append: integration SHA, source/owner SHA and PIN, files changed, dependency/config SHA, tests actually run, result/log SHA, tests not run, runtime receipt, and remaining blockers.
6. Status must be one of evidence levels in [Repository Map](REPOSITORY_MAP_AND_ORGANIZATION.md); never mark complete from source presence or historical partial tests.

## P1 execution priority

- M13: approved/reviewed revision inputs → immutable save/import → ordinary detail and pagination/cutoff consumer.
- M14: preserve READY_WITH_GAPS/CANNOT_CONFIRM and pending reasons; no fabricated empty pool or qualification upgrade.
- M03/M15: real source/material inputs → fixed run and exact saved readback → manager consumer.
- M18: consume only contract-accepted products; same manager run/generation/SHA across save, independent cold read, API and page.
- Full system acceptance remains separate: fixed release regression, natural applicable-day continuity, independent startup and rollback.

# M06 限定自然运行与动态页面部署回执（2026-10-13）

本件仅转存主控已实际读取的 Mac 执行回执；转存者未执行测试、部署、模型生成或 Mac 文件读取。时间均为北京时间（UTC+08:00）。末次状态核验：2026-10-13 17:54:26。

## 固定代码及运行结果

- M06 current：`c518d0c4bf8d947881586a7ed667f2a9ac5c6d1e`；P0 route：`161e17972bed079413a1812320c06676246682a8`。
- 自然准入：17:32:50.160822。P0 run `9a051e7a4b16453a9705f7cf2bf61c30`：17:32:54.781867–17:33:20.464899，SUCCEEDED / readback PASS。
- M06 run `35f98194cfae491d9822f8f014fdf3c8`：17:32:59.181976–17:33:09.989429，SUCCEEDED / readback PASS。
- EXISTING_VERIFIED_POOL，100 行；signal=20261013、target=20261014、eligibility=20261013。source run=`20261014-hk-connect-d1-top100-0-2-c448bcd60ebe`。owner_reused=false 表示新增 owner 运行记录，不代表模型重新计算。
- 17:33:26.693780：CURRENT_SUCCESS_PROMOTED。17:38:41 及 17:49:13（第 40 tick）复核为 REUSED_SUCCESS / REUSED_CURRENT_SUCCESS；两 ledger 各 1 条，current 不变，无新增 owner attempt。

## 动态页面部署回执

- 部署前发现活动 runtime 的旧 M06 fixed reader 不支持 dynamic，未直接误切。独立组合树只更换 `m06_readonly.py` 与 `p0_hk_preselection.py`，SHA-256 见 verification.json。
- runledger / worker 及 50 个 owner 文件同字节复用；保留活动 18 模块 module_api 与 P0 161e route。
- Mac 9 项定向测试全部通过。17:52:45–17:52:57 临时 loopback 验证后有序切换，仅 source PID 88709 → 18570，原端口 61236；前端 PID 54780、manager 及 V4 保留。
- 新日期 100 行 payload 与原 owner 冷读全等；31 次真实 HTTP jsdom 检查零错误；其他 10 路 source 语义一致；2,653 个保护文件不变。此为 HTTP / jsdom 验证，不是原生浏览器视觉验收。

## 未完成边界

整体 daily 仍为 DISPATCH_ATTEMPT_ONLY；manager=BLOCKED_POST_OWNER_REQUEST_MISSING，natural_verified=false。不能宣称全链自然验证或完整模块验收通过。旧 M18 run `46596b03c2ab4e29b1219fd2e5eb698f` 独立保留，本次 M06 不归入旧 manager run。

主控回执证据标识：`turn01a1349e-09aa-7532-b1c1-d70e5f2a60ba`、`01a134aa-b688-7551-8923-3757117e6e76`。本次 GitHub 提交仅新增本反馈目录中的两份文字记录，不包含股票行、数据文件、凭据或私有绝对路径。

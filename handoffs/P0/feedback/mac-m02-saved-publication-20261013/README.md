# M02 saved publication：主控 Mac 回执转存

本件仅转存主控读取的 Mac 真实回执，转存者未重测、采集、生成模型或读取 Mac 文件。以下时间均为 2026-10-13 北京时间。

## 原产物及限定结论

- 原 M02 代码标识：`ce6cddce...`（主控提供的缩写，不补造完整 hash）。build/coldread：18:26:14.297–18:26:15.229，exit 0。target=20261013、signal=20261012、native E=20261013；membership 7 文件、698 条，native 4，HK02 九资产。
- run：`37139d842d68ad1bfb6bb0144262d65411f4ad131bb1ea6a2155b53144a47297`。SOURCE_IDENTITY_ONLY；temporal=CANNOT_CONFIRM；三源 PIT 与正式历史资格均为 false。
- 原 SDK 手动调用两板各 698、RET 0；RAW_CAPTURED SHA-256：`b4fdab446aa1083f44b4af909add39432fdbda6db766846671a5d121281a908c`。整体 collector 最终因 stock_owner NaN 失败，不能以局部成功替代整体通过。
- 原 recovery：18:22:38.544–18:22:38.788，PRIVATE_MEMBERSHIP_PUBLISHED 七件；coldread 18:22:38.789–18:22:38.869 成功；过早 asof 仍拒绝；execution_trigger=manual_controlled、natural_verified=false。原 receipt.manual flag 未核实，本件不引用或赋值；手动受控执行不代表自然执行。

## 实际 saved binding 发布

- 接线候选：`a451275c5eee5ec63139b7e8f886624ebdd4c7d5`。云端 18 项定向 PASS、0 skip，仅为云端测试。
- Mac 实际操作：18:58:54–19:00:00，exit 0；18:59:24 CAS 发布。generation 从 `5afd3802652bc36e8ff67b56124f8fd0782c2e5cc82851494fc24e4a5e665945` 更新为 `ef028788c825681136ef76318ba389c384b8f3eb38191e01c1e9f8befdcbbe21`。
- 仅隔离运行副本的 2 个桥文件匹配前像后更新，使用原 publish_m02_saved_binding / coldreader；未重跑 build、采集或模型。
- M01/M03/M05 三行 canonical 全保留，其余 10 路语义不变。data_kind=RECORDED_INPUT_REPLAY；M02 发布内容无私有绝对路径。
- 实际部署前端 DOM 15 请求全部 HTTP 200、0 error；没有原生浏览器截图验收。M06 target=20261014 / 100 行仍正常。
- API 61236 / PID 18570、前端 54780 / PID 88722、经理 63668 / PID 17107 未重启；V4 及其他保护源、配置、输入不变。临时 58301 / PID 27947 核对身份后停止。

主控总体计数原样记录：18/14/14/0/0（本件不补造各位定义）。M02 未完整准入；限定 M06 自然运行计数为 1。本件不提升 PIT、历史资格、自然运行或全链验收结论。

证据：主控读取 Mac 线程 `01a12e51-a0ec-705c-96e5-26cfd89360f8`，turn `01a134e7-6b61-750a-afbf-599f1aed5479` 的真实回执。本提交仅新增本目录 README.md 和 verification.json，不含真实输入或私有路径。

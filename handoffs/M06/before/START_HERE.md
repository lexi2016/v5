# M06实际源码审阅补包：HK Top100

固定目标f7cb731c384ee6890a87d16c19a5b5a621779477，历史报告164c010c7eaa1659db9bfed0ff5f123c7a39eefc。60份GitHub原件；逐件commit/path/blob/SHA256/bytes及源manifest/原owner提交在SOURCE_MANIFEST.json。所有blob与connector吻合、34件hk_preselection胶囊满足原manifest、ZIP CRC与逐件SHA读回已核。没有产品执行、测试、模型加载、行情采集、部署或Mac真实数据。

## 实际源码
- V5/src/v5_shadow/hk_preselection.py及只读共享a_preselection/contract/composition/digest/provider依赖
- V5/tests/test_hk_preselection.py和fixtures/hk_pool_factory.py
- V5/contracts/hk_preselection_source_manifest.json与完整34件vendor/hk_preselection_baseline闭包
- 原materialize_hk_0_2.py、shared_data.hk_0_2及10件原shared_data直接依赖，原scheduled materializer与两个原HK日期/市场隔离测试
- V5/docs/HK_PRESELECTION.md及M06_EXISTING_POOL_EVIDENCE.md原报告、TASK_DOCUMENTS四份新任务书

## 原生产与现有reader
run_hk_preselection是既有池严格读取/投影，明确model_weights_reverified=false；原materialize_frozen_hk_0_2才读取panel/实际models.joblib、原模型/排序、生成并发布Top100。新hk_preselection_daily在f7cb不存在；Chat应薄封装原生成owner，不重训/改权重/阈值或用旧100行假装新日生成。

目标日、HK证券信号日、资格来源日分别绑定；主表/pool/receipt实际时间<=cutoff。完整100行、代码顺序、score文本/数值、原拒绝码保留。无fallback旧日池、无私自补行。现有guard kind/paths修复已在包内，不重做。

## 历史证据与本轮边界
当前hk_preselection.py SHA256=00ccdaa1890675335836351d33c4fea5f9458a8dd287e3724efb9f0cb0fb1b21，与164c报告修复字节相同；仍只引用当时15/15及100行既有输入回放，不冒称本轮实跑/新池/自然通过。独审又15/15不能加成30项。原HK_PRESELECTION.md旧10 ERROR等记录为历史，由较新报告精确覆盖对应问题。

原source/model assets、models.joblib、真实panel/资格/主表三文件不在源码包内；嘻嘻Mac验收时核实际字节和取得时点。固定模型SHA字段不是实际读取权重证据。原scheduled materializer/老日期测试涉及更广runtime，本包没有整套调度/阶段业务闭包，不声称全部旧测试可独立执行。V5当前34件reader胶囊完整，不等于新producer环境已验证。

## 写入边界
Chat只修改M06模块自身/新增daily及定向测试。a_preselection共享guard、M02来源、M08阶段、原vendor、UI/gateway/调度/contract注册只读，改动提INTEGRATION_REQUEST。嘻嘻Mac落地独验；缺active前像不阻挡静态候选。保留V4/8910，不交易、不扩权限或凭据。

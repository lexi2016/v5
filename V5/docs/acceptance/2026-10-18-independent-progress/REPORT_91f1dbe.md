> 历史定向测试记录，范围为当时测试；后续全量结果以 TEST_RESULTS.md 为准。

# 91f1dbe 定向复核

固定HEAD：91f1dbe18e9da1d6abbdb974c600c8196a9b796e。
相对de1a525仅2测试文件：savedManagerNavigation.node.mjs更新reload函数签名抽取；ACloseReplay.spec.ts将M09合成投影改为beforeAll生成一次、单例structuredClone，加入30秒子进程限制。没有产品运行源码变化。

- npm run test:p0：164/164 PASS，0 FAIL，exit0。
- PYTHON=<已安装Python3.14.8隔离环境> npm test -- src/components/ACloseReplay.spec.ts：4/4 PASS，exit0。
- 独立detached worktree，复用依赖，tracked源码无本地修改。
- 样本来源：V5/tests/export_m09_readonly_fixture.py明确标注SYNTHETIC；使用临时目录create_fixture，再调用原v5_shadow.m09_readonly.read_record产生投影。未绑定私人V5_M09_RESPONSE_FILE，没有发布此投影，也没有替代currentRecovery缺失真实回执。
- 已消除de1a525的两个p0 harness失败。之前日期竞争五类验证属于de1a525历史结果；本轮未重复。
- 本轮typecheck、全前端、全Python、build、HTTP、浏览器、真实采集均NOT_RUN。真实currentRecovery证据缺口仍未解决，不能将M09合成测试通过计为真实业务验收。

日志：logs-91f1dbe/p0.log、aclose-replay.log及各.exit、verified-head.txt、tracked-source-diff.txt。
未修改产品、push、上传、外发或重试被阻塞浏览器。

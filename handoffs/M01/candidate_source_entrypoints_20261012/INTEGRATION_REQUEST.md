# M01 接线说明

本轮无共享文件修改请求。既有统一整合者在核准活动前像后采用 M01 完整 after 文件；默认入口依赖原 infrastructure.owned_io、infrastructure.formula_generation 和同包 composition，不外传安全实现，不修改其内容。

创建仅接收 private_root/source_root/generation_pointer/target_date；读取仅接收 private_root/source_root/relative。失败沿原异常准确传播，已有输出不覆盖。消费者依旧使用完整来源 identity 与 r15 schema，cutoff 未验证。

V5 前缀是 donor 命名空间，不是部署根声明。M05/M09、UI/API 和调度接线由唯一整合者核现场后实施；没有本候选提供的共享覆盖补丁。完整业务验收不得用本合成 fixture 或历史 R6 结果代替。

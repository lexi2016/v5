# 独立V5只读包工程交付

基线 b52334941e712dc642f78eae8970349332969aac（d53e08产品+验收文档），开发分支 dev/v5-standalone-packaging-20261012。未更新 main、集成分支、54780 或 V4。

## 结果

- 678项源码/资源哈希清单；tar含自身manifest共679文件。
- 两次确定性tar SHA256均为 c6f16533ce4b486639a6526cb8c4f10b408d7eaf047ee943027cb3868ac84d56。
- 原前端19文件/835248字节，rebound独立owner38文件/449131字节，US owner48文件/385577字节逐字节校验。
- 单入口 V5/run_standalone.py，使用原 main_runtime/module_process/module_api/api_gateway。没有新web框架、数据库、容器、线程/进程池或依赖安装。
- main_runtime仅修必要边界：隔离子进程bootstrap、10秒有界READY读取、符号链接/硬链接拒绝、start/stop同锁、失败回收与半写回滚、保存Popen handle并wait、消除无人读取stderr管道。

## 实际验证

云Python3.12.14：

- 新standalone测试16/16通过，包含解包后全新根三路真实HTTP synthetic saved fixture、原值一致、错误参数/POST/外站Origin拒绝、调用cwd注入拒绝、根外路径/链接拒绝、GET零写、并发/超时/失败恢复及SIGHUP关闭。
- 既有M18 unittest发现66项，65通过，1个原opt-in测试跳过：test_actual_rss_and_wall_failure_reap。独立的resource_stress和90秒receipt gate实际通过；不能把跳过项称已执行。
- 既有managed_module_process的4个pytest-style函数直接调用通过；这不是pytest全套。
- 尝试 python3 -m pytest，实际阻塞为No module named pytest；未安装新依赖。
- US原loader --check-only通过；rebound冻结包独立namespace导入通过。未执行owner、采集、策略或daily。
- 独立代码复核关闭具体问题后重验：200个RST断连后3次health 200；start/stop交错、partial identity rollback、重复start保留handle、SIGTERM/SIGHUP关闭均实测。

记录分别见同目录日志及verification.json。产品主体M18未改算法；M18回归日志与最后main_runtime修补无依赖，最后16项standalone测试已覆盖修补后真实隔离子进程HTTP。

## Mac独验（由既有测试会话协调）

不要替换当前checkout/54780，不停止V4，不重新构建前端，不安装依赖。不要求原V4源码目录可读。

1. checkout本开发分支最终固定SHA到新V5专属目录。
2. 用已有V5 Python运行：
   - python -I -B V5/run_standalone.py verify
   - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=V5/src:V5/tests python -B -m unittest discover -s V5/tests -p 'test_standalone*py' -v
   - python -I -B V5/tools/build_standalone.py --output /NEW/PRIVATE/v5-standalone.tar
3. 核对tar SHA256；测试自身使用新临时根/空闲loopback端口并退出，不接现役预览。
4. 如随后获准以现有真实已发布数据验证，只把完整不可变bundle及module publication复制到新独立V5数据根，保持对象原字节/身份/hash。按V5/STANDALONE.md配置与启动；前端/api兼容URL均由本包同源提供。不要自动从V4位置查找数据。

Mac未在本交付执行。完整daily实际生产尚需原锁环境、真实输入/provider/日期资格证据和既有调度验收；本入口不安装或启用daily。18模块完整验收不因本包装改状态。SIGKILL/断电遗留身份按文档fail-closed，需核实本次进程，不承诺自动恢复。

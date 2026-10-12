# V5 独立只读运行包

## 本次交付范围

本包是完整 GitHub 源码树中的一种可重复部署布局：`V5/src`、`vendor`、`contracts`、`producers`、固定前端构建及单一启动入口一起交付。运行时不读取其他 V4 checkout，不连接 V4 现役服务；`/api/v4/...` 仅保留原兼容 URL，`vendor/.../v4` 是包内原源码目录。

这是已有三路 saved-result 只读预览的工程包装，不等于 daily 生产启用或原 18 模块全部验收。无真实数据、账户、凭据、订单或自动采集随包交付。没有安装依赖、修改安全设置或现役 54780/V4。

固定输入：

- 集成基线：`lexi2016/v5@b52334941e712dc642f78eae8970349332969aac`，产品代码 d53e0820318462806d9e67dae1818bb684b38ade。
- 原已构建前端：`lexi2016/v5@e8c753b6109a8c26e8cf8c7cb843c789479260a0:static/d53e08`，19 资源、835248 字节，原 manifest 原样保留在 `frontend/manifest.json`；不重新构建。
- Rebound daily：`lexi2016/v4@2d8e38ec61792b3e75581f96318e9c284f72b7ba` 的 38 文件/449131 字节放入 `vendor/rebound_daily_owner`。保持原嵌套 `V5/...` 与子进程 namespace 隔离；没有将旧算法覆盖现集成算法。逐文件来源在 `contracts/bundled_rebound_owner.json`。
- US collector：`lexi2016/v4@164c010c7eaa1659db9bfed0ff5f123c7a39eefc` 的 48 文件/385577 字节放入 `vendor/us_collector_owner`，沿用原 `contracts/cloud_us_collector_sources.json`。

原 owner 文件均逐字节复制、Git blob 与 SHA256 核验。只修改两个外围定位入口；rebound 原外部 Git HEAD 检查换成固定 descriptor+严格文件集合校验，执行前后校验及 `-I -B` 子进程不变。准备新的 rebound daily 请求时省略 `owner_checkout`；旧外部路径明确拒绝，不静默选取外部目录。US collector 默认包内闭包，保留其原显式 override 接口作为兼容工具，不被此只读启动入口调用。

## 最小使用方式

使用已经存在的 V5 Python 环境；本包不自动下载或安装 Python/依赖。只读入口使用 Python 标准库；此提交云端实际测试 Python 3.12.14。原 daily 的 Python >=3.14 及 `uv.lock` 精确版本要求仍然保留，不能用只读测试替代。

在本提交 checkout 中，或构建产物解包后，从任何工作目录运行：

```sh
/EXISTING/V5/PYTHON -I -B /INSTALL/V5/run_standalone.py verify
/EXISTING/V5/PYTHON -I -B /INSTALL/V5/run_standalone.py init --root /NEW/PRIVATE/V5_DATA
```

`init` 仅创建新 V5 根、标记及 `config/data/runtime/logs` 空目录；拒绝已有根、源码重叠和符号链接。它不会制造真实结果或写入可运行的假配置。

把已经授权的、完整已发布 module root 与原 immutable M18 bundle 放在新根的 `data/` 内，保持其中 manifest、objects、generation、marker 和 hashes 不变。填写 `config/standalone.json`，格式见 `examples/standalone_config.example.json`。示例含明显占位符，不能直接运行；请使用真实已发布配置的 identity/hash。只改 data_root、bundle_root 为新根内路径，不重建业务数据。

```sh
/EXISTING/V5/PYTHON -I -B /INSTALL/V5/run_standalone.py validate --root /NEW/PRIVATE/V5_DATA
/EXISTING/V5/PYTHON -I -B /INSTALL/V5/run_standalone.py serve --root /NEW/PRIVATE/V5_DATA
```

`serve` 是唯一前台启动命令：复用 `main_runtime` 启动原 module_process，再用现有 api_gateway 同源提供原静态前端与 GET-only API。输出 `READY_READ_ONLY`、实际空闲 loopback 端口和 `/manager-selection/` URL；端口默认示例为 0，系统分配，不占用现役端口。无 Node、Vite、`V5_MODULE_API_ORIGIN`、外部 owner checkout 或 V4 服务要求。

Ctrl-C / SIGTERM / SIGHUP 退出时关闭本次 gateway，并调用原 runtime.stop 停本次 module 子进程。启动失败会回收本次新子进程并清除此尝试的半写身份文件；并发启动有排他锁，子进程用隔离bootstrap拒绝调用目录注入。子进程stderr不保留阻塞管道，失败由入口错误状态报告。它不安装 launchd，不触碰其他进程或调度。若此前异常断电/SIGKILL 留下 `runtime/runtime.json`，会拒绝重复启动；先核对本次记录进程，不自动删除旧身份或杀未知 PID。

根内配置支持四条原 M18 路由：descriptor、pages、overview、sections；三路公告/超跌/美股映射都从同一已保存 bundle 读取。Host/Origin、只读、分页、身份/哈希校验沿用原实现。路径逃逸或符号链接先拒绝；配置不接受外部服务端口/URL、调度开关或写接口。

## 可重复构建

```sh
/EXISTING/V5/PYTHON -I -B V5/tools/build_standalone.py --output /NEW/OUTPUT/v5-standalone.tar
```

先核 `contracts/standalone_sources.json` 的完整资源清单，再按排序、固定时间戳/uid/gid/mode 构建标准 tar。相同提交两次构建 SHA256 相同。不包含 `.git`、`.venv`、node_modules、用户数据、缓存或机器路径。资源改动必须同步重新生成并审查 manifest 后提交，否则拒绝构建/启动。完整源码、构建脚本、原 manifest 和测试都在本 GitHub 分支；tar 是产物，不替代源码交付。

本次支持 source-layout 应用包，不把现有仅收 `src` 的 setuptools wheel 或裸 `pip install V5` 当作独立部署方式。`pyproject.toml` / `uv.lock` 作为原依赖约束随包保留；运行路径布局保持原模块的 `BASE/vendor/contracts` 资源查找语义。

## 实际测试与尚未证明

详细输出在本分支 handoffs/P0/standalone-packaging-20261012。

- 新入口、根约束、包内 owner 校验、确定性构建测试
- 解包后的全新安装目录 + 全新数据根、无外部源码 PYTHONPATH，真实启动原 module API/gateway
- 既有 synthetic fixture 构造的 immutable bundle，三路真实 HTTP 读取原值；错误身份、POST、外站 Origin 拒绝
- GET 前后完整安装目录/数据根字节及 mtime 不变，外部哨兵不变；退出清理本次 runtime identity
- US 48 文件实际原 loader 导入通过，network_checked=false、capture_executed=false；rebound 原包独立 namespace 导入通过，owner_executed=false

以上为合成工程验证。没有运行真实采集、rebound 计算、原锁环境 daily 或全 18 模块全套业务验收。daily 源码闭包已带齐，但真实请求/输入/provider 准入、日期/单位/资格证据、活动配置、原锁依赖、调度及生产验收仍须分别验证。只读入口不提供 daily 启动开关。真实 Mac 解包独验由既有测试会话执行，不替换当前预览。

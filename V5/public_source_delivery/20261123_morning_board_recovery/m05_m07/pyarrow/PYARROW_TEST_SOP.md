# 云电脑 M05 六路离线验收依赖

只对项目专用 venv 安装 PyArrow 22.0.0，不改系统 Python 或生产环境。当前 Linux x86-64 / CPython 3.12.14；venv 使用现有只读 NumPy 2.3.5、pandas 2.2.3。依赖包从 PyPI 官方索引下载，按 requirements-pyarrow.lock 锁定的 SHA 对照发布页，禁止降级为 CSV 或跳过 V192。
1. 使用 `python -m venv --system-site-packages venv`。用 venv 的 pip 从 `https://pypi.org/simple` 通过 `download --no-deps --only-binary=:all: --require-hashes -r requirements-pyarrow.lock -d wheels` 取包。
2. 在 venv 内用 `pip install --no-index --find-links wheels --no-deps --require-hashes -r requirements-pyarrow.lock` 安装；核 `pyarrow.__file__` 在 venv 内，并用磁盘 Parquet 小样本写回读。
3. 在固定 M05 V5 原码根下，设置 `PYTHONNOUSERSITE=1 PYTHONPATH="$PWD/src:$PWD/tests"`，使用 venv 解释器 `-B -m unittest discover -s tests -p 'test*.py' -v`。同时单核六路 writer 测试和 V192 原生 Parquet。测试失败保留错误，不重写原固件或改保护门。
4. 六路 writer 测试证明写入和读回，不等于 M07 业务准入。原 M07 仍需按既有阶段门验证来源身份、表头日期和同日行情；不将离线结果计入自然节点或直接部署。
5. 备份只收锁文件、SOP 和结果摘要；不上传第三方 wheel、venv、测试临时目录或原数据。重建按官方来源和哈希复现。

源：[PyPI 22.0.0](https://pypi.org/project/pyarrow/22.0.0/#pyarrow-22.0.0-cp312-cp312-manylinux_2_28_x86_64.whl)。

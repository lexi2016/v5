# M16 Mac ac1d14 隔离验收

主控Mac原回执转存；转存者未执行测试。固定候选ac1d1404ee76ca18a55dc65451b34868de6db552，155 blob/154 manifest核验。result.json保留原7,534字节，SHA-256 a25b81bb9c3167745ce25676df0b83970d60dbe74f7761ecbe6d34984a7d77b8。

31/31合成隔离测试PASS，exit 0。首次1 PASS/30 setup ERROR因macOS默认TMPDIR经过/var symlink，原owned_io的O_NOFOLLOW拒绝；改为真实非symlink TMPDIR后通过，未改产品，候选字节不变。首轮失败保留，不算30项业务断言失败或忽略错误。

原loader32未重跑。Python3.14.6与README云端3.12.14不同；fastapi/httpx/uvicorn版本相符，私有pypdf由原解析测试核manifest/license。完整锁环境、真实PDF/provider网络、部署/原生页面/自然均NOT_RUN；不计全模块验收完成，未安装依赖或触发新外采。

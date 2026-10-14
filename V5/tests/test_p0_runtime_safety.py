"""Bounded synthetic regressions for source launch and process ownership."""
import hashlib
import json
import os
from pathlib import Path
import py_compile
import shutil
import signal
import select
import subprocess
import sys
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor

import pytest
from v5_shadow import main_runtime
from v5_shadow.digests import canonical_bytes, sha256_json

BASE = Path(__file__).resolve().parents[1]


def config(root):
    data = root / "data"
    data.mkdir()
    (data / ".v5-module-root").write_text("v5.module-root.v1:p0_test\n")
    return dict(runtime_root=str(root / "runtime"), composition="SYNTHETIC",
                module_api=dict(schema_version="v5.module_api.v1", module_id="p0_test",
                                release_id="SYNTHETIC_SAFETY", data_root=str(data), routes=[]))


def test_invalid_module_config_rejected_before_runtime_writes(tmp_path):
    value = config(tmp_path)
    value["module_api"] = {"host": "127.0.0.1", "mode": "READ_ONLY"}
    with pytest.raises(ValueError, match="CONTRACT_FIELDS_INVALID"):
        main_runtime.validate_config(value)
    with pytest.raises(ValueError, match="CONTRACT_FIELDS_INVALID"):
        main_runtime.start(value)
    assert not (tmp_path / "runtime").exists()


@pytest.mark.skipif(not Path('/proc/self/fd').exists(), reason='Linux descriptor observation')
def test_repeated_validate_closes_readonly_root_descriptor(tmp_path):
    value = config(tmp_path)
    before = len(list(Path('/proc/self/fd').iterdir()))
    for _ in range(20):
        assert main_runtime.validate_config(value)['status'] == 'CONFIGURATION_VALID'
    assert len(list(Path('/proc/self/fd').iterdir())) == before


def test_concurrent_starts_keep_one_owned_child(tmp_path):
    value = config(tmp_path)
    def launch():
        try:return main_runtime.start(value)
        except ValueError as exc:return str(exc)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _: launch(),range(2)))
    try:
        started=[r for r in results if isinstance(r,dict)]
        assert len(started)==1,results
        assert next(r for r in results if isinstance(r,str)) in ('RUNTIME_BUSY','RUNTIME_ALREADY_EXISTS')
        assert main_runtime.status(value)['identity']['module_pid']==started[0]['identity']['module_pid']
    finally:
        main_runtime.stop(value)


def test_stop_preserves_unrelated_process_and_stale_identity(tmp_path):
    value = config(tmp_path)
    root = Path(value["runtime_root"])
    root.mkdir()
    sleeper = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"])
    identity = root / "runtime.json"
    raw = canonical_bytes(dict(marker=main_runtime.MARKER, module_pid=sleeper.pid,
                               port=1, config_sha256=sha256_json(value)))
    identity.write_bytes(raw)
    try:
        assert main_runtime.status(value)["status"] == "STALE"
        with pytest.raises(ValueError, match="RUNTIME_PROCESS_IDENTITY_UNVERIFIED"):
            main_runtime.stop(value)
        assert sleeper.poll() is None
        assert identity.read_bytes() == raw
    finally:
        sleeper.terminate()
        sleeper.wait(timeout=5)


@pytest.mark.skipif(not hasattr(os, 'pidfd_open'), reason='Linux pidfd exit identity')
def test_stop_reaps_exited_child_and_releases_stale_runtime(tmp_path):
    value = config(tmp_path)
    root = Path(value['runtime_root'])
    root.mkdir()
    child = subprocess.Popen([sys.executable, '-c', 'pass'])
    fd = os.pidfd_open(child.pid)
    try:
        assert select.select([fd], [], [], 3)[0]
        (root/'runtime.json').write_bytes(canonical_bytes(dict(
            marker=main_runtime.MARKER, module_pid=child.pid, port=1,
            config_sha256=sha256_json(value))))
        assert main_runtime.stop(value)['status'] == 'STOPPED'
        assert not (root/'runtime.json').exists()
    finally:
        os.close(fd)
        child.wait(timeout=3)


def test_managed_child_ignores_valid_timestamp_bytecode(tmp_path):
    source = tmp_path / "V5"
    source.mkdir()
    shutil.copytree(BASE / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(BASE / "run_shadow.py", source / "run_shadow.py")
    module = source / "src/v5_shadow/module_api.py"
    original = module.read_bytes()
    info = module.stat()
    module.write_bytes(original.replace(b"READ_ONLY_RESPONSE_SERVICE", b"STALE_PYC_RESPONSE_SERVICE"))
    os.utime(module, ns=(info.st_atime_ns, info.st_mtime_ns))
    cache = Path(py_compile.compile(str(module), doraise=True))
    cache_before = cache.read_bytes()
    module.write_bytes(original)
    os.utime(module, ns=(info.st_atime_ns, info.st_mtime_ns))
    value = config(tmp_path)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(value))

    def run(action):
        result = subprocess.run([sys.executable, "-I", "-B", str(source / "run_shadow.py"),
                                 "runtime", action, "--config", str(cfg)],
                                cwd=tmp_path, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    started = run("start")
    try:
        with urlopen(f"http://127.0.0.1:{started['identity']['port']}/__v5/module-health", timeout=3) as response:
            health = json.load(response)
        assert health["status"] == "READ_ONLY_RESPONSE_SERVICE"
        assert health["implementation_sha256"] == hashlib.sha256(original).hexdigest()
        assert cache.read_bytes() == cache_before
    finally:
        run("stop")


def test_silent_child_start_is_bounded_and_reaped(tmp_path):
    value = config(tmp_path)
    # Inject a task-owned silent process at the OS boundary, not a fake READY.
    code = """import json,subprocess,sys
sys.path.insert(0,sys.argv[1])
from v5_shadow import main_runtime as m
real=m.subprocess.Popen; children=[]
def silent(*args,**kwargs):
 p=real([sys.executable,'-c','import time;time.sleep(30)'],**kwargs)
 children.append(p);return p
m.subprocess.Popen=silent;m.START_TIMEOUT=.15
try:m.start(json.loads(sys.argv[2]))
except ValueError as e:
 assert str(e)=='MODULE_API_START_FAILED',str(e)
 assert children[0].poll() is not None
 print('BOUNDED_AND_REAPED')
else:raise AssertionError('silent child accepted')
"""
    proc = subprocess.Popen([sys.executable, "-I", "-B", "-c", code, str(BASE / "src"), json.dumps(value)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=3)
        assert proc.returncode == 0, out + err
        assert "BOUNDED_AND_REAPED" in out
        assert not (tmp_path / "runtime/runtime.json").exists()
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate(timeout=3)

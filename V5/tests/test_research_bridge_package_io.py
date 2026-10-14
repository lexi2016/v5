"""Malformed local package files must fail before invoking an M04 reader."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

BASE = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("kind", ["fifo", "symlink", "oversize"])
def test_manifest_type_and_size_fail_before_blocking_or_launch(tmp_path, kind):
    package = tmp_path / "package"
    package.mkdir()
    manifest = package / "RELEASE.json"
    if kind == "fifo":
        os.mkfifo(manifest)
    elif kind == "symlink":
        target = tmp_path / "outside.json"
        target.write_text("{}")
        manifest.symlink_to(target)
    else:
        with manifest.open("wb") as stream:
            stream.truncate(4 * 1024 * 1024 + 1)
    config = dict(module_id="source_bundle", routes=["/api/v5/research/lane"],
                  m04_research_lane_binding=dict(package_root=str(package),
                       package_manifest_sha256="0" * 64, archive_binding={"root": str(tmp_path), "files": {}},
                       python_executable=str(Path(sys.executable).resolve())))
    code = """import sys,json
sys.path.insert(0,sys.argv[1])
from v5_shadow.research_workbench_readonly import _lane
try:_lane(json.loads(sys.argv[2]),{})
except ValueError as e:
 assert str(e) in ('RESEARCH_PACKAGE_FILE_TYPE','RESEARCH_PATH'),str(e)
 print('REJECTED_BEFORE_LAUNCH')
else:raise AssertionError('invalid package accepted')
"""
    result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(BASE / "src"), json.dumps(config)],
                            capture_output=True, text=True, timeout=2)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "REJECTED_BEFORE_LAUNCH" in result.stdout

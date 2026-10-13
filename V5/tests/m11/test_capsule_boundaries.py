import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import pytest
from v5_shadow.m11.intraday_capsule import IntradayCapsuleStore, M11Slot


def slot():
    return M11Slot('2026-10-12', '09:25', '09:33', 'manual', 'run-1')


def test_child_symlink_cannot_write_outside(tmp_path):
    root = tmp_path / 'private'; root.mkdir()
    outside = tmp_path / 'outside'; outside.mkdir()
    (root / '2026-10-12').symlink_to(outside, target_is_directory=True)
    with pytest.raises((ValueError, OSError)):
        IntradayCapsuleStore(root).write_success(slot(), {'v': 1}, 'source')
    assert list(outside.iterdir()) == []


def test_read_rejects_payload_symlink(tmp_path):
    store = IntradayCapsuleStore(tmp_path / 'private')
    store.write_success(slot(), {'v': 1}, 'source')
    # Every committed byte must be read with no-follow, including the final file.
    target = store._artifact_dir(slot())
    final = target / 'commit.json'
    assert final.exists(), 'a single atomic commit envelope is required'
    outside = tmp_path / 'copy.json'; outside.write_bytes(final.read_bytes())
    final.unlink(); final.symlink_to(outside)
    with pytest.raises((ValueError, OSError)):
        store.read_verified(slot())


def test_uncommitted_payload_is_never_read(tmp_path):
    store = IntradayCapsuleStore(tmp_path)
    target = store._artifact_dir(slot()); target.mkdir(parents=True)
    (target / 'payload.json').write_text('{"v": 1}')
    (target / 'manifest.json').write_text(json.dumps({'identity':slot().identity(), 'payload_sha':__import__('hashlib').sha256(json.dumps({'v':1},sort_keys=True).encode()).hexdigest()}))
    with pytest.raises((ValueError, OSError)):
        store.read_verified(slot())
    # A crash before the one commit file must not permanently poison this identity.
    store.write_success(slot(), {'v': 2}, 'source')
    assert store.read_verified(slot()) == {'v': 2}


def test_independent_worker_read_and_receipt_tamper(tmp_path):
    store = IntradayCapsuleStore(tmp_path)
    store.write_success(slot(), {'v':1}, 'source')
    code = 'import json,sys; from v5_shadow.m11.intraday_capsule import *; print(json.dumps(IntradayCapsuleStore(sys.argv[1]).read_verified(M11Slot(**json.loads(sys.argv[2])))))'
    result = subprocess.run([sys.executable,'-B','-c',code,str(tmp_path),json.dumps(slot().__dict__)],capture_output=True,text=True,check=True)
    assert json.loads(result.stdout) == {'v':1}
    final = store._artifact_dir(slot()) / 'commit.json'
    envelope = json.loads(final.read_text()); envelope['receipt']['manifest_sha256'] = '0' * 64
    final.write_text(json.dumps(envelope))
    with pytest.raises(ValueError):store.read_verified(slot())


def test_attempt_history_is_retained(tmp_path):
    store = IntradayCapsuleStore(tmp_path)
    store.write_attempt(slot(), 'REQUEST_IN_FLIGHT')
    store.write_attempt(slot(), 'ATTEMPT_UNKNOWN')
    assert len(list((tmp_path/'2026-10-12'/'attempts'/'0925'/'events').glob('*.json'))) == 2


def _publish_in_process(root):
    try:
        IntradayCapsuleStore(Path(root)).write_success(slot(),{'value':1},'source')
        return 'published'
    except FileExistsError:return 'exists'


def test_process_race_has_exactly_one_commit(tmp_path):
    with ProcessPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(_publish_in_process,[str(tmp_path)]*3))
    assert results.count('published')==1
    assert results.count('exists')==2
    assert IntradayCapsuleStore(tmp_path).read_verified(slot())=={'value':1}


def test_changed_config_is_new_identity():
    a=M11Slot('2026-10-12','09:25','09:33','manual','run-1',config_sha='a')
    b=M11Slot('2026-10-12','09:25','09:33','manual','run-1',config_sha='b')
    assert a.identity()!=b.identity()

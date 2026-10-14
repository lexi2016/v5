"""Resource-check fixtures are synthetic; no owners or provider calls."""
import hashlib
import json
from pathlib import Path

import pytest


def fixture(tmp_path):
    from v5_shadow.source_release import RUNTIME_MANIFESTS
    (tmp_path/'contracts').mkdir()
    (tmp_path/'source_owners').mkdir()
    source=tmp_path/'source_owners/synthetic.py'
    source.write_bytes(b'# SYNTHETIC source, never imported\n')
    entry=dict(path='source_owners/synthetic.py',sha256=hashlib.sha256(source.read_bytes()).hexdigest(),bytes=source.stat().st_size)
    for name in RUNTIME_MANIFESTS:
        (tmp_path/'contracts'/name).write_text(json.dumps({'entries':[entry]}))
    return source


def test_resource_check_keeps_scope_and_does_not_execute_source(tmp_path):
    from v5_shadow.source_release import check_resources
    fixture(tmp_path)
    result=check_resources(tmp_path)
    assert result['status']=='MATCH'
    assert result['entry_references']==10
    assert result['unique_files']==1
    assert result['complete_release_verified'] is False
    assert result['owner_execution']=='NOT_RUN'
    assert not list(tmp_path.rglob('__pycache__'))


def test_identical_repeated_source_references_are_counted_not_rewritten(tmp_path):
    from v5_shadow.source_release import check_resources, RUNTIME_MANIFESTS
    fixture(tmp_path)
    manifest=tmp_path/'contracts'/RUNTIME_MANIFESTS[0]
    value=json.loads(manifest.read_text())
    value['entries']*=3
    manifest.write_text(json.dumps(value))
    result=check_resources(tmp_path)
    assert result['status']=='MATCH'
    assert result['entry_references']==12
    assert result['unique_files']==1


@pytest.mark.parametrize('fault', ['missing','tamper','symlink','unsafe-manifest-path'])
def test_resource_check_rejects_incomplete_or_unsafe_package(tmp_path,fault):
    from v5_shadow.source_release import check_resources, RUNTIME_MANIFESTS
    source=fixture(tmp_path)
    if fault=='missing':source.unlink()
    elif fault=='tamper':source.write_text('changed')
    elif fault=='symlink':
        outside=tmp_path/'outside.py';outside.write_bytes(source.read_bytes())
        source.unlink();source.symlink_to(outside)
    else:
        p=tmp_path/'contracts'/RUNTIME_MANIFESTS[0]
        value=json.loads(p.read_text());value['entries'][0]['path']='../outside.py';p.write_text(json.dumps(value))
    result=check_resources(tmp_path)
    assert result['status']=='MISMATCH'
    assert result['errors']

from pathlib import Path
import pytest
from v5_shadow.m11.storage_guard import assert_safe_root,atomic_absent_publish


def test_root_ancestor_symlink_rejected(tmp_path):
    real=tmp_path/'real';real.mkdir()
    link=tmp_path/'link';link.symlink_to(real,target_is_directory=True)
    with pytest.raises((ValueError,OSError)):assert_safe_root(link/'child')


def test_atomic_publish_uses_no_follow_source(tmp_path):
    other=tmp_path/'other';other.write_text('outside')
    root=tmp_path/'root';root.mkdir();temp=root/'temp';temp.symlink_to(other)
    with pytest.raises((ValueError,OSError)):atomic_absent_publish(temp,root/'final',root)
    assert not (root/'final').exists()

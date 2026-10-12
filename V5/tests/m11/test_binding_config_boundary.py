"""Config is an immutable input: it must never live in the archive output tree."""
import hashlib
import pytest
from test_default_owner_chain import binding
from v5_shadow.m11.daily import M11Binding


@pytest.mark.parametrize('placement',['equal','direct_child','nested_child'])
def test_configuration_cannot_overlap_archive_output(tmp_path,placement):
    b=binding(tmp_path)
    path=b.archive_root if placement=='equal' else b.archive_root/('config.json' if placement=='direct_child' else 'executions/config.json')
    if placement!='equal':
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b.config_path.read_bytes())
    invalid=M11Binding(b.state_root,b.archive_root,path,b.config_sha256,b.owner_manifest_sha256)
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    with pytest.raises(ValueError,match='M11_CONFIG_OUTPUT_OVERLAP'):
        invalid.validate()
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def test_separate_configuration_is_accepted_without_writes(tmp_path):
    b=binding(tmp_path)
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    cfg=b.validate()
    assert cfg['state_root']==str(b.state_root)
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}

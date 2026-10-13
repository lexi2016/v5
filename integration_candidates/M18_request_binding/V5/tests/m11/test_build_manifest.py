"""New V5 build identity, not a recovered historical F or r4 manifest."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from v5_shadow.m11.owner_sources import OWNER_ROOT,V5


def test_new_v5_manifest_real_original_validator():
    path=OWNER_ROOT/'domains/research_review_generation/OWNED_SOURCE_MANIFEST.json'
    assert path.exists(), 'explicit V5 build manifest must be packaged'
    raw=path.read_bytes();doc=json.loads(raw)
    assert doc['schema']=='v5.m11.build_source_manifest.v1'
    assert doc['build_origin']['commit']=='f7cb731c384ee6890a87d16c19a5b5a621779477'
    assert len(doc['files'])==40 and 'iwencai_binding.py' in doc['files']
    from v5_shadow.m11.owner_sources import BUILD_MANIFEST_SHA
    assert hashlib.sha256(raw).hexdigest()==BUILD_MANIFEST_SHA
    code='import sys;sys.path.insert(0,sys.argv[1]);from domains.research_review_generation.owned_runtime import verify_owned_sources;print(verify_owned_sources(sys.argv[2])["status"])'
    p=subprocess.run([sys.executable,'-I','-B','-c',code,str(OWNER_ROOT),BUILD_MANIFEST_SHA],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    assert p.stdout.strip()=='HASH_BOUND'


@pytest.mark.parametrize('damage',['tamper','missing','extra','wrong_pin'])
def test_original_validator_rejects_modified_build_closure(tmp_path,damage):
    from v5_shadow.m11.owner_sources import BUILD_MANIFEST_SHA
    root=tmp_path/'owner';shutil.copytree(OWNER_ROOT,root)
    p=root/'domains/research_review_generation/assembly.py'
    if damage=='tamper':p.write_bytes(p.read_bytes()+b'\n# changed\n')
    if damage=='missing':p.rename(root/'removed-assembly.fixture')
    if damage=='extra':(p.parent/'extra.py').write_text('pass\n')
    pin='0'*64 if damage=='wrong_pin' else BUILD_MANIFEST_SHA
    code='import sys;sys.path.insert(0,sys.argv[1]);from domains.research_review_generation.owned_runtime import verify_owned_sources;verify_owned_sources(sys.argv[2])'
    result=subprocess.run([sys.executable,'-I','-B','-c',code,str(root),pin],capture_output=True,text=True)
    assert result.returncode!=0


def test_original_default_assembly_accepts_build_pin_without_opening_credentials(tmp_path):
    from v5_shadow.m11.owner_sources import BUILD_MANIFEST_SHA
    root=tmp_path/'state';root.mkdir()
    profile=OWNER_ROOT/'contracts/vibe_runtime_profile.json'
    cfg={'schema':'v4.vibe_assembly.v1','state_root':str(root),'cache_root':str(root/'cache'),
         'cache_manifest_path':str(root/'inventory.json'),'cache_manifest_sha256':'1'*64,
         'profile_path':str(profile),'profile_sha256':hashlib.sha256(profile.read_bytes()).hexdigest(),
         'credential_db':str(tmp_path/'synthetic-not-opened.db'),'data_mode':'snapshot',
         'data_as_of':'2026-10-12T15:00:00+08:00','snapshot_sha256':'2'*64}
    raw=json.dumps(cfg).encode();path=tmp_path/'config.json';path.write_bytes(raw)
    code='import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from domains.research_review_generation.assembly import assemble_runtime;r=assemble_runtime(config_path=Path(sys.argv[2]),config_sha256=sys.argv[3],implementation_manifest_sha256=sys.argv[4]);print(type(r).__name__)'
    p=subprocess.run([sys.executable,'-I','-B','-c',code,str(OWNER_ROOT),str(path),hashlib.sha256(raw).hexdigest(),BUILD_MANIFEST_SHA],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    assert p.stdout.strip()=='RuntimeAssembly'
    assert not (tmp_path/'synthetic-not-opened.db').exists()
    assert not list(root.iterdir())

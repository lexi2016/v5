"""Extract the exact provided runtime archive into a new isolated directory."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import stat
import zipfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--archive',required=True);p.add_argument('--out',required=True)
a=p.parse_args();archive,out=Path(a.archive),Path(a.out)
assert archive.is_absolute() and out.is_absolute() and '..' not in out.parts
assert not out.exists() and not any(x.is_symlink() for x in (out,*out.parents))
assert archive.stat().st_size==7577304
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='24eb6689e336c45e63d0bc071722ea0379c9b98a2961a60a54dd8807999f2f44'
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    seen=set()
    for info in z.infolist():
        path=PurePosixPath(info.filename)
        assert not path.is_absolute() and '..' not in path.parts and '\\' not in info.filename
        assert not stat.S_ISLNK(info.external_attr>>16) and info.filename not in seen
        seen.add(info.filename)
    out.mkdir(mode=0o700)
    z.extractall(out)
root=out/'M09_ORIGINAL_INPUTS_RUNTIME_BINDINGS_20261011'
manifest=json.loads((root/'MANIFEST.json').read_bytes());assert len(manifest['files'])==40
for row in manifest['files']:
    path=root/row['path'];assert path.stat().st_size==row['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'],row['path']
print(json.dumps({'status':'EXACT_40_RUNTIME_FILES_VERIFIED','runtime_input_root':str(root),'archive_unchanged':True}))

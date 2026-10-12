"""Reproducible source-layout application archive; no dependency installation."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
BASE = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE/'src'))
from v5_shadow.standalone import MANIFEST, verify_package
from v5_shadow.composition import no_symlinks


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args=parser.parse_args()
    verify_package()
    output=no_symlinks(args.output)
    if output.exists():raise ValueError('BUILD_FRESH_OUTPUT_REQUIRED')
    if output.is_relative_to(BASE):raise ValueError('BUILD_OUTPUT_SOURCE_OVERLAP')
    manifest=json.loads((BASE/MANIFEST).read_bytes())
    names=sorted([row['path'] for row in manifest['files']]+[MANIFEST])
    with output.open('xb') as stream, tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name in names:
            raw=(BASE/name).read_bytes()
            info=tarfile.TarInfo('V5/'+name)
            info.size=len(raw);info.mode=0o644;info.mtime=0;info.uid=info.gid=0
            info.uname=info.gname=''
            archive.addfile(info, io.BytesIO(raw))
    print(json.dumps(dict(status='BUILT_SOURCE_LAYOUT',output=str(output),files=len(names),
        sha256=hashlib.sha256(output.read_bytes()).hexdigest(),python_embedded=False,
        business_verified=False,daily_enabled=False)))

if __name__=='__main__':main()

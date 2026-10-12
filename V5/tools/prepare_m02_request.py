"""Print a source-identity-only request from explicit local inputs; never publish.

Use only in the isolated overlay, with existing private root/marker and original
membership/native binding JSON files. No model deserialization or owner changes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from v5_shadow import hk_source_daily as daily
from v5_shadow.composition import no_symlinks


def asset_binding(root):
    root=no_symlinks(root); io=daily._safe_root()(root); paths=set()
    for pointer,key in (('panel_latest.json','panel_relative'),('model_latest.json','bundle_relative'),('name_latest.json','dictionary_relative')):
        try:raw=daily._read(io,pointer)
        except FileNotFoundError:
            if pointer=='name_latest.json':continue
            raise
        paths.add(pointer);manifest=daily._json(raw)['manifest_relative']
        paths.add(manifest);paths.add(daily._json(daily._read(io,manifest))[key])
    files={}
    for relative in sorted(paths):
        with io.parent(relative) as (parent,name):
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
            try:
                meta=os.fstat(fd)
                if not stat.S_ISREG(meta.st_mode) or meta.st_size>daily.ASSET_MAX_FILE_BYTES:
                    raise ValueError('M02_ASSET_SIZE_OR_TYPE')
                digest=hashlib.sha256(); consumed=0
                while block:=os.read(fd,1024*1024):
                    consumed+=len(block)
                    if consumed>meta.st_size:raise ValueError('M02_ASSET_CHANGED')
                    digest.update(block)
                after=os.fstat(fd);keys=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')
                if consumed!=meta.st_size or any(getattr(meta,k)!=getattr(after,k) for k in keys):
                    raise ValueError('M02_ASSET_CHANGED')
                files[relative]=digest.hexdigest()
            finally:os.close(fd)
    binding=dict(root=str(root),files=files)
    daily._asset_snapshot(binding)
    return binding


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('asset-root','membership-binding','native-binding','private-root','target-date','signal-date','eligibility-source-date','cutoff'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args(argv)
    member=daily._json(Path(args.membership_binding).read_bytes())
    native=daily._json(Path(args.native_binding).read_bytes())
    request=dict(private_root=str(no_symlinks(args.private_root)),asset_binding=asset_binding(args.asset_root),
        membership_root=member['root'],membership_files=member['files'],native_binding=native,
        target_date=args.target_date,signal_date=args.signal_date,eligibility_source_date=args.eligibility_source_date,
        cutoff=args.cutoff,require_pit=False)
    print(json.dumps(request,sort_keys=True,ensure_ascii=False,indent=2))

if __name__=='__main__':main()

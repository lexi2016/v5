"""Maintainer-only hash inventory refresh; review and commit changes before use.

Does not retrieve sources, install dependencies, change vendor bytes or run owners.
"""
import hashlib
import json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
MANIFEST=BASE/'contracts/standalone_sources.json'
DIRECTORIES=['src','contracts','vendor','producers','frontend']
FILES=['run_standalone.py','run_shadow.py','pyproject.toml','uv.lock','STANDALONE.md',
       'examples/standalone_config.example.json','tools/build_standalone.py',
       'tools/refresh_standalone_manifest.py']

def main():
    paths=[p for name in DIRECTORIES for p in (BASE/name).rglob('*') if p.is_file() and p!=MANIFEST]
    paths += [BASE/name for name in FILES]
    if any(p.is_symlink() or '__pycache__' in p.parts or p.suffix=='.pyc' for p in paths):
        raise ValueError('SOURCE_SYMLINK_OR_CACHE_REJECTED')
    rows=[dict(path=str(p.relative_to(BASE)),bytes=p.stat().st_size,
               sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(paths)]
    manifest=dict(schema_version='v5.standalone_sources.v1',
        base_commit='b52334941e712dc642f78eae8970349332969aac',
        frontend_source_commit='e8c753b6109a8c26e8cf8c7cb843c789479260a0',
        frontend_product_commit='d53e0820318462806d9e67dae1818bb684b38ade',
        directories=DIRECTORIES,files=rows,
        dependency_policy=dict(readonly_preview='Python stdlib, tested separately from daily',
            daily='Existing Python >=3.14 and V5/uv.lock required; not installed or certified by packaging'),
        scope='READ_ONLY_SAVED_PREVIEW; daily source closure only; not full 18 module acceptance')
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status='MANIFEST_REFRESHED_REVIEW_REQUIRED',files=len(rows))))

if __name__=='__main__':main()

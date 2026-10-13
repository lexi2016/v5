"""Reproducible V5 build metadata over unchanged fixed-F original source bytes.

This creates a NEW V5 build identity. It does not recover a historical manifest,
change owner code, authorize providers, or accept arbitrary runtime source paths.
"""
import argparse
import hashlib
import json
from pathlib import Path

F='f7cb731c384ee6890a87d16c19a5b5a621779477'
EXTERNAL=('infrastructure/owned_io.py','infrastructure/interprocess_lock.py','infrastructure/trading_safety.py','ops/run_research_review_generation.py','contracts/vibe_runtime_profile.json')


def build(repo):
    vendor=repo/'V5/vendor/research_review_baseline'
    originals=json.loads((repo/'handoffs/M11/original_source/SOURCE_MANIFEST.json').read_text())
    prefix='fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/'
    originals={e['package_path'][len(prefix):]:e for e in originals if e['package_path'].startswith(prefix)}
    def bind(relative):
        path=vendor/relative
        if any(p.is_symlink() for p in [path,*path.parents]):raise ValueError('source symlink')
        raw=path.read_bytes();actual={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        e=originals[relative]
        if e['commit']!=F or any(actual[k]!=e[k] for k in actual):raise ValueError('fixed-F source drift: '+relative)
        return actual
    owner=vendor/'domains/research_review_generation'
    files={str(p.relative_to(owner)):bind(str(p.relative_to(vendor))) for p in sorted(owner.rglob('*.py'))}
    expected={name[len('domains/research_review_generation/'):] for name in originals if name.startswith('domains/research_review_generation/') and name.endswith('.py')}
    if set(files)!=expected or len(files)!=40:raise ValueError('fixed-F owner closure incomplete')
    return (json.dumps({'schema':'v5.m11.build_source_manifest.v1',
        'build_origin':{'repository':'lexi2016/v4','commit':F,'source_path':'handoff/v4-running-source-20261005/canonical'},
        'approval_status':'V5_NEW_BUILD_REQUIRES_EXTERNAL_PIN','historical_original_manifest':False,
        'files':files,'external_files':{name:bind(name) for name in sorted(EXTERNAL)}},sort_keys=True,indent=2)+'\n').encode()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    repo=Path(__file__).absolute().parents[2];raw=build(repo)
    target=repo/'V5/vendor/research_review_baseline/domains/research_review_generation/OWNED_SOURCE_MANIFEST.json'
    if args.check:
        if target.read_bytes()!=raw:raise SystemExit('V5 build manifest differs')
    else:target.write_bytes(raw)
    print(hashlib.sha256(raw).hexdigest())

"""Pinned original M08 owners, with explicit compatibility aliases only.

Canonical missing _namespace files are NOT fabricated. The existing frozen
namespace helper is mapped in memory, identified separately in the candidate.
No source formula, collector, store or donor byte is modified.
"""
import hashlib
import importlib.abc
import importlib.util
import json
import sys
from pathlib import Path
from .composition import no_symlinks
from .digests import sha256_json

ROOT=Path(__file__).resolve().parents[3]
DESCRIPTOR=ROOT/'integration_candidates/M08/CAPSULE_INTEGRATION_CANDIDATE.json'
SOURCE_SHA='451f39aabcec3206ebda1252f7cdd426bac4a19e74889ed35881a9ae9b787d8d'


def source_bytes():
    raw=no_symlinks(DESCRIPTOR).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise ValueError('M08_SOURCE_MANIFEST_SHA')
    entries=json.loads(raw)['entries']; result={}
    for entry in entries:
        path=no_symlinks(ROOT/entry['path']); data=path.read_bytes()
        if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256'] or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=entry['git_blob_sha']:
            raise ValueError('M08_SOURCE_BYTES:'+entry['module'])
        result[entry['module']]=(entry,data,path)
    return result


class FrozenOwners(importlib.abc.MetaPathFinder,importlib.abc.Loader):
    def __init__(self):
        self.sources=source_bytes(); self.packages={'stage_center','infrastructure'}
        for name,(entry,_,_) in self.sources.items():
            if entry['package']:self.packages.add(name)
            parts=name.split('.')
            for i in range(1,len(parts)):self.packages.add('.'.join(parts[:i]))
    def find_spec(self,fullname,path=None,target=None):
        if fullname in self.sources or fullname in self.packages:
            return importlib.util.spec_from_loader(fullname,self,is_package=fullname in self.packages)
        if fullname.split('.')[0] in ('stage_center','infrastructure'):
            raise ImportError('M08_SOURCE_CLOSURE_INCOMPLETE:'+fullname)
        return None
    def create_module(self,spec):return None
    def exec_module(self,module):
        if module.__name__ in self.packages:module.__path__=[]
        item=self.sources.get(module.__name__)
        if item:
            _,data,path=item;module.__file__=str(path)
            exec(compile(data,str(path),'exec'),module.__dict__)


def load_owners():
    if any(k in sys.modules for k in ('stage_center','infrastructure')):
        raise ValueError('M08_FRESH_PROCESS_REQUIRED')
    sys.meta_path.insert(0,FrozenOwners())
    from stage_center import selection,contracts,calendar
    return selection,contracts,calendar


def implementation_identity():
    names=('hk_stage_daily.py','hk_stage_reader.py','hk_stage_sources.py','contracts.py','digests.py','composition.py')
    return {name:hashlib.sha256(no_symlinks(Path(__file__).with_name(name)).read_bytes()).hexdigest() for name in names}

"""New isolated 09:25/09:30 M07 replay contract. Not original manifest recovery.
Runs original pinned selectors over explicit recorded input snapshots. No provider,
CURRENT, ledger, formal authority, shared locks, scheduling or production changes.
Must run as a fresh CLI process: the original in-process guard is permanent.
"""
import re,argparse,hashlib,importlib.abc,importlib.util,json,pathlib,sys,tempfile,types
HERE=pathlib.Path(__file__).resolve().parent
PINS_SHA='6b2e566bd77b03403b2d82487a3abf05571e8bf91b547a84fba0cad1f12be6f3'
MAX_REQUEST=2*1024*1024

def need(ok,reason):
 if not ok:raise ValueError(reason)
def strict(raw):
 def pairs(items):
  out={}
  for k,v in items:need(k not in out,'DUPLICATE_JSON_KEY');out[k]=v
  return out
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
def safe_bytes(path,limit):
 import os,stat
 path=pathlib.Path(path)
 need(not path.is_symlink() and not any(p.is_symlink() for p in path.parents),'SYMLINK')
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,'rb') as stream:
  info=os.fstat(stream.fileno());need(stat.S_ISREG(info.st_mode) and 0<info.st_size<=limit,'REGULAR_SIZE')
  raw=stream.read(limit+1)
 need(len(raw)==info.st_size,'SIZE_CHANGED');return raw

class FrozenV5(importlib.abc.MetaPathFinder,importlib.abc.Loader):
 def __init__(self,root,refs):
  self.root=root;self.sources={}
  for ref in refs:
   relative=pathlib.PurePosixPath(ref['path'])
   need(relative.parts[:3]==('V5','src','v5_shadow') and '..' not in relative.parts and relative.suffix=='.py','CODE_PATH')
   raw=safe_bytes(root/ref['path'],1024*1024)
   need(len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'CODE_PIN')
   name='.'.join(relative.parts[2:])[:-3];need(name not in self.sources,'DUPLICATE_CODE');self.sources[name]=(ref['path'],raw)
 def find_spec(self,name,path=None,target=None):
  if name=='v5_shadow' or name in self.sources:return importlib.util.spec_from_loader(name,self,is_package=name=='v5_shadow')
  if name.startswith('v5_shadow.'):raise ImportError('UNPINNED_V5_MODULE')
 def create_module(self,spec):return None
 def exec_module(self,module):
  if module.__name__=='v5_shadow':module.__path__=[];return
  path,raw=self.sources[module.__name__];module.__file__=str(self.root/path);exec(compile(raw,module.__file__,'exec'),module.__dict__)

def precise_request_times(request):
 # datetime.fromisoformat truncates beyond microseconds (including comma and
 # fractional UTC offsets). Never silently turn a late/nonexact time into a
 # cutoff-equal time. Original parsers still own syntax, date and timezone.
 recording=request.get('recording')
 values=[request.get('cutoff')]
 if isinstance(recording,dict):values.extend(recording.get(k) for k in ('captured_at','acquired_at'))
 for value in values:
  if isinstance(value,str) and re.search(r'[.,][0-9]{7,}',value):
   raise ValueError('M07_TIME_PRECISION_UNSUPPORTED')
  # CPython drops a fractional UTC offset when its whole-second part is zero.
  # Reject fractional offsets rather than allowing the parser to move an instant.
  if isinstance(value,str) and re.search(r'[+-][0-9:]+[.,][0-9]+$',value):
   raise ValueError('M07_OFFSET_PRECISION_UNSUPPORTED')

def replay(root,raw):
 need(type(raw)is bytes and 0<len(raw)<=MAX_REQUEST,'REQUEST_SIZE')
 request=strict(raw)
 need(type(request)is dict and request.get('stage_id') in ('STAGE_0925','STAGE_0930_0935'),'STAGE_SCOPE')
 precise_request_times(request)
 need(not any(n=='v5_shadow' or n.startswith('v5_shadow.') for n in sys.modules),'FRESH_PROCESS_REQUIRED')
 pins=safe_bytes(HERE/'CODE_PINS.json',65536);need(hashlib.sha256(pins).hexdigest()==PINS_SHA,'NEW_CODE_MANIFEST_PIN')
 manifest=strict(pins);need(manifest['schema']=='NEW_M07_REPLAY_CODE_IDENTITY_V1' and manifest['not_original_source_manifest'] is True,'NEW_CONTRACT_IDENTITY')
 root=pathlib.Path(root).resolve();loader=FrozenV5(root,manifest['refs']);sys.meta_path.insert(0,loader)
 import v5_shadow.a_stage_daily as m
 request=m._request(request);owner=m._load_owner()
 with tempfile.TemporaryDirectory(prefix='new-m07-replay-') as t:
  folder=pathlib.Path(t);roots,originals=m._snapshots(request,folder);m._guard((folder,))
  spec,pool,recording,rows=m._admit(request,roots)
  synthetic=any('SYNTHETIC' in str(v).upper() for v in [recording['source_id'],*recording['source_evidence']])
  need(not synthetic or request['data_kind']=='SYNTHETIC','SYNTHETIC_RELABEL_FORBIDDEN')
  result,selector_input=m._select(request,roots,spec,pool,recording,rows,owner)
  for key,files in originals.items():
   for relative,data in files.items():need(m._bytes(m._path(roots[key],relative))==data,'SNAPSHOT_MUTATED')
  m._owner_sources()
  return {'schema':'NEW_M07_ISOLATED_REPLAY_RESULT_V1','status':'ORIGINAL_SELECTOR_REPLAY_NOT_ADMITTED','contract_kind':'NEW_NOT_ORIGINAL_SOURCE_MANIFEST','code_manifest_sha256':PINS_SHA,'owner_closure_sha256':m.MANIFEST_SHA256,'request_sha256':hashlib.sha256(raw).hexdigest(),'target_date':request['target_date'],'stage_id':request['stage_id'],'data_kind':request['data_kind'],'known_synthetic':synthetic,'pool_codes':list(pool.codes),'missing_symbols':recording['missing_symbols'],'selection':result,'selector_input':selector_input,'production_allowed':False,'natural_verified':False,'business_accepted':False,'source_admission':'UNKNOWN','orders_sent':False,'collector_calls':0,'activation_performed':False,'persistent_outputs_written':False,'isolation':'ORIGINAL_PYTHON_GUARD_NOT_OS_CERTIFICATION'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--m07-root',required=True);a=p.parse_args()
 try:
  result=replay(a.m07_root,sys.stdin.buffer.read(MAX_REQUEST+1));print(json.dumps(result,ensure_ascii=False,allow_nan=False))
 except Exception as error:
  print(json.dumps({'status':'BLOCKED_NEW_REPLAY','reason':type(error).__name__+':'+str(error),'production_allowed':False,'natural_verified':False,'source_admission':'UNKNOWN','orders_sent':False}));sys.exit(2)

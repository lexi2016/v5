"""Private owner snapshot adapter. No catalog registration, bootstrap or disk writes.

An enclosing trusted owner must supply pinned registry bytes and a held-snapshot
reader. A caller-chosen registry hash is NOT authority; this is no public API.
"""
import hashlib,json,gzip,copy
from datetime import datetime

def need(ok,label):
 if not ok:raise ValueError(label)
def hexsha(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def canon(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def checked(raw,ref):
 need(isinstance(raw,bytes) and type(ref.get('bytes')) is int and ref['bytes']>=0 and len(raw)==ref['bytes'] and hexsha(ref.get('sha256')) and hashlib.sha256(raw).hexdigest()==ref['sha256'],'SNAPSHOT_BYTES')
 return raw

class Binding:
 def __init__(self,registry_bytes,owner_registry_ref,snapshot_reader,gate):
  self.gate=gate;gate()
  registry=json.loads(checked(registry_bytes,owner_registry_ref))
  need(registry.get('schema')=='OWNER_CHECKPOINT_REGISTRY_V1','REGISTRY_SCHEMA')
  need(type(registry.get('entries')) is list,'REGISTRY_ENTRIES')
  self.entries={};self.snapshots={}
  for entry in registry['entries']:
   prior=entry['continuation_ref'];cp=entry['checkpoint_ref'];key=prior['sha256']
   need(hexsha(key) and key not in self.entries,'REGISTRY_DUPLICATE_OR_SHA')
   gate();prior_raw=checked(snapshot_reader(prior),prior);gate();cp_raw=checked(snapshot_reader(cp),cp)
   bundle=json.loads(gzip.decompress(prior_raw));checkpoint=json.loads(cp_raw)
   need(bundle.get('schema') in ('NOV5_MINIMUM_CONTINUATION_BUNDLE_V1','SAME_BASIS_CONTINUATION_BUNDLE_V1'),'CONTINUATION_SCHEMA')
   need(checkpoint.get('schema')=='OWNER_CHECKPOINT_PREFIX_V1' and checkpoint.get('prior_continuation_sha256')==key,'CHECKPOINT_PRIOR')
   state=bundle['component109'];state51=bundle['state51']
   symbol=bundle.get('symbol');date=bundle.get('asof')
   need(isinstance(symbol,str) and bool(symbol.strip()) and isinstance(date,str) and len(date)==8 and date.isascii() and date.isdigit(),'CONTINUATION_IDENTITY_REQUIRED')
   try:datetime.strptime(date,'%Y%m%d')
   except ValueError as exc:raise ValueError('CONTINUATION_DATE') from exc
   need(canon(state)==canon(checkpoint['state']),'STATE_NOT_SAME_CONTINUATION')
   need(state.get('symbol')==bundle.get('symbol') and state.get('last_date')==bundle.get('asof') and type(state.get('count')) is int and state['count']>0 and type(state51.get('count')) is int and state51['count']==state['count'],'CONTINUATION_STATE_IDENTITY')
   need(hexsha(checkpoint.get('prefix_sha256')),'PERSISTED_PREFIX_REQUIRED')
   self.entries[key]=(copy.deepcopy(prior),copy.deepcopy(cp))
   self.snapshots[canon(cp)]=cp_raw
  gate()
 def bound_checkpoint_ref(self,selection):
  self.gate();prior=selection.get('continuation_ref',{});key=prior.get('sha256')
  need(key in self.entries,'UNREGISTERED_PRIOR_NO_SYNTHESIS')
  registered,cp=self.entries[key]
  need(prior==registered,'PRIOR_REF_NOT_OWNER_SNAPSHOT')
  return copy.deepcopy(cp)
 def checked(self,ref):
  self.gate();raw=self.snapshots.get(canon(ref))
  need(raw is not None,'UNREGISTERED_CHECKPOINT')
  return checked(raw,ref)

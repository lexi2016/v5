"""Isolated coordination experiment. Not connected to production owner or locks."""
import contextlib,fcntl,hashlib,json,os,pathlib
TAG='LATEST109_ISOLATED_LEDGER_V1'
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save_new(path,obj):
 raw=json.dumps(obj,sort_keys=True).encode();fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 finally:pass
 fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def initialize(root):
 root=pathlib.Path(root);root.mkdir(exist_ok=False);save_new(root/'ISOLATED_ONLY.json',{'tag':TAG})
 (root/'claims').mkdir();return root
class Ledger:
 def __init__(self,root):
  self.root=pathlib.Path(root).absolute()
  if self.root!=self.root.resolve() or json.loads((self.root/'ISOLATED_ONLY.json').read_text())!={'tag':TAG}:raise ValueError('ISOLATED_ROOT_REQUIRED')
 @contextlib.contextmanager
 def lock(self):
  fd=os.open(self.root/'COORDINATOR.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
  try:
   fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);yield
  finally:os.close(fd)
 def location(self,identity):
  if set(identity)!={'symbol','event_date','input_sha256','code_sha256','checkpoint_sha256'} or not all(type(v)is str and v for v in identity.values()):raise ValueError('IDENTITY_REQUIRED')
  # Date+symbol excludes version: changed inputs cannot bypass an uncertain claim.
  p=self.root/'claims'/digest({k:identity[k] for k in ('symbol','event_date')})
  if p!=p.resolve():raise ValueError('CLAIM_SYMLINK_REJECTED')
  return p
 def checked_artifact(self,artifact):
  p=self.root/artifact['path']
  if p!=p.resolve() or not p.is_relative_to(self.root) or not p.is_file():raise ValueError('ARTIFACT_SCOPE')
  raw=p.read_bytes()
  if len(raw)!=artifact['bytes'] or hashlib.sha256(raw).hexdigest()!=artifact['sha256']:raise ValueError('ARTIFACT_CHANGED')
 def inspect_locked(self,claim,identity):
  record=json.loads((claim/'STARTED.json').read_text())
  if record['identity']!=identity:raise ValueError('IDENTITY_CONFLICT_INSPECT')
  if (claim/'SUCCESS.json').exists() and (claim/'FAILED.json').exists():raise ValueError('CONFLICTING_TERMINALS')
  if (claim/'SUCCESS.json').exists():
   success=json.loads((claim/'SUCCESS.json').read_text())
   if success['identity']!=identity or not success['artifacts']:raise ValueError('TERMINAL_BINDING')
   for a in success['artifacts']:self.checked_artifact(a)
   return {'status':'REUSE_VERIFIED','claim':str(claim),'artifacts':success['artifacts']}
  return {'status':'FAILED_INSPECT_NO_RETRY' if (claim/'FAILED.json').exists() else 'UNKNOWN_INSPECT_NO_RETRY','claim':str(claim)}
 def claim(self,identity,requested_output):
  with self.lock():
   c=self.location(identity)
   if c.exists():return self.inspect_locked(c,identity)
   c.mkdir();save_new(c/'STARTED.json',{'identity':identity,'requested_output':str(requested_output),'production_allowed':False})
   return {'status':'CLAIMED','claim':str(c)}
 def finish(self,identity,artifacts=None,error=None):
  with self.lock():
   c=self.location(identity);old=self.inspect_locked(c,identity)
   if old['status']!='UNKNOWN_INSPECT_NO_RETRY':raise ValueError('TERMINAL_EXISTS')
   if error is not None:save_new(c/'FAILED.json',{'identity':identity,'error':str(error)});return
   if not artifacts:raise ValueError('ARTIFACTS_REQUIRED')
   for a in artifacts:self.checked_artifact(a)
   save_new(c/'SUCCESS.json',{'identity':identity,'artifacts':artifacts,'production_allowed':False})

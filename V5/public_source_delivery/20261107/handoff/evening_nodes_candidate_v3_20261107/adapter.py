"""Pinned read-only merged-state adapter; isolated content-addressed freeze writer."""
import datetime as dt,fcntl,hashlib,json,os,stat,sys,types
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];LIMIT=16*1024**2

def raw_read(path):
 p=Path(path);p=p if p.is_absolute() else ROOT/p
 if not p.is_relative_to(ROOT) or '..' in p.parts:raise ValueError('PATH_SCOPE')
 fds=[]
 try:
  fd=os.open(ROOT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(fd)
  parts=p.relative_to(ROOT).parts
  for part in parts[:-1]:fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(fd)
  f=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);fds.append(f);before=os.fstat(f)
  if not stat.S_ISREG(before.st_mode) or not 0<before.st_size<=LIMIT:raise ValueError('SIZE_TYPE')
  raw=b''
  while len(raw)<=before.st_size:
   b=os.read(f,min(65536,before.st_size+1-len(raw)))
   if not b:break
   raw+=b
  after=os.fstat(f);named=os.stat(parts[-1],dir_fd=fd,follow_symlinks=False)
  identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
  if len(raw)!=before.st_size or identity(before)!=identity(after) or identity(after)!=identity(named):raise ValueError('READ_CHANGED')
  return raw
 finally:
  for fd in reversed(fds):os.close(fd)
def ref(path):
 raw=raw_read(path);return {'path':str(Path(path).relative_to(ROOT) if Path(path).is_absolute() else path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def checked(pin):
 if not isinstance(pin,dict) or set(pin)!={'path','bytes','sha256'}:raise ValueError('PIN_SHAPE')
 raw=raw_read(pin['path'])
 if len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('PIN_CHANGED')
 return json.loads(raw)
def inspect():
 # Public source export intentionally has no private deployment binding.
 # No runtime caller may register or bypass an approved evidence adapter.
 raise ValueError('PUBLIC_EXPORT_NO_APPROVED_PRIVATE_INPUT_BINDING')
def snapshot(expected):
 raise ValueError('PUBLIC_EXPORT_NO_APPROVED_RUNTIME_BINDING')

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def freeze(report,root=None):
 root=HERE/'frozen' if root is None else root
 if not root.is_relative_to(HERE) or '..' in root.parts or root.is_symlink() or root.resolve()!=root:raise ValueError('WRITER_SCOPE')
 root.mkdir(exist_ok=True);fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 lock=None
 try:
  lock=os.open('WRITER.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600,dir_fd=fd)
  if not stat.S_ISREG(os.fstat(lock).st_mode) or os.fstat(lock).st_nlink!=1:raise ValueError('WRITER_LOCK_TYPE')
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  raw=canonical(report)
  if len(raw)>LIMIT:raise ValueError('OUTPUT_SIZE')
  key=hashlib.sha256(raw).hexdigest()
  manifest=canonical({'schema':'FROZEN_EVENING_PACKAGE_V1','report_sha256':key,'bytes':len(raw),'generated':True,'saved_local':True,'uploaded':False,'readback':'SUCCESSFUL_FREEZE_RETURN_REQUIRED_NOT_FILE_PRESENCE','business_accepted':False,'natural_verified':False,'delivery_status':'NOT_SENT'})
  try:os.mkdir(key,dir_fd=fd)
  except FileExistsError:
   path=root/key/'report.json'
   if raw_read(path)!=raw or raw_read(root/key/'manifest.json')!=manifest:raise ValueError('FROZEN_CONFLICT_OR_INCOMPLETE')
   return root/key
  child=os.open(key,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
  try:
   contents={'report.json':raw,'manifest.json':manifest}
   for name,data in contents.items():
    f=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=child)
    with os.fdopen(f,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
   os.fsync(child)
  finally:os.close(child)
  os.fsync(fd)
  if raw_read(root/key/'report.json')!=raw:raise ValueError('REPORT_READBACK_FAILED')
  if raw_read(root/key/'manifest.json')!=manifest:raise ValueError('MANIFEST_READBACK_FAILED')
  return root/key
 finally:
  if lock is not None:os.close(lock)
  os.close(fd)

"""Fixed bootstrap: execute the same bounded launcher bytes whose SHA was read."""
import argparse,hashlib,json,os,stat,sys,types
from pathlib import Path
HERE=Path(__file__).absolute().parent
ROOT=HERE.parents[1]
LAUNCHER_SHA='cc19ae4822353999389c4791726ee3b14d7e3f6e38131d7bb33ff9db19eb8db0'
LAUNCHER_BYTES=19869

def load():
 fds=[];path=HERE/'launcher.py'
 try:
  fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(fd)
  for part in path.parts[1:-1]:fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(fd)
  f=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);fds.append(f);before=os.fstat(f)
  if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size!=LAUNCHER_BYTES:raise ValueError('BOOTSTRAP_TYPE_SIZE')
  raw=b''
  while len(raw)<=before.st_size:
   b=os.read(f,min(65536,before.st_size+1-len(raw)))
   if not b:break
   raw+=b
  ident=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
  if len(raw)!=LAUNCHER_BYTES or ident(before)!=ident(os.fstat(f)) or ident(before)!=ident(os.stat(path.name,dir_fd=fd,follow_symlinks=False)) or hashlib.sha256(raw).hexdigest()!=LAUNCHER_SHA:raise ValueError('BOOTSTRAP_LAUNCHER_PIN')
 finally:
  for fd in reversed(fds):os.close(fd)
 name='_pinned_us_fixed_launcher_v5';m=types.ModuleType(name);m.__file__=str(path)
 m.__verified_source_pin__={'path':str(path.relative_to(ROOT)),'bytes':LAUNCHER_BYTES,'sha256':LAUNCHER_SHA}
 sys.modules[name]=m;exec(compile(raw,str(path),'exec'),m.__dict__);return m

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('operation',choices=('preflight','execute','reconcile'));args=p.parse_args();m=load()
 if args.operation=='reconcile':
  b=m.load_bundle();result=m.replay(b,b['session_plan'].plan(m.TARGET))
 else:result=m.execute() if args.operation=='execute' else m.preflight()
 print(json.dumps(result,ensure_ascii=False,indent=2))

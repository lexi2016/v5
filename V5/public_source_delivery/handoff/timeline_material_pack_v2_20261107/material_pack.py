"""Isolated material assembly, not a source collector, research model, or scheduler.
Accepts an explicitly supplied list only. Never discovers private files or sends data.
Byte integrity is not source authorization, content truth, or business acceptance.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
import stat
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

SLOTS={'night':('material_identity','logical_risk','business_mapping'),
       'morning-materials':('announcements','essential_news','preopen_memo','preopen_analysis')}
MAX_BYTES=8*1024*1024

def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(v):return hashlib.sha256(v).hexdigest()
def timestamp(v):
 t=dt.datetime.fromisoformat(v)
 if t.tzinfo is None:raise ValueError('NAIVE_TIMESTAMP')
 return t

def directory_fd(path,create=False):
 """Anchor every component from / without following directory symlinks."""
 absolute=Path(os.path.abspath(path))
 fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  for part in absolute.parts[1:]:
   if create:
    try:os.mkdir(part,mode=0o700,dir_fd=fd)
    except FileExistsError:pass
   child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
   os.close(fd);fd=child
  return fd
 except BaseException:
  os.close(fd);raise

def read_at(parent,name):
 fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,dir_fd=parent)
 try:
  before=os.fstat(fd)
  if not stat.S_ISREG(before.st_mode) or before.st_size>MAX_BYTES:raise ValueError('FILE_TYPE_OR_SIZE')
  data=bytearray()
  while len(data)<=MAX_BYTES:
   chunk=os.read(fd,min(65536,MAX_BYTES+1-len(data)))
   if not chunk:break
   data.extend(chunk)
  after=os.fstat(fd)
  if len(data)>MAX_BYTES:raise ValueError('FILE_SIZE')
  identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
  if identity(before)!=identity(after):raise ValueError('FILE_CHANGED_DURING_READ')
  return bytes(data)
 finally:os.close(fd)

def local_bytes(root,relative):
 p=Path(relative)
 if p.is_absolute() or '..' in p.parts or not p.parts:raise ValueError('PATH_SCOPE')
 fd=directory_fd(root)
 try:
  for part in p.parts[:-1]:
   child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
   os.close(fd);fd=child
  return read_at(fd,p.name)
 finally:os.close(fd)

def assemble(root,node,target_date,records,now):
 if node not in SLOTS:raise ValueError('UNSUPPORTED_ASSEMBLY_NODE')
 if now.tzinfo is None:raise ValueError('TIMEZONE_REQUIRED')
 target=dt.date.fromisoformat(target_date)
 if now.astimezone(ZoneInfo('Asia/Shanghai')).date()!=target:raise ValueError('WRONG_TARGET_DATE')
 if not isinstance(records,list):raise ValueError('RECORDS_LIST_REQUIRED')
 rows=[];seen={};errors=[]
 for record in records:
  row=dict(record) if isinstance(record,dict) else {'invalid_input':str(type(record))}
  try:
   key=(row['category'],row['path']);fingerprint=sha(canonical(row))
   if key in seen:
    if seen[key]!=fingerprint:raise ValueError('CONFLICTING_DUPLICATE')
    continue
   seen[key]=fingerprint
   if row['category'] not in SLOTS[node]:raise ValueError('UNEXPECTED_CATEGORY')
   if row['source_date']!=target_date:raise ValueError('HISTORICAL_OR_WRONG_SOURCE_DATE')
   url=urlsplit(row['source_url'])
   if url.scheme not in ('http','https') or not url.hostname or url.username or url.password:raise ValueError('SOURCE_URL')
   if not isinstance(row['title'],str) or not row['title'].strip():raise ValueError('TITLE')
   published=timestamp(row['published_at']);retrieved=timestamp(row['retrieved_at'])
   if published>retrieved or retrieved>now:raise ValueError('TIME_ORDER_OR_FUTURE')
   data=local_bytes(root,row['path'])
   if sha(data)!=row['sha256']:raise ValueError('SHA_MISMATCH')
   row.update(byte_integrity='PASS',byte_count=len(data),content_truth='NOT_VERIFIED',source_authorization='NOT_GRANTED_BY_ASSEMBLER')
  except (ValueError,OSError,KeyError,TypeError) as e:
   row.update(byte_integrity='FAILED_OR_UNKNOWN',error=type(e).__name__+':'+str(e));errors.append(row['error'])
  rows.append(row)
 filled={r.get('category') for r in rows if r.get('byte_integrity')=='PASS'}
 missing=[s for s in SLOTS[node] if s not in filled]
 body={'schema':'TIMELINE_MATERIAL_ASSEMBLY_V1','node':node,'target_date':target_date,
  'code_sha256':sha(Path(__file__).read_bytes()),'items':rows,'missing_slots':missing,'errors':errors,
  'assembly_status':'BLOCKED' if missing or errors else 'READY_FOR_REVIEW',
  'business_accepted':False,'natural_verified':False,'trigger_source':'MANUAL_ASSEMBLY',
  'job_started':False,'source_calls':0,'training_calls':0,'delivery_status':'NOT_SENT',
  'source_admission':'REQUIRES_ORIGINAL_PROJECT_SOURCE_REVIEW','scope':'LOCAL_BYTE_AND_REQUIRED_SLOT_CHECK_ONLY'}
 body['identity']=sha(canonical(body))
 body['observed_at']=now.isoformat()
 return body

def write_at(parent,name,data):
 fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=parent)
 try:
  pending=memoryview(data)
  while pending:
   n=os.write(fd,pending)
   if n<=0:raise OSError('SHORT_WRITE')
   pending=pending[n:]
  os.fsync(fd)
 finally:os.close(fd)

def freeze(destination,report):
 """FD-relative exclusive candidate snapshot, never formal project acceptance."""
 identity=report.get('identity')
 if not isinstance(identity,str) or len(identity)!=64 or any(c not in '0123456789abcdef' for c in identity):raise ValueError('IDENTITY')
 core={k:v for k,v in report.items() if k not in ('identity','observed_at')}
 if sha(canonical(core))!=identity:raise ValueError('REPORT_IDENTITY')
 root=directory_fd(destination,create=True);folder=None;reused=False
 try:
  try:os.mkdir(identity,mode=0o700,dir_fd=root)
  except FileExistsError:reused=True
  folder=os.open(identity,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root)
  if not reused:
   raw=canonical(report);manifest=canonical({'sha256':sha(raw),'bytes':len(raw),'identity':identity})
   if len(raw)>MAX_BYTES:raise ValueError('REPORT_SIZE')
   write_at(folder,'report.json',raw);write_at(folder,'manifest.json',manifest)
   os.fsync(folder)
  try:
   raw=read_at(folder,'report.json');manifest=json.loads(read_at(folder,'manifest.json'));stored=json.loads(raw)
  except (OSError,ValueError) as e:raise ValueError('INCOMPLETE_PRIOR_FREEZE_NO_OVERWRITE') from e
  if manifest!={'sha256':sha(raw),'bytes':len(raw),'identity':identity} or {k:v for k,v in stored.items() if k not in ('identity','observed_at')}!=core or stored.get('identity')!=identity:raise ValueError('READBACK_CHANGED')
  # Also require the advertised path still opens the exact held directories.
  check=directory_fd(destination)
  try:
   if (os.fstat(check).st_dev,os.fstat(check).st_ino)!=(os.fstat(root).st_dev,os.fstat(root).st_ino):raise ValueError('OUTPUT_ROOT_RENAMED')
   child=os.open(identity,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=check)
   try:
    if (os.fstat(child).st_dev,os.fstat(child).st_ino)!=(os.fstat(folder).st_dev,os.fstat(folder).st_ino):raise ValueError('OUTPUT_DIR_RENAMED')
   finally:os.close(child)
  finally:os.close(check)
  return {'path':str(Path(destination)/identity/'report.json'),'sha256':sha(raw),'byte_readback':'PASS','reused':reused,'saved_candidate':True,'uploaded':False,'business_accepted':False}
 finally:
  if folder is not None:os.close(folder)
  os.close(root)

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--records',type=Path,required=True);p.add_argument('--node',choices=SLOTS,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 now=dt.datetime.now(dt.timezone.utc);date=now.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
 report=assemble(a.root,a.node,date,json.loads(a.records.read_text()),now)
 print(json.dumps(freeze(a.output,report),ensure_ascii=False,indent=2))
if __name__=='__main__':main()

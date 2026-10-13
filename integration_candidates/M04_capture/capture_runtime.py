"""Explicit M04 acquisition and recovery around unchanged frozen original owners.

No schedule, model, credential discovery, V4 runtime lookup, or shared publication.
The only network-capable action is capture, using the explicitly pinned CLI.
"""
import contextlib
from datetime import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import uuid
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
V5=ROOT/'source/V5'
PRODUCER=V5/'producers/archive-acquisition-v2/source'
sys.path.insert(0,str(V5/'src'))
from v5_shadow import research_ingest_daily as ingest
from v5_shadow.current_us_research import _raw_file
from v5_shadow.digests import canonical_bytes,MAX_JSON_BYTES,sha256_json
FIELDS={'schema_version','runtime_root','cli','selector_panel','groups','page_limit','max_pages','lookback_days'}
MARKER=b'v5.m04-capture.v1\n'
SAFETY=ingest.SAFETY
_OWNER=None


def _absolute(value):
 if not isinstance(value,str) or not value or '\\' in value:raise ValueError('ABSOLUTE_PATH')
 p=Path(value)
 if not p.is_absolute() or '..' in p.parts or str(p)!=value or any(x.is_symlink() for x in (p,*p.parents)):raise ValueError('ABSOLUTE_PATH')
 return p


def _read(path):
 if path.is_symlink() or path.stat().st_size>MAX_JSON_BYTES:raise ValueError('CHECKPOINT_PATH_SIZE')
 return json.loads(path.read_bytes())


def _checkpoint(path,value):
 # The original ingest remains unchanged. New wrapper receipts are committed
 # atomically without replacing a prior receipt, including after interruption.
 pending=path.with_name(path.name+'.'+uuid.uuid4().hex+'.pending')
 try:
  with pending.open('xb') as stream:
   stream.write(canonical_bytes(value));stream.flush();os.fsync(stream.fileno())
  os.link(pending,path,follow_symlinks=False)
  descriptor=os.open(path.parent,os.O_RDONLY)
  try:os.fsync(descriptor)
  finally:os.close(descriptor)
 finally:
  if pending.exists():pending.unlink()



def verify_sources():
 manifest=_read(ROOT/'RELEASE.json')
 for name,expected in manifest['files'].items():
  if hashlib.sha256(_raw_file(ROOT,name)).hexdigest()!=expected:raise ValueError('RELEASE_SOURCE_SHA:'+name)
 return manifest


def validate(config,*,check_inputs=True):
 if not isinstance(config,dict) or set(config)!=FIELDS or config['schema_version']!='v5.m04_capture_config.v1':raise ValueError('CONFIG_FIELDS')
 root=_absolute(config['runtime_root'])
 if not root.is_dir():raise ValueError('RUNTIME_ROOT_REQUIRED')
 if root==ROOT or ROOT in root.parents or root in ROOT.parents:raise ValueError('RUNTIME_SOURCE_OVERLAP')
 for name in ('cli','selector_panel'):
  ref=config[name]
  if not isinstance(ref,dict) or set(ref)!={'path','sha256'} or not re.fullmatch('[0-9a-f]{64}',str(ref['sha256'])):raise ValueError('INPUT_REFERENCE')
  p=_absolute(ref['path'])
  if p==root or root in p.parents:raise ValueError('INPUT_IN_RUNTIME')
  if check_inputs:
   if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=ref['sha256']:raise ValueError('INPUT_SHA:'+name)
   if name=='cli' and not os.access(p,os.X_OK):raise ValueError('CLI_NOT_EXECUTABLE')
 groups=config['groups']
 if not isinstance(groups,list) or not groups or len(groups)>20:raise ValueError('GROUPS')
 seen=set()
 for row in groups:
  if not isinstance(row,list) or len(row)!=2 or not isinstance(row[0],str) or not re.fullmatch('[0-9]{1,30}',row[0]) or not isinstance(row[1],str) or not row[1] or row[0] in seen:raise ValueError('GROUPS')
  seen.add(row[0])
 for key,limit in [('page_limit',30),('max_pages',20),('lookback_days',4)]:
  if type(config[key]) is not int or not 1<=config[key]<=limit:raise ValueError('CAPTURE_BOUND:'+key)
 if len(groups)*config['max_pages']>400:raise ValueError('CAPTURE_PAGE_BOUND')
 return root


def initialize(config):
 root=validate(config)
 marker=root/'.v5-m04-capture';existed=marker.exists()
 if existed:
  if _raw_file(root,marker.name)!=MARKER:raise ValueError('RUNTIME_MARKER')
 else:
  if list(root.iterdir()):raise ValueError('INIT_EMPTY_ROOT_REQUIRED')
  with marker.open('xb') as f:f.write(MARKER)
 with _lock(root):
  for name in ('captures','ingest'):
   p=root/name
   if p.is_symlink():raise ValueError('RUNTIME_SUBROOT')
   p.mkdir(exist_ok=True)
  path=root/'ingest/.v5-research-ingest'
  if path.exists():
   if _raw_file(root,'ingest/.v5-research-ingest')!=b'v5.research-ingest.v1\n':raise ValueError('INGEST_STATE_MARKER')
  else:
   with path.open('xb') as f:f.write(b'v5.research-ingest.v1\n')
 return {'status':'EXISTS' if existed else 'INITIALIZED',**SAFETY}


def _owned(config):
 root=validate(config,check_inputs=False)
 if _raw_file(root,'.v5-m04-capture')!=MARKER:raise ValueError('RUNTIME_MARKER')
 for name in ('captures','ingest'):
  if not (root/name).is_dir() or (root/name).is_symlink():raise ValueError('RUNTIME_SUBROOT')
 return root


@contextlib.contextmanager
def _lock(root):
 fd=os.open(root/'capture.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'r+b') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError as exc:raise ValueError('CAPTURE_BUSY') from exc
  yield


def _run(root,run_id):
 if not isinstance(run_id,str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}',run_id):raise ValueError('RUN_ID')
 p=root/'captures'/run_id
 if p.is_symlink():raise ValueError('RUN_PATH')
 return p


def _producer():
 global _OWNER
 if _OWNER is None:
  sys.path.insert(0,str(PRODUCER))
  spec=importlib.util.spec_from_file_location('m04_frozen_acquisition',PRODUCER/'ops/run_zsxq_hourly_delta.py')
  _OWNER=importlib.util.module_from_spec(spec);spec.loader.exec_module(_OWNER)
 return _OWNER


def _request(root,attempt,claim):
 capture=attempt/'source'
 rel=f"research_module/runtime_outputs/zsxq_hourly/{claim['trade_date']}/{claim['slot']}/v35_zsxq_hourly_status_{claim['trade_date']}_{claim['slot']}.json"
 try:raw=_raw_file(capture,rel)
 except FileNotFoundError as exc:raise ValueError('CAPTURE_INCOMPLETE: no committed original status; retain attempt, use a new run only after review') from exc
 status=json.loads(raw)
 if status.get('fetch_ok') is not True or status.get('status') not in {'READY','READY_EMPTY'}:raise ValueError('CAPTURE_INCOMPLETE')
 if status.get('trade_date')!=claim['trade_date'] or status.get('slot')!=claim['slot']:raise ValueError('CAPTURE_STATUS_IDENTITY')
 if 'acquisition_evidence_v2' not in status:raise ValueError('ACQUISITION_TIME_UNKNOWN')
 receipt={k:status['acquisition_evidence_v2'][k] for k in ('path','sha256','bytes')}
 receipt_raw=_raw_file(capture,receipt['path'])
 if hashlib.sha256(receipt_raw).hexdigest()!=receipt['sha256'] or len(receipt_raw)!=receipt['bytes']:raise ValueError('CAPTURE_RECEIPT_SHA')
 r=json.loads(receipt_raw)
 names=set(r['files'])|{p['path'] for p in r['pages']}|{receipt['path'],rel}
 files={name:hashlib.sha256(_raw_file(capture,name)).hexdigest() for name in sorted(names)}
 return {'capture_root':str(capture),'capture_files':files,'receipt':receipt,'status':{'path':rel,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)},'state_root':str(root/'ingest')}


def _resume(config,root,attempt):
 if not attempt.is_dir():raise ValueError('CAPTURE_NOT_FOUND')
 claim=_read(attempt/'claim.json')
 if claim.get('run_id')!=attempt.name:raise ValueError('CAPTURE_CLAIM_IDENTITY')
 if claim['config_sha256']!=sha256_json(config):raise ValueError('CAPTURE_CONFIG_IDENTITY')
 request=_request(root,attempt,claim)
 request_path=attempt/'request.json'
 if request_path.exists():
  if _read(request_path)!=request:raise ValueError('CAPTURE_REQUEST_CHANGED')
 else:_checkpoint(request_path,request)
 result=ingest.run(request)
 # Re-read the original owner on every resume, including when our receipt was lost.
 if (attempt/'result.json').exists():
  if _read(attempt/'result.json')!=result:raise ValueError('CAPTURE_RESULT_CHANGED')
 else:_checkpoint(attempt/'result.json',result)
 return result


def resume(config,run_id):
 root=_owned(config)
 with _lock(root):return _resume(config,root,_run(root,run_id))


def capture(config,trade_date,slot,run_id):
 root=_owned(config)
 with _lock(root):
  attempt=_run(root,run_id)
  if attempt.exists():
   claim=_read(attempt/'claim.json')
   if claim.get('trade_date')!=trade_date or claim.get('slot')!=slot or claim.get('run_id')!=run_id:raise ValueError('CAPTURE_REQUEST_IDENTITY')
   return _resume(config,root,attempt)
  validate(config)
  now=datetime.now(ZoneInfo('Asia/Shanghai'))
  if not isinstance(trade_date,str) or trade_date!=now.strftime('%Y%m%d'):raise ValueError('NEW_CAPTURE_DATE_REQUIRED')
  if slot not in ['0830']+[f'{hour:02d}00' for hour in range(9,24)]:raise ValueError('CAPTURE_SLOT')
  if slot>now.strftime('%H%M'):raise ValueError('CAPTURE_FUTURE_SLOT')
  attempt.mkdir(mode=0o700);source=attempt/'source';source.mkdir()
  (source/'.v5-archive-acquisition').write_bytes(b'v5.archive-acquisition.v2\n')
  claim={'schema_version':'v5.m04_capture_claim.v1','config_sha256':sha256_json(config),'trade_date':trade_date,'slot':slot,'run_id':run_id,**SAFETY}
  _checkpoint(attempt/'claim.json',claim)
  try:
   status=_producer().materialize_zsxq_hourly_delta(data_root=source,trade_date=trade_date,slot=slot,cli=Path(config['cli']['path']),selector_panel=Path(config['selector_panel']['path']),refetch_root=PRODUCER/'upstreams',groups=[tuple(x) for x in config['groups']],page_limit=config['page_limit'],max_pages=config['max_pages'],lookback_days=config['lookback_days'])
   _checkpoint(attempt/'status.json',status)
   # Keep the original analyzer's lookup health/error in persisted summary;
   # it is not upgraded to security identity or strategy qualification here.
   return _resume(config,root,attempt)
  except Exception as exc:
   ingest._write(attempt/'failure.json',{'status':'FAILED','reason':type(exc).__name__+':'+str(exc),**SAFETY})
   raise


def _article(article,name,digest):
 retrieved=article.get('retrieved_at') or None;available=article.get('available_at') or None
 return {'article_id':article['article_id'],'body_text':article.get('body_text'),'published_at':article.get('published_at'),'retrieved_at':retrieved,'available_at':available,'acquisition_status':'RECORDED' if retrieved not in (None,'UNKNOWN') and available not in (None,'UNKNOWN') else 'UNKNOWN','archive_file':name,'archive_sha256':digest,'source_article':article}


def verified_records(binding):
 checked=ingest.cold_read(binding);selected={};outside={}
 for key,record in checked['records'].items():
  day,slot=key.split('/')
  name=f'research/hourly/live/{day}/{slot}.json' if slot else f'research/archives/{day}.json'
  if name not in binding['files']:
   if record.get('error'):outside[key]=record['error']
   continue
  if record.get('error'):raise ValueError('ORIGINAL_READER_REJECTED:'+json.dumps(record['error']))
  if record.get('payload') is None:raise ValueError('BOUND_ARCHIVE_NOT_MATERIALIZED')
  if record['binding']['payload_path']!=name or record['binding']['receipt_path'] not in binding['files']:raise ValueError('ARTICLE_REFERENCE_NOT_BOUND')
  selected[key]=record
 return checked,selected,outside


def materials(binding):
 checked,selected,outside=verified_records(binding);rows=[]
 for record in selected.values():
  name=record['binding']['payload_path']
  rows.extend(_article(a,name,binding['files'][name]) for a in record['payload'].get('articles',[]))
 return {'schema_version':'v5.m04_material_references.v1','archive_binding':binding,'articles':rows,'out_of_scope_record_errors':outside,'original_reader':{'source_capsule_sha256':checked['source_capsule_sha256'],'article_v2_source_sha256':checked['article_v2_source_sha256']},**SAFETY}

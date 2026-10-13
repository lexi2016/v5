"""V5 research GET bridge. No V4 fallback, producer execution, or data writes."""
from datetime import datetime
import hashlib,json,os,re,subprocess,stat
from pathlib import Path
LANE='/api/v5/research/lane'
WECHAT='/api/v5/research/wechat/materials'
ROUTES=(LANE,WECHAT)
KEY='m04_research_lane_binding'
LIMIT=16*1024*1024
FLAGS=dict(production_allowed=False,buy_gate_updated=False,orders_sent=False)

def query_date(query):
 if not isinstance(query,dict) or set(query) not in (set(),{'research_date'}):raise ValueError('RESEARCH_QUERY')
 date=query.get('research_date','')
 if date:
  if not isinstance(date,str) or not re.fullmatch('[0-9]{8}',date):raise ValueError('RESEARCH_DATE')
  if datetime.strptime(date,'%Y%m%d').strftime('%Y%m%d')!=date:raise ValueError('RESEARCH_DATE')
 elif query:raise ValueError('RESEARCH_DATE')
 return date

def _absolute(value):
 if not isinstance(value,str):raise ValueError('RESEARCH_PATH')
 p=Path(value)
 if not p.is_absolute() or '..' in p.parts or any(x.is_symlink() for x in (p,*p.parents)):raise ValueError('RESEARCH_PATH')
 return p

def validate_binding(config):
 b=config.get(KEY)
 if b is None:return
 if config.get('module_id')!='source_bundle' or LANE not in config.get('routes',[]):raise ValueError('RESEARCH_CONFIG')
 if not isinstance(b,dict) or set(b)!={'package_root','package_manifest_sha256','archive_binding','python_executable'}:raise ValueError('RESEARCH_BINDING')
 _absolute(b['package_root']);_absolute(b['python_executable'])
 if not re.fullmatch('[0-9a-f]{64}',str(b['package_manifest_sha256'])):raise ValueError('RESEARCH_PACKAGE_PIN')
 a=b['archive_binding']
 if not isinstance(a,dict) or set(a)!={'root','files'} or not isinstance(a['files'],dict):raise ValueError('RESEARCH_ARCHIVE_BINDING')
 _absolute(a['root'])

def validate_payload(value,query):
 date=query_date(query)
 if not isinstance(value,dict) or value.get('schema_version')!='v3_5.research_lane.v1':raise ValueError('RESEARCH_SCHEMA')
 if value.get('endpoint_mode')!=('EXACT' if date else 'LATEST'):raise ValueError('RESEARCH_MODE')
 if date and value.get('research_date')!=date:raise ValueError('RESEARCH_DATE_MISMATCH')
 actual=value.get('research_date')
 if actual:query_date({'research_date':actual})
 elif value.get('status')!='NOT_MATERIALIZED':raise ValueError('RESEARCH_DATE_MISSING')
 if value.get('status') not in ('READY','LIVE_HOURLY','LIVE_PERIPHERAL_ONLY','NOT_MATERIALIZED'):raise ValueError('RESEARCH_STATUS')
 if value.get('write_policy')!='read_only' or value.get('recommendation_status')!='RESEARCH_ONLY':raise ValueError('RESEARCH_READ_ONLY')
 if any(value.get(k) is not False for k in FLAGS):raise ValueError('RESEARCH_SAFETY')
 if not isinstance(value.get('cannot_confirm'),list) or any(not isinstance(x,str) for x in value['cannot_confirm']):raise ValueError('RESEARCH_GAPS')
 return value

def _lane(config,query):
 date=query_date(query);b=config.get(KEY)
 if b is None:return dict(schema_version='v3_5.research_lane.v1',endpoint_mode='EXACT' if date else 'LATEST',research_date=date,status='NOT_MATERIALIZED',reason='V5_M04_RESEARCH_BINDING_NOT_CONFIGURED',cannot_confirm=['V5_M04_RESEARCH_BINDING_NOT_CONFIGURED'],write_policy='read_only',recommendation_status='RESEARCH_ONLY',**FLAGS)
 validate_binding(config)
 package=_absolute(b['package_root']);manifest=(package/'RELEASE.json').read_bytes()
 if hashlib.sha256(manifest).hexdigest()!=b['package_manifest_sha256']:raise ValueError('RESEARCH_PACKAGE_PIN')
 files=json.loads(manifest).get('files')
 if not isinstance(files,dict) or not {'launch.py','research_lane.py','capture_runtime.py'}<=set(files):raise ValueError('RESEARCH_PACKAGE_FILES')
 for member in package.rglob('*'):
  relative=str(member.relative_to(package))
  if member.is_symlink():raise ValueError('RESEARCH_PACKAGE_SYMLINK')
  if member.suffix=='.pyc' or (member.suffix in ('.py','.so','.pyd','.dylib') and relative not in files):raise ValueError('RESEARCH_PACKAGE_UNPINNED_CODE:'+relative)
 for name,digest in files.items():
  relative=Path(name)
  if relative.is_absolute() or '..' in relative.parts:raise ValueError('RESEARCH_PACKAGE_PATH')
  target=_absolute(str(package/relative))
  if not stat.S_ISREG(target.stat().st_mode) or target.stat().st_size>64*1024*1024:raise ValueError('RESEARCH_PACKAGE_FILE_TYPE')
  if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('RESEARCH_PACKAGE_BYTES:'+name)
 command=[b['python_executable'],'-I','-B',str(package/'launch.py'),'lane']
 if date:command.extend(['--research-date',date])
 try:
  result=subprocess.run(command,input=json.dumps(b['archive_binding']).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,env={k:v for k,v in os.environ.items() if not k.startswith(('V4_','V35_'))})
 except subprocess.TimeoutExpired as exc:raise TimeoutError('RESEARCH_READER_TIMEOUT') from exc
 if result.returncode or len(result.stdout)>LIMIT:raise ValueError('RESEARCH_READER_REJECTED')
 if (package/'RELEASE.json').read_bytes()!=manifest:raise ValueError('RESEARCH_PACKAGE_CHANGED')
 return validate_payload(json.loads(result.stdout),query)

def _wechat(query):
 if set(query)-{'date','date_basis','q','limit','cursor'}:raise ValueError('WECHAT_QUERY')
 if query.get('cursor'):raise ValueError('WECHAT_NOT_CONFIGURED_CURSOR')
 date=query.get('date') or None
 if date:query_date({'research_date':date})
 basis=query.get('date_basis','article')
 if basis not in ('article','received'):raise ValueError('WECHAT_DATE_BASIS')
 limit=int(query.get('limit','20'))
 if not 1<=limit<=100 or len(query.get('q',''))>512:raise ValueError('WECHAT_QUERY')
 return dict(schema_version='v4.wechat_materials.stage_a.v1',status='NOT_CONFIGURED',query=dict(date=date,date_basis=basis,q=query.get('q','').strip(),limit=limit),timezone='Asia/Shanghai',items=[],total=0,returned=0,next_cursor=None,index_revision=None,cannot_confirm=['V5_WECHAT_INDEX_NOT_CONFIGURED'],RESEARCH_ONLY=True,WATCH_ONLY=True,NO_BUY_GATE=True,**FLAGS)

def response(config,path,query):
 if path==LANE:return 200,validate_payload(_lane(config,query),query)
 if path==WECHAT:return 200,_wechat(query)
 raise ValueError('RESEARCH_ROUTE')

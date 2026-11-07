"""Date-bound local evening exports. No source collection, freeze authority or sending."""
import ast,csv,datetime as dt,hashlib,io,json,os,re,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
LEGACY=HERE.parent/'evening_delivery_bundle_v2_20261107'
BUNDLE_SHA='38db71a2c56be47cf14f4ba3d451c35b1138f82da8a77d53a4c1dc09ca5fda7a'
SAFEIO_SHA='facce7970f4919034d62e59dde8375e94d7a6a165de214f2e5178dbb5615fff5'
# Only separately reviewed owner bindings belong here; callers cannot provide paths/gates.
REGISTRY={}
def sha(b):return hashlib.sha256(b).hexdigest()
def helpers():
 raw=(LEGACY/'safeio.py').read_bytes()
 if sha(raw)!=SAFEIO_SHA:raise ValueError('SAFEIO_VERSION')
 m=types.ModuleType('evening_safeio');m.__file__=str(LEGACY/'safeio.py');exec(compile(raw,m.__file__,'exec'),m.__dict__)
 raw=m.local_bytes(LEGACY,'bundle.py')
 if sha(raw)!=BUNDLE_SHA:raise ValueError('BUNDLE_VERSION')
 tree=ast.parse(raw);names={'cell','render','canonical','sha'}
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 ns={'csv':csv,'dt':dt,'hashlib':hashlib,'io':io,'json':json,'re':re,'safeio':m,'GROUPS':('original','nav_smallk','nav_pullback','nav_breakout'),'STATES':('TRUE','FALSE','UNKNOWN')}
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'pinned_original_renderer','exec'),ns)
 return m,ns['render']
def run(stage,registration_id,package_id=None):
 if stage not in ('1830','1850','1900'):raise ValueError('STAGE')
 if registration_id not in REGISTRY:return {'status':'BLOCKED','reason':'NO_REVIEWED_OWNER_BINDING','stage':stage,'natural_verified':False,'sent':False}
 cfg=REGISTRY[registration_id];s,render=helpers()
 # The original owner must supply a lock/resource/source-approved context. No default bypass.
 with cfg['owner_context']():
  def checked(pin):
   raw=s.local_bytes(cfg['input_root'],pin['path'])
   if sha(raw)!=pin['sha256'] or len(raw)!=pin['bytes']:raise ValueError('INPUT_CHANGED')
   return json.loads(raw)
  d=checked(cfg['data']);ad=checked(cfg['admission'])
  date=cfg['data_date'];obs=cfg['observation_date']
  for value in (date,obs):
   if dt.datetime.strptime(value,'%Y%m%d').strftime('%Y%m%d')!=value:raise ValueError('DATE')
  if obs<=date or d['source_date']!=date or d['calculation_date']!=date or d['observation_date']!=obs:raise ValueError('DATE_BINDING')
  if d['scope_count']!=cfg['scope_count']:raise ValueError('SCOPE_BINDING')
  if ad.get('status')!='PASS_RESEARCH_MERGE_DISPLAY_ONLY' or ad.get('production_allowed') is not False or ad.get('research_display_allowed') is not True:raise ValueError('ADMISSION')
  if [d['counts'][g]['after_risk']['TRUE'] for g in ('original','nav_smallk','nav_pullback','nav_breakout')]!=ad['group_true'] or any(d[k]!=ad[k] for k in ('scope_count','dedup_selected','dedup_pending')):raise ValueError('ADMISSION_COUNTS')
  payloads=render(d)
  payloads['research_prompt.txt']=('请仅对 selected.csv 名单补公告及基本面证据，保留完整代码、来源日期与 UNKNOWN；不得将数值候选当买入资格。资料日期 '+date+'；观察日期 '+obs+'。不改名单、不执行交易。\n').encode()
  manifest={'schema':'EVENING_DATE_BOUND_EXPORT_V1','registration_id':registration_id,'binding_version':cfg['binding_version'],'data_date':date,'observation_date':obs,'inputs':[cfg['data'],cfg['admission']],'code_sha256':sha(s.local_bytes(HERE,'execution.py')),'renderer_sha256':BUNDLE_SHA,'safeio_sha256':SAFEIO_SHA,'files':{n:{'sha256':sha(b),'bytes':len(b)} for n,b in payloads.items()},'formal_freeze':False,'sent':False,'natural_verified':False,'business_accepted':False}
  raw=s.canonical(manifest);key=sha(raw)
  if stage!='1830' and package_id!=key:raise ValueError('PACKAGE_VERSION_REQUIRES_PREPARE')
  root=s.directory_fd(cfg['output_root'],create=stage=='1830');child=None;reused=True
  try:
   if stage=='1830':
    try:os.mkdir(key,mode=0o700,dir_fd=root);reused=False
    except FileExistsError:pass
   child=os.open(key,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=root)
   expected={**payloads,'manifest.json':raw}
   if not reused:
    for name,content in expected.items():s.write_at(child,name,content)
    os.fsync(child);os.fsync(root)
   for name,content in expected.items():
    if s.read_at(child,name)!=content:raise ValueError('OUTPUT_CHANGED_OR_INCOMPLETE')
  finally:
   if child is not None:os.close(child)
   os.close(root)
  return {'status':'LOCAL_EXPORT_VERIFIED','stage':stage,'package_id':key,'path':str(Path(cfg['output_root'])/key),'data_date':date,'observation_date':obs,'reused':reused,'byte_readback':'PASS','natural_verified':False,'formal_freeze':False,'sent':False,'uploaded':False,'business_accepted':False,'trigger_source':'MANUAL_OR_CALLER_UNKNOWN_NOT_NATURAL_PROOF'}

"""Public-safe adapter only; approved original dependency closure is not included."""
import sys,pathlib,re,hashlib,json,fcntl,threading,time,os,datetime,shutil
from urllib.parse import urlsplit,unquote
BINDINGS=None

def identity_allowed(host,origin,port):
 hosts={'127.0.0.1:'+str(port),'localhost:'+str(port)}
 return host in hosts and (not origin or origin in {'http://'+x for x in hosts})

def verify_binding(binding):
 if not isinstance(binding,dict):raise ValueError('NO_APPROVED_PRIVATE_BINDING')
 for key in ('root','business_date','selection_version','catalog_version','pins'):
  if not binding.get(key):raise ValueError('INCOMPLETE_PRIVATE_BINDING')
 date=binding['business_date']
 try:valid=datetime.datetime.strptime(date,'%Y%m%d').strftime('%Y%m%d')==date
 except (TypeError,ValueError):valid=False
 if not valid or any(not isinstance(binding[k],str) or not re.fullmatch(r'[A-Za-z0-9_-]+',binding[k]) for k in ('selection_version','catalog_version')):raise ValueError('BINDING_IDENTITY')
 root=pathlib.Path(binding['root'])
 if not root.is_absolute() or root.is_symlink() or not root.is_dir():raise ValueError('BINDING_ROOT')
 pins=binding['pins']
 required={'serve_workbench.py','catalog_api.py','node_results_api.py','local/public/research-system/index.html','local/public/research-system/timeline-view.mjs','local/public/research-system/shared-par-store.mjs','local/public/research-system/workbench.css','local/public/research-system/timeline.css'}
 if not isinstance(pins,dict) or not required.issubset(pins):raise ValueError('INCOMPLETE_DEPENDENCY_PINS')
 # Exact entire closure required before imports, including transitive Python/static/data files.
 actual=set()
 for path in root.rglob('*'):
  if path.is_symlink():raise ValueError('SYMLINK_REJECTED')
  if path.is_file():actual.add(str(path.relative_to(root)))
 if actual!=set(pins):raise ValueError('UNPINNED_DEPENDENCY_CLOSURE')
 for name,pin in pins.items():
  path=root/name
  if not path.resolve().is_relative_to(root.resolve()) or not isinstance(pin,dict) or type(pin.get('bytes')) is not int or pin['bytes']<0:raise ValueError('PIN_DESCRIPTOR')
  raw=path.read_bytes()
  if len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin.get('sha256'):raise ValueError('SOURCE_PIN_CHANGED')
 return root

def resource_check(directory):
 available=None
 for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
  if line.startswith('MemAvailable:'):available=int(line.split()[1])*1024
 if available is None:raise ValueError('RESOURCE_MEMORY_UNKNOWN')
 limit=pathlib.Path('/sys/fs/cgroup/memory.max');current=pathlib.Path('/sys/fs/cgroup/memory.current')
 if limit.exists() and current.exists() and limit.read_text().strip()!='max':available=min(available,int(limit.read_text())-int(current.read_text()))
 if available<1024**3:raise ValueError('RESOURCE_MEMORY_HEADROOM')
 if shutil.disk_usage(directory).free<256*1024**2:raise ValueError('RESOURCE_DISK_HEADROOM')

def prepare(binding):
 C=verify_binding(binding)
 # Fresh process only: do not reuse an unrelated import identity.
 if any(x in sys.modules for x in ('serve_workbench','catalog_api','node_results_api')):raise ValueError('DEPENDENCY_ALREADY_LOADED')
 sys.dont_write_bytecode=True;sys.path.insert(0,str(C))
 from serve_workbench import WorkbenchHandler,WorkbenchServer,ResourceGate
 from catalog_api import CatalogService
 from node_results_api import NodeResultsService
 business_date=binding['business_date'];selection_version=binding['selection_version'];catalog_version=binding['catalog_version']
 PUBLIC=C/'local/public';RS=PUBLIC/'research-system'
 # Reuse exact original timeline shell and modules, not a replacement dashboard.
 s=(RS/'index.html').read_text();aside=s[s.index('<aside id="workflowDrawer"'):s.index('</aside>',s.index('<aside id="workflowDrawer"'))+8]
 html=('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>V11.8 隔离轻量模块验收</title><link rel="stylesheet" href="./workbench.css"><link rel="stylesheet" href="./timeline.css"><body><h1>V11.8 原节点模块 · 隔离轻量验收</h1><p>历史业务日{business_date}。只验节点展示和历史资料读取，不是现役切换。K线、训练、采集、冻结、送达均禁用；完整启动4.25GiB门未改。自然触发统一待验。</p><label>股票资料日<input id="date" value="{business_date}" readonly></label><nav id="stageTimeline"></nav>'''+aside+'<script type="module" src="./light-preview.mjs"></script></body></html>').encode()
 js='''import {mountTimeline} from './timeline-view.mjs';
 import {createSharedParStore} from './shared-par-store.mjs';
 const timeline=mountTimeline({document,collapsible:false,businessDate:'{business_date}',sharedPar:{store:createSharedParStore(),getInput:()=>({sourceDate:'{business_date}',selectionVersion:'{selection_version}'}),catalogLoader:async input=>{const r=await fetch('/api/par/catalog?date='+input.sourceDate+'&version='+input.selectionVersion,{cache:'no-store',redirect:'error'});if(!r.ok)throw Error('CATALOG');const c=await r.json();if(c.schema!=='PAR_UNIFIED_METADATA_SUMMARY_V1'||c.source_date!==input.sourceDate||c.selection_version!=='{catalog_version}'||c.no_buy!==true||c.production_allowed!==false)throw Error('CATALOG_BINDING');return c;},openLane:()=>{}}});
 await timeline.refresh();
 for(const b of document.querySelectorAll('button'))if(b.textContent.startsWith('打开原')){b.disabled=true;b.title='隔离轻量验收不加载K线或其他业务模块';}
 '''.encode()
 html=html.replace(b'{business_date}',business_date.encode())
 js=js.replace(b'{business_date}',business_date.encode()).replace(b'{selection_version}',selection_version.encode()).replace(b'{catalog_version}',catalog_version.encode())
 # Explicit dependency graph only; retained data use existing pinned readers.
 allowed=set();todo=['timeline-view.mjs','shared-par-store.mjs']
 while todo:
  name=todo.pop()
  if name in allowed:continue
  allowed.add(name);text=(RS/name).read_text()
  todo.extend(x.split('?')[0][2:] for x in re.findall(r"from\s*['\"]([^'\"]+)['\"]",text) if x.startswith('./') and x.split('?')[0][2:] not in allowed)
 allowed.update(['workbench.css','timeline.css'])
 for folder in ['timeline-data','par-screen-data']:
  for p in (RS/folder).rglob('*'):
   if p.is_file():allowed.add(str(p.relative_to(RS)))
 class Preview(WorkbenchHandler):
  def do_HEAD(self):self.send_error(405,'No HEAD')
  def do_GET(self):
   path=unquote(urlsplit(self.path).path)
   allowed_hosts={'127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port)}
   if not identity_allowed(self.headers.get('Host'),self.headers.get('Origin'),self.server.server_port):return self.send_error(403)
   if path in ['/research-system/','/research-system/light-preview.mjs']:
    raw=html if path.endswith('/') else js;self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8' if path.endswith('/') else 'application/javascript');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
   if path in ['/api/par/catalog','/api/node/result']:return super().do_GET()
   if path.startswith('/research-system/') and path[len('/research-system/'):] in allowed:return super().do_GET()
   return self.send_error(404,'ISOLATED_LIGHTWEIGHT_ONLY')
  def log_message(self,*args):pass

 return Preview,WorkbenchServer,ResourceGate,CatalogService,NodeResultsService

def run(binding=None,output=None):
 # No default environment, source dates, source versions or startup.
 if output is None:raise ValueError('LOCAL_LIFECYCLE_DIRECTORY_REQUIRED')
 output=pathlib.Path(output)
 if not output.is_dir() or output.is_symlink():raise ValueError('LOCAL_LIFECYCLE_DIRECTORY_REQUIRED')
 resource_check(output)
 with (output/'preview.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  Preview,Server,Gate,Catalog,Results=prepare(binding)
  Gate()()
  server=Server(('127.0.0.1',8779),Preview)
  server.catalog_service=Catalog(Gate());server.node_results_service=Results(Gate())
  (output/'START.json').write_text(json.dumps({'pid':os.getpid(),'port':8779,'started':time.time(),'scope':'partial modules only','full_gate_unchanged':True}))
  timer=threading.Timer(600,server.shutdown);timer.daemon=True;timer.start()
  try:server.serve_forever()
  finally:timer.cancel();server.server_close();(output/'STOP.json').write_text(json.dumps({'pid':os.getpid(),'stopped':time.time()}))

if __name__=='__main__':raise SystemExit('UNBOUND_PUBLIC_ADAPTER_NOT_RUNNABLE')

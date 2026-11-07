"""Thin adapter to original admitted historical reader. No server or collector start."""
import hashlib,json,pathlib,importlib.util,builtins,threading
READER_ROOT=None;CODE_PINS=None;HISTORY_DATE=None;HISTORY_SLOT=None
class IntradayHistoryService:
 def __init__(self,gate):self.gate=gate;self.lock=threading.Lock()
 def get(self,path):
  if path=='/api/intraday/current':return 409,json.dumps({'status':'BLOCKED_CURRENT_BINDING_UNKNOWN','current_rows':None,'historical_fallback_used':False,'natural_verified':False,'missing':['current-day exact frozen contract','independent review and activation receipt','current bucket and source receipts','original collector deployment binding']}).encode()
  if not isinstance(READER_ROOT,pathlib.Path) or not READER_ROOT.is_absolute() or not isinstance(CODE_PINS,dict) or not {'safeio.py','observation_api.py'}.issubset(CODE_PINS) or not isinstance(HISTORY_DATE,str) or not HISTORY_DATE or not isinstance(HISTORY_SLOT,str) or not HISTORY_SLOT:raise ValueError('NO_APPROVED_PRIVATE_BINDING')
  if path not in {'/api/intraday/history/'+HISTORY_DATE+'/'+HISTORY_SLOT,'/api/intraday/contract/'+HISTORY_DATE}:return 404,b'{"status":"UNKNOWN","error":"UNSUPPORTED_DATE_OR_BUCKET"}'
  if not self.lock.acquire(timeout=95):raise ValueError('RESOURCE_BUSY')
  try:
   if hasattr(self.gate,'start'):self.gate.start()
   self.gate();root=READER_ROOT;pins=CODE_PINS
   for name,pin in pins.items():
    relative=pathlib.Path(name);source=root/relative
    if relative.is_absolute() or '..' in relative.parts or root.is_symlink() or any((root/pathlib.Path(*relative.parts[:i])).is_symlink() for i in range(1,len(relative.parts)+1)) or not source.resolve().is_relative_to(root.resolve()):raise ValueError('SOURCE_PATH')
    raw=source.read_bytes()
    if len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('ORIGINAL_READER_CHANGED')
   def load(name,file,dependency=None):
    spec=importlib.util.spec_from_file_location(name,root/file);m=importlib.util.module_from_spec(spec)
    if dependency is not None:
     local_builtins=dict(vars(builtins))
     def dependency_import(name,*a,**kw):return dependency if name=='safeio' else builtins.__import__(name,*a,**kw)
     local_builtins['__import__']=dependency_import;m.__dict__['__builtins__']=local_builtins
    spec.loader.exec_module(m);return m
   safe=load('intraday_original_safeio','safeio.py');reader=load('intraday_original_reader','observation_api.py',safe)
   raw,input_pins=reader.load()
   if path=='/api/intraday/contract/'+HISTORY_DATE:
    pin=input_pins['daily_contract'];raw=safe.local_bytes(reader.ROOT,pin['path'])
    if len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('CONTRACT_CHANGED')
   self.gate();return 200,raw
  finally:self.lock.release()

"""Bounded, pinned SQLite index summary; original source admission unchanged."""
import hashlib,importlib.util,json,pathlib,threading
HERE=pathlib.Path(__file__).resolve().parent
PRIVATE_ROOT=None;PRIVATE_BINDINGS=None
class CatalogService:
 def __init__(self,gate):self.gate=gate;self.lock=threading.Lock()
 def get(self,date,version):
  if date!='20261106' or version!='merge407':raise ValueError('CATALOG_VERSION_UNAVAILABLE')
  if not self.lock.acquire(timeout=95):raise ValueError('RESOURCE_BUSY')
  try:
   if hasattr(self.gate,'start'):self.gate.start()
   self.gate()
   if PRIVATE_ROOT is None or PRIVATE_BINDINGS is None:raise ValueError('PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING')
   root=PRIVATE_ROOT;pins=PRIVATE_BINDINGS
   for name,pin in pins.items():
    path=root/name
    if path.is_symlink() or path.stat().st_size!=pin['bytes']:raise ValueError('CATALOG_PIN')
    with path.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
    if actual!=pin['sha256']:raise ValueError('CATALOG_PIN')
   spec=importlib.util.spec_from_file_location('par_unified_catalog',root/'database.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
   result=module.summary(date,'MAIN_PLUS_SINA69_407');result['database_sha256']=pins['catalog.sqlite3']['sha256'];self.gate();return result
  finally:self.lock.release()

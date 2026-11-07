"""Registered local 09:15 recorded-observation receipt. No capture or admission."""
import hashlib, json, types, datetime as dt
from pathlib import Path
REGISTRY = {}  # Reviewed private registrations only; HTTP arguments cannot populate this.
ORIGINAL = Path(__file__).resolve().parent.parent/'remaining_four_dispatch_20261107'
PINS = {'safeio.py':'facce7970f4919034d62e59dde8375e94d7a6a165de214f2e5178dbb5615fff5', 'a0915.py':'be03158ad98d050c6692f035f56e3f2bcb753f22118b6a3dbe838fc941b3433f'}
def _load():
    modules = {}
    for name in ('safeio.py','a0915.py'):
        raw = (ORIGINAL/name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != PINS[name]: raise ValueError('ORIGINAL_PIN_CHANGED')
        source = raw.decode()
        module = types.ModuleType('pinned_'+name[:-3]); module.__file__ = str(ORIGINAL/name)
        if name == 'a0915.py':
            if source.count('import safeio\n') != 1: raise ValueError('IMPORT_CONTRACT_CHANGED')
            source = source.replace('import safeio\n','')
            module.safeio = modules['safeio.py']
        exec(compile(source,str(ORIGINAL/name),'exec'),module.__dict__)
        modules[name] = module
    return modules['safeio.py'], modules['a0915.py']
def dispatch(run_id, environment_id):
    key = (run_id, environment_id)
    if key not in REGISTRY:
        return {'status':'BLOCKED_UNREGISTERED', 'production_allowed':False, 'natural_verified':False, 'source_calls':0}
    r = REGISTRY[key]
    if r['run_id'] != run_id or r['environment_id'] != environment_id: raise ValueError('REGISTRATION_IDENTITY')
    if not callable(r['gate']) or not callable(r['owner_context']): raise ValueError('ORIGINAL_GATES_REQUIRED')
    r['gate']()
    # Context is the original owner lock contract, never constructed from browser fields.
    with r['owner_context']():
        safeio, reader = _load()
        result = reader.read_recorded(r['input_root'],r['input_relative'],r['input_sha256'],r['target_date'],r['gate'])
        raw = safeio.local_bytes(r['input_root'],r['input_relative'])
        if hashlib.sha256(raw).hexdigest()!=r['input_sha256']: raise ValueError('INPUT_CHANGED')
        source = json.loads(raw)
        if source['scope'] != list(r['scope']): raise ValueError('REGISTERED_SCOPE_MISMATCH')
        report = {'schema':'A0915_LOCAL_RECEIPT_V1', 'run_id':run_id, 'environment_id':environment_id,
                  'input_sha256':r['input_sha256'],'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'dependency_pins':PINS,'result':result, 'source_calls':0,'delivery_status':'NOT_SENT',
                  'source_admission':'UNKNOWN','production_allowed':False,'business_accepted':False,'natural_verified':False}
        report['identity']=safeio.sha(safeio.canonical(report))
        report['observed_at']=dt.datetime.now(dt.timezone.utc).isoformat()
        r['gate']()
        saved=safeio.freeze(r['output'],report)
        return {'status':'RECORDED_RECEIPT_SAVED_BUSINESS_BLOCKED','report':report,'saved':saved,
                'production_allowed':False,'natural_verified':False,'source_calls':0}

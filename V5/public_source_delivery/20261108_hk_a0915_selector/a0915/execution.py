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
# Explicit replacement contract, not recovery or alteration of the original reader pin.
TEXT_V3_PINS = {
    'safeio': 'facce7970f4919034d62e59dde8375e94d7a6a165de214f2e5178dbb5615fff5',
    'reader': 'd2a62605fc7eafa3f0d62af6964601fe327981af954ed0efe73ecaf37161f12e'}
def _load_text_v3():
    import os, stat
    public = Path(__file__).resolve().parents[2]
    repo = public.parent.parent
    paths = {'safeio':public/'handoff/timeline_material_pack_v2_20261107/material_pack.py',
             'reader':repo/'handoff/reconstruction_candidates_20261108/a0915_text_v3/recorded.py'}
    modules = {}
    for name, path in paths.items():
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or not 0<info.st_size<=131072:raise ValueError('TEXT_V3_CODE_SIZE')
            raw=stream.read(131073)
        if len(raw)!=info.st_size or hashlib.sha256(raw).hexdigest()!=TEXT_V3_PINS[name]:raise ValueError('TEXT_V3_CODE_PIN')
        module=types.ModuleType('new_text_v3_'+name);module.__file__=str(path)
        exec(compile(raw,str(path),'exec'),module.__dict__);modules[name]=module
    return modules['safeio'],modules['reader']

def _text_v3_receipt(r,run_id,environment_id):
    # Invoked only inside dispatch's existing original owner context.
    if r.get('domain')!='synthetic' or r.get('natural') is not False or r.get('trigger') not in ('SYNTHETIC_TEST','MANUAL_RECORDED_REPLAY'):
        raise ValueError('TEXT_V3_ISOLATED_ONLY')
    safeio,reader=_load_text_v3()
    reference=r['text_contract']
    if type(reference)is not dict or set(reference)!={'path','sha256','bytes'} or type(reference['bytes'])is not int:raise ValueError('TEXT_V3_CONTRACT_REFERENCE')
    policy_raw=safeio.local_bytes(r['input_root'],reference['path'])
    if len(policy_raw)!=reference['bytes'] or safeio.sha(policy_raw)!=reference['sha256']:raise ValueError('TEXT_V3_CONTRACT_CHANGED')
    policy=reader.strict(policy_raw)
    if type(policy)is not dict or policy.get('target_date')!=r['target_date'] or policy.get('scope')!=list(r['scope']) or policy.get('input_sha256')!=r['input_sha256']:
        raise ValueError('TEXT_V3_REGISTERED_BINDING')
    raw=safeio.local_bytes(r['input_root'],r['input_relative'])
    result=reader.read_recorded_bytes(raw,policy)
    if r['trigger']=='SYNTHETIC_TEST' and result['recorded_input']['data_kind']!='SYNTHETIC_TEST':raise ValueError('TEXT_V3_DATA_KIND_BINDING')
    report={'schema':'A0915_TEXT_V3_LOCAL_RECEIPT_V1','contract_kind':'NEW_CALLER_POLICY_NOT_ORIGINAL_READER',
            'run_id':run_id,'environment_id':environment_id,'domain':'synthetic','trigger':r['trigger'],
            'input_sha256':r['input_sha256'],'text_contract':reference,
            'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'dependency_pins':TEXT_V3_PINS,
            'result':result,'source_calls':0,'delivery_status':'NOT_SENT','source_admission':'UNKNOWN',
            'production_allowed':False,'business_accepted':False,'natural_verified':False}
    report['identity']=safeio.sha(safeio.canonical(report));report['observed_at']=dt.datetime.now(dt.timezone.utc).isoformat()
    r['gate']()
    if safeio.local_bytes(r['input_root'],r['input_relative'])!=raw or safeio.local_bytes(r['input_root'],reference['path'])!=policy_raw:raise ValueError('TEXT_V3_INPUT_CHANGED_BEFORE_SAVE')
    saved=safeio.freeze(r['output'],report)
    return {'status':'TEXT_V3_RECEIPT_SAVED_BUSINESS_BLOCKED','report':report,'saved':saved,
            'production_allowed':False,'natural_verified':False,'source_calls':0}

def dispatch(run_id, environment_id):
    key = (run_id, environment_id)
    if key not in REGISTRY:
        return {'status':'BLOCKED_UNREGISTERED', 'production_allowed':False, 'natural_verified':False, 'source_calls':0}
    r = REGISTRY[key]
    mode=r.get('reader_mode','ORIGINAL')
    if mode not in ('ORIGINAL','TEXT_V3_ISOLATED'):raise ValueError('READER_MODE')
    if r['run_id'] != run_id or r['environment_id'] != environment_id: raise ValueError('REGISTRATION_IDENTITY')
    if not callable(r['gate']) or not callable(r['owner_context']): raise ValueError('ORIGINAL_GATES_REQUIRED')
    r['gate']()
    # Context is the original owner lock contract, never constructed from browser fields.
    with r['owner_context']():
        if mode=='TEXT_V3_ISOLATED':return _text_v3_receipt(r,run_id,environment_id)
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

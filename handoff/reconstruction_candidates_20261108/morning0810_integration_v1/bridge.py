"""Synthetic-only, no-send integration experiment. NOT a production registration.
Existing merged registered.py is intentionally untouched and still blocks 08:10.
"""
import hashlib
from pathlib import Path
import types
REGISTRY={}
IDENTITY_KEYS=('task_id','node','environment_id','binding_version','authorization_ref','channel','destination','input_sha256','code_version','data_date','run_id','output_root')
DEPENDENCY_PINS = {'outbox.py': '50a7fee95e2b24911ee3c205b5e402316a764e7d7d1ece2a634bb78552ac5891', 'bundle_candidate.py': '0eb3bb66f5589dc8a48faf6484ff675f8e990c7addf2e8cf7aa46056885c2121'}  # populated in this isolated candidate, never supplied by an input

def _load_pinned(name):
    path=Path(__file__).resolve().with_name(name)
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=DEPENDENCY_PINS[name]:
        raise ValueError('DEPENDENCY_CHANGED')
    module=types.ModuleType('isolated_'+name[:-3])
    module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module

bundle_candidate=_load_pinned('bundle_candidate.py')
outbox=_load_pinned('outbox.py')

def prepare(key,raws):
    for name,module in (("outbox.py",outbox),("bundle_candidate.py",bundle_candidate)):
        if Path(module.__file__).resolve()!=Path(__file__).resolve().with_name(name):
            raise ValueError("MODULE_ORIGIN_CHANGED")
    for name,digest in DEPENDENCY_PINS.items():
        if hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()!=digest:
            raise ValueError('DEPENDENCY_CHANGED')
    if key not in REGISTRY:
        raise ValueError('NO_CANDIDATE_BINDING')
    binding=REGISTRY[key]
    if binding.get('domain')!='synthetic' or binding.get('review')!='SYNTHETIC_REVIEW_ONLY':
        raise ValueError('UNREGISTERED_PRODUCTION_BLOCKED')
    pins=binding['pins']
    if set(raws)!=set(pins):
        raise ValueError('INPUT_SET_CHANGED')
    config=outbox._config(binding['outbox_registration'])
    if config['node']!='0810' or {k:config[k] for k in IDENTITY_KEYS}!=binding['outbox_identity']:
        raise ValueError('OUTBOX_BINDING_CHANGED')
    if config['input_sha256']!=outbox.sha(outbox.canonical(pins)) or config['data_date']!=binding['business_date']:
        raise ValueError('OUTBOX_INPUT_BINDING_CHANGED')
    bundle=bundle_candidate.assemble(raws,pins,binding['business_date'],binding['cutoff'])
    # Reuse the original durable outbox PREPARED path ONLY. Never attempt/reconcile.
    prepared=outbox.prepare(binding['outbox_registration'],outbox.canonical(bundle).decode())
    return {'status':'SYNTHETIC_LOCAL_PREPARATION_ONLY','bundle':bundle,'outbox':prepared,
            'business_accepted':False,'natural_trigger_verified':False,'delivery_verified':False}

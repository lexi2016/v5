"""Pinned M07 code and exact-reference process invocation; no automatic jobs."""
import hashlib,json,os,re,subprocess
from pathlib import Path
from .composition import no_symlinks
from .contracts import exact_keys,trade_date,sha
from .digests import MAX_JSON_BYTES,canonical_bytes
BASE=Path(__file__).resolve().parents[2]
OWNER_COMMIT='e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31'
MANIFEST=BASE/'contracts/m07_runtime.json'
MANIFEST_SHA256='1e3302422d31a595eab83552efe3ba201f56f288f7072288f3e0067978e067c4'
STAGES=('STAGE_0925','STAGE_0930_0935','STAGE_0935_0940','STAGE_0940_0945','STAGE_0945_1030','STAGE_1300_1315','STAGE_1445_1500')
FLAGS=dict(natural_verified=False,formal_eligibility_verified=False,production_allowed=False,buy_gate_updated=False,orders_sent=False)


def raw(path):
    from .module_api import _open_directory,_read_regular
    import stat
    path=no_symlinks(Path(path));directory=_open_directory(path.parent)
    try:fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
    finally:os.close(directory)
    try:return _read_regular(fd,MAX_JSON_BYTES)
    finally:os.close(fd)


def owner_root():
    content=raw(MANIFEST)
    if hashlib.sha256(content).hexdigest()!=MANIFEST_SHA256:raise ValueError('M07_RUNTIME_MANIFEST')
    manifest=json.loads(content)
    if manifest.get('source_commit')!=OWNER_COMMIT:raise ValueError('M07_OWNER_COMMIT')
    for entry in manifest['entries']:
        relative=Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts or not (entry['path'].startswith('source_owners/m07/') or entry['path']=='src/v5_shadow/m07_owner_worker.py'):raise ValueError('M07_RUNTIME_PATH')
        value=raw(BASE/relative)
        if len(value)!=entry['bytes'] or hashlib.sha256(value).hexdigest()!=entry['sha256']:raise ValueError('M07_RUNTIME_BYTES')
    return no_symlinks(BASE/'source_owners/m07')


def validate_reference(reference):
    exact_keys(reference,('generation','target_date','stage_id','run_id','artifact_sha256','manifest_sha256','receipt_sha256'))
    trade_date(reference['target_date'])
    if reference['stage_id'] not in STAGES:raise ValueError('M07_A_STAGE_REQUIRED')
    for field in ('generation','artifact_sha256','manifest_sha256','receipt_sha256'):sha(reference[field])
    if not isinstance(reference['run_id'],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,255}',reference['run_id']):raise ValueError('M07_RUN_ID')


def validate_paths(binding):
    for key in ('output_root','python_executable'):
        value=binding[key]
        if not isinstance(value,str) or not Path(value).is_absolute() or '..' in Path(value).parts:raise ValueError('M07_ABSOLUTE_BINDING_PATH')
    sha(binding['python_sha256'])


def _python(binding):
    # A venv's interpreter is commonly a symlink. Pin the actual target bytes,
    # never resolve away the venv invocation path or modify its environment.
    target=Path(binding['python_executable']).resolve(strict=True)
    if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=binding['python_sha256']:raise ValueError('M07_PYTHON_IDENTITY')
    return binding['python_executable']


def invoke(binding,operation,payload):
    validate_paths(binding);owner=owner_root();python=_python(binding)
    message=dict(operation=operation,output_root=binding['output_root'],**payload)
    try:
        proc=subprocess.run([python,'-I','-B',str(BASE/'src/v5_shadow/m07_owner_worker.py'),str(owner)],input=canonical_bytes(message),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=150,cwd=str(BASE.parent),env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'})
    except subprocess.TimeoutExpired as error:raise ValueError('M07_PROCESS_OUTCOME_UNKNOWN_NO_RETRY') from error
    if proc.returncode or len(proc.stdout)>MAX_JSON_BYTES:raise ValueError('M07_ORIGINAL_READBACK_OR_RUN_REJECTED')
    try:result=json.loads(proc.stdout)
    except (ValueError,UnicodeError) as error:raise ValueError('M07_WORKER_JSON') from error
    owner_root();_python(binding)
    return result


def read_reference(binding,reference):
    validate_reference(reference)
    result=invoke(binding,'read',dict(reference=reference))
    if not isinstance(result,dict) or any(result.get(k) is not v for k,v in FLAGS.items()):raise ValueError('M07_READBACK_FLAGS')
    for key in ('generation','artifact_sha256','manifest_sha256','receipt_sha256'):
        if result.get(key)!=reference[key]:raise ValueError('M07_READBACK_REFERENCE')
    selection=result.get('selection',{})
    if (selection.get('trade_date')!=reference['target_date'] or selection.get('stage_id')!=reference['stage_id'] or selection.get('run_id')!=reference['run_id'] or selection.get('market')!='A_SHARE' or any(selection.get(k) is not False for k in ('production_allowed','buy_gate_updated','orders_sent'))):raise ValueError('M07_READBACK_IDENTITY')
    return result

"""Read-only registered M07 source handoff; not collector, replay or activation.
Only a separately reviewed owner may register a completed recording descriptor.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json,re,subprocess,sys
HERE=Path(__file__).resolve().parent
M07=HERE.parents[1]/'source_owners/m07'
ENTRY_SHA='01c791dee6547e5e1a54ef3c412ac3102dfcafdf7e78be34c702b053f6fb5791'
REGISTRY={}
def encode(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(encode(x)).hexdigest()
@dataclass(frozen=True)
class Binding:
 job_id:str
 environment_id:str
 source_id:str
 scope:tuple
 scope_sha256:str
 source_review_sha256:str
 owner_review_sha256:str
 descriptor:dict
 gate:object
 lock:object
 synthetic:bool=False

def verify_registered_recording(b):
 if not b.job_id or not b.environment_id or not b.source_id:raise ValueError('IDENTITY_REQUIRED')
 if type(b.synthetic) is not bool:raise ValueError('KIND_REQUIRED')
 if not b.scope or len(set(b.scope))!=len(b.scope) or any(not re.fullmatch(r'A\.\d{6}',c) for c in b.scope):raise ValueError('SCOPE_INVALID')
 if b.scope_sha256!=digest(list(b.scope)):raise ValueError('SCOPE_SHA')
 if any(not re.fullmatch('[0-9a-f]{64}',s) for s in (b.source_review_sha256,b.owner_review_sha256)):raise ValueError('REVIEW_REQUIRED')
 if not callable(b.gate) or not callable(b.lock):raise ValueError('ORIGINAL_GATES_REQUIRED')
 request=json.loads(encode(b.descriptor))
 if set(request)!={'target_date','stage_id','cutoff','pool_source_dates','inputs','recording'}:raise ValueError('SOURCE_DESCRIPTOR_FIELDS')
 if request['stage_id'] not in ('STAGE_0925','STAGE_0930_0935'):raise ValueError('STAGE_UNSUPPORTED')
 if set(request['inputs'])!={'pool','live','research','morning'}:raise ValueError('FOUR_INPUTS_REQUIRED')
 # Source bytes must already exist. There is deliberately no provider callback.
 b.gate()
 with b.lock():
  b.gate()
  p=subprocess.run([sys.executable,'-I','-B',str(HERE/'verify_worker.py')],input=encode(request),capture_output=True,timeout=120)
  b.gate()
  if len(p.stdout)>1048576:raise ValueError('RESPONSE_LIMIT')
  try:r=json.loads(p.stdout)
  except (ValueError,UnicodeError):raise ValueError('VERIFIER_RESPONSE') from None
  if p.returncode or r.get('status')!='VERIFIED':raise ValueError(r.get('reason','VERIFIER_FAILED'))
  if r['known_synthetic'] and not b.synthetic:raise ValueError('SYNTHETIC_RELABEL_FORBIDDEN')
  if r['source_id']!=b.source_id:raise ValueError('SOURCE_IDENTITY')
  if r['pool_codes']!=sorted(b.scope):raise ValueError('SCOPE_MISMATCH')
  return dict(status='SOURCE_RECORDING_VERIFIED_ONLY',job_id=b.job_id,environment_id=b.environment_id,
   target_date=request['target_date'],stage_id=request['stage_id'],descriptor_sha256=digest(request),
   source_id=b.source_id,scope_sha256=b.scope_sha256,source_review_sha256=b.source_review_sha256,
   owner_review_sha256=b.owner_review_sha256,recording=r['recording'],rows=r['rows'],missing_symbols=r['missing_symbols'],
   data_kind='SYNTHETIC' if b.synthetic else 'RECORDED_INPUT_KIND_UNKNOWN',production_allowed=False,natural_verified=False,
   business_verified=False,orders_sent=False,source_authority='UNKNOWN',collector_executed=False)

def dispatch(job_id,environment_id):
 if (job_id,environment_id) not in REGISTRY:return dict(status='BLOCKED',reason='TRUSTED_OWNER_SOURCE_BINDING_MISSING',production_allowed=False,natural_verified=False)
 b=REGISTRY[job_id,environment_id]
 if (b.job_id,b.environment_id)!=(job_id,environment_id):raise ValueError('REGISTRY_IDENTITY')
 return verify_registered_recording(b)

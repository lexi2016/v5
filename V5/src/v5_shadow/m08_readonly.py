"""Read-only exact M08 observed imports; no selection, source or latest path."""
import hashlib,json,re,subprocess,time
from pathlib import Path
from .composition import no_symlinks
from .contracts import exact_keys,trade_date,sha
from .digests import MAX_JSON_BYTES,canonical_bytes,sha256_json
ROUTE='/api/v5/source-bundle/hk-stage-observed'
BINDING='m08_hk_stage_observed_binding'
BASE=Path(__file__).resolve().parents[2]
MANIFEST=BASE/'contracts/m08_readonly_runtime.json'
MANIFEST_SHA256='907e0dfadd79d09083fcdf589d57763ac76530e047ee8d436c24db72a7922bdd'
OWNER_COMMIT='0a9e49a088358954ce36093f6c068e694fde961f'
STAGES=('STAGE_0925','STAGE_0930_0935','STAGE_0935_0940','STAGE_0940_0945','STAGE_0945_1030','STAGE_1300_1315','STAGE_1445_1500','STAGE_1545_1555')
FLAGS=dict(research_only=True,production_allowed=False,buy_gate_updated=False,orders_sent=False,natural_verified=False,pit_verified=False,formal_admission=False,raw_input_verified=False,computation_replayed=False,market_data_authenticity_verified=False)
OBSERVED=dict(data_kind='OWNER_RESULT',evidence_mode='HISTORICAL',qualification='OBSERVED_ONLY')
def validate_reference(ref):
 exact_keys(ref,('schema_version','import_sha256','import_receipt_sha256','target_date','stage_id','market','run_id'))
 if ref['schema_version']!='v5.hk_stage_observed_reference.v1' or ref['market']!='HK_CONNECT' or ref['stage_id'] not in STAGES:raise ValueError('M08_REFERENCE_IDENTITY')
 trade_date(ref['target_date']);sha(ref['import_sha256']);sha(ref['import_receipt_sha256'])
 if not isinstance(ref['run_id'],str) or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,254}[A-Za-z0-9])?',ref['run_id']):raise ValueError('M08_REFERENCE_RUN')
 return ref

def validate_binding(config):
 binding=config.get(BINDING)
 if binding is None:return
 if config.get('module_id')!='source_bundle' or ROUTE not in config.get('routes',[]):raise ValueError('M08_ROUTE_CONFIG')
 exact_keys(binding,('recorded_root','python_executable','references'))
 for key in ('recorded_root','python_executable'):
  value=binding[key]
  if not isinstance(value,str) or not value or not Path(value).is_absolute() or '..' in Path(value).parts:raise ValueError('M08_BINDING_PATH')
 refs=binding['references']
 if not isinstance(refs,list) or len(refs)!=10:raise ValueError('M08_TEN_REFERENCES_REQUIRED')
 for ref in refs:validate_reference(ref)
 if len({(r['target_date'],r['stage_id'],r['run_id']) for r in refs})!=10 or len({r['import_sha256'] for r in refs})!=10 or {r['stage_id'] for r in refs}!=set(STAGES):raise ValueError('M08_REFERENCE_INVENTORY')
 canonical_bytes(binding)

def owner_root():
    raw=no_symlinks(MANIFEST).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA256:raise ValueError('M08_OWNER_MANIFEST_SHA')
    manifest=json.loads(raw)
    if manifest.get('source_commit')!=OWNER_COMMIT or not manifest.get('entries'):
        raise ValueError('M08_OWNER_CLOSURE_MISSING')
    for entry in manifest['entries']:
        rel=Path(entry['path'])
        if rel.is_absolute() or '..' in rel.parts or not entry['path'].startswith('source_owners/m08/'):
            raise ValueError('M08_OWNER_PATH')
        data=no_symlinks(BASE/rel).read_bytes()
        if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
            raise ValueError('M08_OWNER_BYTES_MISMATCH')
    root=no_symlinks(BASE/'source_owners/m08')
    expected={entry['path'] for entry in manifest['entries']}
    actual={str(path.relative_to(BASE)) for path in root.rglob('*') if path.is_file() or path.is_symlink()}
    if actual!=expected:raise ValueError('M08_OWNER_CLOSURE_EXTRA_FILES')
    return root



def not_configured():
 return dict(status='NOT_CONFIGURED',module_id='M08_HK_STAGE_OBSERVED',reason_codes=['M08_REFERENCES_NOT_CONFIGURED'],**FLAGS)

def read_record(config,query):
 validate_binding(config);binding=config.get(BINDING)
 if query:
  exact_keys(query,('date','stage','run_id','import_sha256'));trade_date(query['date']);sha(query['import_sha256'])
  if query['stage'] not in STAGES:raise ValueError('M08_QUERY_STAGE')
 if binding is None:
  if query:raise ValueError('M08_REFERENCE_NOT_CONFIGURED')
  return None
 root=owner_root()
 if not query:
  value=dict(schema_version='v5.hk_stage_observed_catalog.v1',module_id='M08_HK_STAGE_OBSERVED',status='CONFIGURED_REFERENCES',references=binding['references'],references_verified=False,owner_commit=OWNER_COMMIT,**OBSERVED,**FLAGS)
  source_sha=sha256_json(binding['references']);generated=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
 else:
  matches=[r for r in binding['references'] if query==dict(date=r['target_date'],stage=r['stage_id'],run_id=r['run_id'],import_sha256=r['import_sha256'])]
  if len(matches)!=1:raise ValueError('M08_UNKNOWN_REFERENCE')
  ref=matches[0];request=dict(recorded_root=binding['recorded_root'],reference=ref)
  worker=Path(__file__).with_name('m08_readonly_worker.py')
  try:proc=subprocess.run([binding['python_executable'],'-I','-B',str(worker),str(root)],input=canonical_bytes(request),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=75)
  except subprocess.TimeoutExpired as error:raise ValueError('M08_READ_TIMEOUT') from error
  if len(proc.stdout)>MAX_JSON_BYTES or proc.returncode:raise ValueError('M08_COMMITTED_REFERENCE_REJECTED')
  try:value=json.loads(proc.stdout)
  except (ValueError,UnicodeError) as error:raise ValueError('M08_READ_RESPONSE_JSON') from error
  if (not isinstance(value,dict) or value.get('schema_version')!='v5.hk_stage_observed_readonly.v1' or value.get('module_id')!='M08_HK_STAGE_OBSERVED' or value.get('owner_commit')!=OWNER_COMMIT or value.get('reference')!=ref or value.get('read_status')!='VERIFIED' or any(value.get(k) is not v for k,v in FLAGS.items()) or any(value.get(k)!=v for k,v in OBSERVED.items())):raise ValueError('M08_READ_RESPONSE_BOUNDARY')
  a=value['artifact'];p=value['provenance']
  if (a.get('trade_date')!=ref['target_date'] or a.get('stage_id')!=ref['stage_id'] or a.get('run_id')!=ref['run_id'] or a.get('market')!='HK_CONNECT' or a.get('selection_status')!=value.get('status') or value['status'] not in ('READY','READY_EMPTY','PARTIAL_WITH_ROWS','CANNOT_CONFIRM') or not isinstance(a.get('rows'),list) or len(a['rows'])>10 or a.get('selected_rows')!=len(a['rows']) or any(a.get(k) is not False for k in ('production_allowed','buy_gate_updated','orders_sent')) or p.get('captured_at') is not None or any(p.get(k)!=v for k,v in OBSERVED.items()) or any(p.get(k) is not False for k in ('natural_verified','pit_verified','formal_admission','raw_input_verified','computation_replayed','market_data_authenticity_verified')) or value.get('stage_group')!=('HK_STAGE8_SEPARATE' if ref['stage_id']==STAGES[-1] else 'HK_SEVEN_STAGE') or value.get('m10_stage_member') is not (ref['stage_id']!=STAGES[-1])):raise ValueError('M08_ORIGINAL_IDENTITY_OR_BOUNDARY')
  source_sha=ref['import_sha256'];generated=p['imported_at'];owner_root()
 record=dict(schema_version='v5.module_response.v1',module_id=config['module_id'],release_id=config['release_id'],path=ROUTE,query=query,payload=value,payload_sha256=sha256_json(value),source_input_sha256=source_sha,data_kind='OWNER_RESULT',generated_at=generated,status_code=200)
 from .module_api import _validate_record
 return _validate_record(config,record,ROUTE,query),sha256_json(record)

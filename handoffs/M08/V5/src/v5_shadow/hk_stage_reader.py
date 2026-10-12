"""Independent exact-run M08 reader. Never produces or follows latest pointers."""
import sys
from pathlib import Path
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import copy
import json
from v5_shadow.contracts import exact_keys,sha,trade_date
from v5_shadow.digests import canonical_bytes,sha256_json,MAX_JSON_BYTES
from v5_shadow.composition import no_symlinks
from v5_shadow.hk_stage_sources import SOURCE_SHA,load_owners,implementation_identity,source_bytes
from v5_shadow.hk_stage_daily import checked_root,read_json,_process,SAFETY,STAGES,validate_request


def _read(root,reference):
    exact_keys(reference,('generation_sha256','run_id','market','target_date','stage_id','artifact_sha256','manifest_sha256','receipt_sha256','product_sha256'))
    for field in ('generation_sha256','artifact_sha256','manifest_sha256','receipt_sha256','product_sha256'):sha(reference[field])
    trade_date(reference['target_date'])
    if reference['market']!='HK_CONNECT' or reference['stage_id'] not in STAGES:raise ValueError('M08_READ_IDENTITY')
    root=checked_root(root);generation=no_symlinks(root/'generations'/reference['generation_sha256'])
    product=read_json(generation/'product.json');attempt=read_json(generation/'attempt.json')
    if product.get('schema_version')!='v5.hk_stage_product.v1' or product['reference']!=reference or attempt['status']!='SUCCEEDED' or attempt['reference']!=reference:raise ValueError('M08_COMMIT_IDENTITY')
    unhashed=copy.deepcopy(product);unhashed['reference'].pop('product_sha256')
    if sha256_json(unhashed)!=reference['product_sha256']:raise ValueError('M08_PRODUCT_SHA')
    identity=attempt['identity'];provenance=product['provenance'];code=implementation_identity()
    if sha256_json(identity)!=reference['generation_sha256'] or identity['input_sha256']!=sha256_json(product['request']):raise ValueError('M08_INPUT_IDENTITY')
    if identity['source_manifest_sha256']!=SOURCE_SHA or identity['implementation_identity']!=code:raise ValueError('M08_CODE_IDENTITY')
    for key,value in identity.items():
        if provenance.get(key)!=value:raise ValueError('M08_PROVENANCE_IDENTITY')
    if provenance.get('formal_admission') is not False or provenance.get('natural_verified') is not False:raise ValueError('M08_ADMISSION_FLAGS')
    selection,contracts,calendar=load_owners()
    request=product['request']
    metadata=validate_request(request,contracts,calendar)
    expected_source=dict(request['source'],m06_run_id=request['m06']['run_id'],m06_rows_sha256=request['m06']['rows_sha256'],membership_receipt_sha256=request['m02']['receipt_sha256'])
    if (provenance.get('data_kind')!=request['data_kind'] or provenance.get('source_identity')!=expected_source
            or provenance.get('stage_contract')!=metadata or identity.get('config')!=dict(cap_limit_yi=100,mode='RETAINED_INPUT_ONLY')):
        raise ValueError('M08_PROVENANCE_REQUEST_BINDING')
    store=selection.SelectionStore(no_symlinks(generation/'owner'))
    verified=store._verify_run(reference['target_date'],reference['stage_id'],'HK_CONNECT',reference['run_id'])
    for key in ('artifact_sha256','manifest_sha256','receipt_sha256'):
        if verified[key]!=reference[key]:raise ValueError('M08_OWNER_REFERENCE_SHA')
    artifact=verified['envelope']
    if artifact!=product['artifact'] or artifact['raw_artifact_sha256']!=reference['generation_sha256']:raise ValueError('M08_OWNER_PRODUCT_MISMATCH')
    for value in (product,attempt,artifact):
        if any(value.get(k) is not False for k in SAFETY):raise ValueError('M08_SAFETY_FLAGS')
    if artifact['market']!='HK_CONNECT' or artifact['trade_date']!=reference['target_date'] or artifact['stage_id']!=reference['stage_id'] or len(artifact['rows'])>10:raise ValueError('M08_OWNER_CONTRACT')
    source_bytes()
    return dict(artifact=artifact,reference=reference,provenance=provenance,natural_verified=False,**SAFETY)


def read_hk_stage(root,reference):
    return _process(Path(__file__).resolve(),dict(root=str(checked_root(root)),reference=reference))


def read_m10_seven(root,references,target_date):
    """Seven ordered exact references, no Stage8, no missing-stage filling."""
    trade_date(target_date)
    if not isinstance(references,list) or [r.get('stage_id') for r in references]!=list(STAGES[:7]):raise ValueError('M08_M10_EXACT_SEVEN_REQUIRED')
    if any(r.get('target_date')!=target_date for r in references):raise ValueError('M08_M10_DATE')
    values=[read_hk_stage(root,r) for r in references]
    return dict(target_date=target_date,stages=values,stage8_included=False,natural_verified=False,**SAFETY)


def main():
    parser=argparse.ArgumentParser(description='Read an exact committed M08 reference without computing')
    parser.add_argument('--worker',action='store_true');parser.add_argument('--root');parser.add_argument('--reference');args=parser.parse_args()
    if args.worker:
        raw=sys.stdin.buffer.read(MAX_JSON_BYTES+1)
        if len(raw)>MAX_JSON_BYTES:raise ValueError('M08_READ_INPUT_SIZE')
        value=json.loads(raw);return _read(value['root'],value['reference'])
    if not args.root or not args.reference:parser.error('--root and --reference are required')
    return read_hk_stage(Path(args.root).absolute(),read_json(Path(args.reference).absolute()))

if __name__=='__main__':
    try:print(canonical_bytes(main()).decode())
    except Exception as error:
        print(canonical_bytes(dict(status='FAILED',reason=type(error).__name__+':'+str(error))).decode());raise SystemExit(1)

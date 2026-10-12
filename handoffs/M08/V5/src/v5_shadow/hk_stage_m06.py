"""Consume the original M06 mapped artifact without creating stage evidence.

Call with the result of M06's original exact-reference cold reader and its
independently pinned source reference. This pure adapter checks consistency;
it does not re-read M06 storage, verify model weights, or attest qualification.
Original raw row fields are retained byte-semantically in the request JSON.
"""
import copy
import math
import re
from .contracts import exact_keys, sha
from .digests import canonical_bytes, sha256_json

SOURCE_KEYS=('role','run_id','artifact_sha256','manifest_sha256','receipt_sha256','artifact_relative')
PROJECTION={'run_id':'source_run_id','artifact_sha256':'source_sha256',
    'manifest_sha256':'source_manifest_sha256','receipt_sha256':'source_receipt_sha256',
    'artifact_relative':'source_path'}
FLAGS=('production_allowed','buy_gate_updated','orders_sent')


def pool_codes(rows):
    """Use native symbol for mapped M06 rows; retain legacy synthetic code rows."""
    if not isinstance(rows,list) or any(not isinstance(row,dict) for row in rows):
        raise ValueError('M08_M06_ROWS')
    codes=[]
    for row in rows:
        mapped=any(key in row for key in ('symbol','pool_rank','pool_score','pool_id'))
        code=row.get('symbol') if mapped else row.get('code')
        if not isinstance(code,str) or not re.fullmatch(r'HK\.[0-9]{5}',code):
            raise ValueError('M08_M06_SYMBOL')
        codes.append(code)
    return codes


def validate_pool_rows(rows,date,signal,*,mapped_required=False):
    codes=pool_codes(rows)
    if len(codes)!=100 or len(set(codes))!=100:raise ValueError('M08_M06_EXACT_TOP100')
    previous=math.inf
    for index,row in enumerate(rows,1):
        mapped=any(key in row for key in ('symbol','pool_rank','pool_score','pool_id'))
        if mapped_required and not mapped:raise ValueError('M08_M06_MAPPED_FIELDS_REQUIRED')
        rank=row.get('pool_rank') if mapped else row.get('rank')
        score=row.get('pool_score') if mapped else row.get('score_prob_active')
        if row.get('target_date')!=date or row.get('signal_date')!=signal or type(rank) is not int or rank!=index:
            raise ValueError('M08_M06_ROW_IDENTITY')
        if isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score):
            raise ValueError('M08_M06_POOL_SCORE')
        if mapped:
            if (row.get('market')!='HK' or row.get('pool_id')!='hkconnect_d1_top100'
                    or row.get('selected_strategy')!='prob_active' or row.get('d1_freshness_status')!='PASS'
                    or row.get('recommendation_status')!='WATCH_ONLY'
                    or any(row.get(key) is not False for key in FLAGS)):
                raise ValueError('M08_M06_MAPPED_ROW_CONTRACT')
            if not 0<=score<=1 or score>previous:raise ValueError('M08_M06_POOL_ORDER')
            previous=score
    # D1 gives membership and metadata, not a preselect or LIVE lane.
    return codes


def owner_d1_rows(rows):
    """Project only the original symbol alias expected by the D1 reference owner."""
    return [dict(row,code=code) for row,code in zip(rows,pool_codes(rows))]


def bind_m06_verified_result(request,result,expected_source_reference):
    """Bind native M06 rows; leave all stage/M02/quote/time evidence untouched."""
    if 'm06' in request:raise ValueError('M08_M06_ALREADY_BOUND')
    expected=copy.deepcopy(expected_source_reference)
    exact_keys(expected,SOURCE_KEYS)
    if expected['role']!='HK_CONNECT_D1_TOP100_0_2':raise ValueError('M08_M06_SOURCE_ROLE')
    if any(not isinstance(expected[key],str) or not expected[key] for key in SOURCE_KEYS):
        raise ValueError('M08_M06_SOURCE_REFERENCE')
    for key in ('artifact_sha256','manifest_sha256','receipt_sha256'):sha(expected[key])
    if (not isinstance(result,dict) or result.get('status')!='ASSEMBLED'
            or result.get('data_kind')!='VERIFIED_SOURCE_SNAPSHOT'
            or result.get('model_weights_reverified') is not False
            or any(result.get(key) is not False for key in FLAGS)):
        raise ValueError('M08_M06_READER_RESULT')
    date=request['target_date'];signal=request['signal_date']
    if result.get('target_date')!=date or result.get('signal_date')!=signal:raise ValueError('M08_M06_DATE')
    if result.get('verified_source_reference')!=expected:raise ValueError('M08_M06_SOURCE_REFERENCE')
    verification=result.get('source_verification')
    if (not isinstance(verification,dict) or verification.get('status')!='READY'
            or verification.get('row_count')!=100
            or any(verification.get(key)!=expected[key] for key in SOURCE_KEYS if key!='role')):
        raise ValueError('M08_M06_SOURCE_VERIFICATION')
    if type(result.get('fixture_only')) is not bool:raise ValueError('M08_M06_FIXTURE_FLAG')
    if result['fixture_only'] and request.get('data_kind')!='SYNTHETIC':raise ValueError('M08_M06_FIXTURE_NOT_REPLAY')
    artifact=result.get('artifact')
    required=dict(schema_version='v3_5.preselection_pool.v1',market='HK',pool_id='hkconnect_d1_top100',
        trade_date=date,target_date=date,signal_date=signal,status='STRICT_0_2_READY',
        source_role='SHARED_VERIFIED_HK_0_2',producer_id='v3_shared_hk_0_2_consumer_v1')
    if (not isinstance(artifact,dict) or any(artifact.get(key)!=value for key,value in required.items())
            or artifact.get('stage_selection_eligible') is not True or artifact.get('source_row_count')!=100
            or any(artifact.get(key) is not False for key in FLAGS)):
        raise ValueError('M08_M06_ARTIFACT')
    if any(artifact.get(output)!=expected[key] for key,output in PROJECTION.items()):
        raise ValueError('M08_M06_SOURCE_PROJECTION')
    validate_pool_rows(artifact.get('rows'),date,signal,mapped_required=True)
    canonical_bytes(result)
    out=copy.deepcopy(request);rows=copy.deepcopy(artifact['rows'])
    out['m06']=dict(target_date=date,signal_date=signal,run_id=expected['run_id'],rows=rows,rows_sha256=sha256_json(rows))
    evidence=out['source']['source_evidence']
    if not isinstance(evidence,list):raise ValueError('M08_SOURCE_DIAGNOSTICS')
    # Retain non-path source bindings only. No raw payload or private path export.
    evidence.extend(['m06_adapter=ORIGINAL_MAPPED_FIELDS_ONLY','m06_adapter_attests_source=false',
        'm06_mapped_artifact_sha256='+sha256_json(artifact),
        'm06_source_reference_sha256='+sha256_json(expected),
        'm06_source_artifact_sha256='+expected['artifact_sha256'],
        'm06_source_manifest_sha256='+expected['manifest_sha256'],
        'm06_source_receipt_sha256='+expected['receipt_sha256'],
        'm06_fixture_only='+str(result['fixture_only']).lower()])
    canonical_bytes(out)
    return out


def main():
    """Local JSON interface; output must be a new file, never overwritten."""
    import argparse
    from pathlib import Path
    from .composition import no_symlinks
    from .hk_stage_daily import read_json
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('request','m06-result','expected-source','output'):parser.add_argument('--'+key,required=True)
    args=parser.parse_args()
    result=bind_m06_verified_result(read_json(args.request),read_json(args.m06_result),read_json(args.expected_source))
    with no_symlinks(Path(args.output)).open('xb') as stream:stream.write(canonical_bytes(result)+b'\n')


if __name__=='__main__':main()

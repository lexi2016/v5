"""One cold exact-generation read in a fresh interpreter with existing pandas.

No producer is called. The frozen native review is returned byte-semantically
unchanged; public metadata is an allowlisted subset of its pure projection.
Private root/pointer fields and volatile latest-attempt exceptions stay local.
"""
import json
from pathlib import Path
import sys

OWNER_COMMIT='084df7c61e57e7615633828a0d6a5d9078dc9b1c'
PUBLICATION_KEYS=('schema_version','trade_date','model_run_id','canonical_review_sha256',
    'raw_review_sha256','source_sha256','record_sha256','generation_sha256','read_status',
    'data_kind','execution_kind','business_status','computed_at','scope','natural_verified',
    'source_provenance_independently_verified','strict_1500_pit_verified','scenario_probabilities_status',
    'review_cannot_confirm','record_cannot_confirm','model_cannot_confirm','close_chain_cannot_confirm',
    'reason_codes','safety','historical_research')


def public_historical(value):
    """Preserve defined historical diagnostics, never open source/receipt extras."""
    result=dict(value);origin=value['original_source']
    source={key:origin[key] for key in ('sha256','bytes','format','hash_verified')}
    if source['format'] not in ('PARQUET','SYNTHETIC_FIXTURE_ONLY'):
        raise ValueError('M09_PUBLIC_SOURCE_FORMAT')
    if 'pointer_sha256' in origin:
        from v5_shadow.contracts import sha
        source['pointer_sha256']=sha(origin['pointer_sha256'])
    if 'verification' in origin:
        if origin['verification']!='STREAM_HASH_BEFORE_AND_AFTER_EXACT_DATE_FILTER':
            raise ValueError('M09_PUBLIC_SOURCE_VERIFICATION')
        source['verification']=origin['verification']
    result['original_source']=source
    receipt=value['original_receipt']
    result['original_receipt']=None if receipt is None else {key:receipt[key] for key in ('sha256','bytes','hash_verified','metadata_status')}
    return result


def main():
    root=Path(sys.argv[1]);sys.path.insert(0,str(root/'V5/src'))
    from v5_shadow.a_close_daily import read_a_close_daily
    from v5_shadow.a_close_daily_api import project_committed_review
    from v5_shadow.a_close_historical import MARKER,MARKER_BYTES
    from v5_shadow.a_close_daily_sources import safe_root
    raw=sys.stdin.buffer.read(65537)
    if len(raw)>65536:raise ValueError('M09_READ_REQUEST_LIMIT')
    binding=json.loads(raw)
    if safe_root(Path(binding['run_root'])).read_bytes(MARKER,max_bytes=100)!=MARKER_BYTES:
        raise ValueError('M09_HISTORICAL_ROOT_REQUIRED')
    value=read_a_close_daily(binding['run_root'],binding['trade_date'],generation_sha256=binding['generation'])
    identity=value['identity'];record=value['record']
    if (identity['model_run_id']!=binding['run_id'] or identity['generation_sha256']!=binding['generation']
            or identity['trade_date']!=binding['trade_date']):raise ValueError('M09_REFERENCE_RESPONSE_MISMATCH')
    projected=project_committed_review(value,binding['trade_date']);publication=projected['m09_publication']
    if (publication['read_status']!='VERIFIED' or record['data_kind']!='RECORDED_INPUT_REPLAY'
            or record['execution_kind']!='HISTORICAL_REPLAY' or record['scope']!='OBSERVED_ROWS_ONLY'
            or record['business_status']!='PARTIAL' or 'historical_research' not in publication):
        raise ValueError('M09_HISTORICAL_CLASSIFICATION_REQUIRED')
    public={key:publication[key] for key in PUBLICATION_KEYS}
    public['historical_research']=public_historical(publication['historical_research'])
    response=dict(schema_version='v5.a_close_replay_readonly.v1',module_id='M09_A_CLOSE_REPLAY',
        status=record['business_status'],trade_date=binding['trade_date'],run_id=binding['run_id'],
        generation=binding['generation'],owner_commit=OWNER_COMMIT,identity=identity,
        review=value['review'],publication=public,data_kind=record['data_kind'],
        execution_kind=record['execution_kind'],scope=record['scope'],research_only=True,
        production_allowed=False,buy_gate_updated=False,orders_sent=False,natural_verified=False,
        formal_eligibility_verified=False,strict_1500_pit_verified=False,source_time_verified=False,
        membership_qualification_verified=False)
    text=json.dumps(response,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    for private in (binding['run_root'],record.get('run_root_at_creation')):
        if private and private in text:raise ValueError('M09_PRIVATE_PATH_IN_RESPONSE')
    sys.stdout.write(text)


if __name__=='__main__':
    try:main()
    except Exception:
        sys.stdout.write('{"status":"CANNOT_CONFIRM","reason":"M09_COMMITTED_REFERENCE_REJECTED"}')
        raise SystemExit(1)

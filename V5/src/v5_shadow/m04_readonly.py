"""Cold-read one fixed historical M04 sample with the unchanged archive owner.

No latest selector, owner run/build/import, provider, model, publication, or writes.
The configured root is an independently marked V5 copy of the exact saved trio.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from .composition import no_symlinks
from .contracts import exact_keys
from .digests import canonical_bytes, sha256_json, MAX_JSON_BYTES

ROUTE='/api/v5/source-bundle/research-intelligence'
BINDING='m04_saved_research_binding'
BASE=Path(__file__).resolve().parents[2]
RUNTIME=BASE/'contracts/m04_readonly_runtime.json'
RUNTIME_SHA256='2c66538a28864c919e6b43b5f73fce730d35c5236034ad930e0a58512b265a91'
EXPECTED_OUT_OF_SAMPLE_ERRORS=53
CAPSULE_SHA256='33a4b671c4b2b6b89db2c3e8bed7efdc8d1ee8fc983ff005d2ade2692d47b2a4'
ARTICLE_SOURCE_SHA256='5c3f8dea7b25d12be209a809fbff49dfb85063be5a653b3ea4053397f12c0e5c'
FILES={
    'manifest.json':'b3018c40ba6ffb88f1eec00a48448b5f3414fd55f067fb39a7518febb012fb52',
    'research/archives/20261012.json':'3fdf8ce89eefc4e6c39b03201e56dd3a4aaaefca125c5b3ae787228fa7bb21af',
    'receipts/research/archives/20261012.json':'8b62a83a0dcc85879734af21a309a7e464ff0cbabbad6e68271b4d11a9766ecd',
}
REFERENCE=dict(archive_date='20261012',source_slot='2100',source_run_id='hip-49cb26f7f3a0661bde1d1440',
    batch_fetched_at='2026-10-12T21:00:00+08:00',source_publication_available_at='2026-10-12T21:00:01.768546+08:00',
    publication_time_is_not_article_availability=True,original_code_commit='8a3c1d2013e34b7e070fd924e1ee754f7dfd8de7',
    verification_commit='8261160018537c71de0af17584d371a2d31913c8')
FLAGS=dict(research_only=True,natural_verified=False,historical_pit_claimed=False,
    formal_eligibility_verified=False,production_allowed=False,buy_gate_updated=False,orders_sent=False)


def validate_binding(config):
    binding=config.get(BINDING)
    if binding is None:return
    if config.get('module_id')!='source_bundle' or ROUTE not in config.get('routes',[]):
        raise ValueError('M04_ROUTE_CONFIG')
    exact_keys(binding,('archive_root','python_executable'))
    for key in ('archive_root','python_executable'):
        value=binding[key]
        if not isinstance(value,str) or not value or not Path(value).is_absolute() or '..' in Path(value).parts:
            raise ValueError('M04_BINDING_PATH')


def _raw(path):
    path=no_symlinks(path)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        from .module_api import _read_regular
        return _read_regular(fd,MAX_JSON_BYTES)
    finally:os.close(fd)


def _runtime():
    raw=_raw(RUNTIME)
    if hashlib.sha256(raw).hexdigest()!=RUNTIME_SHA256:raise ValueError('M04_RUNTIME_MANIFEST')
    for entry in json.loads(raw)['entries']:
        relative=Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('M04_RUNTIME_PATH')
        content=_raw(BASE/relative)
        if len(content)!=entry['bytes'] or hashlib.sha256(content).hexdigest()!=entry['sha256']:
            raise ValueError('M04_RUNTIME_BYTES')


def _sample(root):
    expected=set(FILES)|{'.v5-m04-saved-root'}
    for name in FILES:
        expected.update(str(parent) for parent in Path(name).parents if str(parent)!='.')
    actual={str(path.relative_to(root)) for path in root.rglob('*')}
    if actual!=expected:raise ValueError('M04_PRIVATE_ROOT_INVENTORY')
    for relative in actual:no_symlinks(root/relative)
    if _raw(root/'.v5-m04-saved-root')!=b'v5.m04-saved-reference.v1\n':raise ValueError('M04_PRIVATE_ROOT_MARKER')
    sample={}
    for name,digest in FILES.items():
        raw=_raw(root/name)
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('M04_SAVED_SAMPLE_CHANGED')
        sample[name]=raw
    return sample


def not_configured():
    return dict(status='NOT_CONFIGURED',module_id='M04_RESEARCH_INTELLIGENCE',
        reason_codes=['M04_SAVED_REFERENCE_NOT_CONFIGURED'],**FLAGS)


def read_record(config,query):
    if query:raise ValueError('M04_FIXED_REFERENCE_QUERY')
    validate_binding(config);binding=config.get(BINDING)
    if binding is None:return None
    root=no_symlinks(Path(binding['archive_root']));sample=_sample(root);_runtime()
    request=dict(root=str(root),files=FILES)
    # Execute the original reader entrypoint directly. Its worker installs the
    # original frozen store and read-only audit boundary, never the ingest CLI.
    try:
        proc=subprocess.run([binding['python_executable'],'-I','-B',str(BASE/'src/v5_shadow/archive_reader.py')],
            input=canonical_bytes(request),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,
            env={k:v for k,v in os.environ.items() if not k.startswith(('V4_','V35_'))})
    except subprocess.TimeoutExpired as error:raise ValueError('M04_READER_TIMEOUT') from error
    if proc.returncode or len(proc.stdout)>MAX_JSON_BYTES:raise ValueError('M04_ORIGINAL_READER_REJECTED')
    try:readback=json.loads(proc.stdout)
    except (ValueError,UnicodeError) as error:raise ValueError('M04_READER_JSON') from error
    if (not isinstance(readback,dict) or readback.get('source_capsule_sha256')!=CAPSULE_SHA256
        or readback.get('article_v2_source_sha256')!=ARTICLE_SOURCE_SHA256
        or readback.get('request_sha256')!=sha256_json(request)):
        raise ValueError('M04_READER_IDENTITY')
    records=readback.get('records')
    if not isinstance(records,dict) or any(not isinstance(row,dict) for row in records.values()):raise ValueError('M04_READER_RECORDS')
    outside_errors=sum(bool(row.get('error')) for key,row in records.items() if key!='20261012/')
    if outside_errors!=EXPECTED_OUT_OF_SAMPLE_ERRORS:raise ValueError('M04_OUT_OF_SAMPLE_CHANGED')
    selected=records.get('20261012/',{})
    if selected.get('error') or not isinstance(selected.get('payload'),dict):raise ValueError('M04_SAMPLE_NOT_READABLE')
    archive=selected['payload']
    if archive!=json.loads(sample['research/archives/20261012.json']):raise ValueError('M04_PAYLOAD_NOT_ORIGINAL')
    articles=archive.get('articles')
    if (archive.get('archive_date')!='20261012' or archive.get('article_count')!=18
        or not isinstance(articles,list) or len(articles)!=18
        or archive.get('recommendation_status')!='RESEARCH_ONLY'
        or any(archive.get(key) is not False for key in ('production_allowed','buy_gate_updated','orders_sent'))):
        raise ValueError('M04_SAMPLE_CONTRACT')
    missing={key:sum(not a.get(key) or a.get(key)=='UNKNOWN' for a in articles) for key in ('retrieved_at','available_at')}
    if missing!={'retrieved_at':18,'available_at':18}:raise ValueError('M04_SAMPLE_CLOCKS_CHANGED')
    if _sample(root)!=sample:raise ValueError('M04_SAVED_SAMPLE_CHANGED')
    _runtime()
    payload=dict(schema_version='v5.m04_saved_research.v1',module_id='M04_RESEARCH_INTELLIGENCE',
        status='SAVED_HISTORICAL_SAMPLE',data_kind='RECORDED_INPUT_REPLAY',coverage_scope='FIXED_18_ARTICLE_SAMPLE',
        reference=REFERENCE,file_sha256=FILES,archive=archive,article_count=18,pit='UNKNOWN',
        missing_retrieved_at=18,missing_available_at=18,
        out_of_sample_record_errors=outside_errors,
        source_capsule_sha256=CAPSULE_SHA256,article_v2_source_sha256=ARTICLE_SOURCE_SHA256,**FLAGS)
    record=dict(schema_version='v5.module_response.v1',module_id=config['module_id'],release_id=config['release_id'],
        path=ROUTE,query={},payload=payload,payload_sha256=sha256_json(payload),source_input_sha256=archive['source_input_sha256'],
        data_kind='RECORDED_INPUT_REPLAY',generated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),status_code=200)
    from .module_api import _validate_record
    return _validate_record(config,record,ROUTE,{}),sha256_json(record)

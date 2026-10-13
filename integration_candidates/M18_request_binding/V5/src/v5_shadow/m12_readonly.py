"""M12 exact saved run API binding; no producer, latest selector, or writes."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from .contracts import exact_keys,trade_date,sha
from .digests import canonical_bytes,sha256_json
from .m12_readonly_worker import waiting,raw

BASE=Path(__file__).resolve().parents[2]
ROUTE='/api/v5/source-bundle/video-fupan'
BINDING='m12_video_fupan_binding'
RUNTIME=BASE/'contracts/m12_runtime.json'
RUNTIME_SHA256='62fc6d512b1c43bc247123e299cd0e27dae6c71bbfb7b31bc3b8f0b1a751a79c'

def validate_reference(binding):
    exact_keys(binding,('private_root','trade_date','run_id','manifest_sha256','owner_receipt_sha256','data_kind','python_executable'))
    trade_date(binding['trade_date']);sha(binding['manifest_sha256']);sha(binding['owner_receipt_sha256'])
    if not isinstance(binding['run_id'],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,255}',binding['run_id']):raise ValueError('M12_RUN_ID')
    if binding['data_kind'] not in {'SYNTHETIC','RECORDED_INPUT_REPLAY','OWNER_RESULT'}:raise ValueError('M12_DATA_KIND')
    for key in ('private_root','python_executable'):
        p=binding[key]
        if not isinstance(p,str) or not Path(p).is_absolute() or '..' in Path(p).parts:raise ValueError('M12_PATH')

def validate_binding(config):
    if BINDING not in config:return
    if config['module_id']!='source_bundle' or ROUTE not in config['routes']:raise ValueError('M12_ROUTE')
    validate_reference(config[BINDING])

def verify_runtime():
    content=raw(RUNTIME)
    if hashlib.sha256(content).hexdigest()!=RUNTIME_SHA256:raise ValueError('M12_RUNTIME_MANIFEST')
    for entry in json.loads(content)['entries']:
        p=Path(entry['path'])
        if p.is_absolute() or '..' in p.parts:raise ValueError('M12_RUNTIME_PATH')
        value=raw(BASE/p)
        if len(value)!=entry['bytes'] or hashlib.sha256(value).hexdigest()!=entry['sha256']:raise ValueError('M12_RUNTIME_BYTES')

def not_configured():return waiting('M12_SAVED_REFERENCE_NOT_CONFIGURED')

def read_record(config,query):
    if set(query)-{'trade_date'}:raise ValueError('M12_QUERY')
    if 'trade_date' in query:trade_date(query['trade_date'])
    validate_binding(config);binding=config.get(BINDING)
    if binding is None:payload=not_configured()
    elif query.get('trade_date',binding['trade_date'])!=binding['trade_date']:
        payload=waiting('M12_NO_SAVED_RESULT_FOR_DATE',requested_trade_date=query['trade_date'])
    else:
        verify_runtime()
        try:
            proc=subprocess.run([binding['python_executable'],'-I','-B',str(BASE/'src/v5_shadow/m12_readonly_worker.py')],
                input=canonical_bytes(binding),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,cwd=str(BASE.parent),
                env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'})
        except subprocess.TimeoutExpired as error:raise ValueError('M12_READER_TIMEOUT') from error
        if proc.returncode or len(proc.stdout)>4*1024*1024:raise ValueError('M12_READER_REJECTED')
        payload=json.loads(proc.stdout);verify_runtime()
    record=dict(schema_version='v5.module_response.v1',module_id=config['module_id'],release_id=config['release_id'],path=ROUTE,query=query,payload=payload,
        payload_sha256=sha256_json(payload),source_input_sha256=binding['manifest_sha256'] if binding else sha256_json(payload),
        data_kind=binding['data_kind'] if binding else 'OWNER_RESULT',generated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),status_code=200)
    from .module_api import _validate_record
    return _validate_record(config,record,ROUTE,query),sha256_json(record)

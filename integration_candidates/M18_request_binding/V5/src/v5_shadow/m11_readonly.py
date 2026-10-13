"""Saved M11 exact-reference API. Never calls the original acquisition service."""
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from .contracts import exact_keys,trade_date,sha
from .digests import canonical_bytes,sha256_json
from .m11_readonly_worker import waiting,raw,SLOTS

BASE=Path(__file__).resolve().parents[2]
ROUTE='/api/v5/source-bundle/intraday-research'
BINDING='m11_saved_research_binding'
RUNTIME=BASE/'contracts/m11_runtime.json'
RUNTIME_SHA256='f602879a5b575e45de1168fb01f0492fd6c79e2dc4ecd46b9b863c5596212644'

def validate_reference(binding):
    exact_keys(binding,('archive_root','identity','operation','commit_sha256','data_kind','python_executable'))
    identity=binding['identity']
    exact_keys(identity,('target_date','slot','cutoff','trigger','run_id','input_sha','config_sha','code_sha','source_sha'))
    day=identity['target_date']
    if not isinstance(day,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):raise ValueError('M11_DATE')
    trade_date(day.replace('-',''));stamp=datetime.fromisoformat(identity['cutoff'])
    if stamp.tzinfo is None or stamp.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()!=day:raise ValueError('M11_CUTOFF')
    operation=binding['operation']
    if operation not in {'capture','generate'} or identity['slot'] not in SLOTS:raise ValueError('M11_OPERATION')
    if identity['trigger']!=('capture' if operation=='capture' else 'explicit-daily-generation'):raise ValueError('M11_TRIGGER')
    if operation=='generate' and identity['slot']!='15:00':raise ValueError('M11_DAILY_SLOT')
    if not isinstance(identity['run_id'],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,255}',identity['run_id']):raise ValueError('M11_RUN_ID')
    for key in ('input_sha','config_sha','code_sha','source_sha'):sha(identity[key])
    from .m11.owner_sources import BUILD_MANIFEST_SHA
    if identity['source_sha']!=BUILD_MANIFEST_SHA:raise ValueError('M11_OWNER_SOURCE_PIN')
    sha(binding['commit_sha256'])
    if binding['data_kind'] not in {'SYNTHETIC','RECORDED_INPUT_REPLAY','OWNER_RESULT'}:raise ValueError('M11_DATA_KIND')
    for key in ('archive_root','python_executable'):
        p=binding[key]
        if not isinstance(p,str) or not Path(p).is_absolute() or '..' in Path(p).parts:raise ValueError('M11_PATH')

def validate_binding(config):
    if BINDING not in config:return
    if config['module_id']!='source_bundle' or ROUTE not in config['routes']:raise ValueError('M11_ROUTE')
    validate_reference(config[BINDING])

def verify_runtime():
    content=raw(RUNTIME)
    if hashlib.sha256(content).hexdigest()!=RUNTIME_SHA256:raise ValueError('M11_RUNTIME_MANIFEST')
    for entry in json.loads(content)['entries']:
        p=Path(entry['path'])
        if p.is_absolute() or '..' in p.parts:raise ValueError('M11_RUNTIME_PATH')
        value=raw(BASE/p)
        if len(value)!=entry['bytes'] or hashlib.sha256(value).hexdigest()!=entry['sha256']:raise ValueError('M11_RUNTIME_BYTES')

def not_configured():return waiting('M11_SAVED_REFERENCE_NOT_CONFIGURED')

def read_record(config,query):
    if set(query)-{'trade_date'}:raise ValueError('M11_QUERY')
    if 'trade_date' in query:trade_date(query['trade_date'])
    validate_binding(config);binding=config.get(BINDING)
    if binding is None:payload=not_configured()
    elif query.get('trade_date',binding['identity']['target_date'].replace('-',''))!=binding['identity']['target_date'].replace('-',''):
        payload=waiting('M11_NO_SAVED_RESULT_FOR_DATE',requested_trade_date=query['trade_date'])
    else:
        verify_runtime()
        try:
            proc=subprocess.run([binding['python_executable'],'-I','-B',str(BASE/'src/v5_shadow/m11_readonly_worker.py')],input=canonical_bytes(binding),
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,cwd=str(BASE.parent),env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'})
        except subprocess.TimeoutExpired as error:raise ValueError('M11_READER_TIMEOUT') from error
        if proc.returncode or len(proc.stdout)>4*1024*1024:raise ValueError('M11_READER_REFUSED')
        payload=json.loads(proc.stdout);verify_runtime()
    record=dict(schema_version='v5.module_response.v1',module_id=config['module_id'],release_id=config['release_id'],path=ROUTE,query=query,payload=payload,
        payload_sha256=sha256_json(payload),source_input_sha256=binding['commit_sha256'] if binding else sha256_json(payload),
        data_kind=binding['data_kind'] if binding else 'OWNER_RESULT',generated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),status_code=200)
    from .module_api import _validate_record
    return _validate_record(config,record,ROUTE,query),sha256_json(record)

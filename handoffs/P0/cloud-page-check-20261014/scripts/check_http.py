"""Actual loopback HTTP checks against saved SYNTHETIC products, not a browser."""
import hashlib
import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

root, evidence = map(Path, sys.argv[1:3])
origin = 'http://127.0.0.1:4177'
info = json.loads((root / 'fixture-info.json').read_text())
records = []

def inventory():
    return {str(p.relative_to(root)):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mtime_ns=p.stat().st_mtime_ns)
            for folder in ['m04-new','m04-old','m17-synthetic','manager-bundle','manager-api','source-api']
            for p in (root / folder).rglob('*') if p.is_file()}

def request(path, query=None, method='GET'):
    url=origin+path+('?' + urlencode(query) if query else '')
    try: response=urlopen(Request(url,method=method),timeout=40)
    except HTTPError as exc:response=exc
    with response:
        raw=response.read();headers=dict(response.headers);status=response.status
    content_type=next((v for k,v in headers.items() if k.lower()=='content-type'),'')
    value=json.loads(raw) if 'json' in content_type else raw.decode()
    records.append(dict(method=method,url=url,status=status,headers=headers,body=value,
                        sha256=hashlib.sha256(raw).hexdigest()))
    return status,value

before=inventory()
for page in ['/', '/?view=research&date='+info['m04_dates'][0]]:
    status,html=request(page)
    assert status==200 and 'SYNTHETIC 合成样例' in html
for day,folder in zip(info['m04_dates'],['m04-new','m04-old']):
    status,value=request('/api/v5/research/lane',dict(research_date=day))
    assert status==200 and value['research_date']==day and value['endpoint_mode']=='EXACT',value
    archive=json.loads((root/folder/f'research/archives/{day}.json').read_text())
    assert value['archive_materials']['articles']==archive['articles']
    assert value['archive_materials']['source_reference']['archive_binding']['root']==str(root/folder)
    assert value['production_allowed'] is False
    if folder=='m04-old':
        assert value['archive_materials']['acquisition_status']=='UNKNOWN' and value['source_run_id'] is None
status,value=request('/api/v5/research/lane')
assert status==200 and value['research_date']==info['m04_dates'][0] and value['endpoint_mode']=='LATEST'
status,value=request('/api/v5/research/lane',dict(research_date='19990101'))
assert status==200 and value['status']=='NOT_MATERIALIZED' and value['archive_materials'] is None
assert request('/api/v5/research/lane',method='POST')[0]==405

route='/api/v5/manager/close-recapture'
status,value=request(route,info['m17_query'])
assert status==200 and value['run_id']==info['m17_query']['run_id'] and value['execution_kind']=='SIMULATED'
overlay=root/'m17-synthetic/state'/info['m17_reference']['files']['candidate_overlay']['artifact_ref']
assert value['rows']==json.loads(overlay.read_text())['rows'] and len(value['rows'])==100
assert value['files']==info['m17_reference']['files'] and value['natural_verified'] is False
for query in [dict(info['m17_query'],run_id='f'*32),dict(info['m17_query'],source_trade_date='20260929'),{}]:
    status,value=request(route,query)
    assert status==409 and value['status']=='CANNOT_CONFIRM' and 'rows' not in value
assert request(route,info['m17_query'],method='POST')[0]==405

manager='/api/v4/manager/m18/v2'
status,descriptor=request(manager,dict(run_id=info['manager_descriptor']['run_id']))
assert status==200 and descriptor==info['manager_descriptor']
query=dict(run_id=descriptor['run_id'],generation_id=descriptor['generation_id'])
status,overview=request(manager+'/overview',query)
assert status==200 and overview['identity']==descriptor['identity']
status,first=request(manager+'/sections',dict(query,section='materials'))
assert status==200 and first['offset']==0 and len(first['entries'])==32
status,second=request(manager+'/sections',dict(query,section='materials',cursor=first['next_cursor']))
assert status==200 and second['offset']==32 and len(second['entries'])==32
for page in [first,second]:
    assert page['identity']==descriptor['identity'] and page['generation_id']==descriptor['generation_id']
    assert page['manifest_sha256']==overview['manifest_sha256']
status,value=request(manager+'/sections',dict(query,run_id='f'*32,section='materials',cursor=first['next_cursor']))
assert status==503 and value['status']=='CANNOT_CONFIRM' and 'entries' not in value,(status,value)
after=inventory()
assert before==after,'READ_MUTATED_SAVED_ARTIFACTS'
report=dict(layer='REAL_HTTP_NOT_BROWSER',input_kind='SYNTHETIC',base_commit='afddbdf75b86f3669b9329e1bffdd77c03bb3c7c',
            browser_screenshots='NOT_RUN',saved_files_unchanged=len(before),checks='PASS',requests=records)
(evidence/'http-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(evidence/'saved-inventory-before.json').write_text(json.dumps(before,indent=2))
print(json.dumps(dict(status='PASS',http_requests=len(records),saved_files_unchanged=len(before))))

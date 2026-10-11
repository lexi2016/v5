"""Independent negative probe, only explicitly synthetic private fixtures."""
from pathlib import Path
from datetime import datetime,timezone
import json,copy,sys,hashlib
from v5_shadow import a_close_daily as daily
from v5_shadow.digests import canonical_bytes,sha256_json
from test_a_close_daily import make_input,file_sha
O=Path(sys.argv[1]).resolve();O.mkdir();results=[]
mutations={'schema':lambda r:r.update(schema_version='INVALID_SCHEMA'),'date':lambda r:r.update(trade_date='20261008'),'trigger':lambda r:r['trigger'].update(attempt_id='other-attempt'),'safety':lambda r:r['safety'].update(orders_sent=True),'status_success':lambda r:r.update(status='SUCCEEDED',run_id='fabricated-run',generation_sha256='a'*64),'missing_fields':lambda r:[r.pop(k,None) for k in ['schema_version','trade_date','trigger','safety','status']]}
for name,mutate in mutations.items():
 b=O/name;b.mkdir();source=b/'source';root=b/'private-output';make_input(source);daily.initialize_a_close_root(root)
 request=dict(schema_version='v5.m09.daily_request.v1',trade_date='20261009',slot='16:05',job_id='a_share_close_review_1605',attempt_id='same-attempt',execution_kind='ENGINEERING',triggered_at=datetime.now(timezone.utc).isoformat(),source_root=str(source),input_manifest='input.json',input_manifest_sha256='0'*64,configuration_revision='independent-negative')
 first=daily.run_a_close_daily(root,request);assert first['status']=='FAILED',first
 p=root/'attempts'/first['trigger_sha256']/'receipt.json';original=p.read_bytes();(b/'original_receipt.json').write_bytes(original);bad=copy.deepcopy(first);mutate(bad);assert bad['request_sha256']==sha256_json(request);p.write_bytes(canonical_bytes(bad));(b/'tampered_receipt.json').write_bytes(p.read_bytes());(b/'request.json').write_bytes(canonical_bytes(request))
 try:
  second=daily.run_a_close_daily(root,request);accepted=second==bad;(b/'returned_receipt.json').write_bytes(canonical_bytes(second));error=None
 except Exception as e:accepted=False;error=type(e).__name__+':'+str(e)
 result={'case':name,'first_status':first['status'],'first_reason':first.get('reason'),'tampered_receipt_returned_unchanged':accepted,'error':error,'source_kind':'SYNTHETIC','private_root':str(root),'expected':'REJECT_INVALID_PERSISTED_RECEIPT','observed':'VULNERABLE_DIRECT_REUSE' if accepted else 'REJECTED'};results.append(result);print(json.dumps(result),flush=True)
(O/'RESULTS.json').write_text(json.dumps(results,indent=2));raise SystemExit(1 if any(r['tampered_receipt_returned_unchanged'] for r in results) else 0)

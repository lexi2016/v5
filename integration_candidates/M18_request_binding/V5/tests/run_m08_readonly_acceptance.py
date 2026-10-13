"""One fixed-commit acceptance of the M08 P0 seam, using existing dependencies.

Real references/config/responses and logs stay local. Upload only report.json.
No original M08 90/16/21 suite, producer, import, collection or deployment runs.
"""
import argparse,hashlib,http.client,json,os,subprocess,sys,tempfile,threading
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode,urlsplit
REPO=Path(__file__).resolve().parents[2];sys.path[:0]=[str(REPO/'V5/src'),str(REPO/'V5/tests')]
from v5_shadow.m08_readonly import BINDING,ROUTE,owner_root,validate_binding
from v5_shadow.module_api import create_module_server
from run_m09_readonly_acceptance import verify_checkout

def now():return datetime.now(timezone.utc).isoformat()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def inventory(root):
 return {str(p.relative_to(root)):(digest(p.read_bytes()),p.stat().st_size,p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
def request(port,path):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=90);c.request('GET',path);r=c.getresponse();raw=r.read();status=r.status;c.close();return status,json.loads(raw),raw

def real_read(config,private_file,baseline_origin=None,protected_roots=()):
 validate_binding(config);binding=config[BINDING];roots=[Path(binding['recorded_root']),Path(config['data_root']),*protected_roots];before=[inventory(p) for p in roots]
 server=create_module_server(config);t=threading.Thread(target=server.serve_forever);t.start();results=[];summaries=[];old=[]
 try:
  port=server.server_address[1];status,catalog,_=request(port,ROUTE)
  if status!=200 or catalog.get('references')!=binding['references']:raise ValueError('M08_REAL_CATALOG_MISMATCH')
  for ref in binding['references']:
   query=dict(date=ref['target_date'],stage=ref['stage_id'],run_id=ref['run_id'],import_sha256=ref['import_sha256'])
   status,value,body=request(port,ROUTE+'?'+urlencode(query))
   if status!=200:raise ValueError('M08_REAL_GET_REJECTED')
   code="import json,sys;sys.path.insert(0,sys.argv[1]);from v5_shadow.hk_stage_observed import read_hk_stage_observed;from v5_shadow.hk_stage_api import _public_value;r=json.load(sys.stdin);print(json.dumps(_public_value(read_hk_stage_observed(r['root'],r['reference']))))"
   proc=subprocess.run([binding['python_executable'],'-I','-B','-c',code,str(owner_root()/'V5/src')],input=json.dumps(dict(root=binding['recorded_root'],reference=ref)),capture_output=True,text=True,timeout=90)
   if proc.returncode:raise ValueError('M08_REAL_INDEPENDENT_READ_FAILED')
   expected=json.loads(proc.stdout)
   if any(value[k]!=expected[k] for k in ('artifact','reference','provenance','read_status')) or len(value['artifact']['rows'])!=10:raise ValueError('M08_REAL_ORIGINAL_FIELDS_MISMATCH')
   results.append(value);summaries.append(dict(stage=ref['stage_id'],date=ref['target_date'],rows=len(value['artifact']['rows']),status=value['status'],source_status=value['artifact']['source_status'],stage_group=value['stage_group'],response_sha256=digest(body),exact_original_fields=True,captured_at=None))
  bad=dict(query);bad['import_sha256']='0'*64
  if request(port,ROUTE+'?'+urlencode(bad))[0]!=409:raise ValueError('M08_REAL_UNKNOWN_REFERENCE_ACCEPTED')
  if baseline_origin:
   u=urlsplit(baseline_origin)
   if u.scheme!='http' or u.hostname!='127.0.0.1' or not u.port or u.path not in ('','/') or u.query or u.fragment or u.username:raise ValueError('M08_BASELINE_LOOPBACK_ONLY')
   for route in ('/api/v5/source-bundle/status','/api/v5/source-bundle/hk-preselection','/api/v5/source-bundle/hk-close-review','/api/v5/source-bundle/a-close-replay'):
    a,av,_=request(u.port,route);b,bv,_=request(port,route)
    if a!=200 or b!=200 or av!=bv:raise ValueError('M08_EXISTING_SOURCE_REGRESSION')
    old.append(dict(route=route,status='PASS',exact_existing_payload=True))
 finally:server.shutdown();t.join();server.server_close()
 if [inventory(p) for p in roots]!=before:raise ValueError('M08_REAL_READ_CHANGED_FILES')
 private_file.write_text(json.dumps(dict(catalog=catalog,results=results)))
 return dict(status='PASS',reference_count=10,stage_count=8,results=summaries,exact_rows_order_fields=True,recorded_and_api_and_protected_roots_unchanged=True,protected_root_count=len(roots),unknown_reference_rejected=True,existing_source_regression=old)

def probe(executable):
 proc=subprocess.run([executable,'-I','-B','-c','import json,sys;print(json.dumps(dict(python=sys.version.split()[0],supported=sys.version_info[:2]>=(3,14))))'],capture_output=True,text=True,timeout=15)
 if proc.returncode:raise ValueError('M08_EXISTING_PYTHON_PROBE_FAILED')
 return json.loads(proc.stdout)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--expected-commit');p.add_argument('--source-config',type=Path);p.add_argument('--baseline-source-origin');p.add_argument('--protected-root',type=Path,action='append',default=[]);p.add_argument('--evidence-dir',type=Path,required=True);p.add_argument('--skip-frontend',action='store_true');args=p.parse_args()
 if args.source_config and (not args.expected_commit or args.skip_frontend or not args.baseline_source_origin):p.error('Real acceptance requires fixed commit, baseline source origin and all frontend checks')
 report=dict(schema_version='v5.m08_readonly_acceptance.v1',started_utc=now(),mode='REAL_SAVED_COLD_READ' if args.source_config else 'SYNTHETIC_ONLY',steps=[],real_read={'status':'NOT_RUN'},frontend={'status':'NOT_RUN'},original_90_16_21_rerun=False,real_producer_invoked=False,real_imports_performed=False,synthetic_fixture_imports_only=True,synthetic_test_fixture_producer_only=True,collection=False,deployed=False,services_changed=False)
 evidence=args.evidence_dir.resolve();evidence.mkdir(parents=True,exist_ok=True);env=dict(os.environ,PYTHON=sys.executable,PYTHONDONTWRITEBYTECODE='1');failed=False
 def run(name,argv,cwd):
  nonlocal failed
  try:r=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,timeout=600);out,err,code=r.stdout,r.stderr,r.returncode
  except (OSError,subprocess.TimeoutExpired) as error:out=b'';err=type(error).__name__.encode();code=127
  (evidence/(name+'.stdout.local.log')).write_bytes(out);(evidence/(name+'.stderr.local.log')).write_bytes(err);report['steps'].append(dict(name=name,status='PASS' if code==0 else 'FAILED',exit_code=code,stdout_sha256=digest(out),stderr_sha256=digest(err)));failed|=code!=0
 try:
  if args.expected_commit:report['commit']=verify_checkout(REPO,args.expected_commit)
  owner_root();report['runner_environment']=probe(sys.executable);config=None
  if args.source_config:
   config=json.loads(args.source_config.read_bytes());report['worker_environment']=probe(config[BINDING]['python_executable'])
   if not report['runner_environment']['supported'] or not report['worker_environment']['supported']:raise ValueError('M08_EXISTING_SUPPORTED_PYTHON_REQUIRED')
  with tempfile.TemporaryDirectory(prefix='m08-private-acceptance-') as tmp:
   if config:
    report['real_read']=real_read(config,Path(tmp)/'responses.json',args.baseline_source_origin,[r.resolve() for r in args.protected_root]);env['V5_M08_RESPONSES_FILE']=str(Path(tmp)/'responses.json')
   code="import sys;sys.path[:0]=['V5/src','V5/tests'];import unittest;unittest.main(module=None,argv=['unittest','test_m08_readonly_api','test_m08_acceptance_runner','test_module_api','test_m06_readonly_api','test_m09_readonly_api','test_m10_readonly_api','-v'])"
   run('targeted-python',[sys.executable,'-I','-B','-c',code],REPO)
   run('targeted-node',['node','--test','tests/hkStageObserved.node.mjs','tests/hkPreselectionPool.node.mjs','tests/hkCloseReview.node.mjs','tests/aCloseReplay.node.mjs','tests/sourceBundle.node.mjs'],REPO/'frontend')
   if not args.skip_frontend:
    run('component-dom',['npm','run','test','--','src/components/HkStageObserved.spec.ts','src/components/SourceBundleStatus.m08.spec.ts','src/components/SourceBundleStatus.m09.spec.ts','src/components/HkPreselectionPool.spec.ts','src/components/HkCloseReview.spec.ts','src/components/ACloseReplay.spec.ts'],REPO/'frontend')
    run('typecheck',['npm','run','typecheck','--','--project','tsconfig.cloud-product.json'],REPO/'frontend');run('build',['npm','run','build'],REPO/'frontend')
    report['frontend']['status']='PASS' if all(s['status']=='PASS' for s in report['steps'] if s['name'] in ('component-dom','typecheck','build')) else 'FAILED'
 except Exception as error:report['reason']=str(error) if str(error).startswith(('M08_','M09_')) else type(error).__name__;failed=True
 report['ended_utc']=now();report['status']='FAILED' if failed else 'PARTIAL_VERIFICATION' if args.skip_frontend else 'PASS';(evidence/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('status','mode','real_read','frontend')}));return int(failed)
if __name__=='__main__':raise SystemExit(main())

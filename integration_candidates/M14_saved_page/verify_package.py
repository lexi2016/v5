"""Isolated package verification; synthetic owner fixture only."""
import argparse,hashlib,json,os,select,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from urllib.request import urlopen
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-checkout',required=True,help='Unmodified complete P0 checkout at candidate base commit')
args=parser.parse_args()
CANDIDATE=Path(__file__).resolve().parent
BEFORE=Path(args.base_checkout)
if not BEFORE.is_absolute() or not BEFORE.is_dir():parser.error('base checkout must be an absolute existing directory')
PYTHON=sys.executable

def run(*args):
 return subprocess.run([PYTHON,'-B',str(CANDIDATE/'apply_candidate.py'),*args],capture_output=True,text=True)

with tempfile.TemporaryDirectory(prefix='m14-package-') as tmp:
 root=Path(tmp).resolve();checkout=root/'checkout';checkout.mkdir()
 for name in ['V5','frontend','tests']:shutil.copytree(BEFORE/name,checkout/name,ignore=shutil.ignore_patterns('__pycache__','node_modules','.venv','.git'))
 source=checkout/'V5/src/v5_shadow/module_api.py';original=source.read_bytes()
 source.write_bytes(original+b'\n# deliberately wrong synthetic preimage\n')
 result=run('--target',str(checkout));assert result.returncode!=0 and 'PREIMAGE_MISMATCH' in result.stderr
 assert not (checkout/'V5/src/v5_shadow/m14_readonly.py').exists()
 source.write_bytes(original)
 result=run('--target',str(checkout),'--check-only');assert result.returncode==0,result.stderr
 assert not (checkout/'V5/src/v5_shadow/m14_readonly.py').exists()
 result=run('--target',str(checkout));assert result.returncode==0,result.stderr
 manifest=json.loads((CANDIDATE/'verification.json').read_bytes())
 for item in manifest['files']:assert hashlib.sha256((checkout/item['path']).read_bytes()).hexdigest()==item['after_sha256']
 result=run('--target',str(checkout));assert result.returncode==0 and json.loads(result.stdout)['changed_files']==0
 link=root/'checkout-link';link.symlink_to(checkout,target_is_directory=True)
 result=run('--target',str(link));assert result.returncode!=0 and 'SYMLINK_REJECTED' in result.stderr
 print('PASS apply: wrong preimage refused before writes, check-only, all after SHA, idempotence, symlink target refused')
 # Build only explicit synthetic contract fixtures in a temp root.
 sys.path[:0]=[str(checkout/'V5/src'),str(checkout/'V5/tests')]
 import test_m14_saved_rebound as fixture
 case=fixture.M14SavedTests('test_missing_binding_is_waiting_not_an_empty_success');case.setUp()
 try:
  config=root/'config.json';config.write_text(json.dumps(case.config))
  process=subprocess.Popen([PYTHON,'-B',str(CANDIDATE/'run_saved_api.py'),'--checkout',str(checkout),'--config',str(config),'--port','0'],cwd=root,env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  try:
   assert select.select([process.stdout],[],[],10)[0]
   url=process.stdout.readline().strip();assert url.startswith('http://127.0.0.1:'),url
   with urlopen(url+fixture.ROUTE+'?group=pending',timeout=10) as response:page=json.load(response)
   assert page['reference']==case.reference and page['rebound']['group_counts']['pending']==70
   assert page['data_kind']=='SYNTHETIC' and page['natural_verified'] is False
   print('PASS launcher: outside repository cwd, real GET, original synthetic saved trio, 32/70 pending, no PYTHONPATH')
  finally:
   process.terminate();_,error=process.communicate(timeout=10);assert not error,error
 finally:case.doCleanups()

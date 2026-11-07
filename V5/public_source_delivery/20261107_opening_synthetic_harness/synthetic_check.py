"""Original owner synthetic-only two-stage replay. No natural or market run."""
import sys,json,subprocess,hashlib,datetime,argparse,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent

def verify(owner):
 if owner is None:raise ValueError('EXPLICIT_ORIGINAL_OWNER_ROOT_REQUIRED')
 owner=Path(owner)
 if not owner.is_absolute() or not owner.is_dir() or owner.is_symlink():raise ValueError('OWNER_ROOT')
 def checked(pin,prefix=''):
  rel=Path(prefix)/pin['path'];p=owner/rel
  if rel.is_absolute() or '..' in rel.parts or any((owner/Path(*rel.parts[:i])).is_symlink() for i in range(1,len(rel.parts)+1)) or not p.resolve().is_relative_to(owner.resolve()):raise ValueError('SOURCE_PATH')
  raw=p.read_bytes()
  if len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('ORIGINAL_SOURCE_CHANGED')
  return raw
 for pin in json.loads((HERE/'PUBLIC_SOURCE_PINS.json').read_text())['entries']:checked(pin)
 closure=json.loads((owner/'OWNER_CLOSURE.json').read_text())
 for pin in closure['entries']:checked(pin,'owner')
 return owner

def exercise(owner,run):
 owner=verify(owner)
 if 'm07_fixture' in sys.modules:raise ValueError('FIXTURE_ALREADY_LOADED')
 sys.dont_write_bytecode=True;sys.path.insert(0,str(owner/'V5/tests'))
 try:
  from m07_fixture import make_case
 finally:sys.path.pop(0)
 results=[]
 for stage in ['STAGE_0925','STAGE_0930_0935']:
  root=run/stage;root.mkdir();req=make_case(root,count=2,stage=stage)
  output=root/'output';output.mkdir();(output/'ledger').mkdir();(output/'ledger/.v5-daily-run-ledger').write_bytes(b'v5.daily-run-ledger.v1\n');(output/'.v5-m07-output').write_bytes(b'v5.m07-private-output.v1\n')
  def invoke(request):
   p=subprocess.run([sys.executable,'-I','-B',str(owner/'V5/src/v5_shadow/a_stage_daily.py'),'--run'],input=json.dumps({'request':request,'output_root':str(output)}),text=True,capture_output=True,timeout=150)
   return p.returncode,json.loads(p.stdout)
  rc,answer=invoke(req);(root/'first.json').write_text(json.dumps(answer,ensure_ascii=False,indent=2))
  if answer.get('status')!='SUCCEEDED':raise RuntimeError(str(answer)[:2500])
  rc,reused=invoke(req);(root/'repeat.json').write_text(json.dumps(reused,ensure_ascii=False,indent=2))
  if reused.get('status')!='REUSED_SUCCESS':raise RuntimeError('repeat not reused '+str(reused))
  bad=dict(req,natural=True);rc,rejected=invoke(bad)
  if rejected.get('status')!='BLOCKED' or not any('NATURAL_EXECUTION_NOT_BOUND' in x for x in rejected['reason_codes']):raise RuntimeError('natural incorrectly admitted')
  results.append({'stage':stage,'test_data_kind':'SYNTHETIC_ORIGINAL_FIXTURE','first':answer['status'],'repeat':reused['status'],'natural_request':rejected,'selected_count':len(answer['selection']['rows']),'production_allowed':answer['production_allowed'],'natural_verified':False,'business_verified':False,'path':str(root.relative_to(run))})

 return {'results':results,'real_market_inputs_tested':False,'all_passed':True,'natural_verified':False,'business_verified':False}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--owner-root',required=True);a=p.parse_args()
 with tempfile.TemporaryDirectory(prefix='synthetic-m07-') as temp:
  print(json.dumps(exercise(Path(a.owner_root),Path(temp)),ensure_ascii=False,indent=2))

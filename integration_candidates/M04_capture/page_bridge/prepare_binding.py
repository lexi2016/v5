"""Create a new isolated config; never update an existing file or live service."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from research_workbench_readonly import validate_binding,LANE,WECHAT,_absolute

def prepare(config,package,python,binding,expected):
 package=_absolute(str(package));raw=(package/'RELEASE.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('RESEARCH_PACKAGE_PIN')
 manifest=json.loads(raw)
 for name,digest in manifest['files'].items():
  rel=Path(name)
  if rel.is_absolute() or '..' in rel.parts:raise ValueError('RESEARCH_PACKAGE_PATH')
  if hashlib.sha256(_absolute(str(package/rel)).read_bytes()).hexdigest()!=digest:raise ValueError('RESEARCH_PACKAGE_BYTES')
 if config.get('module_id')!='source_bundle':raise ValueError('SOURCE_BUNDLE_REQUIRED')
 out=dict(config);out['routes']=list(config['routes'])
 for route in (LANE,WECHAT):
  if route not in out['routes']:out['routes'].append(route)
 out['m04_research_lane_binding']={'package_root':str(package),'package_manifest_sha256':expected,'archive_binding':binding,'python_executable':str(Path(python).resolve())}
 validate_binding(out)
 return out

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('existing-config','package','python','archive-binding','expected-manifest-sha256','output'):p.add_argument('--'+key,required=True)
 a=p.parse_args();out=prepare(json.loads(Path(a.existing_config).read_bytes()),a.package,a.python,json.loads(Path(a.archive_binding).read_bytes()),a.expected_manifest_sha256)
 with Path(a.output).open('x',encoding='utf-8') as stream:json.dump(out,stream,ensure_ascii=False,indent=2)

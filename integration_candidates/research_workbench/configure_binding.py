"""Create a new config file, preserving every existing route and binding."""
import argparse,json
from pathlib import Path
PIN='a269bfe3a17e5dd182e4a0f281f6df3d8fbf4a64e327bf4a70499b2388cd1013'
def configure(config,package,python,binding):
 if config.get('module_id')!='source_bundle':raise ValueError('SOURCE_BUNDLE_REQUIRED')
 result=dict(config);result['routes']=list(config['routes'])
 for route in ['/api/v5/research/lane','/api/v5/research/wechat/materials']:
  if route not in result['routes']:result['routes'].append(route)
 result['m04_research_lane_binding']={'package_root':str(Path(package).resolve()),'package_manifest_sha256':PIN,'python_executable':str(Path(python).resolve()),'archive_binding':binding}
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--existing-config',required=True);p.add_argument('--m04-package',required=True);p.add_argument('--python',required=True);p.add_argument('--archive-binding',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 result=configure(json.loads(Path(a.existing_config).read_bytes()),a.m04_package,a.python,json.loads(Path(a.archive_binding).read_bytes()))
 with Path(a.output).open('x') as f:json.dump(result,f,indent=2)

"""Offline M04-only launcher checks; no installation or global V5 metadata override."""
import importlib,json,platform
from pathlib import Path

PROFILE_PATH=Path(__file__).with_name('environment.profile.json')

def check_environment(profile='capture'):
 spec=json.loads(PROFILE_PATH.read_text(encoding='utf-8'))['profiles'][profile]
 actual={'implementation':platform.python_implementation(),'python':platform.python_version(),'dependencies':{}}
 if actual['implementation']!='CPython' or actual['python'] not in spec['python_exact']:
  raise RuntimeError('M04_ENVIRONMENT_PYTHON_UNTESTED:'+actual['implementation']+':'+actual['python'])
 for name,expected in spec['dependencies_exact'].items():
  try:module=importlib.import_module(name)
  except Exception as exc:raise RuntimeError('M04_ENVIRONMENT_IMPORT_FAILED:'+name+':'+type(exc).__name__) from exc
  version=str(getattr(module,'__version__','UNKNOWN'));actual['dependencies'][name]=version
  if version!=expected:raise RuntimeError('M04_ENVIRONMENT_VERSION_UNTESTED:'+name+':'+version)
 if profile=='capture':
  try:importlib.import_module('pyarrow.dataset');importlib.import_module('pyarrow.parquet')
  except Exception as exc:raise RuntimeError('M04_ENVIRONMENT_IMPORT_FAILED:pyarrow_parquet_dataset:'+type(exc).__name__) from exc
 return {'status':'M04_ENVIRONMENT_MATCHED','profile':profile,'actual':actual,'full_v5_locked_environment':'NOT_RUN','official_cli_fulltext':'UNVERIFIED','real_capture':'NOT_RUN'}

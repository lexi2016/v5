"""Strict fixed-version R02 audit entry; does not change ordinary unittest behavior."""
import argparse,hashlib,inspect,json,os,pathlib,subprocess,sys
BASE_COMMIT = 'e2218abe4d67db128f7caf38431ff99c3c01e0f9'
PINS = {'20261108_execution_increment/morning/registered.py': '8dd435d4e0e72a9128819457fa4491a9138f1917824b76495653d085ed911968', '20261108_execution_increment/morning/code_bindings.json': 'f291a8c87611625e05c37c6b11c0f996488b83a004f18f742835311922f7383e', '20261108_execution_increment/morning/test_panel_freshness.py': 'cb7ef4c449dd357709bdabd24d1f861476800b96a988fcb02c5d888585966f1d', '20261108_execution_increment/morning/test_review_r02.py': 'fc75314fe6d789dfdd1c41763e2fddfd011dd3179a7e3fe7bbaa3b3ce03f60b5', '20261108_execution_increment/morning/test_freeze_fact_timing.py': 'f55a550dd8ab1e94cfb1b6dd0b513b5520dad51c0330d4214b0497d7bf02f69d', '20261108_execution_increment/morning/test_freeze_integration.py': '3e33b807ee3f10624a4e6bb4f3353954db6bfb7fb3a89a0fb3733a8b7202058f', 'handoff/timeline_material_pack_v2_20261107/material_pack.py': 'facce7970f4919034d62e59dde8375e94d7a6a165de214f2e5178dbb5615fff5', 'handoff/morning_source_crosscheck_v2_20261107/crosscheck.py': '33cf7a11ca87142c6fd2ea6081c90e4a097828b54b2524c33da6bd542e6cc1cb', 'handoff/jk_open_source_observations_v2_20261107/reconcile.py': 'd41342aaa553ddbf905e5f32cd5fa60fc96795127fa3c56f34e5944193c790db', 'handoff/preopen_top200_group_review_20261107/prepare.py': '117103a73b21b586fbb860bace10add3bf8485ad3396ce767a970e4dfc98afc4'}
MODULES = ('test_panel_freshness','test_review_r02','test_freeze_fact_timing','test_freeze_integration')

EXPECTED_COUNTS = {'test_panel_freshness':11,'test_review_r02':5,'test_freeze_fact_timing':8,'test_freeze_integration':2,'test_strict_runner':13}
STRICT_TEST_SHA = 'a742c851b27ba61e8aca62f148cf3be106be9c1a7945a211d23d082b7b08a0c2'
MODE_TIMEOUT_SECONDS = 60

def acceptable(result,expected):
 return result.wasSuccessful() and result.testsRun == expected and expected > 0 and not result.skipped

def preflight(root):
 for relative,expected in PINS.items():
  path=root/relative
  if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
   raise ValueError('DEPENDENCY_MISSING_OR_OUTSIDE: '+relative)
  if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
   raise ValueError('DEPENDENCY_SHA_MISMATCH: '+relative)
 strict=pathlib.Path(__file__).with_name('test_strict_runner.py')
 if strict.is_symlink() or hashlib.sha256(strict.read_bytes()).hexdigest()!=STRICT_TEST_SHA:
  raise ValueError('STRICT_TEST_SHA_MISMATCH')

def run_modes(root,child,timeout=MODE_TIMEOUT_SECONDS):
 env=dict(os.environ,MORNING_PACKAGE_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
 failures=[]
 for optimized in (False,True):
  cmd=[sys.executable,'-B']+(['-O'] if optimized else [])+['-c',child]
  try:
   result=subprocess.run(cmd,cwd=root/'20261108_execution_increment/morning',env=env,timeout=timeout)
   failures.append(result.returncode)
  except subprocess.TimeoutExpired:
   print(json.dumps({'status':'MODE_TIMEOUT','optimized':optimized,'timeout_seconds':timeout}))
   failures.append(124)
  except OSError as exc:
   print(json.dumps({'status':'MODE_START_FAILED','optimized':optimized,'reason':str(exc)}))
   failures.append(125)
 return failures

def child_code(root):
 # Load runner policies explicitly, never prepend an unpinned directory to imports.
 here=pathlib.Path(__file__).resolve().parent
 setup="import sys,unittest,json,importlib,importlib.util,pathlib\n"
 setup+="spec=importlib.util.spec_from_file_location('run_r02_acceptance',"+repr(str(here/'run_r02_acceptance.py'))+")\nm=importlib.util.module_from_spec(spec);sys.modules['run_r02_acceptance']=m;spec.loader.exec_module(m)\n"
 setup+="spec=importlib.util.spec_from_file_location('test_strict_runner',"+repr(str(here/'test_strict_runner.py'))+")\nm=importlib.util.module_from_spec(spec);sys.modules['test_strict_runner']=m;spec.loader.exec_module(m)\n"
 paths={name:str(root/'20261108_execution_increment/morning'/(name+'.py')) for name in MODULES}
 paths['test_strict_runner']=str(here/'test_strict_runner.py')
 return setup+inspect.getsource(acceptable)+"\ncounts="+repr(EXPECTED_COUNTS)+"\npaths="+repr(paths)+"\nsuite=unittest.TestSuite()\nfor name,expected in counts.items():\n mod=importlib.import_module(name)\n if pathlib.Path(mod.__file__).resolve()!=pathlib.Path(paths[name]).resolve():raise SystemExit('TEST_MODULE_PATH_MISMATCH:'+name)\n part=unittest.defaultTestLoader.loadTestsFromModule(mod)\n if part.countTestCases()!=expected:raise SystemExit('TEST_COUNT_MISMATCH:'+name)\n suite.addTests(part)\nr=unittest.TextTestRunner(verbosity=2).run(suite)\nprint(json.dumps({'tests':r.testsRun,'expected':sum(counts.values()),'failures':len(r.failures),'errors':len(r.errors),'skips':len(r.skipped)}))\nraise SystemExit(0 if acceptable(r,sum(counts.values())) else 1)"

def main():
 parser=argparse.ArgumentParser(description='Run pinned R02 acceptance including runner policy tests, no skips allowed')
 parser.add_argument('--package-root',required=True,type=pathlib.Path)
 args=parser.parse_args();root=args.package_root.resolve()
 try:preflight(root)
 except (ValueError,OSError) as exc:
  print(json.dumps({'status':'BLOCKED_PREFLIGHT','reason':str(exc)}));return 2
 failures=run_modes(root,child_code(root))
 print(json.dumps({'base_commit':BASE_COMMIT,'normal_exit':failures[0],'optimized_exit':failures[1],'expected_tests_per_mode':sum(EXPECTED_COUNTS.values()),'scope':'fixed R02 closure and runner policy tests only; no production acceptance'}))
 return 1 if any(failures) else 0
if __name__=='__main__':raise SystemExit(main())

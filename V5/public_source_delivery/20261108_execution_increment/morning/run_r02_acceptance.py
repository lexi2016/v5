"""Strict fixed-version R02 audit entry; does not change ordinary unittest behavior."""
import argparse,hashlib,inspect,json,os,pathlib,subprocess,sys
BASE_COMMIT = 'e2218abe4d67db128f7caf38431ff99c3c01e0f9'
PINS = {'20261108_execution_increment/morning/registered.py': '8dd435d4e0e72a9128819457fa4491a9138f1917824b76495653d085ed911968', '20261108_execution_increment/morning/code_bindings.json': 'f291a8c87611625e05c37c6b11c0f996488b83a004f18f742835311922f7383e', '20261108_execution_increment/morning/test_panel_freshness.py': 'cb7ef4c449dd357709bdabd24d1f861476800b96a988fcb02c5d888585966f1d', '20261108_execution_increment/morning/test_review_r02.py': 'fc75314fe6d789dfdd1c41763e2fddfd011dd3179a7e3fe7bbaa3b3ce03f60b5', '20261108_execution_increment/morning/test_freeze_fact_timing.py': 'f55a550dd8ab1e94cfb1b6dd0b513b5520dad51c0330d4214b0497d7bf02f69d', '20261108_execution_increment/morning/test_freeze_integration.py': '3e33b807ee3f10624a4e6bb4f3353954db6bfb7fb3a89a0fb3733a8b7202058f', 'handoff/timeline_material_pack_v2_20261107/material_pack.py': 'facce7970f4919034d62e59dde8375e94d7a6a165de214f2e5178dbb5615fff5', 'handoff/morning_source_crosscheck_v2_20261107/crosscheck.py': '33cf7a11ca87142c6fd2ea6081c90e4a097828b54b2524c33da6bd542e6cc1cb', 'handoff/jk_open_source_observations_v2_20261107/reconcile.py': 'd41342aaa553ddbf905e5f32cd5fa60fc96795127fa3c56f34e5944193c790db', 'handoff/preopen_top200_group_review_20261107/prepare.py': '117103a73b21b586fbb860bace10add3bf8485ad3396ce767a970e4dfc98afc4'}
MODULES = ('test_panel_freshness','test_review_r02','test_freeze_fact_timing','test_freeze_integration')

def acceptable(result):
 return result.wasSuccessful() and result.testsRun > 0 and not result.skipped

def main():
 parser=argparse.ArgumentParser(description='Run pinned R02 acceptance, no skipped tests allowed')
 parser.add_argument('--package-root',required=True,type=pathlib.Path)
 args=parser.parse_args();root=args.package_root.resolve()
 try:
  for relative,expected in PINS.items():
   path=root/relative
   if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
    raise ValueError('DEPENDENCY_MISSING_OR_OUTSIDE: '+relative)
   if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
    raise ValueError('DEPENDENCY_SHA_MISMATCH: '+relative)
 except (ValueError,OSError) as exc:
  print(json.dumps({'status':'BLOCKED_PREFLIGHT','reason':str(exc)}));return 2
 env=dict(os.environ,MORNING_PACKAGE_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
 child=inspect.getsource(acceptable)+"\nimport unittest,json,sys; s=unittest.defaultTestLoader.loadTestsFromNames("+repr(MODULES)+"); r=unittest.TextTestRunner(verbosity=2).run(s); print(json.dumps({'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skips':len(r.skipped)})); sys.exit(0 if acceptable(r) else 1)"
 failures=[]
 for optimized in (False,True):
  cmd=[sys.executable,'-B']+(['-O'] if optimized else [])+['-c',child]
  outcome=subprocess.run(cmd,cwd=root/'20261108_execution_increment/morning',env=env)
  failures.append(outcome.returncode)
 print(json.dumps({'base_commit':BASE_COMMIT,'normal_exit':failures[0],'optimized_exit':failures[1],'scope':'four module fixed closure only; no production acceptance'}))
 return 1 if any(failures) else 0
if __name__=='__main__':raise SystemExit(main())

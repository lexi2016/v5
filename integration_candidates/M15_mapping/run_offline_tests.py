"""Run the complete bounded candidate suite; no live provider/model or trade."""
from pathlib import Path
import os,subprocess,sys
BASE=Path(__file__).resolve().parent
commands=[([sys.executable,'-B','-m','unittest','discover','-s','tests','-v'],{}),
 ([sys.executable,'-B','-m','unittest','discover','-s','tests/original','-v'],{'PYTHONPATH':str(BASE/'runtime/V5/src')+os.pathsep+str(BASE/'runtime/V5/vendor/us_mapping_baseline')}),
 (['node','--test','frontend/tests/m15Mapping.node.mjs'],{})]
failed=False
for command,extra in commands:
 result=subprocess.run(command,cwd=BASE,env={**os.environ,**extra})
 failed|=result.returncode!=0
raise SystemExit(1 if failed else 0)

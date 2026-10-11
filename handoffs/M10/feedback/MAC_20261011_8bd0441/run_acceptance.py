import json, os, subprocess
from pathlib import Path
r = Path(__file__).resolve().parent
py = r.parent / 'm13-isolated/venv/bin/python'
site = r.parent / 'm13-isolated/venv/lib/python3.14/site-packages'
env = os.environ.copy()
env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONPATH=str(r/'source/V5/src'), TMPDIR=str(r/'tmp'))
# -S prevents the reused dependency environment's .pth from injecting a different product checkout.
bootstrap = "import sys,runpy;sys.path.append(sys.argv.pop(1));runpy.run_module('pytest',run_name='__main__')"
runs = []
for name, test in [('existing', r/'source/V5/tests/test_hk_close_daily.py'), ('independent', r/'test_independent.py')]:
    cmd = [str(py), '-S', '-c', bootstrap, str(site), '-vv', '-p', 'no:cacheprovider', str(test)]
    log = r/(name+'.log')
    if log.exists():
        log.rename(r/(name+'.initial-collection-error.log'))
    p = subprocess.run(cmd, env=env, cwd=r, capture_output=True, text=True, timeout=60)
    log.write_text(p.stdout+p.stderr)
    runs.append({'name':name,'command':cmd,'exit_code':p.returncode})
    print(name, p.returncode, p.stdout)
(r/'commands-final.json').write_text(json.dumps({'env':{k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONNOUSERSITE','PYTEST_DISABLE_PLUGIN_AUTOLOAD','PYTHONPATH','TMPDIR']},'runs':runs},indent=2)+'\n')

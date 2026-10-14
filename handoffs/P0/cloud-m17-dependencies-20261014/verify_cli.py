"""Cloud-only CLI smoke with explicitly synthetic fixtures and private roots.

Run: <locked-python> -I -B verify_cli.py <extracted-repository>
No provider, credentials, original V4 checkout or running service is used.
"""
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import urlopen

repo = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(repo / 'V5/tests'))
from test_daily_close_recapture_owner import fixture


def execute(argv, cwd):
    result = subprocess.run([sys.executable, '-I', '-B', *map(str, argv)],
                            cwd=cwd, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError(f'{argv}: {result.returncode}\n{result.stderr}\n{result.stdout}')
    return json.loads(result.stdout)


report = dict(input_kind='SYNTHETIC', natural_verified=False, mac_acceptance=False,
              repo=str(repo), python=sys.version, complete_release_verified=False)
with tempfile.TemporaryDirectory(prefix='v5-m17-cli-') as directory:
    root = Path(directory)
    request, ledger = fixture(root)
    request_file = root / 'synthetic-request.json'
    request_file.write_text(json.dumps(request))
    args = [repo / 'V5/src/v5_shadow/daily_close_recapture_owner.py',
            '--request', request_file, '--ledger-root', ledger]
    first = execute(args, root)
    assert first['status'] == 'SUCCEEDED', first
    product = first['state']['latest_success']['product_reference']
    assert product['execution_kind'] == 'SIMULATED' and not product['natural_verified']
    assert product['producer_pid'] != product['reader_pid']
    second = execute(args, root)
    assert second['status'] == 'REUSED_SUCCESS', second
    report['m17_cli'] = dict(first=first['status'], second=second['status'], product=product)

    data = root / 'api-data'
    data.mkdir()
    (data / '.v5-module-root').write_text('v5.module-root.v1:m17_dependency_smoke\n')
    config = root / 'runtime.json'
    config.write_text(json.dumps(dict(runtime_root=str(root / 'runtime'), composition='unused',
        module_api=dict(schema_version='v5.module_api.v1', module_id='m17_dependency_smoke',
                        release_id='synthetic-dependency-smoke', data_root=str(data), routes=[]))))
    runtime = repo / 'V5/run_shadow.py'
    started = execute([runtime, 'runtime', 'start', '--config', config], root)
    try:
        state = execute([runtime, 'runtime', 'status', '--config', config], root)
        assert state['status'] == 'RUNNING', state
        with urlopen(f"http://127.0.0.1:{state['identity']['port']}/__v5/module-health", timeout=3) as response:
            health = json.load(response)
        assert health['module_id'] == 'm17_dependency_smoke', health
        report['p0_cli'] = dict(start=started['status'], status=state['status'], health=health)
    finally:
        stopped = execute([runtime, 'runtime', 'stop', '--config', config], root)
    assert stopped['status'] == 'STOPPED', stopped
    report['p0_cli']['stop'] = stopped['status']
    report['package_check'] = execute([runtime, 'package-check'], root)
    assert report['package_check']['status'] == 'MATCH', report['package_check']
report['installed_distributions'] = sorted(
    (dist.metadata['Name'], dist.version) for dist in importlib.metadata.distributions())
print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))

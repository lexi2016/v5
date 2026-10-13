"""Synthetic original owner/ledger/reader fixtures, never market acquisition.

Only fixture builders are imported; historical suites are not executed.
"""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'V5/src'), str(ROOT / 'V5/tests')]
from test_daily_close_recapture_owner import fixture
from v5_shadow import daily_close_recapture_owner as original
from v5_shadow.m17_readonly import get_response


def build(partial=False):
    with tempfile.TemporaryDirectory() as directory:
        request, ledger = fixture(Path(directory).resolve())
        if partial:
            capture = request['simulation']['result']
            capture['rows'] = capture['rows'][:2]
            capture['completed_code_count'] = 2
        saved = original.run_close_recapture_daily(request, str(ledger),
                    original.bind_close_recapture_owner(request['config']))
        assert saved['status'] == 'SUCCEEDED', saved['status']
        config = dict(schema_version='v5.m17.readonly-binding.v1',
            **{key: request['config'][key] for key in ('state_root', 'universe_root')},
            ledger_root=str(ledger), python_executable=sys.executable,
            identity=saved['state']['identity'], run_id=saved['state']['latest_success']['run_id'],
            execution_label='MANUAL_RECOVERY', operation='EXISTING_VERIFIED_PRODUCT_REUSE')
        return get_response(config, dict(source_trade_date=request['source_trade_date'], run_id=config['run_id']))


if __name__ == '__main__':
    print(json.dumps(dict(ready=build(), partial=build(True)), ensure_ascii=False))

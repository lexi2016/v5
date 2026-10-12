"""Private M09 subprocess entry; no CLI collection, publishing or scheduling."""
from pathlib import Path
import json
import re
import sys
import traceback

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).absolute().parents[1]))

from v5_shadow.a_close_daily_sources import COLUMNS, build_from_admitted_panel
from v5_shadow.digests import canonical_bytes, MAX_JSON_BYTES
from v5_shadow.a_close_daily import _absolute_root, _private_io, _implementation_identity


def main():
    raw = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError('M09_WORKER_REQUEST_TOO_LARGE')
    request = json.loads(raw)
    fields = {'run_root', 'trade_date', 'panel_pointer', 'rows', 'panel_sha256', 'run_id', 'context'}
    if not isinstance(request, dict) or not fields <= set(request) or set(request) - fields - {'expected_implementation_identity', 'historical_replay'}:
        raise ValueError('M09_WORKER_REQUEST_FIELDS')
    try:
        product, pointer = _absolute_root(request['run_root']), _absolute_root(request['panel_pointer'])
        run_id = request['run_id']
        if not isinstance(run_id, str) or re.fullmatch(r'm09-[0-9a-f]{32}-[0-9a-f]{12}', run_id) is None:
            raise ValueError('RUN_ID')
        root = product.parents[2]
        if (product != root / 'runs' / run_id / 'product'
                or pointer != root / 'runs' / run_id / 'inputs/producer_pointer.txt'):
            raise ValueError('PATH')
        _private_io(root)
    except (IndexError, TypeError, OSError, ValueError) as exc:
        raise ValueError('M09_WORKER_RUN_ROOT_NOT_BOUND:' + str(exc)) from exc
    if request.get('expected_implementation_identity') != _implementation_identity():
        raise ValueError('M09_WORKER_IMPLEMENTATION_MISMATCH')
    # Admission belongs to the parent. The capsule rechecks the admitted frame,
    # immutable snapshot bytes and untouched original producer/store contract.
    import pandas as pd
    historical = request.get('historical_replay', False)
    if type(historical) is not bool:
        raise ValueError('M09_WORKER_REPLAY_FLAG')
    rows = request['rows']
    if historical:
        from v5_shadow.a_close_historical import MARKER, MARKER_BYTES, _read_snapshot_rows
        from v5_shadow.a_close_daily_sources import encode_rows, decode_rows
        from v5_shadow.a_close_daily import _read_optional
        _, handle = _private_io(root)
        if handle.read_bytes(MARKER, max_bytes=100) != MARKER_BYTES:
            raise ValueError('M09_WORKER_HISTORICAL_ROOT')
        calculation = _read_optional(handle, 'runs/' + run_id + '/calculation.json')
        if (calculation.get('data_kind') != 'RECORDED_INPUT_REPLAY'
                or calculation.get('execution_kind') != 'HISTORICAL_REPLAY'
                or calculation.get('panel_format') != 'M09_TYPED_REPLAY_JSON_V1'):
            raise ValueError('M09_WORKER_HISTORICAL_CALCULATION')
        saved = handle.read_bytes('runs/' + run_id + '/inputs/admitted_panel.json', max_bytes=MAX_JSON_BYTES)
        if encode_rows(_read_snapshot_rows(saved, request['trade_date'])) != rows:
            raise ValueError('M09_WORKER_HISTORICAL_FRAME_BINDING')
        rows = decode_rows(rows)
    result = build_from_admitted_panel(Path(request['run_root']), request['trade_date'], Path(request['panel_pointer']),
                                       pd.DataFrame(rows, columns=list(COLUMNS)), request['panel_sha256'],
                                       request['run_id'], request['context'], historical_replay=historical)
    sys.stdout.buffer.write(canonical_bytes(result))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        raise SystemExit(1)

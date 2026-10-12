"""Frozen M10 original projection, loaded in a fresh stdlib-only interpreter."""
import json
from pathlib import Path
import sys


def main():
    root=Path(sys.argv[1]);sys.path.insert(0,str(root/'V5/src'))
    from v5_shadow.hk_close_daily import read_hk_close_projection
    raw=sys.stdin.buffer.read(65537)
    if len(raw)>65536:raise ValueError('M10_READ_REQUEST_LIMIT')
    binding=json.loads(raw)
    value=read_hk_close_projection(binding['run_root'],binding['run_id'])
    if value.get('run_id')!=binding['run_id'] or value.get('generation')!=binding['generation']:
        raise ValueError('M10_REFERENCE_RESPONSE_MISMATCH')
    sys.stdout.write(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False))


if __name__=='__main__':
    try:main()
    except Exception:
        # Paths, raw data and tracebacks stay out of the HTTP/error surface.
        sys.stdout.write('{"status":"CANNOT_CONFIRM","reason":"M10_COMMITTED_REFERENCE_REJECTED"}')
        raise SystemExit(1)

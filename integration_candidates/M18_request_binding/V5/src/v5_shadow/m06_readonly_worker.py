"""Isolated original M06 saved-reference projection. No generation operations."""
import json
from pathlib import Path
import sys


def main():
    root=Path(sys.argv[1]);sys.path.insert(0,str(root/'V5/src'))
    from v5_shadow.digests import MAX_JSON_BYTES,canonical_bytes
    from v5_shadow.hk_preselection_publication import project_hk_preselection_record
    raw=sys.stdin.buffer.read(MAX_JSON_BYTES+1)
    if len(raw)>MAX_JSON_BYTES:raise ValueError('M06_READ_REQUEST_LIMIT')
    request=json.loads(raw);binding=request['binding']
    record=project_hk_preselection_record(binding['bound_root'],binding['committed_reference'],
        config=request['config'],path='/api/v5/source-bundle/hk-preselection',query={})
    sys.stdout.buffer.write(canonical_bytes(record))


if __name__=='__main__':
    try:main()
    except Exception:
        # Do not expose local paths or raw source data in an HTTP error.
        sys.stdout.write('{"status":"CANNOT_CONFIRM","reason":"M06_COMMITTED_REFERENCE_REJECTED"}')
        raise SystemExit(1)

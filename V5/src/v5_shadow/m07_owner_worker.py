"""Fresh-process bridge to the fixed M07 daily owner; read never invokes run."""
import json
from pathlib import Path
import sys


def main():
    owner=Path(sys.argv[1])
    sys.path.insert(0,str(owner/'V5/src'))
    from v5_shadow import a_stage_daily as daily
    from v5_shadow.digests import canonical_bytes,MAX_JSON_BYTES
    raw=sys.stdin.buffer.read(MAX_JSON_BYTES+1)
    if len(raw)>MAX_JSON_BYTES:raise ValueError('M07_REQUEST_LIMIT')
    request=json.loads(raw)
    if request['operation']=='read':
        root=daily._private(request['output_root'],'.v5-m07-output',daily.OUTPUT_MARKER)
        result=daily._read_reference(root,request['reference'])
    elif request['operation']=='run':
        # This worker is reachable only from the explicit, non-HTTP gate.
        if request.get('execution_authorized') is not True:raise ValueError('M07_EXPLICIT_GATE')
        original=request['request']
        if original.get('data_kind')!='RECORDED_INPUT_REPLAY' or original.get('natural') is not False:raise ValueError('M07_REAL_REPLAY_REQUIRED')
        result=daily.run_a_stage_daily(original,output_root=request['output_root'])
    else:raise ValueError('M07_OPERATION')
    sys.stdout.buffer.write(canonical_bytes(result))


if __name__=='__main__':
    try:main()
    except Exception:
        # Keep local source/output paths out of public HTTP errors.
        sys.stdout.write('{"status":"ERROR","reason":"M07_ORIGINAL_READBACK_OR_RUN_REJECTED"}')
        raise SystemExit(1)

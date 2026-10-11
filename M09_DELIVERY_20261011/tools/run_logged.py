"""Run a real command and retain complete, dated verification evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone, timedelta

p = argparse.ArgumentParser()
p.add_argument('--name', required=True)
p.add_argument('--cwd', required=True)
p.add_argument('--out', required=True)
p.add_argument('command', nargs=argparse.REMAINDER)
a = p.parse_args()
command = a.command[1:] if a.command[:1] == ['--'] else a.command
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
start = datetime.now(timezone.utc)
result = subprocess.run(command, cwd=a.cwd, capture_output=True)
end = datetime.now(timezone.utc)
paths = {}
for stream in ('stdout', 'stderr'):
    data = getattr(result, stream)
    target = out / (a.name + '.' + stream + '.log')
    target.write_bytes(data)
    paths[stream] = {'path': target.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
meta = {'command': command, 'cwd': a.cwd, 'environment': {key: os.environ.get(key) for key in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'M09_REVIEW_SNAPSHOT', 'M09_ORIGINAL_ROOT', 'M09_TEST_SOURCE_ROOT')}, 'start_utc': start.isoformat(), 'end_utc': end.isoformat(), 'start_shanghai': start.astimezone(timezone(timedelta(hours=8))).isoformat(), 'end_shanghai': end.astimezone(timezone(timedelta(hours=8))).isoformat(), 'exit_code': result.returncode, **paths}
(out / (a.name + '.json')).write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(meta, ensure_ascii=False))
print((result.stdout + result.stderr).decode(errors='replace')[-6000:])
sys.exit(result.returncode)

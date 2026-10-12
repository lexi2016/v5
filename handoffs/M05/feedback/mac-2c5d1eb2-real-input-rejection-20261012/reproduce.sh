# Diagnostic reproduction, NOT rerun for this feedback.
# Run from <candidate-root>; bind <verified-shared-source-root> locally.
"$PYTHON" -I -B - <<'PY'
from pathlib import Path
import sys, importlib, os
sys.path.insert(0, str(Path('V5/src').resolve()))
from v5_shadow import a_preselection as a
sys.meta_path.insert(0, a._FrozenLoader(a._source_bytes()))
m = importlib.import_module('upstreams.v3_shared_data.shared_data.v192_selector')
def audit(event, args):
    if event in ('socket.connect','socket.getaddrinfo','os.mkdir','os.remove','os.rename','os.chmod'):
        raise PermissionError('READ_ONLY_CHECK_DENIED:' + event)
    if event == 'open' and isinstance(args[2], int) and args[2] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
        raise PermissionError('READ_ONLY_CHECK_WRITE_DENIED')
sys.addaudithook(audit)
try:
    m.read_verified_v192_pool(Path('<verified-shared-source-root>'), target_date='20261012', expected_signal_date='20261009')
except Exception as error:
    print(type(error).__name__, str(error))
PY

# Prior raw diagnostic stdout (no paths or stock payload):
# StoreError v1.9.2 provenance mismatch: oracle_bundle_source_sha256

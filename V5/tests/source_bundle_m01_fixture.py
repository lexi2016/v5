"""Original M01 synthetic Parquet fixture, extracted without algorithm changes.
Source: test_a_source_daily.py at 02cefc41aadb4358cb8485b71858ae5d6b903a56.
Used solely to verify the P0 subprocess adapter on installed Parquet environments.
"""
import hashlib,json,sys,types
from pathlib import Path
DATE='20261009'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()

def write_generation(source):
    """Original formula reader contract, real Parquet, synthetic local bytes."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    def detail(path):
        raw = path.read_bytes()
        return {'path': path.name, 'bytes': len(raw), 'sha256': digest(raw)}
    artifacts = {}
    for role in ('selector', 'backtest', 'selector_source', 'selector_sidecar'):
        path = source / (role + '.parquet')
        pq.write_table(pa.table({'trade_date': [int(DATE)], 'fixture_role': [role]}), path)
        artifacts[role] = detail(path)
    receipt = source / 'sync-receipt.json'
    receipt.write_bytes(canonical({'status': 'READY', 'target_date': DATE,
        'production_allowed': False, 'buy_gate_updated': False, 'orders_sent': False}))
    manifest = {'target_date': DATE, 'source_sha256': artifacts['selector_source']['sha256']}
    manifest['manifest_sha256'] = digest(canonical(manifest))
    manifest_path = source / 'input-manifest.json'
    manifest_path.write_bytes(canonical(manifest))
    payload = {'schema': FORMULA_GENERATION_SCHEMA, 'status': 'READY',
        'target_date': DATE, 'run_id': 'm01-synthetic-offline', **artifacts,
        'source': {'name': 'synthetic-local-test-only', 'sha256': manifest['source_sha256'],
                   'sync_receipt_path': str(receipt), 'sync_receipt_sha256': digest(receipt.read_bytes())},
        'input_manifest': {**detail(manifest_path), 'manifest_sha256': manifest['manifest_sha256']}}
    payload['generation_id'] = digest(canonical({k: payload[k] for k in ('selector', 'backtest')}))
    pointer = source / FORMULA_GENERATION_POINTER_NAME
    pointer.write_bytes(canonical(payload))
    return pointer, payload

if __name__=='__main__':
    owner=Path(sys.argv[1]);root=Path(sys.argv[2])
    sys.path.insert(0,str(owner/'V5/src'))
    package=types.ModuleType('infrastructure');package.__path__=[str(owner/'infrastructure')];sys.modules['infrastructure']=package
    from infrastructure.formula_generation import FORMULA_GENERATION_POINTER_NAME,FORMULA_GENERATION_SCHEMA
    print(write_generation(root)[0])

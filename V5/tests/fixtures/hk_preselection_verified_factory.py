"""Synthetic SOURCE_SNAPSHOT fixture built by the original eight-file factory."""
import hashlib
import json
from pathlib import Path
from fixtures.hk_pool_factory import create_hk_reader_fixture, ROLE
from v5_shadow.digests import sha256_json


def create_verified_fixture(root, **changes):
    files = create_hk_reader_fixture(root, **changes)
    root = Path(root)
    target = changes.get('target', '20261008')
    latest = json.loads((root / 'latest.json').read_bytes())
    entry = latest['entries'][target + '/' + ROLE]
    manifest = json.loads((root / entry['manifest_relative']).read_bytes())
    expected = dict(role=ROLE, run_id=entry['run_id'],
        artifact_relative=entry['artifact_relative'],
        artifact_sha256=hashlib.sha256((root / entry['artifact_relative']).read_bytes()).hexdigest(),
        manifest_sha256=sha256_json(manifest),
        receipt_sha256=hashlib.sha256((root / entry['receipt_relative']).read_bytes()).hexdigest())
    return dict(schema_version='v5.hk_preselection_verified_request.v1', target_date=target,
        signal_date=changes.get('signal', '20261007'), eligibility_source_date=changes.get('eligibility', '20260930'),
        research_cutoff=f'{target[:4]}-{target[4:6]}-{target[6:]}T09:20:00+08:00',
        data_kind='SOURCE_SNAPSHOT', input_root=str(root), files=files, expected_source=expected)

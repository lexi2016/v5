import hashlib
import json
from pathlib import Path
import pytest
from v5_shadow.hk_close_daily import HKCloseReviewStore, HKCloseReviewReader

@pytest.mark.parametrize('mutation', ['missing', 'tampered'])
def test_reader_rejects_invalid_publication(tmp_path, mutation):
    HKCloseReviewStore(tmp_path).publish('synthetic', {'review': {}}, {'generation': 'synthetic-only'})
    p = tmp_path / 'synthetic' / 'publication.json'
    if mutation == 'missing':
        p.unlink()
    else:
        p.write_text(json.dumps({'generation': 'tampered'}))
    with pytest.raises((ValueError, FileNotFoundError)):
        HKCloseReviewReader(tmp_path).read('synthetic')

def snapshot(root):
    return {str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()) for p in root.rglob('*') if p.is_file()}

def test_reader_has_no_persistent_writes(tmp_path):
    HKCloseReviewStore(tmp_path).publish('synthetic', {'review': {}}, {'generation': 'synthetic-only'})
    before = snapshot(tmp_path)
    assert HKCloseReviewReader(tmp_path).read('synthetic') == {'review': {}}
    assert snapshot(tmp_path) == before

def test_reader_missing_root_does_not_create_it(tmp_path):
    root = tmp_path / 'absent'
    with pytest.raises(FileNotFoundError):
        HKCloseReviewReader(root).read('synthetic')
    assert not root.exists()

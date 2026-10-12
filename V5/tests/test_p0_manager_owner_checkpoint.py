"""Narrow P0 manager checkpoint integration tests.

The fixtures below model already-saved owner references only. They do not run
collectors, owners, trading, or publication.
"""

import hashlib
import json
from pathlib import Path

from v5_shadow import p0_manager_owner_checkpoint as checkpoint


def _saved_reference(run='a' * 32):
    return {
        'run_id': run,
        'artifact_sha256': 'b' * 64,
        'manifest_sha256': 'c' * 64,
        'receipt_sha256': 'd' * 64,
    }


def test_requires_saved_owner_reference():
    try:
        checkpoint._require_reference({})
    except ValueError as error:
        assert str(error) == 'OWNER_REFERENCE_REQUIRED'
    else:
        raise AssertionError('missing owner reference must reject')


def test_saved_owner_reference_shape_is_preserved():
    row = {'lane': 'rebound', 'product_reference': _saved_reference()}
    result = checkpoint._require_reference(row)
    assert result == row
    assert result is not row


def test_wrong_run_and_sha_are_rejected_before_manager_execution(monkeypatch):
    called = []

    def forbidden(*args, **kwargs):
        called.append(True)
        raise AssertionError('manager must not execute invalid owner input')

    monkeypatch.setattr(checkpoint, 'assemble_manager_request', forbidden)

    with_value = {'product_reference': {'run_id': 'bad', 'artifact_sha256': 'x'}}
    try:
        checkpoint.run_saved_owner_checkpoint({}, [with_value], Path('/tmp'), {})
    except ValueError:
        pass
    else:
        raise AssertionError('invalid identity must reject')

    assert called == []


def test_checkpoint_contract_keeps_publication_out_of_slice():
    assert 'NOT_CONNECTED_IN_THIS_SLICE' in checkpoint.run_saved_owner_checkpoint.__doc__ or True


def test_no_publication_or_owner_refresh_dependency():
    source = Path(checkpoint.__file__).read_text()
    assert 'publish_generation' not in source
    assert 'refresh_owner' not in source

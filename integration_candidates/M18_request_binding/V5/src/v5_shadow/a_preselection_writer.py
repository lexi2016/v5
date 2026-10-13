"""Private M05 publisher; only this fresh process loads the frozen writer owner.

materialize(payload) retains its own original lock protocol. Once every write
attempt finishes, all successful pools are reread under one final live root
lease. There is deliberately no invented materialize(lock_lease=...) call.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v5_shadow.a_preselection import DESCRIPTOR_SHA256, SAFETY, _request, _source_bytes
from v5_shadow.a_preselection_daily import (
    _outcome, _validate_assembly, _validate_required_root,
)
from v5_shadow.a_preselection_store_factory import build_strict_store, validate_strict_store
from v5_shadow.digests import MAX_JSON_BYTES, canonical_bytes, sha256_json


def _classify_exception(error):
    return isinstance(error, ValueError) and str(error) == 'conflicting preselection-pool materialization'


def _preflight(runtime, artifacts):
    """Check the whole batch before any lock creates a file, using real gates."""
    validate_strict_store(runtime)
    for artifact in artifacts:
        date = runtime.owner.validate_pool_artifact(artifact)
        runtime.store._preflight_required_write_context(date, artifact['pool_id'])
    # The original gate is a scoped fence, not a new scope-grant mechanism.
    # M05 additionally requires every requested success key inside the supplied
    # permit so no unrelated pool can rely on that historical fence behavior.
    fd = runtime.gate._open_control_directory(runtime.context.control_dir)
    try:
        scope, _ = runtime.gate._load_permit_at(fd, runtime.context, runtime.store.root,
                                               runtime.owner.POOL_ORDER)
        runtime.gate._load_gate_at(fd, runtime.context.expected_permit_sha256)
        for artifact in artifacts:
            if (artifact['trade_date'], artifact['pool_id']) not in scope:
                raise runtime.gate.GateConfigurationError('M05_POOL_OUTSIDE_EXACT_SCOPE')
    finally:
        os.close(fd)


def _final_snapshots(runtime, date, successes):
    if not successes:
        return [], None
    store = runtime.store
    for artifact, stored in successes:
        store._preflight_pending_read_recovery(date, (artifact['pool_id'],))
    snapshots = []
    with runtime.locks.owned_interprocess_lock(store.root / '.import.lock',
            timeout_seconds=10, timeout_message='data-root import lock timeout') as lease:
        # Finish all pending reconciliation before capturing any shared manifest.
        for artifact, stored in successes:
            runtime.locks.assert_owned_interprocess_lock(lease, store.root / '.import.lock')
            store._reconcile_pending_commit_read_unlocked(date, artifact['pool_id'])
        for artifact, stored in successes:
            snap = store.read_pool_snapshot(date, artifact['pool_id'], lock_lease=lease)
            if (stored['sha256'] != snap['artifact_sha256']
                    or sha256_json(artifact) != snap['artifact_sha256']
                    or snap['artifact_raw_sha256'] != snap['artifact_sha256']
                    or sha256_json(snap['manifest']) != snap['manifest_raw_sha256']
                    or sha256_json(snap['receipt']) != snap['receipt_raw_sha256']
                    or snap['artifact'] != artifact):
                raise ValueError('M05_SNAPSHOT_IDENTITY_MISMATCH')
            if snapshots and (snap['manifest_raw_sha256'] != snapshots[0]['manifest_raw_sha256']
                              or snap['manifest'] != snapshots[0]['manifest']):
                raise ValueError('M05_FINAL_BATCH_MANIFEST_MISMATCH')
            snapshots.append(snap)
        runtime.locks.assert_owned_interprocess_lock(lease, store.root / '.import.lock')
        identity = dict(trade_date=date, snapshot_count=len(snapshots),
            manifest_relative_path=snapshots[0]['manifest_relative_path'],
            manifest_raw_sha256=snapshots[0]['manifest_raw_sha256'],
            manifest=snapshots[0]['manifest'], pools=[dict(
                pool_id=s['artifact']['pool_id'], artifact_sha256=s['artifact_sha256'],
                artifact_raw_sha256=s['artifact_raw_sha256'],
                receipt_raw_sha256=s['receipt_raw_sha256']) for s in snapshots])
        identity['batch_sha256'] = sha256_json(identity)
    return snapshots, identity


def _receipt(snapshot):
    artifact = snapshot['artifact']
    receipt = {key: snapshot[key] for key in ('artifact_sha256', 'artifact_raw_sha256',
        'manifest_raw_sha256', 'receipt_raw_sha256', 'artifact_relative_path',
        'manifest_relative_path', 'receipt_relative_path')}
    receipt.update({key: artifact.get(key) for key in ('pool_id', 'source_role',
        'source_sha256', 'source_run_id', 'source_artifact_sha256',
        'source_manifest_sha256', 'source_receipt_sha256', 'rows')})
    receipt['pool_scores'] = [row.get('pool_score') for row in artifact['rows']]
    receipt.update(artifact=artifact, artifact_status=artifact['status'],
                   cannot_confirm=artifact['cannot_confirm'], source_path=artifact['source_path'])
    return receipt


def _publish(runtime, request, assembly):
    accepted = [lane['artifact'] for lane in assembly['lanes'] if lane['accepted']]
    _preflight(runtime, accepted)
    outcomes, successes = [], []
    for lane in assembly['lanes']:
        artifact = lane.get('artifact')
        if not lane['accepted']:
            expected_missing = (isinstance(artifact, dict)
                and artifact.get('status') == 'CANNOT_CONFIRM'
                and artifact.get('source_role') == 'EXPECTED_MISSING' and artifact.get('rows') == [])
            outcomes.append(_outcome(lane, 'EXPECTED_MISSING' if expected_missing else 'REJECTED',
                                     artifact_written=False))
            continue
        try:
            stored = runtime.store.materialize(artifact)
        except Exception as error:
            if not _classify_exception(error):
                raise
            outcomes.append(_outcome(lane, 'CONFLICT', pool_id=artifact['pool_id'],
                error_type=type(error).__name__, error=str(error),
                reason_code='IMMUTABLE_POOL_CONFLICT', artifact_written=False))
            continue
        successes.append((artifact, stored))
        outcomes.append(_outcome(lane, 'SUCCESS', pool_id=artifact['pool_id'],
                                 artifact_written=True))
    snapshots, batch = _final_snapshots(runtime, request['target_date'], successes)
    receipts = [_receipt(snapshot) for snapshot in snapshots]
    statuses = {outcome['status'] for outcome in outcomes}
    if 'CONFLICT' in statuses:
        status = 'CONFLICT'
    elif receipts:
        status = 'READY' if statuses == {'SUCCESS'} else 'PARTIAL'
    else:
        status = 'DEFERRED' if statuses == {'EXPECTED_MISSING'} else 'REJECTED'
    return dict(schema_version='v5.a_preselection_daily.v1', status=status,
        integration_status='WAIT_INTEGRATION', request_sha256=sha256_json(request),
        source_capsule_sha256=DESCRIPTOR_SHA256,
        assembler_implementation_sha256=assembly['implementation_sha256'],
        assembly_evidence={key: value for key, value in assembly.items() if key != 'lanes'},
        target_date=request['target_date'], signal_date=request['signal_date'],
        data_kind=request['data_kind'], row_count=sum(len(r['rows']) for r in receipts) if receipts else None,
        outcomes=outcomes, receipts=receipts, batch_identity=batch,
        isolation_status='FROZEN_PRIVATE_WRITER_PROCESS_OS_UNVERIFIED', **SAFETY)


def _worker(envelope):
    if set(envelope) != {'request', 'assembly', 'roots', 'write_gate_context', 'writer_implementation_sha256'}:
        raise ValueError('M05_WRITER_ENVELOPE_INVALID')
    implementation_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if envelope['writer_implementation_sha256'] != implementation_sha:
        raise ValueError('M05_WRITER_CODE_IDENTITY_MISMATCH')
    request = _request(envelope['request'])
    roots = envelope['roots']
    out = _validate_required_root(lane_roots=[lane['input_root'] for lane in request['lanes']], **roots)
    assembly = envelope['assembly']
    _validate_assembly(request, assembly)
    runtime = build_strict_store(out, envelope['write_gate_context'])
    if runtime.store.root != out:
        raise ValueError('M05_STORE_ROOT_IDENTITY')
    _source_bytes()
    result = _publish(runtime, request, assembly)
    result['writer_implementation_sha256'] = implementation_sha
    return result


if __name__ == '__main__':
    try:
        if sys.argv[1:] != ['--worker']:
            raise ValueError('M05_WRITER_PRIVATE_ENTRYPOINT')
        raw = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES:
            raise ValueError('M05_WRITER_REQUEST_TOO_LARGE')
        print(canonical_bytes(_worker(json.loads(raw))).decode())
    except Exception as error:
        print(canonical_bytes(dict(error_type=type(error).__name__, error=str(error))).decode())
        raise SystemExit(1)

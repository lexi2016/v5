"""Independent quote-only capture into the unchanged original three-file store.

Called in a fresh pinned owner child by the R14 source chain. No test clock or
provider parameter is accepted by the CLI. Network capture requires the exact
request gate, current original calendar/window, and controlled transport.
"""
import argparse
import json

from v5_shadow.cloud_transport import guarded_transport_class
from v5_shadow.cloud_us_collector import load_owner, verify, audit_modules, admit_output
from v5_shadow.us_source_daily import (
    _request_from_dict, _validate_request, collector_argv, parse_utc,
    _safe_root, _assert_source_absent, _validate_payload, source_paths,
)


NEWS_NOT_REQUESTED = 'NEWS_NOT_REQUESTED_QUOTE_ONLY_CAPTURE'


def _validate_quote_scope(payload):
    captures = payload.get('us_session_captures', [])
    if (payload.get('item_count') != 0 or payload.get('raw_item_count') != 0
            or any(payload.get(key) != [] for key in ('details', 'overview', 'items', 'feed_receipts'))
            or NEWS_NOT_REQUESTED not in payload.get('cannot_confirm', [])
            or len(captures) != 1 or captures[0].get('rss_status') != 'NOT_REQUESTED'
            or captures[0].get('quote_capture_status') != 'ATTEMPTED'):
        raise ValueError('M03_QUOTE_ONLY_SCOPE_MISMATCH')


def capture_owned(req, owner, transport_module):
    """Use already admitted modules; persist/reuse one immutable capture root."""
    _validate_request(req)
    collector_argv(req)
    if not req.market_snapshot_only or req.capture_phase != 'POST_CLOSE':
        raise ValueError('M03_MARKET_CAPTURE_POST_CLOSE_ONLY')
    admit_output(req.capture_root, req.owner_root)
    audit_modules()
    from infrastructure.research_peripheral_store import ResearchPeripheralStore
    from ops.materialize_research_peripherals import _base_payload
    from v5_shadow.market_snapshot_adapter import MarketSnapshotRequest, build_market_snapshot

    io = _safe_root(req.capture_root)
    with io.kernel_lock('.locks/market-capture.lock', timeout=30):
        store = ResearchPeripheralStore(req.capture_root)
        paths = source_paths(req.capture_root, req.trade_date)
        expected_relative = str(paths['payload'].relative_to(req.capture_root))
        # A generation root never accumulates another date or source. The
        # original store handles partial writes, idempotence, and exact hashes.
        try:
            manifest = json.loads(io.read_bytes(str(paths['manifest'].relative_to(req.capture_root))))
        except FileNotFoundError:
            manifest = {}
        if not isinstance(manifest, dict) or set(manifest) - {expected_relative}:
            raise ValueError('M03_CAPTURE_ROOT_NOT_IMMUTABLE')
        existing = store.read_exact(req.trade_date, 'external_finance')
        if existing is not None:
            _validate_payload(req, existing)
            _validate_quote_scope(existing)
            return {'status': 'MARKET_SOURCE_REUSED', 'source_status': existing['status'],
                    'market_snapshot_status': existing['market_snapshot']['status']}
        _assert_source_absent(req.capture_root, req)

        # Obtain one actual instant. No request-controlled captured_at/now.
        now = owner._capture_now()
        if now > parse_utc(req.cutoff):
            raise ValueError('M03_CAPTURE_AFTER_CUTOFF')
        certification = owner.us_market_day_certification(req.session)
        if certification['status'] != 'VERIFIED':
            raise ValueError('M03_MARKET_SESSION_NOT_VERIFIED:' + certification['reason'])
        metadata = owner.build_capture_metadata(
            req.session, req.capture_phase, captured_at=now,
            run_id=f'v5:m03:quote-only:{req.session}:{now.isoformat()}',
            allow_late_post_close=req.allow_late_post_close, now=now,
        )
        transport = guarded_transport_class(transport_module)()
        snapshot = build_market_snapshot(request=MarketSnapshotRequest(
            us_session_date=req.session, capture_phase=req.capture_phase,
            captured_at=metadata['captured_at'], session=req.session, cutoff=req.cutoff,
            capture_id=metadata['capture_id'], run_id=metadata['run_id'],
        ), transport=transport)
        for key in ('capture_mode', 'reason', 'capture_reason', 'late',
                    'natural_capture_window_start', 'natural_capture_window_end',
                    'allowed_recovery_window_start', 'allowed_recovery_window_end'):
            if key in metadata:
                snapshot[key] = metadata[key]
        # READY_EMPTY describes zero news rows, not an empty quote snapshot.
        # No RSS request was made: this limitation is retained in the original
        # envelope/capture fields. Only snapshot READY qualifies the R14 chain.
        payload = _base_payload(
            trade_date=req.trade_date, source='external_finance', status='READY_EMPTY',
            source_url=snapshot.get('quote_url') or snapshot['provider_url'],
            fetched_at=metadata['captured_at'], raw_item_count=0, item_count=0,
            overview=[], details=[], items=[], feed_receipts=[],
            cannot_confirm=[NEWS_NOT_REQUESTED],
        )
        payload = owner._annotate_payload(payload, metadata)
        payload['us_session_captures'][0].update(
            rss_status='NOT_REQUESTED', rss_item_count=0, rss_raw_item_count=0,
            quote_capture_status='ATTEMPTED',
        )
        payload['market_snapshot'] = snapshot
        payload['market_snapshot_status'] = snapshot['status']
        payload['cannot_confirm'] = sorted(set(payload['cannot_confirm']) | set(snapshot['cannot_confirm']))
        if snapshot['status'] != 'READY':
            payload['status'] = 'CANNOT_CONFIRM'
            payload['cannot_confirm'] = sorted(set(payload['cannot_confirm']) | {'MARKET_SNAPSHOT_CANNOT_CONFIRM'})
        _validate_payload(req, payload)
        _validate_quote_scope(payload)
        store.publish(payload)
        if store.read_exact(req.trade_date, 'external_finance') != payload:
            raise ValueError('M03_CAPTURE_LOCAL_READBACK_MISMATCH')
        return {'status': 'MARKET_SOURCE_SAVED', 'source_status': payload['status'],
                'market_snapshot_status': snapshot['status']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request-json', required=True)
    args = parser.parse_args(argv)
    req = _request_from_dict(json.loads(args.request_json))
    _validate_request(req)
    collector_argv(req)
    owner, transport_module = load_owner(req.owner_root)
    try:
        result = capture_owned(req, owner, transport_module)
    finally:
        verify(req.owner_root)
        audit_modules()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

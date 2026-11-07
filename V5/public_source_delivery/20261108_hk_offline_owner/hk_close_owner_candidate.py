"""Offline assembly candidate only. NOT the missing original hk_close_owner.
No production registration, caller provider, output-root or CAS execution route.
"""
from datetime import datetime
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile

RECOVERY = Path(__file__).resolve().parent.parent / 'hk_provider_recovery_20261108'
COLLECTOR_BLOB = '1b329ef71a29ff61330ba2960362aa8e5a89a4b1'


def verify_sources():
    manifest = json.loads((RECOVERY / 'hk_close_source_manifest.json').read_text())
    for entry in manifest['entries']:
        raw = (RECOVERY / 'original' / entry['relative_path']).read_bytes()
        relative = Path(entry['relative_path'])
        if relative.suffix == '.py':
            parts = list(relative.with_suffix('').parts)
            if parts[-1] == '__init__': parts.pop()
            loaded = sys.modules.get('.'.join(parts))
            if loaded is not None and Path(getattr(loaded, '__file__', '') or '').resolve() != (RECOVERY / 'original' / relative).resolve():
                raise ValueError('LOADED_MODULE_ORIGIN_MISMATCH')
        if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('ORIGINAL_SOURCE_INTEGRITY_FAILURE')
    raw = (RECOVERY / 'references/ops/collect_hkconnect_close_snapshot.py').read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if blob != COLLECTOR_BLOB:
        raise ValueError('COLLECTOR_SOURCE_INTEGRITY_FAILURE')


class _Frame:
    def __init__(self, rows): self.rows = rows
    def to_dict(self, orient): return self.rows


class _SyntheticQuote:
    def __init__(self, day): self.day, self.calls, self.closed = day, 0, False
    def get_plate_stock(self, plate):
        return 0, _Frame([{'code': f'HK.{i:05d}', 'stock_name': 'SYNTHETIC'} for i in range(1, 601)])
    def get_market_snapshot(self, codes):
        self.calls += 1
        return 0, _Frame([{'code': c, 'update_time': self.day + ' 16:10:01',
            'last_price': 10 + int(c[-5:]) / 1000, 'prev_close_price': 10,
            'turnover': 1000} for c in codes])
    def close(self): self.closed = True


def run_owner(trade_date, *, mode='BLOCKED', node='M10_OFFLINE'):
    """Only generated fixture replay allowed; arbitrary providers cannot be injected.
    Temp store uses original publication locks. Real resource/job/source contracts
    remain UNKNOWN; this offline check does not assert those gates passed.
    """
    if mode != 'SYNTHETIC_ONLY' or node != 'M10_OFFLINE':
        return {'status': 'BLOCKED', 'reason': 'REAL_SOURCE_CAS_RESOURCE_OWNER_CONTRACT_UNVERIFIED',
                'production_allowed': False, 'buy_gate_updated': False, 'orders_sent': False}
    if not isinstance(trade_date, str) or len(trade_date) != 8 or not trade_date.isdigit():
        raise ValueError('INVALID_DATE')
    day = datetime.strptime(trade_date, '%Y%m%d')
    verify_sources()
    sys.path.insert(0, str(RECOVERY / 'original'))
    from domains.close_review import build_native_close_review
    from infrastructure.hkconnect_close_store import CloseSnapshotStore
    spec = importlib.util.spec_from_file_location('_pinned_offline_collector', RECOVERY / 'references/ops/collect_hkconnect_close_snapshot.py')
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
    quote = _SyntheticQuote(day.strftime('%Y-%m-%d'))
    with tempfile.TemporaryDirectory(prefix='hk_owner_SYNTHETIC_') as directory:
        root = Path(directory)
        now = day.replace(hour=16, minute=11)
        first = collector.collect_close_snapshot(trade_date, data_root=root,
                quote_context_factory=lambda: quote, now=now)
        def forbidden(): raise AssertionError('DUPLICATE_CAPTURE')
        second = collector.collect_close_snapshot(trade_date, data_root=root,
                quote_context_factory=forbidden, now=now)
        snapshot, sha = CloseSnapshotStore(root).read_snapshot(trade_date)
        review = build_native_close_review(trade_date, close_rows=snapshot['rows'],
                model_rows=[], stage_rows={}, close_source_sha256=sha)
    return {'status': 'SYNTHETIC_CHECK_COMPLETE', 'evidence_mode': 'SYNTHETIC_ONLY',
            'production_allowed': False, 'buy_gate_updated': False, 'orders_sent': False,
            'trade_date': trade_date, 'node': node, 'original_source_integrity': 'PASS',
            'source_live_availability': 'UNKNOWN', 'actual_cas_terminal_event': 'UNKNOWN',
            'real_resource_and_job_lock_gate': 'UNKNOWN', 'real_owner_closure': 'UNKNOWN',
            'fixture_provider': 'IN_PROCESS_SYNTHETIC_NOT_FUTU',
            'original_source_label_not_live_evidence': snapshot.get('source'),
            'calls': quote.calls, 'context_closed': quote.closed,
            'second_publication': second['publication']['status'],
            'row_counts': review['row_counts'], 'top20_codes': [r['code'] for r in review['close_top20']],
            'missing_stages': review['missing_stages'], 'models': review['models'],
            'formal_artifact_saved': False, 'temporary_store_removed': True,
            'natural_business_acceptance': 'NOT_TESTED'}

"""Read-only original-owner request preparation; never dispatch, refresh or publish.

Sources are explicit original bindings, not invented daily ledger acknowledgments.
Temporary preview output prevents an older saved plan from masking missing inputs.
"""
import sys
from pathlib import Path
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import copy
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
import re
import tempfile
from v5_shadow.contracts import aware, trade_date
from v5_shadow.digests import canonical_bytes, sha256_json
from v5_shadow.manager_plan import _request, _snapshot, run_manager_plan, PIN
from v5_shadow.module_api import _open_directory, _read_at


def template(spec):
    """Complete only original read controls. Never guess paths, dates or hashes."""
    value = copy.deepcopy(spec)
    value.update(action='read', view='dynamic', selection_date=None, announcement_date=None)
    return _request(value)


def _hex(value, length=64):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{%d}' % length, value) is not None


def lane_readiness(payload, target):
    """Project original owner's decision, preserving all gaps and identities.

    This function is not a standalone admission validator: only prepare's fresh
    pinned owner read may produce a prepared request.
    """
    trade_date(target)
    context = payload.get('plan_context') or {}
    same_target = payload.get('target_trade_date') == target and context.get('plan_trade_date') == target
    announcement = payload.get('announcement_reviewed_analysis') or {}
    products = announcement.get('products') or []
    hashes = announcement.get('consumed_product_sha256s') or []
    ann_ok = (same_target and announcement.get('status') in ('READY','READY_EMPTY')
        and bool(products) and len(products) == len(hashes)
        and all(p.get('status') == 'CONSUMED' and p.get('consumed') is True
            and p.get('target_trade_date') == target and _hex(p.get('product_sha256'))
            and p['product_sha256'] in hashes for p in products))
    screen = payload.get('market_screen') or {}
    rebound_ok = (same_target and screen.get('status') == 'READY'
        and screen.get('main_screen_ready') is True and screen.get('target_trade_date') == target
        and screen.get('verified_session') == context.get('market_session')
        and _hex(screen.get('input_identity')) and screen.get('pending') == [])
    daily = (payload.get('us_mapping_research') or {}).get('daily_run') or {}
    mapping = (payload.get('owner_chain') or {}).get('us_mapping_daily_plan_reference') or {}
    us_ok = (same_target and mapping.get('status') == 'CONSUMED'
        and daily.get('target_trade_date') == target and mapping.get('target_trade_date') == target
        and _hex(daily.get('run_id'),32) and _hex(daily.get('artifact_sha256'))
        and all(mapping.get(k) == daily[k] for k in ('run_id','artifact_sha256'))
        and daily.get('status') in ('COMPLETED','VALID_EMPTY')
        and isinstance(daily.get('matches'),list)
        and (daily['status'] != 'VALID_EMPTY' or daily['matches'] == []))
    return dict(
        announcement=dict(accepted=bool(ann_ok), owner_status=announcement.get('status','MISSING'),
            reference=copy.deepcopy(announcement), reason_codes=[] if ann_ok else ['ANNOUNCEMENT_ORIGINAL_CONSUMPTION_NOT_COMPLETE']),
        rebound=dict(accepted=bool(rebound_ok), owner_status=screen.get('status','MISSING'),
            reference=copy.deepcopy(screen), reason_codes=[] if rebound_ok else ['REBOUND_FORMAL_SCREEN_NOT_COMPLETE_PENDING_IS_NOT_EMPTY']),
        us_mapping=dict(accepted=bool(us_ok), owner_status=mapping.get('status','MISSING'),
            reference=copy.deepcopy(mapping), daily_status=daily.get('status'),
            reason_codes=[] if us_ok else ['US_MAPPING_ORIGINAL_CONSUMPTION_NOT_COMPLETE']))


def _source_bytes(request):
    """Verify all explicit file pins before any read and again after readback."""
    result = {name: {p: hashlib.sha256(raw).hexdigest() for p,raw in _snapshot(binding).items()}
              for name,binding in request['inputs'].items()}
    for key in ('membership','registry_observation'):
        if request.get(key) is not None:
            result[key] = {p: hashlib.sha256(raw).hexdigest() for p,raw in _snapshot(request[key]).items()}
    # Reference-only products are verified by their pinned original cold readers.
    return result


def prepare(request):
    value = template(request)
    before = _source_bytes(value)
    # This is not the user's durable output. No prior run can supply admission.
    with tempfile.TemporaryDirectory(prefix='v5-m18-preparation-') as name:
        root = Path(name).resolve()
        (root/'.v5-manager-plan-root').write_bytes(b'v5.manager-plan-root.v1\n')
        result = run_manager_plan(dict(value, manager_output_root=str(root)))
        if list(root.iterdir()) != [root/'.v5-manager-plan-root']:
            raise ValueError('M18_PREPARATION_UNEXPECTED_OWNER_WRITE')
    if _source_bytes(value) != before:
        raise ValueError('M18_PREPARATION_SOURCE_CHANGED')
    if result.get('source_capsule_sha256') != PIN:
        raise ValueError('M18_PREPARATION_OWNER_PIN')
    lanes = lane_readiness(result['payload'],value['target_date'])
    complete = all(row['accepted'] for row in lanes.values())
    daily = (result['payload'].get('us_mapping_research') or {}).get('daily_run') or {}
    references = dict(announcement=copy.deepcopy(value.get('announcement_offline_owner')),
        rebound=copy.deepcopy(value.get('rebound')), rebound_owner=copy.deepcopy(value.get('rebound_owner')),
        us_mapping=(dict(manager_output_root=value['inputs']['manager']['root'],
            target_date=daily['target_trade_date'], run_id=daily['run_id'],
            artifact_sha256=daily['artifact_sha256']) if lanes['us_mapping']['accepted'] else None))
    actual = datetime.now(timezone.utc)
    hk = actual.astimezone(timezone(timedelta(hours=8)))
    in_window = (hk.strftime('%Y%m%d') == value['target_date']
                 and (8,45) <= (hk.hour,hk.minute) < (9,0))
    # A template is preparation only. Original assembler must seal the actual
    # cutoff and original dispatcher must recheck the real execution window.
    return dict(schema_version='v5.m18_request_preparation.v1',
        status='PREPARED_READ_ONLY' if complete else 'WAITING_SOURCES',
        target_date=value['target_date'], research_cutoff=value['now'],
        observed_at=actual.isoformat(), original_window_open=in_window,
        lanes=lanes, source_files=before, source_references=references,
        original_bindings=copy.deepcopy(value),
        request_sha256=sha256_json(value), owner_source_sha256=PIN,
        preview_input_identity=result['payload']['input_identity'],
        manager_template=copy.deepcopy(value) if complete else None,
        # Never return a directly executable refresh request from a read probe.
        manager_request=None, execution_status='NOT_RUN',
        next_action='ORIGINAL_ASSEMBLER_AND_DISPATCHER_RECHECK_REQUIRED' if complete else 'WAIT_FOR_ORIGINAL_SOURCES',
        production_allowed=False, orders_sent=False, buy_gate_updated=False,
        natural_verified=False, three_lane_accepted=False)


def bind_saved(request, expected):
    """Cold-read a saved manager identity; never accept a different latest run."""
    if (set(expected) != {'run_id','plan_sha256'} or not _hex(expected['run_id'],32)
            or not _hex(expected['plan_sha256'])):
        raise ValueError('M18_SAVED_REFERENCE')
    value=copy.deepcopy(request);value['action']='read';_request(value)
    before=_source_bytes(value)
    first=run_manager_plan(value)
    second=run_manager_plan(value)  # Separate original owner subprocess/cold read.
    for result in (first,second):
        product=result['payload']['plan_product']; readback=result['readback']
        attempt=readback.get('attempt') or {}
        if (product.get('consumed') is not True or product.get('run_id') != expected['run_id']
                or product.get('sha256') != expected['plan_sha256']
                or readback.get('run_id') != expected['run_id']
                or readback.get('plan_sha256') != expected['plan_sha256']
                or attempt.get('run_id') != expected['run_id']):
            raise ValueError('M18_SAVED_SAME_RUN_REQUIRED')
    if (first['readback']['input_identity'] != second['readback']['input_identity']
            or before != _source_bytes(value)):
        raise ValueError('M18_SAVED_READBACK_CHANGED')
    lanes=lane_readiness(second['payload'],value['target_date'])
    return dict(schema_version='v5.m18_saved_binding.v1',status='SAVED_READBACK_MATCHED',
        saved_reference=copy.deepcopy(expected), manager_output_root=value['manager_output_root'],
        target_date=value['target_date'], source_files=before, request_sha256=sha256_json(value),
        store_relative=second['readback']['store_relative'], input_identity=second['readback']['input_identity'],
        lanes=lanes, three_lane_accepted=all(x['accepted'] for x in lanes.values()),
        owner_source_sha256=PIN, natural_verified=False, production_allowed=False,
        orders_sent=False,buy_gate_updated=False,execution_status='READ_ONLY')


def _read_json(path):
    path=Path(path).absolute();fd=_open_directory(path.parent)
    try:return json.loads(_read_at(fd,None,path.name))
    finally:os.close(fd)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--saved-reference',type=Path)
    args=parser.parse_args()
    request=_read_json(args.request)
    result=(bind_saved(request,_read_json(args.saved_reference)) if args.saved_reference else prepare(request))
    print(canonical_bytes(result).decode())
    return 2 if result['status']=='WAITING_SOURCES' else 0


if __name__=='__main__':
    raise SystemExit(main())

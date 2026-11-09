"""New V2 evening orchestration; original renderer/safeio/outbox stay pinned.

Only an internally reviewed binding may supply the owner, clock and read-only
independent review callbacks. A local export or a self-written proof never grants
freeze/delivery authority. Empty registry remains blocked at execution.run().
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import types

HERE = Path(__file__).resolve().parent
BRIDGE_PATH = HERE.parents[3] / 'handoff/reconstruction_candidates_20261108/terminal17_alert_v1/controlled_delivery.py'
DELIVERY_BRIDGE_SHA = 'a9369a26d5ca8f016f62d3484db543687b7afdc68de7ef1f14371fd7b0d38ca0'
GROUPS = ('original', 'nav_smallk', 'nav_pullback', 'nav_breakout')


def _bridge():
    raw = BRIDGE_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DELIVERY_BRIDGE_SHA:
        raise ValueError('DELIVERY_BRIDGE_CHANGED')
    module = types.ModuleType('evening_controlled_delivery')
    module.__file__ = str(BRIDGE_PATH)
    exec(compile(raw, str(BRIDGE_PATH), 'exec'), module.__dict__)
    return module


def _snapshot(cfg, registration_id, io, render, versions, bridge):
    data = json.loads(bridge.checked_pin(io, cfg['input_root'], cfg['data']))
    admission = json.loads(bridge.checked_pin(io, cfg['input_root'], cfg['admission']))
    # Python bool compares equal to 0/1. Validate the wrapper's count contract
    # before invoking the unchanged original renderer/comparison code.
    for document in (data, admission):
        for field in ('scope_count', 'dedup_selected', 'dedup_pending'):
            if type(document.get(field)) is not int or document[field] < 0:
                raise ValueError('INTEGER_COUNT_REQUIRED:' + field)
    for group in GROUPS:
        counts = data['counts'][group]['after_risk']
        for state in ('TRUE', 'FALSE', 'UNKNOWN'):
            if type(counts.get(state)) is not int or counts[state] < 0:
                raise ValueError('INTEGER_GROUP_COUNT_REQUIRED')
    group_true = admission.get('group_true')
    if (not isinstance(group_true, list) or len(group_true) != len(GROUPS)
            or any(type(count) is not int or count < 0 for count in group_true)):
        raise ValueError('INTEGER_ADMISSION_GROUP_COUNT_REQUIRED')
    day, observation = cfg['data_date'], cfg['observation_date']
    if bridge.date(observation) <= bridge.date(day):
        raise ValueError('OBSERVATION_DATE_BINDING')
    if (bridge.date(day) > bridge.date(cfg['run_date'])
            or bridge.date(observation) <= bridge.date(cfg['run_date'])):
        raise ValueError('SOURCE_OR_NEXT_SESSION_DATE_BINDING')
    if (data['source_date'] != day or data['calculation_date'] != day
            or data['observation_date'] != observation):
        raise ValueError('DATE_BINDING')
    if type(cfg['scope_count']) is not int or data['scope_count'] != cfg['scope_count']:
        raise ValueError('SCOPE_BINDING')
    if (admission.get('status') != 'PASS_RESEARCH_MERGE_DISPLAY_ONLY'
            or admission.get('production_allowed') is not False
            or admission.get('research_display_allowed') is not True):
        raise ValueError('ADMISSION')
    if ([data['counts'][g]['after_risk']['TRUE'] for g in GROUPS] != admission['group_true']
            or any(data[k] != admission[k] for k in ('scope_count', 'dedup_selected', 'dedup_pending'))):
        raise ValueError('ADMISSION_COUNTS')
    payloads = render(data)
    payloads['research_prompt.txt'] = (
        '请仅对 selected.csv 名单补公告及基本面证据，保留完整代码、来源日期与 UNKNOWN；'
        '不得将数值候选当买入资格。资料日期 ' + day + '；观察日期 ' + observation
        + '。不改名单、不执行交易。\n').encode()
    manifest = dict(
        schema='EVENING_RESEARCH_PACKAGE_V2', registration_id=registration_id,
        binding_version=cfg['binding_version'], owner_id=cfg['owner_id'],
        task_id=cfg['task_id'], environment_id=cfg['environment_id'],
        run_date=cfg['run_date'], data_date=day, observation_date=observation,
        authorization_ref=cfg['authorization_ref'], source_contract_ref=cfg['source_contract_ref'],
        calendar_ref=cfg['calendar_ref'], inputs=[cfg['data'], cfg['admission']],
        root_identity=cfg['root_identity'], delivery_contract=bridge.delivery_identity(cfg),
        code_versions=versions,
        files={name: dict(sha256=bridge.sha(raw), bytes=len(raw)) for name, raw in payloads.items()},
        content_scope='ORIGINAL_RESEARCH_EXPORT_NO_RESELECTION',
        buy_qualification=False, production_allowed=False, natural_verified=False)
    raw = io.canonical(manifest)
    return manifest, raw, bridge.sha(raw), payloads


def _review(proof, schema, manifest, key, cfg, bridge):
    expected = dict(schema=schema, status='VERIFIED', package_id=key, manifest_sha256=key,
                    run_date=cfg['run_date'], data_date=cfg['data_date'],
                    observation_date=cfg['observation_date'], owner_id=cfg['owner_id'],
                    binding_version=cfg['binding_version'], source_contract_ref=cfg['source_contract_ref'],
                    calendar_ref=cfg['calendar_ref'], authority_ref=cfg['authorization_ref'],
                    scope='RESEARCH_PACKAGE_ONLY')
    if (not isinstance(proof, dict) or any(proof.get(k) != v for k, v in expected.items())
            or not bridge.text_identity(proof.get('reviewer_id'))
            or proof['reviewer_id'] == cfg['owner_id']
            or not bridge.text_identity(proof.get('evidence_ref'))):
        raise ValueError('INDEPENDENT_' + schema + '_MISMATCH')
    # Ensure non-finite or non-JSON callback output cannot enter the identity.
    bridge.canonical(proof)
    return proof


def _require_review_time_authority():
    """Quarantine formal preparation until original review time is recoverable.

    Neither the registered current clock nor a local checked_at proves when an
    independent review occurred. No reviewed authority binds that original event
    to this package, stage and run with rollback protection. Caller flags, new
    callbacks and local file hashes cannot supply that missing authority.
    Local-only exports remain available through execution._run_local.
    """
    raise ValueError('INDEPENDENT_REVIEW_TIME_AUTHORITY_UNBOUND_NO_FORMAL_RECEIPT')


def _receipt(io, fd, name, core, now, create, cfg, slot, bridge):
    # Keep the private call boundary blocked as well: do not create a receipt
    # from now, or accept an old one after editing its unbound checked_at field.
    _require_review_time_authority()


def _package(cfg, stage, registration_id, package_id, io, render, versions, now, bridge, allow_later=False):
    _require_review_time_authority()
    manifest, raw, key, payloads = _snapshot(cfg, registration_id, io, render, versions, bridge)
    if stage != '1830' and package_id != key:
        raise ValueError('PACKAGE_VERSION_REQUIRES_PREPARE')
    proof = _review(cfg['review_freeze'](manifest=json.loads(raw), package_id=key),
                    'EVENING_FREEZE_REVIEW_V2', manifest, key, cfg, bridge)
    bridge.original_gate(cfg)
    now = bridge.clock_gate(cfg, stage, allow_later=allow_later)
    attempt = io.canonical(dict(schema='EVENING_LOCAL_COMMIT_ATTEMPT_V2', package_id=key,
                                manifest_sha256=key, freeze_review_sha256=bridge.sha(io.canonical(proof))))
    expected = payloads | {'manifest.json': raw, 'attempt.json': attempt}
    allowed = set(expected) | {'freeze.json', 'verification.json'}
    root = bridge.checked_root(io, cfg['output_root'], cfg['root_identity'])
    child = None
    reused = True
    try:
        if stage == '1830':
            try:
                os.mkdir(key, mode=0o700, dir_fd=root)
                os.fsync(root)
                reused = False
            except FileExistsError:
                pass
        child = os.open(key, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=root)
        present = set(os.listdir(child))
        if present - allowed:
            raise ValueError('UNKNOWN_PACKAGE_FILES_NO_OVERWRITE')
        if reused and 'attempt.json' not in present:
            raise ValueError('UNKNOWN_PARTIAL_PACKAGE_REQUIRES_REVIEW')
        # Verify every existing byte before writing any missing local-only file.
        for name in present & set(expected):
            if io.read_at(child, name) != expected[name]:
                raise ValueError('OUTPUT_CHANGED_OR_INCOMPLETE')
        if stage != '1830' and not set(expected).issubset(present):
            raise ValueError('INCOMPLETE_PACKAGE')
        if stage == '1830':
            # Durable provenance precedes payload writes, allowing missing-file
            # resumption only for this exact local attempt. Partial files block.
            for name in ['attempt.json', *payloads, 'manifest.json']:
                if name not in present:
                    io.write_at(child, name, expected[name])
                    os.fsync(child)
            for name, content in expected.items():
                if io.read_at(child, name) != content:
                    raise ValueError('OUTPUT_CHANGED_OR_INCOMPLETE')
        freeze_core = dict(schema='EVENING_FREEZE_RECEIPT_V2', package_id=key,
                           manifest_sha256=key, proof=proof, formal_freeze=True,
                           evidence_domain=cfg['domain'], natural_verified=False, business_accepted=False)
        bridge.original_gate(cfg)
        now = bridge.clock_gate(cfg, stage, allow_later=allow_later)
        frozen, freeze_sha = _receipt(io, child, 'freeze.json', freeze_core, now,
                                      stage == '1830', cfg, '1830', bridge)
        checked_sha = None
        if stage in ('1850', '1900'):
            check = _review(cfg['review_check'](manifest=json.loads(raw), package_id=key,
                                               freeze_receipt=json.loads(io.canonical(frozen))),
                            'EVENING_CHECK_REVIEW_V2', manifest, key, cfg, bridge)
            check_core = dict(schema='EVENING_CHECK_RECEIPT_V2', package_id=key,
                              manifest_sha256=key, freeze_receipt_sha256=freeze_sha, proof=check,
                              evidence_domain=cfg['domain'], natural_verified=False, business_accepted=False)
            bridge.original_gate(cfg)
            now = bridge.clock_gate(cfg, stage, allow_later=allow_later)
            _, checked_sha = _receipt(io, child, 'verification.json', check_core, now,
                                       stage == '1850', cfg, '1850', bridge)
        # The advertised root and package must still name the held directories.
        again = bridge.checked_root(io, cfg['output_root'], cfg['root_identity'])
        try:
            opened = os.open(key, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=again)
            try:
                if (os.fstat(opened).st_dev, os.fstat(opened).st_ino) != (os.fstat(child).st_dev, os.fstat(child).st_ino):
                    raise ValueError('PACKAGE_DIRECTORY_CHANGED')
            finally:
                os.close(opened)
        finally:
            os.close(again)
    finally:
        if child is not None:
            os.close(child)
        os.close(root)
    return dict(package_id=key, manifest=manifest, payloads=payloads, reused=reused,
                freeze_receipt_sha256=freeze_sha, verification_receipt_sha256=checked_sha)


def run(stage, registration_id, package_id, cfg, io, render, versions, action='deliver'):
    bridge = _bridge()
    base = dict(stage=stage, package_id=package_id, formal_freeze=False, sent=False,
                uploaded=False, delivery_verified=False, natural_verified=False, business_accepted=False)
    try:
        bridge.validate_binding(cfg, 'EVENING_CONTROLLED_BINDING_V2')
        if stage not in ('1830', '1850', '1900') or action not in ('prepare', 'deliver', 'reconcile'):
            raise ValueError('STAGE_OR_ACTION')
        if stage != '1900' and action != 'deliver':
            raise ValueError('DELIVERY_ACTION_ONLY_AT_1900')
        if not bridge.text_identity(cfg.get('calendar_ref')):
            raise ValueError('MISSING_CALENDAR_CONTRACT')
        for name in ('review_freeze', 'review_check'):
            if not callable(cfg.get(name)):
                raise ValueError('MISSING_INDEPENDENT_REVIEW:' + name)
        allow_later = stage == '1900' and action == 'reconcile'
        bridge.clock_gate(cfg, stage, allow_later=allow_later)
        _require_review_time_authority()
        with cfg['owner_context']():
            bridge.original_gate(cfg)
            now = bridge.clock_gate(cfg, stage, allow_later=allow_later)
            result = _package(cfg, stage, registration_id, package_id, io, render, versions, now, bridge, allow_later)
        key = result['package_id']
        base.update(package_id=key, path=str(Path(cfg['output_root']) / key), formal_freeze=True,
                    data_date=cfg['data_date'], observation_date=cfg['observation_date'], run_date=cfg['run_date'],
                    evidence_domain=cfg['domain'], byte_readback='PASS', reused=result['reused'],
                    freeze_receipt_sha256=result['freeze_receipt_sha256'],
                    verification_receipt_sha256=result['verification_receipt_sha256'])
        if stage != '1900':
            return base | {'status': 'FROZEN_REVIEW_VERIFIED' if stage == '1830' else 'PACKAGE_CHECK_VERIFIED',
                           'delivery_state': 'NOT_PREPARED', 'sent_in_this_call': False}
        payload = dict(schema='EVENING_DELIVERY_V2', package_id=key, manifest_sha256=key,
                       run_date=cfg['run_date'], data_date=cfg['data_date'], observation_date=cfg['observation_date'],
                       freeze_receipt_sha256=result['freeze_receipt_sha256'],
                       verification_receipt_sha256=result['verification_receipt_sha256'],
                       files=result['manifest']['files'], source_contract_ref=cfg['source_contract_ref'],
                       original_research_text=result['payloads']['delivery.txt'].decode(),
                       evidence_domain=cfg['domain'], buy_qualification=False, natural_verified=False)

        def preflight():
            current_now = bridge.clock_gate(cfg, '1900', allow_later=action == 'reconcile')
            current = _package(cfg, '1900', registration_id, key, io, render, versions, current_now, bridge, allow_later)
            if any(current[name] != result[name] for name in
                   ('package_id', 'freeze_receipt_sha256', 'verification_receipt_sha256')):
                raise ValueError('FROZEN_PACKAGE_CHANGED')

        delivery = bridge.dispatch(cfg, node='1900', input_sha256=key,
                                   code_version=bridge.sha(bridge.canonical(versions)),
                                   payload=payload, preflight=preflight, action=action)
        state = delivery['delivery_state']
        base['sent'] = True if state in ('ACCEPTED', 'DELIVERED_VERIFIED') else (None if state == 'ATTEMPT_UNKNOWN' else False)
        return base | delivery
    except (ValueError, KeyError, TypeError, FileNotFoundError) as error:
        return base | bridge.blocked(type(error).__name__ + ':' + str(error))
    except OSError as error:
        return base | dict(status='UNKNOWN_RECONCILIATION_REQUIRED', reason=type(error).__name__,
                           delivery_state='UNKNOWN', sent=None, sent_in_this_call=None)

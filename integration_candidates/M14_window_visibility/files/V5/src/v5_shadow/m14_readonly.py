"""Independent saved M14 pages; original owner cold-read verification per GET.

Adapted from the original M14 Chat's 4f3da9dd adapter: retain server-owned
binding, no_symlinks, direct artifact return and four-reference/group cursor.
Integration adds closed queries, bounded public projections and module records.
No producer, collection, build, model, daily execution or publication occurs here.
"""
from __future__ import annotations
import base64
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from .composition import no_symlinks
from .contracts import exact_keys, sha, trade_date
from .digests import canonical_bytes, sha256_json
from .rebound_owner import read_rebound_owner, SAFETY

ROUTE = '/api/v5/source-bundle/rebound-saved'
BINDING = 'm14_rebound_binding'
SCHEMA = 'v5.m14.saved_rebound.v1'
GROUPS = ('strict', 'near', 'pending', 'excluded', 'screen_unresolved')
REF_KEYS = ('run_id', 'artifact_sha256', 'manifest_sha256', 'receipt_sha256')
PAGE_LIMIT = 32
MAX_CURSOR_BYTES = 4096
MAX_PAGE_BYTES = 256 * 1024
MAX_ITEM_BYTES = 16 * 1024
MAX_VALUES_BYTES = 128 * 1024
MAX_ENTRIES = 10000


class M14ReadonlyError(ValueError):
    pass


class WaitingBinding(M14ReadonlyError):
    pass


@dataclass(frozen=True)
class SavedBinding:
    private_root: Path
    reference: dict[str, str]


def _require(condition, reason):
    if not condition:
        raise M14ReadonlyError(reason)


def _reference(reference):
    exact_keys(reference, REF_KEYS)
    _require(isinstance(reference['run_id'], str) and
             re.fullmatch('[0-9a-f]{32}', reference['run_id']), 'M14_RUN_ID')
    for key in REF_KEYS[1:]:
        sha(reference[key])
    return dict(reference)


def parse_binding(binding: Mapping[str, Any] | None) -> SavedBinding:
    if binding is None:
        raise WaitingBinding('M14_SAVED_REFERENCE_NOT_CONFIGURED')
    exact_keys(binding, ('private_root', 'reference'))
    _require(isinstance(binding['private_root'], (str, Path)), 'M14_ROOT')
    # Preserve the raw configured path until no_symlinks rejects relative/..
    # and every symlink ancestor. The original reader owns marker/no-follow I/O.
    return SavedBinding(no_symlinks(binding['private_root']), _reference(binding['reference']))


def validate_binding(config):
    if BINDING not in config:
        return
    _require(config['module_id'] == 'source_bundle' and ROUTE in config['routes'], 'M14_ROUTE')
    parse_binding(config[BINDING])


def _check_query(query):
    _require(isinstance(query, dict) and all(isinstance(v, str) for v in query.values()), 'M14_QUERY')
    _require(not set(query) - {'group', 'cursor', *REF_KEYS}, 'M14_QUERY')
    present = set(query) & set(REF_KEYS)
    _require(not present or present == set(REF_KEYS), 'M14_QUERY_REFERENCE')
    if present:
        _reference({key: query[key] for key in REF_KEYS})
    _require(query.get('group', 'pending') in GROUPS, 'M14_GROUP')
    if 'cursor' in query:
        _require(0 < len(query['cursor']) <= MAX_CURSOR_BYTES, 'M14_CURSOR_SIZE')


def _encode_cursor(binding, group, offset):
    raw = canonical_bytes(dict(binding.reference, group=group, offset=offset))
    result = base64.urlsafe_b64encode(raw).decode('ascii')
    _require(len(result) <= MAX_CURSOR_BYTES, 'M14_CURSOR_SIZE')
    return result


def _decode_cursor(cursor, binding, group):
    _require(isinstance(cursor, str) and 0 < len(cursor) <= MAX_CURSOR_BYTES, 'M14_CURSOR_SIZE')
    def pairs(items):
        value = {}
        for key, item in items:
            _require(key not in value, 'M14_CURSOR_DUPLICATE')
            value[key] = item
        return value
    try:
        raw = base64.b64decode(cursor.encode('ascii'), altchars=b'-_', validate=True)
        _require(len(raw) <= MAX_CURSOR_BYTES, 'M14_CURSOR_SIZE')
        value = json.loads(raw, object_pairs_hook=pairs)
    except (ValueError, UnicodeError, TypeError) as error:
        raise M14ReadonlyError('M14_CURSOR_INVALID') from error
    exact_keys(value, (*REF_KEYS, 'group', 'offset'))
    _require(all(value[key] == binding.reference[key] for key in REF_KEYS)
             and value['group'] == group, 'M14_CURSOR_REFERENCE')
    offset = value['offset']
    _require(type(offset) is int and 0 < offset < MAX_ENTRIES, 'M14_CURSOR_OFFSET')
    _require(cursor == _encode_cursor(binding, group, offset), 'M14_CURSOR_CANONICAL')
    return offset


# Only approved observation fields cross the API. In particular, artifact
# request/snapshot/diagnostic/authority/private locations never cross it.
ROW_FIELDS = (
    'code', 'name', 'classification', 'qualification_status', 'connect_eligibility',
    'observed_session', 'target_monday', 'target_trade_date', 'reason_for_group',
    'amount_native', 'currency', 'amount_unit', 'volume_unit', 'price_currency',
    'close', 'prev_close', 'day_positive_close_gt_prev_close', 'pct_change',
    'current_volume', 'close_position_0_low_1_high', 'rebound_close_vs_low_pct',
    'rebound_ge_3pct', 'recent_3_session_return_pct', 'recent_5_session_return_pct',
    'history_status', 'history_unknown_reasons', 'history_raw_status',
    'prior60_session_count', 'previous5_session_count', 'previous20_session_count',
    'prior60_session_high', 'oversold_cutoff_80pct_prior60_high',
    'previous5_mean_volume', 'volume_ratio_5d', 'volume_ratio_current_to_previous5_mean',
    'previous20_mean_volume_background', 'volume_ratio_20d_background',
    'volume_ratio_current_to_previous20_mean_background', 'background20_status',
    'oversold_flag', 'oversold_close_le_80pct_prior60_high', 'volume_flag_5d_ge_1_5',
    'high_volume_ratio_ge_1_5', 'oversold_rebound_watch', 'strict_two_gate_oversold_5dvolume',
    'near_two_gate_one_missing', 'continuous_strength_highvolume_risk',
    'history_source', 'history_adjustment', 'adjustment_consistency', 'near_failed_gate',
    'near_failed_value', 'near_gate_value', 'near_gate_gap_ratio', 'near_gate_gap_value',
    'exclusion_reason_code', 'reason_for_exclusion', 'volume_source',
    'volume_unit_status', 'volume_scale_applied', 'research_boundary',
    *SAFETY,
)
SOURCE_REF_FIELDS = ('owner', 'sha256', 'payload_sha256', 'artifact_sha256', 'manifest_sha256', 'receipt_sha256')


def _public_scalar(value):
    if isinstance(value, str):
        # Even allowed reason/name fields must not reflect absolute paths or
        # filesystem URLs supplied by a saved diagnostic. No URL synthesis.
        if re.search(r'(^|[\s:=\'"(])(?:/|[A-Za-z]:[\\/])|file://', value):
            return '[PRIVATE_PATH_REDACTED]'
        return value
    if value is None or type(value) in (bool, int, float):
        return value
    if isinstance(value, list):
        _require(len(value) <= MAX_ENTRIES, 'M14_PUBLIC_LIST_SIZE')
        return [_public_scalar(item) for item in value]
    raise M14ReadonlyError('M14_PUBLIC_FIELD_SHAPE')


def _fields(value, names):
    _require(isinstance(value, dict), 'M14_PUBLIC_OBJECT')
    return {key: _public_scalar(value[key]) for key in names if key in value}


def _public_row(row):
    if not isinstance(row, dict):
        return _public_scalar(row)
    result = _fields(row, ROW_FIELDS)
    if 'source_refs' in row:
        _require(isinstance(row['source_refs'], list) and len(row['source_refs']) <= 64, 'M14_SOURCE_REFS')
        result['source_refs'] = [_fields(item, SOURCE_REF_FIELDS) for item in row['source_refs']]
    if 'membership_source' in row:
        result['membership_source'] = _fields(row['membership_source'], ('owner', 'source_date', 'payload_sha256', 'exchange'))
    return result


def _groups(artifact):
    observation = artifact.get('research_observation')
    _require(isinstance(observation, dict), 'M14_OBSERVATION_UNAVAILABLE')
    _require(all(isinstance(observation.get(group), list) for group in GROUPS), 'M14_GROUP_SHAPE')
    groups = {group: observation[group] for group in GROUPS}
    _require(sum(map(len, groups.values())) <= MAX_ENTRIES, 'M14_GROUP_LIMIT')
    return observation, groups


def _state(artifact, observation, binding, counts):
    # Reuse the existing saved rebound metadata field contract, not M18's
    # generation/identity or bundle reader. This is an independent owner source.
    from .module_api import (M18_REBOUND_OBSERVATION_FIELDS, M18_REBOUND_COVERAGE_FIELDS,
                             M18_REBOUND_DATE_FIELDS, M18_REBOUND_UNIT_FIELDS)
    public = _fields(observation, M18_REBOUND_OBSERVATION_FIELDS)
    if 'coverage' in observation:
        public['coverage'] = _fields(observation['coverage'], M18_REBOUND_COVERAGE_FIELDS)
    if 'native_evidence' in observation:
        native = observation['native_evidence']
        public['native_evidence'] = _fields(native, (
            'volume_unit', 'price_currency', 'price_basis', 'gaps',
            'research_cutoff', 'capture_started_at', 'capture_finished_at',
            'original_member_count', 'volume_unit_status', 'scale_applied'))
        if 'source_contract' in native:
            public['native_evidence']['source_contract'] = _fields(native['source_contract'], (
                'name', 'provider', 'interface', 'category', 'market', 'representation',
                'high_window', 'volume_window', 'volume_field', 'scale_applied',
                'volume_unit', 'volume_unit_status', 'price_currency', 'price_basis',
                'amount_unit', 'provider_finality', 'target_membership',
                'member_source', 'missing_policy', 'qualification'))
        if 'pending_reasons' in native:
            reasons = native['pending_reasons']
            _require(isinstance(reasons, dict) and len(reasons) <= MAX_ENTRIES,
                     'M14_PENDING_REASONS')
            _require(all(isinstance(code, str) and re.fullmatch(r'HK\.[0-9]{5}', code)
                         and isinstance(items, list) and all(isinstance(item, str) for item in items)
                         for code, items in reasons.items()), 'M14_PENDING_REASON_SHAPE')
            public['native_evidence']['pending_reasons'] = {
                code: _public_scalar(items) for code, items in reasons.items()}
        for name, fields in (('date_evidence', M18_REBOUND_DATE_FIELDS), ('unit_evidence', M18_REBOUND_UNIT_FIELDS)):
            if name in native:
                public['native_evidence'][name] = _fields(native[name], fields)
    source = dict(status=artifact['formal_status'], eligible_screen=None,
                  source_run_id=artifact['run_id'], binding_reference=dict(binding.reference),
                  scope='INDEPENDENT_SAVED_M14_OWNER_RESEARCH',
                  reason_codes=_public_scalar(artifact['reason_codes']),
                  **{key: artifact[key] for key in SAFETY})
    return dict(source_section_sha256=sha256_json(observation), group_counts=counts,
                source=source, observation=public)


def not_configured():
    return dict(schema_version=SCHEMA, status='WAITING', source_kind='M14_OWNER',
                reason_codes=['M14_SAVED_REFERENCE_NOT_CONFIGURED'], **SAFETY)


def read_saved_rebound(*, server_binding, query):
    _check_query(query)
    if server_binding is None:
        return not_configured()
    binding = parse_binding(server_binding)
    if 'run_id' in query:
        _require(all(query[key] == binding.reference[key] for key in REF_KEYS), 'M14_REFERENCE_MISMATCH')
    group = query.get('group', 'pending')
    cursor = query.get('cursor')
    offset = _decode_cursor(cursor, binding, group) if cursor is not None else 0
    # Critical boundary retained from original Chat: every GET re-reads and
    # verifies artifact/manifest/receipt, returning the artifact directly.
    artifact = read_rebound_owner(binding.private_root, binding.reference)
    observation, groups = _groups(artifact)
    target = trade_date(artifact['request']['target_date'])
    signal = trade_date(artifact['request']['signal_date'])
    _require(signal < target, 'M14_DATE_ORDER')
    rows = groups[group]; total = len(rows)
    _require(offset == 0 if cursor is None else offset < total, 'M14_OFFSET_RANGE')
    entries = []; loaded = 0; loaded_bytes = 0
    for index in range(offset, min(offset + PAGE_LIMIT, total)):
        row = rows[index]; raw = canonical_bytes(row)
        entry = dict(index=index, kind=('object' if isinstance(row, dict) else 'scalar'),
                     bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), value_state='NOT_LOADED')
        if len(raw) > MAX_ITEM_BYTES:
            entry['reason'] = 'ITEM_BYTES_LIMIT'
        elif loaded_bytes + len(raw) > MAX_VALUES_BYTES:
            break
        else:
            value = _public_row(row)
            entry.update(value=value, projection_sha256=sha256_json(value), value_state='LOADED')
            loaded += 1; loaded_bytes += len(raw)
        entries.append(entry)
    next_offset = offset + len(entries)
    response = dict(schema_version=SCHEMA, status='SAVED_RESEARCH', source_kind='M14_OWNER',
                    reference=dict(binding.reference), target_date=target, signal_date=signal,
                    data_kind=artifact['request']['data_kind'], execution_kind=artifact['execution_kind'],
                    **{key: artifact[key] for key in SAFETY}, projection='rebound_references', group=group,
                    rebound=_state(artifact, observation, binding, {key: len(value) for key, value in groups.items()}),
                    cursor=cursor, offset=offset, limit=PAGE_LIMIT, matched_total=total, loaded_count=loaded,
                    not_loaded_count=total-loaded, remaining_entries=total-next_offset, entries=entries,
                    next_cursor=_encode_cursor(binding, group, next_offset) if next_offset < total else None)
    _require(len(canonical_bytes(response)) <= MAX_PAGE_BYTES, 'M14_PAGE_SIZE')
    return response


def read_record(config, query):
    validate_binding(config)
    payload = read_saved_rebound(server_binding=config.get(BINDING), query=query)
    reference = payload.get('reference')
    record = dict(schema_version='v5.module_response.v1', module_id=config['module_id'],
                  release_id=config['release_id'], path=ROUTE, query=query, payload=payload,
                  payload_sha256=sha256_json(payload), source_input_sha256=reference['artifact_sha256'] if reference else sha256_json(payload),
                  data_kind=payload.get('data_kind', 'OWNER_RESULT'),
                  generated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), status_code=200)
    from .module_api import _validate_record
    return _validate_record(config, record, ROUTE, query), sha256_json(record)

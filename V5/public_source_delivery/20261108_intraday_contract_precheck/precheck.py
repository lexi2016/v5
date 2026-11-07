"""Offline structural/date/byte binding only. No producer, network, locks or activation.
Expected dates must come from independently validated trading calendar upstream.
This does NOT parse source CSV or establish its equality to the contract's scope.
"""
import datetime as dt
import hashlib
import json
import re

def need(condition, reason):
    if not condition:
        raise ValueError(reason)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def day(value):
    need(type(value) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value), 'DATE_FORMAT')
    return dt.date.fromisoformat(value)

def unique_object(pairs):
    result = {}
    for k, v in pairs:
        need(k not in result, 'DUPLICATE_JSON_KEY')
        result[k] = v
    return result

def precheck(contract_bytes, expected_contract_sha256, source_bytes,
             expected_source_date, expected_observation_date):
    need(type(contract_bytes) is bytes and type(source_bytes) is bytes, 'MISSING_BYTES')
    need(sha(contract_bytes) == expected_contract_sha256, 'CONTRACT_SHA_MISMATCH')
    c = json.loads(contract_bytes, object_pairs_hook=unique_object)
    need(type(c) is dict, 'CONTRACT_SCHEMA')
    source_day, observation_day = day(expected_source_date), day(expected_observation_date)
    need(source_day < observation_day, 'DATE_ORDER')
    need(c.get('source_date') == expected_source_date and
         c.get('observation_date') == expected_observation_date, 'DATE_BINDING')
    need(c.get('source_sha256') == sha(source_bytes), 'SOURCE_SHA_MISMATCH')
    for k in ('source_path', 'generation', 'input_identity'):
        need(type(c.get(k)) is str and bool(c[k]), 'MISSING_' + k)
    for k in ('generation', 'input_identity'):
        need(re.fullmatch('[a-f0-9]{64}', c[k]) is not None, 'FORMAT_' + k)
    need(c.get('purpose') == 'CURRENT_NUMERIC_CANDIDATE_OBSERVATION_ONLY', 'PURPOSE')
    need(c.get('carry_forward') is False and c.get('formula_or_chart_admission') is False
         and c.get('no_HK_scope_assumed') is True
         and c.get('missing_daily_selection') == 'BLOCKED_SCOPE', 'SCOPE_SAFETY_FLAGS')
    symbols, keys = c.get('symbols'), c.get('keys')
    need(type(symbols) is list and type(keys) is list and bool(symbols), 'MISSING_SCOPE')
    need(all(type(s) is str and re.fullmatch(r'[0-9]{6}\.(SH|SZ|BJ)', s) for s in symbols), 'IDENTITY')
    need(all(type(k) is str for k in keys), 'KEY_TYPE')
    need(type(c.get('count')) is int and c['count'] == len(symbols) == len(keys), 'COUNT')
    need(len(set(symbols)) == len(symbols) and len(set(keys)) == len(keys), 'DUPLICATE_SCOPE')
    need(keys == [s[-2:].lower() + s[:6] for s in symbols], 'KEY_BINDING')
    return {'status': 'OFFLINE_BYTE_DATE_STRUCTURE_CHECKED_NOT_ADMITTED',
            'source_date': expected_source_date, 'observation_date': expected_observation_date,
            'count': len(symbols), 'contract_sha256': sha(contract_bytes),
            'source_sha256': sha(source_bytes), 'approved_for_capture': False,
            'unverified': ['source_csv_schema_and_scope_equality', 'generation_algorithm',
                          'input_identity_algorithm', 'trading_calendar_provenance',
                          'current_owner_approval', 'resource_and_source_gates',
                          'runtime_lock_and_attempt', 'capture_runner_and_scheduler']}

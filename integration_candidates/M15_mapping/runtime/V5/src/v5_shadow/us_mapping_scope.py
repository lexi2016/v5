"""Explain the exact reviewed scope; no new relation, time or eligibility claims."""
import copy
from datetime import timezone
import re
from v5_shadow.contracts import aware, exact_keys, sha, trade_date
from v5_shadow.digests import canonical_bytes, sha256_json


def describe_scope(daily,market,reviewed):
    cards=reviewed['cards'];index={}
    for card in cards:
        for symbol in card.get('daily_match_symbols',[]):
            index.setdefault(symbol,[]).append(card)
    reasons=['BROADER_US_HK_RELATIONS_NOT_ASSESSED','TARGET_DATE_ELIGIBILITY_CANNOT_CONFIRM']
    source=market.get('source_identity') or {};saved=daily.get('source_identity') or {}
    hashes=('payload_sha256','manifest_sha256','receipt_sha256')
    same_source=(source.get('status')=='VERIFIED' and saved.get('status')=='VERIFIED'
        and all(isinstance(source.get(key),str) and len(source[key])==64 and source[key]==saved.get(key) for key in hashes))
    try:
        timely=(aware(daily.get('research_cutoff'))<=aware(market.get('research_cutoff'))
                and aware(daily.get('generated_at'))<=aware(market.get('research_cutoff')))
    except (ValueError,TypeError,AttributeError):timely=False
    ready=(timely and market.get('status')=='READY' and daily.get('source_status')=='READY'
        and daily.get('us_session_date')==market.get('expected_us_session')
        and same_source
        and daily.get('relation_artifact_sha256')==reviewed.get('artifact_sha256'))
    if not ready:reasons.append('CURRENT_US_SOURCE_OR_REVIEWED_RELATION_IDENTITY_NOT_MATCHED')
    rows=[]
    if ready:
        for raw in market.get('raw_individual_up',[]):
            symbol=raw['symbol'];matches=[copy.deepcopy(m) for m in daily.get('matches',[]) if m.get('us_symbol')==symbol]
            rows.append(dict(us_symbol=symbol,source_row=copy.deepcopy(raw),
                relation_assessment='REVIEWED_REGISTRY_MATCHED' if matches else 'NOT_IN_REVIEWED_REGISTRY_NOT_ASSESSED' if symbol not in index else 'REVIEWED_REGISTRY_NO_MATCH',
                reviewed_relation_count=len(index.get(symbol,[])) if symbol in index else None,
                matched_relation_count=len(matches) if symbol in index else None))
    assessed=sum(row['us_symbol'] in index for row in rows) if ready else None
    return dict(schema_version='v5.us_mapping_scope.v1',status='PARTIAL' if ready else 'CANNOT_CONFIRM',
        scope='PINNED_REVIEWED_RELATIONS_WITHIN_CONFIGURED_US_SAMPLE',
        reviewed_us_symbols=sorted(index),reviewed_us_symbol_count=len(index),
        reviewed_relation_artifact_sha256=reviewed['artifact_sha256'],
        registry_readback=dict(scope='ORIGINAL_REVIEWED_RETROSPECTIVE_RESEARCH_NOT_CURRENT_SELECTION',
            seed_target_date=reviewed.get('target_trade_date'),report=copy.deepcopy(reviewed.get('report')),
            cards=copy.deepcopy(cards),
            non_matching_theme_cards=[copy.deepcopy(card) for card in cards if not card.get('daily_match_symbols')],
            original_source_scope=copy.deepcopy(reviewed.get('source_scope')),
            formal_eligible=False,natural_verified=False),
        us_session_date=market.get('expected_us_session'),daily_run_id=daily.get('run_id'),
        daily_artifact_sha256=daily.get('artifact_sha256'),
        rising_individual_count=len(rows) if ready else None,assessed_rising_symbol_count=assessed,
        unassessed_rising_symbol_count=len(rows)-assessed if ready else None,
        configured_sample_count=copy.deepcopy(daily.get('coverage',{}).get('configured_us_universe_count')) if ready else None,
        full_market_coverage=False,broader_relation_result=None,
        rows=rows if ready else None,reason_codes=reasons,formal_eligible=False,natural_verified=False)


def describe_recovery_evaluation(result, request):
    """Describe a verified replay product, never its historical PIT eligibility.

    Pure projection over the fixed owner's return contract. The caller must
    finish its source/input/implementation checks before invoking this function.
    No source read, producer invocation, clock substitution or scope promotion.
    """
    def require(condition, reason):
        if not condition:
            raise ValueError('US_RECOVERY_' + reason)

    def safety_tree(value):
        # JSON/Python equality alone treats False == 0 and True == 1. Check
        # safety claims recursively even when a caller rehashes the artifact.
        flags = dict(RESEARCH_ONLY=True, production_allowed=False,
                     buy_gate_updated=False, orders_sent=False,
                     natural_verified=False, source_origin_verified=False,
                     formal_eligible=False, full_market_coverage=False,
                     readback_required=True)
        if isinstance(value, dict):
            for key, item in value.items():
                if key in flags:
                    require(type(item) is bool and item is flags[key], 'SAFETY_' + key)
                if key == 'target_date_eligibility':
                    require(item == 'CANNOT_CONFIRM', 'TARGET_ELIGIBILITY')
                safety_tree(item)
        elif isinstance(value, list):
            for item in value:
                safety_tree(item)

    try:
        canonical_bytes(result)
        canonical_bytes(request)
        safety_tree(result)
        exact_keys(request, ('target_date', 'now', 'us_data_root', 'us_files', 'manager_output_root'))
        exact_keys(result, ('schema_version', 'execution_kind', 'requested_research_cutoff', 'context_sha256',
                            'actual_started_at', 'actual_finished_at', 'source_capsule_sha256',
                            'implementation_identity', 'persisted_daily', 'payload', 'readback_status',
                            'coverage_diagnostics', 'input_sha_before', 'input_sha_after',
                            'source_origin_verified', 'natural_verified', 'isolation'))
        require(result['schema_version'] == 'v5.us_mapping_daily.v1'
                and result['execution_kind'] == 'MANUAL_RECOVERY', 'ENVELOPE')
        require(result['readback_status'] == 'MATCHED', 'READBACK')
        require(result['natural_verified'] is False and result['source_origin_verified'] is False, 'VERIFICATION_FLAGS')
        daily = result['persisted_daily']
        payload = result['payload']
        exact_keys(daily, ('schema_version', 'status', 'target_trade_date', 'run_id', 'generated_at',
                           'us_session_date', 'research_cutoff', 'coverage_scope', 'coverage', 'matches',
                           'source_status', 'source_identity', 'source_gaps', 'input_identity',
                           'relation_artifact_sha256', 'target_date_eligibility', 'producer_owner',
                           'readback_required', 'gaps', 'RESEARCH_ONLY', 'production_allowed',
                           'buy_gate_updated', 'orders_sent', 'artifact_sha256'))
        exact_keys(payload, ('schema_version', 'target_trade_date', 'daily_run', 'reviewed_research',
                             'RESEARCH_ONLY', 'production_allowed', 'buy_gate_updated', 'orders_sent'))
        require(canonical_bytes(daily) == canonical_bytes(payload['daily_run']), 'DAILY_READBACK')
        require(daily['schema_version'] == 'v4.manager_research.us_mapping_daily_run.v1'
                and payload['schema_version'] == 'v4.manager_research.us_mapping_research.v1', 'SCHEMA')
        flags = dict(RESEARCH_ONLY=True, production_allowed=False, buy_gate_updated=False, orders_sent=False)
        for value in (daily, payload):
            require(all(value[key] is expected for key, expected in flags.items()), 'SAFETY_REQUIRED')
        require(daily['readback_required'] is True, 'READBACK_REQUIRED')
        require(daily['target_date_eligibility'] == 'CANNOT_CONFIRM', 'TARGET_ELIGIBILITY')
        require(all(result['coverage_diagnostics'][key] is False
                    for key in ('formal_eligible', 'natural_verified', 'full_market_coverage')), 'HISTORICAL_FLAGS')
        target = trade_date(request['target_date'])
        session = trade_date(daily['us_session_date'])
        require(daily['target_trade_date'] == payload['target_trade_date'] == target, 'TARGET_DATE')
        require(isinstance(daily['run_id'], str) and re.fullmatch('[0-9a-f]{32}', daily['run_id']) is not None, 'RUN_ID')
        artifact = sha(daily['artifact_sha256'])
        require(sha256_json({key: value for key, value in daily.items() if key != 'artifact_sha256'}) == artifact, 'ARTIFACT_SHA')
        sha(daily['input_identity'])
        if daily['relation_artifact_sha256'] is not None:
            sha(daily['relation_artifact_sha256'])
        sha(result['context_sha256'])
        sha(result['source_capsule_sha256'])
        require(isinstance(result['implementation_identity'], dict) and bool(result['implementation_identity']), 'IMPLEMENTATION_IDENTITY')
        for value in result['implementation_identity'].values():
            sha(value)

        paths = dict(payload_path=f'research/peripherals/{session}/external_finance.json',
                     receipt_path=f'receipts/research/peripherals/{session}/external_finance.json',
                     manifest_path='research/peripherals/manifest.json')
        files = request['us_files']
        exact_keys(files, paths.values())
        for digest in files.values():
            sha(digest)
        require(canonical_bytes(files) == canonical_bytes(result['input_sha_before'])
                == canonical_bytes(result['input_sha_after']), 'SOURCE_DECLARATION')
        source = daily['source_identity']
        base_source_keys = ('owner', 'source', 'session_date', 'status',
                            'payload_path', 'receipt_path', 'manifest_path')
        verified_source = isinstance(source, dict) and source.get('status') == 'VERIFIED'
        if verified_source:
            exact_keys(source, base_source_keys + ('payload_sha256', 'receipt_sha256', 'manifest_sha256'))
        else:
            # These are the fixed original owner's failed-product shapes.
            # Missing lineage is evidence of failure, not a new success gate.
            failure_status = {'INPUT_MISSING': 'INPUT_MISSING',
                              'SOURCE_FAILED': 'FAILED', 'CANNOT_CONFIRM': 'CANNOT_CONFIRM'}
            require(daily['source_status'] in failure_status
                    and daily['status'] == failure_status[daily['source_status']], 'FAILED_SOURCE_STATUS')
            require(daily['matches'] == [], 'FAILED_SOURCE_MATCHES')
            require(daily['coverage']['reviewed_us_symbol_count'] == 4
                    and all(daily['coverage'][key] is None for key in (
                        'matched_us_symbol_count', 'matched_hk_relation_count',
                        'configured_us_universe_count', 'available_us_universe_count')), 'FAILED_SOURCE_COVERAGE')
            require(all(isinstance(daily[key], list) and bool(daily[key])
                        and all(isinstance(item, str) and bool(item) for item in daily[key])
                        for key in ('source_gaps', 'gaps')), 'FAILED_SOURCE_GAPS')
            if source is not None:
                exact_keys(source, base_source_keys + ('reason',))
                require(daily['source_status'] == source['status'] == 'CANNOT_CONFIRM'
                        and source['reason'] == 'US_MARKET_LINEAGE_BYTES_INVALID'
                        and 'US_MARKET_LINEAGE_UNVERIFIED' in daily['source_gaps'], 'UNVERIFIED_SOURCE')
        if source is not None:
            require(source['owner'] == 'ResearchPeripheralStore'
                    and source['source'] == 'external_finance' and source['session_date'] == session, 'SOURCE_IDENTITY')
            for path_key, path in paths.items():
                require(source[path_key] == path, 'SOURCE_SHA_OR_PATH')
                if verified_source:
                    require(source[path_key.replace('_path', '_sha256')] == files[path], 'SOURCE_SHA_OR_PATH')

        cutoff = aware(request['now']).astimezone(timezone.utc)
        started = aware(result['actual_started_at']).astimezone(timezone.utc)
        finished = aware(result['actual_finished_at']).astimezone(timezone.utc)
        generated = aware(daily['generated_at']).astimezone(timezone.utc)
        require(aware(result['requested_research_cutoff']) == aware(daily['research_cutoff']) == cutoff, 'CUTOFF')
        require(cutoff <= started <= finished, 'EXECUTION_TIME')
        # The fixed owner writes generated_at with UTC seconds, while the
        # wrapper records the actual start and finish with subsecond precision.
        require(generated == started.replace(microsecond=0), 'GENERATION_TIME')
        require(daily['status'] in {'COMPLETED', 'VALID_EMPTY', 'PARTIAL', 'CANNOT_CONFIRM', 'INPUT_MISSING', 'FAILED'}, 'OWNER_STATUS')
        require(isinstance(daily['source_status'], str), 'SOURCE_STATUS')
        coverage = daily['coverage']
        exact_keys(coverage, ('reviewed_us_symbol_count', 'matched_us_symbol_count', 'matched_hk_relation_count',
                              'configured_us_universe_count', 'available_us_universe_count', 'full_market_coverage'))
        require(coverage['full_market_coverage'] is False, 'COVERAGE_SCOPE')
        for key, value in coverage.items():
            if key != 'full_market_coverage':
                require(value is None or (type(value) is int and value >= 0), 'COVERAGE_COUNT')
        require(isinstance(daily['matches'], list), 'MATCHES')
        for match in daily['matches']:
            require(isinstance(match, dict) and match['session_date'] == session
                    and match['source_row']['session_date'] == session
                    and match['reviewed_relation_artifact_sha256'] == daily['relation_artifact_sha256']
                    and match['target_date_eligibility'] == 'CANNOT_CONFIRM', 'MATCH_SESSION')
        evaluation = {key: copy.deepcopy(daily[key]) for key in (
            'status', 'run_id', 'artifact_sha256', 'input_identity', 'target_trade_date', 'us_session_date',
            'generated_at', 'research_cutoff', 'source_status', 'source_identity', 'coverage', 'matches',
            'target_date_eligibility')}
        evaluation.update(schema_version='v5.us_mapping_recovery_evaluation.v1',
            scope='CURRENT_REPLAY_PRODUCT_NOT_HISTORICAL_AVAILABILITY', execution_kind=result['execution_kind'],
            actual_started_at=result['actual_started_at'], actual_finished_at=result['actual_finished_at'],
            readback_status=result['readback_status'], recorded_generated_at_lte_cutoff=generated <= cutoff,
            generation_time_precision='SECOND',
            historical_availability='NOT_ESTABLISHED', formal_eligible=False,
            natural_verified=result['natural_verified'], source_origin_verified=result['source_origin_verified'], **flags)
        return evaluation
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('US_RECOVERY_CONTRACT') from error

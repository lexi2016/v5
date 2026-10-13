"""Publish a cold-verified HK run through the existing immutable module API.

This adapter is called explicitly after a private run has been committed. The
shared module API serves the resulting records without importing this adapter,
opening the private store, collecting data, or running a selector.
"""
import ast
import json
import re

from .contracts import aware, exact_keys, sha, trade_date
from .digests import canonical_bytes, sha256_json
from .module_artifacts import publish_generation


ROUTE = '/api/v5/hk-stage-selection'
STAGES = (
    'STAGE_0925', 'STAGE_0930_0935', 'STAGE_0935_0940', 'STAGE_0940_0945',
    'STAGE_0945_1030', 'STAGE_1300_1315', 'STAGE_1445_1500', 'STAGE_1545_1555',
)
_FALSE_FLAGS = ('production_allowed', 'buy_gate_updated', 'orders_sent')
_REFERENCE_KEYS = (
    'generation_sha256', 'run_id', 'market', 'target_date', 'stage_id',
    'artifact_sha256', 'manifest_sha256', 'receipt_sha256', 'product_sha256',
)
_REDACTED = '[REDACTED_PATH]'
_PATH_KEY = re.compile(r'(?:^|_)(?:path|paths|root|roots|dir|dirs|directory|directories|relative|file|filename)$', re.I)
_FORMULA_KEY = re.compile(r'(?:^|_)formulas?$', re.I)
_QUOTED_LOCAL_PATH = re.compile(
    r'''(?P<quote>["'])(?:file://|[A-Za-z]:[\\/]|\\\\|/|~/|\.\.?/).*?(?P=quote)'''
)
# Match local paths at token boundaries, not division operators or public URLs.
_LOCAL_PATH = re.compile(
    r'''(?<![\w:/\\])(?:file://|[A-Za-z]:[\\/]|\\\\|/|~/|\.\.?/)'''
    r'''(?:[^\n\r"';,()\[\]]*[\\/])?'''
    r'''(?:[^\n\r"';,()\[\]]*?\.[A-Za-z0-9]{1,16}(?=\s|$|[,;\]\)"'])|[^\s,;\]\)"']+)'''
)


def _public_formula(value):
    # Division syntax is not a path. A literal path in a formula-labelled field
    # remains private, however, and a label alone must not bypass redaction.
    value = _QUOTED_LOCAL_PATH.sub(
        lambda match: match['quote'] + _REDACTED + match['quote'], value)
    if _LOCAL_PATH.match(value.lstrip()):
        return _REDACTED
    # Parsing never evaluates an expression. It distinguishes actual division
    # syntax from prose such as "loaded from /Users/..." in a formula label.
    try:
        ast.parse(value, mode='eval')
    except (SyntaxError, ValueError):
        return _LOCAL_PATH.sub(_REDACTED, value)
    return value


def _public_string(value):
    # Key/value evidence may contain relative paths and spaces. Preserve the
    # evidence label, but never expose a path value merely because it is relative.
    label, separator, detail = value.partition('=')
    if separator and _PATH_KEY.search(label.strip()):
        return label + '=' + _REDACTED
    if separator and _FORMULA_KEY.search(label.strip()):
        return label + '=' + _public_formula(detail)
    value = _QUOTED_LOCAL_PATH.sub(
        lambda match: match['quote'] + _REDACTED + match['quote'], value)
    return _LOCAL_PATH.sub(_REDACTED, value)


def _public_value(value, *, field=''):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            # Identity maps can use filenames as keys; absolute local keys need
            # stable opaque labels to avoid either disclosure or key collisions.
            public_key = ('redacted_path_' + sha256_json(key)
                          if _LOCAL_PATH.search(key) else key)
            result[public_key] = _public_value(item, field=key)
        return result
    if isinstance(value, list):
        return [_public_value(item, field=field) for item in value]
    if isinstance(value, str):
        if _PATH_KEY.search(field) and value:
            return _REDACTED
        if _FORMULA_KEY.search(field):
            return _public_formula(value)
        return _public_string(value)
    return value


def _reference(value):
    exact_keys(value, _REFERENCE_KEYS)
    for key in _REFERENCE_KEYS:
        if key.endswith('_sha256'):
            sha(value[key])
    trade_date(value['target_date'])
    if (value['market'] != 'HK_CONNECT' or value['stage_id'] not in STAGES
            or not isinstance(value['run_id'], str)
            or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,256}', value['run_id'])):
        raise ValueError('HK_API_REFERENCE_INVALID')
    return json.loads(canonical_bytes(value))


def _validate_readback(value, reference):
    if not isinstance(value, dict) or value.get('reference') != reference:
        raise ValueError('HK_API_REFERENCE_MISMATCH')
    artifact = value.get('artifact')
    provenance = value.get('provenance')
    if not isinstance(artifact, dict) or not isinstance(provenance, dict):
        raise ValueError('HK_API_READBACK_INVALID')
    if (artifact.get('market') != reference['market']
            or artifact.get('trade_date') != reference['target_date']
            or artifact.get('stage_id') != reference['stage_id']
            or artifact.get('run_id') != reference['run_id']):
        raise ValueError('HK_API_ARTIFACT_IDENTITY')
    if (any(value.get(flag) is not False or artifact.get(flag) is not False
            for flag in _FALSE_FLAGS)
            or value.get('natural_verified') is not False
            or provenance.get('natural_verified') is not False
            or provenance.get('formal_admission') is not False):
        raise ValueError('HK_API_SAFETY_INVALID')
    if provenance.get('data_kind') not in ('SYNTHETIC', 'RECORDED_INPUT_REPLAY'):
        raise ValueError('HK_API_DATA_KIND_INVALID')
    for key in ('input_sha256', 'source_manifest_sha256'):
        sha(provenance.get(key))
    source = provenance.get('source_identity')
    if not isinstance(source, dict):
        raise ValueError('HK_API_SOURCE_IDENTITY')
    aware(source.get('captured_at'))
    if artifact.get('selection_status') not in ('READY', 'READY_EMPTY', 'PARTIAL_WITH_ROWS', 'CANNOT_CONFIRM'):
        raise ValueError('HK_API_SELECTION_STATUS')
    # Snapshot the validated object before projecting; never mutate the reader's
    # original envelope or private evidence and never recompute owner formulas.
    return json.loads(canonical_bytes(value))


def publish_hk_stage_response(config, root, reference, *, expected_generation):
    """Cold-read one exact private run, then CAS-publish its public projection.

    ``root`` is the private HK store; ``config['data_root']`` is a separately
    V5-marked ``hk_stage`` response store. ``expected_generation`` names the
    current *module API* generation, not the private HK generation. Missing
    data, invalid identity/safety, and CAS conflicts propagate without replacing
    the active public generation. This function is never a GET handler.
    """
    if (not isinstance(config, dict) or config.get('module_id') != 'hk_stage'
            or not isinstance(config.get('routes'), list) or ROUTE not in config['routes']):
        raise ValueError('HK_API_CONFIG')
    requested = _reference(reference)
    # Import only the independent reader, and only during explicit publication.
    from .hk_stage_reader import read_hk_stage
    value = _validate_readback(read_hk_stage(root, json.loads(canonical_bytes(requested))), requested)
    provenance = value['provenance']
    payload = _public_value(value)
    is_stage8 = requested['stage_id'] == STAGES[-1]
    payload.update(schema_version='v5.hk_stage_public_response.v1',
                   status=value['artifact']['selection_status'],
                   stage_group='HK_STAGE8_SEPARATE' if is_stage8 else 'HK_SEVEN_STAGE',
                   m10_stage_member=not is_stage8)
    query = dict(date=requested['target_date'], stage=requested['stage_id'], run_id=requested['run_id'])
    record = dict(schema_version='v5.module_response.v1', module_id='hk_stage',
                  release_id=config['release_id'], path=ROUTE, query=query, payload=payload,
                  payload_sha256=sha256_json(payload), source_input_sha256=provenance['input_sha256'],
                  data_kind=provenance['data_kind'],
                  generated_at=provenance['source_identity']['captured_at'], status_code=200)
    return publish_generation(config, [record], expected_generation=expected_generation)

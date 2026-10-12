"""Explicit observed-result publication through the existing read-only API."""
import argparse
from pathlib import Path
from .digests import canonical_bytes, sha256_json
from .hk_stage_api import _public_value
from .hk_stage_observed import read_hk_stage_observed, _read_cli_json, STAGES
from .module_artifacts import publish_generation

ROUTE='/api/v5/hk-stage-observed'


def publish_hk_stage_observed_response(config, recorded_root, reference, *, expected_generation):
    if (not isinstance(config,dict) or config.get('module_id')!='hk_stage'
            or not isinstance(config.get('routes'),list) or ROUTE not in config['routes']):
        raise ValueError('M08_OBSERVED_API_CONFIG')
    read=read_hk_stage_observed(recorded_root,reference)
    payload=_public_value(read)
    stage8=reference['stage_id']==STAGES[-1]
    payload.update(schema_version='v5.hk_stage_observed_response.v1',
                   status=read['artifact']['selection_status'],
                   stage_group='HK_STAGE8_SEPARATE' if stage8 else 'HK_SEVEN_STAGE',
                   m10_stage_member=not stage8)
    record=dict(schema_version='v5.module_response.v1',module_id='hk_stage',release_id=config['release_id'],
                path=ROUTE,query=dict(date=reference['target_date'],stage=reference['stage_id'],
                                     run_id=reference['run_id'],import_sha256=reference['import_sha256']),
                payload=payload,payload_sha256=sha256_json(payload),
                source_input_sha256=reference['import_sha256'],data_kind='OWNER_RESULT',
                generated_at=read['provenance']['imported_at'],status_code=200)
    return publish_generation(config,[record],expected_generation=expected_generation)


def main(argv=None):
    parser=argparse.ArgumentParser(description='Publish a verified historical observed HK result')
    parser.add_argument('--config',required=True);parser.add_argument('--root',required=True)
    parser.add_argument('--reference',required=True);parser.add_argument('--expected-generation',required=True)
    args=parser.parse_args(argv)
    return publish_hk_stage_observed_response(_read_cli_json(args.config),Path(args.root).absolute(),
        _read_cli_json(args.reference),
        expected_generation=None if args.expected_generation=='NONE' else args.expected_generation)


if __name__=='__main__':print(canonical_bytes(main()).decode())

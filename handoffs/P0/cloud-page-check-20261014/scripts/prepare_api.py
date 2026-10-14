"""Prepare marked synthetic saved products with existing owners; no live publish."""
import json
from pathlib import Path
import sys

repo = Path(sys.argv[1]).resolve()
root = Path(sys.argv[2]).resolve()
sys.path[:0] = [str(repo / 'V5/src'), str(repo / 'V5/tests')]
from test_daily_close_recapture_owner import fixture
from test_m18_offline_pages import fixture as manager_fixture
from v5_shadow import daily_close_recapture_owner as owner, m18_offline_v2 as m18
from v5_shadow.m18_v2_publication_bridge import descriptor_from_bundle, publish_m18_descriptor, ROUTE

inputs = root / 'm17-synthetic'
inputs.mkdir()
request, ledger = fixture(inputs)
result = owner.run_close_recapture_daily(request, str(ledger), owner.bind_close_recapture_owner(request['config']))
assert result['status'] == 'SUCCEEDED', result
saved = result['state']['latest_success']
binding = dict(schema_version='v5.m17.readonly-binding.v1', state_root=request['config']['state_root'],
               universe_root=request['config']['universe_root'], ledger_root=str(ledger),
               python_executable=sys.executable, identity=result['state']['identity'], run_id=saved['run_id'],
               execution_label='MANUAL_RECOVERY', operation='EXISTING_VERIFIED_PRODUCT_REUSE')
api = root / 'source-api'
api.mkdir()
(api / '.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
routes = ['/api/v5/research/lane', '/api/v5/research/wechat/materials', '/api/v5/manager/close-recapture']
routes += ['/api/v5/source-bundle/' + suffix for suffix in ['status', 'research-intelligence', 'a-stage-saved',
    'manager-public-research', 'intraday-research', 'video-fupan', 'hk-preselection', 'hk-close-review',
    'a-close-replay', 'hk-stage-observed']]
m04 = json.loads((root / 'm04-fixture.json').read_text())
source_config = dict(schema_version='v5.module_api.v1', module_id='source_bundle', release_id='SYNTHETIC_cloud_page_check',
    data_root=str(api), routes=routes, m17_close_recapture_binding=binding,
    m04_research_lane_binding={k: m04[k] for k in ['package_root','package_manifest_sha256','archive_binding','python_executable']})
(root / 'source-config.json').write_text(json.dumps(source_config, indent=2))

raw, saved_raw, identity = manager_fixture(run='46596b03c2ab4e29b1219fd2e5eb698f', extra={
    'stocks':[dict(code='SYNTHETIC_ONLY',name='合成经理股票',status='PARTIAL')],
    'gaps':['SYNTHETIC_NOT_REAL_MARKET','SYNTHETIC_NO_PIT_ACCEPTANCE']})
bundle = m18.build(raw, saved_raw, identity, expected_profile=m18.PROFILE_SHA256)
bundle_root = root / 'manager-bundle'
(bundle_root / 'objects').mkdir(parents=True)
(bundle_root / 'manifest.json').write_bytes(bundle.manifest)
for key, value in bundle.objects.items():
    (bundle_root / 'objects' / key).write_bytes(value)
publication = root / 'manager-api'
publication.mkdir()
(publication / '.v5-module-root').write_text('v5.module-root.v1:manager\n')
manager_config = dict(schema_version='v5.module_api.v1', module_id='manager', release_id='SYNTHETIC_cloud_page_check',
    data_root=str(publication), routes=[ROUTE,ROUTE+'/pages',ROUTE+'/overview',ROUTE+'/sections'],
    m18_v2_binding=dict(manifest_sha256=m18.sha(bundle.manifest), identity=identity,
                      profile_sha256=m18.PROFILE_SHA256, bundle_root=str(bundle_root)))
reader = m18.Reader(bundle, m18.sha(bundle.manifest), identity, expected_profile=m18.PROFILE_SHA256)
descriptor = descriptor_from_bundle(reader, identity, json.loads(bundle.manifest))
descriptor['generated_at']='2026-10-12T00:00:00+00:00'
publish_m18_descriptor(manager_config, descriptor, expected_generation=None)
(root / 'manager-config.json').write_text(json.dumps(manager_config, indent=2))
info = dict(input_kind='SYNTHETIC', natural_verified=False, real_provider_execution='NOT_RUN',
            m04_dates=m04['dates'], m17_query=dict(source_trade_date=request['source_trade_date'], run_id=saved['run_id']),
            m17_reference=saved['product_reference'], manager_descriptor=descriptor,
            legal_real_archive_copy='NOT_FOUND; no new acquisition requested or performed')
(root / 'fixture-info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2))
print(json.dumps({'status':'SYNTHETIC_FIXTURES_PREPARED','m17_query':info['m17_query'],'m04_dates':info['m04_dates']}))

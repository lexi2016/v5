"""Bounded M18 v2 publication bridge.

Consumes an already-built v2 bundle and publishes only descriptors/chunks through
module_artifacts. It never builds bundles, runs owners, or performs collection.
"""
from __future__ import annotations

from datetime import datetime, timezone
from .module_artifacts import publish_generation

ROUTE = "/api/v4/manager/m18/v2"


def descriptor_from_bundle(reader, identity, bundle_meta):
    """Create a small API object; large response bytes stay in v2 pages."""
    if bundle_meta.get("identity") != identity:
        raise ValueError("M18_IDENTITY_MISMATCH")
    return {
        "schema_version": "v5.m18.v2.descriptor.v1",
        "identity": identity,
        "run_id": identity["run_id"],
        "target_date": identity["target_date"],
        "generation_id": bundle_meta["generation_id"],
        "profile_sha256": bundle_meta["profile_sha256"],
        "pages_route": ROUTE + "/pages",
        "status": "READY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def publish_m18_descriptor(config, descriptor, *, expected_generation):
    record = {
        "schema_version": "v5.module_response.v1",
        "module_id": config["module_id"],
        "release_id": config["release_id"],
        "path": ROUTE,
        "query": {"run_id": descriptor["run_id"]},
        "payload": descriptor,
        "payload_sha256": __import__("v5_shadow.digests", fromlist=["sha256_json"]).sha256_json(descriptor),
        "source_input_sha256": descriptor["profile_sha256"],
        "data_kind": "OWNER_RESULT",
        "generated_at": descriptor["generated_at"],
        "status_code": 200,
    }
    return publish_generation(config, [record], expected_generation=expected_generation)


def publish_daily_manager_result(*, request, result, config, expected_generation,
                                 expected_run_id, expected_plan_sha256):
    """Publish an already verified saved result; never call an owner or refresh.

    Full offline build + independent disk read must finish before the existing
    module CAS exposes either the exact-run descriptor or the current alias.
    Transport success does not change PARTIAL/gaps or business acceptance.
    """
    import os
    import re
    import tempfile
    from contextlib import ExitStack
    from pathlib import Path
    from . import m18_offline_v2 as m
    from .m18_offline_v2_process import run
    from .module_api import (_config, _open_directory, _read_regular, _generation_head,
                             _load_generation, _read_object, read_response, response_key,
                             _m18_identity_from_descriptor, _m18_read_value)
    from .module_artifacts import _directory, _write_once
    from .digests import sha256_json
    from .contracts import sha

    if config.get('m18_v2_daily_publication') is not True:
        raise ValueError('M18_DAILY_PUBLICATION_DISABLED')
    if request.get('action') != 'read' or request.get('view') != 'auto':
        raise ValueError('M18_DAILY_READ_REQUIRED')
    if (not isinstance(expected_run_id, str)
            or not re.fullmatch('[0-9a-f]{32}', expected_run_id)):
        raise ValueError('M18_DAILY_RUN_ID')
    sha(expected_plan_sha256)
    if result.get('request_sha256') != sha256_json(request):
        raise ValueError('M18_DAILY_REQUEST_SHA')
    product = result.get('payload', {}).get('plan_product', {})
    attempt = result.get('payload', {}).get('workspace_plan_attempt', {})
    if (product.get('consumed') is not True or product.get('run_id') != expected_run_id
            or product.get('sha256') != expected_plan_sha256
            or attempt.get('run_id') != expected_run_id
            or attempt.get('state') not in {'SUCCEEDED', 'SUCCEEDED_EMPTY', 'PARTIAL'}):
        raise ValueError('M18_DAILY_SAME_ATTEMPT')
    response = {key: value for key, value in result.items() if key != 'local_result_transport'}
    identity = dict(run_id=expected_run_id, target_date=request['target_date'],
                    plan_sha256=expected_plan_sha256, raw_sha256='0' * 64,
                    response_sha256=m.v1.streamed_sha(response),
                    input_identity=result['payload']['input_identity'])
    m.v1.identity_check(identity)
    if result['readback'].get('store_relative', '.') != '.':
        raise ValueError('M18_DAILY_ORIGINAL_STORE_REQUIRED')
    saved_root = _open_directory(Path(request['manager_output_root']) /
                                 'workspace_plans' / identity['target_date'])
    try:
        saved_fd = os.open(expected_run_id + '.json', os.O_RDONLY | os.O_NOFOLLOW |
                           os.O_NONBLOCK, dir_fd=saved_root)
        try:
            saved_raw = _read_regular(saved_fd, m.PROFILE['generation_bytes'] - 1)
        finally:
            os.close(saved_fd)
    finally:
        os.close(saved_root)
    identity['raw_sha256'] = m.sha(saved_raw)
    generation = m.generation(identity)
    with ExitStack() as cleanup:
        checked, root = _config(config)
        cleanup.callback(os.close, root)
        if _generation_head(root, checked) != expected_generation:
            raise ValueError('GENERATION_CONFLICT')
        # Read from the immutable expected generation, not a racing active head.
        # The final CAS makes this existing-run check part of the same decision.
        previous = None
        query = {'run_id': expected_run_id}
        if expected_generation is not None:
            refs = _load_generation(root, checked, expected_generation)['records']
            key = response_key(checked['module_id'], ROUTE, query)
            if key in refs:
                previous = _read_object(root, refs[key], checked)[0]['payload']
        else:
            try:
                previous = read_response(checked, root, ROUTE, query)[0]['payload']
            except FileNotFoundError:
                pass
        if previous is not None:
            _m18_identity_from_descriptor(previous)
            if previous['identity'] != identity or 'manifest_sha256' not in previous:
                raise ValueError('M18_DAILY_RUN_IMMUTABLE')
        bundles = _directory(root, 'm18-v2-bundles')
        cleanup.callback(os.close, bundles)
        parent = Path(checked['data_root']) / 'm18-v2-bundles'
        def check_parent():
            current = _open_directory(parent)
            try:
                before, after = os.fstat(bundles), os.fstat(current)
                if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                    raise ValueError('M18_DAILY_ROOT_CHANGED')
            finally:
                os.close(current)
        check_parent()
        # Private temporary staging never follows a replaceable publication path.
        # Final immutable writes below use only the retained directory handles.
        with tempfile.TemporaryDirectory(prefix='v5-m18-daily-') as temporary:
            stage = Path(temporary).resolve()
            saved = stage / 'saved.json'; saved.write_bytes(saved_raw)
            response_path = stage / 'response.json'
            size = 0
            with response_path.open('xb') as stream:
                for piece in m.v1._pieces(response):
                    size += len(piece)
                    m.require(size < m.PROFILE['generation_bytes'], 'V2_SOURCE_LIMIT')
                    stream.write(piece)
            build = run(dict(action='build', output_root=str(stage / 'bundle'),
                identity=identity, profile_sha256=m.PROFILE_SHA256,
                response_path=str(response_path), saved_path=str(saved)))
            if build['status'] != 'OK':
                raise ValueError('M18_DAILY_BUILD_REJECTED')
            if previous is not None and (previous['manifest_sha256'] != build['manifest_sha256']
                    or previous['profile_sha256'] != m.PROFILE_SHA256):
                raise ValueError('M18_DAILY_RUN_IMMUTABLE')
            check_parent()
            destination = _directory(bundles, generation)
            try:
                objects = _directory(destination, 'objects')
                try:
                    built = stage / 'bundle'
                    _write_once(destination, 'manifest.json', (built / 'manifest.json').read_bytes())
                    for path in (built / 'objects').iterdir():
                        if not re.fullmatch('[0-9a-f]{64}', path.name):
                            raise ValueError('M18_DAILY_OBJECT_NAME')
                        _write_once(objects, path.name, path.read_bytes())
                finally:
                    os.close(objects)
            finally:
                os.close(destination)
        check_parent()
        binding = dict(bundle_root=str(parent / generation), identity=identity,
                       manifest_sha256=build['manifest_sha256'], profile_sha256=m.PROFILE_SHA256)
        # Existing read-only worker pins every ancestor and verifies the complete
        # persisted bundle under unchanged resource budgets before returning.
        _m18_read_value(binding, 'overview', {})
        check_parent()
        descriptor = previous or descriptor_from_bundle(None, identity, dict(identity=identity,
            generation_id=generation, profile_sha256=m.PROFILE_SHA256))
        descriptor['manifest_sha256'] = build['manifest_sha256']
        records = [dict(schema_version='v5.module_response.v1', module_id=checked['module_id'],
            release_id=checked['release_id'], path=ROUTE, query=query, payload=descriptor,
            payload_sha256=sha256_json(descriptor), source_input_sha256=result['request_sha256'],
            data_kind='OWNER_RESULT', generated_at=descriptor['generated_at'], status_code=200)
            for query in ({'run_id':expected_run_id}, {})]
        from .p0_manager_publication_bridge import ROUTE as workspace_route, build_manager_record
        if workspace_route in checked['routes']:
            records.append(build_manager_record(config=checked, payload=result['payload'],
                source_input_sha256=result['request_sha256'], date=identity['target_date']))
        return publish_generation(checked, records, expected_generation=expected_generation)

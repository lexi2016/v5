"""V5 application bundle: existing read-only API + existing static gateway.

No owner invocation, collection, scheduler installation, or V4 service access.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
from .composition import no_symlinks
from .contracts import exact_keys

BASE = Path(__file__).resolve().parents[2]
MARKER = '.v5-standalone-root'
MARKER_BYTES = b'v5.standalone-root.v1\n'
MANIFEST = 'contracts/standalone_sources.json'


def verify_package(base=BASE):
    base = no_symlinks(base)
    manifest = json.loads((base/MANIFEST).read_bytes())
    if manifest.get('schema_version') != 'v5.standalone_sources.v1':
        raise ValueError('STANDALONE_MANIFEST_SCHEMA')
    names = set()
    for row in manifest['files']:
        relative = Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts or str(relative) in names:
            raise ValueError('STANDALONE_MANIFEST_PATH')
        path = no_symlinks(base/relative)
        if not path.is_relative_to(base) or not path.is_file():
            raise ValueError('STANDALONE_RESOURCE_MISSING:'+str(relative))
        raw = path.read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('STANDALONE_RESOURCE_SHA:'+str(relative))
        names.add(str(relative))
    # Reject injected modules/resources inside the shipped runtime directories.
    actual = {str(p.relative_to(base)) for name in manifest['directories']
              for p in (base/name).rglob('*') if p.is_file()}
    if actual - names - {MANIFEST}:
        raise ValueError('STANDALONE_UNLISTED_RESOURCE')
    return dict(status='PACKAGE_VERIFIED', files=len(names),
                frontend_source_commit=manifest['frontend_source_commit'],
                business_verified=False, daily_enabled=False)


def _separate_root(root):
    root = no_symlinks(root)
    if root.is_relative_to(BASE) or BASE.is_relative_to(root):
        raise ValueError('STANDALONE_SOURCE_ROOT_OVERLAP')
    return root


def initialize_root(root):
    root = _separate_root(root)
    if root.exists():
        raise ValueError('STANDALONE_FRESH_ROOT_REQUIRED')
    root.mkdir(parents=True)
    (root/MARKER).write_bytes(MARKER_BYTES)
    for name in ('config', 'data', 'runtime', 'logs'):
        (root/name).mkdir()
    return dict(status='ROOT_INITIALIZED_NO_DATA', root=str(root), daily_enabled=False)


def _inside(root, value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('STANDALONE_PATH_INVALID')
    candidate = Path(value)
    path = no_symlinks(candidate if candidate.is_absolute() else root/candidate)
    if not path.is_relative_to(root) or path == root:
        raise ValueError('STANDALONE_PATH_OUTSIDE_ROOT')
    return path


def load_config(root, relative='config/standalone.json'):
    root = _separate_root(root)
    marker = no_symlinks(root/MARKER)
    if marker.read_bytes() != MARKER_BYTES:
        raise ValueError('STANDALONE_ROOT_MARKER')
    config = json.loads(_inside(root, relative).read_bytes())
    exact_keys(config, ('schema_version', 'port', 'module_api'))
    if config['schema_version'] != 'v5.standalone.v1':
        raise ValueError('STANDALONE_CONFIG_SCHEMA')
    if type(config['port']) is not int or not 0 <= config['port'] <= 65535:
        raise ValueError('STANDALONE_PORT_INVALID')
    module = config['module_api']
    if module.get('module_id') != 'manager':
        raise ValueError('STANDALONE_MANAGER_ONLY')
    module['data_root'] = str(_inside(root, module['data_root']))
    if 'm18_v2_binding' in module:
        binding = module['m18_v2_binding']
        binding['bundle_root'] = str(_inside(root, binding['bundle_root']))
    from .module_api import _config, M18_ROUTE
    if set(module['routes']) - {M18_ROUTE, M18_ROUTE+'/pages', M18_ROUTE+'/overview', M18_ROUTE+'/sections'}:
        raise ValueError('STANDALONE_SAVED_ROUTES_ONLY')
    checked, fd = _config(module)
    os.close(fd)
    # Validate output parents before the existing runtime can create files.
    _inside(root, 'runtime')
    return dict(config, module_api=checked)


def serve(root, config):
    from . import main_runtime
    from .api_gateway import create_gateway, load_frontend
    root = _separate_root(root)
    verify_package()
    frontend_manifest = json.loads((BASE/'frontend/manifest.json').read_bytes())
    frontend = load_frontend(BASE/'frontend/dist',
                             {r['path']: r['sha256'] for r in frontend_manifest['files']})
    runtime = dict(runtime_root=str(_inside(root, 'runtime')),
                   composition='STANDALONE_READ_ONLY_NO_DAILY_COMPOSITION',
                   module_api=config['module_api'])
    started = False
    gateway = None
    try:
        ready = main_runtime.start(runtime)
        started = True
        module = config['module_api']
        gateway_config = dict(schema_version='v5.api_gateway.v1',
            modules=dict(manager=dict(port=ready['identity']['port'], timeout_seconds=30,
                                      max_inflight=1, release_id=module['release_id'])),
            routes=[dict(path=path, module_id='manager', methods=['GET']) for path in module['routes']])
        gateway = create_gateway(gateway_config, port=config['port'], frontend=frontend)
        print(json.dumps(dict(status='READY_READ_ONLY', pid=os.getpid(),
            port=gateway.server_address[1], module_pid=ready['identity']['module_pid'],
            url='http://127.0.0.1:'+str(gateway.server_address[1])+'/manager-selection/',
            daily_enabled=False, business_verified=False)), flush=True)
        gateway.serve_forever()
    finally:
        if gateway is not None:
            gateway.server_close()
        if started:
            main_runtime.stop(runtime)



def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('verify', 'init', 'validate', 'serve'))
    parser.add_argument('--root', type=Path)
    parser.add_argument('--config', default='config/standalone.json')
    args = parser.parse_args(argv)
    if args.command == 'verify':
        print(json.dumps(verify_package()));return 0
    if args.root is None:
        parser.error('--root is required')
    if args.command == 'init':
        print(json.dumps(initialize_root(args.root)));return 0
    config = load_config(args.root, args.config)
    if args.command == 'validate':
        print(json.dumps(dict(verify_package(), status='CONFIGURATION_VALID_READ_ONLY')));return 0
    def stop(_signum, _frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    if hasattr(signal, 'SIGHUP'):signal.signal(signal.SIGHUP, stop)
    try:serve(args.root, config)
    except KeyboardInterrupt:pass
    return 0

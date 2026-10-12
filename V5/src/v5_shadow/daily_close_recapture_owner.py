"""M17 independent late owner/reader and original-ledger adapter.

Real collection requires an explicit verified runtime/root binding. Python audit guards are
not an OS sandbox. The original owner owns algorithms, windows and publication.
No scheduler is installed and no shared P0 file is changed by this module.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v5_shadow.composition import no_symlinks
from v5_shadow.contracts import aware, exact_keys, trade_date, sha
from v5_shadow.digests import canonical_bytes, sha256_json
from v5_shadow.module_api import _open_directory, _read_at, _read_regular
from v5_shadow.run_ledger import claim_run, finish_run, read_run

LANE = 'manager_close_recapture'
MODE = 'PYTDX_LATE_OBSERVATION'
FLAGS = dict(RESEARCH_ONLY=True, production_allowed=False, buy_gate_updated=False, orders_sent=False)
MANIFEST_SHA256 = 'f3c6eedee74ea4d2f72641e4c0e9386b844ff0dfd40506f8c2e1ba566a94cf50'
MARKER = b'v5.m17.simulated-close.v1\n'
REAL_MARKER = b'v5.m17.close.v1\n'
CONFIG_KEYS = ('capture_mode', 'owner_root', 'python', 'state_root', 'universe_root', 'source_manifest', 'timeout_seconds')


class OutcomeUnknown(RuntimeError):
    """The original producer may have written: retain RUNNING, never retry."""


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read_file(path):
    path = no_symlinks(Path(path))
    fd = _open_directory(path.parent)
    try:
        return _read_at(fd, None, path.name)
    finally:
        os.close(fd)


def _config(config):
    exact_keys(config, (*CONFIG_KEYS, 'real_binding') if 'real_binding' in config else CONFIG_KEYS)
    if config['capture_mode'] != MODE:
        raise ValueError('M17_CAPTURE_MODE_NOT_BOUND')
    if type(config['timeout_seconds']) is not int or not 1 <= config['timeout_seconds'] <= 420:
        raise ValueError('M17_TIMEOUT_CONTRACT')
    # Existing venv interpreters may be symlinks. No installation or credential use.
    python = Path(config['python'])
    if not python.is_absolute() or not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError('M17_EXISTING_PYTHON_REQUIRED')
    owner = no_symlinks(Path(config['owner_root']))
    state = no_symlinks(Path(config['state_root']))
    universe = no_symlinks(Path(config['universe_root']))
    for other in (owner, universe):
        if state.is_relative_to(other) or other.is_relative_to(state):
            raise ValueError('M17_ROOT_OVERLAP')
    if _read_file(state / '.v5-m17-close-root') not in (MARKER, REAL_MARKER):
        raise ValueError('M17_PRIVATE_ROOT_REQUIRED')
    raw = _read_file(config['source_manifest'])
    if _sha(raw) != MANIFEST_SHA256:
        raise ValueError('M17_SOURCE_MANIFEST_MISMATCH')
    manifest = json.loads(raw)
    if manifest['schema'] != 'v5.m17.close-recapture-source.v1' or len(manifest['files']) != 24:
        raise ValueError('M17_SOURCE_MANIFEST_CONTRACT')
    actual = {}
    for entry in manifest['files']:
        path = entry['path']
        if Path(path).is_absolute() or '..' in Path(path).parts or path in actual:
            raise ValueError('M17_SOURCE_PATH')
        content = _read_file(owner / path)
        if len(content) != entry['bytes'] or _sha(content) != entry['sha256']:
            raise ValueError('M17_SOURCE_BYTES_MISMATCH')
        actual[path] = _sha(content)
    return sha256_json(actual)


def bind_close_recapture_owner(config):
    dependency = _config(config)
    # Include the real ledger/import closure in the adapter's code identity.
    names = ('daily_close_recapture_owner.py', 'run_ledger.py', 'contracts.py', 'digests.py',
             'module_api.py', 'module_artifacts.py', 'api_gateway.py', 'composition.py', '__init__.py')
    return dict(invoke=run_close_recapture_owner,
                code_sha256=sha256_json({n: _sha(_read_file(Path(__file__).with_name(n))) for n in names}),
                config_sha256=sha256_json(config), dependency_sha256=dependency)


def request_identity(request, binding):
    if request.get('execution_kind') not in {'SIMULATED', 'OWNER_VERIFIED'}:
        raise ValueError('M17_EXECUTION_KIND')
    keys = {'config', 'source_trade_date', 'research_cutoff', 'execution_kind'}
    if request.get('execution_kind') == 'SIMULATED':
        keys.add('simulation')
    exact_keys(request, keys)
    trade_date(request['source_trade_date']); aware(request['research_cutoff'])
    if request['execution_kind'] == 'SIMULATED' and _read_file(Path(request['config']['state_root'])/'.v5-m17-close-root') != MARKER:
        raise ValueError('M17_SIMULATED_ROOT_MARKER_REQUIRED')
    current = bind_close_recapture_owner(request['config'])
    if any(binding.get(k) != current[k] for k in ('code_sha256', 'config_sha256', 'dependency_sha256')):
        raise ValueError('M17_BINDING_CHANGED')
    if binding.get('invoke') is not run_close_recapture_owner:
        raise ValueError('M17_INVOKE_NOT_BOUND')
    return dict(lane=LANE, target_date=request['source_trade_date'], input_sha256=sha256_json(request),
                research_cutoff=request['research_cutoff'], **{k: current[k] for k in
                ('code_sha256', 'config_sha256', 'dependency_sha256')})


def _receipt(status, reference, reasons, verified=False):
    return dict(status=status, product_reference=reference, readback_verified=verified,
                retry_safe_without_external_effect=False, reason_codes=reasons)


def verify_envelope(value, request, ledger_run_id):
    if (not isinstance(value, dict) or value.get('ledger_run_id') != ledger_run_id
            or value.get('request_sha256') != sha256_json(request)
            or value.get('source_trade_date') != request['source_trade_date']
            or value.get('execution_kind') != request['execution_kind']
            or value.get('natural_verified') is not False
            or any(value.get(k) is not v for k, v in FLAGS.items())):
        raise ValueError('M17_WORKER_ENVELOPE_MISMATCH')
    return value


def _process(role, request, ledger_run_id):
    config = request['config']
    _config(config)
    packet = canonical_bytes(dict(request=request, ledger_run_id=ledger_run_id))
    try:
        child = subprocess.run([config['python'], '-I', '-B', str(Path(__file__).resolve()),
                                '--worker', role], input=packet, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=config['timeout_seconds'],
                               cwd=config['owner_root'], env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'})
    except (subprocess.TimeoutExpired, OSError) as error:
        raise OutcomeUnknown('M17_WORKER_OUTCOME_UNKNOWN') from error
    if child.returncode or len(child.stdout) > 1024 * 1024:
        raise OutcomeUnknown('M17_WORKER_EXIT_OR_OUTPUT_UNKNOWN')
    try:
        value = json.loads(child.stdout)
        return verify_envelope(value, request, ledger_run_id)
    except (ValueError, TypeError) as error:
        raise OutcomeUnknown('M17_WORKER_ENVELOPE_UNKNOWN') from error


def _same_product(producer, reader):
    for key in ('ledger_run_id', 'request_sha256', 'source_trade_date', 'plan_trade_date', 'files'):
        if producer.get(key) != reader.get(key):
            raise OutcomeUnknown('M17_PRODUCER_READER_MISMATCH')


def run_close_recapture_owner(request, ledger_run_id):
    """Dispatcher-compatible five-field receipt; no hidden generic callbacks."""
    binding = bind_close_recapture_owner(request['config'])
    request_identity(request, binding)
    if not re.fullmatch('[a-zA-Z0-9_-]{1,128}', ledger_run_id):
        raise ValueError('M17_LEDGER_RUN_ID')
    if request['execution_kind'] == 'OWNER_VERIFIED':
        reasons = real_binding_reasons(request)
        if reasons:
            return _receipt('BLOCKED', dict(**FLAGS, natural_verified=False), reasons)
    producer = _process('producer', request, ledger_run_id)
    status = producer['owner_status']
    if status not in {'MATERIALIZED', 'ALREADY_EXISTS', 'PARTIAL'}:
        terminal = 'BLOCKED' if status in {'NOT_APPLICABLE', 'INPUT_MISSING', 'PENDING_SLOT'} else 'FAILED'
        return _receipt(terminal, producer, [producer.get('reason') or 'M17_ORIGINAL_OWNER_NOT_READY'])
    reader = _process('reader', request, ledger_run_id)
    if reader['owner_status'] not in {'READY', 'PARTIAL'}:
        return _receipt('FAILED', reader, ['M17_INDEPENDENT_READER_REJECTED'])
    _same_product(producer, reader)
    reference = dict(reader, producer_pid=producer['pid'], reader_pid=reader['pid'],
                     producer_status=status, root=request['config']['state_root'])
    return _receipt('SUCCEEDED', reference, reader['cannot_confirm'], verified=True)


def run_close_recapture_daily(request, ledger_root, binding):
    identity = request_identity(request, binding)
    claim = claim_run(ledger_root, identity, max_attempts=1)
    if claim['status'] == 'REUSED_SUCCESS':
        saved = claim['state']['latest_success']
        try:
            reader = _process('reader', request, saved['run_id'])
            if reader['owner_status'] not in {'READY', 'PARTIAL'}:
                raise ValueError('M17_SAVED_READER_REJECTED')
            _same_product(saved['product_reference'], reader)
            if saved['product_reference']['pool'] != reader['pool']:
                raise ValueError('M17_SAVED_POOL_CHANGED')
        except (ValueError, OutcomeUnknown):
            return dict(status='BLOCKED_SAVED_PRODUCT_INVALID', state=claim['state'], natural_verified=False)
        return dict(claim, readback_verified=True, natural_verified=False)
    if claim['status'] != 'CLAIMED':
        return dict(claim, natural_verified=False)
    try:
        receipt = binding['invoke'](request, claim['run_id'])
    except OutcomeUnknown:
        return dict(status='IN_PROGRESS_OR_OUTCOME_UNKNOWN', state=read_run(ledger_root, identity), natural_verified=False)
    state = finish_run(ledger_root, claim, receipt)
    reopened = read_run(ledger_root, identity)
    if reopened != state or reopened['attempts'][-1]['run_id'] != claim['run_id']:
        raise OutcomeUnknown('M17_LEDGER_READBACK_MISMATCH')
    if receipt['status'] == 'SUCCEEDED' and reopened['latest_success']['product_reference']['ledger_run_id'] != claim['run_id']:
        raise OutcomeUnknown('M17_LEDGER_PRODUCT_RUN_MISMATCH')
    return dict(status=receipt['status'], state=reopened, natural_verified=False)


def _audit_guard(role, state, allowed_commands=()):
    """In-process guards, not a claim of OS-enforced sandbox isolation."""
    def audit(event, args):
        if event == 'subprocess.Popen':
            if role != 'producer' or list(args[1]) not in allowed_commands:
                raise PermissionError('M17_CHILD_PROCESS_NOT_BOUND')
        if event.startswith('socket.') or event in {'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn', 'os.exec', 'os.spawn'}:
            raise PermissionError('M17_NETWORK_OR_CHILD_PROCESS_DENIED')
        if event == 'open':
            path, mode, flags = args
            writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if writing and role == 'reader':
                raise PermissionError('M17_READER_WRITE_DENIED')
            if writing and isinstance(path, (str, bytes)) and os.path.isabs(path):
                if not Path(os.fsdecode(path)).is_relative_to(state):
                    raise PermissionError('M17_WRITE_ROOT_DENIED')
        if role == 'reader' and event in {'os.mkdir', 'os.remove', 'os.rename', 'os.rmdir', 'os.link', 'os.symlink', 'os.chmod', 'os.truncate'}:
            raise PermissionError('M17_READER_WRITE_DENIED')
    sys.addaudithook(audit)


REAL_KEYS = ('active_capture_mode', 'pytdx_python', 'pytdx_python_sha256',
             'pytdx_exhq_sha256', 'provider_root', 'state_root', 'universe_root')

# A fixed read-only admission probe, never arbitrary code supplied in config.
_RUNTIME_PROBE = """import sys, importlib.util, pathlib, hashlib, json, os
sys.dont_write_bytecode = True
def guard(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.exec','os.spawn','os.posix_spawn','os.fork'):
        raise PermissionError('M17_RUNTIME_PROBE_NETWORK_OR_PROCESS_DENIED')
    if event == 'open':
        mode, flags = args[1], args[2]
        if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
            raise PermissionError('M17_RUNTIME_PROBE_WRITE_DENIED')
sys.addaudithook(guard)
try:
    spec = importlib.util.find_spec('pytdx.exhq')
    value = dict(available=spec is not None and bool(spec.origin))
    if value['available']:
        value['module_sha256'] = hashlib.sha256(pathlib.Path(spec.origin).read_bytes()).hexdigest()
except (ImportError, OSError, ValueError):
    value = dict(available=False)
print(json.dumps(value,sort_keys=True))
"""


def real_runtime_command(binding):
    return [binding['pytdx_python'], '-I', '-B', '-c', _RUNTIME_PROBE]


def _probe_command(binding):
    return [binding['pytdx_python'], '-m', 'scripts.live_acquisition.pytdx_exhq_probe']


def _real_environment(binding=None):
    env = dict(PATH=os.defpath, PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1',
               RESEARCH_ONLY='true', PRODUCTION_ALLOWED='false', BUY_GATE_UPDATED='false', ORDERS_SENT='false')
    if binding is not None:
        env['PYTHONPATH'] = binding['provider_root']
    return env


def _runtime_sha(path):
    # Executables can exceed the JSON artifact limit. Reuse the original regular
    # file/no-change reader with a separate bounded binary budget.
    path = no_symlinks(Path(path).resolve())
    parent = _open_directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        return _sha(_read_regular(fd, 128 * 1024 * 1024))
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def real_binding_reasons(request):
    config = request['config']; binding = config.get('real_binding')
    if binding is None:
        return ['REAL_COLLECTOR_NOT_BOUND']
    try:
        exact_keys(binding, REAL_KEYS)
        if binding['active_capture_mode'] != MODE:
            return ['M17_REAL_ACTIVE_MODE_NOT_BOUND']
        if binding['state_root'] != config['state_root'] or binding['universe_root'] != config['universe_root']:
            return ['M17_REAL_ROOT_BINDING']
        for name in ('state_root', 'universe_root'):
            if not no_symlinks(Path(binding[name])).is_dir():
                return ['M17_REAL_ROOT_MISSING']
        if _read_file(Path(binding['state_root'])/'.v5-m17-close-root') != REAL_MARKER:
            return ['M17_REAL_ROOT_MARKER_REQUIRED']
        provider = no_symlinks(Path(binding['provider_root']))
        if provider != Path(config['owner_root'])/'upstreams/v3_shared_data':
            return ['M17_REAL_PROVIDER_BINDING']
        python = Path(binding['pytdx_python'])
        if not python.is_absolute() or not python.is_file() or not os.access(python, os.X_OK):
            return ['M17_REAL_INTERPRETER_MISSING']
        sha(binding['pytdx_python_sha256']); sha(binding['pytdx_exhq_sha256'])
        if _runtime_sha(python) != binding['pytdx_python_sha256']:
            return ['M17_REAL_INTERPRETER_SHA_MISMATCH']
        if aware(request['research_cutoff']) > datetime.now(timezone.utc):
            return ['M17_REAL_FUTURE_REQUEST_CUTOFF']
    except (OSError, ValueError, KeyError, TypeError):
        return ['M17_REAL_BINDING_INVALID']
    return []


def _real_runtime_ready(binding):
    try:
        result = subprocess.run(real_runtime_command(binding), capture_output=True, text=True,
            timeout=10, shell=False, env=_real_environment())
        if result.returncode or len(result.stdout) > 8192:
            return False
        value = json.loads(result.stdout)
        return value.get('available') is True and value.get('module_sha256') == binding['pytdx_exhq_sha256']
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        return False


class _ProbeOutcomeUnknown(BaseException):
    """Escape the frozen collector's except Exception failure downgrade.

    The worker must exit without a terminal receipt if its fixed probe may still
    have been in flight. The parent retains its original RUNNING claim.
    """


def _real_process_runner(binding, source_date):
    def run(command, **kwargs):
        # The original collector alone supplies quote-request bytes. No shell,
        # alternative module, extra env, or caller-defined command is admitted.
        if command != _probe_command(binding) or kwargs.get('shell') is not False:
            raise ValueError('M17_REAL_PROBE_COMMAND_NOT_BOUND')
        allowed = {'input','capture_output','text','encoding','errors','timeout','shell'}
        if set(kwargs) != allowed or not 0 < kwargs['timeout'] <= 180:
            raise ValueError('M17_REAL_PROBE_OPTIONS_NOT_BOUND')
        payload = json.loads(kwargs['input'])
        exact_keys(payload, ('trade_date', 'stage_id', 'codes'))
        if payload['trade_date'] != source_date or payload['stage_id'] != 'STAGE_1545_1555':
            raise ValueError('M17_REAL_PROBE_SOURCE_NOT_BOUND')
        try:
            result = subprocess.run(command, **kwargs, env=_real_environment(binding), cwd=binding['provider_root'])
        except (subprocess.TimeoutExpired, OSError) as error:
            raise _ProbeOutcomeUnknown('M17_REAL_PROBE_OUTCOME_UNKNOWN') from error
        if result.returncode < 0:
            raise _ProbeOutcomeUnknown('M17_REAL_PROBE_OUTCOME_UNKNOWN')
        return result
    return run


def _worker(role, packet):
    request, run_id = packet['request'], packet['ledger_run_id']
    config = request['config']; _config(config)
    execution = request['execution_kind']
    if execution not in {'SIMULATED', 'OWNER_VERIFIED'}:
        raise ValueError('M17_EXECUTION_KIND')
    envelope = dict(ledger_run_id=run_id, request_sha256=sha256_json(request),
                    source_trade_date=request['source_trade_date'], execution_kind=execution,
                    natural_verified=False, pid=os.getpid(), **FLAGS)
    state = Path(config['state_root']); owner_root = Path(config['owner_root'])
    commands = []
    if execution == 'OWNER_VERIFIED':
        reasons = real_binding_reasons(request)
        if reasons:
            return dict(envelope, owner_status='INPUT_MISSING', reason=reasons[0])
        binding = config['real_binding']
        if role == 'producer':
            commands = [real_runtime_command(binding), _probe_command(binding)]
    elif _read_file(state/'.v5-m17-close-root') != MARKER:
        raise ValueError('M17_SIMULATED_ROOT_MARKER_REQUIRED')
    _audit_guard(role, state, commands)
    if execution == 'OWNER_VERIFIED' and role == 'producer' and not _real_runtime_ready(config['real_binding']):
        return dict(envelope, owner_status='INPUT_MISSING', reason='M17_PYTDX_RUNTIME_NOT_BOUND')
    sys.path.insert(0, str(owner_root))
    from ops import materialize_manager_close_discovery as owner
    from apps.api.v35_api.manager_workbench_router import ManagerWorkbenchResearchReader
    from infrastructure.owned_io import SafeRoot
    if owner.APP_ROOT != owner_root:
        raise ValueError('M17_OWNER_ORIGIN')
    date = request['source_trade_date']
    if role == 'producer':
        if execution == 'OWNER_VERIFIED':
            # No clock override and no collector injection: invoke the original
            # default collector. Only its subprocess transport is narrowly bound.
            try:
                produced = owner.recapture_close_minutes(manager_state_root=state,
                    universe_root=Path(config['universe_root']),
                    pytdx_python=Path(binding['pytdx_python']), trade_date=date,
                    app_root=owner_root, provider_root=Path(binding['provider_root']),
                    process_runner=_real_process_runner(binding, date))
            except owner.EvidenceError as error:
                return dict(envelope, owner_status='FAILED', reason=str(error))
        else:
            simulation = request['simulation']; exact_keys(simulation, ('clocks', 'result'))
            clocks = iter([aware(t) for t in simulation['clocks']])
            if not simulation['clocks'] or simulation['clocks'][0] != request['research_cutoff']:
                raise ValueError('M17_SIMULATED_CLOCK_CONTRACT')
            result = simulation['result']
            exact_keys(result, ('status', 'rows', 'requested_code_count', 'completed_code_count', 'no_data_codes', 'cannot_confirm'))
            def collector(python, trade_date, stage_id, codes, **kwargs):
                if trade_date != date or stage_id != 'STAGE_1545_1555' or kwargs['market'] != 'HK_CONNECT':
                    raise ValueError('M17_SIMULATED_COLLECTOR_REQUEST')
                return SimpleNamespace(**result)
            try:
                produced = owner.recapture_close_minutes(manager_state_root=state,
                    universe_root=Path(config['universe_root']), pytdx_python=Path(config['python']),
                    trade_date=date, app_root=owner_root, provider_root=owner_root/'upstreams/v3_shared_data',
                    clock=lambda: next(clocks), pytdx_collector=collector)
            except owner.EvidenceError as error:
                return dict(envelope, owner_status='FAILED', reason=str(error))
        envelope.update(owner_status=produced['status'], reason=produced.get('reason'), plan_trade_date=produced.get('plan_trade_date'))
        if produced['status'] not in {'MATERIALIZED', 'ALREADY_EXISTS', 'PARTIAL'}:
            return envelope
    else:
        readback = ManagerWorkbenchResearchReader(state).read_close_recapture(date)
        envelope.update(owner_status=readback['status'], plan_trade_date=readback.get('plan_trade_date'))
        if readback['status'] not in {'READY', 'PARTIAL'}:
            return envelope
        pool, _ = owner._read_close_recapture_pool(Path(config['universe_root'])/'.runtime/data', date)
        if pool != readback['pool']:
            raise ValueError('M17_EXTERNAL_POOL_CHANGED')
        envelope.update(pool=pool, pool_run_id=pool['run_id'], cannot_confirm=readback['cannot_confirm'],
                        captured_at=readback['request']['captured_at'], available_at=readback['request']['available_at'],
                        candidate_count=readback['candidate_overlay']['count'], received_not_historical_1530=readback['received_not_historical_1530'])
    # SafeRoot reopens each original file; receipt hash is its bytes, never artifact_sha256.
    safe = SafeRoot(state)
    prefix = f'workbench_research/{date}/'
    refs = dict(artifact=prefix+'close_recapture.json', receipt=prefix+'close_recapture.receipt.json',
                snapshot=prefix+'inputs/close_recapture_pytdx.json', candidate_overlay=prefix+'close_recapture.candidates.json')
    files = {key: dict(artifact_ref=ref, sha256=_sha(safe.read_bytes(ref))) for key, ref in refs.items()}
    if role == 'producer':
        if any(produced.get(key+'_ref') != item['artifact_ref'] or produced.get(key+'_sha256') != item['sha256'] for key, item in files.items()):
            raise ValueError('M17_PRODUCER_FILES_MISMATCH')
    else:
        expected = dict(artifact=readback['receipt']['artifact_sha256'],
                        snapshot=readback['snapshot']['sha256'], candidate_overlay=readback['candidate_overlay']['sha256'])
        if any(files[key]['sha256'] != sha for key, sha in expected.items()):
            raise ValueError('M17_READER_FILES_CHANGED')
    return dict(envelope, files=files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', choices=('producer', 'reader'), help=argparse.SUPPRESS)
    parser.add_argument('--request', type=Path)
    parser.add_argument('--ledger-root', type=Path)
    args = parser.parse_args(argv)
    if args.worker:
        packet = json.loads(sys.stdin.buffer.read(1024 * 1024 + 1))
        value = _worker(args.worker, packet)
    else:
        if args.request is None or args.ledger_root is None:
            parser.error('--request and --ledger-root are required')
        request = json.loads(_read_file(args.request))
        value = run_close_recapture_daily(request, str(args.ledger_root), bind_close_recapture_owner(request['config']))
    print(canonical_bytes(value).decode())
    return 0 if args.worker or value['status'] in {'SUCCEEDED', 'REUSED_SUCCESS'} else 2


if __name__ == '__main__':
    raise SystemExit(main())

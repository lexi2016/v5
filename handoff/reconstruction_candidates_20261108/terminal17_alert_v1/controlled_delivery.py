"""New V2 bridge to the unchanged reviewed outbox; no built-in sender or binding.

Registry entries are supplied by the original owner after independent review.
Runtime requests cannot supply paths, recipients, clocks or authorization.  A
byte digest proves identity, never authority.  Tests use isolated fake callbacks.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import types
from zoneinfo import ZoneInfo

# Only code-reviewed original-owner ledger descriptors may be pinned here.
# Empty by default: runtime bindings cannot grant a new store or migration.
OWNER_LEDGER_PINS = {}

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUTBOX_SHA = '50a7fee95e2b24911ee3c205b5e402316a764e7d7d1ece2a634bb78552ac5891'
SAFEIO_SHA = 'facce7970f4919034d62e59dde8375e94d7a6a165de214f2e5178dbb5615fff5'
SAFEIO_PATH = REPO / 'V5/public_source_delivery/20261108_execution_increment/evening_delivery_bundle_v2_20261107/safeio.py'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned_module(path, expected_sha):
    raw = Path(path).read_bytes()
    if sha(raw) != expected_sha:
        raise ValueError('DEPENDENCY_CHANGED:' + Path(path).name)
    module = types.ModuleType('controlled_' + Path(path).stem)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def safeio():
    return pinned_module(SAFEIO_PATH, SAFEIO_SHA)


def text_identity(value):
    return isinstance(value, str) and bool(value.strip()) and value.upper() not in (
        'UNKNOWN', 'NONE', 'UNBOUND', 'NOT_SET')


def date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{8}', value):
        raise ValueError('DATE')
    return dt.datetime.strptime(value, '%Y%m%d').date()


def validate_binding(binding, schema):
    if not isinstance(binding, dict) or binding.get('schema') != schema:
        raise ValueError('NO_REVIEWED_V2_BINDING')
    if binding.get('domain') not in ('isolated_test', 'reviewed_project'):
        raise ValueError('UNREVIEWED_BINDING_DOMAIN')
    for name in ('owner_id', 'authorization_ref', 'task_id', 'environment_id',
                 'binding_version', 'run_id', 'source_contract_ref'):
        if not text_identity(binding.get(name)):
            raise ValueError('MISSING_CONTRACT:' + name)
    for name in ('owner_context', 'gate', 'clock'):
        if not callable(binding.get(name)):
            raise ValueError('MISSING_ORIGINAL_OWNER_CALLBACK:' + name)
    date(binding.get('run_date'))


def clock_gate(binding, slot, allow_later=False):
    now = binding['clock']()
    if not isinstance(now, dt.datetime) or now.utcoffset() is None:
        raise ValueError('AWARE_REGISTERED_CLOCK_REQUIRED')
    local = now.astimezone(ZoneInfo('Asia/Shanghai'))
    target = date(binding['run_date'])
    minimum = dt.time(int(slot[:2]), int(slot[2:]))
    boundary = dt.datetime.combine(target, minimum, ZoneInfo('Asia/Shanghai'))
    if local < boundary or (not allow_later and local.date() != target):
        raise ValueError('NODE_DATE_TIME_GATE')
    return now


def original_gate(binding):
    """Original raise-only gates return None; explicit boolean True also passes."""
    result = binding['gate']()
    if result is not None and result is not True:
        raise ValueError('ORIGINAL_GATE_FAILED')


def checked_pin(io, root, pin):
    if (not isinstance(pin, dict) or type(pin.get('bytes')) is not int
            or not 0 < pin['bytes'] <= io.MAX_BYTES
            or not re.fullmatch('[a-f0-9]{64}', str(pin.get('sha256', '')))):
        raise ValueError('INPUT_PIN_CONTRACT')
    raw = io.local_bytes(root, pin['path'])
    if len(raw) != pin['bytes'] or sha(raw) != pin['sha256']:
        raise ValueError('INPUT_CHANGED')
    return raw


def checked_root(io, path, identity):
    if (not isinstance(identity, dict) or set(identity) != {'device', 'inode'}
            or any(type(identity[k]) is not int for k in identity)):
        raise ValueError('ORIGINAL_ROOT_IDENTITY_REQUIRED')
    fd = io.directory_fd(path)
    info = os.fstat(fd)
    if identity != {'device': info.st_dev, 'inode': info.st_ino}:
        os.close(fd)
        raise ValueError('ORIGINAL_ROOT_CHANGED')
    return fd


def delivery_identity(binding):
    """Serializable contract included in the frozen package identity."""
    config = binding.get('delivery')
    if not isinstance(config, dict):
        return None
    names = ('authorized', 'channel', 'destination', 'authorization_ref', 'binding_version', 'root_identity')
    return {name: config.get(name) for name in names}


def canonical_claim_root(binding, io, template):
    """Resolve a pre-existing ledger from the original owner, never output_root.

    This callback is an authority boundary, not a request field. The original
    owner must resolve a durable, immutable task/environment ledger using its
    reviewed registry while holding its existing lock. No fallback, directory
    creation, migration, or reset is supported here.
    """
    resolve = binding.get('resolve_delivery_authority')
    if not callable(resolve):
        raise ValueError('ORIGINAL_DELIVERY_LEDGER_NOT_BOUND')
    identity = {k: binding[k] for k in ('owner_id', 'task_id', 'environment_id')}
    authority = resolve(**identity)
    if (not isinstance(authority, dict)
            or authority.get('schema') != 'OWNER_DELIVERY_LEDGER_V1'
            or not text_identity(authority.get('authority_ref'))
            or any(authority.get(k) != v for k, v in identity.items())):
        raise ValueError('ORIGINAL_DELIVERY_LEDGER_AUTHORITY_MISMATCH')
    expected = OWNER_LEDGER_PINS.get(tuple(identity[k] for k in ('owner_id', 'task_id', 'environment_id')))
    if (not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected)
            or sha(canonical(authority)) != expected):
        raise ValueError('ORIGINAL_DELIVERY_LEDGER_PIN_NOT_BOUND_OR_CHANGED')
    # Also bind the pre-existing outbox independently. This prevents a first
    # call after upgrade from using a fresh directory to escape old attempts.
    approved_output = authority.get('output_root')
    if (not isinstance(approved_output, (str, Path))
            or str(Path(approved_output).absolute()) != str(Path(template['output_root']).absolute())
            or authority.get('output_root_identity') != template['root_identity']):
        raise ValueError('ORIGINAL_OUTBOX_CHANGED_REQUIRES_RECONCILIATION')
    # Caller-supplied delivery paths/identities cannot select this store.
    path = authority.get('ledger_root')
    if not isinstance(path, (str, Path)):
        raise ValueError('ORIGINAL_DELIVERY_LEDGER_ROOT_REQUIRED')
    return checked_root(io, path, authority.get('root_identity'))


def _delivery_config(binding, node, input_sha256, code_version, body, preflight, action):
    template = binding.get('delivery')
    if not isinstance(template, dict):
        raise ValueError('NO_REVIEWED_DELIVERY_CONTRACT')
    if template.get('authorized') is not True:
        raise ValueError('DELIVERY_NOT_EXPLICITLY_AUTHORIZED')
    for name in ('channel', 'destination', 'authorization_ref', 'binding_version'):
        if not text_identity(template.get(name)):
            raise ValueError('MISSING_DELIVERY_CONTRACT:' + name)
    if template['channel'] != 'chatgpt':
        raise ValueError('UNREVIEWED_CHANNEL')
    if binding['domain'] == 'isolated_test' and template['destination'] != 'SYNTHETIC_NO_RECIPIENT':
        raise ValueError('ISOLATED_TEST_RECIPIENT_REQUIRED')
    if binding['domain'] == 'reviewed_project' and template['destination'] == 'SYNTHETIC_NO_RECIPIENT':
        raise ValueError('REAL_RECIPIENT_CONTRACT_REQUIRED')
    for name in ('sender', 'reconciler'):
        if not callable(template.get(name)):
            raise ValueError('MISSING_DELIVERY_CALLBACK:' + name)
    if not re.fullmatch('[a-f0-9]{64}', input_sha256):
        raise ValueError('DELIVERY_INPUT_IDENTITY')
    io = safeio()
    config = {name: binding[name] for name in ('task_id', 'environment_id', 'run_id')}
    config.update({name: template[name] for name in
                   ('channel', 'destination', 'authorization_ref', 'binding_version',
                    'output_root', 'sender', 'reconciler')})
    config.update(authorized=template['authorized'], owner_context=binding['owner_context'], node=node,
                  input_sha256=input_sha256, code_version=code_version, data_date=binding['run_date'])
    # Changing recipient/version/root cannot silently create a second outbox item
    # for the same logical input. The original owner context covers this claim.
    logical = {name: config[name] for name in ('task_id', 'node', 'data_date', 'input_sha256')}
    claim_name = 'delivery-claim-' + sha(canonical(logical)) + '.json'
    claim = {name: config[name] for name in ('task_id', 'node', 'environment_id',
             'binding_version', 'authorization_ref', 'channel', 'destination',
             'input_sha256', 'code_version', 'data_date')}
    claim.update(payload_sha256=sha(body), owner_id=binding['owner_id'],
                 root_identity=template['root_identity'])
    claim_raw = canonical(claim)
    attempt_name = claim_name.replace('delivery-claim-', 'delivery-attempt-')

    def guarded_sender(**message):
        # Local state can be rolled back with the outbox. No reviewed external
        # consume-once authority exists yet. No binding/callback can bypass this.
        raise ValueError('ANTI_ROLLBACK_AUTHORITY_UNBOUND_NO_SEND')

    config['sender'] = guarded_sender

    def gate():
        original_gate(binding)
        clock_gate(binding, node, allow_later=action == 'reconcile')
        preflight()
        output = checked_root(io, template['output_root'], template['root_identity'])
        os.close(output)
        root = canonical_claim_root(binding, io, template)
        try:
            try:
                previous = io.read_at(root, claim_name)
            except FileNotFoundError:
                io.write_at(root, claim_name, claim_raw)
                os.fsync(root)
                previous = io.read_at(root, claim_name)
            if previous != claim_raw:
                raise ValueError('DELIVERY_BINDING_CHANGED_REQUIRES_REVIEW')
            try:
                attempt = io.read_at(root, attempt_name)
            except FileNotFoundError:
                attempt = None
            if attempt is not None:
                if attempt != claim_raw:
                    raise ValueError('DELIVERY_ATTEMPT_CHANGED_REQUIRES_RECONCILIATION')
                # A lost/rolled-back outbox is not a new delivery entitlement.
                # Read only: never silently recreate state during recovery.
                db_path = Path(template['output_root']) / 'outbox.sqlite3'
                if not db_path.is_file() or db_path.is_symlink():
                    raise ValueError('OUTBOX_LOST_REQUIRES_RECONCILIATION')
                db = sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True)
                try:
                    rows = db.execute('SELECT state FROM items WHERE identity=?',
                        (canonical({k: v for k, v in claim.items()
                                    if k not in ('owner_id', 'root_identity')}),)).fetchall()
                    if len(rows) != 1 or rows[0][0] not in (
                            'ATTEMPT_UNKNOWN', 'ACCEPTED', 'DELIVERED_VERIFIED'):
                        raise ValueError('OUTBOX_ROLLBACK_REQUIRES_RECONCILIATION')
                finally:
                    db.close()
        finally:
            os.close(root)
        return True

    config['gate'] = gate
    return config


def dispatch(binding, *, node, input_sha256, code_version, payload, preflight, action):
    """Use the original outbox. No reset or resend path for uncertain attempts."""
    if action not in ('prepare', 'deliver', 'reconcile'):
        raise ValueError('DELIVERY_ACTION')
    body = canonical(payload)
    config = _delivery_config(binding, node, input_sha256, code_version, body, preflight, action)
    module = pinned_module(HERE / 'outbox.py', OUTBOX_SHA)
    module.REGISTRY = {'controlled': config}
    item = module.prepare('controlled', body.decode())
    attempted = False
    accepted_in_this_call = False
    result = item
    if action == 'deliver' and item['state'] == 'PREPARED':
        # PREPARED/empty local state cannot prove no historical send occurred.
        # Preserve read-only reconciliation paths, quarantine all new attempts.
        raise ValueError('ANTI_ROLLBACK_AUTHORITY_UNBOUND_NO_SEND')
    # A repeat after an uncertain send only reconciles; absence never clears it.
    if action != 'prepare' and result['state'] != 'PREPARED':
        try:
            result = module.reconcile('controlled', item['key'])
        except Exception as error:
            return dict(status='UNKNOWN_RECONCILIATION_REQUIRED', outbox_key=item['key'],
                        delivery_state=result['state'], reason='RECONCILE_UNAVAILABLE:' + type(error).__name__,
                        attempted_in_this_call=attempted,
                        sent_in_this_call=(None if attempted and result['state'] == 'ATTEMPT_UNKNOWN'
                                           else accepted_in_this_call),
                        delivery_verified=False, reused=item['reused'], evidence_domain=binding['domain'],
                        business_accepted=False, natural_verified=False)
    state = result['state']
    verified = result.get('delivery_verified') is True
    return dict(status='DELIVERY_VERIFIED' if verified else 'DELIVERY_PENDING',
                outbox_key=item['key'], delivery_state=state, reused=item['reused'],
                attempted_in_this_call=attempted,
                sent_in_this_call=(None if attempted and state == 'ATTEMPT_UNKNOWN'
                                   else accepted_in_this_call),
                delivery_verified=verified, evidence_domain=binding['domain'],
                business_accepted=False, natural_verified=False)


def blocked(reason, **values):
    # A blocked current invocation provides no evidence that an older attempt
    # never sent. Preserve the distinction from sent_in_this_call=False.
    return dict(status='BLOCKED', reason=reason, delivery_state='UNKNOWN',
                sent_in_this_call=False, delivery_verified=False,
                business_accepted=False, natural_verified=False, **values)

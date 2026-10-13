"""Read one pinned original M16 commit. Never create its store or service."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import parse_qsl, urlsplit

BASE = Path(__file__).resolve().parents[2]
if __package__ in (None, ''):
    sys.path.insert(0, str(BASE / 'src'))
OWNER_MANIFEST = BASE / 'contracts/m16_owner_source_manifest.json'
OWNER_MANIFEST_SHA256 = '4ee00c59820c73564512650bbb471e70155058110eef1d42d774760bd1c03994'
MAX_BYTES = 8 * 1024 * 1024
OUTPUT_BYTES = 4 * 1024 * 1024
FLAGS = dict(read_only=True, can_execute=False, research_only=True,
             natural_verified=False, production_allowed=False,
             buy_gate_updated=False, orders_sent=False)
TERMINAL = {'READY', 'PARTIAL_WITH_ROWS', 'CANNOT_CONFIRM', 'FAILED'}


def unavailable(reason, *, status='WAITING', **extra):
    return dict(schema_version='v5.m16_saved_public_research.v1',
                module_id='M16_PUBLIC_RESEARCH', status=status,
                mode='READ_ONLY_SAVED_RESULT', reason_codes=[reason], **FLAGS, **extra)


def raw(path, limit=None):
    """Read bounded stable regular-file bytes through no-follow descriptors."""
    limit = MAX_BYTES if limit is None else limit
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('M16_PATH')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        child = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(child, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
                raise ValueError('M16_READ_LIMIT')
            content = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            keys = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
            if len(content) > limit:
                raise ValueError('M16_READ_LIMIT')
            if len(content) != before.st_size or any(getattr(before, k) != getattr(after, k) for k in keys):
                raise ValueError('M16_FILE_CHANGED')
            return content
    finally:
        os.close(fd)


def owner_components():
    from v5_shadow.m16_readonly import verify_runtime
    from v5_shadow.manager_loader import OwnerClosure, load_owner
    verify_runtime()
    return load_owner(OwnerClosure(BASE / 'source_owners/m16/canonical',
                                  OWNER_MANIFEST, OWNER_MANIFEST_SHA256))['components']


class PinnedCommitBytes:
    """Supply the unchanged original validator the exact prechecked buffer."""
    def __init__(self, name, content):
        self.name, self.content = name, content

    def read_bytes(self, name, **kwargs):
        if name != self.name:
            raise ValueError('M16_PINNED_PATH_CHANGED')
        return self.content


def public_tree(value, depth=0):
    if depth > 32:
        raise ValueError('M16_PROJECTION_DEPTH')
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError('M16_PROJECTION_KEY')
            normal = re.sub('[^a-z0-9]', '', key.lower())
            if normal in {'productionallowed', 'buygateupdated', 'orderssent', 'naturalverified'} and item is not False:
                raise ValueError('M16_UNVERIFIED_AUTHORITY_CLAIM')
            if (any(token in normal for token in ('path', 'root', 'credential', 'token', 'secret', 'password', 'apikey', 'accesskey', 'authorization', 'cookie', 'sessionid', 'sessionkey', 'privatekey', 'clientkey'))
                    or key in {'owner_pid', 'owner_instance', '__proto__', 'constructor', 'prototype'}):
                continue
            result[key] = public_tree(item, depth + 1)
        return result
    if isinstance(value, list):
        return [public_tree(item, depth + 1) for item in value]
    if isinstance(value, str):
        if value.lower().startswith(('file:', 'data:', 'javascript:')):
            return '[NON_PUBLIC_REFERENCE_REDACTED]'
        # Keep public document URLs, never forward credential-bearing URLs.
        for match in re.finditer(r'https?://[^\s<>"\']+', value, flags=re.IGNORECASE):
            try:
                url = urlsplit(match.group())
                names = [re.sub('[^a-z0-9]', '', key.lower()) for key, _ in parse_qsl(url.query)]
                if url.username is not None or url.password is not None or any(
                        any(token in key for token in ('token', 'secret', 'credential', 'password', 'signature', 'apikey', 'accesskey', 'authorization'))
                        or key in {'key', 'sig', 'auth'} for key in names):
                    return '[CREDENTIAL_REFERENCE_REDACTED]'
            except ValueError:
                return '[INVALID_REFERENCE_REDACTED]'
        if value.startswith('/') or re.search(r'(?:^|[\s"\'(])/(?:Users|home|workspace|private|tmp|var|opt|root|mnt|etc)/|[A-Za-z]:\\', value):
            return '[LOCAL_PATH_REDACTED]'
    return value


def _members(commit, binding):
    product = commit['product']
    job = commit['jobs'].get(binding['job_id'])
    receipt = commit['receipts'].get(binding['job_id'])
    if not isinstance(job, dict) or not isinstance(receipt, dict):
        raise ValueError('M16_COMMITTED_JOB_MISSING')
    receipt_schema = 'catalyst_receipt' if job.get('mode') == 'EVENT_REFRESH' else 'receipt'
    for obj, schema in ((product, 'product'), (job, 'job'), (receipt, receipt_schema)):
        if obj.get('schema_version') != f'v4.manager_research.{schema}.v1':
            raise ValueError('M16_MEMBER_SCHEMA')
        if obj.get('target_trade_date') != binding['trade_date'] or obj.get('input_identity') != binding['input_identity']:
            raise ValueError('M16_MEMBER_IDENTITY')
    if job.get('attempt') != binding['attempt'] or job.get('generation') != binding['generation']:
        raise ValueError('M16_JOB_ATTEMPT')
    # Original receipts have no attempt/generation. Their committed job anchors
    # those fields; an explicitly contradictory receipt remains invalid.
    for key in ('attempt', 'generation'):
        if key in receipt and receipt[key] != binding[key]:
            raise ValueError('M16_RECEIPT_ATTEMPT')
    if product.get('kind') != 'MANAGER_RESEARCH_PRODUCT' or product.get('status') not in TERMINAL:
        raise ValueError('M16_PRODUCT_KIND_OR_STATUS')
    if job.get('status') not in TERMINAL or receipt.get('status') != job['status']:
        raise ValueError('M16_TERMINAL_STATUS')
    if job.get('mode') != 'EVENT_REFRESH' and product['status'] != job['status']:
        raise ValueError('M16_PRODUCT_JOB_STATUS')
    for key in ('stage_id', 'market', 'cutoff_at', 'input_source_sha256', 'input_row_count'):
        if product.get(key) != job.get(key):
            raise ValueError('M16_PRODUCT_JOB_IDENTITY')
    if product.get('stage_id') != 'STAGE_0935_0940' or product.get('market') != 'HK_CONNECT':
        raise ValueError('M16_PRODUCT_SCOPE')
    rows = product.get('rows')
    if not isinstance(rows, list) or type(product.get('input_row_count')) is not int or len(rows) != product['input_row_count']:
        raise ValueError('M16_ROW_COUNT')
    if len(rows) > 50 or any(not isinstance(row, dict) for row in rows):
        raise ValueError('M16_ROW_BOUNDARY')
    return product, job, receipt


def project(binding):
    from v5_shadow.m16_readonly import validate_reference
    from v5_shadow.digests import sha256_json
    validate_reference(binding)
    root = Path(binding['private_root'])
    marker = json.loads(raw(root / '.m16-private-root.json', 256))
    if marker != {'module': 'M16', 'private': True, 'schema': 'v5.private_root.v1'}:
        raise ValueError('M16_PRIVATE_ROOT_MARKER')
    relative = f".commits/{binding['trade_date']}/{binding['input_identity']}.json"
    path = root / relative
    content = raw(path)
    if hashlib.sha256(content).hexdigest() != binding['commit_file_sha256']:
        raise ValueError('M16_COMMIT_FILE_PIN')
    original = json.loads(content)
    if original.get('sha256') != binding['commit_sha256']:
        raise ValueError('M16_COMMIT_CANONICAL_PIN')
    cls = owner_components().store_class
    # Same established no-constructor pattern as manager_plan.plan_store.
    # No mkdir, locks, worker pools, provider, or lifecycle calls are needed.
    store = cls.__new__(cls)
    store.root = root
    store._io = PinnedCommitBytes(relative, content)
    commit = store._read_commit(binding['trade_date'], binding['input_identity'])
    if commit != original:
        raise ValueError('M16_PINNED_COMMIT_CHANGED')
    if hashlib.sha256(raw(path)).hexdigest() != binding['commit_file_sha256']:
        raise ValueError('M16_COMMIT_CHANGED')
    product, job, receipt = _members(commit, binding)
    reference = {key: binding[key] for key in ('trade_date', 'input_identity', 'job_id', 'generation', 'attempt', 'commit_sha256', 'commit_file_sha256')}
    reference.update(product_sha256=sha256_json(product), job_sha256=sha256_json(job), receipt_sha256=sha256_json(receipt))
    return dict(schema_version='v5.m16_saved_public_research.v1', module_id='M16_PUBLIC_RESEARCH',
                status='SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED', mode='READ_ONLY_SAVED_RESULT',
                reference=reference, data_kind=binding['data_kind'], evidence_status='VERIFIED_PERSISTENCE_ONLY',
                business_status=product['status'], product=public_tree(product), job=public_tree(job),
                receipt=public_tree(receipt), reason_codes=['NATURAL_RESEARCH_NOT_VERIFIED', 'SOURCE_PDF_BYTES_NOT_VERIFIED'], **FLAGS)


def readonly_audit(event, args):
    if event == 'open':
        mode, flags = args[1:3]
        if ((isinstance(mode, str) and any(c in mode for c in 'wax+'))
                or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))):
            raise ValueError('M16_READ_ONLY')
    if event in {'os.remove', 'os.rename', 'os.mkdir', 'os.rmdir', 'subprocess.Popen', 'socket.connect', 'socket.bind'}:
        raise ValueError('M16_READ_ONLY')


def main():
    request = sys.stdin.buffer.read(65537)
    if len(request) > 65536:
        raise ValueError('M16_REQUEST_LIMIT')
    binding = json.loads(request)
    sys.addaudithook(readonly_audit)
    try:
        result = project(binding)
    except FileNotFoundError:
        result = unavailable('M16_COMMITTED_RESULT_MISSING')
    except Exception:
        result = unavailable('M16_COMMITTED_RESULT_REJECTED', status='CANNOT_CONFIRM')
    encoded = json.dumps(result, ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(encoded) > OUTPUT_BYTES:
        encoded = json.dumps(unavailable('M16_RESULT_LIMIT', status='CANNOT_CONFIRM')).encode()
    sys.stdout.buffer.write(encoded)


if __name__ == '__main__':
    main()

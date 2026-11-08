"""Isolated subset coordinator candidate. No production argv or scheduler.
One trusted test root per owner, not per run/slot/version/output. Registry pins
and independent reconciliation are caller trust-boundary inputs, not generated
from an executor's return code. Direct calls remain isolated test seams. The
separate entrypoint owns the new reviewed original-owner callback contract;
its real-run registry stays empty. This module grants no production approval.
"""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
from subset_plan import canonical, digest, need, pinned, plan

TAG = {'schema':'ISOLATED_SUBSET_COORDINATOR_V1','production_allowed':False}


def initialize(path):
    path = Path(path).absolute()
    need(path.parent == path.parent.resolve(), 'SYMLINK_ROOT_PARENT')
    path.mkdir(mode=0o700, exist_ok=False)
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        write_new(fd, 'ISOLATED_ONLY.json', TAG)
        lockfd = os.open('OWNER.lock',os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW,0o600,dir_fd=fd)
        try:
            inode = os.fstat(lockfd)
            os.fsync(lockfd)
            write_new(fd,'LOCK_IDENTITY.json',{'inode':[inode.st_dev,inode.st_ino]})
        finally:
            os.close(lockfd)
    finally:
        os.close(fd)
    return path


def read(fd, name):
    f = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
    try:
        s = os.fstat(f)
        need(stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and s.st_size <= 16*1024**2, 'REGULAR_BOUNDED_SINGLE_LINK')
        raw = b''
        while True:
            chunk = os.read(f, 65536)
            if not chunk: break
            raw += chunk
            need(len(raw) <= 16*1024**2, 'READ_LIMIT')
        t = os.fstat(f)
        need((s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns) ==
             (t.st_ino,t.st_size,t.st_mtime_ns,t.st_ctime_ns), 'FILE_CHANGED')
        return json.loads(raw)
    finally:
        os.close(f)


def write_new(fd, name, value):
    raw = canonical(value)
    f = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        view = memoryview(raw)
        while view:
            n = os.write(f, view)
            need(n > 0, 'SHORT_WRITE')
            view = view[n:]
        os.fsync(f)
    finally:
        os.close(f)
    os.fsync(fd)


class Coordinator:
    def __init__(self, root):
        self.root = Path(root).absolute()
        need(self.root == self.root.resolve(), 'SYMLINK_ROOT')
        self.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            need(read(self.fd,'ISOLATED_ONLY.json') == TAG, 'ISOLATED_ROOT_REQUIRED')
            self.inode = (os.fstat(self.fd).st_dev,os.fstat(self.fd).st_ino)
        except BaseException:
            os.close(self.fd)
            raise

    def close(self):
        os.close(self.fd)

    def anchored(self):
        s = os.stat(self.root, follow_symlinks=False)
        need(stat.S_ISDIR(s.st_mode) and (s.st_dev,s.st_ino) == self.inode, 'ROOT_REPLACED')

    def _lock_anchored(self, fd):
        s = os.fstat(fd)
        current = os.stat('OWNER.lock', dir_fd=self.fd, follow_symlinks=False)
        registered = read(self.fd,'LOCK_IDENTITY.json')
        need(stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and
             [s.st_dev,s.st_ino] == registered['inode'] == [current.st_dev,current.st_ino], 'LOCK_REPLACED')

    @contextlib.contextmanager
    def lock(self):
        self.anchored()
        # Initialization alone creates the fixed lock; missing lock never recreated.
        f = os.open('OWNER.lock', os.O_RDWR | os.O_NOFOLLOW, dir_fd=self.fd)
        try:
            self._lock_anchored(f)
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock_anchored(f)
            self.anchored()
            yield f
            self._lock_anchored(f)
            self.anchored()
        finally:
            os.close(f)

    def _day_anchored(self, fd, name):
        registered = read(self.fd, name + '.identity.json')
        held = os.fstat(fd)
        current = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
        need(stat.S_ISDIR(current.st_mode) and
             [held.st_dev,held.st_ino] == registered['inode'] == [current.st_dev,current.st_ino],
             'DAY_REPLACED_UNKNOWN')

    def _open_day(self, binding):
        # Exclude run/version/slot: these cannot create a new same-date budget.
        name = 'day-' + binding['data_date']
        registry = name + '.identity.json'
        names = set(os.listdir(self.fd))
        if registry not in names:
            # Existing unregistered directory may be an interrupted initialization.
            need(name not in names, 'UNREGISTERED_DAY_UNKNOWN')
            os.mkdir(name, mode=0o700, dir_fd=self.fd)
            os.fsync(self.fd)
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
            try:
                held = os.fstat(fd)
                write_new(self.fd,registry,{'inode':[held.st_dev,held.st_ino]})
                self._day_anchored(fd,name)
            except BaseException:
                os.close(fd)
                raise
        else:
            # A missing old day directory must never create a fresh retry budget.
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
            try: self._day_anchored(fd,name)
            except BaseException:
                os.close(fd)
                raise
        return fd, name

    def execute(self, binding, review_raw, review_sha, outputs, node, now, fake_executor):
        """Low-level candidate seam; never accepts an argv or command.
        The legacy argument name fake_executor remains API compatible. A real
        owner hook may only be bound by the separate reviewed entry interface.
        New independently pinned review must include all locally claimed attempts.
        Partial/unknown results never synthesize safe-retry approval.
        """
        # Validate full evidence before any claim; repeat with held owner lock.
        candidate = plan(binding,review_raw,review_sha,outputs,node,now)
        binding = candidate['binding']
        review = pinned(review_raw,review_sha)
        with self.lock() as lockfd:
            candidate = plan(binding,review_raw,review_sha,outputs,node,now)
            fd, day_name = self._open_day(binding)
            try:
                names = set(os.listdir(fd))
                if 'BASELINE.json' not in names:
                    need(not names, 'INCOMPLETE_BASELINE_UNKNOWN')
                    write_new(fd,'BASELINE.json',{'binding':binding,'attempt_ids':review['attempt_ids'],
                              'initial_review_sha256':review_sha,'success':candidate['reuse_success']})
                baseline = read(fd,'BASELINE.json')
                need(baseline['binding'] == binding, 'SAME_DATE_IDENTITY_CONFLICT')
                names = set(os.listdir(fd))
                allowed = {'BASELINE.json'}
                ids = list(baseline['attempt_ids'])
                success = {r['symbol']:r['output_sha256'] for r in baseline['success']}
                for ordinal in range(len(ids)+1,4):
                    claimname = f'CLAIM-{ordinal}.json'
                    terminalname = f'RETURNED-{ordinal}.json'
                    allowed |= {claimname,terminalname}
                    if claimname not in names:
                        need(terminalname not in names,'TERMINAL_WITHOUT_CLAIM')
                        continue
                    claim = read(fd,claimname)
                    need(claim['binding'] == binding and claim['ordinal'] == len(ids)+1, 'CLAIM_CHAIN_INVALID')
                    ids.append(claim['attempt_id'])
                    if terminalname in names:
                        terminal = read(fd,terminalname)
                        need(terminal['attempt_id'] == claim['attempt_id'], 'TERMINAL_ATTEMPT')
                        for row in terminal['success']:
                            old = success.get(row['symbol'])
                            need(old is None or old == row['output_sha256'], 'SUCCESS_CONFLICT')
                            success[row['symbol']] = row['output_sha256']
                need(names <= allowed, 'UNRECOGNIZED_STATE_UNKNOWN')
                # Missing/malformed partial claim/terminal reads fail closed.
                need(review['attempt_ids'] == ids, 'UNKNOWN_CLAIM_REQUIRES_INDEPENDENT_RECONCILIATION')
                reviewed_success = {r['symbol']:r['output_sha256'] for r in candidate['reuse_success']}
                need(all(reviewed_success.get(s) == sha for s,sha in success.items()), 'SUCCESS_CANNOT_BE_RETRIED_OR_REPLACED')
                if not candidate['retry_symbols']:
                    return {'status':'NO_RETRY_NEEDED','production_allowed':False,'plan':candidate}
                need(len(ids) < 3, 'SHARED_ATTEMPT_LIMIT')
                ordinal = len(ids)+1
                attempt_id = candidate['intent_id']
                claim = {'binding':binding,'ordinal':ordinal,'attempt_id':attempt_id,
                         'retry_symbols':candidate['retry_symbols'],'node':node,'review_sha256':review_sha}
                self.anchored()
                self._day_anchored(fd,day_name)
                self._lock_anchored(lockfd)
                # Durable immutable claim exists before any executor call.
                write_new(fd,f'CLAIM-{ordinal}.json',claim)
                # Deliberately no exception cleanup: interruption remains UNKNOWN.
                result = fake_executor(tuple(candidate['retry_symbols']))
                need(isinstance(result,dict) and set(result) == set(candidate['retry_symbols']), 'EXECUTOR_SCOPE')
                succeeded=[]
                for symbol,value in result.items():
                    if type(value) is bytes:
                        succeeded.append({'symbol':symbol,'output_sha256':hashlib.sha256(value).hexdigest()})
                    else:
                        need(value is None, 'EXECUTOR_RESULT_UNKNOWN')
                terminal = {'attempt_id':attempt_id,'success':succeeded,
                            'status':'RETURNED_AWAIT_INDEPENDENT_RECONCILIATION','production_allowed':False}
                self.anchored()
                self._day_anchored(fd,day_name)
                self._lock_anchored(lockfd)
                write_new(fd,f'RETURNED-{ordinal}.json',terminal)
                return terminal
            finally:
                os.close(fd)

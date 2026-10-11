"""Assemble the fixed M09 source payload and verify forward/reverse patches.

All mutations are confined to a newly created delivery root and evidence
workspace. The source worktree, its index, and its object store are read-only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tarfile

ROOT = Path('/workspace/scratch/a5458cb06b78/m09_work')
SOURCE = ROOT / 'after'
DELIVERY = ROOT / 'delivery'
BASELINE = 'e45aee9e185dda6f9d4b5032e6d60231cce27809'
FIXED_F = 'f7cb731c384ee6890a87d16c19a5b5a621779477'
EXPECTED_FINAL = {
    'V5/src/v5_shadow/a_close_daily.py': '23b4200ffb29e83041b761927c6f285ff84d6b92a3cf8b2fc3e527a9d8ae1d9c',
    'V5/tests/test_a_close_daily.py': 'c8d83504465efba96543db2363e79b74903e3af76bb99ef34f786bd807eb045a',
}
EXCLUDED = {'.git', '__pycache__'}
RUN_ID = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
WORK = ROOT / 'evidence' / ('delivery_assembly_' + RUN_ID)
LOGS = WORK / 'logs'
COMMANDS = []


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_id(raw, mode):
    return {'bytes': len(raw), 'sha256': digest(raw),
            'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest(),
            'git_mode': mode}


def path_allowed(relative):
    path = PurePosixPath(relative)
    if (path.is_absolute() or any(part in ('', '.', '..') for part in relative.split('/'))
            or '\\' in relative or any(part in EXCLUDED for part in path.parts)):
        raise ValueError('PAYLOAD_PATH_INVALID:' + relative)
    return path


def snapshot(root, *, keep_bytes=False):
    rows, content = {}, {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        if any(part in EXCLUDED for part in PurePosixPath(relative).parts):
            continue
        if path.is_symlink():
            raise ValueError('PAYLOAD_SYMLINK:' + relative)
        if path.is_dir():
            continue
        path_allowed(relative)
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('PAYLOAD_NONREGULAR:' + relative)
        raw = path.read_bytes()
        after = path.stat()
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError('SOURCE_CHANGED_DURING_FILE_READ:' + relative)
        mode = '100755' if after.st_mode & 0o111 else '100644'
        rows[relative] = file_id(raw, mode)
        if keep_bytes:
            content[relative] = raw
    return rows, content


def tree_id(rows):
    return digest(canonical(rows))


def manifest(rows):
    return {'file_count': len(rows), 'raw_tree_sha256': tree_id(rows), 'files': rows,
            'tree_digest_definition': 'SHA256 of UTF-8 ensure_ascii=False sort_keys=True compact JSON path-to-{bytes,sha256,git_blob_sha1,git_mode}; no trailing LF'}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode() + b'\n')


def run(name, command, *, cwd, env_extra=None):
    environment = dict(os.environ)
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        environment.pop(key, None)
    environment.update(env_extra or {})
    started = datetime.now(timezone.utc)
    result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True)
    ended = datetime.now(timezone.utc)
    logs = {}
    for stream in ('stdout', 'stderr'):
        raw = getattr(result, stream)
        path = LOGS / (name + '.' + stream + '.log')
        path.write_bytes(raw)
        logs[stream] = {'filename': path.name, 'bytes': len(raw), 'sha256': digest(raw)}
    meta = {'command_name': name, 'argv': command, 'cwd': str(cwd), 'environment_overrides': env_extra or {},
            'started_at_utc': started.isoformat(), 'finished_at_utc': ended.isoformat(),
            'started_at_shanghai': started.astimezone(ZoneInfo('Asia/Shanghai')).isoformat(),
            'finished_at_shanghai': ended.astimezone(ZoneInfo('Asia/Shanghai')).isoformat(),
            'exit_code': result.returncode, 'logs': logs}
    save(LOGS / (name + '.metadata.json'), meta)
    COMMANDS.append(meta)
    if result.returncode:
        raise RuntimeError(name + ' failed with exit ' + str(result.returncode) + ': ' + result.stderr.decode(errors='replace'))
    return result.stdout


def parse_tree(raw):
    result = {}
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        header, name = entry.split(b'\t', 1)
        mode, kind, blob = header.decode().split()
        relative = name.decode('utf-8')
        path_allowed(relative)
        if kind != 'blob' or mode not in ('100644', '100755'):
            raise ValueError('UNSUPPORTED_GIT_TREE_ENTRY:' + relative)
        result[relative] = {'git_mode': mode, 'git_blob_sha1': blob}
    return result


def write_payload(root, rows, content):
    root.mkdir()
    for relative, item in rows.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content[relative])
        path.chmod(0o755 if item['git_mode'] == '100755' else 0o644)


def reason(relative, action, donor_entries):
    if action == 'UNCHANGED':
        return 'Preserve the exact original F source-slice file; no M09 mutation to existing shared or baseline behavior.'
    if relative in donor_entries:
        entry = donor_entries[relative]
        return 'Add a byte-exact M09-private frozen dependency from ' + entry['source_path'] + '; preserve original implementation and safety semantics.'
    roles = {
        'V5/contracts/m09_a_close_daily_source_manifest.json': 'Pin the complete M09 donor import closure, byte identities, dynamic reads, external dependencies, and explicit runtime adaptation.',
        'V5/docs/M09_A_CLOSE_HANDOFF.md': 'Document the module-local daily interfaces, input/receipt/generation contracts, execution classifications, and outstanding shared integration.',
        'V5/src/v5_shadow/a_close_daily.py': 'Add exact-date admitted-input execution, immutable original products, independent readback, commit witnesses, separate attempts, verified reads and explicit rollback within a private M09 root.',
        'V5/src/v5_shadow/a_close_daily_api.py': 'Project committed M09 A reviews read-only with linked identities, original fields, independent attempt/recovery metadata, and an A-only envelope merge preserving HK.',
        'V5/src/v5_shadow/a_close_daily_sources.py': 'Load the byte-verified frozen donor closure in a private namespace and bridge admitted panel bytes without altering original algorithm code.',
        'V5/src/v5_shadow/a_close_daily_worker.py': 'Run the original producer/store in an isolated worker bound to admitted input and immutable source identities.',
        'V5/tests/test_a_close_daily.py': 'Exercise daily admission, immutable publication, timing/identity, attempts, failure recovery, readback/rollback and conditional real-engine Parquet engineering cases.',
        'V5/tests/test_a_close_daily_api.py': 'Exercise exact-date read projection, cross-layer hashes/safety, missing/invalid states, separate attempts/recovery and preservation of HK/unrelated envelope data.',
        'V5/tests/test_a_close_daily_sources.py': 'Exercise original-source identity, private imports, dependency closure, admitted-frame bridge and original producer/store parity.',
    }
    if relative not in roles:
        raise ValueError('CHANGE_REASON_NOT_DEFINED:' + relative)
    return roles[relative]


def main():
    WORK.mkdir()
    LOGS.mkdir()
    if DELIVERY.exists():
        raise ValueError('DELIVERY_ROOT_ALREADY_EXISTS; REFUSE_TO_MERGE')
    created_delivery = False
    try:
        candidate_start, candidate_bytes = snapshot(SOURCE, keep_bytes=True)
        if len(candidate_start) != 77:
            raise ValueError('EXPECTED_77_CANDIDATE_FILES')
        for relative, expected in EXPECTED_FINAL.items():
            if candidate_start[relative]['sha256'] != expected:
                raise ValueError('PARENT_FINAL_CANDIDATE_PIN_MISMATCH:' + relative)
        source_head = run('01_source_head', ['git', 'rev-parse', 'HEAD'], cwd=SOURCE).decode().strip()
        base_tree = parse_tree(run('02_baseline_tree', ['git', 'ls-tree', '-r', '-z', '--full-tree', BASELINE], cwd=SOURCE))
        if len(base_tree) != 52:
            raise ValueError('EXPECTED_52_BASELINE_FILES')
        archive = run('03_baseline_archive', ['git', 'archive', '--format=tar', BASELINE], cwd=SOURCE)
        baseline_bytes = {}
        with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as tar:
            for entry in tar:
                if entry.isdir():
                    continue
                if not entry.isfile() or entry.name not in base_tree:
                    raise ValueError('BASELINE_ARCHIVE_ENTRY_INVALID:' + entry.name)
                path_allowed(entry.name)
                raw = tar.extractfile(entry).read()
                if hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != base_tree[entry.name]['git_blob_sha1']:
                    raise ValueError('BASELINE_ARCHIVE_BLOB_MISMATCH:' + entry.name)
                baseline_bytes[entry.name] = raw
        if set(baseline_bytes) != set(base_tree):
            raise ValueError('BASELINE_ARCHIVE_MEMBERS_MISMATCH')
        baseline_rows = {p: file_id(raw, base_tree[p]['git_mode']) for p, raw in sorted(baseline_bytes.items())}
        if any(candidate_start.get(p) != item for p, item in baseline_rows.items()):
            raise ValueError('EXPECTED_ALL_52_ORIGINAL_FILES_UNCHANGED')

        proof_path = ROOT / 'evidence/BASELINE_PATH_VERIFICATION.json'
        proof_raw = proof_path.read_bytes()
        proof = json.loads(proof_raw)
        if proof['commit'] != FIXED_F or proof['truncated'] is not False or proof['all_tree_entries'] != 2746:
            raise ValueError('FULL_F_PROOF_IDENTITY_INVALID')
        absent = {x['path'] for x in proof['new_paths'] if x['present_in_fixed_F'] is False}
        new_paths = set(candidate_start) - set(baseline_rows)
        if len(new_paths) != 25 or new_paths != absent:
            raise ValueError('FULL_F_ABSENCE_PROOF_DOES_NOT_MATCH_NEW_PATHS')
        old_proof = {x['path']: x for x in proof['unchanged_sources']}
        if set(old_proof) != set(baseline_rows) or any(
                old_proof[p]['remote_git_blob_sha'] != item['git_blob_sha1'] or old_proof[p]['match'] is not True
                for p, item in baseline_rows.items()):
            raise ValueError('FULL_F_BASELINE_BLOB_PROOF_MISMATCH')

        DELIVERY.mkdir()
        created_delivery = True
        write_payload(DELIVERY / 'before', baseline_rows, baseline_bytes)
        write_payload(DELIVERY / 'after', candidate_start, candidate_bytes)
        if snapshot(SOURCE)[0] != candidate_start:
            raise ValueError('SOURCE_CHANGED_DURING_SNAPSHOT; RETRY_REQUIRED')
        if snapshot(DELIVERY / 'before')[0] != baseline_rows or snapshot(DELIVERY / 'after')[0] != candidate_start:
            raise ValueError('DELIVERY_COPY_MISMATCH')

        # Only the isolated index/object directory is writable. Baseline Git
        # objects are read via alternates; no source index/object writes occur.
        object_dir = WORK / 'objects'
        object_dir.mkdir()
        isolated_env = {'GIT_INDEX_FILE': str(WORK / 'snapshot.index'), 'GIT_OBJECT_DIRECTORY': str(object_dir),
                        'GIT_ALTERNATE_OBJECT_DIRECTORIES': str(SOURCE / '.git/objects')}
        git = ['git', '--git-dir=' + str(SOURCE / '.git'), '--work-tree=' + str(DELIVERY / 'after'),
               '-c', 'core.autocrlf=false', '-c', 'core.filemode=true']
        run('04_snapshot_read_tree', git + ['read-tree', BASELINE], cwd=DELIVERY / 'after', env_extra=isolated_env)
        run('05_snapshot_stage', git + ['add', '--all', '--force', '--', '.'], cwd=DELIVERY / 'after', env_extra=isolated_env)
        diff_options = ['diff', '--cached', '--binary', '--full-index', '--no-ext-diff', '--no-textconv', '--no-renames', '--src-prefix=a/', '--dst-prefix=b/']
        forward = run('06_forward_diff', git + diff_options + [BASELINE, '--'], cwd=DELIVERY / 'after', env_extra=isolated_env)
        reverse = run('07_reverse_diff', git + diff_options + ['-R', BASELINE, '--'], cwd=DELIVERY / 'after', env_extra=isolated_env)
        (DELIVERY / 'forward.patch').write_bytes(forward)
        (DELIVERY / 'reverse.patch').write_bytes(reverse)
        candidate_git_tree = run('08_snapshot_write_tree', git + ['write-tree'], cwd=DELIVERY / 'after', env_extra=isolated_env).decode().strip()
        diff_names = run('09_snapshot_name_status', git + ['diff', '--cached', '--name-status', '--no-renames', BASELINE, '--'], cwd=DELIVERY / 'after', env_extra=isolated_env).decode().splitlines()
        if {line.split('\t', 1)[1] for line in diff_names} != new_paths or any(not line.startswith('A\t') for line in diff_names):
            raise ValueError('PATCH_SCOPE_EXPECTED_25_ADDS')

        verification = WORK / 'apply_verification_tree'
        write_payload(verification, baseline_rows, baseline_bytes)
        run('10_verification_git_init', ['git', 'init', '--quiet'], cwd=verification)
        observed_before = snapshot(verification)[0]
        if observed_before != baseline_rows:
            raise ValueError('VERIFICATION_BEFORE_MISMATCH')
        run('11_forward_check', ['git', 'apply', '--check', str(DELIVERY / 'forward.patch')], cwd=verification)
        run('12_forward_apply', ['git', 'apply', str(DELIVERY / 'forward.patch')], cwd=verification)
        observed_forward = snapshot(verification)[0]
        if observed_forward != candidate_start or len(observed_forward) != 77:
            raise ValueError('FORWARD_APPLY_WHOLE_TREE_MISMATCH')
        run('13_reverse_check', ['git', 'apply', '--check', str(DELIVERY / 'reverse.patch')], cwd=verification)
        run('14_reverse_apply', ['git', 'apply', str(DELIVERY / 'reverse.patch')], cwd=verification)
        observed_reverse = snapshot(verification)[0]
        if observed_reverse != baseline_rows or len(observed_reverse) != 52:
            raise ValueError('REVERSE_APPLY_WHOLE_TREE_MISMATCH')

        requests = DELIVERY / 'INTERFACE_REQUESTS'
        requests.mkdir()
        request_files = ('M09-IR-001-READ_COMPOSITION.md', 'M09-IR-002-REVIEW_UI.md',
                         'M09-IR-003-PUBLICATION_AND_DISPATCH.md', 'M09_INTERFACE_BEFORE_IMAGES.json')
        request_copies = []
        for name in request_files:
            source = ROOT / 'evidence/interface_draft' / name
            raw = source.read_bytes()
            destination = requests / name
            destination.write_bytes(raw)
            if destination.read_bytes() != source.read_bytes():
                raise ValueError('INTERFACE_REQUEST_COPY_MISMATCH:' + name)
            request_copies.append({'path': 'INTERFACE_REQUESTS/' + name, 'bytes': len(raw), 'sha256': digest(raw)})

        donor_manifest = json.loads(candidate_bytes['V5/contracts/m09_a_close_daily_source_manifest.json'])
        donor_entries = {entry['target_path']: entry for entry in donor_manifest['entries']}
        records = []
        for relative, after in candidate_start.items():
            before = baseline_rows.get(relative)
            action = 'UNCHANGED' if before == after else 'ADD' if before is None else 'MODIFY'
            row = {'path': relative, 'action': action, 'reason': reason(relative, action, donor_entries),
                   'before': {'exists': before is not None, **(before or {'bytes': None, 'sha256': None, 'git_blob_sha1': None, 'git_mode': None})},
                   'after': {'exists': True, **after}}
            if before is None:
                row['new_path_verification'] = {'status': 'ADD_ABSENT', 'assembled_local_baseline_commit': BASELINE,
                    'assembled_local_baseline_path_present': False, 'fixed_F_commit': FIXED_F, 'fixed_F_path_present': False,
                    'proof_path': 'logs/patch_verification/BASELINE_PATH_VERIFICATION.json', 'proof_sha256': digest(proof_raw)}
            if relative in donor_entries:
                entry = donor_entries[relative]
                if after['sha256'] != entry['sha256'] or after['bytes'] != entry['bytes'] or after['git_blob_sha1'] != entry['source_git_blob_sha1']:
                    raise ValueError('NEW_FROZEN_DONOR_IDENTITY_MISMATCH:' + relative)
                row['copied_donor'] = {key: entry[key] for key in ('source_repository', 'source_commit', 'source_path', 'source_git_blob_sha1')}
            records.append(row)
        changes = {'schema_version': 'v5.m09.delivery_changed_files.v1', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                   'source_repository': 'lexi2016/v4', 'original_source_commit': FIXED_F,
                   'local_reconstructed_diff_baseline_commit': BASELINE,
                   'local_baseline_is_complete_repository': False, 'local_baseline_scope': 'Exact 52-file supplied F source slice',
                   'candidate_identity_kind': 'CURRENT_WORKTREE_RAW_BYTE_SNAPSHOT', 'observed_candidate_local_head_commit': source_head,
                   'candidate_snapshot_git_tree': candidate_git_tree, 'candidate_commit_remote_publication_claim': False,
                   'excluded_path_components': sorted(EXCLUDED),
                   'before_file_count': 52, 'after_file_count': 77,
                   'action_counts': {'ADD': 25, 'MODIFY': 0, 'DELETE': 0, 'UNCHANGED': 52},
                   'before_raw_tree_sha256': tree_id(baseline_rows), 'after_raw_tree_sha256': tree_id(candidate_start),
                   'tree_digest_definition': manifest(candidate_start)['tree_digest_definition'],
                   'fixed_F_full_tree_proof': {'path': 'logs/patch_verification/BASELINE_PATH_VERIFICATION.json',
                       'bytes': len(proof_raw), 'sha256': digest(proof_raw), 'endpoint': proof['endpoint'],
                       'retrieved_at': proof['retrieved_at'], 'truncated': False, 'all_tree_entries': 2746},
                   'files': records, 'interface_request_copies': request_copies}
        save(DELIVERY / 'CHANGED_FILES.json', changes)
        candidate_end = snapshot(SOURCE)[0]
        if candidate_end != candidate_start or snapshot(DELIVERY / 'after')[0] != candidate_start:
            raise ValueError('SOURCE_CHANGED_BEFORE_FINALIZATION; RETRY_REQUIRED')
        save(LOGS / 'before_tree_manifest.json', manifest(baseline_rows))
        save(LOGS / 'after_tree_manifest.json', manifest(candidate_start))
        save(LOGS / 'observed_forward_tree_manifest.json', manifest(observed_forward))
        save(LOGS / 'observed_reverse_tree_manifest.json', manifest(observed_reverse))
        (LOGS / 'BASELINE_PATH_VERIFICATION.json').write_bytes(proof_raw)
        summary = {'schema_version': 'v5.m09.patch_roundtrip_verification.v1', 'status': 'VERIFIED',
                   'finished_at_utc': datetime.now(timezone.utc).isoformat(), 'verification_tree': str(verification),
                   'local_baseline_commit': BASELINE, 'fixed_F_commit': FIXED_F, 'observed_candidate_local_head_commit': source_head,
                   'candidate_snapshot_git_tree': candidate_git_tree, 'candidate_source_snapshot_stable': True,
                   'before_file_count': 52, 'forward_file_count': 77, 'reverse_file_count': 52,
                   'forward_whole_tree_equals_candidate': True, 'reverse_whole_tree_equals_before': True,
                   'before_raw_tree_sha256': tree_id(baseline_rows), 'after_raw_tree_sha256': tree_id(candidate_start),
                   'observed_forward_raw_tree_sha256': tree_id(observed_forward), 'observed_reverse_raw_tree_sha256': tree_id(observed_reverse),
                   'forward_patch': {'bytes': len(forward), 'sha256': digest(forward)},
                   'reverse_patch': {'bytes': len(reverse), 'sha256': digest(reverse)},
                   'commands': COMMANDS, 'source_worktree_mutated_by_assembly': False,
                   'source_git_index_and_object_store_mutated_by_assembly': False,
                   'shared_api_ui_deployment_or_mac_acceptance': 'NOT_RUN'}
        save(LOGS / 'PATCH_VERIFICATION.json', summary)
        shutil.copytree(LOGS, DELIVERY / 'logs/patch_verification')
        if snapshot(SOURCE)[0] != candidate_start:
            raise ValueError('SOURCE_CHANGED_AFTER_LOG_COPY; RETRY_REQUIRED')
        print(json.dumps({'status': 'VERIFIED', 'delivery': str(DELIVERY), 'work': str(WORK),
                          'before_count': 52, 'after_count': 77, 'source_head': source_head,
                          'candidate_git_tree': candidate_git_tree, 'before_tree_sha256': tree_id(baseline_rows),
                          'after_tree_sha256': tree_id(candidate_start), 'forward_patch_sha256': digest(forward),
                          'reverse_patch_sha256': digest(reverse),
                          'changed_files_sha256': digest((DELIVERY / 'CHANGED_FILES.json').read_bytes()),
                          'patch_verification_sha256': digest((LOGS / 'PATCH_VERIFICATION.json').read_bytes())}, indent=2))
    except Exception as error:
        save(LOGS / 'ASSEMBLY_ABORTED.json', {'status': 'ABORTED', 'error': type(error).__name__ + ':' + str(error),
                                           'commands': COMMANDS, 'at_utc': datetime.now(timezone.utc).isoformat()})
        if created_delivery and DELIVERY.exists():
            DELIVERY.rename(WORK / 'aborted_delivery')
        raise


if __name__ == '__main__':
    main()

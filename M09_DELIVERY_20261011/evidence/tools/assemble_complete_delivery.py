"""Assemble the frozen M09 candidate with its complete, observed evidence.

This is delivery machinery, not a product entry point. It does not edit after,
install packages, call a market source, or publish a remote branch.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': digest(raw),
            'git_blob_sha1': hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),
            'git_mode': '100755' if path.stat().st_mode & 0o111 else '100644'}


def files(root):
    return sorted(p for p in root.rglob('*') if p.is_file()
                  and not {'.git', '__pycache__'} & set(p.parts))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                               allow_nan=False)+'\n', encoding='utf-8')


def copy_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert source.read_bytes() == target.read_bytes(), str(target)


def ref(path, root):
    return {'path': str(path.relative_to(root)), **identity(path)}


def verified_log(root, relative):
    path = root/relative
    data = json.loads(path.read_bytes())
    for key in ('stdout', 'stderr'):
        artifact = path.parent/data[key]['path']
        actual = identity(artifact)
        assert all(actual[k] == data[key][k] for k in ('sha256', 'bytes'))
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', required=True)
    args = parser.parse_args()
    work = Path(args.work)
    assert work.is_absolute()
    delivery, evidence = work/'delivery', work/'evidence'
    assert delivery.is_dir()
    frozen_commit = '4f874c23daaa96787ebeebb5b772079635193cb0'
    observed = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=work/'after', text=True).strip()
    assert observed == frozen_commit
    changed = json.loads((delivery/'CHANGED_FILES.json').read_bytes())
    assert changed['action_counts'] == {'ADD': 25, 'DELETE': 0, 'MODIFY': 0, 'UNCHANGED': 52}
    for item in changed['files']:
        assert identity(work/'after'/item['path']) == identity(delivery/'after'/item['path'])
        assert all(identity(work/'after'/item['path'])[k] == item['after'][k]
                   for k in ('bytes', 'sha256', 'git_blob_sha1', 'git_mode'))
        if item['action'] == 'UNCHANGED':
            assert (delivery/'before'/item['path']).read_bytes() == (work/'after'/item['path']).read_bytes()
    assert len(files(delivery/'after')) == 77 and len(files(delivery/'before')) == 52

    excluded = []
    for path in files(evidence):
        rel = path.relative_to(evidence)
        skip = (rel.name == 'REMOTE_BASE_TEXT_FILES.json'
                or any(part in ('cloud_walkthrough_smoke', 'cloud_walkthrough_smoke_02',
                                'apply_verification_tree', 'isolated_git') for part in rel.parts)
                or any(part.endswith('.git') for part in rel.parts))
        if skip:
            excluded.append(str(rel))
            continue
        copy_file(path, delivery/'evidence'/rel)
    for dirname in ('original', 'supplement'):
        for path in files(work/dirname):
            copy_file(path, delivery/dirname/path.relative_to(work/dirname))
    for path in files(evidence/'logs'):
        copy_file(path, delivery/'logs'/path.relative_to(evidence/'logs'))
    for path in files(work/'packaging_logs'):
        copy_file(path, delivery/'logs/packaging'/path.relative_to(work/'packaging_logs'))
    for path in (evidence/'independent_review').glob('test_*.py'):
        copy_file(path, delivery/'tests'/path.name)
    for path in files(evidence/'tools'):
        copy_file(path, delivery/'tools'/path.relative_to(evidence/'tools'))
    for path in [evidence/'run_logged.py', evidence/'delivery_docs/raw_historical_input_diagnosis.py',
                 evidence/'mac_draft/mac_real_input_check.py',
                 evidence/'mac_draft/mac_generation_walkthrough.py']:
        if path.exists():
            copy_file(path, delivery/'tools'/path.name)
    for name in ('INPUTS_MANIFEST.json', 'ENVIRONMENT.json', 'SOURCE_DEPENDENCIES.json',
                 'ALGORITHM_PARITY.json', 'FAILURE_MATRIX.json', 'FAILURE_MATRIX.md',
                 'SOURCE_EVIDENCE_VALIDATION.json'):
        copy_file(evidence/'delivery_docs'/name, delivery/name)
    copy_file(delivery/'logs/patch_verification/BASELINE_PATH_VERIFICATION.json',
              delivery/'BASELINE_PATH_VERIFICATION.json')
    copy_file(delivery/'logs/patch_verification/PATCH_VERIFICATION.json',
              delivery/'PATCH_VERIFICATION.json')

    for path in files(work/'engineering_outputs'):
        copy_file(path, delivery/'outputs/engineering'/path.relative_to(work/'engineering_outputs'))
    originals = {'panel_20261009_required8.parquet', 'membership_20261009.txt',
                 'panel_source_receipt.json', 'CURRENT_SELECTOR_READY_PANEL.txt',
                 'daily_pointer.txt', 'dispatcher_pointer.txt'}
    for path in files(work/'historical_rejection'):
        rel = path.relative_to(work/'historical_rejection')
        if rel.parts[0] == 'relocated_source' and rel.name in originals:
            continue
        copy_file(path, delivery/'outputs/historical_rejection'/rel)
    output_files = [ref(path, delivery) for path in files(delivery/'outputs')]
    engineering = json.loads((delivery/'outputs/engineering/walkthrough_result.json').read_bytes())
    historical = json.loads((delivery/'outputs/historical_rejection/result.json').read_bytes())
    assert historical['status'] == 'EXPECTED_REJECTION_CONFIRMED'
    assert historical['original_bytes_unchanged'] is True
    assert engineering['two_slots_distinct_receipts_one_calculation'] is True
    save(delivery/'OUTPUTS_MANIFEST.json', {
        'schema_version': 'v5.m09.delivery_outputs.v1',
        'source_code_local_commit': frozen_commit,
        'engineering': {'classification': 'SYNTHETIC_ENGINEERING_ONLY',
                        'result': engineering, 'http_or_ui_execution': 'NOT_RUN'},
        'real_historical_rejection': historical,
        'original_output_is_not_an_input_prerequisite': True,
        'retained_absolute_paths': 'Original observed creation paths are immutable evidence. They do not claim the same host exists on another machine.',
        'omitted_duplicate_raw_copies': {
            'files': sorted(originals),
            'reason': 'Unchanged original bytes are physically included in repository/handoff/m09-20261011/M09_ORIGINAL_INPUTS_RUNTIME_BINDINGS_20261011.zip and in the original R3 ZIP. No source data is omitted from the enclosing repository export.',
            'reconstruction': 'tools/extract_pinned_runtime.py then tools/run_offline_historical_rejection.py in a new directory; this produces new execution timestamps, not the historical recorded attempts.'},
        'files': output_files})

    final = verified_log(delivery, 'logs/final_candidate_regression.json')
    final_text = (delivery/'logs/final_candidate_regression.stderr.log').read_text()
    assert final['exit_code'] == 0 and re.search(r'Ran 125 tests', final_text)
    assert 'OK (skipped=4)' in final_text
    passed = [line for line in final_text.splitlines() if re.search(r'^test_.* \.\.\. ok$', line)]
    skipped = [line for line in final_text.splitlines() if re.search(r'^test_.* \.\.\. skipped ', line)]
    assert len(passed) == 121 and len(skipped) == 4, (len(passed), len(skipped))
    independent = verified_log(delivery, 'evidence/independent_review/independent_final_all_green.json')
    independent_text = (delivery/'evidence/independent_review/independent_final_all_green.stderr.log').read_text()
    assert independent['exit_code'] == 0 and 'Ran 6 tests' in independent_text
    patch = json.loads((delivery/'PATCH_VERIFICATION.json').read_bytes())
    assert patch['status'] == 'VERIFIED' and patch['forward_whole_tree_equals_candidate']
    assert patch['reverse_whole_tree_equals_before'] and patch['candidate_source_snapshot_stable']
    parity = json.loads((delivery/'ALGORITHM_PARITY.json').read_bytes())
    assert parity['status'] == 'PASS_SYNTHETIC_ADMITTED_FRAME_FULL_CHAIN'
    source_identity = {
        'schema_version': 'v5.m09.final_source_identity.v1',
        'original_F': 'f7cb731c384ee6890a87d16c19a5b5a621779477',
        'handoff_H': '782bfc9ae91ff9cfe897afffc52aad43b7c1b78c',
        'local_reconstructed_source_baseline': 'e45aee9e185dda6f9d4b5032e6d60231cce27809',
        'final_local_source_commit': frozen_commit,
        'final_local_source_tree': changed['candidate_snapshot_git_tree'],
        'published_candidate_commit': 'ENCLOSING_GIT_COMMIT',
        'commit_resolution': 'The verified outer EXPORT_VERIFICATION.json supplies the actual full GitHub commit without a self-referential hash inside its own tree.',
        'source_dependency_null_commit_binding': 'The retained earlier SOURCE_DEPENDENCIES.json has local_candidate.commit=null. This later final manifest binds its exact candidate bytes to final_local_source_commit and the enclosing GitHub commit.',
        'historical_snapshot_warning': 'Earlier freeze files and RED/GREEN logs retain their actual development-time identities; FINAL_VERIFICATION.json and this file identify the final delivered candidate.',
        'after_files': [ref(path, delivery/'after') for path in files(delivery/'after')]}
    save(delivery/'SOURCE_IDENTITY.json', source_identity)
    save(delivery/'FINAL_VERIFICATION.json', {
        'schema_version': 'v5.m09.final_verification.v1', 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'result': 'ENGINEERING_CANDIDATE_VERIFIED_WITH_EXPLICIT_NOT_RUN_LAYERS',
        'source_identity': ref(delivery/'SOURCE_IDENTITY.json', delivery),
        'regression': {'discovered': 125, 'passed': 121, 'skipped': 4, 'failed': 0, 'errors': 0,
                       'actual_command': final, 'passed_test_lines': passed, 'skipped_test_lines': skipped},
        'independent_review': {'passed': 6, 'skipped': 0, 'failed': 0, 'actual_command': independent,
                               'resolution': ref(delivery/'evidence/independent_review/FINAL_REVIEW_RESOLUTION.md', delivery)},
        'original_algorithm': {'status': parity['status'], 'full_object_cases': 2, 'original_refusal_cases': 1,
                               'field_counts': [1239, 1301], 'report': ref(delivery/'ALGORITHM_PARITY.json', delivery),
                               'real_parquet_decoder_parity': 'NOT_RUN'},
        'patch_roundtrip': ref(delivery/'PATCH_VERIFICATION.json', delivery),
        'historical_daily_attempts': {'status': 'EXPECTED_REJECTION_CONFIRMED', 'slots': ['16:05', '17:10'],
                                     'result': ref(delivery/'outputs/historical_rejection/result.json', delivery)},
        'engineering_outputs': ref(delivery/'OUTPUTS_MANIFEST.json', delivery),
        'original_pytest_suites': {'status': 'BLOCKED', 'reason': 'pytest is absent in the actual execution environment; no install attempted',
                                  'actual_command': ref(delivery/'evidence/project_pytest_availability.json', delivery)},
        'acceptance_layers': [
            {'layer': '工程候选与隔离故障', 'status': 'PASS_WITH_4_EXPLICIT_PARQUET_SKIPS'},
            {'layer': '真实 parquet/Mac 现有环境兼容与完整行情结果', 'status': 'NOT_RUN'},
            {'layer': '活动普通 API、原 ReviewView 与 A/H 现场隔离', 'status': 'NOT_RUN'},
            {'layer': '16:05/17:10 自然触发及正式发布资格', 'status': 'NOT_RUN'},
            {'layer': '连续两个自然交易日与现场回滚验收', 'status': 'NOT_RUN'}],
        'no_dependency_or_environment_change': True,
        'scope': 'Engineering evidence is neither real-market success nor deployment approval.'})
    save(delivery/'REPOSITORY_LAYOUT.json', {
        'schema_version': 'v5.m09.repository_layout.v1',
        'repository': 'lexi2016/v5', 'candidate_branch': 'v5/m09-candidate-20261011-r1',
        'parent_commit': source_identity['handoff_H'], 'candidate_commit': 'ENCLOSING_GIT_COMMIT',
        'root_entry': 'M09_CANDIDATE.md', 'delivery_prefix': 'M09_DELIVERY_20261011',
        'root_source_mapping': 'Every file after/<relative> is also committed at repository/<relative> with identical bytes and Git mode.',
        'base_commit_unchanged': 'All 32 handoff commit blobs, including START_HERE.md and the original R3 ZIP, are retained unchanged.',
        'input_archive': 'handoff/m09-20261011/M09_ORIGINAL_INPUTS_RUNTIME_BINDINGS_20261011.zip',
        'tools_aliases': {'tools/run_logged.py': 'evidence/run_logged.py',
                          'tools/mac_real_input_check.py': 'evidence/mac_draft/mac_real_input_check.py',
                          'tools/mac_generation_walkthrough.py': 'evidence/mac_draft/mac_generation_walkthrough.py',
                          'tests/': 'evidence/independent_review/test_*.py'},
        'source_files': [item['path'] for item in changed['files']],
        'export_metadata': 'The offline ZIP contains repository/ with exactly the commit tree; EXPORT_VERIFICATION.json is an external export receipt, not an extra committed file.'})
    mac = (evidence/'mac_draft/MAC_ACCEPTANCE_DRAFT.md').read_text()
    mac = mac.replace('# M09 Mac 独立验收与单模块回滚草案', '# M09 Mac 独立验收与单模块回滚执行手册', 1)
    mac = mac.replace('**文档状态：DRAFT。', '**文档状态：候选配套验收手册；Mac 执行状态 NOT_RUN。', 1)
    mac = mac.replace("export M09_ORIGINAL='/absolute/verified/material/original'", "export M09_ORIGINAL='/absolute/verified/delivery/original'")
    mac = mac.replace('test_a_close_review test_a_close_daily_sources test_a_close_daily test_a_close_daily_api',
                      'test_a_close_review test_a_close_daily_sources test_a_close_daily test_a_close_daily_api test_daily_close_plan')
    mac = mac.replace('请求 T = A.trade_date = model.review_date = record/generation 日 = publication.trade_date；model.run_id',
                      '请求 T = `market_reviews.A.trade_date` = `market_reviews.A.model_review.review_date` = record/generation 日 = `market_reviews.A.m09_publication.trade_date`；`market_reviews.A.model_review.run_id`')
    introduction = ('\n本手册对应本交付 `SOURCE_IDENTITY.json` 的最终源码；实际 GitHub 完整提交见离线包外层 `EXPORT_VERIFICATION.json`。'
                    '下面 `/absolute/verified/delivery` 指离线 `repository/M09_DELIVERY_20261011` 或 Git checkout 中同名目录。'
                    '`original/` 已完整包含；runtime 原 ZIP 在仓库 `handoff/m09-20261011/`，先按 README 解压并核原件。'
                    'helper 和独立测试保留了 `evidence/...` 原路径，同时在 `tools/`、`tests/` 提供完全相同的便捷副本。\n')
    mac = mac.replace('\n## 1. 固定对象和范围', introduction+'\n## 1. 固定对象和范围', 1)
    (delivery/'MAC_ACCEPTANCE.md').write_text(mac, encoding='utf-8')
    readme = (evidence/'delivery_docs/README_DELIVERY.md').read_text()
    readme = readme.replace('`PATCH_VERIFICATION.json`、`logs/patch/`', '`PATCH_VERIFICATION.json`、`logs/patch_verification/`')
    (delivery/'README.md').write_text(readme, encoding='utf-8')
    save(delivery/'EVIDENCE_LAYOUT.json', {
        'schema_version': 'v5.m09.evidence_layout.v1',
        'historical_logs': 'All actual command logs are retained at their original relative evidence paths. Root logs/ is a convenience copy of evidence/logs/; logs/patch_verification is the complete actual assembly transcript.',
        'excluded_reproducible_duplicates': excluded,
        'exclusion_limits': 'No final source, required before, actual command log, current engineering product, original input archive, or original-algorithm comparison object is excluded. Disposable old smoke products and verification worktrees are not final outputs.',
        'binary_command_output': '03_baseline_archive.stdout.log is the exact tar byte stream emitted by git archive. Its binary contents are retained and hashed; it is not a UTF-8 terminal log.',
        'input_root_mapping': {'original/': 'Included directly', 'supplement/': 'Included directly',
                               'runtime_inputs/': 'Extract the fixed runtime ZIP into a new directory',
                               'm09_input/m09_handoff_20261011/': 'Original handoff files remain in repository/handoff/m09-20261011/'}})
    for item in source_identity['after_files']:
        assert identity(work/'after'/item['path']) == {k:item[k] for k in ('bytes','sha256','git_blob_sha1','git_mode')}
    entries = [ref(path, delivery) for path in files(delivery) if path.name != 'DELIVERY_FILES.json']
    save(delivery/'DELIVERY_FILES.json', {'schema_version': 'v5.m09.delivery_files.v1',
        'self_excluded': 'DELIVERY_FILES.json only; the enclosing Git tree and outer export receipt bind it.',
        'file_count_excluding_self': len(entries), 'total_bytes_excluding_self': sum(x['bytes'] for x in entries),
        'files': entries})
    print(json.dumps({'status': 'COMPLETE_DELIVERY_ASSEMBLED', 'delivery': str(delivery),
                      'file_count': len(entries)+1, 'bytes': sum(p.stat().st_size for p in files(delivery)),
                      'source_files': 77, 'before_files': 52, 'source_unchanged': True}, indent=2))


if __name__ == '__main__':
    main()

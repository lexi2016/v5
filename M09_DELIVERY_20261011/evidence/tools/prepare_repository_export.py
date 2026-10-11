"""Seal delivery and assemble the exact private-repository candidate tree."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def ident(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'git_blob_sha1': hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),
            'git_mode': '100755' if path.stat().st_mode & 0o111 else '100644'}


def allfiles(root):
    return sorted(p for p in root.rglob('*') if p.is_file()
                  and not {'.git', '__pycache__'} & set(p.parts))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n', encoding='utf-8')


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert ident(source) == ident(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', required=True)
    a = parser.parse_args()
    w = Path(a.work)
    d, repo = w/'delivery', w/'repository_export'
    assert w.is_absolute()
    assert subprocess.check_output(['git','rev-parse','HEAD'], cwd=w/'after', text=True).strip() == '4f874c23daaa96787ebeebb5b772079635193cb0'
    for p in allfiles(w/'packaging_logs'):
        copy(p, d/'logs/packaging'/p.relative_to(w/'packaging_logs'))
    copy(Path(__file__), d/'tools'/Path(__file__).name)
    copy(Path(__file__), d/'evidence/tools'/Path(__file__).name)
    changed = json.loads((d/'CHANGED_FILES.json').read_bytes())
    for item in changed['files']:
        key = item['path']
        assert ident(w/'after'/key) == ident(d/'after'/key)
        assert all(ident(d/'after'/key)[k] == item['after'][k] for k in ('bytes','sha256','git_blob_sha1','git_mode'))
        if item['before']['exists']:
            assert ident(d/'before'/key) == ident(d/'after'/key)
    parity = json.loads((d/'ALGORITHM_PARITY.json').read_bytes())
    for path, sha in parity['candidate_python_files'].items():
        assert ident(d/'after'/path)['sha256'] == sha
    for row in parity['successful_cases']:
        assert ident(d/row['detail']['path'])['sha256'] == row['detail']['sha256']
    for name, sibling in [('mac_generation_walkthrough.py','mac_draft'), ('mac_real_input_check.py','mac_draft')]:
        assert (d/'tools'/name).read_bytes() == (d/'evidence'/sibling/name).read_bytes()
    for p in (d/'tests').glob('test_*.py'):
        assert p.read_bytes() == (d/'evidence/independent_review'/p.name).read_bytes()
    assert len(list((d/'tests').glob('test_*.py'))) == 4
    assert len(allfiles(d/'before')) == 52 and len(allfiles(d/'after')) == 77
    outputs = json.loads((d/'OUTPUTS_MANIFEST.json').read_bytes())
    for item in outputs['files']:
        assert ident(d/item['path']) == {k:item[k] for k in ('bytes','sha256','git_blob_sha1','git_mode')}
    current_final = json.loads((d/'FINAL_VERIFICATION.json').read_bytes())
    assert current_final['regression']['passed'] == 121 and current_final['regression']['skipped'] == 4
    write(d/'DELIVERY_VALIDATION.json', {
        'schema_version': 'v5.m09.delivery_validation.v1', 'status': 'VERIFIED',
        'observed_at_utc': datetime.now(timezone.utc).isoformat(),
        'before_files_exact': 52, 'after_files_exact': 77, 'python_source_sha_bindings_verified': 40,
        'complete_output_files_verified': len(outputs['files']), 'independent_test_copies_verified': 4,
        'both_mac_helper_sibling_copies_verified': True,
        'all_source_bytes_unchanged_since_final_test': True,
        'mac_active_http_ui_natural_or_deployment_claim': 'NOT_RUN',
        'scope': 'Delivery byte and reference validation. This does not rerun or replace the retained product test evidence.'})
    delivery_entries = [{'path': str(p.relative_to(d)), **ident(p)} for p in allfiles(d) if p.name != 'DELIVERY_FILES.json']
    write(d/'DELIVERY_FILES.json', {'schema_version': 'v5.m09.delivery_files.v1',
        'self_excluded': 'DELIVERY_FILES.json only; enclosing Git tree and outer export receipt bind it.',
        'file_count_excluding_self': len(delivery_entries),
        'total_bytes_excluding_self': sum(x['bytes'] for x in delivery_entries), 'files': delivery_entries})
    for row in delivery_entries:
        assert ident(d/row['path']) == {k:row[k] for k in ('bytes','sha256','git_blob_sha1','git_mode')}
    base = json.loads((w/'evidence/REMOTE_HANDOFF_BASE_TREE.json').read_bytes())
    assert base['sha'] == 'aa29ae3a72ee902d3dc471bf6dd09e4ec2ff2fc8' and base['truncated'] is False
    base_files = {x['path']:x for x in base['tree'] if x['type']=='blob'}
    assert len(base_files) == 32
    existing = {str(p.relative_to(repo)):ident(p) for p in allfiles(repo)}
    assert set(existing) == set(base_files), 'Repository export must initially contain only the verified 32 base files'
    for path, row in base_files.items():
        assert existing[path]['git_blob_sha1'] == row['sha']
        assert existing[path]['bytes'] == row['size'] and existing[path]['git_mode'] == row['mode']
    for p in allfiles(d/'after'):
        rel = p.relative_to(d/'after')
        assert str(rel) not in base_files
        copy(p, repo/rel)
    for p in allfiles(d):
        copy(p, repo/'M09_DELIVERY_20261011'/p.relative_to(d))
    (repo/'M09_CANDIDATE.md').write_text('''# M09 A 股收盘复盘完整候选

本提交在独立私有 `lexi2016/v5` 中提供 M09 完整候选实现与实体交付。父提交为固定交接 `782bfc9ae91ff9cfe897afffc52aad43b7c1b78c`；原只读出处 F 仍为 `lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`。原交接 32 文件（含 R3 ZIP）原字节保留。

## 入口

- [完整交付与资格状态](M09_DELIVERY_20261011/README.md)
- [实际代码入口、数据合同和调用](V5/docs/M09_A_CLOSE_HANDOFF.md)
- [before/after、逐文件 SHA 和动作](M09_DELIVERY_20261011/CHANGED_FILES.json)
- [当前固定候选的实际验证](M09_DELIVERY_20261011/FINAL_VERIFICATION.json)
- [完整原算法等价](M09_DELIVERY_20261011/ALGORITHM_PARITY.json)
- [新 review/store/run/generation/两槽回执与投影](M09_DELIVERY_20261011/OUTPUTS_MANIFEST.json)
- [Mac 独立验收及单模块回滚](M09_DELIVERY_20261011/MAC_ACCEPTANCE.md)
- [唯一集成者的函数级请求](M09_DELIVERY_20261011/INTERFACE_REQUESTS)

根目录的 `V5/...` 等 77 份源码与 `M09_DELIVERY_20261011/after/` 完全相同：52 份原件保持不变，新增 25 文件。实现 M09 私有 daily、原完整链、不可变 run/generation、两槽回执、失败保旧、提交见证和硬中断恢复、独立验读及 A 只读 API 投影。固定概率、PIT/研究资格、禁用 LLM、WATCH_ONLY 和空 core pool 保留。

实际工程回归 125 项：121 通过、4 因缺少 pyarrow 跳过；独立审查另 6 项通过；正反 patch 已实际应用并做全树字节核对。原算法两个完整工程对照及一个原拒绝异常一致。真实 T=20261009 原件两槽拒绝路径已执行并留失败回执；未解码的 panel 行数保持 null。

**本提交不是部署完成或生产验收。** Mac 现有 pandas 3.0.5 / pyarrow 25.0.1 超固定 V5 声明上界，未改依赖/环境；Mac 实测、真实 parquet 解码、活动普通 API/原 ReviewView 接线、自然两槽及连续两个自然交易日验收均保留 NOT_RUN。共享接线只交函数级请求；不写 V4、不修改全局 root、不交易。

同提交离线导出包含整个 `repository/` 树和外层 `EXPORT_VERIFICATION.json`。外层回执记录实际远端完整 commit/tree 与逐文件核验；回执本身不是提交树中的自引用文件。
''', encoding='utf-8')
    for path,row in base_files.items():
        assert ident(repo/path)['git_blob_sha1'] == row['sha']
    repo_entries = [{'path':str(p.relative_to(repo)), **ident(p), 'is_base_file':str(p.relative_to(repo)) in base_files}
                    for p in allfiles(repo)]
    write(w/'publication/PUBLISH_MANIFEST.json', {
        'schema_version':'v5.m09.prepublication_manifest.v1', 'repository':'lexi2016/v5',
        'candidate_branch':'v5/m09-candidate-20261011-r1',
        'base_commit':'782bfc9ae91ff9cfe897afffc52aad43b7c1b78c', 'base_tree':base['sha'],
        'root':str(repo), 'base_files_unchanged':32, 'file_count':len(repo_entries),
        'bytes':sum(x['bytes'] for x in repo_entries), 'files':repo_entries})
    print(json.dumps({'status':'REPOSITORY_EXPORT_PREPARED','file_count':len(repo_entries),
                      'bytes':sum(x['bytes'] for x in repo_entries),
                      'delivery_files':len(delivery_entries)+1, 'base_blobs_unchanged':32,
                      'candidate_source_files':77}, indent=2))


if __name__ == '__main__':
    main()

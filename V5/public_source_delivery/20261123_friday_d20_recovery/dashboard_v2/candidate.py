"""Reconstructed V5 preview: only 11/20 pinned research Top200. No owner."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from types import ModuleType

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'board_reconstructed_20261122' / 'board.py'
TOP = HERE.parent / 'tonight_d20_replay_20261121/historical_inputs/a_top200_official_20261120/TOP200.json'
BASE_SHA = '580dbcded9cdf4f7b5bb71963280ace59c9262264a8e0db29580b553f2f508b9'
TOP_SHA = '9e6626a38b5df40d404d3e8a7a6f10c7b7b2c5e3df2d5c658e277c5df4d556b2'
DAY = '20261120'

def pinned(path, expected):
    if path.is_symlink():
        raise ValueError('SOURCE_SYMLINK')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('SOURCE_PIN')
    return raw

def friday_rows(path=TOP):
    t = json.loads(pinned(path, TOP_SHA))
    rows = t['rows']
    if (t['schema'] != 'PARAMETERIZED_FIXED_REFERENCE_RESEARCH_TOP200_V1'
        or t['source_date'] != int(DAY)
        or tuple(t[k] for k in ('scope_count','valid_rank_count','unknown_count','top_count')) != (5575,5566,9,200)
        or any(t[k] is not False for k in ('production_allowed','selection_admission','natural_acceptance'))
        or len(rows) != 200 or len({x['symbol'] for x in rows}) != 200
        or [(x['rank'],x['source_date']) for x in rows] != [(i,int(DAY)) for i in range(1,201)]
        or any(not re.fullmatch(r'[0-9]{6}\.(SH|SZ|BJ)',x['symbol']) for x in rows)):
        raise ValueError('FRIDAY_TOP200_IDENTITY')
    return [dict(rank=x['rank'],symbol=x['symbol'],change=x['change_pct_display'],close=x['raw_close']) for x in rows]

def build_preview():
    board = ModuleType('pinned_reconstructed_board')
    board.__file__ = str(BASE)
    raw = pinned(BASE, BASE_SHA)
    exec(compile(raw, str(BASE), 'exec'), vars(board))
    old = board.project
    def project(day):
        result = old(day)
        if day == DAY:
            result['historical_top200'] = friday_rows()
        return result
    board.project = project
    initial_render = board.render
    def render():
        output = initial_render()
        substitutions = (
            ('仅在 11 月 19 日可读已核冻结候选榜；其余日期不回填。',
             '按所选日期显示已核冻结候选榜；无该日榜单时不回填。'),
            ("'11月19日冻结原 G4 候选榜，显示 '",
             "Number(p.date.slice(4,6))+'月'+Number(p.date.slice(6,8))+'日冻结原 G4 候选榜，显示 '"),
        )
        for source, target in substitutions:
            old, new = source.encode(), target.encode()
            if output.count(old) != 1:
                raise ValueError('PREVIEW_LABEL_ANCHOR')
            output = output.replace(old,new)
        return output
    board.render = render
    return board

def main():
    a = argparse.ArgumentParser(description=__doc__)
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument('--export',action='store_true')
    g.add_argument('--serve',action='store_true')
    x = a.parse_args()
    b = build_preview()
    if x.export:
        with (HERE/'D20_RESEARCH_PREVIEW.html').open('xb') as f:
            f.write(b.render())
    else:
        with b.server(0) as srv:
            print(f'http://127.0.0.1:{srv.server_port}/research-system/',flush=True)
            srv.serve_forever()
if __name__ == '__main__':
    main()

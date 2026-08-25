"""
一次性迁移：按更新后的 team_config 重新划分 history.json 中已存储的历史分类。

history.json 每天都固化了分类结果（rooms[].type / *_rooms 列表 / comp_rooms /
type_summary），改 team_config.py 不会回溯修正它们，所以需要这个脚本重算。

用法：
    python migrate_reclassify.py          # 试运行，只报告差异，不写盘
    python migrate_reclassify.py --apply  # 写盘（先备份 history.json.bak）
"""
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from team_config import classify_room, ALL_TEAMS

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "sales_analysis" / "history.json"

BUCKETS = {
    '我司': 'our_rooms',
    '机械空间': 'jixie_rooms',
    '纵横': 'zongheng_rooms',
    '逐梦': 'zhumeng_rooms',
    '斐纳': 'feina_rooms',
    '凝云': 'ningyun_rooms',
    '乐群': 'lequn_rooms',
    '炽木电商': 'chimu_rooms',
    '良米': 'liangmi_rooms',
}


def rebuild_day(day):
    """从 day['rooms'] 重算该天的全部分类衍生字段。"""
    rooms = day.get('rooms') or {}
    types = {name: classify_room(name) for name in rooms}

    new = {}
    for team, key in BUCKETS.items():
        new[key] = sorted([n for n, t in types.items() if t == team])
    new['comp_rooms'] = sorted([n for n, t in types.items() if t != '我司'])

    agg = defaultdict(lambda: {'orders': 0, 'revenue': 0.0, 'rooms': 0})
    for name, info in rooms.items():
        a = agg[types[name]]
        a['orders'] += int(info.get('orders', 0))
        a['revenue'] += float(info.get('revenue', 0.0))
        a['rooms'] += 1

    type_summary = {}
    for t in ALL_TEAMS:
        if t in agg and agg[t]['orders'] > 0:
            a = agg[t]
            type_summary[t] = {
                'orders': a['orders'],
                'revenue': round(a['revenue'], 2),
                'avg_price': round(a['revenue'] / a['orders'], 2),
                'rooms': a['rooms'],
            }
    new['type_summary'] = type_summary
    return types, new


def main():
    apply = '--apply' in sys.argv
    data = json.loads(HISTORY.read_text(encoding='utf-8'))

    # ---- 校验：对成员未变动的团队，重算值必须能复现原值 ----
    tol_fail = []
    for day in data:
        old_ts = day.get('type_summary') or {}
        _, new = rebuild_day(day)
        new_ts = new['type_summary']
        for t in set(old_ts) & set(new_ts):
            o, n = old_ts[t], new_ts[t]
            if o.get('orders') != n['orders']:
                continue  # 成员变了，订单数本就该变，不参与校验
            if abs(o.get('revenue', 0) - n['revenue']) > 0.05:
                tol_fail.append((day['date'], t, o.get('revenue'), n['revenue']))

    if tol_fail:
        print('!! 校验失败：订单数相同但营收对不上，重算逻辑与原逻辑不一致')
        for d, t, o, n in tol_fail[:10]:
            print(f'   {d} {t}: 原 {o} -> 重算 {n}')
        sys.exit(1)
    print(f'校验通过：{len(data)} 天中，成员未变动的团队重算结果与原值一致\n')

    # ---- 差异报告 ----
    moved = defaultdict(lambda: defaultdict(float))
    for day in data:
        rooms = day.get('rooms') or {}
        old_type = {n: (i.get('type') or '') for n, i in rooms.items()}
        types, _ = rebuild_day(day)
        for n in rooms:
            if old_type.get(n) != types[n]:
                moved[n][f'{old_type.get(n) or "?"} -> {types[n]}'] += float(
                    rooms[n].get('revenue', 0.0))

    print('=== 归属变更（按累计营收） ===')
    rows = [(n, k, v) for n, d in moved.items() for k, v in d.items()]
    for n, k, v in sorted(rows, key=lambda x: -x[2]):
        print(f'  {v:12,.0f}  {n:<24s} {k}')
    if not rows:
        print('  （无变化）')

    print('\n=== 全期团队汇总 变更前 -> 变更后 ===')
    before, after = defaultdict(float), defaultdict(float)
    for day in data:
        for n, i in (day.get('rooms') or {}).items():
            before[i.get('type') or '?'] += float(i.get('revenue', 0.0))
        types, _ = rebuild_day(day)
        for n, i in (day.get('rooms') or {}).items():
            after[types[n]] += float(i.get('revenue', 0.0))
    for t in sorted(set(before) | set(after), key=lambda x: -after.get(x, 0)):
        b, a = before.get(t, 0), after.get(t, 0)
        flag = '' if abs(b - a) < 1 else f'   ({a - b:+,.0f})'
        print(f'  {t:<8s} {b:14,.0f} -> {a:14,.0f}{flag}')

    if not apply:
        print('\n[试运行] 未写盘。确认无误后加 --apply 执行。')
        return

    shutil.copy2(HISTORY, HISTORY.with_suffix('.json.bak'))
    for day in data:
        types, new = rebuild_day(day)
        for n, info in (day.get('rooms') or {}).items():
            info['type'] = types[n]
        day.update(new)
    HISTORY.write_text(
        json.dumps(data, ensure_ascii=False, separators=(',', ':')),
        encoding='utf-8')
    print(f'\n[已写盘] 备份：{HISTORY.with_suffix(".json.bak").name}')


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""
小米手环11 首销月 · 每日销售总结

职责：**算事实 + 存总结**。不碰 xlsx —— xlsx 由 generate_band11_target.py 渲染。

**只看当天整体销售（订单口径）**，不含主播业绩 / 班次维度。
每天两块文字：销售总结（整体好坏，2-3 句）+ 交接要点（交给接班同事，1-2 句）。

为什么总结必须存独立 JSON：
    generate_band11_target.py 的 main() 每次都 `Workbook()` 从零重建整个工作簿，
    任何只写在 xlsx 里的内容第二次跑就永久消失。所以这里存，那边渲染。

用法：
    python band11_review.py status              # 最新日期对照
    python band11_review.py context [日期]      # 打印写作素材（默认=最新已入库日）
    python band11_review.py auto <日期>         # 用数据生成兜底稿并落库
    python band11_review.py add <日期> [--replace]   # 读输入稿落库
    python band11_review.py validate            # 校验 store 完整性
"""
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from generate_band11_target import (  # noqa: E402
    END, PRODUCT, ROOM_TARGETS, START, TOTAL_TARGET, OTHER_LABEL, load_daily,
)

STORE_FILE = os.path.join(ROOT, 'sales_analysis', 'daily_summary.json')
INPUT_DIR = os.path.join(ROOT, 'sales_analysis', 'daily_review_input')
HISTORY_FILE = os.path.join(ROOT, 'sales_analysis', 'history.json')

DAILY_QUOTA = TOTAL_TARGET / 31          # ≈ 1935 台/天的首销月日均需求
RATINGS = ('好', '一般', '差')

MAIN_ROOMS = [r for r, _ in ROOM_TARGETS]
B11_COLS = MAIN_ROOMS + [OTHER_LABEL]    # 手环11 口径的列


# ============ 数据读取 ============

_hist_cache = {}


def load_history_index():
    """history.json → {date_str: rec}。"""
    if 'idx' not in _hist_cache:
        if not os.path.exists(HISTORY_FILE):
            sys.exit(f'找不到 {HISTORY_FILE}，请先跑一次 run_all.py sales')
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            _hist_cache['idx'] = {r['date']: r for r in json.load(f)}
    return _hist_cache['idx']


def data_days(daily):
    """已入库（9.7~10.7 且 history 有数据）的日期，升序。"""
    return sorted(d for d in daily if START <= d <= END)


def b11_of(row):
    """当日手环11 台数。

    ⚠️ 不能对 daily[d].values() 直接求和：load_daily() 返回的 dict 里既有
       「我司其他直播间」的**聚合行**、又有被它聚合的**单间**，直接求和会重复计数。
       口径与 generate_band11_target.main() 的「四渠道 + 我司其他直播间」严格一致。
    """
    return sum(row.get(r, 0) for r in B11_COLS)


# ============ 事实汇总 ============

def day_metrics(d, daily, hist):
    """某天的全部事实数字（块头 + 兜底文案都用它）。"""
    ds = d.isoformat()
    rec = hist.get(ds, {})
    days = data_days(daily)
    prev_days = [x for x in days if x < d]
    prev = prev_days[-1] if prev_days else None
    prev_rec = hist.get(prev.isoformat(), {}) if prev else {}

    our = (rec.get('type_summary') or {}).get('我司', {})
    our_orders = our.get('orders', 0)
    our_rev = our.get('revenue', 0.0)
    total_orders = rec.get('total_orders', 0) or 0
    p_our = ((prev_rec.get('type_summary') or {}).get('我司', {}) or {}).get('orders', 0)

    b11 = daily.get(d, {})
    b11_total = b11_of(b11)
    b11_prev = b11_of(daily.get(prev, {})) if prev else 0

    upto = [x for x in days if x <= d]
    cum = sum(b11_of(daily[x]) for x in upto)

    # 分渠道环比，用来写「哪儿涨哪儿跌」
    moves = []
    if prev:
        prev_b11 = daily.get(prev, {})
        for r in B11_COLS:
            cur_n, prev_n = b11.get(r, 0), prev_b11.get(r, 0)
            if cur_n or prev_n:
                moves.append({'room': r, 'now': cur_n, 'prev': prev_n,
                              'delta': cur_n - prev_n,
                              'pct': _dod(cur_n, prev_n)})
        moves.sort(key=lambda m: m['delta'])

    top_room, top_n = max(((r, b11.get(r, 0)) for r in B11_COLS),
                          key=lambda kv: kv[1], default=('—', 0))

    return {
        'date': ds,
        'weekday': '一二三四五六日'[d.weekday()],
        'prev_date': prev.isoformat() if prev else None,
        'our_orders': our_orders, 'our_revenue': our_rev,
        'our_share': our_orders / total_orders if total_orders else 0.0,
        'our_dod': _dod(our_orders, p_our),
        'b11_total': b11_total,
        'b11_dod': _dod(b11_total, b11_prev),
        'b11_vs_quota': b11_total / DAILY_QUOTA if DAILY_QUOTA else 0.0,
        'b11_share_of_our': b11_total / our_orders if our_orders else 0.0,
        'cum': cum,
        'cum_rate': cum / TOTAL_TARGET,
        'time_rate': len(upto) / 31,
        'pace_diff': cum / TOTAL_TARGET - len(upto) / 31,
        'top_room': top_room, 'top_n': top_n,
        'moves': moves,
    }


def _dod(cur, prev):
    """环比。基准为 0 / 缺失时返回 None（不显示 -100% 或 +0% 这种误导值）。"""
    return (cur - prev) / prev if prev else None


def grade(m):
    """好 / 一般 / 差。

    主判据是节奏比（当日台数 ÷ 日均需求），环比做辅助。两个特判：
    - 首销日无环比基准 → 好。
    - **开售次日**：9.7 单日 15,869 台是全月峰值，拿它当环比基准会把正常的
      回落日（9.8，-88%）打成「差」。开售日的长尾不该由次日承担，故跳过环比判据。
    """
    ratio = m['b11_vs_quota']
    if m['b11_dod'] is None:
        return '好'
    dod = 99.0 if m['prev_date'] == START.isoformat() else m['b11_dod']
    if ratio >= 1.00 and dod >= -0.05:
        return '好'
    if ratio >= 0.75 and dod >= -0.30:
        return '一般'
    return '差'


def auto_summary(m):
    """没人工写时的兜底：整体好坏，最多 3 句。只陈述数字，不编造原因。"""
    lines = []
    if m['b11_dod'] is None:
        lines.append(f'首销日 {m["b11_total"]:,} 台，单日完成全月目标的 '
                     f'{m["b11_total"] / TOTAL_TARGET:.1%}。')
    else:
        trend = '涨' if m['b11_dod'] >= 0 else '跌'
        lines.append(
            f'{PRODUCT} {m["b11_total"]:,} 台，环比{trend} {abs(m["b11_dod"]):.1%}，'
            f'达日均需求 {m["b11_vs_quota"]:.2f} 倍。')
    lines.append(f'我司全店 {m["our_orders"]:,} 单 / ¥{m["our_revenue"]:,.0f}，'
                 f'占全店 {m["our_share"]:.1%}。')
    lines.append(f'累计 {m["cum"]:,} / {TOTAL_TARGET:,} = {m["cum_rate"]:.1%}，'
                 f'进度差 {m["pace_diff"]:+.1%}。（⚪ 脚本兜底，待人工补充判断）')
    return '\n'.join(lines)


def auto_handover(m):
    """没人工写时的兜底交接：点出跌得最多和涨得最多的渠道。"""
    moves = [x for x in m['moves'] if x['pct'] is not None]
    if not moves:
        return '（⚪ 脚本兜底）接班后按既定节奏继续，留意当日同时段单量变化。'
    low, high = moves[0], moves[-1]
    return (f'（⚪ 脚本兜底）重点盯 {low["room"]}（{low["prev"]}→{low["now"]} 台，'
            f'{low["pct"]:+.1%}）；{high["room"]} {high["pct"]:+.1%} 势头可延续。')


def make_record(d, daily, hist, written_by='auto'):
    m = day_metrics(d, daily, hist)
    return {
        'date': m['date'],
        'rating': grade(m),
        'written_by': written_by,
        'written_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'summary': auto_summary(m),
        'handover': auto_handover(m),
    }


# ============ Store 读写 ============

def load_store():
    if not os.path.exists(STORE_FILE):
        return {'schema_version': 1, 'updated_at': None, 'reviews': {}}
    try:
        with open(STORE_FILE, 'r', encoding='utf-8') as f:
            s = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f'[!] {STORE_FILE} 读取失败（{e}），本次按空库处理，不覆盖原文件')
        return {'schema_version': 1, 'updated_at': None, 'reviews': {}}
    s.setdefault('reviews', {})
    return s


def save_store(store):
    """原子写：先写 .tmp 再 replace，避免中途失败把整份记录报废。"""
    store['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    os.makedirs(os.path.dirname(STORE_FILE), exist_ok=True)
    tmp = STORE_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, STORE_FILE)


def save_review(d, record, replace=False):
    """只增改 d 这一天，**绝不触碰其他日期**。已存在且未 --replace 时拒绝写入。"""
    store = load_store()
    ds = d.isoformat() if hasattr(d, 'isoformat') else str(d)
    if ds in store['reviews'] and not replace:
        return False, f'{ds} 已有总结（written_by={store["reviews"][ds].get("written_by")}），' \
                      f'要覆盖请加 --replace'
    store['reviews'][ds] = record
    save_store(store)
    return True, f'{ds} 已落库（共 {len(store["reviews"])} 天）'


# ============ CLI ============

def _fmt_pct(v):
    return '—' if v is None else f'{v:+.1%}'


def cmd_status():
    hist = load_history_index()
    hist_latest = max(hist) if hist else None
    store = load_store()
    sum_latest = max(store['reviews']) if store['reviews'] else None
    print(f'history 最新 : {hist_latest}')
    print(f'总结最新     : {sum_latest}')
    days = [d.isoformat() for d in data_days(load_daily())]
    missing = [d for d in days if d not in store['reviews']]
    print(f'待补总结     : {"、".join(missing) if missing else "无 ✔"}')
    if days and hist_latest and days[-1] != hist_latest:
        print(f'⚠ history 末条 {hist_latest} 不在 9.7~10.7 区间内，可能是脏记录')


def cmd_context(date_str=None):
    daily = load_daily()
    hist = load_history_index()
    days = data_days(daily)
    if date_str:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        d = days[-1] if days else None
    if d is None:
        print('还没有已入库的数据')
        return
    if d not in daily:
        print(f'⚠ {d} 在 history.json 里没有数据（9.7~10.7 区间内已入库：{days[0]} ~ {days[-1]}）')
        return
    m = day_metrics(d, daily, hist)
    rec = hist.get(d.isoformat(), {})

    print(f'══ {m["date"]}（周{m["weekday"]}）  脚本评级：{grade(m)}')
    print(f'   手环11 {m["b11_total"]:,} 台，环比 {_fmt_pct(m["b11_dod"])}，'
          f'达日均需求 {m["b11_vs_quota"]:.2f} 倍')
    print(f'   我司全店 {m["our_orders"]:,} 单 / ¥{m["our_revenue"]:,.0f} '
          f'（环比 {_fmt_pct(m["our_dod"])} vs {m["prev_date"]}），占全店 {m["our_share"]:.1%}')
    print(f'   手环11 占我司 {m["b11_share_of_our"]:.1%}')
    print(f'   累计 {m["cum"]:,}/{TOTAL_TARGET:,} = {m["cum_rate"]:.1%}，'
          f'时间进度 {m["time_rate"]:.1%}，进度差 {m["pace_diff"]:+.1%}')

    b11 = daily.get(d, {})
    print('\n── 手环11 分渠道台数（对比前一入库日）' + '─' * 12)
    for room in B11_COLS:
        n = b11.get(room, 0)
        mv = next((x for x in m['moves'] if x['room'] == room), None)
        pct = f'{mv["pct"]:+.1%}' if (mv and mv['pct'] is not None) else '—'
        dlt = f'{mv["delta"]:+}' if mv else ''
        if n or (mv and mv['prev']):
            print(f'   {room:<24} {n:>6,}   {dlt:>7}  {pct:>8}')
    print(f'   {"合计":<24} {m["b11_total"]:>6,}')

    print('\n── 各间订单口径 ' + '─' * 32)
    for name in rec.get('our_rooms', []):
        info = rec.get('rooms', {}).get(name) or {}
        prod = (info.get('products') or {}).get(PRODUCT) or {}
        print(f'   {name:<24} {info.get("orders", 0):>6,} 单  '
              f'¥{info.get("revenue", 0):>12,.0f}  手环11 {int(prod.get("orders", 0)):>5,} 台')

    print('\n── 兜底稿（人工判断请覆盖它）' + '─' * 20)
    print(auto_summary(m))
    print()
    print(auto_handover(m))


def cmd_auto(date_str, force=False):
    daily = load_daily()
    d = datetime.strptime(date_str, '%Y-%m-%d').date()
    _check_range(d)
    if d not in daily:
        sys.exit(f'{date_str} 在 history.json 里没有数据，不能生成（先入库订单）')
    rec = make_record(d, daily, load_history_index())
    ok, msg = save_review(d, rec, replace=force)
    print(('[OK] ' if ok else '[X] ') + msg)


def cmd_add(date_str, replace=False):
    """读 sales_analysis/daily_review_input/<date>.json 落库。

    走文件而不是命令行参数：Windows + Git Bash 下中文 argv 容易被转坏，
    而且稿子用 Write 工具写文件零转义风险。
    """
    d = datetime.strptime(date_str, '%Y-%m-%d').date()
    _check_range(d)
    path = os.path.join(INPUT_DIR, f'{date_str}.json')
    if not os.path.exists(path):
        sys.exit(f'找不到输入稿 {path}\n请先写这个文件，字段见 WORKFLOW.md「每日销售总结」')
    with open(path, 'r', encoding='utf-8') as f:
        draft = json.load(f)

    errs = []
    if not str(draft.get('summary', '')).strip():
        errs.append('summary 不能为空')
    if not str(draft.get('handover', '')).strip():
        errs.append('handover 不能为空')
    if draft.get('rating') and draft['rating'] not in RATINGS:
        errs.append(f'rating 必须是 {RATINGS} 之一，收到 {draft["rating"]!r}')
    n = len([s for s in str(draft.get('summary', '')).split('\n') if s.strip()])
    if n > 4:
        errs.append(f'summary 有 {n} 段，要求 2-3 句（最多 4 段），请精简')
    if errs:
        sys.exit('[X] 校验不过，未写入：\n  - ' + '\n  - '.join(errs))

    rec = make_record(d, daily=load_daily(), hist=load_history_index())
    rec.update({k: v for k, v in draft.items() if k in ('rating', 'summary', 'handover')})
    rec['written_by'] = 'claude'
    if rec.get('rating') not in RATINGS:
        rec['rating'] = grade(day_metrics(d, load_daily(), load_history_index()))
    ok, msg = save_review(d, rec, replace=replace)
    print(('[OK] ' if ok else '[X] ') + msg)
    if ok:
        print(f'     评级 {rec["rating"]}，总结 {n} 段')


def cmd_validate():
    store = load_store()
    revs, ok = store['reviews'], True
    days = [d.isoformat() for d in data_days(load_daily())]
    for ds in sorted(revs):
        r = revs[ds]
        if ds not in days:
            print(f'[!] {ds} 不在已入库日期里')
            ok = False
        if r.get('rating') not in RATINGS:
            print(f'[!] {ds} 评级非法：{r.get("rating")!r}')
            ok = False
        if not str(r.get('summary', '')).strip():
            print(f'[!] {ds} 总结为空')
            ok = False
    missing = [d for d in days if d not in revs]
    if missing:
        print(f'[i] 待补总结：{"、".join(missing)}（会在表里显示为自动兜底，不算错误）')
    print(f'共 {len(revs)} 天总结，校验{"通过 ✔" if ok else "有问题 ✗"}')


def _check_range(d):
    if not (START <= d <= END):
        sys.exit(f'{d} 不在首销月区间 {START} ~ {END} 内')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        return
    cmd = args[0]
    rest = [a for a in args[1:] if not a.startswith('--')]
    flags = {a for a in args[1:] if a.startswith('--')}

    if cmd == 'status':
        cmd_status()
    elif cmd == 'context':
        cmd_context(rest[0] if rest else None)
    elif cmd == 'auto':
        if not rest:
            sys.exit('用法：python band11_review.py auto <YYYY-MM-DD> [--force]')
        cmd_auto(rest[0], force='--force' in flags)
    elif cmd == 'add':
        if not rest:
            sys.exit('用法：python band11_review.py add <YYYY-MM-DD> [--replace]')
        cmd_add(rest[0], replace='--replace' in flags)
    elif cmd == 'validate':
        cmd_validate()
    else:
        sys.exit(f'未知子命令 {cmd!r}，可用：status / context / auto / add / validate')


if __name__ == '__main__':
    main()

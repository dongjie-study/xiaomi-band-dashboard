# -*- coding: utf-8 -*-
"""终端流量分析 · 截图入库脚本（按直播间 × 终端构成）

为什么有这一支：
    平台「终端构成」报表**不能按直播间导出 xlsx**（导出的 6 份文件内容完全一样，是账号级），
    但页面上选「自营 / <直播间>」筛选后得到的表格是**按直播间**的真实数据。
    用户按直播间逐张截图发过来 → 本脚本把「人工转写好的数字」（shots/<日期>.json）
    校验后落盘成 data/YYYY/YYYY-MM-DD.json。

用法：
    python -X utf8 terminal_analysis/ingest_shots.py terminal_analysis/shots/2026-11-01.json
    python -X utf8 terminal_analysis/ingest_shots.py --rebuild-index
    python -X utf8 terminal_analysis/ingest_shots.py --list

shots/<日期>.json 结构（每行 6 个数，顺序固定）：
    { "date": "2026-11-01",
      "sell": "自营",                      # 默认售卖类型（可被单间覆盖）
      "rooms": { "<直播间>": { "<终端>": [曝光, 点击, 曝光→点击率%, 点击→成交率%, 曝光→成交率%, 千次曝光支付元] } } }

    单间售卖类型与默认不同时（平台下拉框是「售卖类型 / 直播间」，如「合作 / 小米官旗手表…」）：
      "rooms": { "小米官旗手表直播间": { "sell": "合作", "terminals": { "<终端>": [...] } } }

铁律：
    1. 数值一律来自截图，本脚本只做「整体 ↔ Σ终端」的一致性校验 + 两个明示为推算的派生指标；
    2. 截图被截断（少行）时，差额落成一行「未显示（截图截断）」，保证 整体 = Σ终端，
       并且该行只填能用差额精确算出的字段，比率/千次支付留空（页面显示 —），绝不猜；
    3. 每天每间各自一份，**绝不把多间相加当全店**（各间是平台按间筛选后的口径）。
"""
import os
import sys
import json
import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')
SHOTS = os.path.join(BASE, 'shots')

TRUNC = '未显示（截图截断）'
MICRO_IMP = 100   # 平台「整体」比可见终端之和少 ≤100 次曝光 → 视为口径微差
MICRO_CLK = 20    # 同上，点击 ≤20 次
TERMINAL_ORDER = ['抖音', '抖音极速版', '抖音商城APP', '红果短剧', '豆包', '其他']

# 2026-11-09 用户：「我看只有一个官方耳机，小米官方耳机直播间！小号的终端流量可以先不考虑！」
# 该间截图里的曝光/成交远小于直播间口径（11-03~11-05 只有 1.7k~4.7k 元 vs 直播间 6.9万~9.5万），
# 判定为小号账号的终端数据 → 入库时跳过，写进日档 excluded_scopes，截图转写原样保留（要恢复就删这一行）。
EXCLUDE_SCOPES = {
    '小米官方耳机直播间': '小号账号；用户 2026-11-09「小号的终端流量先不考虑」',
}

# 指标定义：键 / 中文名 / 类型 / 是否推算
METRICS = [
    ('paid_amount',         '支付金额（推算）',   'money',   True),
    ('paid_orders',         '成交订单（推算）',   'int',     True),
    ('product_impressions', '商品曝光次数',       'int',     False),
    ('product_clicks',      '商品点击次数',       'int',     False),
    ('evr_click',           '商品曝光→点击率',     'rate',    False),
    ('click_cvr',           '商品点击→成交率',     'rate',    False),
    ('evr_order',           '商品曝光→成交率',     'rate',    False),
    ('gpm_1k',              '千次曝光支付金额',   'perunit', False),
]
METRIC_KEYS = [k for k, _, _, _ in METRICS]
METRIC_META = [{'key': k, 'label': lb, 'kind': kd, 'est': es} for k, lb, kd, es in METRICS]


def _row(vals):
    imp, clk, evr_click, click_cvr, evr_order, gpm = vals
    r = {
        'product_impressions': float(imp),
        'product_clicks': float(clk),
        'evr_click': round(float(evr_click) / 100.0, 6),
        'click_cvr': round(float(click_cvr) / 100.0, 6),
        'evr_order': round(float(evr_order) / 100.0, 6),
        'gpm_1k': float(gpm),
    }
    r['paid_amount'] = round(r['gpm_1k'] * r['product_impressions'] / 1000.0, 2)
    r['paid_orders'] = round(r['product_clicks'] * r['click_cvr'], 1)
    return r


def build_day(payload):
    date = payload['date']
    sell = payload.get('sell') or '自营'
    rooms = {k: v for k, v in payload['rooms'].items() if k not in EXCLUDE_SCOPES}
    excluded = [{'scope': k, 'reason': EXCLUDE_SCOPES[k]} for k in payload['rooms'] if k in EXCLUDE_SCOPES]
    scopes = {}
    trunc_report = []
    micro_report = []
    sells = []
    for room, spec in rooms.items():
        if isinstance(spec, dict) and 'terminals' in spec:
            sell = spec.get('sell') or payload.get('sell') or '自营'
            terms = spec['terminals']
        else:
            sell = payload.get('sell') or '自营'
            terms = spec
        sells.append(sell)
        if '整体' not in terms:
            raise SystemExit('❌ %s 缺少「整体」行' % room)
        known = {t: v for t, v in terms.items() if t != '整体'}
        o = terms['整体']
        sum_imp = sum(v[0] for v in known.values())
        sum_clk = sum(v[1] for v in known.values())
        d_imp = round(o[0] - sum_imp)
        d_clk = round(o[1] - sum_clk)
        if d_imp != 0 or d_clk != 0:
            if d_imp < 0 or d_clk < 0:
                # 平台「整体」偶尔比可见终端之和少一丁点（去重/四舍五入），属口径微差、不是转写错。
                # 阈值刻意收得很紧（曝光 ≤100、点击 ≤20），超了仍然报错让人复核。
                if abs(d_imp) <= MICRO_IMP and abs(d_clk) <= MICRO_CLK:
                    micro_report.append((room, d_imp, d_clk))
                    d_imp = d_clk = 0
                else:
                    raise SystemExit('❌ %s 各终端之和大于整体（曝光差 %s / 点击差 %s），转写有误' % (room, d_imp, d_clk))
        if d_imp != 0 or d_clk != 0:
            known[TRUNC] = [d_imp, d_clk,
                            0 if not d_imp else round(d_clk / d_imp * 100, 2),
                            None, None, None]
            trunc_report.append((room, d_imp, d_clk))

        out_terms = {}
        for t, vals in known.items():
            if any(v is None for v in vals):
                r = {
                    'product_impressions': float(vals[0]),
                    'product_clicks': float(vals[1]) if vals[1] is not None else None,
                    'evr_click': (round(vals[1] / vals[0], 6) if vals[0] else None),
                    'click_cvr': None, 'evr_order': None, 'gpm_1k': None,
                    'paid_amount': None, 'paid_orders': None,
                    'truncated': True,
                }
            else:
                r = _row(vals)
            out_terms[t] = {sell: r}
        out_terms['整体'] = {sell: _row(o)}
        order = [t for t in TERMINAL_ORDER if t in out_terms]
        if TRUNC in out_terms:
            order.append(TRUNC)
        out_terms['整体'] = out_terms.pop('整体')
        scopes[room] = {'sell_types': [sell],
                       'terminals': dict([('整体', out_terms['整体'])] + [(t, out_terms[t]) for t in order])}

    day = {
        'date': date,
        'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'scope_mode': 'rooms',
        'sell_types': [s for i, s in enumerate(sells) if s not in sells[:i]],
        'source': payload.get('source') or '截图转写',
        'source_n': len(payload['rooms']),
        'note': payload.get('note') or '',
        'terminal_order': ['整体'] + TERMINAL_ORDER + [TRUNC],
        'metric_keys': METRIC_KEYS,
        'metrics': METRIC_META,
        'scopes': scopes,
        'truncated': payload.get('meta', {}).get('truncated') or {},
        'micro_diff': {room: {'impressions': di, 'clicks': dc} for room, di, dc in micro_report},
    }
    if excluded:
        day['excluded_scopes'] = excluded
    return day, trunc_report, micro_report


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            if f.read() == txt:
                return False
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(txt)
    return True


def all_day_files():
    out = []
    for root, _, files in os.walk(DATA):
        for fn in files:
            if fn.endswith('.json') and fn != 'index.json':
                out.append(os.path.join(root, fn))
    return sorted(out)


def rebuild_index():
    days = []
    months = {}
    scopes = []
    for p in all_day_files():
        with open(p, 'r', encoding='utf-8') as f:
            d = json.load(f)
        if d.get('scope_mode') != 'rooms':
            continue
        date = d['date']
        first = d['scopes'][list(d['scopes'].keys())[0]]
        first_sell = (first.get('sell_types') or d['sell_types'])[0]
        ov = first['terminals']['整体'][first_sell]
        days.append({
            'date': date,
            'pretty': date,
            'scopes': list(d['scopes'].keys()),
            'scope_n': len(d['scopes']),
            'sell': '/'.join(d.get('sell_types') or [first_sell]),
            'paid_amount': ov.get('paid_amount'),
            'product_impressions': ov.get('product_impressions'),
            'paid_orders': ov.get('paid_orders'),
        })
        for s in d['scopes'].keys():
            if s not in scopes:
                scopes.append(s)
        ym = date[:7]
        months.setdefault(ym, []).append(date)
    days.sort(key=lambda x: x['date'])
    ml = []
    for ym in sorted(months.keys()):
        ds = sorted(months[ym], reverse=True)
        ml.append({'ym': ym, 'label': '%d月' % int(ym[5:7]), 'count': len(ds), 'dates': ds})
    idx = {
        'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'months': ml,
        'days': list(reversed(days)),
        'scopes': scopes,
        'metrics': METRIC_META,
        'source': '截图转写（平台「终端构成」按直播间筛选）',
    }
    write_json(os.path.join(DATA, 'index.json'), idx)
    return idx


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    if argv[0] == '--rebuild-index':
        idx = rebuild_index()
        print('✅ 索引重建：%d 天 / %d 个口径' % (len(idx['days']), len(idx['scopes'])))
        return 0
    if argv[0] == '--list':
        for p in all_day_files():
            print(p)
        return 0
    for path in argv:
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        day, trunc, micro = build_day(payload)
        out = os.path.join(DATA, day['date'][:4], day['date'] + '.json')
        changed = write_json(out, day)
        print('%s %s → %s（%d 间 / %d 指标）' % ('✅' if changed else '·', day['date'], os.path.relpath(out, BASE), len(day['scopes']), len(METRIC_KEYS)))
        for room, imp, clk in trunc:
            print('   ⚠️  %s 截图截断：差额行 %s 曝光 %s / 点击 %s（该行比率留空，请补发完整截图）' % (room, TRUNC, imp, clk))
        for room, imp, clk in micro:
            print('   ℹ️  %s 平台整体比可见终端之和少 曝光 %s / 点击 %s（口径微差，保留平台「整体」值，不补行）' % (room, -imp, -clk))
        for room, sc in day['scopes'].items():
            o = sc['terminals']['整体'][sc['sell_types'][0]]
            print('   %-16s [%s] 曝光 %10s  点击 %8s  曝光→点击 %6.2f%%  点击→成交 %6.2f%%  千次支付 ¥%.2f  推算支付 ¥%.2f' % (
                room, sc['sell_types'][0], '{:,.0f}'.format(o['product_impressions']), '{:,.0f}'.format(o['product_clicks']),
                o['evr_click'] * 100, o['click_cvr'] * 100, o['gpm_1k'], o['paid_amount']))
    idx = rebuild_index()
    print('✅ 索引：%d 天 / 口径 %s' % (len(idx['days']), idx['scopes']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))

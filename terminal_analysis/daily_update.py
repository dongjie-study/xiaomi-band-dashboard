# -*- coding: utf-8 -*-
"""终端流量分析 · 入库脚本（「流量-终端构成」表）

用法：
    python -X utf8 terminal_analysis/daily_update.py <文件或文件夹...>
    python -X utf8 terminal_analysis/daily_update.py --rebuild-only   # 只重建索引
    python -X utf8 terminal_analysis/daily_update.py --check          # 体检产物
    python -X utf8 terminal_analysis/daily_update.py --view           # 入库后打印摘要

产物：
    terminal_analysis/data/YYYY/YYYY-MM-DD.json   每天一份
    terminal_analysis/data/index.json             索引（月份 / 日期 / 口径）

数值一律取自源表，不做二次换算；跨口径「合计」的加总/比率重算在本脚本内完成，页面只读不重算。

⚠️ 口径说明（2026-11-05 实测）：平台导出的「流量-终端构成」是**账号级（全店）**口径，
   6 份按直播间命名的文件内容完全一致（仅文件元数据不同）→ 入库时按内容指纹去重，
   归为单一「店铺整体」口径，**绝不重复相加**。若以后导出能按直播间过滤，脚本会自动改回逐间模式。
"""
import os
import re
import sys
import json
import glob
import zipfile
import datetime
import xml.etree.ElementTree as ET

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
ACCOUNT_SCOPE = '店铺整体'
ACCOUNT_NOTE = '平台导出为账号级（全店）终端构成，各直播间文件内容一致，已按内容指纹去重后入库'

# ---------- 口径定义：键 / 源表列名 / 类型 ----------
# kind: money 金额(可加总) / int 次数(可加总) / rate 比率 / perunit 单价型(不可加总，按公式重算)
FIELDS = [
    ('paid_amount',        '用户支付金额',                       'money'),
    ('gmv',                '成交金额',                           'money'),
    ('product_impressions','商品曝光次数',                       'int'),
    ('product_clicks',     '商品点击次数',                       'int'),
    ('paid_orders',        '成交订单数',                         'int'),
    ('paid_items',         '成交件数',                           'int'),
    ('evr_click',          '商品曝光-点击转化率（次数）',          'rate'),
    ('click_cvr',          '商品点击-成交转化率（次数）',          'rate'),
    ('evr_order',          '商品曝光-成交转化率（次数）',          'rate'),
    ('gpm_1k',             '千次曝光用户支付金额',                'perunit'),
    ('unit_price',         '件单价',                             'perunit'),
    ('coupon',             '智能优惠券金额',                     'money'),
    ('platform_subsidy',   '平台补贴金额',                       'money'),
    ('talent_subsidy',     '达人补贴金额',                       'money'),
    ('settle',             '结算金额',                           'money'),
    ('settle_7d',          '7日结算金额',                        'money'),
    ('settle_14d',         '14日结算金额',                       'money'),
    ('presale',            '预售定金',                           'money'),
    ('refund_amount',      '退款金额（支付时间）',                'money'),
    ('refund_orders',      '退款订单数（支付时间）',              'int'),
    ('refund_rate',        '退款率（支付时间）',                  'rate'),
    ('hour_refund_amount', '1小时成交退款金额（支付时间）',        'money'),
    ('hour_refund_orders', '1小时退款订单数（支付时间）',          'int'),
    ('hour_refund_rate',   '1小时退款率（支付时间）',              'rate'),
    ('ship_paid',          '发货用户支付金额（发货时间）',        'money'),
    ('net_paid',           '退款后用户支付金额（支付时间）',      'money'),
]
FIELD_KIND = {k: kind for k, _, kind in FIELDS}
FIELD_LABEL = {k: label for k, label, _ in FIELDS}
METRIC_KEYS = [k for k, _, _ in FIELDS]
SUM_KEYS = [k for k in METRIC_KEYS if FIELD_KIND[k] in ('money', 'int')]

# 比率/单价型：跨口径合计时必须按公式重算（不能相加）
DERIVED = {
    'evr_click':        lambda r: _div(r.get('product_clicks'), r.get('product_impressions'), 1),
    'click_cvr':        lambda r: _div(r.get('paid_orders'), r.get('product_clicks'), 1),
    'evr_order':        lambda r: _div(r.get('paid_orders'), r.get('product_impressions'), 1),
    'gpm_1k':           lambda r: _div(r.get('paid_amount'), r.get('product_impressions'), 1000),
    'unit_price':       lambda r: _div(r.get('paid_amount'), r.get('paid_items'), 1),
}
# 这两个比率平台的算法与「退款订单数/成交订单数」不一致（实测 0.55 vs 0.27），
# 不做重算、也不可加总；跨口径合计时置空（页面显示 —），单口径一律用源表值。
NON_AGG = ('refund_rate', 'hour_refund_rate')


def _div(a, b, scale):
    a = a or 0
    b = b or 0
    if not b:
        return None
    return round(a / b * scale, 8 if scale == 1 else 2)


# ---------- 直播间名单（与流量分析保持一致的在营 7 间） ----------
CANON_ROOMS = [
    '小米官方手环直播间',
    '小米官方手表',
    '小米数码旗舰店',
    '小米官旗手表直播间',
    '小米官方耳机直播间',
    '小米智能设备旗舰店直播间',
    '小米耳机直播间',
]
TERMINAL_BASE_ORDER = ['整体', '抖音', '抖音极速版', '抖音商城APP', '红果短剧', '豆包', '其他']
SELL_ORDER = ['全部', '自营', '合作']


def _norm(s):
    return re.sub(r'[\s\-_—·（）()【】\[\]「」]', '', str(s or ''))


def resolve_room(stem):
    raw = stem
    name = raw
    for pat in [r'流量-终端构成$', r'流量终端构成$', r'-终端构成$', r'终端构成$', r'流量构成$']:
        name = re.sub(pat, '', name).strip()
    name = re.sub(r'\d{1,2}[\.月]\d{1,2}\s*日?$', '', name).strip()
    if name in CANON_ROOMS:
        return name, '精确匹配'
    n = _norm(name)
    for r in CANON_ROOMS:
        if _norm(r) == n:
            return r, '归一化匹配'
    cand = [r for r in CANON_ROOMS if _norm(r) in n or n in _norm(r)]
    if len(cand) == 1:
        return cand[0], '相互包含'
    return name, '未在名单（按原名记录）'


# ---------- xlsx 读取（不依赖 openpyxl，兼容 Go/Excelize 的 inlineStr） ----------
def _col_idx(ref):
    m = re.match(r'([A-Z]+)', ref or '')
    if not m:
        return 0
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx_rows(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    shared = []
    if 'xl/sharedStrings.xml' in names:
        st = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in st.iter(NS + 'si'):
            shared.append(''.join(t.text or '' for t in si.iter(NS + 't')))
    sheets = sorted(n for n in names if re.match(r'xl/worksheets/sheet\d+\.xml$', n))
    if not sheets:
        raise SystemExit('❌ %s 里没有 worksheet' % path)
    best = None
    for sh in sheets:
        root = ET.fromstring(z.read(sh))
        rows = []
        for row in root.iter(NS + 'row'):
            cells = {}
            for c in row.iter(NS + 'c'):
                t = c.get('t')
                v = c.find(NS + 'v')
                isel = c.find(NS + 'is')
                if t == 's' and v is not None:
                    val = shared[int(v.text)] if int(v.text) < len(shared) else ''
                elif t == 'inlineStr' and isel is not None:
                    val = ''.join(x.text or '' for x in isel.iter(NS + 't'))
                elif v is not None:
                    val = v.text
                else:
                    val = ''
                cells[_col_idx(c.get('r'))] = (val or '').strip()
            if cells:
                rows.append([cells.get(i, '') for i in range(max(cells) + 1)])
        if best is None or len(rows) > len(best):
            best = rows
    return best or []


def parse_date(v):
    s = str(v or '').strip()
    m = re.match(r'^(\d{4})[-/\.]?(\d{1,2})[-/\.]?(\d{1,2})', s)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError:
        return None


def parse_workbook(path):
    rows = read_xlsx_rows(path)
    if not rows:
        raise SystemExit('❌ %s 是空表' % path)
    hdr = [str(c).strip() for c in rows[0]]
    idx = {}
    for key, col, _kind in FIELDS:
        if col not in hdr:
            raise SystemExit('❌ %s 缺少列「%s」' % (os.path.basename(path), col))
        idx[key] = hdr.index(col)
    i_date = hdr.index('日期') if '日期' in hdr else 0
    i_term = hdr.index('终端类型') if '终端类型' in hdr else 1
    i_sell = hdr.index('售卖类型') if '售卖类型' in hdr else 2
    out = {}
    for r in rows[1:]:
        if len(r) <= max(i_date, i_term, i_sell):
            continue
        d = parse_date(r[i_date])
        term = str(r[i_term]).strip()
        sell = str(r[i_sell]).strip()
        if not d or not term or not sell:
            continue
        rec = {}
        for key, _col, kind in FIELDS:
            raw = r[idx[key]] if idx[key] < len(r) else ''
            try:
                val = float(str(raw).replace(',', ''))
            except (TypeError, ValueError):
                val = None
            if val is None:
                rec[key] = None
            elif kind == 'int':
                rec[key] = int(round(val))
            elif kind in ('rate',):
                rec[key] = round(val, 8)
            else:
                rec[key] = round(val, 2)
        out.setdefault(d, {})[(term, sell)] = rec
    return out


def fingerprint(records):
    """一天内容的指纹：用于识别「多份文件其实是同一口径」的重复导出。"""
    items = sorted((t, s, json.dumps(rec, sort_keys=True)) for (t, s), rec in records.items())
    return json.dumps(items, ensure_ascii=False)


def aggregate(datasets):
    """datasets: [records...] → 合计口径（加总 + 比率重算）"""
    agg = {}
    for records in datasets:
        for (term, sell), rec in records.items():
            bucket = agg.setdefault(term, {}).setdefault(sell, {k: None for k in METRIC_KEYS})
            for k in SUM_KEYS:
                v = rec.get(k)
                if v is None:
                    continue
                bucket[k] = round((bucket.get(k) or 0) + v, 2)
    for term, sells in agg.items():
        for sell, rec in sells.items():
            for k, fn in DERIVED.items():
                rec[k] = fn(rec)
            for k in NON_AGG:
                rec[k] = None
    return agg


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            if f.read() == txt:
                return False
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(txt)
    return True


def rebuild_index():
    days = []
    for path in sorted(glob.glob(os.path.join(DATA, '*', '*.json'))):
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        scopes = d.get('scopes') or {}
        main = next(iter(scopes.values()), {})
        tot = (main.get('terminals') or {}).get('整体', {}).get('全部', {})
        days.append({
            'date': d['date'],
            'pretty': '%d月%d日' % (int(d['date'][5:7]), int(d['date'][8:10])),
            'scopes': list(scopes.keys()),
            'scope_mode': d.get('scope_mode'),
            'source_n': len(d.get('source_files') or []),
            'paid_amount': tot.get('paid_amount'),
            'product_impressions': tot.get('product_impressions'),
            'paid_orders': tot.get('paid_orders'),
        })
    days.sort(key=lambda x: x['date'])
    months = {}
    for d in days:
        ym = d['date'][:7]
        m = months.setdefault(ym, {'ym': ym, 'label': '%d月' % int(ym[5:7]), 'count': 0, 'dates': []})
        m['count'] += 1
        m['dates'].append(d['date'])
    for m in months.values():
        m['dates'].sort(reverse=True)
    index = {
        'months': [months[k] for k in sorted(months, reverse=True)],
        'days': days,
        'scopes': days[-1]['scopes'] if days else [ACCOUNT_SCOPE],
        'metrics': [{'key': k, 'label': FIELD_LABEL[k], 'kind': FIELD_KIND[k]} for k in METRIC_KEYS],
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    write_json(os.path.join(DATA, 'index.json'), index)
    return days


def verify_day(date):
    path = os.path.join(DATA, date[:4], date + '.json')
    if not os.path.exists(path):
        print('❌ 缺日档 %s' % path)
        return 1
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    bad = 0
    print('[1] 日档 %s 口径=%s，%d 个口径，终端顺序 %s' % (
        date, d.get('scope_mode'), len(d.get('scopes') or {}), d.get('terminal_order')))
    for scope, sd in (d.get('scopes') or {}).items():
        terms = sd.get('terminals') or {}
        if '整体' not in terms:
            print('   ❌ %s 缺「整体」行' % scope)
            bad += 1
            continue
        tot = terms['整体']['全部']
        diffs = []
        # 整体 == 各终端相加（全部）
        s = {}
        for t, sells in terms.items():
            if t == '整体':
                continue
            for k in SUM_KEYS:
                s[k] = (s.get(k) or 0) + (sells['全部'].get(k) or 0)
        for k in ('paid_amount', 'gmv', 'product_impressions', 'product_clicks', 'paid_orders'):
            a, b = tot.get(k) or 0, s.get(k) or 0
            if abs(a - b) > max(2.0, abs(a) * 0.002):
                diffs.append('%s 整体%.2f≠终端和%.2f' % (k, a, b))
        # 全部 == 自营 + 合作
        for t, sells in terms.items():
            for k in SUM_KEYS:
                a = sells['全部'].get(k) or 0
                b = (sells['自营'].get(k) or 0) + (sells['合作'].get(k) or 0)
                if abs(a - b) > max(2.0, abs(a) * 0.002):
                    diffs.append('%s/%s 全部%.2f≠自营+合作%.2f' % (t, k, a, b))
        print('   %-10s 支付 %13.2f 成交 %13.2f 曝光 %9d 点击 %7d 订单 %6d %s' % (
            scope, tot.get('paid_amount') or 0, tot.get('gmv') or 0,
            tot.get('product_impressions') or 0, tot.get('product_clicks') or 0,
            tot.get('paid_orders') or 0, '✅' if not diffs else '⚠️ ' + '; '.join(diffs[:3])))
        bad += len(diffs)
    with open(os.path.join(DATA, 'index.json'), encoding='utf-8') as f:
        ix = json.load(f)
    print('[2] 索引：%d 天（%s ~ %s），月份 %s' % (
        len(ix['days']), ix['days'][0]['date'] if ix['days'] else '-',
        ix['days'][-1]['date'] if ix['days'] else '-',
        [(m['ym'], m['count']) for m in ix['months']]))
    return 0 if bad == 0 else 1


def ingest(paths):
    # 收集：date → [ (room, records) ]
    per_date = {}
    for p in paths:
        files = sorted(glob.glob(os.path.join(p, '*.xlsx'))) if os.path.isdir(p) else [p]
        for f in files:
            if not f.lower().endswith(('.xlsx', '.xlsm')):
                continue
            stem = os.path.splitext(os.path.basename(f))[0]
            room, why = resolve_room(stem)
            books = parse_workbook(f)
            if not books:
                print('⚠️ 跳过（没解析出数据）：%s' % os.path.basename(f))
                continue
            print('  %-44s → %-16s %-8s 日期 %s' % (os.path.basename(f)[:44], room, why, ', '.join(sorted(books))))
            for d, recs in books.items():
                per_date.setdefault(d, []).append((room, os.path.basename(f), recs))
    if not per_date:
        raise SystemExit('❌ 没有解析出任何数据')

    dates = sorted(per_date)
    for d in dates:
        entries = per_date[d]
        # 按内容指纹分组：不同指纹 = 不同口径；同指纹 = 同一份数据的重复导出
        groups = {}
        for room, fname, recs in entries:
            fp = fingerprint(recs)
            g = groups.setdefault(fp, {'records': recs, 'files': [], 'rooms': []})
            g['files'].append(fname)
            if room not in g['rooms']:
                g['rooms'].append(room)
        glist = list(groups.values())
        scope_mode = 'account' if len(glist) == 1 and len(glist[0]['files']) > 1 else (
            'account' if len(glist) == 1 else 'rooms')
        if scope_mode == 'account':
            scopes = {ACCOUNT_SCOPE: {'terminals': normalize_terminals(glist[0]['records'])}}
            sources = glist[0]['files']
        else:
            scopes = {}
            for g in glist:
                name = g['rooms'][0] if g['rooms'] else ACCOUNT_SCOPE
                scopes[name] = {'terminals': normalize_terminals(g['records'])}
            if len(scopes) > 1:
                scopes['合计'] = {'terminals': aggregate([g['records'] for g in glist])}
            sources = sorted(f for g in glist for f in g['files'])
        order = []
        for g in glist:
            for t, _s in g['records'].keys():
                if t not in order:
                    order.append(t)
        order = [t for t in TERMINAL_BASE_ORDER if t in order] + [t for t in order if t not in TERMINAL_BASE_ORDER]
        obj = {
            'date': d,
            'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'scope_mode': scope_mode,
            'source_files': sources,
            'source_n': len(entries),
            'terminal_order': order,
            'sell_order': SELL_ORDER,
            'metric_keys': METRIC_KEYS,
            'scopes': scopes,
        }
        if scope_mode == 'account':
            obj['note'] = ACCOUNT_NOTE
            obj['duplicate_files'] = len(sources)
        changed = write_json(os.path.join(DATA, d[:4], d + '.json'), obj)
        print('  → %s %s（口径 %s，%d 个）' % (d, '已写入' if changed else '无变化（同字节幂等）', scope_mode, len(scopes)))
    return dates


def normalize_terminals(records):
    """补齐缺失的 终端×售卖类型 组合，保证前端结构完整。"""
    terms = {}
    for (t, s), rec in records.items():
        terms.setdefault(t, {})[s] = rec
    for t in terms:
        for s in SELL_ORDER:
            terms[t].setdefault(s, {k: None for k in METRIC_KEYS})
    return terms


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('-')]
    flags = set(a for a in argv[1:] if a.startswith('-'))
    if '--check' in flags or '-c' in flags:
        paths = sorted(glob.glob(os.path.join(DATA, '*', '*.json')))
        dates = sorted(os.path.basename(p)[:-5] for p in paths)
        if not dates:
            print('（还没有任何终端数据）')
            return 0
        rc = 0
        for d in dates:
            rc |= verify_day(d)
        return rc
    if '--rebuild-only' in flags or '-r' in flags:
        days = rebuild_index()
        print('✅ 索引重建完成：%d 天' % len(days))
        return 0
    if not args:
        home = os.path.join(os.path.expanduser('~'), 'Desktop')
        args = sorted(glob.glob(os.path.join(home, '*终端构成*.xlsx'))
                      + glob.glob(os.path.join(home, 'Downloads', '*终端构成*.xlsx')))
        if not args:
            print('❌ 没找到「终端构成」表：请把文件路径作为参数传进来，或放到桌面（文件名含「终端构成」）')
            return 1
        print('自动找到 %d 份表' % len(args))
    print('入库：共 %d 个输入' % len(args))
    dates = ingest(args)
    days = rebuild_index()
    print('✅ 入库完成：本次 %d 天（%s），索引共 %d 天' % (len(dates), ', '.join(dates), len(days)))
    rc = 0
    for d in dates:
        rc |= verify_day(d)
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv))

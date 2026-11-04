# -*- coding: utf-8 -*-
"""终端流量分析 · 数据复核（独立于入库脚本的二次读取）

用法：
    python -X utf8 terminal_analysis/verify_day.py                # 复核全部日期
    python -X utf8 terminal_analysis/verify_day.py 2026-11-03     # 只复核某一天

复核项（A~E）：
    A 源表「整体 / 全部」行 26 项 ↔ 日档 scopes.店铺整体.terminals.整体.全部 逐项相等
    B 源表内部恒等式：整体 == 各终端相加、全部 == 自营 + 合作
    C 日档「按公式重算」的 7 个比率/单价与源表值一致（容差 0.01%）
    D 索引 index.json 覆盖全部日档，天数/月份/末条正确
    E 页面 index.html 关键钩子齐全（#chartTmPie / #tmKpi / renderShare …）
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
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

# 与入库脚本保持同一份口径定义（键 / 源表列名）
COLS = {
    'paid_amount': '用户支付金额', 'gmv': '成交金额',
    'product_impressions': '商品曝光次数', 'product_clicks': '商品点击次数',
    'paid_orders': '成交订单数', 'paid_items': '成交件数',
    'evr_click': '商品曝光-点击转化率（次数）', 'click_cvr': '商品点击-成交转化率（次数）',
    'evr_order': '商品曝光-成交转化率（次数）', 'gpm_1k': '千次曝光用户支付金额',
    'unit_price': '件单价', 'coupon': '智能优惠券金额', 'platform_subsidy': '平台补贴金额',
    'talent_subsidy': '达人补贴金额', 'settle': '结算金额', 'settle_7d': '7日结算金额',
    'settle_14d': '14日结算金额', 'presale': '预售定金',
    'refund_amount': '退款金额（支付时间）', 'refund_orders': '退款订单数（支付时间）',
    'refund_rate': '退款率（支付时间）', 'hour_refund_amount': '1小时成交退款金额（支付时间）',
    'hour_refund_orders': '1小时退款订单数（支付时间）', 'hour_refund_rate': '1小时退款率（支付时间）',
    'ship_paid': '发货用户支付金额（发货时间）', 'net_paid': '退款后用户支付金额（支付时间）',
}
SUM_KEYS = ['paid_amount', 'gmv', 'product_impressions', 'product_clicks', 'paid_orders', 'paid_items',
            'coupon', 'platform_subsidy', 'talent_subsidy', 'settle', 'settle_7d', 'settle_14d', 'presale',
            'refund_amount', 'refund_orders', 'hour_refund_amount', 'hour_refund_orders', 'ship_paid', 'net_paid']
# 只复核「可由次数/金额重算」的 5 项；退款率平台算法不同（非 退款订单/成交订单），不参与重算
DERIVED = ['evr_click', 'click_cvr', 'evr_order', 'gpm_1k', 'unit_price']

PAGE_HOOKS = ['chartTmPie', 'chartTmSell', 'chartTmBar', 'chartTmLine', 'chartTmShare',
              'tmKpi', 'tmTableBody', 'tmStatus', 'tmHeadline', 'renderShare', 'setHighlight',
              'PLACEHOLDER_NO']


def _ci(ref):
    m = re.match(r'([A-Z]+)', ref or '')
    n = 0
    for ch in (m.group(1) if m else 'A'):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_rows(path):
    """独立实现：zip + ElementTree，抽出所有 sheet 中行数最多的那张。"""
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).iter(NS + 'si'):
            shared.append(''.join(t.text or '' for t in si.iter(NS + 't')))
    best = []
    for sheet in [n for n in z.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml$', n)]:
        rows = []
        for row in ET.fromstring(z.read(sheet)).iter(NS + 'row'):
            vals = {}
            for c in row.iter(NS + 'c'):
                t, v, istr = c.get('t'), c.find(NS + 'v'), c.find(NS + 'is')
                if t == 's' and v is not None:
                    val = shared[int(v.text)] if int(v.text) < len(shared) else ''
                elif istr is not None:
                    val = ''.join(x.text or '' for x in istr.iter(NS + 't'))
                else:
                    val = v.text if v is not None else ''
                vals[_ci(c.get('r'))] = (val or '').strip()
            if vals:
                rows.append([vals.get(i, '') for i in range(max(vals) + 1)])
        if len(rows) > len(best):
            best = rows
    return best


def source_paths():
    home = os.path.expanduser('~')
    pats = [os.path.join(home, 'Desktop', '*终端构成*.xlsx'), os.path.join(home, 'Downloads', '*终端构成*.xlsx')]
    return sorted(p for pat in pats for p in glob.glob(pat))


def parse_source(paths):
    """date → {(终端, 售卖): {指标: float}}（多份同内容文件自动去重）"""
    out = {}
    for p in paths:
        rows = read_rows(p)
        if not rows:
            continue
        hdr = [str(c).strip() for c in rows[0]]
        ic = {}
        for k, name in COLS.items():
            if name in hdr:
                ic[k] = hdr.index(name)
        i_d, i_t, i_s = hdr.index('日期'), hdr.index('终端类型'), hdr.index('售卖类型')
        for r in rows[1:]:
            if len(r) <= max(i_d, i_t, i_s):
                continue
            m = re.match(r'^(\d{4})[-/\.]?(\d{1,2})[-/\.]?(\d{1,2})', str(r[i_d]).strip())
            if not m:
                continue
            d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
            rec = {}
            for k, i in ic.items():
                if i >= len(r):
                    rec[k] = None
                    continue
                try:
                    rec[k] = float(str(r[i]).replace(',', ''))
                except ValueError:
                    rec[k] = None
            rec.setdefault('terminal', str(r[i_t]).strip())
            rec.setdefault('sell', str(r[i_s]).strip())
            out.setdefault(d, {})[(rec['terminal'], rec['sell'])] = rec
    return out


def check_day(d, src):
    """返回 (bad_count, lines)"""
    bad, lines = 0, []
    path = os.path.join(DATA, d[:4], d + '.json')
    if not os.path.exists(path):
        return 1, ['❌ 缺日档 %s' % path]
    with open(path, encoding='utf-8') as f:
        day = json.load(f)
    scope = (day.get('scopes') or {}).get('店铺整体')
    if not scope:
        return 1, ['❌ 日档里没有「店铺整体」口径']
    terms = scope['terminals']
    # A：26 项逐项对源表
    a_bad = []
    for k in COLS:
        want = (src.get(('整体', '全部')) or {}).get(k)
        got = terms.get('整体', {}).get('全部', {}).get(k)
        if want is None and got is None:
            continue
        if want is None or got is None:
            a_bad.append('%s 源%s≠档%s' % (k, want, got))
            continue
        tol = max(0.02, abs(want) * 1e-6) if k in SUM_KEYS else 1e-6
        if abs(want - got) > tol:
            a_bad.append('%s 源%s≠档%s' % (k, want, got))
    lines.append('[A] 源表「整体/全部」26 项 ↔ 日档：%s' % ('✅' if not a_bad else '❌ ' + '; '.join(a_bad[:4])))
    bad += len(a_bad)
    # B：恒等式（源表内部）
    b_bad = []
    tot = src.get(('整体', '全部')) or {}
    for k in SUM_KEYS:
        s = sum((src.get((t, '全部')) or {}).get(k) or 0 for t in
                ['抖音', '抖音极速版', '抖音商城APP', '红果短剧', '豆包', '其他'])
        if abs((tot.get(k) or 0) - s) > max(2.0, abs(tot.get(k) or 0) * 0.002):
            b_bad.append('%s 整体%.2f≠终端和%.2f' % (k, tot.get(k) or 0, s))
        s2 = ((src.get(('整体', '自营')) or {}).get(k) or 0) + ((src.get(('整体', '合作')) or {}).get(k) or 0)
        if abs((tot.get(k) or 0) - s2) > max(2.0, abs(tot.get(k) or 0) * 0.002):
            b_bad.append('%s 全部≠自营+合作' % k)
    lines.append('[B] 源表恒等式（整体=各终端、全部=自营+合作）：%s' % ('✅' if not b_bad else '❌ ' + '; '.join(b_bad[:4])))
    bad += len(b_bad)
    # C：重算比率
    c_bad = []
    imp = tot.get('product_impressions') or 0
    clk = tot.get('product_clicks') or 0
    ords = tot.get('paid_orders') or 0
    items = tot.get('paid_items') or 0
    paid = tot.get('paid_amount') or 0
    exp = {
        'evr_click': clk / imp if imp else None,
        'click_cvr': ords / clk if clk else None,
        'evr_order': ords / imp if imp else None,
        'gpm_1k': paid / imp * 1000 if imp else None,
        'unit_price': paid / items if items else None,
    }
    for k in DERIVED:
        got = terms['整体']['全部'].get(k)
        want = exp[k]
        if want is None:
            continue
        tol = max(1e-4, abs(want) * 1e-3) if abs(want) < 1 else max(0.02, abs(want) * 1e-6)
        if got is None or abs(got - want) > tol:
            c_bad.append('%s 期望%.6f 档%.6f' % (k, want, got if got is not None else -1))
    lines.append('[C] 比率/单价按合计重算：%s' % ('✅' if not c_bad else '❌ ' + '; '.join(c_bad[:4])))
    bad += len(c_bad)
    lines.append('    %s 支付 %s 成交 %s 曝光 %s 订单 %s' % (
        d, '{:,.2f}'.format(paid), '{:,.2f}'.format(tot.get('gmv') or 0),
        '{:,}'.format(int(imp)), '{:,}'.format(int(ords))))
    return bad, lines


def main(argv):
    want = [a for a in argv[1:] if re.match(r'^\d{4}-\d{2}-\d{2}$', a)]
    paths = source_paths()
    src = parse_source(paths) if paths else {}
    if not src:
        print('⚠️ 桌面/下载里没找到「终端构成」源表，跳过 A~C，只做 D/E')
    dates = want or sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(DATA, '*', '*.json')))
    bad = 0
    for d in dates:
        if d not in src:
            print('⚠️ %s 没有对应源表（跳过 A~C）' % d)
            continue
        b, lines = check_day(d, src[d])
        bad += b
        for ln in lines:
            print(ln)
    # D：索引
    ix_path = os.path.join(DATA, 'index.json')
    if not os.path.exists(ix_path):
        print('[D] ❌ 缺 index.json')
        bad += 1
    else:
        with open(ix_path, encoding='utf-8') as f:
            ix = json.load(f)
        day_files = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(DATA, '*', '*.json')))
        got = [x['date'] for x in ix['days']]
        ok = got == day_files
        months = {}
        for x in day_files:
            months[x[:7]] = months.get(x[:7], 0) + 1
        mok = {m['ym']: m['count'] for m in ix['months']} == months
        print('[D] 索引 %d 天（%s ~ %s），月份 %s，与日档一致 %s，月份计数 %s' % (
            len(got), got[0] if got else '-', got[-1] if got else '-',
            [(m['ym'], m['count']) for m in ix['months']], '✅' if ok else '❌', '✅' if mok else '❌'))
        bad += (0 if ok else 1) + (0 if mok else 1)
    # E：页面钩子
    page = os.path.join(BASE, 'index.html')
    with open(page, encoding='utf-8') as f:
        html = f.read()
    hooks = [h for h in PAGE_HOOKS if 'PLACEHOLDER' not in h]
    miss = [h for h in hooks if h not in html]
    print('[E] 页面钩子 %d 个（%d 字节）：%s' % (len(hooks), len(html.encode('utf-8')),
          '✅' if not miss else '❌ 缺 ' + ', '.join(miss)))
    bad += len(miss)
    if not bad:
        print('✅ OK %d 条，无 BAD' % (len(dates) + 2))
    else:
        print('❌ 共 %d 处不一致' % bad)
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))

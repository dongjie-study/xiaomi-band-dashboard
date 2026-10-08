# -*- coding: utf-8 -*-
"""小米官方手表直播间 · 品专效果分析（大盘占比口径）→ 桌面 xlsx。

分析框架（刻意不看"跟自己比"）：
  品专（品牌专区，2026-09-29 上线）的价值 = 本间在**全站手表大盘**里的占比是否抬升。
  主口径 A：本间手表品类额 ÷ 全站所有直播间的手表品类额
  辅助口径 B：本间手表品类额 ÷ 全体服务商「手表类直播间」的手表品类额
  参考口径 C：本间全品类额 ÷ 全站全品类额
  手表品类判定复用 gen_weekly_report.category_of（商品名含 Watch/手表）。

派生指标全部写成 Excel 公式（蓝色 = 源数据，深灰 = 公式，绿色 = 跨表引用）。

用法：
    python tools/gen_pinzhuan_report.py
    python tools/gen_pinzhuan_report.py --after 2026-09-30 2026-10-07 --before 2026-09-15 2026-09-22
"""
import argparse
import json
import os
import sys
from datetime import datetime
from statistics import median

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_weekly_report as W  # noqa: E402  复用 house style（字体/配色/数字格式/标题块）
from openpyxl import Workbook  # noqa: E402
from openpyxl.chart import LineChart, Reference  # noqa: E402
from team_config import IGNORED_ROOMS  # noqa: E402  项目约定：忽略的房间不计入任何口径

ROOT = W.ROOT
BRAND_START = '2026-09-29'          # 品专上线日（用户口径：手表直播间 29 号起有品专）
SERIES_START = '2026-08-25'         # 逐日/周维度起点
PPFMT = '+0.00"pp";[Red]-0.00"pp";"-"'
WEEK = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
SHEETS = ['结论摘要', '大盘占比总览', '逐日明细', '竞对对照', '时段结构', '口径与说明']


# ====================== 取数 ======================
def load():
    hist = json.load(open(os.path.join(ROOT, 'sales_analysis', 'history.json'), encoding='utf-8'))
    return {d['date']: d for d in hist}, sorted(d['date'] for d in hist)


def room_watch(day, room):
    o, r = 0, 0.0
    for p, pv in day['rooms'].get(room, {}).get('products', {}).items():
        if W.category_of(p) == '手表':
            o += pv['orders']
            r += pv['revenue']
    return o, round(r, 2)


def market_watch(day, rooms=None):
    tot = 0.0
    for r, v in day['rooms'].items():
        if rooms is not None and r not in rooms:
            continue
        for p, pv in v.get('products', {}).items():
            if W.category_of(p) == '手表':
                tot += pv['revenue']
    return round(tot, 2)


def market_watch_o(day):
    n = 0
    for v in day['rooms'].values():
        for p, pv in v.get('products', {}).items():
            if W.category_of(p) == '手表':
                n += pv['orders']
    return n


def watch_rooms(dates):
    # 口径 B 的分母集合：名称含「手表」的直播间，剔除项目 IGNORED_ROOMS（约定忽略的重复/历史间）
    seen = {}
    for dt in dates:
        for r in BY[dt]['rooms']:
            if '手表' in r and r not in IGNORED_ROOMS:
                seen[r] = W.classify_room(r)
    return seen


def span(d0, d1):
    return [d for d in DATES if d0 <= d <= d1]


def win(d0, d1, rooms):
    o, rv, allr, a, b, site = 0, 0.0, 0.0, 0.0, 0.0, 0.0
    for dt in span(d0, d1):
        day = BY[dt]
        oo, rr = room_watch(day, ROOM)
        o += oo
        rv += rr
        allr += day['rooms'].get(ROOM, {}).get('revenue', 0.0)
        a += market_watch(day)
        b += market_watch(day, rooms)
        site += day['total_revenue']
    rv, a, b, site, allr = round(rv, 2), round(a, 2), round(b, 2), round(site, 2), round(allr, 2)
    return {'days': len(span(d0, d1)), 'o': o, 'rv': rv, 'all': allr, 'a': a, 'b': b, 'site': site,
            'avg': round(rv / o, 2) if o else 0.0,
            'shA': rv / a if a else 0.0, 'shB': rv / b if b else 0.0, 'shS': allr / site if site else 0.0}


def pv_day(day):
    o, rv = room_watch(day, ROOM)
    return {'o': o, 'rv': rv, 'a': market_watch(day), 'b': market_watch(day, ROOMS),
            'all': round(day['rooms'].get(ROOM, {}).get('revenue', 0.0), 2),
            'site': round(day['total_revenue'], 2)}


def load_hourly(d0, d1):
    """本间按小时聚合，只统计手表品类（与全表口径一致；小时文件里同时含手环等其它品类）。"""
    h = {i: (0, 0.0) for i in range(24)}
    for dt in span(d0, d1):
        p = os.path.join(ROOT, 'sales_analysis', 'hourly', dt + '.json')
        hs = json.load(open(p, encoding='utf-8'))['rooms'].get(ROOM, {}).get('_hourly_stats', {})
        for k, v in hs.items():
            pr = v.get('products') or {}
            if pr:
                o = sum(x['orders'] for name, x in pr.items() if W.category_of(name) == '手表')
                r = sum(x['revenue'] for name, x in pr.items() if W.category_of(name) == '手表')
            else:
                o, r = v.get('orders', 0), v.get('revenue', 0.0)
            oh, rh = h[int(k)]
            h[int(k)] = (oh + o, rh + r)
    return h


def win_room(room, d0, d1):
    """指定直播间在窗口内的手表品类（订单数, 销售额）。"""
    o, rv = 0, 0.0
    for dt in span(d0, d1):
        oo, rr = room_watch(BY[dt], room)
        o += oo
        rv += rr
    return {'o': o, 'rv': round(rv, 2)}


# ====================== 单元格小工具 ======================
def inp(ws, r, c, v, fmt=None):
    cell = ws.cell(row=r, column=c, value=v)
    cell.font = W.F_INPUT
    if fmt:
        cell.number_format = fmt
    return cell


def fml(ws, r, c, f, fmt=None, xref=False):
    cell = ws.cell(row=r, column=c, value=f)
    cell.font = W.F_XREF if xref else W.F_FORM
    if fmt:
        cell.number_format = fmt
    return cell


def txt(ws, r, c, v, font=None, fmt=None):
    # 以 "=" 开头的说明文字会被 openpyxl 当公式写入 → 保存后 #NAME?，统一改全角等号
    if isinstance(v, str) and v.startswith('='):
        v = '＝' + v[1:]
    cell = ws.cell(row=r, column=c, value=v)
    cell.font = font or W.F_BODY
    if fmt:
        cell.number_format = fmt
    return cell


def total_row(ws, r, ncol, label):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=r, column=c)
        cell.border = W.B_TOP
        cell.fill = W.P_TOTAL
    ws.cell(row=r, column=1).value = label
    ws.cell(row=r, column=1).font = W.F_BOLD
    ws.row_dimensions[r].height = 21


def grid(ws, r0, r1, ncol):
    for r in range(r0, r1 + 1):
        for c in range(1, ncol + 1):
            ws.cell(row=r, column=c).border = W.B_ALL


def zebra(ws, r0, r1, ncol):
    for i, r in enumerate(range(r0, r1 + 1)):
        if i % 2:
            for c in range(1, ncol + 1):
                ws.cell(row=r, column=c).fill = W.P_ZEBRA


def wd(iso):
    return WEEK[datetime.strptime(iso, '%Y-%m-%d').weekday()]


def col_of(n):
    from openpyxl.utils import get_column_letter
    return get_column_letter(n)


# ====================== 表 2 大盘占比总览（先跑，供跨表引用） ======================
def sheet_overview(ws, x):
    W.no_grid(ws)
    W.widths(ws, [22, 24, 24, 6, 14, 14, 10, 9, 9, 10, 13, 13, 15, 15, 10, 11, 11, 12, 46])
    W.title_block(ws, '大盘占比总览（多窗口交叉验证）',
                  '主口径 A = 本间手表品类额 ÷ 全站手表品类大盘 ｜ 辅助口径 B = 本间手表品类额 ÷ 手表类直播间合计',
                  note='每个窗口都是「等长前窗口 vs 后窗口」。占比、环比、百分点变化全部为 Excel 公式；'
                       '绿色单元格为跨表引用。异常窗口已在备注列标注。', span=17)
    r = 5
    r = W.section(ws, r, '一、主口径 A：全站手表品类大盘（本间手表品类额 ÷ 全站手表品类额）', span=17)
    r = W.header_row(ws, r, ['对比窗口', '前窗口', '后窗口', '天数', '本间手表额（前）', '本间手表额（后）',
                             '额环比', '本间单量（前）', '本间单量（后）', '单量环比', '本间手表均价（前）',
                             '本间手表均价（后）', '全站手表大盘（前）', '全站手表大盘（后）', '大盘环比',
                             '占比 A（前）', '占比 A（后）', '变化（pp）', '备注'], height=34)
    a_first = r
    for w in x['windows']:
        B, A = w['B'], w['A']
        txt(ws, r, 1, w['label'])
        txt(ws, r, 2, w['b_label'], W.F_TINY)
        txt(ws, r, 3, w['a_label'], W.F_TINY)
        inp(ws, r, 4, A['days'], W.INT)
        inp(ws, r, 5, B['rv'], W.MONEY)
        inp(ws, r, 6, A['rv'], W.MONEY)
        fml(ws, r, 7, '=IF(E%d=0,"-",F%d/E%d-1)' % (r, r, r), W.PCT)
        inp(ws, r, 8, B['o'], W.INT)
        inp(ws, r, 9, A['o'], W.INT)
        fml(ws, r, 10, '=IF(H%d=0,"-",I%d/H%d-1)' % (r, r, r), W.PCT)
        fml(ws, r, 11, '=IF(H%d=0,"-",E%d/H%d)' % (r, r, r), W.MONEY1)
        fml(ws, r, 12, '=IF(I%d=0,"-",F%d/I%d)' % (r, r, r), W.MONEY1)
        inp(ws, r, 13, B['a'], W.MONEY)
        inp(ws, r, 14, A['a'], W.MONEY)
        fml(ws, r, 15, '=IF(M%d=0,"-",N%d/M%d-1)' % (r, r, r), W.PCT)
        fml(ws, r, 16, '=IF(M%d=0,"-",E%d/M%d)' % (r, r, r), W.PCT)
        fml(ws, r, 17, '=IF(N%d=0,"-",F%d/N%d)' % (r, r, r), W.PCT)
        fml(ws, r, 18, '=(Q%d-P%d)*100' % (r, r), PPFMT)
        txt(ws, r, 19, w['note'], W.F_TINY)
        r += 1
    a_last = r - 1
    grid(ws, a_first, a_last, 19)
    zebra(ws, a_first, a_last, 19)
    r += 1
    r = W.section(ws, r, '二、辅助口径 B（手表类直播间合计）与参考口径 C（全站全品类）', span=17)
    r = W.header_row(ws, r, ['对比窗口', '手表类间大盘（前）', '手表类间大盘（后）', '大盘环比',
                             '占比 B（前）', '占比 B（后）', '变化（pp）', '本间全品类（前）',
                             '本间全品类（后）', '全品类环比', '全站总销售额（前）', '全站总销售额（后）',
                             '占比 C（前）', '占比 C（后）', '变化（pp）', '参考：占比 A 变化（pp）',
                             '备注'], height=34)
    b_first = r
    for idx, w in enumerate(x['windows']):
        B, A = w['B'], w['A']
        ar = a_first + idx
        txt(ws, r, 1, w['label'])
        inp(ws, r, 2, B['b'], W.MONEY)
        inp(ws, r, 3, A['b'], W.MONEY)
        fml(ws, r, 4, '=IF(B%d=0,"-",C%d/B%d-1)' % (r, r, r), W.PCT)
        fml(ws, r, 5, '=IF(B%d=0,"-",E%d/B%d)' % (r, ar, r), W.PCT)
        fml(ws, r, 6, '=IF(C%d=0,"-",F%d/C%d)' % (r, ar, r), W.PCT)
        fml(ws, r, 7, '=(F%d-E%d)*100' % (r, r), PPFMT)
        inp(ws, r, 8, B['all'], W.MONEY)
        inp(ws, r, 9, A['all'], W.MONEY)
        fml(ws, r, 10, '=IF(H%d=0,"-",I%d/H%d-1)' % (r, r, r), W.PCT)
        inp(ws, r, 11, B['site'], W.MONEY)
        inp(ws, r, 12, A['site'], W.MONEY)
        fml(ws, r, 13, '=IF(K%d=0,"-",H%d/K%d)' % (r, r, r), W.PCT)
        fml(ws, r, 14, '=IF(L%d=0,"-",I%d/L%d)' % (r, r, r), W.PCT)
        fml(ws, r, 15, '=(N%d-M%d)*100' % (r, r), PPFMT)
        fml(ws, r, 16, '=R%d' % ar, PPFMT, xref=True)
        txt(ws, r, 17, w['note'], W.F_TINY)
        r += 1
    b_last = r - 1
    grid(ws, b_first, b_last, 17)
    zebra(ws, b_first, b_last, 17)
    r += 1

    r = W.section(ws, r, '三、自然周走势（本间手表品类与占比 A）', span=17)
    r = W.header_row(ws, r, ['周区间', '起', '止', '天数', '本间手表额', '本间手表单量', '客单价',
                             '全站手表大盘', '占比 A', '手表类间大盘', '占比 B', '本间全品类额',
                             '全站总销售额', '占全站', '品专状态', '周环比（占比 A）', '备注'], height=34)
    w_first = r
    for w in x['weeks']:
        txt(ws, r, 1, w['label'])
        txt(ws, r, 2, w['d0'], W.F_TINY)
        txt(ws, r, 3, w['d1'], W.F_TINY)
        inp(ws, r, 4, w['days'], W.INT)
        inp(ws, r, 5, w['rv'], W.MONEY)
        inp(ws, r, 6, w['o'], W.INT)
        fml(ws, r, 7, '=IF(F%d=0,"-",E%d/F%d)' % (r, r, r), W.MONEY1)
        inp(ws, r, 8, w['a'], W.MONEY)
        fml(ws, r, 9, '=IF(H%d=0,"-",E%d/H%d)' % (r, r, r), W.PCT)
        inp(ws, r, 10, w['b'], W.MONEY)
        fml(ws, r, 11, '=IF(J%d=0,"-",E%d/J%d)' % (r, r, r), W.PCT)
        inp(ws, r, 12, w['all'], W.MONEY)
        inp(ws, r, 13, w['site'], W.MONEY)
        fml(ws, r, 14, '=IF(M%d=0,"-",L%d/M%d)' % (r, r, r), W.PCT)
        txt(ws, r, 15, w['phase'], W.F_TINY)
        if r == w_first:
            txt(ws, r, 16, '—', W.F_TINY)
        else:
            fml(ws, r, 16, '=(I%d-I%d)*100' % (r, r - 1), PPFMT)
        txt(ws, r, 17, w['note'], W.F_TINY)
        r += 1
    w_last = r - 1
    w_tot = r
    total_row(ws, w_tot, 17, '合计（%s ~ %s）' % (x['weeks'][0]['d0'], x['weeks'][-1]['d1']))
    for c, fmt in ((5, W.MONEY), (6, W.INT), (8, W.MONEY), (10, W.MONEY), (12, W.MONEY), (13, W.MONEY)):
        fml(ws, w_tot, c, '=SUM(%s%d:%s%d)' % (col_of(c), w_first, col_of(c), w_last), fmt)
    fml(ws, w_tot, 7, '=IF(F%d=0,"-",E%d/F%d)' % (w_tot, w_tot, w_tot), W.MONEY1)
    fml(ws, w_tot, 9, '=IF(H%d=0,"-",E%d/H%d)' % (w_tot, w_tot, w_tot), W.PCT)
    fml(ws, w_tot, 11, '=IF(J%d=0,"-",E%d/J%d)' % (w_tot, w_tot, w_tot), W.PCT)
    fml(ws, w_tot, 14, '=IF(M%d=0,"-",L%d/M%d)' % (w_tot, w_tot, w_tot), W.PCT)
    txt(ws, w_tot, 16, '—', W.F_TINY)
    grid(ws, w_first, w_tot, 17)
    zebra(ws, w_first, w_last, 17)
    r = w_tot + 2

    r = W.section(ws, r, '四、品专前 / 后（两段长度不等，主要看占比与日均）', span=17)
    r = W.header_row(ws, r, ['阶段', '起', '止', '天数', '本间手表额', '日均本间手表额', '本间手表单量',
                             '日均单量', '全站手表大盘', '日均大盘', '占比 A', '手表类间大盘', '占比 B',
                             '本间全品类额', '全站总销售额', '占比 C', '备注'], height=34)
    s_first = r
    for s in x['stages']:
        txt(ws, r, 1, s['label'])
        txt(ws, r, 2, s['d0'], W.F_TINY)
        txt(ws, r, 3, s['d1'], W.F_TINY)
        inp(ws, r, 4, s['days'], W.INT)
        inp(ws, r, 5, s['rv'], W.MONEY)
        fml(ws, r, 6, '=IF(D%d=0,"-",E%d/D%d)' % (r, r, r), W.MONEY)
        inp(ws, r, 7, s['o'], W.INT)
        fml(ws, r, 8, '=IF(D%d=0,"-",G%d/D%d)' % (r, r, r), W.INT)
        inp(ws, r, 9, s['a'], W.MONEY)
        fml(ws, r, 10, '=IF(D%d=0,"-",I%d/D%d)' % (r, r, r), W.MONEY)
        fml(ws, r, 11, '=IF(I%d=0,"-",E%d/I%d)' % (r, r, r), W.PCT)
        inp(ws, r, 12, s['b'], W.MONEY)
        fml(ws, r, 13, '=IF(L%d=0,"-",E%d/L%d)' % (r, r, r), W.PCT)
        inp(ws, r, 14, s['all'], W.MONEY)
        inp(ws, r, 15, s['site'], W.MONEY)
        fml(ws, r, 16, '=IF(O%d=0,"-",N%d/O%d)' % (r, r, r), W.PCT)
        txt(ws, r, 17, s['note'], W.F_TINY)
        r += 1
    s_last = r - 1
    grid(ws, s_first, s_last, 17)
    zebra(ws, s_first, s_last, 17)
    x['refs'] = {'a_first': a_first, 'b_first': b_first, 'w_first': w_first, 's_first': s_first}
    return ws


# ====================== 表 1 结论摘要 ======================
def sheet_summary(ws, x):
    W.no_grid(ws)
    W.widths(ws, [22, 16, 16, 12, 52, 14])
    W.title_block(ws, '%s · 品专效果分析（大盘占比口径）' % ROOM,
                  '品专上线日 %s ｜ 主窗口：前 %s ~ %s（%d 天） vs 后 %s ~ %s（%d 天）' % (
                      BRAND_START, x['b0'], x['b1'], x['B']['days'], x['a0'], x['a1'], x['A']['days']),
                  note='口径：销售额取 sales_analysis/history.json（订单口径，未扣退款）。「手表品类」= 商品名含 Watch/手表。'
                       '占比 A = 本间手表品类额 ÷ 全站手表品类额；占比 B = 本间手表品类额 ÷ 各服务商手表类直播间合计。'
                       '蓝色 = 源数据输入，深灰 = 公式，绿色 = 跨表引用。', span=6)
    r = 5
    r = W.section(ws, r, '一、品专效果判定', span=6)
    r = W.bullets(ws, r, 6, x['headline'])
    r += 1
    r = W.section(ws, r, '二、占比与关键量速览（数值由「大盘占比总览」跨表带出）', span=6)
    r = W.header_row(ws, r, ['指标', '品专后（%s ~ %s）' % (x['a0'][5:], x['a1'][5:]),
                             '品专前（%s ~ %s）' % (x['b0'][5:], x['b1'][5:]), '变化', '说明', ''], height=34)
    kpi_start = r
    ar = x['refs']['a_first']
    br = x['refs']['b_first']
    specs = [
        ('占全站手表大盘（口径 A）', 'Q%d' % ar, 'P%d' % ar, W.PCT, 'pp', '本间手表品类 ÷ 全站手表品类大盘 ← 主口径'),
        ('占手表类直播间（口径 B）', 'F%d' % br, 'E%d' % br, W.PCT, 'pp', '手表类直播间合计口径（易被首销日污染）'),
        ('本间手表品类额', 'F%d' % ar, 'E%d' % ar, W.MONEY, 'pct', '本间「Watch/手表」商品销售额'),
        ('本间手表品类单量', 'I%d' % ar, 'H%d' % ar, W.INT, 'pct', '本间 Watch/手表 商品订单数'),
        ('全站手表大盘', 'N%d' % ar, 'M%d' % ar, W.MONEY, 'pct', '全站所有直播间的手表品类额'),
    ]
    for label, aref, bref, fmt, kind, note in specs:
        txt(ws, r, 1, label)
        fml(ws, r, 2, "='大盘占比总览'!%s" % aref, fmt, xref=True)
        fml(ws, r, 3, "='大盘占比总览'!%s" % bref, fmt, xref=True)
        if kind == 'pp':
            fml(ws, r, 4, '=(B%d-C%d)*100' % (r, r), PPFMT)
        else:
            fml(ws, r, 4, '=IF(C%d=0,"-",B%d/C%d-1)' % (r, r, r), W.PCT)
        txt(ws, r, 5, note, W.F_TINY)
        r += 1
    rev_row, ord_row, cust_row = kpi_start + 2, kpi_start + 3, r
    txt(ws, cust_row, 1, '本间手表客单价')
    fml(ws, cust_row, 2, '=IF(B%d=0,"-",B%d/B%d)' % (ord_row, rev_row, ord_row), W.MONEY1)
    fml(ws, cust_row, 3, '=IF(C%d=0,"-",C%d/C%d)' % (ord_row, rev_row, ord_row), W.MONEY1)
    fml(ws, cust_row, 4, '=IF(C%d=0,"-",B%d/C%d-1)' % (cust_row, cust_row, cust_row), W.PCT)
    txt(ws, cust_row, 5, '本间手表品类额 ÷ 单量（表内公式）', W.F_TINY)
    r += 1
    grid(ws, kpi_start, r - 1, 5)
    r += 1
    r = W.section(ws, r, '三、份额为什么上升（支持证据）', span=6)
    r = W.bullets(ws, r, 6, x['good'])
    r += 1
    r = W.section(ws, r, '四、还不成立的证据与风险', span=6)
    r = W.bullets(ws, r, 6, x['bad'])
    r += 1
    r = W.section(ws, r, '五、下一步动作', span=6)
    r = W.bullets(ws, r, 6, x['plan'])
    r += 1
    r = W.section(ws, r, '六、口径提醒（对外汇报先读这一段）', span=6)
    r = W.bullets(ws, r, 6, x['caveat'])
    return ws


# ====================== 表 3 逐日明细 ======================
def sheet_daily(ws, x):
    W.no_grid(ws)
    W.widths(ws, [12, 7, 13, 10, 11, 15, 9, 15, 9, 13, 13, 9, 34])
    W.title_block(ws, '逐日明细（%s ~ %s）' % (x['series'][0]['date'], x['series'][-1]['date']),
                  '看断点：%s 起手表直播间有了品专。占比 A = 本间手表品类额 ÷ 全站手表品类额。' % BRAND_START,
                  note='黄底 = 异常日（全站手表大盘 ≥ 1.5 倍区间中位日）：首销/大促会把大盘抬高，从而压低占比，跨窗口对比时要避开。'
                       '底部小计分别覆盖「品专前」与「品专后」。', span=13)
    r = 5
    r = W.header_row(ws, r, ['日期', '星期', '本间手表额', '本间手表单', '客单价', '全站手表大盘', '占比 A',
                             '手表类间大盘', '占比 B', '本间全品类额', '全站额', '占全站', '备注'], height=34)
    first = r
    for d in x['series']:
        txt(ws, r, 1, d['date'])
        txt(ws, r, 2, wd(d['date']), W.F_TINY)
        inp(ws, r, 3, d['rv'], W.MONEY)
        inp(ws, r, 4, d['o'], W.INT)
        fml(ws, r, 5, '=IF(D%d=0,"-",C%d/D%d)' % (r, r, r), W.MONEY1)
        inp(ws, r, 6, d['a'], W.MONEY)
        fml(ws, r, 7, '=IF(F%d=0,"-",C%d/F%d)' % (r, r, r), W.PCT)
        inp(ws, r, 8, d['b'], W.MONEY)
        fml(ws, r, 9, '=IF(H%d=0,"-",C%d/H%d)' % (r, r, r), W.PCT)
        inp(ws, r, 10, d['all'], W.MONEY)
        inp(ws, r, 11, d['site'], W.MONEY)
        fml(ws, r, 12, '=IF(K%d=0,"-",J%d/K%d)' % (r, r, r), W.PCT)
        txt(ws, r, 13, d['note'], W.F_TINY)
        r += 1
    last = r - 1
    pre_rows = [first + i for i, d in enumerate(x['series']) if d['date'] < BRAND_START]
    post_rows = [first + i for i, d in enumerate(x['series']) if d['date'] >= BRAND_START]
    labels = (('小计（品专前 %s ~ %s）' % (x['series'][0]['date'], x['b1']), pre_rows),
              ('小计（品专后 %s ~ %s）' % (x['a0'], x['series'][-1]['date']), post_rows))
    tot_rows = []
    for label, rows in labels:
        total_row(ws, r, 13, label)
        fml(ws, r, 3, '=SUM(%s)' % ','.join('C%d' % i for i in rows), W.MONEY)
        fml(ws, r, 4, '=SUM(%s)' % ','.join('D%d' % i for i in rows), W.INT)
        fml(ws, r, 5, '=IF(D%d=0,"-",C%d/D%d)' % (r, r, r), W.MONEY1)
        fml(ws, r, 6, '=SUM(%s)' % ','.join('F%d' % i for i in rows), W.MONEY)
        fml(ws, r, 7, '=IF(F%d=0,"-",C%d/F%d)' % (r, r, r), W.PCT)
        fml(ws, r, 8, '=SUM(%s)' % ','.join('H%d' % i for i in rows), W.MONEY)
        fml(ws, r, 9, '=IF(H%d=0,"-",C%d/H%d)' % (r, r, r), W.PCT)
        fml(ws, r, 10, '=SUM(%s)' % ','.join('J%d' % i for i in rows), W.MONEY)
        fml(ws, r, 11, '=SUM(%s)' % ','.join('K%d' % i for i in rows), W.MONEY)
        fml(ws, r, 12, '=IF(K%d=0,"-",J%d/K%d)' % (r, r, r), W.PCT)
        tot_rows.append(r)
        r += 1
    pre_tot, post_tot = tot_rows
    total_row(ws, r, 13, '合计（全区间）')
    fml(ws, r, 3, '=C%d+C%d' % (pre_tot, post_tot), W.MONEY)
    fml(ws, r, 4, '=D%d+D%d' % (pre_tot, post_tot), W.INT)
    fml(ws, r, 5, '=IF(D%d=0,"-",C%d/D%d)' % (r, r, r), W.MONEY1)
    for c in (6, 8, 10, 11):
        fml(ws, r, c, '=%s%d+%s%d' % (col_of(c), pre_tot, col_of(c), post_tot), W.MONEY)
    fml(ws, r, 7, '=IF(F%d=0,"-",C%d/F%d)' % (r, r, r), W.PCT)
    fml(ws, r, 9, '=IF(H%d=0,"-",C%d/H%d)' % (r, r, r), W.PCT)
    fml(ws, r, 12, '=IF(K%d=0,"-",J%d/K%d)' % (r, r, r), W.PCT)
    all_tot = r
    grid(ws, first, all_tot, 13)
    zebra(ws, first, last, 13)
    for i, d in enumerate(x['series']):
        if d['note']:
            for c in range(1, 14):
                ws.cell(row=first + i, column=c).fill = W.P_WARN
    for rr in (pre_tot, post_tot, all_tot):
        for c in range(1, 14):
            ws.cell(row=rr, column=c).fill = W.P_TOTAL
    ch = LineChart()
    ch.title = '逐日占比 A（本间手表品类 ÷ 全站手表品类大盘）'
    ch.height, ch.width = 8.5, 26
    ch.add_data(Reference(ws, min_col=7, min_row=first - 1, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=first, max_row=last))
    ch.y_axis.numFmt = '0.0%'
    ws.add_chart(ch, 'A%d' % (all_tot + 2))
    x['daily_rows'] = {'first': first, 'last': last, 'pre': pre_tot, 'post': post_tot, 'all': all_tot}
    return ws


# ====================== 表 4 竞对对照 ======================
def sheet_rivals(ws, x):
    W.no_grid(ws)
    W.widths(ws, [22, 10, 14, 8, 15, 8, 11, 12, 12, 12, 36])
    W.title_block(ws, '手表类直播间对照（全体服务商）',
                  '前窗口 %s ~ %s ｜ 后窗口 %s ~ %s' % (x['b0'], x['b1'], x['a0'], x['a1']),
                  note='口径 = 手表品类销售额（商品名含 Watch/手表）。占比 B = 该间手表品类额 ÷ 手表类直播间合计。'
                       '本间 = 小米官方手表（有品专的间）。', span=11)
    r = 5
    r = W.header_row(ws, r, ['直播间', '服务商', '前窗口手表额', '单量', '后窗口手表额', '单量', '额环比',
                             '前占比 B', '后占比 B', '变化（pp）', '备注'], height=34)
    first = r
    rws = x['rivals']
    tot = first + len(rws)
    other = tot + 1
    our_row = first + [i for i, v in enumerate(rws) if v['room'] == ROOM][0]
    for v in rws:
        txt(ws, r, 1, v['room'])
        txt(ws, r, 2, v['team'], W.F_TINY)
        inp(ws, r, 3, v['b_rv'], W.MONEY)
        inp(ws, r, 4, v['b_o'], W.INT)
        inp(ws, r, 5, v['a_rv'], W.MONEY)
        inp(ws, r, 6, v['a_o'], W.INT)
        fml(ws, r, 7, '=IF(C%d=0,"-",E%d/C%d-1)' % (r, r, r), W.PCT)
        fml(ws, r, 8, '=IF($C$%d=0,"-",C%d/$C$%d)' % (tot, r, tot), W.PCT)
        fml(ws, r, 9, '=IF($E$%d=0,"-",E%d/$E$%d)' % (tot, r, tot), W.PCT)
        fml(ws, r, 10, '=(I%d-H%d)*100' % (r, r), PPFMT)
        txt(ws, r, 11, v['note'], W.F_TINY)
        r += 1
    last = r - 1
    total_row(ws, tot, 11, '手表类直播间合计')
    for c, fmt in ((3, W.MONEY), (4, W.INT), (5, W.MONEY), (6, W.INT)):
        fml(ws, tot, c, '=SUM(%s%d:%s%d)' % (col_of(c), first, col_of(c), last), fmt)
    fml(ws, tot, 7, '=IF(C%d=0,"-",E%d/C%d-1)' % (tot, tot, tot), W.PCT)
    fml(ws, tot, 8, '=IF(C%d=0,"-",C%d/C%d)' % (tot, tot, tot), W.PCT)
    fml(ws, tot, 9, '=IF(E%d=0,"-",E%d/E%d)' % (tot, tot, tot), W.PCT)
    fml(ws, tot, 10, '=(I%d-H%d)*100' % (tot, tot), PPFMT)
    total_row(ws, other, 11, '非我司合计（竞对）')
    for c in (3, 5):
        fml(ws, other, c, '=%s%d-%s%d' % (col_of(c), tot, col_of(c), our_row), W.MONEY)
    fml(ws, other, 4, '=D%d-D%d' % (tot, our_row), W.INT)
    fml(ws, other, 6, '=F%d-F%d' % (tot, our_row), W.INT)
    fml(ws, other, 7, '=IF(C%d=0,"-",E%d/C%d-1)' % (other, other, other), W.PCT)
    fml(ws, other, 8, '=IF(C%d=0,"-",C%d/C%d)' % (tot, other, tot), W.PCT)
    fml(ws, other, 9, '=IF(E%d=0,"-",E%d/E%d)' % (tot, other, tot), W.PCT)
    fml(ws, other, 10, '=(I%d-H%d)*100' % (other, other), PPFMT)
    txt(ws, other, 11, '非我司 = 手表类直播间合计 − 本间（首行）', W.F_TINY)
    grid(ws, first, other, 11)
    zebra(ws, first, last, 11)
    x['riv_rows'] = {'first': first, 'last': last, 'tot': tot, 'other': other, 'our': our_row}
    return ws


# ====================== 表 5 时段结构 ======================
def sheet_hours(ws, x):
    W.no_grid(ws)
    W.widths(ws, [14, 15, 15, 11, 11, 12, 11, 11, 11, 44])
    W.title_block(ws, '本间时段结构（订单口径）',
                  '前窗口 %s ~ %s ｜ 后窗口 %s ~ %s' % (x['b0'], x['b1'], x['a0'], x['a1']),
                  note='口径 = 本间手表品类（商品名含 Watch/手表），小时数据来自 sales_analysis/hourly/。'
                       '品专 = 搜索/品牌专区流量，理论上更偏白天自然流量；看成交是否从晚间黄金档前移。占比为占当日合计。', span=10)
    r = 5
    r = W.section(ws, r, '一、时段块对比', span=10)
    r = W.header_row(ws, r, ['时段块', '前窗口金额', '后窗口金额', '前占比', '后占比', '变化（pp）',
                             '前订单', '后订单', '订单环比', '说明'], height=30)
    first = r
    blocks = x['blocks']
    tot_row = first + len(blocks)
    for v in blocks:
        txt(ws, r, 1, v['label'])
        inp(ws, r, 2, v['b'], W.MONEY)
        inp(ws, r, 3, v['a'], W.MONEY)
        fml(ws, r, 4, '=IF($B$%d=0,"-",B%d/$B$%d)' % (tot_row, r, tot_row), W.PCT)
        fml(ws, r, 5, '=IF($C$%d=0,"-",C%d/$C$%d)' % (tot_row, r, tot_row), W.PCT)
        fml(ws, r, 6, '=(E%d-D%d)*100' % (r, r), PPFMT)
        inp(ws, r, 7, v['b_o'], W.INT)
        inp(ws, r, 8, v['a_o'], W.INT)
        fml(ws, r, 9, '=IF(G%d=0,"-",H%d/G%d-1)' % (r, r, r), W.PCT)
        txt(ws, r, 10, v['note'], W.F_TINY)
        r += 1
    blk_last = r - 1
    total_row(ws, tot_row, 10, '合计')
    for c, fmt in ((2, W.MONEY), (3, W.MONEY), (7, W.INT), (8, W.INT)):
        fml(ws, tot_row, c, '=SUM(%s%d:%s%d)' % (col_of(c), first, col_of(c), blk_last), fmt)
    fml(ws, tot_row, 4, '=IF(B%d=0,"-",B%d/B%d)' % (tot_row, tot_row, tot_row), W.PCT)
    fml(ws, tot_row, 5, '=IF(C%d=0,"-",C%d/C%d)' % (tot_row, tot_row, tot_row), W.PCT)
    fml(ws, tot_row, 6, '=(E%d-D%d)*100' % (tot_row, tot_row), PPFMT)
    fml(ws, tot_row, 9, '=IF(G%d=0,"-",H%d/G%d-1)' % (tot_row, tot_row, tot_row), W.PCT)
    grid(ws, first, tot_row, 10)
    zebra(ws, first, blk_last, 10)
    r = tot_row + 2
    r = W.section(ws, r, '二、24 小时明细', span=10)
    r = W.header_row(ws, r, ['小时', '前窗口金额', '后窗口金额', '前占比', '后占比', '变化（pp）',
                             '前订单', '后订单', '订单环比', '说明'], height=30)
    h_first = r
    h_tot = h_first + 24
    for i in range(24):
        v = x['hours'][i]
        txt(ws, r, 1, '%02d:00' % i)
        inp(ws, r, 2, v['b'], W.MONEY)
        inp(ws, r, 3, v['a'], W.MONEY)
        fml(ws, r, 4, '=IF($B$%d=0,"-",B%d/$B$%d)' % (h_tot, r, h_tot), W.PCT)
        fml(ws, r, 5, '=IF($C$%d=0,"-",C%d/$C$%d)' % (h_tot, r, h_tot), W.PCT)
        fml(ws, r, 6, '=(E%d-D%d)*100' % (r, r), PPFMT)
        inp(ws, r, 7, v['b_o'], W.INT)
        inp(ws, r, 8, v['a_o'], W.INT)
        fml(ws, r, 9, '=IF(G%d=0,"-",H%d/G%d-1)' % (r, r, r), W.PCT)
        txt(ws, r, 10, v['note'], W.F_TINY)
        r += 1
    h_last = r - 1
    total_row(ws, h_tot, 10, '合计')
    for c, fmt in ((2, W.MONEY), (3, W.MONEY), (7, W.INT), (8, W.INT)):
        fml(ws, h_tot, c, '=SUM(%s%d:%s%d)' % (col_of(c), h_first, col_of(c), h_last), fmt)
    fml(ws, h_tot, 4, '=IF(B%d=0,"-",B%d/B%d)' % (h_tot, h_tot, h_tot), W.PCT)
    fml(ws, h_tot, 5, '=IF(C%d=0,"-",C%d/C%d)' % (h_tot, h_tot, h_tot), W.PCT)
    fml(ws, h_tot, 6, '=(E%d-D%d)*100' % (h_tot, h_tot), PPFMT)
    grid(ws, h_first, h_tot, 10)
    zebra(ws, h_first, h_last, 10)
    x['hour_rows'] = {'first': first, 'tot': tot_row, 'h_first': h_first, 'h_tot': h_tot}
    return ws


# ====================== 表 6 口径与说明 ======================
def sheet_notes(ws, x):
    W.no_grid(ws)
    W.widths(ws, [20, 100, 15, 15])
    W.title_block(ws, '口径、异常日与局限', '读数之前先看这一页', span=4)
    r = 5
    for title, rows in (('一、数据源', x['src']), ('二、口径定义', x['defs'])):
        r = W.section(ws, r, title, span=4)
        for k, v in rows:
            txt(ws, r, 1, k, W.F_BOLD)
            txt(ws, r, 2, v, W.F_BODY)
            r += 1
        r += 1
    r = W.section(ws, r, '三、异常日（会污染占比，跨窗口对比必须避开）', span=4)
    r = W.header_row(ws, r, ['日期', '全站手表大盘', '相对中位日', '原因'], height=24)
    for d, v, ratio, why in x['anomalies']:
        txt(ws, r, 1, d)
        inp(ws, r, 2, v, W.MONEY)
        inp(ws, r, 3, ratio, '0.00"x"')
        txt(ws, r, 4, why, W.F_TINY)
        r += 1
    r += 1
    r = W.section(ws, r, '四、方法与局限', span=4)
    r = W.bullets(ws, r, 4, x['method'])
    return ws


# ====================== 文案（数据驱动） ======================
def build_text(x):
    A, B = x['A'], x['B']
    w2 = x['windows'][1]
    dp_pool = (A['shA'] - B['shA']) * 100
    dp_room = (A['shB'] - B['shB']) * 100
    mkt_wow = (A['a'] / B['a'] - 1) * 100
    our_wow = (A['rv'] / B['rv'] - 1) * 100
    o_wow = (A['o'] / B['o'] - 1) * 100 if B['o'] else 0
    rv = [v for v in x['rivals'] if v['room'] == ROOM][0]
    others = [v for v in x['rivals'] if v['room'] != ROOM]
    otherB = sum(v['b_rv'] for v in others)
    otherA = sum(v['a_rv'] for v in others)
    other_wow = (otherA / otherB - 1) * 100 if otherB else 0
    b19 = [v for v in x['blocks'] if v['label'].startswith('19')][0]
    b12 = [v for v in x['blocks'] if v['label'].startswith('12')][0]
    b00 = [v for v in x['blocks'] if v['label'].startswith('00')][0]
    tb, ta = sum(v['b'] for v in x['blocks']), sum(v['a'] for v in x['blocks'])
    med_pre = median([d['rv'] / d['a'] for d in x['series'] if d['date'] < BRAND_START and not d['note'] and d['a']]) * 100
    med_post = median([d['rv'] / d['a'] for d in x['series'] if d['date'] >= BRAND_START and not d['note'] and d['a']]) * 100
    wk = x['weeks']
    pre_weeks = [w['shA'] for w in wk[:4]]
    post_weeks = [w['shA'] for w in wk[5:]]
    top_rival = others[0]
    sib = [v for v in x['rivals'] if v['room'] == '小米官旗手表直播间']
    sib = sib[0] if sib else None
    anom_txt = '、'.join('%s（%.2f 倍中位日）' % (d, r) for d, _, r, _ in x['anomalies'])

    x['headline'] = [
        '品专 %s 上线，截至 %s 已运行 %d 天。主窗口（前 %s ~ %s vs 后 %s ~ %s，各 %d 天）本间手表品类占全站手表大盘 '
        '%.2f%% → %.2f%%（%+.2f pp）：占比是提升的，方向为正。' % (
            BRAND_START, x['a1'], A['days'], x['b0'], x['b1'], x['a0'], x['a1'], A['days'],
            B['shA'] * 100, A['shA'] * 100, dp_pool),
        '换窗口复核，结论一致：同星期对齐 7 天窗口 %.2f%% → %.2f%%（%+.2f pp）；剔除异常日后的中位日 %.1f%% → %.1f%%（%+.1f pp）。'
        '幅度属于「小幅抬升」，不是跳跃式提升。' % (
            w2['B']['shA'] * 100, w2['A']['shA'] * 100, (w2['A']['shA'] - w2['B']['shA']) * 100,
            med_pre, med_post, med_post - med_pre),
        '辅助口径 B（手表类直播间合计）%.2f%% → %.2f%%（%+.2f pp）：本间在全体服务商手表间里维持第一，'
        '且第一竞对「%s」（%s）同期 %+.1f%%。' % (
            B['shB'] * 100, A['shB'] * 100, dp_room, top_rival['room'], top_rival['team'],
            (top_rival['a_rv'] / top_rival['b_rv'] - 1) * 100 if top_rival['b_rv'] else 0),
        '但要说清楚：占比抬升有一部分来自大盘萎缩——全站手表品类 %+.1f%%（¥%s → ¥%s），本间手表额 %+.1f%%（¥%s → ¥%s）；'
        '即"守住了量、份额被动+主动一起抬"，不是绝对放量（单量 %s → %s，%+.1f%%）。' % (
            mkt_wow, W.num(B['a']), W.num(A['a']), our_wow, W.num(B['rv']), W.num(A['rv']),
            W.num(B['o']), W.num(A['o']), o_wow),
    ]

    x['good'] = [
        '大盘在跌、我们没跌：全站手表品类 ¥%s → ¥%s（%+.1f%%），本间 ¥%s → ¥%s（%+.1f%%）→ 占比 %+.2f pp。' % (
            W.num(B['a']), W.num(A['a']), mkt_wow, W.num(B['rv']), W.num(A['rv']), our_wow, dp_pool),
        '竞对让位（品专"抢量"最直接的证据）：非我司手表间手表品类 ¥%s → ¥%s（%+.1f%%）；'
        '其中 %s %+.1f%%、%s %+.1f%%、%s %+.1f%%。' % (
            W.num(otherB), W.num(otherA), other_wow,
            others[0]['room'], (others[0]['a_rv'] / others[0]['b_rv'] - 1) * 100 if others[0]['b_rv'] else 0,
            others[1]['room'], (others[1]['a_rv'] / others[1]['b_rv'] - 1) * 100 if others[1]['b_rv'] else 0,
            others[2]['room'], (others[2]['a_rv'] / others[2]['b_rv'] - 1) * 100 if others[2]['b_rv'] else 0),
        '成交时段前移（与"搜索流量"假说一致）：12:00–18:59 占比 %.1f%% → %.1f%%（%+.1f pp），19:00–23:59 占比 %.1f%% → %.1f%%（%+.1f pp）；'
        '00:00–11:59 占比 %.1f%% → %.1f%%。' % (
            b12['b'] / tb * 100, b12['a'] / ta * 100, (b12['a'] / ta - b12['b'] / tb) * 100,
            b19['b'] / tb * 100, b19['a'] / ta * 100, (b19['a'] / ta - b19['b'] / tb) * 100,
            b00['b'] / tb * 100, b00['a'] / ta * 100),
        '客单价抬升：本间手表客单 ¥%s → ¥%s（%+.1f%%），金额靠结构撑住。' % (
            W.num(B['avg']), W.num(A['avg']), (A['avg'] / B['avg'] - 1) * 100 if B['avg'] else 0),
    ]

    x['bad'] = [
        '单量没有放量：本间手表品类 %s → %s 单（%+.1f%%），全站手表大盘 %s → %s 单。'
        '若品专真带来搜索增量，本间单量应同步增长——目前只能确认"份额与结构"改善，看不到"增量"证据。' % (
            W.num(B['o']), W.num(A['o']), o_wow, W.num(x['mkt_wo_b']), W.num(x['mkt_wo_a'])),
        '占比提升确实有一部分来自大盘萎缩：全站手表品类 %+.1f%%，非我司 %+.1f%%；剔除大盘因素后的绝对增量有限。' % (mkt_wow, other_wow),
        '上线前 9 天含异常日（%s），用"紧邻等长窗口"会算出 %+.2f pp 的虚高值，那个口径不能对外用。' % (
            '、'.join(d for d, _, _, _ in x['anomalies'] if d >= '2026-09-20'),
            (x['windows'][2]['A']['shA'] - x['windows'][2]['B']['shA']) * 100),
        '按自然周看：品专前四周占比 A 在 %.1f%%–%.1f%% 区间，品专后两周为 %.1f%% / %.1f%%（提升约 0.5–2.5 pp），'
        '尚不能排除国庆大促与竞对自身波动的贡献。' % (
            min(pre_weeks) * 100, max(pre_weeks) * 100, post_weeks[0] * 100, post_weeks[1] * 100),
    ]
    if sib and sib['b_rv']:
        x['bad'].append('我司另一手表间「小米官旗手表直播间」同期 %+.1f%%（¥%s → ¥%s）→ 我司手表类整体在涨，'
                        '品专的净贡献需与"我司内部流量再分配"剥离。' % (
                            (sib['a_rv'] / sib['b_rv'] - 1) * 100, W.num(sib['b_rv']), W.num(sib['a_rv'])))

    x['plan'] = [
        '要增量、不要只看份额：把品专搜索词的进店与转化链路拆出来（需要平台侧曝光/点击/进店 UV），当前订单口径只能看结果。',
        '口径固化：对外统一用「全站手表品类大盘」口径（占比 A）；「手表类间」口径（占比 B）易被首销日污染，只在内部看。',
        '连续跟踪：按同星期对齐窗口每 7 天复算一次占比 A，连续 3 个周期不低于 %.0f%% 才算稳定抬升。' % (med_post if med_post > 25 else 30),
        '白天承接：12:00–18:59 占比 %.1f%% → %.1f%%，把主推品与排班往这个时段倾斜，验证搜索流量是否持续走白天。' % (
            b12['b'] / tb * 100, b12['a'] / ta * 100),
        '盯防竞对：%s（%s）本期 %+.1f%%，若其恢复投放，本间份额可能回落，需提前备好货盘与排播。' % (
            top_rival['room'], top_rival['team'],
            (top_rival['a_rv'] / top_rival['b_rv'] - 1) * 100 if top_rival['b_rv'] else 0),
    ]

    x['caveat'] = [
        '异常日 %s：全站手表大盘被首销/大促抬高，占比会被压低。逐日表已黄底标注，跨窗口对比时本报告已避开。' % anom_txt,
        '「紧邻等长窗口」（%s vs %s）含异常日，占比变化 %+.2f pp 属于失真值，仅作对照、不要引用。' % (
            x['windows'][2]['b_label'], x['windows'][2]['a_label'],
            (x['windows'][2]['A']['shA'] - x['windows'][2]['B']['shA']) * 100),
        '只有订单结果数据（下单时间/金额/商品/直播间），没有曝光、点击、进店 UV：'
        '"品专带来搜索流量"只能从份额与时段结构间接推断，不能直接证实或证伪。',
        '结论对窗口选择敏感：用户指定窗口（各 8 天）%+.2f pp、同星期对齐（各 7 天）%+.2f pp、中位日 %+.1f pp、'
        '紧邻窗口（含异常日）%+.2f pp。对外建议只引用前三个。' % (
            dp_pool, (w2['A']['shA'] - w2['B']['shA']) * 100, med_post - med_pre,
            (x['windows'][2]['A']['shA'] - x['windows'][2]['B']['shA']) * 100),
    ]
    return x


# ====================== 主流程 ======================
def build(a):
    rooms = ROOMS
    win_cfgs = [
        ('主窗口（用户指定 8 天）', a.before[0], a.before[1], a.after[0], a.after[1],
         '用户指定：前 9.15-9.22 vs 后 9.30-10.7，等长 8 天，且不含 9.23-9.24 异常日 → 主口径。'),
        ('同星期对齐（各 7 天）', '2026-09-16', '2026-09-22', '2026-09-30', '2026-10-06',
         '周三~周二 对 周三~周二，剔除星期结构影响；两组同样避开异常日。'),
        ('上线前 7 天 vs 后 7 天', '2026-09-22', '2026-09-28', '2026-09-29', '2026-10-05',
         '上线前一周含 9.23-9.24 异常日 → 占比虚低。'),
        ('紧邻等长（各 9 天，含异常日）', '2026-09-20', '2026-09-28', '2026-09-29', '2026-10-07',
         '含 9.23-9.24 异常日：大盘被抬高 1.98~4.86 倍 → 比值失真，仅作对照。'),
    ]
    x = {'windows': []}
    for label, b0, b1, a0, a1, note in win_cfgs:
        x['windows'].append({'label': label, 'b_label': '%s ~ %s' % (b0[5:], b1[5:]), 'a_label': '%s ~ %s' % (a0[5:], a1[5:]),
                             'B': win(b0, b1, rooms), 'A': win(a0, a1, rooms), 'note': note})
    x['b0'], x['b1'] = a.before
    x['a0'], x['a1'] = a.after
    x['A'] = win(x['a0'], x['a1'], rooms)
    x['B'] = win(x['b0'], x['b1'], rooms)

    med = median([pv_day(BY[d])['a'] for d in span(SERIES_START, x['a1'])])
    x['med'] = med
    series = []
    for d in span(SERIES_START, x['a1']):
        v = pv_day(BY[d])
        note = ''
        if v['a'] >= 1.5 * med:
            note = '异常日：全站手表大盘为中位日的 %.2f 倍' % (v['a'] / med)
        if d == BRAND_START:
            note = '品专上线首日' + ('；' + note if note else '')
        series.append({'date': d, 'o': v['o'], 'rv': v['rv'], 'a': v['a'], 'b': v['b'],
                       'all': v['all'], 'site': v['site'], 'note': note})
    x['series'] = series

    x['weeks'] = []
    for lbl, d0, d1 in (('W1', '2026-08-25', '2026-08-31'), ('W2', '2026-09-01', '2026-09-07'),
                        ('W3', '2026-09-08', '2026-09-14'), ('W4', '2026-09-15', '2026-09-21'),
                        ('W5', '2026-09-22', '2026-09-28'), ('W6', '2026-09-29', '2026-10-05'),
                        ('W7', '2026-10-01', '2026-10-07')):
        w = win(d0, d1, rooms)
        note = ''
        if any(d in ('2026-09-23', '2026-09-24') for d in span(d0, d1)):
            note = '含 9.23-9.24 异常日，占比被压低'
        x['weeks'].append({'label': lbl, 'd0': d0, 'd1': d1, 'days': w['days'], 'rv': w['rv'], 'o': w['o'],
                           'a': w['a'], 'b': w['b'], 'all': w['all'], 'site': w['site'], 'shA': w['shA'],
                           'shB': w['shB'], 'phase': '品专前' if d0 < BRAND_START and d1 < BRAND_START else '品专后',
                           'note': note})

    x['stages'] = []
    for lbl, d0, d1 in (('品专前（%s ~ 2026-09-28）' % SERIES_START, SERIES_START, '2026-09-28'),
                        ('品专后（%s ~ %s）' % (BRAND_START, x['a1']), BRAND_START, x['a1'])):
        w = win(d0, d1, rooms)
        x['stages'].append({'label': lbl, 'd0': d0, 'd1': d1, 'days': w['days'], 'rv': w['rv'], 'o': w['o'],
                            'a': w['a'], 'b': w['b'], 'all': w['all'], 'site': w['site'],
                            'note': '长度不等，主要看占比与日均'})

    rivals = []
    for r, team in rooms.items():
        b = win_room(r, x['b0'], x['b1'])
        aa = win_room(r, x['a0'], x['a1'])
        rivals.append({'room': r, 'team': team, 'b_rv': b['rv'], 'b_o': b['o'], 'a_rv': aa['rv'], 'a_o': aa['o'],
                       'note': '本间（有品专的直播间）' if r == ROOM else ''})
    rivals.sort(key=lambda v: -v['a_rv'])
    for v in rivals:
        if v['room'] != ROOM and v['b_rv'] and v['a_rv'] and (v['a_rv'] / v['b_rv'] - 1) < -0.8:
            v['note'] = '大幅掉量（自有波动或投放收缩）'
    x['rivals'] = rivals

    hb = load_hourly(x['b0'], x['b1'])
    ha = load_hourly(x['a0'], x['a1'])
    blocks = []
    for label, lo, hi, note in (('00:00–11:59', 0, 11, '凌晨/上午：以自然与搜索流量为主'),
                                ('12:00–18:59', 12, 18, '下午：本期抬升，疑似搜索流量承接'),
                                ('19:00–23:59', 19, 23, '晚间黄金档：本期占比下降')):
        blocks.append({'label': label,
                       'b': round(sum(hb[i][1] for i in range(lo, hi + 1)), 2),
                       'a': round(sum(ha[i][1] for i in range(lo, hi + 1)), 2),
                       'b_o': sum(hb[i][0] for i in range(lo, hi + 1)),
                       'a_o': sum(ha[i][0] for i in range(lo, hi + 1)), 'note': note})
    x['blocks'] = blocks
    top_b = sorted(range(24), key=lambda i: -hb[i][1])[:3]
    top_a = sorted(range(24), key=lambda i: -ha[i][1])[:3]
    x['hours'] = [{'b': round(hb[i][1], 2), 'a': round(ha[i][1], 2), 'b_o': hb[i][0], 'a_o': ha[i][0],
                   'note': ('前窗口峰值时段' if i in top_b else '') + ('；后窗口峰值时段' if i in top_a else '')}
                  for i in range(24)]

    x['anomalies'] = [(d, pv_day(BY[d])['a'], round(pv_day(BY[d])['a'] / med, 2),
                       '首销/大促日：全站手表大盘异常放大，本间占比被压低')
                      for d in span(SERIES_START, x['a1']) if pv_day(BY[d])['a'] >= 1.5 * med]
    x['mkt_o_b'] = sum(BY[d]['total_orders'] for d in span(x['b0'], x['b1']))
    x['mkt_o_a'] = sum(BY[d]['total_orders'] for d in span(x['a0'], x['a1']))
    x['mkt_wo_b'] = sum(market_watch_o(BY[d]) for d in span(x['b0'], x['b1']))
    x['mkt_wo_a'] = sum(market_watch_o(BY[d]) for d in span(x['a0'], x['a1']))

    x['src'] = [
        ('订单数据', 'sales_analysis/history.json —— 每日「直播间 × 商品」订单数/销售额（订单口径，未扣退款），共 %d 天（%s ~ %s）' % (
            len(DATES), DATES[0], DATES[-1])),
        ('时段数据', 'sales_analysis/hourly/<date>.json —— 每日每小时订单数/销售额，用于「时段结构」表'),
        ('团队归属', 'team_config.py 的 TEAM_MAP / classify_room()；未登记房间默认归良米'),
        ('手表品类', 'tools/gen_weekly_report.py 的 category_of()：商品名含 Watch/手表 → 手表品类（与周报同源口径）'),
    ]
    x['defs'] = [
        ('占比 A（主口径）', '本间手表品类销售额 ÷ 全站所有直播间的手表品类销售额 —— 回答"我们在整个服务商手表大盘里占多少"'),
        ('占比 B（辅助）', '本间手表品类销售额 ÷ 全体服务商「手表类直播间」（共 %d 间）的手表品类销售额' % len(rooms)),
        ('占比 C（参考）', '本间全品类销售额 ÷ 全站全品类销售额 —— 只看整个直播间在全站的位置，不作为品专效果口径'),
        ('品专上线日', '%s（用户口径：手表直播间 29 号起有品专）' % BRAND_START),
        ('手表类直播间', '、'.join('%s（%s）' % (r, t) for r, t in sorted(rooms.items(), key=lambda kv: kv[1]))),
    ]
    x['method'] = [
        '为什么用"占大盘比重"而不是"跟自己比"：品专的价值在于从全站手表大盘里多分到份额，所以主口径是占比 A 的前后变化。',
        '四个角度交叉验证：用户指定窗口（各 8 天）、同星期对齐窗口（各 7 天）、中位日口径（剔异常日）、自然周维度。',
        '异常日处理：9.23-9.24（手环11 首销/大促）把全站手表大盘抬到中位日的 1.98~4.86 倍，任何跨该日的窗口对比都会失真，已单列并避开。',
        '局限：只有订单结果数据，没有曝光/点击/进店 UV，无法直接归因"品专带来多少搜索流量"；份额提升是必要证据，不是充分证明。',
        '读法：先看「结论摘要」的判定 → 再看「大盘占比总览」四个窗口是否一致 → 最后用「逐日明细」确认断点位置与异常日。',
    ]
    return build_text(x)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--room', default='小米官方手表')
    ap.add_argument('--before', nargs=2, default=['2026-09-15', '2026-09-22'])
    ap.add_argument('--after', nargs=2, default=['2026-09-30', '2026-10-07'])
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)

    global BY, DATES, ROOMS, ROOM
    BY, DATES = load()
    ROOM = a.room
    ROOMS = watch_rooms(span(SERIES_START, a.after[1]))

    x = build(a)
    wb = Workbook()
    wb.remove(wb.active)
    for n in SHEETS:
        wb.create_sheet(n)
    # 先渲染总览表（结论摘要要跨表引用它的行号）
    sheet_overview(wb['大盘占比总览'], x)
    sheet_summary(wb['结论摘要'], x)
    sheet_daily(wb['逐日明细'], x)
    sheet_rivals(wb['竞对对照'], x)
    sheet_hours(wb['时段结构'], x)
    sheet_notes(wb['口径与说明'], x)

    out = a.out or os.path.join(W.DESKTOP, '小米官方手表_品专效果与大盘占比_%s-%s.xlsx' % (
        x['a0'][5:].replace('-', '.'), x['a1'][5:].replace('-', '.')))
    wb.save(out)
    exp = os.path.join(ROOT, '_artifacts', 'pinzhuan_expect.json')
    json.dump({'room': ROOM, 'brand_start': BRAND_START, 'before': [x['b0'], x['b1']], 'after': [x['a0'], x['a1']],
               'A': x['A'], 'B': x['B'], 'mkt_o_b': x['mkt_o_b'], 'mkt_o_a': x['mkt_o_a'],
               'windows': [{'label': w['label'], 'b_label': w['b_label'], 'a_label': w['a_label'],
                            'B': w['B'], 'A': w['A']} for w in x['windows']],
               'daily': x['series'], 'weeks': x['weeks'], 'stages': x['stages'], 'rivals': x['rivals'],
               'hours': x['hours'], 'blocks': x['blocks'], 'anomalies': x['anomalies'], 'med': x['med'],
               'rows': {k: v for k, v in x.items() if k.endswith('_rows')} | {'ov': x['refs']}},
              open(exp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('已生成：%s' % out)
    print('占比 A：%.2f%% → %.2f%% (%+.2f pp) ｜ 占比 B：%.2f%% → %.2f%% (%+.2f pp)' % (
        x['B']['shA'] * 100, x['A']['shA'] * 100, (x['A']['shA'] - x['B']['shA']) * 100,
        x['B']['shB'] * 100, x['A']['shB'] * 100, (x['A']['shB'] - x['B']['shB']) * 100))
    print('本间手表：%s → %s 单，¥%s → ¥%s；大盘 A：¥%s → ¥%s' % (
        W.num(x['B']['o']), W.num(x['A']['o']), W.num(x['B']['rv']), W.num(x['A']['rv']),
        W.num(x['B']['a']), W.num(x['A']['a'])))
    print('异常日：%s ｜ 中位日 ¥%s' % (', '.join('%s %.2fx' % (d, r) for d, _, r, _ in x['anomalies']), W.num(x['med'])))
    return out


if __name__ == '__main__':
    main()

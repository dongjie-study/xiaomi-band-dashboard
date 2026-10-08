# -*- coding: utf-8 -*-
"""单直播间周期销售分析（等长两窗口环比）→ 桌面 xlsx。

默认：小米官方手表 9.29–10.7（本期） vs 9.20–9.28（上期）；
任意房间、任意等长两窗口都可跑（例：--cur 2026-10-01 2026-10-07 --prev 2026-09-14 2026-09-20）。
派生指标全部写成 Excel 公式（蓝色 = 源数据硬编码，深灰 = 公式，绿色 = 跨表引用），
零公式错误依赖 _artifacts/verify_watch_xlsx.ps1 复核。

用法：
    python tools/gen_watch_report.py
    python tools/gen_watch_report.py --room 小米官方手表 --cur 2026-09-29 2026-10-07 --prev 2026-09-20 2026-09-28
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_weekly_report as W  # noqa: E402  复用 house style（字体/配色/数字格式/标题块）
from openpyxl import Workbook  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

ROOT = W.ROOT
ROOM_ID_BY_NAME = {'小米官方手表': 'room_xiaomi_watch'}

WEEK = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
PPFMT = '+0.00"pp";[Red]-0.00"pp";"-"'


def weekday_cn(iso):
    return WEEK[datetime.strptime(iso, '%Y-%m-%d').weekday()]


def daterange(a, b):
    d0 = datetime.strptime(a, '%Y-%m-%d')
    d1 = datetime.strptime(b, '%Y-%m-%d')
    out, d = [], d0
    while d <= d1:
        out.append(d.strftime('%Y-%m-%d'))
        d = d.fromordinal(d.toordinal() + 1)
    return out


# ====================== 取数 ======================
def load(dates):
    hist = json.load(open(os.path.join(ROOT, 'sales_analysis', 'history.json'), encoding='utf-8'))
    by_date = {d['date']: d for d in hist}
    rows, orders, revenue = [], 0, 0.0
    our_o = our_r = site_o = site_r = 0
    site_r = 0.0
    our_r = 0.0
    products = {}
    for dt in dates:
        d = by_date[dt]
        r = d['rooms'].get(ROOM)
        assert r, 'history.json 缺少房间 %s @ %s' % (ROOM, dt)
        oo = sum(x['orders'] for x in d['rooms'].values() if x.get('type') == '我司')
        ov = sum(x['revenue'] for x in d['rooms'].values() if x.get('type') == '我司')
        rows.append({'date': dt, 'week': weekday_cn(dt), 'orders': r['orders'],
                     'revenue': round(r['revenue'], 2), 'our_orders': oo,
                     'our_revenue': round(ov, 2), 'site_orders': d['total_orders'],
                     'site_revenue': round(d['total_revenue'], 2)})
        orders += r['orders']; revenue += r['revenue']
        our_o += oo; our_r += ov; site_o += d['total_orders']; site_r += d['total_revenue']
        for name, p in r['products'].items():
            e = products.setdefault(name, {'orders': 0, 'revenue': 0.0})
            e['orders'] += p['orders']; e['revenue'] += p['revenue']
    for e in products.values():
        e['revenue'] = round(e['revenue'], 2)
    return {'rows': rows, 'orders': orders, 'revenue': round(revenue, 2),
            'our_orders': our_o, 'our_revenue': round(our_r, 2),
            'site_orders': site_o, 'site_revenue': round(site_r, 2),
            'avg': round(revenue / orders, 2) if orders else 0,
            'days': len(dates), 'products': products}


def load_anchor(dates, room_id):
    anc = json.load(open(os.path.join(ROOT, '主播业绩', 'anchor_records.json'), encoding='utf-8'))
    recs = anc['records']
    by_anchor, by_shift, per_day = {}, {}, {}
    for dt in dates:
        rs = [r for r in recs.get(dt, []) if r['roomId'] == room_id]
        per_day[dt] = round(sum(r['sales'] for r in rs), 2)
        for r in rs:
            by_anchor[r['anchor']] = round(by_anchor.get(r['anchor'], 0) + r['sales'], 2)
            by_shift[r['shift']] = round(by_shift.get(r['shift'], 0) + r['sales'], 2)
    return {'by_anchor': by_anchor, 'by_shift': by_shift, 'per_day': per_day,
            'total': round(sum(per_day.values()), 2)}


def load_hourly(dates):
    h = {i: [0, 0.0] for i in range(24)}
    for dt in dates:
        j = json.load(open(os.path.join(ROOT, 'sales_analysis', 'hourly', dt + '.json'), encoding='utf-8'))
        st = j['rooms'][ROOM]['_hourly_stats']
        for k, v in st.items():
            h[int(k)][0] += v['orders']; h[int(k)][1] += v['revenue']
    return h


# ====================== 小工具 ======================
def inp(ws, r, c, v, fmt=None):
    """源数据（蓝）"""
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


def txt(ws, r, c, v, font=None):
    # 以 "=" 开头的说明文字会被 openpyxl 当作公式写入 → 保存后显示 #NAME?，这里统一改成全角等号
    if isinstance(v, str) and v.startswith('='):
        v = '＝' + v[1:]
    cell = ws.cell(row=r, column=c, value=v)
    cell.font = font or W.F_BODY
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


# ====================== 各表 ======================
def sheet_summary(wb, ctx):
    ws = wb.create_sheet('结论摘要')
    W.no_grid(ws)
    W.widths(ws, [16, 15, 15, 15, 42, 22])
    W.title_block(ws, '%s · 直播间销售分析' % ctx['room'],
                  '本期 %s ~ %s（%d 天）｜对比 %s ~ %s（%d 天，等长窗口）' % (
                      ctx['cur_start'], ctx['cur_end'], ctx['c']['days'],
                      ctx['prev_start'], ctx['prev_end'], ctx['p']['days']),
                  note='口径：订单/销售额取 sales_analysis/history.json；主播业绩取 主播业绩/anchor_records.json（GSV，未扣退款）。'
                       '蓝色 = 源数据输入，深灰 = 公式，绿色 = 跨表引用；环比 = 本期 ÷ 上期 − 1。', span=6)
    r = 5
    r = W.section(ws, r, '一、核心结论', span=6)
    r = W.bullets(ws, r, 6, ctx['headline'], bullet_char='•')
    r += 1
    r = W.section(ws, r, '二、关键指标速览（数值由「汇总对比」「逐日明细」公式带出）', span=6)
    hdr = ['指标', '本期', '上期', '环比', '说明']
    r = W.header_row(ws, r, hdr + [''] * (6 - len(hdr)), height=24)
    ov = ctx['ov']
    kpi = [('订单数', ov['订单数（间内）'], W.INT, W.PCT, '间内订单（订单口径）'),
           ('销售额', ov['销售额（间内）'], W.MONEY, W.PCT, '间内销售额'),
           ('客单价', ov['客单价'], W.MONEY1, W.PCT, '销售额 ÷ 订单数'),
           ('占我司单量', ov['占我司单量'], W.PCT, PPFMT, '我司同窗口 %s 单' % W.num(ctx['c']['our_orders'])),
           ('占我司金额', ov['占我司金额'], W.PCT, PPFMT, '我司同窗口 ¥%s' % W.num(ctx['c']['our_revenue'])),
           ('主播 GSV', ov['主播 GSV（业绩口径）'], W.MONEY, W.PCT, '业绩口径（主播上报，未扣退款）')]
    kpi_start = r
    for name, row_ref, fmt, cfmt, note in kpi:
        txt(ws, r, 1, name)
        fml(ws, r, 2, "='汇总对比'!B%d" % row_ref, fmt, xref=True)
        fml(ws, r, 3, "='汇总对比'!C%d" % row_ref, fmt, xref=True)
        fml(ws, r, 4, "='汇总对比'!D%d" % row_ref, cfmt, xref=True)
        txt(ws, r, 5, note, W.F_TINY)
        r += 1
    grid(ws, kpi_start, r - 1, 5)
    r += 1
    r = W.section(ws, r, '三、做得好的', span=6)
    r = W.bullets(ws, r, 6, ctx['good'])
    r += 1
    r = W.section(ws, r, '四、不足与风险', span=6)
    r = W.bullets(ws, r, 6, ctx['bad'])
    r += 1
    r = W.section(ws, r, '五、建议行动', span=6)
    r = W.bullets(ws, r, 6, ctx['plan'])
    return ws


def sheet_overview(wb, ctx):
    ws = wb.create_sheet('汇总对比')
    W.no_grid(ws)
    W.widths(ws, [22, 16, 16, 12, 44])
    W.title_block(ws, '关键指标对比', '本期 %s ~ %s vs 上期 %s ~ %s' % (
        ctx['cur_start'], ctx['cur_end'], ctx['prev_start'], ctx['prev_end']), span=5)
    r = 5
    r = W.header_row(ws, r, ['指标', '本期（%s~%s）' % (ctx['cur_start'], ctx['cur_end']),
                             '上期（%s~%s）' % (ctx['prev_start'], ctx['prev_end']), '环比', '说明'], height=32)
    c, p = ctx['c'], ctx['p']
    R = {}
    rows = [
        ('天数（天）', c['days'], p['days'], W.INT, '两窗口等长', 'plain'),
        ('订单数（间内）', c['orders'], p['orders'], W.INT, 'history.json rooms[%s].orders' % ctx['room'], 'pct'),
        ('销售额（间内）', c['revenue'], p['revenue'], W.MONEY, 'history.json rooms[%s].revenue' % ctx['room'], 'pct'),
        ('客单价', None, None, W.MONEY1, '= 销售额 ÷ 订单数', 'pct'),
        ('日均订单', None, None, W.INT, '= 订单数 ÷ 天数', 'pct'),
        ('日均销售额', None, None, W.MONEY, '= 销售额 ÷ 天数', 'pct'),
        ('我司单量（全店）', c['our_orders'], p['our_orders'], W.INT, '我司全部直播间合计', 'pct'),
        ('我司销售额（全店）', c['our_revenue'], p['our_revenue'], W.MONEY, '我司全部直播间合计', 'pct'),
        ('占我司单量', None, None, W.PCT, '= 间内订单 ÷ 我司单量', 'pp'),
        ('占我司金额', None, None, W.PCT, '= 间内销售额 ÷ 我司销售额', 'pp'),
        ('全站单量', c['site_orders'], p['site_orders'], W.INT, '全站（含竞对）', 'pct'),
        ('全站销售额', c['site_revenue'], p['site_revenue'], W.MONEY, '全站（含竞对）', 'pct'),
        ('占全站单量', None, None, W.PCT, '= 间内订单 ÷ 全站单量', 'pp'),
        ('占全站金额', None, None, W.PCT, '= 间内销售额 ÷ 全站销售额', 'pp'),
        ('主播 GSV（业绩口径）', ctx['ac']['total'], ctx['ap']['total'], W.MONEY, 'anchor_records.json（未扣退款）', 'pct'),
        ('峰值日销售额', None, None, W.MONEY, '本期峰值 %s；上期 %s' % (ctx['cur_peak'], ctx['prev_peak']), 'pct'),
        ('最低日销售额', None, None, W.MONEY, '本期最低 %s；上期 %s' % (ctx['cur_low'], ctx['prev_low']), 'pct'),
    ]
    first = r
    for name, cv, pv, fmt, note, kind in rows:
        txt(ws, r, 1, name)
        if cv is not None:
            inp(ws, r, 2, cv, fmt)
            inp(ws, r, 3, pv, fmt)
        R[name] = r
        txt(ws, r, 5, note, W.F_TINY)
        r += 1
    # 公式行
    fml(ws, R['客单价'], 2, '=IF(B%d=0,"-",B%d/B%d)' % (R['订单数（间内）'], R['销售额（间内）'], R['订单数（间内）']), W.MONEY1)
    fml(ws, R['客单价'], 3, '=IF(C%d=0,"-",C%d/C%d)' % (R['订单数（间内）'], R['销售额（间内）'], R['订单数（间内）']), W.MONEY1)
    fml(ws, R['日均订单'], 2, '=IF(B%d=0,"-",B%d/B%d)' % (R['天数（天）'], R['订单数（间内）'], R['天数（天）']), W.INT)
    fml(ws, R['日均订单'], 3, '=IF(C%d=0,"-",C%d/C%d)' % (R['天数（天）'], R['订单数（间内）'], R['天数（天）']), W.INT)
    fml(ws, R['日均销售额'], 2, '=IF(B%d=0,"-",B%d/B%d)' % (R['天数（天）'], R['销售额（间内）'], R['天数（天）']), W.MONEY)
    fml(ws, R['日均销售额'], 3, '=IF(C%d=0,"-",C%d/C%d)' % (R['天数（天）'], R['销售额（间内）'], R['天数（天）']), W.MONEY)
    for nm, num_row, den_row in (('占我司单量', '订单数（间内）', '我司单量（全店）'),
                                 ('占我司金额', '销售额（间内）', '我司销售额（全店）'),
                                 ('占全站单量', '订单数（间内）', '全站单量'),
                                 ('占全站金额', '销售额（间内）', '全站销售额')):
        fml(ws, R[nm], 2, '=IF(B%d=0,"-",B%d/B%d)' % (R[den_row], R[num_row], R[den_row]), W.PCT)
        fml(ws, R[nm], 3, '=IF(C%d=0,"-",C%d/C%d)' % (R[den_row], R[num_row], R[den_row]), W.PCT)
    dr = ctx['daily_rows']
    fml(ws, R['峰值日销售额'], 2, "=MAX('逐日明细'!D%d:D%d)" % (dr['cur0'], dr['cur1']), W.MONEY, xref=True)
    fml(ws, R['峰值日销售额'], 3, "=MAX('逐日明细'!D%d:D%d)" % (dr['prev0'], dr['prev1']), W.MONEY, xref=True)
    fml(ws, R['最低日销售额'], 2, "=MIN('逐日明细'!D%d:D%d)" % (dr['cur0'], dr['cur1']), W.MONEY, xref=True)
    fml(ws, R['最低日销售额'], 3, "=MIN('逐日明细'!D%d:D%d)" % (dr['prev0'], dr['prev1']), W.MONEY, xref=True)
    # 环比列
    for name, cv, pv, fmt, note, kind in rows:
        rr = R[name]
        if kind == 'pp':
            fml(ws, rr, 4, '=(B%d-C%d)*100' % (rr, rr), PPFMT)
        elif kind == 'pct':
            fml(ws, rr, 4, '=IF(C%d=0,"-",B%d/C%d-1)' % (rr, rr, rr), W.PCT)
        else:
            txt(ws, rr, 4, '—', W.F_TINY)
    grid(ws, first, r - 1, 5)
    # 合计行样式
    for nm in ('订单数（间内）', '销售额（间内）', '占我司金额', '主播 GSV（业绩口径）'):
        ws.cell(row=R[nm], column=1).font = W.F_BOLD
        ws.cell(row=R[nm], column=2).font = W.F_BOLD
        ws.cell(row=R[nm], column=3).font = W.F_BOLD
    return ws, R


def sheet_daily(wb, ctx):
    ws = wb.create_sheet('逐日明细')
    W.no_grid(ws)
    W.widths(ws, [13, 8, 10, 14, 11, 11, 14, 12, 12, 13, 13])
    W.title_block(ws, '逐日明细（订单口径）', '上=本期 %s ~ %s；下=上期 %s ~ %s。对位环比 = 本期第 N 天 ÷ 上期第 N 天 − 1。' % (
        ctx['cur_start'], ctx['cur_end'], ctx['prev_start'], ctx['prev_end']), span=11)
    r = 5
    r = W.header_row(ws, r, ['日期', '星期', '订单数', '销售额', '客单价', '我司单量', '我司销售额',
                             '占我司单量', '占我司金额', '对位单量环比', '对位金额环比'], height=34)
    c, p = ctx['c'], ctx['p']
    cur0 = r
    for i, row in enumerate(c['rows']):
        txt(ws, r, 1, row['date']); txt(ws, r, 2, row['week'], W.F_TINY)
        inp(ws, r, 3, row['orders'], W.INT)
        inp(ws, r, 4, row['revenue'], W.MONEY)
        fml(ws, r, 5, '=IF(C%d=0,"-",D%d/C%d)' % (r, r, r), W.MONEY1)
        inp(ws, r, 6, row['our_orders'], W.INT)
        inp(ws, r, 7, row['our_revenue'], W.MONEY)
        fml(ws, r, 8, '=IF(F%d=0,"-",C%d/F%d)' % (r, r, r), W.PCT)
        fml(ws, r, 9, '=IF(G%d=0,"-",D%d/G%d)' % (r, r, r), W.PCT)
        r += 1
    cur1 = r - 1
    cur_tot = r
    total_row(ws, cur_tot, 11, '合计（本期）')
    fml(ws, cur_tot, 3, '=SUM(C%d:C%d)' % (cur0, cur1), W.INT)
    fml(ws, cur_tot, 4, '=SUM(D%d:D%d)' % (cur0, cur1), W.MONEY)
    fml(ws, cur_tot, 5, '=IF(C%d=0,"-",D%d/C%d)' % (cur_tot, cur_tot, cur_tot), W.MONEY1)
    fml(ws, cur_tot, 6, '=SUM(F%d:F%d)' % (cur0, cur1), W.INT)
    fml(ws, cur_tot, 7, '=SUM(G%d:G%d)' % (cur0, cur1), W.MONEY)
    fml(ws, cur_tot, 8, '=IF(F%d=0,"-",C%d/F%d)' % (cur_tot, cur_tot, cur_tot), W.PCT)
    fml(ws, cur_tot, 9, '=IF(G%d=0,"-",D%d/G%d)' % (cur_tot, cur_tot, cur_tot), W.PCT)
    r += 2
    prev0 = r
    for row in p['rows']:
        txt(ws, r, 1, row['date']); txt(ws, r, 2, row['week'], W.F_TINY)
        inp(ws, r, 3, row['orders'], W.INT)
        inp(ws, r, 4, row['revenue'], W.MONEY)
        fml(ws, r, 5, '=IF(C%d=0,"-",D%d/C%d)' % (r, r, r), W.MONEY1)
        inp(ws, r, 6, row['our_orders'], W.INT)
        inp(ws, r, 7, row['our_revenue'], W.MONEY)
        fml(ws, r, 8, '=IF(F%d=0,"-",C%d/F%d)' % (r, r, r), W.PCT)
        fml(ws, r, 9, '=IF(G%d=0,"-",D%d/G%d)' % (r, r, r), W.PCT)
        r += 1
    prev1 = r - 1
    prev_tot = r
    total_row(ws, prev_tot, 11, '合计（上期）')
    fml(ws, prev_tot, 3, '=SUM(C%d:C%d)' % (prev0, prev1), W.INT)
    fml(ws, prev_tot, 4, '=SUM(D%d:D%d)' % (prev0, prev1), W.MONEY)
    fml(ws, prev_tot, 5, '=IF(C%d=0,"-",D%d/C%d)' % (prev_tot, prev_tot, prev_tot), W.MONEY1)
    fml(ws, prev_tot, 6, '=SUM(F%d:F%d)' % (prev0, prev1), W.INT)
    fml(ws, prev_tot, 7, '=SUM(G%d:G%d)' % (prev0, prev1), W.MONEY)
    fml(ws, prev_tot, 8, '=IF(F%d=0,"-",C%d/F%d)' % (prev_tot, prev_tot, prev_tot), W.PCT)
    fml(ws, prev_tot, 9, '=IF(G%d=0,"-",D%d/G%d)' % (prev_tot, prev_tot, prev_tot), W.PCT)
    # 对位环比（本期第 N 天 vs 上期第 N 天）
    for i in range(len(c['rows'])):
        rr = cur0 + i
        pr = prev0 + i
        fml(ws, rr, 10, '=IF(C%d=0,"-",C%d/C%d-1)' % (pr, rr, pr), W.PCT)
        fml(ws, rr, 11, '=IF(D%d=0,"-",D%d/D%d-1)' % (pr, rr, pr), W.PCT)
    fml(ws, cur_tot, 10, '=IF(C%d=0,"-",C%d/C%d-1)' % (prev_tot, cur_tot, prev_tot), W.PCT)
    fml(ws, cur_tot, 11, '=IF(D%d=0,"-",D%d/D%d-1)' % (prev_tot, cur_tot, prev_tot), W.PCT)
    grid(ws, cur0, prev_tot, 11)
    for rr in (cur_tot, prev_tot):
        for cc in range(1, 12):
            cell = ws.cell(row=rr, column=cc)
            cell.border = W.B_TOP
            cell.fill = W.P_TOTAL
    return ws, {'cur0': cur0, 'cur1': cur1, 'cur_tot': cur_tot,
                'prev0': prev0, 'prev1': prev1, 'prev_tot': prev_tot}


def sheet_products(wb, ctx):
    ws = wb.create_sheet('商品结构')
    W.no_grid(ws)
    W.widths(ws, [20, 11, 15, 12, 11, 11, 15, 12, 11, 11, 11])
    W.title_block(ws, '商品结构（订单口径）', '本期 %s ~ %s vs 上期 %s ~ %s；占比 = 该商品销售额 ÷ 本间销售额合计。' % (
        ctx['cur_start'], ctx['cur_end'], ctx['prev_start'], ctx['prev_end']), span=11)
    r = 5
    r = W.header_row(ws, r, ['商品', '本期单量', '本期销售额', '本期占比', '本期均价',
                             '上期单量', '上期销售额', '上期占比', '上期均价', '金额环比', '单量环比'], height=34)
    c, p = ctx['c'], ctx['p']
    names = sorted(set(c['products']) | set(p['products']),
                   key=lambda n: (-c['products'].get(n, {'revenue': 0})['revenue'],
                                  -p['products'].get(n, {'revenue': 0})['revenue']))
    first = r
    for n in names:
        cv = c['products'].get(n, {'orders': 0, 'revenue': 0.0})
        pv = p['products'].get(n, {'orders': 0, 'revenue': 0.0})
        txt(ws, r, 1, n)
        inp(ws, r, 2, cv['orders'], W.INT)
        inp(ws, r, 3, round(cv['revenue'], 2), W.MONEY)
        fml(ws, r, 4, '=IF($C$%d=0,"-",C%d/$C$%d)' % (0, r, 0), W.PCT)  # 占位，稍后重写
        fml(ws, r, 5, '=IF(B%d=0,"-",C%d/B%d)' % (r, r, r), W.MONEY1)
        inp(ws, r, 6, pv['orders'], W.INT)
        inp(ws, r, 7, round(pv['revenue'], 2), W.MONEY)
        fml(ws, r, 8, '=IF($G$%d=0,"-",G%d/$G$%d)' % (0, r, 0), W.PCT)  # 占位
        fml(ws, r, 9, '=IF(F%d=0,"-",G%d/F%d)' % (r, r, r), W.MONEY1)
        fml(ws, r, 10, '=IF(G%d=0,"-",C%d/G%d-1)' % (r, r, r), W.PCT)
        fml(ws, r, 11, '=IF(F%d=0,"-",B%d/F%d-1)' % (r, r, r), W.PCT)
        r += 1
    last = r - 1
    tot = r
    total_row(ws, tot, 11, '合计')
    fml(ws, tot, 2, '=SUM(B%d:B%d)' % (first, last), W.INT)
    fml(ws, tot, 3, '=SUM(C%d:C%d)' % (first, last), W.MONEY)
    fml(ws, tot, 4, '=IF(C%d=0,"-",C%d/C%d)' % (tot, tot, tot), W.PCT)
    fml(ws, tot, 5, '=IF(B%d=0,"-",C%d/B%d)' % (tot, tot, tot), W.MONEY1)
    fml(ws, tot, 6, '=SUM(F%d:F%d)' % (first, last), W.INT)
    fml(ws, tot, 7, '=SUM(G%d:G%d)' % (first, last), W.MONEY)
    fml(ws, tot, 8, '=IF(G%d=0,"-",G%d/G%d)' % (tot, tot, tot), W.PCT)
    fml(ws, tot, 9, '=IF(F%d=0,"-",G%d/F%d)' % (tot, tot, tot), W.MONEY1)
    fml(ws, tot, 10, '=IF(G%d=0,"-",C%d/G%d-1)' % (tot, tot, tot), W.PCT)
    fml(ws, tot, 11, '=IF(F%d=0,"-",B%d/F%d-1)' % (tot, tot, tot), W.PCT)
    # 修正占比公式（引用合计行）
    for rr in range(first, last + 1):
        fml(ws, rr, 4, '=IF($C$%d=0,"-",C%d/$C$%d)' % (tot, rr, tot), W.PCT)
        fml(ws, rr, 8, '=IF($G$%d=0,"-",G%d/$G$%d)' % (tot, rr, tot), W.PCT)
    grid(ws, first, tot, 11)
    for cc in range(1, 12):
        cell = ws.cell(row=tot, column=cc)
        cell.border = W.B_TOP
        cell.fill = W.P_TOTAL
    return ws, {'first': first, 'last': last, 'tot': tot}


def sheet_anchor(wb, ctx):
    ws = wb.create_sheet('主播业绩')
    W.no_grid(ws)
    W.widths(ws, [14, 15, 15, 12, 14, 30])
    W.title_block(ws, '主播业绩（业绩口径 GSV，未扣退款）', '本期 %s ~ %s vs 上期 %s ~ %s；来源 主播业绩/anchor_records.json（roomId=%s）。' % (
        ctx['cur_start'], ctx['cur_end'], ctx['prev_start'], ctx['prev_end'], ctx['room_id']), span=5)
    r = 5
    r = W.section(ws, r, '一、主播维度（按本期 GSV 降序）', span=5)
    r = W.header_row(ws, r, ['主播', '本期 GSV', '上期 GSV', '环比', '本期占比'], height=26)
    ac, ap = ctx['ac'], ctx['ap']
    names = sorted(set(ac['by_anchor']) | set(ap['by_anchor']),
                   key=lambda n: (-ac['by_anchor'].get(n, 0), -ap['by_anchor'].get(n, 0)))
    first = r
    for n in names:
        cv = ac['by_anchor'].get(n, 0)
        pv = ap['by_anchor'].get(n, 0)
        txt(ws, r, 1, n)
        inp(ws, r, 2, round(cv, 2), W.MONEY)
        inp(ws, r, 3, round(pv, 2), W.MONEY)
        fml(ws, r, 4, '=IF(C%d=0,IF(B%d=0,"-","新增"),B%d/C%d-1)' % (r, r, r, r), W.PCT)
        fml(ws, r, 5, '=IF($B$%d=0,"-",B%d/$B$%d)' % (0, r, 0), W.PCT)
        r += 1
    last = r - 1
    tot = r
    total_row(ws, tot, 5, '合计')
    fml(ws, tot, 2, '=SUM(B%d:B%d)' % (first, last), W.MONEY)
    fml(ws, tot, 3, '=SUM(C%d:C%d)' % (first, last), W.MONEY)
    fml(ws, tot, 4, '=IF(C%d=0,"-",B%d/C%d-1)' % (tot, tot, tot), W.PCT)
    fml(ws, tot, 5, '=IF(B%d=0,"-",B%d/B%d)' % (tot, tot, tot), W.PCT)
    for rr in range(first, last + 1):
        fml(ws, rr, 5, '=IF($B$%d=0,"-",B%d/$B$%d)' % (tot, rr, tot), W.PCT)
    grid(ws, first, tot, 5)
    for cc in range(1, 6):
        ws.cell(row=tot, column=cc).border = W.B_TOP
        ws.cell(row=tot, column=cc).fill = W.P_TOTAL
    # 班次
    r = tot + 2
    r = W.section(ws, r, '二、班次维度', span=5)
    r = W.header_row(ws, r, ['班次', '本期 GSV', '上期 GSV', '环比', '本期占比'], height=26)
    shifts = sorted(set(ac['by_shift']) | set(ap['by_shift']))
    sfirst = r
    for s in shifts:
        cv = ac['by_shift'].get(s, 0)
        pv = ap['by_shift'].get(s, 0)
        txt(ws, r, 1, s + ' 班')
        inp(ws, r, 2, round(cv, 2), W.MONEY)
        inp(ws, r, 3, round(pv, 2), W.MONEY)
        fml(ws, r, 4, '=IF(C%d=0,IF(B%d=0,"-","新增"),B%d/C%d-1)' % (r, r, r, r), W.PCT)
        fml(ws, r, 5, '=IF($B$%d=0,"-",B%d/$B$%d)' % (0, r, 0), W.PCT)
        r += 1
    slast = r - 1
    stot = r
    total_row(ws, stot, 5, '合计')
    fml(ws, stot, 2, '=SUM(B%d:B%d)' % (sfirst, slast), W.MONEY)
    fml(ws, stot, 3, '=SUM(C%d:C%d)' % (sfirst, slast), W.MONEY)
    fml(ws, stot, 4, '=IF(C%d=0,"-",B%d/C%d-1)' % (stot, stot, stot), W.PCT)
    fml(ws, stot, 5, '=IF(B%d=0,"-",B%d/B%d)' % (stot, stot, stot), W.PCT)
    for rr in range(sfirst, slast + 1):
        fml(ws, rr, 5, '=IF($B$%d=0,"-",B%d/$B$%d)' % (stot, rr, stot), W.PCT)
    grid(ws, sfirst, stot, 5)
    for cc in range(1, 6):
        ws.cell(row=stot, column=cc).border = W.B_TOP
        ws.cell(row=stot, column=cc).fill = W.P_TOTAL
    # 逐日
    r = stot + 2
    r = W.section(ws, r, '三、逐日 GSV（上=本期，下=上期，对位环比）', span=5)
    r = W.header_row(ws, r, ['日期', '星期', 'GSV', '对位环比', '备注'], height=26)
    cf = r
    for dt in ac['per_day']:
        txt(ws, r, 1, dt); txt(ws, r, 2, weekday_cn(dt), W.F_TINY)
        inp(ws, r, 3, ac['per_day'][dt], W.MONEY)
        r += 1
    cl = r - 1
    ct = r
    total_row(ws, ct, 5, '合计（本期）')
    fml(ws, ct, 3, '=SUM(C%d:C%d)' % (cf, cl), W.MONEY)
    r += 2
    pf = r
    for dt in ap['per_day']:
        txt(ws, r, 1, dt); txt(ws, r, 2, weekday_cn(dt), W.F_TINY)
        inp(ws, r, 3, ap['per_day'][dt], W.MONEY)
        r += 1
    pl = r - 1
    pt = r
    total_row(ws, pt, 5, '合计（上期）')
    fml(ws, pt, 3, '=SUM(C%d:C%d)' % (pf, pl), W.MONEY)
    for i in range(cl - cf + 1):
        fml(ws, cf + i, 4, '=IF(C%d=0,"-",C%d/C%d-1)' % (pf + i, cf + i, pf + i), W.PCT)
    fml(ws, ct, 4, '=IF(C%d=0,"-",C%d/C%d-1)' % (pt, ct, pt), W.PCT)
    grid(ws, cf, pt, 5)
    for rr in (ct, pt):
        for cc in range(1, 6):
            ws.cell(row=rr, column=cc).border = W.B_TOP
            ws.cell(row=rr, column=cc).fill = W.P_TOTAL
    txt(ws, ct, 5, '与「汇总对比」主播 GSV 行一致', W.F_TINY)
    return ws


def sheet_hours(wb, ctx):
    ws = wb.create_sheet('时段分布')
    W.no_grid(ws)
    W.widths(ws, [10, 12, 15, 13, 12, 15, 13, 12])
    W.title_block(ws, '时段分布（订单提交小时，累计 %d 天）' % ctx['c']['days'],
                  '来源 sales_analysis/hourly/<日期>.json 的 rooms[%s]._hourly_stats；占比 = 该时段金额 ÷ 区间金额。' % ctx['room'], span=8)
    r = 5
    r = W.header_row(ws, r, ['时段', '本期订单', '本期金额', '本期金额占比',
                             '上期订单', '上期金额', '上期金额占比', '金额环比'], height=30)
    hc, hp = ctx['hc'], ctx['hp']
    first = r
    for h in range(24):
        txt(ws, r, 1, '%02d:00' % h)
        inp(ws, r, 2, hc[h][0], W.INT)
        inp(ws, r, 3, round(hc[h][1], 2), W.MONEY)
        fml(ws, r, 4, '=IF($C$%d=0,"-",C%d/$C$%d)' % (0, r, 0), W.PCT)
        inp(ws, r, 5, hp[h][0], W.INT)
        inp(ws, r, 6, round(hp[h][1], 2), W.MONEY)
        fml(ws, r, 7, '=IF($F$%d=0,"-",F%d/$F$%d)' % (0, r, 0), W.PCT)
        fml(ws, r, 8, '=IF(F%d=0,"-",C%d/F%d-1)' % (r, r, r), W.PCT)
        r += 1
    last = r - 1
    tot = r
    total_row(ws, tot, 8, '合计')
    fml(ws, tot, 2, '=SUM(B%d:B%d)' % (first, last), W.INT)
    fml(ws, tot, 3, '=SUM(C%d:C%d)' % (first, last), W.MONEY)
    fml(ws, tot, 4, '=IF(C%d=0,"-",C%d/C%d)' % (tot, tot, tot), W.PCT)
    fml(ws, tot, 5, '=SUM(E%d:E%d)' % (first, last), W.INT)
    fml(ws, tot, 6, '=SUM(F%d:F%d)' % (first, last), W.MONEY)
    fml(ws, tot, 7, '=IF(F%d=0,"-",F%d/F%d)' % (tot, tot, tot), W.PCT)
    fml(ws, tot, 8, '=IF(F%d=0,"-",C%d/F%d-1)' % (tot, tot, tot), W.PCT)
    for rr in range(first, last + 1):
        fml(ws, rr, 4, '=IF($C$%d=0,"-",C%d/$C$%d)' % (tot, rr, tot), W.PCT)
        fml(ws, rr, 7, '=IF($F$%d=0,"-",F%d/$F$%d)' % (tot, rr, tot), W.PCT)
    grid(ws, first, tot, 8)
    for cc in range(1, 9):
        ws.cell(row=tot, column=cc).border = W.B_TOP
        ws.cell(row=tot, column=cc).fill = W.P_TOTAL
    # 时段段位汇总
    r = tot + 2
    r = W.section(ws, r, '时段段位汇总', span=8)
    r = W.header_row(ws, r, ['段位', '本期订单', '本期金额', '本期金额占比', '', '上期金额', '上期金额占比', ''], height=26)
    segs = [('00:00–05:59 深夜', 0, 5), ('06:00–11:59 上午', 6, 11), ('12:00–18:59 下午', 12, 18), ('19:00–23:59 晚间', 19, 23)]
    sfirst = r
    for lab, a, b in segs:
        txt(ws, r, 1, lab)
        fml(ws, r, 2, '=SUM(B%d:B%d)' % (first + a, first + b), W.INT)
        fml(ws, r, 3, '=SUM(C%d:C%d)' % (first + a, first + b), W.MONEY)
        fml(ws, r, 4, '=IF($C$%d=0,"-",C%d/$C$%d)' % (tot, r, tot), W.PCT)
        fml(ws, r, 6, '=SUM(F%d:F%d)' % (first + a, first + b), W.MONEY)
        fml(ws, r, 7, '=IF($F$%d=0,"-",F%d/$F$%d)' % (tot, r, tot), W.PCT)
        r += 1
    grid(ws, sfirst, r - 1, 8)
    return ws


def sheet_notes(wb, ctx):
    ws = wb.create_sheet('数据说明')
    W.no_grid(ws)
    W.widths(ws, [110, 20])
    W.title_block(ws, '数据说明与口径', '生成时间 %s｜脚本 tools/gen_watch_report.py' % datetime.now().strftime('%Y-%m-%d %H:%M'), span=2)
    r = 5
    r = W.section(ws, r, '一、区间', span=2)
    r = W.bullets(ws, r, 2, [
        '本期：%s ~ %s（%d 天）' % (ctx['cur_start'], ctx['cur_end'], ctx['c']['days']),
        '上期：%s ~ %s（%d 天%s）' % (ctx['prev_start'], ctx['prev_end'], ctx['p']['days'], ctx['prev_gap_note']),
        '房间：%s（roomId %s，team_config 归属我司）' % (ctx['room'], ctx['room_id']),
    ])
    r += 1
    r = W.section(ws, r, '二、数据来源', span=2)
    r = W.bullets(ws, r, 2, [
        '订单口径：sales_analysis/history.json（每日 run_all.py sales 入库；含已发货/待发货/风控审核中/已完成各状态，未剔除退款）。',
        '主播业绩口径：主播业绩/anchor_records.json（由 主播业绩/业绩demo.html 的 DAILY_RECORDS 抽取；主播上报 GSV，未扣退款）。',
        '时段分布：sales_analysis/hourly/<日期>.json 的 rooms[%s]._hourly_stats（按订单提交小时）。' % ctx['room'],
    ])
    r += 1
    r = W.section(ws, r, '三、指标定义', span=2)
    r = W.bullets(ws, r, 2, [
        '客单价 = 销售额 ÷ 订单数（间内，订单口径）。',
        '占我司 = 间内 ÷ 我司全部直播间合计；占全站 = 间内 ÷ 全站（含竞对）。',
        '环比 = 本期 ÷ 上期 − 1；占比类指标的环比用「百分点（pp）」表示差值的绝对值变化。',
        '对位环比（逐日明细）= 本期第 N 天 ÷ 上期第 N 天 − 1，两天并非同一星期几，仅作节奏对照。',
        '颜色：蓝色 = 源数据硬编码输入；深灰 = 公式；绿色 = 跨表引用；橙色表头 = 区间标题行。',
    ])
    r += 1
    r = W.section(ws, r, '四、口径提醒', span=2)
    r = W.bullets(ws, r, 2, [
        ctx['peak_note'],
        '订单口径与业绩口径（主播 GSV）统计对象不同：前者是平台订单表，后者是主播上报的直播间 GSV，'
        '两者绝对值不可直接相减，趋势可互相印证。',
        '本表所有派生指标（客单价/占比/环比/合计）均为 Excel 公式，未硬编码，可自行改数重算。',
    ])
    return ws


# ====================== 主流程 ======================
def build(room, cur_start, cur_end, prev_start, prev_end, out):
    global ROOM
    ROOM = room
    room_id = ROOM_ID_BY_NAME.get(room, '')
    CUR = daterange(cur_start, cur_end)
    PREV = daterange(prev_start, prev_end)
    c = load(CUR)
    p = load(PREV)
    ac = load_anchor(CUR, room_id)
    ap = load_anchor(PREV, room_id)
    hc = load_hourly(CUR)
    hp = load_hourly(PREV)
    peak = max(c['rows'], key=lambda r: r['revenue'])
    low = min(c['rows'], key=lambda r: r['revenue'])
    ppk = max(p['rows'], key=lambda r: r['revenue'])
    plw = min(p['rows'], key=lambda r: r['revenue'])
    # 峰值日修正口径
    import statistics as st
    med = st.median([r['revenue'] for r in p['rows']])
    spike = max(p['rows'], key=lambda r: r['revenue'])
    p_ex_spike = round(p['revenue'] - spike['revenue'], 2)
    rev_wow = c['revenue'] / p['revenue'] - 1
    rev_wow_ex = c['revenue'] / p_ex_spike - 1 if p_ex_spike else None
    hc_tot = round(sum(v[1] for v in hc.values()), 2)
    hp_tot = round(sum(v[1] for v in hp.values()), 2)
    # 两窗口是否紧邻（叙述与数据说明都要用，不能写死）
    _gap = (datetime.strptime(cur_start, '%Y-%m-%d') - datetime.strptime(prev_end, '%Y-%m-%d')).days - 1
    if _gap <= 0:
        prev_gap_note = '，紧邻本期之前'
    else:
        _gs = (datetime.strptime(prev_end, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        _ge = (datetime.strptime(cur_start, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        prev_gap_note = '，与本期之间隔了 %d 天（%s ~ %s），不是紧邻窗口' % (_gap, _gs, _ge)
    ctx = {
        'room': room, 'room_id': room_id, 'c': c, 'p': p, 'ac': ac, 'ap': ap, 'hc': hc, 'hp': hp,
        'prev_gap_note': prev_gap_note,
        'cur_start': cur_start, 'cur_end': cur_end, 'prev_start': prev_start, 'prev_end': prev_end,
        'cur_peak': peak['date'], 'cur_low': low['date'], 'prev_peak': ppk['date'], 'prev_low': plw['date'],
        'p_peak_rev': spike['revenue'], 'p_ex_spike': p_ex_spike,
        'rev_wow': rev_wow, 'rev_wow_ex_spike': rev_wow_ex,
    }
    # 文案
    w6c = c['products'].get('REDMI Watch 6', {'orders': 0, 'revenue': 0})
    w6p = p['products'].get('REDMI Watch 6', {'orders': 0, 'revenue': 0})
    s5c = c['products'].get('Xiaomi Watch S5', {'orders': 0, 'revenue': 0})
    s5p = p['products'].get('Xiaomi Watch S5', {'orders': 0, 'revenue': 0})
    b11c = c['products'].get('小米手环11', {'orders': 0, 'revenue': 0})
    b11p = p['products'].get('小米手环11', {'orders': 0, 'revenue': 0})
    tail3 = sum(r['revenue'] for r in c['rows'][-3:])
    top1 = sorted(ac['by_anchor'].items(), key=lambda kv: -kv[1])[:3]

    # ---------------- 方向判定（叙述层全部由此生成，不写死方向） ----------------
    def _w(v, up, down, flat, eps=0.01):
        if v is None:
            return flat
        return up if v > eps else (down if v < -eps else flat)

    def _pv(d, k):
        return d['products'].get(k, {'orders': 0, 'revenue': 0})

    def _hi(d):
        """单品均价 ≥ ¥1,000 的销售额合计（高端价格带）。"""
        return sum(v['revenue'] for v in d['products'].values()
                   if v['orders'] > 0 and v['revenue'] / v['orders'] >= 1000)

    o_wow = c['orders'] / p['orders'] - 1 if p['orders'] else None
    a_wow = c['avg'] / p['avg'] - 1 if p['avg'] else None
    our_o_wow = c['our_orders'] / p['our_orders'] - 1 if p['our_orders'] else None
    sh_o_c, sh_o_p = c['orders'] / c['our_orders'], p['orders'] / p['our_orders']
    sh_r_c, sh_r_p = c['revenue'] / c['our_revenue'], p['revenue'] / p['our_revenue']
    sh_o_pp, sh_r_pp = 100 * (sh_o_c - sh_o_p), 100 * (sh_r_c - sh_r_p)
    qty_w = _w(o_wow, '单量放量', '单量收缩', '单量持平')
    prc_w = _w(a_wow, '均价上移', '均价下移', '均价持平')
    qp_w = '量%s价%s' % (
        '增' if (o_wow or 0) > 0.01 else ('减' if (o_wow or 0) < -0.01 else '平'),
        '升' if (a_wow or 0) > 0.01 else ('跌' if (a_wow or 0) < -0.01 else '平'))
    sh_w = _w(sh_o_pp / 100, '份额抬升', '份额回落', '份额基本持平', eps=0.003)
    vs_mkt = '跑赢我司大盘' if (o_wow is not None and our_o_wow is not None and o_wow > our_o_wow) else '跑输我司大盘'
    _shift = max([abs(100 * (v['revenue'] / c['revenue'] - _pv(p, k)['revenue'] / p['revenue']))
                  for k, v in c['products'].items()] or [0])
    struct_w = '商品结构大切换' if _shift >= 5 else '商品结构小幅调整'
    prod_names = set(list(c['products']) + list(p['products']))
    movers = sorted(prod_names, key=lambda k: -abs(_pv(c, k)['revenue'] - _pv(p, k)['revenue']))
    mv = movers[0] if movers else ''
    tail_rising = c['days'] >= 3 and all(c['rows'][i]['revenue'] <= c['rows'][i + 1]['revenue']
                                         for i in range(len(c['rows']) - 3, len(c['rows']) - 1))
    if c['days'] >= 3:
        _bi = min(range(len(c['rows']) - 2), key=lambda i: sum(r['revenue'] for r in c['rows'][i:i + 3]))
        low3 = c['rows'][_bi:_bi + 3]
    else:
        low3 = c['rows']
    low3_avg = sum(r['revenue'] for r in low3) / len(low3)
    hi_c, hi_p = _hi(c), _hi(p)
    eve_c, eve_p = sum(hc[h][1] for h in range(19, 24)), sum(hp[h][1] for h in range(19, 24))
    aft_c, aft_p = sum(hc[h][1] for h in range(12, 19)), sum(hp[h][1] for h in range(12, 19))
    worst_h = min(range(19, 24), key=lambda h: hc[h][1] / hp[h][1] if hp[h][1] else 9e9)
    d_eve, d_aft = W.wow(eve_c, eve_p), W.wow(aft_c, aft_p)
    d_wh = W.wow(hc[worst_h][1], hp[worst_h][1])

    def _sp(v):
        """环比格式化：上期基数为 0 时说明是新增，避免 None 崩溃。"""
        return W.signed_pct(v) if v is not None else '新增'

    def _pp(v):
        """百分点差值：用与 signed_pct 一致的减号字符，避免 ASCII '-' 混排。"""
        return ('+' if v >= 0 else '−') + '%.2fpp' % abs(v)
    hour_w = ('成交高峰从晚间前移到下午' if eve_c < eve_p and aft_c > aft_p else
              ('晚间与下午段同步回落' if eve_c < eve_p else
               ('晚间回升、下午回落' if aft_c < aft_p else '晚间与下午段同步回升')))
    prev_main = max(ap['by_anchor'].items(), key=lambda kv: kv[1])[0] if ap['by_anchor'] else None
    gone = [n for n in sorted(ap['by_anchor'], key=lambda n: -ap['by_anchor'][n]) if n not in ac['by_anchor']]
    drop_a = [n for n, v in sorted(ac['by_anchor'].items(), key=lambda kv: -ap['by_anchor'].get(kv[0], 0))
              if ap['by_anchor'].get(n) and v / ap['by_anchor'][n] - 1 < -0.2][:2]
    spike_ratio = spike['revenue'] / med if med else 1.0
    daily_c = c['revenue'] / c['days']
    daily_p_ex = p_ex_spike / (p['days'] - 1) if p['days'] > 1 else p_ex_spike
    if spike_ratio >= 1.3:
        ctx['peak_note'] = ('上期含峰值日 %s（本间 ¥%s，约为上期中位日 ¥%s 的 %.1f 倍），会抬高上期基数 —— '
                            '「销售额环比 %s」被峰值压低；剔除该日后上期 %d 天日均 ¥%s，本期日均 ¥%s（%s）。' % (
                                spike['date'], W.num(spike['revenue']), W.num(med), spike_ratio,
                                W.signed_pct(rev_wow), p['days'] - 1, W.num(daily_p_ex),
                                W.num(daily_c), W.signed_pct(daily_c / daily_p_ex - 1)))
        ctx['peak_head'] = ('基数提醒：上期含 %s 峰值日 ¥%s（约为上期中位日 ¥%s 的 %.1f 倍），剔除该日后上期日均 ¥%s，'
                            '本期日均 ¥%s（%s）—— 表内「销售额环比 %s」被峰值基数压低。' % (
                                spike['date'], W.num(spike['revenue']), W.num(med), spike_ratio,
                                W.num(daily_p_ex), W.num(daily_c), W.signed_pct(daily_c / daily_p_ex - 1),
                                W.signed_pct(rev_wow)))
    else:
        ctx['peak_note'] = ('上期无异常峰值日（上期峰值日 %s ¥%s，约为上期中位日 ¥%s 的 %.1f 倍），两窗口基数可比，'
                            '环比数字可直接解读。' % (
                                spike['date'], W.num(spike['revenue']), W.num(med), spike_ratio))
        ctx['peak_head'] = ('基数提醒：上期无异常峰值日（峰值日 %s ¥%s，约为中位日的 %.1f 倍），两窗口可直接对比。' % (
            spike['date'], W.num(spike['revenue']), spike_ratio))

    ctx['headline'] = [
        '%s、%s：本期 %s 单（环比 %s）、销售额 ¥%s（%s）、客单 ¥%s（%s）—— %s%s。' % (
            qty_w, prc_w, W.num(c['orders']), W.signed_pct(o_wow), W.num(c['revenue']),
            W.signed_pct(rev_wow), W.num(c['avg']), W.signed_pct(a_wow), qp_w,
            ('，结构上最大变动来自 %s（¥%s → ¥%s，%s）' % (
                mv, W.num(_pv(p, mv)['revenue']), W.num(_pv(c, mv)['revenue']),
                W.signed_pct(_pv(c, mv)['revenue'] / _pv(p, mv)['revenue'] - 1))
             if (mv and _pv(p, mv)['revenue']) else '')),
        '%s：占我司单量 %s → %s（%s），占我司金额 %s → %s（%s）；同期我司全店单量 %s → %s（%s），'
        '本间 %s → %s 单（%s），%s。' % (
            sh_w, W.pct(sh_o_p), W.pct(sh_o_c), _pp(sh_o_pp), W.pct(sh_r_p), W.pct(sh_r_c), _pp(sh_r_pp),
            W.num(p['our_orders']), W.num(c['our_orders']), W.signed_pct(our_o_wow),
            W.num(p['orders']), W.num(c['orders']), W.signed_pct(o_wow), vs_mkt),
        '%s：Watch 6 占本间销售额 %s → %s（¥%s → ¥%s，%s）；Xiaomi Watch S5 占比 %.1f%% → %.1f%%（¥%s → ¥%s，%s）；'
        '小米手环11 %d → %d 单（%s）。' % (
            struct_w, W.pct(w6p['revenue'] / p['revenue']), W.pct(w6c['revenue'] / c['revenue']),
            W.num(w6p['revenue']), W.num(w6c['revenue']), W.signed_pct(w6c['revenue'] / w6p['revenue'] - 1),
            100 * s5p['revenue'] / p['revenue'], 100 * s5c['revenue'] / c['revenue'],
            W.num(s5p['revenue']), W.num(s5c['revenue']), W.signed_pct(s5c['revenue'] / s5p['revenue'] - 1),
            b11p['orders'], b11c['orders'], W.signed_pct(b11c['orders'] / b11p['orders'] - 1)),
        '末段节奏%s：逐日 %s ¥%s → 低点 %s ¥%s → 峰值 %s ¥%s；最后三天合计 ¥%s，占本期 %.1f%%。' % (
            '（连续三天抬升）' if tail_rising else '', c['rows'][0]['date'], W.num(c['rows'][0]['revenue']),
            low['date'], W.num(low['revenue']), peak['date'], W.num(peak['revenue']),
            W.num(tail3), 100 * tail3 / c['revenue']),
        '主播侧%s：业绩 GSV ¥%s（%s），前三 %s%s。' % (
            _w(ac['total'] / ap['total'] - 1 if ap['total'] else None, '同步走强', '同步走弱', '基本持平'),
            W.num(ac['total']), W.signed_pct(ac['total'] / ap['total'] - 1),
            '、'.join('%s ¥%s（%s）' % (n, W.num(v), W.signed_pct(v / ap['by_anchor'].get(n, 0) - 1)
                                     if ap['by_anchor'].get(n) else '新增') for n, v in top1),
            ('；上期主力 %s ¥%s → ¥%s（%s）' % (
                prev_main, W.num(ap['by_anchor'][prev_main]), W.num(ac['by_anchor'].get(prev_main, 0)),
                W.signed_pct(ac['by_anchor'].get(prev_main, 0) / ap['by_anchor'][prev_main] - 1))
             if prev_main else '')),
        ctx['peak_head'],
    ]
    # 做得好的：逐条判定是否真的成立，不成立就不写（避免出现「−12.7% 却说放量」这类反向话术）
    _good = []
    if o_wow is not None and our_o_wow is not None and o_wow > our_o_wow:
        _good.append('跑赢我司大盘：我司全店同窗口单量 %s → %s（%s），本间 %s → %s 单（%s），占我司单量 %s → %s。' % (
            W.num(p['our_orders']), W.num(c['our_orders']), W.signed_pct(our_o_wow),
            W.num(p['orders']), W.num(c['orders']), W.signed_pct(o_wow), W.pct(sh_o_p), W.pct(sh_o_c)))
    _up = [(k, _pv(p, k)['orders'], _pv(c, k)['orders'], _pv(p, k)['revenue'], _pv(c, k)['revenue'])
           for k in prod_names
           if _pv(p, k)['revenue'] >= 20000 and _pv(c, k)['revenue'] > _pv(p, k)['revenue'] * 1.1]
    _up.sort(key=lambda t: -(t[4] - t[3]))
    if _up:
        k, op_, oc_, rp_, rc_ = _up[0]
        _good.append('%s 放量：¥%s → ¥%s（%s），%s → %s 单（%s），占本间销售额 %s → %s。' % (
            k, W.num(rp_), W.num(rc_), W.signed_pct(rc_ / rp_ - 1), W.num(op_), W.num(oc_),
            W.signed_pct(oc_ / op_ - 1) if op_ else '新增', W.pct(rp_ / p['revenue']), W.pct(rc_ / c['revenue'])))
    if tail_rising and tail3 > c['revenue'] / c['days'] * 3:
        _good.append('末段抬升（%s ~ %s）：¥%s / ¥%s / ¥%s，最后三天占本期 %.1f%%，收官日 %s 创本期峰值 ¥%s。' % (
            c['rows'][-3]['date'], c['rows'][-1]['date'], W.num(c['rows'][-3]['revenue']),
            W.num(c['rows'][-2]['revenue']), W.num(c['rows'][-1]['revenue']),
            100 * tail3 / c['revenue'], peak['date'], W.num(peak['revenue'])))
    _up_a = sorted([(n, v, ap['by_anchor'][n]) for n, v in ac['by_anchor'].items()
                    if ap['by_anchor'].get(n) and ap['by_anchor'][n] >= 20000 and v > ap['by_anchor'][n]],
                   key=lambda t: -(t[1] - t[2]))
    if _up_a:
        _good.append('主播侧转化：%s。' % '、'.join(
            '%s ¥%s（%s）' % (n, W.num(v), W.signed_pct(v / pv - 1)) for n, v, pv in _up_a[:3]))
    if a_wow is not None and a_wow > 0.01:
        _good.append('均价上移：¥%s → ¥%s（%s）；¥1,000+ 价格带占本间 %.1f%% → %.1f%%。' % (
            W.num(p['avg']), W.num(c['avg']), W.signed_pct(a_wow), 100 * hi_p / p['revenue'], 100 * hi_c / c['revenue']))
    if b11c['orders'] > b11p['orders'] and (not _up or _up[0][0] != '小米手环11'):
        _good.append('手环11 在手表间补量：%d → %d 单（%s），¥%s → ¥%s。' % (
            b11p['orders'], b11c['orders'], W.signed_pct(b11c['orders'] / b11p['orders'] - 1),
            W.num(b11p['revenue']), W.num(b11c['revenue'])))
    ctx['good'] = _good[:5] or ['本期无突出增长项，重点看下方风险与建议。']
    # 不足与风险：同样逐条判定，方向不符的不写
    _bad = []
    if rev_wow < 0 or (o_wow or 0) < 0:
        _bad.append('收入端回落：销售额 ¥%s → ¥%s（%s）、单量 %s → %s 单（%s）—— 两项%s。' % (
            W.num(p['revenue']), W.num(c['revenue']), W.signed_pct(rev_wow),
            W.num(p['orders']), W.num(c['orders']), W.signed_pct(o_wow),
            '双降' if (rev_wow < 0 and (o_wow or 0) < 0) else '一升一降'))
    if a_wow is not None and a_wow < -0.01:
        _bad.append('均价 %s（¥%s → ¥%s）：高客单结构被稀释 —— S5 占比 %.1f%% → %.1f%%，'
                    'Watch 6 + 手环11 合计占比 %.1f%% → %.1f%%。' % (
                        W.signed_pct(a_wow), W.num(p['avg']), W.num(c['avg']),
                        100 * s5p['revenue'] / p['revenue'], 100 * s5c['revenue'] / c['revenue'],
                        100 * (w6p['revenue'] + b11p['revenue']) / p['revenue'],
                        100 * (w6c['revenue'] + b11c['revenue']) / c['revenue']))
    _bad.append('¥1,000+ 价格带：占比 %.1f%% → %.1f%%（¥%s → ¥%s）—— %s。' % (
        100 * hi_p / p['revenue'], 100 * hi_c / c['revenue'], W.num(hi_p), W.num(hi_c),
        '高端占比回升，但绝对量仍小，客单价缺支撑' if hi_c >= hi_p else '高端缺位，客单价被低价单品拉低'))
    if s5c['revenue'] < s5p['revenue'] * 0.7:
        _bad.append('S5 掉档：¥%s → ¥%s（%s），本期无同价位替代（Xiaomi Watch 5 仅 ¥%s）。' % (
            W.num(s5p['revenue']), W.num(s5c['revenue']), W.signed_pct(s5c['revenue'] / s5p['revenue'] - 1),
            W.num(c['products'].get('Xiaomi Watch 5', {'revenue': 0})['revenue'])))
    else:
        _bad.append('高端依赖单点：S5 ¥%s → ¥%s（%s），价格带上移主要靠这一款，需盯库存与排期。' % (
            W.num(s5p['revenue']), W.num(s5c['revenue']), W.signed_pct(s5c['revenue'] / s5p['revenue'] - 1)))
    _bad.append('时段结构：19:00–23:59 ¥%s → ¥%s（%s），其中 %02d:00 单小时 ¥%s → ¥%s（%s）；'
                '12:00–18:59 下午段 ¥%s → ¥%s（%s）—— %s。' % (
                    W.num(eve_p), W.num(eve_c), _sp(d_eve),
                    worst_h, W.num(hp[worst_h][1]), W.num(hc[worst_h][1]), _sp(d_wh),
                    W.num(aft_p), W.num(aft_c), _sp(d_aft), hour_w))
    _bad.append('低谷三天（%s ~ %s）日均 ¥%s，是本期最低段；本期日均 ¥%s、同期我司日均 ¥%s。' % (
        low3[0]['date'], low3[-1]['date'], W.num(low3_avg), W.num(daily_c),
        W.num(c['our_revenue'] / c['days'])))
    if gone or drop_a:
        _parts = []
        if gone:
            _parts.append('上期在岗的 %s 本期未出摊' % '、'.join(gone[:5]))
        if drop_a:
            _parts.append('、'.join('%s %s' % (n, W.signed_pct(ac['by_anchor'][n] / ap['by_anchor'][n] - 1))
                                   for n in drop_a) + ' 明显回落')
        _bad.append('主播供给波动：%s —— 经验与稳定性存在断档风险。' % '；'.join(_parts))
    ctx['bad'] = _bad[:6]
    top_hours = sorted(range(24), key=lambda h: -hc[h][1])[:3]
    ctx['plan'] = [
        '稳 Watch 6：本期日均 %.0f 单、单日峰值 %d 单（占本间销售额 %s），主推位与库存优先保障，避免断货丢单。' % (
            w6c['orders'] / c['days'], max(r['orders'] for r in c['rows']), W.pct(w6c['revenue'] / c['revenue'])),
        '补齐高客单：¥1,000+ 价格带本期 ¥%s（占本间 %.1f%%），把 Watch S5 / Watch 5 重新排进高转化时段'
        '（本期金额前三时段：%s）。' % (
            W.num(hi_c), 100 * hi_c / c['revenue'],
            '、'.join('%02d:00（¥%s）' % (h, W.num(hc[h][1])) for h in top_hours)),
        '主播排班固化：把 %s 的班次固定为主推班%s。' % (
            '、'.join(n for n, _ in top1),
            ('，%s 回到重点时段恢复手感' % '、'.join(drop_a)) if drop_a else ''),
        '复盘低谷三天（%s ~ %s，日均 ¥%s）：对照同期大盘与排播表，确认是流量下滑还是排班/货盘问题。' % (
            low3[0]['date'], low3[-1]['date'], W.num(low3_avg)),
        '搭售抬客单：用手环11（本期 %d 单，均价 ¥%s）+ 腕带/耳机做组合，把客单价从 ¥%s %s。' % (
            b11c['orders'], W.num(b11c['revenue'] / b11c['orders'] if b11c['orders'] else 0),
            W.num(c['avg']),
            ('继续往上抬（上期 ¥%s，本期已高于上期）' % W.num(p['avg'])) if c['avg'] >= p['avg']
            else ('拉回上期 ¥%s 的水平' % W.num(p['avg']))),
    ]

    wb = Workbook()
    wb.remove(wb.active)
    _, daily_rows = sheet_daily(wb, ctx)
    ctx['daily_rows'] = daily_rows
    _, ov_rows = sheet_overview(wb, ctx)
    ctx['ov'] = ov_rows
    sheet_summary(wb, ctx)
    sheet_products(wb, ctx)
    sheet_anchor(wb, ctx)
    sheet_hours(wb, ctx)
    sheet_notes(wb, ctx)
    # 表顺序：结论摘要在最前
    order = ['结论摘要', '汇总对比', '逐日明细', '商品结构', '主播业绩', '时段分布', '数据说明']
    wb._sheets = [wb[n] for n in order]
    for name, color in (('结论摘要', W.BRAND), ('汇总对比', W.BRAND_DK), ('逐日明细', 'F59E0B'),
                        ('商品结构', 'FF6900'), ('主播业绩', '2E7D32'), ('时段分布', '1E90FF'),
                        ('数据说明', '9AA3AF')):
        wb[name].sheet_properties.tabColor = color
    wb.save(out)
    print('已生成：%s' % out)
    print('本期 %s ~ %s：%d 单 / ¥%.2f（环比 %s / %s）｜均价 ¥%.2f（%s）' % (
        cur_start, cur_end, c['orders'], c['revenue'],
        W.signed_pct(c['orders'] / p['orders'] - 1), W.signed_pct(rev_wow), c['avg'],
        W.signed_pct(c['avg'] / p['avg'] - 1)))
    print('份额：我司单量 %.2f%%（%.2f%%）｜金额 %.2f%%（%.2f%%）' % (
        100 * c['orders'] / c['our_orders'], 100 * p['orders'] / p['our_orders'],
        100 * c['revenue'] / c['our_revenue'], 100 * p['revenue'] / p['our_revenue']))
    print('业绩口径 GSV：¥%.2f（%s）｜时段合计 ¥%.2f / ¥%.2f' % (
        ac['total'], W.signed_pct(ac['total'] / ap['total'] - 1), hc_tot, hp_tot))
    expect = {'file': out, 'room': room, 'sheets': wb.sheetnames,
              'cur': {'start': cur_start, 'end': cur_end, 'orders': c['orders'], 'revenue': c['revenue'],
                      'avg': c['avg'], 'our_orders': c['our_orders'], 'our_revenue': c['our_revenue'],
                      'site_orders': c['site_orders'], 'site_revenue': c['site_revenue']},
              'prev': {'start': prev_start, 'end': prev_end, 'orders': p['orders'], 'revenue': p['revenue'],
                       'avg': p['avg'], 'our_orders': p['our_orders'], 'our_revenue': p['our_revenue'],
                       'site_orders': p['site_orders'], 'site_revenue': p['site_revenue']},
              'anchor': {'cur': ac['total'], 'prev': ap['total']},
              'hours': {'cur': hc_tot, 'prev': hp_tot},
              'overview_rows': ov_rows, 'daily_rows': daily_rows}
    ck = os.path.join(ROOT, '_artifacts', 'watch_expect.json')
    with open(ck, 'w', encoding='utf-8') as fh:
        json.dump(expect, fh, ensure_ascii=False, indent=2)
    print('自检 JSON：%s' % ck)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--room', default='小米官方手表')
    ap.add_argument('--cur', nargs=2, default=['2026-09-29', '2026-10-07'])
    ap.add_argument('--prev', nargs=2, default=['2026-09-20', '2026-09-28'])
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    if a.out:
        out = a.out
    else:
        # 默认文件名跟着窗口走（房间名_起-止销售分析.xlsx），换窗口不必手写 --out
        md = lambda s: '%d.%d' % (int(s[5:7]), int(s[8:10]))
        out = os.path.join(W.DESKTOP, '%s_%s-%s销售分析.xlsx' % (a.room, md(a.cur[0]), md(a.cur[1])))
    return build(a.room, a.cur[0], a.cur[1], a.prev[0], a.prev[1], out)


if __name__ == '__main__':
    main()

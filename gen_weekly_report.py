# -*- coding: utf-8 -*-
"""生成 9.4-9.10 vs 8.29-9.3 四主要直播间周报 xlsx 到桌面。

数据源：sales_analysis/history.json
数值单元格为硬编码输入，派生指标（环比/日均/占比/合计）全部用 Excel 公式。
"""
import json
import os

from openpyxl import Workbook
from openpyxl.formatting.rule import DataBarRule
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = r"C:\Users\Administrator\Desktop\9.4-9.10周报_主要直播间对比分析.xlsx"

ROOMS = ['小米数码旗舰店', '小米官方手环直播间', '小米官旗手表直播间', '小米官方手表']

# ===== 主题 =====
FONT = '微软雅黑'
BRAND, BRAND_DK = 'FF6900', 'B34A00'
INK, INK_SOFT, INK_MUTE = '1F2937', '6B7280', '9AA3AF'
ZEBRA = 'FAFBFC'
TOTAL_BG = 'FFF4EC'
WARN_BG, OK_BG, HL_BG = 'FDECEA', 'EAF7F0', 'FFF8E7'
GRID = 'E2E6EB'

# ===== 字体 =====
F_TITLE = Font(name=FONT, size=17, bold=True, color=INK)
F_SUB = Font(name=FONT, size=9, color=INK_SOFT)
F_NOTE = Font(name=FONT, size=9, color='C0392B')
F_SEC = Font(name=FONT, size=11, bold=True, color=BRAND_DK)
F_HDR = Font(name=FONT, size=10, bold=True, color='FFFFFF')
F_BODY = Font(name=FONT, size=10, color=INK)
F_BOLD = Font(name=FONT, size=10, bold=True, color=INK)
F_INPUT = Font(name=FONT, size=10, color='1F4E79')     # 深蓝 = 硬编码输入
F_FORM = Font(name=FONT, size=10, color='404040')      # 深灰 = 公式
F_TINY = Font(name=FONT, size=9, color=INK_SOFT)

# ===== 填充 =====
P_HDR = PatternFill('solid', start_color=BRAND)
P_ZEBRA = PatternFill('solid', start_color=ZEBRA)
P_TOTAL = PatternFill('solid', start_color=TOTAL_BG)
P_WARN = PatternFill('solid', start_color=WARN_BG)
P_OK = PatternFill('solid', start_color=OK_BG)
P_HL = PatternFill('solid', start_color=HL_BG)

THIN = Side(style='thin', color=GRID)
MED = Side(style='medium', color=BRAND)
B_ALL = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
B_TOP = Border(left=THIN, right=THIN, top=MED, bottom=THIN)

MONEY = '¥#,##0;[Red]-¥#,##0;"-"'
MONEY1 = '¥#,##0.0;[Red]-¥#,##0.0;"-"'
PCT = '0.0%;[Red]-0.0%;"-"'
INT = '#,##0;[Red]-#,##0;"-"'
CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
LEFT = Alignment(horizontal='left', vertical='center')
RIGHT = Alignment(horizontal='right', vertical='center')
TOPWRAP = Alignment(horizontal='left', vertical='top', wrap_text=True)


def load():
    return json.load(open(os.path.join(ROOT, 'sales_analysis', 'history.json'), encoding='utf-8'))


def agg(history, start, end, room=None):
    ds = [d for d in history if start <= d['date'] <= end]
    o = v = 0
    for d in ds:
        if room:
            i = d['rooms'].get(room, {})
            o += i.get('orders', 0)
            v += i.get('revenue', 0)
        else:
            for r in ROOMS:
                i = d['rooms'].get(r, {})
                o += i.get('orders', 0)
                v += i.get('revenue', 0)
    return o, v, len(ds)


def title_block(ws, title, sub, note=None, span=7):
    ws['A1'] = title
    ws['A1'].font = F_TITLE
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=span)
    ws['A2'] = sub
    ws['A2'].font = F_SUB
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=span)
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 16
    if note:
        ws['A3'] = note
        ws['A3'].font = F_NOTE
        ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=span)
        ws.row_dimensions[3].height = 16


def header_row(ws, row, labels):
    for c, lab in enumerate(labels, start=1):
        cell = ws.cell(row=row, column=c, value=lab)
        cell.font = F_HDR
        cell.fill = P_HDR
        cell.alignment = CENTER
        cell.border = B_ALL
    ws.row_dimensions[row].height = 30


def section(ws, row, text, span=7):
    ws.cell(row=row, column=1, value=text).font = F_SEC
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
    ws.row_dimensions[row].height = 24


def no_grid(ws):
    ws.sheet_view.showGridLines = False


def band11(history):
    """{date: (全站, 我司, 4主要间)} 的手环11 销量"""
    from team_config import TEAM_MAP
    our = [r for r in set(k for d in history for k in d['rooms']) if TEAM_MAP.get(r) == '我司']
    out = {}
    for d in history:
        if not d['date'].startswith('2026-09'):
            continue
        p = d['products'].get('小米手环11', {})
        if not p.get('orders'):
            continue
        o = sum(d['rooms'].get(r, {}).get('products', {}).get('小米手环11', {}).get('orders', 0)
                for r in our)
        m = sum(d['rooms'].get(r, {}).get('products', {}).get('小米手环11', {}).get('orders', 0)
                for r in ROOMS)
        out[d['date']] = (p['orders'], o, m)
    return out


# ==================== Sheet 1 ====================
def sheet_compare(wb, h):
    ws = wb.active
    ws.title = '本周vs上周'
    no_grid(ws)
    title_block(
        ws, '四主要直播间 · 本周 vs 上周',
        '本周 9.4-9.10（7天）　对比　上周 8.29-9.3（6天）　｜　数据源 sales_analysis/history.json',
        '⚠ 两段天数不等（7天 vs 6天），总量对比会被天数放大；日均口径见「首发影响分段」页', span=10)

    heads = ['直播间', '上周订单', '本周订单', '订单环比',
             '上周销售额', '本周销售额', '销售额环比',
             '上周均价', '本周均价', '均价环比']
    header_row(ws, 5, heads)

    r0 = 6
    for k, room in enumerate(ROOMS):
        r = r0 + k
        lo, lv, _ = agg(h, '2026-08-29', '2026-09-03', room)
        to, tv, _ = agg(h, '2026-09-04', '2026-09-10', room)
        ws.cell(row=r, column=1, value=room).font = F_BOLD
        ws.cell(row=r, column=2, value=lo).font = F_INPUT
        ws.cell(row=r, column=3, value=to).font = F_INPUT
        ws.cell(row=r, column=4, value=f'=IFERROR((C{r}-B{r})/B{r},"-")').font = F_FORM
        ws.cell(row=r, column=5, value=lv).font = F_INPUT
        ws.cell(row=r, column=6, value=tv).font = F_INPUT
        ws.cell(row=r, column=7, value=f'=IFERROR((F{r}-E{r})/E{r},"-")').font = F_FORM
        ws.cell(row=r, column=8, value=f'=IFERROR(E{r}/B{r},"-")').font = F_FORM
        ws.cell(row=r, column=9, value=f'=IFERROR(F{r}/C{r},"-")').font = F_FORM
        ws.cell(row=r, column=10, value=f'=IFERROR((I{r}-H{r})/H{r},"-")').font = F_FORM
        if k % 2:
            for c in range(1, 11):
                ws.cell(row=r, column=c).fill = P_ZEBRA

    rt = r0 + len(ROOMS)
    ws.cell(row=rt, column=1, value='4 间合计').font = F_BOLD
    for col in (2, 3, 5, 6):
        L = chr(64 + col)
        ws.cell(row=rt, column=col, value=f'=SUM({L}{r0}:{L}{rt - 1})').font = F_BOLD
    for col, f in [(4, f'=IFERROR((C{rt}-B{rt})/B{rt},"-")'), (7, f'=IFERROR((F{rt}-E{rt})/E{rt},"-")'),
                   (8, f'=IFERROR(E{rt}/B{rt},"-")'), (9, f'=IFERROR(F{rt}/C{rt},"-")'),
                   (10, f'=IFERROR((I{rt}-H{rt})/H{rt},"-")')]:
        ws.cell(row=rt, column=col, value=f).font = F_BOLD

    for r in range(r0, rt + 1):
        is_tot = (r == rt)
        for c in range(1, 11):
            cell = ws.cell(row=r, column=c)
            cell.border = B_TOP if is_tot else B_ALL
            if is_tot:
                cell.fill = P_TOTAL
            cell.alignment = LEFT if c == 1 else RIGHT
            if c in (2, 3):
                cell.number_format = INT
            elif c in (5, 6):
                cell.number_format = MONEY
            elif c in (4, 7, 10):
                cell.number_format = PCT
            elif c in (8, 9):
                cell.number_format = MONEY1
        ws.row_dimensions[r].height = 22

    for c, w in enumerate([19, 11, 11, 10, 15, 15, 11, 10, 10, 10], start=1):
        ws.column_dimensions[chr(64 + c)].width = w
    ws.freeze_panes = 'B6'
    return ws


# ==================== Sheet 2 ====================
def sheet_target(wb, h):
    from team_config import TEAM_MAP
    b = band11(h)
    ws = wb.create_sheet('手环11目标进度')
    no_grid(ws)
    title_block(
        ws, '小米手环11 · 月净销 60,000 台目标进度',
        '口径：我司全部直播间（含商品卡，不含良米/机械空间等其他团队）　｜　订单口径，未扣退款',
        span=5)

    section(ws, 5, '一、逐日销量', span=5)
    header_row(ws, 6, ['日期', '全站（台）', '我司（台）', '四主要间（台）', '我司占比'])
    r0 = 7
    for k, (dt, (a, o, m)) in enumerate(sorted(b.items())):
        r = r0 + k
        ws.cell(row=r, column=1, value=dt).font = F_BODY
        ws.cell(row=r, column=2, value=a).font = F_INPUT
        ws.cell(row=r, column=3, value=o).font = F_INPUT
        ws.cell(row=r, column=4, value=m).font = F_INPUT
        ws.cell(row=r, column=5, value=f'=IFERROR(C{r}/B{r},"-")').font = F_FORM
        if k % 2:
            for c in range(1, 6):
                ws.cell(row=r, column=c).fill = P_ZEBRA
    rt = r0 + len(b)
    ws.cell(row=rt, column=1, value='累计').font = F_BOLD
    for c in (2, 3, 4):
        L = chr(64 + c)
        ws.cell(row=rt, column=c, value=f'=SUM({L}{r0}:{L}{rt - 1})').font = F_BOLD
    ws.cell(row=rt, column=5, value=f'=IFERROR(C{rt}/B{rt},"-")').font = F_BOLD
    for r in range(r0, rt + 1):
        is_tot = (r == rt)
        for c in range(1, 6):
            cell = ws.cell(row=r, column=c)
            cell.border = B_TOP if is_tot else B_ALL
            if is_tot:
                cell.fill = P_TOTAL
            if c in (2, 3, 4):
                cell.number_format = INT
                cell.alignment = RIGHT
            elif c == 5:
                cell.number_format = PCT
                cell.alignment = RIGHT
            else:
                cell.alignment = LEFT
        ws.row_dimensions[r].height = 20

    # 二、目标进度
    r = rt + 2
    section(ws, r, '二、目标进度', span=5)
    header_row(ws, r + 1, ['指标', '数值', '说明', '', ''])
    base = r + 2
    items = [
        ('月目标（净销台数）', 60000, 'input', '公司下达目标', None),
        ('剩余天数', 20, 'input', '9.11 - 9.30', None),
        ('已达成（我司 9.7-9.10）', f'=C{rt}', 'formula', '首发日起累计', None),
        ('达成率', f'=IFERROR(B{base + 2}/B{base},"-")', 'pct', '已达成 ÷ 月目标', None),
        ('剩余缺口', f'=B{base}-B{base + 2}', 'formula', '月目标 − 已达成', None),
        ('剩余期需日均', f'=IFERROR(B{base + 4}/B{base + 1},"-")', 'formula', '缺口 ÷ 剩余天数', None),
        ('首发后稳态日均（9.8-9.10）', f'=ROUND(AVERAGE(C{rt - 3}:C{rt - 1}),0)', 'formula', '当前实际水位', None),
        ('稳态 vs 需日均', f'=IFERROR(B{base + 6}/B{base + 5}-1,"-")', 'pct',
         '负值 = 按现状走会不达标', P_WARN),
    ]
    for k, (name, val, kind, note, fill) in enumerate(items):
        rr = base + k
        ws.cell(row=rr, column=1, value=name).font = F_BOLD
        c = ws.cell(row=rr, column=2, value=val)
        c.font = F_INPUT if kind == 'input' else F_FORM
        c.number_format = PCT if kind == 'pct' else INT
        c.alignment = RIGHT
        ws.cell(row=rr, column=3, value=note).font = F_TINY
        ws.cell(row=rr, column=3).alignment = LEFT
        for cc in range(1, 6):
            ws.cell(row=rr, column=cc).border = B_ALL
            if fill:
                ws.cell(row=rr, column=cc).fill = fill
        ws.row_dimensions[rr].height = 21

    # 三、情景测算
    r = base + len(items) + 2
    section(ws, r, '三、剩余 20 天情景测算', span=5)
    header_row(ws, r + 1, ['情景', '假设日均（台）', '剩余期销量', '月末累计', '达成率'])
    sr = r + 2
    scen = [('热度回落 20%', 0.8), ('维持现状', 1.0), ('提升 5%', 1.05), ('提升 10%', 1.10)]
    for k, (label, mult) in enumerate(scen):
        rr = sr + k
        ws.cell(row=rr, column=1, value=label).font = F_BOLD
        ws.cell(row=rr, column=2, value=f'=ROUND($B${base + 6}*{mult},0)').font = F_FORM
        ws.cell(row=rr, column=3, value=f'=B{rr}*$B${base + 1}').font = F_FORM
        ws.cell(row=rr, column=4, value=f'=$B${base + 2}+C{rr}').font = F_FORM
        ws.cell(row=rr, column=5, value=f'=IFERROR(D{rr}/$B${base},"-")').font = F_FORM
        for c in range(1, 6):
            cell = ws.cell(row=rr, column=c)
            cell.border = B_ALL
            if c > 1:
                cell.number_format = PCT if c == 5 else INT
                cell.alignment = RIGHT
            else:
                cell.alignment = LEFT
        if k == 1:
            for c in range(1, 6):
                ws.cell(row=rr, column=c).fill = P_HL
        ws.row_dimensions[rr].height = 21

    # 四、我司各来源贡献
    r = sr + len(scen) + 2
    section(ws, r, '四、我司各来源贡献（9.7-9.10）', span=5)
    header_row(ws, r + 1, ['来源', '手环11 台数', '占我司比重', '', ''])
    src = {}
    for d in h:
        if not d['date'].startswith('2026-09'):
            continue
        for rn, ri in d['rooms'].items():
            if TEAM_MAP.get(rn) != '我司':
                continue
            n = ri.get('products', {}).get('小米手环11', {}).get('orders', 0)
            if n:
                src[rn] = src.get(rn, 0) + n
    rr = r + 2
    first_src = rr
    last_src = rr + len(src) - 1
    for k, (name, n) in enumerate(sorted(src.items(), key=lambda kv: -kv[1])):
        ws.cell(row=rr, column=1, value=name).font = F_BODY
        ws.cell(row=rr, column=2, value=n).font = F_INPUT
        cell = ws.cell(row=rr, column=3, value=f'=IFERROR(B{rr}/$B${last_src + 1},"-")')
        cell.font = F_FORM
        for c in range(1, 6):
            cl = ws.cell(row=rr, column=c)
            cl.border = B_ALL
            if c == 2:
                cl.number_format = INT
                cl.alignment = RIGHT
            elif c == 3:
                cl.number_format = PCT
                cl.alignment = RIGHT
            else:
                cl.alignment = LEFT
        if k % 2:
            for c in range(1, 6):
                ws.cell(row=rr, column=c).fill = P_ZEBRA
        ws.row_dimensions[rr].height = 21
        rr += 1
    ws.cell(row=rr, column=1, value='我司合计').font = F_BOLD
    ws.cell(row=rr, column=2, value=f'=SUM(B{first_src}:B{rr - 1})').font = F_BOLD
    ws.cell(row=rr, column=3, value='=1').font = F_BOLD
    for c in range(1, 6):
        cl = ws.cell(row=rr, column=c)
        cl.border = B_TOP
        cl.fill = P_TOTAL
        if c in (2, 3):
            cl.number_format = INT if c == 2 else PCT
            cl.alignment = RIGHT
    ws.conditional_formatting.add(
        f'B{first_src}:B{rr - 1}',
        DataBarRule(start_type='num', start_value=0, end_type='num', end_value=max(src.values()),
                    color='FFB27A', showValue=True))

    for c, w in enumerate([27, 15, 14, 14, 12], start=1):
        ws.column_dimensions[chr(64 + c)].width = w
    return ws


# ==================== Sheet 3 ====================
def sheet_segment(wb, h):
    ws = wb.create_sheet('首发影响分段')
    no_grid(ws)
    title_block(
        ws, '手环11 首发（9.7）对各直播间的影响',
        '用日均口径消除天数差异　｜　首发日全站售出手环11 59,883 台 / ¥19,337,118', span=7)
    header_row(ws, 4, ['直播间', '上周日均\n8.29-9.3\n(6天)', '首发前日均\n9.4-9.6\n(3天)',
                       '首发日\n9.7', '首发后日均\n9.8-9.10\n(3天)',
                       '首发后 vs 首发前', '首发后 vs 上周'])
    segs = [('2026-08-29', '2026-09-03'), ('2026-09-04', '2026-09-06'),
            ('2026-09-07', '2026-09-07'), ('2026-09-08', '2026-09-10')]
    r0 = 5
    for k, room in enumerate(ROOMS):
        r = r0 + k
        vals = [agg(h, a, b, room) for a, b in segs]
        ws.cell(row=r, column=1, value=room).font = F_BOLD
        for j, (o, v, n) in enumerate(vals):
            ws.cell(row=r, column=2 + j, value=round(v / n)).font = F_INPUT
        ws.cell(row=r, column=6, value=f'=IFERROR((E{r}-C{r})/C{r},"-")').font = F_FORM
        ws.cell(row=r, column=7, value=f'=IFERROR((E{r}-B{r})/B{r},"-")').font = F_FORM
        if k % 2:
            for c in range(1, 8):
                ws.cell(row=r, column=c).fill = P_ZEBRA
    rt = r0 + len(ROOMS)
    tvals = [agg(h, a, b) for a, b in segs]
    ws.cell(row=rt, column=1, value='4 间合计').font = F_BOLD
    for j, (o, v, n) in enumerate(tvals):
        ws.cell(row=rt, column=2 + j, value=round(v / n)).font = F_BOLD
    ws.cell(row=rt, column=6, value=f'=IFERROR((E{rt}-C{rt})/C{rt},"-")').font = F_BOLD
    ws.cell(row=rt, column=7, value=f'=IFERROR((E{rt}-B{rt})/B{rt},"-")').font = F_BOLD
    for r in range(r0, rt + 1):
        is_tot = (r == rt)
        for c in range(1, 8):
            cell = ws.cell(row=r, column=c)
            cell.border = B_TOP if is_tot else B_ALL
            if is_tot:
                cell.fill = P_TOTAL
            if c == 1:
                cell.alignment = LEFT
            else:
                cell.alignment = RIGHT
                cell.number_format = PCT if c in (6, 7) else MONEY
        ws.row_dimensions[r].height = 22
    for c, w in enumerate([19, 15, 15, 14, 15, 16, 15], start=1):
        ws.column_dimensions[chr(64 + c)].width = w
    return ws


# ==================== Sheet 4 ====================
def sheet_daily(wb, h):
    ws = wb.create_sheet('逐日明细')
    no_grid(ws)
    title_block(ws, '逐日销售额明细（8.29 - 9.10）', '单位：元　｜　首发日 9.7 已标注', span=7)
    header_row(ws, 3, ['日期', '阶段'] + ROOMS + ['4间合计'])
    seg_of = {}
    for d in h:
        dt = d['date']
        if dt == '2026-09-07':
            seg_of[dt] = '首发日'
        elif '2026-08-29' <= dt <= '2026-09-03':
            seg_of[dt] = '上周'
        elif '2026-09-04' <= dt <= '2026-09-06':
            seg_of[dt] = '首发前'
        elif '2026-09-08' <= dt <= '2026-09-10':
            seg_of[dt] = '首发后'
    r0 = 4
    days = [d for d in h if '2026-08-29' <= d['date'] <= '2026-09-10']
    for k, d in enumerate(days):
        r = r0 + k
        ws.cell(row=r, column=1, value=d['date']).font = F_BODY
        tag = seg_of.get(d['date'], '')
        tc = ws.cell(row=r, column=2, value=tag)
        tc.font = Font(name=FONT, size=9, bold=(tag == '首发日'),
                       color=BRAND_DK if tag == '首发日' else INK_SOFT)
        tc.alignment = CENTER
        for j, room in enumerate(ROOMS):
            ws.cell(row=r, column=3 + j,
                    value=round(d['rooms'].get(room, {}).get('revenue', 0))).font = F_INPUT
        ws.cell(row=r, column=7, value=f'=SUM(C{r}:F{r})').font = F_FORM
        if tag == '首发日':
            for c in range(1, 8):
                ws.cell(row=r, column=c).fill = P_HL
        elif k % 2:
            for c in range(1, 8):
                ws.cell(row=r, column=c).fill = P_ZEBRA
    rt = r0 + len(days)
    ws.cell(row=rt, column=1, value='合计').font = F_BOLD
    for c in range(3, 8):
        L = chr(64 + c)
        ws.cell(row=rt, column=c, value=f'=SUM({L}{r0}:{L}{rt - 1})').font = F_BOLD
    for r in range(r0, rt + 1):
        is_tot = (r == rt)
        for c in range(1, 8):
            cell = ws.cell(row=r, column=c)
            cell.border = B_TOP if is_tot else B_ALL
            if is_tot:
                cell.fill = P_TOTAL
            if c >= 3:
                cell.number_format = MONEY
                cell.alignment = RIGHT
            elif c == 1:
                cell.alignment = LEFT
        ws.row_dimensions[r].height = 21
    for c, w in enumerate([12, 9, 16, 18, 16, 15, 15], start=1):
        ws.column_dimensions[chr(64 + c)].width = w
    ws.freeze_panes = 'C4'
    return ws


# ==================== Sheet 4.5 手表间诊断 ====================
def sheet_watch(wb, h):
    from team_config import TEAM_MAP
    ws = wb.create_sheet('手表间诊断')
    no_grid(ws)
    title_block(
        ws, '两个手表直播间 · 问题诊断',
        '手表直播间的核心指标是「手表转化」；手环11 是拉流量工具，不用它衡量手表间表现', span=7)

    # --- 品类大盘 ---
    def prod_stat(a, b, key, team=None):
        ds = [d for d in h if a <= d['date'] <= b]
        o = v = 0
        for d in ds:
            for rn, ri in d['rooms'].items():
                if team and TEAM_MAP.get(rn) != team:
                    continue
                p = ri.get('products', {}).get(key, {})
                o += p.get('orders', 0)
                v += p.get('revenue', 0)
        return o, v

    section(ws, 5, '一、手表品类：大盘 / 我司 / 良米（台数）', span=7)
    header_row(ws, 6, ['产品', '全站 上周', '全站 本周', '全站变化',
                       '我司 上周', '我司 本周', '我司份额变化'])
    r0 = 7
    cats = ['REDMI Watch 6', 'Xiaomi Watch S5', '小米手环10 Pro']
    for k, key in enumerate(cats):
        r = r0 + k
        al, _ = prod_stat('2026-08-29', '2026-09-03', key)
        at, _ = prod_stat('2026-09-04', '2026-09-10', key)
        ol, _ = prod_stat('2026-08-29', '2026-09-03', key, '我司')
        ot, _ = prod_stat('2026-09-04', '2026-09-10', key, '我司')
        ws.cell(row=r, column=1, value=key).font = F_BOLD
        ws.cell(row=r, column=2, value=al).font = F_INPUT
        ws.cell(row=r, column=3, value=at).font = F_INPUT
        ws.cell(row=r, column=4, value=f'=IFERROR(C{r}/B{r}-1,"-")').font = F_FORM
        ws.cell(row=r, column=5, value=ol).font = F_INPUT
        ws.cell(row=r, column=6, value=ot).font = F_INPUT
        ws.cell(row=r, column=7,
                value=f'=IFERROR(F{r}/C{r}-E{r}/B{r},"-")').font = F_FORM
        if k % 2:
            for c in range(1, 8):
                ws.cell(row=r, column=c).fill = P_ZEBRA
    rt = r0 + len(cats)
    for r in range(r0, rt):
        for c in range(1, 8):
            cell = ws.cell(row=r, column=c)
            cell.border = B_ALL
            if c == 1:
                cell.alignment = LEFT
            else:
                cell.alignment = RIGHT
                cell.number_format = PCT if c in (4, 7) else INT
        ws.row_dimensions[r].height = 21
    ws.cell(row=rt, column=1, value='→ 全站基本持平甚至上涨，我司大跌、良米大涨：问题不在品，在我司丢份额').font = F_NOTE
    ws.merge_cells(start_row=rt, start_column=1, end_row=rt, end_column=7)
    ws.row_dimensions[rt].height = 20

    # --- 分间分产品 ---
    def room_products(a, b, room):
        ds = [d for d in h if a <= d['date'] <= b]
        out = {}
        for d in ds:
            for p, i in d['rooms'].get(room, {}).get('products', {}).items():
                e = out.setdefault(p, {'orders': 0, 'revenue': 0})
                e['orders'] += i['orders']
                e['revenue'] += i['revenue']
        return out

    r = rt + 2
    for room in ['小米官方手表', '小米官旗手表直播间']:
        section(ws, r, f'二、{room} · 分产品拆解' if room == '小米官方手表'
                else f'三、{room} · 分产品拆解', span=7)
        header_row(ws, r + 1, ['产品', '上周销售额', '本周销售额', '销售额变化',
                               '上周单量', '本周单量', '单量变化'])
        lw = room_products('2026-08-29', '2026-09-03', room)
        tw = room_products('2026-09-04', '2026-09-10', room)
        keys = sorted(set(lw) | set(tw), key=lambda k: -tw.get(k, {}).get('revenue', 0))
        keys = [k for k in keys if (lw.get(k, {}).get('revenue', 0) +
                                    tw.get(k, {}).get('revenue', 0)) > 500][:6]
        rr = r + 2
        for k, key in enumerate(keys):
            a_ = lw.get(key, {})
            b_ = tw.get(key, {})
            ws.cell(row=rr, column=1, value=key).font = F_BOLD
            ws.cell(row=rr, column=2, value=round(a_.get('revenue', 0))).font = F_INPUT
            ws.cell(row=rr, column=3, value=round(b_.get('revenue', 0))).font = F_INPUT
            ws.cell(row=rr, column=4,
                    value=f'=IFERROR(C{rr}/B{rr}-1,"新增")').font = F_FORM
            ws.cell(row=rr, column=5, value=a_.get('orders', 0)).font = F_INPUT
            ws.cell(row=rr, column=6, value=b_.get('orders', 0)).font = F_INPUT
            ws.cell(row=rr, column=7,
                    value=f'=IFERROR(F{rr}/E{rr}-1,"新增")').font = F_FORM
            if key == 'REDMI Watch 6' and room == '小米官方手表':
                for c in range(1, 8):
                    ws.cell(row=rr, column=c).fill = P_WARN
            if key == '小米手环10 Pro' and room == '小米官旗手表直播间':
                for c in range(1, 8):
                    ws.cell(row=rr, column=c).fill = P_WARN
            for c in range(1, 8):
                cell = ws.cell(row=rr, column=c)
                cell.border = B_ALL
                if c == 1:
                    cell.alignment = LEFT
                else:
                    cell.alignment = RIGHT
                    if c in (2, 3):
                        cell.number_format = MONEY
                    elif c in (4, 7):
                        cell.number_format = PCT
                    else:
                        cell.number_format = INT
            ws.row_dimensions[rr].height = 21
            rr += 1
        r = rr + 1

    # --- 诊断结论 ---
    section(ws, r, '四、诊断结论', span=7)
    header_row(ws, r + 1, ['#', '诊断', '数据依据', '', '', '', ''])
    diag = [
        ('小米官方手表：手环11 的流量进来了，但没转化成手表销量',
         '该间手环类全线上涨（手环10Pro +57%、手环11 新增 121 台），'
         '但核心品 REDMI Watch 6 单量 3,436→2,344 台（-32%），而它占该间 88% 营收', P_WARN),
        ('小米官旗手表直播间：全品类同步下滑，无一是幸免',
         'Watch S5 -23%、Watch 5 -16%、REDMI Watch 6 -23%；'
         '小米手环10 Pro 更是从 158 单崩到 14 单（-91%），需单独排查是否为断货/替换', P_WARN),
        ('两个间的共同根因：我司在手表品类上系统性丢份额给良米',
         'REDMI Watch 6 我司份额 59.0%→41.6%（-17.4pp），我司 -1,506 台而良米 +1,207 台；'
         'Watch S5 我司 26.8%→18.1%（-8.7pp）', None),
        ('优先级：官方手表的量级是官旗手表的 6 倍，应先救它',
         '上周日均 官方手表 ¥301,912 vs 官旗手表 ¥45,572', None),
    ]
    rr = r + 2
    for k, (a, b, fill) in enumerate(diag):
        ws.cell(row=rr, column=1, value=k + 1).font = Font(name=FONT, size=10, bold=True, color=BRAND)
        ws.cell(row=rr, column=1).alignment = Alignment(horizontal='center', vertical='top')
        ws.cell(row=rr, column=2, value=a).font = F_BOLD
        ws.cell(row=rr, column=3, value=b).font = F_TINY
        ws.merge_cells(start_row=rr, start_column=3, end_row=rr, end_column=7)
        for c in range(1, 8):
            cell = ws.cell(row=rr, column=c)
            cell.border = B_ALL
            if c > 1:
                cell.alignment = TOPWRAP
            if fill:
                cell.fill = fill
        ws.row_dimensions[rr].height = 40
        rr += 1

    for c, w in enumerate([24, 13, 13, 11, 11, 11, 12], start=1):
        ws.column_dimensions[chr(64 + c)].width = w
    ws.column_dimensions['A'].width = 26
    return ws


# ==================== Sheet 5 ====================
def sheet_analysis(wb):
    ws = wb.create_sheet('分析与规划')
    no_grid(ws)
    title_block(ws, '数据解读与下周规划', '周期 9.11 - 9.17　｜　目标导向：手环11 月净销 60,000 台', span=4)

    ws.cell(row=5, column=1, value='一、核心结论').font = F_SEC
    ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=4)
    header_row(ws, 6, ['#', '结论', '数据依据', ''])
    concl = [
        ('【定位纠偏】手表直播间的核心指标是「手表转化」；手环11 是拉流量的工具，'
         '不能用手环11 销量去衡量手表间的表现',
         '两个手表间的手环11 销量本就有限（官方手表 121 台、官旗手表 19 台）；'
         '真正要看的是它们把手表卖得怎么样', P_HL),
        ('【问题性质】不是品不行，是我司在手表品类上系统性丢份额给良米',
         'REDMI Watch 6 全站仅 -5%，我司 -33%，良米 +53%；'
         'Xiaomi Watch S5 全站 +22%，我司 -18%，良米 +35%', P_WARN),
        ('【份额】我司 REDMI Watch 6 份额 59.0%→41.6%（-17.4pp）；Watch S5 26.8%→18.1%（-8.7pp）',
         'Watch 6 我司 -1,506 台、良米 +1,207 台 —— 丢掉的份额几乎被良米全额接收', P_WARN),
        ('【官方手表诊断】手环11 的流量进来了，但没转化成手表销量',
         '该间手环类全线上涨（手环10Pro +57%、手环11 新增 121 台），'
         '但核心品 REDMI Watch 6 单量 3,436→2,344 台（-32%），而它占该间 88% 营收', P_WARN),
        ('【官旗手表诊断】全品类同步下滑，无一是幸免',
         'Watch S5 -23%、Watch 5 -16%、REDMI Watch 6 -23%；'
         '小米手环10 Pro 从 158 单崩到 14 单（-91%），需单独排查断货/替换', P_WARN),
        ('【优先级】官方手表的量级是官旗手表的 6 倍，应先救它',
         '上周日均 官方手表 ¥301,912 vs 官旗手表 ¥45,572', None),
        ('【手环11 进度】月净销 60,000 台，已达成 21,583 台（36.0%），剩余 20 天需日均 1,921 台',
         '9.7-9.10 累计；这是全公司级目标，含商品卡，不含其他团队直播间', P_HL),
        ('【手环11 风险】首发后稳态日均只有 1,905 台，低于所需的 1,921 台',
         '按现状走，月末约 59,683 台，差 317 台不达标 —— 目标卡在临界点上', P_WARN),
        ('【手环11 可达性】只需在稳态基础上提升 5%（日均 2,000 台）即可稳过 6 万线',
         '并非激进目标，但没有任何冗余空间，必须主动加动作而不是「顺其自然」', None),
        ('【口径提醒】history.json 是订单口径，若「净销」需扣退款，实际需更高出货量',
         '如退款率 10%，则需出货 66,667 台，日均要求从 1,921 提到 2,254 台', P_WARN),
        ('【本周大盘】四间合计 21,897 单 / ¥7,738,000，环比订单 +257.6%、金额 +164.6%',
         '但增量 61% 来自 9/7 首发日（当天 ¥4,725,254），是事件驱动而非自然增长', None),
        ('【剔除首发日】本周日均 ¥502,124 vs 上周 ¥487,328，仅 +3.0%',
         '自然增长基本停滞；首发前 9.4-9.6 日均甚至只有 ¥320,880，比上周 -34%', None),
        ('【渠道结构】我司手环11 的 56.4% 来自小米数码旗舰店，商品卡贡献 16.2%（第三大来源）',
         '数码 12,164 台 / 手环直播间 5,511 台 / 商品卡 3,506 台；'
         '商品卡属被动承接，若目标吃紧需评估其可拉动空间', None),
    ]
    for k, (a, b, fill) in enumerate(concl):
        r = 7 + k
        ws.cell(row=r, column=1, value=k + 1).font = Font(name=FONT, size=10, bold=True, color=BRAND)
        ws.cell(row=r, column=2, value=a).font = F_BOLD
        ws.cell(row=r, column=3, value=b).font = F_TINY
        for c in range(1, 5):
            cell = ws.cell(row=r, column=c)
            cell.border = B_ALL
            cell.alignment = TOPWRAP if c > 1 else Alignment(horizontal='center', vertical='top')
            if fill:
                cell.fill = fill
        ws.row_dimensions[r].height = 34

    r = 7 + len(concl) + 1
    ws.cell(row=r, column=1, value='二、下周规划（9.11 - 9.17）').font = F_SEC
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    header_row(ws, r + 1, ['优先级', '直播间', '重点动作', '目标'])
    plan = [
        ('P0', '手环11 冲量\n（我司全部直播间）',
         '本月一号目标：日均必须从 1,905 提到 2,000 台以上，且没有任何冗余。'
         '① 手环11 固定讲解时段（每小时至少 2 轮），首发热度期不能让品断档；'
         '② 直播间贴片 / 背景板 / 置顶评论强化手环11；'
         '③ 做好关联搭配（表带、充电、手环10Pro 清库）；'
         '④ 用首发期积累的人群包做二次触达与复购；'
         '⑤ 每日盯 4 主要间的分小时销量，哪间掉队当天就补',
         '日均 ≥2,000 台\n月末累计 ≥60,000 台', P_WARN),
        ('P0', '小米官方手表\n（回归手表）',
         '这间是最大的手表间（日均 ¥30万），核心品 REDMI Watch 6 占其 88% 营收，本周掉了 32%。'
         '手环11 的流量确实进来了（手环类全线上涨），但没转化成手表销量 —— '
         '直播间在卖便宜的手环，手表没承接住。动作：'
         '① 设手表专属讲解时段，手环11 讲完必须带出手表对比与关联；'
         '② 排查 Watch 6 掉量根因（货盘 / 价格 / 话术 / 排班），拉分小时数据定位掉在哪个班次；'
         '③ 对齐良米打法 —— 同期良米 Watch 6 +53%，我们没有理由做不到',
         'REDMI Watch 6\n单量回到 3,000 台/周\n我司份额重回 50%+', P_WARN),
        ('P1', '小米官旗手表直播间\n（回归手表）',
         '全品类同步下滑，其中小米手环10 Pro 从 158 单崩到 14 单（-91%），'
         '需先确认是否断货或被手环11 替换。核心品 Xiaomi Watch S5 掉 24%。'
         '这间量级较小（日均 ¥4.5万），先查清 10Pro 崩盘原因，再谈手表动销',
         '日均 ≥¥35,000\n环比转正', None),
        ('P1', '四主要间（复盘）',
         '手环类靠首发拉动了流量，但手表品类没接住，份额被良米拿走。'
         '复盘「手环11 引流 → 手表转化」的承接链路，沉淀 SOP 供双11 复用',
         '手表品类份额 ≥50%', None),
    ]
    for k, (p, room, act, goal, fill) in enumerate(plan):
        rr = r + 2 + k
        pc = ws.cell(row=rr, column=1, value=p)
        pc.font = Font(name=FONT, size=11, bold=True,
                       color='C0392B' if p == 'P0' else BRAND_DK)
        pc.alignment = Alignment(horizontal='center', vertical='top')
        ws.cell(row=rr, column=2, value=room).font = F_BOLD
        ws.cell(row=rr, column=3, value=act).font = F_BODY
        gc = ws.cell(row=rr, column=4, value=goal)
        gc.font = Font(name=FONT, size=10, bold=True, color=BRAND_DK)
        for c in range(1, 5):
            cell = ws.cell(row=rr, column=c)
            cell.border = B_ALL
            cell.alignment = TOPWRAP if c > 1 else Alignment(horizontal='center', vertical='top')
            if fill:
                cell.fill = fill
        ws.row_dimensions[rr].height = 74

    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 66
    ws.column_dimensions['D'].width = 24
    return ws


# ==================== Sheet 6 运营共识与人员 ====================
def sheet_ops(wb):
    ws = wb.create_sheet('扭亏共识与人员')
    no_grid(ws)
    title_block(ws, '直播间扭亏共识 · 人员稳定性', '口径：手环 / 手表 / 耳机直播间　｜　数据周期 9.4-9.10', span=4)

    ws.cell(row=5, column=1, value='一、直播间扭亏共识').font = F_SEC
    ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=4)
    header_row(ws, 6, ['#', '共识 / 议题', '数据依据与动作', '状态'])
    rows1 = [
        ('止损优先于提效',
         '我司直播间本周合计 ¥7,869,313，前 3 大间占 96.0%：'
         '数码旗舰店 ¥602,291/日（53.6%）、官方手环直播间 ¥274,963/日（24.5%）、'
         '官方手表 ¥202,004/日（18.0%），其余全部仅 4.0%。\n'
         '低效待收缩：小米智能设备旗舰店 ¥2,339/日（环比 -93%）、'
         '官方耳机直播间 ¥1,928/日（仅 2/7 天开播）、手环10Pro 与 AI眼镜 0 数据。\n'
         '例外：手环官旗直播间日均 ¥14,492 但环比 +829%，处回升通道，保留观察',
         '待执行'),
        ('耳机直播间 · 小米耳机定金预售方案',
         '本周仅 ¥13,494 / 60 单，只有 2/7 天开播；产品结构全是低客单——'
         'REDMI Buds 8 系列 ¥99-317、Xiaomi Buds 6 ¥540、'
         '最高的 Xiaomi Buds 5 Pro 也仅 ¥874。\n'
         '客单低、铺不出量级，自然流量撬不动。'
         '方案需拉通整个 9 月，便于政策申请与收割节点，形成持续曝光而非零散开播',
         '方案制定中'),
        ('高端表直播间 · 节点收割',
         '小米官旗手表直播间（均价 ¥885，全司最高）：销售额 ¥273,434→¥183,193（-33%）、'
         '单量 386→207（-46%），但均价 ¥708→¥885（+25%），9/5-9/6 破 ¥1,000。\n'
         '人少了但质量更高 → 非节点收缩直播时长、压缩人力，节点集中资源收割',
         '已定策略'),
    ]
    rr = 7
    for k, (a, b, c) in enumerate(rows1):
        ws.cell(row=rr, column=1, value=k + 1).font = Font(name=FONT, size=10, bold=True, color=BRAND)
        ws.cell(row=rr, column=1).alignment = Alignment(horizontal='center', vertical='top')
        ws.cell(row=rr, column=2, value=a).font = F_BOLD
        ws.cell(row=rr, column=3, value=b).font = F_BODY
        ws.cell(row=rr, column=4, value=c).font = F_TINY
        for c_ in range(1, 5):
            cell = ws.cell(row=rr, column=c_)
            cell.border = B_ALL
            if c_ > 1:
                cell.alignment = TOPWRAP
            else:
                cell.alignment = Alignment(horizontal='center', vertical='top')
        ws.row_dimensions[rr].height = 82
        rr += 1

    rr += 1
    ws.cell(row=rr, column=1, value='二、人员稳定性').font = F_SEC
    ws.merge_cells(start_row=rr, start_column=1, end_row=rr, end_column=4)
    header_row(ws, rr + 1, ['#', '问题反馈', '解决措施', '状态'])
    rows2 = [
        ('排班希望早点发，A 班能早点睡觉', '排班每天下午 5:30 前必须发出', '已定规则'),
        ('穿戴组主播反映样机拿得有点慢',
         '后续直播间样机充足，各直播间配一套；由该间对应运营 / 主播组长统一管理', '推进中'),
        ('登记礼赠电脑不够用，建议增加 1 台',
         '礼赠 9 月统一切换班牛系统，主播无需手动登记', '9 月落地'),
        ('排班建议 3 天换一次且不平均', '近期稳定执行中', '执行中'),
        ('建议每个直播间配一台手机', '见下方配备清单', '部分完成'),
    ]
    r2 = rr + 2
    for k, (a, b, c) in enumerate(rows2):
        x = r2 + k
        ws.cell(row=x, column=1, value=k + 1).font = Font(name=FONT, size=10, bold=True, color=BRAND)
        ws.cell(row=x, column=1).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(row=x, column=2, value=a).font = F_BOLD
        ws.cell(row=x, column=3, value=b).font = F_BODY
        ws.cell(row=x, column=4, value=c).font = F_TINY
        for c_ in range(1, 5):
            cell = ws.cell(row=x, column=c_)
            cell.border = B_ALL
            cell.alignment = TOPWRAP if c_ > 1 else Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[x].height = 32

    r3 = r2 + len(rows2) + 1
    ws.cell(row=r3, column=1, value='三、手机配备清单（手环 / 手表 / 耳机口径）').font = F_SEC
    ws.merge_cells(start_row=r3, start_column=1, end_row=r3, end_column=4)
    header_row(ws, r3 + 1, ['状态', '直播间', '本周日均销售额', '备注'])
    phones = [
        ('✅ 已配备', '小米数码旗舰店', 602291, ''),
        ('✅ 已配备', '小米官方手环直播间', 274963, ''),
        ('✅ 已配备', '小米官方手表（大号）', 202004, ''),
        ('✅ 已配备', '小米官旗手表直播间（小号）', 26170, ''),
        ('❌ 待配备', '小米手环官旗直播间', 14492, '本周环比 +829%，建议优先配备'),
        ('❌ 待配备', '小米官方耳机直播间', 1928, '结合耳机定金预售方案一并考虑'),
    ]
    x = r3 + 2
    for k, (st, room, avg, note) in enumerate(phones):
        ws.cell(row=x, column=1, value=st).font = Font(
            name=FONT, size=10, bold=True, color='1E7A46' if st.startswith('✅') else 'C0392B')
        ws.cell(row=x, column=1).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(row=x, column=2, value=room).font = F_BOLD
        ws.cell(row=x, column=3, value=avg).font = F_INPUT
        ws.cell(row=x, column=3).number_format = MONEY
        ws.cell(row=x, column=3).alignment = RIGHT
        ws.cell(row=x, column=4, value=note).font = F_TINY
        for c_ in range(1, 5):
            cell = ws.cell(row=x, column=c_)
            cell.border = B_ALL
            if c_ in (2, 4):
                cell.alignment = TOPWRAP
            if not st.startswith('✅'):
                cell.fill = P_WARN
        ws.row_dimensions[x].height = 26
        x += 1
    ws.cell(row=x, column=1, value='注：小米手环10Pro直播间、小米AI眼镜直播间本周无直播数据，'
                                   '待确认是否仍在运营，确认后再定是否配备').font = F_TINY
    ws.merge_cells(start_row=x, start_column=1, end_row=x, end_column=4)
    ws.row_dimensions[x].height = 20

    ws.column_dimensions['A'].width = 13
    ws.column_dimensions['B'].width = 26
    ws.column_dimensions['C'].width = 72
    ws.column_dimensions['D'].width = 26
    return ws


def main():
    h = load()
    wb = Workbook()
    sheet_compare(wb, h)
    sheet_target(wb, h)
    sheet_segment(wb, h)
    sheet_watch(wb, h)
    sheet_daily(wb, h)
    sheet_analysis(wb)
    sheet_ops(wb)
    wb.save(OUT)
    print('已生成:', OUT)


if __name__ == '__main__':
    main()

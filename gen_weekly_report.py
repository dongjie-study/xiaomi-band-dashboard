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


# ==================== Sheet 5 ====================
def sheet_analysis(wb):
    ws = wb.create_sheet('分析与规划')
    no_grid(ws)
    title_block(ws, '数据解读与下周规划', '周期 9.11 - 9.17　｜　目标导向：手环11 月净销 60,000 台', span=4)

    ws.cell(row=5, column=1, value='一、核心结论').font = F_SEC
    ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=4)
    header_row(ws, 6, ['#', '结论', '数据依据', ''])
    concl = [
        ('【目标进度】手环11 月净销 60,000 台，已达成 21,583 台（36.0%）',
         '9.7-9.10 累计；剩余 20 天（9.11-9.30）需日均 1,921 台', P_HL),
        ('【关键风险】首发后稳态日均只有 1,905 台，低于所需的 1,921 台',
         '按现状走，月末约 59,683 台，差 317 台不达标 —— 目标卡在临界点上', P_WARN),
        ('【可达性】只需在稳态基础上提升 5%（日均 2,000 台）即可稳过 6 万线',
         '6 万并非激进目标，但没有任何冗余空间，必须主动加动作而不是「顺其自然」', None),
        ('【口径提醒】history.json 记录的是订单口径，若「净销」需扣退款，实际需更高出货量',
         '如退款率 10%，则需出货 66,667 台，日均要求从 1,921 提到 2,254 台', P_WARN),
        ('【本周大盘】四间合计 21,897 单 / ¥7,738,000，环比订单 +257.6%、金额 +164.6%',
         '但增量 61% 来自 9/7 首发日（当天 ¥4,725,254），是事件驱动而非自然增长', None),
        ('【剔除首发日】本周日均 ¥502,124 vs 上周 ¥487,328，仅 +3.0%',
         '自然增长基本停滞；首发前 9.4-9.6 日均甚至只有 ¥320,880，比上周 -34%', None),
        ('【结构分化】手环/数码两间被首发强带动，两间手表直播间完全没吃到红利',
         '数码旗舰店日均 44,170→249,352；手环直播间 23,393→235,976；'
         '官旗手表 23,658→25,932（持平）；官方手表 229,659→172,108（继续 -25%）', None),
        ('【渠道结构】我司手环11 的 56.4% 来自小米数码旗舰店，商品卡贡献 16.2%（第三大来源）',
         '数码 12,164 台 / 手环直播间 5,511 台 / 商品卡 3,506 台；'
         '商品卡属被动承接，若目标吃紧需评估其可拉动空间', None),
        ('【份额】我司手环11 占全站销量 26.9%；四间占全站销售额份额 34.8%→22.0%',
         '首发流量外溢：机械空间、良米等直播间同样在卖手环11，我方没能独占首发红利', None),
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
        ('P0', '小米官方手表',
         '连续两个阶段下滑（301,912 → 229,659 → 172,108），且 9.7 首发日也没被带动'
         '（当天仅 ¥208,729），说明不是大盘问题而是这间自身出了问题。'
         '必须单独复盘：拉分小时数据定位掉在哪个班次，排查货盘、话术、投放',
         '日均回到 ¥200,000\n止住连续跌势', None),
        ('P1', '小米官旗手表直播间',
         '连续低位（约 ¥2.5万/日，本周环比 -33%），首发完全没带动。'
         '评估该间与官方手表的定位是否重叠，考虑差异化选品或调整投放策略',
         '日均 ≥¥35,000\n环比转正', None),
        ('P1', '四主要间（复盘）',
         '四间份额从 34.8% 掉到 22.0%，首发红利被分散到机械空间 / 良米等间。'
         '复盘首发的流量承接链路（选品-短视频-直播承接-转化），沉淀 SOP 供双11 复用',
         '下一节点份额 ≥30%', None),
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


def main():
    h = load()
    wb = Workbook()
    sheet_compare(wb, h)
    sheet_target(wb, h)
    sheet_segment(wb, h)
    sheet_daily(wb, h)
    sheet_analysis(wb)
    wb.save(OUT)
    print('已生成:', OUT)


if __name__ == '__main__':
    main()

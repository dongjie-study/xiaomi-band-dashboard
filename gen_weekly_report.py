# -*- coding: utf-8 -*-
"""生成 9.4-9.10 vs 8.29-9.3 四主要直播间周报 xlsx 到桌面。

数据源：sales_analysis/history.json
数值单元格为蓝字硬编码输入，派生指标（环比/日均/占比/合计）全部用 Excel 公式。
"""
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = r"C:\Users\Administrator\Desktop\9.4-9.10周报_主要直播间对比分析.xlsx"

ROOMS = ['小米数码旗舰店', '小米官方手环直播间', '小米官旗手表直播间', '小米官方手表']

FONT = '微软雅黑'
HDR_FILL = PatternFill('solid', start_color='FFF4EC')      # 品牌橙浅底
SEG_FILL = PatternFill('solid', start_color='F2F4F7')
TOT_FILL = PatternFill('solid', start_color='EAF7F0')
TITLE_FONT = Font(name=FONT, size=14, bold=True, color='16181D')
SUB_FONT = Font(name=FONT, size=9, color='7A828E')
HDR_FONT = Font(name=FONT, size=10, bold=True, color='B34A00')
BODY_FONT = Font(name=FONT, size=10)
BOLD_FONT = Font(name=FONT, size=10, bold=True)
INPUT_FONT = Font(name=FONT, size=10, color='0000FF')       # 蓝字 = 硬编码输入
FORMULA_FONT = Font(name=FONT, size=10, color='000000')     # 黑字 = 公式
THIN = Side(style='thin', color='D9DEE5')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
MONEY = '¥#,##0;[Red]-¥#,##0;"-"'
PCT = '0.0%;[Red]-0.0%;"-"'
INT = '#,##0;[Red]-#,##0;"-"'


def load():
    h = json.load(open(os.path.join(ROOT, 'sales_analysis', 'history.json'), encoding='utf-8'))
    return h


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


def style_header(ws, row, ncols, labels):
    for c, lab in enumerate(labels, start=1):
        cell = ws.cell(row=row, column=c, value=lab)
        cell.font = HDR_FONT
        cell.fill = HDR_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER


def band11(history):
    """返回 {date: (全站, 我司, 4主要间)} 的手环11 销量"""
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


def sheet_target(wb, h):
    """手环11 月净销 6 万台目标进度"""
    from team_config import TEAM_MAP
    b = band11(h)
    ws = wb.create_sheet('手环11目标进度')
    ws['A1'] = '小米手环11 · 月净销 60,000 台目标进度'
    ws['A1'].font = TITLE_FONT
    ws['A2'] = ('口径：我司全部直播间（含商品卡，不含良米/机械空间等其他团队）'
                '｜ 数据源：sales_analysis/history.json（订单口径，未扣退款）')
    ws['A2'].font = SUB_FONT

    # --- 逐日 ---
    ws['A4'] = '一、逐日销量'
    ws['A4'].font = Font(name=FONT, size=11, bold=True, color='B34A00')
    style_header(ws, 5, 5, ['日期', '全站(台)', '我司(台)', '四主要间(台)', '我司占比'])
    r0 = 6
    for k, (dt, (a, o, m)) in enumerate(sorted(b.items())):
        r = r0 + k
        ws.cell(row=r, column=1, value=dt).font = BODY_FONT
        ws.cell(row=r, column=2, value=a).font = INPUT_FONT
        ws.cell(row=r, column=3, value=o).font = INPUT_FONT
        ws.cell(row=r, column=4, value=m).font = INPUT_FONT
        ws.cell(row=r, column=5, value=f'=IFERROR(C{r}/B{r},"-")').font = FORMULA_FONT
    rt = r0 + len(b)
    ws.cell(row=rt, column=1, value='累计').font = BOLD_FONT
    for c in (2, 3, 4):
        L = chr(64 + c)
        ws.cell(row=rt, column=c, value=f'=SUM({L}{r0}:{L}{rt - 1})').font = BOLD_FONT
    ws.cell(row=rt, column=5, value=f'=IFERROR(C{rt}/B{rt},"-")').font = BOLD_FONT
    for r in range(r0, rt + 1):
        for c in range(1, 6):
            cell = ws.cell(row=r, column=c)
            cell.border = BORDER
            if c in (2, 3, 4):
                cell.number_format = INT
                cell.alignment = Alignment(horizontal='right')
            if c == 5:
                cell.number_format = PCT
                cell.alignment = Alignment(horizontal='right')
        if r == rt:
            for c in range(1, 6):
                ws.cell(row=r, column=c).fill = TOT_FILL

    # --- 目标进度 ---
    r = rt + 2
    ws.cell(row=r, column=1, value='二、目标进度').font = Font(name=FONT, size=11, bold=True, color='B34A00')
    style_header(ws, r + 1, 3, ['指标', '数值', '说明'])
    base = r + 2
    items = [
        ('月目标（净销台数）', 60000, 'input', '公司下达目标'),
        ('剩余天数', 20, 'input', '9.11 - 9.30'),
        ('已达成（我司，9.7-9.10）', f'=C{rt}', 'formula', '首发日起累计'),
        ('达成率', f'=IFERROR(B{base + 2}/B{base},"-")', 'pct', '已达成 / 月目标'),
        ('剩余缺口', f'=B{base}-B{base + 2}', 'formula', '月目标 - 已达成'),
        ('剩余期需日均', f'=IFERROR(B{base + 4}/B{base + 1},"-")', 'formula', '缺口 / 剩余天数'),
        ('首发后稳态日均（9.8-9.10）', f'=ROUND(AVERAGE(C{rt - 3}:C{rt - 1}),0)', 'formula', '当前实际水位'),
        ('稳态 vs 需日均', f'=IFERROR(B{base + 6}/B{base + 5}-1,"-")', 'pct',
         '负值 = 按现状走会不达标'),
    ]
    for k, (name, val, kind, note) in enumerate(items):
        rr = base + k
        ws.cell(row=rr, column=1, value=name).font = BOLD_FONT
        c = ws.cell(row=rr, column=2, value=val)
        c.font = INPUT_FONT if kind == 'input' else FORMULA_FONT
        c.number_format = PCT if kind == 'pct' else INT
        c.alignment = Alignment(horizontal='right')
        ws.cell(row=rr, column=3, value=note).font = Font(name=FONT, size=9, color='5C6470')
        for cc in range(1, 4):
            ws.cell(row=rr, column=cc).border = BORDER
        if name.startswith('稳态 vs'):
            for cc in range(1, 4):
                ws.cell(row=rr, column=cc).fill = PatternFill('solid', start_color='FDECEA')

    # --- 情景测算 ---
    r = base + len(items) + 2
    ws.cell(row=r, column=1, value='三、剩余 20 天情景测算').font = Font(name=FONT, size=11, bold=True, color='B34A00')
    style_header(ws, r + 1, 5, ['情景', '假设日均(台)', '剩余期销量', '月末累计', '达成率'])
    sr = r + 2
    scen = [('热度回落 20%', 0.8), ('维持现状', 1.0), ('提升 5%', 1.05), ('提升 10%', 1.10)]
    for k, (label, mult) in enumerate(scen):
        rr = sr + k
        ws.cell(row=rr, column=1, value=label).font = BODY_FONT
        ws.cell(row=rr, column=2, value=f'=ROUND($B${base + 6}*{mult},0)').font = FORMULA_FONT
        ws.cell(row=rr, column=3, value=f'=B{rr}*$B${base + 1}').font = FORMULA_FONT
        ws.cell(row=rr, column=4, value=f'=$B${base + 2}+C{rr}').font = FORMULA_FONT
        ws.cell(row=rr, column=5, value=f'=IFERROR(D{rr}/$B${base},"-")').font = FORMULA_FONT
        for c in range(1, 6):
            cell = ws.cell(row=rr, column=c)
            cell.border = BORDER
            if c > 1:
                cell.number_format = PCT if c == 5 else INT
                cell.alignment = Alignment(horizontal='right')
        if k == 1:
            for c in range(1, 6):
                ws.cell(row=rr, column=c).fill = PatternFill('solid', start_color='FFF8E7')

    # --- 我司各来源贡献 ---
    r = sr + len(scen) + 2
    ws.cell(row=r, column=1, value='四、我司各来源贡献（9.7-9.10）').font = Font(
        name=FONT, size=11, bold=True, color='B34A00')
    style_header(ws, r + 1, 3, ['来源', '手环11 台数', '占我司比重'])
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
    for name, n in sorted(src.items(), key=lambda kv: -kv[1]):
        ws.cell(row=rr, column=1, value=name).font = BODY_FONT
        ws.cell(row=rr, column=2, value=n).font = INPUT_FONT
        ws.cell(row=rr, column=3,
                value=f'=IFERROR(B{rr}/$B${first_src + len(src)},"-")').font = FORMULA_FONT
        rr += 1
    ws.cell(row=rr, column=1, value='我司合计').font = BOLD_FONT
    ws.cell(row=rr, column=2, value=f'=SUM(B{first_src}:B{rr - 1})').font = BOLD_FONT
    ws.cell(row=rr, column=3, value=f'=IFERROR(B{rr}/B{rr},"-")').font = BOLD_FONT
    for x in range(first_src, rr + 1):
        for c in range(1, 4):
            cell = ws.cell(row=x, column=c)
            cell.border = BORDER
            if c == 2:
                cell.number_format = INT
                cell.alignment = Alignment(horizontal='right')
            if c == 3:
                cell.number_format = PCT
                cell.alignment = Alignment(horizontal='right')
        if x == rr:
            for c in range(1, 4):
                ws.cell(row=x, column=c).fill = TOT_FILL

    for c, w in enumerate([26, 14, 13, 13, 12], start=1):
        ws.column_dimensions[chr(64 + c)].width = w
    return ws


def main():
    h = load()
    wb = Workbook()

    # ============ Sheet 1: 本周 vs 上周 ============
    ws = wb.active
    ws.title = '本周vs上周'
    ws['A1'] = '四主要直播间 · 本周 vs 上周对比'
    ws['A1'].font = TITLE_FONT
    ws['A2'] = '本周 9.4-9.10（7天） 对比 上周 8.29-9.3（6天） ｜ 数据源：sales_analysis/history.json'
    ws['A2'].font = SUB_FONT
    ws['A3'] = '⚠️ 两段天数不等（7天 vs 6天），总量对比会被天数放大；日均口径见「首发影响分段」页'
    ws['A3'].font = Font(name=FONT, size=9, color='C0392B')

    heads = ['直播间', '上周订单', '本周订单', '订单环比',
             '上周销售额', '本周销售额', '销售额环比',
             '上周均价', '本周均价', '均价环比']
    style_header(ws, 5, len(heads), heads)

    r0 = 6
    for k, room in enumerate(ROOMS):
        r = r0 + k
        lo, lv, _ = agg(h, '2026-08-29', '2026-09-03', room)
        to, tv, _ = agg(h, '2026-09-04', '2026-09-10', room)
        ws.cell(row=r, column=1, value=room).font = BODY_FONT
        ws.cell(row=r, column=2, value=lo).font = INPUT_FONT
        ws.cell(row=r, column=3, value=to).font = INPUT_FONT
        ws.cell(row=r, column=4, value=f'=IFERROR((C{r}-B{r})/B{r},"-")').font = FORMULA_FONT
        ws.cell(row=r, column=5, value=lv).font = INPUT_FONT
        ws.cell(row=r, column=6, value=tv).font = INPUT_FONT
        ws.cell(row=r, column=7, value=f'=IFERROR((F{r}-E{r})/E{r},"-")').font = FORMULA_FONT
        ws.cell(row=r, column=8, value=f'=IFERROR(E{r}/B{r},"-")').font = FORMULA_FONT
        ws.cell(row=r, column=9, value=f'=IFERROR(F{r}/C{r},"-")').font = FORMULA_FONT
        ws.cell(row=r, column=10, value=f'=IFERROR((I{r}-H{r})/H{r},"-")').font = FORMULA_FONT

    rt = r0 + len(ROOMS)
    ws.cell(row=rt, column=1, value='4间合计').font = BOLD_FONT
    for col in (2, 3, 5, 6):
        L = chr(64 + col)
        ws.cell(row=rt, column=col, value=f'=SUM({L}{r0}:{L}{rt - 1})').font = BOLD_FONT
    ws.cell(row=rt, column=4, value=f'=IFERROR((C{rt}-B{rt})/B{rt},"-")').font = BOLD_FONT
    ws.cell(row=rt, column=7, value=f'=IFERROR((F{rt}-E{rt})/E{rt},"-")').font = BOLD_FONT
    ws.cell(row=rt, column=8, value=f'=IFERROR(E{rt}/B{rt},"-")').font = BOLD_FONT
    ws.cell(row=rt, column=9, value=f'=IFERROR(F{rt}/C{rt},"-")').font = BOLD_FONT
    ws.cell(row=rt, column=10, value=f'=IFERROR((I{rt}-H{rt})/H{rt},"-")').font = BOLD_FONT

    for r in range(r0, rt + 1):
        for c in range(1, len(heads) + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = BORDER
            if c in (2, 3):
                cell.number_format = INT
            elif c in (5, 6):
                cell.number_format = MONEY
            elif c in (4, 7, 10):
                cell.number_format = PCT
            elif c in (8, 9):
                cell.number_format = '¥#,##0.0'
            if c >= 2:
                cell.alignment = Alignment(horizontal='right')
        if r == rt:
            for c in range(1, len(heads) + 1):
                ws.cell(row=r, column=c).fill = TOT_FILL
    widths = [20, 11, 11, 10, 15, 15, 11, 10, 10, 10]
    for c, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + c)].width = w
    ws.freeze_panes = 'B6'

    # ============ Sheet 2: 手环11 目标进度 ============
    sheet_target(wb, h)

    # ============ Sheet 3: 首发影响分段 ============
    ws2 = wb.create_sheet('首发影响分段')
    ws2['A1'] = '手环11 首发（9/7）对各直播间的影响 · 分段日均销售额'
    ws2['A1'].font = TITLE_FONT
    ws2['A2'] = '用日均口径消除天数差异。首发日 9/7 全站售出手环11 59,883 台 / ¥19,337,118'
    ws2['A2'].font = SUB_FONT

    h2 = ['直播间', '上周日均\n8.29-9.3\n(6天)', '首发前日均\n9.4-9.6\n(3天)',
          '首发日\n9.7', '首发后日均\n9.8-9.10\n(3天)', '首发后 vs 首发前',
          '首发后 vs 上周']
    style_header(ws2, 4, len(h2), h2)

    segs = [('2026-08-29', '2026-09-03'), ('2026-09-04', '2026-09-06'),
            ('2026-09-07', '2026-09-07'), ('2026-09-08', '2026-09-10')]
    r0 = 5
    for k, room in enumerate(ROOMS):
        r = r0 + k
        vals = [agg(h, a, b, room) for a, b in segs]
        ws2.cell(row=r, column=1, value=room).font = BODY_FONT
        for j, (o, v, n) in enumerate(vals):
            cell = ws2.cell(row=r, column=2 + j, value=round(v / n))
            cell.font = INPUT_FONT
        ws2.cell(row=r, column=6, value=f'=IFERROR((E{r}-C{r})/C{r},"-")').font = FORMULA_FONT
        ws2.cell(row=r, column=7, value=f'=IFERROR((E{r}-B{r})/B{r},"-")').font = FORMULA_FONT

    rt2 = r0 + len(ROOMS)
    tvals = [agg(h, a, b) for a, b in segs]
    ws2.cell(row=rt2, column=1, value='4间合计').font = BOLD_FONT
    for j, (o, v, n) in enumerate(tvals):
        ws2.cell(row=rt2, column=2 + j, value=round(v / n)).font = BOLD_FONT
    ws2.cell(row=rt2, column=6, value=f'=IFERROR((E{rt2}-C{rt2})/C{rt2},"-")').font = BOLD_FONT
    ws2.cell(row=rt2, column=7, value=f'=IFERROR((E{rt2}-B{rt2})/B{rt2},"-")').font = BOLD_FONT

    for r in range(r0, rt2 + 1):
        for c in range(1, len(h2) + 1):
            cell = ws2.cell(row=r, column=c)
            cell.border = BORDER
            if c == 1:
                cell.alignment = Alignment(horizontal='left')
            else:
                cell.number_format = MONEY
                cell.alignment = Alignment(horizontal='right')
            if c in (6, 7):
                cell.number_format = PCT
        if r == rt2:
            for c in range(1, len(h2) + 1):
                ws2.cell(row=r, column=c).fill = TOT_FILL
    for c, w in enumerate([20, 15, 15, 14, 15, 16, 15], start=1):
        ws2.column_dimensions[chr(64 + c)].width = w

    # ============ Sheet 3: 逐日明细 ============
    ws3 = wb.create_sheet('逐日明细')
    ws3['A1'] = '逐日销售额明细（8.29 - 9.10）'
    ws3['A1'].font = TITLE_FONT
    h3 = ['日期', '阶段'] + ROOMS + ['4间合计']
    style_header(ws3, 3, len(h3), h3)
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
        ws3.cell(row=r, column=1, value=d['date']).font = BODY_FONT
        ws3.cell(row=r, column=2, value=seg_of.get(d['date'], '')).font = BODY_FONT
        for j, room in enumerate(ROOMS):
            ws3.cell(row=r, column=3 + j,
                     value=round(d['rooms'].get(room, {}).get('revenue', 0))).font = INPUT_FONT
        ws3.cell(row=r, column=7, value=f'=SUM(C{r}:F{r})').font = FORMULA_FONT
    rt3 = r0 + len(days)
    ws3.cell(row=rt3, column=1, value='合计').font = BOLD_FONT
    for c in range(3, 8):
        L = chr(64 + c)
        ws3.cell(row=rt3, column=c, value=f'=SUM({L}{r0}:{L}{rt3 - 1})').font = BOLD_FONT
    for r in range(r0, rt3 + 1):
        for c in range(1, len(h3) + 1):
            cell = ws3.cell(row=r, column=c)
            cell.border = BORDER
            if c >= 3:
                cell.number_format = MONEY
                cell.alignment = Alignment(horizontal='right')
        if seg_of.get(ws3.cell(row=r, column=1).value) == '首发日':
            for c in range(1, len(h3) + 1):
                ws3.cell(row=r, column=c).fill = SEG_FILL
        if r == rt3:
            for c in range(1, len(h3) + 1):
                ws3.cell(row=r, column=c).fill = TOT_FILL
    for c, w in enumerate([12, 9, 16, 18, 15, 15, 15], start=1):
        ws3.column_dimensions[chr(64 + c)].width = w
    ws3.freeze_panes = 'C4'

    # ============ Sheet 4: 分析与规划 ============
    ws4 = wb.create_sheet('分析与规划')
    ws4['A1'] = '数据解读与下周规划（9.11 - 9.17）'
    ws4['A1'].font = TITLE_FONT

    ws4['A3'] = '一、核心结论'
    ws4['A3'].font = Font(name=FONT, size=11, bold=True, color='B34A00')
    style_header(ws4, 4, 3, ['#', '结论', '数据依据'])
    concl = [
        ('【目标进度】手环11 月净销 60,000 台，已达成 21,583 台（36.0%）',
         '9.7-9.10 累计；剩余 20 天（9.11-9.30）需日均 1,921 台'),
        ('【关键风险】首发后稳态日均只有 1,905 台，低于所需的 1,921 台',
         '按现状走，月末约 59,683 台，差 317 台不达标——目标卡在临界点上'),
        ('【可达性】只需在稳态基础上提升 5%（日均 2,000 台）即可稳过 6 万线',
         '6 万并非激进目标，但没有任何冗余空间，必须主动加动作而不是"顺其自然"'),
        ('【口径提醒】history.json 记录的是订单口径，若"净销"需扣退款，实际需更高的出货量',
         '如退款率 10%，则需出货 66,667 台，日均要求从 1,921 提到 2,254 台'),
        ('【本周大盘】四间合计 21,897 单 / ¥7,738,000，环比订单 +257.6%、金额 +164.6%',
         '但增量 61% 来自 9/7 首发日（当天 ¥4,725,254），是事件驱动而非自然增长'),
        ('【剔除首发日】本周日均 ¥502,124 vs 上周 ¥487,328，仅 +3.0%',
         '自然增长基本停滞；首发前(9.4-9.6)日均甚至只有 ¥320,880，比上周 -34%'),
        ('【结构分化】手环/数码两间被首发强带动，两间手表直播间完全没吃到红利',
         '数码旗舰店日均 44,170→249,352；手环直播间 23,393→235,976；'
         '官旗手表 23,658→25,932（持平）；官方手表 229,659→172,108（继续 -25%）'),
        ('【渠道结构】我司手环11 的 56.4% 来自小米数码旗舰店，商品卡贡献 16.2%（第三大来源）',
         '数码 12,164 台 / 手环直播间 5,511 台 / 商品卡 3,506 台；'
         '商品卡属被动承接，若目标吃紧需评估其可拉动空间'),
        ('【份额】我司手环11 占全站销量 26.9%；四间占全站销售额份额 34.8%→22.0%',
         '首发流量外溢：机械空间、良米等直播间同样在卖手环11，我方没能独占首发红利'),
    ]
    for k, (a, b) in enumerate(concl):
        r = 5 + k
        ws4.cell(row=r, column=1, value=k + 1).font = BOLD_FONT
        ws4.cell(row=r, column=2, value=a).font = BODY_FONT
        ws4.cell(row=r, column=3, value=b).font = Font(name=FONT, size=9, color='5C6470')

    r = 5 + len(concl) + 2
    ws4.cell(row=r, column=1, value='二、下周规划（9.11 - 9.17）')
    ws4.cell(row=r, column=1).font = Font(name=FONT, size=11, bold=True, color='B34A00')
    style_header(ws4, r + 1, 4, ['优先级', '直播间', '重点动作', '目标'])
    plan = [
        ('P0', '手环11 冲量\n（我司全部直播间）',
         '这是本月唯一的一号目标：日均必须从 1,905 提到 2,000 台以上，且没有任何冗余。'
         '具体动作：① 手环11 固定讲解时段（每小时至少 2 轮），首发热度期不能让品断档；'
         '② 直播间贴片/背景板/置顶评论强化手环11；'
         '③ 做好关联搭配（表带、充电、手环10Pro 清库）；'
         '④ 用首发期积累的人群包做二次触达与复购；'
         '⑤ 每日盯 4 主要间的分小时销量，哪间掉队当天就补',
         '日均 ≥2,000 台\n月末累计 ≥60,000 台'),
        ('P0', '小米官方手表',
         '连续两个阶段下滑（301,912 → 229,659 → 172,108），且 9.7 首发日也没被带动'
         '（当天仅 ¥208,729），说明不是大盘问题而是这间自身出了问题。'
         '必须单独复盘：拉分小时数据定位掉在哪个班次，排查货盘、话术、投放',
         '日均回到 ¥200,000\n止住连续跌势'),
        ('P1', '小米官旗手表直播间',
         '连续低位（约 ¥2.5万/日，本周环比 -33%），首发完全没带动。'
         '评估该间与官方手表的定位是否重叠，考虑差异化选品或调整投放策略',
         '日均 ≥¥35,000\n环比转正'),
        ('P1', '四主要间（复盘）',
         '四间份额从 34.8% 掉到 22.0%，首发红利被分散到机械空间/良米等间。'
         '复盘首发的流量承接链路（选品-短视频-直播承接-转化），沉淀 SOP 供双11 复用',
         '下一节点份额 ≥30%'),
    ]
    for k, (p, room, act, goal) in enumerate(plan):
        rr = r + 2 + k
        ws4.cell(row=rr, column=1, value=p).font = BOLD_FONT
        ws4.cell(row=rr, column=2, value=room).font = BODY_FONT
        ws4.cell(row=rr, column=3, value=act).font = BODY_FONT
        ws4.cell(row=rr, column=4, value=goal).font = BODY_FONT
        for c in range(1, 5):
            cell = ws4.cell(row=rr, column=c)
            cell.border = BORDER
            cell.alignment = Alignment(vertical='top', wrap_text=True)
            if c == 1:
                cell.alignment = Alignment(horizontal='center', vertical='top')
    for c, w in enumerate([7, 22, 62, 26], start=1):
        ws4.column_dimensions[chr(64 + c)].width = w
    ws4.column_dimensions['B'].width = 22
    for rr in range(5, 5 + len(concl)):
        ws4.cell(row=rr, column=2).alignment = Alignment(vertical='top', wrap_text=True)
        ws4.cell(row=rr, column=3).alignment = Alignment(vertical='top', wrap_text=True)
        ws4.row_dimensions[rr].height = 32
    for rr in range(r + 2, r + 2 + len(plan)):
        ws4.row_dimensions[rr].height = 62

    wb.save(OUT)
    print('已生成:', OUT)


if __name__ == '__main__':
    main()

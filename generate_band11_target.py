# -*- coding: utf-8 -*-
"""
小米手环11 首销月（9.7-10.7）我司四渠道目标进度表生成器

数据源：sales_analysis/history.json（每天跑完 run_all.py sales 后自动有当日数据）
输出：桌面 小米手环11首销月目标进度表.xlsx

用法：
    python generate_band11_target.py

不需要手填任何数字。每天订单入库后重跑本脚本即可刷新进度表。
首销月结束后（10.7 之后）本表即作废，不再需要更新。
"""
import json
import os
import sys
from datetime import date, datetime, timedelta

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference, Series
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ============ 配置区 ============

PRODUCT = '小米手环11'
START = date(2026, 9, 7)      # 首销日（开售日）
END = date(2026, 10, 7)       # 首销月末
TOTAL_TARGET = 60000          # 首销月我司四渠道下单台数总目标

# 四渠道首销月目标（按 9.7-9.11 开售期五天占比拆分：54.3% / 27.5% / 17.5% / 0.6%）
ROOM_TARGETS = [
    ('小米官方手环直播间', 16500),
    ('小米数码旗舰店',     32600),
    ('我司商品卡',         10500),
    ('小米官方手表',         400),
]

# 我司「其他直播间」：计入 60000 台总量、直接冲减剩余，但不单独设目标、不做主要分析。
# 由 team_config.OUR_ROOMS 减去上面四个渠道自动推导，避免以后新增直播间漏掉。
OTHER_LABEL = '我司其他直播间'

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from team_config import OUR_ROOMS  # noqa: E402

MAIN_ROOMS = {r for r, _ in ROOM_TARGETS}
OTHER_OUR_ROOMS = sorted(OUR_ROOMS - MAIN_ROOMS)

HISTORY_FILE = os.path.join(ROOT, 'sales_analysis', 'history.json')
OUT_FILE = os.path.join(os.path.expanduser('~'), 'Desktop', '小米手环11首销月目标进度表.xlsx')

# ============ 样式 ============

C_MI = 'FF6900'        # 小米橙
C_HEAD = 'F2F2F2'      # 表头灰
C_TOTAL = 'FFF3E0'     # 合计行浅橙
C_BLANK = 'FAFAFA'     # 未到日期
C_OK = 'E8F5E9'        # 领先绿
C_WARN = 'FFF8E1'      # 正常黄
C_BAD = 'FFEBEE'       # 落后红

FONT = '微软雅黑'
THIN = Side(style='thin', color='D0D0D0')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']


def hdr_cell(ws, row, col, text):
    c = ws.cell(row=row, column=col, value=text)
    c.font = Font(name=FONT, size=10, bold=True, color='FFFFFF')
    c.fill = PatternFill('solid', fgColor=C_MI)
    c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    c.border = BORDER
    return c


def body_cell(ws, row, col, value, fmt=None, bold=False, fill=None, align='center'):
    c = ws.cell(row=row, column=col, value=value)
    c.font = Font(name=FONT, size=10, bold=bold)
    c.alignment = Alignment(horizontal=align, vertical='center')
    c.border = BORDER
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = PatternFill('solid', fgColor=fill)
    return c


def title_row(ws, text, ncols, sub=None):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    c = ws.cell(row=1, column=1, value=text)
    c.font = Font(name=FONT, size=14, bold=True, color='FFFFFF')
    c.fill = PatternFill('solid', fgColor=C_MI)
    c.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 30
    if sub:
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
        c2 = ws.cell(row=2, column=1, value=sub)
        c2.font = Font(name=FONT, size=9, color='777777')
        c2.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[2].height = 18


# ============ 数据读取 ============

def load_daily():
    """从 history.json 读取 9.7 起每天的 小米手环11 分渠道下单台数。

    返回 {date: {room: orders}}，只含 9.7~10.7 区间。
    """
    if not os.path.exists(HISTORY_FILE):
        sys.exit(f'找不到 {HISTORY_FILE}，请先跑一次 run_all.py sales')
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        history = json.load(f)

    daily = {}
    for rec in history:
        try:
            d = datetime.strptime(rec['date'], '%Y-%m-%d').date()
        except (KeyError, ValueError):
            continue
        if not (START <= d <= END):
            continue
        row = {}
        for room_name in [r for r, _ in ROOM_TARGETS] + OTHER_OUR_ROOMS:
            info = rec.get('rooms', {}).get(room_name)
            prod = (info or {}).get('products', {}).get(PRODUCT)
            row[room_name] = int(prod.get('orders', 0)) if prod else 0
        # 我司其他直播间合并成一行
        row[OTHER_LABEL] = sum(row[r] for r in OTHER_OUR_ROOMS)
        daily[d] = row
    return daily


def build_dates():
    """首销月全部日期 9.7 ~ 10.7。"""
    out, d = [], START
    while d <= END:
        out.append(d)
        d += timedelta(days=1)
    return out


# ============ Sheet 1：进度总览 ============

def sheet_overview(wb, dates, daily):
    ws = wb.create_sheet('进度总览')
    ncols = 6
    title_row(ws, f'{PRODUCT} 首销月目标进度总览', ncols,
              f'统计区间 {START:%Y-%m-%d} ~ {END:%Y-%m-%d}（{len(dates)}天）  |  口径：我司四渠道下单台数（不扣退款）')

    # 总量口径 = 四渠道 + 我司其他直播间（其他直播间直接冲减剩余，不单独设目标）
    main_rooms = [r for r, _ in ROOM_TARGETS] + [OTHER_LABEL]

    # 已过天数 = 有数据的天数
    data_days = [d for d in dates if d in daily]
    elapsed = len(data_days)
    last_date = data_days[-1] if data_days else None

    done_total = sum(daily[d].get(r, 0) for d in data_days for r in main_rooms)
    done_other = sum(daily[d].get(OTHER_LABEL, 0) for d in data_days)
    total_days = len(dates)

    # --- 顶部 KPI ---
    r = 4
    kpis = [
        ('首销月总目标', TOTAL_TARGET, '#,##0'),
        ('已达成台数', done_total, '#,##0'),
        ('累计达成率', done_total / TOTAL_TARGET if TOTAL_TARGET else 0, '0.0%'),
        ('时间进度', elapsed / total_days, '0.0%'),
        ('进度差', done_total / TOTAL_TARGET - elapsed / total_days if TOTAL_TARGET else 0, '+0.0%;-0.0%'),
        ('剩余台数', TOTAL_TARGET - done_total, '#,##0'),
    ]
    for i, (label, val, fmt) in enumerate(kpis, start=1):
        body_cell(ws, r, i, label, bold=True, fill=C_HEAD)
        c = body_cell(ws, r + 1, i, val, fmt=fmt, bold=True)
        c.font = Font(name=FONT, size=16 if i in (2, 3, 5) else 12, bold=True, color='333333')
        ws.row_dimensions[r + 1].height = 28
    ws.row_dimensions[r].height = 20

    # --- 节奏判断 ---
    r = 7
    remain_days = total_days - elapsed
    remain_qty = TOTAL_TARGET - done_total
    recent = [d for d in data_days][-4:]
    rec_rate = (sum(daily[d].get(x, 0) for d in recent for x in main_rooms) / len(recent)) if recent else 0
    need_rate = (remain_qty / remain_days) if remain_days > 0 else 0

    body_cell(ws, r, 1, '剩余天数', bold=True, fill=C_HEAD)
    body_cell(ws, r, 2, remain_days, fmt='0"天"')
    body_cell(ws, r, 3, '剩余日均需求', bold=True, fill=C_HEAD)
    body_cell(ws, r, 4, need_rate, fmt='#,##0"台/天"')
    body_cell(ws, r, 5, f'近{len(recent)}天实际日均', bold=True, fill=C_HEAD)
    body_cell(ws, r, 6, rec_rate, fmt='#,##0"台/天"')

    r = 9
    if rec_rate > 0 and remain_qty > 0:
        eta = elapsed + int(remain_qty / rec_rate) + (1 if remain_qty % rec_rate else 0)
        eta_date = START + timedelta(days=eta - 1)
        pace = f'按近{len(recent)}天日均 {rec_rate:,.0f} 台推算，预计 {eta_date:%Y-%m-%d} 可达成 60000 台目标。'
        if eta_date <= END:
            fill = C_OK
            pace += ' ✅ 在首销月窗口内可完成。'
        else:
            fill = C_BAD
            pace += f' ⚠️ 将超出首销月末（{END:%Y-%m-%d}）。'
    else:
        fill = C_WARN
        pace = '数据不足，无法推算达成日期。'
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncols)
    c = ws.cell(row=r, column=1, value=pace)
    c.font = Font(name=FONT, size=10, bold=True)
    c.fill = PatternFill('solid', fgColor=fill)
    c.alignment = Alignment(horizontal='left', vertical='center')
    ws.row_dimensions[r].height = 24

    body_cell(ws, 12, 1, '数据截至', bold=True, fill=C_HEAD)
    body_cell(ws, 12, 2, f'{last_date:%Y-%m-%d}' if last_date else '—', align='left')
    body_cell(ws, 12, 3, '数据源', bold=True, fill=C_HEAD)
    ws.merge_cells(start_row=12, start_column=4, end_row=12, end_column=6)
    body_cell(ws, 12, 4, 'sales_analysis/history.json（每日跑 run_all.py sales 后重跑本脚本刷新）',
              align='left')

    # 我司其他直播间的贡献单列一行，说明它只冲减、不设目标
    body_cell(ws, 11, 1, OTHER_LABEL, bold=True, fill=C_HEAD)
    body_cell(ws, 11, 2, done_other, fmt='#,##0')
    ws.merge_cells(start_row=11, start_column=3, end_row=11, end_column=6)
    body_cell(ws, 11, 3,
              f'已计入上方总量、直接冲减剩余（{"、".join(OTHER_OUR_ROOMS)}）。'
              f'不单独设目标，主要分析仍以四渠道为准。', align='left')
    for col, w in zip(range(1, ncols + 1), [16, 16, 16, 18, 18, 16]):
        ws.column_dimensions[get_column_letter(col)].width = w
    return ws


# ============ Sheet 2：分渠道目标 ============

def sheet_by_room(wb, dates, daily):
    ws = wb.create_sheet('分渠道目标')
    ncols = 10
    title_row(ws, '分渠道目标与达成情况', ncols,
              '目标按 9.7-9.11 开售期五天占比拆分（含 9.7 首销日）；剩余日均需求 = 剩余台数 ÷ 剩余天数')

    heads = ['渠道', '首销月目标', '已达成', '达成率', '进度差', '剩余台数',
             '剩余日均需求', '近4天日均', '缺口/富余', '状态']
    for i, h in enumerate(heads, start=1):
        hdr_cell(ws, 4, i, h)
    ws.row_dimensions[4].height = 30

    data_days = [d for d in dates if d in daily]
    elapsed = len(data_days)
    total_days = len(dates)
    remain_days = total_days - elapsed
    recent = data_days[-4:]

    r = 5
    for room, target in ROOM_TARGETS:
        done = sum(daily[d].get(room, 0) for d in data_days)
        rate = done / target if target else 0
        time_rate = elapsed / total_days
        diff = rate - time_rate
        remain = max(target - done, 0)
        need = remain / remain_days if remain_days > 0 else 0
        rec = (sum(daily[d].get(room, 0) for d in recent) / len(recent)) if recent else 0
        gap = rec - need
        if rec >= need * 1.1:
            status, fill = '领先', C_OK
        elif rec >= need:
            status, fill = '正常', C_WARN
        else:
            status, fill = '落后', C_BAD
        body_cell(ws, r, 1, room, align='left', bold=True)
        body_cell(ws, r, 2, target, fmt='#,##0')
        body_cell(ws, r, 3, done, fmt='#,##0')
        body_cell(ws, r, 4, rate, fmt='0.0%')
        c = body_cell(ws, r, 5, diff, fmt='+0.0%;-0.0%')
        c.font = Font(name=FONT, size=10, color='2E7D32' if diff >= 0 else 'C62828')
        body_cell(ws, r, 6, remain, fmt='#,##0')
        body_cell(ws, r, 7, round(need), fmt='#,##0')
        body_cell(ws, r, 8, round(rec), fmt='#,##0')
        c = body_cell(ws, r, 9, round(gap), fmt='+#,##0;-#,##0')
        c.font = Font(name=FONT, size=10, color='2E7D32' if gap >= 0 else 'C62828')
        c = body_cell(ws, r, 10, status, bold=True, fill=fill)
        r += 1

    # 我司其他直播间：不设目标，只把已成交量冲减剩余（剩余列显示为负数 = 净冲减）
    oth_done = sum(daily[d].get(OTHER_LABEL, 0) for d in data_days)
    oth_rec = (sum(daily[d].get(OTHER_LABEL, 0) for d in recent) / len(recent)) if recent else 0
    body_cell(ws, r, 1, OTHER_LABEL, align='left', bold=True)
    body_cell(ws, r, 2, 0, fmt='#,##0;-#,##0;"—"')
    body_cell(ws, r, 3, oth_done, fmt='#,##0')
    body_cell(ws, r, 4, '—')
    body_cell(ws, r, 5, '—')
    body_cell(ws, r, 6, f'=B{r}-C{r}', fmt='#,##0;-#,##0;"—"')
    body_cell(ws, r, 7, '—')
    body_cell(ws, r, 8, round(oth_rec), fmt='#,##0')
    body_cell(ws, r, 9, '—')
    body_cell(ws, r, 10, '冲减', bold=True, fill=C_BLANK)
    ws.row_dimensions[r].height = 18
    r += 1

    body_cell(ws, r, 1, '合计', bold=True, fill=C_TOTAL, align='left')
    body_cell(ws, r, 2, f'=SUM(B5:B{r-1})', fmt='#,##0', bold=True, fill=C_TOTAL)
    body_cell(ws, r, 3, f'=SUM(C5:C{r-1})', fmt='#,##0', bold=True, fill=C_TOTAL)
    body_cell(ws, r, 4, f'=C{r}/B{r}', fmt='0.0%', bold=True, fill=C_TOTAL)
    body_cell(ws, r, 5, f'=D{r}-{elapsed / total_days}', fmt='+0.0%;-0.0%', bold=True, fill=C_TOTAL)
    body_cell(ws, r, 6, f'=SUM(F5:F{r-1})', fmt='#,##0', bold=True, fill=C_TOTAL)
    body_cell(ws, r, 7, f'=ROUND(F{r}/{remain_days},0)' if remain_days > 0 else '—',
              fmt='#,##0', bold=True, fill=C_TOTAL)
    body_cell(ws, r, 8, f'=SUM(H5:H{r-1})', fmt='#,##0', bold=True, fill=C_TOTAL)
    body_cell(ws, r, 9, f'=H{r}-G{r}', fmt='+#,##0;-#,##0', bold=True, fill=C_TOTAL)
    body_cell(ws, r, 10, '', fill=C_TOTAL)

    r += 2
    note = (f'说明：①「已达成」为首销月累计下单台数，取自 history.json，不扣退款；'
            f'②「进度差」= 达成率 − 时间进度（当前 {elapsed}/{total_days}）；'
            f'③「缺口/富余」= 近4天日均 − 剩余日均需求，正数为富余；'
            f'④ 我司其他直播间不设目标，其成交量直接冲减总剩余（该行「剩余台数」显示为负数）。')
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncols)
    c = ws.cell(row=r, column=1, value=note)
    c.font = Font(name=FONT, size=9, color='666666')
    c.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    ws.row_dimensions[r].height = 34

    r += 2
    body_cell(ws, r, 1, f'{OTHER_LABEL}包含', bold=True, fill=C_HEAD, align='left')
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=ncols)
    body_cell(ws, r, 2, f'{"、".join(OTHER_OUR_ROOMS)}。'
                        f'（由 team_config.OUR_ROOMS 自动推导，新增我司直播间会自动纳入）',
              align='left')

    widths = [22, 12, 11, 10, 10, 11, 13, 11, 12, 9]
    for col, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(col)].width = w
    return ws


# ============ Sheet 3：每日明细 ============

def sheet_daily(wb, dates, daily):
    ws = wb.create_sheet('每日明细')
    chan_cols = [r for r, _ in ROOM_TARGETS] + [OTHER_LABEL]
    ncols = 3 + len(chan_cols) + 6
    title_row(ws, '每日台数明细（9.7 - 10.7）· 历史数据全部保留，逐日追加', ncols,
              '每天新数据只往下追加，已入库日期不会被覆盖；灰底行 = 尚未到来的日期')

    heads = ['日期', '星期'] + chan_cols + \
            ['当日合计', '累计合计', '累计达成率', '时间进度', '累计目标(线性)', '进度差']
    for i, h in enumerate(heads, start=1):
        if h == OTHER_LABEL:
            c = ws.cell(row=4, column=i, value=h)
            c.font = Font(name=FONT, size=9, bold=True, color='FFFFFF')
            c.fill = PatternFill('solid', fgColor='B0BEC5')
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            c.border = BORDER
        else:
            hdr_cell(ws, 4, i, h)
    ws.row_dimensions[4].height = 32

    N = len(dates)
    last_room_col = 2 + len(chan_cols)             # = 7
    sum_col = last_room_col + 1                    # G 当日合计
    cum_col = sum_col + 1                          # H 累计合计
    rate_col = cum_col + 1                         # I 累计达成率
    time_col = rate_col + 1                        # J 时间进度
    pace_col = time_col + 1                        # K 累计目标(线性)
    diff_col = pace_col + 1                        # L 进度差

    r = 5
    first_data_row = r
    last_actual_row = first_data_row - 1
    for i, d in enumerate(dates):
        has = d in daily
        fill = None if has else C_BLANK
        body_cell(ws, r, 1, d.strftime('%m-%d'), fill=fill, bold=not has)
        body_cell(ws, r, 2, WEEKDAYS[d.weekday()], fill=fill)
        for j, room in enumerate(chan_cols):
            v = daily[d].get(room, 0) if has else None
            body_cell(ws, r, 3 + j, v, fmt='#,##0', fill=fill)
        # 已入库行写公式（可手改明细自动重算）；未到日期留空，避免把"还没到"误读成"没达成"
        if has:
            last_actual_row = r
            body_cell(ws, r, sum_col, f'=SUM(C{r}:{get_column_letter(last_room_col)}{r})',
                      fmt='#,##0', bold=True, fill=C_HEAD)
            body_cell(ws, r, cum_col,
                      f'=SUM(${get_column_letter(sum_col)}${first_data_row}:'
                      f'{get_column_letter(sum_col)}{r})', fmt='#,##0', bold=True)
            body_cell(ws, r, rate_col, f'={get_column_letter(cum_col)}{r}/{TOTAL_TARGET}',
                      fmt='0.0%')
            # 领先绿、落后红交给数字格式，避免负数也显示成绿色
            body_cell(ws, r, diff_col,
                      f'={get_column_letter(cum_col)}{r}-{get_column_letter(pace_col)}{r}',
                      fmt='[Color2E7D32]+#,##0;[Red]-#,##0')
        else:
            for col in (sum_col, cum_col, rate_col, diff_col):
                body_cell(ws, r, col, None, fill=fill)
        body_cell(ws, r, time_col, (i + 1) / N, fmt='0.0%', fill=fill)
        body_cell(ws, r, pace_col, f'={TOTAL_TARGET}*{get_column_letter(time_col)}{r}',
                  fmt='#,##0', fill=fill)
        r += 1

    last_row = r - 1
    body_cell(ws, r, 1, '合计', bold=True, fill=C_TOTAL)
    body_cell(ws, r, 2, '', fill=C_TOTAL)
    for j in range(len(chan_cols)):
        col = get_column_letter(3 + j)
        body_cell(ws, r, 3 + j, f'=SUM({col}{first_data_row}:{col}{last_row})',
                  fmt='#,##0', bold=True, fill=C_TOTAL)
    for col in (sum_col, cum_col):
        L = get_column_letter(col)
        body_cell(ws, r, col, f'=SUM({L}{first_data_row}:{L}{last_row})',
                  fmt='#,##0', bold=True, fill=C_TOTAL)
    body_cell(ws, r, rate_col, f'={get_column_letter(cum_col)}{r}/{TOTAL_TARGET}',
              fmt='0.0%', bold=True, fill=C_TOTAL)
    body_cell(ws, r, time_col, 1.0, fmt='0.0%', bold=True, fill=C_TOTAL)
    body_cell(ws, r, pace_col, TOTAL_TARGET, fmt='#,##0', bold=True, fill=C_TOTAL)
    body_cell(ws, r, diff_col, f'={get_column_letter(cum_col)}{r}-{TOTAL_TARGET}',
              fmt='+#,##0;-#,##0', bold=True, fill=C_TOTAL)

    widths = [9, 6] + [15] * len(ROOM_TARGETS) + [11] + [11, 11, 12, 10, 14, 12]
    for col, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(col)].width = w
    ws.freeze_panes = 'C5'

    # --- 趋势图：每日台数(柱) + 累计达成(线) vs 线性目标(线) ---
    bar = BarChart()
    bar.type = 'col'
    bar.title = f'{PRODUCT} 首销月每日达成'
    bar.y_axis.title = '台数'
    bar.x_axis.title = '日期'
    bar.height, bar.width = 9, 26
    data_bar = Reference(ws, min_col=sum_col, min_row=4, max_row=last_row)
    cats = Reference(ws, min_col=1, min_row=first_data_row, max_row=last_row)
    bar.add_data(data_bar, titles_from_data=True)
    bar.set_categories(cats)
    bar.gapWidth = 40
    bar.series[0].graphicalProperties.solidFill = C_MI

    line = LineChart()
    line.y_axis.axId = 200
    line.y_axis.title = '累计台数'
    # 累计达成线只画到最后一个已入库日期，不把未来空行画成"已完成"
    for col, last, color, w in [(cum_col, last_actual_row, '2E7D32', 2.5),
                                (pace_col, last_row, '9E9E9E', 1.5)]:
        if last < first_data_row:
            continue
        s = Series(Reference(ws, min_col=col, min_row=4, max_row=last), title_from_data=True)
        s.graphicalProperties.line.solidFill = color
        s.graphicalProperties.line.width = w * 12700
        s.smooth = False
        line.series.append(s)
    line.y_axis.crosses = 'max'
    bar.y_axis.crosses = 'autoZero'
    bar += line
    ws.add_chart(bar, f'{get_column_letter(diff_col + 2)}4')

    ncol_chart = diff_col - 1
    ws.merge_cells(start_row=r + 2, start_column=1, end_row=r + 2, end_column=ncol_chart)
    c = ws.cell(row=r + 2, column=1,
                value='绿线 = 累计达成，灰线 = 60000 台的线性进度基准，绿线在灰线上方即为领先。'
                      '已入库日期每日一行，历史数据永久保留。')
    c.font = Font(name=FONT, size=9, color='666666')
    c.alignment = Alignment(horizontal='left', vertical='center')
    return ws


# ============ Sheet 4：拆分说明 ============

def sheet_notes(wb, dates, daily):
    ws = wb.create_sheet('拆分说明')
    ncols = 6
    title_row(ws, '60000 台目标拆分依据', ncols)

    data_days = [d for d in dates if d in daily]
    base = data_days  # 9.7 首销日起的全部已入库天数

    r = 4
    lines = [
        ('一、总目标', f'小米手环11 首销月（{START:%Y-%m-%d} ~ {END:%Y-%m-%d}，共 {len(dates)} 天）'
                       f'我司四渠道下单台数目标 {TOTAL_TARGET:,} 台。'),
        ('二、拆分口径', f'按 9.7 首销日起已入库的 {len(base)} 天（{base[0]:%m-%d} ~ {base[-1]:%m-%d}）'
                         f'累计占比拆分，含 9.7 开售日。开售日单日 '
                         f'{sum(daily[START].get(x, 0) for x, _ in ROOM_TARGETS):,} 台，'
                         f'是各渠道真实吃到开售流量的结果，按此拆分可让承担更多开售红利的渠道扛更多目标。'),
        ('三、我司其他直播间', f'{"、".join(OTHER_OUR_ROOMS)} 的手环11 成交也计入 60000 台总量，'
                               f'合并为「{OTHER_LABEL}」一行，直接冲减总剩余；'
                               f'但不单独设目标，主要分析仍以上面四个渠道为准。'
                               f'（该行由 team_config.OUR_ROOMS 自动推导，新增我司直播间会自动纳入）'),
        ('四、口径', '① 下单台数 = 订单条数，不扣退款；② 数据源 sales_analysis/history.json，'
                     '与销售分析看板同口径；③ 总达成 = 四渠道 + 我司其他直播间；'
                     '④ 后续每日订单入库后重跑本脚本刷新。'),
        ('五、有效期', f'本表仅适用于 10.7 首销月结束前。{END:%Y-%m-%d} 之后不再需要更新。'),
    ]
    for label, text in lines:
        body_cell(ws, r, 1, label, bold=True, fill=C_HEAD, align='left')
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=ncols)
        c = ws.cell(row=r, column=2, value=text)
        c.font = Font(name=FONT, size=10)
        c.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        c.border = BORDER
        ws.row_dimensions[r].height = 42
        r += 1

    r += 1
    hdr_cell(ws, r, 1, '渠道')
    hdr_cell(ws, r, 2, f'{base[0]:%m-%d}~{base[-1]:%m-%d} 台数')
    hdr_cell(ws, r, 3, '累计占比')
    hdr_cell(ws, r, 4, '首销月目标')
    hdr_cell(ws, r, 5, '目标占比')
    hdr_cell(ws, r, 6, '偏差')
    r += 1
    base_total = sum(daily[d].get(x, 0) for d in base for x, _ in ROOM_TARGETS)
    for room, target in ROOM_TARGETS:
        n = sum(daily[d].get(room, 0) for d in base)
        share = n / base_total if base_total else 0
        tshare = target / TOTAL_TARGET
        body_cell(ws, r, 1, room, align='left')
        body_cell(ws, r, 2, n, fmt='#,##0')
        body_cell(ws, r, 3, share, fmt='0.00%')
        body_cell(ws, r, 4, target, fmt='#,##0', bold=True)
        body_cell(ws, r, 5, tshare, fmt='0.00%')
        body_cell(ws, r, 6, tshare - share, fmt='+0.00%;-0.00%')
        r += 1
    body_cell(ws, r, 1, '合计', bold=True, fill=C_TOTAL, align='left')
    for col, val, fmt in [(2, base_total, '#,##0'), (3, 1.0, '0.00%'),
                          (4, TOTAL_TARGET, '#,##0'), (5, 1.0, '0.00%'), (6, '', None)]:
        body_cell(ws, r, col, val, fmt=fmt, bold=True, fill=C_TOTAL)

    for col, w in zip(range(1, ncols + 1), [24, 15, 12, 13, 12, 12]):
        ws.column_dimensions[get_column_letter(col)].width = w
    return ws


def main():
    daily = load_daily()
    dates = build_dates()
    wb = Workbook()
    wb.remove(wb.active)

    sheet_overview(wb, dates, daily)
    sheet_by_room(wb, dates, daily)
    sheet_daily(wb, dates, daily)
    sheet_notes(wb, dates, daily)

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    wb.save(OUT_FILE)
    print(f'[OK] 进度表已生成：{OUT_FILE}')

    data_days = [d for d in dates if d in daily]
    main = sum(daily[d].get(r, 0) for d in data_days for r, _ in ROOM_TARGETS)
    other = sum(daily[d].get(OTHER_LABEL, 0) for d in data_days)
    done = main + other
    print(f'   数据截至 {data_days[-1]:%Y-%m-%d}，已入库 {len(data_days)} 天，'
          f'累计 {done:,} / {TOTAL_TARGET:,} 台（{done / TOTAL_TARGET:.1%}）'
          f' = 四渠道 {main:,} + 我司其他直播间 {other:,}')


if __name__ == '__main__':
    main()

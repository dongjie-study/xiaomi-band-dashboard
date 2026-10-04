# -*- coding: utf-8 -*-
"""直播间销量周报生成器（参数化 · 每周一跑上一周）

用法
----
    python tools/gen_weekly_report.py                            # 默认：history.json 里最近 7 个完整日
    python tools/gen_weekly_report.py --start 2026-09-28 --end 2026-10-03
    python tools/gen_weekly_report.py --top 30                   # 商品榜行数（默认 25）
    python tools/gen_weekly_report.py --out "D:\\xx.xlsx"        # 自定义输出（默认桌面）
    python tools/gen_weekly_report.py --check-json _artifacts\\weekly_expected.json

口径
----
  * 数据源：sales_analysis/history.json（每日订单入库产物）
  * 直播间归属：team_config.TEAM_MAP（未列出的房间按 classify_room() 兜底归「良米」）
  * 统计区间 = 最近 N 个完整日（默认 7）；对比区间 = 紧邻其前的等长区间
  * 商品名归并：product_classifier.classify_product()
  * 数值单元格 = 硬编码输入（深蓝字 1F4E79），派生指标（占比/环比/合计/均价）= Excel 公式（深灰字 404040）
  * 订单口径，未扣退款
"""
import argparse
import json
import os
import sys

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.formatting.rule import DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# Windows 控制台默认 GBK，含 ¥ / 中文标点的输出会报 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# 本脚本位于 tools/ 下：项目根是上一级，共享模块（team_config / product_classifier）在根目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from product_classifier import classify_product  # noqa: E402
from team_config import TEAM_ORDER, classify_room  # noqa: E402

DESKTOP = os.path.join(os.path.expanduser('~'), 'Desktop')

# ===== 主题（沿用 house style）=====
FONT = '微软雅黑'
BRAND, BRAND_DK = 'FF6900', 'B34A00'
INK, INK_SOFT, INK_MUTE = '1F2937', '6B7280', '9AA3AF'
ZEBRA = 'FAFBFC'
TOTAL_BG = 'FFF4EC'
WARN_BG, OK_BG, HL_BG = 'FDECEA', 'EAF7F0', 'FFF8E7'
RIVAL_BG = 'F1F5F9'
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
F_XREF = Font(name=FONT, size=10, color='2E7D32')      # 绿 = 跨表引用
F_TINY = Font(name=FONT, size=9, color=INK_SOFT)
F_LEAD = Font(name=FONT, size=10, color=INK)

# ===== 填充 =====
P_HDR = PatternFill('solid', start_color=BRAND)
P_ZEBRA = PatternFill('solid', start_color=ZEBRA)
P_TOTAL = PatternFill('solid', start_color=TOTAL_BG)
P_WARN = PatternFill('solid', start_color=WARN_BG)
P_OK = PatternFill('solid', start_color=OK_BG)
P_HL = PatternFill('solid', start_color=HL_BG)
P_RIVAL = PatternFill('solid', start_color=RIVAL_BG)
P_HEAD_BG = PatternFill('solid', start_color='FFF1E6')

THIN = Side(style='thin', color=GRID)
MED = Side(style='medium', color=BRAND)
B_ALL = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
B_TOP = Border(left=THIN, right=THIN, top=MED, bottom=THIN)

MONEY = '¥#,##0;[Red]-¥#,##0;"-"'
MONEY1 = '¥#,##0.0;[Red]-¥#,##0.0;"-"'
PCT = '0.0%;[Red]-0.0%;"-"'
INT = '#,##0;[Red]-#,##0;"-"'
RATIO = '0.00"x";[Red]-0.00"x";"-"'
CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
LEFT = Alignment(horizontal='left', vertical='center')
RIGHT = Alignment(horizontal='right', vertical='center')
TOPWRAP = Alignment(horizontal='left', vertical='top', wrap_text=True)

TAB_COLORS = {
    '总览': BRAND, '我司直播间': '1E90FF', '竞对对比': '94A3B8', '全站直播间': '6B7280',
    '商品结构': 'FF6900', '逐日明细': BRAND_DK, '结论与建议': '2E7D32',
    '趋势图': 'F59E0B', '数据说明': '9AA3AF',
}


# ====================== 数据 ======================
def load_history():
    path = os.path.join(ROOT, 'sales_analysis', 'history.json')
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def all_dates(history):
    return sorted({d['date'] for d in history})


def scan(history, start, end):
    """把 [start, end] 区间的逐日数据汇总成房间 / 商品 / 商品×团队 三张表。"""
    days = [d for d in history if start <= d['date'] <= end]
    rooms, products, prod_team, declared = {}, {}, {}, 0
    for d in days:
        declared += d.get('total_orders', 0)
        for r, ri in (d.get('rooms') or {}).items():
            a = rooms.setdefault(r, {'orders': 0, 'revenue': 0.0})
            a['orders'] += ri.get('orders', 0) or 0
            a['revenue'] += ri.get('revenue', 0) or 0.0
            tm = classify_room(r)
            for p, pi in (ri.get('products') or {}).items():
                b = prod_team.setdefault((p, tm), {'orders': 0, 'revenue': 0.0})
                b['orders'] += pi.get('orders', 0) or 0
                b['revenue'] += pi.get('revenue', 0) or 0.0
        for p, pi in (d.get('products') or {}).items():
            a = products.setdefault(p, {'orders': 0, 'revenue': 0.0})
            a['orders'] += pi.get('orders', 0) or 0
            a['revenue'] += pi.get('revenue', 0) or 0.0
    total = {
        'orders': sum(v['orders'] for v in rooms.values()),
        'revenue': sum(v['revenue'] for v in rooms.values()),
    }
    return {'days': days, 'rooms': rooms, 'products': products,
            'prod_team': prod_team, 'total': total, 'declared_orders': declared}


def team_rollup(rooms):
    out = {}
    for r, v in rooms.items():
        tm = classify_room(r)
        a = out.setdefault(tm, {'orders': 0, 'revenue': 0.0, 'rooms': []})
        a['orders'] += v['orders']
        a['revenue'] += v['revenue']
        a['rooms'].append(r)
    for a in out.values():
        a['rooms'].sort(key=lambda r: -rooms[r]['revenue'])
    return out


def category_of(product):
    """粗品类归属：手环 / 手表 / 耳机 / 眼镜 / 其它。"""
    if '手环' in product or 'Band' in product:
        return '手环'
    if 'Watch' in product or '手表' in product:
        return '手表'
    if 'Buds' in product or '耳机' in product:
        return '耳机'
    if '眼镜' in product:
        return '眼镜'
    return '其它'


CATEGORIES = ['手环', '手表', '耳机', '眼镜', '其它']


def cat_team_rollup(prod_team):
    """{(品类, 团队): {orders, revenue}}"""
    out = {}
    for (p, tm), v in prod_team.items():
        c = category_of(p)
        a = out.setdefault((c, tm), {'orders': 0, 'revenue': 0.0})
        a['orders'] += v['orders']
        a['revenue'] += v['revenue']
    return out


def window_before(dates, start, end, length):
    """取 [start, end] 之前紧邻的等长日期窗口。"""
    idx = dates.index(start)
    prev = dates[max(0, idx - length):idx]
    if not prev:
        return None, None
    return prev[0], prev[-1]


def d2s(iso):
    """'2026-09-27' → '9.27'"""
    y, m, dd = iso.split('-')
    return '%d.%d' % (int(m), int(dd))


def num(v):
    return format(round(v), ',')


def wan(v):
    """金额口语化：¥123.5万 / ¥8,640"""
    if abs(v) >= 10000:
        return '¥%.1f万' % (v / 10000.0)
    return '¥%s' % num(v)


def pct(v):
    return '%.1f%%' % (v * 100)


def signed_pct(v):
    return ('+' if v >= 0 else '−') + '%.1f%%' % (abs(v) * 100)


def wow(cur_v, prev_v):
    if not prev_v:
        return None
    return (cur_v - prev_v) / float(prev_v)


# ====================== 版式助手 ======================
def no_grid(ws):
    ws.sheet_view.showGridLines = False
    if ws.title in TAB_COLORS:
        ws.sheet_properties.tabColor = TAB_COLORS[ws.title]


def title_block(ws, title, sub, note=None, span=9):
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


def section(ws, row, text, span=9):
    c = ws.cell(row=row, column=1, value=text)
    c.font = F_SEC
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
    ws.row_dimensions[row].height = 24
    return row + 1


def header_row(ws, row, labels, height=30):
    for i, lab in enumerate(labels, start=1):
        c = ws.cell(row=row, column=i, value=lab)
        c.font = F_HDR
        c.fill = P_HDR
        c.alignment = CENTER
        c.border = B_ALL
    ws.row_dimensions[row].height = height
    return row + 1


def widths(ws, spec):
    for i, w in enumerate(spec, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def style_rows(ws, r0, r1, ncol, fmts, bold_row=None, zebra=True):
    """统一边框 / 斑马纹 / 数字格式；bold_row = 合计行行号。"""
    for r in range(r0, r1 + 1):
        is_tot = (r == bold_row)
        for c in range(1, ncol + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = B_TOP if is_tot else B_ALL
            if is_tot:
                cell.fill = P_TOTAL
            elif zebra and (r - r0) % 2:
                cell.fill = P_ZEBRA
            cell.alignment = LEFT if c == 1 else RIGHT
            fmt = fmts.get(c)
            if fmt:
                cell.number_format = fmt
        ws.row_dimensions[r].height = 21


F_LINE_DEFAULT = F_BODY


def mark(ws, row, ncol, font=None, fill=None):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        if font:
            cell.font = font
        if fill:
            cell.fill = fill


def bullets(ws, row, span, items, bullet_char='•'):
    """把若干条结论写成一列合并单元格（自动换行）。"""
    for text in items:
        cell = ws.cell(row=row, column=1, value=bullet_char + ' ' + text)
        cell.font = F_LEAD
        cell.alignment = TOPWRAP
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
        h = 20 + 16 * max(0, (len(text) - 1) // int(span * 11))
        ws.row_dimensions[row].height = max(22, min(96, h))
        row += 1
    return row


# ====================== 上下文 ======================
def build_ctx(history, start, end, top_n=25):
    dates = all_dates(history)
    cur = scan(history, start, end)
    p_start, p_end = window_before(dates, start, end, len(cur['days']))
    prev = scan(history, p_start, p_end) if p_start else {'days': [], 'rooms': {}, 'products': {},
                                                          'prod_team': {}, 'total': {'orders': 0, 'revenue': 0.0},
                                                          'declared_orders': 0}
    cur_teams, prev_teams = team_rollup(cur['rooms']), team_rollup(prev['rooms'])
    ctx = {
        'history': history, 'start': start, 'end': end, 'prev_start': p_start, 'prev_end': p_end,
        'cur': cur, 'prev': prev, 'cur_teams': cur_teams, 'prev_teams': prev_teams,
        'cur_cat': cat_team_rollup(cur['prod_team']), 'prev_cat': cat_team_rollup(prev['prod_team']),
        'top_n': top_n,
        'label_cur': '%s-%s' % (d2s(start), d2s(end)),
        'label_prev': ('%s-%s' % (d2s(p_start), d2s(p_end))) if p_start else '—',
        'n_days': len(cur['days']),
        'our': cur_teams.get('我司', {'orders': 0, 'revenue': 0.0, 'rooms': []}),
        'liang': cur_teams.get('良米', {'orders': 0, 'revenue': 0.0, 'rooms': []}),
        'our_prev': prev_teams.get('我司', {'orders': 0, 'revenue': 0.0, 'rooms': []}),
        'liang_prev': prev_teams.get('良米', {'orders': 0, 'revenue': 0.0, 'rooms': []}),
    }
    others = [t for t in cur_teams if t not in ('我司', '良米')]
    others_prev = [t for t in prev_teams if t not in ('我司', '良米')]
    ctx['other_rev'] = sum(cur_teams[t]['revenue'] for t in others)
    ctx['other_ord'] = sum(cur_teams[t]['orders'] for t in others)
    ctx['other_rev_prev'] = sum(prev_teams[t]['revenue'] for t in others_prev)
    ctx['other_ord_prev'] = sum(prev_teams[t]['orders'] for t in others_prev)
    ctx['other_teams'] = others
    ctx['other_teams_sorted'] = sorted(others, key=lambda t: -cur_teams[t]['revenue'])
    ctx['other_sorted_txt'] = ' / '.join('%s %s' % (t, wan(cur_teams[t]['revenue'])) for t in ctx['other_teams_sorted'])
    ctx['our_rooms_n'] = len([r for r, v in cur['rooms'].items() if classify_room(r) == '我司' and v['revenue'] > 0])
    ctx['liang_rooms_n'] = len([r for r, v in cur['rooms'].items() if classify_room(r) == '良米' and v['revenue'] > 0])
    # TEAM_MAP 登记数（用于「数据说明」页，避免写死）
    from team_config import IGNORED_ROOMS, TEAM_MAP
    cfg = {}
    for room, team in TEAM_MAP.items():
        if room in IGNORED_ROOMS:
            continue
        cfg[team] = cfg.get(team, 0) + 1
    ctx['cfg_counts'] = cfg
    ctx['other_cfg_n'] = len([t for t in cfg if t not in ('我司', '良米')])
    return ctx


# ====================== Sheet: 总览 ======================
def sheet_overview(wb, x):
    ws = wb.create_sheet('总览')
    no_grid(ws)
    title_block(
        ws, '直播间销量周报 · %s' % x['label_cur'],
        '统计区间 2026.%s（%d天）　对比区间 2026.%s（%d天）　｜　数据源 sales_analysis/history.json（每日订单入库）'
        % (x['label_cur'], x['n_days'], x['label_prev'], len(x['prev']['days'])),
        '⚠ 口径：订单数 / 销售额取自每日入库的直播间订单明细，未扣退款；「占比」= 该项 ÷ 全站；'
        '「环比」= (本周 − 上周) ÷ 上周。深蓝字 = 硬编码输入，深灰字 = Excel 公式', span=9)

    r = section(ws, 5, '一、核心指标', span=9)
    hdr = ['指标', '本周 %s' % x['label_cur'], '上周 %s' % x['label_prev'], '环比', '口径 / 说明']
    r = header_row(ws, r, hdr)
    first = r

    ct, pt = x['cur']['total'], x['prev']['total']
    our, liang = x['our'], x['liang']
    ourp, liangp = x['our_prev'], x['liang_prev']

    def kpi(name, cur_v, prev_v, fmt, note):
        nonlocal r
        ws.cell(row=r, column=1, value=name).font = F_BOLD
        c2 = ws.cell(row=r, column=2, value=cur_v)
        c3 = ws.cell(row=r, column=3, value=prev_v)
        c2.font = F_INPUT
        c3.font = F_INPUT
        c4 = ws.cell(row=r, column=4, value='=IFERROR((B%d-C%d)/C%d,"-")' % (r, r, r))
        c4.font = F_FORM
        c5 = ws.cell(row=r, column=5, value=note)
        c5.font = F_TINY
        c5.alignment = LEFT
        c2.number_format = c3.number_format = fmt
        c4.number_format = PCT
        r += 1
        return r - 1

    def kpi_formula(name, formula, fmt, note, font=F_FORM):
        nonlocal r
        ws.cell(row=r, column=1, value=name).font = F_BOLD
        c = ws.cell(row=r, column=2, value=formula)
        c.font = font
        c.number_format = fmt
        ws.cell(row=r, column=4, value='—').font = F_TINY
        ws.cell(row=r, column=5, value=note).font = F_TINY
        ws.cell(row=r, column=5).alignment = LEFT
        r += 1
        return r - 1

    row_site_rev = kpi('全站销售额', ct['revenue'], pt['revenue'], MONEY, '全站所有团队 + 商品卡渠道')
    row_site_ord = kpi('全站订单数', ct['orders'], pt['orders'], INT, '订单口径，未扣退款')
    kpi_formula('全站均价', '=IFERROR(B%d/B%d,"-")' % (row_site_rev, row_site_ord), MONEY1,
                '销售额 ÷ 订单数', F_FORM)
    row_our_rev = kpi('我司销售额', our['revenue'], ourp['revenue'], MONEY,
                      '本周有销量 %d 间（含我司商品卡）' % x['our_rooms_n'])
    row_our_ord = kpi('我司订单数', our['orders'], ourp['orders'], INT, '我司全部直播间')
    row_our_avg = kpi_formula('我司均价', '=IFERROR(B%d/B%d,"-")' % (row_our_rev, row_our_ord), MONEY1,
                              '我司销售额 ÷ 我司订单数')
    kpi_formula('我司销售额占比', '=IFERROR(B%d/B%d,"-")' % (row_our_rev, row_site_rev), PCT,
                '我司销售额 ÷ 全站销售额 ★核心指标')
    row_liang_rev = kpi('良米销售额', liang['revenue'], liangp['revenue'], MONEY,
                        '本周有销量 %d 间（含良米商品卡）' % x['liang_rooms_n'])
    kpi_formula('良米销售额占比', '=IFERROR(B%d/B%d,"-")' % (row_liang_rev, row_site_rev), PCT, '良米销售额 ÷ 全站销售额')
    kpi_formula('我司 ÷ 良米（销售额）', '=IFERROR(B%d/B%d,"-")' % (row_our_rev, row_liang_rev), RATIO,
                '> 1 才算压过良米；< 1 = 被良米压制')
    row_other_rev = kpi('其它团队销售额（%d家）' % len(x['other_teams']), x['other_rev'], x['other_rev_prev'], MONEY,
                        '本周其它团队：%s' % (x['other_sorted_txt'] or '无'))
    kpi_formula('其它团队销售额占比', '=IFERROR(B%d/B%d,"-")' % (row_other_rev, row_site_rev), PCT, '其它团队合计 ÷ 全站')
    kpi_formula('有销量直播间数', '=COUNTIF(\'全站直播间\'!$E$7:$E$200,">0")', INT,
                '本周销售额 > 0 的直播间个数（含商品卡渠道）')
    last_kpi = r - 1

    style_rows(ws, first, last_kpi, 5, {}, zebra=False)
    for rr in range(first, last_kpi + 1):
        ws.cell(row=rr, column=2).alignment = RIGHT
        ws.cell(row=rr, column=3).alignment = RIGHT
        ws.cell(row=rr, column=4).alignment = RIGHT
    mark(ws, row_our_rev, 5, fill=P_HL)
    mark(ws, row_our_ord, 5, fill=P_HL)
    mark(ws, row_our_avg, 5, fill=P_HL)

    r = last_kpi + 2
    r = section(ws, r, '二、团队对比（按本周销售额降序）', span=9)
    r = header_row(ws, r, ['团队', '订单', '销售额', '销售额占比', '订单占比', '均价',
                           '有销量间数', '上周销售额', '销售额环比'])
    t_first = r
    order = sorted(x['cur_teams'], key=lambda t: -x['cur_teams'][t]['revenue'])
    for k, tm in enumerate(order):
        v = x['cur_teams'][tm]
        pv = x['prev_teams'].get(tm, {'revenue': 0.0, 'orders': 0})
        ws.cell(row=r, column=1, value=tm).font = F_BOLD
        ws.cell(row=r, column=2, value=v['orders']).font = F_INPUT
        ws.cell(row=r, column=3, value=v['revenue']).font = F_INPUT
        ws.cell(row=r, column=4, value='=IFERROR(C%d/$C$%d,"-")' % (r, t_first + len(order))).font = F_FORM
        ws.cell(row=r, column=5, value='=IFERROR(B%d/$B$%d,"-")' % (r, t_first + len(order))).font = F_FORM
        ws.cell(row=r, column=6, value='=IFERROR(C%d/B%d,"-")' % (r, r)).font = F_FORM
        ws.cell(row=r, column=7, value=len([q for q in v['rooms'] if x['cur']['rooms'][q]['orders'] > 0])).font = F_INPUT
        ws.cell(row=r, column=8, value=pv['revenue']).font = F_INPUT
        ws.cell(row=r, column=9, value='=IFERROR((C%d-H%d)/H%d,"-")' % (r, r, r)).font = F_FORM
        r += 1
    t_tot = r
    ws.cell(row=t_tot, column=1, value='全站合计').font = F_BOLD
    ws.cell(row=t_tot, column=2, value='=SUM(B%d:B%d)' % (t_first, t_tot - 1)).font = F_BOLD
    ws.cell(row=t_tot, column=3, value='=SUM(C%d:C%d)' % (t_first, t_tot - 1)).font = F_BOLD
    ws.cell(row=t_tot, column=4, value='=IFERROR(C%d/$C$%d,"-")' % (t_tot, t_tot)).font = F_BOLD
    ws.cell(row=t_tot, column=5, value='=IFERROR(B%d/$B$%d,"-")' % (t_tot, t_tot)).font = F_BOLD
    ws.cell(row=t_tot, column=6, value='=IFERROR(C%d/B%d,"-")' % (t_tot, t_tot)).font = F_BOLD
    ws.cell(row=t_tot, column=7, value='=SUM(G%d:G%d)' % (t_first, t_tot - 1)).font = F_BOLD
    ws.cell(row=t_tot, column=8, value='=SUM(H%d:H%d)' % (t_first, t_tot - 1)).font = F_BOLD
    ws.cell(row=t_tot, column=9, value='=IFERROR((C%d-H%d)/H%d,"-")' % (t_tot, t_tot, t_tot)).font = F_BOLD
    style_rows(ws, t_first, t_tot, 9, {2: INT, 3: MONEY, 4: PCT, 5: PCT, 6: MONEY1, 7: '0', 8: MONEY, 9: PCT},
               bold_row=t_tot, zebra=True)
    for k, tm in enumerate(order):
        if tm == '我司':
            mark(ws, t_first + k, 9, font=F_BOLD, fill=P_HL)
        elif tm == '良米':
            mark(ws, t_first + k, 9, fill=P_RIVAL)
    ws.conditional_formatting.add('C%d:C%d' % (t_first, t_tot - 1),
                                  DataBarRule(start_type='num', start_value=0, end_type='max',
                                              color=BRAND, showValue=True))

    r = t_tot + 2
    r = section(ws, r, '三、关键结论（明细见「结论与建议」页）', span=9)
    bullets(ws, r, 9, x['headlines'])

    widths(ws, [26, 15, 17, 13, 13, 11, 10, 15, 13])
    ws.freeze_panes = 'A%d' % (t_first)
    return {'kpi_first': first, 'kpi_last': last_kpi, 'team_first': t_first, 'team_tot': t_tot,
            'team_last': t_tot - 1, 'row_site_rev': row_site_rev, 'row_our_rev': row_our_rev,
            'row_liang_rev': row_liang_rev, 'row_other_rev': row_other_rev}


# ====================== Sheet: 我司直播间 ======================
def room_table(ctx, teams_cur, teams_prev, team, start_row, ws, span=11):
    """某团队各直播间明细表，返回 (合计行, 末行)。"""
    rooms = set(teams_cur.get(team, {'rooms': []})['rooms']) | set(teams_prev.get(team, {'rooms': []})['rooms'])
    rooms = sorted(rooms, key=lambda r: -ctx['cur']['rooms'].get(r, {'revenue': 0})['revenue'])
    hdr = ['直播间', '本周订单', '本周销售额', '本周均价', '上周订单', '上周销售额', '上周均价',
           '销售额环比', '订单环比', '占本团队销售额', '占全站销售额']
    r = header_row(ws, start_row, hdr)
    first = r
    for room in rooms:
        c = ctx['cur']['rooms'].get(room, {'orders': 0, 'revenue': 0.0})
        p = ctx['prev']['rooms'].get(room, {'orders': 0, 'revenue': 0.0})
        ws.cell(row=r, column=1, value=room).font = F_BOLD
        ws.cell(row=r, column=2, value=c['orders']).font = F_INPUT
        ws.cell(row=r, column=3, value=c['revenue']).font = F_INPUT
        ws.cell(row=r, column=4, value='=IFERROR(C%d/B%d,"-")' % (r, r)).font = F_FORM
        ws.cell(row=r, column=5, value=p['orders']).font = F_INPUT
        ws.cell(row=r, column=6, value=p['revenue']).font = F_INPUT
        ws.cell(row=r, column=7, value='=IFERROR(F%d/E%d,"-")' % (r, r)).font = F_FORM
        ws.cell(row=r, column=8, value='=IFERROR((C%d-F%d)/F%d,"-")' % (r, r, r)).font = F_FORM
        ws.cell(row=r, column=9, value='=IFERROR((B%d-E%d)/E%d,"-")' % (r, r, r)).font = F_FORM
        ws.cell(row=r, column=10, value='=IFERROR(C%d/SUM($C$%d:$C$%d),"-")' % (r, first, first + len(rooms) - 1)).font = F_FORM
        ws.cell(row=r, column=11, value="=IFERROR(C%d/总览!$B$%d,\"-\")" % (r, ctx['anchors']['row_site_rev'])).font = F_XREF
        r += 1
    tot = r
    ws.cell(row=tot, column=1, value='%s 合计' % team).font = F_BOLD
    for col in (2, 3, 5, 6):
        L = get_column_letter(col)
        ws.cell(row=tot, column=col, value='=SUM(%s%d:%s%d)' % (L, first, L, tot - 1)).font = F_BOLD
    for col, f in [(4, '=IFERROR(C%d/B%d,"-")' % (tot, tot)), (7, '=IFERROR(F%d/E%d,"-")' % (tot, tot)),
                   (8, '=IFERROR((C%d-F%d)/F%d,"-")' % (tot, tot, tot)), (9, '=IFERROR((B%d-E%d)/E%d,"-")' % (tot, tot, tot)),
                   (10, '=IFERROR(C%d/SUM($C$%d:$C$%d),"-")' % (tot, first, tot - 1))]:
        ws.cell(row=tot, column=col, value=f).font = F_BOLD
    ws.cell(row=tot, column=11, value="=IFERROR(C%d/总览!$B$%d,\"-\")" % (tot, ctx['anchors']['row_site_rev'])).font = F_XREF
    style_rows(ws, first, tot, 11, {2: INT, 3: MONEY, 4: MONEY1, 5: INT, 6: MONEY, 7: MONEY1,
                                    8: PCT, 9: PCT, 10: PCT, 11: PCT}, bold_row=tot)
    return tot, r


def sheet_our(wb, x):
    ws = wb.create_sheet('我司直播间')
    no_grid(ws)
    title_block(ws, '我司直播间 · 本周 %s' % x['label_cur'],
                '我司 = team_config 中归属「我司」的直播间 + 「我司商品卡」渠道　｜　对比上周 2026.%s　｜　按本周销售额降序'
                % x['label_prev'],
                '⚠ 「占全站销售额」= 本间销售额 ÷ 全站销售额（跨表引用「总览」）。订单口径，未扣退款', span=11)
    r = section(ws, 5, '一、我司分直播间明细', span=11)
    tot, _ = room_table(x, x['cur_teams'], x['prev_teams'], '我司', r, ws)
    ws.conditional_formatting.add('C%d:C%d' % (r + 1, tot - 1),
                                  DataBarRule(start_type='num', start_value=0, end_type='max',
                                              color='1E90FF', showValue=True))
    widths(ws, [26, 11, 15, 11, 11, 15, 11, 12, 11, 14, 13])
    ws.freeze_panes = 'B%d' % (r + 1)
    # 小结
    r = tot + 2
    r = section(ws, r, '二、分间小结（自动生成）', span=11)
    bullets(ws, r, 11, x['our_notes'])
    return ws


# ====================== Sheet: 竞对对比 ======================
def sheet_rival(wb, x):
    ws = wb.create_sheet('竞对对比')
    no_grid(ws)
    title_block(ws, '竞对对比 · 我司 vs 良米 vs 其它 %d 家团队' % len(x['other_teams']),
                '统计区间 2026.%s（%d天）　对比区间 2026.%s　｜　数据源 sales_analysis/history.json'
                % (x['label_cur'], x['n_days'], x['label_prev']),
                '⚠ 良米 = team_config 中归属「良米」的 14 间（含「良米商品卡」）；其余 8 家团队归入「其它团队」',
                span=11)
    r = section(ws, 5, '一、三方对比', span=11)
    r = header_row(ws, r, ['阵营', '订单', '销售额', '销售额占比', '均价', '有销量间数', '上周销售额', '销售额环比'])
    first = r
    groups = [('我司', x['our'], x['our_prev']),
              ('良米', x['liang'], x['liang_prev']),
              ('其它团队合计', {'orders': x['other_ord'], 'revenue': x['other_rev'],
                            'rooms': [q for t in x['other_teams'] for q in x['cur_teams'][t]['rooms']]},
               {'orders': x['other_ord_prev'], 'revenue': x['other_rev_prev']})]
    for name, v, pv in groups:
        ws.cell(row=r, column=1, value=name).font = F_BOLD
        ws.cell(row=r, column=2, value=v['orders']).font = F_INPUT
        ws.cell(row=r, column=3, value=v['revenue']).font = F_INPUT
        ws.cell(row=r, column=4, value="=IFERROR(C%d/总览!$B$%d,\"-\")" % (r, x['anchors']['row_site_rev'])).font = F_XREF
        ws.cell(row=r, column=5, value='=IFERROR(C%d/B%d,"-")' % (r, r)).font = F_FORM
        ws.cell(row=r, column=6,
                value=len([q for q in v['rooms'] if x['cur']['rooms'].get(q, {}).get('orders', 0) > 0])).font = F_INPUT
        ws.cell(row=r, column=7, value=pv['revenue']).font = F_INPUT
        ws.cell(row=r, column=8, value='=IFERROR((C%d-G%d)/G%d,"-")' % (r, r, r)).font = F_FORM
        r += 1
    ws.cell(row=r, column=1, value='全站合计').font = F_BOLD
    ws.cell(row=r, column=2, value='=SUM(B%d:B%d)' % (first, r - 1)).font = F_BOLD
    ws.cell(row=r, column=3, value='=SUM(C%d:C%d)' % (first, r - 1)).font = F_BOLD
    ws.cell(row=r, column=4, value="=IFERROR(C%d/总览!$B$%d,\"-\")" % (r, x['anchors']['row_site_rev'])).font = F_XREF
    ws.cell(row=r, column=5, value='=IFERROR(C%d/B%d,"-")' % (r, r)).font = F_BOLD
    ws.cell(row=r, column=6, value='=SUM(F%d:F%d)' % (first, r - 1)).font = F_BOLD
    ws.cell(row=r, column=7, value='=SUM(G%d:G%d)' % (first, r - 1)).font = F_BOLD
    ws.cell(row=r, column=8, value='=IFERROR((C%d-G%d)/G%d,"-")' % (r, r, r)).font = F_BOLD
    style_rows(ws, first, r, 8, {2: INT, 3: MONEY, 4: PCT, 5: MONEY1, 6: '0', 7: MONEY, 8: PCT},
               bold_row=r, zebra=False)
    mark(ws, first, 8, font=F_BOLD, fill=P_HL)
    mark(ws, first + 1, 8, fill=P_RIVAL)
    groups_tot = r

    r = groups_tot + 2
    r = section(ws, r, '二、良米分直播间明细', span=11)
    rival_first = r + 1
    lm_tot, _ = room_table(x, x['cur_teams'], x['prev_teams'], '良米', r, ws)
    for rr in range(rival_first, lm_tot + 1):
        if rr != lm_tot:
            for c in range(1, 12):
                cell = ws.cell(row=rr, column=c)
                if cell.fill.start_color.rgb in (None, '00000000', '00FAFBFC') or cell.fill.start_color.rgb == '00' + ZEBRA:
                    cell.fill = P_RIVAL
    mark(ws, lm_tot, 11, font=F_BOLD)

    r = lm_tot + 2
    r = section(ws, r, '三、其它团队分直播间明细', span=11)
    r = header_row(ws, r, ['团队', '直播间', '本周订单', '本周销售额', '本周均价', '上周销售额', '销售额环比', '占全站销售额'])
    first3 = r
    rows = []
    for tm in x['other_teams']:
        for room in x['cur_teams'][tm]['rooms']:
            rows.append((tm, room))
        for room in x['prev_teams'].get(tm, {'rooms': []})['rooms']:
            if (tm, room) not in rows:
                rows.append((tm, room))
    rows.sort(key=lambda t: -x['cur']['rooms'].get(t[1], {'revenue': 0})['revenue'])
    for tm, room in rows:
        c = x['cur']['rooms'].get(room, {'orders': 0, 'revenue': 0.0})
        p = x['prev']['rooms'].get(room, {'orders': 0, 'revenue': 0.0})
        ws.cell(row=r, column=1, value=tm).font = F_BODY
        ws.cell(row=r, column=2, value=room).font = F_BOLD
        ws.cell(row=r, column=3, value=c['orders']).font = F_INPUT
        ws.cell(row=r, column=4, value=c['revenue']).font = F_INPUT
        ws.cell(row=r, column=5, value='=IFERROR(D%d/C%d,"-")' % (r, r)).font = F_FORM
        ws.cell(row=r, column=6, value=p['revenue']).font = F_INPUT
        ws.cell(row=r, column=7, value='=IFERROR((D%d-F%d)/F%d,"-")' % (r, r, r)).font = F_FORM
        ws.cell(row=r, column=8, value="=IFERROR(D%d/总览!$B$%d,\"-\")" % (r, x['anchors']['row_site_rev'])).font = F_XREF
        r += 1
    tot3 = r
    ws.cell(row=tot3, column=1, value='其它合计').font = F_BOLD
    ws.cell(row=tot3, column=3, value='=SUM(C%d:C%d)' % (first3, tot3 - 1)).font = F_BOLD
    ws.cell(row=tot3, column=4, value='=SUM(D%d:D%d)' % (first3, tot3 - 1)).font = F_BOLD
    ws.cell(row=tot3, column=5, value='=IFERROR(D%d/C%d,"-")' % (tot3, tot3)).font = F_BOLD
    ws.cell(row=tot3, column=6, value='=SUM(F%d:F%d)' % (first3, tot3 - 1)).font = F_BOLD
    ws.cell(row=tot3, column=7, value='=IFERROR((D%d-F%d)/F%d,"-")' % (tot3, tot3, tot3)).font = F_BOLD
    ws.cell(row=tot3, column=8, value="=IFERROR(D%d/总览!$B$%d,\"-\")" % (tot3, x['anchors']['row_site_rev'])).font = F_XREF
    style_rows(ws, first3, tot3, 8, {3: INT, 4: MONEY, 5: MONEY1, 6: MONEY, 7: PCT, 8: PCT}, bold_row=tot3)
    for rr in range(first3, tot3):
        for cc in range(9, 12):
            ws.cell(row=rr, column=cc).border = B_ALL

    r = tot3 + 2
    r = section(ws, r, '四、竞对小结（自动生成）', span=11)
    bullets(ws, r, 11, x['rival_notes'])
    widths(ws, [26, 15, 17, 13, 13, 11, 15, 13, 11, 14, 13])
    ws.freeze_panes = 'A%d' % (first3)
    return ws


# ====================== Sheet: 全站直播间 ======================
def sheet_all_rooms(wb, x):
    ws = wb.create_sheet('全站直播间')
    no_grid(ws)
    rooms = set(x['cur']['rooms']) | set(x['prev']['rooms'])
    rooms = sorted(rooms, key=lambda q: -x['cur']['rooms'].get(q, {'revenue': 0})['revenue'])
    n_active = len([q for q in rooms if x['cur']['rooms'].get(q, {}).get('revenue', 0) > 0])
    title_block(ws, '全站直播间销量占比（本周 %s）' % x['label_cur'],
                '全部 %d 间（含「我司商品卡」「良米商品卡」渠道）；本周有销量 %d 间，其余为上周有量、本周 0　｜　按本周销售额降序'
                % (len(rooms), n_active),
                '⚠ 「占本团队销售额」用 SUMIF 按团队列汇总；「排名」用 RANK 函数，改数会自动重排', span=11)
    r = section(ws, 5, '一、全站直播间排名', span=11)
    r = header_row(ws, r, ['排名', '直播间', '团队', '本周订单', '本周销售额', '均价', '占全站销售额',
                           '占本团队销售额', '上周订单', '上周销售额', '销售额环比'])
    first = r
    n = len(rooms)
    last = first + n - 1
    for room in rooms:
        c = x['cur']['rooms'].get(room, {'orders': 0, 'revenue': 0.0})
        p = x['prev']['rooms'].get(room, {'orders': 0, 'revenue': 0.0})
        tmv = classify_room(room)
        ws.cell(row=r, column=1, value='=RANK(E%d,$E$%d:$E$%d)' % (r, first, last)).font = F_FORM
        ws.cell(row=r, column=2, value=room).font = F_BOLD
        ws.cell(row=r, column=3, value=tmv).font = F_BODY
        ws.cell(row=r, column=4, value=c['orders']).font = F_INPUT
        ws.cell(row=r, column=5, value=c['revenue']).font = F_INPUT
        ws.cell(row=r, column=6, value='=IFERROR(E%d/D%d,"-")' % (r, r)).font = F_FORM
        ws.cell(row=r, column=7, value='=IFERROR(E%d/SUM($E$%d:$E$%d),"-")' % (r, first, last)).font = F_FORM
        ws.cell(row=r, column=8, value='=IFERROR(E%d/SUMIF($C$%d:$C$%d,C%d,$E$%d:$E$%d),"-")'
                % (r, first, last, r, first, last)).font = F_FORM
        ws.cell(row=r, column=9, value=p['orders']).font = F_INPUT
        ws.cell(row=r, column=10, value=p['revenue']).font = F_INPUT
        ws.cell(row=r, column=11, value='=IFERROR((E%d-J%d)/J%d,"-")' % (r, r, r)).font = F_FORM
        r += 1
    tot = r
    ws.cell(row=tot, column=2, value='全站合计').font = F_BOLD
    for col in (4, 5, 9, 10):
        L = get_column_letter(col)
        ws.cell(row=tot, column=col, value='=SUM(%s%d:%s%d)' % (L, first, L, tot - 1)).font = F_BOLD
    ws.cell(row=tot, column=6, value='=IFERROR(E%d/D%d,"-")' % (tot, tot)).font = F_BOLD
    ws.cell(row=tot, column=7, value='=IFERROR(E%d/SUM($E$%d:$E$%d),"-")' % (tot, first, tot - 1)).font = F_BOLD
    ws.cell(row=tot, column=11, value='=IFERROR((E%d-J%d)/J%d,"-")' % (tot, tot, tot)).font = F_BOLD
    style_rows(ws, first, tot, 11, {1: '0', 4: INT, 5: MONEY, 6: MONEY1, 7: PCT, 8: PCT, 9: INT, 10: MONEY, 11: PCT},
               bold_row=tot)
    for i, room in enumerate(rooms):
        if classify_room(room) == '我司':
            mark(ws, first + i, 11, fill=P_HL)
        elif classify_room(room) == '良米':
            mark(ws, first + i, 11, fill=P_RIVAL)
    ws.conditional_formatting.add('E%d:E%d' % (first, last),
                                  DataBarRule(start_type='num', start_value=0, end_type='max',
                                              color=BRAND, showValue=True))
    widths(ws, [6, 26, 12, 11, 15, 11, 13, 15, 11, 15, 12])
    ws.freeze_panes = 'C%d' % first
    return ws


# ====================== Sheet: 商品结构 ======================
def sheet_products(wb, x):
    ws = wb.create_sheet('商品结构')
    no_grid(ws)
    title_block(ws, '商品结构 & 重点单品份额（本周 %s）' % x['label_cur'],
                '商品名已按 product_classifier.classify_product() 归并　｜　品类：手环 / 手表 / 耳机 / 眼镜 / 其它',
                '⚠ 商品口径为全站商品汇总；「我司占比」= 我司该商品销售额 ÷ 该商品全站销售额（跨表口径见「数据说明」）',
                span=11)
    r = section(ws, 5, '一、品类结构（全站）', span=11)
    r = header_row(ws, r, ['品类', '本周订单', '本周销售额', '占全站销售额', '我司销售额', '我司占该品类',
                           '良米销售额', '良米占该品类', '其它销售额', '其它占该品类', '上周销售额'])
    first = r
    cat_rows = []
    for cat in CATEGORIES:
        cur_rev = sum(v['revenue'] for (c, tm), v in x['cur_cat'].items() if c == cat)
        cur_ord = sum(v['orders'] for (c, tm), v in x['cur_cat'].items() if c == cat)
        prev_rev = sum(v['revenue'] for (c, tm), v in x['prev_cat'].items() if c == cat)
        our_rev = x['cur_cat'].get((cat, '我司'), {'orders': 0, 'revenue': 0.0})['revenue']
        lm_rev = x['cur_cat'].get((cat, '良米'), {'orders': 0, 'revenue': 0.0})['revenue']
        other_rev = cur_rev - our_rev - lm_rev
        cat_rows.append((cat, cur_ord, cur_rev, prev_rev, our_rev, lm_rev, other_rev))
    last = first + len(cat_rows) - 1
    tot = last + 1
    for i, (cat, cur_ord, cur_rev, prev_rev, our_rev, lm_rev, other_rev) in enumerate(cat_rows):
        rr = first + i
        ws.cell(row=rr, column=1, value=cat).font = F_BOLD
        ws.cell(row=rr, column=2, value=cur_ord).font = F_INPUT
        ws.cell(row=rr, column=3, value=cur_rev).font = F_INPUT
        ws.cell(row=rr, column=4, value='=IFERROR(C%d/$C$%d,"-")' % (rr, tot)).font = F_FORM
        ws.cell(row=rr, column=5, value=our_rev).font = F_INPUT
        ws.cell(row=rr, column=6, value='=IFERROR(E%d/C%d,"-")' % (rr, rr)).font = F_FORM
        ws.cell(row=rr, column=7, value=lm_rev).font = F_INPUT
        ws.cell(row=rr, column=8, value='=IFERROR(G%d/C%d,"-")' % (rr, rr)).font = F_FORM
        ws.cell(row=rr, column=9, value=other_rev).font = F_INPUT
        ws.cell(row=rr, column=10, value='=IFERROR(I%d/C%d,"-")' % (rr, rr)).font = F_FORM
        ws.cell(row=rr, column=11, value=prev_rev).font = F_INPUT
    ws.cell(row=tot, column=1, value='合计').font = F_BOLD
    for col in (2, 3, 5, 7, 9, 11):
        L = get_column_letter(col)
        ws.cell(row=tot, column=col, value='=SUM(%s%d:%s%d)' % (L, first, L, last)).font = F_BOLD
    ws.cell(row=tot, column=4, value='=IFERROR(C%d/$C$%d,"-")' % (tot, tot)).font = F_BOLD
    ws.cell(row=tot, column=6, value='=IFERROR(E%d/C%d,"-")' % (tot, tot)).font = F_BOLD
    ws.cell(row=tot, column=8, value='=IFERROR(G%d/C%d,"-")' % (tot, tot)).font = F_BOLD
    ws.cell(row=tot, column=10, value='=IFERROR(I%d/C%d,"-")' % (tot, tot)).font = F_BOLD
    style_rows(ws, first, tot, 11, {2: INT, 3: MONEY, 4: PCT, 5: MONEY, 6: PCT, 7: MONEY, 8: PCT,
                                    9: MONEY, 10: PCT, 11: MONEY}, bold_row=tot)
    cat_tot_row = tot

    r = tot + 2
    r = section(ws, r, '二、商品 Top %d（按本周销售额降序）' % x['top_n'], span=11)
    r = header_row(ws, r, ['商品', '本周订单', '本周销售额', '均价', '占全站销售额', '上周订单', '上周销售额',
                           '销售额环比', '本周排名', '上周排名', '排名变化'])
    p_first = r
    prods_cur = sorted(x['cur']['products'].items(), key=lambda kv: -kv[1]['revenue'])[:x['top_n']]
    prods_prev_rank = {p: i + 1 for i, (p, _) in
                       enumerate(sorted(x['prev']['products'].items(), key=lambda kv: -kv[1]['revenue']))}
    n = len(prods_cur)
    p_last = p_first + n - 1
    for i, (p, v) in enumerate(prods_cur):
        rr = p_first + i
        pv = x['prev']['products'].get(p, {'orders': 0, 'revenue': 0.0})
        ws.cell(row=rr, column=1, value=p).font = F_BOLD
        ws.cell(row=rr, column=2, value=v['orders']).font = F_INPUT
        ws.cell(row=rr, column=3, value=v['revenue']).font = F_INPUT
        ws.cell(row=rr, column=4, value='=IFERROR(C%d/B%d,"-")' % (rr, rr)).font = F_FORM
        ws.cell(row=rr, column=5, value="=IFERROR(C%d/总览!$B$%d,\"-\")" % (rr, x['anchors']['row_site_rev'])).font = F_XREF
        ws.cell(row=rr, column=6, value=pv['orders']).font = F_INPUT
        ws.cell(row=rr, column=7, value=pv['revenue']).font = F_INPUT
        ws.cell(row=rr, column=8, value='=IFERROR((C%d-G%d)/G%d,"-")' % (rr, rr, rr)).font = F_FORM
        ws.cell(row=rr, column=9, value='=RANK(C%d,$C$%d:$C$%d)' % (rr, p_first, p_last)).font = F_FORM
        ws.cell(row=rr, column=10, value=prods_prev_rank.get(p, '')).font = F_INPUT
        ws.cell(row=rr, column=11, value='=IF(J%d="","新进",J%d-I%d)' % (rr, rr, rr)).font = F_FORM
    style_rows(ws, p_first, p_last, 11, {2: INT, 3: MONEY, 4: MONEY1, 5: PCT, 6: INT, 7: MONEY,
                                         8: PCT, 9: '0', 10: '0', 11: '+0;-0;0'})

    r = p_last + 2
    r = section(ws, r, '三、重点单品 × 团队份额（全站销售额 Top 10）', span=11)
    r = header_row(ws, r, ['商品', '全站订单', '全站销售额', '我司订单', '我司销售额', '我司占比',
                           '良米订单', '良米销售额', '良米占比', '其它销售额', '其它占比'])
    k_first = r
    for i, (p, v) in enumerate(prods_cur[:10]):
        rr = k_first + i
        our_o = x['cur']['prod_team'].get((p, '我司'), {'orders': 0, 'revenue': 0.0})
        lm = x['cur']['prod_team'].get((p, '良米'), {'orders': 0, 'revenue': 0.0})
        other = v['revenue'] - our_o['revenue'] - lm['revenue']
        ws.cell(row=rr, column=1, value=p).font = F_BOLD
        ws.cell(row=rr, column=2, value=v['orders']).font = F_INPUT
        ws.cell(row=rr, column=3, value=v['revenue']).font = F_INPUT
        ws.cell(row=rr, column=4, value=our_o['orders']).font = F_INPUT
        ws.cell(row=rr, column=5, value=our_o['revenue']).font = F_INPUT
        ws.cell(row=rr, column=6, value='=IFERROR(E%d/C%d,"-")' % (rr, rr)).font = F_FORM
        ws.cell(row=rr, column=7, value=lm['orders']).font = F_INPUT
        ws.cell(row=rr, column=8, value=lm['revenue']).font = F_INPUT
        ws.cell(row=rr, column=9, value='=IFERROR(H%d/C%d,"-")' % (rr, rr)).font = F_FORM
        ws.cell(row=rr, column=10, value=other).font = F_INPUT
        ws.cell(row=rr, column=11, value='=IFERROR(J%d/C%d,"-")' % (rr, rr)).font = F_FORM
    style_rows(ws, k_first, k_first + min(10, n) - 1, 11,
               {2: INT, 3: MONEY, 4: INT, 5: MONEY, 6: PCT, 7: INT, 8: MONEY, 9: PCT, 10: MONEY, 11: PCT})
    widths(ws, [26, 11, 15, 12, 13, 13, 13, 13, 13, 13, 10])
    ws.freeze_panes = 'A%d' % p_first
    return ws, {'cat_first': first, 'cat_tot': cat_tot_row, 'prod_first': p_first, 'prod_last': p_last}


# ====================== Sheet: 逐日明细 ======================
def sheet_daily(wb, x):
    ws = wb.create_sheet('逐日明细')
    no_grid(ws)
    title_block(ws, '逐日明细 · %s' % x['label_cur'],
                '本周 %d 天 + 上周 %d 天逐日对比（我司 / 良米 / 其它团队）　｜　数据源 sales_analysis/history.json'
                % (x['n_days'], len(x['prev']['days'])),
                '⚠ 占比均为「占当日全站销售额」；当日入库缺失则显示为 0', span=11)
    hdr = ['日期', '全站订单', '全站销售额', '我司订单', '我司销售额', '我司销售额占比',
           '良米订单', '良米销售额', '良米占比', '其它销售额', '其它占比']
    anchors = {}
    row = 5
    for tag, days, key in (('一、本周 %s' % x['label_cur'], x['cur']['days'], 'cur'),
                           ('二、上周 %s' % x['label_prev'], x['prev']['days'], 'prev')):
        row = section(ws, row, tag, span=11)
        row = header_row(ws, row, hdr)
        first = row
        for d in days:
            rooms = d.get('rooms') or {}
            t_ord = t_rev = o_ord = o_rev = l_ord = l_rev = 0
            for room, ri in rooms.items():
                tm = classify_room(room)
                t_ord += ri.get('orders', 0) or 0
                t_rev += ri.get('revenue', 0) or 0.0
                if tm == '我司':
                    o_ord += ri.get('orders', 0) or 0
                    o_rev += ri.get('revenue', 0) or 0.0
                elif tm == '良米':
                    l_ord += ri.get('orders', 0) or 0
                    l_rev += ri.get('revenue', 0) or 0.0
            ws.cell(row=row, column=1, value=d['date']).font = F_BODY
            ws.cell(row=row, column=2, value=t_ord).font = F_INPUT
            ws.cell(row=row, column=3, value=t_rev).font = F_INPUT
            ws.cell(row=row, column=4, value=o_ord).font = F_INPUT
            ws.cell(row=row, column=5, value=o_rev).font = F_INPUT
            ws.cell(row=row, column=6, value='=IFERROR(E%d/C%d,"-")' % (row, row)).font = F_FORM
            ws.cell(row=row, column=7, value=l_ord).font = F_INPUT
            ws.cell(row=row, column=8, value=l_rev).font = F_INPUT
            ws.cell(row=row, column=9, value='=IFERROR(H%d/C%d,"-")' % (row, row)).font = F_FORM
            ws.cell(row=row, column=10, value=t_rev - o_rev - l_rev).font = F_INPUT
            ws.cell(row=row, column=11, value='=IFERROR(J%d/C%d,"-")' % (row, row)).font = F_FORM
            row += 1
        tot = row
        ws.cell(row=tot, column=1, value='合计（本周）' if key == 'cur' else '合计（上周）').font = F_BOLD
        for col in (2, 3, 4, 5, 7, 8, 10):
            L = get_column_letter(col)
            ws.cell(row=tot, column=col, value='=SUM(%s%d:%s%d)' % (L, first, L, tot - 1)).font = F_BOLD
        # 占比列（6/9/11）在合计行必须引用各自的「销售额列 ÷ 全站销售额列」（5/8/10），
        # 若按同列引用会形成循环引用（Excel 静默算成 0，不报错），务必用 src 列。
        for col, src in ((6, 5), (9, 8), (11, 10)):
            S = get_column_letter(src)
            ws.cell(row=tot, column=col, value='=IFERROR(%s%d/C%d,"-")' % (S, tot, tot)).font = F_BOLD
        style_rows(ws, first, tot, 11, {2: INT, 3: MONEY, 4: INT, 5: MONEY, 6: PCT, 7: INT, 8: MONEY,
                                        9: PCT, 10: MONEY, 11: PCT}, bold_row=tot)
        anchors[key] = (first, tot - 1)
        row = tot + 2
    widths(ws, [26, 11, 15, 11, 15, 14, 11, 15, 11, 13, 11])
    ws.freeze_panes = 'A6'
    return ws, anchors


# ====================== Sheet: 结论与建议 ======================
def sheet_findings(wb, x):
    ws = wb.create_sheet('结论与建议')
    no_grid(ws)
    title_block(ws, '结论与建议 · %s' % x['label_cur'],
                '本页文字由 tools/gen_weekly_report.py 依据 history.json 自动生成（数字与各表同源，改动数据后重跑即更新）',
                '⚠ 结论仅基于订单入库口径（未扣退款），不包含达人分销 / 线下渠道数据', span=9)
    r = 5
    for title, items in x['findings']:
        r = section(ws, r, title, span=9)
        r = bullets(ws, r, 9, items)
        r += 1
    widths(ws, [22, 16, 16, 12, 12, 12, 12, 12, 12])
    return ws


# ====================== Sheet: 趋势图 ======================
def sheet_charts(wb, x, anchors):
    ws = wb.create_sheet('趋势图')
    no_grid(ws)
    title_block(ws, '趋势图 · %s' % x['label_cur'], '图表数据引用「逐日明细」「总览」「商品结构」页；改数后图表自动更新',
                None, span=9)
    dfirst, dlast = anchors['daily']['cur']
    ch = LineChart()
    ch.title = '逐日销售额：我司 vs 良米 vs 其它（%s）' % x['label_cur']
    ch.height, ch.width = 8.5, 24
    ch.y_axis.title = '销售额（元）'
    ch.x_axis.title = '日期'
    data = Reference(wb['逐日明细'], min_col=5, max_col=5, min_row=dfirst - 1, max_row=dlast)
    data2 = Reference(wb['逐日明细'], min_col=8, max_col=8, min_row=dfirst - 1, max_row=dlast)
    data3 = Reference(wb['逐日明细'], min_col=10, max_col=10, min_row=dfirst - 1, max_row=dlast)
    cats = Reference(wb['逐日明细'], min_col=1, max_col=1, min_row=dfirst, max_row=dlast)
    ch.add_data(data, titles_from_data=True)
    ch.add_data(data2, titles_from_data=True)
    ch.add_data(data3, titles_from_data=True)
    ch.set_categories(cats)
    ws.add_chart(ch, 'A5')

    ch2 = BarChart()
    ch2.type = 'bar'
    ch2.title = '各团队销售额（%s）' % x['label_cur']
    ch2.height, ch2.width = 9, 24
    tf, tl = anchors['overview']['team_first'], anchors['overview']['team_last']
    data4 = Reference(wb['总览'], min_col=3, max_col=3, min_row=tf - 1, max_row=tl)
    cats2 = Reference(wb['总览'], min_col=1, max_col=1, min_row=tf, max_row=tl)
    ch2.add_data(data4, titles_from_data=True)
    ch2.set_categories(cats2)
    ws.add_chart(ch2, 'A24')

    ch3 = PieChart()
    ch3.title = '品类销售额占比（%s）' % x['label_cur']
    ch3.height, ch3.width = 9, 12
    cf, cl = anchors['products']['cat_first'], anchors['products']['cat_tot'] - 1
    data5 = Reference(wb['商品结构'], min_col=3, max_col=3, min_row=cf - 1, max_row=cl)
    cats3 = Reference(wb['商品结构'], min_col=1, max_col=1, min_row=cf, max_row=cl)
    ch3.add_data(data5, titles_from_data=True)
    ch3.set_categories(cats3)
    ws.add_chart(ch3, 'A43')
    return ws


# ====================== Sheet: 数据说明 ======================
def sheet_notes(wb, x):
    ws = wb.create_sheet('数据说明')
    no_grid(ws)
    title_block(ws, '数据说明与口径', '生成时间口径：以 sales_analysis/history.json 入库数据为准', None, span=6)
    r = 5
    rows = [
        ('数据源', 'sales_analysis/history.json（每日订单入库产物，入库流程见 WORKFLOW.md）'),
        ('统计区间', '%s ~ %s（%d 天）' % (x['start'], x['end'], x['n_days'])),
        ('对比区间', ('%s ~ %s（%d 天，紧邻其前的等长窗口）'
                    % (x['prev_start'], x['prev_end'], len(x['prev']['days']))) if x['prev_start'] else '无（数据不足）'),
        ('异常峰值日', '%s → %s' % (x['spike_txt'], x['spike_advice'])),
        ('直播间归属', 'team_config.py TEAM_MAP；未列出的房间按 classify_room() 兜底归「良米」'),
        ('团队口径', 'TEAM_MAP 登记：我司 %s 间 +「我司商品卡」；良米 %s 间 +「良米商品卡」；'
                    '其余 %s 家团队归「其它团队」。本周实际有销量：我司 %d 间、良米 %d 间'
                    % (x['cfg_counts'].get('我司', 0), x['cfg_counts'].get('良米', 0),
                       x['other_cfg_n'], x['our_rooms_n'], x['liang_rooms_n'])),
        ('商品口径', '商品名经 product_classifier.classify_product() 归并；品类 = 手环 / 手表 / 耳机 / 眼镜 / 其它'),
        ('订单数', '当日入库明细的订单行数合计（订单口径，未扣退款）'),
        ('销售额', '当日入库明细的成交金额合计（未扣退款）'),
        ('均价', '销售额 ÷ 订单数（Excel 公式，随数据自动重算）'),
        ('占比', '该项 ÷ 对应分母（全站 / 本团队 / 本品类），Excel 公式'),
        ('环比', '(本周 − 上周) ÷ 上周，Excel 公式；上周为 0 时显示「-」'),
        ('一致性校验', '每日 total_orders 与各直播间订单之和已校验，差异 %s'
                    % ('0（一致）' if x['consistency'] == 0 else '%d 单（需排查）' % x['consistency'])),
    ]
    r = header_row(ws, r, ['项目', '说明', '', '', '', ''])
    first = r
    for name, desc in rows:
        ws.cell(row=r, column=1, value=name).font = F_BOLD
        c = ws.cell(row=r, column=2, value=desc)
        c.font = F_BODY
        c.alignment = LEFT
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
        for cc in range(1, 7):
            ws.cell(row=r, column=cc).border = B_ALL
            if cc == 1:
                ws.cell(row=r, column=cc).fill = P_HEAD_BG
        ws.row_dimensions[r].height = 22
        r += 1

    r += 1
    r = section(ws, r, '颜色约定（沿用项目 house style）', span=6)
    legend = [
        ('深蓝字 1F4E79', '硬编码输入（来自 history.json 的原始数值）', F_INPUT, None),
        ('深灰字 404040', 'Excel 公式（占比 / 环比 / 合计 / 均价）', F_FORM, None),
        ('绿色字 2E7D32', '跨表引用（如「占全站销售额」引用「总览」页）', F_XREF, None),
        ('橙色表头', '表头行', F_HDR, P_HDR),
        ('橙色底合计行', '合计 / 全站合计', F_BOLD, P_TOTAL),
        ('浅橙底', '我司行（重点观察）', F_BOLD, P_HL),
        ('浅灰蓝底', '良米行（主要竞对）', F_BODY, P_RIVAL),
    ]
    r = header_row(ws, r, ['样式', '含义', '', '', '', ''])
    for name, desc, font, fill in legend:
        ws.cell(row=r, column=1, value=name).font = font
        if fill:
            ws.cell(row=r, column=1).fill = fill
        c = ws.cell(row=r, column=2, value=desc)
        c.font = F_BODY
        c.alignment = LEFT
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
        for cc in range(1, 7):
            ws.cell(row=r, column=cc).border = B_ALL
        ws.row_dimensions[r].height = 21
        r += 1

    r += 1
    r = section(ws, r, '复现命令', span=6)
    cmds = [
        'python tools/gen_weekly_report.py                      # 最近 7 个完整日（每周一跑上一周）',
        'python tools/gen_weekly_report.py --start 2026-09-28 --end 2026-10-03',
        'python tools/gen_weekly_report.py --top 30 --out "D:\\周报.xlsx"',
    ]
    for cmd in cmds:
        c = ws.cell(row=r, column=1, value=cmd)
        c.font = Font(name='Consolas', size=9, color=INK)
        c.alignment = LEFT
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        ws.row_dimensions[r].height = 19
        r += 1
    widths(ws, [22, 26, 14, 14, 14, 14])
    return ws


# ====================== 结论文本 ======================
def build_text(x):
    ct, pt = x['cur']['total'], x['prev']['total']
    our, liang = x['our'], x['liang']
    ourp, liangp = x['our_prev'], x['liang_prev']
    n = x['n_days']
    our_share = our['revenue'] / ct['revenue'] if ct['revenue'] else 0
    our_share_p = ourp['revenue'] / pt['revenue'] if pt['revenue'] else 0
    lm_share = liang['revenue'] / ct['revenue'] if ct['revenue'] else 0
    lm_share_p = liangp['revenue'] / pt['revenue'] if pt['revenue'] else 0
    ratio = our['revenue'] / liang['revenue'] if liang['revenue'] else 0
    ratio_p = ourp['revenue'] / liangp['revenue'] if liangp['revenue'] else 0

    our_rooms = sorted(x['cur']['rooms'].items(), key=lambda kv: -kv[1]['revenue'])
    our_rooms = [(r, v) for r, v in our_rooms if classify_room(r) == '我司' and v['revenue'] > 0]
    lm_rooms = [(r, v) for r, v in sorted(x['cur']['rooms'].items(), key=lambda kv: -kv[1]['revenue'])
                if classify_room(r) == '良米' and v['revenue'] > 0]

    # 我司分间变化（仅看本周或上周销售额 >= 5万的间，避免小样本噪声）
    moves = []
    for room in set(x['cur']['rooms']) | set(x['prev']['rooms']):
        if classify_room(room) != '我司':
            continue
        c = x['cur']['rooms'].get(room, {'revenue': 0.0})['revenue']
        p = x['prev']['rooms'].get(room, {'revenue': 0.0})['revenue']
        if max(c, p) >= 50000:
            moves.append((room, c, p, wow(c, p)))
    moves.sort(key=lambda t: (t[3] if t[3] is not None else -9))
    up = moves[-1] if moves else None
    down = moves[0] if moves else None

    prods = sorted(x['cur']['products'].items(), key=lambda kv: -kv[1]['revenue'])
    p_top = prods[0] if prods else ('—', {'orders': 0, 'revenue': 0.0, 'avg_price': 0})
    p_top_share = p_top[1]['revenue'] / ct['revenue'] if ct['revenue'] else 0
    b11 = p_top[0] if p_top[0] == '小米手环11' else next((p for p, _ in prods if p == '小米手环11'), '小米手环11')
    b11_team = {}
    for (p, tm), v in x['cur']['prod_team'].items():
        if p == b11:
            b11_team[tm] = b11_team.get(tm, 0.0) + v['revenue']
    b11_all = x['cur']['products'].get(b11, {'revenue': 0.0, 'orders': 0})
    b11_our = b11_team.get('我司', 0.0)
    b11_lm = b11_team.get('良米', 0.0)
    b11_other = b11_all['revenue'] - b11_our - b11_lm
    b11_share = b11_all['revenue'] / ct['revenue'] if ct['revenue'] else 0

    cat_total = {}
    for (c, tm), v in x['cur_cat'].items():
        cat_total[c] = cat_total.get(c, 0.0) + v['revenue']
    cat_txt = '、'.join('%s %s（%s）' % (c, wan(cat_total.get(c, 0.0)),
                                       pct(cat_total.get(c, 0.0) / ct['revenue'] if ct['revenue'] else 0))
                       for c in CATEGORIES[:4])

    # ---- 异常峰值日检测（首销/大促日会把环比拉成失真值，必须显式提示）----
    def _day_stat(days):
        out = []
        for d in days:
            rooms = d.get('rooms') or {}
            out.append((d['date'],
                        sum((ri.get('orders', 0) or 0) for ri in rooms.values()),
                        sum((ri.get('revenue', 0) or 0.0) for ri in rooms.values())))
        return out

    def _spikes(stat):
        if len(stat) < 3:
            return []
        vals = sorted(v for _, v, _ in stat)
        med = vals[len(vals) // 2]
        if med <= 0:
            return []
        return [(dt, v, rv, v / float(med)) for dt, v, rv in stat if v >= 2 * med]

    ds_prev = _day_stat(x['prev']['days'])
    ds_cur = _day_stat(x['cur']['days'])
    spikes_prev = _spikes(ds_prev)
    spikes_cur = _spikes(ds_cur)

    day_range_txt = '—'
    if ds_cur:
        dmax = max(ds_cur, key=lambda t: t[2])
        dmin = min(ds_cur, key=lambda t: t[2])
        day_range_txt = '最高 %s %s（%s 单），最低 %s %s（%s 单）' % (
            d2s(dmax[0]), wan(dmax[2]), num(dmax[1]), d2s(dmin[0]), wan(dmin[2]), num(dmin[1]))

    def _spike_txt(items):
        return '、'.join('%s %s 单（约为该区间中位日的 %.1f 倍）' % (d2s(dt), num(v), k) for dt, v, _, k in items)

    SPIKE_ADVICE = '首销 / 大促日会显著抬高该区间基数，环比数字仅供参考，趋势判断请看日均与单日分布'
    spike_txt = '无（各单日订单量均在区间中位日的 2 倍以内）'
    if spikes_prev or spikes_cur:
        bits = []
        if spikes_prev:
            bits.append('对比区间 %s 含 %d 个异常峰值日：%s'
                        % (x['label_prev'], len(spikes_prev), _spike_txt(spikes_prev)))
        if spikes_cur:
            bits.append('本区间 %s 含 %d 个异常峰值日：%s'
                        % (x['label_cur'], len(spikes_cur), _spike_txt(spikes_cur)))
        spike_txt = '；'.join(bits)
    x['spike_txt'] = spike_txt
    x['spike_advice'] = SPIKE_ADVICE

    hl = []
    hl.append('大盘：全站 %s 单 / %s，日均 %s 单 / %s；销售额环比 %s，订单环比 %s。'
              % (num(ct['orders']), wan(ct['revenue']), num(ct['orders'] / float(n)), wan(ct['revenue'] / float(n)),
                 signed_pct(wow(ct['revenue'], pt['revenue']) or 0), signed_pct(wow(ct['orders'], pt['orders']) or 0)))
    hl.append('我司：%s 单 / %s，销售额占比 %s（上周 %s，%+.1f 个百分点）；与良米销售额之比 %s（上周 %s）。'
              % (num(our['orders']), wan(our['revenue']), pct(our_share), pct(our_share_p),
                 (our_share - our_share_p) * 100, '%.2fx' % ratio, '%.2fx' % ratio_p))
    hl.append('良米：%s 单 / %s，占比 %s（上周 %s）；良米本周有销量 %d 间，头部为「%s」（%s，占全站 %s）。'
              % (num(liang['orders']), wan(liang['revenue']), pct(lm_share), pct(lm_share_p), len(lm_rooms),
                 lm_rooms[0][0] if lm_rooms else '—', wan(lm_rooms[0][1]['revenue']) if lm_rooms else '—',
                 pct(lm_rooms[0][1]['revenue'] / ct['revenue'] if lm_rooms and ct['revenue'] else 0)))
    hl.append('单品：%s 全站 %s 台 / %s（占全站销售额 %s）；其中我司 %s（%s）、良米 %s（%s）。'
              % (b11, num(b11_all.get('orders', 0)), wan(b11_all['revenue']), pct(b11_share),
                 wan(b11_our), pct(b11_our / b11_all['revenue'] if b11_all['revenue'] else 0),
                 wan(b11_lm), pct(b11_lm / b11_all['revenue'] if b11_all['revenue'] else 0)))
    hl.append('结构：%s。' % cat_txt)
    if spikes_prev or spikes_cur:
        hl.append('口径提示：%s → %s。' % (spike_txt, SPIKE_ADVICE))

    our_notes = []
    if our_rooms:
        top3 = our_rooms[:3]
        our_notes.append('我司 %d 间有销量；销售额 Top3：%s。'
                         % (len(our_rooms),
                            '、'.join('%s %s（占我司 %s）' % (r, wan(v['revenue']),
                                                          pct(v['revenue'] / our['revenue'] if our['revenue'] else 0))
                                     for r, v in top3)))
    if x['cur']['rooms'].get('我司商品卡'):
        card = x['cur']['rooms']['我司商品卡']
        card_p = x['prev']['rooms'].get('我司商品卡', {'revenue': 0.0})['revenue']
        our_notes.append('我司商品卡渠道 %s（占我司 %s，环比 %s）；商品卡属货架/商品卡渠道，不占用直播时长。'
                         % (wan(card['revenue']), pct(card['revenue'] / our['revenue'] if our['revenue'] else 0),
                            signed_pct(wow(card['revenue'], card_p) or 0)))
    if up and up[3] is not None and up[3] > 0:
        our_notes.append('环比涨幅最大：%s %s → %s（%s）。' % (up[0], wan(up[2]), wan(up[1]), signed_pct(up[3])))
    if down and down[3] is not None and down[3] < 0:
        our_notes.append('环比跌幅最大：%s %s → %s（%s），需复盘时段/排品/投流。'
                         % (down[0], wan(down[2]), wan(down[1]), signed_pct(down[3])))
    idle = [r for r, v in x['cur']['rooms'].items() if classify_room(r) == '我司' and v['revenue'] == 0]
    if idle:
        our_notes.append('本周无销量入库的我司直播间：%s（确认是否停播 / 未入库）。' % '、'.join(idle))

    rival_notes = []
    rival_notes.append('三方格局：我司 %s（%s）/ 良米 %s（%s）/ 其它 %d 家合计 %s（%s）。'
                       % (wan(our['revenue']), pct(our_share), wan(liang['revenue']), pct(lm_share),
                          len(x['other_teams']), wan(x['other_rev']),
                          pct(x['other_rev'] / ct['revenue'] if ct['revenue'] else 0)))
    if lm_rooms:
        rival_notes.append('良米 Top3：%s。'
                           % '、'.join('%s %s（占全站 %s）' % (r, wan(v['revenue']),
                                                            pct(v['revenue'] / ct['revenue'] if ct['revenue'] else 0))
                                       for r, v in lm_rooms[:3]))
    if x['other_teams']:
        big = x['other_teams_sorted'][0]
        rival_notes.append('其它团队头名：%s（%s，占全站 %s，%d 间在跑）。'
                           % (big, wan(x['cur_teams'][big]['revenue']),
                              pct(x['cur_teams'][big]['revenue'] / ct['revenue'] if ct['revenue'] else 0),
                              len(x['cur_teams'][big]['rooms'])))
    if b11_all['revenue']:
        gap = b11_lm - b11_our
        rival_notes.append('核心单品 %s：我司 %s vs 良米 %s，差额 %s（占该单品全站销售额 %s）；良米在该单品上%s。'
                           % (b11, wan(b11_our), wan(b11_lm), wan(abs(gap)),
                              pct(abs(gap) / b11_all['revenue']),
                              '领先' if gap > 0 else '落后'))

    find = []
    find.append(('一、大盘', hl[:1] + ['单日分布：%s。' % day_range_txt]))
    find.append(('二、我司表现', [hl[1]] + our_notes))
    find.append(('三、竞对动态', [hl[2]] + rival_notes))
    find.append(('四、商品结构', hl[3:5]))

    risk = []
    if our_share < lm_share:
        risk.append('份额落后：我司销售额占比 %s < 良米 %s（差 %s 个百分点），需在排播时长与投流上追赶。'
                    % (pct(our_share), pct(lm_share), '%.1f' % ((lm_share - our_share) * 100)))
    else:
        risk.append('份额领先：我司 %s > 良米 %s，注意守住头部单品的价格与赠品节奏。' % (pct(our_share), pct(lm_share)))
    if our_share < our_share_p:
        risk.append('份额回落：%+.1f 个百分点（%s → %s），需排查是被竞对抢量还是自身排播减少。'
                    % ((our_share - our_share_p) * 100, pct(our_share_p), pct(our_share)))
    else:
        risk.append('份额提升：%+.1f 个百分点（%s → %s），可复制本周有效动作（排品 / 时段 / 话术）。'
                    % ((our_share - our_share_p) * 100, pct(our_share_p), pct(our_share)))
    if b11_our < b11_lm:
        risk.append('%s 我司份额偏弱（我司 %s vs 良米 %s）：建议核对我司各间的库存/价格与商品卡曝光，'
                    '把落后差额（%s）拆到具体直播间去追。'
                    % (b11, pct(b11_our / b11_all['revenue'] if b11_all['revenue'] else 0),
                       pct(b11_lm / b11_all['revenue'] if b11_all['revenue'] else 0), wan(b11_lm - b11_our)))
    if down and down[3] is not None and down[3] < -0.2:
        risk.append('单间异常：%s 环比 %s，建议本周先复盘该间（时段、主播、排品、投流），再决定是否调整资源。'
                    % (down[0], signed_pct(down[3])))
    if x['other_rev'] / ct['revenue'] > 0.12 if ct['revenue'] else False:
        risk.append('其它团队合计占比 %s，已不可忽视（%s 等），关注其低价/国补类打法对我司价格带的影响。'
                    % (pct(x['other_rev'] / ct['revenue']), '、'.join(x['other_teams_sorted'][:3])))
    risk.append('口径提醒：以上均为订单入库口径、未扣退款；结论用于内部排播与投流决策，不作为对外披露数据。')
    if spikes_prev or spikes_cur:
        risk.append('环比失真提醒：%s → %s。建议本周复盘以「日均销售额 / 单日分布」为主，不要直接拿环比结论问责排播。'
                    % (spike_txt, SPIKE_ADVICE))
    find.append(('五、风险与行动建议', risk))

    x['headlines'] = hl
    x['our_notes'] = our_notes
    x['rival_notes'] = rival_notes
    x['findings'] = find
    return x


# ====================== 主流程 ======================
def main(argv=None):
    ap = argparse.ArgumentParser(description='生成直播间销量周报 xlsx')
    ap.add_argument('--start', help='统计起始日 YYYY-MM-DD（默认：history.json 里倒数第 7 天）')
    ap.add_argument('--end', help='统计结束日 YYYY-MM-DD（默认：history.json 最后一天）')
    ap.add_argument('--days', type=int, default=7, help='不指定 --start 时的窗口天数（默认 7）')
    ap.add_argument('--top', type=int, default=25, help='商品榜行数（默认 25）')
    ap.add_argument('--out', help='输出 xlsx 路径（默认桌面）')
    ap.add_argument('--check-json', help='把自检数值写到该 json（供 Excel COM 复核）')
    a = ap.parse_args(argv)

    history = load_history()
    dates = all_dates(history)
    if a.start and a.end:
        start, end = a.start, a.end
    else:
        end = a.end or dates[-1]
        if a.start:
            start = a.start
        else:
            win = [d for d in dates if d <= end][-a.days:]
            start = win[0]
    x = build_ctx(history, start, end, top_n=a.top)
    build_text(x)

    # 一致性校验：每日 total_orders vs 各间订单之和
    diff = 0
    for d in x['cur']['days'] + x['prev']['days']:
        s = sum((ri or {}).get('orders', 0) or 0 for ri in (d.get('rooms') or {}).values())
        diff += abs((d.get('total_orders', 0) or 0) - s)
    x['consistency'] = diff

    wb = Workbook()
    wb.remove(wb.active)
    anchors = {}
    anchors['overview'] = sheet_overview(wb, x)
    x['anchors'] = anchors['overview']
    sheet_our(wb, x)
    sheet_rival(wb, x)
    sheet_all_rooms(wb, x)
    _, anchors['products'] = sheet_products(wb, x)
    _, anchors['daily'] = sheet_daily(wb, x)
    sheet_findings(wb, x)
    sheet_charts(wb, x, anchors)
    sheet_notes(wb, x)
    wb.active = 0

    out = a.out or os.path.join(DESKTOP, '%s周报_直播间销量对比分析.xlsx' % x['label_cur'])
    wb.save(out)

    ct, pt = x['cur']['total'], x['prev']['total']
    print('输出：%s' % out)
    print('区间：%s ~ %s（%d天）｜对比 %s ~ %s' % (start, end, x['n_days'], x['prev_start'], x['prev_end']))
    print('全站：%s 单 / ¥%s（环比 %s）' % (num(ct['orders']), num(ct['revenue']),
                                        signed_pct(wow(ct['revenue'], pt['revenue']) or 0)))
    print('我司：%s 单 / ¥%s｜占比 %s' % (num(x['our']['orders']), num(x['our']['revenue']),
                                       pct(x['our']['revenue'] / ct['revenue'] if ct['revenue'] else 0)))
    print('良米：%s 单 / ¥%s｜占比 %s' % (num(x['liang']['orders']), num(x['liang']['revenue']),
                                       pct(x['liang']['revenue'] / ct['revenue'] if ct['revenue'] else 0)))
    print('一致性：total_orders 与各间订单之和差异 = %d 单' % diff)
    print('Top5 商品：' + '、'.join('%s(¥%s)' % (p, num(v['revenue'])) for p, v in
                                  sorted(x['cur']['products'].items(), key=lambda kv: -kv[1]['revenue'])[:5]))

    if a.check_json:
        expect = {
            'file': out, 'start': start, 'end': end, 'prev_start': x['prev_start'], 'prev_end': x['prev_end'],
            'site_orders': ct['orders'], 'site_revenue': ct['revenue'],
            'prev_site_orders': pt['orders'], 'prev_site_revenue': pt['revenue'],
            'our_orders': x['our']['orders'], 'our_revenue': x['our']['revenue'],
            'liang_orders': x['liang']['orders'], 'liang_revenue': x['liang']['revenue'],
            'our_share': x['our']['revenue'] / ct['revenue'] if ct['revenue'] else None,
            'other_revenue': x['other_rev'], 'consistency': diff,
            'sheets': wb.sheetnames,
        }
        with open(a.check_json, 'w', encoding='utf-8') as fh:
            json.dump(expect, fh, ensure_ascii=False, indent=2)
        print('自检 JSON：%s' % a.check_json)
    return out


if __name__ == '__main__':
    main()

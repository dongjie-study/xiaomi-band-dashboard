# -*- coding: utf-8 -*-
"""流量分析 · 每日数据入库 + 环比 + 平台规则匹配 + 日报生成。

链路（与 sales_analysis/daily_update.py 同构，但完全独立，互不污染）：

    x.xx日流量.xlsx / 流量数据.xlsx
        └─▶ traffic_analysis/daily_update.py
                ├─▶ traffic_analysis/data/YYYY/YYYY-MM-DD.json   ⭐ 主库（一天一个文件）
                ├─▶ traffic_analysis/data/index.json             （日期索引，页面用它出月份/日期下拉）
                └─▶ traffic_analysis/reports/YYYY-MM-DD.json     ⭐ 日报 + 指标卡（页面直接渲染）

用法：
    python traffic_analysis/daily_update.py "C:\\Users\\Administrator\\Desktop\\10.11日流量.xlsx"
    python traffic_analysis/daily_update.py <xlsx> --date 2026-10-11 --room 小米官方手环直播间
    python traffic_analysis/daily_update.py --rebuild          # 只重建 index.json + 全部日报
    python traffic_analysis/daily_update.py --check            # 体检，不写文件

约定：
  * 数据起始 **10 月份**，早于 10 月的文件直接拒绝（见 RULES 里的 START_YM）。
  * 列名**看含义不看字面**（关键词匹配），不要求固定表头文字。
  * 同一天重复入库 = upsert（覆盖当天，不追加）。
"""
import argparse
import glob
import json
import os
import re
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAFFIC_DIR = os.path.join(ROOT, 'traffic_analysis')
DATA_DIR = os.path.join(TRAFFIC_DIR, 'data')
REPORT_DIR = os.path.join(TRAFFIC_DIR, 'reports')

# 流量分析数据起始月份（规则：不得早于 10 月）
START_YM = '2026-10'

# ============================================================ 列名口径
# (内部字段, 中文名, 单位, 关键词候选) —— 按 order 优先级做「关键词匹配」
COLS = [
    ('impressions',      '直播间曝光次数', '次', ['直播间曝光次数', '直播曝光次数', '曝光次数', '曝光量', '曝光']),
    ('views',            '直播间观看次数', '次', ['直播间观看次数', '直播间观看人次', '观看次数', '观看人次', '观看人数', '观看']),
    ('interactions',     '直播间互动次数', '次', ['直播间互动次数', '互动次数', '互动量', '互动']),
    ('new_followers',    '新增粉丝数',    '人', ['新增粉丝数', '新增粉丝', '涨粉数', '涨粉', '新增关注']),
    ('product_impressions', '商品曝光次数', '次', ['商品曝光次数', '商品曝光', '商品展现次数', '商品展现']),
    ('product_clicks',   '商品点击次数', '次', ['商品点击次数', '商品点击', '点击次数', '点击量']),
    ('paid_orders',      '成交订单数',    '单', ['成交订单数', '成交订单量', '成交订单', '订单数', '支付订单数', '成交件数']),
    ('paid_amount',      '用户支付金额', '元', ['用户支付金额', '支付金额', '成交金额', '支付gmv', 'gmv', '销售额']),
]
CHANNEL_KEYS = ['渠道名称', '流量渠道', '渠道', '来源渠道', '流量来源', '来源', '渠道名']
IGNORE_ROW_NAMES = {'同行同级优秀值', '同行同层优秀值', '行业均值', '合计', '总计', '汇总'}

# 单位换算：单元格里可能写「1.2万」「3,456」「12.5%」
UNIT_FACTOR = {'万': 10000.0, 'w': 10000.0, 'W': 10000.0, 'k': 1000.0, 'K': 1000.0, '千': 1000.0}

# ============================================================ 平台规则阈值
# 抖音直播电商 带货口碑/流量分发 常用观测区间（行业经验值，可按实际调）
PLATFORM_RULES = [
    # (指标key, 名称, 下限, 上限, 单位, 平台含义)  —— 比率类阈值单位是「百分数」，如 8 = 8%
    ('exposure_view_rate', '曝光→观看率', 8.0, 30.0, '%',
     '直播间曝光后愿意进来的人占比。低于 8% 说明封面/标题/贴片没吸引力，平台会判定「推荐了没人看」而收量。'),
    ('interaction_rate', '观看→互动率', 3.0, 15.0, '%',
     '进来的人愿不愿意说话（评论/点赞/加团/停留）。低于 3% 会被判定为低质直播间，进入「推荐—无互动—减少推荐」负循环。'),
    ('product_ctr', '商品点击率', 5.0, 30.0, '%',
     '商品卡曝光后被点开的比例。低于 5% 通常是排品顺序/讲解节奏问题：主推品没在前 30 分钟曝光。'),
    ('click_cvr', '点击→成交转化率', 5.0, 40.0, '%',
     '点开商品的人最终下单的比例。低于 5% 要看价格力、库存、运费险、支付引导。'),
    ('new_follower_rate', '涨粉率', 0.5, 10.0, '%',
     '观看人数转化成粉丝的比例。涨粉是平台判断直播间「值得持续分发」的重要正反馈，低于 0.5% 说明没有引导关注动作。'),
    ('gpm', 'GPM（千次观看成交额）', 200.0, None, '元',
     '每 1000 次观看带来的支付金额。这是平台最核心的分发指标——GPM 高就继续给量，GPM 掉就收量。'),
]

# 异常渠道：这些渠道的「互动次数 > 观看次数」，计数口径不一致，不参与互动率合算
ANOMALY_CHANNELS = {'个人主页&店铺&橱窗', '个人主页&店铺&橱窗 ', '活动页'}


# ============================================================ 工具
def num(v):
    """把单元格值转成 float：支持 '1.2万' / '3,456' / '12.5%' / None / '—'。"""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(',', '').replace('，', '')
    if s in ('', '-', '—', '--', '/', 'N/A', 'n/a', 'null', 'None'):
        return 0.0
    m = re.match(r'^(-?[\d.]+)\s*([万wWkK千]?)\s*%?$', s)
    if not m:
        m2 = re.search(r'(-?\d[\d.]*)', s)
        if not m2:
            return 0.0
        return float(m2.group(1))
    val = float(m.group(1))
    return val * UNIT_FACTOR.get(m.group(2), 1.0)


def norm(s):
    return re.sub(r'[\s\u3000()（）\-_/]', '', str(s or '')).lower()


def div(a, b):
    return (a / b) if b else None


def pct(v, nd=2):
    return None if v is None else round(v * 100, nd)


def signed(v, nd=1):
    if v is None:
        return '—'
    return ('+' if v >= 0 else '') + ('%.' + str(nd) + 'f') + '%%' % (v * 100)


def fmt_int(v):
    return '—' if v is None else f'{v:,.0f}'


def fmt_num(v, nd=2):
    return '—' if v is None else f'{v:,.{nd}f}'


# ============================================================ 解析 xlsx
def find_header(rows):
    """在前 15 行里找表头行：命中「渠道」列 + 至少 3 个指标列。返回 (行号, {字段: 列号}, 渠道列号)。"""
    best = None
    for i, row in enumerate(rows[:15]):
        cells = [norm(c) for c in row]
        ch_idx = None
        for k in CHANNEL_KEYS:
            nk = norm(k)
            for j, c in enumerate(cells):
                if c and (c == nk or nk in c):
                    ch_idx = j
                    break
            if ch_idx is not None:
                break
        if ch_idx is None:
            continue
        idx = {}
        for field, _label, _unit, kws in COLS:
            for kw in kws:
                nkw = norm(kw)
                hit = None
                for j, c in enumerate(cells):
                    if c and c == nkw:
                        hit = j
                        break
                if hit is None:
                    for j, c in enumerate(cells):
                        if c and nkw in c:
                            hit = j
                            break
                if hit is not None:
                    idx[field] = hit
                    break
        if len(idx) >= 3 and (best is None or len(idx) > len(best[1])):
            best = (i, idx, ch_idx)
    return best


def parse_date_from_name(path):
    """从文件名抽日期：支持 10.11 / 10-11 / 2026-10-11 / 1011 等写法。"""
    base = os.path.splitext(os.path.basename(path))[0]
    m = re.search(r'(20\d{2})[-._年]?(\d{1,2})[-._月]?(\d{1,2})', base)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(y, mo, d).isoformat()
    # 10.11 / 10-11 / 10月11日
    m = re.search(r'(?<!\d)(\d{1,2})\s*[.\-月/]\s*(\d{1,2})\s*日?(?!\d)', base)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        return date(2026, mo, d).isoformat()
    # 1011（4 位，仅当整串像日期时）
    m = re.search(r'(?<!\d)(1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)', base)
    if m:
        return date(2026, int(m.group(1)), int(m.group(2))).isoformat()
    return None


def parse_workbook(path, sheet=None):
    """解析工作簿 → (表头信息, 渠道明细 dict)。多 sheet 时自动挑「有渠道列且行数最多」的那个。"""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    names = [sheet] if sheet else list(wb.sheetnames)
    best = None
    for sn in names:
        ws = wb[sn]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        rows = [r for r in rows if any(c is not None and str(c).strip() != '' for c in r)]
        if not rows:
            continue
        hdr = find_header(rows)
        if not hdr:
            continue
        hi, idx, ch = hdr
        chan = {}
        for r in rows[hi + 1:]:
            if len(r) <= ch:
                continue
            name = str(r[ch]).strip() if r[ch] is not None else ''
            if not name or name in IGNORE_ROW_NAMES or norm(name) in {norm(x) for x in IGNORE_ROW_NAMES}:
                continue
            rec = {}
            for field, _l, _u, _k in COLS:
                rec[field] = num(r[idx[field]]) if (idx.get(field) is not None and len(r) > idx[field]) else 0.0
            chan[name] = rec
        if chan and (best is None or len(chan) > len(best[1])):
            best = (sn, chan, sorted(idx.keys()))
    wb.close()
    return best


# ============================================================ 指标计算
def compute_metrics(tot, ok_tot=None):
    """由合计字段算派生指标。ok_tot 用于互动率（剔除口径异常的渠道）。"""
    o = ok_tot or tot
    m = {
        'exposure_view_rate': div(tot['views'], tot['impressions']),
        'view_interaction_rate': div(tot['interactions'], tot['views']),
        'interaction_rate': div(o['interactions'], o['views']),
        'product_ctr': div(tot['product_clicks'], tot['product_impressions']),
        'click_cvr': div(tot['paid_orders'], tot['product_clicks']),
        'order_per_1000_view': div(tot['paid_orders'] * 1000.0, tot['views']),
        'new_follower_rate': div(tot['new_followers'], tot['views']),
        'gpm': div(tot['paid_amount'] * 1000.0, tot['views']),
        'uv_value': div(tot['paid_amount'], tot['views']),
        'aov': div(tot['paid_amount'], tot['paid_orders']),
        'funnel': [
            {'key': 'impressions', 'label': '直播间曝光', 'value': tot['impressions']},
            {'key': 'views', 'label': '直播间观看', 'value': tot['views']},
            {'key': 'product_impressions', 'label': '商品曝光', 'value': tot['product_impressions']},
            {'key': 'product_clicks', 'label': '商品点击', 'value': tot['product_clicks']},
            {'key': 'paid_orders', 'label': '成交订单', 'value': tot['paid_orders']},
        ],
    }
    return m


def evaluate_rules(m, tot):
    """平台规则匹配：逐条判 优/正常/偏低/偏高。比率类统一换算成百分数展示。"""
    out = []
    for key, label, lo, hi, unit, why in PLATFORM_RULES:
        v = m.get(key)
        pv = v * 100 if (v is not None and unit == '%') else v
        if pv is None:
            status = 'unknown'
        elif lo is not None and pv < lo:
            status = 'low'
        elif hi is not None and pv > hi:
            status = 'high'
        else:
            status = 'ok'
        if pv is None:
            disp = '—'
        elif unit == '%':
            disp = f'{pv:.2f}%'
        else:
            disp = f'{pv:,.0f} 元'
        rng = (f'≥ {lo:g}' if hi is None else f'{lo:g} ~ {hi:g}') + ('%' if unit == '%' else ' 元')
        out.append({
            'key': key, 'label': label, 'status': status, 'unit': unit,
            'value': pv, 'value_disp': disp, 'range': rng, 'why': why,
        })
    return out


def day_over_day(cur, prev, prev_date):
    """逐指标环比：绝对值 + 前一日 + 环比%。cur/prev 为入库 payload（含 totals/metrics）。"""
    ct = (cur or {}).get('totals') or {}
    pt = (prev or {}).get('totals') or {}
    cm = (cur or {}).get('metrics') or {}
    pm = (prev or {}).get('metrics') or {}
    rows = []
    for field, label, unit, _k in COLS:
        c = ct.get(field)
        p = pt.get(field) if pt else None
        chg = (c / p - 1) if (p not in (None, 0) and c is not None) else None
        rows.append({'key': field, 'label': label, 'unit': unit, 'cur': c, 'prev': p,
                     'chg': chg, 'is_rate': False,
                     'dir': ('up' if (chg or 0) > 0 else ('down' if (chg or 0) < 0 else 'flat')) if chg is not None else 'na'})
    for key, label, unit, nd in [
        ('exposure_view_rate', '曝光→观看率', '%', 2), ('interaction_rate', '观看→互动率', '%', 2),
        ('product_ctr', '商品点击率', '%', 2), ('click_cvr', '点击→成交转化率', '%', 2),
        ('new_follower_rate', '涨粉率', '%', 2), ('gpm', 'GPM', '元', 0),
        ('uv_value', 'UV 价值', '元', 2), ('aov', '客单价', '元', 2),
    ]:
        c = cm.get(key)
        p = pm.get(key) if pm else None
        cd = round(c * 100, nd) if c is not None else None
        pd_ = round(p * 100, nd) if p is not None else None
        diff = round(cd - pd_, nd) if (cd is not None and pd_ is not None) else None
        rows.append({'key': key, 'label': label, 'unit': unit, 'cur': cd, 'prev': pd_,
                     'chg': (diff / abs(pd_) if (diff is not None and pd_) else None),
                     'pp_diff': diff, 'is_rate': True,
                     'dir': ('up' if (diff or 0) > 0 else ('down' if (diff or 0) < 0 else 'flat')) if diff is not None else 'na'})
    return rows


def channel_rows(cur, prev):
    """渠道明细 + 环比。"""
    cur_ch = (cur or {}).get('channels') or {}
    prev_ch = (prev or {}).get('channels') or {}
    rows = []
    for name, rec in sorted(cur_ch.items(), key=lambda kv: -(kv[1].get('views') or 0)):
        p = prev_ch.get(name) or {}
        v = rec.get('views')
        pi = rec.get('product_impressions')
        pc = rec.get('product_clicks')
        rows.append({
            'name': name,
            'impressions': rec.get('impressions'), 'views': v,
            'interactions': rec.get('interactions'), 'new_followers': rec.get('new_followers'),
            'product_impressions': pi, 'product_clicks': pc,
            'paid_orders': rec.get('paid_orders'), 'paid_amount': rec.get('paid_amount'),
            'evr': pct(div(v, rec.get('impressions'))),
            'ctr': pct(div(pc, pi)),
            'cvr': pct(div(rec.get('paid_orders'), pc)),
            'gpm': round(div((rec.get('paid_amount') or 0) * 1000.0, v)) if v else None,
            'share': None,
            'prev_views': p.get('views'),
            'chg': (v / p['views'] - 1) if (p.get('views') and v is not None) else None,
            'anomaly': name in ANOMALY_CHANNELS,
        })
    tv = sum((x['views'] or 0) for x in rows)
    for x in rows:
        x['share'] = pct(div(x['views'], tv))
    return rows


def build_insights(cur, prev, dod, rules, channels):
    """生成「数据表现 / 平台规则匹配 / 优化建议」三段文字。"""
    t = cur['totals']
    m = cur['metrics']
    lines = {'headline': [], 'data': [], 'rules': [], 'actions': []}

    # —— 数据表现
    if prev:
        dv = dod and [r for r in dod if r['key'] == 'views'][0]
        lines['headline'].append(
            f"观看 {fmt_int(t['views'])} 次（前一日 {fmt_int(dv['prev'])}，{('+' if (dv['chg'] or 0)>=0 else '')}{fmt_num((dv['chg'] or 0)*100,1)}%）"
        )
        for key in ('impressions', 'product_clicks', 'paid_orders', 'paid_amount'):
            r = [x for x in dod if x['key'] == key][0]
            arrow = '↑' if r['dir'] == 'up' else ('↓' if r['dir'] == 'down' else '→')
            lines['data'].append(
                f"{r['label']} {fmt_int(r['cur'])} {r['unit']}，前一日 {fmt_int(r['prev'])}，{arrow} {abs((r['chg'] or 0)*100):.1f}%"
            )
        for key, label in (('exposure_view_rate', '曝光→观看率'), ('interaction_rate', '观看→互动率'),
                           ('product_ctr', '商品点击率'), ('click_cvr', '点击→成交转化率')):
            r = [x for x in dod if x['key'] == key][0]
            if r['cur'] is None or r['prev'] is None:
                continue
            lines['data'].append(
                f"{label} {r['cur']:.2f}%（前一日 {r['prev']:.2f}%，{(r['pp_diff'] or 0):+.2f}pp）"
            )
    else:
        lines['headline'].append(f"观看 {fmt_int(t['views'])} 次（首日入库，无前一日可比）")
        lines['data'].append('⚠️ 没有前一日数据，环比一栏留空；第二天起自动出环比。')

    # 最大涨/跌渠道
    chg_ok = [c for c in channels if c['chg'] is not None and (c['prev_views'] or 0) >= 50]
    if chg_ok:
        up = max(chg_ok, key=lambda c: c['chg'])
        dn = min(chg_ok, key=lambda c: c['chg'])
        lines['data'].append(f"渠道里 {up['name']} 涨得最猛（观看 {up['chg']*100:+.1f}%）；{dn['name']} 掉得最多（{dn['chg']*100:+.1f}%）")

    # —— 平台规则匹配
    bad = [r for r in rules if r['status'] in ('low', 'high')]
    good = [r for r in rules if r['status'] == 'ok']
    if good:
        lines['rules'].append('✅ 达标：' + '、'.join(f"{r['label']} {r['value_disp']}（平台参考 {r['range']}）" for r in good))
    for r in bad:
        direction = '低于' if r['status'] == 'low' else '高于'
        lines['rules'].append(f"⚠️ {r['label']} {r['value_disp']}，{direction}平台参考区间 {r['range']}。{r['why']}")
    if not bad:
        lines['rules'].append('✅ 全部核心指标落在平台推荐区间内，当前分发逻辑健康，重点是保住这套节奏。')

    # —— 优化建议（按规则命中的短板给动作）
    def has(k, st='low'):
        return any(r['key'] == k and r['status'] == st for r in rules)
    if has('gpm') or has('click_cvr'):
        lines['actions'].append('**转化端**：GPM/转化率是平台给量的第一指标。把主推品提到开场前 30 分钟，配合「限时直降 + 库存倒计时」逼单；检查到手价与竞对同款价差，价格力不足时优先用赠品而非降标价。')
    if has('product_ctr'):
        lines['actions'].append('**商品卡**：点击率偏低说明福袋/主图/讲解节奏没把商品推到观众面前。每 10 分钟口播一次主推品并置顶商品卡，商品标题前 8 个字放「型号 + 核心卖点 + 价格」。')
    if has('interaction_rate'):
        lines['actions'].append('**互动**：开播 5 分钟做「扣1抽奖」，每 15 分钟一次福袋；把「点关注亮灯牌」写进话术循环，互动率是平台判断是否继续推流的直接信号。')
    if has('exposure_view_rate'):
        lines['actions'].append('**封面/标题**：曝光进不来人是推荐位素材问题。今日换 2 组封面（产品特写 + 价格钩子），标题带「今晚 8 点直降」，隔天对比曝光→观看率。')
    if has('new_follower_rate'):
        lines['actions'].append('**涨粉**：涨粉率低 = 缺关注引导。每场安排 3 次「关注的家人扣关注，抽手环」，把加粉丝团作为抽奖门槛。')
    if not lines['actions']:
        lines['actions'].append('**守成**：数据在全绿区间，重点不是加动作而是「复制今天」——把本场排品顺序、开播时间、话术节奏固化成模板，明天照跑。')

    # —— 异常与波动
    if prev:
        dv = t['views'] / prev['totals']['views'] - 1 if prev['totals'].get('views') else None
        if dv is not None and abs(dv) >= 0.30:
            lines['data'].append(('⚠️ ' if dv < 0 else '🚀 ') + f"观看量单日{'下滑' if dv<0 else '暴涨'} {abs(dv)*100:.0f}%，{'若为下滑需排查是否被限流/断播' if dv<0 else '注意承接能力是否跟得上'}")
    neg = [x for x in cur.get('channels', {}) if x in ANOMALY_CHANNELS]
    if neg:
        lines['data'].append('ℹ️ 渠道「' + '、'.join(neg) + '」口径异常（互动次数 > 观看次数），已从互动率合算中剔除。')

    # —— 判断是否「可能被限流/断播」（观看下滑 + 曝光下滑，但进人率没降 = 不是素材问题）
    if prev:
        prev_t = prev['totals']
        v_chg = (t.get('views') or 0) / prev_t['views'] - 1 if prev_t.get('views') else 0
        i_chg = (t.get('impressions') or 0) / prev_t['impressions'] - 1 if prev_t.get('impressions') else 0
        evr_c = m.get('exposure_view_rate'); evr_p = (prev.get('metrics') or {}).get('exposure_view_rate')
        if v_chg < -0.15 and i_chg < -0.15 and evr_c is not None and evr_p and evr_c >= evr_p:
            lines['rules'].append('🔎 判断：曝光和观看同比例下滑、但「曝光→观看率」没降 → 不是封面/素材问题，更像是**平台减少推流**（时段竞争加剧、历史 GPM 拖累、或场次时长不足）。优先核对是否断播、是否被限流提示。')

    return lines


# ============================================================ 落盘
def day_path(d):
    return os.path.join(DATA_DIR, d[:4], d + '.json')


def load_day(d):
    p = day_path(d)
    if not os.path.exists(p):
        return None
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def all_dates():
    out = []
    for p in glob.glob(os.path.join(DATA_DIR, '*', '*.json')):
        b = os.path.splitext(os.path.basename(p))[0]
        if re.match(r'^\d{4}-\d{2}-\d{2}$', b):
            out.append(b)
    return sorted(out)


def write_day(d, payload):
    p = day_path(d)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return p


def write_index():
    dates = all_dates()
    days = []
    for d in dates:
        rec = load_day(d) or {}
        days.append({
            'date': d, 'room': rec.get('room'),
            'views': (rec.get('totals') or {}).get('views'),
            'impressions': (rec.get('totals') or {}).get('impressions'),
            'paid_orders': (rec.get('totals') or {}).get('paid_orders'),
            'paid_amount': (rec.get('totals') or {}).get('paid_amount'),
        })
    months = {}
    for x in days:
        months.setdefault(x['date'][:7], []).append(x['date'])
    idx = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'start_month': START_YM,
        'months': [{'ym': k, 'label': f'{int(k[5:7])}月', 'count': len(v),
                    'dates': sorted(v, reverse=True)} for k, v in sorted(months.items())],
        'days': days,
    }
    p = os.path.join(DATA_DIR, 'index.json')
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    return p, idx


def write_report(d, payload, prev):
    dod = day_over_day(payload, prev, prev['date'] if prev else None)
    rules = evaluate_rules(payload['metrics'], payload['totals'])
    channels = channel_rows(payload, prev)
    ins = build_insights(payload, prev, dod, rules, channels)
    rpt = {
        'date': d, 'room': payload.get('room'), 'source_file': payload.get('source_file'),
        'prev_date': prev['date'] if prev else None,
        'totals': payload['totals'], 'metrics': payload['metrics'],
        'dod': dod, 'rules': rules, 'channels': channels, 'insights': ins,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(os.path.join(REPORT_DIR, d + '.json'), 'w', encoding='utf-8') as f:
        json.dump(rpt, f, ensure_ascii=False, indent=1)
    return rpt


def rebuild_reports():
    dates = all_dates()
    prev = None
    for d in dates:
        cur = load_day(d)
        if not cur:
            continue
        write_report(d, cur, prev)
        prev = cur
    p, idx = write_index()
    return dates, p, idx


# ============================================================ 主流程
def ingest(xlsx, d=None, room=None, sheet=None):
    if not os.path.exists(xlsx):
        raise SystemExit(f'❌ 找不到文件：{xlsx}')
    d = d or parse_date_from_name(xlsx)
    if not d:
        raise SystemExit('❌ 无法从文件名判断日期，请用 --date YYYY-MM-DD 指定')
    if d[:7] < START_YM:
        raise SystemExit(f'❌ {d} 早于流量分析起始月份 {START_YM}（规则：数据不得早于 10 月）')

    parsed = parse_workbook(xlsx, sheet=sheet)
    if not parsed:
        raise SystemExit('❌ 没找到「渠道名称 + 指标」表头。请确认导出的是直播流量渠道明细表')
    sn, chan, fields = parsed

    tot = {f: 0.0 for f, _l, _u, _k in COLS}
    for rec in chan.values():
        for k, v in rec.items():
            tot[k] += v
    ok = {k: v for k, v in chan.items() if k not in ANOMALY_CHANNELS}
    ok_tot = {f: sum(c.get(f, 0.0) for c in ok.values()) for f, _l, _u, _k in COLS}

    payload = {
        'date': d, 'room': room or '全店（全渠道汇总）', 'source_file': os.path.basename(xlsx),
        'source_sheet': sn, 'matched_fields': fields,
        'channels': {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in chan.items()},
        'totals': {k: round(v, 4) for k, v in tot.items()},
        'ok_totals': {k: round(v, 4) for k, v in ok_tot.items()},
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    payload['metrics'] = compute_metrics(payload['totals'], payload['ok_totals'])
    payload['metrics'] = {k: (round(v, 6) if isinstance(v, float) else v) for k, v in payload['metrics'].items()}

    existed = os.path.exists(day_path(d))
    p = write_day(d, payload)
    dates, ip, idx = rebuild_reports()
    return {'date': d, 'path': p, 'channels': len(chan), 'totals': payload['totals'],
            'metrics': payload['metrics'], 'overwrote': existed, 'n_days': len(dates), 'index': ip}


def check():
    dates = all_dates()
    print(f'流量入库天数：{len(dates)}')
    if dates:
        print(f'  最早 {dates[0]}   最新 {dates[-1]}')
    bad = []
    for d in dates:
        rec = load_day(d)
        t = (rec or {}).get('totals') or {}
        if not t.get('impressions') and not t.get('views'):
            bad.append(d + ' 曝光/观看全为 0')
        if not os.path.exists(os.path.join(REPORT_DIR, d + '.json')):
            bad.append(d + ' 缺日报')
    if bad:
        print('⚠️ 问题：')
        for b in bad:
            print('  -', b)
        return 1
    print('✔ 体检通过')
    return 0


def main():
    ap = argparse.ArgumentParser(description='流量分析每日入库 + 环比 + 平台规则匹配 + 日报')
    ap.add_argument('xlsx', nargs='?', help='流量 xlsx 路径')
    ap.add_argument('--date', help='覆盖日期 YYYY-MM-DD')
    ap.add_argument('--room', help='直播间名（默认「全店（全渠道汇总）」）')
    ap.add_argument('--sheet', help='指定 sheet 名')
    ap.add_argument('--rebuild', action='store_true', help='只重建 index.json + 全部日报')
    ap.add_argument('--check', action='store_true', help='体检，不写文件')
    a = ap.parse_args()

    if a.check:
        return check()
    if a.rebuild or not a.xlsx:
        dates, ip, idx = rebuild_reports()
        print(f'✔ 重建完成：{len(dates)} 天，索引 {os.path.relpath(ip, ROOT)}')
        for mm in idx['months']:
            print(f"   {mm['ym']}  {mm['count']} 天")
        return 0

    r = ingest(a.xlsx, a.date, a.room, a.sheet)
    t, m = r['totals'], r['metrics']
    print(('⚠️ 同日已有数据，已覆盖：' if r['overwrote'] else '✔ 入库：') + f"{r['date']}  {os.path.relpath(r['path'], ROOT)}")
    print(f"   源文件   {os.path.basename(a.xlsx)}  渠道 {r['channels']} 个")
    print(f"   曝光 {fmt_int(t['impressions'])}  观看 {fmt_int(t['views'])}  互动 {fmt_int(t['interactions'])}  涨粉 {fmt_int(t['new_followers'])}")
    print(f"   商品曝光 {fmt_int(t['product_impressions'])}  商品点击 {fmt_int(t['product_clicks'])}  成交 {fmt_int(t['paid_orders'])} 单  支付 {fmt_num(t['paid_amount'])} 元")
    print(f"   曝光→观看 {fmt_num(pct(m['exposure_view_rate']))}%  互动率 {fmt_num(pct(m['interaction_rate']))}%  "
          f"商品点击率 {fmt_num(pct(m['product_ctr']))}%  点击→成交 {fmt_num(pct(m['click_cvr']))}%  GPM {fmt_num(m['gpm'],0)} 元")
    print(f"   累计 {r['n_days']} 天，索引已刷新")
    return 0


if __name__ == '__main__':
    sys.exit(main())

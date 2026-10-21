# -*- coding: utf-8 -*-
"""流量分析 · 每日数据入库 + 环比 + 平台规则匹配 + 日报生成。

链路（与 sales_analysis/daily_update.py 同构，但完全独立，互不污染）：

    流量表（每直播间一份）.xlsx
        └─▶ traffic_analysis/daily_update.py
                ├─▶ traffic_analysis/data/YYYY/YYYY-MM-DD.json          ⭐ 主库（一天一个文件，含各直播间）
                ├─▶ traffic_analysis/data/index.json                    （月份/日期/直播间索引，页面下拉用它）
                └─▶ traffic_analysis/reports/YYYY/YYYY-MM-DD/*.json     ⭐ 日报（all.json + 每间一份）

用法：
    python traffic_analysis/daily_update.py "C:/Users/Administrator/Desktop/10.10日流量"   # 整个文件夹
    python traffic_analysis/daily_update.py a.xlsx b.xlsx --date 2026-10-10
    python traffic_analysis/daily_update.py --rebuild          # 只重建 index.json + 全部日报
    python traffic_analysis/daily_update.py --check            # 体检，不写文件

约定：
  * 数据起始 **10 月份**，早于 10 月的文件直接拒绝（START_YM）。
  * 列名**看含义不看字面**（关键词匹配），不要求固定表头文字。
  * 表里「较上周期」「同行同级优秀值」两行直接忽略；「整体」行是该直播间合计（真值）。
  * 一天多个文件 = 多个直播间，合并进同一天的日文件；同一直播间重复入库 = 覆盖。
  * 真实数据不会被示例数据覆盖（除非 --force）。
"""
import argparse
import difflib
import glob
import json
import os
import re
import shutil
import statistics
import sys
import zipfile
from datetime import date, datetime
from xml.etree import ElementTree as ET

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAFFIC_DIR = os.path.join(ROOT, 'traffic_analysis')
DATA_DIR = os.path.join(TRAFFIC_DIR, 'data')
REPORT_DIR = os.path.join(TRAFFIC_DIR, 'reports')

# 流量分析数据起始月份（规则：不得早于 10 月）
START_YM = '2026-10'

# 「全店」= 6 个直播间简单相加（各间观看人数会重复计算，非去重 UV，仅用于看总盘子）
ALL_SCOPE = '全店'
ALL_SCOPE_FULL = '全店（各直播间合计）'

# ============================================================ 列名口径
# (内部字段, 中文名, 单位, 关键词候选) —— 按含义匹配，不要求表头字面一致
COLS = [
    ('impressions',      '直播间曝光次数', '次', ['直播间曝光次数', '直播曝光次数', '曝光次数', '曝光量', '曝光']),
    ('views',            '直播间观看次数', '次', ['直播间观看次数', '直播间观看人次', '观看次数', '观看人次', '观看人数', '观看']),
    ('interactions',     '直播间互动次数', '次', ['直播间互动次数', '互动次数', '互动量', '互动']),
    ('new_followers',    '新增粉丝数',    '人', ['新增粉丝数', '新增粉丝', '涨粉数', '涨粉', '新增关注']),
    ('product_impressions', '商品曝光次数', '次', ['商品曝光次数', '商品曝光', '商品展现次数', '商品展现']),
    ('product_clicks',   '商品点击次数',  '次', ['商品点击次数', '商品点击', '点击次数', '点击量']),
    ('paid_orders',      '成交订单数',    '单', ['成交订单数', '成交订单量', '成交订单', '订单数', '支付订单数']),
    ('paid_amount',      '用户支付金额', '元', ['用户支付金额', '支付金额', '成交金额', '支付gmv', 'gmv', '销售额']),
]
# 补充字段（只有「整体」行有值，渠道行为空）
EXTRA_COLS = [
    ('live_duration',  '直播时长',   '',  ['直播时长']),
    ('avg_watch_time', '人均观看时长', '', ['人均观看时长']),
    ('qianchuan',      '千川消耗',  '元', ['千川消耗', '千川花费', '投放消耗']),
]
# 表里必须跳过的行（用户明确要求忽略前两个）
SKIP_ROW_NAMES = ['较上周期', '环比上周期', '同行同级优秀值', '同行同层优秀值', '行业均值', '行业优秀值']
TOTAL_ROW_NAMES = ['整体', '全部', '合计', '总计', '汇总', '全店']
CHANNEL_KEYS = ['渠道名称', '流量渠道', '渠道', '来源渠道', '流量来源', '来源', '渠道名']

# 单位换算：单元格里可能写「1.2万」「3,456」「12.5%」
UNIT_FACTOR = {'万': 10000.0, 'w': 10000.0, 'W': 10000.0, 'k': 1000.0, 'K': 1000.0, '千': 1000.0}

# ============================================================ 平台规则阈值
# 依据 2026-10-10 六个直播间的真实分布 + 抖音/快手/淘宝直播公开的流量分发逻辑校准：
#   EVR 4.5~9.1%   互动率 9.4~27.6%   商品点击率 3.0~12.0%   点击→成交 0.9~8.5%
#   涨粉率 0.28~0.78%   GPM 2019~5938 元   千川 ROI 14.0~46.5
# 比率类阈值单位是「百分数」（如 3.5 = 3.5%）。
PLATFORM_RULES = [
    # (key, 名称, 下限, 上限, 单位, 平台含义)
    ('exposure_view_rate', '曝光→观看率', 3.5, None, '%',
     '直播间曝光后愿意点进来的人占比。低于 3.5% 说明封面/标题/贴片没吸引力，平台判定「推了没人看」直接收量。'),
    ('interaction_rate', '观看→互动率', 5.0, None, '%',
     '进来的人愿不愿意说话（评论/点赞/加团/停留）。低于 5% 会被判低质直播间，进入「推荐—无互动—少推荐」负循环；已剔除口径异常的渠道。'),
    ('product_ctr', '商品点击率', 4.0, 25.0, '%',
     '商品卡曝光后被点开的比例。低于 4% 通常是排品顺序/讲解节奏问题：主推品没在前 30 分钟曝光。'),
    ('click_cvr', '点击→成交转化率', 1.5, 10.0, '%',
     '点开商品的人最终下单的比例。低于 1.5% 要看价格力、库存、运费险、支付引导。'),
    ('new_follower_rate', '涨粉率', 0.2, 3.0, '%',
     '观看人数转化成粉丝的比例。涨粉是平台判断「值得持续分发」的正反馈，低于 0.2% 说明没有引导关注动作。'),
    ('gpm', 'GPM（千次观看成交额）', 2000.0, None, '元',
     '每 1000 次观看带来的支付金额，平台最核心的分发指标。本店客单价 157~694 元，品类基线取 2000 元；GPM 高就继续给量，掉就收量。'),
    ('qianchuan_roi', '千川投放 ROI', 10.0, None, '倍',
     '支付金额 ÷ 千川消耗。低于 10 倍说明付费流量买贵了，要继续放量必须先优化转化率或出价。'),
]
# 按「本店各直播间」横向对比时，用中位数做参照的指标
# 同业横向基准用的指标：key 必须与 room_compare() 产出的行字段同名（比率都是百分数）
PEER_METRICS = [
    ('gpm', 'GPM（元/千次观看）', '元', 0),
    ('aov', '客单价（元/单）', '元', 0),
    ('uv_value', 'UV 价值（元/次观看）', '元', 2),
    ('evr', '曝光→观看率', '%', 2),
    ('interaction_rate', '观看→互动率', '%', 2),
    ('ctr', '商品点击率', '%', 2),
    ('cvr', '点击→成交转化率', '%', 2),
    ('new_follower_rate', '涨粉率', '%', 2),
    ('roi', '千川投放 ROI（倍）', '倍', 2),
]

# 异常渠道自动判定：互动次数 ÷ 观看次数 ≥ 阈值，就认为这两列的统计口径不一致。
# 实测六个直播间：多数渠道落在 10%~40%，少数渠道异常放大到 64%~2372%。
# 取保守阈值 2.5 —— 只剔除「明显不可能」的（互动比观看还多数倍），不误伤 40%~80% 的正常偏差，
# 被剔除的渠道会在日报里逐条列出并写明原因，宁少剔不错剔。
ANOM_RATIO = 2.5          # 达到这个倍数 → 判定口径异常，剔除出互动率合算
ANOM_WARN_RATIO = 0.6     # 达到这个倍数（但没到 2.5）→ 只提示留意，不剔除
ANOM_MIN_VIEWS = 150      # 观看数太小的渠道比率本就不稳定，不参与异常判定
ANOM_MIN_INTER = 50       # ★ 但「观看少、互动多」恰恰是最典型的错口径（如 37 观看 / 1010 互动），
                          #   所以互动数本身够大（≥50）时照样判异常，否则把这种渠道算进互动率会得出 101% 这种数


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
    pct = s.endswith('%')
    s2 = s[:-1] if pct else s
    m = re.match(r'^(-?[\d.]+)\s*([万wWkK千]?)\s*$', s2)
    if not m:
        m2 = re.search(r'(-?\d[\d.]*)', s2)
        return float(m2.group(1)) if m2 else 0.0
    val = float(m.group(1)) * UNIT_FACTOR.get(m.group(2), 1.0)
    return val / 100.0 if pct else val


def norm(s):
    return re.sub(r'[\s\u3000()（）\-_/]', '', str(s or '')).lower()


def div(a, b):
    return (a / b) if b else None


def pct(v, nd=2):
    return None if v is None else round(v * 100, nd)


def fmt_int(v):
    return '—' if v is None else f'{v:,.0f}'


def fmt_num(v, nd=2):
    return '—' if v is None else f'{v:,.{nd}f}'


def fmt_pct(v, nd=2):
    return '—' if v is None else f'{v * 100:.{nd}f}%'


def r6(v):
    return round(v, 6) if isinstance(v, float) else v


def nz0(v):
    """把 -0.0 归一成 0.0。

    Python 里 round(-0.0043, 2) == -0.0，而 -0.0 是假值：`x or 0` 会把它换成 +0.0。
    于是同一页会出现「卡片 -0.00pp、报告 +0.00pp」这种符号相反的零（10-08 耳机直播间
    涨粉率就踩过）。差值小到显示不出来时统一按 +0.0 走。
    """
    if v is None:
        return None
    return 0.0 if v == 0 else v


# ============================================================ 解析 xlsx（不依赖 openpyxl）
class ExcelizeError(Exception):
    """这个 xlsx 读不出表格结构。"""


def _col_to_idx(ref):
    s = re.sub(r'\d', '', ref or '')
    n = 0
    for ch in s:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def parse_sheet_xml(xml_bytes):
    """把 worksheet XML 解析成 {行号: [单元格字符串, ...]}（已按列号补空、已反转义）。"""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ExcelizeError('工作表 XML 解析失败：%s' % e)
    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag[:root.tag.index('}') + 1]
    sd = root.find(ns + 'sheetData')
    if sd is None:
        return {}
    out = {}
    for ri, row in enumerate(sd.findall(ns + 'row'), start=1):
        rnum = int(row.get('r') or ri)
        cells = {}
        maxi = -1
        for c in row.findall(ns + 'c'):
            ref = c.get('r') or ''
            i = _col_to_idx(ref) if ref else (maxi + 1)
            if i < 0:
                i = 0
            t = c.get('t') or ''
            val = ''
            if t == 'inlineStr' or t == 'str':
                vn = c.find(ns + 'v')
                node = c.find(ns + 'is')
                if node is not None:
                    val = ''.join(x.text or '' for x in node.iter(ns + 't'))
                elif vn is not None and vn.text is not None:
                    val = vn.text
            else:
                vn = c.find(ns + 'v')
                if vn is not None and vn.text is not None:
                    val = vn.text
                else:
                    node = c.find(ns + 'is')
                    if node is not None:
                        val = ''.join(x.text or '' for x in node.iter(ns + 't'))
            cells[i] = val.strip()
            maxi = max(maxi, i)
        out[rnum] = [] if maxi < 0 else [cells.get(i, '') for i in range(maxi + 1)]
    return out


def sheet_names_from_zip(z):
    """列 zip 里的工作表名（按 workbook.xml 里的顺序）。"""
    try:
        xml = z.read('xl/workbook.xml').decode('utf-8', 'replace')
        return re.findall(r'<sheet[^>]*name="([^"]*)"', xml)
    except KeyError:
        return []


def parse_xlsx(path, sheet=None):
    """解析 xlsx → {sheet名: {行号: [值,...]}}。

    ★ 关键：Go Excelize 导出的表没有 sharedStrings.xml，全部是 inline t="str"。
    openpyxl 读这类文件只会看到 A1 一格（实测 16 行数据全丢），所以这里自己解 zip + XML。
    """
    try:
        z = zipfile.ZipFile(path)
    except Exception as e:
        raise ExcelizeError('不是能打开的 xlsx（%s）' % e)
    try:
        names = [n for n in z.namelist() if re.match(r'^xl/worksheets/sheet\d+\.xml$', n)]
        names.sort(key=lambda n: int(re.search(r'(\d+)', os.path.basename(n)).group(1)))
        if not names:
            raise ExcelizeError('zip 里没有工作表（xl/worksheets/sheetN.xml）')
        cn = sheet_names_from_zip(z)
        out = {}
        for i, n in enumerate(names):
            label = cn[i] if i < len(cn) else os.path.basename(n)
            out[label] = parse_sheet_xml(z.read(n))
        if sheet:
            for k in out:
                if k == sheet or norm(k) == norm(sheet):
                    return {k: out[k]}
            raise ExcelizeError('找不到 sheet「%s」，现有：%s' % (sheet, '、'.join(out.keys())))
        return out
    finally:
        z.close()


def find_header(rows):
    """在前 15 行里找表头行：命中「渠道」列 + 至少 3 个指标列。返回 (行号, {字段: 列号}, 渠道列号)。"""
    best = None
    for i in sorted(rows.keys())[:15]:
        row = rows[i]
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
        hit_how = {}
        for field, _label, _unit, kws in COLS + EXTRA_COLS:
            # ★ 两段式：先全表找「完全相等」的列名，找不到才退化成「包含」
            #   （否则「直播时长」会被「直播间曝光次数」这种长关键词的包含匹配抢走）
            hit = None
            for kw in kws:
                nkw = norm(kw)
                for j, c in enumerate(cells):
                    if c and c == nkw:
                        hit = j
                        break
                if hit is not None:
                    break
            used = 'exact'
            if hit is None:
                for kw in kws:
                    nkw = norm(kw)
                    for j, c in enumerate(cells):
                        if c and nkw in c:
                            hit = j
                            break
                    if hit is not None:
                        break
                used = 'fuzzy'
            if hit is not None:
                idx[field] = hit
                hit_how[field] = used
        if len(idx) >= 3 and (best is None or len(idx) > len(best[1])):
            best = (i, idx, ch_idx, hit_how)
    return best


def pick_sheet(book):
    """多 sheet 时挑「有渠道列且渠道行最多」的那个。"""
    best = None
    for sn, rows in book.items():
        if not rows:
            continue
        hdr = find_header(rows)
        if not hdr:
            continue
        hi, idx, ch, how = hdr
        n = sum(1 for i in sorted(rows.keys()) if i > hi and len(rows[i]) > ch and str(rows[i][ch]).strip())
        if best is None or n > best[0]:
            best = (n, sn, rows, hi, idx, ch, how)
    if not best:
        return None
    return best[1], best[2], best[3], best[4], best[5], best[6]


# ============================================================ 日期推定
def _strip_ext(name):
    """去掉扩展名。★ 不能用 os.path.splitext —— 它把「10.10日流量」当成 (10, .10日流量)，
    因为日文/中文字符不参与「扩展名」判定，第一个点就被当成分隔符，日期直接丢一半。"""
    m = re.match(r'^(.*).(xlsx|xls|csv|txt|json)$', name, flags=re.I)
    return m.group(1) if m else name


def strip_all_ext(name):
    """反复剥扩展名：「小米官方手表10.9日流量.xlsx.xlsx」要剥成「小米官方手表10.9日流量」。
    ★ 有人的导出是双后缀，只剥一层会在直播间名/日志里留一个 .xlsx 尾巴。
    """
    out = str(name or '')
    for _ in range(4):
        got = _strip_ext(out)
        if got == out:
            break
        out = got
    return out


def parse_date_from_name(path):
    """从文件名/目录名抽日期：支持 10.11 / 10-11 / 10月11日 / 2026-10-11 / 1011。"""
    base = _strip_ext(os.path.basename(path))
    m = re.search(r'(20\d{2})[-._年]?(\d{1,2})[-._月]?(\d{1,2})', base)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            pass
    # ★ 「10.10日流量」这种要能匹配：日/号后缀是可选的，且 (?!\d) 不能卡在「日」上
    #   （旧写法 [.\-月/] 的字符类里「月」没问题，但 \s*日?(?!\d) 在「日」后还要求非数字 → 10.10日 反而失配）
    m = re.search(r'(?<![\d.])(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?', base)
    if m:
        try:
            return date(2026, int(m.group(1)), int(m.group(2))).isoformat()
        except ValueError:
            pass
    m = re.search(r'(?<![\d.])(\d{1,2})[.\-/](\d{1,2})(?![\d.])', base)
    if m:
        try:
            return date(2026, int(m.group(1)), int(m.group(2))).isoformat()
        except ValueError:
            pass
    m = re.search(r'(?<![\d.])(1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)', base)
    if m:
        try:
            return date(2026, int(m.group(1)), int(m.group(2))).isoformat()
        except ValueError:
            pass
    return None


def date_from_sheet(rows_by_sheet):
    """表内找日期：扫前 6 行 × 前 8 列里的日期字面量，取最大日期。"""
    cands = []
    for _sn, rows in (rows_by_sheet or {}).items():
        for i in sorted(rows.keys())[:6]:
            for cell in (rows[i] or [])[:8]:
                s = str(cell or '').strip()
                if not s:
                    continue
                m = re.search(r'(20\d{2})\s*[-./年]\s*(\d{1,2})\s*[-./月]\s*(\d{1,2})', s)
                if m:
                    try:
                        cands.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat())
                    except ValueError:
                        pass
                    continue
                m = re.search(r'(?<!\d)(\d{1,2})\s*[.\-月/]\s*(\d{1,2})\s*[日号]?(?!\d)', s)
                if m:
                    try:
                        cands.append(date(2026, int(m.group(1)), int(m.group(2))).isoformat())
                    except ValueError:
                        pass
    return sorted(cands)[-1] if cands else None


def common_dir(paths):
    try:
        ds = [os.path.dirname(os.path.abspath(p)) for p in paths]
        return os.path.commonpath(ds) if len(set(ds)) == 1 else ds[0]
    except Exception:
        return os.path.dirname(os.path.abspath(paths[0]))


def resolve_date(paths, d=None, rows_by_sheet=None, d_src=None):
    """日期推定：--date > 所在文件夹名（如「10.10日流量」）> 文件名 > 表内单元格 > 文件修改时间。"""
    if d:
        return d, (d_src or '--date')
    if isinstance(paths, str):
        paths = [paths]
    # ★ 坑一：os.path.basename('…/10.10日流量/') 返回空串（补假文件名也没用，basename 结果永远是假名）
    # ★ 坑二：'+ os.sep' 也不行——basename 会吃掉整段目录名
    # 正确做法：拿目录名本身去解析
    got = parse_date_from_name(os.path.basename(common_dir(paths)))
    if got:
        return got, '所在文件夹'
    names = [x for x in (parse_date_from_name(p) for p in paths) if x]
    if names:
        return max(names), '文件名'
    if rows_by_sheet:
        got = date_from_sheet(rows_by_sheet)
        if got:
            return got, '表内日期'
    ms = sorted(date.fromtimestamp(os.path.getmtime(p)).isoformat() for p in paths)
    got = ms[-1]
    print('⚠️ 文件名和表内都没有日期，按文件修改时间推定 %s；如不对请用 --date YYYY-MM-DD 指定' % got)
    return got, '文件修改时间'


def group_by_date(paths):
    """按文件名里的日期分组：一次可以传多天的表（例如 Downloads 里 10.8 和 10.9 混在一起）。

    返回 (groups, rest)：groups = [(日期, [路径…]), …] 按日期升序；rest = 文件名里没日期的路径。
    """
    buckets, rest = {}, []
    for p in paths:
        got = parse_date_from_name(p)
        if got:
            buckets.setdefault(got, []).append(p)
        else:
            rest.append(p)
    return sorted(buckets.items()), rest


def is_live_duration(v):
    s = str(v or '').strip()
    if not s:
        return False
    if re.match(r'^\d{1,3}:\d{2}(:\d{2})?$', s):
        return True
    return bool(re.search(r'\d+\s*(小时|分钟|秒|天)', s))


def parse_duration_minutes(v):
    """'23小时57分钟29秒' / '1天' / '1:23:45' → 分钟数。"""
    s = str(v or '').strip()
    if not s or not is_live_duration(s):
        return None
    if re.match(r'^\d{1,3}:\d{2}(:\d{2})?$', s):
        parts = [int(x) for x in s.split(':')]
        return parts[0] * 60 + parts[1]
    mins = 0.0
    for pat, factor in ((r'(\d+(?:\.\d+)?)\s*天', 1440.0), (r'(\d+(?:\.\d+)?)\s*(?:小时|时)', 60.0),
                        (r'(\d+(?:\.\d+)?)\s*(?:分钟|分)', 1.0), (r'(\d+(?:\.\d+)?)\s*秒', 1.0 / 60.0)):
        m = re.search(pat, s)
        if m and not (factor == 1.0 and re.search(r'\d\s*(?:小时|时)', s) and '钟' not in s):
            mins += float(m.group(1)) * factor
    return round(mins, 2) if mins else None


# ============================================================ 单个直播间分析
def _debug(debug, *a):
    if debug:
        print('      ·', *a)


def analyze_room(rows, hi, idx, ch, sheet_name, src_file, aw=None, debug=False):
    """把一个直播间的工作表 → {channels, totals, ok_totals, metrics, ...}。

    aw = find_header 返回的「列名 → 精确/模糊」映射，仅用于 --debug 打印。
    """
    field_keys = [f for f, _l, _u, _k in COLS]
    channels = []
    did_totals = None
    extras = {}
    skipped = []
    for i in sorted(rows.keys()):
        if i <= hi:
            continue
        row = rows[i] or []
        if len(row) <= ch:
            continue
        name = str(row[ch] or '').strip()
        if not name:
            continue
        if name in SKIP_ROW_NAMES or norm(name) in {norm(x) for x in SKIP_ROW_NAMES}:
            skipped.append(name)
            continue
        rec = {}
        for f in field_keys:
            j = idx.get(f)
            rec[f] = round(num(row[j]), 4) if (j is not None and len(row) > j) else 0.0
        if name in TOTAL_ROW_NAMES:
            did_totals = rec
            for f, _l, _u, _k in EXTRA_COLS:
                j = idx.get(f)
                if j is not None and len(row) > j and str(row[j] or '').strip() not in ('', '—'):
                    extras[f] = str(row[j]).strip()
            continue
        rec['name'] = name
        channels.append(rec)

    # 合计：优先用表里的「整体」行（真值），没有才自己加总
    src = '表内整体行'
    if did_totals:
        totals = dict(did_totals)
    else:
        totals = {f: round(sum(c.get(f, 0.0) for c in channels), 4) for f in field_keys}
        src = '渠道加总'
    for f, _l, _u, _k in EXTRA_COLS:
        v = extras.get(f)
        if f == 'qianchuan':
            totals[f] = round(num(v), 4)
        elif f == 'live_duration':
            totals[f] = parse_duration_minutes(v)
        else:
            # 人均观看时长是「58秒」这种带单位的文本，原样留着（前端直接显示）
            totals[f] = (str(v).strip() if v is not None else None)

    sum_ch = {f: round(sum(c.get(f, 0.0) for c in channels), 4) for f in field_keys}
    mismatch = {f: round(sum_ch[f] - (totals.get(f) or 0), 4) for f in field_keys}

    # 异常渠道：互动次数 ÷ 观看次数 ≥ ANOM_RATIO → 两个数口径不一致，不参与互动率合算
    #            达到 ANOM_WARN_RATIO 但没到 ANOM_RATIO → 只挂提示，数据照常参与合算
    anomalies = []
    warnings = []
    for c in channels:
        v, it = c.get('views') or 0, c.get('interactions') or 0
        ratio = (it / v) if v else None
        c['interaction_ratio'] = round(ratio, 4) if ratio is not None else None
        big = (v >= ANOM_MIN_VIEWS) or (it >= ANOM_MIN_INTER)   # 观看够多 或 互动本身够大
        c['anomaly'] = bool(big and ratio is not None and ratio >= ANOM_RATIO)
        c['suspect'] = bool(not c['anomaly'] and v >= ANOM_MIN_VIEWS and ratio is not None and ratio >= ANOM_WARN_RATIO)
        if c['anomaly']:
            anomalies.append(c['name'])
        elif c['suspect']:
            warnings.append(c['name'])
    ok_totals = {f: round(sum(c.get(f, 0.0) for c in channels if not c['anomaly']), 4) for f in field_keys}
    excluded_inter = round((totals.get('interactions') or 0) - (ok_totals.get('interactions') or 0), 4)

    metrics = compute_metrics(totals, ok_totals)
    metrics['qianchuan_roi'] = div(totals.get('paid_amount'), totals.get('qianchuan'))
    if totals.get('live_duration'):
        metrics['orders_per_hour'] = div(totals.get('paid_orders'), (totals.get('live_duration') or 0) / 60.0)
        metrics['gmv_per_hour'] = div(totals.get('paid_amount'), (totals.get('live_duration') or 0) / 60.0)

    return {
        'sheet': sheet_name, 'source_file': src_file,
        'channels': {c['name']: {k: v for k, v in c.items() if k != 'name'} for c in channels},
        'channel_order': [c['name'] for c in channels],
        'totals': {k: r6(v) for k, v in totals.items()},
        'ok_totals': ok_totals,
        'metrics': {k: r6(v) for k, v in metrics.items()},
        'totals_source': src,
        'row_sum_mismatch': {k: v for k, v in mismatch.items() if abs(v) > 0.5},
        'anomaly_channels': anomalies,
        'suspect_channels': warnings,
        'excluded_interactions': excluded_inter,
        'excluded_share': round(div(excluded_inter, totals.get('interactions')) or 0.0, 4),
        'skipped_rows': skipped,
        'extras': extras,
    }


def compute_metrics(tot, ok_tot=None):
    """由合计字段算派生指标。ok_tot 用于互动率（剔除口径异常的渠道）。"""
    o = ok_tot or tot
    return {
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
        'qianchuan_roi': None,
        'live_duration': tot.get('live_duration'),
        'qianchuan': tot.get('qianchuan'),
        'funnel': [
            {'key': 'impressions', 'label': '直播间曝光', 'value': tot['impressions']},
            {'key': 'views', 'label': '直播间观看', 'value': tot['views']},
            {'key': 'product_impressions', 'label': '商品曝光', 'value': tot['product_impressions']},
            {'key': 'product_clicks', 'label': '商品点击', 'value': tot['product_clicks']},
            {'key': 'paid_orders', 'label': '成交订单', 'value': tot['paid_orders']},
        ],
    }


def sum_rooms(rooms):
    """把多个直播间相加成「全店」口径。"""
    field_keys = [f for f, _l, _u, _k in COLS]
    keys = field_keys + ['qianchuan']
    tot = {k: round(sum((r['totals'].get(k) or 0) for r in rooms.values()), 4) for k in keys}
    live = round(sum((r['totals'].get('live_duration') or 0) for r in rooms.values()), 2)
    tot['live_duration'] = live
    ok_tot = {f: round(sum((r['ok_totals'].get(f) or 0) for r in rooms.values()), 4) for f in field_keys}
    m = compute_metrics(tot, ok_tot)
    m['qianchuan_roi'] = div(tot.get('paid_amount'), tot.get('qianchuan'))
    if live:
        m['orders_per_hour'] = div(tot.get('paid_orders'), live / 60.0)
        m['gmv_per_hour'] = div(tot.get('paid_amount'), live / 60.0)
    total_inter = round(sum((r['totals'].get('interactions') or 0) for r in rooms.values()), 4)
    excl = round(sum((r.get('excluded_interactions') or 0) for r in rooms.values()), 4)
    # 全店视角的渠道明细：同名渠道跨直播间相加，比率按合计值重算（异常/可疑标记同 analyze_room 口径）
    merged_ch = {}
    for one in rooms.values():
        for name, ch in (one.get('channels') or {}).items():
            agg = merged_ch.setdefault(name, {f: 0.0 for f in field_keys})
            for f in field_keys:
                agg[f] = round(agg[f] + (ch.get(f) or 0.0), 4)
    for name, agg in merged_ch.items():
        v, it = agg.get('views') or 0, agg.get('interactions') or 0
        ratio = (it / v) if v else None
        agg['interaction_ratio'] = round(ratio, 4) if ratio is not None else None
        big = (v >= ANOM_MIN_VIEWS) or (it >= ANOM_MIN_INTER)
        agg['anomaly'] = bool(big and ratio is not None and ratio >= ANOM_RATIO)
        agg['suspect'] = bool(not agg['anomaly'] and v >= ANOM_MIN_VIEWS and ratio is not None and ratio >= ANOM_WARN_RATIO)
    merged_order = [n for n, _v in sorted(((n, a.get('views') or 0) for n, a in merged_ch.items()), key=lambda x: -x[1])]
    return {
        'sheet': '多直播间合计',
        'source_file': '＋'.join(sorted({(r.get('source_file') or '') for r in rooms.values()})),
        'channels': merged_ch, 'channel_order': merged_order,
        'totals': {k: r6(v) for k, v in tot.items()},
        'ok_totals': ok_tot,
        'metrics': {k: r6(v) for k, v in m.items()},
        'totals_source': '各直播间相加',
        'row_sum_mismatch': {},
        'anomaly_channels': sorted({a for r in rooms.values() for a in (r.get('anomaly_channels') or [])}),
        'suspect_channels': sorted({a for r in rooms.values() for a in (r.get('suspect_channels') or [])}),
        'excluded_interactions': excl,
        'excluded_share': round(div(excl, total_inter) or 0.0, 4),
        'skipped_rows': [],
        'extras': {},
        'is_all': True,
    }


# ============================================================ 规则 / 环比 / 渠道 / 洞察
def evaluate_rules(m, tot):
    """平台规则匹配：逐条判 达标/偏低/偏高。比率类统一换算成百分数展示。"""
    out = []
    for key, label, lo, hi, unit, why in PLATFORM_RULES:
        v = m.get(key)
        pv = v * 100 if (unit == '%' and v is not None) else v
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
            disp = '%.2f%%' % pv
        elif unit == '倍':
            disp = '%.2f 倍' % pv
        else:
            disp = '%s 元' % f'{pv:,.0f}'
        # ★ 互动率 > 100% 是平台两列口径不一致（互动次数按动作计数、观看按人头计数），
        #   这种数不当成「达标」也不当成「不达标」，标成暂不判定并在 why 里说清原因。
        #   注：PLATFORM_RULES 里这条规则的 key 是 interaction_rate（用剔除异常渠道后的 ok_totals 算），
        #   但两个 key 都兜住，免得以后换口径时护栏悄悄失效。
        if key in ('interaction_rate', 'view_interaction_rate') and pv is not None and pv > 100:
            status = 'unknown'
            why = '互动次数已超过观看次数，属平台两列口径不一致（互动按动作计、观看按人头计），今日这项不判定'
        rng = ('≥ %g' % lo) if hi is None else ('%g ~ %g' % (lo, hi))
        rng += '%' if unit == '%' else (' 倍' if unit == '倍' else ' 元')
        out.append({'key': key, 'label': label, 'status': status, 'unit': unit,
                    'value': round(pv, 4) if pv is not None else None,
                    'value_disp': disp, 'range': rng, 'why': why})
    return out


def day_over_day(cur, prev):
    """逐指标环比：绝对值 + 前一日 + 环比%（比率类给百分点差 pp）。"""
    ct = (cur or {}).get('totals') or {}
    pt = (prev or {}).get('totals') or {}
    cm = (cur or {}).get('metrics') or {}
    pm = (prev or {}).get('metrics') or {}
    rows = []
    for field, label, unit, _k in COLS:
        c = ct.get(field)
        p = pt.get(field) if pt else None
        chg = nz0((c / p - 1) if (p not in (None, 0) and c is not None) else None)
        rows.append({'key': field, 'label': label, 'unit': unit, 'cur': c, 'prev': p, 'chg': chg, 'is_rate': False,
                     'dir': ('up' if (chg or 0) > 0 else ('down' if (chg or 0) < 0 else 'flat')) if chg is not None else 'na'})
    for key, label, unit, nd in [
        ('exposure_view_rate', '曝光→观看率', '%', 2), ('interaction_rate', '观看→互动率', '%', 2),
        ('product_ctr', '商品点击率', '%', 2), ('click_cvr', '点击→成交转化率', '%', 2),
        ('new_follower_rate', '涨粉率', '%', 2), ('gpm', 'GPM', '元', 0),
        ('uv_value', 'UV 价值', '元', 2), ('aov', '客单价', '元', 2),
        ('qianchuan_roi', '千川 ROI', '倍', 2),
    ]:
        c = cm.get(key)
        p = pm.get(key) if pm else None
        # ★ 派生指标的差必须用「原始值先差、再 round」：若先把两边各自 round 到 nd 位再相减，
        #   会出现同页两个数（卡片用 raw metrics 算 delta，报告 bullet 用这里），例如
        #   卡片 +0.08pp 而报告 +0.09pp（10-10 全店 曝光→观看率）。
        raw_diff = (c - p) if (c is not None and p is not None) else None
        if unit == '%':
            cd = round(c * 100, nd) if c is not None else None
            pd_ = round(p * 100, nd) if p is not None else None
            diff = round(raw_diff * 100, nd) if raw_diff is not None else None
        else:
            cd = round(c, nd) if c is not None else None
            pd_ = round(p, nd) if p is not None else None
            diff = round(raw_diff, nd) if raw_diff is not None else None
        rows.append({'key': key, 'label': label, 'unit': unit, 'cur': cd, 'prev': pd_,
                     'chg': nz0(raw_diff / abs(p) if (raw_diff is not None and p) else None),
                     'pp_diff': nz0(diff), 'is_rate': True,
                     'dir': ('up' if (diff or 0) > 0 else ('down' if (diff or 0) < 0 else 'flat')) if diff is not None else 'na'})
    return rows


def channel_rows(cur, prev):
    """渠道明细 + 环比 + 占比。"""
    cur_ch = (cur or {}).get('channels') or {}
    order = (cur or {}).get('channel_order') or list(cur_ch.keys())
    prev_ch = (prev or {}).get('channels') or {}
    rows = []
    for name in order:
        rec = cur_ch.get(name)
        if rec is None:
            continue
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
            'anomaly': bool(rec.get('anomaly')),
            'suspect': bool(rec.get('suspect')),
            'interaction_ratio': pct(rec.get('interaction_ratio')),
        })
    rows.sort(key=lambda x: -(x['views'] or 0))
    tv = sum((x['views'] or 0) for x in rows)
    for x in rows:
        x['share'] = pct(div(x['views'], tv))
    return rows


def build_insights(cur, prev, dod, rules, channels, compare=None):
    """生成「数据表现 / 平台规则匹配 / 优化建议」三段文字。"""
    t = cur['totals']
    m = cur['metrics']
    lines = {'headline': [], 'data': [], 'rules': [], 'actions': []}

    if prev:
        dv = [r for r in dod if r['key'] == 'views'][0]
        sign = '+' if (dv['chg'] or 0) >= 0 else ''
        lines['headline'].append('观看 %s 次（前一日 %s，%s%s%%）' % (
            fmt_int(t['views']), fmt_int(dv['prev']), sign, fmt_num((dv['chg'] or 0) * 100, 1)))
    else:
        lines['headline'].append('观看 %s 次（首日入库，无前一日可比）' % fmt_int(t['views']))

    if prev:
        for key in ('impressions', 'product_clicks', 'paid_orders', 'paid_amount'):
            r = [x for x in dod if x['key'] == key][0]
            arrow = '↑' if r['dir'] == 'up' else ('↓' if r['dir'] == 'down' else '→')
            lines['data'].append('%s %s %s，前一日 %s，%s %.1f%%' % (
                r['label'], fmt_int(r['cur']), r['unit'], fmt_int(r['prev']), arrow, abs((r['chg'] or 0) * 100)))
        for key, label in (('exposure_view_rate', '曝光→观看率'), ('interaction_rate', '观看→互动率'),
                           ('product_ctr', '商品点击率'), ('click_cvr', '点击→成交转化率')):
            r = [x for x in dod if x['key'] == key][0]
            if r['cur'] is None or r['prev'] is None:
                continue
            lines['data'].append('%s %.2f%%（前一日 %.2f%%，%+.2fpp）' % (label, r['cur'], r['prev'], (r['pp_diff'] or 0)))
    else:
        lines['data'].append('曝光→观看率 %s、观看→互动率 %s、商品点击率 %s、点击→成交 %s、涨粉率 %s' % (
            fmt_pct(m.get('exposure_view_rate')), fmt_pct(m.get('interaction_rate')), fmt_pct(m.get('product_ctr')),
            fmt_pct(m.get('click_cvr')), fmt_pct(m.get('new_follower_rate'))))
        lines['data'].append('⚠️ 没有前一日数据，环比一栏留空；第二天起自动出环比。')

    if channels:
        top = channels[0]
        lines['data'].append('渠道结构：%s 贡献观看 %s 次（占 %s%%），共 %d 个入口' % (
            top['name'], fmt_int(top['views']), fmt_num(top['share'], 1), len(channels)))
        chg_ok = [c for c in channels if c['chg'] is not None and (c['prev_views'] or 0) >= 50]
        if chg_ok:
            up = max(chg_ok, key=lambda c: c['chg'])
            dn = min(chg_ok, key=lambda c: c['chg'])
            # ★ 按符号分支措辞：涨跌看 max/min，若全是上涨，min 那个也是涨的，
            #   固定写「掉得最多（+3.2%）」会自相矛盾（10-10 数码旗舰店、10-09 智能设备都踩过）。
            if up['chg'] <= 0:
                lines['data'].append('渠道里 %s 相对最抗跌（观看 %+.1f%%）；当日各入口环比全为负' % (
                    up['name'], up['chg'] * 100))
            elif dn['chg'] >= 0:
                lines['data'].append('渠道里 %s 涨得最猛（观看 %+.1f%%）；当日各入口环比全为正' % (
                    up['name'], up['chg'] * 100))
            else:
                lines['data'].append('渠道里 %s 涨得最猛（观看 %+.1f%%）；%s 掉得最多（%+.1f%%）' % (
                    up['name'], up['chg'] * 100, dn['name'], dn['chg'] * 100))

    if compare and len(compare) > 1:
        by_views = sorted(compare, key=lambda x: -(x['views'] or 0))
        lead = by_views[0]
        rests = '、'.join('%s 占 %s%%' % (x['name'], fmt_num(x['view_share'], 1)) for x in by_views[1:4])
        lines['data'].append('直播间对比：%s 观看最多（%s 次，占 %s%%）；%s' % (
            lead['name'], fmt_int(lead['views']), fmt_num(lead['view_share'], 1), rests))
        pool = [x for x in compare if x.get('gpm')]
        if pool:
            best = max(pool, key=lambda x: x['gpm'])
            worst = min(pool, key=lambda x: x['gpm'])
            lines['data'].append('变现效率：%s GPM %s 元最高，%s %s 元最低（差 %s%%）' % (
                best['name'], fmt_int(best['gpm']), worst['name'], fmt_int(worst['gpm']),
                fmt_num((best['gpm'] / worst['gpm'] - 1) * 100, 0) if worst['gpm'] else '—'))

    anom = cur.get('anomaly_channels') or []
    if anom:
        tail = ('；被剔除的互动数占全场 %.1f%%，若占比过高请找平台核对两列口径。' % ((cur.get('excluded_share') or 0) * 100)
                if (cur.get('excluded_share') or 0) > 0.15 else '。')
        # ★ 判定在「房间内」做，全店列表是多间并集：不能写成「全店该渠道 ≥250%」，
        #   否则与页面渠道表（按全店合计比值打标签，全店比值往往 <250%）对不上。
        lines['data'].append('ℹ️ 渠道「%s」在部分直播间内口径异常（互动次数 ÷ 观看次数 ≥ %.0f%%），'
                             '对应房间的这些渠道已从互动率合算中剔除%s' % (
                                 '、'.join(anom), ANOM_RATIO * 100, tail))

    if prev:
        pv = prev['totals'].get('views')
        dv = (t['views'] / pv - 1) if pv else None
        if dv is not None and abs(dv) >= 0.30:
            lines['data'].append(('⚠️ ' if dv < 0 else '🚀 ') + '观看量单日%s %.0f%%，%s' % (
                '下滑' if dv < 0 else '暴涨', abs(dv) * 100,
                '若为下滑需排查是否被限流/断播' if dv < 0 else '注意承接能力是否跟得上'))

    good = [r for r in rules if r['status'] == 'ok']
    bad = [r for r in rules if r['status'] in ('low', 'high')]
    if good:
        lines['rules'].append('✅ 达标：' + '、'.join('%s %s（平台参考 %s）' % (r['label'], r['value_disp'], r['range']) for r in good))
    for r in bad:
        lines['rules'].append('⚠️ %s %s，%s平台参考区间 %s。%s' % (
            r['label'], r['value_disp'], '低于' if r['status'] == 'low' else '高于', r['range'], r['why']))
    for r in rules:
        if r['status'] == 'unknown' and r['value'] is not None:
            lines['rules'].append('❓ %s %s，%s。' % (r['label'], r['value_disp'], r['why']))
    if not bad and not any(r['status'] == 'unknown' and r['value'] is not None for r in rules):
        lines['rules'].append('✅ 全部核心指标落在平台推荐区间内，当前分发逻辑健康，重点是保住这套节奏。')

    if prev:
        prev_t = prev['totals']
        v_chg = (t.get('views') or 0) / prev_t['views'] - 1 if prev_t.get('views') else 0
        i_chg = (t.get('impressions') or 0) / prev_t['impressions'] - 1 if prev_t.get('impressions') else 0
        evr_c, evr_p = m.get('exposure_view_rate'), (prev.get('metrics') or {}).get('exposure_view_rate')
        if v_chg < -0.15 and i_chg < -0.15 and evr_c is not None and evr_p and evr_c >= evr_p:
            lines['rules'].append('🔎 判断：曝光和观看同比例下滑，但「曝光→观看率」没降 → 不是封面/素材问题，更像**平台减少了推流**（时段竞争加剧、历史 GPM 拖累、或场次时长不足）。优先核对是否断播、是否有违规限流提示。')

    def has(k, st='low'):
        return any(r['key'] == k and r['status'] == st for r in rules)

    if has('gpm') or has('click_cvr') or has('qianchuan_roi'):
        lines['actions'].append('**转化端**：GPM/ROI 是平台给量的第一指标。把主推品提到开场前 30 分钟，配合「限时直降 + 库存倒计时」逼单；检查到手价与竞对同款价差，价格力不足时优先用赠品而不是降标价。')
    if has('product_ctr'):
        lines['actions'].append('**商品卡**：点击率偏低说明福袋/主图/讲解节奏没把商品推到观众面前。每 10 分钟口播一次主推品并置顶商品卡，商品标题前 8 个字放「型号 + 核心卖点 + 价格」。')
    if has('interaction_rate'):
        lines['actions'].append('**互动**：开播 5 分钟做「扣1抽奖」，每 15 分钟一次福袋；把「点关注亮灯牌」写进话术循环——互动率是平台判断是否继续推流的直接信号。')
    if has('exposure_view_rate'):
        lines['actions'].append('**封面/标题**：曝光进不来人是推荐位素材问题。今天换 2 组封面（产品特写 + 价格钩子），标题带「今晚 8 点直降」，隔天对比曝光→观看率。')
    if has('new_follower_rate'):
        lines['actions'].append('**涨粉**：涨粉率低 = 缺关注引导。每场安排 3 次「关注的家人扣关注，抽手环」，把加粉丝团作为抽奖门槛。')
    if compare and len(compare) > 1:
        weak = [x for x in compare if x.get('view_share') is not None and x['view_share'] < 5]
        if weak:
            lines['actions'].append('**流量分配**：%s 观看占比不足 5%%，属于「开播了但平台没给量」。先补齐这间的开播时长与场次稳定性（平台按历史场次给初始流量），再谈投放。' % '、'.join(x['name'] for x in weak))
        top2 = sorted([x for x in compare if x.get('gpm')], key=lambda x: -(x['gpm'] or 0))[:2]
        if top2:
            lines['actions'].append('**复制高效场**：%s 是本店变现效率最高的两间，把它们的排品顺序、开播时段、话术脚本抄到低效直播间。' % '、'.join(
                '%s（GPM %s 元、客单价 %s 元）' % (x['name'], fmt_int(x['gpm']), fmt_int(x.get('aov'))) for x in top2))
    if not lines['actions']:
        lines['actions'].append('**守成**：数据全绿，重点不是加动作而是「复制今天」——把本场排品顺序、开播时间、话术节奏固化成模板，明天照跑。')

    return lines


# ============================================================ 落盘
def day_path(d):
    return os.path.join(DATA_DIR, d[:4], d + '.json')


def report_dir_for(d):
    return os.path.join(REPORT_DIR, d[:4], d)


def report_path(d, scope):
    return os.path.join(report_dir_for(d), scope + '.json')


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


def _strip_times(obj):
    """去掉时间戳后的副本 —— 用来判断「重灌同一天是否真的没变化」。"""
    import copy as _copy
    o = _copy.deepcopy(obj or {})
    o.pop('updated_at', None)
    o.pop('generated_at', None)
    for r in (o.get('rooms') or {}).values():
        if isinstance(r, dict):
            r.pop('updated_at', None)
    return o


def write_day(d, payload):
    p = day_path(d)
    old = load_day(d) if os.path.exists(p) else None
    if old and _strip_times(old) == _strip_times(payload):
        # 内容一模一样（只是又跑了一遍同一份表）→ 保留原时间戳，
        # 否则每次双击「刷流量数据.bat」都会产生一个只有时间戳变化的空提交。
        payload['updated_at'] = old.get('updated_at')
        for rn, r in (payload.get('rooms') or {}).items():
            o_room = (old.get('rooms') or {}).get(rn) or {}
            if o_room.get('updated_at'):
                r['updated_at'] = o_room['updated_at']
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return p


def day_is_demo(rec):
    rooms = (rec or {}).get('rooms') or {}
    if not rooms:
        return bool((rec or {}).get('demo'))
    return all((r.get('demo') for r in rooms.values()))


def write_index():
    days = []
    for d in all_dates():
        rec = load_day(d) or {}
        rooms = rec.get('rooms') or {}
        t = rec.get('totals') or {}
        days.append({
            'date': d, 'pretty': '%d月%d日' % (int(d[5:7]), int(d[8:10])),
            'demo': day_is_demo(rec), 'rooms': list(rooms.keys()), 'n_rooms': len(rooms),
            'views': t.get('views'), 'impressions': t.get('impressions'),
            'paid_orders': t.get('paid_orders'), 'paid_amount': t.get('paid_amount'),
            'gpm': round((rec.get('metrics') or {}).get('gpm') or 0) or None,
            'roi': (rec.get('metrics') or {}).get('qianchuan_roi'),
        })
    months = {}
    for x in days:
        months.setdefault(x['date'][:7], []).append(x['date'])
    idx = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'start_month': START_YM, 'all_scope': ALL_SCOPE,
        'months': [{'ym': k, 'label': '%d月' % int(k[5:7]), 'count': len(v), 'dates': sorted(v, reverse=True)}
                   for k, v in sorted(months.items())],
        'days': days,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    p = os.path.join(DATA_DIR, 'index.json')
    if os.path.exists(p):
        try:
            with open(p, encoding='utf-8') as f:
                old_idx = json.load(f)
            if _strip_times(old_idx) == _strip_times(idx):
                idx['generated_at'] = old_idx.get('generated_at')   # 没实质变化就别改时间戳
        except Exception:
            pass
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    return p, idx


def room_compare(rec):
    """全店视角：各直播间横向对比行。"""
    rooms = (rec or {}).get('rooms') or {}
    if len(rooms) <= 1:
        return []
    tot_views = sum((r['totals'].get('views') or 0) for r in rooms.values())
    gmps = sorted([g for g in ((r['metrics'].get('gpm') or 0) for r in rooms.values()) if g])
    # ★ 偶数个直播间时 len//2 取的是「上中位」（6 间取第 4 小），会系统性偏高；
    #   用 statistics.median 取真中位数（两中间值平均）。
    med_gpm = statistics.median(gmps) if gmps else None
    rows = []
    for name, r in rooms.items():
        t, m = r['totals'], r['metrics']
        rows.append({
            'name': name, 'views': t.get('views'), 'impressions': t.get('impressions'),
            'view_share': pct(div(t.get('views'), tot_views)),
            'paid_amount': t.get('paid_amount'), 'paid_orders': t.get('paid_orders'),
            'evr': pct(m.get('exposure_view_rate')), 'ctr': pct(m.get('product_ctr')),
            'cvr': pct(m.get('click_cvr')), 'gpm': round(m.get('gpm')) if m.get('gpm') else None,
            'aov': round(m.get('aov')) if m.get('aov') else None,
            'roi': m.get('qianchuan_roi'),
            'uv_value': round(m['uv_value'], 4) if m.get('uv_value') is not None else None,
            'interaction_rate': pct(m.get('interaction_rate')),
            'new_follower_rate': pct(m.get('new_follower_rate')),
            'anomaly_channels': r.get('anomaly_channels') or [],
            'suspect_channels': r.get('suspect_channels') or [],
            'vs_peer_gpm': (round((m.get('gpm') or 0) / med_gpm, 2) if (med_gpm and m.get('gpm')) else None),
        })
    rows.sort(key=lambda x: -(x['views'] or 0))
    return rows


def peer_benchmark(compare):
    """横向对比：各指标中位数（本店各间的参照线）。"""
    out = []
    if not compare or len(compare) < 2:
        return out
    for key, label, unit, nd in PEER_METRICS:
        vals = sorted(x[key] for x in compare if x.get(key) is not None)
        if not vals:
            continue
        pool = [x for x in compare if x.get(key) is not None]
        best = max(pool, key=lambda x: x[key])
        worst = min(pool, key=lambda x: x[key])
        out.append({'key': key, 'label': label, 'unit': unit, 'decimals': nd,
                    'median': round(statistics.median(vals), nd),
                    'best': {'name': best['name'], 'value': round(best[key], nd)},
                    'worst': {'name': worst['name'], 'value': round(worst[key], nd)}})
    return out


def build_scope(rec, prev_rec, scope):
    """生成某个 scope（全店 / 某直播间）的完整日报体。"""
    if scope == ALL_SCOPE:
        cur = {k: v for k, v in rec.items() if k != 'rooms'}
        prev = ({k: v for k, v in prev_rec.items() if k != 'rooms'} if prev_rec else None)
    else:
        cur = (rec.get('rooms') or {}).get(scope)
        prev = ((prev_rec or {}).get('rooms') or {}).get(scope) if prev_rec else None
    if not cur:
        return None
    dod = day_over_day(cur, prev)
    rules = evaluate_rules(cur['metrics'], cur['totals'])
    channels = channel_rows(cur, prev)
    # 全店与单间都带上「各直播间横向对比」：单间视角里它用来回答
    # 「我这间在全店排第几」，页面的同业横向基准表也依赖它。
    compare = room_compare(rec)
    ins = build_insights(cur, prev, dod, rules, channels,
                         compare=compare if scope == ALL_SCOPE else None)
    return {
        # room 与 scope 同值：scope='全店' 时 room 也写 '全店'。
        # 前端会拿 r.room || r.scope 当显示名，保留 room 是为了兼容旧版页面的读取路径。
        'scope': scope, 'room': scope, 'is_all': scope == ALL_SCOPE,
        # 页面拿 date/prev_date 显示「数据日期 / 对比基准」，缺了会显示成首日无对比
        'date': rec.get('date'), 'prev_date': (prev_rec or {}).get('date'),
        # 状态条右侧的「更新于」：用日文件里的 updated_at（内容没变时 write_day 会保留旧值，
        # 所以重建不会让这个时间戳乱跳；日报体自己不再生成时间戳，避免无谓的 git 改动）
        'generated_at': rec.get('updated_at') or rec.get('created_at'),
        'prev_scope_exists': bool(prev),
        'totals': cur['totals'], 'metrics': cur['metrics'], 'ok_totals': cur.get('ok_totals'),
        'source_file': cur.get('source_file'), 'source_sheet': cur.get('sheet'),
        'totals_source': cur.get('totals_source'),
        'anomaly_channels': cur.get('anomaly_channels') or [],
        'suspect_channels': cur.get('suspect_channels') or [],
        'excluded_share': cur.get('excluded_share'),
        'row_sum_mismatch': cur.get('row_sum_mismatch') or {},
        'dod': dod, 'rules': rules, 'channels': channels,
        'room_compare': compare, 'peer_benchmark': peer_benchmark(compare),
        'insights': ins,
    }


def write_report(d, rec, prev_rec):
    rpt = {
        'date': d, 'prev_date': (prev_rec or {}).get('date'),
        'demo': day_is_demo(rec),
        'rooms': list((rec.get('rooms') or {}).keys()),
        'all_scope': ALL_SCOPE, 'source_files': rec.get('source_files') or {},
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'scopes': {},
    }
    for scope in [ALL_SCOPE] + list((rec.get('rooms') or {}).keys()):
        s = build_scope(rec, prev_rec, scope)
        if s:
            rpt['scopes'][scope] = s
    return rpt


def refresh_all_scope(rec):
    """全店口径永远由各直播间现算。
    日文件里存的合计可能是旧版脚本写的（例如早期版本不带渠道明细），
    重建日报时重算一遍，避免「rooms 有 6 间但全店渠道是空的」这种自相矛盾。"""
    rooms = rec.get('rooms') or {}
    if not rooms:
        return rec
    agg = sum_rooms(rooms)
    out = dict(rec)
    for k in ('channels', 'channel_order', 'totals', 'ok_totals', 'metrics', 'totals_source',
              'anomaly_channels', 'suspect_channels', 'excluded_interactions', 'excluded_share',
              'row_sum_mismatch', 'skipped_rows'):
        if k in agg:
            out[k] = agg[k]
    return out


def rebuild_reports(quiet=False):
    dates = all_dates()
    prev_rec = None
    for d in dates:
        cur = refresh_all_scope(load_day(d) or {})
        if not cur:
            continue
        rpt = write_report(d, cur, prev_rec)
        dd = report_dir_for(d)
        os.makedirs(dd, exist_ok=True)
        want = {'%s.json' % k for k in rpt['scopes']}
        for p in glob.glob(os.path.join(dd, '*.json')):
            if os.path.basename(p) not in want:
                os.remove(p)
        for k, s in rpt['scopes'].items():
            with open(os.path.join(dd, k + '.json'), 'w', encoding='utf-8') as f:
                json.dump(s, f, ensure_ascii=False, indent=1)
        prev_rec = cur
        if not quiet:
            rooms = list((cur.get('rooms') or {}).keys())
            print('   日报 %s  直播间 %d 个%s' % (d, len(rooms), '' if len(rooms) != 1 else '（%s）' % rooms[0]))
    # 清掉「没有对应日文件」的残留日报目录（例如 seed_demo --clear 删了示例天、
    # 或早前测试留下的 reports/2026/2026-12-31）——否则它们会一直被 git 跟踪着。
    alive = set(dates)
    for p in glob.glob(os.path.join(REPORT_DIR, '*', '*')):
        if not os.path.isdir(p):
            continue
        d = os.path.basename(p)
        if re.match(r'^\d{4}-\d{2}-\d{2}$', d) and d not in alive:
            shutil.rmtree(p, ignore_errors=True)
            if not quiet:
                print('   🧹 清理无对应数据的日报目录 %s' % os.path.relpath(p, ROOT))
    ip, idx = write_index()
    return dates, ip, idx


# ============================================================ 猜直播间名
def room_core(name):
    """直播间的「核」名：去掉尾部「直播间」三个字（小米智能设备旗舰店直播间 → 小米智能设备旗舰店）。

    只剥「直播间」，不剥「旗舰店」：剥成「小米智能设备」就对不上文件名里的「小米智能设备旗舰店」了。
    """
    s = norm(name)
    suf = '直播间'
    return s[:-len(suf)] if (s.endswith(suf) and len(s) > len(suf) + 1) else s


def guess_room(stem, known):
    """用文件名猜直播间名：先精确/包含匹配已是 key 的名字，再抽「xx直播间/旗舰店」片段。

    最后一步会拿「核」名回捞历史名 —— 文件名少写或多写尾部「直播间」时也能对上，例如
    小米智能设备旗舰店10.13日流量.xlsx → 历史名「小米智能设备旗舰店直播间」，
    否则会凭空多出一个直播间、让该间的历史记录断档。
    """
    s = str(stem or '').strip()
    ns = norm(s)
    if not ns:
        return None
    for k in known:
        if norm(k) == ns:
            return k
    # ① 先抽「文件名里的直播间片段」，按核名回捞历史名
    #    ★ 必须排在「子串包含」前面：known 里同时有「小米智能设备旗舰店」和「小米智能设备旗舰店直播间」时，
    #      子串匹配只会捞到短名 → 凭空多一个直播间、老记录断档
    m = re.search(r'(小米[\u4e00-\u9fa5A-Za-z0-9&]{2,20}?(?:直播间|旗舰店直播间|旗舰店))', s)
    if not m:
        m = re.search(r'([\u4e00-\u9fa5A-Za-z0-9&]{2,20}?(?:直播间|旗舰店))', s)
    frag = m.group(1) if m else None
    if frag:
        hit = sorted({k for k in known if len(k) >= 4 and room_core(k) == room_core(frag)})
        if hit:
            return max(hit, key=len)
    # ② 再退回「子串包含」（文件名叫「小米官方手表10.16日流量」这类没后缀的）
    cands = [k for k in known if len(k) >= 4 and (norm(k) in ns or ns in norm(k))]
    if cands:
        return max(cands, key=lambda x: len(x))
    return frag


_KNOWN_CACHE = None


def known_rooms():
    """历史入库过的直播间名 + team_config 里的名单。"""
    global _KNOWN_CACHE
    if _KNOWN_CACHE is not None:
        return _KNOWN_CACHE
    out = set()
    for d in all_dates():
        rec = load_day(d) or {}
        out.update((rec.get('rooms') or {}).keys())
    try:
        sys.path.insert(0, ROOT)
        import team_config
        for attr in dir(team_config):
            if attr.startswith('_'):
                continue
            v = getattr(team_config, attr)
            if isinstance(v, dict):
                for k in v.keys():
                    # ★ 全收：TEAM_MAP 里「小米官方手表」「小米数码旗舰店」这类名字不含「直播间/旗舰店」，
                    #   但真实导出文件名正好就是它们，必须能精确命中
                    if isinstance(k, str) and len(k) >= 4:
                        out.add(k)
            elif isinstance(v, (list, tuple, set)):
                for k in v:
                    if isinstance(k, str) and ('直播间' in k or '旗舰店' in k):
                        out.add(k)
    except Exception:
        pass
    _KNOWN_CACHE = out
    return out


# ============================================================ 直播间名矫正
# 用户 2026-10-16 定稿：「直播间名字如果有小误差，你自己矫正就行，我们大概率就是这六个直播间，
# 以后新加的我会跟你同步！」→ 文件名推出来的名字先往在营名单上矫正；矫正不了就 **中止、不写数据**，
# 绝不再静默新建一个「幻影直播间」，把该间的历史记录截断。
CANON_ROOMS = [
    '小米官方手环直播间',
    '小米官方手表',
    '小米数码旗舰店',
    '小米官旗手表直播间',
    '小米官方耳机直播间',
    '小米智能设备旗舰店直播间',
]

# 文件名上常见的手写误差，人工兜底（改这里比调相似度阈值可靠）
ROOM_ALIAS = {
    '小米官方手表直播间': '小米官方手表',
    '小米官方手表直播': '小米官方手表',
    '小米官方手表直播号': '小米官方手表',
    '小米官方手表旗舰店': '小米官方手表',
    '小米数码旗舰店直播间': '小米数码旗舰店',
    '小米数码官方旗舰店': '小米数码旗舰店',
    '小米智能设备旗舰店': '小米智能设备旗舰店直播间',
    '小米智能设备直播间': '小米智能设备旗舰店直播间',
    '小米官旗手表': '小米官旗手表直播间',
    '小米手表官旗直播间': '小米官旗手表直播间',
    '小米官方耳机': '小米官方耳机直播间',
    '小米耳机直播间': '小米官方耳机直播间',
    '小米官方手环': '小米官方手环直播间',
    '小米手环直播间': '小米官方手环直播间',
}

_CANON_CACHE = None


def canonical_rooms():
    """在营直播间名单：CANON_ROOMS 打头，再补最近 14 天数据里出现过的名字（顺序=显示顺序）。"""
    global _CANON_CACHE
    if _CANON_CACHE is not None:
        return _CANON_CACHE
    out = list(CANON_ROOMS)
    for d in reversed(all_dates()[-14:]):
        rec = load_day(d) or {}
        for rn in (rec.get('rooms') or {}).keys():
            if rn not in out:
                out.append(rn)
    _CANON_CACHE = out
    return out


def clean_stem(stem):
    """把文件名里的日期/「流量」等噪音去掉，只留直播间名（相似度兜底用）。"""
    s = str(stem or '')
    s = re.sub(r'[\(\)（）\[\]【】\s]', '', s)
    s = re.sub(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?', '', s)
    s = re.sub(r'\d{1,2}\.\d{1,2}日?', '', s)
    s = re.sub(r'\d+', '', s)
    s = re.sub(r'(流量数据|流量表|流量|数据表|数据|明细|导出|副本)', '', s)
    return s.strip('-_·. ')


def correct_room(name, canonical=None):
    """把文件名推出来的直播间名矫正到在营名单。命中返回 (规范名, 依据)，认不出返回 (None, '')。

    顺序：别名表 → 归一化精确 → 核名（尾部「直播间」有无）→ 一方包含另一方 → 相似度。
    相似度要**同时**满足「够像」（≥ 0.62）与「明显领先第二名」（≥ 0.08），
    免得「小米官方手表」和「小米官旗手表直播间」互相抢。
    """
    s = str(name or '').strip()
    if not s:
        return None, ''
    canon = canonical or canonical_rooms()
    if not canon:
        return s, ''                       # 名单空（全新仓库）→ 原样放行
    if s in canon:
        return s, ''
    if ROOM_ALIAS.get(s) in canon:
        return ROOM_ALIAS[s], '别名表'
    ns = norm(s)
    hit = [k for k in canon if norm(k) == ns]
    if hit:
        return hit[0], '去掉空格/符号后同名'
    core = room_core(s)
    hit = [k for k in canon if room_core(k) == core]
    if hit:
        return max(hit, key=len), '尾部「直播间」三字有无'
    hit = [k for k in canon if len(norm(k)) >= 4 and (norm(k) in ns or ns in norm(k))]
    if hit:
        return max(hit, key=len), '名字互相包含'
    ranked = sorted(((difflib.SequenceMatcher(None, ns, norm(k)).ratio(), i, k)
                     for i, k in enumerate(canon)), key=lambda t: (-t[0], t[1]))
    top = ranked[0]
    second = ranked[1][0] if len(ranked) > 1 else 0.0
    if top[0] >= 0.62 and top[0] - second >= 0.08:
        return top[2], '相似度 %.0f%%' % (top[0] * 100)
    return None, ''


def resolve_room(stem, known=None, canon=None, room=None):
    """文件名（已剥扩展名）→ 在营直播间名。

    返回 (名字, 矫正记录, 认不出的原名)：
      * 名字        —— 认出来就是在营名单里的规范名；认不出是 None（--room 时原样返回）
      * 矫正记录    —— [(原名, 规范名, 依据)]，没矫正就是 []
      * 认不出的原名 —— 既不在名单、也找不到相似项时给出原名，入库流程据此中止
    """
    known = known_rooms() if known is None else known
    canon = canonical_rooms() if canon is None else canon
    if room:
        fixed, why = correct_room(room, canon)
        if fixed and fixed != room:
            return fixed, [(room, fixed, why)], None
        return room, [], (None if (not canon or room in canon) else room)
    rn = guess_room(stem, known) or correct_room(clean_stem(stem), canon)[0]
    if not rn:
        return None, [], (stem or None)
    fixed, why = correct_room(rn, canon)
    if fixed and fixed != rn:
        return fixed, [(rn, fixed, why)], None
    if not fixed:
        return None, [], rn
    return rn, [], None


# ============================================================ 主流程
def expand_inputs(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            # ★ 跳过 Excel 打开文件时生成的 ~$xxx.xlsx 锁文件，否则整批会因为「读不出表头」中止
            out.extend(sorted(x for x in glob.glob(os.path.join(p, '*.xlsx'))
                              if not os.path.basename(x).startswith('~$')))
        else:
            out.append(p)
    seen, res = set(), []
    for p in out:
        a = os.path.abspath(p)
        if a not in seen:
            seen.add(a)
            res.append(p)
    return res


def ingest_one_day(paths, d=None, room=None, sheet=None, force=False, quiet=False, debug=False, d_src=None):
    book = None
    try:
        book = parse_xlsx(paths[0], sheet=sheet)
    except ExcelizeError:
        book = None
    d, how = resolve_date(paths, d=d, rows_by_sheet=book, d_src=d_src)
    if d[:7] < START_YM:
        raise SystemExit('❌ %s 早于流量分析起始月份 %s（规则：数据不得早于 10 月）' % (d, START_YM))

    payload = load_day(d) or {
        'date': d, 'demo': False, 'source_files': {}, 'rooms': {},
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    payload.setdefault('rooms', {})
    payload.setdefault('source_files', {})
    payload['demo'] = False

    known = known_rooms()
    canon = canonical_rooms()
    added, replaced, guesses, corrected = [], [], [], []
    for p in paths:
        if not os.path.exists(p):
            raise SystemExit('❌ 找不到文件：%s' % p)
        stem = strip_all_ext(os.path.basename(p))   # ★ 双后缀（.xlsx.xlsx）要全剥掉，否则直播间名会带尾巴
        rn, fixes, unknown = resolve_room(stem, known=known, canon=canon, room=room)
        corrected.extend(fixes)
        if unknown and room:
            print('   ⚠️ 你指定的直播间「%s」不在在营名单（%s）里，按你指定的名字新建。' % (unknown, '、'.join(canon)))
        elif unknown:
            raise SystemExit(
                '❌ 文件名推出来的直播间「%s」不在在营名单里，也找不到相似的。\n'
                '   在营名单：%s\n'
                '   ① 名字写错 → 改文件名重跑，或加 --room "正确名"；\n'
                '   ② 确实是新直播间 → 先跟用户确认归属，再把名字加进 CANON_ROOMS（%s）后重跑。'
                % (unknown, '、'.join(canon), os.path.relpath(os.path.abspath(__file__), ROOT)))
        if not room and rn not in known:
            guesses.append(rn)
        book = parse_xlsx(p, sheet=sheet)
        picked = pick_sheet(book)
        if not picked:
            raise SystemExit('❌ %s：没找到「渠道名称 + 指标」表头，请确认导出的是直播流量渠道明细表' % os.path.basename(p))
        sn, rows, hi, idx, ch, how_cols = picked   # ★ 不能叫 how —— 会覆盖上面 resolve_date 的日期来源
        res = analyze_room(rows, hi, idx, ch, sn, os.path.basename(p), aw=how_cols, debug=debug)
        if debug:
            print('   [debug] %s / sheet「%s」表头第 %d 行，渠道列第 %d 列，命中 %d 个字段' % (
                os.path.basename(p), sn, hi, ch + 1, len(idx)))
            for f, j in sorted(idx.items(), key=lambda kv: kv[1]):
                raw = (rows[hi][j] if (j < len(rows[hi])) else '')
                print('           %-20s ← 第 %d 列「%s」(%s)' % (f, j + 1, raw, how_cols.get(f, '?')))
        res['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        existed = rn in payload['rooms']
        payload['rooms'][rn] = res
        payload['source_files'][rn] = os.path.basename(p)
        (replaced if existed else added).append(rn)

    if not payload['rooms']:
        raise SystemExit('❌ 这一天没有任何可用的直播间数据')

    payload.update(sum_rooms(payload['rooms']))
    payload['date'] = d
    payload['demo'] = all((r.get('demo') for r in payload['rooms'].values()))
    payload['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    existed_day = os.path.exists(day_path(d))
    p = write_day(d, payload)
    if not quiet:
        print('%s%s  （日期来源：%s）  %s' % ('⚠️ 同日已有数据，按表覆盖对应直播间（其余沿用）：' if existed_day else '✔ 入库：', d, how, os.path.relpath(p, ROOT)))
        for rn in list(payload['rooms'].keys()):
            r = payload['rooms'][rn]
            t, m = r['totals'], r['metrics']
            tag = '新增' if rn in added else ('更新' if rn in replaced else '保留')
            print('   [%s] %s  源文件 %s' % (tag, rn, r.get('source_file')))
            print('          曝光 %s  观看 %s  互动 %s  涨粉 %s' % (fmt_int(t.get('impressions')), fmt_int(t.get('views')), fmt_int(t.get('interactions')), fmt_int(t.get('new_followers'))))
            print('          商品曝光 %s  点击 %s  成交 %s 单  支付 %s 元' % (fmt_int(t.get('product_impressions')), fmt_int(t.get('product_clicks')), fmt_int(t.get('paid_orders')), fmt_num(t.get('paid_amount'))))
            print('          曝光→观看 %s  互动率 %s  商品点击率 %s  点击→成交 %s  涨粉 %s' % (
                fmt_pct(m.get('exposure_view_rate')), fmt_pct(m.get('interaction_rate')), fmt_pct(m.get('product_ctr')),
                fmt_pct(m.get('click_cvr')), fmt_pct(m.get('new_follower_rate'))))
            print('          GPM %s 元  UV %s 元  客单价 %s 元  千川 ROI %s' % (
                fmt_num(m.get('gpm'), 0), fmt_num(m.get('uv_value')), fmt_num(m.get('aov'), 0), fmt_num(m.get('qianchuan_roi'))))
            if r.get('anomaly_channels'):
                print('          ⚠️ 口径异常渠道（互动÷观看 ≥ %.1f 倍，已剔除互动率合算）：%s，剔除互动数占全场 %.1f%%' % (
                    ANOM_RATIO, '、'.join(r['anomaly_channels']), r.get('excluded_share', 0) * 100))
            if r.get('suspect_channels'):
                print('          ℹ️ 需要留意（互动÷观看 ≥ %.1f 倍但未剔除）：%s' % (
                    ANOM_WARN_RATIO, '、'.join(r['suspect_channels'])))
            if r.get('row_sum_mismatch'):
                print('          ⚠️ 渠道加总与「整体」行不一致：%s' % r['row_sum_mismatch'])
        kept = [rn for rn in payload['rooms'] if rn not in added and rn not in replaced]
        if kept:
            print('   ── 本次未重灌：%s（沿用当天已有数据）' % '、'.join(kept))
        t, m = payload['totals'], payload['metrics']
        print('   ── 全店（%d 个直播间相加）' % len(payload['rooms']))
        print('      观看 %s  支付 %s 元  订单 %s 单  GPM %s 元  客单价 %s 元  ROI %s' % (
            fmt_int(t.get('views')), fmt_num(t.get('paid_amount')), fmt_int(t.get('paid_orders')),
            fmt_num(m.get('gpm'), 0), fmt_num(m.get('aov'), 0), fmt_num(m.get('qianchuan_roi'))))
    dates, ip, idx = rebuild_reports(quiet=True)
    return {'date': d, 'path': p, 'date_how': how, 'rooms': payload['rooms'], 'totals': payload['totals'],
            'metrics': payload['metrics'], 'added': added, 'replaced': replaced, 'guesses': guesses,
            'corrected': corrected,
            'n_days': len(dates), 'index': ip, 'payload': payload}


def check():
    dates = all_dates()
    print('流量入库天数：%d' % len(dates))
    if dates:
        print('  最早 %s   最新 %s' % (dates[0], dates[-1]))
    bad, note = [], []
    for d in dates:
        rec = load_day(d) or {}
        t = rec.get('totals') or {}
        if not t.get('impressions') and not t.get('views'):
            bad.append(d + ' 曝光/观看全为 0')
        if rec.get('demo'):
            bad.append(d + ' 目前只有示例数据（demo），等真实流量表')
        for rn, r in (rec.get('rooms') or {}).items():
            if not os.path.exists(report_path(d, rn)):
                bad.append('%s 缺 %s 的日报' % (d, rn))
            if r.get('row_sum_mismatch'):
                mm = r['row_sum_mismatch'] or {}
                # ★ 「只差几个涨粉」是平台自己的取整/口径差（渠道行按次去重），不算数据问题：
                #   过往每天都有一两条，一律报「问题」会让 --check 永远红着、没人看。
                tiny = (set(mm.keys()) <= {'new_followers'}
                        and all(abs(v) <= 5 for v in mm.values() if isinstance(v, (int, float))))
                (note if tiny else bad).append('%s %s 渠道加总与整体行不一致 %s' % (d, rn, mm))
        if not os.path.exists(report_path(d, ALL_SCOPE)):
            bad.append(d + ' 缺全店日报')
    if bad:
        print('⚠️ 问题（%d 条）：' % len(bad))
        for b in bad:
            print('  -', b)
        if note:
            print('ℹ️ 另有 %d 条轻微提示（涨粉 ±5 以内的平台取整差，页面也会标注）：' % len(note))
        return 1
    if note:
        print('ℹ️ 轻微提示 %d 条（涨粉 ±5 以内的平台取整差，不影响数据可用）：' % len(note))
        for n in note:
            print('  -', n)
    print('✔ 体检通过')
    return 0


def main():
    ap = argparse.ArgumentParser(description='流量分析每日入库 + 环比 + 平台规则匹配 + 日报')
    ap.add_argument('xlsx', nargs='*', help='流量 xlsx 或文件夹（一天多间传整个文件夹；多天混传也行，会按文件名日期分批入库）')
    ap.add_argument('--date', help='覆盖日期 YYYY-MM-DD')
    ap.add_argument('--room', help='直播间名（单个文件时用；文件夹模式自动从文件名认）')
    ap.add_argument('--sheet', help='指定 sheet 名')
    ap.add_argument('--force', action='store_true', help='保留位（同一直播间重复入库默认覆盖）')
    ap.add_argument('--rebuild', action='store_true', help='只重建 index.json + 全部日报')
    ap.add_argument('--check', action='store_true', help='体检，不写文件')
    ap.add_argument('--debug', action='store_true', help='打印表头匹配细节（列名是精确命中还是模糊命中）')
    a = ap.parse_args()

    if a.check:
        return check()
    if a.rebuild or not a.xlsx:
        dates, ip, idx = rebuild_reports()
        print('✔ 重建完成：%d 天，索引 %s' % (len(dates), os.path.relpath(ip, ROOT)))
        for mm in idx['months']:
            print('   %s  %d 天' % (mm['ym'], mm['count']))
        return 0

    paths = expand_inputs(a.xlsx)
    if not paths:
        raise SystemExit('❌ 没找到任何 xlsx')
    groups, rest = group_by_date(paths)
    # ★ 走单天还是分批，只看「分发日期」够不够用，不看文件夹名有没有日期：
    #   踩过的坑：一次传「10.10日流量\ 文件夹 + 下载里 10.8/10.9 的表」，
    #   旧写法用 folder_date 判断（文件夹名是 10.10 就直接走单天），结果 18 份表被并进同一天，
    #   每个直播间都被同名的 10.8 那份覆盖 → 10-10 的日文件里躺着 10.8 的数据。
    #   现在：有 --date 才强制单天；只有一天的表（且没有额外的无日期文件）走单天；
    #   其余（多天混传 / 有日期的表 + 无日期的文件夹表）一律分批，各出各的日报。
    if a.date:
        results = [ingest_one_day(paths, d=a.date, room=a.room, sheet=a.sheet, force=a.force, debug=a.debug)]
    elif len(groups) <= 1 and not (groups and rest):
        # 单天：沿用原有推定顺序（--date > 文件夹名 > 文件名 > 表内日期 > 文件修改时间）
        results = [ingest_one_day(paths, d=None, room=a.room, sheet=a.sheet, force=a.force, debug=a.debug)]
    else:
        # ★ 多天混传（例如 Downloads 里同时有 10.8 与 10.9 的表）：按文件名日期分批入库，各出各的日报
        print('📅 这批文件里有 %d 个日期，按日期分批入库：%s' % (
            len(groups), '、'.join('%s（%d 份）' % (d, len(ps)) for d, ps in groups)))
        results = [ingest_one_day(ps, d=d, d_src='文件名', room=a.room, sheet=a.sheet, force=a.force, debug=a.debug)
                   for d, ps in groups]
        if rest:
            print('ℹ️ 另有 %d 份文件名里没日期，按文件夹/修改时间推定：%s' % (
                len(rest), '、'.join(os.path.basename(x) for x in rest)))
            results.append(ingest_one_day(rest, d=None, room=a.room, sheet=a.sheet, force=a.force, debug=a.debug))
    for r in results:
        for bad, good, why in (r.get('corrected') or []):
            print('   ⚠️ 直播间名已矫正：%s → %s（%s）' % (bad, good, why))
        if r['guesses']:
            print('   ℹ️ 以下直播间名是从文件名推出来的，如果不对请用 --room 指定：%s' % '、'.join(r['guesses']))
    print('   累计 %d 天，索引已刷新' % results[-1]['n_days'])
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
主播业绩数据读取器 —— 只读解析 主播业绩/业绩demo.html 里的 ROOMS 与 DAILY_RECORDS。

本模块**纯只读**，绝不写回 HTML。写入侧是 update_daily_html.py（业绩文件流程专用）。

为什么单独一个文件，而不放进 generate_band11_target.py：
    generate_band11_target.py 在首销月（2026-10-07）结束后就停用了，
    而 业绩demo.html 是长期资产。解析器放这里，换月后的月度总结、周报都还能用。

roomId ↔ 中文直播间名 的取法（唯一真源）：
    走 业绩demo.html 自己的 ROOMS 数组（页面用 getRoomById(id) 显示名字，
    改了页面就坏，所以它不会单方面漂移），再经 team_config.classify_room() 判团队。
    ✗ 不用 update_daily_html.py:SHOP_TO_ROOM —— 只有 6 间，缺眼镜/智能设备/手环官旗
    ✗ 不用 WORKFLOW.md 的映射表 —— 那是文档，必然漂移，不该做代码的数据源
"""
import os
import re

from team_config import classify_room, OUR_TEAM

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(ROOT, '主播业绩', '业绩demo.html')

# 伪直播间：ROOMS 里有 id 有名字，但不是真实直播间（预约期口径，无主播无班次）。
# ⚠️ 必须显式排除：classify_room('手环预约期业绩') 查不到 TEAM_MAP 会**静默兜底成「良米」**，
#    不排除的话预约期业绩会被算进竞对口径，而且不报任何错。
PSEUDO_ROOM_IDS = {'room_xiaomi_band_preorder'}

SHIFT_ORDER = ['A', 'B', 'C', 'D', 'E']

_ROOM_RE = re.compile(
    r"\{\s*id:\s*'([^']+)'\s*,\s*name:\s*'([^']+)'\s*,\s*color:\s*'([^']+)'\s*\}")
_DATE_RE = re.compile(r"'(\d{4}-\d{2}-\d{2})':\s*\[")
_REC_RE = re.compile(
    r"\{\s*roomId:\s*'([^']+)'\s*,\s*shift:\s*'([^']*)'\s*,"
    r"\s*anchor:\s*'([^']*)'\s*,\s*sales:\s*(-?[\d.]+)\s*\}")

_cache = {}


class PerfParseError(RuntimeError):
    """业绩demo.html 结构不符合预期（正则少匹配 / 页面被改过）。"""


def _html():
    if 'html' not in _cache:
        with open(HTML_FILE, encoding='utf-8') as f:
            _cache['html'] = f.read()
    return _cache['html']


def _daily_records_block():
    """截出 DAILY_RECORDS 的源码文本（从 const DAILY_RECORDS 到下一个顶层声明）。"""
    if 'block' in _cache:
        return _cache['block']
    src = _html()
    i = src.find('const DAILY_RECORDS')
    if i < 0:
        raise PerfParseError(f'{HTML_FILE} 里找不到 const DAILY_RECORDS')
    j = src.find('const getRoomById', i)
    if j < 0:
        j = src.find('\n            };', i)
    if j < 0:
        raise PerfParseError('找不到 DAILY_RECORDS 的结束位置，页面结构可能被改过')
    _cache['block'] = src[i:j]
    return _cache['block']


def load_rooms():
    """ROOMS 数组 → {roomId: {'name','color'}}（含伪直播间）。"""
    if 'rooms' not in _cache:
        block = _daily_records_block()
        src = _html()
        i = src.find('const ROOMS')
        j = src.find('];', i)
        if i < 0 or j < 0:
            raise PerfParseError('找不到 ROOMS 数组')
        out = {}
        for rid, name, color in _ROOM_RE.findall(src[i:j]):
            out[rid] = {'name': name.strip(), 'color': color.strip()}
        if not out:
            raise PerfParseError('ROOMS 数组解析出 0 条，正则可能已失效')
        _cache['rooms'] = out
        _ = block
    return _cache['rooms']


def our_room_ids():
    """我司真实直播间 → {roomId: 中文名}。

    「我司」的判定走 team_config.classify_room()，与 history.json 的 our_rooms 同源。
    ⚠️ 不要用 team_config.OUR_ROOMS 判我司 —— 那是「主打手环对比模块」的显式名单，
       少了「小米智能设备旗舰店直播间」（它属我司但无 10Pro/11 销售）。
    """
    if 'our_rooms' not in _cache:
        _cache['our_rooms'] = {
            rid: info['name']
            for rid, info in load_rooms().items()
            if rid not in PSEUDO_ROOM_IDS and classify_room(info['name']) == OUR_TEAM
        }
    return _cache['our_rooms']


def load_daily_records():
    """DAILY_RECORDS → {date: [ {roomId, shift, anchor, sales} ]}。

    先按日期切块再在块内匹配，**不能对整块做一次 findall 再猜归属** ——
    否则某天缺了块头就会把记录串到隔壁日期，而且不报错。
    """
    if 'records' not in _cache:
        block = _daily_records_block()
        marks = list(_DATE_RE.finditer(block))
        if not marks:
            raise PerfParseError('DAILY_RECORDS 里解析出 0 个日期块')
        out = {}
        for k, m in enumerate(marks):
            end = marks[k + 1].start() if k + 1 < len(marks) else len(block)
            d = m.group(1)
            if d in out:
                raise PerfParseError(f'DAILY_RECORDS 出现重复日期块 {d}')
            out[d] = [
                {'roomId': rid, 'shift': sh, 'anchor': an, 'sales': float(s)}
                for rid, sh, an, s in _REC_RE.findall(block[m.end():end])
            ]
        _cache['records'] = dict(sorted(out.items()))
    return _cache['records']


def latest_perf_date(records=None):
    """业绩数据里最新的日期（YYYY-MM-DD），没有则 None。"""
    recs = records if records is not None else load_daily_records()
    return max(recs) if recs else None


def unknown_room_ids(records=None):
    """DAILY_RECORDS 里出现、但 ROOMS 数组查不到的 roomId（保险丝，应为空）。"""
    recs = records if records is not None else load_daily_records()
    known = set(load_rooms())
    seen = {r['roomId'] for blk in recs.values() for r in blk}
    return sorted(seen - known)


def daily_room_shift(records, date):
    """某天的 {roomId: {'total': 总GSV, 'shifts': [{'shift','anchor','sales'}]}}。

    shifts 按 A→E 排序（同档再按 GSV 降序）。sales 为 0 的班次**保留** ——
    那是「出勤但零成交」的真实信号，过滤掉反而丢了最有价值的交接信息。
    """
    agg = {}
    for r in records.get(date, []):
        b = agg.setdefault(r['roomId'], {'total': 0.0, 'shifts': []})
        b['total'] += r['sales']
        b['shifts'].append(
            {'shift': r['shift'], 'anchor': r['anchor'], 'sales': r['sales']})
    for b in agg.values():
        b['shifts'].sort(key=lambda s: (
            SHIFT_ORDER.index(s['shift']) if s['shift'] in SHIFT_ORDER else 99,
            -s['sales']))
    return agg


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    recs = load_daily_records()
    print(f'ROOMS        : {len(load_rooms())} 间（含伪直播间 {len(PSEUDO_ROOM_IDS)} 个）')
    print(f'我司直播间   : {len(our_room_ids())} 间 → {list(our_room_ids().values())}')
    print(f'日期块       : {len(recs)} 天（{min(recs)} ~ {max(recs)}）')
    print(f'记录总条数   : {sum(len(v) for v in recs.values())}')
    unk = unknown_room_ids(recs)
    print(f'未知 roomId  : {unk if unk else "无 ✔"}')

# -*- coding: utf-8 -*-
"""业绩表通用解析：python _artifacts/parse_perf.py <xlsx> [输出名]

规则（沿用历史口径）：
- 段头：A 列非空且 B~G 全空；含「预约期业绩」→ 预约期段，否则映射成房间块
- 常规块锚点：A 列非空且 C 列非空（shift 取 C 首字母，多段取排序后第一个）
- 锚点的 GSV = 从该锚点行到下一个锚点行之前，所有 E 列之和
- 校验：锚点行 F 值（总 GSV）用于比对；不一致的条目单独列出
- 预约期段：一行一主播（A=主播、C=场次、F 或 E = GSV），保留原始精度
- 主播名过 anchor_aliases.normalize()
"""
import io
import json
import os
import re
import sys
from collections import OrderedDict

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tools'))
sys.stdout.reconfigure(encoding='utf-8')

import openpyxl  # noqa: E402

from anchor_aliases import ALIASES, normalize  # noqa: E402

ROOM_MAP = OrderedDict([
    ('小米官方手环直播间', 'room_xiaomi_band'),
    ('小米官方手表', 'room_xiaomi_watch'),
    ('小米官方耳机直播间', 'room_xiaomi_earphone'),
    ('小米官旗手表直播间', 'room_xiaomi_watch_flagship'),
    ('小米数码旗舰店', 'room_xiaomi_digital'),
    ('小米智能设备旗舰店直播间', 'room_xiaomi_smart_device'),
    ('小米耳机直播间', 'room_xiaomi_earphone_new'),
    ('小米智能设备直播间', 'room_xiaomi_smart_device_new'),
    ('小米手环官旗直播间', 'room_xiaomi_band_flagship'),
    ('小米官方智能设备直播间', 'room_xiaomi_smart_device_official'),
])
PREORDER_MAP = OrderedDict([
    ('手环', 'room_xiaomi_band_preorder'),
    ('手表', 'room_xiaomi_watch_preorder'),
    ('耳机', 'room_xiaomi_earphone_preorder'),
    ('智能设备', 'room_xiaomi_smart_device_preorder'),
])

path = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\Administrator\Desktop\11.6日业绩.xlsx'
out_name = sys.argv[2] if len(sys.argv) > 2 else 'perf_1106_recs.json'

wb = openpyxl.load_workbook(path, data_only=True)
ws = wb.active
print('sheet:', ws.title, ' max_row=%d max_col=%d' % (ws.max_row, ws.max_column))

rows = []
for r in range(1, ws.max_row + 1):
    vals = [ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)]
    rows.append((r, vals))

# 找日期标记
date_tag = None
unknown_heads = []
for r, vals in rows:
    for v in vals:
        if isinstance(v, str) and v.startswith('日期:'):
            date_tag = v.split(':', 1)[1].strip()
print('G 列日期标记:', date_tag)

records = []
anomalies = []
preorder = []
cur_room = None
cur_id = None
cur_pre = None
anchors = []  # [(row, name, shift, f_val, e_sum)]


def flush():
    """把当前块已收集的锚点写进 records。"""
    global anchors, cur_id, cur_pre
    for idx, (r, name, shift, f_val, e_sum, e_rows) in enumerate(anchors):
        gsv = round(e_sum, 2)
        rec = OrderedDict([('roomId', cur_id), ('shift', shift), ('anchor', normalize(name)), ('sales', gsv)])
        records.append(rec)
        if f_val is not None and abs(float(f_val) - e_sum) > 0.005:
            anomalies.append({
                'anchor': name, 'row': r, 'e_sum': round(e_sum, 2),
                'f': float(f_val), 'diff': round(e_sum - float(f_val), 2),
            })
        if cur_pre:
            preorder.append(rec)
    anchors = []


for r, vals in rows:
    a = vals[0] if len(vals) > 0 else None
    b = vals[1] if len(vals) > 1 else None
    c = vals[2] if len(vals) > 2 else None
    d = vals[3] if len(vals) > 3 else None
    e = vals[4] if len(vals) > 4 else None
    f = vals[5] if len(vals) > 5 else None
    g = vals[6] if len(vals) > 6 else None
    a_s = str(a).strip() if isinstance(a, str) else a
    others_empty = all(x in (None, '') or (isinstance(x, str) and not x.strip()) for x in (b, c, d, e, f, g))

    # 段头
    if a_s and others_empty:
        flush()
        txt = str(a_s)
        m = re.match(r'^(.+?)预约期业绩$', txt)
        if m:
            room_name = m.group(1).strip()
            cur_id = PREORDER_MAP.get(room_name)
            cur_pre = True
            print('  段头(预约期): %s → %s' % (txt, cur_id))
        elif txt in ROOM_MAP:
            cur_id = ROOM_MAP[txt]
            cur_pre = False
            print('  段头: %s → %s' % (txt, cur_id))
        else:
            cur_id = None
            cur_pre = False
            if txt not in ('达人', '主播', '场次'):
                unknown_heads.append((r, txt))
                print('  ⚠ 未知段头: %r (行 %d)' % (txt, r))
        continue

    if a_s in ('达人', '主播'):
        continue

    if cur_id is None:
        continue

    if cur_pre:
        if not a_s:
            continue
        shift = str(c).strip()
        segs = re.findall(r'[A-Z]', shift.upper())
        shift = segs[0] if segs else 'B'
        gsv = f if f is not None else e
        if gsv is None:
            gsv = 0
        records.append(OrderedDict([('roomId', cur_id), ('shift', shift), ('anchor', normalize(a_s)), ('sales', float(gsv))]))
        preorder.append(records[-1])
        continue

    # 常规块：A 列出现新名字（且带场次）才算新锚点；子段（A2/B2）只在 C 列，A 为空 → 继续累加
    if a_s:
        if anchors:
            flush()
        shift = str(c).strip() if c else ''
        segs = re.findall(r'[A-Z]', shift.upper())
        shift = sorted(set(segs))[0] if segs else 'A'
        anchors.append([r, a_s, shift, f, 0.0, []])

    if anchors and e is not None:
        anchors[-1][4] += float(e)
        anchors[-1][5].append(r)

flush()

# 去重检查
seen = {}
dup = []
for rec in records:
    k = (rec['roomId'], rec['shift'], rec['anchor'])
    if k in seen:
        dup.append(k)
    seen[k] = 1

total = round(sum(rec['sales'] for rec in records), 2)
by_room = OrderedDict()
for rec in records:
    by_room.setdefault(rec['roomId'], [0, 0.0])
    by_room[rec['roomId']][0] += 1
    by_room[rec['roomId']][1] += rec['sales']

# 页面主播名
page = io.open(os.path.join('主播业绩', '业绩demo.html'), encoding='utf-8').read()
known = set(re.findall(r"anchor:\s*'([^']+)'", page))
unknown = sorted({rec['anchor'] for rec in records if rec['anchor'] not in known})

print('\n=== 记录 %d 条，合计 GSV %.2f ===' % (len(records), total))
for rec in records:
    print('   %-10s %-32s %s %12.2f' % (rec['roomId'].replace('room_xiaomi_', ''), rec['anchor'], rec['shift'], rec['sales']))
print('\n=== 分间 ===')
for k, (n, amt) in by_room.items():
    print('   %-32s %2d 条  %12.2f' % (k, n, amt))
print('\n明细≠F 条数: %d' % len(anomalies))
for x in anomalies:
    print('   ', x)
print('预约期条数: %d 合计 %.2f' % (len(preorder), round(sum(x['sales'] for x in preorder), 2)))
print('(roomId, shift, anchor) 重复:', dup or '（无）')
print('页面主播数: %d | 查无此人: %s' % (len(known), unknown or '（无）'))
print('归一命中:', {k: v for k, v in ALIASES.items() if any(rec['anchor'] == v for rec in records)})

with io.open(os.path.join('_artifacts', out_name), 'w', encoding='utf-8') as f:
    json.dump({'date_tag': date_tag, 'records': records, 'total': total,
               'anomalies': anomalies, 'unknown_anchors': unknown}, f, ensure_ascii=False, indent=1)
print('\n已写 _artifacts/%s' % out_name)

# GUARD-UNKNOWN-HEADERS: 未知段头 = 该块的数据被静默丢弃，必须失败
if unknown_heads:
    print('\n\n!!! 发现 %d 个未知段头，这些块的数据未被解析 !!!' % len(unknown_heads))
    for r, t in unknown_heads:
        print('    行 %d: %r   → 请在 ROOM_MAP / PREORDER_MAP 里补上' % (r, t))
    sys.exit(3)

# GUARD-COVERAGE: 明细合计 + 与 F 列总额交叉核对
f_total = 0.0
for r, vals in rows:
    if len(vals) < 6:
        continue
    a, c, f = vals[0], vals[2], vals[5]
    a_s = str(a).strip() if isinstance(a, str) else a
    if a_s in ('达人', '主播', '场次'):
        continue
    if f is None:
        continue
    try:
        f_total += float(f)
    except (TypeError, ValueError):
        pass
if f_total and abs(f_total - total) > 1.0:
    print('\n     F 列合计 %.2f vs 明细合计 %.2f（差 %.2f），请核对是否有块未计入' % (f_total, total, f_total - total))


import json
import os
import re
from collections import Counter, defaultdict

base = r'C:\Users\Administrator\Desktop\违规情况'
with open(os.path.join(base, 'ocr_results.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

# Parse each violation entry
def parse_violation(text_lines):
    """Extract structured info from OCR text lines."""
    info = {
        'type': '',        # 直播违规/账号违规
        'action': '',      # 预警/违规
        'time': '',        # 处置时间
        'reason': '',      # 违规原因大类
        'detail': '',      # 详细违规描述
        'location': '',    # 违规位置
        'violation_point': '', # 违规点
        'product': '',     # 违规商品
        'ticket': '',      # 违规单号
        'penalty': '',     # 处罚
        'room_id': '',     # 直播间ID
    }

    full_text = ' '.join(text_lines)

    # Extract ticket number
    m = re.search(r'违规单号[:\s]*(\d{15,25})', full_text)
    if m: info['ticket'] = m.group(1)

    # Extract type
    if '账号违规' in full_text:
        info['type'] = '账号违规'
    elif '直播违规' in full_text:
        info['type'] = '直播违规'

    # Extract action
    if '预警' in full_text:
        info['action'] = '预警'
    elif '违规' in full_text:
        info['action'] = '违规'

    # Extract time
    m = re.search(r'处置时间[:\s]*(\d{4}-\d{2}-\d{2}\s*\d{1,2}[.:]\d{1,2}[.:;]\d{1,2})', full_text)
    if m: info['time'] = m.group(1)
    # Fallback
    if not info['time']:
        m = re.search(r'执行时间[:\s]*(\d{4}-\d{2}-\d{2}\s*\d{1,2}[.:]\d{1,2}[.:;]\d{1,2})', full_text)
        if m: info['time'] = m.group(1)

    # Extract reason category
    reason_map = {
        '商品活动信息不规范': '商品活动信息不规范',
        '综合服务不符': '综合服务不符',
        '综合服务': '综合服务不符',
        '功效虚假': '功效虚假',
        '综合判定高风险': '综合判定高风险',
        '活动信息与实际': '商品活动信息不规范',
        '活动信息与实': '商品活动信息不规范',
        '服务不符': '综合服务不符',
        '功效': '功效虚假',
    }
    for kw, cat in reason_map.items():
        if kw in full_text:
            info['reason'] = cat
            break

    # Extract detail from 详细违规
    m = re.search(r'详细违规[:\s]*(.+?)(?:违规位置|$)', full_text)
    if m: info['detail'] = m.group(1)[:200]

    # Extract location
    loc_map = {
        '直播间内': '直播间内',
        '直播画面': '直播画面',
        '口播': '口播',
        '达人主页': '达人主页',
        '直播': '直播画面',
    }
    m = re.search(r'违规位置[:\s]*(\S+)', full_text)
    if m:
        loc = m.group(1)
        for kw, val in loc_map.items():
            if kw in loc:
                info['location'] = val
                break
        if not info['location']:
            info['location'] = loc[:20]

    # Extract violation point
    m = re.search(r'违规点[:\s]*["\']?(.+?)["\']?(?:违规|直播|$)', full_text)
    if m: info['violation_point'] = m.group(1)[:80]

    # Extract product
    m = re.search(r'违规商品[:\s]*(.+?)(?:\(\s*第|$)', full_text)
    if m: info['product'] = m.group(1)[:100]

    # Extract penalty
    penalty_parts = []
    if '扣除' in full_text or '扣分' in full_text:
        m = re.search(r'(扣除[^。\n]{0,30})', full_text)
        if m: penalty_parts.append(m.group(1))
    if '保证金' in full_text:
        m = re.search(r'(保证金[^。\n]{0,40})', full_text)
        if m: penalty_parts.append(m.group(1))
    if '冻结' in full_text:
        m = re.search(r'(冻结[^。\n]{0,40})', full_text)
        if m: penalty_parts.append(m.group(1))
    if '下架' in full_text or '关闭商品' in full_text:
        penalty_parts.append('关闭/下架商品')
    if '停止直播' in full_text or '中断播放' in full_text:
        penalty_parts.append('中断直播')
    if '扣5%' in full_text or '5%' in full_text:
        penalty_parts.append('扣除佣金5%')
    if '扣15%' in full_text or '15%' in full_text:
        penalty_parts.append('扣除佣金15%')
    info['penalty'] = '; '.join(penalty_parts) if penalty_parts else '警告'

    # Extract room ID
    m = re.search(r'直播间.*?ID[:\s]*(\d{15,25})', full_text)
    if m: info['room_id'] = m.group(1)

    return info

# Process all data
all_violations = []
for folder, items in data.items():
    for item in items:
        if item.get('text'):
            info = parse_violation(item['text'])
            info['folder'] = folder
            info['file'] = item['file']
            all_violations.append(info)

print("=" * 80)
print("直播间违规情况汇总分析")
print("=" * 80)

# By room
rooms = defaultdict(list)
for v in all_violations:
    rooms[v['folder']].append(v)

for room, violations in rooms.items():
    print(f"\n{'='*60}")
    print(f"【{room}】共 {len(violations)} 次违规")
    print(f"{'='*60}")

    reason_counts = Counter(v['reason'] for v in violations)
    action_counts = Counter(v['action'] for v in violations)
    loc_counts = Counter(v['location'] for v in violations)

    print(f"  处置类型: {dict(action_counts)}")
    print(f"  违规原因分布: {dict(reason_counts)}")
    print(f"  违规位置分布: {dict(loc_counts)}")

    print(f"\n  详细记录:")
    for i, v in enumerate(violations, 1):
        print(f"    {i}. [{v['action']}] {v['time'] or '未知时间'}")
        print(f"       原因: {v['reason'] or '未知'}")
        print(f"       位置: {v['location'] or '未知'}")
        if v['violation_point']:
            print(f"       违规点: {v['violation_point']}")
        if v['product']:
            print(f"       商品: {v['product']}")
        print(f"       处罚: {v['penalty']}")
        print(f"       单号: {v['ticket']}")

# Overall summary
print(f"\n\n{'='*80}")
print("总体汇总")
print(f"{'='*80}")

total = len(all_violations)
print(f"\n总违规次数: {total}")

all_reasons = Counter(v['reason'] for v in all_violations)
all_actions = Counter(v['action'] for v in all_violations)
all_locs = Counter(v['location'] for v in all_violations)

print(f"\n违规类型分布:")
for k, v in all_actions.items():
    print(f"  {k}: {v}次 ({v/total*100:.1f}%)")

print(f"\n违规原因分布:")
for k, v in all_reasons.most_common():
    print(f"  {k}: {v}次 ({v/total*100:.1f}%)")

print(f"\n违规位置分布:")
for k, v in all_locs.most_common():
    print(f"  {k}: {v}次 ({v/total*100:.1f}%)")

# Monthly trend
month_counts = Counter()
for v in all_violations:
    if v['time']:
        try:
            month = v['time'][:7]  # YYYY-MM
        except (ValueError, IndexError, TypeError, KeyError):
            month = '未知'
    else:
        month = '未知'
    month_counts[month] += 1

print(f"\n月度趋势:")
for month in sorted(month_counts.keys()):
    print(f"  {month}: {month_counts[month]}次")

# Room comparison
print(f"\n直播间违规次数对比:")
for room, violations in sorted(rooms.items(), key=lambda x: len(x[1]), reverse=True):
    reasons = Counter(v['reason'] for v in violations)
    top_reason = reasons.most_common(1)[0] if reasons else ('未知', 0)
    print(f"  {room}: {len(violations)}次 | 最多原因: {top_reason[0]}({top_reason[1]}次)")

# Save structured data for visualization
output = {
    'summary': {
        'total': total,
        'actions': dict(all_actions),
        'reasons': dict(all_reasons),
        'locations': dict(all_locs),
        'monthly': dict(sorted(month_counts.items())),
    },
    'rooms': {}
}
for room, violations in rooms.items():
    output['rooms'][room] = {
        'count': len(violations),
        'reasons': dict(Counter(v['reason'] for v in violations)),
        'actions': dict(Counter(v['action'] for v in violations)),
        'violations': [{
            'time': v['time'],
            'reason': v['reason'],
            'location': v['location'],
            'violation_point': v['violation_point'],
            'product': v['product'],
            'penalty': v['penalty'],
            'action': v['action'],
            'ticket': v['ticket'],
        } for v in violations]
    }

with open(os.path.join(base, 'analysis.json'), 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n数据已保存至 analysis.json")

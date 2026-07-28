# -*- coding: utf-8 -*-
"""Parse July OCR results and update report.html with new violation data."""
import json, os, re
from collections import Counter, defaultdict

base = r'C:\Users\Administrator\Desktop\小米手环直播间销量分析\违规情况'

# Load OCR results
ocr_path = os.path.join(base, '7月账号违规', 'ocr_results.json')
with open(ocr_path, 'r', encoding='utf-8') as f:
    ocr_data = json.load(f)

# Known tickets already in report.html (to avoid duplicates)
existing_tickets = {
    '76466358056411958309', '7643349423544205583', '7648165811143688500',
    '7649934301415331248', '7658380441224773924', '7536494293812658473',
    '7539301178585292806', '76422923203391491190', '7648496881592516883',
    '76530149197860', '7654339375326398245', '76352147209546632040',
    '7650559382040853760', '75404001323196910625', '75411094941515287305',
    '7642750111487148331', '7642974458155474226', '7642986916338123062',
    '7543509078755770086', '76440321333458865140', '7645066775767286054',
    '7542513087310921218', '7548406803645267658', '7648621291297407270',
    '7635206695983235370', '7645124267600383931', '7649336590503633802',
    '7648406303546257653', '7648521291297407270', '765545910472747432',
    '7543943557177331746', '7656231531917039318',
}

def extract_violation(text_lines):
    """Extract structured data from OCR text."""
    info = {}
    full = ' '.join(text_lines)

    # Ticket number
    m = re.search(r'违规单号[:\s]*(\d{15,25})', full)
    if m:
        info['ticket'] = m.group(1)
        if info['ticket'] in existing_tickets:
            return None  # Skip already existing

    # Time
    m = re.search(r'违规时间[:\s]*(\d{4}/\d{2}/\d{2}\s*\d{1,2}:\d{2}:\d{2})', full)
    if m:
        dt = m.group(1).replace('/', '-').replace(' ', '').split(':')[0]
        dt = dt[:10] if len(dt) > 10 else dt
        info['time'] = dt
    else:
        info['time'] = '2026-07-01'

    # Reason
    reason_patterns = [
        ('违规买赠', '违规买赠'),
        ('赠品活动信息与宣传不符', '赠品活动信息与宣传不符'),
        ('售后服务不符', '售后服务不符'),
        ('诱导互动', '诱导互动'),
        ('功效虚假', '功效虚假'),
        ('综合判定高风险', '综合判定高风险'),
    ]
    info['reason'] = '其他'
    for pattern, label in reason_patterns:
        if pattern in full:
            info['reason'] = label
            break

    # Action
    if '已撤销' in full:
        info['action'] = '已撤销'
    elif '已预警' in full or '预警' in full:
        info['action'] = '预警'
    elif '违规' in full:
        info['action'] = '违规'
    else:
        info['action'] = '预警'

    # Location
    m = re.search(r'违规位置[:\s]*(\S+)', full)
    if m:
        loc = m.group(1)
        if '口播' in loc:
            info['location'] = '直播口播'
        elif '画面' in loc:
            info['location'] = '直播画面'
        else:
            info['location'] = loc[:20]
    else:
        info['location'] = '直播口播'

    # Penalty
    penalty = '警告'
    if '已撤销' in full:
        if '申诉成功' in full:
            penalty = '警告(已撤销，申诉成功)'
        else:
            penalty = '警告(已撤销)'
    elif '申诉失败' in full:
        penalty = '警告(申诉失败)'
    elif '超时未申诉' in full:
        penalty = '警告(超时未申诉)'
    elif '冻结' in full:
        parts = []
        m = re.search(r'(冻结[^。\n]{0,40})', full)
        if m: parts.append(m.group(1))
        penalty = '; '.join(parts) if parts else '警告'
    info['penalty'] = penalty

    # Violation phrase
    m = re.search(r'违规句[:\s]*["\']?(.+?)["\']?(?:违规依据|直播时间|$)', full)
    if m:
        phrase = m.group(1).strip().strip('"').strip("'")
        info['phrase'] = phrase[:80] if phrase else '-'
    else:
        info['phrase'] = '-'

    # Product
    product_match = re.search(r'(?:小米手环|REDMI|Xiaomi|小米)[^\s，。]*', full)
    if product_match:
        info['product'] = product_match.group(0)[:50]
    elif 'Buds' in full:
        m = re.search(r'(.*?Buds[^)]*)', full)
        if m: info['product'] = m.group(1)[:50]
        else: info['product'] = '-'
    elif 'Watch' in full:
        m = re.search(r'(REDMI\s*Watch[^)]*)', full)
        if m: info['product'] = m.group(1)[:50]
        else: info['product'] = '-'
    else:
        info['product'] = '-'

    info['isNew'] = True
    info['isJuly'] = True

    return info

# Process all OCR data
new_violations = defaultdict(list)
total_new = 0
skipped = 0

for room, items in ocr_data.items():
    for item in items:
        if item.get('text') and not item.get('error'):
            text = item['text']
            # Check if it looks like a violation detail page
            if any('违规' in t and '详情' in t for t in text[:2]):
                info = extract_violation(text)
                if info:
                    new_violations[room].append(info)
                    total_new += 1
                    print(f"NEW: {room} | {info['time']} | {info['reason']} | {info['action']} | {info['ticket']}")
                else:
                    skipped += 1
                    print(f"SKIP (duplicate): {room} | {item['file']}")

print(f"\n{'='*60}")
print(f"Total new violations: {total_new}")
print(f"Skipped (duplicates): {skipped}")
print(f"By room:")
for room, items in new_violations.items():
    print(f"  {room}: {len(items)}")

# Save parsed data
parsed_path = os.path.join(base, 'july_parsed.json')
with open(parsed_path, 'w', encoding='utf-8') as f:
    json.dump(dict(new_violations), f, ensure_ascii=False, indent=2)
print(f"\nParsed data saved to: {parsed_path}")

# Summary statistics
all_new = []
for room, items in new_violations.items():
    for v in items:
        v['room'] = room
        all_new.append(v)

print(f"\n=== JULY SUMMARY ===")
print(f"Total new: {total_new}")
reason_counts = Counter(v['reason'] for v in all_new)
action_counts = Counter(v['action'] for v in all_new)
print(f"Reasons: {dict(reason_counts)}")
print(f"Actions: {dict(action_counts)}")

# Count effective (non-revoked)
effective = sum(1 for v in all_new if v['action'] != '已撤销')
print(f"Effective (non-revoked): {effective}")
revoked = sum(1 for v in all_new if v['action'] == '已撤销')
print(f"Revoked (申诉成功): {revoked}")

# Appeal stats
appeal_fail = sum(1 for v in all_new if '申诉失败' in v.get('penalty', ''))
appeal_timeout = sum(1 for v in all_new if '超时未申诉' in v.get('penalty', ''))
appeal_success = sum(1 for v in all_new if '申诉成功' in v.get('penalty', ''))
print(f"申诉失败: {appeal_fail}, 超时未申诉: {appeal_timeout}, 申诉成功: {appeal_success}")

print("\nDone!")

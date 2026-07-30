"""
Daily HTML updater for 业绩demo.html
Usage: python update_daily_html.py <excel_path> [date_override]
Example:
  python update_daily_html.py "C:/Users/Administrator/Desktop/7.30日订单.xlsx"
  python update_daily_html.py "C:/Users/Administrator/Desktop/7.30日订单.xlsx" 2026-07-30

Updates both DAILY_RECORDS (anchor-level GSV) and BAND10PRO_DAILY (10Pro comparison)
in the 业绩demo.html file.
"""
import pandas as pd
import re
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from team_config import TEAM_MAP

HTML_FILE = ROOT / '业绩demo.html'

SHOP_TO_ROOM = {
    '小米数码旗舰店': 'room_xiaomi_digital',
    '小米官方手环直播间': 'room_xiaomi_band',
    '小米官方手表': 'room_xiaomi_watch',
    '小米官旗手表直播间': 'room_xiaomi_watch_flagship',
    '小米官方耳机直播间': 'room_xiaomi_earphone',
}

ANCHOR_MAP = {
    'room_xiaomi_digital': {0: '宋紫茹', 1: '张蓬元', 2: '秦雨琪', 3: '申琰', 4: '付慧娴'},
    'room_xiaomi_band': {0: '周亚锦', 1: '朱弘颖', 2: '欧阳硕果', 3: '周家会', 4: '梁思雅'},
    'room_xiaomi_watch': {0: '郭孟航', 1: '王嘉琦', 2: '高智敏', 3: '高珊珊', 4: '牛萌萌'},
    'room_xiaomi_watch_flagship': {0: '刘卓凡', 1: '刘垚', 2: '马琪', 3: '李牧遥', 4: '未知'},
    'room_xiaomi_earphone': {0: '范金蝶', 1: '刘子源', 2: '李晓洋', 3: '王瑞', 4: '陈依雨'},
}


def get_shift(hour):
    if hour < 6: return 0
    elif hour < 12: return 1
    elif hour < 18: return 2
    elif hour < 21: return 3
    else: return 4


def process_excel(filepath):
    df = pd.read_excel(filepath)
    df.columns = ['product', 'time', 'status', 'amount', 'shop']
    df['time'] = pd.to_datetime(df['time'].astype(str).str.replace('\t', '', regex=False))
    df['hour'] = df['time'].dt.hour
    paid = df[df['status'] == '已发货'].copy()
    return paid


def generate_daily_records(paid, date_str):
    """Generate DAILY_RECORDS entries for our 5 rooms."""
    our = paid[paid['shop'].isin(list(SHOP_TO_ROOM.keys()))].copy()
    our['roomId'] = our['shop'].map(SHOP_TO_ROOM)
    our['shift_idx'] = our['hour'].apply(get_shift)

    lines = [f"                '{date_str}': ["]
    for room_id in ['room_xiaomi_digital', 'room_xiaomi_band', 'room_xiaomi_watch',
                     'room_xiaomi_watch_flagship', 'room_xiaomi_earphone']:
        sub = our[our['roomId'] == room_id]
        anchors = ANCHOR_MAP[room_id]
        shifts_found = set()
        for si in sorted(sub['shift_idx'].unique()):
            amt = round(float(sub[sub['shift_idx'] == si]['amount'].sum()), 2)
            if amt == 0:
                continue
            anchor = anchors.get(si, '未知')
            lines.append(f"                    {{ roomId: '{room_id}', shift: '{chr(65+si)}', anchor: '{anchor}', sales: {amt:.2f} }},")
            shifts_found.add(si)
        # Add zero-sales entries for missing shifts with anchor names
    lines.append(f"                ],")
    return '\n'.join(lines)


def generate_10pro_data(paid, date_str):
    """Generate BAND10PRO_DAILY entry for 10Pro comparison."""
    b10p = paid[paid['product'].str.contains('10Pro|10 Pro', na=False)].copy()
    b10p['team'] = b10p['shop'].apply(lambda x: TEAM_MAP.get(str(x).strip(), '良米'))

    result = {}
    for team in ['我司', '良米']:
        t = b10p[b10p['team'] == team]
        live = t[~t['shop'].str.contains('商品卡', na=False)]
        card = t[t['shop'].str.contains('商品卡', na=False)]
        result[team] = {
            'live_o': int(len(live)), 'live_a': round(float(live['amount'].sum()), 2),
            'card_o': int(len(card)), 'card_a': round(float(card['amount'].sum()), 2),
        }

    our = result['我司']
    lm = result['良米']
    return f"                '{date_str}': {{ our: {{live_o:{our['live_o']},live_a:{our['live_a']:.2f},card_o:{our['card_o']},card_a:{our['card_a']:.2f}}}, lm: {{live_o:{lm['live_o']},live_a:{lm['live_a']:.2f},card_o:{lm['card_o']},card_a:{lm['card_a']:.2f}}} }},"


def update_html(date_str, daily_records_entry, b10pro_entry):
    """Update the HTML file with new data entries."""
    content = HTML_FILE.read_text(encoding='utf-8')

    # Check if date already exists
    if f"'{date_str}':" in content:
        print(f"WARNING: {date_str} already exists in the HTML. Skipping to avoid duplicates.")
        print("Delete the existing entry first if you want to overwrite.")
        return False

    # Insert DAILY_RECORDS entry before the closing comment
    marker = '                // 按日期添加新数据，格式同上'
    if marker in content:
        content = content.replace(marker, daily_records_entry + '\n' + marker)
    else:
        print("ERROR: Could not find DAILY_RECORDS insertion point")
        return False

    # Insert BAND10PRO_DAILY entry before the closing of the object
    b10p_marker = '            const getB10ProDates = () => Object.keys(BAND10PRO_DAILY).sort();'
    if b10p_marker in content:
        content = content.replace(b10p_marker, b10pro_entry + '\n' + b10p_marker)
    else:
        print("ERROR: Could not find BAND10PRO_DAILY insertion point")
        return False

    HTML_FILE.write_text(content, encoding='utf-8')
    print(f"Successfully added {date_str} data to 业绩demo.html")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    excel_path = sys.argv[1]
    if not os.path.exists(excel_path):
        print(f"ERROR: File not found: {excel_path}")
        sys.exit(1)

    paid = process_excel(excel_path)

    # Determine date from filename or override
    if len(sys.argv) > 2:
        date_str = sys.argv[2]
    else:
        basename = os.path.basename(excel_path)
        m = re.match(r'(\d+)\.(\d+)日订单', basename)
        if m:
            date_str = f'2026-{int(m.group(1)):02d}-{int(m.group(2)):02d}'
        else:
            print("ERROR: Cannot determine date from filename. Use date override.")
            sys.exit(1)

    print(f"Processing: {excel_path}")
    print(f"Date: {date_str}")
    print()

    total_gsv = paid[paid['shop'].isin(list(SHOP_TO_ROOM.keys()))]['amount'].sum()
    print(f"Our 5 rooms total GSV: {total_gsv:,.2f} yuan")

    # 10Pro summary
    b10p = paid[paid['product'].str.contains('10Pro|10 Pro', na=False)]
    b10p['team'] = b10p['shop'].apply(lambda x: TEAM_MAP.get(str(x).strip(), '良米'))
    for t in ['我司', '良米']:
        sub = b10p[b10p['team'] == t]
        live = sub[~sub['shop'].str.contains('商品卡', na=False)]
        card = sub[sub['shop'].str.contains('商品卡', na=False)]
        print(f"  {t}: 直播={len(live)}单/{live['amount'].sum():,.0f}元, 商品卡={len(card)}单/{card['amount'].sum():,.0f}元")

    print()
    daily_entry = generate_daily_records(paid, date_str)
    b10pro_entry = generate_10pro_data(paid, date_str)

    print("=== DAILY_RECORDS entry ===")
    print(daily_entry)
    print()
    print("=== BAND10PRO_DAILY entry ===")
    print(b10pro_entry)
    print()

    ok = update_html(date_str, daily_entry, b10pro_entry)
    if ok:
        print("Done! HTML updated. Remember to refresh browser.")
    else:
        print("HTML update failed. Copy the entries above manually.")


if __name__ == '__main__':
    main()

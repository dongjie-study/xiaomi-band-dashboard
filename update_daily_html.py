"""
Daily HTML updater for 业绩demo.html — DAILY_RECORDS only
Usage: python update_daily_html.py <excel_path> [date_override]
Example:
  python update_daily_html.py "C:/Users/Administrator/Desktop/7.31日订单.xlsx"

Note: 10Pro data is now automatically handled by sales_analysis/daily_update.py
"""
import pandas as pd
import re
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

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
    return df[df['status'] == '已发货'].copy()


def generate_daily_records(paid, date_str):
    our = paid[paid['shop'].isin(list(SHOP_TO_ROOM.keys()))].copy()
    our['roomId'] = our['shop'].map(SHOP_TO_ROOM)
    our['shift_idx'] = our['hour'].apply(get_shift)

    lines = [f"                '{date_str}': ["]
    for room_id in ['room_xiaomi_digital', 'room_xiaomi_band', 'room_xiaomi_watch',
                     'room_xiaomi_watch_flagship', 'room_xiaomi_earphone']:
        sub = our[our['roomId'] == room_id]
        anchors = ANCHOR_MAP[room_id]
        for si in sorted(sub['shift_idx'].unique()):
            amt = round(float(sub[sub['shift_idx'] == si]['amount'].sum()), 2)
            if amt == 0:
                continue
            anchor = anchors.get(si, '未知')
            lines.append(f"                    {{ roomId: '{room_id}', shift: '{chr(65+si)}', anchor: '{anchor}', sales: {amt:.2f} }},")
    lines.append(f"                ],")
    return '\n'.join(lines)


def update_html(date_str, daily_records_entry):
    content = HTML_FILE.read_text(encoding='utf-8')
    if f"'{date_str}':" in content:
        print(f"WARNING: {date_str} already exists. Delete it first to overwrite.")
        return False
    marker = '                // 按日期添加新数据，格式同上'
    if marker in content:
        content = content.replace(marker, daily_records_entry + '\n' + marker)
    else:
        print("ERROR: Could not find insertion point")
        return False
    HTML_FILE.write_text(content, encoding='utf-8')
    print(f"Added {date_str} to 业绩demo.html")
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

    print(f"Processing: {excel_path} -> {date_str}")
    total_gsv = paid[paid['shop'].isin(list(SHOP_TO_ROOM.keys()))]['amount'].sum()
    print(f"Our 5 rooms GSV: {total_gsv:,.2f} yuan")

    entry = generate_daily_records(paid, date_str)
    print("\n=== DAILY_RECORDS entry ===")
    print(entry)

    ok = update_html(date_str, entry)
    if ok:
        print("\nDone! Run 'python run_all.py sales <excel>' to update the sales dashboard.")
    else:
        print("\nHTML update failed. Copy the entry above manually.")


if __name__ == '__main__':
    main()

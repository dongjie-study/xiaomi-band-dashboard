import pandas as pd
import sys
import re
import json

sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_excel(r'C:\Users\Administrator\Desktop\618我司订单.xlsx')
df['订单提交时间'] = df['订单提交时间'].astype(str).str.strip()
df['订单提交时间'] = pd.to_datetime(df['订单提交时间'], errors='coerce')

def extract_product(name):
    name = re.sub(r'^【[^】]*】', '', str(name))
    name = re.sub(r'-[^-]+-\(\d+\)$', '', name)
    return name.strip()

df['商品名称'] = df['选购商品'].apply(extract_product)

def categorize(name):
    n = name.lower()
    if '手环10pro' in n or '手环10 pro' in n or '手环10Pro' in name:
        return '手环10 Pro'
    elif '手环10' in n:
        return '手环10'
    elif '手环9 pro' in n or '手环9Pro' in n:
        return '手环9 Pro'
    elif '手环' in n:
        return '手环系列'
    elif 'watch s5' in n or 'watch 5' in n:
        return 'Watch S5/5'
    elif 'watch s4' in n:
        return 'Watch S4'
    elif 'redmi watch' in n:
        return 'REDMI Watch 6'
    elif 'ai眼镜' in n:
        return 'AI眼镜'
    elif '眼镜' in n:
        return '眼镜'
    elif 'buds 5 pro' in n or 'buds5pro' in n:
        return 'Buds 5 Pro'
    elif 'buds 6' in n:
        return 'Buds 6'
    elif 'buds 8 pro' in n or 'buds8pro' in n:
        return 'Buds 8 Pro'
    elif 'buds 8' in n:
        return 'Buds 8'
    elif 'buds 7s' in n or 'buds7s' in n:
        return 'Buds 7S'
    elif 'buds' in n or '耳机' in n or '耳夹' in n or '骨传导' in n:
        return '其他耳机'
    elif '儿童' in n or '米兔' in n:
        return '儿童手表'
    elif '充电' in n:
        return '充电配件'
    elif '背包' in n:
        return '背包'
    elif 'tag' in n:
        return '定位器'
    elif '表带' in n or '腕带' in n:
        return '表带配件'
    elif '温湿度' in n:
        return '温湿度计'
    elif '偏光' in n or '太阳镜' in n:
        return '太阳镜'
    else:
        return '其他'

df['品类'] = df['商品名称'].apply(categorize)
df['渠道类型'] = df['达人昵称'].apply(lambda x: '商品卡' if x == '我司商品卡' else '直播间')

total_gmv = df['订单应付金额'].sum()
total_orders = len(df)
date_min = df['订单提交时间'].min().strftime('%m/%d')
date_max = df['订单提交时间'].max().strftime('%m/%d')

# ===== 1. Overall category =====
cat_all = df.groupby('品类').agg(订单数=('订单应付金额','count'), GSV=('订单应付金额','sum')).sort_values('GSV', ascending=False).reset_index()
cat_all['占比'] = (cat_all['GSV'] / total_gmv * 100).round(1)
cat_all['客单价'] = (cat_all['GSV'] / cat_all['订单数']).round(0)

# ===== 2. Channel type =====
ch_type = df.groupby('渠道类型').agg(订单数=('订单应付金额','count'), GSV=('订单应付金额','sum')).sort_values('GSV', ascending=False).reset_index()
ch_type['占比'] = (ch_type['GSV'] / total_gmv * 100).round(1)

# ===== 3. Live rooms list =====
live_rooms = df[df['渠道类型']=='直播间'].groupby('达人昵称').agg(订单数=('订单应付金额','count'), GSV=('订单应付金额','sum')).sort_values('GSV', ascending=False).reset_index()
live_rooms['占总GSV'] = (live_rooms['GSV'] / total_gmv * 100).round(1)
live_rooms['客单价'] = (live_rooms['GSV'] / live_rooms['订单数']).round(0)

# ===== 4. Each live room x product =====
room_product = df[df['渠道类型']=='直播间'].groupby(['达人昵称','品类']).agg(订单数=('订单应付金额','count'), GSV=('订单应付金额','sum')).reset_index()

# Add share within each room
room_product['直播间占比'] = 0.0
for room in live_rooms['达人昵称']:
    mask = room_product['达人昵称'] == room
    room_total = room_product.loc[mask, 'GSV'].sum()
    room_product.loc[mask, '直播间占比'] = (room_product.loc[mask, 'GSV'] / room_total * 100).round(1)

room_product = room_product.sort_values(['达人昵称','GSV'], ascending=[True, False])

# Build structured data per room
room_detail = {}
for room in live_rooms['达人昵称']:
    items = room_product[room_product['达人昵称'] == room]
    room_detail[room] = items[['品类','订单数','GSV','直播间占比']].to_dict('records')

# ===== 5. Product card x product =====
card_product = df[df['渠道类型']=='商品卡'].groupby('品类').agg(订单数=('订单应付金额','count'), GSV=('订单应付金额','sum')).sort_values('GSV', ascending=False).reset_index()
card_total = card_product['GSV'].sum()
card_product['商品卡占比'] = (card_product['GSV'] / card_total * 100).round(1)
card_product['客单价'] = (card_product['GSV'] / card_product['订单数']).round(0)

# ===== Output =====
data = {
    'total_gmv': float(total_gmv),
    'total_orders': int(total_orders),
    'date_range': f"{date_min}-{date_max}",
    'cat_all': cat_all.to_dict('records'),
    'ch_type': ch_type.to_dict('records'),
    'live_rooms': live_rooms.to_dict('records'),
    'room_detail': room_detail,
    'card_product': card_product.to_dict('records'),
}

with open(r'C:\Users\Administrator\Desktop\小米手环直播间销量分析\618_report_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)

print(f"总GSV: {total_gmv:,.0f}元 | 总订单: {total_orders:,}单")
print(f"\n渠道: 直播间 {ch_type[ch_type['渠道类型']=='直播间']['占比'].values[0]}% | 商品卡 {ch_type[ch_type['渠道类型']=='商品卡']['占比'].values[0]}%")
print("\n直播间:")
for _, r in live_rooms.iterrows():
    print(f"  {r['达人昵称']}: {r['GSV']:,.0f}元 ({r['占总GSV']}%)")
print("\nJSON saved.")

import pandas as pd
import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ========== CONFIG ==========
TEAM_MAPPING = {
    # 我方直播间
    '小米数码旗舰店': '我方', '小米官方手表': '我方', '小米官方手环直播间': '我方',
    '小米官方耳机直播间': '我方', '小米手环10Pro直播间': '我方', '小米官旗手表直播间': '我方',
    # 良米直播间（其他所有未明确分配的直播间默认归良米）
    '小米手环': '良米', '小米手表官方直播间': '良米', '小米手表': '良米',
    '小米耳机官方直播间': '良米', '小米手表官旗直播间': '良米', '小米手表直播间': '良米',
    '小米数码智能旗舰店': '良米', '小米智能手表旗舰店': '良米',
    # 机械空间
    '小米智能穿戴国补号': '机械空间', '小米智能穿戴授权号': '机械空间',
    # 综训
    '小米官方手表直播号': '综训',
    # 商品卡
    '我司商品卡': '我方', '良米商品卡': '良米',
}

def classify_product(name):
    name = str(name)
    if '10Pro' in name or '10 Pro' in name:
        return '小米手环10 Pro'
    if '10 陶瓷' in name or '10陶瓷' in name or '陶瓷白' in name:
        return '小米手环10'
    if '10系' in name or '10 标准' in name:
        return '小米手环10'
    if '手环10' in name and 'Pro' not in name:
        return '小米手环10'
    if '9 Pro' in name:
        return '小米手环9 Pro'
    if 'REDMI Watch 6' in name:
        return 'REDMI Watch 6'
    if '开放式耳机' in name or '耳夹式耳机' in name:
        return 'Xiaomi 开放式耳机'
    if 'Buds 8 Pro' in name:
        return 'REDMI Buds 8 Pro'
    if 'Buds 8 青春' in name:
        return 'REDMI Buds 8 青春版'
    if 'Buds 8 活力' in name:
        return 'REDMI Buds 8 活力版'
    if 'Buds 8' in name:
        return 'REDMI Buds 8'
    if '手表 S' in name or 'Watch S' in name:
        return '小米手表 S系列'
    if '骨传导' in name:
        return '小米骨传导耳机'
    if '耳机' in name or 'Buds' in name:
        return '其他耳机'
    if '手环' in name:
        return '其他手环'
    if '手表' in name or 'Watch' in name:
        return '其他手表'
    return '其他品类'

# Load
df = pd.read_excel(r'C:\Users\Administrator\Desktop\6.15-6.18日我司跟良米穿戴直播间+商品卡订单..xlsx')
cols = df.columns.tolist()
col_product, col_time, col_amount, col_nick = cols[0], cols[1], cols[2], cols[3]

df['date'] = pd.to_datetime(df[col_time]).dt.date
df['team'] = df[col_nick].map(TEAM_MAPPING).fillna('未分类')
df['channel'] = df[col_nick].apply(lambda x: '商品卡' if '商品卡' in str(x) else '直播间')
df['product_cat'] = df[col_product].apply(classify_product)

# Full 618 period: 5/15-6/18
mask = (df['date'] >= pd.Timestamp('2026-05-15').date()) & (df['date'] <= pd.Timestamp('2026-06-18').date())
df = df[mask].copy()

result = {}

# === OVERALL KPIs ===
total_orders = len(df)
total_gsv = df[col_amount].sum()
result['total_orders'] = int(total_orders)
result['total_gsv_wan'] = round(total_gsv / 10000, 1)
result['total_gsv'] = round(total_gsv, 2)
result['period_start'] = '2026-05-15'
result['period_end'] = '2026-06-18'
result['total_days'] = 35

# Channel breakdown
live_df = df[df['channel'] == '直播间']
card_df = df[df['channel'] == '商品卡']
result['live_orders'] = int(len(live_df))
result['live_gsv_wan'] = round(live_df[col_amount].sum() / 10000, 1)
result['card_orders'] = int(len(card_df))
result['card_gsv_wan'] = round(card_df[col_amount].sum() / 10000, 1)

# === TEAM SUMMARY ===
teams_order = ['我方', '良米', '机械空间', '综训']
teams = {}
for team in teams_order:
    tdf = df[df['team'] == team]
    n_orders = int(len(tdf))
    teams[team] = {
        'orders': n_orders,
        'gsv': round(tdf[col_amount].sum(), 2),
        'gsv_wan': round(tdf[col_amount].sum() / 10000, 1),
        'pct': round(n_orders / total_orders * 100, 1),
    }
    # Channel breakdown per team
    for ch in ['直播间', '商品卡']:
        chtdf = tdf[tdf['channel'] == ch]
        teams[team][f'{ch}_orders'] = int(len(chtdf))
        teams[team][f'{ch}_gsv_wan'] = round(chtdf[col_amount].sum() / 10000, 1)
    # Room count (only for livestream)
    if team in ['我方', '良米', '机械空间', '综训']:
        live_team = live_df[live_df['team'] == team]
        teams[team]['rooms'] = int(live_team[col_nick].nunique())
        teams[team]['avg_per_room'] = int(len(live_team) / live_team[col_nick].nunique()) if live_team[col_nick].nunique() > 0 else 0

result['teams'] = teams

# === DAILY TREND (full including 商品卡) ===
ddf_full = df.groupby('date').agg(orders=(col_amount, 'count'), gsv=(col_amount, 'sum'))
daily_dates = sorted(df['date'].unique())
result['dates'] = [str(d) for d in daily_dates]
result['dates_mmdd'] = [f"{d.month}/{d.day}" for d in daily_dates]

for team in teams_order:
    result[f'daily_{team}_orders'] = []
    result[f'daily_{team}_gsv_wan'] = []

result['daily_total'] = []
result['daily_live_orders'] = []
result['daily_card_orders'] = []

for date in daily_dates:
    ddf = df[df['date'] == date]
    result['daily_total'].append(int(len(ddf)))
    result['daily_live_orders'].append(int(len(ddf[ddf['channel'] == '直播间'])))
    result['daily_card_orders'].append(int(len(ddf[ddf['channel'] == '商品卡'])))
    for team in teams_order:
        tdf = ddf[ddf['team'] == team]
        result[f'daily_{team}_orders'].append(int(len(tdf)))
        result[f'daily_{team}_gsv_wan'].append(round(tdf[col_amount].sum() / 10000, 1))

# === PRODUCTS BY CHANNEL ===
# All products
all_prods = df.groupby('product_cat').agg(
    orders=(col_amount, 'count'),
    gsv=(col_amount, 'sum')
).sort_values('orders', ascending=False)

# By channel: 直播间
live_prods = live_df.groupby('product_cat').agg(
    orders=(col_amount, 'count'),
    gsv=(col_amount, 'sum')
).sort_values('orders', ascending=False)

# By channel: 商品卡
card_prods = card_df.groupby('product_cat').agg(
    orders=(col_amount, 'count'),
    gsv=(col_amount, 'sum')
).sort_values('orders', ascending=False)

# Products by team (all channels)
our_df = df[df['team'] == '我方']
comp_df = df[df['team'] != '我方']

our_prod = our_df.groupby('product_cat').agg(
    orders=(col_amount, 'count'),
    gsv=(col_amount, 'sum')
).sort_values('orders', ascending=False)

comp_prod = comp_df.groupby('product_cat').agg(
    orders=(col_amount, 'count'),
    gsv=(col_amount, 'sum')
).sort_values('orders', ascending=False)

# By channel x team
our_live_prod = df[(df['team'] == '我方') & (df['channel'] == '直播间')].groupby('product_cat').agg(
    orders=(col_amount, 'count'), gsv=(col_amount, 'sum')).sort_values('orders', ascending=False)
our_card_prod = df[(df['team'] == '我方') & (df['channel'] == '商品卡')].groupby('product_cat').agg(
    orders=(col_amount, 'count'), gsv=(col_amount, 'sum')).sort_values('orders', ascending=False)
comp_live_prod = df[(df['team'] != '我方') & (df['channel'] == '直播间')].groupby('product_cat').agg(
    orders=(col_amount, 'count'), gsv=(col_amount, 'sum')).sort_values('orders', ascending=False)
comp_card_prod = df[(df['team'] != '我方') & (df['channel'] == '商品卡')].groupby('product_cat').agg(
    orders=(col_amount, 'count'), gsv=(col_amount, 'sum')).sort_values('orders', ascending=False)

# Save channel-level product data
result['all_products'] = {k: {'orders': int(v['orders']), 'gsv': round(v['gsv'], 2)}
                          for k, v in all_prods.iterrows()}
result['live_products'] = {k: {'orders': int(v['orders']), 'gsv': round(v['gsv'], 2)}
                           for k, v in live_prods.iterrows()}
result['card_products'] = {k: {'orders': int(v['orders']), 'gsv': round(v['gsv'], 2)}
                           for k, v in card_prods.iterrows()}
result['our_products'] = {k: {'orders': int(v['orders']), 'gsv': round(v['gsv'], 2)}
                          for k, v in our_prod.iterrows()}
result['competitor_products'] = {k: {'orders': int(v['orders']), 'gsv': round(v['gsv'], 2)}
                                 for k, v in comp_prod.iterrows()}

# Channel-specific products
result['our_live_products'] = {k: {'orders': int(v['orders']), 'gsv': round(v['gsv'], 2)}
                               for k, v in our_live_prod.iterrows()}
result['our_card_products'] = {k: {'orders': int(v['orders']), 'gsv': round(v['gsv'], 2)}
                               for k, v in our_card_prod.iterrows()}
result['comp_live_products'] = {k: {'orders': int(v['orders']), 'gsv': round(v['gsv'], 2)}
                                for k, v in comp_live_prod.iterrows()}
result['comp_card_products'] = {k: {'orders': int(v['orders']), 'gsv': round(v['gsv'], 2)}
                                for k, v in comp_card_prod.iterrows()}

# === KEY PRODUCT COMPARISONS (all channels) ===
key_products = ['小米手环10', 'REDMI Watch 6', '小米手环10 Pro', '小米手环9 Pro',
                '小米手表 S系列', 'Xiaomi 开放式耳机',
                'REDMI Buds 8 Pro', 'REDMI Buds 8', 'REDMI Buds 8 活力版', 'REDMI Buds 8 青春版']

for prod in key_products:
    total_p = all_prods.loc[prod, 'orders'] if prod in all_prods.index else 0
    total_p_gsv = all_prods.loc[prod, 'gsv'] if prod in all_prods.index else 0
    our_p = our_prod.loc[prod, 'orders'] if prod in our_prod.index else 0
    our_p_gsv = our_prod.loc[prod, 'gsv'] if prod in our_prod.index else 0
    comp_p = comp_prod.loc[prod, 'orders'] if prod in comp_prod.index else 0
    comp_p_gsv = comp_prod.loc[prod, 'gsv'] if prod in comp_prod.index else 0
    share = round(our_p / total_p * 100, 1) if total_p > 0 else 0
    diff = our_p - comp_p

    # Channel breakdown for this product
    live_p = live_prods.loc[prod, 'orders'] if prod in live_prods.index else 0
    card_p = card_prods.loc[prod, 'orders'] if prod in card_prods.index else 0
    live_p_gsv = live_prods.loc[prod, 'gsv'] if prod in live_prods.index else 0
    card_p_gsv = card_prods.loc[prod, 'gsv'] if prod in card_prods.index else 0
    our_live_p = our_live_prod.loc[prod, 'orders'] if prod in our_live_prod.index else 0
    our_live_gsv = our_live_prod.loc[prod, 'gsv'] if prod in our_live_prod.index else 0
    our_card_p = our_card_prod.loc[prod, 'orders'] if prod in our_card_prod.index else 0
    our_card_gsv = our_card_prod.loc[prod, 'gsv'] if prod in our_card_prod.index else 0
    comp_live_p = comp_live_prod.loc[prod, 'orders'] if prod in comp_live_prod.index else 0
    comp_live_gsv = comp_live_prod.loc[prod, 'gsv'] if prod in comp_live_prod.index else 0
    comp_card_p = comp_card_prod.loc[prod, 'orders'] if prod in comp_card_prod.index else 0
    comp_card_gsv = comp_card_prod.loc[prod, 'gsv'] if prod in comp_card_prod.index else 0

    result[f'prod_{prod}'] = {
        'total': int(total_p), 'total_gsv': round(total_p_gsv, 2),
        'our': int(our_p), 'our_gsv': round(our_p_gsv, 2),
        'comp': int(comp_p), 'comp_gsv': round(comp_p_gsv, 2),
        'share': share, 'diff': int(diff),
        'live_total': int(live_p), 'live_total_gsv': round(live_p_gsv, 2),
        'card_total': int(card_p), 'card_total_gsv': round(card_p_gsv, 2),
        'our_live': int(our_live_p), 'our_live_gsv': round(our_live_gsv, 2),
        'our_card': int(our_card_p), 'our_card_gsv': round(our_card_gsv, 2),
        'comp_live': int(comp_live_p), 'comp_live_gsv': round(comp_live_gsv, 2),
        'comp_card': int(comp_card_p), 'comp_card_gsv': round(comp_card_gsv, 2),
    }

# === LIVE ROOM RANKING (6/18) ===
date_618 = pd.Timestamp('2026-06-18').date()
df_618 = df[df['date'] == date_618]
live_618 = df_618[df_618['channel'] == '直播间']
room_618 = live_618.groupby(col_nick).agg(
    orders=(col_amount, 'count'),
    gsv=(col_amount, 'sum')
).sort_values('orders', ascending=False)

result['rooms_618'] = []
for store, row in room_618.iterrows():
    team = TEAM_MAPPING.get(store, '未分类')
    result['rooms_618'].append({
        'name': store, 'team': team,
        'orders': int(row['orders']), 'gsv': round(row['gsv'], 2),
        'gsv_fmt': f"¥{row['gsv']:,.0f}"
    })

# === INSIGHT DATA ===
june1 = pd.Timestamp('2026-06-01').date()
june18 = date_618
june9 = pd.Timestamp('2026-06-09').date()
june17 = pd.Timestamp('2026-06-17').date()

df_june1 = df[df['date'] == june1]
df_june18 = df[df['date'] == june18]
df_june9 = df[df['date'] == june9]
df_june17 = df[df['date'] == june17]

our_61 = int(len(df_june1[df_june1['team'] == '我方']))
our_618 = int(len(df_june18[df_june18['team'] == '我方']))
our_69 = int(len(df_june9[df_june9['team'] == '我方']))
our_617 = int(len(df_june17[df_june17['team'] == '我方']))
comp_617 = int(len(df_june17[df_june17['team'] != '我方']))
comp_618 = int(len(df_june18[df_june18['team'] != '我方']))
total_618_day = int(len(df_june18))

result['insight'] = {
    'our_618': our_618, 'total_618_day': total_618_day,
    'our_618_pct': round(our_618 / total_618_day * 100, 1) if total_618_day > 0 else 0,
    'our_61': our_61, 'our_61_pct': round(our_61 / len(df_june1) * 100, 1) if len(df_june1) > 0 else 0,
    'our_69': our_69,
    'our_617': our_617, 'our_618_growth': round((our_618 - our_617) / our_617 * 100) if our_617 > 0 else 0,
    'comp_617': comp_617, 'comp_618_growth': round((comp_618 - comp_617) / comp_617 * 100) if comp_617 > 0 else 0,
    'our_618_vs_61_ratio': round(our_618 / our_61, 1) if our_61 > 0 else 0,
}

# Top 3 products for 我方
our_top3 = list(our_prod.index)[:3]
our_top3_total = sum(our_prod.loc[p, 'orders'] for p in our_top3 if p in our_prod.index)
result['our_top3'] = our_top3
result['our_top3_pct'] = round(our_top3_total / teams['我方']['orders'] * 100, 1) if teams['我方']['orders'] > 0 else 0

# Pie chart data
all_pie = [{'name': prod, 'value': int(row['orders'])} for prod, row in all_prods.iterrows()]
result['all_product_pie'] = all_pie

our_pie = [{'name': prod, 'value': int(row['orders'])} for prod, row in our_prod.iterrows()]
result['our_product_pie'] = our_pie

live_pie = [{'name': prod, 'value': int(row['orders'])} for prod, row in live_prods.iterrows()]
result['live_product_pie'] = live_pie

card_pie = [{'name': prod, 'value': int(row['orders'])} for prod, row in card_prods.iterrows()]
result['card_product_pie'] = card_pie

# Store details by team
for team in teams_order:
    live_team = live_df[live_df['team'] == team]
    stores = live_team.groupby(col_nick).agg(
        orders=(col_amount, 'count'), gsv=(col_amount, 'sum')
    ).sort_values('orders', ascending=False)
    result[f'{team}_store_list'] = {k: {'orders': int(v['orders']), 'gsv': round(v['gsv'], 2)}
                                    for k, v in stores.iterrows()}

# Output
with open('618_analysis_data.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"Data generated: {total_orders} orders (直播间{result['live_orders']} + 商品卡{result['card_orders']}), ¥{total_gsv:,.0f} (¥{result['total_gsv_wan']}万)")
print(f"\nTeam summary:")
for t in teams_order:
    info = teams[t]
    print(f"  {t}: {info['orders']}单 ({info['pct']}%) = 直播间{info['直播间_orders']} + 商品卡{info.get('商品卡_orders', 0)}, ¥{info['gsv_wan']}万")

print(f"\nChannel split:")
print(f"  直播间: {result['live_orders']}单 ¥{result['live_gsv_wan']}万")
print(f"  商品卡: {result['card_orders']}单 ¥{result['card_gsv_wan']}万")

print(f"\nKey product shares (all channels):")
for prod in ['小米手环10', 'REDMI Watch 6', '小米手环10 Pro', 'Xiaomi 开放式耳机']:
    d = result[f'prod_{prod}']
    print(f"  {prod}: 总{d['total']} = 我方{d['our']} vs 竞对{d['comp']}, 份额{d['share']}%, 差额{d['diff']}")

print(f"\n6/18: 我方{our_618}单({result['insight']['our_618_pct']}%), 竞对{comp_618}单")

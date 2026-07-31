import pandas as pd
import json
import sys
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from team_config import TEAM_MAP as TEAM_MAPPING
from product_classifier import classify_product

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load
df = pd.read_excel(r'C:\Users\Administrator\Desktop\6.18期间三个店铺订单订单.xlsx')
cols = df.columns.tolist()
col_product, col_time, col_status, col_amount, col_store = cols[0], cols[1], cols[2], cols[3], cols[4]
df['date'] = pd.to_datetime(df[col_time]).dt.date
df['team'] = df[col_store].map(TEAM_MAPPING).fillna('未分类')
df['product_cat'] = df[col_product].apply(classify_product)

# Full 618 period: 5/15-6/18
mask = (df['date'] >= pd.Timestamp('2026-05-15').date()) & (df['date'] <= pd.Timestamp('2026-06-18').date())
df = df[mask].copy()

result = {}

# === OVERALL KPIs ===
total_orders = len(df)
total_gmv = df[col_amount].sum()
result['total_orders'] = int(total_orders)
result['total_gmv_wan'] = round(total_gmv / 10000, 1)
result['total_gmv'] = round(total_gmv, 2)
result['period_start'] = '2026-05-15'
result['period_end'] = '2026-06-18'
result['total_days'] = 35

# === TEAM SUMMARY ===
teams = {}
for team in ['我方', '良米', '机械空间', '综训']:
    tdf = df[df['team'] == team]
    n_rooms = int(tdf[col_store].nunique())
    n_orders = int(len(tdf))
    teams[team] = {
        'orders': n_orders,
        'gmv': round(tdf[col_amount].sum(), 2),
        'gmv_wan': round(tdf[col_amount].sum() / 10000, 1),
        'rooms': n_rooms,
        'pct': round(n_orders / total_orders * 100, 1),
        'avg_per_room': int(n_orders / n_rooms) if n_rooms > 0 else 0,
    }
result['teams'] = teams

# === DAILY TREND ===
daily_dates = sorted(df['date'].unique())
result['dates'] = [str(d) for d in daily_dates]
result['dates_mmdd'] = [f"{d.month}/{d.day}" for d in daily_dates]

for team in ['我方', '良米', '机械空间', '综训']:
    result[f'daily_{team}_orders'] = []
    result[f'daily_{team}_gmv_wan'] = []

result['daily_total'] = []

for date in daily_dates:
    ddf = df[df['date'] == date]
    result['daily_total'].append(int(len(ddf)))
    for team in ['我方', '良米', '机械空间', '综训']:
        tdf = ddf[ddf['team'] == team]
        result[f'daily_{team}_orders'].append(int(len(tdf)))
        result[f'daily_{team}_gmv_wan'].append(round(tdf[col_amount].sum() / 10000, 1))

# === PRODUCTS ===
all_prods = df.groupby('product_cat').agg(
    orders=(col_amount, 'count'),
    gmv=(col_amount, 'sum')
).sort_values('orders', ascending=False)

# Products by team
our_df = df[df['team'] == '我方']
comp_df = df[df['team'].isin(['良米', '机械空间', '综训'])]

our_prod = our_df.groupby('product_cat').agg(
    orders=(col_amount, 'count'),
    gmv=(col_amount, 'sum')
).sort_values('orders', ascending=False)

comp_prod = comp_df.groupby('product_cat').agg(
    orders=(col_amount, 'count'),
    gmv=(col_amount, 'sum')
).sort_values('orders', ascending=False)

result['all_products'] = {k: {'orders': int(v['orders']), 'gmv': round(v['gmv'], 2)}
                          for k, v in all_prods.iterrows()}
result['our_products'] = {k: {'orders': int(v['orders']), 'gmv': round(v['gmv'], 2)}
                          for k, v in our_prod.iterrows()}
result['competitor_products'] = {k: {'orders': int(v['orders']), 'gmv': round(v['gmv'], 2)}
                                 for k, v in comp_prod.iterrows()}

# === KEY PRODUCT COMPARISONS ===
key_products = ['小米手环10', 'REDMI Watch 6', '小米手环10 Pro', '小米手环9 Pro',
                '小米手环10 陶瓷版', '小米手表 S系列', 'Xiaomi 开放式耳机',
                'REDMI Buds 8 Pro', 'REDMI Buds 8', 'REDMI Buds 8 活力版', 'REDMI Buds 8 青春版']

for prod in key_products:
    total_p = all_prods.loc[prod, 'orders'] if prod in all_prods.index else 0
    total_p_gmv = all_prods.loc[prod, 'gmv'] if prod in all_prods.index else 0
    our_p = our_prod.loc[prod, 'orders'] if prod in our_prod.index else 0
    our_p_gmv = our_prod.loc[prod, 'gmv'] if prod in our_prod.index else 0
    comp_p = comp_prod.loc[prod, 'orders'] if prod in comp_prod.index else 0
    comp_p_gmv = comp_prod.loc[prod, 'gmv'] if prod in comp_prod.index else 0
    share = round(our_p / total_p * 100, 1) if total_p > 0 else 0
    result[f'prod_{prod}'] = {
        'total': int(total_p), 'total_gmv': round(total_p_gmv, 2),
        'our': int(our_p), 'our_gmv': round(our_p_gmv, 2),
        'comp': int(comp_p), 'comp_gmv': round(comp_p_gmv, 2),
        'share': share,
    }

# === ROOM RANKING (6/18) ===
date_618 = pd.Timestamp('2026-06-18').date()
df_618 = df[df['date'] == date_618]
room_618 = df_618.groupby(col_store).agg(
    orders=(col_amount, 'count'),
    gmv=(col_amount, 'sum')
).sort_values('orders', ascending=False)

result['rooms_618'] = []
for store, row in room_618.iterrows():
    team = TEAM_MAPPING.get(store, '未分类')
    result['rooms_618'].append({
        'name': store,
        'team': team,
        'orders': int(row['orders']),
        'gmv': round(row['gmv'], 2),
        'gmv_fmt': f"¥{row['gmv']:,.0f}"
    })

# === INSIGHT DATA ===
june1 = pd.Timestamp('2026-06-01').date()
june18 = pd.Timestamp('2026-06-18').date()
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
comp_617 = int(len(df_june17[df_june17['team'].isin(['良米', '机械空间', '综训'])]))
comp_618 = int(len(df_june18[df_june18['team'].isin(['良米', '机械空间', '综训'])]))
total_618_day = int(len(df_june18))

result['insight'] = {
    'our_618': our_618, 'total_618_day': total_618_day,
    'our_618_pct': round(our_618 / total_618_day * 100, 1),
    'our_61': our_61, 'our_61_pct': round(our_61 / len(df_june1) * 100, 1),
    'our_69': our_69,
    'our_617': our_617, 'our_618_growth': round((our_618 - our_617) / our_617 * 100),
    'comp_617': comp_617, 'comp_618_growth': round((comp_618 - comp_617) / comp_617 * 100),
    'our_618_vs_61_ratio': round(our_618 / our_61, 1),
}

# Top 3 products for 我方
our_top3 = list(our_prod.index)[:3]
our_top3_total = sum(our_prod.loc[p, 'orders'] for p in our_top3 if p in our_prod.index)
result['our_top3'] = our_top3
result['our_top3_pct'] = round(our_top3_total / teams['我方']['orders'] * 100, 1)

# All products sorted for pie charts
all_pie = []
for prod, row in all_prods.iterrows():
    all_pie.append({'name': prod, 'value': int(row['orders'])})
result['all_product_pie'] = all_pie

our_pie = []
for prod, row in our_prod.iterrows():
    our_pie.append({'name': prod, 'value': int(row['orders'])})
result['our_product_pie'] = our_pie

# Store details by team
for team in ['我方', '良米', '机械空间', '综训']:
    tdf = df[df['team'] == team]
    stores = tdf.groupby(col_store).agg(
        orders=(col_amount, 'count'),
        gmv=(col_amount, 'sum')
    ).sort_values('orders', ascending=False)
    result[f'{team}_store_list'] = {k: {'orders': int(v['orders']), 'gmv': round(v['gmv'], 2)}
                                    for k, v in stores.iterrows()}

# Output
with open('618_analysis_data.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"Data generated successfully: {total_orders} orders, ¥{total_gmv:,.2f}")
print(f"\nTeam summary:")
for t in ['我方', '良米', '机械空间', '综训']:
    info = teams[t]
    print(f"  {t}: {info['orders']} orders ({info['pct']}%), ¥{info['gmv_wan']}万, {info['rooms']}间, {info['avg_per_room']}单/间")

print(f"\nKey product shares:")
for prod in ['小米手环10', 'REDMI Watch 6', '小米手环10 Pro', 'Xiaomi 开放式耳机']:
    d = result[f'prod_{prod}']
    print(f"  {prod}: 我方{d['our']} vs 竞对{d['comp']}, 份额{d['share']}%")

print(f"\n6/18 details: 我方{our_618}单({result['insight']['our_618_pct']}%), 竞对{comp_618}单")
print(f"6/17→6/18: 我方+{result['insight']['our_618_growth']}%, 竞对+{result['insight']['comp_618_growth']}%")

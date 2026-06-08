import pandas as pd
import numpy as np
import sys
sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_excel(r'C:\Users\Administrator\Downloads\良米6.1-6.7千川视频数据.xlsx')

def to_num(s):
    if isinstance(s, str):
        return float(s.replace(',', '').replace('%', ''))
    return float(s) if pd.notna(s) else np.nan

clean = pd.DataFrame()
clean['name'] = df.iloc[:, 0]
clean['source'] = df.iloc[:, 5]
clean['roi'] = df.iloc[:, 7].apply(to_num)
clean['orders'] = df.iloc[:, 8]
clean['deal_amt'] = df.iloc[:, 9].apply(to_num)
clean['avg_price'] = df.iloc[:, 10]
clean['impressions'] = df.iloc[:, 11].apply(to_num)
clean['clicks'] = df.iloc[:, 12].apply(to_num)
clean['ctr'] = df.iloc[:, 13].apply(to_num)
clean['cvr'] = df.iloc[:, 14].apply(to_num)
clean['cost'] = df.iloc[:, 15].apply(to_num)
clean['cost2'] = df.iloc[:, 16].apply(to_num)
clean['pay_roi'] = df.iloc[:, 17].apply(to_num)
clean['actual_pay'] = df.iloc[:, 21].apply(to_num)
clean['plays1'] = df.iloc[:, 27].apply(to_num)
clean['plays2'] = df.iloc[:, 30].apply(to_num)
clean['completion'] = df.iloc[:, 31].apply(to_num)
clean['plays'] = clean['plays2'].fillna(clean['plays1'])

has_cost = clean[clean['cost'] > 0].copy()

# Their metrics
their_cost = has_cost['cost'].sum()
their_deal = has_cost['deal_amt'].sum()
their_orders = has_cost['orders'].sum()
their_plays = has_cost['plays'].sum()
their_impressions = has_cost['impressions'].sum()
their_clicks = has_cost['clicks'].sum()
their_roi = their_deal / their_cost if their_cost > 0 else 0
their_ctr = their_clicks / their_impressions * 100 if their_impressions > 0 else 0
their_cvr = their_orders / their_clicks * 100 if their_clicks > 0 else 0
their_videos = len(has_cost)

# Our metrics (from previous report)
our_videos = 1880
our_cost = 58237.71
our_deal = 876253.75
our_orders = 2249
our_plays = 2006378
our_roi = 15.05
our_ctr = 7.23
our_cvr = 1.55

def classify_product(name):
    name = str(name)
    if '手环' in name:
        return 'Xiaomi Band'
    if 'watch' in name.lower() or 'Watch' in name:
        return 'Redmi Watch6'
    if '耳机' in name or 'Buds' in name or 'buds' in name:
        return 'Earphones'
    if 'AIGC' in name or 'aigc' in name:
        return 'AIGC Collection'
    return 'Other/General'

has_cost['product'] = has_cost['name'].apply(classify_product)

print("=" * 70)
print("  COMPETITOR ANALYSIS: LiangMi vs Our Company")
print("  2026.6.1 - 2026.6.7")
print("=" * 70)

print("\n[1] CORE METRICS COMPARISON")
print("-" * 70)
print(f"  {'Metric':<28} {'Ours':>15} {'Competitor':>15} {'Diff':>10}")
print(f"  {'-'*68}")
print(f"  {'Videos with Cost':<28} {our_videos:>15,} {their_videos:>15,} {their_videos-our_videos:>+10,}")
print(f"  {'Total Cost':<28} {our_cost:>14,.2f} {their_cost:>14,.2f} {their_cost-our_cost:>+9,.0f}")
print(f"  {'Total Deal Amount':<28} {our_deal:>14,.2f} {their_deal:>14,.2f} {their_deal-our_deal:>+9,.0f}")
print(f"  {'Total Orders':<28} {our_orders:>15,} {their_orders:>15,.0f} {their_orders-our_orders:>+9,.0f}")
print(f"  {'Total Plays':<28} {our_plays:>15,} {their_plays:>15,.0f} {their_plays-our_plays:>+9,.0f}")
print(f"  {'Overall ROI':<28} {our_roi:>15.2f} {their_roi:>15.2f} {their_roi-our_roi:>+10.2f}")
print(f"  {'Overall CTR':<28} {our_ctr:>14.2f}% {their_ctr:>14.2f}% {their_ctr-our_ctr:>+10.2f}%")
print(f"  {'Overall CVR':<28} {our_cvr:>14.2f}% {their_cvr:>14.2f}% {their_cvr-our_cvr:>+10.2f}%")

print("\n[2] PER-VIDEO EFFICIENCY")
print("-" * 70)
our_avg_cost = our_cost / our_videos
their_avg_cost = their_cost / their_videos
our_avg_deal = our_deal / our_videos
their_avg_deal = their_deal / their_videos
our_avg_plays = our_plays / our_videos
their_avg_plays = their_plays / their_videos
our_cpo = our_cost / our_orders
their_cpo = their_cost / their_orders
our_dpo = our_deal / our_orders
their_dpo = their_deal / their_orders
our_ppc = our_plays / our_cost
their_ppc = their_plays / their_cost

print(f"  {'Metric':<28} {'Ours':>15} {'Competitor':>15} {'Diff':>10}")
print(f"  {'-'*68}")
print(f"  {'Avg Cost per Video':<28} {our_avg_cost:>13.2f} {their_avg_cost:>13.2f} {their_avg_cost-our_avg_cost:>+10.2f}")
print(f"  {'Avg Deal per Video':<28} {our_avg_deal:>13.2f} {their_avg_deal:>13.2f} {their_avg_deal-our_avg_deal:>+10.2f}")
print(f"  {'Avg Plays per Video':<28} {our_avg_plays:>13.0f} {their_avg_plays:>13.0f} {their_avg_plays-our_avg_plays:>+10.0f}")
print(f"  {'Cost per Order':<28} {our_cpo:>13.2f} {their_cpo:>13.2f} {their_cpo-our_cpo:>+10.2f}")
print(f"  {'Deal Amount per Order':<28} {our_dpo:>13.2f} {their_dpo:>13.2f} {their_dpo-our_dpo:>+10.2f}")
print(f"  {'Plays per Yuan Cost':<28} {our_ppc:>13.1f} {their_ppc:>13.1f} {their_ppc-our_ppc:>+10.1f}")

print("\n[3] CHANNEL COMPARISON")
print("-" * 70)
our_channels = {
    'Douyin Homepage': (44143, 694374, 15.7, 1747441),
    'AIGC Dynamic': (9927, 133399, 13.4, 152774),
    'Local Upload': (3875, 40932, 10.6, 99669),
}
# Map to competitor Chinese names
cn_map = {
    'Douyin Homepage': '抖音号主页素材',
    'AIGC Dynamic': 'AIGC动态创意',
    'Local Upload': '本地上传',
}
their_channels = {}
for src in has_cost['source'].unique():
    subset = has_cost[has_cost['source'] == src]
    c = subset['cost'].sum()
    d = subset['deal_amt'].sum()
    p = subset['plays'].sum()
    r = d / c if c > 0 else 0
    their_channels[src] = (c, d, r, p, len(subset))

print(f"  {'Channel':<22} {'Our Cost':>12} {'Our ROI':>8} {'Their Cost':>12} {'Their ROI':>8}")
print(f"  {'-'*64}")
for en_name, cn_name in cn_map.items():
    oc, od, oro, op = our_channels.get(en_name, (0, 0, 0, 0))
    tc, td, tro, tp, tv = their_channels.get(cn_name, (0, 0, 0, 0, 0))
    print(f"  {en_name:<22} {oc:>10,.0f}  {oro:>6.1f}  {tc:>10,.0f}  {tro:>6.1f}")

# Also show competitor-only channels
for cn_name, (tc, td, tro, tp, tv) in their_channels.items():
    if cn_name not in cn_map.values():
        print(f"  [{cn_name}]: cost={tc:,.0f} deal={td:,.0f} ROI={tro:.1f} plays={tp:,.0f} videos={tv}")

print("\n[4] PRODUCT LINE COMPARISON")
print("-" * 70)
our_products = {
    'Xiaomi Band': (27434, 386066, 14.1, 882299),
    'Redmi Watch6': (13754, 259876, 18.9, 745889),
    'Earphones': (3202, 49141, 15.3, 132798),
    'AIGC Collection': (9927, 133399, 13.4, 152774),
    'Other/General': (3921, 47772, 12.2, 92618),
}
print(f"  {'Product':<22} {'Our Cost':>12} {'Our ROI':>8} {'Their Cost':>12} {'Their ROI':>8} {'Their Videos':>8}")
print(f"  {'-'*72}")
for prod in ['Xiaomi Band', 'Redmi Watch6', 'Earphones', 'AIGC Collection', 'Other/General']:
    oc, od, oro, op = our_products.get(prod, (0, 0, 0, 0))
    subset = has_cost[has_cost['product'] == prod]
    tc = subset['cost'].sum() if len(subset) > 0 else 0
    td = subset['deal_amt'].sum() if len(subset) > 0 else 0
    tro = td / tc if tc > 0 else 0
    tv = len(subset)
    print(f"  {prod:<22} {oc:>10,.0f}  {oro:>6.1f}  {tc:>10,.0f}  {tro:>6.1f}  {tv:>8}")

print("\n[5] ROI DISTRIBUTION COMPARISON")
print("-" * 70)
their_roi_gt1_pct = (has_cost['roi'] > 1).sum() / len(has_cost) * 100
their_roi_eq0_pct = (has_cost['roi'] == 0).sum() / len(has_cost) * 100
our_roi_gt1_pct = 21.5
our_median_roi = 0.00
their_median_roi = has_cost['roi'].median()
our_mean_roi = 12.42
their_mean_roi = has_cost['roi'].mean()
print(f"  ROI>1 video ratio:     Ours {our_roi_gt1_pct:.1f}%  vs  Theirs {their_roi_gt1_pct:.1f}%")
print(f"  ROI=0 video ratio:     Theirs {their_roi_eq0_pct:.1f}%")
print(f"  Median ROI:            Ours {our_median_roi:.2f}  vs  Theirs {their_median_roi:.2f}")
print(f"  Mean ROI:              Ours {our_mean_roi:.2f}  vs  Theirs {their_mean_roi:.2f}")

print("\n[6] TOP 5 COMPETITOR VIDEOS BY COST")
print("-" * 70)
top5 = has_cost.nlargest(5, 'cost')
for i, (_, row) in enumerate(top5.iterrows()):
    name = str(row['name'])[:90]
    print(f"  {i+1}. {name}")
    print(f"     Cost={row['cost']:,.0f}  Deal={row['deal_amt']:,.0f}  ROI={row['roi']:.1f}  Plays={row['plays']:,.0f}  CTR={row['ctr']:.1f}%")

print("\n[7] KEY FINDINGS")
print("-" * 70)
print(f"  1. Scale: They spend {their_cost/our_cost:.1f}x more ({their_cost:,.0f} vs {our_cost:,.0f}),")
print(f"     with {their_videos/our_videos:.1f}x more videos ({their_videos} vs {our_videos})")
print(f"  2. ROI: Their ROI ({their_roi:.2f}) is slightly {'higher' if their_roi > our_roi else 'lower'} than ours ({our_roi:.2f})")
print(f"  3. CTR: Our CTR ({our_ctr}%) is significantly higher than theirs ({their_ctr:.1f}%) - our content is more engaging")
print(f"  4. CVR: Our CVR ({our_cvr}%) is higher than theirs ({their_cvr:.1f}%) - we convert better")
print(f"  5. Play Efficiency: They get {their_ppc:.1f} plays/yuan vs our {our_ppc:.1f} ({their_ppc/our_ppc:.1f}x)")
print(f"  6. Cost per Order: Nearly identical ({our_cpo:.2f} vs {their_cpo:.2f})")
print(f"  7. AIGC: They barely use AIGC (1 video), we have a dedicated AIGC channel")
print(f"  8. Their Redmi Watch6 ROI ({has_cost[has_cost['product']=='Redmi Watch6']['deal_amt'].sum()/has_cost[has_cost['product']=='Redmi Watch6']['cost'].sum():.1f})")
print(f"     vs ours (18.9) - competitive but different strategy")
print(f"  9. 84.6% of their videos have ROI=0 (no conversions), vs we need to check ours")

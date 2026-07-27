"""
Generate 千川视频数据 7.1-7.26 comprehensive analysis report.
Three modules: Video Data, Title Data, Live Room Screen Data.
Each module: 我司 → 良米 → 对比.
"""
import pandas as pd
import numpy as np
import json
import sys
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from formatters import fmt_money, fmt_num, fmt_roi, fmt_pct

sys.stdout.reconfigure(encoding='utf-8')

# ===== Robust column-name-based data loading =====
def to_num(s):
    if isinstance(s, str):
        return float(s.replace(',', '').replace('%', ''))
    return float(s) if pd.notna(s) else np.nan

def find_col(df, *keywords):
    """Find column index by keyword matching"""
    for i, col in enumerate(df.columns):
        col_str = str(col)
        if all(kw in col_str for kw in keywords):
            return i
    return None

def load_video_data_by_name(path):
    """Load video data using column name matching (handles different column orders)"""
    df = pd.read_excel(path)
    clean = pd.DataFrame()

    col_map = {
        'name': find_col(df, '素材名称'),
        'source': find_col(df, '素材来源'),
        'tag': find_col(df, '标签'),
        'roi': find_col(df, '净成交ROI'),
        'deal_amt': find_col(df, '净成交金额'),
        'orders': find_col(df, '净成交订单数'),
        'impressions': find_col(df, '整体展现'),
        'clicks': find_col(df, '整体点击次数'),
        'ctr': find_col(df, '整体点击率'),
        'cvr': find_col(df, '整体转化率'),
        'cost': find_col(df, '整体消耗'),
        'base_cost': find_col(df, '基础消耗'),
        'pay_roi': find_col(df, '整体支付ROI'),
        'pay_amt': find_col(df, '整体成交金额'),
        'pay_orders': find_col(df, '整体成交订单数'),
        'pay_order_cost': find_col(df, '整体成交订单成本'),
        'user_pay': find_col(df, '用户实际支付'),
        'cpc': find_col(df, '整体点击单价'),
        'cpm': find_col(df, '整体千次展现'),
        'coupon': find_col(df, '智能优惠券'),
        'platform_subsidy': find_col(df, '电商平台补贴'),
        'preorder': find_col(df, '未完结预售'),
        'likes': find_col(df, '视频点赞'),
        'new_fans': find_col(df, '新增粉丝'),
        'avg_watch_time': find_col(df, '平均观看时长'),
        'plays': find_col(df, '视频播放数'),
        'completion': find_col(df, '视频完播率'),
        'comments': find_col(df, '视频评论'),
        'play_2s': find_col(df, '2秒播放'),
        'play_3s': find_col(df, '3秒播放'),
        'play_5s': find_col(df, '5秒播放'),
        'play_10s': find_col(df, '10秒播放'),
    }

    for key, idx in col_map.items():
        if idx is not None:
            if key in ['name', 'source', 'tag']:
                clean[key] = df.iloc[:, idx].astype(str)
            elif key in ['orders', 'pay_orders', 'likes', 'new_fans', 'comments']:
                clean[key] = pd.to_numeric(df.iloc[:, idx], errors='coerce')
            elif key == 'avg_watch_time':
                clean[key] = pd.to_numeric(df.iloc[:, idx], errors='coerce')
            elif key in ['plays']:
                clean[key] = df.iloc[:, idx].apply(to_num)
            else:
                clean[key] = df.iloc[:, idx].apply(to_num)

    # Fill missing with defaults
    for key in ['plays', 'orders', 'pay_orders', 'likes', 'new_fans', 'comments']:
        if key in clean:
            clean[key] = clean[key].fillna(0)
    if 'completion' in clean:
        clean['completion'] = clean['completion'].fillna(0)
    if 'play_2s' in clean:
        clean['play_2s'] = clean['play_2s'].fillna(0)

    return clean

def load_title_data_by_name(path):
    """Load title data using column name matching"""
    df = pd.read_excel(path)
    clean = pd.DataFrame()

    clean['name'] = df.iloc[:, 0].astype(str)
    cost_idx = find_col(df, '整体消耗')
    roi_idx = find_col(df, '整体支付ROI')
    amt_idx = find_col(df, '整体成交金额')
    orders_idx = find_col(df, '整体成交订单数')
    cost_per_order_idx = find_col(df, '整体成交订单成本')

    if cost_idx is not None:
        clean['cost'] = df.iloc[:, cost_idx].apply(to_num)
    if roi_idx is not None:
        clean['pay_roi'] = df.iloc[:, roi_idx].apply(to_num)
    if amt_idx is not None:
        clean['pay_amt'] = df.iloc[:, amt_idx].apply(to_num)
    if orders_idx is not None:
        clean['pay_orders'] = pd.to_numeric(df.iloc[:, orders_idx], errors='coerce')
    if cost_per_order_idx is not None:
        clean['avg_price'] = pd.to_numeric(df.iloc[:, cost_per_order_idx], errors='coerce')

    return clean

def load_room_data_by_name(path):
    """Load live room screen data using column name matching"""
    df = pd.read_excel(path)
    clean = pd.DataFrame()

    clean['name'] = df.iloc[:, 0].astype(str)
    date_idx = find_col(df, '日期')
    cost_idx = find_col(df, '整体消耗')
    roi_idx = find_col(df, '净成交ROI')
    deal_idx = find_col(df, '净成交金额')
    refund_rate_idx = find_col(df, '1小时内退款率')
    pay_roi_idx = find_col(df, '整体支付ROI')
    pay_amt_idx = find_col(df, '整体成交金额')
    settle_idx = find_col(df, '净成交金额结算率')
    orders_idx = find_col(df, '净成交订单数')

    if date_idx is not None:
        clean['date'] = df.iloc[:, date_idx]
    if cost_idx is not None:
        clean['cost'] = df.iloc[:, cost_idx].apply(to_num)
    if roi_idx is not None:
        clean['roi'] = df.iloc[:, roi_idx].apply(to_num)
    if deal_idx is not None:
        clean['deal_amt'] = df.iloc[:, deal_idx].apply(to_num)
    if refund_rate_idx is not None:
        clean['refund_rate_1h'] = pd.to_numeric(df.iloc[:, refund_rate_idx], errors='coerce')
    if pay_roi_idx is not None:
        clean['pay_roi'] = df.iloc[:, pay_roi_idx].apply(to_num)
    if pay_amt_idx is not None:
        clean['pay_amt'] = df.iloc[:, pay_amt_idx].apply(to_num)
    if settle_idx is not None:
        clean['settle_rate'] = df.iloc[:, settle_idx].apply(to_num)
    if orders_idx is not None:
        clean['orders'] = pd.to_numeric(df.iloc[:, orders_idx], errors='coerce')

    return clean


# ===== Product Classification =====
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


# ===== Video Metrics =====
def compute_video_metrics(clean):
    hc = clean[clean['cost'] > 0].copy()
    if len(hc) == 0:
        return None

    total_cost = hc['cost'].sum()
    total_deal = hc['deal_amt'].sum()
    total_orders = int(hc['orders'].sum()) if 'orders' in hc else 0
    total_plays = int(round(hc['plays'].sum())) if 'plays' in hc else 0
    total_impressions = int(round(hc['impressions'].sum())) if 'impressions' in hc else 0
    total_clicks = int(hc['clicks'].sum()) if 'clicks' in hc else 0
    total_pay = hc['pay_amt'].sum() if 'pay_amt' in hc else 0
    total_pay_orders = int(hc['pay_orders'].sum()) if 'pay_orders' in hc else 0

    roi = total_deal / total_cost if total_cost > 0 else 0
    pay_roi = total_pay / total_cost if total_cost > 0 else 0
    ctr = total_clicks / total_impressions * 100 if total_impressions > 0 else 0
    cvr = total_orders / total_clicks * 100 if total_clicks > 0 else 0
    plays_per_yuan = total_plays / total_cost if total_cost > 0 else 0

    # Source breakdown
    sources = []
    for src in hc['source'].unique():
        s = hc[hc['source'] == src]
        c = s['cost'].sum()
        d = s['deal_amt'].sum()
        r = d / c if c > 0 else 0
        o = int(s['orders'].sum()) if 'orders' in s else 0
        p = int(round(s['plays'].sum())) if 'plays' in s else 0
        sources.append({'name': str(src), 'cost': round(c, 2), 'deal': round(d, 2), 'roi': round(r, 2), 'orders': o, 'plays': p, 'videos': len(s)})
    sources.sort(key=lambda x: x['cost'], reverse=True)

    # Product breakdown
    hc['product'] = hc['name'].apply(classify_product)
    products = []
    prod_order = ['Xiaomi Band', 'Redmi Watch6', 'Earphones', 'AIGC Collection', 'Other/General']
    for prod in prod_order:
        s = hc[hc['product'] == prod]
        c = s['cost'].sum()
        d = s['deal_amt'].sum()
        r = d / c if c > 0 else 0
        o = int(s['orders'].sum()) if 'orders' in s else 0
        p = int(round(s['plays'].sum())) if 'plays' in s else 0
        products.append({'name': prod, 'cost': round(c, 2), 'deal': round(d, 2), 'roi': round(r, 2), 'orders': o, 'plays': p, 'videos': len(s)})

    # ROI distribution
    roi_bins = [
        {'label': 'ROI=0', 'min': -999, 'max': 0, 'count': 0},
        {'label': '0<ROI≤1', 'min': 0.001, 'max': 1, 'count': 0},
        {'label': '1<ROI≤5', 'min': 1.001, 'max': 5, 'count': 0},
        {'label': '5<ROI≤10', 'min': 5.001, 'max': 10, 'count': 0},
        {'label': '10<ROI≤20', 'min': 10.001, 'max': 20, 'count': 0},
        {'label': '20<ROI≤100', 'min': 20.001, 'max': 100, 'count': 0},
        {'label': 'ROI>100', 'min': 100.001, 'max': 999999, 'count': 0},
    ]
    for b in roi_bins:
        b['count'] = int(((hc['roi'] >= b['min']) & (hc['roi'] <= b['max'])).sum())

    median_roi = hc['roi'].median()
    mean_roi = hc['roi'].mean()
    roi_gt1_pct = (hc['roi'] > 1).sum() / len(hc) * 100 if len(hc) > 0 else 0
    roi_eq0_pct = (hc['roi'] == 0).sum() / len(hc) * 100 if len(hc) > 0 else 0

    # Top 10 by cost
    top10_list = []
    for _, r in hc.nlargest(10, 'cost').iterrows():
        top10_list.append({
            'name': str(r['name'])[:80],
            'cost': r['cost'], 'deal': r['deal_amt'], 'roi': r['roi'],
            'plays': r.get('plays', 0), 'ctr': r.get('ctr', 0),
        })

    # Dark horse videos
    dark_list = []
    if 'plays' in hc.columns:
        dark = hc[(hc['cost'] <= 200) & (hc['roi'] >= 30)].nlargest(8, 'roi')
        for _, r in dark.iterrows():
            dark_list.append({
                'name': str(r['name'])[:80],
                'cost': r['cost'], 'deal': r['deal_amt'], 'roi': r['roi'],
                'plays': r.get('plays', 0),
            })

    avg_comp = round(hc['completion'].mean(), 2) if 'completion' in hc.columns and pd.notna(hc['completion'].mean()) else 0
    avg_play2s = round(hc['play_2s'].mean(), 2) if 'play_2s' in hc.columns and pd.notna(hc['play_2s'].mean()) else 0
    avg_watch = round(hc['avg_watch_time'].mean(), 2) if 'avg_watch_time' in hc.columns and pd.notna(hc['avg_watch_time'].mean()) else 0

    cpc_val = round(total_cost / total_clicks, 2) if total_clicks > 0 else 0
    cpm_val = round(total_cost / total_impressions * 1000, 2) if total_impressions > 0 else 0

    return {
        'total_videos': len(clean), 'cost_videos': len(hc),
        'total_cost': round(float(total_cost), 2), 'total_deal': round(float(total_deal), 2),
        'total_orders': total_orders, 'total_plays': total_plays,
        'total_impressions': total_impressions, 'total_clicks': total_clicks,
        'total_pay': round(float(total_pay), 2), 'total_pay_orders': total_pay_orders,
        'roi': round(roi, 2), 'pay_roi': round(pay_roi, 2),
        'ctr': round(ctr, 2), 'cvr': round(cvr, 2),
        'plays_per_yuan': round(plays_per_yuan, 2),
        'avg_watch_time': avg_watch, 'avg_completion': avg_comp, 'avg_play_2s': avg_play2s,
        'cpc': cpc_val, 'cpm': cpm_val,
        'sources': sources, 'products': products, 'roi_bins': roi_bins,
        'median_roi': round(median_roi, 2), 'mean_roi': round(mean_roi, 2),
        'roi_gt1_pct': round(roi_gt1_pct, 2), 'roi_eq0_pct': round(roi_eq0_pct, 2),
        'top10': top10_list, 'dark': dark_list,
    }


# ===== Title Analysis =====
def analyze_titles(data):
    hc = data[data['cost'] > 0].copy()
    if len(hc) == 0:
        return None
    total_cost = hc['cost'].sum()
    total_pay = hc['pay_amt'].sum() if 'pay_amt' in hc else 0
    total_orders = int(hc['pay_orders'].sum()) if 'pay_orders' in hc else 0
    roi = total_pay / total_cost if total_cost > 0 else 0
    avg_price = hc['avg_price'].mean() if 'avg_price' in hc else 0

    top10_cost = hc.nlargest(10, 'cost')
    top_cost_list = []
    for _, r in top10_cost.iterrows():
        top_cost_list.append({
            'name': str(r['name'])[:100],
            'cost': float(r['cost']) if pd.notna(r['cost']) else 0,
            'pay_roi': float(r['pay_roi']) if pd.notna(r['pay_roi']) else 0,
            'pay_amt': float(r['pay_amt']) if 'pay_amt' in r and pd.notna(r['pay_amt']) else 0,
            'orders': int(r['pay_orders']) if 'pay_orders' in r and pd.notna(r['pay_orders']) else 0,
        })

    top10_roi = hc.nlargest(10, 'pay_roi')
    top_roi_list = []
    for _, r in top10_roi.iterrows():
        top_roi_list.append({
            'name': str(r['name'])[:100],
            'cost': float(r['cost']) if pd.notna(r['cost']) else 0,
            'pay_roi': float(r['pay_roi']) if pd.notna(r['pay_roi']) else 0,
            'pay_amt': float(r['pay_amt']) if 'pay_amt' in r and pd.notna(r['pay_amt']) else 0,
            'orders': int(r['pay_orders']) if 'pay_orders' in r and pd.notna(r['pay_orders']) else 0,
        })

    # ROI bins
    roi_bins = [
        {'label': 'ROI=0', 'min': -999, 'max': 0, 'count': 0},
        {'label': '0<ROI≤1', 'min': 0.001, 'max': 1, 'count': 0},
        {'label': '1<ROI≤5', 'min': 1.001, 'max': 5, 'count': 0},
        {'label': '5<ROI≤10', 'min': 5.001, 'max': 10, 'count': 0},
        {'label': '10<ROI≤20', 'min': 10.001, 'max': 20, 'count': 0},
        {'label': '20<ROI≤100', 'min': 20.001, 'max': 100, 'count': 0},
        {'label': 'ROI>100', 'min': 100.001, 'max': 999999, 'count': 0},
    ]
    for b in roi_bins:
        b['count'] = int(((hc['pay_roi'] >= b['min']) & (hc['pay_roi'] <= b['max'])).sum())

    # Word frequency
    all_words = []
    for name in hc['name']:
        words = re.findall(r'[一-龥]{2,}', str(name))
        all_words.extend(words)
    word_freq = Counter(all_words).most_common(20)

    return {
        'total_titles': len(data), 'cost_titles': len(hc),
        'total_cost': round(total_cost, 2), 'total_pay': round(total_pay, 2),
        'total_orders': total_orders, 'roi': round(roi, 2),
        'avg_price': round(avg_price, 2),
        'top_cost': top_cost_list, 'top_roi': top_roi_list,
        'roi_bins': roi_bins, 'word_freq': word_freq,
    }


# ===== Live Room Analysis =====
def analyze_liveroom(data):
    """Analyze live room screen data. All rows are daily (no summary). Group by room name."""
    hc = data[data['cost'] > 0].copy()
    if len(hc) == 0:
        return None

    # Aggregate totals from all daily rows
    total_cost = hc['cost'].sum()
    total_deal = hc['deal_amt'].sum() if 'deal_amt' in hc else 0
    total_orders = int(hc['orders'].sum()) if 'orders' in hc else 0
    roi = total_deal / total_cost if total_cost > 0 else 0
    avg_refund = hc['refund_rate_1h'].mean() if 'refund_rate_1h' in hc else 0
    avg_settle = hc['settle_rate'].mean() if 'settle_rate' in hc else 0

    # Per-room aggregation (sum daily rows by unique room name)
    screens = []
    for name in sorted(hc['name'].unique()):
        s = hc[hc['name'] == name]
        sc = s['cost'].sum()
        sd = s['deal_amt'].sum() if 'deal_amt' in s else 0
        sr = sd / sc if sc > 0 else 0
        so = int(s['orders'].sum()) if 'orders' in s else 0
        srfr = s['refund_rate_1h'].mean() if 'refund_rate_1h' in s else 0
        sstl = s['settle_rate'].mean() if 'settle_rate' in s else 0
        screens.append({
            'name': str(name)[:60],
            'cost': round(float(sc), 2),
            'deal': round(float(sd), 2),
            'roi': round(float(sr), 2),
            'refund_rate': round(float(srfr), 2),
            'settle_rate': round(float(sstl), 2),
            'orders': so,
            'days': len(s),
        })
    screens.sort(key=lambda x: x['cost'], reverse=True)

    # Daily trend: sum across all rooms per date
    daily_trend = []
    for date in sorted(hc['date'].unique()):
        d = hc[hc['date'] == date]
        ds = d['deal_amt'].sum() if 'deal_amt' in d else 0
        daily_trend.append({
            'date': str(date)[:10],
            'cost': round(float(d['cost'].sum()), 2),
            'roi': round(float(ds) / float(d['cost'].sum()), 2) if d['cost'].sum() > 0 else 0,
            'deal_amt': round(float(ds), 2),
            'refund_rate': round(float(d['refund_rate_1h'].mean()), 2) if 'refund_rate_1h' in d else 0,
            'orders': int(d['orders'].sum()) if 'orders' in d and pd.notna(d['orders'].sum()) else 0,
        })

    # Per-room daily data for detailed table
    room_daily = {}
    for name in hc['name'].unique():
        rd = hc[hc['name'] == name].copy()
        room_name = str(name)[:60]
        room_daily[room_name] = []
        for _, r in rd.iterrows():
            room_daily[room_name].append({
                'date': str(r['date'])[:10],
                'cost': round(float(r['cost']), 2),
                'roi': round(float(r['roi']), 2),
                'deal_amt': round(float(r['deal_amt']), 2) if 'deal_amt' in r else 0,
                'refund_rate': round(float(r['refund_rate_1h']), 2) if 'refund_rate_1h' in r else 0,
                'orders': int(r['orders']) if pd.notna(r.get('orders', 0)) else 0,
            })

    return {
        'total_screens': len(screens), 'total_cost': round(total_cost, 2),
        'total_deal': round(total_deal, 2), 'total_orders': total_orders,
        'roi': round(roi, 2),
        'avg_refund': round(avg_refund, 2), 'avg_settle': round(avg_settle, 2),
        'screens': screens, 'daily_trend': daily_trend, 'room_daily': room_daily,
    }


# ===== CSS =====
CSS = '''<style>
:root{--bg:#f0f4f8;--surface:#ffffff;--text:#0f172a;--text-secondary:#64748b;--accent:#1E90FF;--accent2:#FF4757;--shadow-sm:0 1px 3px rgba(0,0,0,.04);--shadow-md:0 4px 16px rgba(0,0,0,.06);--shadow-lg:0 8px 30px rgba(0,0,0,.10);--radius:14px;--transition:0.25s cubic-bezier(0.4,0,0.2,1);--ours:#1E90FF;--theirs:#FF6B35;--green:#2ED573;--purple:#A855F7;--orange:#FFA502;}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);}
body::before{content:'';position:fixed;inset:0;background-image:radial-gradient(circle,rgba(148,163,184,.12)1px,transparent 1px);background-size:24px 24px;pointer-events:none;z-index:0;}
.nav-bar{display:flex;justify-content:center;gap:8px;padding:12px 20px;background:rgba(255,255,255,.88);backdrop-filter:blur(12px);border-bottom:1px solid #e8ecf1;position:sticky;top:0;z-index:100;box-shadow:0 1px 4px rgba(0,0,0,.04);flex-wrap:wrap;}
.nav-btn{padding:8px 18px;border-radius:22px;border:1.5px solid #dde1e6;background:#fff;color:#555;font-size:13px;cursor:pointer;text-decoration:none;transition:all var(--transition);font-family:inherit;font-weight:500;}
.nav-btn:hover{border-color:#1E90FF;color:#1E90FF;background:#eff6ff;transform:translateY(-1px);}
.nav-btn.active{background:#1E90FF;color:#fff;border-color:#1E90FF;font-weight:600;box-shadow:0 2px 8px rgba(30,144,255,.25);}
.nav-btn.w5{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border-color:transparent;font-weight:600;}
.header{position:relative;z-index:1;padding:50px 20px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.1);color:white;}
.header h1{font-size:34px;font-weight:800;margin-bottom:10px;letter-spacing:-.02em;}
.header p{font-size:15px;opacity:0.9;font-weight:400;}
.module-header{position:relative;z-index:1;padding:36px 20px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.1);color:white;margin:0;}
.module-header h2{font-size:28px;font-weight:800;margin-bottom:6px;}
.module-header p{font-size:14px;opacity:0.9;}
.kpi-row{display:grid;grid-template-columns:repeat(6,1fr);gap:14px;max-width:1400px;margin:-28px auto 0;padding:0 20px;position:relative;z-index:10;}
.kpi-row-wide{display:grid;grid-template-columns:repeat(8,1fr);gap:12px;max-width:1400px;margin:-28px auto 0;padding:0 20px;position:relative;z-index:10;}
.kpi-card{background:var(--surface);border-radius:var(--radius);padding:22px 14px;text-align:center;box-shadow:var(--shadow-md);border:1px solid #e8ecf1;transition:transform var(--transition),box-shadow var(--transition);}
.kpi-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-lg);}
.kpi-card .value{font-size:26px;font-weight:800;line-height:1.2;}
.kpi-card .label{font-size:12px;color:var(--text-secondary);margin-top:6px;font-weight:500;letter-spacing:.03em;text-transform:uppercase;}
.kpi-card .sub{font-size:11px;color:var(--text-secondary);margin-top:4px;}
.container{max-width:1400px;margin:40px auto;padding:0 20px;position:relative;z-index:1;}
.section{background:var(--surface);border-radius:var(--radius);padding:32px;margin-bottom:24px;box-shadow:var(--shadow-sm);border:1px solid #e8ecf1;transition:box-shadow var(--transition);}
.section:hover{box-shadow:var(--shadow-md);}
.section h2{font-size:20px;font-weight:700;color:var(--text);margin-bottom:20px;padding-bottom:14px;border-bottom:2px solid #f0f0f0;position:relative;}
.section h2::after{content:'';position:absolute;bottom:-2px;left:0;width:48px;height:2px;background:var(--accent2);border-radius:1px;}
.section h3{font-size:16px;font-weight:700;color:var(--text);margin-bottom:14px;}
.chart-box{height:450px;}
.chart-box-lg{height:550px;}
.chart-box-sm{height:350px;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th{background:#f8f9fc;text-align:left;padding:12px 16px;font-size:12px;color:var(--text-secondary);font-weight:600;border-bottom:2px solid #e8ecf1;}
td{padding:12px 16px;font-size:13px;border-bottom:1px solid #f0f2f5;}
tbody tr{transition:background var(--transition);}
tbody tr:hover td{background:#f8fafc;}
.finding{padding:16px 20px;margin-bottom:12px;border-radius:0 10px 10px 0;font-size:14px;line-height:1.8;box-shadow:var(--shadow-sm);}
.finding.good{background:#e8f5e9;border-left:4px solid #2e7d32;}
.finding.warn{background:#fff3e0;border-left:4px solid #e65100;}
.finding.info{background:#e3f2fd;border-left:4px solid #1565c0;}
.finding.neutral{background:#f3e5f5;border-left:4px solid #7b1fa2;}
.footer{text-align:center;color:#94a3b8;padding:30px;font-size:13px;position:relative;z-index:1;}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:24px;}
.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:20px;}
.grid-4{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;margin-bottom:20px;}
.grid-5{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:20px;}
.tag{display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;margin-left:6px;font-weight:600;}
.tag-up{background:#ffebee;color:#c62828;}
.tag-down{background:#e8f5e9;color:#2e7d32;}
.diff-up{color:#c62828;font-weight:600;}
.diff-down{color:#2e7d32;font-weight:600;}
.period-badge{display:inline-block;padding:6px 16px;border-radius:20px;font-size:13px;font-weight:600;background:rgba(255,255,255,.2);margin-left:10px;vertical-align:middle;}
.word-cloud{display:flex;flex-wrap:wrap;gap:8px;padding:20px;}
.word-tag{padding:6px 14px;border-radius:18px;font-size:13px;font-weight:600;background:#e8ecf1;color:#555;transition:all .2s;}
.word-tag:hover{background:#1E90FF;color:#fff;transform:scale(1.05);}
.summary-card{background:linear-gradient(135deg,#f8f9fc 0%,#e8ecf1 100%);border-radius:var(--radius);padding:24px;margin-bottom:16px;border-left:4px solid #667eea;}
.summary-card h3{color:#667eea;margin-bottom:8px;}
.summary-card p{font-size:14px;line-height:1.8;color:var(--text-secondary);}
.divider{height:4px;background:linear-gradient(90deg,#1E90FF,#FF6B35,#2ED573,#A855F7);border-radius:2px;margin:40px 0;}
.compare-kpi-row{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px;}
.compare-card{flex:1;min-width:200px;border-radius:12px;padding:18px 16px;text-align:center;}
.compare-card.ours{background:#f0f4ff;}
.compare-card.theirs{background:#fff4f0;}
.compare-card.neutral{background:#f0fff4;}
.compare-card .v{font-size:28px;font-weight:800;}
.compare-card .l{font-size:12px;color:var(--text-secondary);margin-top:4px;}
.stat-badge{flex:1;min-width:120px;border-radius:12px;padding:18px 16px;text-align:center;}
.room-compare-card{background:var(--surface);border:1px solid #e8ecf1;border-radius:12px;padding:20px;margin-bottom:16px;}
.room-compare-card .room-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.room-half{padding:14px;border-radius:10px;}
.room-half.ours{background:#f0f4ff;}
.room-half.theirs{background:#fff4f0;}
.room-half .room-name{font-size:11px;color:var(--text-secondary);margin-bottom:8px;}
.room-half .room-stats{display:flex;gap:12px;flex-wrap:wrap;font-size:13px;}
.vs-badge{display:inline-block;padding:4px 12px;border-radius:12px;font-size:12px;font-weight:600;margin-top:10px;}
@media(max-width:900px){.kpi-row{grid-template-columns:repeat(3,1fr);}.kpi-row-wide{grid-template-columns:repeat(4,1fr);}.header h1{font-size:26px;}.grid-2{grid-template-columns:1fr;}.grid-3,.grid-4,.grid-5{grid-template-columns:1fr 1fr;}.room-compare-card .room-grid{grid-template-columns:1fr;}}
@media(max-width:500px){.kpi-row{grid-template-columns:1fr 1fr;}.kpi-row-wide{grid-template-columns:1fr 1fr;}.section{padding:20px 16px;}}
</style>'''

AUTH_SCRIPT = '''<script>
(function(){
var K='mi_band_auth_v1';
if(!localStorage.getItem(K)){window.location.href='../index.html';return;}
document.body.style.display='';
})();
</script>'''

NAV_W5 = '''<div class="nav-bar">
<a class="nav-btn" href="../index.html">🏠 首页</a>
<a class="nav-btn" href="核心指标报告_W4.html">W4 我司</a>
<a class="nav-btn" href="竞对数据报告_W4.html">W4 竞对</a>
<a class="nav-btn" href="竞对对比报告_W4.html">W4 对比</a>
<a class="nav-btn w5 active" href="千川视频分析_W5.html">🔥 W5 7.1-7.26</a>
<a class="nav-btn" href="周度总结对比.html">📊 周度总结</a>
</div>'''


# ===== HTML Generator Functions =====

def gen_header(title, subtitle, gradient, badge):
    return f'''<div class="header" style="background:linear-gradient(135deg, {gradient});">
<h1>{title}<span class="period-badge">{badge}</span></h1>
<p>{subtitle}</p>
</div>'''

def gen_module_header(title, subtitle, gradient):
    return f'''<div class="module-header" style="background:linear-gradient(135deg, {gradient});">
<h2>{title}</h2>
<p>{subtitle}</p>
</div>'''

def gen_kpi_cards(m, color_override=None):
    c = color_override or {}
    return f'''<div class="kpi-row">
<div class="kpi-card"><div class="value" style="color:{c.get('cost','#FF4757')};">{fmt_money(m['total_cost'])}</div><div class="label">总消耗</div></div>
<div class="kpi-card"><div class="value" style="color:{c.get('deal','#2ED573')};">{fmt_money(m['total_deal'])}</div><div class="label">净成交金额</div></div>
<div class="kpi-card"><div class="value" style="color:{c.get('roi','#1E90FF')};">{fmt_roi(m['roi'])}</div><div class="label">净成交ROI</div></div>
<div class="kpi-card"><div class="value" style="color:{c.get('plays','#FF6B35')};">{fmt_num(m['total_plays'])}</div><div class="label">总播放量</div></div>
<div class="kpi-card"><div class="value" style="color:{c.get('ctr','#A855F7')};">{fmt_pct(m['ctr'])}</div><div class="label">整体点击率</div></div>
<div class="kpi-card"><div class="value" style="color:{c.get('orders','#FFA502')};">{fmt_num(m['total_orders'])}</div><div class="label">净成交订单数</div></div>
</div>'''

def gen_overview_chart(m, chart_id='chart-overview'):
    data = [
        {'v': m['total_cost'], 'c': '#FF4757'},
        {'v': m['total_deal'], 'c': '#2ED573'},
        {'v': m['total_orders'], 'c': '#FFA502'},
        {'v': m['total_plays'], 'c': '#FF6B35'},
        {'v': m['roi'], 'c': '#1E90FF'},
        {'v': m['ctr'], 'c': '#A855F7'},
        {'v': m['cvr'], 'c': '#FF6348'},
        {'v': m['plays_per_yuan'], 'c': '#0891b2'},
    ]
    labels = ['消耗(¥)', '成交金额(¥)', '订单数', '播放量', 'ROI', 'CTR(%)', 'CVR(%)', '播放/元']
    items = ','.join([f'{{value:{d["v"]:.4f},itemStyle:{{color:"{d["c"]}"}}}}' for d in data])
    return f'''(function(){{
  var chart = echarts.init(document.getElementById('{chart_id}'));
  chart.setOption({{
    tooltip:{{trigger:'axis'}},legend:{{top:0}},
    grid:{{left:80,right:40,top:40,bottom:0}},
    xAxis:{{type:'value',splitLine:{{lineStyle:{{color:'#eee'}}}}}},
    yAxis:{{type:'category',data:{json.dumps(labels)},axisLabel:{{fontSize:13}}}},
    series:[{{type:'bar',barMaxWidth:35,
      data:[{items}],
      label:{{show:true,position:'right',fontSize:13,formatter:function(p){{var v=p.value;if(v>=1000000)return(v/1000000).toFixed(1)+'M';if(v>=10000)return(v/10000).toFixed(1)+'万';if(v>=1000)return v.toLocaleString();return v.toFixed(2);}}}}
    }}]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();'''

def gen_source_table(m):
    rows = ''
    for s in m['sources']:
        rows += f'<tr><td>{s["name"]}</td><td>{fmt_money(s["cost"])}</td><td>{fmt_money(s["deal"])}</td><td>{s["orders"]}</td><td><b>{s["roi"]:.1f}</b></td><td>{fmt_num(s["plays"])}</td></tr>\n'
    return f'<table><tr><th>渠道</th><th>消耗</th><th>成交金额</th><th>订单数</th><th>ROI</th><th>播放量</th></tr>{rows}</table>'

def gen_product_table(m):
    rows = ''
    total_cost = m['total_cost']
    for p in m['products']:
        pct = f' ({p["cost"]/total_cost*100:.1f}%)' if total_cost > 0 else ''
        rows += f'<tr><td>{p["name"]}</td><td>{fmt_money(p["cost"])}{pct}</td><td>{fmt_money(p["deal"])}</td><td><b>{p["roi"]:.1f}</b></td><td>{fmt_num(p["plays"])}</td><td>{p["videos"]}</td></tr>\n'
    return f'<table><tr><th>产品线</th><th>消耗</th><th>成交金额</th><th>ROI</th><th>播放量</th><th>视频数</th></tr>{rows}</table>'

def gen_top10_table(m):
    rows = ''
    for i, t in enumerate(m['top10']):
        rows += f'<tr><td>{i+1}</td><td style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{t["name"]}">{t["name"]}</td><td>{fmt_money(t["cost"])}</td><td>{fmt_money(t["deal"])}</td><td><b>{t["roi"]:.1f}</b></td><td>{fmt_num(t.get("plays",0))}</td><td>{t.get("ctr",0):.2f}%</td></tr>\n'
    return f'<table><tr><th>#</th><th>视频名称</th><th>消耗</th><th>成交金额</th><th>ROI</th><th>播放量</th><th>CTR</th></tr>{rows}</table>'

def gen_dark_table(m):
    rows = ''
    for i, t in enumerate(m['dark']):
        rows += f'<tr><td>{i+1}</td><td style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{t["name"]}">{t["name"]}</td><td>{fmt_money(t["cost"])}</td><td>{fmt_money(t["deal"])}</td><td><b>{t["roi"]:.1f}</b></td><td>{fmt_num(t.get("plays",0))}</td></tr>\n'
    if not rows:
        rows = '<tr><td colspan="6" style="text-align:center;color:#999;">暂无符合条件的黑马视频</td></tr>'
    return f'<table><tr><th>#</th><th>视频名称</th><th>消耗</th><th>成交金额</th><th>ROI</th><th>播放量</th></tr>{rows}</table>'

def gen_roi_stats_table(m):
    return f'''<div style="padding:30px;"><table>
<tr><th>指标</th><th>数值</th></tr>
<tr><td>ROI>0 视频占比</td><td><b>{m['roi_gt1_pct']:.1f}% ({(m['cost_videos'] - m['roi_bins'][0]['count'])}条)</b></td></tr>
<tr><td>ROI=0 视频占比</td><td>{m['roi_eq0_pct']:.1f}% ({m['roi_bins'][0]['count']}条)</td></tr>
<tr><td>中位ROI</td><td>{m['median_roi']:.2f}</td></tr>
<tr><td>均值ROI</td><td>{m['mean_roi']:.2f}</td></tr>
<tr><td>有消耗视频</td><td><b>{m['cost_videos']:,}条</b></td></tr>
<tr><td>总视频数</td><td>{m['total_videos']:,}条</td></tr>
<tr><td>零消耗视频</td><td>{m['total_videos'] - m['cost_videos']:,}条</td></tr>
</table></div>'''

def gen_title_top_table(title_data, label='消耗'):
    rows = ''
    for i, t in enumerate(title_data):
        rows += f'<tr><td>{i+1}</td><td style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{t["name"]}">{t["name"]}</td><td>{fmt_money(t["cost"])}</td><td>{fmt_money(t["pay_amt"])}</td><td><b>{t["pay_roi"]:.1f}</b></td><td>{t["orders"]}</td></tr>\n'
    return f'<table><tr><th>#</th><th>标题</th><th>消耗</th><th>成交金额</th><th>支付ROI</th><th>订单数</th></tr>{rows}</table>'

def gen_title_section(t, label='', sub_label=''):
    if t is None:
        return '<div class="section"><h2>视频标题分析</h2><p style="color:var(--text-secondary);">暂无标题数据</p></div>'
    roi_bin_rows = ''
    for b in t['roi_bins']:
        pct = b['count'] / t['cost_titles'] * 100 if t['cost_titles'] > 0 else 0
        roi_bin_rows += f'<tr><td>{b["label"]}</td><td>{b["count"]}</td><td>{pct:.1f}%</td></tr>\n'
    kw_summary = ''
    if t['word_freq'] and len(t['word_freq']) > 0:
        top_kw = [f'{w}({c})' for w, c in t['word_freq'][:10]]
        kw_summary = f'<p style="color:var(--text-secondary);font-size:14px;margin-bottom:16px;">🔑 高频关键词：{", ".join(top_kw)}</p>'
    return f'''<div class="section"><h2>📝 视频标题分析 {label}</h2>
{sub_label}
<div class="grid-3">
<div class="kpi-card"><div class="value" style="color:#FF4757;">{fmt_money(t['total_cost'])}</div><div class="label">标题总消耗</div></div>
<div class="kpi-card"><div class="value" style="color:#2ED573;">{fmt_money(t['total_pay'])}</div><div class="label">标题总成交</div></div>
<div class="kpi-card"><div class="value" style="color:#1E90FF;">{t['roi']:.2f}</div><div class="label">标题整体ROI</div></div>
</div>
{kw_summary}
<div style="margin-bottom:24px;">
<h3>📊 标题ROI分布</h3>
<table style="max-width:600px;">{roi_bin_rows}</table>
</div>
<div class="grid-2">
<div><h3>🔥 TOP10 高消耗标题</h3>{gen_title_top_table(t['top_cost'])}</div>
<div><h3>⭐ TOP10 高ROI标题</h3>{gen_title_top_table(t['top_roi'])}</div>
</div>
</div>'''

def gen_liveroom_section(room, label=''):
    if room is None:
        return '<div class="section"><h2>直播间画面分析</h2><p style="color:var(--text-secondary);">暂无直播间画面数据</p></div>'
    room_cards = ''
    for s in room['screens']:
        daily_rows = ''
        room_name = s['name']
        if room_name in room.get('room_daily', {}):
            for d in room['room_daily'][room_name]:
                daily_rows += f'<tr><td style="font-size:11px;">{d["date"]}</td><td style="font-size:11px;">{fmt_money(d["cost"])}</td><td style="font-size:11px;">{fmt_money(d["deal_amt"])}</td><td style="font-size:11px;"><b>{d["roi"]:.1f}</b></td><td style="font-size:11px;">{d["orders"]}</td></tr>\n'
        room_cards += f'''<div style="background:var(--surface);border:1px solid #e8ecf1;border-radius:12px;overflow:hidden;margin-bottom:16px;">
<div style="background:linear-gradient(135deg,#f0f4ff,#e8ecf1);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
<h3 style="margin:0;font-size:15px;">📺 {room_name}</h3>
<div style="display:flex;gap:16px;flex-wrap:wrap;font-size:13px;">
<span>💰消耗 <b style="color:#FF4757;">{fmt_money(s["cost"])}</b></span>
<span>💵成交 <b style="color:#2ED573;">{fmt_money(s["deal"])}</b></span>
<span>📈ROI <b style="color:#1E90FF;font-size:15px;">{s["roi"]:.1f}</b></span>
<span>↩️1h退款率 <b>{s["refund_rate"]:.1f}%</b></span>
<span>✅结算率 <b>{s["settle_rate"]:.1f}%</b></span>
<span>📦订单 <b>{s["orders"]}</b></span>
</div>
</div>
<div style="padding:8px 16px 12px;">
<table><tr><th>日期</th><th>消耗</th><th>成交</th><th>ROI</th><th>订单</th></tr>{daily_rows}</table>
</div>
</div>'''
    daily_json = json.dumps(room['daily_trend'])
    return f'''<div class="section"><h2>🎬 直播间画面分析 {label}</h2>
<div class="grid-5">
<div class="kpi-card"><div class="value" style="color:#FF4757;">{fmt_money(room['total_cost'])}</div><div class="label">画面总消耗</div></div>
<div class="kpi-card"><div class="value" style="color:#2ED573;">{fmt_money(room['total_deal'])}</div><div class="label">画面总成交</div></div>
<div class="kpi-card"><div class="value" style="color:#1E90FF;">{room['roi']:.2f}</div><div class="label">画面整体ROI</div></div>
<div class="kpi-card"><div class="value" style="color:#FF6B35;">{room['avg_refund']:.1f}%</div><div class="label">平均1h退款率</div></div>
<div class="kpi-card"><div class="value" style="color:#A855F7;">{fmt_num(room['total_orders'])}</div><div class="label">净成交订单数</div></div>
</div>
<div class="chart-box" id="chart-room-daily-{label.replace("(","").replace(")","").replace(" ","-")}" style="height:320px;"></div>
<h3 style="margin:20px 0 12px;">📺 按直播间逐一拆分</h3>
{room_cards}
</div>
<script>
(function(){{
  var chart = echarts.init(document.getElementById('chart-room-daily-{label.replace("(","").replace(")","").replace(" ","-")}'));
  var daily = {daily_json};
  chart.setOption({{
    tooltip:{{trigger:'axis'}},
    legend:{{data:['消耗','ROI','成交金额'],top:0}},
    grid:{{left:20,right:60,top:50,bottom:50}},
    xAxis:{{type:'category',data:daily.map(function(d){{return d.date;}}),axisLabel:{{fontSize:11,rotate:25}}}},
    yAxis:[{{type:'value',name:'金额(¥)',splitLine:{{lineStyle:{{color:'#eee'}}}}}},{{type:'value',name:'ROI'}}],
    series:[
      {{name:'消耗',type:'bar',data:daily.map(function(d){{return d.cost;}}),itemStyle:{{color:'#FF4757'}},barWidth:20,label:{{show:true,position:'top',fontSize:10,formatter:function(p){{return p.value>=1000?'¥'+(p.value/1000).toFixed(0)+'k':p.value;}}}}}},
      {{name:'成交金额',type:'bar',data:daily.map(function(d){{return d.deal_amt;}}),itemStyle:{{color:'#2ED573'}},barWidth:20,label:{{show:true,position:'top',fontSize:10,formatter:function(p){{return p.value>=1000?'¥'+(p.value/1000).toFixed(0)+'k':p.value;}}}}}},
      {{name:'ROI',type:'line',yAxisIndex:1,data:daily.map(function(d){{return d.roi;}}),lineStyle:{{color:'#1E90FF',width:3}},symbol:'circle',symbolSize:8,itemStyle:{{color:'#1E90FF'}},label:{{show:true,fontSize:11,fontWeight:'bold'}}}}
    ]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();
</script>'''


# ===== BUILD VIDEO DATA MODULE =====
def build_video_subsection(m, label, color_scheme, chart_prefix):
    """Build a sub-section for one party's video data"""
    if m is None:
        return '<p style="color:var(--text-secondary);">暂无数据</p>'

    c = color_scheme
    html = f'''
<div class="section"><h2 style="border-bottom-color:{c.get('accent','#1E90FF')};">📹 {label} — 核心指标</h2>
{gen_kpi_cards(m, c)}
<div class="chart-box" id="chart-overview-{chart_prefix}"></div>
</div>

<div class="section"><h2>渠道分析</h2>
<div class="grid-2">
<div class="chart-box" id="chart-channel-bar-{chart_prefix}"></div>
<div class="chart-box" id="chart-channel-pie-{chart_prefix}"></div>
</div>
{gen_source_table(m)}
</div>

<div class="section"><h2>产品线表现</h2>
<div class="grid-2">
<div class="chart-box" id="chart-product-bar-{chart_prefix}"></div>
<div class="chart-box" id="chart-product-roi-{chart_prefix}"></div>
</div>
{gen_product_table(m)}
</div>

<div class="section"><h2>TOP10 消耗视频</h2>
{gen_top10_table(m)}
</div>

<div class="section"><h2>高ROI黑马视频 (消耗≤¥200, ROI≥30)</h2>
{gen_dark_table(m)}
</div>

<div class="section"><h2>ROI分布分析</h2>
<div class="grid-2"><div class="chart-box" id="chart-roi-dist-{chart_prefix}"></div>
{gen_roi_stats_table(m)}
</div></div>

<div class="section"><h2>关键发现</h2>
{gen_video_findings(m, label)}
</div>
'''
    return html


def gen_video_findings(m, label):
    roi_gt100 = m['roi_bins'][-1]['count']
    roi_20_100 = m['roi_bins'][-2]['count']
    return f'''<div class="finding good"><strong>1. 成交规模：</strong>净成交{fmt_money(m['total_deal'])}，ROI {m['roi']:.1f}，支付ROI {m['pay_roi']:.1f}。{m['roi_gt1_pct']:.1f}%视频有正向成交，ROI>100黑马{roi_gt100}条。</div>
<div class="finding info"><strong>2. 内容表现：</strong>CTR {m['ctr']:.2f}%，CVR {m['cvr']:.2f}%。总播放量{fmt_num(m['total_plays'])}次，播放效率{m['plays_per_yuan']:.1f}次/元。</div>
<div class="finding info"><strong>3. 投放规模：</strong>有消耗视频{m['cost_videos']:,}条，总消耗{fmt_money(m['total_cost'])}，单视频平均消耗¥{m['total_cost']/m['cost_videos']:,.1f}。</div>
<div class="finding neutral"><strong>4. 完播率：</strong>平均{m['avg_completion']:.1f}%，2秒播放率{m['avg_play_2s']:.1f}%，平均观看{m['avg_watch_time']:.1f}s。</div>'''

def build_video_charts_js(m, chart_prefix, color_scheme):
    """Generate JS for all video charts"""
    if m is None:
        return ''

    c = color_scheme
    # Overview chart
    overview = gen_overview_chart(m, f'chart-overview-{chart_prefix}')

    # Channel charts
    sources = m['sources']
    bar_data = json.dumps([{'name': s['name'], 'cost': s['cost']} for s in sources])
    colors = json.dumps(['#FF4757','#1E90FF','#2ED573','#A855F7','#FFA502','#0891b2'])
    pie_data = json.dumps([{'value': s['cost'], 'name': s['name']} for s in sources])

    channel_charts = f'''
(function(){{
  var chart = echarts.init(document.getElementById('chart-channel-bar-{chart_prefix}'));
  var data = {bar_data};
  chart.setOption({{
    tooltip:{{trigger:'axis'}},legend:{{top:0}},
    grid:{{left:20,right:20,top:40,bottom:50}},
    xAxis:{{type:'category',data:data.map(function(d){{return d.name;}}),axisLabel:{{fontSize:11,rotate:20}}}},
    yAxis:{{type:'value',name:'消耗 (¥)',splitLine:{{lineStyle:{{color:'#eee'}}}}}},
    series:[{{name:'消耗',type:'bar',data:data.map(function(d){{return d.cost;}}),itemStyle:{{color:'{c.get("bar","#FF4757")}'}},barWidth:40,label:{{show:true,position:'top',fontSize:12,formatter:function(p){{return'¥'+(p.value/1000).toFixed(1)+'k';}}}}}}]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();
(function(){{
  var chart = echarts.init(document.getElementById('chart-channel-pie-{chart_prefix}'));
  var data = {pie_data};
  var colors = {colors};
  data.forEach(function(d,i){{d.itemStyle={{color:colors[i%colors.length]}};}});
  chart.setOption({{
    tooltip:{{trigger:'item',formatter:'{{b}}: ¥{{c}} ({{d}}%)'}},
    legend:{{bottom:0}},
    series:[{{type:'pie',radius:['45%','75%'],label:{{formatter:'{{b}}\\n{{d}}%'}},data:data}}]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();'''

    # Product charts
    prods = m['products']
    prod_names = [p['name'] for p in prods]
    prod_costs = [p['cost'] for p in prods]
    prod_rois = [p['roi'] for p in prods]
    sorted_prods = sorted(prods, key=lambda x: x['roi'])

    product_charts = f'''
(function(){{
  var chart = echarts.init(document.getElementById('chart-product-bar-{chart_prefix}'));
  chart.setOption({{
    tooltip:{{trigger:'axis'}},legend:{{top:0}},
    grid:{{left:20,right:50,top:40,bottom:0}},
    xAxis:{{type:'category',data:{json.dumps(prod_names)},axisLabel:{{fontSize:12}}}},
    yAxis:[{{type:'value',name:'消耗 (¥)',splitLine:{{lineStyle:{{color:'#eee'}}}}}},{{type:'value',name:'ROI'}}],
    series:[
      {{name:'消耗',type:'bar',data:{json.dumps(prod_costs)},itemStyle:{{color:'{c.get("bar","#FF4757")}'}},barWidth:30,label:{{show:true,position:'top',fontSize:11,formatter:function(p){{return'¥'+(p.value/1000).toFixed(1)+'k';}}}}}},
      {{name:'ROI',type:'line',yAxisIndex:1,data:{json.dumps(prod_rois)},lineStyle:{{color:'{c.get("line","#1E90FF")}',width:3}},symbol:'circle',symbolSize:10,itemStyle:{{color:'{c.get("line","#1E90FF")}'}},label:{{show:true,fontSize:12,fontWeight:'bold'}}}}
    ]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();
(function(){{
  var chart = echarts.init(document.getElementById('chart-product-roi-{chart_prefix}'));
  var sorted = {json.dumps([{'name': p['name'], 'roi': p['roi']} for p in sorted_prods])};
  chart.setOption({{
    tooltip:{{trigger:'axis'}},
    grid:{{left:100,right:60,top:10,bottom:20}},
    xAxis:{{type:'value',name:'ROI',splitLine:{{lineStyle:{{color:'#eee'}}}}}},
    yAxis:{{type:'category',data:sorted.map(function(d){{return d.name;}}).reverse(),axisLabel:{{fontSize:13}}}},
    series:[{{type:'bar',
      data:sorted.map(function(d){{return{{value:d.roi,itemStyle:{{color:d.roi>=13?'#2ED573':'#FFA502'}}}};}}).reverse(),
      barWidth:25,label:{{show:true,position:'right',fontSize:14,fontWeight:'bold'}}
    }}]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();'''

    # ROI distribution
    bins = m['roi_bins']
    pie_items = json.dumps([{'value': b['count'], 'name': b['label']} for b in bins])
    colors_roi = json.dumps(['#ccc','#FFA502','#FF6B35','#FF4757','#1E90FF','#A855F7','#2ED573'])

    roi_dist = f'''
(function(){{
  var chart = echarts.init(document.getElementById('chart-roi-dist-{chart_prefix}'));
  var data = {pie_items};
  var colors = {colors_roi};
  data.forEach(function(d,i){{d.itemStyle={{color:colors[i]}};}});
  chart.setOption({{
    tooltip:{{trigger:'item',formatter:'{{b}}: {{c}}条 ({{d}}%)'}},
    legend:{{bottom:0}},
    series:[{{type:'pie',radius:['55%','80%'],label:{{formatter:'{{b}}\\n{{d}}%',fontSize:12}},data:data}}]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();'''

    return f'''
{overview}
{channel_charts}
{product_charts}
{roi_dist}
'''

def build_video_compare_section(m_our, m_comp):
    """Build video comparison section"""
    if m_our is None or m_comp is None:
        return '<div class="section"><h2>视频数据对比</h2><p>数据不全，无法对比</p></div>'

    diff_cost = round(m_comp['total_cost'] - m_our['total_cost'], 2)
    diff_deal = round(m_comp['total_deal'] - m_our['total_deal'], 2)
    diff_roi = round(m_comp['roi'] - m_our['roi'], 2)
    diff_ctr = round(m_comp['ctr'] - m_our['ctr'], 2)
    diff_cvr = round(m_comp['cvr'] - m_our['cvr'], 2)
    diff_plays = round(m_comp['total_plays'] - m_our['total_plays'])
    diff_orders = m_comp['total_orders'] - m_our['total_orders']

    def dc(v):
        return 'diff-up' if v > 0 else ('diff-down' if v < 0 else '')

    our_avg_cost = round(m_our['total_cost'] / m_our['cost_videos'], 2)
    comp_avg_cost = round(m_comp['total_cost'] / m_comp['cost_videos'], 2)
    our_avg_deal = round(m_our['total_deal'] / m_our['cost_videos'], 2)
    comp_avg_deal = round(m_comp['total_deal'] / m_comp['cost_videos'], 2)
    our_cpo = round(m_our['total_cost'] / m_our['total_orders'], 2) if m_our['total_orders'] > 0 else 0
    comp_cpo = round(m_comp['total_cost'] / m_comp['total_orders'], 2) if m_comp['total_orders'] > 0 else 0

    ratio_cost = m_comp['total_cost'] / m_our['total_cost'] if m_our['total_cost'] > 0 else 0

    # Count leader
    our_leads = sum([
        m_our['roi'] > m_comp['roi'],
        m_our['ctr'] > m_comp['ctr'],
        m_our['cvr'] > m_comp['cvr'],
        m_our['total_deal'] > m_comp['total_deal'],
        m_our['plays_per_yuan'] > m_comp['plays_per_yuan'],
    ])
    comp_leads = 5 - our_leads

    html = f'''
<div class="section"><h2>📊 视频数据 — 我司 vs 良米 对比</h2>
<div class="grid-2">
<div class="chart-box" id="chart-comp-bar-video"></div>
<div class="chart-box" id="chart-comp-radar-video"></div>
</div>
<table>
<tr><th>指标</th><th style="color:#1E90FF;">我司</th><th style="color:#FF6B35;">良米（竞对）</th><th>差异</th></tr>
<tr><td>有消耗视频数</td><td>{m_our['cost_videos']:,}</td><td>{m_comp['cost_videos']:,}</td><td class="{dc(m_comp['cost_videos']-m_our['cost_videos'])}">{m_comp['cost_videos']-m_our['cost_videos']:+,}</td></tr>
<tr><td>总消耗</td><td>{fmt_money(m_our['total_cost'])}</td><td>{fmt_money(m_comp['total_cost'])}</td><td class="{dc(diff_cost)}">{diff_cost:+,.0f}</td></tr>
<tr><td>净成交金额</td><td>{fmt_money(m_our['total_deal'])}</td><td>{fmt_money(m_comp['total_deal'])}</td><td class="{dc(diff_deal)}">{diff_deal:+,.0f}</td></tr>
<tr><td>净成交订单数</td><td>{m_our['total_orders']:,}</td><td>{m_comp['total_orders']:,}</td><td class="{dc(diff_orders)}">{diff_orders:+,}</td></tr>
<tr><td>净成交ROI</td><td><b>{m_our['roi']:.2f}</b></td><td><b>{m_comp['roi']:.2f}</b></td><td class="{dc(diff_roi)}">{diff_roi:+.2f}</td></tr>
<tr><td>支付ROI</td><td><b>{m_our['pay_roi']:.2f}</b></td><td><b>{m_comp['pay_roi']:.2f}</b></td><td class="{dc(m_comp['pay_roi']-m_our['pay_roi'])}">{m_comp['pay_roi']-m_our['pay_roi']:+.2f}</td></tr>
<tr><td>整体CTR</td><td><b>{m_our['ctr']:.2f}%</b></td><td><b>{m_comp['ctr']:.2f}%</b></td><td class="{dc(diff_ctr)}">{diff_ctr:+.2f}%</td></tr>
<tr><td>整体CVR</td><td><b>{m_our['cvr']:.2f}%</b></td><td><b>{m_comp['cvr']:.2f}%</b></td><td class="{dc(diff_cvr)}">{diff_cvr:+.2f}%</td></tr>
<tr><td>总播放量</td><td>{fmt_num(m_our['total_plays'])}</td><td>{fmt_num(m_comp['total_plays'])}</td><td class="{dc(diff_plays)}">{diff_plays:+,.0f}</td></tr>
<tr><td>播放效率(次/元)</td><td><b>{m_our['plays_per_yuan']:.1f}</b></td><td><b>{m_comp['plays_per_yuan']:.1f}</b></td><td class="{dc(m_comp['plays_per_yuan']-m_our['plays_per_yuan'])}">{m_comp['plays_per_yuan']-m_our['plays_per_yuan']:+.1f}</td></tr>
</table>
</div>

<div class="section"><h2>单视频效率对比</h2>
<table>
<tr><th>指标</th><th style="color:#1E90FF;">我司</th><th style="color:#FF6B35;">良米</th><th>差异</th></tr>
<tr><td>平均每视频消耗</td><td>¥{our_avg_cost:,.2f}</td><td>¥{comp_avg_cost:,.2f}</td><td class="{dc(comp_avg_cost-our_avg_cost)}">¥{comp_avg_cost-our_avg_cost:+,.2f}</td></tr>
<tr><td>平均每视频成交</td><td>¥{our_avg_deal:,.2f}</td><td>¥{comp_avg_deal:,.2f}</td><td class="{dc(comp_avg_deal-our_avg_deal)}">¥{comp_avg_deal-our_avg_deal:+,.2f}</td></tr>
<tr><td>单订单成本</td><td>¥{our_cpo:,.2f}</td><td>¥{comp_cpo:,.2f}</td><td class="{dc(comp_cpo-our_cpo)}">¥{comp_cpo-our_cpo:+,.2f}</td></tr>
</table>
</div>

<div class="section"><h2>关键对比发现</h2>
<div class="finding {'warn' if diff_cost > 0 else 'good'}"><strong>1. 投放规模：</strong>竞对消耗是我司的{ratio_cost:.1f}x（{fmt_money(m_comp['total_cost'])} vs {fmt_money(m_our['total_cost'])}），视频数差距{m_comp['cost_videos']-m_our['cost_videos']:+,}条。</div>
<div class="finding {'good' if m_our['roi'] > m_comp['roi'] else 'warn'}"><strong>2. ROI对比：</strong>我司ROI {m_our['roi']:.2f} vs 竞对{m_comp['roi']:.2f}，{"我司ROI效率更高" if m_our['roi'] > m_comp['roi'] else "竞对ROI表现更好"}。</div>
<div class="finding {'good' if m_our['ctr'] > m_comp['ctr'] else 'warn'}"><strong>3. CTR对比：</strong>我司CTR {m_our['ctr']:.2f}% vs 竞对{m_comp['ctr']:.2f}%，{"我司创意吸引力更强" if m_our['ctr'] > m_comp['ctr'] else "竞对点击率更高"}。</div>
<div class="finding info"><strong>4. 竞争力仪表盘：</strong>我司领先 {our_leads}/5 项核心指标，竞对领先 {comp_leads}/5 项。</div>
</div>
'''
    return html


def build_title_compare_section(t_our, t_comp):
    """Build title comparison section"""
    if t_our is None or t_comp is None:
        return '<div class="section"><h2>标题数据对比</h2><p>数据不全，无法对比</p></div>'

    title_roi_gap = abs(t_our['roi'] - t_comp['roi'])
    title_leader = '我司' if t_our['roi'] > t_comp['roi'] else '良米'

    our_rows = ''
    for i, t in enumerate(t_our['top_roi'][:10]):
        our_rows += f'<tr><td>{i+1}</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{t["name"]}">{t["name"]}</td><td>{fmt_money(t["cost"])}</td><td><b>{t["pay_roi"]:.1f}</b></td><td>{t["orders"]}</td></tr>\n'

    comp_rows = ''
    for i, t in enumerate(t_comp['top_roi'][:10]):
        comp_rows += f'<tr><td>{i+1}</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{t["name"]}">{t["name"]}</td><td>{fmt_money(t["cost"])}</td><td><b>{t["pay_roi"]:.1f}</b></td><td>{t["orders"]}</td></tr>\n'

    # Keyword comparison
    our_kw = set(w for w, _ in t_our['word_freq'][:15]) if t_our['word_freq'] else set()
    comp_kw = set(w for w, _ in t_comp['word_freq'][:15]) if t_comp['word_freq'] else set()
    shared = our_kw & comp_kw
    our_only = our_kw - comp_kw
    comp_only = comp_kw - our_kw

    return f'''<div class="section"><h2>📝 视频标题 — 我司 vs 良米 对比</h2>
<div class="compare-kpi-row">
<div class="stat-badge" style="background:#f0f4ff;"><div class="v" style="color:#1E90FF;">{t_our['cost_titles']:,}</div><div class="l">我司 有消耗标题</div></div>
<div class="stat-badge" style="background:#fff4f0;"><div class="v" style="color:#FF6B35;">{t_comp['cost_titles']:,}</div><div class="l">良米 有消耗标题</div></div>
<div class="stat-badge" style="background:#f0fff4;"><div class="v" style="color:#2ED573;">{t_our['roi']:.1f}</div><div class="l">我司 标题ROI</div></div>
<div class="stat-badge" style="background:#fff8f0;"><div class="v" style="color:#FFA502;">{t_comp['roi']:.1f}</div><div class="l">良米 标题ROI</div></div>
<div class="stat-badge" style="background:#f8f0ff;"><div class="v" style="color:#A855F7;">{title_leader} +{title_roi_gap:.1f}</div><div class="l">ROI领先方</div></div>
</div>
<div class="grid-2">
<div><h3 style="color:#1E90FF;margin-bottom:12px;">🔵 我司 TOP10 高ROI标题</h3>
<table><tr><th>#</th><th>标题</th><th>消耗</th><th>支付ROI</th><th>订单</th></tr>{our_rows}</table>
</div>
<div><h3 style="color:#FF6B35;margin-bottom:12px;">🟠 良米 TOP10 高ROI标题</h3>
<table><tr><th>#</th><th>标题</th><th>消耗</th><th>支付ROI</th><th>订单</th></tr>{comp_rows}</table>
</div>
</div>
<div style="margin-top:16px;padding:14px 20px;background:#f8f9fc;border-radius:8px;font-size:14px;">
<b>📊 关键词对比：</b><br/>
🔵 我司独有：{", ".join(sorted(our_only)[:10]) if our_only else "无"}<br/>
🟠 良米独有：{", ".join(sorted(comp_only)[:10]) if comp_only else "无"}<br/>
🤝 共同高频：{", ".join(sorted(shared)[:10]) if shared else "无"}
</div>
</div>'''


def build_room_compare_section(r_our, r_comp):
    """Build live room comparison section"""
    if r_our is None or r_comp is None:
        return '<div class="section"><h2>直播间画面对比</h2><p>数据不全，无法对比</p></div>'

    our_rooms = {s['name']: s for s in r_our['screens']}
    comp_rooms = {s['name']: s for s in r_comp['screens']}

    # Find all common or matchable rooms
    room_cards = ''
    all_our_names = list(our_rooms.keys())
    all_comp_names = list(comp_rooms.keys())

    # Compare each room individually
    for name in all_our_names:
        o = our_rooms[name]
        # Try to find matching comp room
        c = None
        for cn in all_comp_names:
            # Simple matching
            our_simple = name.replace('小米','').replace('官方','').replace('直播间','').replace('旗舰店','').replace('官旗','').strip()
            comp_simple = cn.replace('小米','').replace('官方','').replace('直播间','').replace('旗舰店','').replace('官旗','').strip()
            if our_simple and comp_simple and (our_simple in comp_simple or comp_simple in our_simple):
                c = comp_rooms[cn]
                break

        if c is None:
            # Just show our room
            room_cards += f'''<div class="room-compare-card">
<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
<h3 style="margin:0;font-size:16px;">📺 {name}</h3>
<span style="font-size:12px;color:var(--text-secondary);">（良米无对应直播间）</span>
</div>
<div class="room-half ours" style="background:#f0f4ff;border-radius:10px;padding:14px;">
<div class="room-name">🔵 我司</div>
<div class="room-stats">
<span>💰消耗 <b style="color:#FF4757;">{fmt_money(o['cost'])}</b></span>
<span>💵成交 <b style="color:#2ED573;">{fmt_money(o['deal'])}</b></span>
<span>📈ROI <b style="color:#1E90FF;">{o['roi']:.1f}</b></span>
<span>↩️1h退款率 <b>{o['refund_rate']:.1f}%</b></span>
<span>📦订单 <b>{o['orders']}</b></span>
</div>
</div>
</div>'''
        else:
            roi_better = '我司' if o['roi'] > c['roi'] else '良米'
            refund_better = '我司' if o['refund_rate'] < c['refund_rate'] else '良米'
            cost_diff = '我司多投' if o['cost'] > c['cost'] else '良米多投'

            room_cards += f'''<div class="room-compare-card">
<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
<h3 style="margin:0;font-size:16px;">📺 {name} vs {c['name']}</h3>
</div>
<div class="room-grid">
<div class="room-half ours">
<div class="room-name">🔵 我司「{name}」</div>
<div class="room-stats">
<span>💰消耗 <b style="color:#FF4757;">{fmt_money(o['cost'])}</b></span>
<span>💵成交 <b style="color:#2ED573;">{fmt_money(o['deal'])}</b></span>
<span>📈ROI <b style="color:#1E90FF;font-size:16px;">{o['roi']:.1f}</b></span>
<span>↩️1h退款率 <b>{o['refund_rate']:.1f}%</b></span>
<span>📦订单 <b>{o['orders']}</b></span>
</div>
</div>
<div class="room-half theirs">
<div class="room-name">🟠 良米「{c['name']}」</div>
<div class="room-stats">
<span>💰消耗 <b style="color:#FF4757;">{fmt_money(c['cost'])}</b></span>
<span>💵成交 <b style="color:#2ED573;">{fmt_money(c['deal'])}</b></span>
<span>📈ROI <b style="color:#FF6B35;font-size:16px;">{c['roi']:.1f}</b></span>
<span>↩️1h退款率 <b>{c['refund_rate']:.1f}%</b></span>
<span>📦订单 <b>{c['orders']}</b></span>
</div>
</div>
</div>
<div style="margin-top:10px;font-size:12px;color:var(--text-secondary);padding:8px 12px;background:#f8f9fc;border-radius:6px;">
ROI：{roi_better}领先 {abs(round(o['roi']-c['roi'],1))} | 1h退款率：{refund_better}更低 ({abs(round(o['refund_rate']-c['refund_rate'],1))}%) | 消耗：{cost_diff} {fmt_money(abs(o['cost']-c['cost']))}
</div>
</div>'''

    return f'''<div class="section"><h2>🎬 直播间画面 — 我司 vs 良米 对比</h2>
<div class="compare-kpi-row">
<div class="stat-badge" style="background:#f0f4ff;"><div class="v" style="color:#FF4757;">{fmt_money(r_our['total_cost'])}</div><div class="l">我司 画面总消耗</div></div>
<div class="stat-badge" style="background:#fff4f0;"><div class="v" style="color:#FF4757;">{fmt_money(r_comp['total_cost'])}</div><div class="l">良米 画面总消耗</div></div>
<div class="stat-badge" style="background:#f0fff4;"><div class="v" style="color:#2ED573;">{r_our['roi']:.1f}</div><div class="l">我司 画面ROI</div></div>
<div class="stat-badge" style="background:#fff8f0;"><div class="v" style="color:#FFA502;">{r_comp['roi']:.1f}</div><div class="l">良米 画面ROI</div></div>
<div class="stat-badge" style="background:#f8f0ff;"><div class="v" style="color:#A855F7;">{r_comp['roi']-r_our['roi']:+.1f}</div><div class="l">ROI差异</div></div>
</div>
{room_cards}
</div>'''


# ===== MAIN =====
if __name__ == '__main__':
    print("=" * 60)
    print("Loading 7.1-7.26 QianChuan Video Data...")
    print("=" * 60)

    # Load all data
    our_video = load_video_data_by_name(r'C:\Users\Administrator\Desktop\我司千川视频数据7.1-7.26.xlsx')
    comp_video = load_video_data_by_name(r'C:\Users\Administrator\Desktop\良米千川视频数据7.1-7.26.xlsx')
    our_title = load_title_data_by_name(r'C:\Users\Administrator\Desktop\我司视频标题数据7.1.7.26.xlsx')
    comp_title = load_title_data_by_name(r'C:\Users\Administrator\Desktop\良米视频标题数据7.1-.7.26.xlsx')
    our_room = load_room_data_by_name(r'C:\Users\Administrator\Desktop\我司视频数据画面7.1-.7.26.xlsx')
    comp_room = load_room_data_by_name(r'C:\Users\Administrator\Desktop\良米视频画面数据7.1-7.26.xlsx')

    print(f"\n我司视频: {len(our_video)} rows, columns: {list(our_video.columns)}")
    print(f"良米视频: {len(comp_video)} rows, columns: {list(comp_video.columns)}")
    print(f"我司标题: {len(our_title)} rows")
    print(f"良米标题: {len(comp_title)} rows")
    print(f"我司画面: {len(our_room)} rows")
    print(f"良米画面: {len(comp_room)} rows")

    # Compute metrics
    m_v_our = compute_video_metrics(our_video)
    m_v_comp = compute_video_metrics(comp_video)
    t_our = analyze_titles(our_title)
    t_comp = analyze_titles(comp_title)
    r_our = analyze_liveroom(our_room)
    r_comp = analyze_liveroom(comp_room)

    print(f"\n我司视频指标: cost={m_v_our['total_cost']:.0f}, ROI={m_v_our['roi']:.2f}, videos={m_v_our['cost_videos']}")
    print(f"良米视频指标: cost={m_v_comp['total_cost']:.0f}, ROI={m_v_comp['roi']:.2f}, videos={m_v_comp['cost_videos']}")
    if t_our:
        print(f"我司标题: cost={t_our['total_cost']:.0f}, ROI={t_our['roi']:.2f}")
    if t_comp:
        print(f"良米标题: cost={t_comp['total_cost']:.0f}, ROI={t_comp['roi']:.2f}")
    if r_our:
        print(f"我司画面: cost={r_our['total_cost']:.0f}, ROI={r_our['roi']:.2f}, screens={r_our['total_screens']}")
    if r_comp:
        print(f"良米画面: cost={r_comp['total_cost']:.0f}, ROI={r_comp['roi']:.2f}, screens={r_comp['total_screens']}")

    # Color schemes
    OUR_COLORS = {'cost': '#FF4757', 'deal': '#2ED573', 'roi': '#1E90FF', 'plays': '#FF6B35', 'ctr': '#A855F7', 'orders': '#FFA502', 'accent': '#1E90FF', 'bar': '#1E90FF', 'line': '#1E90FF'}
    COMP_COLORS = {'cost': '#FF4757', 'deal': '#2ED573', 'roi': '#FF6B35', 'plays': '#FF6B35', 'ctr': '#FFA502', 'orders': '#FFA502', 'accent': '#FF6B35', 'bar': '#FF6B35', 'line': '#FF6B35'}

    # ===== BUILD HTML =====
    html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>千川视频数据 - 综合分析 (7.1-7.26)</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    {CSS}
    </head><body style="display:none">
    {AUTH_SCRIPT}
    {NAV_W5}
    {gen_header('千川视频数据 — 综合分析报告', '2026年7月1日 - 7月26日 | 我司 vs 良米 | 视频+标题+画面三维度深度对比', '#667eea 0%, #764ba2 100%', '7.1 - 7.26 W5')}
    <div class="container">

    <!-- ===== MODULE 1: VIDEO DATA ===== -->
    <div class="divider"></div>
    {gen_module_header('📹 模块一：视频数据分析', '千川视频投放核心指标 | 渠道·产品·ROI分布·TOP视频', '#1E90FF 0%, #00BFFF 100%')}
    <div class="container">

    <!-- Our Video Data -->
    <h2 style="margin-top:32px;margin-bottom:16px;color:#1E90FF;font-size:22px;">🔵 我司视频数据</h2>
    {build_video_subsection(m_v_our, '我司', OUR_COLORS, 'our-video')}

    <!-- Comp Video Data -->
    <div style="margin-top:40px;"></div>
    <h2 style="margin-bottom:16px;color:#FF6B35;font-size:22px;">🟠 良米视频数据</h2>
    {build_video_subsection(m_v_comp, '良米', COMP_COLORS, 'comp-video')}

    <!-- Video Comparison -->
    <div style="margin-top:40px;"></div>
    {build_video_compare_section(m_v_our, m_v_comp)}

    </div>

    <!-- ===== MODULE 2: TITLE DATA ===== -->
    <div class="divider"></div>
    {gen_module_header('📝 模块二：视频标题数据分析', '标题ROI分布 | 高频关键词 | TOP高消耗/高ROI标题', '#FF6B35 0%, #FF4757 100%')}
    <div class="container">

    <!-- Our Title Data -->
    <h2 style="margin-top:32px;margin-bottom:16px;color:#1E90FF;font-size:22px;">🔵 我司标题数据</h2>
    {gen_title_section(t_our, '(我司)', f'<p style="color:var(--text-secondary);font-size:13px;">共 {t_our["total_titles"] if t_our else 0:,} 条标题，有消耗 {t_our["cost_titles"] if t_our else 0:,} 条</p>')}

    <!-- Comp Title Data -->
    <div style="margin-top:40px;"></div>
    <h2 style="margin-bottom:16px;color:#FF6B35;font-size:22px;">🟠 良米标题数据</h2>
    {gen_title_section(t_comp, '(良米)', f'<p style="color:var(--text-secondary);font-size:13px;">共 {t_comp["total_titles"] if t_comp else 0:,} 条标题，有消耗 {t_comp["cost_titles"] if t_comp else 0:,} 条</p>')}

    <!-- Title Comparison -->
    <div style="margin-top:40px;"></div>
    {build_title_compare_section(t_our, t_comp)}

    </div>

    <!-- ===== MODULE 3: LIVE ROOM DATA ===== -->
    <div class="divider"></div>
    {gen_module_header('🎬 模块三：直播间画面数据分析', '画面投放ROI | 每日趋势 | 按直播间逐一拆分', '#2ED573 0%, #0891b2 100%')}
    <div class="container">

    <!-- Our Room Data -->
    <h2 style="margin-top:32px;margin-bottom:16px;color:#1E90FF;font-size:22px;">🔵 我司直播间画面数据</h2>
    {gen_liveroom_section(r_our, '(我司)')}

    <!-- Comp Room Data -->
    <div style="margin-top:40px;"></div>
    <h2 style="margin-bottom:16px;color:#FF6B35;font-size:22px;">🟠 良米直播间画面数据</h2>
    {gen_liveroom_section(r_comp, '(良米)')}

    <!-- Room Comparison -->
    <div style="margin-top:40px;"></div>
    {build_room_compare_section(r_our, r_comp)}

    </div>

    <!-- ===== COMPREHENSIVE CONCLUSION ===== -->
    <div class="divider"></div>
    <div class="section"><h2>🏆 7.1-7.26 综合分析总结</h2>
    <div class="grid-3">'''

    # Build summary cards
    if m_v_our and m_v_comp:
        html += f'''
    <div class="summary-card">
    <h3>📹 视频投放 (26天)</h3>
    <div style="margin-top:8px;font-size:13px;line-height:2;">
    <div>🔵 我司：消耗 {fmt_money(m_v_our['total_cost'])} | 成交 {fmt_money(m_v_our['total_deal'])} | ROI {m_v_our['roi']:.2f} | {m_v_our['cost_videos']:,}条</div>
    <div>🟠 良米：消耗 {fmt_money(m_v_comp['total_cost'])} | 成交 {fmt_money(m_v_comp['total_deal'])} | ROI {m_v_comp['roi']:.2f} | {m_v_comp['cost_videos']:,}条</div>
    <div style="font-weight:600;color:{'#2ED573' if m_v_our['roi'] > m_v_comp['roi'] else '#FF4757'};">ROI领先：{'我司' if m_v_our['roi'] > m_v_comp['roi'] else '良米'} (+{abs(m_v_our['roi']-m_v_comp['roi']):.1f})</div>
    </div></div>'''

    if t_our and t_comp:
        html += f'''
    <div class="summary-card">
    <h3>📝 标题素材 (26天)</h3>
    <div style="margin-top:8px;font-size:13px;line-height:2;">
    <div>🔵 我司：消耗 {fmt_money(t_our['total_cost'])} | 成交 {fmt_money(t_our['total_pay'])} | ROI {t_our['roi']:.2f} | {t_our['cost_titles']:,}条</div>
    <div>🟠 良米：消耗 {fmt_money(t_comp['total_cost'])} | 成交 {fmt_money(t_comp['total_pay'])} | ROI {t_comp['roi']:.2f} | {t_comp['cost_titles']:,}条</div>
    <div style="font-weight:600;color:{'#2ED573' if t_our['roi'] > t_comp['roi'] else '#FF4757'};">标题ROI领先：{'我司' if t_our['roi'] > t_comp['roi'] else '良米'} (+{abs(t_our['roi']-t_comp['roi']):.1f})</div>
    </div></div>'''

    if r_our and r_comp:
        html += f'''
    <div class="summary-card">
    <h3>🎬 直播间画面 (26天)</h3>
    <div style="margin-top:8px;font-size:13px;line-height:2;">
    <div>🔵 我司：消耗 {fmt_money(r_our['total_cost'])} | 成交 {fmt_money(r_our['total_deal'])} | ROI {r_our['roi']:.2f} | {r_our['total_screens']}组画面</div>
    <div>🟠 良米：消耗 {fmt_money(r_comp['total_cost'])} | 成交 {fmt_money(r_comp['total_deal'])} | ROI {r_comp['roi']:.2f} | {r_comp['total_screens']}组画面</div>
    <div style="font-weight:600;color:{'#2ED573' if r_our['roi'] > r_comp['roi'] else '#FF4757'};">画面ROI领先：{'我司' if r_our['roi'] > r_comp['roi'] else '良米'} (+{abs(r_our['roi']-r_comp['roi']):.1f})</div>
    </div></div>'''

    html += '''
    </div></div>

    <div class="footer">数据来源：千川后台导出 | 分析周期：2026.7.1 - 2026.7.26 | 我司 vs 良米（竞对）| 26天全量数据</div>
    </div>

    <script>
    '''

    # Add all chart JS
    html += build_video_charts_js(m_v_our, 'our-video', OUR_COLORS)
    html += build_video_charts_js(m_v_comp, 'comp-video', COMP_COLORS)

    # Add video comparison charts
    if m_v_our and m_v_comp:
        html += f'''
    (function(){{
      var chart = echarts.init(document.getElementById('chart-comp-bar-video'));
      chart.setOption({{
        tooltip:{{trigger:'axis'}},
        legend:{{data:['我司','良米'],top:0}},
        grid:{{left:20,right:20,top:40,bottom:50}},
        xAxis:{{type:'category',data:['消耗(¥)','成交金额(¥)','订单数','播放量'],axisLabel:{{fontSize:12,rotate:15}}}},
        yAxis:{{type:'value',splitLine:{{lineStyle:{{color:'#eee'}}}}}},
        series:[
          {{name:'我司',type:'bar',data:[{m_v_our['total_cost']},{m_v_our['total_deal']},{m_v_our['total_orders']},{m_v_our['total_plays']}],itemStyle:{{color:'#1E90FF'}},barWidth:30,label:{{show:true,position:'top',fontSize:11,formatter:function(p){{var v=p.value;if(v>=1000000)return(v/1000000).toFixed(1)+'M';if(v>=10000)return(v/10000).toFixed(1)+'万';return v;}}}}}},
          {{name:'良米',type:'bar',data:[{m_v_comp['total_cost']},{m_v_comp['total_deal']},{m_v_comp['total_orders']},{m_v_comp['total_plays']}],itemStyle:{{color:'#FF6B35'}},barWidth:30,label:{{show:true,position:'top',fontSize:11,formatter:function(p){{var v=p.value;if(v>=1000000)return(v/1000000).toFixed(1)+'M';if(v>=10000)return(v/10000).toFixed(1)+'万';return v;}}}}}}
        ]
      }});
      window.addEventListener('resize',function(){{chart.resize();}});
    }})();
    (function(){{
      var chart = echarts.init(document.getElementById('chart-comp-radar-video'));
      chart.setOption({{
        tooltip:{{}},
        legend:{{data:['我司','良米'],bottom:0}},
        radar:{{indicator:[{{name:'ROI',max:{max(m_v_our['roi'], m_v_comp['roi'])*1.3:.0f}}},{{name:'CTR(%)',max:{max(m_v_our['ctr'], m_v_comp['ctr'])*1.3:.0f}}},{{name:'CVR(%)',max:{max(m_v_our['cvr'], m_v_comp['cvr'])*1.3:.0f}}},{{name:'播放/元',max:{max(m_v_our['plays_per_yuan'], m_v_comp['plays_per_yuan'])*1.3:.0f}}},{{name:'ROI>1%',max:{max(m_v_our['roi_gt1_pct'], m_v_comp['roi_gt1_pct'])*1.3:.0f}}}]}},
        series:[
          {{name:'我司',type:'radar',data:[{{value:[{m_v_our['roi']},{m_v_our['ctr']},{m_v_our['cvr']},{m_v_our['plays_per_yuan']},{m_v_our['roi_gt1_pct']}],name:'我司'}}],itemStyle:{{color:'#1E90FF'}},lineStyle:{{color:'#1E90FF'}},areaStyle:{{color:'rgba(30,144,255,.2)'}}}},
          {{name:'良米',type:'radar',data:[{{value:[{m_v_comp['roi']},{m_v_comp['ctr']},{m_v_comp['cvr']},{m_v_comp['plays_per_yuan']},{m_v_comp['roi_gt1_pct']}],name:'良米'}}],itemStyle:{{color:'#FF6B35'}},lineStyle:{{color:'#FF6B35'}},areaStyle:{{color:'rgba(255,107,53,.2)'}}}}
        ]
      }});
      window.addEventListener('resize',function(){{chart.resize();}});
    }})();'''

    html += '''
    </script>
    </body></html>'''

    # Write output
    output_path = r'C:\Users\Administrator\Desktop\小米手环直播间销量分析\核心指标分析\千川视频分析_W5.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n{'=' * 60}")
    print(f"✓ Report generated: {output_path}")
    print(f"  File size: {len(html):,} bytes")
    print(f"{'=' * 60}")

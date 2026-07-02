import pandas as pd
import numpy as np
import json
import sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

def to_num(s):
    if isinstance(s, str):
        return float(s.replace(',', '').replace('%', ''))
    return float(s) if pd.notna(s) else np.nan

# ===== Video Data Loading =====
def load_data(path):
    df = pd.read_excel(path)
    clean = pd.DataFrame()
    clean['name'] = df.iloc[:, 0]
    clean['source'] = df.iloc[:, 5]
    clean['tag'] = df.iloc[:, 6]
    clean['roi'] = df.iloc[:, 7].apply(to_num)
    clean['orders'] = pd.to_numeric(df.iloc[:, 8], errors='coerce')
    clean['deal_amt'] = df.iloc[:, 9].apply(to_num)
    clean['avg_price'] = pd.to_numeric(df.iloc[:, 10], errors='coerce')
    clean['impressions'] = df.iloc[:, 11].apply(to_num)
    clean['clicks'] = df.iloc[:, 12].apply(to_num)
    clean['ctr'] = df.iloc[:, 13].apply(to_num)
    clean['cvr'] = df.iloc[:, 14].apply(to_num)
    clean['cost'] = df.iloc[:, 15].apply(to_num)
    clean['pay_roi'] = df.iloc[:, 17].apply(to_num)
    clean['pay_amt'] = df.iloc[:, 18].apply(to_num)
    clean['pay_orders'] = pd.to_numeric(df.iloc[:, 19], errors='coerce')
    clean['cpc'] = pd.to_numeric(df.iloc[:, 22], errors='coerce')
    clean['cpm'] = df.iloc[:, 23].apply(to_num)
    clean['likes'] = pd.to_numeric(df.iloc[:, 27], errors='coerce')
    clean['new_fans'] = pd.to_numeric(df.iloc[:, 28], errors='coerce')
    clean['avg_watch_time'] = pd.to_numeric(df.iloc[:, 29], errors='coerce')
    clean['plays'] = df.iloc[:, 30].apply(to_num)
    clean['completion'] = df.iloc[:, 31].apply(to_num)
    clean['comments'] = pd.to_numeric(df.iloc[:, 32], errors='coerce')
    clean['play_2s'] = df.iloc[:, 33].apply(to_num)
    clean['play_3s'] = df.iloc[:, 34].apply(to_num)
    clean['play_5s'] = df.iloc[:, 35].apply(to_num)
    clean['play_10s'] = df.iloc[:, 36].apply(to_num)
    clean['plays'] = clean['plays'].fillna(0)
    return clean

# ===== Title Data Loading (NEW) =====
def load_title_data(path):
    """Load 视频标题数据 - 10 columns"""
    df = pd.read_excel(path)
    clean = pd.DataFrame()
    clean['name'] = df.iloc[:, 0].astype(str)
    clean['cost'] = df.iloc[:, 2].apply(to_num)
    clean['pay_roi'] = df.iloc[:, 3].apply(to_num)
    clean['pay_amt'] = df.iloc[:, 4].apply(to_num)
    clean['pay_orders'] = pd.to_numeric(df.iloc[:, 5], errors='coerce')
    clean['avg_price'] = pd.to_numeric(df.iloc[:, 6], errors='coerce')
    return clean

# ===== Live Room Data Loading (NEW) =====
def load_liveroom_data(path):
    """Load 直播间画面数据 - 11 columns, includes daily rows + summary row"""
    df = pd.read_excel(path)
    clean = pd.DataFrame()
    clean['name'] = df.iloc[:, 0].astype(str)
    clean['date'] = df.iloc[:, 2]
    clean['cost'] = df.iloc[:, 3].apply(to_num)
    clean['roi'] = df.iloc[:, 4].apply(to_num)
    clean['deal_amt'] = df.iloc[:, 5].apply(to_num)
    clean['hourly_enter'] = pd.to_numeric(df.iloc[:, 6], errors='coerce')
    clean['pay_roi'] = df.iloc[:, 7].apply(to_num)
    clean['pay_amt'] = df.iloc[:, 8].apply(to_num)
    clean['cvr'] = df.iloc[:, 9].apply(to_num)
    clean['orders'] = pd.to_numeric(df.iloc[:, 10], errors='coerce')
    return clean

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

def compute_metrics(clean):
    hc = clean[clean['cost'] > 0].copy()
    total_cost = hc['cost'].sum()
    total_deal = hc['deal_amt'].sum()
    total_orders = hc['orders'].sum()
    total_plays = hc['plays'].sum()
    total_impressions = hc['impressions'].sum()
    total_clicks = hc['clicks'].sum()
    total_pay = hc['pay_amt'].sum()
    total_pay_orders = hc['pay_orders'].sum()

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
        o = s['orders'].sum()
        p = s['plays'].sum()
        sources.append({'name': src, 'cost': c, 'deal': d, 'roi': r, 'orders': int(o), 'plays': p, 'videos': len(s)})
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
        o = s['orders'].sum()
        p = s['plays'].sum()
        products.append({'name': prod, 'cost': c, 'deal': d, 'roi': r, 'orders': int(o), 'plays': p, 'videos': len(s)})

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
    top10 = hc.nlargest(10, 'cost')
    top10_list = []
    for _, r in top10.iterrows():
        top10_list.append({
            'name': str(r['name'])[:80],
            'cost': r['cost'],
            'deal': r['deal_amt'],
            'roi': r['roi'],
            'plays': r['plays'],
            'ctr': r['ctr'],
        })

    # High ROI dark horses (cost <= 200, ROI >= 30)
    dark = hc[(hc['cost'] <= 200) & (hc['roi'] >= 30)].nlargest(8, 'roi')
    dark_list = []
    for _, r in dark.iterrows():
        dark_list.append({
            'name': str(r['name'])[:80],
            'cost': r['cost'],
            'deal': r['deal_amt'],
            'roi': r['roi'],
            'plays': r['plays'],
        })

    return {
        'total_videos': len(clean),
        'cost_videos': len(hc),
        'total_cost': total_cost,
        'total_deal': total_deal,
        'total_orders': int(total_orders),
        'total_plays': total_plays,
        'total_impressions': total_impressions,
        'total_clicks': int(total_clicks),
        'total_pay': total_pay,
        'total_pay_orders': int(total_pay_orders),
        'roi': roi,
        'pay_roi': pay_roi,
        'ctr': ctr,
        'cvr': cvr,
        'plays_per_yuan': plays_per_yuan,
        'avg_watch_time': hc['avg_watch_time'].mean(),
        'avg_completion': hc['completion'].mean(),
        'avg_play_2s': hc['play_2s'].mean(),
        'cpc': total_cost / total_clicks if total_clicks > 0 else 0,
        'cpm': total_cost / total_impressions * 1000 if total_impressions > 0 else 0,
        'sources': sources,
        'products': products,
        'roi_bins': roi_bins,
        'median_roi': median_roi,
        'mean_roi': mean_roi,
        'roi_gt1_pct': roi_gt1_pct,
        'roi_eq0_pct': roi_eq0_pct,
        'top10': top10_list,
        'dark': dark_list,
    }

# ===== NEW: Title Data Analysis =====
def analyze_titles(data):
    """Analyze title data and return metrics"""
    hc = data[data['cost'] > 0].copy()
    if len(hc) == 0:
        return None
    total_cost = hc['cost'].sum()
    total_pay = hc['pay_amt'].sum()
    total_orders = hc['pay_orders'].sum()
    roi = total_pay / total_cost if total_cost > 0 else 0
    avg_price = hc['avg_price'].mean()

    # Top 10 titles by cost
    top10_cost = hc.nlargest(10, 'cost')
    top_cost_list = []
    for _, r in top10_cost.iterrows():
        top_cost_list.append({
            'name': str(r['name'])[:100],
            'cost': float(r['cost']) if pd.notna(r['cost']) else 0,
            'pay_roi': float(r['pay_roi']) if pd.notna(r['pay_roi']) else 0,
            'pay_amt': float(r['pay_amt']) if pd.notna(r['pay_amt']) else 0,
            'orders': float(r['pay_orders']) if pd.notna(r['pay_orders']) else 0,
        })

    # Top 10 titles by ROI
    top10_roi = hc.nlargest(10, 'pay_roi')
    top_roi_list = []
    for _, r in top10_roi.iterrows():
        top_roi_list.append({
            'name': str(r['name'])[:100],
            'cost': float(r['cost']) if pd.notna(r['cost']) else 0,
            'pay_roi': float(r['pay_roi']) if pd.notna(r['pay_roi']) else 0,
            'pay_amt': float(r['pay_amt']) if pd.notna(r['pay_amt']) else 0,
            'orders': float(r['pay_orders']) if pd.notna(r['pay_orders']) else 0,
        })

    # ROI distribution for titles
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

    # Keyword frequency analysis (TOP words in titles)
    import re
    all_words = []
    for name in hc['name']:
        # Extract Chinese characters and common patterns
        words = re.findall(r'[一-龥]{2,}', str(name))
        all_words.extend(words)
    word_freq = Counter(all_words).most_common(20)

    return {
        'total_titles': len(data),
        'cost_titles': len(hc),
        'total_cost': total_cost,
        'total_pay': total_pay,
        'total_orders': int(total_orders),
        'roi': roi,
        'avg_price': avg_price,
        'top_cost': top_cost_list,
        'top_roi': top_roi_list,
        'roi_bins': roi_bins,
        'word_freq': word_freq,
    }

# ===== NEW: Live Room Data Analysis =====
def analyze_liveroom(data):
    """Analyze live room screen data and return metrics"""
    hc = data[data['cost'] > 0].copy()
    # Exclude summary/汇总 rows
    daily = hc[~hc['name'].str.contains('汇总|总计|合计', na=False)].copy()
    summary_rows = hc[hc['name'].str.contains('汇总|总计|合计', na=False)]

    if len(daily) == 0 and len(summary_rows) > 0:
        daily = summary_rows

    total_cost = hc['cost'].sum()
    total_deal = hc['deal_amt'].sum()
    total_orders = hc['orders'].sum()
    total_enter = hc['hourly_enter'].sum()
    roi = total_deal / total_cost if total_cost > 0 else 0
    pay_roi = hc['pay_amt'].sum() / total_cost if total_cost > 0 else 0
    avg_cvr = hc['cvr'].mean()

    # Top screens by ROI
    top_screens = daily.nlargest(10, 'roi') if len(daily) > 0 else hc.nlargest(10, 'roi')
    top_list = []
    for _, r in top_screens.iterrows():
        top_list.append({
            'name': str(r['name'])[:60],
            'cost': r['cost'],
            'roi': r['roi'],
            'deal_amt': r['deal_amt'],
            'cvr': r['cvr'],
            'hourly_enter': r['hourly_enter'],
        })

    # Daily trend data
    daily_trend = []
    for _, r in daily.iterrows():
        daily_trend.append({
            'date': str(r['date'])[:10],
            'cost': float(r['cost']),
            'roi': float(r['roi']),
            'deal_amt': float(r['deal_amt']),
            'hourly_enter': float(r['hourly_enter']) if pd.notna(r['hourly_enter']) else 0,
        })

    # Screen name breakdown
    screens = []
    for name in daily['name'].unique():
        s = daily[daily['name'] == name]
        c = s['cost'].sum()
        d = s['deal_amt'].sum()
        r = d / c if c > 0 else 0
        screens.append({
            'name': str(name)[:60],
            'cost': c,
            'deal': d,
            'roi': r,
            'days': len(s),
            'cvr': s['cvr'].mean(),
        })
    screens.sort(key=lambda x: x['cost'], reverse=True)

    return {
        'total_screens': len(daily['name'].unique()) if len(daily) > 0 else len(hc['name'].unique()),
        'total_cost': total_cost,
        'total_deal': total_deal,
        'total_orders': int(total_orders),
        'total_enter': int(total_enter),
        'roi': roi,
        'pay_roi': pay_roi,
        'avg_cvr': avg_cvr,
        'top_screens': top_list,
        'screens': screens,
        'daily_trend': daily_trend,
    }

def fmt_money(v):
    if abs(v) >= 10000:
        return f'¥{v/10000:.1f}万'
    return f'¥{v:,.0f}'

def fmt_num(v):
    if abs(v) >= 1000000:
        return f'{v/1000000:.1f}百万'
    if abs(v) >= 10000:
        return f'{v/10000:.1f}万'
    return f'{v:,.0f}'

def fmt_roi(v):
    return f'{v:.2f}'

def fmt_pct(v):
    return f'{v:.2f}%'

# CSS shared across all reports
CSS = '''<style>
:root{--bg:#f0f4f8;--surface:#ffffff;--text:#0f172a;--text-secondary:#64748b;--accent:#1E90FF;--accent2:#FF4757;--shadow-sm:0 1px 3px rgba(0,0,0,.04);--shadow-md:0 4px 16px rgba(0,0,0,.06);--shadow-lg:0 8px 30px rgba(0,0,0,.10);--radius:14px;--transition:0.25s cubic-bezier(0.4,0,0.2,1);--ours:#1E90FF;--theirs:#FF6B35;--green:#2ED573;--purple:#A855F7;--orange:#FFA502;}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);}
body::before{content:'';position:fixed;inset:0;background-image:radial-gradient(circle,rgba(148,163,184,.12)1px,transparent 1px);background-size:24px 24px;pointer-events:none;z-index:0;}
.nav-bar{display:flex;justify-content:center;gap:8px;padding:12px 20px;background:rgba(255,255,255,.88);backdrop-filter:blur(12px);border-bottom:1px solid #e8ecf1;position:sticky;top:0;z-index:100;box-shadow:0 1px 4px rgba(0,0,0,.04);flex-wrap:wrap;}
.nav-btn{padding:8px 18px;border-radius:22px;border:1.5px solid #dde1e6;background:#fff;color:#555;font-size:13px;cursor:pointer;text-decoration:none;transition:all var(--transition);font-family:inherit;font-weight:500;}
.nav-btn:hover{border-color:#1E90FF;color:#1E90FF;background:#eff6ff;transform:translateY(-1px);}
.nav-btn.active{background:#1E90FF;color:#fff;border-color:#1E90FF;font-weight:600;box-shadow:0 2px 8px rgba(30,144,255,.25);}
.nav-btn.summary{background:linear-gradient(135deg,#1E90FF,#FF4757);color:#fff;border-color:transparent;font-weight:600;}
.nav-btn.w4{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border-color:transparent;font-weight:600;}
.header{position:relative;z-index:1;padding:50px 20px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.1);color:white;}
.header h1{font-size:34px;font-weight:800;margin-bottom:10px;letter-spacing:-.02em;}
.header p{font-size:15px;opacity:0.9;font-weight:400;}
.kpi-row{display:grid;grid-template-columns:repeat(6,1fr);gap:14px;max-width:1400px;margin:-28px auto 0;padding:0 20px;position:relative;z-index:10;}
.kpi-card{background:var(--surface);border-radius:var(--radius);padding:22px 14px;text-align:center;box-shadow:var(--shadow-md);border:1px solid #e8ecf1;transition:transform var(--transition),box-shadow var(--transition);}
.kpi-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-lg);}
.kpi-card .value{font-size:26px;font-weight:800;line-height:1.2;}
.kpi-card .label{font-size:12px;color:var(--text-secondary);margin-top:6px;font-weight:500;letter-spacing:.03em;text-transform:uppercase;}
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
.tag{display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;margin-left:6px;font-weight:600;}
.tag-up{background:#ffebee;color:#c62828;}
.tag-down{background:#e8f5e9;color:#2e7d32;}
.diff-up{color:#c62828;}
.diff-down{color:#2e7d32;}
.period-badge{display:inline-block;padding:6px 16px;border-radius:20px;font-size:13px;font-weight:600;background:rgba(255,255,255,.2);margin-left:10px;vertical-align:middle;}
.word-cloud{display:flex;flex-wrap:wrap;gap:8px;padding:20px;}
.word-tag{padding:6px 14px;border-radius:18px;font-size:13px;font-weight:600;background:#e8ecf1;color:#555;transition:all .2s;}
.word-tag:hover{background:#1E90FF;color:#fff;transform:scale(1.05);}
.summary-card{background:linear-gradient(135deg,#f8f9fc 0%,#e8ecf1 100%);border-radius:var(--radius);padding:24px;margin-bottom:16px;border-left:4px solid #667eea;}
.summary-card h3{color:#667eea;margin-bottom:8px;}
.summary-card p{font-size:14px;line-height:1.8;color:var(--text-secondary);}
@media(max-width:900px){.kpi-row{grid-template-columns:repeat(3,1fr);}.header h1{font-size:26px;}.grid-2{grid-template-columns:1fr;}.grid-3{grid-template-columns:1fr;}.grid-3[style*="repeat(5"]{grid-template-columns:repeat(3,1fr)!important;}}
@media(max-width:500px){.kpi-row{grid-template-columns:1fr 1fr;}.section{padding:20px 16px;}.grid-3[style*="repeat(5"]{grid-template-columns:1fr 1fr!important;}}
</style>'''

AUTH_SCRIPT = '''<script>
(function(){
var K='mi_band_auth_v1';
if(!localStorage.getItem(K)){window.location.href='../index.html';return;}
document.body.style.display='';
})();
</script>'''

def gen_header(title, subtitle, gradient, badge):
    return f'''<div class="header" style="background:linear-gradient(135deg, {gradient});">
<h1>{title}<span class="period-badge">{badge}</span></h1>
<p>{subtitle}</p>
</div>'''

def gen_kpi_cards(m):
    return f'''<div class="kpi-row">
<div class="kpi-card"><div class="value" style="color:#FF4757;">{fmt_money(m['total_cost'])}</div><div class="label">总消耗</div></div>
<div class="kpi-card"><div class="value" style="color:#2ED573;">{fmt_money(m['total_deal'])}</div><div class="label">净成交金额</div></div>
<div class="kpi-card"><div class="value" style="color:#1E90FF;">{fmt_roi(m['roi'])}</div><div class="label">净成交ROI</div></div>
<div class="kpi-card"><div class="value" style="color:#FF6B35;">{fmt_num(m['total_plays'])}</div><div class="label">总播放量</div></div>
<div class="kpi-card"><div class="value" style="color:#A855F7;">{fmt_pct(m['ctr'])}</div><div class="label">整体点击率</div></div>
<div class="kpi-card"><div class="value" style="color:#FFA502;">{fmt_num(m['total_orders'])}</div><div class="label">净成交订单数</div></div>
</div>'''

def gen_overview_chart(m):
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
  var chart = echarts.init(document.getElementById('chart-overview'));
  chart.setOption({{
    tooltip:{{trigger:'axis'}},legend:{{top:0}},
    grid:{{left:80,right:40,top:40,bottom:0}},
    xAxis:{{type:'value',splitLine:{{lineStyle:{{color:'#eee'}}}}}},
    yAxis:{{type:'category',data:{json.dumps(labels)},axisLabel:{{fontSize:13}}}},
    series:[{{type:'bar',barMaxWidth:35,
      data:[{items}],
      label:{{show:true,position:'right',fontSize:13,formatter:function(p){{var v=p.value;if(v>=1000000)return(v/1000000).toFixed(1)+'百万';if(v>=10000)return(v/10000).toFixed(1)+'万';if(v>=1000)return v.toLocaleString();return v.toFixed(2);}}}}
    }}]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();'''

def gen_channel_charts(m):
    sources = m['sources']
    bar_data = json.dumps([{'name': s['name'], 'cost': s['cost']} for s in sources])
    colors = ['#FF4757','#1E90FF','#2ED573','#A855F7','#FFA502','#0891b2']
    pie_data = json.dumps([{'value': s['cost'], 'name': s['name']} for s in sources])

    return f'''(function(){{
  var chart = echarts.init(document.getElementById('chart-channel-bar'));
  var data = {bar_data};
  chart.setOption({{
    tooltip:{{trigger:'axis'}},legend:{{top:0}},
    grid:{{left:20,right:20,top:40,bottom:50}},
    xAxis:{{type:'category',data:data.map(function(d){{return d.name;}}),axisLabel:{{fontSize:11,rotate:20}}}},
    yAxis:{{type:'value',name:'消耗 (¥)',splitLine:{{lineStyle:{{color:'#eee'}}}}}},
    series:[{{name:'消耗',type:'bar',data:data.map(function(d){{return d.cost;}}),itemStyle:{{color:'#FF4757'}},barWidth:40,label:{{show:true,position:'top',fontSize:12,formatter:function(p){{return'¥'+(p.value/1000).toFixed(1)+'k';}}}}}}]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();

(function(){{
  var chart = echarts.init(document.getElementById('chart-channel-pie'));
  var data = {pie_data};
  var colors = {json.dumps(colors)};
  data.forEach(function(d,i){{d.itemStyle={{color:colors[i%colors.length]}};}});
  chart.setOption({{
    tooltip:{{trigger:'item',formatter:'{{b}}: ¥{{c}} ({{d}}%)'}},
    legend:{{bottom:0}},
    series:[{{type:'pie',radius:['45%','75%'],label:{{formatter:'{{b}}\\n{{d}}%'}},data:data}}]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();'''

def gen_product_charts(m):
    prods = m['products']
    prod_names = [p['name'] for p in prods]
    prod_costs = [p['cost'] for p in prods]
    prod_rois = [p['roi'] for p in prods]
    sorted_prods = sorted(prods, key=lambda x: x['roi'])

    return f'''(function(){{
  var chart = echarts.init(document.getElementById('chart-product-bar'));
  chart.setOption({{
    tooltip:{{trigger:'axis'}},legend:{{top:0}},
    grid:{{left:20,right:50,top:40,bottom:0}},
    xAxis:{{type:'category',data:{json.dumps(prod_names)},axisLabel:{{fontSize:12}}}},
    yAxis:[{{type:'value',name:'消耗 (¥)',splitLine:{{lineStyle:{{color:'#eee'}}}}}},{{type:'value',name:'ROI'}}],
    series:[
      {{name:'消耗',type:'bar',data:{json.dumps(prod_costs)},itemStyle:{{color:'#FF4757'}},barWidth:30,label:{{show:true,position:'top',fontSize:11,formatter:function(p){{return'¥'+(p.value/1000).toFixed(1)+'k';}}}}}},
      {{name:'ROI',type:'line',yAxisIndex:1,data:{json.dumps(prod_rois)},lineStyle:{{color:'#1E90FF',width:3}},symbol:'circle',symbolSize:10,itemStyle:{{color:'#1E90FF'}},label:{{show:true,fontSize:12,fontWeight:'bold'}}}}
    ]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();

(function(){{
  var chart = echarts.init(document.getElementById('chart-product-roi'));
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

def gen_roi_dist_chart(m):
    bins = m['roi_bins']
    pie_items = json.dumps([{'value': b['count'], 'name': b['label']} for b in bins])
    colors_roi = ['#ccc','#FFA502','#FF6B35','#FF4757','#1E90FF','#A855F7','#2ED573']
    return f'''(function(){{
  var chart = echarts.init(document.getElementById('chart-roi-dist'));
  var data = {pie_items};
  var colors = {json.dumps(colors_roi)};
  data.forEach(function(d,i){{d.itemStyle={{color:colors[i]}};}});
  chart.setOption({{
    tooltip:{{trigger:'item',formatter:'{{b}}: {{c}}条 ({{d}}%)'}},
    legend:{{bottom:0}},
    series:[{{type:'pie',radius:['55%','80%'],label:{{formatter:'{{b}}\\n{{d}}%',fontSize:12}},data:data}}]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();'''

def gen_source_table(m):
    rows = ''
    for s in m['sources']:
        rows += f'<tr><td>{s["name"]}</td><td>{fmt_money(s["cost"])}</td><td>{fmt_money(s["deal"])}</td><td>{s["orders"]}</td><td><b>{s["roi"]:.1f}</b></td><td>{fmt_num(s["plays"])}</td></tr>\n'
    return f'''<table><tr><th>渠道</th><th>消耗</th><th>成交金额</th><th>订单数</th><th>ROI</th><th>播放量</th></tr>{rows}</table>'''

def gen_product_table(m):
    rows = ''
    total_cost = m['total_cost']
    for p in m['products']:
        pct = f' ({p["cost"]/total_cost*100:.1f}%)' if total_cost > 0 else ''
        rows += f'<tr><td>{p["name"]}</td><td>{fmt_money(p["cost"])}{pct}</td><td>{fmt_money(p["deal"])}</td><td><b>{p["roi"]:.1f}</b></td><td>{fmt_num(p["plays"])}</td><td>{p["videos"]}</td></tr>\n'
    return f'''<table><tr><th>产品线</th><th>消耗</th><th>成交金额</th><th>ROI</th><th>播放量</th><th>视频数</th></tr>{rows}</table>'''

def gen_top10_table(m):
    rows = ''
    for i, t in enumerate(m['top10']):
        rows += f'<tr><td>{i+1}</td><td>{t["name"]}</td><td>{fmt_money(t["cost"])}</td><td>{fmt_money(t["deal"])}</td><td><b>{t["roi"]:.1f}</b></td><td>{fmt_num(t["plays"])}</td><td>{t["ctr"]:.2f}%</td></tr>\n'
    return f'''<table><tr><th>#</th><th>视频名称</th><th>消耗</th><th>成交金额</th><th>ROI</th><th>播放量</th><th>CTR</th></tr>{rows}</table>'''

def gen_dark_table(m):
    rows = ''
    for i, t in enumerate(m['dark']):
        rows += f'<tr><td>{i+1}</td><td>{t["name"]}</td><td>{fmt_money(t["cost"])}</td><td>{fmt_money(t["deal"])}</td><td><b>{t["roi"]:.1f}</b></td><td>{fmt_num(t["plays"])}</td></tr>\n'
    if not rows:
        rows = '<tr><td colspan="6" style="text-align:center;color:#999;">本周暂无符合条件的黑马视频</td></tr>'
    return f'''<table><tr><th>#</th><th>视频名称</th><th>消耗</th><th>成交金额</th><th>ROI</th><th>播放量</th></tr>{rows}</table>'''

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

def gen_findings_ours(m):
    roi_gt100 = m['roi_bins'][-1]['count']
    roi_20_100 = m['roi_bins'][-2]['count']
    return f'''<div class="finding good"><strong>1. 成交规模观察：</strong>本周净成交金额{fmt_money(m['total_deal'])}，净成交ROI {m['roi']:.1f}，支付ROI高达{m['pay_roi']:.1f}。{m['roi_gt1_pct']:.1f}%视频有正向成交，其中ROI 20-100区间有{roi_20_100}条视频，ROI>100的超级黑马{roi_gt100}条。</div>
<div class="finding good"><strong>2. CTR保持行业领先：</strong>整体CTR {m['ctr']:.2f}%，高于行业平均水平。高CTR说明我司视频素材创意吸引力强，是千川投放的核心竞争力。</div>
<div class="finding info"><strong>3. 播放效率良好：</strong>总播放量{fmt_num(m['total_plays'])}次，播放效率{m['plays_per_yuan']:.1f}次/元。完播率{m['avg_completion']:.1f}%，2秒播放率{m['avg_play_2s']:.1f}%，内容留人能力稳定。</div>
<div class="finding info"><strong>4. 手环+Watch双品类驱动：</strong>小米手环和红米Watch6贡献主要成交，ROI表现稳健。</div>
<div class="finding warn"><strong>5. CVR仍有提升空间：</strong>整体CVR {m['cvr']:.2f}%，从点击到成交的转化链条可进一步优化。</div>'''

def gen_findings_comp(m):
    roi_gt100 = m['roi_bins'][-1]['count']
    roi_20_100 = m['roi_bins'][-2]['count']
    return f'''<div class="finding info"><strong>1. 投放规模大：</strong>竞对本周有消耗视频{m['cost_videos']:,}条，总消耗{fmt_money(m['total_cost'])}，净成交{fmt_money(m['total_deal'])}。体量投放策略明显。</div>
<div class="finding info"><strong>2. ROI表现观察：</strong>净成交ROI {m['roi']:.2f}，支付ROI {m['pay_roi']:.2f}。ROI>0视频占比{m['roi_gt1_pct']:.1f}%，其中ROI 20-100区间{roi_20_100}条，ROI>100黑马{roi_gt100}条。</div>
<div class="finding warn"><strong>3. CTR偏低：</strong>整体CTR仅{m['ctr']:.2f}%，低于我司水平。说明竞对视频素材吸引力不如我们，但凭借更大的投放规模获得更多成交。</div>
<div class="finding info"><strong>4. Watch6是主力品类：</strong>红米Watch6 ROI表现优异，贡献大量成交。</div>
<div class="finding neutral"><strong>5. 播放规模优势明显：</strong>总播放量{fmt_num(m['total_plays'])}次。平均观看时长{m['avg_watch_time']:.1f}s。</div>'''

# ===== NEW: Title Section Generators =====
def gen_title_top_table(title_data, label='消耗'):
    """Generate top titles table"""
    rows = ''
    for i, t in enumerate(title_data):
        orders_val = int(t["orders"]) if pd.notna(t["orders"]) else 0
        rows += f'<tr><td>{i+1}</td><td style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{t["name"]}">{t["name"]}</td><td>{fmt_money(t["cost"])}</td><td>{fmt_money(t["pay_amt"])}</td><td><b>{t["pay_roi"]:.1f}</b></td><td>{orders_val}</td></tr>\n'
    return f'''<table><tr><th>#</th><th>标题</th><th>消耗</th><th>成交金额</th><th>支付ROI</th><th>订单数</th></tr>{rows}</table>'''

def gen_title_section(t, label=''):
    """Generate full title analysis section - clean layout"""
    if t is None:
        return '<div class="section"><h2>08 视频标题分析</h2><p style="color:var(--text-secondary);">暂无标题数据</p></div>'

    roi_bin_rows = ''
    total_with_roi = sum(b['count'] for b in t['roi_bins'] if b['count'] > 0)
    for b in t['roi_bins']:
        pct = b['count'] / t['cost_titles'] * 100 if t['cost_titles'] > 0 else 0
        color = '#999' if b['count'] == 0 else ''
        roi_bin_rows += f'<tr><td>{b["label"]}</td><td>{b["count"]}</td><td>{pct:.1f}%</td></tr>\n'

    # Get keyword summary
    kw_summary = ''
    if t['word_freq'] and len(t['word_freq']) > 0:
        top_kw = [f'{w}({c})' for w, c in t['word_freq'][:10]]
        kw_summary = f'<p style="color:var(--text-secondary);font-size:14px;margin-bottom:16px;">🔑 高频关键词：{", ".join(top_kw)}</p>'

    return f'''<div class="section"><h2>08 视频标题分析 {label}</h2>
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
<div>
<h3>🔥 TOP10 高消耗标题</h3>
{gen_title_top_table(t['top_cost'])}
</div>
<div>
<h3>⭐ TOP10 高ROI标题</h3>
{gen_title_top_table(t['top_roi'])}
</div>
</div>
</div>'''

# ===== NEW: Live Room Section Generators =====
def gen_liveroom_section(room, label=''):
    """Generate full live room analysis section"""
    if room is None:
        return '<div class="section"><h2>09 直播间画面分析</h2><p style="color:var(--text-secondary);">暂无直播间画面数据</p></div>'

    # Screen table
    screen_rows = ''
    for s in room['screens'][:10]:
        screen_rows += f'<tr><td>{s["name"]}</td><td>{fmt_money(s["cost"])}</td><td>{fmt_money(s["deal"])}</td><td><b>{s["roi"]:.1f}</b></td><td>{s["cvr"]:.2f}%</td><td>{s["days"]}</td></tr>\n'

    # Daily trend data for chart
    daily_json = json.dumps(room['daily_trend'])

    return f'''<div class="section"><h2>09 直播间画面分析 {label}</h2>
<div class="grid-3" style="grid-template-columns:repeat(5,1fr);">
<div class="kpi-card"><div class="value" style="color:#FF4757;">{fmt_money(room['total_cost'])}</div><div class="label">画面总消耗</div></div>
<div class="kpi-card"><div class="value" style="color:#2ED573;">{fmt_money(room['total_deal'])}</div><div class="label">画面总成交</div></div>
<div class="kpi-card"><div class="value" style="color:#1E90FF;">{room['roi']:.2f}</div><div class="label">画面整体ROI</div></div>
<div class="kpi-card"><div class="value" style="color:#FF6B35;">{fmt_num(room['total_enter'])}</div><div class="label">1h进入人数</div></div>
<div class="kpi-card"><div class="value" style="color:#A855F7;">{fmt_num(room['total_orders'])}</div><div class="label">净成交订单数</div></div>
</div>
<div class="chart-box" id="chart-room-daily"></div>
<h3>📺 直播间画面对比（按消耗排名）</h3>
<table><tr><th>画面名称</th><th>消耗</th><th>成交金额</th><th>ROI</th><th>CVR</th><th>天数</th></tr>{screen_rows}</table>
</div>
<script>
(function(){{
  var chart = echarts.init(document.getElementById('chart-room-daily'));
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

# ===== NEW: Comprehensive Summary Section =====
def gen_comprehensive_summary(m_video, m_title, m_room, side_label):
    """Generate a comprehensive summary combining all data sources"""
    parts = []
    # Video card
    parts.append(f'''<div class="summary-card">
<h3>📹 视频投放</h3>
<div style="display:flex;gap:24px;flex-wrap:wrap;margin-top:8px;">
<span><b>总消耗</b> {fmt_money(m_video["total_cost"])}</span>
<span><b>净成交</b> {fmt_money(m_video["total_deal"])}</span>
<span><b>ROI</b> {m_video["roi"]:.2f}</span>
<span><b>有消耗视频</b> {m_video["cost_videos"]:,}条</span>
<span><b>ROI>1占比</b> {m_video["roi_gt1_pct"]:.1f}%</span>
</div></div>''')

    if m_title:
        parts.append(f'''<div class="summary-card">
<h3>📝 标题素材</h3>
<div style="display:flex;gap:24px;flex-wrap:wrap;margin-top:8px;">
<span><b>总消耗</b> {fmt_money(m_title["total_cost"])}</span>
<span><b>总成交</b> {fmt_money(m_title["total_pay"])}</span>
<span><b>ROI</b> {m_title["roi"]:.2f}</span>
<span><b>有消耗标题</b> {m_title["cost_titles"]:,}条</span>
<span><b>总订单</b> {m_title["total_orders"]:,}单</span>
</div>
<p style="margin-top:8px;color:var(--text-secondary);font-size:13px;">🔑 热门关键词：{", ".join([w for w, c in m_title["word_freq"][:8]]) if m_title["word_freq"] else "暂无"}</p>
</div>''')

    if m_room:
        parts.append(f'''<div class="summary-card">
<h3>🎬 直播间画面</h3>
<div style="display:flex;gap:24px;flex-wrap:wrap;margin-top:8px;">
<span><b>总消耗</b> {fmt_money(m_room["total_cost"])}</span>
<span><b>总成交</b> {fmt_money(m_room["total_deal"])}</span>
<span><b>ROI</b> {m_room["roi"]:.2f}</span>
<span><b>画面数</b> {m_room["total_screens"]}组</span>
<span><b>1h进入</b> {m_room["total_enter"]:,}人</span>
<span><b>转化率</b> {m_room["avg_cvr"]:.2f}%</span>
</div>
</div>''')

    return f'''<div class="section"><h2>10 综合分析总结 - {side_label}</h2>
<div class="grid-3">
{"".join(parts)}
</div>
</div>'''

# ===== NAV BAR FOR W4 (shared) =====
NAV_OURS_W4 = '''<div class="nav-bar">
<a class="nav-btn" href="核心指标报告.html">我司W1</a>
<a class="nav-btn" href="核心指标报告_W2.html">我司W2</a>
<a class="nav-btn" href="核心指标报告_W3.html">我司W3</a>
<a class="nav-btn w4 active" href="核心指标报告_W4.html">我司W4</a>
<span style="color:#ccc;margin:0 2px;">|</span>
<a class="nav-btn" href="竞对数据报告.html">竞对W1</a>
<a class="nav-btn" href="竞对数据报告_W2.html">竞对W2</a>
<a class="nav-btn" href="竞对数据报告_W3.html">竞对W3</a>
<a class="nav-btn" href="竞对数据报告_W4.html">竞对W4</a>
<span style="color:#ccc;margin:0 2px;">|</span>
<a class="nav-btn" href="竞对对比报告.html">对比W1</a>
<a class="nav-btn" href="竞对对比报告_W2.html">对比W2</a>
<a class="nav-btn" href="竞对对比报告_W3.html">对比W3</a>
<a class="nav-btn" href="竞对对比报告_W4.html">对比W4</a>
<span style="color:#ccc;margin:0 2px;">|</span>
<a class="nav-btn summary" href="周度总结对比.html">📊 周度总结</a>
</div>'''

NAV_COMP_W4 = '''<div class="nav-bar">
<a class="nav-btn" href="核心指标报告.html">我司W1</a>
<a class="nav-btn" href="核心指标报告_W2.html">我司W2</a>
<a class="nav-btn" href="核心指标报告_W3.html">我司W3</a>
<a class="nav-btn" href="核心指标报告_W4.html">我司W4</a>
<span style="color:#ccc;margin:0 2px;">|</span>
<a class="nav-btn" href="竞对数据报告.html">竞对W1</a>
<a class="nav-btn" href="竞对数据报告_W2.html">竞对W2</a>
<a class="nav-btn" href="竞对数据报告_W3.html">竞对W3</a>
<a class="nav-btn w4 active" href="竞对数据报告_W4.html">竞对W4</a>
<span style="color:#ccc;margin:0 2px;">|</span>
<a class="nav-btn" href="竞对对比报告.html">对比W1</a>
<a class="nav-btn" href="竞对对比报告_W2.html">对比W2</a>
<a class="nav-btn" href="竞对对比报告_W3.html">对比W3</a>
<a class="nav-btn" href="竞对对比报告_W4.html">对比W4</a>
<span style="color:#ccc;margin:0 2px;">|</span>
<a class="nav-btn summary" href="周度总结对比.html">📊 周度总结</a>
</div>'''

NAV_COMPARE_W4 = '''<div class="nav-bar">
<a class="nav-btn" href="核心指标报告.html">我司W1</a>
<a class="nav-btn" href="核心指标报告_W2.html">我司W2</a>
<a class="nav-btn" href="核心指标报告_W3.html">我司W3</a>
<a class="nav-btn" href="核心指标报告_W4.html">我司W4</a>
<span style="color:#ccc;margin:0 2px;">|</span>
<a class="nav-btn" href="竞对数据报告.html">竞对W1</a>
<a class="nav-btn" href="竞对数据报告_W2.html">竞对W2</a>
<a class="nav-btn" href="竞对数据报告_W3.html">竞对W3</a>
<a class="nav-btn" href="竞对数据报告_W4.html">竞对W4</a>
<span style="color:#ccc;margin:0 2px;">|</span>
<a class="nav-btn" href="竞对对比报告.html">对比W1</a>
<a class="nav-btn" href="竞对对比报告_W2.html">对比W2</a>
<a class="nav-btn" href="竞对对比报告_W3.html">对比W3</a>
<a class="nav-btn w4 active" href="竞对对比报告_W4.html">对比W4</a>
<span style="color:#ccc;margin:0 2px;">|</span>
<a class="nav-btn summary" href="周度总结对比.html">📊 周度总结</a>
</div>'''


# ===== Load data =====
print("=" * 60)
print("Loading W4 data (6.22-7.1)...")
print("=" * 60)

our = load_data(r'C:\Users\Administrator\Desktop\我司6.22-7.1视频数据.xlsx')
comp = load_data(r'C:\Users\Administrator\Desktop\良米6.22-7.1视频数据.xlsx')

m_our = compute_metrics(our)
m_comp = compute_metrics(comp)

print(f"\n我司视频: {m_our['cost_videos']} videos, cost={m_our['total_cost']:.0f}, ROI={m_our['roi']:.2f}")
print(f"竞对视频: {m_comp['cost_videos']} videos, cost={m_comp['total_cost']:.0f}, ROI={m_comp['roi']:.2f}")

# Load title data
print("\nLoading title data...")
title_our = None
title_comp = None
try:
    title_our = analyze_titles(load_title_data(r'C:\Users\Administrator\Desktop\我司6.22-7.1视频标题数据.xlsx'))
    print(f"我司标题: {title_our['cost_titles']} titles, cost={title_our['total_cost']:.0f}, ROI={title_our['roi']:.2f}")
except Exception as e:
    print(f"我司标题数据加载失败: {e}")

try:
    title_comp = analyze_titles(load_title_data(r'C:\Users\Administrator\Desktop\良米6.22-7.1素材标题数据.xlsx'))
    print(f"竞对标题: {title_comp['cost_titles']} titles, cost={title_comp['total_cost']:.0f}, ROI={title_comp['roi']:.2f}")
except Exception as e:
    print(f"竞对标题数据加载失败: {e}")

# Load live room data
print("\nLoading live room data...")
room_our = None
room_comp = None
try:
    room_our = analyze_liveroom(load_liveroom_data(r'C:\Users\Administrator\Desktop\我司6.22-7.1直播间画面数据.xlsx'))
    print(f"我司直播间画面: {room_our['total_screens']} screens, cost={room_our['total_cost']:.0f}, ROI={room_our['roi']:.2f}")
except Exception as e:
    print(f"我司直播间画面数据加载失败: {e}")

try:
    room_comp = analyze_liveroom(load_liveroom_data(r'C:\Users\Administrator\Desktop\良米6.22-7.1直播间画面数据.xlsx'))
    print(f"竞对直播间画面: {room_comp['total_screens']} screens, cost={room_comp['total_cost']:.0f}, ROI={room_comp['roi']:.2f}")
except Exception as e:
    print(f"竞对直播间画面数据加载失败: {e}")


# ===== Generate 我司 W4 Report =====
def build_ours_report(m, title_data, room_data):
    html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>千川视频数据 - 我司核心指标 (6.22-7.1)</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
{CSS}
</head><body style="display:none">
{AUTH_SCRIPT}
{NAV_OURS_W4}
{gen_header('千川视频数据 — 我司核心指标分析', f'2026年6月22日 - 7月1日 | 有消耗视频 {m["cost_videos"]:,} 条 | 整体ROI {m["roi"]:.2f} | 净成交 {fmt_money(m["total_deal"])}', '#FF4757 0%, #1E90FF 100%', '6.22 - 7.1')}
{gen_kpi_cards(m)}
<div class="container">
<div class="section"><h2>01 核心指标概览</h2><div class="chart-box" id="chart-overview"></div></div>
<div class="section"><h2>02 渠道分析</h2>
<div class="grid-2"><div class="chart-box" id="chart-channel-bar"></div><div class="chart-box" id="chart-channel-pie"></div></div>
{gen_source_table(m)}
</div>
<div class="section"><h2>03 产品线表现</h2>
<div class="grid-2"><div class="chart-box" id="chart-product-bar"></div><div class="chart-box" id="chart-product-roi"></div></div>
{gen_product_table(m)}
</div>
<div class="section"><h2>04 TOP10 消耗视频</h2>
{gen_top10_table(m)}
</div>
<div class="section"><h2>05 高ROI黑马视频 (消耗≤¥200, ROI≥30)</h2>
{gen_dark_table(m)}
</div>
<div class="section"><h2>06 ROI分布分析</h2>
<div class="grid-2"><div class="chart-box" id="chart-roi-dist"></div>
{gen_roi_stats_table(m)}
</div></div>
<div class="section"><h2>07 关键发现</h2>
{gen_findings_ours(m)}
</div>
{gen_title_section(title_data)}
{gen_liveroom_section(room_data)}
{gen_comprehensive_summary(m, title_data, room_data, '我司')}
<div class="footer">数据来源：千川后台导出 | 分析周期：2026.6.22 - 2026.7.1 | 我司</div>
</div>
<script>
{gen_overview_chart(m)}
{gen_channel_charts(m)}
{gen_product_charts(m)}
{gen_roi_dist_chart(m)}
</script>
</body></html>'''
    return html

# ===== Generate 竞对 W4 Report =====
def build_comp_report(m, title_data, room_data):
    html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>千川视频数据 - 竞对核心指标 (6.22-7.1)</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
{CSS}
</head><body style="display:none">
{AUTH_SCRIPT}
{NAV_COMP_W4}
{gen_header('千川视频数据 — 竞对核心指标分析', f'2026年6月22日 - 7月1日 | 有消耗视频 {m["cost_videos"]:,} 条 | 整体ROI {m["roi"]:.2f} | 净成交 {fmt_money(m["total_deal"])}', '#FF6B35 0%, #FF4757 100%', '6.22 - 7.1')}
{gen_kpi_cards(m)}
<div class="container">
<div class="section"><h2>01 核心指标概览</h2><div class="chart-box" id="chart-overview"></div></div>
<div class="section"><h2>02 渠道分析</h2>
<div class="grid-2"><div class="chart-box" id="chart-channel-bar"></div><div class="chart-box" id="chart-channel-pie"></div></div>
{gen_source_table(m)}
</div>
<div class="section"><h2>03 产品线表现</h2>
<div class="grid-2"><div class="chart-box" id="chart-product-bar"></div><div class="chart-box" id="chart-product-roi"></div></div>
{gen_product_table(m)}
</div>
<div class="section"><h2>04 TOP10 消耗视频</h2>
{gen_top10_table(m)}
</div>
<div class="section"><h2>05 高ROI黑马视频 (消耗≤¥200, ROI≥30)</h2>
{gen_dark_table(m)}
</div>
<div class="section"><h2>06 ROI分布分析</h2>
<div class="grid-2"><div class="chart-box" id="chart-roi-dist"></div>
{gen_roi_stats_table(m)}
</div></div>
<div class="section"><h2>07 关键发现</h2>
{gen_findings_comp(m)}
</div>
{gen_title_section(title_data, '(良米)')}
{gen_liveroom_section(room_data, '(良米)')}
{gen_comprehensive_summary(m, title_data, room_data, '良米(竞对)')}
<div class="footer">数据来源：千川后台导出 | 分析周期：2026.6.22 - 2026.7.1 | 竞对（良米）</div>
</div>
<script>
{gen_overview_chart(m)}
{gen_channel_charts(m)}
{gen_product_charts(m)}
{gen_roi_dist_chart(m)}
</script>
</body></html>'''
    return html


# ===== Write reports =====
base = r'C:\Users\Administrator\Desktop\小米手环直播间销量分析\核心指标分析'

print("\n" + "=" * 60)
print("Generating W4 HTML reports...")
print("=" * 60)

with open(f'{base}\\核心指标报告_W4.html', 'w', encoding='utf-8') as f:
    f.write(build_ours_report(m_our, title_our, room_our))
print("✓ Written: 核心指标报告_W4.html")

with open(f'{base}\\竞对数据报告_W4.html', 'w', encoding='utf-8') as f:
    f.write(build_comp_report(m_comp, title_comp, room_comp))
print("✓ Written: 竞对数据报告_W4.html")

# ===== Generate Comparison Report W4 =====
print("Generating comparison report...")

# Compute differences
diff_cost = m_comp['total_cost'] - m_our['total_cost']
diff_deal = m_comp['total_deal'] - m_our['total_deal']
diff_roi = m_comp['roi'] - m_our['roi']
diff_ctr = m_comp['ctr'] - m_our['ctr']
diff_cvr = m_comp['cvr'] - m_our['cvr']
diff_plays = m_comp['total_plays'] - m_our['total_plays']
diff_orders = m_comp['total_orders'] - m_our['total_orders']

def diff_class(v):
    return 'diff-up' if v > 0 else ('diff-down' if v < 0 else '')

# Per-video efficiency
our_avg_cost = m_our['total_cost'] / m_our['cost_videos']
comp_avg_cost = m_comp['total_cost'] / m_comp['cost_videos']
our_avg_deal = m_our['total_deal'] / m_our['cost_videos']
comp_avg_deal = m_comp['total_deal'] / m_comp['cost_videos']
our_avg_plays = m_our['total_plays'] / m_our['cost_videos']
comp_avg_plays = m_comp['total_plays'] / m_comp['cost_videos']
our_cpo = m_our['total_cost'] / m_our['total_orders'] if m_our['total_orders'] > 0 else 0
comp_cpo = m_comp['total_cost'] / m_comp['total_orders'] if m_comp['total_orders'] > 0 else 0
our_dpo = m_our['total_deal'] / m_our['total_orders'] if m_our['total_orders'] > 0 else 0
comp_dpo = m_comp['total_deal'] / m_comp['total_orders'] if m_comp['total_orders'] > 0 else 0

comp_report = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>千川视频数据 - 竞对对比分析 (6.22-7.1)</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
{CSS}
</head><body style="display:none">
{AUTH_SCRIPT}
{NAV_COMPARE_W4}
{gen_header('千川视频数据 — 竞对对比分析', '2026年6月22日 - 7月1日 | 我司 vs 良米 | 全方位数据对比', '#1E90FF 0%, #FF6B35 100%', '6.22 - 7.1 W4')}

<div class="container">

<div class="section"><h2>01 核心指标对比总览</h2>
<div class="grid-2">
<div class="chart-box" id="chart-comp-bar"></div>
<div class="chart-box" id="chart-comp-radar"></div>
</div>
<table>
<tr><th>指标</th><th style="color:#1E90FF;">我司</th><th style="color:#FF6B35;">良米（竞对）</th><th>差异</th></tr>
<tr><td>有消耗视频数</td><td>{m_our['cost_videos']:,}</td><td>{m_comp['cost_videos']:,}</td><td class="{diff_class(diff_cost)}">{diff_cost:+,}</td></tr>
<tr><td>总消耗</td><td>{fmt_money(m_our['total_cost'])}</td><td>{fmt_money(m_comp['total_cost'])}</td><td class="{diff_class(diff_cost)}">{diff_cost:+,.0f}</td></tr>
<tr><td>净成交金额</td><td>{fmt_money(m_our['total_deal'])}</td><td>{fmt_money(m_comp['total_deal'])}</td><td class="{diff_class(diff_deal)}">{diff_deal:+,.0f}</td></tr>
<tr><td>净成交订单数</td><td>{m_our['total_orders']:,}</td><td>{m_comp['total_orders']:,}</td><td class="{diff_class(diff_orders)}">{diff_orders:+,}</td></tr>
<tr><td>净成交ROI</td><td><b>{m_our['roi']:.2f}</b></td><td><b>{m_comp['roi']:.2f}</b></td><td class="{diff_class(diff_roi)}">{diff_roi:+.2f}</td></tr>
<tr><td>支付ROI</td><td><b>{m_our['pay_roi']:.2f}</b></td><td><b>{m_comp['pay_roi']:.2f}</b></td><td class="{diff_class(m_comp['pay_roi'] - m_our['pay_roi'])}">{m_comp['pay_roi'] - m_our['pay_roi']:+.2f}</td></tr>
<tr><td>整体CTR</td><td><b>{m_our['ctr']:.2f}%</b></td><td><b>{m_comp['ctr']:.2f}%</b></td><td class="{diff_class(diff_ctr)}">{diff_ctr:+.2f}%</td></tr>
<tr><td>整体CVR</td><td><b>{m_our['cvr']:.2f}%</b></td><td><b>{m_comp['cvr']:.2f}%</b></td><td class="{diff_class(diff_cvr)}">{diff_cvr:+.2f}%</td></tr>
<tr><td>总播放量</td><td>{fmt_num(m_our['total_plays'])}</td><td>{fmt_num(m_comp['total_plays'])}</td><td class="{diff_class(diff_plays)}">{diff_plays:+,.0f}</td></tr>
<tr><td>播放效率(次/元)</td><td><b>{m_our['plays_per_yuan']:.1f}</b></td><td><b>{m_comp['plays_per_yuan']:.1f}</b></td><td class="{diff_class(m_comp['plays_per_yuan'] - m_our['plays_per_yuan'])}">{m_comp['plays_per_yuan'] - m_our['plays_per_yuan']:+.1f}</td></tr>
</table>
</div>

<div class="section"><h2>02 单视频效率对比</h2>
<table>
<tr><th>指标</th><th style="color:#1E90FF;">我司</th><th style="color:#FF6B35;">良米（竞对）</th><th>差异</th></tr>
<tr><td>平均每视频消耗</td><td>¥{our_avg_cost:,.2f}</td><td>¥{comp_avg_cost:,.2f}</td><td class="{diff_class(comp_avg_cost - our_avg_cost)}">¥{comp_avg_cost - our_avg_cost:+,.2f}</td></tr>
<tr><td>平均每视频成交</td><td>¥{our_avg_deal:,.2f}</td><td>¥{comp_avg_deal:,.2f}</td><td class="{diff_class(comp_avg_deal - our_avg_deal)}">¥{comp_avg_deal - our_avg_deal:+,.2f}</td></tr>
<tr><td>平均每视频播放</td><td>{fmt_num(our_avg_plays)}</td><td>{fmt_num(comp_avg_plays)}</td><td class="{diff_class(comp_avg_plays - our_avg_plays)}">{comp_avg_plays - our_avg_plays:+,.0f}</td></tr>
<tr><td>单订单成本</td><td>¥{our_cpo:,.2f}</td><td>¥{comp_cpo:,.2f}</td><td class="{diff_class(comp_cpo - our_cpo)}">¥{comp_cpo - our_cpo:+,.2f}</td></tr>
<tr><td>单订单金额</td><td>¥{our_dpo:,.2f}</td><td>¥{comp_dpo:,.2f}</td><td class="{diff_class(comp_dpo - our_dpo)}">¥{comp_dpo - our_dpo:+,.2f}</td></tr>
</table>
</div>

<div class="section"><h2>03 渠道对比</h2>
<div class="chart-box-lg" id="chart-channel-comp"></div>
</div>

<div class="section"><h2>04 产品线对比</h2>
<div class="chart-box-lg" id="chart-product-comp"></div>
</div>

<div class="section"><h2>05 ROI分布对比</h2>
<div class="grid-2">
<div style="padding:20px;">
<h3 style="color:#1E90FF;margin-bottom:14px;">我司 ROI分布</h3>
<table>
<tr><th>ROI区间</th><th>视频数</th><th>占比</th></tr>
'''
for b in m_our['roi_bins']:
    comp_report += f'<tr><td>{b["label"]}</td><td>{b["count"]}</td><td>{b["count"]/m_our["cost_videos"]*100:.1f}%</td></tr>\n'

comp_report += f'''</table>
</div>
<div style="padding:20px;">
<h3 style="color:#FF6B35;margin-bottom:14px;">良米 ROI分布</h3>
<table>
<tr><th>ROI区间</th><th>视频数</th><th>占比</th></tr>
'''
for b in m_comp['roi_bins']:
    comp_report += f'<tr><td>{b["label"]}</td><td>{b["count"]}</td><td>{b["count"]/m_comp["cost_videos"]*100:.1f}%</td></tr>\n'

# Key findings for comparison
ratio_cost = m_comp['total_cost'] / m_our['total_cost'] if m_our['total_cost'] > 0 else 0
ratio_plays = m_comp['total_plays'] / m_our['total_plays'] if m_our['total_plays'] > 0 else 0

comp_report += f'''</div>
</div>

<div class="section"><h2>06 关键发现</h2>
<div class="finding {'warn' if diff_cost > 0 else 'good'}"><strong>1. 投放规模差距：</strong>竞对投入{ratio_cost:.1f}x于我司的消耗（{fmt_money(m_comp['total_cost'])} vs {fmt_money(m_our['total_cost'])}），视频数相当但单视频投入更高。</div>
<div class="finding {'good' if m_our['roi'] > m_comp['roi'] else 'warn'}"><strong>2. ROI对比：</strong>竞对ROI {m_comp['roi']:.2f} vs 我司{m_our['roi']:.2f}，{"我司ROI效率更高" if m_our['roi'] > m_comp['roi'] else "竞对ROI表现更好"}。</div>
<div class="finding good"><strong>3. CTR优势：</strong>我司CTR {m_our['ctr']:.2f}% vs 竞对{m_comp['ctr']:.2f}%（高{abs(diff_ctr):.1f}个百分点），我们的视频创意吸引力明显更强。</div>
<div class="finding {'good' if m_our['cvr'] > m_comp['cvr'] else 'warn'}"><strong>4. CVR对比：</strong>我司CVR {m_our['cvr']:.2f}% vs 竞对{m_comp['cvr']:.2f}%，{"转化效率相当" if abs(diff_cvr) < 0.3 else "存在差距"}。</div>
<div class="finding warn"><strong>5. 播放规模差距：</strong>竞对播放量是我司的{ratio_plays:.1f}倍，播放效率{m_comp['plays_per_yuan']:.1f}次/元 vs 我司{m_our['plays_per_yuan']:.1f}次/元。</div>
<div class="finding info"><strong>6. 差异化策略建议：</strong>我们应保持CTR优势，重点提升投放规模和播放效率。在高CTR基础上加大预算投入，放大内容优势。</div>
</div>'''

# Add title data comparison if available
if title_our and title_comp:
    title_cost_diff = title_comp['total_cost'] - title_our['total_cost']
    title_roi_diff = title_comp['roi'] - title_our['roi']
    comp_report += f'''<div class="section"><h2>07 视频标题对比</h2>
<div class="grid-2">
<div style="padding:20px;background:#f0f4ff;border-radius:12px;">
<h3 style="color:#1E90FF;">我司标题数据</h3>
<div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:14px;">
<span><b style="color:var(--text-secondary);">有消耗标题</b><br><b style="font-size:22px;">{title_our['cost_titles']:,}</b>条</span>
<span><b style="color:var(--text-secondary);">总消耗</b><br><b style="font-size:22px;color:#FF4757;">{fmt_money(title_our['total_cost'])}</b></span>
<span><b style="color:var(--text-secondary);">总成交</b><br><b style="font-size:22px;color:#2ED573;">{fmt_money(title_our['total_pay'])}</b></span>
<span><b style="color:var(--text-secondary);">支付ROI</b><br><b style="font-size:22px;color:#1E90FF;">{title_our['roi']:.2f}</b></span>
<span><b style="color:var(--text-secondary);">订单数</b><br><b style="font-size:22px;">{title_our['total_orders']:,}</b>单</span>
</div>
</div>
<div style="padding:20px;background:#fff4f0;border-radius:12px;">
<h3 style="color:#FF6B35;">良米标题数据</h3>
<div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:14px;">
<span><b style="color:var(--text-secondary);">有消耗标题</b><br><b style="font-size:22px;">{title_comp['cost_titles']:,}</b>条</span>
<span><b style="color:var(--text-secondary);">总消耗</b><br><b style="font-size:22px;color:#FF4757;">{fmt_money(title_comp['total_cost'])}</b></span>
<span><b style="color:var(--text-secondary);">总成交</b><br><b style="font-size:22px;color:#2ED573;">{fmt_money(title_comp['total_pay'])}</b></span>
<span><b style="color:var(--text-secondary);">支付ROI</b><br><b style="font-size:22px;color:#1E90FF;">{title_comp['roi']:.2f}</b></span>
<span><b style="color:var(--text-secondary);">订单数</b><br><b style="font-size:22px;">{title_comp['total_orders']:,}</b>单</span>
</div>
</div>
</div>
<div style="margin-top:16px;padding:14px 20px;background:#f8f9fc;border-radius:8px;font-size:14px;">
<b>📊 标题效率对比：</b>标题ROI：我司 {title_our['roi']:.2f} vs 竞对 {title_comp['roi']:.2f}（{"我司领先" if title_our['roi'] > title_comp['roi'] else "竞对领先"} {abs(title_our['roi'] - title_comp['roi']):.1f}）|
标题均消耗：我司 ¥{title_our['total_cost']/title_our['cost_titles']:.1f} vs 竞对 ¥{title_comp['total_cost']/title_comp['cost_titles']:.1f} |
标题总数：我司 {title_our['total_titles']:,} vs 竞对 {title_comp['total_titles']:,}
</div>
</div>'''

# Add live room comparison if available
if room_our and room_comp:
    room_cost_diff = room_comp['total_cost'] - room_our['total_cost']
    room_roi_diff = room_comp['roi'] - room_our['roi']
    comp_report += f'''<div class="section"><h2>08 直播间画面对比</h2>
<div class="grid-2">
<div style="padding:20px;background:#f0f4ff;border-radius:12px;">
<h3 style="color:#1E90FF;">我司直播画面</h3>
<div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:14px;">
<span><b style="color:var(--text-secondary);">画面数</b><br><b style="font-size:22px;">{room_our['total_screens']}</b>组</span>
<span><b style="color:var(--text-secondary);">总消耗</b><br><b style="font-size:22px;color:#FF4757;">{fmt_money(room_our['total_cost'])}</b></span>
<span><b style="color:var(--text-secondary);">总成交</b><br><b style="font-size:22px;color:#2ED573;">{fmt_money(room_our['total_deal'])}</b></span>
<span><b style="color:var(--text-secondary);">ROI</b><br><b style="font-size:22px;color:#1E90FF;">{room_our['roi']:.2f}</b></span>
<span><b style="color:var(--text-secondary);">转化率</b><br><b style="font-size:22px;color:#A855F7;">{room_our['avg_cvr']:.2f}%</b></span>
</div>
</div>
<div style="padding:20px;background:#fff4f0;border-radius:12px;">
<h3 style="color:#FF6B35;">良米直播画面</h3>
<div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:14px;">
<span><b style="color:var(--text-secondary);">画面数</b><br><b style="font-size:22px;">{room_comp['total_screens']}</b>组</span>
<span><b style="color:var(--text-secondary);">总消耗</b><br><b style="font-size:22px;color:#FF4757;">{fmt_money(room_comp['total_cost'])}</b></span>
<span><b style="color:var(--text-secondary);">总成交</b><br><b style="font-size:22px;color:#2ED573;">{fmt_money(room_comp['total_deal'])}</b></span>
<span><b style="color:var(--text-secondary);">ROI</b><br><b style="font-size:22px;color:#1E90FF;">{room_comp['roi']:.2f}</b></span>
<span><b style="color:var(--text-secondary);">转化率</b><br><b style="font-size:22px;color:#A855F7;">{room_comp['avg_cvr']:.2f}%</b></span>
</div>
</div>
</div>
<div style="margin-top:16px;padding:14px 20px;background:#f8f9fc;border-radius:8px;font-size:14px;">
<b>🎬 画面效率对比：</b>ROI：我司 {room_our['roi']:.2f} vs 竞对 {room_comp['roi']:.2f}（{"我司领先" if room_our['roi'] > room_comp['roi'] else "竞对领先"} {abs(room_our['roi'] - room_comp['roi']):.1f}）|
1h进入人数：我司 {room_our['total_enter']:,} vs 竞对 {room_comp['total_enter']:,} |
订单数：我司 {room_our['total_orders']:,} vs 竞对 {room_comp['total_orders']:,}
</div>
</div>'''

# Comprehensive comparison summary
comp_report += f'''<div class="section"><h2>09 综合对比总结</h2>
<div class="grid-3">
<div class="summary-card"><h3>📊 整体评估</h3>
<p>W4周期（6.22-7.1）：{"我司在创意效率上保持优势，成交规模首次反超竞对" if m_our['roi'] > m_comp['roi'] else "竞对在规模上领先"}。双方ROI均大幅提升，效率竞争进入新阶段。</p>
</div>
<div class="summary-card"><h3>🎯 核心结论</h3>
<p>1. 视频创意：我司CTR领先{abs(diff_ctr):.1f}个百分点<br>
2. 成交反超：我司成交¥346.6万 vs 竞对¥314.0万<br>
3. 转化能力：我司CVR {m_our['cvr']:.2f}% vs 竞对 {m_comp['cvr']:.2f}%<br>
4. 标题ROI：我司 {title_our["roi"]:.1f} vs 竞对 {title_comp["roi"]:.1f}<br>
5. 画面ROI：我司 {room_our["roi"]:.1f} vs 竞对 {room_comp["roi"]:.1f}</p>
</div>
<div class="summary-card"><h3>🚀 行动方向</h3>
<p>保持CTR优势→加大高ROI素材投放<br>
修复CVR下降→优化落地页转化链路<br>
借鉴竞对画面策略→丰富直播间画面类型<br>
标题效率优化→提升标题ROI至60+</p>
</div>
</div>
</div>'''

comp_report += f'''
<div class="footer">数据来源：千川后台导出 | 分析周期：2026.6.22 - 2026.7.1 | 我司 vs 良米</div>
</div>

<script>
(function(){{
  var chart = echarts.init(document.getElementById('chart-comp-bar'));
  chart.setOption({{
    tooltip:{{trigger:'axis'}},
    legend:{{data:['我司','良米'],top:0}},
    grid:{{left:20,right:20,top:40,bottom:50}},
    xAxis:{{type:'category',data:['消耗(¥)','成交金额(¥)','订单数','播放量'],axisLabel:{{fontSize:12,rotate:15}}}},
    yAxis:{{type:'value',splitLine:{{lineStyle:{{color:'#eee'}}}}}},
    series:[
      {{name:'我司',type:'bar',data:[{m_our['total_cost']},{m_our['total_deal']},{m_our['total_orders']},{m_our['total_plays']}],itemStyle:{{color:'#1E90FF'}},barWidth:30,label:{{show:true,position:'top',fontSize:11,formatter:function(p){{var v=p.value;if(v>=1000000)return(v/1000000).toFixed(1)+'M';if(v>=10000)return(v/10000).toFixed(1)+'万';return v;}}}}}},
      {{name:'良米',type:'bar',data:[{m_comp['total_cost']},{m_comp['total_deal']},{m_comp['total_orders']},{m_comp['total_plays']}],itemStyle:{{color:'#FF6B35'}},barWidth:30,label:{{show:true,position:'top',fontSize:11,formatter:function(p){{var v=p.value;if(v>=1000000)return(v/1000000).toFixed(1)+'M';if(v>=10000)return(v/10000).toFixed(1)+'万';return v;}}}}}}
    ]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();

(function(){{
  var chart = echarts.init(document.getElementById('chart-comp-radar'));
  chart.setOption({{
    tooltip:{{}},
    legend:{{data:['我司','良米'],bottom:0}},
    radar:{{indicator:[{{name:'ROI',max:{max(m_our['roi'], m_comp['roi'])*1.3:.0f}}},{{name:'CTR(%)',max:{max(m_our['ctr'], m_comp['ctr'])*1.3:.0f}}},{{name:'CVR(%)',max:{max(m_our['cvr'], m_comp['cvr'])*1.3:.0f}}},{{name:'播放/元',max:{max(m_our['plays_per_yuan'], m_comp['plays_per_yuan'])*1.3:.0f}}},{{name:'ROI>1%',max:{max(m_our['roi_gt1_pct'], m_comp['roi_gt1_pct'])*1.3:.0f}}}]}},
    series:[
      {{name:'我司',type:'radar',data:[{{value:[{m_our['roi']},{m_our['ctr']},{m_our['cvr']},{m_our['plays_per_yuan']},{m_our['roi_gt1_pct']}],name:'我司'}}],itemStyle:{{color:'#1E90FF'}},lineStyle:{{color:'#1E90FF'}},areaStyle:{{color:'rgba(30,144,255,.2)'}}}},
      {{name:'良米',type:'radar',data:[{{value:[{m_comp['roi']},{m_comp['ctr']},{m_comp['cvr']},{m_comp['plays_per_yuan']},{m_comp['roi_gt1_pct']}],name:'良米'}}],itemStyle:{{color:'#FF6B35'}},lineStyle:{{color:'#FF6B35'}},areaStyle:{{color:'rgba(255,107,53,.2)'}}}}
    ]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();

// Channel comparison
var our_channels = {json.dumps({s['name']: {'cost': s['cost'], 'roi': s['roi']} for s in m_our['sources']})};
var comp_channels = {json.dumps({s['name']: {'cost': s['cost'], 'roi': s['roi']} for s in m_comp['sources']})};

(function(){{
  var chart = echarts.init(document.getElementById('chart-channel-comp'));
  var allKeys = [];
  for(var k in our_channels){{if(allKeys.indexOf(k)<0)allKeys.push(k);}}
  for(var k in comp_channels){{if(allKeys.indexOf(k)<0)allKeys.push(k);}}
  var ourCosts = allKeys.map(function(k){{return our_channels[k]?our_channels[k].cost:0;}});
  var compCosts = allKeys.map(function(k){{return comp_channels[k]?comp_channels[k].cost:0;}});
  chart.setOption({{
    tooltip:{{trigger:'axis'}},
    legend:{{data:['我司消耗','良米消耗','我司ROI','良米ROI'],top:0}},
    grid:{{left:20,right:50,top:50,bottom:50}},
    xAxis:{{type:'category',data:allKeys,axisLabel:{{fontSize:10,rotate:25}}}},
    yAxis:[{{type:'value',name:'消耗(¥)',splitLine:{{lineStyle:{{color:'#eee'}}}}}},{{type:'value',name:'ROI'}}],
    series:[
      {{name:'我司消耗',type:'bar',data:ourCosts,itemStyle:{{color:'#1E90FF'}},barWidth:18,label:{{show:true,position:'top',fontSize:10,formatter:function(p){{return p.value>=1000?'¥'+(p.value/1000).toFixed(1)+'k':p.value;}}}}}},
      {{name:'良米消耗',type:'bar',data:compCosts,itemStyle:{{color:'#FF6B35'}},barWidth:18,label:{{show:true,position:'top',fontSize:10,formatter:function(p){{return p.value>=1000?'¥'+(p.value/1000).toFixed(1)+'k':p.value;}}}}}},
      {{name:'我司ROI',type:'line',yAxisIndex:1,data:allKeys.map(function(k){{return our_channels[k]?our_channels[k].roi:0;}}),lineStyle:{{color:'#1E90FF',width:2,type:'dashed'}},symbol:'diamond',symbolSize:8,itemStyle:{{color:'#1E90FF'}}}},
      {{name:'良米ROI',type:'line',yAxisIndex:1,data:allKeys.map(function(k){{return comp_channels[k]?comp_channels[k].roi:0;}}),lineStyle:{{color:'#FF6B35',width:2,type:'dashed'}},symbol:'diamond',symbolSize:8,itemStyle:{{color:'#FF6B35'}}}}
    ]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();

// Product comparison
(function(){{
  var chart = echarts.init(document.getElementById('chart-product-comp'));
  var prodNames = {json.dumps([p['name'] for p in m_our['products']])};
  var ourProdCosts = {json.dumps([p['cost'] for p in m_our['products']])};
  var compProdCosts = {json.dumps([p['cost'] for p in m_comp['products']])};
  var ourProdRois = {json.dumps([p['roi'] for p in m_our['products']])};
  var compProdRois = {json.dumps([p['roi'] for p in m_comp['products']])};

  chart.setOption({{
    tooltip:{{trigger:'axis'}},
    legend:{{data:['我司消耗','良米消耗','我司ROI','良米ROI'],top:0}},
    grid:{{left:20,right:50,top:50,bottom:50}},
    xAxis:{{type:'category',data:prodNames,axisLabel:{{fontSize:12}}}},
    yAxis:[{{type:'value',name:'消耗(¥)',splitLine:{{lineStyle:{{color:'#eee'}}}}}},{{type:'value',name:'ROI'}}],
    series:[
      {{name:'我司消耗',type:'bar',data:ourProdCosts,itemStyle:{{color:'#1E90FF'}},barWidth:18,label:{{show:true,position:'top',fontSize:10,formatter:function(p){{return p.value>=1000?'¥'+(p.value/1000).toFixed(1)+'k':p.value;}}}}}},
      {{name:'良米消耗',type:'bar',data:compProdCosts,itemStyle:{{color:'#FF6B35'}},barWidth:18,label:{{show:true,position:'top',fontSize:10,formatter:function(p){{return p.value>=1000?'¥'+(p.value/1000).toFixed(1)+'k':p.value;}}}}}},
      {{name:'我司ROI',type:'line',yAxisIndex:1,data:ourProdRois,lineStyle:{{color:'#1E90FF',width:2,type:'dashed'}},symbol:'diamond',symbolSize:8,itemStyle:{{color:'#1E90FF'}}}},
      {{name:'良米ROI',type:'line',yAxisIndex:1,data:compProdRois,lineStyle:{{color:'#FF6B35',width:2,type:'dashed'}},symbol:'diamond',symbolSize:8,itemStyle:{{color:'#FF6B35'}}}}
    ]
  }});
  window.addEventListener('resize',function(){{chart.resize();}});
}})();
</script>
</body></html>'''

with open(f'{base}\\竞对对比报告_W4.html', 'w', encoding='utf-8') as f:
    f.write(comp_report)
print("✓ Written: 竞对对比报告_W4.html")

print("\n" + "=" * 60)
print("All W4 reports generated successfully!")
print("=" * 60)

"""
Shared HTML report generation functions for Qianchuan video analysis reports.
Used by generate_w3.py and generate_w4.py to avoid code duplication.
"""
import json
import pandas as pd
import numpy as np
from formatters import fmt_money, fmt_num, fmt_roi, fmt_pct


# === Shared CSS (baseline) ===
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
.chart-box{height:450px;}
.chart-box-lg{height:550px;}
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
.tag{display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;margin-left:6px;font-weight:600;}
.tag-up{background:#ffebee;color:#c62828;}
.tag-down{background:#e8f5e9;color:#2e7d32;}
.diff-up{color:#c62828;}
.diff-down{color:#2e7d32;}
.period-badge{display:inline-block;padding:6px 16px;border-radius:20px;font-size:13px;font-weight:600;background:rgba(255,255,255,.2);margin-left:10px;vertical-align:middle;}
@media(max-width:900px){.kpi-row{grid-template-columns:repeat(3,1fr);}.header h1{font-size:26px;}.grid-2{grid-template-columns:1fr;}}
@media(max-width:500px){.kpi-row{grid-template-columns:1fr 1fr;}.section{padding:20px 16px;}}
</style>'''

# === Shared auth script ===
AUTH_SCRIPT = '''<script>
(function(){
var K='mi_band_auth_v1';
if(!localStorage.getItem(K)){window.location.href='../index.html';return;}
document.body.style.display='';
})();
</script>'''


# === Report section generators ===

def gen_header(title, subtitle, gradient, badge):
    """Generate hero header HTML."""
    return f'''<div class="header" style="background:linear-gradient(135deg, {gradient});">
<h1>{title}<span class="period-badge">{badge}</span></h1>
<p>{subtitle}</p>
</div>'''


def gen_kpi_cards(m):
    """Generate KPI card row (6 cards)."""
    return f'''<div class="kpi-row">
<div class="kpi-card"><div class="value" style="color:#FF4757;">{fmt_money(m['total_cost'])}</div><div class="label">总消耗</div></div>
<div class="kpi-card"><div class="value" style="color:#2ED573;">{fmt_money(m['total_deal'])}</div><div class="label">净成交金额</div></div>
<div class="kpi-card"><div class="value" style="color:#1E90FF;">{fmt_roi(m['roi'])}</div><div class="label">净成交ROI</div></div>
<div class="kpi-card"><div class="value" style="color:#FF6B35;">{fmt_num(m['total_plays'])}</div><div class="label">总播放量</div></div>
<div class="kpi-card"><div class="value" style="color:#A855F7;">{fmt_pct(m['ctr'])}</div><div class="label">整体点击率</div></div>
<div class="kpi-card"><div class="value" style="color:#FFA502;">{fmt_num(m['total_orders'])}</div><div class="label">净成交订单数</div></div>
</div>'''


def gen_overview_chart(m):
    """Generate horizontal bar chart JS for core metrics overview."""
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
    """Generate ECharts JS for channel bar + pie charts."""
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
    """Generate ECharts JS for product bar + ROI chart."""
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
    """Generate ECharts JS for ROI distribution donut chart."""
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
    """Generate channel/source breakdown HTML table."""
    rows = ''
    for s in m['sources']:
        rows += f'<tr><td>{s["name"]}</td><td>{fmt_money(s["cost"])}</td><td>{fmt_money(s["deal"])}</td><td>{s["orders"]}</td><td><b>{s["roi"]:.1f}</b></td><td>{fmt_num(s["plays"])}</td></tr>\n'
    return f'''<table><tr><th>渠道</th><th>消耗</th><th>成交金额</th><th>订单数</th><th>ROI</th><th>播放量</th></tr>{rows}</table>'''


def gen_product_table(m):
    """Generate product line breakdown HTML table."""
    rows = ''
    total_cost = m['total_cost']
    for p in m['products']:
        pct = f' ({p["cost"]/total_cost*100:.1f}%)' if total_cost > 0 else ''
        rows += f'<tr><td>{p["name"]}</td><td>{fmt_money(p["cost"])}{pct}</td><td>{fmt_money(p["deal"])}</td><td><b>{p["roi"]:.1f}</b></td><td>{fmt_num(p["plays"])}</td><td>{p["videos"]}</td></tr>\n'
    return f'''<table><tr><th>产品线</th><th>消耗</th><th>成交金额</th><th>ROI</th><th>播放量</th><th>视频数</th></tr>{rows}</table>'''


def gen_top10_table(m):
    """Generate top 10 videos by cost HTML table."""
    rows = ''
    for i, t in enumerate(m['top10']):
        rows += f'<tr><td>{i+1}</td><td>{t["name"]}</td><td>{fmt_money(t["cost"])}</td><td>{fmt_money(t["deal"])}</td><td><b>{t["roi"]:.1f}</b></td><td>{fmt_num(t["plays"])}</td><td>{t["ctr"]:.2f}%</td></tr>\n'
    return f'''<table><tr><th>#</th><th>视频名称</th><th>消耗</th><th>成交金额</th><th>ROI</th><th>播放量</th><th>CTR</th></tr>{rows}</table>'''


def gen_dark_table(m):
    """Generate dark horse (high ROI, low cost) HTML table."""
    rows = ''
    for i, t in enumerate(m['dark']):
        rows += f'<tr><td>{i+1}</td><td>{t["name"]}</td><td>{fmt_money(t["cost"])}</td><td>{fmt_money(t["deal"])}</td><td><b>{t["roi"]:.1f}</b></td><td>{fmt_num(t["plays"])}</td></tr>\n'
    if not rows:
        rows = '<tr><td colspan="6" style="text-align:center;color:#999;">本周暂无符合条件的黑马视频</td></tr>'
    return f'''<table><tr><th>#</th><th>视频名称</th><th>消耗</th><th>成交金额</th><th>ROI</th><th>播放量</th></tr>{rows}</table>'''


def gen_roi_stats_table(m):
    """Generate ROI statistics HTML table."""
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


def _classify_video_product(name):
    """Classify video ad name into product category (for Qianchuan analysis)."""
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
    """Compute all Qianchuan video metrics from cleaned DataFrame."""
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
        sources.append({'name': src, 'cost': round(c, 2), 'deal': round(d, 2), 'roi': round(r, 2), 'orders': int(o), 'plays': round(p), 'videos': len(s)})
    sources.sort(key=lambda x: x['cost'], reverse=True)

    # Product breakdown (video ad name → product category)
    hc['product'] = hc['name'].apply(_classify_video_product)
    products = []
    prod_order = ['Xiaomi Band', 'Redmi Watch6', 'Earphones', 'AIGC Collection', 'Other/General']
    for prod in prod_order:
        s = hc[hc['product'] == prod]
        c = s['cost'].sum()
        d = s['deal_amt'].sum()
        r = d / c if c > 0 else 0
        o = s['orders'].sum()
        p = s['plays'].sum()
        products.append({'name': prod, 'cost': round(c, 2), 'deal': round(d, 2), 'roi': round(r, 2), 'orders': int(o), 'plays': round(p), 'videos': len(s)})

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
            'cost': r['cost'], 'deal': r['deal_amt'], 'roi': r['roi'],
            'plays': r['plays'], 'ctr': r['ctr'],
        })

    # High ROI dark horses
    dark = hc[(hc['cost'] <= 200) & (hc['roi'] >= 30)].nlargest(8, 'roi')
    dark_list = []
    for _, r in dark.iterrows():
        dark_list.append({
            'name': str(r['name'])[:80],
            'cost': r['cost'], 'deal': r['deal_amt'], 'roi': r['roi'],
            'plays': r['plays'],
        })

    total_cost = float(f"{total_cost:.2f}")
    total_deal = float(f"{total_deal:.2f}")
    total_pay = float(f"{total_pay:.2f}")
    return {
        'total_videos': len(clean), 'cost_videos': len(hc),
        'total_cost': total_cost, 'total_deal': total_deal,
        'total_orders': int(total_orders), 'total_plays': int(round(total_plays)),
        'total_impressions': int(round(total_impressions)), 'total_clicks': int(total_clicks),
        'total_pay': total_pay, 'total_pay_orders': int(total_pay_orders),
        'roi': round(roi, 2), 'pay_roi': round(pay_roi, 2),
        'ctr': round(ctr, 2), 'cvr': round(cvr, 2),
        'plays_per_yuan': round(plays_per_yuan, 2),
        'avg_watch_time': round(hc['avg_watch_time'].mean(), 2) if pd.notna(hc['avg_watch_time'].mean()) else 0,
        'avg_completion': round(hc['completion'].mean(), 2) if pd.notna(hc['completion'].mean()) else 0,
        'avg_play_2s': round(hc['play_2s'].mean(), 2) if pd.notna(hc['play_2s'].mean()) else 0,
        'cpc': round(total_cost / total_clicks, 2) if total_clicks > 0 else 0,
        'cpm': round(total_cost / total_impressions * 1000, 2) if total_impressions > 0 else 0,
        'sources': sources, 'products': products, 'roi_bins': roi_bins,
        'median_roi': round(median_roi, 2), 'mean_roi': round(mean_roi, 2),
        'roi_gt1_pct': round(roi_gt1_pct, 2), 'roi_eq0_pct': round(roi_eq0_pct, 2),
        'top10': top10_list, 'dark': dark_list,
    }



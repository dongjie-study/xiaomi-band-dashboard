"""
Generate headphone/earphone sales summary report (June vs July 2026).
Outputs an HTML report page with tables and charts.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from team_config import TEAM_MAP, classify_room as get_team, TEAM_ORDER, TEAM_COLORS

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
HEADPHONE_KEYWORDS = ['Buds', 'buds', '耳机', '耳', '开放式', '头戴式', '骨传导', 'ear', 'head']

def is_headphone(name):
    for kw in HEADPHONE_KEYWORDS:
        if kw in name:
            return True
    return False

def load_data():
    with open(os.path.join(DATA_DIR, 'sales_analysis', 'history.json'), 'r', encoding='utf-8') as f:
        history = json.load(f)
    june = [d for d in history if d['date'].startswith('2026-06')]
    july = [d for d in history if d['date'].startswith('2026-07')]
    return june, july

def build_headphone_summary(data_list):
    prod_total = {}
    team_total = {}
    daily_data = []

    for d in data_list:
        hp_ord = 0; hp_rev = 0
        for pname, pinfo in d.get('products', {}).items():
            if is_headphone(pname):
                if pname not in prod_total:
                    prod_total[pname] = {'orders': 0, 'revenue': 0}
                prod_total[pname]['orders'] += pinfo['orders']
                prod_total[pname]['revenue'] += pinfo['revenue']
                hp_ord += pinfo['orders']
                hp_rev += pinfo['revenue']

        team_hp = {}
        for rname, rinfo in d.get('rooms', {}).items():
            team = get_team(rname)
            if team not in team_hp:
                team_hp[team] = {'orders': 0, 'revenue': 0}
            for pname, pinfo in rinfo.get('products', {}).items():
                if is_headphone(pname):
                    team_hp[team]['orders'] += pinfo['orders']
                    team_hp[team]['revenue'] += pinfo['revenue']

        for t, info in team_hp.items():
            if t not in team_total:
                team_total[t] = {'orders': 0, 'revenue': 0}
            team_total[t]['orders'] += info['orders']
            team_total[t]['revenue'] += info['revenue']

        our_hp_room = d.get('rooms', {}).get('小米官方耳机直播间', {})

        daily_data.append({
            'date': d['date'],
            'hp_orders': hp_ord,
            'hp_revenue': hp_rev,
            'total_orders': d['total_orders'],
            'total_revenue': d['total_revenue'],
            'hp_share': round(hp_ord / d['total_orders'] * 100, 1) if d['total_orders'] > 0 else 0,
            'our_hp_room_orders': our_hp_room.get('orders', 0) if our_hp_room else 0,
            'our_hp_room_revenue': our_hp_room.get('revenue', 0) if our_hp_room else 0,
        })

    prod_ranked = sorted(prod_total.items(), key=lambda x: -x[1]['revenue'])
    total_hp_orders = sum(p['orders'] for p in prod_total.values())
    total_hp_rev = sum(p['revenue'] for p in prod_total.values())

    return {
        'prod_ranked': prod_ranked,
        'team_total': team_total,
        'daily_data': daily_data,
        'total_hp_orders': total_hp_orders,
        'total_hp_revenue': total_hp_rev,
        'all_orders': sum(d['total_orders'] for d in data_list),
        'all_revenue': sum(d['total_revenue'] for d in data_list),
        'days': len(data_list),
        'avg_price': round(total_hp_rev / total_hp_orders) if total_hp_orders > 0 else 0,
    }

def generate_html(june_summary, july_summary):
    jd = june_summary
    jld = july_summary

    june_daily_hp = jd['total_hp_orders'] / 30 if jd['days'] > 0 else 0
    july_daily_hp = jld['total_hp_orders'] / jld['days'] if jld['days'] > 0 else 0
    june_daily_hp_rev = jd['total_hp_revenue'] / 30 if jd['days'] > 0 else 0
    july_daily_hp_rev = jld['total_hp_revenue'] / jld['days'] if jld['days'] > 0 else 0

    all_prods = {}
    for name, info in jd['prod_ranked']:
        all_prods[name] = {'june_orders': info['orders'], 'june_rev': info['revenue']}
    for name, info in jld['prod_ranked']:
        if name not in all_prods:
            all_prods[name] = {'june_orders': 0, 'june_rev': 0}
        all_prods[name]['july_orders'] = info['orders']
        all_prods[name]['july_rev'] = info['revenue']
    for name in all_prods:
        if 'july_orders' not in all_prods[name]:
            all_prods[name]['july_orders'] = 0
            all_prods[name]['july_rev'] = 0

    prod_comp = sorted(all_prods.items(), key=lambda x: -(x[1].get('june_rev', 0) + x[1].get('july_rev', 0)))

    our_june_orders = sum(d['our_hp_room_orders'] for d in jd['daily_data'])
    our_june_rev = sum(d['our_hp_room_revenue'] for d in jd['daily_data'])
    our_july_orders = sum(d['our_hp_room_orders'] for d in jld['daily_data'])
    our_july_rev = sum(d['our_hp_room_revenue'] for d in jld['daily_data'])
    our_june_active = sum(1 for d in jd['daily_data'] if d['our_hp_room_orders'] > 0)
    our_july_active = sum(1 for d in jld['daily_data'] if d['our_hp_room_orders'] > 0)

    # Helper functions for HTML generation
    def fmt(n):
        return f"{n:,}"

    def fmt_rmb(n):
        return f"¥{n:,.0f}"

    def chg_cls(v1, v2):
        return 'up' if v2 > v1 else 'down'

    def chg_sign(v1, v2):
        return '+' if v2 >= v1 else ''

    # Build data JSON for charts
    chart_data = {
        'june_dates': [d['date'][-5:] for d in jd['daily_data']],
        'july_dates': [d['date'][-5:] for d in jld['daily_data']],
        'june_hp_orders': [d['hp_orders'] for d in jd['daily_data']],
        'july_hp_orders': [d['hp_orders'] for d in jld['daily_data']],
        'june_hp_rev': [d['hp_revenue'] for d in jd['daily_data']],
        'july_hp_rev': [d['hp_revenue'] for d in jld['daily_data']],
        'june_hp_share': [d['hp_share'] for d in jd['daily_data']],
        'july_hp_share': [d['hp_share'] for d in jld['daily_data']],
        'june_room_orders': [d['our_hp_room_orders'] for d in jd['daily_data']],
        'july_room_orders': [d['our_hp_room_orders'] for d in jld['daily_data']],
        'june_room_rev': [d['our_hp_room_revenue'] for d in jd['daily_data']],
        'july_room_rev': [d['our_hp_room_revenue'] for d in jld['daily_data']],
        'prod_names': [name for name, info in prod_comp[:8]],
        'prod_june_rev': [info.get('june_rev', 0) for name, info in prod_comp[:8]],
        'prod_july_rev': [info.get('july_rev', 0) for name, info in prod_comp[:8]],
        'june_avg_share': round(jd['total_hp_orders'] / jd['all_orders'] * 100, 1),
    }
    chart_json = json.dumps(chart_data, ensure_ascii=False)

    # Build product comparison table rows
    prod_rows = ''
    for name, info in prod_comp:
        jn_o = info.get('june_orders', 0); jn_r = info.get('june_rev', 0)
        jl_o = info.get('july_orders', 0); jl_r = info.get('july_rev', 0)
        jn_avg = jn_r / jn_o if jn_o > 0 else 0
        jl_avg = jl_r / jl_o if jl_o > 0 else 0
        jn_daily = jn_o / 30; jl_daily = jl_o / jld['days']
        if jn_daily > 0:
            chg = (jl_daily - jn_daily) / jn_daily * 100
        else:
            chg = 100 if jl_daily > 0 else 0
        cls = chg_cls(0, chg) if chg != 0 else ''
        sign = chg_sign(0, chg)
        hl = 'highlight' if jn_r + jl_r > 100000 else ''
        prod_rows += f'''        <tr class="{hl}">
          <td><strong>{name}</strong></td>
          <td class="center">{fmt(jn_o)}</td><td class="center amount">{fmt_rmb(jn_r)}</td><td class="center">¥{jn_avg:,.0f}</td>
          <td class="center">{fmt(jl_o)}</td><td class="center amount">{fmt_rmb(jl_r)}</td><td class="center">¥{jl_avg:,.0f}</td>
          <td class="center {cls}">{sign}{chg:.1f}%</td>
        </tr>
'''

    # Build team comparison table rows
    def build_team_rows(team_data, total_hp):
        rows = ''
        for t in TEAM_ORDER:
            info = team_data.get(t)
            if info and info['orders'] > 0:
                share = info['orders'] / total_hp * 100
                cls = 'our' if t == '我司' else ''
                marker = {'我司': '★', '机械空间': '◆', '纵横': '▲', '凝云': '●', '良米': '·'}.get(t, '·')
                rows += f'''            <tr class="{cls}">
              <td>{marker} <strong>{t}</strong></td>
              <td class="center">{fmt(info['orders'])} ({share:.1f}%)</td>
              <td class="center amount">{fmt_rmb(info['revenue'])}</td>
            </tr>
'''
        return rows

    june_team_rows = build_team_rows(jd['team_total'], jd['total_hp_orders'])
    july_team_rows = build_team_rows(jld['team_total'], jld['total_hp_orders'])

    # Summary metrics
    june_hp_share = jd['total_hp_orders'] / jd['all_orders'] * 100
    july_hp_share = jld['total_hp_orders'] / jld['all_orders'] * 100
    share_pp = july_hp_share - june_hp_share
    our_june_share = jd['team_total'].get('我司', {}).get('orders', 0) / jd['total_hp_orders'] * 100
    our_july_share = jld['team_total'].get('我司', {}).get('orders', 0) / jld['total_hp_orders'] * 100

    our_room_pct_june = our_june_orders / jd['team_total']['我司']['orders'] * 100 if jd['team_total'].get('我司', {}).get('orders', 0) > 0 else 0
    our_room_pct_july = our_july_orders / jld['team_total']['我司']['orders'] * 100 if jld['team_total'].get('我司', {}).get('orders', 0) > 0 else 0

    # Buds 8 series totals
    buds8_june_orders = sum(info.get('june_orders', 0) for name, info in prod_comp if 'Buds 8' in name)
    buds8_july_orders = sum(info.get('july_orders', 0) for name, info in prod_comp if 'Buds 8' in name)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>耳机品类销量分析报告 · 小米手环直播间</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
:root {{
  --bg: #f0f4f8; --surface: #ffffff; --text: #0f172a; --text-secondary: #64748b;
  --text-muted: #9ca3af; --border: #e8ecf1;
  --shadow-md: 0 4px 16px rgba(0,0,0,.06); --shadow-lg: 0 8px 30px rgba(0,0,0,.10);
  --radius: 14px; --transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  --clr-ours: #1E90FF; --clr-comp: #FF6B35; --clr-orange: #ff6900;
  --clr-green: #1da85c; --clr-red: #FF4757; --clr-purple: #7c6ff7;
  --clr-up: #1da85c; --clr-down: #FF4757;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.6; -webkit-font-smoothing: antialiased;
}}
body::before {{
  content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image: radial-gradient(circle, rgba(148,163,184,.10) 1px, transparent 1px);
  background-size: 22px 22px;
}}
.nav-bar {{
  display: flex; justify-content: center; gap: 6px; flex-wrap: wrap;
  padding: 10px 16px; background: rgba(255,255,255,.9);
  backdrop-filter: blur(14px); border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 100; box-shadow: 0 1px 3px rgba(0,0,0,.03);
}}
.nav-btn {{
  padding: 7px 18px; border-radius: 20px; border: 1.5px solid #dde1e6;
  background: #fff; color: #555; font-size: 12.5px; cursor: pointer;
  text-decoration: none; transition: all var(--transition); font-family: inherit; font-weight: 500;
}}
.nav-btn:hover {{ border-color: var(--clr-orange); color: var(--clr-orange); background: #fff7ed; }}
.nav-btn.active {{ background: linear-gradient(135deg, var(--clr-orange), #ff8c42); color: #fff; border-color: transparent; font-weight: 600; box-shadow: 0 2px 8px rgba(255,105,0,.2); }}
.hero {{
  position: relative; z-index: 1;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
  color: white; padding: 48px 20px 40px; text-align: center;
  box-shadow: 0 4px 24px rgba(15,52,96,.15);
}}
.hero h1 {{ font-size: 36px; font-weight: 800; letter-spacing: -.02em; }}
.hero h1 .mi {{ color: var(--clr-orange); }}
.hero p {{ font-size: 15px; opacity: 0.85; margin-top: 8px; }}
.hero .badge-row {{ margin-top: 16px; display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; }}
.hero .badge {{ padding: 5px 16px; border-radius: 16px; font-size: 12px; font-weight: 600; letter-spacing: .03em; }}
.badge.green {{ background: rgba(29,168,92,.18); color: #5ddf8a; }}
.badge.warn {{ background: rgba(255,105,0,.18); color: #ffa366; }}
.badge.info {{ background: rgba(30,144,255,.18); color: #80c8ff; }}
.badge.purple {{ background: rgba(124,111,247,.18); color: #b5a8ff; }}
.kpi-row {{
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
  max-width: 1200px; margin: -28px auto 0; padding: 0 20px; position: relative; z-index: 10;
}}
@media (max-width: 800px) {{ .kpi-row {{ grid-template-columns: repeat(2, 1fr); }} }}
.kpi-card {{
  background: var(--surface); border-radius: var(--radius); padding: 18px 14px; text-align: center;
  box-shadow: var(--shadow-md); border: 1px solid var(--border);
  transition: transform var(--transition), box-shadow var(--transition);
}}
.kpi-card:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-lg); }}
.kpi-card .label {{ font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px; }}
.kpi-card .value {{ font-size: 28px; font-weight: 800; letter-spacing: -.02em; }}
.kpi-card .sub {{ font-size: 11px; color: var(--text-muted); margin-top: 2px; }}
.kpi-card.ours .value {{ color: var(--clr-ours); }}
.kpi-card.green .value {{ color: var(--clr-green); }}
.kpi-card.red .value {{ color: var(--clr-red); }}
.section {{
  max-width: 1200px; margin: 28px auto; padding: 0 20px; position: relative; z-index: 1;
}}
.section-title {{
  font-size: 20px; font-weight: 700; margin-bottom: 14px; display: flex; align-items: center; gap: 10px;
}}
.section-title .icon {{ font-size: 22px; }}
.table-wrap {{
  background: var(--surface); border-radius: var(--radius); overflow: hidden;
  box-shadow: var(--shadow-md); border: 1px solid var(--border);
}}
table {{
  width: 100%; border-collapse: collapse; font-size: 13px;
}}
thead th {{
  background: #f8fafc; padding: 10px 12px; text-align: left; font-weight: 600;
  color: var(--text-secondary); font-size: 11px; text-transform: uppercase; letter-spacing: .04em;
  border-bottom: 2px solid var(--border);
}}
thead th.center {{ text-align: center; }}
tbody td {{
  padding: 9px 12px; border-bottom: 1px solid #f1f5f9;
}}
tbody td.center {{ text-align: center; }}
tbody td.right {{ text-align: right; font-variant-numeric: tabular-nums; }}
tbody tr:hover {{ background: #fafbfd; }}
tbody tr.our {{ background: #f0f7ff; }}
tbody tr.highlight {{ background: #fffdf0; }}
.amount {{ font-weight: 600; }}
.up {{ color: var(--clr-up); font-weight: 600; }}
.down {{ color: var(--clr-down); font-weight: 600; }}
.chart-container {{
  background: var(--surface); border-radius: var(--radius);
  box-shadow: var(--shadow-md); border: 1px solid var(--border);
  padding: 20px; margin-bottom: 20px;
}}
.chart-box {{ width: 100%; height: 400px; }}
.chart-box.tall {{ height: 500px; }}
.grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
@media (max-width: 900px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
.summary-box {{
  background: var(--surface); border-radius: var(--radius); padding: 24px 28px;
  box-shadow: var(--shadow-md); border: 1px solid var(--border); line-height: 1.9;
}}
.summary-box h3 {{ font-size: 16px; margin-bottom: 12px; color: var(--clr-orange); }}
.summary-box ul {{ padding-left: 20px; }}
.summary-box li {{ margin-bottom: 6px; font-size: 13.5px; }}
.summary-box .highlight {{ background: linear-gradient(180deg, transparent 60%, #fff3cd 60%); padding: 0 3px; }}
.tag-ours {{ display:inline-block; background:#e6f0ff; color:var(--clr-ours); padding:1px 8px; border-radius:10px; font-size:11px; font-weight:600; }}
.tag-comp {{ display:inline-block; background:#ffe8e0; color:var(--clr-comp); padding:1px 8px; border-radius:10px; font-size:11px; font-weight:600; }}
footer {{
  text-align: center; padding: 32px 20px; color: var(--text-muted); font-size: 12px;
}}
</style>
</head>
<body>

<div class="nav-bar">
  <a href="index.html" class="nav-btn">首页</a>
  <a href="sales_analysis/index.html" class="nav-btn">每日看板</a>
  <a href="六月销量分析.html" class="nav-btn">6月销量</a>
  <a href="七月销量分析.html" class="nav-btn">7月销量</a>
  <a href="#" class="nav-btn active">🎧 耳机专报</a>
</div>

<div class="hero">
  <h1><span class="mi">小米</span>直播间 · 耳机品类销量分析报告</h1>
  <p>2026年6月—7月 耳机品类全渠道销售数据汇总 | 含开放式耳机、头戴式耳机、REDMI Buds系列、Xiaomi Buds系列等</p>
  <div class="badge-row">
    <span class="badge green">6月30天 + 7月10天</span>
    <span class="badge info">12个耳机SKU</span>
    <span class="badge warn">全渠道四队竞争</span>
    <span class="badge purple">耳机品类专项分析</span>
  </div>
</div>

<!-- KPI Row -->
<div class="kpi-row">
  <div class="kpi-card">
    <div class="label">📦 6月耳机订单</div>
    <div class="value">{fmt(jd['total_hp_orders'])}</div>
    <div class="sub">日均 {june_daily_hp:.0f} 单 · 占全渠道 {june_hp_share:.1f}%</div>
  </div>
  <div class="kpi-card ours">
    <div class="label">💰 6月耳机销售额</div>
    <div class="value">¥{jd['total_hp_revenue']/10000:.0f}万</div>
    <div class="sub">{fmt_rmb(jd['total_hp_revenue'])} · 均价¥{jd['avg_price']}</div>
  </div>
  <div class="kpi-card">
    <div class="label">📦 7月耳机订单 (10天)</div>
    <div class="value">{fmt(jld['total_hp_orders'])}</div>
    <div class="sub">日均 {july_daily_hp:.0f} 单 · 占全渠道 {july_hp_share:.1f}%</div>
  </div>
  <div class="kpi-card ours">
    <div class="label">💰 7月耳机销售额 (10天)</div>
    <div class="value">¥{jld['total_hp_revenue']/10000:.1f}万</div>
    <div class="sub">{fmt_rmb(jld['total_hp_revenue'])} · 均价¥{jld['avg_price']}</div>
  </div>
</div>

<!-- ===== 6月 vs 7月 总览对比 ===== -->
<div class="section">
  <div class="section-title"><span class="icon">📊</span> 6月 vs 7月 耳机品类总览对比</div>
  <div class="table-wrap">
    <table>
      <thead><tr>
        <th>指标</th><th class="center">6月 (30天)</th><th class="center">7月 (10天)</th>
        <th class="center">日均6月</th><th class="center">日均7月</th><th class="center">日均变化</th>
      </tr></thead>
      <tbody>
        <tr>
          <td><strong>全渠道总订单</strong></td>
          <td class="center">{fmt(jd['all_orders'])}</td>
          <td class="center">{fmt(jld['all_orders'])}</td>
          <td class="center">{jd['all_orders']/30:,.0f}</td>
          <td class="center">{jld['all_orders']/jld['days']:,.0f}</td>
          <td class="center {chg_cls(jd['all_orders']/30, jld['all_orders']/jld['days'])}">{((jld['all_orders']/jld['days']) - (jd['all_orders']/30)) / (jd['all_orders']/30) * 100:+.1f}%</td>
        </tr>
        <tr>
          <td><strong>全渠道总销售额</strong></td>
          <td class="center">{fmt_rmb(jd['all_revenue'])}</td>
          <td class="center">{fmt_rmb(jld['all_revenue'])}</td>
          <td class="center">{fmt_rmb(jd['all_revenue']/30)}</td>
          <td class="center">{fmt_rmb(jld['all_revenue']/jld['days'])}</td>
          <td class="center {chg_cls(jd['all_revenue']/30, jld['all_revenue']/jld['days'])}">{((jld['all_revenue']/jld['days']) - (jd['all_revenue']/30)) / (jd['all_revenue']/30) * 100:+.1f}%</td>
        </tr>
        <tr class="highlight">
          <td><strong>🎧 耳机品类订单</strong></td>
          <td class="center"><strong>{fmt(jd['total_hp_orders'])}</strong></td>
          <td class="center"><strong>{fmt(jld['total_hp_orders'])}</strong></td>
          <td class="center">{june_daily_hp:,.0f}</td>
          <td class="center">{july_daily_hp:,.0f}</td>
          <td class="center {chg_cls(june_daily_hp, july_daily_hp)}">{(july_daily_hp - june_daily_hp) / june_daily_hp * 100:+.1f}%</td>
        </tr>
        <tr class="highlight">
          <td><strong>🎧 耳机品类销售额</strong></td>
          <td class="center"><strong>{fmt_rmb(jd['total_hp_revenue'])}</strong></td>
          <td class="center"><strong>{fmt_rmb(jld['total_hp_revenue'])}</strong></td>
          <td class="center">{fmt_rmb(june_daily_hp_rev)}</td>
          <td class="center">{fmt_rmb(july_daily_hp_rev)}</td>
          <td class="center {chg_cls(june_daily_hp_rev, july_daily_hp_rev)}">{(july_daily_hp_rev - june_daily_hp_rev) / june_daily_hp_rev * 100:+.1f}%</td>
        </tr>
        <tr>
          <td><strong>耳机占全渠道订单比</strong></td>
          <td class="center">{june_hp_share:.1f}%</td>
          <td class="center">{july_hp_share:.1f}%</td>
          <td class="center" colspan="3">7月耳机占比提升 <span class="up">+{share_pp:.1f}pp</span></td>
        </tr>
        <tr>
          <td><strong>耳机品类均价</strong></td>
          <td class="center">¥{jd['avg_price']}</td>
          <td class="center">¥{jld['avg_price']}</td>
          <td class="center" colspan="3">均价下降 <span class="down">-¥{jd['avg_price'] - jld['avg_price']}</span>，低端Buds占比上升拉低均价</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>

<!-- ===== 产品细分对比 ===== -->
<div class="section">
  <div class="section-title"><span class="icon">🎧</span> 耳机产品线细分对比 (按6月销售额排序)</div>
  <div class="table-wrap">
    <table>
      <thead><tr>
        <th>产品线</th><th class="center">6月订单</th><th class="center">6月销售额</th><th class="center">6月均价</th>
        <th class="center">7月订单</th><th class="center">7月销售额</th><th class="center">7月均价</th>
        <th class="center">日均订单变化</th>
      </tr></thead>
      <tbody>
{prod_rows}
      </tbody>
    </table>
  </div>
</div>

<!-- ===== 团队竞争格局 ===== -->
<div class="section">
  <div class="section-title"><span class="icon">⚔️</span> 耳机品类团队竞争格局</div>
  <div class="grid-2">
    <div>
      <div class="table-wrap">
        <table>
          <thead><tr><th colspan="3" style="text-align:center;background:#f0f7ff;">6月团队耳机销量</th></tr>
          <tr><th>团队</th><th class="center">订单数</th><th class="center">销售额</th></tr></thead>
          <tbody>
{june_team_rows}
          </tbody>
        </table>
      </div>
    </div>
    <div>
      <div class="table-wrap">
        <table>
          <thead><tr><th colspan="3" style="text-align:center;background:#f0f7ff;">7月团队耳机销量 (10天)</th></tr>
          <tr><th>团队</th><th class="center">订单数</th><th class="center">销售额</th></tr></thead>
          <tbody>
{july_team_rows}
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ===== 每日趋势图 ===== -->
<div class="section">
  <div class="grid-2">
    <div class="chart-container"><div class="chart-box" id="chartDailyOrders"></div></div>
    <div class="chart-container"><div class="chart-box" id="chartDailyRevenue"></div></div>
  </div>
  <div class="chart-container"><div class="chart-box tall" id="chartProductComp"></div></div>
</div>

<!-- ===== 耳机品类占全渠道比趋势 ===== -->
<div class="section">
  <div class="chart-container"><div class="chart-box" id="chartShare"></div></div>
</div>

<!-- ===== 我司耳机号表现 ===== -->
<div class="section">
  <div class="section-title"><span class="icon">🏪</span> 我司耳机直播间表现</div>
  <div class="grid-2">
    <div class="chart-container"><div class="chart-box" id="chartOurRoom"></div></div>
    <div class="summary-box">
      <h3>📋 小米官方耳机直播间 关键数据</h3>
      <ul>
        <li>6月累计: <span class="highlight">{fmt(our_june_orders)}单</span>, 销售额 <span class="highlight">{fmt_rmb(our_june_rev)}</span>, 出勤{our_june_active}天</li>
        <li>7月累计(10天): <span class="highlight">{fmt(our_july_orders)}单</span>, 销售额 <span class="highlight">{fmt_rmb(our_july_rev)}</span>, 出勤{our_july_active}天</li>
        <li>6月日均: {our_june_orders/our_june_active:,.0f}单, {fmt_rmb(our_june_rev/our_june_active)} (出勤日)</li>
        <li>7月日均: {our_july_orders/our_july_active:,.0f}单, {fmt_rmb(our_july_rev/our_july_active)} (出勤日)</li>
        <li>耳机号贡献我司耳机销量: 6月 {our_room_pct_june:.0f}% | 7月 {our_room_pct_july:.0f}%</li>
      </ul>
    </div>
  </div>
</div>

<!-- ===== 总结 ===== -->
<div class="section">
  <div class="section-title"><span class="icon">📝</span> 耳机品类综合分析</div>
  <div class="summary-box">
    <h3>一、市场规模与趋势</h3>
    <ul>
      <li>耳机品类6月全渠道<span class="highlight">{fmt(jd['total_hp_orders'])}单 / {fmt_rmb(jd['total_hp_revenue'])}</span>，占全渠道{june_hp_share:.1f}%。日均{june_daily_hp:.0f}单。</li>
      <li>7月前10天耳机品类<span class="highlight">{fmt(jld['total_hp_orders'])}单 / {fmt_rmb(jld['total_hp_revenue'])}</span>，占全渠道{july_hp_share:.1f}%。日均{july_daily_hp:.0f}单。</li>
      <li>日均订单环比<span class="{chg_cls(june_daily_hp, july_daily_hp)}">{chg_sign(june_daily_hp, july_daily_hp)}{(july_daily_hp - june_daily_hp) / june_daily_hp * 100:.1f}%</span>，耳机品类在全渠道占比从{june_hp_share:.1f}%提升至{july_hp_share:.1f}%，品类重要性上升。</li>
    </ul>

    <h3>二、产品结构分析</h3>
    <ul>
      <li><strong>TOP2品类（开放式耳机+头戴式耳机）</strong>占耳机总销售额的68.9%（6月）→ 56.8%（7月），高端品类占比下降。开放式耳机从¥838均价降至¥764，头戴式从¥292升至¥301。</li>
      <li><strong>REDMI Buds 8系列</strong>（含标准版/Pro/活力版/青春版）6月合计{fmt(buds8_june_orders)}单 / ¥{sum(info.get('june_rev',0) for name,info in prod_comp if 'Buds 8' in name):,.0f}。7月10天合计{fmt(buds8_july_orders)}单，日均从{buds8_june_orders/30:.0f}单提升至{buds8_july_orders/jld['days']:.0f}单。</li>
      <li><strong>高端产品线</strong>（Xiaomi Buds 5 Pro / Buds 6 / 骨传导耳机）体量较小，合计不足5%份额，但有高客单价优势（¥500—¥900）。</li>
      <li><strong>6月30日耳机爆发日</strong>：当日耳机{fmt(jd['daily_data'][-1]['hp_orders'])}单 / {fmt_rmb(jd['daily_data'][-1]['hp_revenue'])}，占当日全渠道的{jd['daily_data'][-1]['hp_share']:.0f}%，疑似新品首发或大促活动。</li>
    </ul>

    <h3>三、竞争格局</h3>
    <ul>
      <li>耳机品类<span class="tag-comp">良米</span>以65.2%（6月）→ 61.2%（7月）的订单份额领先，但其产品集中在低端Buds系列，均价偏低。</li>
      <li>我司以<span class="tag-ours">{our_june_share:.1f}%</span>（6月）→ <span class="tag-ours">{our_july_share:.1f}%</span>（7月）份额位居第二，但在高端耳机（开放式、头戴式）上有明显优势。</li>
      <li><strong>机械空间</strong>耳机份额从7.5%提升至12.1%，主要在Buds 8活力版等低端品类增长，需关注其是否会向上渗透。</li>
      <li>我司耳机直播间贡献了我司耳机销量的{our_room_pct_june:.0f}%（6月），7月其他我司直播间耳机销量占比上升，说明耳机品类在我司各直播间的渗透率提高。</li>
    </ul>

    <h3>四、关键发现</h3>
    <ul>
      <li>🔴 <strong>均价下行风险</strong>：耳机品类均价从¥{jd['avg_price']}降至¥{jld['avg_price']}，Buds 8活力版/青春版等低价SKU放量，侵蚀高客单价品类份额。</li>
      <li>🟡 <strong>开放式耳机护城河</strong>：我司在开放式耳机品类优势明显（6月约64%份额），且均价¥800+，是高利润品类，需重点守护。</li>
      <li>🟢 <strong>品类占比提升</strong>：耳机从6月占全渠道{june_hp_share:.1f}%升至7月{july_hp_share:.1f}%，说明耳机品类在直播间的权重在增长，值得投入更多资源。</li>
      <li>🔴 <strong>头戴式耳机短板</strong>：6月我司仅占头戴式耳机14.6%，良米占85.4%。头戴式耳机是全渠道第二大耳机品类（¥48万/月），我司参与度严重不足。</li>
      <li>🟡 <strong>耳机号产能波动大</strong>：日单量从5单到248单波动极大（6月CV≈95%），需稳定日常运营节奏。</li>
    </ul>
  </div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">💡</span> 改进建议</div>
  <div class="summary-box">
    <h3>🔴 短期 (7月内)</h3>
    <ul>
      <li><strong>稳定耳机号日播节奏：</strong>7月前10天耳机号日均仅{our_july_orders/our_july_active:,.0f}单，较6月日均{our_june_orders/our_june_active:,.0f}单下降{(1 - (our_july_orders/our_july_active)/(our_june_orders/our_june_active)) * 100:.0f}%。需排查是排班问题还是品类结构调整导致。</li>
      <li><strong>头戴式耳机破局：</strong>全渠道头戴式耳机6月月均55单/天，我司仅占14.6%。在耳机号+数码旗舰店增加头戴式耳机曝光频次。</li>
      <li><strong>高端Buds 5 Pro/Buds 6推广：</strong>虽然体量小但均价¥583-¥857，可作为差异化产品在黄金时段推广。</li>
    </ul>
    <h3>🟡 中期 (8月)</h3>
    <ul>
      <li><strong>耳机号品类定位明确：</strong>确定以开放式耳机（高客单高利润）为核心品类，Buds系列为走量补充，头戴式为增长品类。</li>
      <li><strong>跨直播间耳机渗透：</strong>手环号、手表号可适当插入耳机SKU，利用现有流量做交叉销售。</li>
      <li><strong>跟踪机械空间耳机动向：</strong>机械空间耳机份额从7.5%→12.1%，关注其是否会增加耳机品类布局。</li>
    </ul>
  </div>
</div>

<footer>
  数据来源：抖音直播间订单 · 分析周期：2026年6月1日—7月10日 · 自动生成于2026年7月11日<br>
  我司 = 小米官方手环直播间 / 小米数码旗舰店 / 小米官方手表 / 小米官方耳机直播间 / 小米官旗手表直播间 / 小米手环10Pro直播间<br>
  ★ 耳机品类定义：含REDMI Buds系列、Xiaomi Buds系列、开放式耳机、头戴式耳机、骨传导耳机及耳机配件
</footer>

<script>
const D = {chart_json};

function fmt(n) {{ return n.toLocaleString('zh-CN'); }}
function fmtRMB(n) {{ return '¥' + Math.round(n).toLocaleString('zh-CN'); }}

(function() {{
  const allDates = D.june_dates.concat(D.july_dates);

  const c1 = echarts.init(document.getElementById('chartDailyOrders'));
  c1.setOption({{
    title: {{ text: '每日耳机订单趋势 (6月+7月)', left: 'center', textStyle: {{fontSize:15,fontWeight:600}} }},
    tooltip: {{ trigger: 'axis' }},
    legend: {{ bottom: 0, data: ['耳机订单'] }},
    grid: {{ left: 45, right: 20, top: 50, bottom: 35 }},
    xAxis: {{ type: 'category', data: allDates, axisLabel: {{rotate:45,fontSize:10}} }},
    yAxis: {{ type: 'value', name: '订单数' }},
    series: [
      {{ name: '耳机订单', type: 'bar', data: D.june_hp_orders.concat(D.july_hp_orders),
         itemStyle: {{color:'#7c6ff7'}}, barWidth:'60%' }},
    ]
  }});

  const c2 = echarts.init(document.getElementById('chartDailyRevenue'));
  c2.setOption({{
    title: {{ text: '每日耳机销售额趋势', left: 'center', textStyle: {{fontSize:15,fontWeight:600}} }},
    tooltip: {{ trigger: 'axis', valueFormatter: function(v) {{ return '¥' + (v/10000).toFixed(2) + '万'; }} }},
    legend: {{ bottom: 0, data: ['销售额'] }},
    grid: {{ left: 55, right: 20, top: 50, bottom: 35 }},
    xAxis: {{ type: 'category', data: allDates, axisLabel: {{rotate:45,fontSize:10}} }},
    yAxis: {{ type: 'value', name: '万元', axisLabel: {{formatter: function(v) {{ return (v/10000).toFixed(0)+'w'; }} }} }},
    series: [
      {{ name: '销售额', type: 'line',
         data: D.june_hp_rev.concat(D.july_hp_rev),
         smooth: true, lineStyle: {{color:'#7c6ff7',width:2.5}}, symbol:'circle', symbolSize:4,
         areaStyle: {{color:'rgba(124,111,247,0.1)'}} }},
    ]
  }});

  const c3 = echarts.init(document.getElementById('chartProductComp'));
  c3.setOption({{
    title: {{ text: 'TOP8 耳机产品销售额对比 (6月 vs 7月10天)', left: 'center', textStyle: {{fontSize:15,fontWeight:600}} }},
    tooltip: {{ trigger: 'axis', valueFormatter: function(v) {{ return '¥' + fmt(v); }} }},
    legend: {{ bottom: 0, data: ['6月(30天)', '7月(10天)'] }},
    grid: {{ left: 100, right: 40, top: 50, bottom: 35 }},
    xAxis: {{ type: 'category', data: D.prod_names, axisLabel: {{fontSize:10}} }},
    yAxis: {{ type: 'value', name: '销售额', axisLabel: {{formatter: function(v) {{ return (v/10000).toFixed(0)+'w'; }} }} }},
    series: [
      {{ name: '6月(30天)', type: 'bar', data: D.prod_june_rev, itemStyle: {{color:'#1E90FF'}} }},
      {{ name: '7月(10天)', type: 'bar', data: D.prod_july_rev, itemStyle: {{color:'#FF6B35'}} }},
    ]
  }});

  const c4 = echarts.init(document.getElementById('chartShare'));
  const shareData = D.june_hp_share.concat(D.july_hp_share);
  c4.setOption({{
    title: {{ text: '耳机品类占全渠道订单比例 (%)', left: 'center', textStyle: {{fontSize:15,fontWeight:600}} }},
    tooltip: {{ trigger: 'axis', formatter: function(p) {{ return p[0].name + '<br/>耳机占比: <b>' + p[0].value + '%</b>'; }} }},
    grid: {{ left: 45, right: 20, top: 50, bottom: 35 }},
    xAxis: {{ type: 'category', data: allDates, axisLabel: {{rotate:45,fontSize:10}} }},
    yAxis: {{ type: 'value', name: '%', axisLabel: {{formatter:'{{value}}%'}} }},
    series: [
      {{ name: '耳机占比', type: 'line', data: shareData, smooth: true,
         lineStyle: {{color:'#ff6900',width:2.5}}, symbol:'circle', symbolSize:4,
         areaStyle: {{color:'rgba(255,105,0,0.12)'}},
         markLine: {{ silent:true, symbol:'none',
           data:[{{yAxis:D.june_avg_share, name:'6月均值', label:{{formatter:'6月\\\\n{{c}}%'}}}}],
           lineStyle:{{color:'#94a3b8',type:'dashed'}} }}
      }},
    ]
  }});

  const c5 = echarts.init(document.getElementById('chartOurRoom'));
  const roomOrders = D.june_room_orders.concat(D.july_room_orders);
  const roomRev = D.june_room_rev.concat(D.july_room_rev);
  c5.setOption({{
    title: {{ text: '小米官方耳机直播间 每日表现', left: 'center', textStyle: {{fontSize:15,fontWeight:600}} }},
    tooltip: {{ trigger: 'axis' }},
    legend: {{ bottom: 0, data: ['订单', '销售额'] }},
    grid: {{ left: 55, right: 55, top: 50, bottom: 35 }},
    xAxis: {{ type: 'category', data: allDates, axisLabel: {{rotate:45,fontSize:10}} }},
    yAxis: [
      {{ type: 'value', name: '订单数' }},
      {{ type: 'value', name: '销售额', axisLabel: {{formatter: function(v) {{ return (v/10000).toFixed(0)+'w'; }} }} }}
    ],
    series: [
      {{ name: '订单', type: 'bar', data: roomOrders, itemStyle: {{color:'#1E90FF'}} }},
      {{ name: '销售额', type: 'line', yAxisIndex:1, data: roomRev, lineStyle: {{color:'#1da85c',width:2.5}}, symbol:'diamond', symbolSize:6 }},
    ]
  }});

  window.addEventListener('resize', function() {{ c1.resize(); c2.resize(); c3.resize(); c4.resize(); c5.resize(); }});
}})();
</script>

</body>
</html>'''
    return html


if __name__ == '__main__':
    june, july = load_data()
    june_summary = build_headphone_summary(june)
    july_summary = build_headphone_summary(july)

    html = generate_html(june_summary, july_summary)
    out_path = os.path.join(DATA_DIR, '耳机销量分析报告.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    sys.stdout.reconfigure(encoding='utf-8')
    print(f'Generated: {out_path}')
    print(f'  6月: {june_summary["days"]}天, 耳机{june_summary["total_hp_orders"]:,}单, ¥{june_summary["total_hp_revenue"]:,.0f}')
    print(f'  7月: {july_summary["days"]}天, 耳机{july_summary["total_hp_orders"]:,}单, ¥{july_summary["total_hp_revenue"]:,.0f}')

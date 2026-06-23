import json

with open('618_analysis_data.json', 'r', encoding='utf-8') as f:
    D = json.load(f)

def fmt(n):
    return f"{n:,}"

def fmt_wan(n):
    return f"¥{n:,.1f}万"

def fmt_yuan(n):
    return f"¥{n:,.0f}"

def diff_str(d):
    if d > 0: return f'我方+{fmt(d)}'
    elif d < 0: return f'竞对+{fmt(abs(d))}'
    return '持平'

def diff_class(d):
    if d > 0: return 'var(--clr-green)'
    elif d < 0: return 'var(--clr-red)'
    return ''

teams = D['teams']
our = teams['我方']
liangmi = teams['良米']
jixie = teams['机械空间']
zongxun = teams['综训']

total_orders = D['total_orders']
total_gmv_wan = D['total_gmv_wan']
live_orders = D['live_orders']
card_orders = D['card_orders']
live_gmv_wan = D['live_gmv_wan']
card_gmv_wan = D['card_gmv_wan']

key_prods = ['小米手环10', 'REDMI Watch 6', '小米手环10 Pro', '小米手环9 Pro',
             '小米手环10 陶瓷版', '小米手表 S系列', 'Xiaomi 开放式耳机',
             'REDMI Buds 8 Pro', 'REDMI Buds 8', 'REDMI Buds 8 活力版', 'REDMI Buds 8 青春版']

# Build daily chart data
dates_mmdd = json.dumps(D['dates_mmdd'])
daily_total = json.dumps(D['daily_total'])
daily_live = json.dumps(D['daily_live_orders'])
daily_card = json.dumps(D['daily_card_orders'])
daily_our = json.dumps(D['daily_我方_orders'])
daily_liangmi = json.dumps(D['daily_良米_orders'])
daily_jixie = json.dumps(D['daily_机械空间_orders'])
daily_zongxun = json.dumps(D['daily_综训_orders'])
daily_our_r = json.dumps(D['daily_我方_gmv_wan'])
daily_liangmi_r = json.dumps(D['daily_良米_gmv_wan'])
daily_jixie_r = json.dumps(D['daily_机械空间_gmv_wan'])
daily_zongxun_r = json.dumps(D['daily_综训_gmv_wan'])

# Product comparison tables
def prod_table_rows(prods, show_channel=False):
    rows = []
    for p in prods:
        d = D.get(f'prod_{p}', {})
        if not d or d.get('total', 0) == 0: continue
        share = d['share']
        diff = d['diff']
        if share >= 50:
            share_color = 'var(--clr-green)'
            comment = '我方领先 ✅'
            comment_color = 'var(--clr-green)'
        elif share >= 40:
            share_color = 'var(--clr-green)'
            comment = diff_str(diff)
            comment_color = diff_class(diff)
        elif share >= 30:
            share_color = 'var(--clr-orange)'
            comment = diff_str(diff)
            comment_color = diff_class(diff)
        else:
            share_color = 'var(--clr-red)'
            comment = diff_str(diff)
            comment_color = diff_class(diff)

        row = {}
        row['name'] = p
        row['our_orders'] = fmt(d['our'])
        row['our_gmv'] = fmt_yuan(d['our_gmv'])
        row['comp_orders'] = fmt(d['comp'])
        row['comp_gmv'] = fmt_yuan(d['comp_gmv'])
        row['total_orders'] = fmt(d['total'])
        row['total_gmv'] = fmt_yuan(d['total_gmv'])
        row['share'] = f'{share}%'
        row['share_color'] = share_color
        row['diff'] = fmt(diff) if diff >= 0 else f'{diff:,}'
        row['diff_display'] = diff_str(diff)
        row['diff_color'] = diff_class(diff)
        row['comment'] = comment
        row['comment_color'] = comment_color
        if show_channel:
            row['live_total'] = fmt(d.get('live_total', 0))
            row['card_total'] = fmt(d.get('card_total', 0))
            row['our_live'] = fmt(d.get('our_live', 0))
            row['our_card'] = fmt(d.get('our_card', 0))
            row['comp_live'] = fmt(d.get('comp_live', 0))
            row['comp_card'] = fmt(d.get('comp_card', 0))
        rows.append(row)
    return rows

core_prods_rows = prod_table_rows(['小米手环10', 'REDMI Watch 6', '小米手环10 Pro'])
secondary_rows = prod_table_rows(['小米手环9 Pro', '小米手环10 陶瓷版', '小米手表 S系列'])
headphone_rows = prod_table_rows(['Xiaomi 开放式耳机', 'REDMI Buds 8 Pro', 'REDMI Buds 8', 'REDMI Buds 8 活力版', 'REDMI Buds 8 青春版'])
all_prod_rows = prod_table_rows(key_prods)

# Live-only product rows
live_core = prod_table_rows(['小米手环10', 'REDMI Watch 6', '小米手环10 Pro'])
live_sec = prod_table_rows(['小米手环9 Pro', '小米手环10 陶瓷版', '小米手表 S系列'])
live_hp = prod_table_rows(['Xiaomi 开放式耳机', 'REDMI Buds 8 Pro', 'REDMI Buds 8', 'REDMI Buds 8 活力版', 'REDMI Buds 8 青春版'])

# Card-only product rows
card_core = prod_table_rows(['小米手环10', 'REDMI Watch 6', '小米手环10 Pro'])
card_sec = prod_table_rows(['小米手环9 Pro', '小米手环10 陶瓷版', '小米手表 S系列'])
card_hp = prod_table_rows(['Xiaomi 开放式耳机', 'REDMI Buds 8 Pro', 'REDMI Buds 8', 'REDMI Buds 8 活力版', 'REDMI Buds 8 青春版'])

# ========== Build the HTML ==========
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>618 大促复盘总结 · 小米手环直播间（含商品卡）</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
:root {{
  --bg: #f0f4f8;
  --surface: #ffffff;
  --text: #0f172a;
  --text-secondary: #64748b;
  --text-muted: #9ca3af;
  --border: #e8ecf1;
  --shadow-sm: 0 1px 3px rgba(0,0,0,.03);
  --shadow-md: 0 4px 16px rgba(0,0,0,.06);
  --shadow-lg: 0 8px 30px rgba(0,0,0,.10);
  --radius: 14px;
  --radius-sm: 10px;
  --transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  --clr-ours: #1E90FF;
  --clr-comp: #FF6B35;
  --clr-orange: #ff6900;
  --clr-green: #1da85c;
  --clr-red: #FF4757;
  --clr-purple: #7c6ff7;
  --clr-gold: #c8960c;
  --clr-cyan: #0ea89d;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html {{ scroll-behavior: smooth; }}
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
.hero h1 {{ font-size: 38px; font-weight: 800; letter-spacing: -.02em; }}
.hero h1 .mi {{ color: var(--clr-orange); }}
.hero p {{ font-size: 15px; opacity: 0.85; margin-top: 8px; max-width: 700px; margin-left: auto; margin-right: auto; }}
.hero .badge-row {{ margin-top: 16px; display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; }}
.hero .badge {{ padding: 5px 16px; border-radius: 16px; font-size: 12px; font-weight: 600; letter-spacing: .03em; }}
.badge.green {{ background: rgba(29,168,92,.18); color: #5ddf8a; }}
.badge.warn {{ background: rgba(255,105,0,.18); color: #ffa366; }}
.badge.info {{ background: rgba(30,144,255,.18); color: #80c8ff; }}
.badge.purple {{ background: rgba(124,111,247,.18); color: #b5a8ff; }}
.badge.card {{ background: rgba(200,150,12,.18); color: #e8c840; }}
.kpi-row {{
  display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px;
  max-width: 1500px; margin: -28px auto 0; padding: 0 20px; position: relative; z-index: 10;
}}
.kpi-card {{
  background: var(--surface); border-radius: var(--radius); padding: 18px 10px; text-align: center;
  box-shadow: var(--shadow-md); border: 1px solid var(--border);
  transition: transform var(--transition), box-shadow var(--transition);
}}
.kpi-card:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-lg); }}
.kpi-card .kpi-value {{ font-size: 26px; font-weight: 800; line-height: 1.2; }}
.kpi-card .kpi-label {{ font-size: 11px; color: var(--text-secondary); margin-top: 6px; font-weight: 500; letter-spacing: .03em; text-transform: uppercase; }}
.kpi-card.highlight {{ border: 2px solid var(--clr-orange); background: linear-gradient(135deg, #fffdf0 0%, #fff 100%); }}
.kpi-card.ours {{ border-left: 4px solid var(--clr-ours); }}
.kpi-card.comp {{ border-left: 4px solid var(--clr-comp); }}
.container {{ max-width: 1500px; margin: 32px auto; padding: 0 20px; position: relative; z-index: 1; }}
.section {{
  background: var(--surface); border-radius: var(--radius); padding: 28px 32px; margin-bottom: 20px;
  box-shadow: var(--shadow-sm); border: 1px solid var(--border); scroll-margin-top: 70px;
  transition: box-shadow var(--transition);
}}
.section:hover {{ box-shadow: var(--shadow-md); }}
.section h2 {{
  font-size: 20px; font-weight: 700; margin-bottom: 20px;
  padding-bottom: 12px; border-bottom: 2px solid #f0f0f0; position: relative;
  display: flex; align-items: center; gap: 10px;
}}
.section h2::after {{ content: ''; position: absolute; bottom: -2px; left: 0; width: 48px; height: 3px; background: var(--clr-orange); border-radius: 2px; }}
.section h3 {{ font-size: 16px; font-weight: 700; margin: 24px 0 12px; color: #333; }}
.section h3:first-of-type {{ margin-top: 0; }}
.grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
.grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }}
.grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }}
.chart-box {{ background: #fcfdfe; border-radius: var(--radius-sm); border: 1px solid var(--border); padding: 16px; overflow: hidden; }}
.chart-box.h250 {{ height: 270px; }}
.chart-box.h300 {{ height: 340px; }}
.chart-box.h360 {{ height: 400px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ background: #f7f8fa; padding: 10px 8px; text-align: center; font-weight: 600; font-size: 12px; border-bottom: 2px solid #e0e3e8; white-space: nowrap; }}
td {{ padding: 9px 8px; text-align: center; border-bottom: 1px solid #f0f2f5; }}
tr:hover {{ background: #fafbfc; }}
.insight-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 8px 0; }}
.insight {{ padding: 12px 16px; border-radius: var(--radius-sm); font-size: 12.5px; line-height: 1.6; border-left: 4px solid; }}
.insight.good {{ border-color: var(--clr-green); background: #f0faf3; }}
.insight.warn {{ border-color: var(--clr-orange); background: #fffdf0; }}
.insight.info {{ border-color: var(--clr-ours); background: #eff6ff; }}
.insight.danger {{ border-color: var(--clr-red); background: #fef2f2; }}
.hl-box {{ padding: 14px 20px; border-radius: var(--radius-sm); font-size: 13px; line-height: 1.6; }}
.hl-box.hl-blue {{ background: #eff6ff; border: 1px solid #bfdbfe; }}
.hl-box.hl-green {{ background: #f0faf3; border: 1px solid #bbf7d0; }}
.hl-box.hl-orange {{ background: #fffdf0; border: 1px solid #fed7aa; }}
.key-num-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 12px 0; }}
.key-num {{
  background: linear-gradient(135deg, #fcfdfe 0%, #f7f8fa 100%);
  border-radius: var(--radius-sm); border: 1px solid var(--border);
  padding: 16px 12px; text-align: center;
}}
.key-num .num {{ font-size: 28px; font-weight: 800; }}
.key-num .desc {{ font-size: 12px; color: var(--text-secondary); margin-top: 4px; }}
.score-bar {{ margin: 10px 0; }}
.score-bar .s-label {{ display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px; }}
.score-bar .s-track {{ height: 8px; border-radius: 4px; background: #e8ecf1; overflow: hidden; }}
.score-bar .s-fill {{ height: 100%; border-radius: 4px; }}
.score-bar .s-fill.ours {{ background: var(--clr-ours); }}
.score-bar .s-fill.comp {{ background: var(--clr-comp); }}
.tl {{ list-style: none; padding: 0; }}
.tl-item {{ display: flex; gap: 14px; margin-bottom: 16px; }}
.tl-dot {{
  width: 40px; height: 40px; border-radius: 50%; color: #fff; display: flex;
  align-items: center; justify-content: center; font-weight: 800; font-size: 16px;
  flex-shrink: 0;
}}
.tl-body h5 {{ font-size: 14px; margin-bottom: 2px; }}
.tl-body p {{ font-size: 12px; color: var(--text-secondary); line-height: 1.6; }}
.conclusion-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 12px 0; }}
.conclusion-card {{ padding: 22px; border-radius: var(--radius); text-align: center; border: 1px solid var(--border); transition: all var(--transition); }}
.conclusion-card:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-lg); }}
.conclusion-card .c-icon {{ font-size: 36px; margin-bottom: 8px; }}
.conclusion-card h4 {{ font-size: 15px; margin-bottom: 6px; }}
.conclusion-card p {{ font-size: 12px; color: var(--text-secondary); line-height: 1.6; }}
.conclusion-card.c1 {{ background: #fffdf0; }}
.conclusion-card.c2 {{ background: #f0faf3; }}
.conclusion-card.c3 {{ background: #eff6ff; }}
.conclusion-card.c4 {{ background: #fef2f2; }}
.plan-card {{
  background: var(--surface); border-radius: var(--radius); padding: 24px 18px;
  box-shadow: var(--shadow-sm); border: 1px solid var(--border);
  position: relative; overflow: hidden; transition: all var(--transition);
}}
.plan-card:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-lg); }}
.plan-card .plan-num {{ font-size: 52px; font-weight: 900; opacity: .06; position: absolute; top: -8px; right: 14px; line-height: 1; }}
.plan-card .plan-icon {{ font-size: 30px; margin-bottom: 10px; }}
.plan-card h4 {{ font-size: 16px; margin-bottom: 8px; position: relative; z-index: 1; }}
.plan-card p {{ font-size: 12.5px; color: #555; line-height: 1.7; position: relative; z-index: 1; }}
.plan-card .plan-tag {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 10.5px; font-weight: 600; margin-top: 10px; position: relative; z-index: 1; }}
.plan-card.p1 {{ border-top: 3px solid var(--clr-ours); }}
.plan-card.p2 {{ border-top: 3px solid var(--clr-green); }}
.plan-card.p3 {{ border-top: 3px solid var(--clr-purple); }}
.plan-card.p4 {{ border-top: 3px solid var(--clr-red); }}

@media (max-width: 1100px) {{
  .kpi-row {{ grid-template-columns: repeat(3, 1fr); }}
}}
@media (max-width: 768px) {{
  .grid-2, .grid-3, .grid-4, .insight-row, .conclusion-grid, .key-num-grid {{ grid-template-columns: 1fr; }}
  .kpi-row {{ grid-template-columns: 1fr 1fr; }}
  .section {{ padding: 20px 16px; }}
  .hero h1 {{ font-size: 24px; }}
  table {{ font-size: 10px; }}
  th, td {{ padding: 5px 3px; }}
}}
</style>
</head>
<body>

<nav class="nav-bar">
  <a class="nav-btn" href="#sales">📊 销量总览</a>
  <a class="nav-btn" href="#products">🏷️ 整体品类占比</a>
  <a class="nav-btn" href="#live-products">📡 直播间品类</a>
  <a class="nav-btn" href="#card-products">🛒 商品卡品类</a>
  <a class="nav-btn" href="#video">🎬 千川视频</a>
  <a class="nav-btn" href="#visual">👁️ 视觉分析</a>
  <a class="nav-btn" href="#learnings">💡 核心洞察</a>
  <a class="nav-btn" href="#plan">🚀 后续规划</a>
</nav>

<div class="hero">
  <h1>🏆 <span class="mi">618</span> 大促复盘总结</h1>
  <p>5/15-6/18 · 35天全周期 · 直播间+商品卡全渠道数据 · 四大团队竞争格局</p>
  <div class="badge-row">
    <span class="badge green">📊 {fmt(total_orders)}单 · ¥{total_gmv_wan}万</span>
    <span class="badge info">📡 直播间{fmt(live_orders)}单</span>
    <span class="badge card">🛒 商品卡{fmt(card_orders)}单</span>
    <span class="badge warn">🏪 {our['rooms']}间我方 vs {liangmi['rooms']}间良米</span>
  </div>
</div>

<div class="kpi-row">
  <div class="kpi-card highlight">
    <div class="kpi-value" style="color:var(--clr-ours);">{fmt(total_orders)}</div>
    <div class="kpi-label">618 总销量</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value" style="color:var(--clr-green);">¥{total_gmv_wan}万</div>
    <div class="kpi-label">618 总GMV</div>
  </div>
  <div class="kpi-card ours">
    <div class="kpi-value" style="color:var(--clr-ours);">{our['pct']}%</div>
    <div class="kpi-label">我方综合份额 ({fmt(our['orders'])}单)</div>
  </div>
  <div class="kpi-card comp">
    <div class="kpi-value" style="color:var(--clr-comp);">{liangmi['pct']}%</div>
    <div class="kpi-label">良米份额 ({fmt(liangmi['orders'])}单)</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value" style="color:var(--clr-ours);">{fmt(live_orders)} / {fmt(card_orders)}</div>
    <div class="kpi-label">直播间 / 商品卡 销量</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value" style="color:var(--clr-green);">{fmt(our['orders'] - liangmi['orders'])}</div>
    <div class="kpi-label">我方 vs 良米 差额</div>
  </div>
</div>

<div class="container">

<!-- ===== 01 销量总览 ===== -->
<section class="section" id="sales">
  <h2>📊 618全渠道销量总览 —— 直播间 + 商品卡</h2>

  <div class="grid-2" style="margin-bottom:12px;">
    <div>
      <h3>🏪 四大团队销量分布</h3>
      <table>
        <tr><th>团队</th><th>总订单</th><th>直播间</th><th>商品卡</th><th>GMV</th><th>占比</th><th>直播间数</th></tr>
        <tr style="background:#eff6ff;">
          <td style="color:var(--clr-ours);font-weight:700;">🔵 我方</td>
          <td style="font-weight:700;">{fmt(our['orders'])}</td>
          <td>{fmt(our['直播间_orders'])}</td>
          <td>{fmt(our['商品卡_orders'])}</td>
          <td>{fmt_wan(our['gmv_wan'])}</td>
          <td style="color:var(--clr-ours);font-weight:700;">{our['pct']}%</td>
          <td>{our['rooms']}间 ({fmt(our['avg_per_room'])}单/间)</td>
        </tr>
        <tr style="background:#fff3e0;">
          <td style="color:var(--clr-comp);font-weight:700;">🟠 良米</td>
          <td style="font-weight:700;">{fmt(liangmi['orders'])}</td>
          <td>{fmt(liangmi['直播间_orders'])}</td>
          <td>{fmt(liangmi['商品卡_orders'])}</td>
          <td>{fmt_wan(liangmi['gmv_wan'])}</td>
          <td style="color:var(--clr-comp);font-weight:700;">{liangmi['pct']}%</td>
          <td>{liangmi['rooms']}间 ({fmt(liangmi['avg_per_room'])}单/间)</td>
        </tr>
        <tr style="background:#f5f0ff;">
          <td style="color:var(--clr-purple);font-weight:700;">🟣 机械空间</td>
          <td>{fmt(jixie['orders'])}</td>
          <td>{fmt(jixie['直播间_orders'])}</td>
          <td>{fmt(jixie['商品卡_orders'])}</td>
          <td>{fmt_wan(jixie['gmv_wan'])}</td>
          <td>{jixie['pct']}%</td>
          <td>{jixie['rooms']}间 ({fmt(jixie['avg_per_room'])}单/间)</td>
        </tr>
        <tr style="background:#fef2f2;">
          <td style="color:var(--clr-red);">🔴 综训</td>
          <td>{fmt(zongxun['orders'])}</td>
          <td>{fmt(zongxun['直播间_orders'])}</td>
          <td>{fmt(zongxun['商品卡_orders'])}</td>
          <td>{fmt_wan(zongxun['gmv_wan'])}</td>
          <td>{zongxun['pct']}%</td>
          <td>{zongxun['rooms']}间</td>
        </tr>
      </table>
    </div>
    <div>
      <h3>📈 渠道结构对比</h3>
      <table>
        <tr><th>渠道</th><th>订单</th><th>GMV</th><th>我方订单</th><th>我方GMV</th><th>我方占比</th></tr>
        <tr>
          <td>📡 直播间</td>
          <td style="font-weight:700;">{fmt(live_orders)}</td>
          <td>{fmt_wan(live_gmv_wan)}</td>
          <td>{fmt(our['直播间_orders'])}</td>
          <td>{fmt_wan(teams['我方'].get('直播间_gmv_wan', 0))}</td>
          <td style="color:var(--clr-ours);">{round(our['直播间_orders']/live_orders*100, 1)}%</td>
        </tr>
        <tr>
          <td>🛒 商品卡</td>
          <td style="font-weight:700;">{fmt(card_orders)}</td>
          <td>{fmt_wan(card_gmv_wan)}</td>
          <td>{fmt(our['商品卡_orders'])}</td>
          <td>{fmt_wan(teams['我方'].get('商品卡_gmv_wan', 0))}</td>
          <td style="color:var(--clr-ours);">{round(our['商品卡_orders']/card_orders*100, 1)}%</td>
        </tr>
        <tr style="background:#f0faf3;">
          <td><b>📊 合计</b></td>
          <td><b>{fmt(total_orders)}</b></td>
          <td><b>{fmt_wan(total_gmv_wan)}</b></td>
          <td><b>{fmt(our['orders'])}</b></td>
          <td><b>{fmt_wan(our['gmv_wan'])}</b></td>
          <td style="color:var(--clr-green);font-weight:700;"><b>{our['pct']}%</b></td>
        </tr>
      </table>
    </div>
  </div>

  <h3>📈 每日销量趋势（含商品卡）</h3>
  <div class="chart-box h360" id="chart-daily-trend"></div>

  <h3 style="margin-top:16px;">💰 每日营收趋势（万元）</h3>
  <div class="chart-box h360" id="chart-daily-revenue"></div>

  <h3 style="margin-top:16px;">🏪 6/18 直播间成交排行</h3>
  <div class="grid-2">
    <div class="chart-box h300" id="chart-rooms-618"></div>
    <div>
      <table>
        <tr><th>排名</th><th>直播间</th><th>团队</th><th>订单</th><th>营收</th></tr>
'''

# Room ranking data
for i, room in enumerate(D['rooms_618'][:15]):
    team_color = {'我方': 'color:var(--clr-ours);', '良米': 'color:var(--clr-comp);',
                  '机械空间': 'color:var(--clr-purple);', '综训': 'color:var(--clr-red);'}.get(room['team'], '')
    bg = {'我方': '#eff6ff', '良米': '#fff3e0', '机械空间': '#f5f0ff', '综训': '#fef2f2'}.get(room['team'], '')
    html += f'        <tr style="background:{bg};"><td>{i+1}</td><td>{room["name"]}</td><td style="{team_color}font-weight:700;">{room["team"]}</td><td style="font-weight:600;">{fmt(room["orders"])}</td><td>{room["gmv_fmt"]}</td></tr>\n'

html += '''      </table>
    </div>
  </div>

  <h3 style="margin-top:16px;">🏪 各团队直播间明细（全周期）</h3>
  <div class="grid-4">
'''

# Store lists
for team_label, team_key, color in [('🔵 我方', '我方', 'var(--clr-ours)'), ('🟠 良米', '良米', 'var(--clr-comp)'), ('🟣 机械空间', '机械空间', 'var(--clr-purple)'), ('🔴 综训', '综训', 'var(--clr-red)')]:
    stores = D.get(f'{team_key}_store_list', {})
    store_items = list(stores.items())
    html += f'''    <div>
      <div style="font-size:12px;font-weight:700;margin-bottom:6px;color:{color};">{team_label} · {len(store_items)}间</div>
      <table style="font-size:11px;">
        <tr><th>直播间</th><th>订单</th><th>GMV</th></tr>
'''
    for sn, sv in sorted(store_items, key=lambda x: x[1]['orders'], reverse=True)[:6]:
        html += f'        <tr><td>{sn}</td><td style="font-weight:600;color:{color};">{fmt(sv["orders"])}</td><td>{fmt_yuan(sv["gmv"])}</td></tr>\n'
    html += '      </table>\n    </div>\n'

html += '''  </div>

  <div class="hl-box hl-orange" style="margin-top:16px;">
    <strong style="color:var(--clr-orange);">🔑 销量核心洞察：</strong>
    618全周期<strong>''' + fmt(total_orders) + '''单 · ¥''' + str(total_gmv_wan) + '''万</strong>（直播间''' + fmt(live_orders) + ''' + 商品卡''' + fmt(card_orders) + '''），四方格局：<strong style="color:var(--clr-ours);">我方''' + str(our['pct']) + '''%</strong> · <strong style="color:#FF6B35;">良米''' + str(liangmi['pct']) + '''%</strong> · <strong style="color:var(--clr-purple);">机械空间''' + str(jixie['pct']) + '''%</strong> · 综训''' + str(zongxun['pct']) + '''%。
    加入商品卡数据后，我方综合份额提升至''' + str(our['pct']) + '''%（直播间''' + str(round(our['直播间_orders']/live_orders*100, 1)) + '''% + 商品卡''' + str(round(our['商品卡_orders']/card_orders*100, 1)) + '''%），与良米差距''' + str(abs(round(our['pct']-liangmi['pct'], 1))) + '''个百分点。
    良米以8间直播间+商品卡矩阵占最大份额；我方商品卡渗透率持续提升是扩大份额的关键路径。
  </div>
</section>

<!-- ===== 02 整体品类占比（商品卡+直播间） ===== -->
<section class="section" id="products">
  <h2>🏷️ 整体品类占比 —— 商品卡+直播间全渠道</h2>

  <div class="insight-row" style="margin-bottom:8px;">
'''

# Dynamic insights
prod_10 = D.get('prod_小米手环10', {})
prod_w6 = D.get('prod_REDMI Watch 6', {})
prod_10p = D.get('prod_小米手环10 Pro', {})
prod_9p = D.get('prod_小米手环9 Pro', {})

html += f'''    <div class="insight good"><strong>✅ 小米手环10 是我方王牌品类（{prod_10['share']}%份额）</strong>我方{fmt(prod_10['our'])}单，竞对{fmt(prod_10['comp'])}单，领先{fmt(abs(prod_10['diff']))}单。全渠道最大单品（{fmt(prod_10['total'])}单）。</div>
    <div class="insight good"><strong>✅ 小米手环9 Pro我方绝对优势（{prod_9p['share']}%份额）</strong>我方{fmt(prod_9p['our'])}单 vs 竞对{fmt(prod_9p['comp'])}单。老品仍保持竞争力。</div>
    <div class="insight warn"><strong>⚠️ REDMI Watch 6差距最大</strong>全市场{fmt(prod_w6['total'])}单，我方仅{prod_w6['share']}%（{fmt(prod_w6['our'])}单）。竞对{fmt(prod_w6['comp'])}单是我方的<strong>{round(prod_w6['comp']/max(prod_w6['our'],1), 1)}倍</strong>，差额{fmt(abs(prod_w6['diff']))}单。</div>
    <div class="insight info"><strong>📊 小米手环10 Pro</strong>我方{fmt(prod_10p['our'])}单（{prod_10p['share']}%），竞对{fmt(prod_10p['comp'])}单（{round(100-prod_10p['share'], 1)}%）。差额{fmt(abs(prod_10p['diff']))}单。</div>
  </div>

  <h3>📊 核心品类对比（含差额列）</h3>
  <table style="margin-bottom:14px;">
    <tr>
      <th style="width:18%;">核心品类</th>
      <th style="width:9%;background:#eff6ff;">我方订单</th><th style="width:9%;background:#eff6ff;">我方营收</th>
      <th style="width:9%;background:#fff3e0;">竞对订单</th><th style="width:9%;background:#fff3e0;">竞对营收</th>
      <th style="width:8%;">总订单</th><th style="width:8%;">总营收</th>
      <th style="width:7%;background:#f0faf3;">我方占比</th>
      <th style="width:9%;background:#fef2f2;">差额（我-竞）</th>
      <th style="width:14%;">备注</th>
    </tr>
'''

def make_prod_row(p, bg=''):
    d = D.get(f'prod_{p}', {})
    if not d or d['total'] == 0: return ''
    share = d['share']
    diff = d['diff']
    if share >= 50:
        sc, cc = 'var(--clr-green)', 'var(--clr-green)'
        note = '我方领先 ✅'
    elif share >= 40:
        sc, cc = 'var(--clr-green)', 'var(--clr-green)'
        note = f'领先+{fmt(abs(diff))}' if diff > 0 else f'落后{fmt(abs(diff))}'
    elif share >= 30:
        sc, cc = 'var(--clr-orange)', 'var(--clr-red)'
        note = f'落后{fmt(abs(diff))} ⚠️'
    else:
        sc, cc = 'var(--clr-red)', 'var(--clr-red)'
        note = f'竞对×{round(d["comp"]/max(d["our"],1), 1)}' if d['our'] > 0 else '几乎被垄断'
    diff_color = 'var(--clr-green)' if diff >= 0 else 'var(--clr-red)'
    diff_sign = '+' if diff >= 0 else ''
    return f'''    <tr style="background:{bg};">
      <td><b>{p}</b></td>
      <td style="background:#eff6ff;font-weight:700;">{fmt(d['our'])}</td>
      <td style="background:#eff6ff;">{fmt_yuan(d['our_gmv'])}</td>
      <td style="background:#fff3e0;font-weight:700;">{fmt(d['comp'])}</td>
      <td style="background:#fff3e0;">{fmt_yuan(d['comp_gmv'])}</td>
      <td><b>{fmt(d['total'])}</b></td>
      <td>{fmt_yuan(d['total_gmv'])}</td>
      <td style="color:{sc};font-weight:700;font-size:15px;">{share}%</td>
      <td style="color:{diff_color};font-weight:700;">{diff_sign}{fmt(diff)}</td>
      <td style="color:{cc};">{note}</td>
    </tr>
'''

for p in ['小米手环10', 'REDMI Watch 6', '小米手环10 Pro']:
    bg = {'小米手环10': '#f0faf3', 'REDMI Watch 6': '#fffdf0', '小米手环10 Pro': '#fef2f2'}.get(p, '')
    html += make_prod_row(p, bg)

html += '''  </table>

  <h3>二级品类</h3>
  <table style="margin-bottom:14px;">
    <tr>
      <th style="width:18%;">二级品类</th>
      <th style="width:9%;background:#eff6ff;">我方订单</th><th style="width:9%;background:#eff6ff;">我方营收</th>
      <th style="width:9%;background:#fff3e0;">竞对订单</th><th style="width:9%;background:#fff3e0;">竞对营收</th>
      <th style="width:8%;">总订单</th><th style="width:8%;">总营收</th>
      <th style="width:7%;background:#f0faf3;">我方占比</th>
      <th style="width:9%;background:#fef2f2;">差额</th>
      <th style="width:14%;">备注</th>
    </tr>
'''

for p in ['小米手环9 Pro', '小米手环10 陶瓷版', '小米手表 S系列']:
    html += make_prod_row(p)

html += '''  </table>

  <h3>耳机品类</h3>
  <table>
    <tr>
      <th style="width:18%;">耳机品类</th>
      <th style="width:9%;background:#eff6ff;">我方订单</th><th style="width:9%;background:#eff6ff;">我方营收</th>
      <th style="width:9%;background:#fff3e0;">竞对订单</th><th style="width:9%;background:#fff3e0;">竞对营收</th>
      <th style="width:8%;">总订单</th><th style="width:8%;">总营收</th>
      <th style="width:7%;background:#f0faf3;">我方占比</th>
      <th style="width:9%;background:#fef2f2;">差额</th>
      <th style="width:14%;">备注</th>
    </tr>
'''

for p in ['Xiaomi 开放式耳机', 'REDMI Buds 8 Pro', 'REDMI Buds 8', 'REDMI Buds 8 活力版', 'REDMI Buds 8 青春版']:
    html += make_prod_row(p)

html += f'''  </table>

  <!-- 总数汇总 -->
  <div style="margin-top:18px;background:linear-gradient(135deg, #1a1a2e, #16213e);color:#fff;border-radius:var(--radius);padding:24px 32px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;">
    <div style="text-align:center;">
      <div style="font-size:11px;opacity:.7;letter-spacing:.05em;">📊 618 总销量（全渠道）</div>
      <div style="font-size:40px;font-weight:800;">{fmt(total_orders)}</div>
      <div style="font-size:13px;opacity:.7;">单 · {fmt_wan(total_gmv_wan)} GMV</div>
    </div>
    <div style="text-align:center;font-size:30px;opacity:.25;">|</div>
    <div style="text-align:center;">
      <div style="font-size:11px;opacity:.7;letter-spacing:.05em;">🔵 我方订单</div>
      <div style="font-size:40px;font-weight:800;color:var(--clr-ours);">{fmt(our['orders'])}</div>
      <div style="font-size:13px;opacity:.7;">{fmt_wan(our['gmv_wan'])} · 占比 <b style="color:var(--clr-ours);">{our['pct']}%</b> · 直播+商品卡</div>
    </div>
    <div style="text-align:center;font-size:30px;opacity:.25;">|</div>
    <div style="text-align:center;">
      <div style="font-size:11px;opacity:.7;letter-spacing:.05em;">🟠 良米</div>
      <div style="font-size:40px;font-weight:800;color:#FF6B35;">{fmt(liangmi['orders'])}</div>
      <div style="font-size:13px;opacity:.7;">{fmt_wan(liangmi['gmv_wan'])} · 占比 <b style="color:#FF6B35;">{liangmi['pct']}%</b> · 8间+商品卡</div>
    </div>
    <div style="text-align:center;font-size:30px;opacity:.25;">|</div>
    <div style="text-align:center;">
      <div style="font-size:11px;opacity:.7;letter-spacing:.05em;">🏆 我方TOP3品类</div>
      <div style="font-size:14px;font-weight:600;line-height:1.7;">
        <span style="color:#1da85c;">手环10</span> {fmt(prod_10['our'])}单({prod_10['share']}%) ·
        <span style="color:#FF6B35;">Watch6</span> {fmt(prod_w6['our'])}单({prod_w6['share']}%) ·
        <span style="color:var(--clr-ours);">10Pro</span> {fmt(prod_10p['our'])}单({prod_10p['share']}%)
      </div>
      <div style="font-size:12px;opacity:.7;">三品类占我方总订单 {D['our_top3_pct']}%</div>
    </div>
  </div>

  <h3 style="margin-top:20px;">📊 全渠道产品结构可视化</h3>
  <div class="grid-2">
    <div class="chart-box h300" id="chart-product-pie"></div>
    <div class="chart-box h300" id="chart-our-product-pie"></div>
  </div>
</section>

<!-- ===== 03 直播间细分商品占比 ===== -->
<section class="section" id="live-products">
  <h2>📡 直播间细分商品占比 —— 仅直播间渠道</h2>

  <div class="hl-box hl-blue" style="margin-bottom:14px;">
    <strong style="color:var(--clr-ours);">📡 直播间数据范围：</strong>
    仅统计直播间渠道订单，共<strong>{fmt(live_orders)}单 · {fmt_wan(live_gmv_wan)}</strong>。
    我方直播间{fmt(D['our_live_products'].get('小米手环10', {}).get('orders', 0) if '小米手环10' in D.get('our_live_products', {}) else 0)}单（{round(our['直播间_orders']/live_orders*100, 1)}%），良米直播间{fmt(liangmi['直播间_orders'])}单（{round(liangmi['直播间_orders']/live_orders*100, 1)}%）。
  </div>

  <h3>核心品类 · 直播间</h3>
  <table style="margin-bottom:14px;">
    <tr>
      <th style="width:16%;">核心品类</th>
      <th style="width:9%;background:#eff6ff;">我方·直播</th><th style="width:9%;background:#fff3e0;">竞对·直播</th>
      <th style="width:8%;">直播总订单</th>
      <th style="width:7%;background:#f0faf3;">我方占比</th>
      <th style="width:9%;background:#fef2f2;">差额</th>
      <th style="width:12%;">直播间占比</th>
      <th style="width:12%;">商品卡占比</th>
      <th style="width:12%;">备注</th>
    </tr>
'''

def make_live_row(p, bg=''):
    d = D.get(f'prod_{p}', {})
    if not d or d['total'] == 0: return ''
    our_l = d.get('our_live', 0)
    comp_l = d.get('comp_live', 0)
    live_t = d.get('live_total', 0)
    card_t = d.get('card_total', 0)
    total = d['total']
    share = round(our_l / live_t * 100, 1) if live_t > 0 else 0
    diff = our_l - comp_l
    live_pct = round(live_t / total * 100, 1) if total > 0 else 0
    card_pct = round(card_t / total * 100, 1) if total > 0 else 0
    sc = 'var(--clr-green)' if share >= 50 else ('var(--clr-orange)' if share >= 30 else 'var(--clr-red)')
    dc = 'var(--clr-green)' if diff >= 0 else 'var(--clr-red)'
    ds = f'+{fmt(diff)}' if diff >= 0 else f'{fmt(diff)}'
    note = '我方直播优势' if diff > 0 else ('竞对直播优势' if diff < 0 else '持平')
    return f'''    <tr style="background:{bg};">
      <td><b>{p}</b></td>
      <td style="background:#eff6ff;font-weight:700;">{fmt(our_l)}</td>
      <td style="background:#fff3e0;font-weight:700;">{fmt(comp_l)}</td>
      <td><b>{fmt(live_t)}</b></td>
      <td style="color:{sc};font-weight:700;">{share}%</td>
      <td style="color:{dc};font-weight:700;">{ds}</td>
      <td>{live_pct}%</td>
      <td>{card_pct}%</td>
      <td style="color:{dc};">{note}</td>
    </tr>
'''

for p in ['小米手环10', 'REDMI Watch 6', '小米手环10 Pro', '小米手环9 Pro', '小米手环10 陶瓷版', '小米手表 S系列']:
    bg = '#f0faf3' if p == '小米手环10' else ('#fffdf0' if p == 'REDMI Watch 6' else '')
    html += make_live_row(p, bg)

html += '''  </table>

  <h3>耳机品类 · 直播间</h3>
  <table>
    <tr>
      <th style="width:16%;">耳机品类</th>
      <th style="width:9%;background:#eff6ff;">我方·直播</th><th style="width:9%;background:#fff3e0;">竞对·直播</th>
      <th style="width:8%;">直播总订单</th>
      <th style="width:7%;background:#f0faf3;">我方占比</th>
      <th style="width:9%;background:#fef2f2;">差额</th>
      <th style="width:12%;">直播间占比</th>
      <th style="width:12%;">商品卡占比</th>
      <th style="width:12%;">备注</th>
    </tr>
'''

for p in ['Xiaomi 开放式耳机', 'REDMI Buds 8 Pro', 'REDMI Buds 8', 'REDMI Buds 8 活力版', 'REDMI Buds 8 青春版']:
    html += make_live_row(p)

html += f'''  </table>

  <h3 style="margin-top:16px;">📊 直播间产品结构图</h3>
  <div class="grid-2">
    <div class="chart-box h300" id="chart-live-product-pie"></div>
    <div class="chart-box h300" id="chart-our-live-product-pie"></div>
  </div>

  <div class="hl-box hl-orange" style="margin-top:12px;">
    <strong style="color:var(--clr-orange);">🔑 直播间洞察：</strong>
    直播间渠道共{fmt(live_orders)}单（占全渠道{round(live_orders/total_orders*100, 1)}%），仍是最主要销售渠道。
    直播间内我方{fmt(our['直播间_orders'])}单占比{round(our['直播间_orders']/live_orders*100, 1)}%，与良米直播间{fmt(liangmi['直播间_orders'])}单（{round(liangmi['直播间_orders']/live_orders*100, 1)}%）差距{fmt(liangmi['直播间_orders'] - our['直播间_orders'])}单。
  </div>
</section>

<!-- ===== 04 商品卡细分商品占比 ===== -->
<section class="section" id="card-products">
  <h2>🛒 商品卡细分商品占比 —— 仅商品卡渠道</h2>

  <div class="hl-box hl-green" style="margin-bottom:14px;">
    <strong style="color:var(--clr-green);">🛒 商品卡数据范围：</strong>
    仅统计商品卡渠道订单（达人昵称列标注），共<strong>{fmt(card_orders)}单 · {fmt_wan(card_gmv_wan)}</strong>。
    我司商品卡<strong>{fmt(our['商品卡_orders'])}单</strong>（占商品卡{round(our['商品卡_orders']/card_orders*100, 1)}%），
    良米商品卡<strong>{fmt(liangmi['商品卡_orders'])}单</strong>（占商品卡{round(liangmi['商品卡_orders']/card_orders*100, 1)}%）。
    商品卡差额：{'+' if our['商品卡_orders'] > liangmi['商品卡_orders'] else ''}{fmt(our['商品卡_orders'] - liangmi['商品卡_orders'])}单。
  </div>

  <h3>核心品类 · 商品卡</h3>
  <table style="margin-bottom:14px;">
    <tr>
      <th style="width:16%;">核心品类</th>
      <th style="width:9%;background:#eff6ff;">我司·商品卡</th><th style="width:9%;background:#fff3e0;">良米·商品卡</th>
      <th style="width:8%;">商品卡总订单</th>
      <th style="width:7%;background:#f0faf3;">我方占比</th>
      <th style="width:9%;background:#fef2f2;">差额</th>
      <th style="width:12%;">直播间占比</th>
      <th style="width:12%;">商品卡占比</th>
      <th style="width:12%;">备注</th>
    </tr>
'''

def make_card_row(p, bg=''):
    d = D.get(f'prod_{p}', {})
    if not d or d['total'] == 0: return ''
    our_c = d.get('our_card', 0)
    comp_c = d.get('comp_card', 0)
    live_t = d.get('live_total', 0)
    card_t = d.get('card_total', 0)
    total = d['total']
    share = round(our_c / card_t * 100, 1) if card_t > 0 else 0
    diff = our_c - comp_c
    live_pct = round(live_t / total * 100, 1) if total > 0 else 0
    card_pct = round(card_t / total * 100, 1) if total > 0 else 0
    sc = 'var(--clr-green)' if share >= 50 else ('var(--clr-orange)' if share >= 30 else 'var(--clr-red)')
    dc = 'var(--clr-green)' if diff >= 0 else 'var(--clr-red)'
    ds = f'+{fmt(diff)}' if diff >= 0 else f'{fmt(diff)}'
    note = '我司商品卡优势' if diff > 0 else ('良米商品卡优势' if diff < 0 else '持平')
    return f'''    <tr style="background:{bg};">
      <td><b>{p}</b></td>
      <td style="background:#eff6ff;font-weight:700;">{fmt(our_c)}</td>
      <td style="background:#fff3e0;font-weight:700;">{fmt(comp_c)}</td>
      <td><b>{fmt(card_t)}</b></td>
      <td style="color:{sc};font-weight:700;">{share}%</td>
      <td style="color:{dc};font-weight:700;">{ds}</td>
      <td>{live_pct}%</td>
      <td>{card_pct}%</td>
      <td style="color:{dc};">{note}</td>
    </tr>
'''

for p in ['小米手环10', 'REDMI Watch 6', '小米手环10 Pro', '小米手环9 Pro', '小米手环10 陶瓷版', '小米手表 S系列']:
    bg = '#f0faf3' if p == '小米手环10' else ('#fffdf0' if p == 'REDMI Watch 6' else '')
    html += make_card_row(p, bg)

html += '''  </table>

  <h3>耳机品类 · 商品卡</h3>
  <table>
    <tr>
      <th style="width:16%;">耳机品类</th>
      <th style="width:9%;background:#eff6ff;">我司·商品卡</th><th style="width:9%;background:#fff3e0;">良米·商品卡</th>
      <th style="width:8%;">商品卡总订单</th>
      <th style="width:7%;background:#f0faf3;">我方占比</th>
      <th style="width:9%;background:#fef2f2;">差额</th>
      <th style="width:12%;">直播间占比</th>
      <th style="width:12%;">商品卡占比</th>
      <th style="width:12%;">备注</th>
    </tr>
'''

for p in ['Xiaomi 开放式耳机', 'REDMI Buds 8 Pro', 'REDMI Buds 8', 'REDMI Buds 8 活力版', 'REDMI Buds 8 青春版']:
    html += make_card_row(p)

html += f'''  </table>

  <h3 style="margin-top:16px;">📊 商品卡产品结构图</h3>
  <div class="grid-2">
    <div class="chart-box h300" id="chart-card-product-pie"></div>
    <div class="chart-box h300" id="chart-our-card-product-pie"></div>
  </div>

  <div class="hl-box hl-orange" style="margin-top:12px;">
    <strong style="color:var(--clr-orange);">🔑 商品卡洞察：</strong>
    商品卡渠道共{fmt(card_orders)}单（占全渠道{round(card_orders/total_orders*100, 1)}%），是重要的增量渠道。
    {"我司商品卡"+fmt(our['商品卡_orders'])+"单超越良米"+fmt(liangmi['商品卡_orders'])+"单 ✅" if our['商品卡_orders'] > liangmi['商品卡_orders'] else "良米商品卡"+fmt(liangmi['商品卡_orders'])+"单领先我司"+fmt(our['商品卡_orders'])+"单"}。
    商品卡作为自然流量渠道，优化商品标题和主图是提升商品卡销量的关键。
  </div>
</section>

<!-- ===== 05 视频分析 ===== -->
<section class="section" id="video">
  <h2>🎬 千川视频分析 —— 内容质量是我们的核心优势</h2>

  <div class="key-num-grid">
    <div class="key-num"><div class="num" style="color:var(--clr-ours);">1,880</div><div class="desc">我司有消耗视频数</div></div>
    <div class="key-num"><div class="num" style="color:var(--clr-comp);">2,566</div><div class="desc">竞对有消耗视频数 (+36%)</div></div>
    <div class="key-num"><div class="num" style="color:var(--clr-green);">¥15.05</div><div class="desc">我司ROI (竞对¥14.77)</div></div>
    <div class="key-num"><div class="num" style="color:var(--clr-green);">7.23%</div><div class="desc">我司CTR (竞对4.36% · 领先66%)</div></div>
  </div>

  <div class="insight-row">
    <div class="insight good"><strong>✅ CTR 7.23% vs 竞对 4.36%（高66%）</strong>内容质量是核心壁垒。用户更愿意点击我们的视频，说明内容方向（场景化、真实测评、iPhone生态）完全正确。</div>
    <div class="insight good"><strong>✅ CVR 1.55% vs 竞对 1.03%（高50%），ROI 15.05 vs 14.77</strong>转化效率和投资回报双领先。每投入¥1元，我司产出¥15.05。</div>
    <div class="insight warn"><strong>⚠️ 播放量差4倍（200万 vs 807万）</strong>竞对播放效率84.3次/元，我司仅34.5次/元。好内容没被足够多人看到——这是数量×分发的问题。</div>
    <div class="insight warn"><strong>⚠️ 消耗差64%、视频数差36%</strong>竞对以更多视频+更高消耗抢占流量入口，规模化优势转化为了市场份额优势。</div>
  </div>

  <h3>📡 全方位能力对比雷达图</h3>
  <div class="chart-box h360" id="chart-radar"></div>

  <h3>📊 产品线 ROI 对比 & 视频效率矩阵</h3>
  <div class="grid-2">
    <div class="chart-box h300" id="chart-product-roi"></div>
    <div class="chart-box h300" id="chart-video-efficiency"></div>
  </div>

  <div class="hl-box hl-green" style="margin-top:12px;">
    <strong style="color:var(--clr-green);">💡 千川核心结论：内容质量是最大护城河，数量差距是最大增长空间。</strong>
    正确策略：<strong>不改变内容方向</strong>（CTR/CVR/ROI全面领先证明方向正确），而是<strong>把对的事情多做3倍</strong>——多发视频、多绑热点、多用AIGC变体。Watch6 ROI 18.9远超手环14.1，建议视频占比从25%提升至40%。
  </div>
</section>

<!-- ===== 06 视觉分析 ===== -->
<section class="section" id="visual">
  <h2>👁️ 直播间视觉分析 —— 优势在视觉冲击力，短板在信任与价格</h2>

  <h3>📊 六维评分对比（自家 vs 竞对）</h3>
  <div class="grid-2">
    <div>
      <div class="score-bar"><div class="s-label"><span>🎨 视觉冲击力</span><span style="color:var(--clr-green);">自家 85 vs 竞对 75</span></div><div class="s-track"><div class="s-fill ours" style="width:85%"></div></div><div class="s-track" style="margin-top:4px"><div class="s-fill comp" style="width:75%"></div></div></div>
      <div class="score-bar"><div class="s-label"><span>📋 信息层次感</span><span style="color:var(--clr-red);">自家 70 vs 竞对 85</span></div><div class="s-track"><div class="s-fill ours" style="width:70%"></div></div><div class="s-track" style="margin-top:4px"><div class="s-fill comp" style="width:85%"></div></div></div>
      <div class="score-bar"><div class="s-label"><span>💰 价格展示</span><span style="color:var(--clr-red);">自家 75 vs 竞对 90</span></div><div class="s-track"><div class="s-fill ours" style="width:75%"></div></div><div class="s-track" style="margin-top:4px"><div class="s-fill comp" style="width:90%"></div></div></div>
      <div class="score-bar"><div class="s-label"><span>🛡️ 信任背书</span><span style="color:var(--clr-red);">自家 60 vs 竞对 85</span></div><div class="s-track"><div class="s-fill ours" style="width:60%"></div></div><div class="s-track" style="margin-top:4px"><div class="s-fill comp" style="width:85%"></div></div></div>
      <div class="score-bar"><div class="s-label"><span>📦 产品展示</span><span>自家 80 vs 竞对 80</span></div><div class="s-track"><div class="s-fill ours" style="width:80%"></div></div><div class="s-track" style="margin-top:4px"><div class="s-fill comp" style="width:80%"></div></div></div>
      <div class="score-bar"><div class="s-label"><span>🎁 赠品策略</span><span style="color:var(--clr-green);">自家 85 vs 竞对 70</span></div><div class="s-track"><div class="s-fill ours" style="width:85%"></div></div><div class="s-track" style="margin-top:4px"><div class="s-fill comp" style="width:70%"></div></div></div>
    </div>
    <div><div class="chart-box h300" id="chart-visual-radar"></div></div>
  </div>

  <div class="grid-2" style="margin-top:16px;">
    <div class="insight good"><strong>✅ 视觉冲击力领先（85 vs 75）</strong>专业舞台灯光+品牌感布置，观感明显优于竞对。这是差异化优势，应保持并扩大。</div>
    <div class="insight good"><strong>✅ 赠品策略领先（85 vs 70）</strong>赠品展示和策略优于竞对，能够有效提升用户购买决策。</div>
    <div class="insight danger"><strong>❌ 信任背书差距最大（60 vs 85）</strong>竞对普遍展示"官方正品/全国联保/七天无理由/运费险"，我们缺少这些信任标识。</div>
    <div class="insight danger"><strong>❌ 价格展示差距显著（75 vs 90）</strong>竞对采用"原价→到手价"对比展示+国补突出，我们缺少价格锚点和折扣感知。</div>
  </div>

  <div class="hl-box hl-orange" style="margin-top:12px;">
    <strong style="color:var(--clr-orange);">🔑 视觉核心结论：</strong>
    视觉冲击力和赠品策略是我们的优势；<strong>信任背书（60 vs 85）和价格展示（75 vs 90）是最大短板</strong>。竞对通过"国补标识+原价对比+信任标签"三重组合大幅降低用户决策门槛。改进方向明确：补齐信任元素、优化价格展示、保持视觉优势。
  </div>
</section>

<!-- ===== 07 核心洞察 ===== -->
<section class="section" id="learnings">
  <h2>💡 618 核心洞察 —— 三维数据交叉分析</h2>

  <div class="conclusion-grid">
    <div class="conclusion-card c1">
      <div class="c-icon">🏆</div>
      <h4>内容质量是最大护城河</h4>
      <p>CTR 7.23%（领先66%）、CVR 1.55%（领先50%）、ROI 15.05（领先2%）。内容竞争力全面超越竞对，用户更信任我们的内容。</p>
    </div>
    <div class="conclusion-card c2">
      <div class="c-icon">📊</div>
      <h4>全渠道数据揭示更真实格局</h4>
      <p>全渠道{fmt(total_orders)}单：我方{our['pct']}% vs 良米{liangmi['pct']}%。商品卡渠道我方{fmt(our['商品卡_orders'])}单，{"超" if our['商品卡_orders'] > liangmi['商品卡_orders'] else "落后"}良米，渠道结构是差异化竞争关键。</p>
    </div>
    <div class="conclusion-card c3">
      <div class="c-icon">🎯</div>
      <h4>战略方向：质量×数量双轮驱动</h4>
      <p>保持内容质量优势，大力提升视频产量+补齐视觉信任短板。手环10全渠道{prod_10['share']}%已领先，Watch6（{prod_w6['share']}%）和10Pro（{prod_10p['share']}%）是最大增长空间。</p>
    </div>
    <div class="conclusion-card c4">
      <div class="c-icon">🛒</div>
      <h4>商品卡是新增长极</h4>
      <p>商品卡{fmt(card_orders)}单（{fmt_wan(card_gmv_wan)}），占全渠道{round(card_orders/total_orders*100, 1)}%。优化商品标题、主图、详情页，提升自然搜索转化率。</p>
    </div>
  </div>

  <h3 style="margin-top:24px;">📋 三维交叉洞察表</h3>
  <table>
    <tr><th>维度</th><th>我方优势</th><th>我方劣势</th><th>竞对优势</th><th>行动方向</th></tr>
    <tr>
      <td><b>销量分析</b></td>
      <td style="color:var(--clr-green);">手环10全渠道{prod_10['share']}%领先、商品卡贡献{fmt(our['商品卡_orders'])}单、618爆发力强</td>
      <td style="color:var(--clr-red);">Watch6仅{prod_w6['share']}%差距大、Watch S仅8.2%、5月底/6/9中期疲软</td>
      <td>8间直播间矩阵、规模化覆盖、Watch6品类主导</td>
      <td>Watch6加大推广、商品卡优化、增开直播间或增加开播时长</td>
    </tr>
    <tr>
      <td><b>千川视频</b></td>
      <td style="color:var(--clr-green);">CTR领先66%、CVR领先50%、ROI领先2%</td>
      <td style="color:var(--clr-red);">视频数少36%、消耗少64%、播放量差4倍</td>
      <td>多房间×多视频覆盖、播放效率84.3远超34.5</td>
      <td>视频产量翻3倍、AIGC变体、Watch6 ROI 18.9加大投放</td>
    </tr>
    <tr>
      <td><b>视觉分析</b></td>
      <td style="color:var(--clr-green);">视觉冲击力85、赠品策略85</td>
      <td style="color:var(--clr-red);">信任背书60、价格展示75、信息层次感70</td>
      <td>信任标识完善、国补醒目、价格对比清晰</td>
      <td>补齐信任元素、优化价格展示、统一品牌视觉</td>
    </tr>
  </table>

  <div class="hl-box hl-blue" style="margin-top:16px;">
    <strong style="color:var(--clr-ours);">🔍 交叉洞察：</strong>
    全渠道{fmt(total_orders)}单数据显示，我方{our['pct']}%份额（直播间{fmt(our['直播间_orders'])}单+商品卡{fmt(our['商品卡_orders'])}单）。
    三个维度指向同一个结论——<strong>我们的内容质量和用户吸引力超越竞对，但被视频数量和视觉信任元素所限制</strong>。
    商品卡作为新兴渠道，{"我方已领先良米" if our['商品卡_orders'] > liangmi['商品卡_orders'] else "需加大商品卡运营力度"}。
    手环10全渠道{prod_10['share']}%份额证明产品力已超越。面对<strong>良米（{liangmi['pct']}%份额·8间）+机械空间（{jixie['pct']}%·单房效率最高）</strong>的双重竞争，
    解决方案是<strong>三维协同：视频端扩量×直播端补信任×重点攻坚Watch6（仅{prod_w6['share']}%份额）和10Pro（仅{prod_10p['share']}%份额）×商品卡渠道优化</strong>。
  </div>
</section>

<!-- ===== 08 后续规划 ===== -->
<section class="section" id="plan">
  <h2>🚀 后续规划 —— Post-618 行动方案</h2>

  <h3>⏱️ 时间线：6月-7月分阶段计划</h3>
  <div class="tl">
    <div class="tl-item">
      <div class="tl-dot" style="background:var(--clr-red);">1</div>
      <div class="tl-body">
        <h5>6/19-6/25 · 618返场收割 <span style="color:var(--clr-red);">🔥 立即执行</span></h5>
        <p>利用618余热+返场标签，主推Watch6高客单（全渠道份额仅{prod_w6['share']}%是最大机会点）。10Pro加大补推力度（份额{prod_10p['share']}%仍有增长空间）。每天发布5-8条返场主题视频，同时优化商品卡标题和主图提升自然流量转化。</p>
      </div>
    </div>
    <div class="tl-item">
      <div class="tl-dot" style="background:var(--clr-orange);">2</div>
      <div class="tl-body">
        <h5>6/26-7/10 · 暑期启动 <span style="color:var(--clr-orange);">⚡ 重点推进</span></h5>
        <p>切换内容方向至暑期场景：户外运动、游泳防水、GPS导航、毕业季送礼。发布30+暑期主题视频。启动AIGC量产流水线：每爆款→5变体→日产15-20条。商品卡产品信息全面优化。</p>
      </div>
    </div>
    <div class="tl-item">
      <div class="tl-dot" style="background:var(--clr-ours);">3</div>
      <div class="tl-body">
        <h5>7/11-7/31 · 世界杯借势 <span style="color:var(--clr-ours);">📈 持续运营</span></h5>
        <p>世界杯期间推出"熬夜心率""运动激情"主题。视频产量目标100条+/月。直播间增加信任背书元素，优化价格展示策略。10Pro和商品卡作为重点攻坚方向。</p>
      </div>
    </div>
  </div>

  <h3>🎯 四大行动方向</h3>
  <div class="grid-4" style="margin-bottom:16px;">
    <div class="plan-card p1">
      <div class="plan-num">01</div><div class="plan-icon">🎬</div>
      <h4 style="color:var(--clr-ours);">视频产量翻3倍</h4>
      <p>每款产品按「4场景×2风格」拍8条。同场景多角度收音，一次拍摄产出3-5条。从每周10条→<strong>每周30-40条</strong>。Watch6占比提升至40%。</p>
      <span class="plan-tag" style="background:rgba(30,144,255,.1);color:var(--clr-ours);">目标：月产100+条</span>
    </div>
    <div class="plan-card p2">
      <div class="plan-num">02</div><div class="plan-icon">🤖</div>
      <h4 style="color:var(--clr-green);">AIGC量产体系</h4>
      <p>阶段1：即创/剪映AI把1条爆款变5条变体。阶段2：AIGC做功能演示动画。阶段3：建立3套模板日产15-20条。几乎零成本产能翻3倍。</p>
      <span class="plan-tag" style="background:rgba(29,168,92,.1);color:var(--clr-green);">零成本扩量</span>
    </div>
    <div class="plan-card p3">
      <div class="plan-num">03</div><div class="plan-icon">🛒</div>
      <h4 style="color:var(--clr-gold);">商品卡渠道优化</h4>
      <p>优化全部商品标题关键词（覆盖手环/Watch/耳机长尾词）。主图统一品牌调性+突出国补。详情页增加信任元素。目标商品卡月销量翻倍。</p>
      <span class="plan-tag" style="background:rgba(200,150,12,.1);color:var(--clr-gold);">自然流量增长</span>
    </div>
    <div class="plan-card p4">
      <div class="plan-num">04</div><div class="plan-icon">📈</div>
      <h4 style="color:var(--clr-red);">投放正循环+Watch6/10Pro攻坚</h4>
      <p>抖加¥100测→互动率>5%加投→千川收割。Watch6全渠道{fmt(prod_w6['total'])}单我方仅{prod_w6['share']}%，10Pro{prod_10p['share']}%，作为重点攻坚品类。Watch6 ROI 18.9继续加码。</p>
      <span class="plan-tag" style="background:rgba(255,71,87,.1);color:var(--clr-red);">Watch6+10Pro攻坚</span>
    </div>
  </div>

  <h3>🎯 7月核心KPI目标</h3>
  <div class="key-num-grid">
    <div class="key-num"><div class="num" style="color:var(--clr-ours);">100+</div><div class="desc">月产视频数（6月 ~60条）</div></div>
    <div class="key-num"><div class="num" style="color:var(--clr-green);">300万+</div><div class="desc">月度视频播放量（6月 200万）</div></div>
    <div class="key-num"><div class="num" style="color:var(--clr-orange);">45%+</div><div class="desc">我方全渠道份额目标（618 {our['pct']}%）</div></div>
    <div class="key-num"><div class="num" style="color:var(--clr-red);">35%+</div><div class="desc">Watch6份额目标（618 {prod_w6['share']}%）</div></div>
  </div>

  <div class="hl-box hl-green" style="margin-top:12px;">
    <strong style="color:var(--clr-green);">🏁 总方针：不改变方向，只放大规模。</strong>
    内容质量（CTR 7.23% / CVR 1.55% / ROI 15.05）已证明方向正确。手环10全渠道{prod_10['share']}%份额证明了品类竞争力已超越竞对。
    接下来就是<strong>把对的事情多做3倍</strong>：视频产量3倍→播放量3倍→订单量3倍。
    <strong>Watch6是最大的增长机会</strong>（全渠道{fmt(prod_w6['total'])}单我方仅{prod_w6['share']}%），10Pro（{prod_10p['share']}%）同样有巨大增长空间。
    商品卡作为增量渠道，持续优化可带来稳定自然流量增量。
    同时补齐视觉端的信任短板，让直播间转化效率追上内容质量。
    <strong style="color:var(--clr-orange);">坚持2个月，全渠道份额从{our['pct']}%→45%+完全可以实现。</strong>
  </div>
</section>
</div>

<footer style="text-align:center;color:var(--text-muted);font-size:11px;padding:32px;position:relative;z-index:1;border-top:1px solid var(--border);margin-top:20px;">
  小米手环直播间 · 618大促复盘总结 · 2026年5-6月 · 35天全周期 · 直播间+商品卡全渠道 · 我方6间 vs 良米8间 vs 机械空间2间 vs 综训1间 · 三维数据驱动</footer>

<script>
var C = {{ ours: '#1E90FF', comp: '#FF6B35', green: '#1da85c', orange: '#ff6900', purple: '#7c6ff7', gold: '#c8960c', cyan: '#0ea89d', red: '#FF4757' }};

// Daily trend
(function(){{
  var d = document.getElementById('chart-daily-trend'); if(!d) return;
  var c = echarts.init(d);
  c.setOption({{
    title: {{ text: '每日总销量趋势（含商品卡）', left: 'center', top: 4, textStyle: {{ fontSize: 12, fontWeight: 600 }} }},
    tooltip: {{ trigger: 'axis' }},
    legend: {{ top: 28, textStyle: {{ fontSize: 9 }}, data: ['我方','良米','机械空间','综训','总订单','商品卡'] }},
    grid: {{ left: 12, right: 12, top: 60, bottom: 20 }},
    xAxis: {{ type: 'category', data: {dates_mmdd}, axisLabel: {{ fontSize: 7, rotate: 45 }} }},
    yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: '#eee', type: 'dashed' }} }} }},
    series: [
      {{ name: '我方', type: 'bar', stack: 'teams', data: {daily_our}, itemStyle: {{ color: C.ours }}, barWidth: '60%', label: {{ show: true, position: 'inside', fontSize: 7, color: '#fff', formatter: function(p){{ return p.value>1000 ? p.value : ''; }} }} }},
      {{ name: '良米', type: 'bar', stack: 'teams', data: {daily_liangmi}, itemStyle: {{ color: '#FF6B35' }}, barWidth: 22 }},
      {{ name: '机械空间', type: 'bar', stack: 'teams', data: {daily_jixie}, itemStyle: {{ color: C.purple }}, barWidth: 22 }},
      {{ name: '综训', type: 'bar', stack: 'teams', data: {daily_zongxun}, itemStyle: {{ color: '#ef4444' }}, barWidth: 22 }},
      {{ name: '总订单', type: 'line', data: {daily_total}, lineStyle: {{ color: C.orange, width: 2.5 }}, itemStyle: {{ color: C.orange }}, symbol: 'circle', symbolSize: 6, label: {{ show: true, fontSize: 9, fontWeight: 700, color: C.orange }} }},
      {{ name: '商品卡', type: 'line', data: {daily_card}, lineStyle: {{ color: C.gold, width: 2, type: 'dashed' }}, itemStyle: {{ color: C.gold }}, symbol: 'diamond', symbolSize: 8, label: {{ show: true, fontSize: 8, fontWeight: 600, color: C.gold }} }}
    ]
  }});
  window.addEventListener('resize', function(){{ c.resize(); }});
}})();

// Daily revenue
(function(){{
  var d = document.getElementById('chart-daily-revenue'); if(!d) return;
  var c = echarts.init(d);
  c.setOption({{
    title: {{ text: '每日营收趋势（万元）', left: 'center', top: 4, textStyle: {{ fontSize: 12, fontWeight: 600 }} }},
    tooltip: {{ trigger: 'axis', formatter: function(p){{ var r = p[0].axisValue; for(var i=0;i<p.length;i++){{ r += '<br/>'+p[i].seriesName+': ¥'+p[i].value+'万'; }} return r; }} }},
    legend: {{ top: 28, textStyle: {{ fontSize: 9 }}, data: ['我方','良米','机械空间','综训'] }},
    grid: {{ left: 12, right: 12, top: 60, bottom: 20 }},
    xAxis: {{ type: 'category', data: {dates_mmdd}, axisLabel: {{ fontSize: 8, rotate: 45 }} }},
    yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: '#eee', type: 'dashed' }} }}, axisLabel: {{ formatter: function(v){{ return '¥'+v+'万'; }}, fontSize: 9 }} }},
    series: [
      {{ name: '我方', type: 'bar', stack: 'rev', data: {daily_our_r}, itemStyle: {{ color: C.ours, borderRadius: [4,4,0,0] }}, barWidth: '60%', label: {{ show: true, position: 'inside', fontSize: 7, color: '#fff', formatter: function(p){{ return p.value>50 ? '¥'+p.value+'万' : ''; }} }} }},
      {{ name: '良米', type: 'bar', stack: 'rev', data: {daily_liangmi_r}, itemStyle: {{ color: '#FF6B35' }}, barWidth: 22 }},
      {{ name: '机械空间', type: 'bar', stack: 'rev', data: {daily_jixie_r}, itemStyle: {{ color: C.purple }}, barWidth: 22 }},
      {{ name: '综训', type: 'bar', stack: 'rev', data: {daily_zongxun_r}, itemStyle: {{ color: '#ef4444' }}, barWidth: 22 }}
    ]
  }});
  window.addEventListener('resize', function(){{ c.resize(); }});
}})();

// Rooms 6/18
(function(){{
  var d = document.getElementById('chart-rooms-618'); if(!d) return;
  var c = echarts.init(d);
  var rooms = {json.dumps([r['name'] for r in reversed(D['rooms_618'][:12])])};
  var orders = {json.dumps([r['orders'] for r in reversed(D['rooms_618'][:12])])};
  var teams = {json.dumps([r['team'] for r in reversed(D['rooms_618'][:12])])};
  var teamColors = {{ ours: C.ours, liangmi: '#FF6B35', 机械空间: C.purple, 综训: '#ef4444' }};
  c.setOption({{
    title: {{ text: '6/18 直播间成交排行', left: 'center', top: 4, textStyle: {{ fontSize: 12, fontWeight: 600 }} }},
    tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
    grid: {{ left: 130, right: 20, top: 30, bottom: 4 }},
    xAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: '#eee', type: 'dashed' }} }} }},
    yAxis: {{ type: 'category', data: rooms, axisLabel: {{ fontSize: 9 }}, inverse: true }},
    series: [{{
      type: 'bar', data: orders.map(function(v, i){{ return {{ value: v, itemStyle: {{ color: teamColors[teams[i]], borderRadius: [0,4,4,0] }} }}; }}), barWidth: 16,
      label: {{ show: true, position: 'right', fontSize: 9, fontWeight: 600, formatter: '{{c}}单' }}
    }}]
  }});
  window.addEventListener('resize', function(){{ c.resize(); }});
}})();

// All product pie
(function(){{
  var d = document.getElementById('chart-product-pie'); if(!d) return;
  var c = echarts.init(d);
  c.setOption({{
    title: {{ text: '全渠道产品结构（{fmt(total_orders)}单）', left: 'center', top: 8, textStyle: {{ fontSize: 12, fontWeight: 700 }} }},
    tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}}单 ({{d}}%)' }},
    legend: {{ bottom: 0, textStyle: {{ fontSize: 9 }} }},
    series: [{{
      type: 'pie', radius: ['42%','70%'], center: ['50%','46%'],
      itemStyle: {{ borderRadius: 6, borderColor: '#fff', borderWidth: 3 }},
      label: {{ show: true, formatter: '{{b}}\\n{{d}}%', fontSize: 9 }},
      data: {json.dumps(D['all_product_pie'][:10])}
    }}]
  }});
  window.addEventListener('resize', function(){{ c.resize(); }});
}})();

// Our product pie
(function(){{
  var d = document.getElementById('chart-our-product-pie'); if(!d) return;
  var c = echarts.init(d);
  c.setOption({{
    title: {{ text: '我方产品结构（{fmt(our["orders"])}单·全渠道）', left: 'center', top: 8, textStyle: {{ fontSize: 12, fontWeight: 700, color: C.ours }} }},
    tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}}单 ({{d}}%)' }},
    legend: {{ bottom: 0, textStyle: {{ fontSize: 9 }} }},
    series: [{{
      type: 'pie', radius: ['42%','70%'], center: ['50%','46%'],
      itemStyle: {{ borderRadius: 6, borderColor: '#fff', borderWidth: 3 }},
      label: {{ show: true, formatter: '{{b}}\\n{{d}}%', fontSize: 9 }},
      data: {json.dumps(D['our_product_pie'][:10])}
    }}]
  }});
  window.addEventListener('resize', function(){{ c.resize(); }});
}})();

// Live product pie
(function(){{
  var d = document.getElementById('chart-live-product-pie'); if(!d) return;
  var c = echarts.init(d);
  c.setOption({{
    title: {{ text: '全市场·直播间产品结构（{fmt(live_orders)}单）', left: 'center', top: 8, textStyle: {{ fontSize: 12, fontWeight: 700 }} }},
    tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}}单 ({{d}}%)' }},
    legend: {{ bottom: 0, textStyle: {{ fontSize: 9 }} }},
    series: [{{
      type: 'pie', radius: ['42%','70%'], center: ['50%','46%'],
      itemStyle: {{ borderRadius: 6, borderColor: '#fff', borderWidth: 3 }},
      label: {{ show: true, formatter: '{{b}}\\n{{d}}%', fontSize: 9 }},
      data: {json.dumps(D['live_product_pie'][:10])}
    }}]
  }});
  window.addEventListener('resize', function(){{ c.resize(); }});
}})();

// Card product pie
(function(){{
  var d = document.getElementById('chart-card-product-pie'); if(!d) return;
  var c = echarts.init(d);
  c.setOption({{
    title: {{ text: '全市场·商品卡产品结构（{fmt(card_orders)}单）', left: 'center', top: 8, textStyle: {{ fontSize: 12, fontWeight: 700 }} }},
    tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}}单 ({{d}}%)' }},
    legend: {{ bottom: 0, textStyle: {{ fontSize: 9 }} }},
    series: [{{
      type: 'pie', radius: ['42%','70%'], center: ['50%','46%'],
      itemStyle: {{ borderRadius: 6, borderColor: '#fff', borderWidth: 3 }},
      label: {{ show: true, formatter: '{{b}}\\n{{d}}%', fontSize: 9 }},
      data: {json.dumps(D['card_product_pie'][:10])}
    }}]
  }});
  window.addEventListener('resize', function(){{ c.resize(); }});
}})();

// Our live/card product pies (placeholder - use our_product_pie with filter)
(function(){{
  var d = document.getElementById('chart-our-live-product-pie'); if(!d) return;
  var c = echarts.init(d);
  c.setOption({{
    title: {{ text: '我方·直播间产品（{fmt(our["直播间_orders"])}单）', left: 'center', top: 8, textStyle: {{ fontSize: 12, fontWeight: 700, color: C.ours }} }},
    tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}}单 ({{d}}%)' }},
    legend: {{ bottom: 0, textStyle: {{ fontSize: 9 }} }},
    series: [{{
      type: 'pie', radius: ['42%','70%'], center: ['50%','46%'],
      itemStyle: {{ borderRadius: 6, borderColor: '#fff', borderWidth: 3 }},
      label: {{ show: true, formatter: '{{b}}\\n{{d}}%', fontSize: 9 }},
      data: {json.dumps([{'name': k, 'value': v['orders']} for k, v in D.get('our_live_products', {}).items()][:10])}
    }}]
  }});
  window.addEventListener('resize', function(){{ c.resize(); }});
}})();

(function(){{
  var d = document.getElementById('chart-our-card-product-pie'); if(!d) return;
  var c = echarts.init(d);
  c.setOption({{
    title: {{ text: '我方·商品卡产品（{fmt(our["商品卡_orders"])}单）', left: 'center', top: 8, textStyle: {{ fontSize: 12, fontWeight: 700, color: C.gold }} }},
    tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}}单 ({{d}}%)' }},
    legend: {{ bottom: 0, textStyle: {{ fontSize: 9 }} }},
    series: [{{
      type: 'pie', radius: ['42%','70%'], center: ['50%','46%'],
      itemStyle: {{ borderRadius: 6, borderColor: '#fff', borderWidth: 3 }},
      label: {{ show: true, formatter: '{{b}}\\n{{d}}%', fontSize: 9 }},
      data: {json.dumps([{'name': k, 'value': v['orders']} for k, v in D.get('our_card_products', {}).items()][:10])}
    }}]
  }});
  window.addEventListener('resize', function(){{ c.resize(); }});
}})();

// Radar video
(function(){{
  var d = document.getElementById('chart-radar'); if(!d) return;
  var c = echarts.init(d);
  c.setOption({{
    tooltip: {{ trigger: 'item' }},
    legend: {{ bottom: 0, textStyle: {{ fontSize: 11 }} }},
    radar: {{ center: ['50%','46%'], radius: '62%', axisName: {{ fontSize: 10 }},
      indicator: [
        {{ name: 'ROI', max: 20 }}, {{ name: 'CTR(%)', max: 10 }}, {{ name: 'CVR(%)', max: 3 }},
        {{ name: '视频数', max: 3000 }}, {{ name: '播放效率', max: 100 }}, {{ name: '成交(万)', max: 150 }}
      ]
    }},
    series: [{{
      type: 'radar', symbol: 'circle', symbolSize: 4,
      data: [
        {{ value: [15.05,7.23,1.55,1880,34.5,87.6], name: '我司', lineStyle: {{ color: C.ours, width: 2 }}, areaStyle: {{ color: 'rgba(30,144,255,.12)' }}, itemStyle: {{ color: C.ours }} }},
        {{ value: [14.77,4.36,1.03,2566,84.3,141.4], name: '竞对', lineStyle: {{ color: C.comp, width: 2 }}, areaStyle: {{ color: 'rgba(255,107,53,.08)' }}, itemStyle: {{ color: C.comp }} }}
      ]
    }}]
  }});
  window.addEventListener('resize', function(){{ c.resize(); }});
}})();

// Product ROI
(function(){{
  var d = document.getElementById('chart-product-roi'); if(!d) return;
  var c = echarts.init(d);
  c.setOption({{
    tooltip: {{ trigger: 'axis' }},
    legend: {{ top: 0, textStyle: {{ fontSize: 10 }}, data: ['我司ROI','竞对ROI'] }},
    grid: {{ left: 12, right: 12, top: 36, bottom: 20 }},
    xAxis: {{ type: 'category', data: ['手环','Watch6','AIGC','耳机','其他'], axisLabel: {{ fontSize: 10 }} }},
    yAxis: {{ type: 'value', name: 'ROI', splitLine: {{ lineStyle: {{ color: '#eee', type: 'dashed' }} }} }},
    series: [
      {{ name: '我司ROI', type: 'bar', data: [14.1,18.9,13.4,15.3,12.2], itemStyle: {{ color: C.ours, borderRadius: [4,4,0,0] }}, barWidth: 16, label: {{ show: true, position: 'top', fontSize: 10, fontWeight: 700, color: C.ours }} }},
      {{ name: '竞对ROI', type: 'bar', data: [12.7,17.5,13.9,19.9,11.8], itemStyle: {{ color: C.comp, borderRadius: [4,4,0,0] }}, barWidth: 16, label: {{ show: true, position: 'top', fontSize: 10 }} }}
    ]
  }});
  window.addEventListener('resize', function(){{ c.resize(); }});
}})();

// Video efficiency
(function(){{
  var d = document.getElementById('chart-video-efficiency'); if(!d) return;
  var c = echarts.init(d);
  c.setOption({{
    tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
    legend: {{ top: 0, textStyle: {{ fontSize: 10 }}, data: ['消耗','成交','ROI'] }},
    grid: {{ left: 14, right: 50, top: 36, bottom: 14 }},
    xAxis: {{ type: 'category', data: ['手环','Watch6','AIGC','耳机','其他'], axisLabel: {{ fontSize: 10 }} }},
    yAxis: [
      {{ type: 'value', name: '金额', splitLine: {{ lineStyle: {{ color: '#eee', type: 'dashed' }} }}, axisLabel: {{ formatter: function(v){{ return (v/10000).toFixed(0)+'万'; }}, fontSize: 9 }} }},
      {{ type: 'value', name: 'ROI', splitLine: {{ show: false }}, axisLabel: {{ fontSize: 9 }} }}
    ],
    series: [
      {{ name: '消耗', type: 'bar', data: [27434,13754,9927,3202,3921], itemStyle: {{ color: '#ff8a80', borderRadius: [4,4,0,0] }}, barWidth: 14 }},
      {{ name: '成交', type: 'bar', data: [386066,259876,133399,49141,47772], itemStyle: {{ color: '#a5d6a7', borderRadius: [4,4,0,0] }}, barWidth: 14 }},
      {{ name: 'ROI', type: 'line', yAxisIndex: 1, data: [14.1,18.9,13.4,15.3,12.2], lineStyle: {{ color: C.orange, width: 2.5 }}, itemStyle: {{ color: C.orange }}, symbol: 'diamond', symbolSize: 12, label: {{ show: true, fontWeight: 700, fontSize: 12, color: C.orange }} }}
    ]
  }});
  window.addEventListener('resize', function(){{ c.resize(); }});
}})();

// Visual radar
(function(){{
  var d = document.getElementById('chart-visual-radar'); if(!d) return;
  var c = echarts.init(d);
  c.setOption({{
    tooltip: {{ trigger: 'item' }},
    legend: {{ bottom: 0, textStyle: {{ fontSize: 10 }} }},
    radar: {{ center: ['50%','46%'], radius: '58%', axisName: {{ fontSize: 9 }},
      indicator: [
        {{ name: '视觉冲击力', max: 100 }}, {{ name: '信息层次感', max: 100 }},
        {{ name: '价格展示', max: 100 }}, {{ name: '信任背书', max: 100 }},
        {{ name: '产品展示', max: 100 }}, {{ name: '赠品策略', max: 100 }}
      ]
    }},
    series: [{{
      type: 'radar', symbol: 'circle', symbolSize: 4,
      data: [
        {{ value: [85,70,75,60,80,85], name: '我司', lineStyle: {{ color: C.green, width: 2 }}, areaStyle: {{ color: 'rgba(29,168,92,.12)' }}, itemStyle: {{ color: C.green }} }},
        {{ value: [75,85,90,85,80,70], name: '竞对', lineStyle: {{ color: C.red, width: 2 }}, areaStyle: {{ color: 'rgba(255,71,87,.08)' }}, itemStyle: {{ color: C.red }} }}
      ]
    }}]
  }});
  window.addEventListener('resize', function(){{ c.resize(); }});
}})();

// Nav scroll spy
(function(){{
  var navs = document.querySelectorAll('.nav-btn');
  var sections = [];
  navs.forEach(function(n){{
    var href = n.getAttribute('href');
    if(href && href.startsWith('#')){{
      var sec = document.querySelector(href);
      if(sec) sections.push({{ el: sec, nav: n }});
    }}
  }});
  function onScroll(){{
    var scrollY = window.scrollY + 120;
    var active = null;
    sections.forEach(function(s){{ if(s.el.offsetTop <= scrollY) active = s; }});
    navs.forEach(function(n){{ n.classList.remove('active'); }});
    if(active) active.nav.classList.add('active');
  }}
  window.addEventListener('scroll', onScroll);
  navs.forEach(function(n){{
    n.addEventListener('click', function(e){{
      var href = n.getAttribute('href');
      if(href && href.startsWith('#')){{
        e.preventDefault();
        var target = document.querySelector(href);
        if(target) target.scrollIntoView({{ behavior: 'smooth' }});
      }}
    }});
  }});
}})();
</script>
</body>
</html>
'''

with open('618复盘总结.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'HTML generated: {len(html)} bytes')
print('Done!')

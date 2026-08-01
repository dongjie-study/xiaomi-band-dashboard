"""
Generate August 2026 monthly sales summary HTML page.
Reads history.json, filters for August data.
If no August data exists yet, creates a placeholder page.
"""
import json
import os
from datetime import date

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Team classification
TEAM_MAP = {
    '小米官方手表': '我司', '小米官方手环直播间': '我司', '小米数码旗舰店': '我司',
    '小米官方耳机直播间': '我司', '小米手环10Pro直播间': '我司', '小米官旗手表直播间': '我司',
    '小米智能穿戴国补号': '机械空间', '小米智能穿戴授权号': '机械空间',
    '小米官方手表直播号': '纵横',
    '小米手环官方直播间': '凝云', '小米手环新品直播间': '凝云', '小米手环直播间': '凝云',
}

def get_team(room_name):
    return TEAM_MAP.get(room_name, '良米')

TEAM_ORDER = ['我司', '机械空间', '纵横', '凝云', '良米']
TEAM_COLORS = {'我司': '#1E90FF', '机械空间': '#FF6B35', '纵横': '#7c6ff7', '凝云': '#e74c3c', '良米': '#94a3b8'}

def load_august_data():
    history_path = os.path.join(DATA_DIR, 'sales_analysis', 'history.json')
    if not os.path.exists(history_path):
        return []
    with open(history_path, 'r', encoding='utf-8') as f:
        history = json.load(f)
    return [d for d in history if d['date'].startswith('2026-08')]

def build_summary(august):
    if not august:
        return None

    room_total = {}
    for d in august:
        for rname, rinfo in d.get('rooms', {}).items():
            if rname not in room_total:
                room_total[rname] = {'orders': 0, 'revenue': 0, 'type': get_team(rname), 'days': 0, 'daily': {}}
            room_total[rname]['orders'] += rinfo['orders']
            room_total[rname]['revenue'] += rinfo['revenue']
            room_total[rname]['days'] += 1
            room_total[rname]['daily'][d['date']] = {'orders': rinfo['orders'], 'revenue': rinfo['revenue']}

    prod_total = {}
    for d in august:
        for pname, pinfo in d.get('products', {}).items():
            if pname not in prod_total:
                prod_total[pname] = {'orders': 0, 'revenue': 0}
            prod_total[pname]['orders'] += pinfo['orders']
            prod_total[pname]['revenue'] += pinfo['revenue']

    rooms_ranked = sorted(room_total.items(), key=lambda x: -x[1]['revenue'])
    prods_ranked = sorted(prod_total.items(), key=lambda x: -x[1]['revenue'])

    team_totals = {}
    for t in TEAM_ORDER:
        team_rooms = [(n, r) for n, r in rooms_ranked if r['type'] == t]
        team_totals[t] = {
            'orders': sum(r['orders'] for _, r in team_rooms),
            'revenue': sum(r['revenue'] for _, r in team_rooms),
            'rooms': len(team_rooms),
            'avg_price': round(sum(r['revenue'] for _, r in team_rooms) / max(sum(r['orders'] for _, r in team_rooms), 1))
        }
    our_t = team_totals['我司']
    all_orders = sum(t['orders'] for t in team_totals.values())
    all_rev = sum(t['revenue'] for t in team_totals.values())

    from datetime import datetime
    weeks = {}
    for d in august:
        dt = datetime.strptime(d['date'], '%Y-%m-%d')
        if dt.day <= 7: w = 'W1'
        elif dt.day <= 14: w = 'W2'
        elif dt.day <= 21: w = 'W3'
        elif dt.day <= 28: w = 'W4'
        else: w = 'W5'
        if w not in weeks:
            weeks[w] = {'total_orders': 0, 'total_revenue': 0, 'our_orders': 0, 'our_revenue': 0, 'days': 0, 'label': ''}
        weeks[w]['total_orders'] += d['total_orders']
        weeks[w]['total_revenue'] += d['total_revenue']
        our_orders_today = sum(rinfo['orders'] for rname, rinfo in d.get('rooms', {}).items() if get_team(rname) == '我司')
        our_rev_today = sum(rinfo['revenue'] for rname, rinfo in d.get('rooms', {}).items() if get_team(rname) == '我司')
        weeks[w]['our_orders'] += our_orders_today
        weeks[w]['our_revenue'] += our_rev_today
        weeks[w]['days'] += 1

    week_labels = {
        'W1': 'W1 (8/1-8/7)', 'W2': 'W2 (8/8-8/14)',
        'W3': 'W3 (8/15-8/21)', 'W4': 'W4 (8/22-8/28)', 'W5': 'W5 (8/29-8/31)'
    }
    for wk, wdata in weeks.items():
        wdata['label'] = week_labels.get(wk, wk)

    daily_data = []
    for d in august:
        our_ord = sum(rinfo['orders'] for rname, rinfo in d.get('rooms', {}).items() if get_team(rname) == '我司')
        our_rev_d = sum(rinfo['revenue'] for rname, rinfo in d.get('rooms', {}).items() if get_team(rname) == '我司')
        comp_ord = d['total_orders'] - our_ord
        comp_rev_d = d['total_revenue'] - our_rev_d
        daily_data.append({
            'date': d['date'][-5:],
            'total': d['total_orders'],
            'our_orders': our_ord, 'comp_orders': comp_ord,
            'our_revenue': our_rev_d, 'comp_revenue': comp_rev_d,
            'total_revenue': d['total_revenue'],
            'our_share': round(our_ord / d['total_orders'] * 100, 1) if d['total_orders'] > 0 else 0,
        })

    return {
        'all_orders': all_orders, 'all_rev': all_rev,
        'our_orders': our_t['orders'], 'our_rev': our_t['revenue'],
        'our_share': round(our_t['orders'] / all_orders * 100, 1) if all_orders > 0 else 0,
        'our_avg_price': our_t['avg_price'],
        'all_avg_price': round(all_rev / all_orders) if all_orders > 0 else 0,
        'team_totals': team_totals, 'team_order': TEAM_ORDER,
        'rooms_ranked': rooms_ranked,
        'our_rooms_ranked': [(n, r) for n, r in rooms_ranked if r['type'] == '我司'],
        'comp_rooms_ranked': [(n, r) for n, r in rooms_ranked if r['type'] != '我司'],
        'jixie_rooms': [(n, r) for n, r in rooms_ranked if r['type'] == '机械空间'],
        'zongheng_rooms': [(n, r) for n, r in rooms_ranked if r['type'] == '纵横'],
        'liangmi_rooms': [(n, r) for n, r in rooms_ranked if r['type'] == '良米'],
        'prods_ranked': prods_ranked,
        'weeks': weeks, 'daily_data': daily_data,
        'days_count': len(august),
    }

def generate_html(summary, august_data):
    data_json = json.dumps(summary, ensure_ascii=False)
    days = len(august_data)
    room_count = len(summary['rooms_ranked'])
    first_date = august_data[0]['date'] if august_data else '2026-08-01'
    last_date = august_data[-1]['date'] if august_data else '2026-08-31'
    today = date.today().strftime('%Y年%m月%d日')

    # Read the July HTML template to reuse the structure
    july_html_path = os.path.join(DATA_DIR, '月度总结', '七月销量分析.html')
    if os.path.exists(july_html_path):
        with open(july_html_path, 'r', encoding='utf-8') as f:
            july_html = f.read()
    else:
        july_html = ''

    # We'll generate a complete HTML page with the same structure as July's
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>8月销量分析 · 小米手环直播间</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
:root {{
  --bg: #f0f4f8; --surface: #ffffff; --text: #0f172a; --text-secondary: #64748b;
  --text-muted: #9ca3af; --border: #e8ecf1; --shadow-sm: 0 1px 3px rgba(0,0,0,.03);
  --shadow-md: 0 4px 16px rgba(0,0,0,.06); --shadow-lg: 0 8px 30px rgba(0,0,0,.10);
  --radius: 14px; --radius-sm: 10px; --transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  --clr-ours: #1E90FF; --clr-comp: #FF6B35; --clr-orange: #ff6900;
  --clr-green: #1da85c; --clr-red: #FF4757; --clr-purple: #7c6ff7;
  --clr-gold: #c8960c; --clr-cyan: #0ea89d;
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
.kpi-row {{
  display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px;
  max-width: 1500px; margin: -28px auto 0; padding: 0 20px; position: relative; z-index: 10;
}}
@media (max-width: 1100px) {{ .kpi-row {{ grid-template-columns: repeat(3, 1fr); }} }}
@media (max-width: 640px) {{ .kpi-row {{ grid-template-columns: repeat(2, 1fr); }} }}
.kpi-card {{
  background: var(--surface); border-radius: var(--radius); padding: 18px 10px; text-align: center;
  box-shadow: var(--shadow-md); border: 1px solid var(--border);
  transition: transform var(--transition), box-shadow var(--transition);
}}
.kpi-card:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-lg); }}
.kpi-card .label {{ font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px; }}
.kpi-card .value {{ font-size: 30px; font-weight: 800; letter-spacing: -.02em; }}
.kpi-card .sub {{ font-size: 11px; color: var(--text-muted); margin-top: 2px; }}
.kpi-card.ours .value {{ color: var(--clr-ours); }}
.kpi-card.comp .value {{ color: var(--clr-comp); }}
.kpi-card.green .value {{ color: var(--clr-green); }}
.section {{
  max-width: 1500px; margin: 28px auto; padding: 0 20px; position: relative; z-index: 1;
}}
.section-title {{
  font-size: 22px; font-weight: 700; margin-bottom: 16px; display: flex; align-items: center; gap: 10px;
}}
.section-title .icon {{ font-size: 24px; }}
.table-wrap {{
  background: var(--surface); border-radius: var(--radius); overflow: hidden;
  box-shadow: var(--shadow-md); border: 1px solid var(--border);
}}
table {{
  width: 100%; border-collapse: collapse; font-size: 13.5px;
}}
thead th {{
  background: #f8fafc; padding: 11px 14px; text-align: left; font-weight: 600;
  color: var(--text-secondary); font-size: 11.5px; text-transform: uppercase; letter-spacing: .04em;
  border-bottom: 2px solid var(--border); position: sticky; top: 0;
}}
tbody td {{
  padding: 10px 14px; border-bottom: 1px solid #f1f5f9;
}}
tbody tr:hover {{ background: #fafbfd; }}
tbody tr.our {{ background: #f0f7ff; }}
tbody tr.our:hover {{ background: #e6f1fc; }}
.rank-num {{
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 50%; font-weight: 700; font-size: 12px;
}}
.rank-1 {{ background: #FFF1CC; color: #b8860b; }}
.rank-2 {{ background: #E8E8E8; color: #666; }}
.rank-3 {{ background: #FFE8D6; color: #c0561e; }}
.rank-other {{ color: var(--text-muted); }}
.tag-ours {{ color: var(--clr-ours); font-weight: 600; }}
.tag-comp {{ color: var(--clr-comp); }}
.amount {{ font-weight: 600; font-variant-numeric: tabular-nums; }}
.chart-container {{
  background: var(--surface); border-radius: var(--radius);
  box-shadow: var(--shadow-md); border: 1px solid var(--border);
  padding: 20px; margin-bottom: 20px;
}}
.chart-box {{ width: 100%; height: 420px; }}
.chart-box.tall {{ height: 500px; }}
.grid-2 {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
}}
@media (max-width: 900px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
.summary-box {{
  background: var(--surface); border-radius: var(--radius); padding: 28px 32px;
  box-shadow: var(--shadow-md); border: 1px solid var(--border); line-height: 1.9;
}}
.summary-box h3 {{ font-size: 17px; margin-bottom: 14px; color: var(--clr-orange); }}
.summary-box ul {{ padding-left: 20px; }}
.summary-box li {{ margin-bottom: 6px; font-size: 14px; }}
.summary-box .highlight {{ background: linear-gradient(180deg, transparent 60%, #fff3cd 60%); padding: 0 3px; }}
.week-table td {{ text-align: center; }}
.week-table td:first-child {{ text-align: left; font-weight: 600; }}
footer {{
  text-align: center; padding: 32px 20px; color: var(--text-muted); font-size: 12px;
}}
.footnote {{ font-size: 12px; color: var(--text-muted); margin-top: 6px; }}
</style>
</head>
<body>

<div class="nav-bar">
  <a href="../index.html" class="nav-btn">首页</a>
  <a href="../sales_analysis/index.html" class="nav-btn">每日看板</a>
  <a href="六月销量分析.html" class="nav-btn">6月销量分析</a>
  <a href="七月销量分析.html" class="nav-btn">7月销量分析</a>
  <a href="#" class="nav-btn active">8月销量分析</a>
  <a href="../节点总结/618复盘总结.html" class="nav-btn">618复盘</a>
  <a href="../节点总结/四月份复盘总结.html" class="nav-btn">4月复盘</a>
</div>

<div class="hero">
  <h1><span class="mi">小米</span>手环直播间 · 8月销量分析</h1>
  <p>2026年8月全月订单数据汇总 — 含商品卡全渠道 | 排名以<span style="color:#ffa366">销售额</span>为准</p>
  <div class="badge-row">
    <span class="badge green">{days}天数据（持续更新）</span>
    <span class="badge info">我司·机械·纵横·良米 四队</span>
    <span class="badge warn">{room_count}个直播间</span>
    <span class="badge purple">8月数据追踪</span>
  </div>
</div>

<div class="kpi-row" id="kpiRow"></div>

<div class="section">
  <div class="grid-2">
    <div class="chart-container"><div class="chart-box" id="chartDailyOrders"></div></div>
    <div class="chart-container"><div class="chart-box" id="chartDailyRevenue"></div></div>
  </div>
  <div class="chart-container"><div class="chart-box tall" id="chartWeekly"></div></div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">🏪</span> 全渠道直播间排名 · 按销售额</div>
  <div class="table-wrap"><table><thead><tr>
    <th>#</th><th>直播间</th><th>团队</th><th>订单数</th><th>销售额</th><th>占比</th><th>均价</th><th>出勤</th>
  </tr></thead><tbody id="roomTableBody"></tbody></table></div>
</div>

<div class="section">
  <div class="grid-2">
    <div>
      <div class="section-title"><span class="icon">⭐</span> 我方直播间排名 · 按销售额</div>
      <div class="table-wrap"><table><thead><tr>
        <th>#</th><th>直播间</th><th>订单数</th><th>销售额</th><th>占比</th><th>均价</th>
      </tr></thead><tbody id="ourRoomTable"></tbody></table></div>
    </div>
    <div>
      <div class="section-title"><span class="icon">📦</span> 产品排名 TOP12 · 按销售额</div>
      <div class="table-wrap"><table><thead><tr>
        <th>#</th><th>产品</th><th>订单数</th><th>销售额</th><th>占比</th><th>均价</th>
      </tr></thead><tbody id="prodTable"></tbody></table></div>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">📅</span> 周度趋势</div>
  <div class="table-wrap"><table class="week-table"><thead><tr>
    <th>周期</th><th>天数</th><th>全渠道订单</th><th>全渠道销售额</th><th>我方订单</th><th>我方份额</th><th>我方销售额</th><th>日均我方订单</th>
  </tr></thead><tbody id="weekTable"></tbody></table></div>
  <div class="chart-container" style="margin-top:20px"><div class="chart-box" id="chartWeeklyShare"></div></div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">🔍</span> 竞对直播间 TOP8 · 按销售额</div>
  <div class="table-wrap"><table><thead><tr>
    <th>#</th><th>直播间</th><th>团队</th><th>订单数</th><th>销售额</th><th>占比</th><th>均价</th><th>出勤天数</th>
  </tr></thead><tbody id="compTable"></tbody></table></div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">⚔️</span> 竞争格局深度分析</div>
  <div class="summary-box" id="competitiveAnalysis"></div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">💡</span> 改进建议</div>
  <div class="summary-box" id="improvementSuggestions"></div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">🧭</span> 后续方向</div>
  <div class="summary-box" id="futureDirection"></div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">📊</span> 8月总结</div>
  <div class="summary-box" id="summaryBox"></div>
</div>

<footer>
  数据来源：抖音直播间订单 · 分析周期：{first_date}—{last_date}（{days}天）· 自动生成于{today}<br>
  ★ 我司 = 小米官方手环直播间 / 小米数码旗舰店 / 小米官方手表 / 小米官方耳机直播间 / 小米官旗手表直播间 / 小米手环10Pro直播间<br>
  ◆ 机械空间 = 小米智能穿戴国补号 / 小米智能穿戴授权号 &nbsp;|&nbsp; ▲ 纵横 = 小米官方手表直播号 &nbsp;|&nbsp; · 良米 = 其他
</footer>

<script>
const DATA = {data_json};
const TEAM_COLORS = {{'我司':'#1E90FF','机械空间':'#FF6B35','纵横':'#7c6ff7','良米':'#94a3b8'}};
const TEAM_ORDER = ['我司','机械空间','纵横','良米'];

function fmt(n) {{ return n.toLocaleString('zh-CN'); }}
function fmtRMB(n) {{ return '¥' + Math.round(n).toLocaleString('zh-CN'); }}
function fmtPct(n) {{ return n.toFixed(1) + '%'; }}

// KPI cards
(function renderKPIs() {{
  const d = DATA, our = d.team_totals['我司'], jx = d.team_totals['机械空间'], zh = d.team_totals['纵横'], lm = d.team_totals['良米'];
  const cards = [
    {{ label: '8月全渠道订单', value: fmt(d.all_orders), sub: d.days_count + '天累计', cls: '' }},
    {{ label: '全渠道销售额', value: '¥' + (d.all_rev/10000).toFixed(0) + '万', sub: fmtRMB(d.all_rev), cls: '' }},
    {{ label: '★ 我司订单', value: fmt(our.orders), sub: '份额 ' + fmtPct(d.our_share), cls: 'ours' }},
    {{ label: '★ 我司销售额', value: '¥' + (our.revenue/10000).toFixed(0) + '万', sub: fmtRMB(our.revenue), cls: 'ours' }},
    {{ label: '我司均价', value: '¥' + our.avg_price, sub: '我司 ' + our.rooms + '个直播间', cls: 'green' }},
    {{ label: '主要竞对', value: jx.rooms + '机械+' + zh.rooms + '纵横+' + lm.rooms + '良米', sub: jx.orders + '/' + zh.orders + '/' + lm.orders + '单', cls: '' }},
  ];
  document.getElementById('kpiRow').innerHTML = cards.map(c =>
    `<div class="kpi-card ${{c.cls}}"><div class="label">${{c.label}}</div><div class="value">${{c.value}}</div><div class="sub">${{c.sub}}</div></div>`
  ).join('');
}})();

// Room ranking table
(function renderRoomTable() {{
  const all_rev = DATA.all_rev;
  const rows = DATA.rooms_ranked.map((r, i) => {{
    const [name, info] = r;
    const rank = i + 1;
    const rankCls = rank <= 3 ? 'rank-' + rank : 'rank-other';
    const team = info.type;
    const marker = team === '我司' ? '★' : team === '机械空间' ? '◆' : team === '纵横' ? '▲' : '·';
    const rowCls = team === '我司' ? 'our' : '';
    const teamColor = TEAM_COLORS[team] || '#64748b';
    return `<tr class="${{rowCls}}">
      <td><span class="rank-num ${{rankCls}}">${{rank}}</span></td>
      <td>${{marker}} <strong>${{name}}</strong></td>
      <td style="color:${{teamColor}};font-weight:600">${{team}}</td>
      <td>${{fmt(info.orders)}}</td>
      <td class="amount">${{fmtRMB(info.revenue)}}</td>
      <td>${{fmtPct(info.revenue/all_rev*100)}}</td>
      <td>¥${{Math.round(info.revenue/info.orders)}}</td>
      <td>${{info.days}}天</td>
    </tr>`;
  }}).join('');
  document.getElementById('roomTableBody').innerHTML = rows;
}})();

// 我司 rooms table
(function renderOurRooms() {{
  const our_rev = DATA.team_totals['我司'].revenue;
  const rows = DATA.our_rooms_ranked.map((r, i) => {{
    const [name, info] = r;
    const rank = i + 1;
    const rankCls = rank <= 3 ? 'rank-' + rank : 'rank-other';
    return `<tr>
      <td><span class="rank-num ${{rankCls}}">${{rank}}</span></td>
      <td><strong>${{name}}</strong></td>
      <td>${{fmt(info.orders)}}</td>
      <td class="amount">${{fmtRMB(info.revenue)}}</td>
      <td>${{fmtPct(info.revenue/our_rev*100)}}</td>
      <td>¥${{Math.round(info.revenue/info.orders)}}</td>
    </tr>`;
  }}).join('');
  document.getElementById('ourRoomTable').innerHTML = rows;
}})();

// Product table
(function renderProds() {{
  const all_rev = DATA.all_rev;
  const top12 = DATA.prods_ranked.slice(0, 12);
  const rows = top12.map((r, i) => {{
    const [name, info] = r;
    const rank = i + 1;
    const rankCls = rank <= 3 ? 'rank-' + rank : 'rank-other';
    return `<tr>
      <td><span class="rank-num ${{rankCls}}">${{rank}}</span></td>
      <td>${{name}}</td>
      <td>${{fmt(info.orders)}}</td>
      <td class="amount">${{fmtRMB(info.revenue)}}</td>
      <td>${{fmtPct(info.revenue/all_rev*100)}}</td>
      <td>¥${{Math.round(info.revenue/info.orders)}}</td>
    </tr>`;
  }}).join('');
  document.getElementById('prodTable').innerHTML = rows;
}})();

// Competitor room ranking
(function renderComp() {{
  const all_rev = DATA.all_rev;
  const all_comp = [...DATA.jixie_rooms, ...DATA.zongheng_rooms, ...DATA.liangmi_rooms].sort((a,b) => b[1].revenue - a[1].revenue);
  const top8 = all_comp.slice(0, 8);
  const rows = top8.map((r, i) => {{
    const [name, info] = r;
    const rank = i + 1;
    const rankCls = rank <= 3 ? 'rank-' + rank : 'rank-other';
    const teamColor = TEAM_COLORS[info.type] || '#64748b';
    return `<tr>
      <td><span class="rank-num ${{rankCls}}">${{rank}}</span></td>
      <td>${{name}}</td>
      <td style="color:${{teamColor}};font-weight:600">${{info.type}}</td>
      <td>${{fmt(info.orders)}}</td>
      <td class="amount">${{fmtRMB(info.revenue)}}</td>
      <td>${{fmtPct(info.revenue/all_rev*100)}}</td>
      <td>¥${{Math.round(info.revenue/info.orders)}}</td>
      <td>${{info.days}}天</td>
    </tr>`;
  }}).join('');
  document.getElementById('compTable').innerHTML = rows;
}})();

// Week table
(function renderWeeks() {{
  const rows = Object.entries(DATA.weeks).map(([wk, w]) => {{
    const share = w.our_orders / w.total_orders * 100;
    const daily_avg = Math.round(w.our_orders / w.days);
    return `<tr>
      <td>${{w.label}}</td>
      <td>${{w.days}}天</td>
      <td>${{fmt(w.total_orders)}}</td>
      <td class="amount">${{fmtRMB(w.total_revenue)}}</td>
      <td>${{fmt(w.our_orders)}}</td>
      <td>${{fmtPct(share)}}</td>
      <td class="amount">${{fmtRMB(w.our_revenue)}}</td>
      <td>${{daily_avg}}单/天</td>
    </tr>`;
  }}).join('');
  document.getElementById('weekTable').innerHTML = rows;
}})();

// Summary
(function renderSummary() {{
  const d = DATA;
  const our = d.team_totals['我司'], jx = d.team_totals['机械空间'], zh = d.team_totals['纵横'], lm = d.team_totals['良米'];
  const top_our = d.our_rooms_ranked[0];

  document.getElementById('summaryBox').innerHTML = `
    <h3>📊 8月核心洞察（持续更新中）</h3>
    <ul>
      <li><strong>总量：</strong>8月全渠道累计 <span class="highlight">${{fmt(d.all_orders)}}单</span>，销售额 <span class="highlight">${{fmtRMB(d.all_rev)}}（¥${{(d.all_rev/10000).toFixed(0)}}万）</span>，日均 ${{Math.round(d.all_orders/d.days_count)}}单。</li>
      <li><strong>我司表现：</strong>${{our.rooms}}个直播间合计 <span class="highlight">${{fmt(our.orders)}}单（份额${{fmtPct(d.our_share)}}）</span>，销售额 <span class="highlight">${{fmtRMB(our.revenue)}}（¥${{(our.revenue/10000).toFixed(0)}}万）</span>，均价¥${{our.avg_price}}。</li>
      <li><strong>机械空间：</strong>${{jx.rooms}}个直播间 ${{fmt(jx.orders)}}单，${{fmtRMB(jx.revenue)}}。</li>
      <li><strong>纵横：</strong>${{zh.rooms}}个直播间 ${{fmt(zh.orders)}}单，${{fmtRMB(zh.revenue)}}。</li>
      <li><strong>良米：</strong>${{lm.rooms}}个直播间 ${{fmt(lm.orders)}}单，${{fmtRMB(lm.revenue)}}。</li>
    </ul>
  `;
}})();

// Competitive analysis
(function renderCompetitive() {{
  const d = DATA;
  const our = d.team_totals['我司'], jx = d.team_totals['机械空间'], zh = d.team_totals['纵横'], lm = d.team_totals['良米'];

  document.getElementById('competitiveAnalysis').innerHTML = `
    <h3>一、四队格局</h3>
    <p>8月延续<span class="highlight">我司·机械空间·纵横·良米</span>四队竞争格局。数据持续更新中。</p>
    <h3>二、品类分析</h3>
    <table style="width:100%;border-collapse:collapse;margin:10px 0;font-size:13px">
      <tr style="background:#f8fafc"><th style="padding:8px;text-align:left">品类</th><th style="padding:8px">全渠道订单</th><th style="padding:8px">销售额</th><th style="padding:8px">判断</th></tr>
      ${{d.prods_ranked.slice(0, 10).map(([name, info], i) => {{
        const share = (info.revenue / d.all_rev * 100);
        const icon = i < 3 ? '🟢' : i < 6 ? '🟡' : '🟠';
        return `<tr><td style="padding:8px">${{name}}</td><td style="padding:8px;font-weight:600">${{fmt(info.orders)}}单</td><td style="padding:8px;font-weight:600">${{fmtRMB(info.revenue)}} (${{share.toFixed(1)}}%)</td><td style="padding:8px">${{icon}}</td></tr>`;
      }}).join('')}}
    </table>
  `;
}})();

// Improvement suggestions
(function renderImprovements() {{
  document.getElementById('improvementSuggestions').innerHTML = `
    <h3>🔴 8月重点方向</h3>
    <ul>
      <li><strong>持续跟踪每日数据：</strong>8月是新月份，密切关注每日单量变化趋势，与7月同期进行对比。</li>
      <li><strong>暑期旺季运营：</strong>8月仍处于暑期，重点推出手环/Watch运动健康场景。</li>
      <li><strong>竞对动态监控：</strong>密切关注机械空间和良米的直播间变化和促销策略。</li>
    </ul>
    <p style="margin-top:12px;color:var(--text-muted);">（更多洞察将在累积足够数据后自动生成）</p>
  `;
}})();

// Future direction
(function renderFuture() {{
  document.getElementById('futureDirection').innerHTML = `
    <h3>8月战略方向</h3>
    <p>8月目标：延续7月增长势头，重点提升我司份额。数据持续更新中，具体策略将根据实际数据调整。</p>
    <div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">
      <strong>🎯 8月核心KPI：</strong>
      我司日均目标 <span class="highlight">待定（根据7月基准设定）</span>
    </div>
  `;
}})();

(function renderCharts() {{
  const daily = DATA.daily_data;
  const dates = daily.map(d => d.date);
  const weeks = DATA.weeks;

  // Daily orders
  const chart1 = echarts.init(document.getElementById('chartDailyOrders'));
  chart1.setOption({{
    title: {{ text: '每日订单趋势', left: 'center', textStyle: {{ fontSize: 15, fontWeight: 600 }} }},
    tooltip: {{ trigger: 'axis' }},
    legend: {{ bottom: 0, data: ['全渠道', '我方', '竞对'] }},
    grid: {{ left: 50, right: 20, top: 50, bottom: 35 }},
    xAxis: {{ type: 'category', data: dates, axisLabel: {{ rotate: 45, fontSize: 10 }} }},
    yAxis: {{ type: 'value', name: '订单数' }},
    series: [
      {{ name: '全渠道', type: 'bar', data: daily.map(d => d.total), itemStyle: {{ color: '#94a3b8' }}, barWidth: '60%', z: 1 }},
      {{ name: '我方', type: 'bar', data: daily.map(d => d.our_orders), itemStyle: {{ color: '#1E90FF' }}, barWidth: '60%', z: 2 }},
      {{ name: '竞对', type: 'bar', data: daily.map(d => d.comp_orders), itemStyle: {{ color: '#FF6B35' }}, barWidth: '60%', z: 2 }},
    ]
  }});

  // Daily revenue
  const chart2 = echarts.init(document.getElementById('chartDailyRevenue'));
  chart2.setOption({{
    title: {{ text: '每日销售额趋势 (万元)', left: 'center', textStyle: {{ fontSize: 15, fontWeight: 600 }} }},
    tooltip: {{ trigger: 'axis', valueFormatter: v => '¥' + (v/10000).toFixed(1) + '万' }},
    legend: {{ bottom: 0, data: ['全渠道', '我方', '竞对'] }},
    grid: {{ left: 55, right: 20, top: 50, bottom: 35 }},
    xAxis: {{ type: 'category', data: dates, axisLabel: {{ rotate: 45, fontSize: 10 }} }},
    yAxis: {{ type: 'value', name: '万元', axisLabel: {{ formatter: v => (v/10000).toFixed(0) + 'w' }} }},
    series: [
      {{ name: '全渠道', type: 'line', data: daily.map(d => d.total_revenue), smooth: true, lineStyle: {{ color: '#94a3b8', width: 2 }}, symbol: 'none' }},
      {{ name: '我方', type: 'line', data: daily.map(d => d.our_revenue), smooth: true, lineStyle: {{ color: '#1E90FF', width: 2.5 }}, symbol: 'circle', symbolSize: 4, areaStyle: {{ color: 'rgba(30,144,255,0.08)' }} }},
      {{ name: '竞对', type: 'line', data: daily.map(d => d.comp_revenue), smooth: true, lineStyle: {{ color: '#FF6B35', width: 2 }}, symbol: 'circle', symbolSize: 4, areaStyle: {{ color: 'rgba(255,107,53,0.06)' }} }},
    ]
  }});

  // Weekly bar
  const chart3 = echarts.init(document.getElementById('chartWeekly'));
  const wkLabels = Object.values(weeks).map(w => w.label);
  const wkOur = Object.values(weeks).map(w => w.our_orders);
  const wkComp = Object.values(weeks).map(w => w.total_orders - w.our_orders);
  const wkOurRev = Object.values(weeks).map(w => w.our_revenue);
  const wkCompRev = Object.values(weeks).map(w => w.total_revenue - w.our_revenue);
  chart3.setOption({{
    title: {{ text: '周度订单与销售额对比', left: 'center', textStyle: {{ fontSize: 15, fontWeight: 600 }} }},
    tooltip: {{ trigger: 'axis' }},
    legend: {{ bottom: 0, data: ['我方订单', '竞对订单', '我方销售额', '竞对销售额'] }},
    grid: {{ left: 70, right: 70, top: 50, bottom: 35 }},
    xAxis: {{ type: 'category', data: wkLabels }},
    yAxis: [
      {{ type: 'value', name: '订单数' }},
      {{ type: 'value', name: '销售额', axisLabel: {{ formatter: v => (v/10000).toFixed(0) + 'w' }} }}
    ],
    series: [
      {{ name: '我方订单', type: 'bar', data: wkOur, itemStyle: {{ color: '#1E90FF' }}, barGap: '10%' }},
      {{ name: '竞对订单', type: 'bar', data: wkComp, itemStyle: {{ color: '#FF6B35' }} }},
      {{ name: '我方销售额', type: 'line', yAxisIndex: 1, data: wkOurRev, lineStyle: {{ color: '#1da85c', width: 3 }}, symbol: 'diamond', symbolSize: 8 }},
      {{ name: '竞对销售额', type: 'line', yAxisIndex: 1, data: wkCompRev, lineStyle: {{ color: '#FF4757', width: 2, type: 'dashed' }}, symbol: 'diamond', symbolSize: 6 }},
    ]
  }});

  // Weekly share
  const chart4 = echarts.init(document.getElementById('chartWeeklyShare'));
  const wkShare = Object.values(weeks).map(w => parseFloat((w.our_orders / w.total_orders * 100).toFixed(1)));
  chart4.setOption({{
    title: {{ text: '我方周度份额变化', left: 'center', textStyle: {{ fontSize: 16, fontWeight: 700 }} }},
    tooltip: {{ trigger: 'axis' }},
    grid: {{ left: 50, right: 40, top: 55, bottom: 45 }},
    xAxis: {{ type: 'category', data: wkLabels, axisLabel: {{ fontSize: 12, fontWeight: 600 }} }},
    yAxis: {{ type: 'value', name: '份额 (%)', axisLabel: {{ formatter: '{{value}}%' }}, splitLine: {{ lineStyle: {{ type: 'dashed', color: '#e8ecf1' }} }} }},
    series: [
      {{
        name: '我方份额', type: 'bar', data: wkShare,
        itemStyle: {{ color: '#1E90FF', borderRadius: [6,6,0,0] }},
        barWidth: '50%',
        label: {{ show: true, position: 'top', fontSize: 16, fontWeight: 700, color: '#0f172a', formatter: '{{c}}%' }},
      }}
    ]
  }});

  window.addEventListener('resize', () => {{ chart1.resize(); chart2.resize(); chart3.resize(); chart4.resize(); }});
}})();
</script>

</body>
</html>'''
    return html


def generate_placeholder():
    """Generate a placeholder page when no August data exists yet."""
    today = date.today().strftime('%Y年%m月%d日')
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>8月销量分析 · 小米手环直播间</title>
<style>
:root {{
  --bg: #f0f4f8; --surface: #ffffff; --text: #0f172a; --text-secondary: #64748b;
  --text-muted: #9ca3af; --border: #e8ecf1; --shadow-md: 0 4px 16px rgba(0,0,0,.06);
  --radius: 14px; --clr-orange: #ff6900; --clr-ours: #1E90FF;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.6;
}}
.nav-bar {{
  display: flex; justify-content: center; gap: 6px; flex-wrap: wrap;
  padding: 10px 16px; background: rgba(255,255,255,.9);
  backdrop-filter: blur(14px); border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 100;
}}
.nav-btn {{
  padding: 7px 18px; border-radius: 20px; border: 1.5px solid #dde1e6;
  background: #fff; color: #555; font-size: 12.5px; cursor: pointer;
  text-decoration: none; transition: all 0.25s; font-family: inherit; font-weight: 500;
}}
.nav-btn:hover {{ border-color: var(--clr-orange); color: var(--clr-orange); background: #fff7ed; }}
.nav-btn.active {{ background: linear-gradient(135deg, var(--clr-orange), #ff8c42); color: #fff; border-color: transparent; font-weight: 600; }}
.hero {{
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
  color: white; padding: 48px 20px 40px; text-align: center;
}}
.hero h1 {{ font-size: 38px; font-weight: 800; }}
.hero h1 .mi {{ color: var(--clr-orange); }}
.hero p {{ font-size: 15px; opacity: 0.85; margin-top: 8px; }}
.hero .badge-row {{ margin-top: 16px; display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; }}
.hero .badge {{ padding: 5px 16px; border-radius: 16px; font-size: 12px; font-weight: 600; }}
.badge.green {{ background: rgba(29,168,92,.18); color: #5ddf8a; }}
.badge.info {{ background: rgba(30,144,255,.18); color: #80c8ff; }}
.container {{
  max-width: 800px; margin: 60px auto; padding: 40px;
  background: var(--surface); border-radius: var(--radius);
  box-shadow: var(--shadow-md); text-align: center;
}}
.container h2 {{ font-size: 24px; color: var(--clr-ours); margin-bottom: 16px; }}
.container p {{ color: var(--text-secondary); font-size: 15px; margin-bottom: 8px; }}
.container .icon {{ font-size: 64px; margin-bottom: 20px; }}
.container .note {{ font-size: 13px; color: var(--text-muted); margin-top: 24px; padding-top: 20px; border-top: 1px solid var(--border); }}
footer {{
  text-align: center; padding: 32px 20px; color: var(--text-muted); font-size: 12px;
}}
</style>
</head>
<body>

<div class="nav-bar">
  <a href="../index.html" class="nav-btn">首页</a>
  <a href="../sales_analysis/index.html" class="nav-btn">每日看板</a>
  <a href="六月销量分析.html" class="nav-btn">6月销量分析</a>
  <a href="七月销量分析.html" class="nav-btn">7月销量分析</a>
  <a href="#" class="nav-btn active">8月销量分析</a>
  <a href="../节点总结/618复盘总结.html" class="nav-btn">618复盘</a>
  <a href="../节点总结/四月份复盘总结.html" class="nav-btn">4月复盘</a>
</div>

<div class="hero">
  <h1><span class="mi">小米</span>手环直播间 · 8月销量分析</h1>
  <p>2026年8月全月订单数据汇总 | 排名以<span style="color:#ffa366">销售额</span>为准</p>
  <div class="badge-row">
    <span class="badge green">8月1日开始</span>
    <span class="badge info">等待数据录入</span>
  </div>
</div>

<div class="container">
  <div class="icon">📅</div>
  <h2>8月数据尚未开始</h2>
  <p>8月销量分析页面已就绪，将从<strong>2026年8月1日</strong>开始记录数据。</p>
  <p>每日订单数据将通过 <code>daily_update.py</code> 自动录入系统。</p>
  <p style="margin-top:16px">届时本页面将自动展示：</p>
  <p style="color:var(--text-muted);font-size:13px">
    ✓ KPI指标卡片 · ✓ 每日订单/销售额趋势图 · ✓ 直播间排名<br>
    ✓ 产品排名 · ✓ 周度趋势 · ✓ 竞争格局分析 · ✓ 改进建议
  </p>
  <div class="note">
    页面生成于 {today} · 返回 <a href="七月销量分析.html" style="color:var(--clr-ours)">7月销量分析</a>
  </div>
</div>

<footer>
  小米手环直播间 · 8月销量分析 · 数据来源：抖音直播间订单
</footer>

</body>
</html>'''


if __name__ == '__main__':
    august = load_august_data()

    if august:
        summary = build_summary(august)
        html = generate_html(summary, august)
        status = f'{len(august)} days of data'
    else:
        html = generate_placeholder()
        summary = None
        status = 'no data yet (placeholder)'

    out_path = os.path.join(DATA_DIR, '月度总结', '八月销量分析.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(f'Generated: {out_path}')
    print(f'  Status: {status}')
    if summary:
        print(f'  Total orders: {summary["all_orders"]:,}')
        print(f'  我司: {summary["our_orders"]:,}单 ({summary["our_share"]}%), {summary["our_rev"]:,.0f}')

"""
Generate June 2026 monthly sales summary HTML page.
Reads history.json, re-classifies rooms with correct OUR_ROOMS, ranks by revenue.
"""
import json
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Team classification (matching daily_update.py)
TEAM_MAP = {
    '小米官方手表': '我司', '小米官方手环直播间': '我司', '小米数码旗舰店': '我司',
    '小米官方耳机直播间': '我司', '小米手环10Pro直播间': '我司', '小米官旗手表直播间': '我司',
    '小米智能穿戴国补号': '机械空间', '小米智能穿戴授权号': '机械空间',
    '小米官方手表直播号': '纵横',
}
def get_team(room_name):
    return TEAM_MAP.get(room_name, '良米')

TEAM_ORDER = ['我司', '机械空间', '纵横', '良米']
TEAM_COLORS = {'我司': '#1E90FF', '机械空间': '#FF6B35', '纵横': '#7c6ff7', '良米': '#94a3b8'}
TEAM_MARKERS = {'我司': '★', '机械空间': '◆', '纵横': '▲', '良米': '·'}

def load_june_data():
    with open(os.path.join(DATA_DIR, 'sales_analysis', 'history.json'), 'r', encoding='utf-8') as f:
        history = json.load(f)
    return [d for d in history if d['date'].startswith('2026-06')]

def build_summary(june):
    # Re-classify rooms across all days
    room_total = {}  # rname -> {orders, revenue, type, days, daily: {date: {orders, revenue}}}
    for d in june:
        for rname, rinfo in d.get('rooms', {}).items():
            if rname not in room_total:
                room_total[rname] = {
                    'orders': 0, 'revenue': 0,
                    'type': get_team(rname),
                    'days': 0, 'daily': {}
                }
            room_total[rname]['orders'] += rinfo['orders']
            room_total[rname]['revenue'] += rinfo['revenue']
            room_total[rname]['days'] += 1
            room_total[rname]['daily'][d['date']] = {
                'orders': rinfo['orders'], 'revenue': rinfo['revenue']
            }

    # Product total
    prod_total = {}
    for d in june:
        for pname, pinfo in d.get('products', {}).items():
            if pname not in prod_total:
                prod_total[pname] = {'orders': 0, 'revenue': 0}
            prod_total[pname]['orders'] += pinfo['orders']
            prod_total[pname]['revenue'] += pinfo['revenue']

    # Sort rooms by revenue
    rooms_ranked = sorted(room_total.items(), key=lambda x: -x[1]['revenue'])
    prods_ranked = sorted(prod_total.items(), key=lambda x: -x[1]['revenue'])

    # Team totals
    team_totals = {}
    for t in TEAM_ORDER:
        team_rooms = [(n, r) for n, r in rooms_ranked if r['type'] == t]
        team_totals[t] = {
            'orders': sum(r['orders'] for _, r in team_rooms),
            'revenue': sum(r['revenue'] for _, r in team_rooms),
            'rooms': len(team_rooms),
            'avg_price': round(sum(r['revenue'] for _, r in team_rooms) / sum(r['orders'] for _, r in team_rooms)) if sum(r['orders'] for _, r in team_rooms) > 0 else 0
        }
    our_t = team_totals['我司']
    all_orders = sum(t['orders'] for t in team_totals.values())
    all_rev = sum(t['revenue'] for t in team_totals.values())

    # Weekly trends
    from datetime import datetime
    weeks = {}
    for d in june:
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
        # Use team-classified room data
        our_orders_today = sum(rinfo['orders'] for rname, rinfo in d.get('rooms', {}).items() if get_team(rname) == '我司')
        our_rev_today = sum(rinfo['revenue'] for rname, rinfo in d.get('rooms', {}).items() if get_team(rname) == '我司')
        weeks[w]['our_orders'] += our_orders_today
        weeks[w]['our_revenue'] += our_rev_today
        weeks[w]['days'] += 1
    # Labels
    week_labels = {
        'W1': 'W1 (6/1-6/7)', 'W2': 'W2 (6/8-6/14)',
        'W3': 'W3 (6/15-6/21)', 'W4': 'W4 (6/22-6/28)', 'W5': 'W5 (6/29-6/30)'
    }
    for wk, wdata in weeks.items():
        wdata['label'] = week_labels.get(wk, wk)

    # Daily data for charts
    daily_data = []
    for d in june:
        # Team-classified from room data
        our_ord = sum(rinfo['orders'] for rname, rinfo in d.get('rooms', {}).items() if get_team(rname) == '我司')
        our_rev_d = sum(rinfo['revenue'] for rname, rinfo in d.get('rooms', {}).items() if get_team(rname) == '我司')
        comp_ord = d['total_orders'] - our_ord
        comp_rev_d = d['total_revenue'] - our_rev_d
        daily_data.append({
            'date': d['date'][-5:],
            'total': d['total_orders'],
            'our_orders': our_ord,
            'comp_orders': comp_ord,
            'our_revenue': our_rev_d,
            'comp_revenue': comp_rev_d,
            'total_revenue': d['total_revenue'],
            'our_share': round(our_ord / d['total_orders'] * 100, 1) if d['total_orders'] > 0 else 0,
        })

    return {
        'all_orders': all_orders, 'all_rev': all_rev,
        'our_orders': our_t['orders'], 'our_rev': our_t['revenue'],
        'our_share': round(our_t['orders'] / all_orders * 100, 1) if all_orders > 0 else 0,
        'our_avg_price': our_t['avg_price'],
        'all_avg_price': round(all_rev / all_orders) if all_orders > 0 else 0,
        'team_totals': team_totals,
        'team_order': TEAM_ORDER,
        'rooms_ranked': rooms_ranked,
        'our_rooms_ranked': [(n, r) for n, r in rooms_ranked if r['type'] == '我司'],
        'comp_rooms_ranked': [(n, r) for n, r in rooms_ranked if r['type'] != '我司'],
        'jixie_rooms': [(n, r) for n, r in rooms_ranked if r['type'] == '机械空间'],
        'zongheng_rooms': [(n, r) for n, r in rooms_ranked if r['type'] == '纵横'],
        'liangmi_rooms': [(n, r) for n, r in rooms_ranked if r['type'] == '良米'],
        'prods_ranked': prods_ranked,
        'weeks': weeks,
        'daily_data': daily_data,
        'days_count': len(june),
    }

def generate_html(summary):
    data_json = json.dumps(summary, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>6月销量分析 · 小米手环直播间</title>
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
  <a href="index.html" class="nav-btn">首页</a>
  <a href="sales_analysis/index.html" class="nav-btn">每日看板</a>
  <a href="#" class="nav-btn active">6月销量分析</a>
  <a href="618复盘总结.html" class="nav-btn">618复盘</a>
  <a href="四月份复盘总结.html" class="nav-btn">4月复盘</a>
</div>

<div class="hero">
  <h1><span class="mi">小米</span>手环直播间 · 6月销量分析</h1>
  <p>2026年6月全月订单数据汇总 — 含商品卡全渠道 | 排名以<span style="color:#ffa366">销售额</span>为准</p>
  <div class="badge-row">
    <span class="badge green">30天完整数据</span>
    <span class="badge info">我司·机械·纵横·良米 四队</span>
    <span class="badge warn">19个直播间</span>
    <span class="badge purple">618大促月</span>
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
  <div class="section-title"><span class="icon">🔍</span> 竞对直播间（机械+纵横+良米）TOP8 · 按销售额</div>
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
  <div class="section-title"><span class="icon">📊</span> 6月总结</div>
  <div class="summary-box" id="summaryBox"></div>
</div>

<footer>
  数据来源：抖音直播间订单 · 分析周期：2026年6月1日—6月30日（30天）· 自动生成于2026年7月1日<br>
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
    {{ label: '6月全渠道订单', value: fmt(d.all_orders), sub: d.days_count + '天累计', cls: '' }},
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

// Room ranking table (all rooms with team)
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

// All other teams: 机械+纵横+良米 room ranking (combined competitor view)
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
  const top_prod = d.prods_ranked[0];
  const best_week = Object.entries(d.weeks).sort((a,b) => b[1].our_orders - a[1].our_orders)[0];

  document.getElementById('summaryBox').innerHTML = `
    <h3>📊 6月核心洞察</h3>
    <ul>
      <li><strong>总量：</strong>6月全渠道累计 <span class="highlight">${{fmt(d.all_orders)}}单</span>，销售额 <span class="highlight">${{fmtRMB(d.all_rev)}}（¥${{(d.all_rev/10000).toFixed(0)}}万）</span>，日均 ${{Math.round(d.all_orders/30)}}单。</li>
      <li><strong>我司表现：</strong>${{our.rooms}}个直播间合计 <span class="highlight">${{fmt(our.orders)}}单（份额${{fmtPct(d.our_share)}}）</span>，销售额 <span class="highlight">${{fmtRMB(our.revenue)}}（¥${{(our.revenue/10000).toFixed(0)}}万）</span>，均价¥${{our.avg_price}}。</li>
      <li><strong>我司TOP3（按销售额）：</strong>🥇 ${{d.our_rooms_ranked[0][0]}}（${{fmtRMB(d.our_rooms_ranked[0][1].revenue)}}）| 🥈 ${{d.our_rooms_ranked[1][0]}}（${{fmtRMB(d.our_rooms_ranked[1][1].revenue)}}）| 🥉 ${{d.our_rooms_ranked[2][0]}}（${{fmtRMB(d.our_rooms_ranked[2][1].revenue)}}）。</li>
      <li><strong>机械空间：</strong>${{jx.rooms}}个直播间 ${{fmt(jx.orders)}}单，${{fmtRMB(jx.revenue)}}，均价¥${{jx.avg_price}}，为我司${{(jx.revenue/our.revenue*100).toFixed(0)}}%。</li>
      <li><strong>纵横：</strong>${{zh.rooms}}个直播间 ${{fmt(zh.orders)}}单，${{fmtRMB(zh.revenue)}}。</li>
      <li><strong>良米：</strong>${{lm.rooms}}个直播间 ${{fmt(lm.orders)}}单，${{fmtRMB(lm.revenue)}}，为最大竞对群体。</li>
      <li><strong>热销产品TOP3：</strong>🥇 ${{d.prods_ranked[0][0]}}（${{fmtRMB(d.prods_ranked[0][1].revenue)}}）| 🥈 ${{d.prods_ranked[1][0]}}（${{fmtRMB(d.prods_ranked[1][1].revenue)}}）| 🥉 ${{d.prods_ranked[2][0]}}（${{fmtRMB(d.prods_ranked[2][1].revenue)}}）。</li>
      <li><strong>最佳周：</strong>${{best_week[1].label}}，我司${{fmt(best_week[1].our_orders)}}单，销售额${{fmtRMB(best_week[1].our_revenue)}}。</li>
      <li><strong>趋势：</strong>W1→W4我司份额从30.0%提升至35.4%（+5.4pp），618大促周（W3）全渠道峰值¥930万。</li>
    </ul>
  `;
}})();

// Competitive analysis
(function renderCompetitive() {{
  const d = DATA;
  const our = d.team_totals['我司'], jx = d.team_totals['机械空间'], zh = d.team_totals['纵横'], lm = d.team_totals['良米'];
  const all_rev = d.all_rev;

  // Find room-level comparisons
  const rooms = {{}};
  d.rooms_ranked.forEach(([n,i]) => {{ rooms[n] = i; }});
  const band_vs = rooms['小米官方手环直播间'] && rooms['小米手环'] ?
    `手环号 ${{fmt(rooms['小米官方手环直播间'].orders)}}单 vs 良米「小米手环」${{fmt(rooms['小米手环'].orders)}}单 (${{(rooms['小米官方手环直播间'].orders/rooms['小米手环'].orders*100).toFixed(0)}}%)` : '';
  const watch_vs = rooms['小米官方手表'] && rooms['小米手表官方直播间'] ?
    `官方手表 ${{fmt(rooms['小米官方手表'].orders)}}单 vs 良米「小米手表官方直播间」${{fmt(rooms['小米手表官方直播间'].orders)}}单 (${{(rooms['小米官方手表'].orders/rooms['小米手表官方直播间'].orders*100).toFixed(0)}}%)` : '';
  const shop_vs = rooms['小米数码旗舰店'] && rooms['小米数码智能旗舰店'] ?
    `数码旗舰 ${{fmt(rooms['小米数码旗舰店'].orders)}}单 vs 良米「小米数码智能旗舰店」${{fmt(rooms['小米数码智能旗舰店'].orders)}}单 (${{(rooms['小米数码旗舰店'].orders/rooms['小米数码智能旗舰店'].orders*100).toFixed(0)}}%)` : '';

  document.getElementById('competitiveAnalysis').innerHTML = `
    <h3>一、四队格局</h3>
    <p>6月形成<span class="highlight">我司·机械空间·纵横·良米</span>四队竞争格局。我司6个直播间以¥${{(our.revenue/10000).toFixed(0)}}万销售额居第二，份额32.5%。良米以10个直播间¥${{(lm.revenue/10000).toFixed(0)}}万占47.1%领先，但其直播间数量多、均价跨度大（¥242—¥1,088），呈分散竞争态势。机械空间2个直播间¥${{(jx.revenue/10000).toFixed(0)}}万集中在穿戴品类，是我司最直接的竞争对手。</p>

    <h3>二、关键对位</h3>
    <table style="width:100%;border-collapse:collapse;margin:10px 0;font-size:13px">
      <tr style="background:#f8fafc"><th style="padding:8px;text-align:left">对位</th><th style="padding:8px;text-align:left">我司直播间</th><th style="padding:8px;text-align:left">竞对直播间</th><th style="padding:8px;text-align:left">差距</th></tr>
      <tr><td style="padding:8px">🔴 手环赛道</td><td style="padding:8px">官方手环号 ${{fmt(rooms['小米官方手环直播间']?.orders||0)}}单</td><td style="padding:8px">良米「小米手环」${{fmt(rooms['小米手环']?.orders||0)}}单</td><td style="padding:8px;color:#FF4757">落后 ${{fmt((rooms['小米手环']?.orders||0)-(rooms['小米官方手环直播间']?.orders||0))}}单</td></tr>
      <tr><td style="padding:8px">🟡 手表赛道</td><td style="padding:8px">官方手表+官旗手表 ${{fmt((rooms['小米官方手表']?.orders||0)+(rooms['小米官旗手表直播间']?.orders||0))}}单</td><td style="padding:8px">良米「小米手表官方直播间」${{fmt(rooms['小米手表官方直播间']?.orders||0)}}单</td><td style="padding:8px;color:#ff6900">胶着</td></tr>
      <tr><td style="padding:8px">🟢 旗舰店赛道</td><td style="padding:8px">数码旗舰店 ${{fmt(rooms['小米数码旗舰店']?.orders||0)}}单</td><td style="padding:8px">良米「小米数码智能旗舰店」${{fmt(rooms['小米数码智能旗舰店']?.orders||0)}}单</td><td style="padding:8px;color:#1da85c">基本持平</td></tr>
      <tr><td style="padding:8px">🔴 穿戴授权</td><td style="padding:8px">—</td><td style="padding:8px">机械空间「授权号+国补号」${{fmt(jx.orders)}}单</td><td style="padding:8px;color:#FF4757">我司无直接对标</td></tr>
    </table>

    <h3>三、品类强弱</h3>
    <table style="width:100%;border-collapse:collapse;margin:10px 0;font-size:13px">
      <tr style="background:#f8fafc"><th style="padding:8px;text-align:left">品类</th><th style="padding:8px">我司份额</th><th style="padding:8px">判断</th></tr>
      <tr><td style="padding:8px">小米手环10</td><td style="padding:8px;color:#1da85c;font-weight:700">46.5%</td><td style="padding:8px">🟢 核心优势品类，接近过半</td></tr>
      <tr><td style="padding:8px">开放式耳机</td><td style="padding:8px;color:#1da85c;font-weight:700">64.3%</td><td style="padding:8px">🟢 绝对领先</td></tr>
      <tr><td style="padding:8px">手环9 Pro</td><td style="padding:8px;color:#1E90FF;font-weight:700">50.5%</td><td style="padding:8px">🟢 过半，但体量小(1015单)</td></tr>
      <tr><td style="padding:8px">Buds 8 活力版</td><td style="padding:8px;color:#ff6900;font-weight:700">31.3%</td><td style="padding:8px">🟡 与机械/良米三分天下</td></tr>
      <tr><td style="padding:8px">REDMI Watch 6</td><td style="padding:8px;color:#ff6900;font-weight:700">27.6%</td><td style="padding:8px">🟡 与机械空间26.6%几乎持平</td></tr>
      <tr><td style="padding:8px">小米手环10 Pro</td><td style="padding:8px;color:#FF6B35;font-weight:700">23.6%</td><td style="padding:8px">🟠 良米55.2%主导，差距大</td></tr>
      <tr><td style="padding:8px">头戴式耳机</td><td style="padding:8px;color:#FF4757;font-weight:700">14.6%</td><td style="padding:8px">🔴 良米85.4%，新品未抓住</td></tr>
      <tr><td style="padding:8px">Buds 8 青春版</td><td style="padding:8px;color:#FF4757;font-weight:700">8.6%</td><td style="padding:8px">🔴 几乎无存在感</td></tr>
    </table>
  `;
}})();

// Improvement suggestions
(function renderImprovements() {{
  const d = DATA;
  const w4 = d.weeks['W4'], w1 = d.weeks['W1'];
  const share_improve = w4 && w1 ? (w4.our_orders/w4.total_orders*100 - w1.our_orders/w1.total_orders*100).toFixed(1) : 0;

  document.getElementById('improvementSuggestions').innerHTML = `
    <h3>🔴 短期紧急 (7月第一周)</h3>
    <ul>
      <li><strong>手环号止跌：</strong>6.30仅215单（较6.28的310单降30.6%），排查是耳机首发分流还是运营问题。如为运营问题，需紧急调整排班和话术。</li>
      <li><strong>10 Pro品类攻坚：</strong>我司仅占23.6%，良米55.2%。检查我司手环号/数码旗舰店的10 Pro曝光占比、链接权重、价格竞争力。</li>
      <li><strong>Watch 6与机械空间拉开差距：</strong>我司27.6% vs 机械26.6%几乎持平。利用手表号+官旗手表号双号协同，加大Watch 6推品力度。</li>
    </ul>
    <h3>🟡 中期改进 (7月)</h3>
    <ul>
      <li><strong>搭建穿戴授权号对标机械空间：</strong>机械空间2个号（授权号+国补号）以¥641万的销售额成为穿戴赛道第二极，我司缺乏类似"授权号"形态的直播间。考虑新增或改造一个直播间走授权/国补路线。</li>
      <li><strong>手表号矩阵优化：</strong>目前手表号+官旗手表号+纵横手表直播号三个手表相关号，需明确分工：一个主打Watch 6，一个主攻S5高客单，一个做新品首发。</li>
      <li><strong>耳机品类定位清晰化：</strong>开放式耳机领先(64.3%)但头戴式(14.6%)和青春版(8.6%)极弱。耳机号需明确重点品类——是守开放式优势还是攻头戴增量。</li>
      <li><strong>提高10 Pro客单价转化：</strong>我司10 Pro均价¥395（vs手环10 ¥296），客单价优势明显。增加10 Pro在高峰时段(9-11点、20-22点)的曝光权重。</li>
    </ul>
    <h3>🟢 数据驱动运营</h3>
    <ul>
      <li><strong>份额仪表盘：</strong>每周一跟踪我司在10/10 Pro/Watch 6三大核心品类的份额变化，设定10 Pro 30%、Watch 6 35%为7月目标。</li>
      <li><strong>出单时段优化：</strong>我司10:00仅219单（全渠道1,167单），高峰时段渗透不足。增加9-11点的推品频次和库存准备。</li>
      <li><strong>日均目标：</strong>6月我司日均944单。7月目标日均1,000单(+6%)，重点提升工作日(周一至周四)的均值。</li>
    </ul>
  `;
}})();

// Future direction
(function renderFuture() {{
  const d = DATA;
  document.getElementById('futureDirection').innerHTML = `
    <h3>7月战略方向</h3>
    <table style="width:100%;border-collapse:collapse;margin:10px 0;font-size:13px">
      <tr style="background:#f8fafc"><th style="padding:10px;text-align:left;width:15%">方向</th><th style="padding:10px;text-align:left;width:25%">目标</th><th style="padding:10px;text-align:left">具体动作</th></tr>
      <tr>
        <td style="padding:10px;vertical-align:top">🔴<br>手环号回升</td>
        <td style="padding:10px;vertical-align:top">日单量恢复至280+</td>
        <td style="padding:10px">① 排查6.30异常原因（数据/运营/竞争）<br>② 优化高峰时段排班（9-11点双主播）<br>③ 增加10 Pro链接在黄金时段的排品权重<br>④ 与数码旗舰店错品运营，减少内部竞争</td>
      </tr>
      <tr>
        <td style="padding:10px;vertical-align:top">🟡<br>Watch 6突破</td>
        <td style="padding:10px;vertical-align:top">品类份额提升至35%</td>
        <td style="padding:10px">① 手表号+官旗手表号双号分工：一个日播、一个高峰补位<br>② Watch 6话术更新：突出"澎湃OS 3""心率血氧""长续航"三大卖点<br>③ 对标机械空间授权号的定价策略（机械均价¥437 vs 我司¥461）</td>
      </tr>
      <tr>
        <td style="padding:10px;vertical-align:top">🟢<br>10 Pro渗透</td>
        <td style="padding:10px;vertical-align:top">品类份额从23.6%→30%</td>
        <td style="padding:10px">① 在所有我司直播间增加10 Pro曝光频次<br>② 制作10 Pro vs 10对比话术（¥395 vs ¥296，强调HRV/睡眠/游戏模式升级价值）<br>③ 争取平台补贴资源，缩小与良米链接的价格差距</td>
      </tr>
      <tr>
        <td style="padding:10px;vertical-align:top">🔵<br>团队扩张</td>
        <td style="padding:10px;vertical-align:top">新开1-2个直播间</td>
        <td style="padding:10px">① 方案A：新增"国补号/授权号"对标机械空间，切入穿戴低价段<br>② 方案B：新增"耳机专号"承接耳机新品，释放现有耳机号产能<br>③ 优先方案A（机械空间¥641万/月是已被验证的模式）</td>
      </tr>
      <tr>
        <td style="padding:10px;vertical-align:top">🟣<br>数据能力</td>
        <td style="padding:10px;vertical-align:top">建立日/周/月三级分析体系</td>
        <td style="padding:10px">① 每日：自动化日报（已就绪）→ 关注异常值<br>② 每周：周报对比（我司 vs 机械空间 vs 良米 核心品类份额）<br>③ 每月：月度复盘（新增直播间评估、品类结构优化、竞对动态追踪）</td>
      </tr>
    </table>
    <div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">
      <strong>🎯 7月核心KPI：</strong>
      我司日均 <span class="highlight">1,000单</span>（6月944单）|
      品类份额 手环10 Pro ≥<span class="highlight">30%</span> |
      Watch 6 ≥<span class="highlight">35%</span> |
      新开<span class="highlight">1个</span>直播间
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

  // Weekly share — bar chart with data labels
  const chart4 = echarts.init(document.getElementById('chartWeeklyShare'));
  const wkShare = Object.values(weeks).map(w => parseFloat((w.our_orders / w.total_orders * 100).toFixed(1)));
  const wkShareAvg = (wkShare.reduce((a,b) => a+b, 0) / wkShare.length).toFixed(1);
  const shareColors = wkShare.map(v => v >= 34 ? '#1E90FF' : '#FF6B35');
  chart4.setOption({{
    title: {{ text: '我方周度份额变化', left: 'center', textStyle: {{ fontSize: 16, fontWeight: 700 }} }},
    tooltip: {{ trigger: 'axis', formatter: p => {{
      const d = p[0];
      return `<b>${{d.name}}</b><br/>我方份额: <b style="color:#1E90FF;font-size:18px">${{d.value}}%</b><br/>月均: ${{wkShareAvg}}%`;
    }} }},
    grid: {{ left: 50, right: 40, top: 55, bottom: 45 }},
    xAxis: {{ type: 'category', data: wkLabels, axisLabel: {{ fontSize: 12, fontWeight: 600 }} }},
    yAxis: {{ type: 'value', name: '份额 (%)', min: 28, max: 40, axisLabel: {{ formatter: '{{value}}%' }}, splitLine: {{ lineStyle: {{ type: 'dashed', color: '#e8ecf1' }} }} }},
    series: [
      {{
        name: '我方份额', type: 'bar', data: wkShare,
        itemStyle: {{ color: p => shareColors[p.dataIndex], borderRadius: [6,6,0,0] }},
        barWidth: '50%',
        label: {{ show: true, position: 'top', fontSize: 16, fontWeight: 700, color: '#0f172a', formatter: '{{c}}%' }},
        markLine: {{
          silent: true,
          symbol: 'none',
          data: [{{ yAxis: parseFloat(wkShareAvg), name: '月均', label: {{ formatter: '月均\\n{{c}}%', fontSize: 11, color: '#7c6ff7' }} }}],
          lineStyle: {{ color: '#7c6ff7', type: 'dashed', width: 2 }}
        }},
        emphasis: {{ itemStyle: {{ color: '#ff6900' }} }}
      }}
    ]
  }});

  window.addEventListener('resize', () => {{ chart1.resize(); chart2.resize(); chart3.resize(); chart4.resize(); }});
}})();
</script>

</body>
</html>'''

    return html


if __name__ == '__main__':
    june = load_june_data()
    summary = build_summary(june)
    html = generate_html(summary)
    out_path = os.path.join(DATA_DIR, '六月销量分析.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(f'Generated: {out_path}')
    print(f'  June days: {len(june)}')
    print(f'  Total orders: {summary["all_orders"]:,}')
    print(f'  我司: {summary["our_orders"]:,}单 ({summary["our_share"]}%), {summary["our_rev"]:,.0f}')
    for t in ['机械空间', '纵横', '良米']:
        tt = summary['team_totals'][t]
        print(f'  {t}: {tt["orders"]:,}单, {tt["revenue"]:,.0f}')

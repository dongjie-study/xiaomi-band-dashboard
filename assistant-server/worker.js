// 小米手环直播间 · 数据小管家
// Cloudflare Worker：内嵌聊天页 + DeepSeek function calling 查询项目数据
//
// 数据源：GitHub raw（仓库每天 push 自动最新），只读，不碰本地任何流程
// 口令：环境变量 ACCESS_ENABLED ("true"/"false") + ACCESS_CODE，可在 CF 控制台随时改、随时开关，不写死在代码里
// DeepSeek key：wrangler secret put DEEPSEEK_API_KEY（绝不进 git）

const RAW_BASE = 'https://raw.githubusercontent.com/dongjie-study/xiaomi-band-dashboard/main/';
const GH_FILE = {
  history: 'sales_analysis/history.json',
  band11: 'sales_analysis/band11_history.json',
  dailySummary: 'sales_analysis/daily_summary.json',
  anchor: '主播业绩/anchor_records.json',
  hourly: (d) => `sales_analysis/hourly/${d}.json`,
};

// ---------- 团队归属（与 team_config.py 同步维护） ----------
const TEAM_MAP = {
  '小米官方手表': '我司', '小米官方手环直播间': '我司', '小米数码旗舰店': '我司',
  '小米官方耳机直播间': '我司', '小米手环10Pro直播间': '我司', '小米官旗手表直播间': '我司',
  '小米智能设备旗舰店直播间': '我司', '小米手环官旗直播间': '我司', '小米AI眼镜直播间': '我司',
  '小米智能穿戴国补号': '机械空间', '小米智能穿戴授权号': '机械空间',
  '小米官方手表直播号': '纵横', '小米手环官方直播间': '纵横',
  '小米手环直播间': '凝云', '小米手环官方账号': '逐梦',
  '小米智能穿戴官方直播间': '斐纳', '小米官方手环账号': '斐纳',
  '小米智能手表官方直播间': '乐畔',
  '小米耳机数码官方直播间': '炽木电商', '小米手环智能穿戴官方直播间': '炽木电商',
  '小米手环官方': '米乐',
  '小米官方手环号': '良米', '小米手环': '良米', '小米数码智能旗舰店': '良米',
  'watch智能手环直播间': '良米', 'watch数码手环直播间': '良米', '小米智能手表旗舰店': '良米',
  '小米手表官方直播间': '良米', '小米手表': '良米', '小米官方手表直播': '良米',
  '小米耳机官方直播间': '良米', '小米官方Ai智能眼镜': '良米', '小米手环11直播间': '良米', '小米耳机': '良米',
  '我司商品卡': '我司', '良米商品卡': '良米',
};
const TEAM_ORDER = ['我司', '机械空间', '纵横', '凝云', '逐梦', '斐纳', '乐畔', '炽木电商', '米乐', '良米'];
const IGNORED_ROOM = '小米手环手表直播间'; // 归属未定，整间不入库

const BAND11 = {
  product: '小米手环11', target: 60000, start: '2026-09-07', end: '2026-10-07',
  mainRooms: ['小米官方手环直播间', '小米数码旗舰店', '我司商品卡', '小米官方手表'],
  quotaPerDay: 60000 / 31,
};

// ---------- 数据缓存（每个 isolate 一份，10 分钟） ----------
const CACHE = new Map();
const CACHE_TTL = 10 * 60 * 1000;

async function fetchJson(path) {
  const url = RAW_BASE + path.split('/').map(encodeURIComponent).join('/');
  const hit = CACHE.get(url);
  if (hit && Date.now() - hit.t < CACHE_TTL) return hit.data;
  const res = await fetch(url, { headers: { 'User-Agent': 'data-assistant/1.0' } });
  if (!res.ok) throw new Error(`拉取 ${path} 失败（HTTP ${res.status}）`);
  const data = await res.json();
  CACHE.set(url, { t: Date.now(), data });
  return data;
}

// ---------- 工具实现 ----------

function today() { return new Date().toISOString().slice(0, 10); }
function validDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }

async function toolQuerySales(args) {
  const history = await fetchJson(GH_FILE.history);
  const latest = history[history.length - 1].date;
  const first = history[0].date;
  let start = validDate(args.start_date) ? args.start_date : null;
  let end = validDate(args.end_date) ? args.end_date : null;
  if (!start && !end) { end = latest; start = history[Math.max(0, history.length - 7)].date; }
  if (!start) start = first;
  if (!end) end = latest;
  if (end < start) [start, end] = [end, start];

  const days = history.filter(r => r.date >= start && r.date <= end);
  if (!days.length) {
    return { error: `该区间没有数据。数据范围：${first} ~ ${latest}`, meta: { first, latest } };
  }
  const clipped = days[0].date > start || days[days.length - 1].date < end;
  const meta = { latest, first, queried: `${days[0].date} ~ ${days[days.length - 1].date}`, clipped };

  // 团队聚合口径
  if (args.team && TEAM_ORDER.includes(args.team)) {
    const rows = days.map(r => {
      const t = (r.type_summary || {})[args.team] || {};
      return { date: r.date, orders: t.orders || 0, revenue: Math.round(t.revenue || 0), rooms: t.rooms };
    });
    const sum = rows.reduce((a, x) => ({ orders: a.orders + x.orders, revenue: a.revenue + x.revenue }), { orders: 0, revenue: 0 });
    return { meta, unit: `${args.team}团队（订单口径，含退款后实付）`, days: rows, range_total: sum };
  }

  // 直播间口径
  let roomKey = null;
  if (args.room) {
    roomKey = resolveRoom(args.room);
    if (roomKey instanceof Array) return { error: `「${args.room}」匹配到多个直播间：${roomKey.join('、')}，请用完整名称重查`, meta };
    if (roomKey === null) return { error: `没找到直播间「${args.room}」。已知直播间见房间归属表`, meta };
    if (roomKey === IGNORED_ROOM) return { error: `「${roomKey}」归属未定，整间不入库，无数据`, meta };
  }

  let prodKey = args.product ? resolveProduct(days, args.product) : null;
  if (args.product && !prodKey) {
    const sample = Object.keys(days[days.length - 1].products || {}).slice(0, 20);
    return { error: `没找到商品「${args.product}」。近期在售商品示例：${sample.join('、')}`, meta };
  }

  const rows = days.map(r => {
    const row = { date: r.date };
    if (!roomKey && !prodKey) {
      row.orders = r.total_orders; row.revenue = Math.round(r.total_revenue); row.avg_price = Math.round(r.avg_price);
    } else if (roomKey && !prodKey) {
      const rm = (r.rooms || {})[roomKey] || {};
      row.orders = rm.orders || 0; row.revenue = Math.round(rm.revenue || 0); row.avg_price = Math.round(rm.avg_price || 0);
      row.team = rm.type || TEAM_MAP[roomKey];
    } else if (!roomKey && prodKey) {
      const p = (r.products || {})[prodKey] || {};
      row[prodKey] = { orders: p.orders || 0, revenue: Math.round(p.revenue || 0) };
      row.total_orders = r.total_orders; // 附全天总量便于算占比
    } else {
      const p = ((r.rooms || {})[roomKey] || {}).products || {};
      const pp = p[prodKey] || {};
      row[prodKey] = { orders: pp.orders || 0, revenue: Math.round(pp.revenue || 0) };
      row.room_orders = ((r.rooms || {})[roomKey] || {}).orders || 0;
    }
    return row;
  });

  const range_total = rows.reduce((a, x) => {
    a.orders = (a.orders || 0) + (x.orders ?? x[prodKey]?.orders ?? x.room_orders ?? 0);
    a.revenue = (a.revenue || 0) + (x.revenue ?? x[prodKey]?.revenue ?? 0);
    return a;
  }, {});

  const unit = roomKey
    ? `${roomKey}（${TEAM_MAP[roomKey]}，订单口径）`
    : prodKey ? `商品「${prodKey}」${roomKey ? '在 ' + roomKey : '全天'}（订单口径）` : '全店（订单口径）';
  return { meta, unit, days: rows, range_total };
}

function resolveRoom(name) {
  const n = String(name).trim();
  if (TEAM_MAP[n] !== undefined) return n;                 // 完整名
  if (TEAM_ORDER.includes(n)) return null;                  // 团队名在 sales 工具里走 team 参数
  const contains = Object.keys(TEAM_MAP).filter(k => k.includes(n));
  if (contains.length === 1) return contains[0];
  if (contains.length > 1) return contains;
  return null;
}

function resolveProduct(days, name) {
  const n = String(name).trim();
  const pool = new Set();
  days.forEach(r => Object.keys(r.products || {}).forEach(k => pool.add(k)));
  if (pool.has(n)) return n;
  const hits = [...pool].filter(k => k.includes(n) || n.includes(k.replace(/REDMI|Xiaomi|小米/g, '').trim()));
  if (hits.length >= 1) return hits.sort((a, b) => a.length - b.length)[0]; // 最短=最贴近
  return null;
}

async function toolQueryHourly(args) {
  if (!validDate(args.date)) return { error: 'date 必须是 YYYY-MM-DD 格式（如 2026-09-24）' };
  let data;
  try { data = await fetchJson(GH_FILE.hourly(args.date)); }
  catch (e) { return { error: `${args.date} 没有小时级数据（可能是还没入库，或日期超出数据范围）` }; }

  let roomKey = null;
  if (args.room) {
    roomKey = resolveRoom(args.room);
    if (roomKey instanceof Array) return { error: `「${args.room}」匹配到多个直播间：${roomKey.join('、')}` };
    if (!roomKey || !(data.rooms || {})[roomKey]) return { error: `当天没有「${args.room}」的数据` };
  }
  let prodKey = args.product ? String(args.product).trim() : null;

  const src = roomKey ? data.rooms[roomKey]._hourly_stats : data._hourly_stats;
  const hours = {};
  for (const [h, v] of Object.entries(src || {})) {
    let orders = v.orders, revenue = v.revenue;
    if (prodKey) {
      const p = (v.products || {})[prodKey] || [...Object.entries(v.products || {})].find(([k]) => k.includes(prodKey))?.[1];
      if (!p) continue;
      orders = p.orders; revenue = p.revenue;
    }
    hours[`${String(h).padStart(2, '0')}:00`] = { orders, revenue: Math.round(revenue) };
  }
  const peak = Object.entries(hours).sort((a, b) => b[1].orders - a[1].orders).slice(0, 3)
    .map(([h, v]) => `${h} ${v.orders}单`);
  return {
    unit: `${args.date} ${roomKey || '全店'}${prodKey ? ' · ' + prodKey : ''}（订单口径，按小时）`,
    hours, top3_peak: peak,
  };
}

async function toolQueryAnchor(args) {
  const data = await fetchJson(GH_FILE.anchor);
  const records = data.records || {};
  const allDays = Object.keys(records).sort();
  if (!allDays.length) return { error: '主播业绩数据还没生成（主播业绩/anchor_records.json 为空）' };
  const latest = allDays[allDays.length - 1];
  let start = validDate(args.start_date) ? args.start_date : null;
  let end = validDate(args.end_date) ? args.end_date : latest;
  if (!start) start = allDays[Math.max(0, allDays.length - 7)];
  if (end < start) [start, end] = [end, start];

  const name2id = Object.fromEntries(Object.entries(data.room_names || {}).map(([id, nm]) => [nm, id]));
  let roomId = null;
  if (args.room) {
    const r = String(args.room).trim();
    roomId = name2id[r] || Object.entries(name2id).find(([nm]) => nm.includes(r))?.[1];
    if (!roomId) return { error: `没找到直播间「${args.room}」。业绩面板覆盖：${Object.keys(name2id).join('、')}`, meta: { latest } };
  }

  const out = [];
  for (const d of allDays.filter(x => x >= start && x <= end)) {
    for (const rec of records[d]) {
      if (roomId && rec.roomId !== roomId) continue;
      if (args.anchor && !String(rec.anchor).includes(String(args.anchor).trim())) continue;
      out.push({ date: d, room: (data.room_names || {})[rec.roomId] || rec.roomId, shift: rec.shift, anchor: rec.anchor, gsv: Math.round(rec.sales) });
    }
  }
  if (!out.length) return { error: '该条件下没有业绩记录', meta: { latest, range: `${start} ~ ${end}` } };
  const total = Math.round(out.reduce((a, x) => a + x.gsv, 0));
  const capped = out.slice(0, 120);
  return {
    meta: { latest, range: `${start} ~ ${end}`, count: out.length, truncated: out.length > 120 },
    unit: '主播 GSV 口径（未扣退款）。shift: A/B/C/D/E 班，A=早班起',
    records: capped, gsv_total: total,
  };
}

async function toolDailyReviews(args) {
  const store = await fetchJson(GH_FILE.dailySummary);
  const reviews = (store.reviews || {});
  const allDays = Object.keys(reviews).sort();
  if (!allDays.length) return { error: '每日总结库为空' };
  let start = validDate(args?.start_date) ? args.start_date : allDays[0];
  let end = validDate(args?.end_date) ? args.end_date : allDays[allDays.length - 1];
  const picked = {};
  for (const d of allDays.filter(x => x >= start && x <= end)) {
    const r = reviews[d];
    picked[d] = { rating: r.rating, good: r.good, bad: r.bad, watch: r.watch, by: r.written_by };
  }
  return { unit: '每日销售总结（订单口径，只有首销月 9.7~10.7 期间）', latest: allDays[allDays.length - 1], reviews: picked };
}

async function toolBand11Progress() {
  const rows = await fetchJson(GH_FILE.band11);
  const inRange = rows.filter(r => r.date >= BAND11.start && r.date <= BAND11.end);
  const cumOur = inRange.reduce((a, r) => a + (r.our?.live_o || 0) + (r.our?.card_o || 0), 0);
  const cumLm = inRange.reduce((a, r) => a + (r.lm?.live_o || 0) + (r.lm?.card_o || 0), 0);
  const days = inRange.map(r => ({
    date: r.date,
    our: (r.our?.live_o || 0) + (r.our?.card_o || 0),
    our_gsv: Math.round((r.our?.live_a || 0) + (r.our?.card_a || 0)),
    lm: (r.lm?.live_o || 0) + (r.lm?.card_o || 0),
  }));
  const last = inRange[inRange.length - 1];
  const cumRate = cumOur / BAND11.target;
  const timeRate = inRange.length / 31;
  return {
    unit: `手环11 首销月（${BAND11.start} ~ ${BAND11.end}），我司四渠道+其他直播间，台数=订单口径`,
    target: BAND11.target, quota_per_day: Math.round(BAND11.quotaPerDay),
    cumulative_our: cumOur, cumulative_lm: cumLm,
    cum_rate: +(cumRate * 100).toFixed(1) + '%',
    time_rate: +(timeRate * 100).toFixed(1) + '%',
    pace_diff: +((cumRate - timeRate) * 100).toFixed(1) + '%',
    latest_day: last ? { date: last.date, our: (last.our?.live_o || 0) + (last.our?.card_o || 0), lm: (last.lm?.live_o || 0) + (last.lm?.card_o || 0) } : null,
    days,
    note: 'our_gsv 为我司直播+商品卡金额合计（元）。分渠道明细用 query_sales 查 product=小米手环11。',
  };
}

const TOOLS = [
  {
    type: 'function', function: {
      name: 'query_sales',
      description: '查询每日销量数据（订单口径，全店/某直播间/某商品/某团队）。可查订单量、销售额、均价。数据自 2026-06-01 起。',
      parameters: {
        type: 'object', properties: {
          start_date: { type: 'string', description: 'YYYY-MM-DD，缺省=近7天' },
          end_date: { type: 'string', description: 'YYYY-MM-DD，缺省=最新一天' },
          room: { type: 'string', description: '直播间完整名，如 小米官方手环直播间' },
          product: { type: 'string', description: '商品名，如 小米手环11、REDMI Watch 6' },
          team: { type: 'string', description: '团队名：我司/良米/机械空间/纵横/凝云/逐梦/斐纳/乐畔/炽木电商/米乐' },
        },
      },
    },
  },
  {
    type: 'function', function: {
      name: 'query_hourly',
      description: '查询某天的小时级销量分布（全天或某直播间，可选商品），可看出单高峰时段。',
      parameters: {
        type: 'object', required: ['date'], properties: {
          date: { type: 'string', description: 'YYYY-MM-DD' },
          room: { type: 'string' },
          product: { type: 'string' },
        },
      },
    },
  },
  {
    type: 'function', function: {
      name: 'query_anchor_performance',
      description: '查询主播业绩（GSV 口径，未扣退款）：每主播每班次的销售额。注意 GSV 与订单实付口径不同。',
      parameters: {
        type: 'object', properties: {
          start_date: { type: 'string', description: 'YYYY-MM-DD' },
          end_date: { type: 'string', description: 'YYYY-MM-DD' },
          room: { type: 'string', description: '直播间名（我司 9 间 + 手环预约期业绩）' },
          anchor: { type: 'string', description: '主播姓名（支持部分匹配）' },
        },
      },
    },
  },
  {
    type: 'function', function: {
      name: 'get_daily_reviews',
      description: '查询官方每日销售总结（好/差/盯三段式 + 评级），首销月期间每天一篇。',
      parameters: {
        type: 'object', properties: {
          start_date: { type: 'string' },
          end_date: { type: 'string' },
        },
      },
    },
  },
  {
    type: 'function', function: {
      name: 'get_band11_progress',
      description: '查询手环11 首销月（9.7~10.7）目标进度：累计台数 vs 60000 目标、我司 vs 良米每日对比、进度差。',
      parameters: { type: 'object', properties: {} },
    },
  },
];

const TOOL_IMPLS = {
  query_sales: toolQuerySales,
  query_hourly: toolQueryHourly,
  query_anchor_performance: toolQueryAnchor,
  get_daily_reviews: toolDailyReviews,
  get_band11_progress: toolBand11Progress,
};

// ---------- 系统提示词：项目知识库 ----------
function systemPrompt() {
  const roomLines = TEAM_ORDER.map(t => {
    const rooms = Object.keys(TEAM_MAP).filter(k => TEAM_MAP[k] === t);
    return `- ${t}（${rooms.length}间）：${rooms.join('、')}`;
  }).join('\n');
  return `你是「小米手环直播间数据分析小管家」，服务内部同事查询直播间销量数据。今天日期：${today()}。

## 数据口径（非常重要，回答时必须说明口径）
1. **订单口径**（query_sales/query_hourly/get_band11_progress）：来自后台导出的订单明细，金额=实付销售额。总订单量与直播间明细一致。
2. **主播 GSV 口径**（query_anchor_performance）：主播每班次业绩，**未扣退款**，与订单口径数字对不上是正常的。
3. **手环11 台数**：指商品「小米手环11」的订单件数，不是 GMV。
4. 「小米手环手表直播间」归属未定，整间不入库，查不到是正常的。
5. 每份工具返回里有 meta/latest 字段标明数据更新到哪天，回答时注明数据截至日期。

## 直播间归属表（房间名必须一字不差）
${roomLines}
⚠️ 极易混淆：「小米官方手环直播间」（我司）≠「小米手环官方直播间」（纵横）≠「小米手环直播间」（凝云）；「小米官方手表」（我司）≠「小米手表」（良米）。

## 背景知识
- 平台监控 36 个直播间，分属 10 个服务商团队；我司=阳光（自营），良米=主要竞对。
- 主力商品：小米手环11（首销月 9.7~10.7，总目标 60000 台，日均需求约 1935 台）、REDMI Watch 6、小米手环10 Pro、Xiaomi Watch S5、REDMI Buds 8 系列。
- 数据范围：销量自 2026-06-01 起；主播业绩自 2026-08 月起。
- 考核四渠道：小米官方手环直播间、小米数码旗舰店、我司商品卡、小米官方手表。

## 回答规则
1. 任何数字必须来自工具查询结果，禁止编造或凭记忆推测。
2. 日期一律用 YYYY-MM-DD 传给工具；用户说「9月20日」你要转成 2026-09-20。
3. 用户问的直播间名如果不完整（如「手环间」），先按归属表推断成完整名再查；匹配到多个就列出让用户选。
4. 回答简洁、给结论和关键数字，适当给环比/对比；数据较多的用小表格呈现。
5. 不知道或数据里没有的，直接说没有，不要编。
6. 用中文回答。`;
}

// ---------- DeepSeek 调用 ----------
async function deepseekChat(env, messages) {
  const res = await fetch('https://api.deepseek.com/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${env.DEEPSEEK_API_KEY}` },
    body: JSON.stringify({
      model: 'deepseek-chat', messages, tools: TOOLS, tool_choice: 'auto', max_tokens: 3000, temperature: 0.3,
    }),
  });
  if (!res.ok) {
    const errText = (await res.text()).slice(0, 300);
    throw new Error(`DeepSeek 接口异常（${res.status}）：${errText}`);
  }
  const data = await res.json();
  return data.choices[0].message;
}

async function chatWithTools(env, userMessages) {
  const messages = [{ role: 'system', content: systemPrompt() }, ...userMessages];
  for (let round = 0; round < 6; round++) {
    const msg = await deepseekChat(env, messages);
    if (!msg.tool_calls || !msg.tool_calls.length) return msg.content || '（空回复）';
    messages.push({ role: 'assistant', content: msg.content || '', tool_calls: msg.tool_calls });
    for (const tc of msg.tool_calls) {
      const fn = tc.function;
      let result;
      try {
        const args = JSON.parse(fn.arguments || '{}');
        result = await (TOOL_IMPLS[fn.name] || (() => { throw new Error(`未知工具 ${fn.name}`); }))(args);
      } catch (e) {
        result = { error: `查询失败：${e.message}` };
      }
      messages.push({ role: 'tool', tool_call_id: tc.id, content: JSON.stringify(result) });
    }
  }
  return '查询轮次太多，换个更具体的问题试试（比如指定日期和直播间）。';
}

// ---------- HTTP 入口 ----------
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // CORS 预检（工作台模块页跨域调用需要）
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    if (request.method === 'GET' && (url.pathname === '/' || url.pathname === '/index.html')) {
      return new Response(PAGE_HTML, { headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' } });
    }

    if (url.pathname === '/api/config' && request.method === 'GET') {
      const enabled = (env.ACCESS_ENABLED || 'true') === 'true';
      return json({ enabled });
    }

    if (url.pathname === '/api/chat' && request.method === 'POST') {
      const enabled = (env.ACCESS_ENABLED || 'true') === 'true';
      let body;
      try { body = await request.json(); } catch { return json({ error: '请求体不是合法 JSON' }, 400); }

      if (enabled) {
        if (!body.code || body.code !== (env.ACCESS_CODE || '')) {
          return json({ error: '口令不正确', need_code: true }, 403);
        }
      }
      if (!env.DEEPSEEK_API_KEY) return json({ error: '服务端未配置 DeepSeek API key' }, 500);

      // 消息校验与裁剪
      let msgs = Array.isArray(body.messages) ? body.messages : [];
      msgs = msgs
        .filter(m => (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string' && m.content.trim())
        .map(m => ({ role: m.role, content: m.content.slice(0, 4000) }))
        .slice(-20);
      if (!msgs.length || msgs[msgs.length - 1].role !== 'user') {
        return json({ error: '消息格式不对：需要至少一条用户消息，且最后一条是用户消息' }, 400);
      }

      try {
        const answer = await chatWithTools(env, msgs);
        return json({ answer });
      } catch (e) {
        return json({ error: e.message }, 502);
      }
    }

    return json({ error: 'Not Found' }, 404);
  },
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Access-Control-Allow-Origin': '*' },
  });
}

// ---------- 内嵌聊天页 ----------
const PAGE_HTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>数据小管家 · 小米手环直播间</title>
<style>
:root{--bg:#f5f6f8;--card:#fff;--txt:#1a1d26;--sub:#6b7280;--blue:#1E90FF;--mine:#1E90FF;--bubble:#fff;--border:#e5e7eb}
*{box-sizing:border-box;margin:0;padding:0}
body{font:15px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--txt);display:flex;flex-direction:column;height:100vh;max-height:100vh}
header{background:linear-gradient(135deg,#FF6900,#ff8f4d);color:#fff;padding:14px 16px;display:flex;align-items:center;gap:10px;flex-shrink:0}
header .logo{width:34px;height:34px;border-radius:9px;background:rgba(255,255,255,.22);display:flex;align-items:center;justify-content:center;font-size:18px}
header b{font-size:16px;font-weight:600}
header small{display:block;font-size:11px;opacity:.85;font-weight:400}
main{flex:1;overflow-y:auto;padding:14px 12px 8px;-webkit-overflow-scrolling:touch}
.msg{display:flex;margin-bottom:12px;gap:8px}
.msg .av{width:32px;height:32px;border-radius:8px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:16px}
.msg.ai .av{background:#fff3e6}
.msg.me{flex-direction:row-reverse}
.msg.me .av{background:var(--mine);color:#fff}
.bubble{max-width:82%;padding:9px 12px;border-radius:12px;white-space:pre-wrap;word-break:break-word;font-size:14px}
.msg.ai .bubble{background:var(--bubble);border:1px solid var(--border);border-top-left-radius:4px}
.msg.me .bubble{background:var(--mine);color:#fff;border-top-right-radius:4px}
.typing i{display:inline-block;width:6px;height:6px;border-radius:50%;background:#bbb;margin-right:3px;animation:b 1s infinite}
.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}
@keyframes b{0%,60%,100%{transform:none;opacity:.4}30%{transform:translateY(-4px);opacity:1}}
.chips{display:flex;gap:8px;flex-wrap:wrap;padding:4px 12px 8px}
.chip{border:1px solid var(--border);background:#fff;border-radius:16px;padding:5px 12px;font-size:12px;color:var(--sub);cursor:pointer}
form{display:flex;gap:8px;padding:10px 12px calc(12px + env(safe-area-inset-bottom));background:var(--bg);flex-shrink:0}
input[type=text]{flex:1;border:1px solid var(--border);border-radius:10px;padding:10px 14px;font-size:15px;background:#fff;outline:none}
input[type=text]:focus{border-color:var(--blue)}
button{background:var(--blue);color:#fff;border:0;border-radius:10px;padding:0 18px;font-size:15px;cursor:pointer}
button:disabled{opacity:.5}
.gate{position:fixed;inset:0;background:rgba(245,246,248,.98);display:flex;align-items:center;justify-content:center;z-index:9;padding:24px}
.gate .box{background:#fff;border-radius:16px;padding:26px 22px;width:100%;max-width:340px;text-align:center;border:1px solid var(--border)}
.gate h2{font-size:16px;margin-bottom:6px}
.gate p{font-size:12px;color:var(--sub);margin-bottom:16px}
.gate input{width:100%;text-align:center;letter-spacing:3px}
.gate button{width:100%;margin-top:12px;padding:10px 0;border-radius:10px}
.gate .err{color:#e02424;font-size:12px;margin-top:8px;height:16px}
</style>
</head>
<body>
<div class="gate" id="gate" hidden>
  <div class="box">
    <h2>请输入访问口令</h2>
    <p>数据小管家 · 仅限内部使用</p>
    <input type="text" id="codeInput" placeholder="口令" maxlength="20" autofocus>
    <button id="codeBtn">进入</button>
    <div class="err" id="codeErr"></div>
  </div>
</div>
<header><div class="logo">📊</div><div><b>数据小管家</b><small>小米手环直播间销量 · 问我就答</small></div></header>
<main id="list"></main>
<div class="chips" id="chips"></div>
<form id="f"><input type="text" id="q" placeholder="如：9月24日手环直播间卖了多少台手环11？" autocomplete="off"><button id="send">发送</button></form>
<script>
const $=s=>document.querySelector(s);
const list=$('#list'),chips=$('#chips');
const SUGGEST=['手环11首销月进度怎么样了？','9月24日我司整体卖了多少？','手环直播间最近7天走势','9月20日到9月24日谁是销冠主播？','良米这周手环11卖了多少台？'];
let history_=[],busy=false,myCode=localStorage.getItem('dg_code')||'';

function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function add(role,text,typing){
  const d=document.createElement('div');d.className='msg '+role;
  d.innerHTML='<div class="av">'+(role==='ai'?'管家':'我')+'</div><div class="bubble">'+(typing?'<span class="typing"><i></i><i></i><i></i></span>':esc(text))+'</div>';
  list.appendChild(d);list.scrollTop=list.scrollHeight;return d}
function chipsInit(){
  if(history_.length)return;
  SUGGEST.forEach(s=>{const c=document.createElement('div');c.className='chip';c.textContent=s;
    c.onclick=()=>{if(!busy){$('#q').value='';send(s)}};chips.appendChild(c)})}

async function api(path,body){
  const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,code:myCode})}:undefined);
  return {status:r.status,data:await r.json().catch(()=>({}))}}

async function send(text){
  if(busy)return;text=text||$('#q').value.trim();if(!text)return;
  busy=true;$('#send').disabled=true;$('#q').value='';chips.style.display='none';
  history_.push({role:'user',content:text});add('me',text);
  const typingEl=add('ai','',true);
  try{
    const {status,data}=await api('/api/chat',{messages:history_});
    typingEl.remove();
    if(status===403){history_.pop();showGate('口令不正确，请重新输入');return}
    if(data.error){add('ai','出错了：'+data.error)}
    else{history_.push({role:'assistant',content:data.answer});add('ai',data.answer)}
  }catch(e){typingEl.remove();add('ai','网络异常，稍后再试：'+e.message)}
  busy=false;$('#send').disabled=false}

function showGate(msg){$('#gate').hidden=false;$('#codeErr').textContent=msg||'';$('#codeInput').focus()}
async function init(){
  const {data}=await api('/api/config');
  if(data.enabled){
    if(!myCode){showGate()}
    $('#gate').hidden=false;
  }
  add('ai','你好，我是数据小管家 📊\\n我可以查这个项目的销量数据：每日销量、各直播间、主播业绩、手环11 首销月进度等。\\n直接用大白话问就行，比如"9月24日数码旗舰店卖了多少"');
  chipsInit();
}
$('#f').onsubmit=e=>{e.preventDefault();send()};
$('#codeBtn').onclick=async()=>{
  const v=$('#codeInput').value.trim();if(!v)return;
  myCode=v;
  const {status}=await api('/api/chat',{messages:[{role:'user',content:'你好'}]});
  if(status===403){$('#codeErr').textContent='口令不正确';return}
  localStorage.setItem('dg_code',v);$('#gate').hidden=true;
};
$('#codeInput').onkeydown=e=>{if(e.key==='Enter')$('#codeBtn').click()};
init();
</script>
</body>
</html>`;

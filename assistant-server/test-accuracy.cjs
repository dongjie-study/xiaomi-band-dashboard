// 对抗性测试：真实问题打线上小管家，用本地数据独立验证回答是否正确
const fs = require('fs');
const path = require('path');

const BASE = 'https://data.xiaomi-exam.top';
const CODE = 'xiaomi';

// ---------- 本地独立计算期望值 ----------
const root = path.join(__dirname, '..');
const H = JSON.parse(fs.readFileSync(path.join(root, 'sales_analysis', 'history.json'), 'utf8'));
const B11 = JSON.parse(fs.readFileSync(path.join(root, 'sales_analysis', 'band11_history.json'), 'utf8'));
const AN = JSON.parse(fs.readFileSync(path.join(root, '主播业绩', 'anchor_records.json'), 'utf8'));

const latest = H[H.length - 1].date; // 2026-09-25
const day = d => H.find(r => r.date === d);
const fmt = n => Number(n).toLocaleString('en-US');

// 期望值计算
function expect() {
  const out = {};
  // ① 昨天我司卖了多少单（昨天=latest 2026-09-25）
  const t = day(latest).type_summary['我司'];
  out.q1 = { date: latest, our_orders: t.orders, our_revenue: Math.round(t.revenue) };
  // ② 首销月进度
  const inR = B11.filter(r => r.date >= '2026-09-07' && r.date <= '2026-10-07');
  out.q2 = {
    our: inR.reduce((a, r) => a + (r.our?.live_o || 0) + (r.our?.card_o || 0), 0),
    lm: inR.reduce((a, r) => a + (r.lm?.live_o || 0) + (r.lm?.card_o || 0), 0),
  };
  // ③ 9月25日 官方手环直播间 手环11
  const rm = day('2026-09-25').rooms['小米官方手环直播间'];
  const p = (rm?.products || {})['小米手环11'] || {};
  out.q3 = { orders: p.orders, revenue: Math.round(p.revenue || 0), room_total: rm?.orders };
  // ④ 我司 vs 良米 手环11（首销月内最近一天）
  const last = inR[inR.length - 1];
  out.q4 = { date: last.date, our_day: (last.our?.live_o || 0) + (last.our?.card_o || 0), lm_day: (last.lm?.live_o || 0) + (last.lm?.card_o || 0) };
  // ⑤ 9月24日销冠主播（GSV）
  const recs24 = (AN.records['2026-09-24'] || []).slice().sort((a, b) => b.sales - a.sales);
  out.q5 = { anchor: recs24[0]?.anchor, gsv: Math.round(recs24[0]?.sales), room: AN.room_names?.[recs24[0]?.roomId] };
  // ⑥ 9月25日全店总订单
  out.q6 = { total: day('2026-09-25').total_orders, revenue: Math.round(day('2026-09-25').total_revenue) };
  return out;
}

const E = expect();
console.log('=== 本地期望值（数据最新 ' + latest + '）===');
console.log(JSON.stringify(E, null, 1).slice(0, 800));

// ---------- 打线上接口 ----------
async function ask(q) {
  const r = await fetch(BASE + '/api/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code: CODE, messages: [{ role: 'user', content: q }] }),
  });
  const d = await r.json().catch(() => ({}));
  return d.answer || ('ERROR: ' + (d.error || r.status));
}

const QUESTIONS = [
  ['q1', '昨天我司卖了多少单？'],
  ['q2', '手环11首销月进度怎么样了？'],
  ['q3', '9月25日官方手环直播间手环11卖了多少台？'],
  ['q4', '我们和良米比，最近手环11卖得怎么样？'],
  ['q5', '9月24日销冠主播是谁？'],
  ['q6', '9月25日全店卖了多少？几点出单最多？'],
];

(async () => {
  let pass = 0, fail = 0;
  for (const [id, q] of QUESTIONS) {
    const a = await ask(q);
    const num = s => (s.match(/[\d,]+(?:\.\d+)?/g) || []).map(x => x.replace(/,/g, ''));
    let verdict = '';
    if (id === 'q1') {
      const has = num(a).some(x => Math.abs(+x - E.q1.our_orders) <= 2);
      verdict = has ? '✓ 单数正确' : `✗ 期望 ${E.q1.our_orders} 单，未在回答中找到`;
    } else if (id === 'q2') {
      const has = num(a).some(x => Math.abs(+x - E.q2.our) <= 30);
      verdict = has ? '✓ 累计台数正确' : `✗ 期望累计 ${E.q2.our}，回答: ${a.slice(0, 150)}`;
    } else if (id === 'q3') {
      const has = num(a).some(x => Math.abs(+x - E.q3.orders) <= 2);
      verdict = has ? '✓ 台数正确' : `✗ 期望 ${E.q3.orders} 台，回答: ${a.slice(0, 150)}`;
    } else if (id === 'q4') {
      const hasOur = num(a).some(x => Math.abs(+x - E.q4.our_day) <= 5);
      const hasLm = num(a).some(x => Math.abs(+x - E.q4.lm_day) <= 5);
      verdict = hasOur && hasLm ? '✓ 双方数字都正确' : `△ 我司${E.q4.our_day}/良米${E.q4.lm_day}（9-25）——回答可能用了其他区间`;
    } else if (id === 'q5') {
      const has = a.includes(E.q5.anchor);
      verdict = has ? '✓ 销冠正确' : `✗ 期望 ${E.q5.anchor}，回答: ${a.slice(0, 150)}`;
    } else if (id === 'q6') {
      const has = num(a).some(x => Math.abs(+x - E.q6.total) <= 5);
      verdict = has ? '✓ 总量正确' : `✗ 期望 ${E.q6.total} 单，回答: ${a.slice(0, 150)}`;
    }
    if (verdict.startsWith('✓')) pass++; else fail++;
    console.log(`\n【${id}】${q}\n  ${verdict}\n  回答: ${a.slice(0, 260).replace(/\n/g, ' | ')}`);
  }
  console.log(`\n===== 结果: ${pass} 通过 / ${fail} 存疑或错误 =====`);
  process.exit(fail ? 1 : 0);
})();

// 本地端到端测试：直接调 worker.js 的 fetch，真实访问 GitHub raw + DeepSeek
// 用法：node test.mjs
import worker from './worker.js';

const env = {};
const fs = await import('node:fs');
for (const l of fs.readFileSync(new URL('./.dev.vars', import.meta.url), 'utf-8').split('\n')) {
  const m = l.match(/^([A-Z_]+)=(.*)$/);
  if (m) env[m[1]] = m[2].trim();
}

const base = 'http://localhost';
const results = [];
function check(name, ok, extra = '') {
  results.push([name, ok]);
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${extra ? '  | ' + extra : ''}`);
}

// 1. 页面
const page = await worker.fetch(new Request(base + '/'), env);
check('GET / 返回聊天页', page.status === 200 && (await page.text()).includes('数据小管家'));

// 2. 配置口令开关
const cfg = await (await worker.fetch(new Request(base + '/api/config'), env)).json();
check('GET /api/config', cfg.enabled === true, JSON.stringify(cfg));

// 3. 错误口令
const bad = await worker.fetch(new Request(base + '/api/chat', { method: 'POST', body: JSON.stringify({ code: 'wrong', messages: [{ role: 'user', content: 'hi' }] }) }), env);
check('错误口令 → 403', bad.status === 403);

// 4. 端到端真实问答（DeepSeek + 数据查询）
async function ask(q) {
  const r = await worker.fetch(new Request(base + '/api/chat', {
    method: 'POST', body: JSON.stringify({ code: env.ACCESS_CODE, messages: [{ role: 'user', content: q }] }),
  }), env);
  return { status: r.status, body: await r.json() };
}

console.log('\n--- 端到端问答（真实调用，需要几十秒）---');
const t1 = await ask('9月24日小米官方手环直播间卖了多少台小米手环11？数据截至哪天？');
check('问答1：手环11 台数', t1.status === 200 && /2,\d{3}|2\d{3}/.test(t1.body.answer || ''), (t1.body.answer || t1.body.error || '').slice(0, 160));

const t2 = await ask('手环11首销月目标进度怎么样了？');
check('问答2：首销月进度', t2.status === 200 && /83|84|60000|进度/.test(t2.body.answer || ''), (t2.body.answer || t2.body.error || '').slice(0, 160));

const t3 = await ask('9月24日谁是销冠主播？他/她当班卖了多少钱？');
check('问答3：主播业绩', t3.status === 200 && /主播|班/.test(t3.body.answer || ''), (t3.body.answer || t3.body.error || '').slice(0, 160));

console.log(`\n结果：${results.filter(r => r[1]).length}/${results.length} 通过`);
process.exit(results.every(r => r[1]) ? 0 : 1);

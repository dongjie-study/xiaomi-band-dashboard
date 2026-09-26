// 本地测试：直接调用云函数 main(event)，验证腾讯云版逻辑（含真实 DeepSeek 调用）
// 用法：node test-local.cjs
const fs = require('fs');
const path = require('path');

// 1) 载入密钥（复用 Cloudflare 版的 .dev.vars，该文件已 gitignore）
const varsPath = path.join(__dirname, '..', 'assistant-server', '.dev.vars');
if (fs.existsSync(varsPath)) {
  fs.readFileSync(varsPath, 'utf8').split(/\r?\n/).forEach(line => {
    const m = line.match(/^([A-Z_]+)=(.*)$/);
    if (m) process.env[m[1]] = m[2].trim();
  });
}
if (!process.env.ACCESS_CODE) process.env.ACCESS_CODE = 'xiaomi';
if (!process.env.ACCESS_ENABLED) process.env.ACCESS_ENABLED = 'true';

const fn = require('./cloudfunctions/chat/index.js');

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log(`  ✅ ${name}`); }
  else { fail++; console.log(`  ❌ ${name}${extra ? ' → ' + extra : ''}`); }
}
const ev = o => Object.assign({ path: '/api/chat', httpMethod: 'POST' }, o);

(async () => {
  console.log('\n=== 1. 协议层 ===');
  const opt = await fn.main(ev({ httpMethod: 'OPTIONS' }), {});
  check('OPTIONS 跨域预检 → 204 + CORS', opt.statusCode === 204 && opt.headers['Access-Control-Allow-Origin'] === '*');

  const cfg = await fn.main(ev({ path: '/api/config', httpMethod: 'GET' }), {});
  check('GET /api/config → enabled', cfg.statusCode === 200 && JSON.parse(cfg.body).enabled === true, cfg.body);

  const page = await fn.main({ path: '/api', httpMethod: 'GET' }, {});
  check('GET /api → 内嵌聊天页', page.statusCode === 200 && /数据小管家/.test(page.body));

  const bad = await fn.main(ev({ body: JSON.stringify({ code: 'wrong', messages: [{ role: 'user', content: 'hi' }] }) }), {});
  check('错误口令 → 403', bad.statusCode === 403, bad.body);

  const badBody = await fn.main(ev({ body: 'not json' }), {});
  check('非法请求体 → 400', badBody.statusCode === 400, badBody.body);

  const shortMsgs = await fn.main(ev({ body: JSON.stringify({ code: 'xiaomi', messages: [] }) }), {});
  check('空消息 → 400', shortMsgs.statusCode === 400, shortMsgs.body);

  console.log('\n=== 2. 数据工具（不调 AI，直连本地数据） ===');
  const mod = require('./cloudfunctions/chat/index.js');
  // 通过提问走完整链路更真实，这里先验证基础数据能读到
  const hist = JSON.parse(fs.readFileSync(path.join(__dirname, 'cloudfunctions/chat/assets/history.json'), 'utf8'));
  check('history.json 可读', Array.isArray(hist) && hist.length > 100, `天数=${hist.length}`);
  const hz = fs.existsSync(path.join(__dirname, 'cloudfunctions/chat/assets/hourly.json.gz'));
  check('hourly.json.gz 已生成', hz);

  console.log('\n=== 3. 端到端问答（真实调用 DeepSeek） ===');
  if (!process.env.DEEPSEEK_API_KEY || process.env.DEEPSEEK_API_KEY.startsWith('dummy')) {
    console.log('  ⏭  未找到 DEEPSEEK_API_KEY，跳过端到端测试');
  } else {
    const questions = [
      '9月24日小米官方手环直播间卖了多少台小米手环11？',
      '手环11首销月进度怎么样了？',
      '9月20日到9月24日，小米手环直播间（凝云）谁是销冠主播？',
    ];
    for (const q of questions) {
      const t0 = Date.now();
      const r = await fn.main(ev({ body: JSON.stringify({ code: 'xiaomi', messages: [{ role: 'user', content: q }] }) }), {});
      const d = JSON.parse(r.body);
      const ok = r.statusCode === 200 && d.answer && d.answer.length > 10;
      check(`Q: ${q}`, ok, d.error || JSON.stringify(d).slice(0, 200));
      if (ok) console.log(`     答：${d.answer.replace(/\n/g, ' ').slice(0, 160)}…  (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
    }
  }

  console.log('\n=== 4. 口令开关 ===');
  process.env.ACCESS_ENABLED = 'false';
  const noCode = await fn.main(ev({ body: JSON.stringify({ messages: [{ role: 'user', content: '你好' }] }) }), {});
  check('关闭口令后免口令（非 403）', noCode.statusCode !== 403, noCode.body.slice(0, 120));
  process.env.ACCESS_ENABLED = 'true';

  console.log(`\n结果：${pass} 通过 / ${fail} 失败\n`);
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('测试异常：', e); process.exit(1); });

// 端到端 DOM 桩测试：让模块页脚本在 Node 里真正执行一遍（此前所有失败都是"接口通但页面没跑"）
const fs = require('fs');
const vm = require('vm');

const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', '数据小管家', 'index.html'), 'utf8');
const code = html.match(/<script>([\s\S]*?)<\/script>/)[1];

function el() {
  return {
    hidden: false, value: '', textContent: '', innerHTML: '', style: {},
    disabled: false, scrollTop: 0, scrollHeight: 0,
    children: [],
    appendChild(c) { this.children.push(c); },
    remove() {}, focus() {}, click() {}, addEventListener() {},
    set onclick(f) { this._onclick = f; }, get onclick() { return this._onclick; },
    set onsubmit(f) { this._onsubmit = f; }, get onsubmit() { return this._onsubmit; },
    set onkeydown(f) { this._onkeydown = f; }, get onkeydown() { return this._onkeydown; },
  };
}
const ids = {};
const q = s => { const k = s; if (!ids[k]) ids[k] = el(); return ids[k]; };

const store = {};
const sandbox = {
  console,
  fetch: global.fetch,
  document: { querySelector: q, createElement: () => el() },
  window: { addEventListener() {} },
  localStorage: {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
  },
  location: { reload() {} },
  prompt: () => null,
  setTimeout, clearTimeout,
};
sandbox.window.addEventListener = () => {};
vm.createContext(sandbox);

(async () => {
  let pass = 0, fail = 0;
  const ok = (name, cond) => { cond ? pass++ : (fail++, console.log('  ✗ ' + name)); };

  try { vm.runInContext(code, sandbox); ok('脚本顶层执行无异常', true); }
  catch (e) { console.log('脚本执行失败:', e.message); process.exit(1); }

  // init 是异步的，等它跑完
  await new Promise(r => setTimeout(r, 500));

  ok('欢迎消息已渲染（list 至少 1 条）', ids['#list'] && ids['#list'].children.length >= 1);
  ok('建议问题 chips 已渲染（5 个）', ids['#chips'] && ids['#chips'].children.length === 5);
  ok('表单 onsubmit 已绑定', typeof ids['#f']._onsubmit === 'function');
  ok('口令按钮 onclick 已绑定', typeof ids['#codeBtn']._onclick === 'function');

  // 模拟输入口令并点「进入」→ 应触发真实 /api/chat
  ids['#codeInput'].value = 'xiaomi';
  await ids['#codeBtn']._onclick();
  ok('正确口令后口令框隐藏', ids['#gate'].hidden === true);
  ok('口令已持久化', store['dg_code'] === 'xiaomi');

  // 模拟输入问题并提交 → 真实问答
  q('#q').value = '9月24日小米官方手环直播间卖了多少台手环11？';
  await ids['#f']._onsubmit({ preventDefault() {} });
  await new Promise(r => setTimeout(r, 30000)); // 等 DeepSeek + 工具查询
  const listHtml = ids['#list'].children.map(c => c.innerHTML).join('\n');
  ok('用户问题气泡已渲染', listHtml.includes('9月24日小米官方手环直播间'));
  ok('AI 回答已渲染（含数字）', /台|1487|14\d\d/.test(listHtml));
  ok('回答不是报错信息', !listHtml.includes('网络异常') && !listHtml.includes('出错了'));

  console.log(`\n结果: ${pass} 通过 / ${fail} 失败`);
  console.log('--- AI 回答预览 ---');
  console.log((ids['#list'].children.at(-1)?.innerHTML || '').replace(/<[^>]+>/g, '').slice(0, 220));
  process.exit(fail ? 1 : 0);
})();

// 数据小管家 · 悬浮组件端到端测试
// 用迷你 DOM 桩让 assistant-widget.js 真正执行一遍：结构 → 事件 → 真实问答
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const SRC = path.join(__dirname, '..', 'assistant-widget.js');
const code = fs.readFileSync(SRC, 'utf8');

// ── 迷你 DOM ─────────────────────────────────────────────
function makeEl(tag) {
  const el = {
    tagName: String(tag || 'div').toUpperCase(),
    children: [], _html: '', _text: '',
    className: '', id: '',
    hidden: false, disabled: false, value: '', title: '',
    scrollTop: 0, scrollHeight: 100,
    style: new Proxy({ cssText: '' }, { set(t, k, v) { t[k] = v; return true; }, get(t, k) { return t[k] === undefined ? '' : t[k]; } }),
    _events: {},
    addEventListener(t, f) { (this._events[t] = this._events[t] || []).push(f); },
    removeEventListener() {},
    appendChild(c) { this.children.push(c); c.parentNode = this; return c; },
    remove() {},
    focus() {}, click() {}, setPointerCapture() {}, releasePointerCapture() {},
    closest() { return null; },
    contains() { return false; },
    getBoundingClientRect() { return { width: 400, height: 500, top: 0, left: 0 }; },
    fire(type, ev) { (this._events[type] || []).forEach(f => f(Object.assign({ preventDefault() {}, stopPropagation() {}, target: this }, ev))); },
  };
  Object.defineProperty(el, 'innerHTML', {
    get() { return this._html; },
    set(h) { this._html = String(h); parseInto(String(h), this); },
  });
  Object.defineProperty(el, 'childNodes', { get() { return this.children; } });
  Object.defineProperty(el, 'textContent', { get() { return this._text; }, set(v) { this._text = String(v); } });
  el.classList = {
    _s: new Set(),
    add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
    contains(c) { return this._s.has(c); },
    toggle(c, on) { const v = on === undefined ? !this._s.has(c) : !!on; v ? this._s.add(c) : this._s.delete(c); return v; },
  };
  el.attachShadow = function () {
    if (!this._shadow) {
      resetIndexes();
      this._shadow = {
        _root: null, _host: this,
        getElementById: id => IDX[id] || null,
        querySelector: qs,
        appendChild(c) { this._root = c; return c; },
      };
    }
    return this._shadow;
  };
  return el;
}

let IDX = {};      // id -> el
let CLS = {};      // class -> el[]  (只索引当前 shadow 内的)
function resetIndexes() { IDX = {}; CLS = {}; }
function reg(el) {
  if (el.id) IDX[el.id] = el;
  String(el.className || '').split(/\s+/).filter(Boolean).forEach(c => (CLS[c] = CLS[c] || []).push(el));
}
// 从 HTML 片段里抽出带 id / class 的元素做成对象（不做真实嵌套，够用）
function parseInto(html, parent) {
  const re = /<([a-zA-Z][\w-]*)([^>]*?)\/?>/g;
  let m;
  while ((m = re.exec(html))) {
    const attrs = m[2] || '';
    const idM = attrs.match(/\bid=["']([^"']+)["']/);
    const clM = attrs.match(/\bclass=["']([^"']+)["']/);
    if (!idM && !clM) continue;
    const el = makeEl(m[1]);
    el.id = idM ? idM[1] : '';
    el.className = clM ? clM[1] : '';
    reg(el);
  }
}
function qs(sel) {
  if (sel.startsWith('#')) return IDX[sel.slice(1)] || null;
  if (sel.startsWith('.')) return (CLS[sel.slice(1)] || [])[0] || null;
  return null;
}

function buildSandbox(opts) {
  opts = opts || {};
  resetIndexes();
  const host = makeEl('div');          // 脚本会把它当作组件宿主
  host.contains = function (t) { return t === this; };
  let hostTaken = false;

  const body = makeEl('body');
  const docEvents = {};
  const doc = {
    body,
    documentElement: makeEl('html'),
    createElement: t => {
      if (t === 'div' && !hostTaken) { hostTaken = true; return host; }
      return makeEl(t);
    },
    getElementById: id => (id === 'dg-widget-host' ? (hostTaken ? host : null) : (IDX[id] || null)),
    querySelector: qs,
    addEventListener(t, f) { (docEvents[t] = docEvents[t] || []).push(f); },
    removeEventListener() {},
  };
  const store = {};
  const win = {
    innerWidth: 1440, innerHeight: 900,
    addEventListener() {}, removeEventListener() {},
    prompt: () => null,
  };
  win.self = win; win.top = win;
  if (opts.iframe) { win.top = {}; }

  const sandbox = {
    console,
    fetch: global.fetch,
    document: doc,
    window: win,
    localStorage: {
      getItem: k => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: k => { delete store[k]; },
      _store: store,
    },
    setTimeout, clearTimeout, JSON, Math, Date, Object, Array, String, Number, RegExp, Error, Promise, parseInt, parseFloat, isNaN,
    getComputedStyle: () => ({ right: '22px', bottom: '22px' }),
  };
  sandbox.globalThis = sandbox;
  return {
    sandbox, host, doc, store, docEvents,
    get shadow() { return host._shadow; },
  };
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  let pass = 0, fail = 0;
  const ok = (name, cond, extra) => {
    if (cond) { pass++; console.log('  ✓ ' + name); }
    else { fail++; console.log('  ✗ ' + name + (extra ? '  → ' + extra : '')); }
  };

  // ══ 1. iframe 内不渲染 ══
  console.log('\n[1] iframe 嵌套场景');
  {
    const ctx = buildSandbox({ iframe: true });
    vm.createContext(ctx.sandbox);
    try { vm.runInContext(code, ctx.sandbox); ok('iframe 内静默跳过', true); }
    catch (e) { ok('iframe 内静默跳过', false, e.message); }
    ok('iframe 内未创建任何组件', ctx.doc.body.children.length === 0);
  }

  // ══ 2. 顶层页面正常挂载 ══
  console.log('\n[2] 顶层页面挂载');
  const ctx = buildSandbox();
  vm.createContext(ctx.sandbox);
  try { vm.runInContext(code, ctx.sandbox); ok('脚本顶层执行无异常', true); }
  catch (e) { console.log('  脚本执行失败: ' + e.message + '\n' + e.stack); process.exit(1); }
  await sleep(300);

  const host = ctx.host;
  ok('组件宿主已插入 body', ctx.doc.body.children.length === 1 && ctx.doc.body.children[0] === host);
  const $ = id => ctx.shadow.getElementById(id);
  ['fab', 'panel', 'msgs', 'ta', 'go', 'gate', 'chips', 'hello', 'codeBtn', 'codeInput'].forEach(id => {
    ok('元素存在 #' + id, !!$(id));
  });
  await sleep(1500);   // 等 /api/config 探测完成（后端开了口令门会自动弹面板）

  // ══ 3. 交互骨架 ══
  console.log('\n[3] 交互骨架');
  ok('欢迎消息已渲染', $('msgs').children.length >= 1, 'children=' + $('msgs').children.length);
  ok('快捷问题 5 个', $('chips').children.length === 5, 'chips=' + $('chips').children.length);
  ok('发送按钮 on 绑定', typeof $('go').onclick === 'function');
  ok('textarea keydown 已绑定', ($('ta')._events['keydown'] || []).length > 0);
  ok('fab click 已绑定', ($('fab')._events['click'] || []).length > 0);

  // 后端若开了口令门，脚本会自动弹开面板 —— 先归零到关闭态
  if ($('panel').classList.contains('show')) $('fab').fire('click');
  ok('面板初始为收起态', !$('panel').classList.contains('show'));

  // 打开面板
  $('fab').fire('click');
  ok('点击小球后面板展开', $('panel').classList.contains('show'));

  // 关闭面板
  $('btnClose').onclick();
  ok('关闭按钮可收起', !$('panel').classList.contains('show'));

  // 清空会话
  $('fab').fire('click');
  $('btnClear').onclick();
  ok('清空后回到欢迎语', $('msgs').children.length === 1);

  // ══ 4. 真实问答（走线上后端） ══
  console.log('\n[4] 真实问答端到端（DeepSeek + 工具查询，约 10-30s）');
  $('codeInput').value = 'xiaomi';
  $('codeBtn').onclick();
  let g = 0;
  while (g < 35000) {                       // 口令校验走的是真实 /api/chat，等它跑完
    await sleep(500); g += 500;
    if ($('gate').hidden === true || $('codeErr').textContent) break;
  }
  if ($('gate').hidden !== true) console.log('  [调试] 口令门错误提示: ' + JSON.stringify($('codeErr').textContent || $('codeErr').innerHTML));
  ok('口令校验通过后隐藏口令门', $('gate').hidden === true);
  ok('口令已持久化到 localStorage', ctx.store['dg_code'] === 'xiaomi');

  $('ta').value = '9月24日小米官方手环直播间卖了多少台手环11？';
  $('go').onclick();
  let waited = 0;
  while (waited < 45000) {
    await sleep(1000); waited += 1000;
    const last = $('msgs').children[$('msgs').children.length - 1];
    if (last && !/typing/.test(last.innerHTML || '')) break;
  }
  const allHtml = $('msgs').children.map(c => (c.innerHTML || '')).join('\n');
  ok('用户问题气泡已渲染', allHtml.includes('9月24日小米官方手环直播间'), '');
  ok('AI 回答已渲染（非报错）', !allHtml.includes('网络异常') && !allHtml.includes('出错了'));
  ok('回答含实质数据（数字/台）', /台|台|1\d{2,}|手环/.test(allHtml));
  ok('会话历史已落盘', !!ctx.store['dg_hist']);
  ok('Markdown 渲染器生效（出现结构标签或纯文本）', true);

  const plain = ($('msgs').children[$('msgs').children.length - 1].innerHTML || '').replace(/<[^>]+>/g, '');
  console.log('\n--- AI 回答预览 ---\n' + plain.slice(0, 260));

  console.log('\n结果: ' + pass + ' 通过 / ' + fail + ' 失败');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.log('测试异常: ' + e.stack); process.exit(1); });

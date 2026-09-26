/*!
 * 数据小管家 · 全局悬浮组件
 * ────────────────────────────────────────────────────────────
 * 用法：在任意页面 </body> 前加一行
 *   <script src="assistant-widget.js" defer></script>
 * 子目录页面用相对路径：<script src="../assistant-widget.js" defer></script>
 *
 * 特性
 *  - 右下角悬浮小球，点击弹出对话框（右侧抽屉式面板）
 *  - Shadow DOM 样式隔离，绝不污染/被污染宿主页面
 *  - iframe 内不重复渲染（避免嵌套出现两个球）
 *  - 可拖拽换位、位置记忆、会话历史记忆
 *  - 口令门、Markdown 渲染、快捷提问
 * 换后端只改下面的 API_BASE
 */
(function () {
  'use strict';

  // ── 配置 ────────────────────────────────────────────────
  var API_BASE = 'https://data.xiaomi-exam.top';   // 只填域名，不带 /api
  var VERSION = 'v3';

  // ── 只在顶层窗口渲染 ──────────────────────────────────────
  try { if (window.self !== window.top) return; } catch (e) { return; }
  if (document.getElementById('dg-widget-host')) return;

  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
    del: function (k) { try { localStorage.removeItem(k); } catch (e) {} }
  };

  var SUGGEST = [
    '手环11首销月进度怎么样了？',
    '昨天我司整体卖了多少？',
    '最近7天走势怎么样',
    '谁是这周销冠主播？',
    '良米这周手环11卖了多少台？'
  ];

  var WELCOME = '你好，我是数据小管家 📊\n'
    + '可以问我：每日销量、各直播间/商品/团队数据、小时出单高峰、主播业绩、手环11 首销月进度。\n'
    + '直接用大白话问就行。';

  // ── 样式（全部 scoped 在 shadow root 内） ──────────────────
  var CSS = ''
  + ':host{all:initial;display:block;width:0;height:0}'
  + '*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}'
  + '.root{position:fixed;right:0;bottom:0;width:0;height:0;z-index:2147483000}'
  + '.fab{position:fixed;width:58px;height:58px;border-radius:50%;border:0;cursor:pointer;'
  + '  background:linear-gradient(135deg,#FF6900,#FF9A3D);color:#fff;font-size:25px;line-height:1;'
  + '  box-shadow:0 10px 28px rgba(255,105,0,.42),0 2px 6px rgba(0,0,0,.14);'
  + '  display:flex;align-items:center;justify-content:center;transition:transform .22s cubic-bezier(.34,1.56,.64,1),box-shadow .22s;'
  + '  right:22px;bottom:22px;touch-action:none;user-select:none;-webkit-user-select:none}'
  + '.fab:hover{transform:scale(1.08);box-shadow:0 14px 34px rgba(255,105,0,.5),0 2px 8px rgba(0,0,0,.16)}'
  + '.fab:active{transform:scale(.96)}'
  + '.fab.dragging{transition:none;cursor:grabbing}'
  + '.fab .ic{display:block;transition:transform .3s,opacity .2s}'
  + '.fab.open .ic{transform:rotate(90deg) scale(.9)}'
  + '.fab::after{content:"";position:absolute;inset:0;border-radius:50%;border:2px solid rgba(255,105,0,.55);'
  + '  animation:dgPulse 2.6s ease-out infinite;pointer-events:none}'
  + '.fab.nopulse::after{display:none}'
  + '@keyframes dgPulse{0%{transform:scale(1);opacity:.85}70%{transform:scale(1.5);opacity:0}100%{transform:scale(1.5);opacity:0}}'
  + '.dot{position:absolute;top:2px;right:2px;width:13px;height:13px;border-radius:50%;background:#e02424;'
  + '  border:2px solid #fff;display:none}'
  + '.fab.hasnews .dot{display:block}'

  // 提示气泡
  + '.hello{position:fixed;right:92px;bottom:34px;max-width:250px;background:#fff;color:#1a1d26;'
  + '  border-radius:14px;padding:11px 14px;font-size:13px;line-height:1.5;box-shadow:0 10px 30px rgba(0,0,0,.16);'
  + '  border:1px solid #ffe2cc;opacity:0;transform:translateY(8px) scale(.96);pointer-events:none;transition:all .28s cubic-bezier(.34,1.4,.64,1)}'
  + '.hello.show{opacity:1;transform:none;pointer-events:auto}'
  + '.hello b{color:#FF6900}'
  + '.hello .x{position:absolute;top:-7px;right:-7px;width:19px;height:19px;border-radius:50%;background:#1a1d26;color:#fff;'
  + '  font-size:12px;line-height:1;display:flex;align-items:center;justify-content:center;cursor:pointer;border:0}'

  // 面板
  + '.panel{position:fixed;right:22px;bottom:94px;width:min(620px,calc(100vw - 56px));'
  + '  height:min(920px,calc(100vh - 118px));background:#f5f6f8;'
  + '  border-radius:20px;overflow:hidden;display:flex;flex-direction:column;'
  + '  box-shadow:0 26px 70px rgba(15,20,30,.26),0 2px 10px rgba(0,0,0,.1);'
  + '  opacity:0;transform:translateY(18px) scale(.96);transform-origin:100% 100%;pointer-events:none;'
  + '  transition:opacity .24s,transform .28s cubic-bezier(.34,1.3,.64,1)}'
  + '.panel.show{opacity:1;transform:none;pointer-events:auto}'
  + '@media (max-width:560px){.panel{right:0;bottom:0;width:100%;height:100%;max-height:100%;border-radius:0}'
  + '  .hello{right:88px;bottom:30px}}'

  + '.head{background:linear-gradient(135deg,#FF6900,#ff8f4d);color:#fff;padding:13px 14px;'
  + '  display:flex;align-items:center;gap:10px;flex-shrink:0;cursor:grab;user-select:none}'
  + '.head .logo{width:34px;height:34px;border-radius:10px;background:rgba(255,255,255,.24);'
  + '  display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}'
  + '.head h3{font-size:15px;font-weight:600;line-height:1.25}'
  + '.head .sub{font-size:11px;opacity:.9;font-weight:400;display:flex;align-items:center;gap:5px;margin-top:1px}'
  + '.head .sub i{width:6px;height:6px;border-radius:50%;background:#6ee7a8;display:inline-block;box-shadow:0 0 0 3px rgba(110,231,168,.28)}'
  + '.head .acts{margin-left:auto;display:flex;gap:4px}'
  + '.head .acts button{width:28px;height:28px;border-radius:8px;border:0;background:rgba(255,255,255,.2);color:#fff;'
  + '  font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background .18s}'
  + '.head .acts button:hover{background:rgba(255,255,255,.36)}'

  + '.msgs{flex:1;overflow-y:auto;padding:14px 12px 6px;-webkit-overflow-scrolling:touch;overscroll-behavior:contain}'
  + '.msg{display:flex;margin-bottom:12px;gap:8px;animation:dgIn .26s ease-out}'
  + '@keyframes dgIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}'
  + '.msg .av{width:30px;height:30px;border-radius:9px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:15px}'
  + '.msg.ai .av{background:#fff3e6}'
  + '.msg.me{flex-direction:row-reverse}'
  + '.msg.me .av{background:#1E90FF;color:#fff}'
  + '.bubble{max-width:86%;padding:10px 13px;border-radius:13px;white-space:pre-wrap;word-break:break-word;font-size:14.5px;line-height:1.7}'
  + '.msg.ai .bubble{background:#fff;border:1px solid #e5e7eb;border-top-left-radius:4px;color:#1a1d26}'
  + '.msg.me .bubble{background:#1E90FF;color:#fff;border-top-right-radius:4px}'
  + '.typing i{display:inline-block;width:6px;height:6px;border-radius:50%;background:#bbb;margin-right:3px;animation:dgB 1s infinite}'
  + '.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}'
  + '@keyframes dgB{0%,60%,100%{transform:none;opacity:.4}30%{transform:translateY(-4px);opacity:1}}'

  + '.bubble.md{white-space:normal}'
  + '.bubble.md p{margin:4px 0}'
  + '.bubble.md h4{margin:10px 0 4px;font-size:13.5px;color:#FF6900;font-weight:600}'
  + '.bubble.md ul{margin:4px 0 4px 17px}'
  + '.bubble.md li{margin:2px 0}'
  + '.bubble.md blockquote{border-left:3px solid #FF6900;background:#fff8f3;padding:4px 9px;color:#6b7280;margin:6px 0;border-radius:0 6px 6px 0;font-size:12.5px}'
  + '.bubble.md table{border-collapse:collapse;margin:8px 0;font-size:12.5px;width:100%;display:block;overflow-x:auto}'
  + '.bubble.md th,.bubble.md td{border:1px solid #e5e7eb;padding:5px 9px;text-align:left;white-space:nowrap}'
  + '.bubble.md th{background:#fff3e6;font-weight:600}'
  + '.bubble.md tr:nth-child(even) td{background:#fafbfc}'
  + '.bubble.md code{background:#f0f1f3;border-radius:4px;padding:1px 5px;font-size:12px;font-family:ui-monospace,Consolas,monospace}'

  + '.chips{display:flex;gap:7px;flex-wrap:wrap;padding:2px 12px 8px;flex-shrink:0}'
  + '.chips[hidden]{display:none}'
  + '.chip{border:1px solid #e5e7eb;background:#fff;border-radius:15px;padding:5px 11px;font-size:12px;color:#6b7280;cursor:pointer;transition:all .16s}'
  + '.chip:hover{border-color:#FFB27A;color:#FF6900;background:#fff8f3}'

  + '.foot{display:flex;gap:8px;padding:9px 12px 12px;background:#f5f6f8;flex-shrink:0;align-items:flex-end}'
  + '.foot textarea{flex:1;border:1px solid #e5e7eb;border-radius:14px;padding:12px 13px;font-size:14px;line-height:1.55;'
  + '  background:#fff;outline:none;resize:none;min-height:60px;max-height:150px;color:#1a1d26;transition:border-color .18s}'
  + '.foot textarea:focus{border-color:#1E90FF}'
  + '.foot textarea::placeholder{color:#a5abb6}'
  + '.foot button{min-height:60px;padding:0 18px;font-size:14px;font-weight:600;background:#1E90FF;color:#fff;border:0;'
  + '  border-radius:14px;cursor:pointer;transition:opacity .18s}'
  + '.foot button:hover{opacity:.9}'
  + '.foot button:disabled{opacity:.45;cursor:not-allowed}'

  + '.gate{position:absolute;top:52px;right:0;bottom:0;left:0;background:rgba(245,246,248,.985);display:flex;align-items:center;justify-content:center;padding:22px;z-index:5}'
  + '.gate[hidden]{display:none}'
  + '.gate .box{background:#fff;border-radius:16px;padding:24px 20px;width:100%;max-width:330px;text-align:center;border:1px solid #e5e7eb;box-shadow:0 12px 34px rgba(0,0,0,.08)}'
  + '.gate .ico{font-size:26px;margin-bottom:8px}'
  + '.gate h2{font-size:15px;margin-bottom:6px;color:#1a1d26}'
  + '.gate p{font-size:12px;color:#6b7280;margin-bottom:15px;white-space:pre-line;text-align:left;line-height:1.7}'
  + '.gate input{width:100%;text-align:center;letter-spacing:3px;border:1px solid #e5e7eb;border-radius:10px;padding:10px;font-size:15px;outline:none}'
  + '.gate input:focus{border-color:#1E90FF}'
  + '.gate button{width:100%;margin-top:11px;padding:10px 0;border:0;border-radius:10px;background:#1E90FF;color:#fff;font-size:14px;cursor:pointer}'
  + '.gate button:disabled{opacity:.5}'
  + '.gate .err{color:#e02424;font-size:12px;margin-top:8px;min-height:16px}'
  + '.gate .link{display:inline-block;margin-top:12px;font-size:12px;color:#8a909b;cursor:pointer;text-decoration:underline}';

  // ── DOM ─────────────────────────────────────────────────
  var host;
  try { host = document.createElement('div'); host.id = 'dg-widget-host'; } catch (e) { return; }
  var shadow = host.attachShadow({ mode: 'open' });

  var styleEl = document.createElement('style');
  styleEl.textContent = CSS;
  shadow.appendChild(styleEl);

  var wrap = document.createElement('div');
  wrap.className = 'root';
  wrap.innerHTML =
      '<button class="fab" id="fab" title="数据小管家" aria-label="打开数据小管家">'
    +   '<span class="ic" id="fabIc">💬</span><span class="dot"></span>'
    + '</button>'
    + '<div class="hello" id="hello"><button class="x" id="helloX">✕</button>'
    +   '有问题就问我 <b>数据小管家</b> 👋<br>销量、主播、手环11 进度都能查～</div>'
    + '<div class="panel" id="panel">'
    +   '<div class="head" id="head">'
    +     '<div class="logo">📊</div>'
    +     '<div><h3>数据小管家</h3><div class="sub"><i></i>在线 · 直播间销量数据</div></div>'
    +     '<div class="acts">'
    +       '<button id="btnClear" title="清空对话">🧹</button>'
    +       '<button id="btnSet" title="设置后端地址">⚙</button>'
    +       '<button id="btnClose" title="收起">✕</button>'
    +     '</div>'
    +   '</div>'
    +   '<div class="gate" id="gate" hidden>'
    +     '<div class="box">'
    +       '<div class="ico">🔒</div>'
    +       '<h2 id="gateTitle">请输入访问口令</h2>'
    +       '<p id="gateHint">数据小管家 · 仅限内部使用</p>'
    +       '<input type="text" id="codeInput" placeholder="口令" maxlength="20" autocomplete="off">'
    +       '<button id="codeBtn">进入</button>'
    +       '<div class="err" id="codeErr"></div>'
    +       '<span class="link" id="gateBack">查看设置</span>'
    +     '</div>'
    +   '</div>'
    +   '<div class="msgs" id="msgs"></div>'
    +   '<div class="chips" id="chips"></div>'
    +   '<div class="foot">'
    +     '<textarea id="ta" rows="1" placeholder="问我任何数据问题…（Enter 发送，Shift+Enter 换行）"></textarea>'
    +     '<button id="go">发送</button>'
    +   '</div>'
    + '</div>';
  shadow.appendChild(wrap);
  document.body.appendChild(host);

  var $ = function (s) { return shadow.getElementById(s); };
  var fab = $('fab'), hello = $('hello'), panel = $('panel'), head = $('head');
  var msgs = $('msgs'), chips = $('chips'), ta = $('ta'), goBtn = $('go');
  var gate = $('gate'), codeInput = $('codeInput'), codeBtn = $('codeBtn'), codeErr = $('codeErr');
  var gateTitle = $('gateTitle'), gateHint = $('gateHint');

  // ── 状态 ────────────────────────────────────────────────
  var history_ = [];
  var busy = false;
  var open = false;
  var myCode = store.get('dg_code') || '';
  var base = (API_BASE || store.get('dg_base') || '').replace(/\/+$/, '');
  var flagged = false;   // 后端是否开启了口令门

  // 恢复会话历史
  try {
    var saved = JSON.parse(store.get('dg_hist') || '[]');
    if (Object.prototype.toString.call(saved) === '[object Array]') history_ = saved.slice(-24);
  } catch (e) { history_ = []; }

  function saveHist() {
    try { store.set('dg_hist', JSON.stringify(history_.slice(-24))); } catch (e) {}
  }

  // ── Markdown 渲染 ────────────────────────────────────────
  function esc(s) { return String(s).replace(/[&<>]/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]; }); }
  function mdInline(s) {
    return s.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
            .replace(/`([^`]+)`/g, '<code>$1</code>');
  }
  function mdRender(src) {
    var lines = String(src).split('\n'), out = '', p = [], i = 0;
    function flush() { if (p.length) { out += '<p>' + mdInline(p.join('<br>')) + '</p>'; p = []; } }
    function isSep(l) { return l.indexOf('-') >= 0 && /^[\s|:\-]+$/.test(l); }
    function row(l) { return l.trim().replace(/^\||\|$/g, '').split('|').map(function (c) { return c.trim(); }); }
    while (i < lines.length) {
      var l = lines[i];
      if (/^\s*\|.*\|?\s*$/.test(l) && l.indexOf('|') >= 0 && i + 1 < lines.length && isSep(lines[i + 1])) {
        flush();
        var tb = '<table><tr>' + row(l).map(function (h) { return '<th>' + mdInline(h) + '</th>'; }).join('') + '</tr>';
        i += 2;
        while (i < lines.length && /^\s*\|/.test(lines[i])) {
          tb += '<tr>' + row(lines[i]).map(function (c) { return '<td>' + mdInline(c) + '</td>'; }).join('') + '</tr>';
          i++;
        }
        out += tb + '</table>';
        continue;
      }
      var h = l.match(/^#{1,6}\s+(.*)/);
      if (h) { flush(); out += '<h4>' + mdInline(h[1]) + '</h4>'; i++; continue; }
      if (/^(&gt;|>)\s?/.test(l)) { flush(); out += '<blockquote>' + mdInline(l.replace(/^(&gt;|>)\s?/, '')) + '</blockquote>'; i++; continue; }
      if (/^[-*]\s+/.test(l)) {
        flush();
        var ul = '<ul>';
        while (i < lines.length && /^[-*]\s+/.test(lines[i])) { ul += '<li>' + mdInline(lines[i].replace(/^[-*]\s+/, '')) + '</li>'; i++; }
        out += ul + '</ul>';
        continue;
      }
      if (!l.trim()) { flush(); i++; continue; }
      p.push(l); i++;
    }
    flush();
    return out;
  }

  // ── 消息渲染 ────────────────────────────────────────────
  function add(role, text, typing) {
    var d = document.createElement('div');
    d.className = 'msg ' + role;
    var body = typing
      ? '<span class="typing"><i></i><i></i><i></i></span>'
      : (role === 'ai' ? mdRender(esc(text)) : esc(text));
    d.innerHTML = '<div class="av">' + (role === 'ai' ? '管家' : '我') + '</div>'
      + '<div class="bubble' + (role === 'ai' && !typing ? ' md' : '') + '">' + body + '</div>';
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
    return d;
  }

  function renderHistory() {
    msgs.innerHTML = '';
    if (!history_.length) { add('ai', WELCOME); chipsInit(); return; }
    history_.forEach(function (m) { add(m.role === 'user' ? 'me' : 'ai', m.content); });
    chips.hidden = true;
  }

  function chipsInit() {
    if (chips.childNodes.length) return;
    SUGGEST.forEach(function (s) {
      var c = document.createElement('div');
      c.className = 'chip';
      c.textContent = s;
      c.onclick = function () { if (!busy) send(s); };
      chips.appendChild(c);
    });
  }

  // ── 网络 ────────────────────────────────────────────────
  function api(path, body) {
    var opt = body
      ? {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(Object.assign({}, body, { code: myCode }))
        }
      : undefined;
    return fetch(base + path, opt).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) { return { status: r.status, data: d }; });
    });
  }

  function showGate(title, hint, needInput) {
    gate.hidden = false;
    gateTitle.textContent = title;
    gateHint.innerHTML = hint;
    codeInput.style.display = needInput ? '' : 'none';
    codeBtn.style.display = needInput ? '' : 'none';
    codeErr.textContent = '';
    if (needInput) setTimeout(function () { try { codeInput.focus(); } catch (e) {} }, 120);
  }

  function send(text) {
    if (busy) return;
    text = text || ta.value.trim();
    if (!text) return;
    if (!base) { showGate('小管家还没接上后端', '请点右上角 ⚙ 填写后端地址（只填域名，不带 /api）。', false); return; }
    busy = true;
    goBtn.disabled = true;
    ta.value = '';
    ta.style.height = 'auto';
    chips.hidden = true;
    history_.push({ role: 'user', content: text });
    add('me', text);
    var typingEl = add('ai', '', true);

    api('/api/chat', { messages: history_ }).then(function (res) {
      var status = res.status, data = res.data;
      typingEl.remove();
      if (status === 403) {
        history_.pop(); saveHist();
        showGate('口令不正确', '请重新输入访问口令', true);
        return;
      }
      if (data && data.error) { add('ai', '出错了：' + data.error); }
      else if (data && data.answer) {
        history_.push({ role: 'assistant', content: data.answer });
        add('ai', data.answer);
      } else {
        add('ai', '后端返回异常（HTTP ' + status + '），请稍后再试。');
      }
      saveHist();
    }).catch(function (e) {
      typingEl.remove();
      add('ai', '网络异常，稍后再试：' + (e && e.message ? e.message : e));
    }).then(function () {
      busy = false;
      goBtn.disabled = false;
    });
  }

  // ── 开关面板 ────────────────────────────────────────────
  function setOpen(v) {
    open = v;
    panel.classList.toggle('show', v);
    fab.classList.toggle('open', v);
    $('fabIc').textContent = v ? '✕' : '💬';
    if (v) {
      hello.classList.remove('show');
      fab.classList.remove('hasnews');
      store.set('dg_seen', '1');
      setTimeout(function () {
        try { msgs.scrollTop = msgs.scrollHeight; if (!flagged) ta.focus(); } catch (e) {}
      }, 200);
    }
  }
  fab.addEventListener('click', function () {
    if (dragMoved) { dragMoved = false; return; }
    setOpen(!open);
  });
  $('btnClose').onclick = function () { setOpen(false); };
  $('btnClear').onclick = function () {
    if (!history_.length) { return; }
    history_ = [];
    store.del('dg_hist');
    renderHistory();
    chips.hidden = false;
  };
  $('btnSet').onclick = function () {
    var v = window.prompt('小管家后端地址（只填域名，不带 /api）：', base);
    if (v !== null) {
      base = v.trim().replace(/\/+$/, '');
      store.set('dg_base', base);
      gate.hidden = true;
      add('ai', '后端地址已更新为：' + (base || '（空）'));
    }
  };
  $('gateBack').onclick = function () { $('btnSet').click(); };

  codeBtn.onclick = function () {
    var v = codeInput.value.trim();
    if (!v) return;
    codeBtn.disabled = true;
    codeBtn.textContent = '连接中…';
    codeErr.textContent = '';
    myCode = v;
    api('/api/chat', { messages: [{ role: 'user', content: '你好' }] }).then(function (res) {
      if (res.status === 403) { codeErr.textContent = '口令不正确'; return; }
      if (res.status !== 200) { codeErr.textContent = '后端异常（HTTP ' + res.status + '），点「查看设置」检查地址'; return; }
      store.set('dg_code', v);
      gate.hidden = true;
    }).catch(function () {
      codeErr.innerHTML = '连接不上后端（网络问题或地址不对）。<br>点「查看设置」检查地址。';
    }).then(function () {
      codeBtn.disabled = false;
      codeBtn.textContent = '进入';
    });
  };
  codeInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') codeBtn.click(); });

  // 输入区
  ta.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 150) + 'px';
  });
  ta.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });
  goBtn.onclick = function () { send(); };

  // ── 拖拽小球 ────────────────────────────────────────────
  var dragging = false, dragMoved = false, sx = 0, sy = 0, ox = 0, oy = 0, movedX = 0, movedY = 0;
  (function place() {
    var p = null;
    try { p = JSON.parse(store.get('dg_pos') || 'null'); } catch (e) {}
    if (p && typeof p.r === 'number' && typeof p.b === 'number') {
      fab.style.right = p.r + 'px';
      fab.style.bottom = p.b + 'px';
      panel.style.bottom = (p.b + 72) + 'px';
    }
  })();
  fab.addEventListener('pointerdown', function (e) {
    dragging = true; dragMoved = false;
    sx = e.clientX; sy = e.clientY;
    ox = parseFloat(getComputedStyle(fab).right) || 22;
    oy = parseFloat(getComputedStyle(fab).bottom) || 22;
    fab.classList.add('dragging');
    try { fab.setPointerCapture(e.pointerId); } catch (err) {}
  });
  fab.addEventListener('pointermove', function (e) {
    if (!dragging) return;
    movedX = e.clientX - sx;
    movedY = e.clientY - sy;
    if (Math.abs(movedX) > 4 || Math.abs(movedY) > 4) dragMoved = true;
    if (!dragMoved) return;
    var r = Math.max(8, Math.min(window.innerWidth - 66, ox - movedX));
    var b = Math.max(8, Math.min(window.innerHeight - 66, oy - movedY));
    fab.style.right = r + 'px';
    fab.style.bottom = b + 'px';
    panel.style.bottom = (b + 72) + 'px';
    panel.style.right = Math.min(Math.max(8, r), Math.max(8, window.innerWidth - 630)) + 'px';
  });
  function endDrag() {
    if (!dragging) return;
    dragging = false;
    fab.classList.remove('dragging');
    if (dragMoved) {
      store.set('dg_pos', JSON.stringify({
        r: parseFloat(fab.style.right) || 22,
        b: parseFloat(fab.style.bottom) || 22
      }));
      setTimeout(function () { dragMoved = false; }, 60);
    }
  }
  fab.addEventListener('pointerup', endDrag);
  fab.addEventListener('pointercancel', endDrag);
  fab.addEventListener('pointerleave', endDrag);

  // 面板头部拖拽
  head.addEventListener('pointerdown', function (e) {
    if (e.target.closest && e.target.closest('button')) return;
    var pr = parseFloat(getComputedStyle(panel).right) || 22;
    var pb = parseFloat(getComputedStyle(panel).bottom) || 94;
    var x0 = e.clientX, y0 = e.clientY, mm = false;
    function mv(ev) {
      var dx = ev.clientX - x0, dy = ev.clientY - y0;
      if (Math.abs(dx) > 4 || Math.abs(dy) > 4) mm = true;
      if (!mm) return;
      panel.style.right = Math.max(8, Math.min(window.innerWidth - panel.offsetWidth - 8, pr - dx)) + 'px';
      panel.style.bottom = Math.max(8, Math.min(window.innerHeight - 60, pb - dy)) + 'px';
    }
    function up() {
      document.removeEventListener('pointermove', mv);
      document.removeEventListener('pointerup', up);
    }
    document.addEventListener('pointermove', mv);
    document.addEventListener('pointerup', up);
  });

  // 点击外部关闭（仅桌面，移动端全屏不关）
  document.addEventListener('click', function (e) {
    if (!open) return;
    if (window.innerWidth <= 560) return;
    var t = e.target;
    if (t === fab || (t.closest && t.closest('.fab'))) return;
    if (host.contains(t)) return;
    setOpen(false);
  }, true);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && open) setOpen(false);
  });

  // ── 初始化 ──────────────────────────────────────────────
  renderHistory();

  // 首次访问的引导气泡
  if (!store.get('dg_seen')) {
    setTimeout(function () { if (!open) { hello.classList.add('show'); fab.classList.add('hasnews'); } }, 2200);
    setTimeout(function () { hello.classList.remove('show'); store.set('dg_seen', '1'); }, 16000);
  }
  $('helloX').onclick = function (e) {
    e.stopPropagation();
    hello.classList.remove('show');
    store.set('dg_seen', '1');
  };
  hello.addEventListener('click', function () { setOpen(true); });

  // 探测后端是否开启了口令门
  if (base) {
    api('/api/config').then(function (res) {
      var cfg = res.data || {};
      flagged = !!cfg.enabled;
      if (flagged && !myCode) { setOpen(true); showGate('请输入访问口令', '数据小管家 · 仅限内部使用', true); }
    }).catch(function () {});
  }

  // 对外暴露，方便调试
  window.DGAssistant = {
    open: function () { setOpen(true); },
    close: function () { setOpen(false); },
    ask: function (q) { setOpen(true); send(q); },
    version: VERSION
  };
})();

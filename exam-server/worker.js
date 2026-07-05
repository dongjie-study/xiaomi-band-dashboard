import examHtml from './exam.html';

const ADMIN_TOKEN = 'xiaomi2026';

// ---- Admin Page Template ----
function adminPage(results) {
  const sorted = [...results].sort((a, b) => b.score - a.score);
  const groups = {};
  let passed = 0;
  sorted.forEach(r => {
    if (!groups[r.group]) groups[r.group] = { count: 0, totalScore: 0, passed: 0 };
    groups[r.group].count++;
    groups[r.group].totalScore += r.score;
    if (r.pct >= 100) groups[r.group].passed++;
    if (r.pct >= 100) passed++;
  });

  const rows = sorted.map((r, i) =>
    `<tr style="${r.pct >= 100 ? 'background:#e6fff0' : 'background:#fff5f5'}">
      <td>${i + 1}</td><td><strong>${esc(r.name)}</strong></td><td>${esc(r.group) || '-'}</td>
      <td style="font-weight:700;color:${r.pct >= 100 ? '#16a34a' : '#e94560'}">${r.score}</td>
      <td>${r.pct}%</td><td>${r.correct} / ${(r.correct||0)+(r.wrong||0)}</td>
      <td>${r.pct >= 100 ? '🏆 通过' : '❌ 未通过'}</td>
      <td style="font-size:12px;color:#888">${fmtTime(r.time)}</td></tr>`
  ).join('');

  const groupRows = Object.entries(groups).map(([g, s]) =>
    `<tr><td><strong>${esc(g) || '未填组别'}</strong></td><td>${s.count}</td><td>${s.passed}</td>
      <td>${s.count > 0 ? Math.round(s.totalScore / s.count) : 0}</td>
      <td>${s.count > 0 ? Math.round(s.passed / s.count * 100) : 0}%</td></tr>`
  ).join('');

  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>考试管理后台</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f0f4f8;color:#0f172a;min-height:100vh}.header{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:24px 32px;text-align:center}.header h1{font-size:22px;margin-bottom:4px}.header p{font-size:13px;color:#94a3b8}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;max-width:1100px;margin:20px auto;padding:0 20px}.stat{background:#fff;border-radius:12px;padding:20px;text-align:center;box-shadow:0 2px 10px rgba(0,0,0,.04);border:1px solid #e8ecf1}.stat .num{font-size:30px;font-weight:800}.stat .lbl{font-size:12px;color:#888;margin-top:4px}.stat.green .num{color:#20bf6b}.stat.red .num{color:#e94560}.stat.blue .num{color:#3867d6}.stat.purple .num{color:#8854d0}.container{max-width:1100px;margin:0 auto;padding:0 20px 40px}.card{background:#fff;border-radius:12px;padding:24px;margin-bottom:16px;box-shadow:0 2px 10px rgba(0,0,0,.04);border:1px solid #e8ecf1}.card h3{font-size:15px;font-weight:700;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #e8ecf1;color:#3867d6}table{width:100%;border-collapse:collapse;font-size:13px}th{background:#f8f9fc;padding:10px 12px;text-align:left;font-weight:600;color:#64748b;border-bottom:2px solid #e8ecf1;font-size:12px}td{padding:10px 12px;border-bottom:1px solid #f0f2f5}tr:hover td{background:#f8fafc}.refresh{text-align:right;font-size:12px;color:#94a3b8;margin-top:12px}.footer{text-align:center;padding:20px;color:#94a3b8;font-size:12px}@media(max-width:768px){.stats{grid-template-columns:1fr 1fr}}</style></head><body><div class="header"><h1>📊 主播合规考试 — 管理后台</h1><p>实时查看所有主播考试成绩 · 共 ${sorted.length} 人 · ${new Date().toLocaleString('zh-CN')} 刷新</p></div><div class="stats"><div class="stat blue"><div class="num">${sorted.length}</div><div class="lbl">总考试人次</div></div><div class="stat green"><div class="num">${passed}</div><div class="lbl">满分通过</div></div><div class="stat red"><div class="num">${sorted.length - passed}</div><div class="lbl">未通过</div></div><div class="stat purple"><div class="num">${sorted.length > 0 ? Math.round(passed / sorted.length * 100) : 0}%</div><div class="lbl">通过率</div></div></div><div class="container"><div class="card"><h3>📋 各组别汇总</h3><table><thead><tr><th>组别</th><th>人数</th><th>通过</th><th>平均分</th><th>通过率</th></tr></thead><tbody>${groupRows || '<tr><td colspan="5" style="text-align:center;color:#888">暂无数据</td></tr>'}</tbody></table></div><div class="card"><h3>📝 详细成绩单（按分数降序）</h3><table><thead><tr><th>#</th><th>姓名</th><th>组别</th><th>分数</th><th>正确率</th><th>对/错</th><th>结果</th><th>交卷时间</th></tr></thead><tbody>${rows || '<tr><td colspan="8" style="text-align:center;color:#888">暂无考试记录</td></tr>'}</tbody></table><div class="refresh">🔄 刷新页面获取最新数据</div></div></div><div class="footer">小米系直播间 · 主播合规考试系统</div></body></html>`;
}

function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function fmtTime(t) { try { const d = new Date(t); return d.toLocaleString('zh-CN', {month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}); } catch(e) { return t; } }

// ---- Main Worker ----
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const method = request.method;
    const path = url.pathname;

    // POST /api/submit — store exam result
    if (method === 'POST' && path === '/api/submit') {
      try {
        const body = await request.json();
        const { name, group, score, total, pct, correct, wrong, grade } = body;
        if (!name || score === undefined) {
          return new Response(JSON.stringify({ error: '缺少姓名或成绩' }), { status: 400, headers: { 'Content-Type': 'application/json' } });
        }
        const record = {
          name: String(name).trim(),
          group: String(group || '').trim(),
          score, total, pct, correct, wrong, grade,
          time: new Date().toISOString()
        };
        // Load existing results from KV
        const raw = await env.EXAM_KV.get('results');
        const results = raw ? JSON.parse(raw) : [];
        results.push(record);
        await env.EXAM_KV.put('results', JSON.stringify(results));
        console.log(`[提交] ${record.name} | ${record.group} | ${record.score}/${record.total} | ${record.grade}`);
        return new Response(JSON.stringify({ ok: true, id: results.length }), { headers: { 'Content-Type': 'application/json' } });
      } catch (e) {
        return new Response(JSON.stringify({ error: '请求格式错误' }), { status: 400, headers: { 'Content-Type': 'application/json' } });
      }
    }

    // GET /api/results?token=xxx
    if (method === 'GET' && path === '/api/results') {
      if (url.searchParams.get('token') !== ADMIN_TOKEN) {
        return new Response(JSON.stringify({ error: 'token 错误' }), { status: 403, headers: { 'Content-Type': 'application/json' } });
      }
      const raw = await env.EXAM_KV.get('results');
      const results = raw ? JSON.parse(raw) : [];
      return new Response(JSON.stringify({ count: results.length, results }), { headers: { 'Content-Type': 'application/json' } });
    }

    // GET /admin?token=xxx
    if (method === 'GET' && path === '/admin') {
      const token = url.searchParams.get('token') || '';
      if (token !== ADMIN_TOKEN) {
        return new Response(`<html><body style="font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#f0f4f8"><div style="background:#fff;padding:40px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.1);text-align:center"><h2 style="color:#e94560">🔒 需要授权</h2><p>请在 URL 后添加 <code>?token=你的密码</code></p></div></body></html>`, { status: 403, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
      }
      const raw = await env.EXAM_KV.get('results');
      const results = raw ? JSON.parse(raw) : [];
      return new Response(adminPage(results), { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
    }

    // Serve exam page for root or /index.html
    if (method === 'GET' && (path === '/' || path === '/index.html' || path === '/主播合规考试.html')) {
      return new Response(examHtml, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
    }

    // 404
    return new Response('<h2>404 - 页面不存在</h2>', { status: 404, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
  }
};

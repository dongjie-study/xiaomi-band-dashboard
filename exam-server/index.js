const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || 'xiaomi2026';

// 自动适配数据目录
const DATA_DIR = fs.existsSync('/tmp') ? '/tmp/data' : path.join(__dirname, 'data');
const RESULTS_FILE = path.join(DATA_DIR, 'results.json');

// MIME types for static files
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

function loadResults() {
  try { return JSON.parse(fs.readFileSync(RESULTS_FILE, 'utf-8')); }
  catch (e) { return []; }
}

function saveResults(data) {
  fs.writeFileSync(RESULTS_FILE, JSON.stringify(data, null, 2), 'utf-8');
}

function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function fmtTime(t) { try { const d = new Date(t); return d.toLocaleString('zh-CN', {month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}); } catch(e) { return t; } }

function readBody(req) {
  return new Promise((resolve) => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try { resolve(JSON.parse(body)); }
      catch (e) { resolve({}); }
    });
  });
}

// Admin dashboard HTML
function adminPage(results) {
  results = [...results].sort((a, b) => b.score - a.score);

  const groups = {};
  let passed = 0;
  results.forEach(r => {
    if (!groups[r.group]) groups[r.group] = { count: 0, totalScore: 0, passed: 0 };
    groups[r.group].count++;
    groups[r.group].totalScore += r.score;
    if (r.pct >= 100) groups[r.group].passed++;
    if (r.pct >= 100) passed++;
  });

  const rows = results.map((r, i) => `
    <tr style="${r.pct >= 100 ? 'background:#e6fff0' : 'background:#fff5f5'}">
      <td>${i + 1}</td>
      <td><strong>${esc(r.name)}</strong></td>
      <td>${esc(r.group) || '-'}</td>
      <td style="font-weight:700;color:${r.pct >= 100 ? '#16a34a' : '#e94560'}">${r.score}</td>
      <td>${r.pct}%</td>
      <td>${r.correct} / ${(r.correct||0)+(r.wrong||0)}</td>
      <td>${r.pct >= 100 ? '🏆 通过' : '❌ 未通过'}</td>
      <td style="font-size:12px;color:#888">${fmtTime(r.time)}</td>
    </tr>`).join('');

  const groupRows = Object.entries(groups).map(([g, s]) => `
    <tr>
      <td><strong>${esc(g) || '未填组别'}</strong></td>
      <td>${s.count}</td>
      <td>${s.passed}</td>
      <td>${s.count > 0 ? Math.round(s.totalScore / s.count) : 0}</td>
      <td>${s.count > 0 ? Math.round(s.passed / s.count * 100) : 0}%</td>
    </tr>`).join('');

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>考试管理后台</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f0f4f8;color:#0f172a;min-height:100vh}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:24px 32px;text-align:center}
.header h1{font-size:22px;margin-bottom:4px}
.header p{font-size:13px;color:#94a3b8}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;max-width:1100px;margin:20px auto;padding:0 20px}
.stat{background:#fff;border-radius:12px;padding:20px;text-align:center;box-shadow:0 2px 10px rgba(0,0,0,.04);border:1px solid #e8ecf1}
.stat .num{font-size:30px;font-weight:800}
.stat .lbl{font-size:12px;color:#888;margin-top:4px}
.stat.green .num{color:#20bf6b}
.stat.red .num{color:#e94560}
.stat.blue .num{color:#3867d6}
.stat.purple .num{color:#8854d0}
.container{max-width:1100px;margin:0 auto;padding:0 20px 40px}
.card{background:#fff;border-radius:12px;padding:24px;margin-bottom:16px;box-shadow:0 2px 10px rgba(0,0,0,.04);border:1px solid #e8ecf1}
.card h3{font-size:15px;font-weight:700;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #e8ecf1;color:#3867d6}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:#f8f9fc;padding:10px 12px;text-align:left;font-weight:600;color:#64748b;border-bottom:2px solid #e8ecf1;font-size:12px}
td{padding:10px 12px;border-bottom:1px solid #f0f2f5}
tr:hover td{background:#f8fafc}
.refresh{text-align:right;font-size:12px;color:#94a3b8;margin-top:12px}
.footer{text-align:center;padding:20px;color:#94a3b8;font-size:12px}
@media(max-width:768px){.stats{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>
<div class="header">
  <h1>📊 主播合规考试 — 管理后台</h1>
  <p>实时查看所有主播考试成绩 · 共 ${results.length} 人 · ${new Date().toLocaleString('zh-CN')} 刷新</p>
</div>
<div class="stats">
  <div class="stat blue"><div class="num">${results.length}</div><div class="lbl">总考试人次</div></div>
  <div class="stat green"><div class="num">${passed}</div><div class="lbl">满分通过</div></div>
  <div class="stat red"><div class="num">${results.length - passed}</div><div class="lbl">未通过</div></div>
  <div class="stat purple"><div class="num">${results.length > 0 ? Math.round(passed / results.length * 100) : 0}%</div><div class="lbl">通过率</div></div>
</div>
<div class="container">
  <div class="card">
    <h3>📋 各组别汇总</h3>
    <table>
      <thead><tr><th>组别</th><th>人数</th><th>通过</th><th>平均分</th><th>通过率</th></tr></thead>
      <tbody>${groupRows || '<tr><td colspan="5" style="text-align:center;color:#888">暂无数据</td></tr>'}</tbody>
    </table>
  </div>
  <div class="card">
    <h3>📝 详细成绩单（按分数降序）</h3>
    <table>
      <thead><tr><th>#</th><th>姓名</th><th>组别</th><th>分数</th><th>正确率</th><th>对/错</th><th>结果</th><th>交卷时间</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="8" style="text-align:center;color:#888">暂无考试记录</td></tr>'}</tbody>
    </table>
    <div class="refresh">🔄 刷新页面获取最新数据</div>
  </div>
</div>
<div class="footer">小米系直播间 · 主播合规考试系统</div>
</body></html>`;
}

// Create server
const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const method = req.method;

  try {
    // POST /api/submit
    if (method === 'POST' && url.pathname === '/api/submit') {
      const body = await readBody(req);
      const { name, group, score, total, pct, correct, wrong, grade } = body;
      if (!name || score === undefined) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ error: '缺少姓名或成绩' }));
      }
      const record = {
        name: String(name).trim(),
        group: String(group || '').trim(),
        score, total, pct,
        correct, wrong, grade,
        time: new Date().toISOString()
      };
      const results = loadResults();
      results.push(record);
      saveResults(results);
      console.log(`[提交] ${record.name} | ${record.group} | ${record.score}/${record.total} | ${record.grade}`);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ ok: true, id: results.length }));
    }

    // GET /api/results
    if (method === 'GET' && url.pathname === '/api/results') {
      if (url.searchParams.get('token') !== ADMIN_TOKEN) {
        res.writeHead(403, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ error: 'token 错误' }));
      }
      const results = loadResults();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ count: results.length, results }));
    }

    // GET /admin
    if (method === 'GET' && url.pathname === '/admin') {
      const token = url.searchParams.get('token') || '';
      if (token !== ADMIN_TOKEN) {
        res.writeHead(403, { 'Content-Type': 'text/html; charset=utf-8' });
        return res.end(`<html><body style="font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#f0f4f8"><div style="background:#fff;padding:40px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.1);text-align:center"><h2 style="color:#e94560">🔒 需要授权</h2><p>请在 URL 后添加 <code>?token=你的密码</code></p></div></body></html>`);
      }
      const results = loadResults();
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      return res.end(adminPage(results));
    }

    // Serve static files
    let filePath = url.pathname === '/' ? '/主播合规考试.html' : url.pathname;
    filePath = path.join(__dirname, filePath);

    // Security: prevent directory traversal
    if (!filePath.startsWith(__dirname)) {
      res.writeHead(403);
      return res.end('Forbidden');
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME[ext] || 'application/octet-stream';

    if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
      const content = fs.readFileSync(filePath);
      res.writeHead(200, { 'Content-Type': contentType });
      return res.end(content);
    }

    // 404
    res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end('<h2>404 - 页面不存在</h2>');

  } catch (err) {
    console.error(err);
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: '服务器内部错误' }));
  }
});

// Ensure data dir
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
if (!fs.existsSync(RESULTS_FILE)) fs.writeFileSync(RESULTS_FILE, '[]');

// Start server
server.listen(PORT, () => {
  console.log(`考试服务器已启动: http://localhost:${PORT}`);
  console.log(`管理后台: http://localhost:${PORT}/admin?token=${ADMIN_TOKEN}`);
});
